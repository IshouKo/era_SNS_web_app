from flask import Blueprint, render_template, request, redirect, url_for, flash, session, jsonify, abort
from db_instance import db
from models import AuditLog, Report, Tweet, User
from services import audit, validate_csrf, verified_age_band
from datetime import datetime
import os

bp = Blueprint('admin', __name__, url_prefix='/admin')

def requires_admin_role():
    if 'user_id' not in session:
        flash('ログインが必要です。', 'danger')
        return redirect(url_for('auth.login'))
    
    user = User.query.get(session['user_id'])
    if not user or not user.is_admin():
        flash('アクセス権がありません。', 'danger')
        abort(403)

@bp.before_request
def before_request():
    if request.endpoint and 'admin' in request.endpoint:
        requires_admin_role()

@bp.route('/verification')
def verification_queue():
    pending_users = User.query.filter_by(verification_status='uploaded_both').all()
    return render_template('admin/verification.html', pending_users=pending_users)


def delete_images(user):
    """ユーザーの関連画像ファイルをサーバーから削除するヘルパー関数"""
    if user.id_card_image:
        try:
            filepath = os.path.join('static', user.id_card_image.split('uploads/')[1])
            if os.path.exists(filepath):
                os.remove(filepath)
        except Exception:
            pass
        user.id_card_image = None
    if user.face_scan_image:
        try:
            filepath = os.path.join('static', user.face_scan_image.split('uploads/')[1])
            if os.path.exists(filepath):
                os.remove(filepath)
        except Exception:
            pass
        user.face_scan_image = None

@bp.route('/verification/approve/<int:user_id>', methods=['POST'])
def approve_user(user_id):
    if not request.is_json and not validate_csrf():
        flash('セッションの有効期限が切れました。', 'danger')
        return redirect(url_for('admin.verification_queue'))
    user = User.query.get_or_404(user_id)
    if user.verification_status != 'uploaded_both':
        return jsonify({'message': '無効な操作です。'}), 400

    user.is_verified = True
    user.verification_status = 'approved'
    user.age_band = verified_age_band(user.birth_date, user.user_age)
    user.age_verified_at = datetime.utcnow()
    delete_images(user) # 承認後に画像を削除
    audit('admin_verify_approve', session.get('user_id'), user.username)
    db.session.commit()

    flash(f'{user.username}の本人確認を承認し、関連画像を削除しました。', 'success')
    if not request.is_json:
        return redirect(url_for('admin.verification_queue'))
    return jsonify({'message': '承認完了'})


@bp.route('/verification/reject/<int:user_id>', methods=['POST'])
def reject_user(user_id):
    if not request.is_json and not validate_csrf():
        flash('セッションの有効期限が切れました。', 'danger')
        return redirect(url_for('admin.verification_queue'))
    user = User.query.get_or_404(user_id)
    if user.verification_status != 'uploaded_both':
        return jsonify({'message': '無効な操作です。'}), 400

    user.is_verified = False
    user.verification_status = 'rejected'
    delete_images(user) # 拒否後に画像を削除
    audit('admin_verify_reject', session.get('user_id'), user.username)
    db.session.commit()

    flash(f'{user.username}の本人確認を拒否し、関連画像を削除しました。', 'danger')
    if not request.is_json:
        return redirect(url_for('admin.verification_queue'))
    return jsonify({'message': '拒否完了'})


@bp.route('/moderation')
def moderation_queue():
    tweets = Tweet.query.filter(Tweet.moderation_status.in_(['blocked', 'review'])).order_by(Tweet.timestamp.desc()).all()
    reports = Report.query.filter_by(status='open').order_by(Report.created_at.desc()).all()
    return render_template('admin/moderation.html', tweets=tweets, reports=reports)


@bp.route('/moderation/tweet/<int:tweet_id>/<action>', methods=['POST'])
def moderate_tweet(tweet_id, action):
    if not validate_csrf():
        flash('セッションの有効期限が切れました。', 'danger')
        return redirect(url_for('admin.moderation_queue'))
    tweet = Tweet.query.get_or_404(tweet_id)
    if action == 'approve':
        tweet.moderation_status = 'approved'
        tweet.moderation_reason = None
        flash('投稿を承認しました。', 'success')
    elif action == 'delete':
        tweet.is_deleted = True
        tweet.moderation_status = 'deleted'
        flash('投稿を削除扱いにしました。', 'danger')
    else:
        return jsonify({'message': '無効な操作です。'}), 400
    Report.query.filter_by(tweet_id=tweet.id, status='open').update({'status': 'closed'})
    audit(f'admin_moderate_{action}', session.get('user_id'), str(tweet.id))
    db.session.commit()
    return redirect(url_for('admin.moderation_queue'))


@bp.route('/audit')
def audit_logs():
    logs = AuditLog.query.order_by(AuditLog.created_at.desc()).limit(100).all()
    return render_template('admin/audit.html', logs=logs)
