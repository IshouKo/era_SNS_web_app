import base64
import os
import secrets
import time
import uuid
from datetime import date, datetime, timedelta

from flask import current_app, request, session, url_for
from werkzeug.utils import secure_filename

from db_instance import db
from models import AuditLog, Notification, age_zone_for_age, calculate_age

_rate_limit_buckets = {}


def generate_token():
    return secrets.token_urlsafe(32)


def csrf_token():
    token = session.get('_csrf_token')
    if not token:
        token = generate_token()
        session['_csrf_token'] = token
    return token


def validate_csrf():
    expected = session.get('_csrf_token')
    supplied = request.form.get('csrf_token') or request.headers.get('X-CSRF-Token')
    return bool(expected and supplied and secrets.compare_digest(expected, supplied))


def rate_limited(key, max_requests=None, window_seconds=None):
    max_requests = max_requests or current_app.config['RATE_LIMIT_MAX_REQUESTS']
    window_seconds = window_seconds or current_app.config['RATE_LIMIT_WINDOW_SECONDS']
    now = time.time()
    bucket = _rate_limit_buckets.setdefault(key, [])
    bucket[:] = [seen for seen in bucket if now - seen < window_seconds]
    if len(bucket) >= max_requests:
        return True
    bucket.append(now)
    return False


def audit(action, user_id=None, detail=None):
    log = AuditLog(
        user_id=user_id,
        action=action,
        ip_address=request.headers.get('X-Forwarded-For', request.remote_addr),
        user_agent=(request.headers.get('User-Agent') or '')[:255],
        detail=(detail or '')[:500],
    )
    db.session.add(log)


def notify(user_id, kind, message, actor_id=None, tweet_id=None):
    if user_id and user_id != actor_id:
        db.session.add(Notification(
            user_id=user_id,
            actor_id=actor_id,
            tweet_id=tweet_id,
            kind=kind,
            message=message[:220],
        ))


def parse_birth_date(value):
    if not value:
        return None
    return date.fromisoformat(value)


def verified_age_band(birth_date, fallback_age=None):
    age = calculate_age(birth_date) if birth_date else fallback_age
    return age_zone_for_age(age)


def save_upload(file_storage, subdir='images'):
    if not file_storage or not file_storage.filename:
        return None
    ext = file_storage.filename.rsplit('.', 1)[-1].lower()
    if ext not in current_app.config['ALLOWED_EXTENSIONS']:
        raise ValueError('許可されていないファイル形式です。')
    filename = secure_filename(file_storage.filename)
    unique_filename = f'{uuid.uuid4()}_{filename}'
    upload_root = current_app.config['UPLOAD_FOLDER']
    target_dir = os.path.join(upload_root, subdir)
    os.makedirs(target_dir, exist_ok=True)
    file_storage.save(os.path.join(target_dir, unique_filename))
    return url_for('static', filename=f'uploads/{subdir}/{unique_filename}')


def save_base64_image(data_url, prefix='capture', subdir='verification'):
    header, encoded = data_url.split(',', 1)
    binary_data = base64.b64decode(encoded)
    unique_filename = f'{uuid.uuid4()}_{prefix}.png'
    target_dir = os.path.join(current_app.config['UPLOAD_FOLDER'], subdir)
    os.makedirs(target_dir, exist_ok=True)
    file_path = os.path.join(target_dir, unique_filename)
    with open(file_path, 'wb') as handle:
        handle.write(binary_data)
    return file_path, url_for('static', filename=f'uploads/{subdir}/{unique_filename}')


def moderate_text(text):
    normalized = (text or '').lower()
    banned_keywords = [
        '死ね', '殺す', '自殺しろ', '爆破', 'テロ', '個人情報', '住所晒し',
        'kill yourself', 'terrorist attack', 'doxx',
    ]
    for keyword in banned_keywords:
        if keyword in normalized:
            return 'blocked', f'禁止語句を検出しました: {keyword}'

    api_key = current_app.config.get('OPENAI_API_KEY')
    if not api_key:
        return 'approved', None

    try:
        from openai import OpenAI
        client = OpenAI(api_key=api_key)
        result = client.moderations.create(
            model=current_app.config['OPENAI_MODERATION_MODEL'],
            input=text,
        )
        flagged = bool(result.results[0].flagged)
        if flagged:
            return 'blocked', 'OpenAI Moderation が有害コンテンツの可能性を検出しました。'
    except Exception as exc:
        current_app.logger.warning('OpenAI moderation failed: %s', exc)

    return 'approved', None


def send_email(to_email, subject, body):
    current_app.logger.info('Email to %s | %s\n%s', to_email, subject, body)


def verification_link(token):
    return f"{current_app.config['APP_BASE_URL']}{url_for('auth.verify_email', token=token)}"


def reset_link(token):
    return f"{current_app.config['APP_BASE_URL']}{url_for('auth.reset_password', token=token)}"


def reset_token_is_valid(user):
    return (
        user.password_reset_sent_at
        and datetime.utcnow() - user.password_reset_sent_at < timedelta(hours=2)
    )
