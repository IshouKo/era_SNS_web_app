from flask import Blueprint, render_template, request, redirect, url_for, flash, session, current_app
from db_instance import db
from models import DirectMessage, Follow, Like, Notification, Report, Tweet, User
from sqlalchemy import and_, desc, func, or_
from services import audit, moderate_text, notify, save_upload, validate_csrf

bp = Blueprint('main', __name__)


def require_login():
    if 'user_id' not in session:
        flash('ログインしてください。', 'danger')
        return None
    return User.query.get(session['user_id'])


def visible_tweets_query():
    return Tweet.query.filter_by(is_deleted=False, moderation_status='approved', parent_id=None)

@bp.route('/')
def index():
    if 'user_id' not in session:
        return redirect(url_for('auth.login'))

    logged_in_user = User.query.get(session['user_id'])
    if not logged_in_user:
        session.pop('user_id', None)
        session.pop('username', None)
        flash('ユーザーが見つかりません。再ログインしてください。', 'danger')
        return redirect(url_for('auth.login'))

    followed_users_ids = [f.followed_id for f in logged_in_user.following]
    display_user_ids = followed_users_ids + [logged_in_user.id]
    zone = request.args.get('zone') or logged_in_user.public_age_zone

    tweets = visible_tweets_query().filter(
        or_(Tweet.user_id.in_(display_user_ids), Tweet.age_zone == zone)
    ).order_by(Tweet.timestamp.desc()).limit(50).all()
    trends = db.session.query(Tweet.topic, func.count(Tweet.id)).filter(
        Tweet.topic.isnot(None),
        Tweet.age_zone == zone,
        Tweet.moderation_status == 'approved',
    ).group_by(Tweet.topic).order_by(desc(func.count(Tweet.id))).limit(5).all()
    suggested_users = User.query.filter(
        User.id != logged_in_user.id,
        User.age_band == logged_in_user.public_age_zone,
        User.is_verified.is_(True),
    ).limit(4).all()
    unread_count = Notification.query.filter_by(user_id=logged_in_user.id, is_read=False).count()
    communities = ['プログラミング', '音楽好き', 'カフェ巡り', '旅行記録']

    return render_template(
        'index.html',
        user=logged_in_user,
        tweets=tweets,
        trends=trends,
        suggested_users=suggested_users,
        unread_count=unread_count,
        communities=communities,
        selected_zone=zone,
    )


@bp.route('/post_tweet', methods=['POST'])
def post_tweet():
    if 'user_id' not in session:
        flash('ログインしてください。', 'danger')
        return redirect(url_for('auth.login'))

    if not validate_csrf():
        flash('セッションの有効期限が切れました。もう一度お試しください。', 'danger')
        return redirect(url_for('main.index'))

    current_user = User.query.get(session['user_id'])
    body = request.form['body'].strip()
    topic = request.form.get('topic') or None
    image_url = None
    image_file = request.files.get('image_file')
    if image_file and image_file.filename:
        try:
            image_url = save_upload(image_file, 'posts')
        except Exception as exc:
            flash(str(exc), 'danger')
            return redirect(url_for('main.index'))
    if not body:
        flash('ツイート内容を入力してください。', 'danger')
        return redirect(url_for('main.index'))

    if len(body) > 280:
        flash('ツイートは280文字以内で入力してください。', 'danger')
        return redirect(url_for('main.index'))

    moderation_status, moderation_reason = moderate_text(body)
    tweet = Tweet(
        body=body,
        user_id=session['user_id'],
        image_url=image_url,
        topic=topic,
        age_zone=current_user.public_age_zone,
        moderation_status=moderation_status,
        moderation_reason=moderation_reason,
    )
    db.session.add(tweet)
    audit('tweet_create', session['user_id'], moderation_status)
    db.session.commit()
    if moderation_status == 'blocked':
        flash('投稿は有害コンテンツ検知により保留されました。', 'danger')
    else:
        flash('投稿が作成されました！', 'success')
    return redirect(url_for('main.index'))


@bp.route('/profile/<username>', methods=['GET', 'POST'])
def profile(username):
    target_user = User.query.filter_by(username=username).first_or_404()
    tweets = target_user.tweets.filter_by(is_deleted=False, moderation_status='approved', parent_id=None).order_by(Tweet.timestamp.desc()).all()

    # ログイン中のユーザーが自分のプロフィールを見ているか
    is_current_user_profile = ('user_id' in session and session['user_id'] == target_user.id)


    is_following = False
    if 'user_id' in session and session['user_id'] != target_user.id:
        logged_in_user = User.query.get(session['user_id'])
        if logged_in_user:
            is_following = db.session.query(Follow).filter_by(
                follower_id=logged_in_user.id,
                followed_id=target_user.id
            ).first() is not None

    # プロフィール更新フォームのPOST処理
    if request.method == 'POST' and is_current_user_profile: # 自分のプロフィールかつPOSTリクエストの場合
        if not validate_csrf():
            flash('セッションの有効期限が切れました。もう一度お試しください。', 'danger')
            return redirect(url_for('main.profile', username=username))
        bio = request.form.get('bio', None)
        # ファイルアップロード処理
        profile_image_path = target_user.profile_image # デフォルトは現在の画像パス

        if 'profile_image_file' in request.files: # ファイルが送信されたかチェック
            file = request.files['profile_image_file']
            if file.filename != '': # ファイルが選択されているか
                try:
                    profile_image_path = save_upload(file, 'profiles')
                except Exception as e:
                    flash(f'プロフィール画像の保存に失敗しました: {str(e)}', 'danger')
                    return redirect(url_for('main.profile', username=username))
            else:
                # ファイルが選択されていないが、input type="file"があるため、既存の値を保持する場合はここを調整
                # 今回は空文字列が送られてきたらNoneにする（つまり画像削除）か、既存保持のロジックを組む
                # 現状はファイルが送られなかったら既存のパスを保持
                pass # file.filename == '' の場合は、profile_image_path は変更しない（現在のまま）

        # 'profile_image_remove' チェックボックスがオンの場合、画像を削除
        if request.form.get('profile_image_remove') == 'on':
            profile_image_path = None # DBからパスを削除
        
        target_user.bio = bio # データベースのbioを更新
        target_user.profile_image = profile_image_path # データベースのprofile_imageを更新

        try:
            audit('profile_update', target_user.id)
            db.session.commit()
            flash('プロフィールが更新されました！', 'success')
        except Exception as e:
            db.session.rollback()
            flash(f'プロフィールの更新に失敗しました: {str(e)}', 'danger')
        
        return redirect(url_for('main.profile', username=username)) # 更新後、プロフィールページにリダイレクト

    # GETリクエストの場合、またはPOSTでエラーがあった場合は表示
    return render_template(
        'profile.html',
        target_user=target_user,
        tweets=tweets,
        is_following=is_following,
        is_current_user_profile=is_current_user_profile # テンプレートにフラグを渡す
    )

    return render_template('profile.html', target_user=target_user, tweets=tweets, is_following=is_following)

@bp.route('/follow/<username>')
def follow(username):
    if 'user_id' not in session:
        flash('ログインしてください。', 'danger')
        return redirect(url_for('auth.login'))

    logged_in_user = User.query.get(session['user_id'])
    target_user = User.query.filter_by(username=username).first_or_404()

    if logged_in_user.id == target_user.id:
        flash('自分自身をフォローすることはできません。', 'danger')
        return redirect(url_for('main.profile', username=username))

    existing_follow = Follow.query.filter_by(
        follower_id=logged_in_user.id,
        followed_id=target_user.id
    ).first()

    if existing_follow:
        flash(f'あなたは既に{username}さんをフォローしています。', 'info')
    else:
        follow_record = Follow(follower_id=logged_in_user.id, followed_id=target_user.id)
        db.session.add(follow_record)
        notify(target_user.id, 'follow', f'{logged_in_user.username} さんがあなたをフォローしました。', logged_in_user.id)
        audit('follow', logged_in_user.id, target_user.username)
        db.session.commit()
        flash(f'{username}さんをフォローしました！', 'success')

    return redirect(url_for('main.profile', username=username))


@bp.route('/unfollow/<username>')
def unfollow(username):
    if 'user_id' not in session:
        flash('ログインしてください。', 'danger')
        return redirect(url_for('auth.login'))

    logged_in_user = User.query.get(session['user_id'])
    target_user = User.query.filter_by(username=username).first_or_404()

    if logged_in_user.id == target_user.id:
        flash('自分自身をアンフォローすることはできません。', 'danger')
        return redirect(url_for('main.profile', username=username))

    follow_record = Follow.query.filter_by(
        follower_id=logged_in_user.id,
        followed_id=target_user.id
    ).first()

    if follow_record:
        db.session.delete(follow_record)
        audit('unfollow', logged_in_user.id, target_user.username)
        db.session.commit()
        flash(f'{username}さんのフォローを解除しました。', 'info')
    else:
        flash(f'あなたは{username}さんをフォローしていません。', 'info')

    return redirect(url_for('main.profile', username=username))


@bp.route('/tweet/<int:tweet_id>/like', methods=['POST'])
def like_tweet(tweet_id):
    current_user = require_login()
    if not current_user:
        return redirect(url_for('auth.login'))
    if not validate_csrf():
        flash('セッションの有効期限が切れました。', 'danger')
        return redirect(url_for('main.index'))
    tweet = Tweet.query.get_or_404(tweet_id)
    like = Like.query.filter_by(user_id=current_user.id, tweet_id=tweet.id).first()
    if like:
        db.session.delete(like)
        audit('tweet_unlike', current_user.id, str(tweet.id))
    else:
        db.session.add(Like(user_id=current_user.id, tweet_id=tweet.id))
        notify(tweet.user_id, 'like', f'{current_user.username} さんが投稿にいいねしました。', current_user.id, tweet.id)
        audit('tweet_like', current_user.id, str(tweet.id))
    db.session.commit()
    return redirect(request.referrer or url_for('main.index'))


@bp.route('/tweet/<int:tweet_id>/reply', methods=['POST'])
def reply_tweet(tweet_id):
    current_user = require_login()
    if not current_user:
        return redirect(url_for('auth.login'))
    if not validate_csrf():
        flash('セッションの有効期限が切れました。', 'danger')
        return redirect(url_for('main.index'))
    parent = Tweet.query.get_or_404(tweet_id)
    body = request.form.get('body', '').strip()
    if not body:
        flash('返信内容を入力してください。', 'danger')
        return redirect(request.referrer or url_for('main.index'))
    status, reason = moderate_text(body)
    reply = Tweet(
        body=body[:280],
        user_id=current_user.id,
        parent_id=parent.id,
        age_zone=current_user.public_age_zone,
        moderation_status=status,
        moderation_reason=reason,
    )
    db.session.add(reply)
    notify(parent.user_id, 'reply', f'{current_user.username} さんが投稿に返信しました。', current_user.id, parent.id)
    audit('tweet_reply', current_user.id, str(parent.id))
    db.session.commit()
    flash('返信しました。' if status == 'approved' else '返信はモデレーション待ちです。', 'success' if status == 'approved' else 'warning')
    return redirect(request.referrer or url_for('main.index'))


@bp.route('/tweet/<int:tweet_id>/report', methods=['POST'])
def report_tweet(tweet_id):
    current_user = require_login()
    if not current_user:
        return redirect(url_for('auth.login'))
    if not validate_csrf():
        flash('セッションの有効期限が切れました。', 'danger')
        return redirect(url_for('main.index'))
    tweet = Tweet.query.get_or_404(tweet_id)
    reason = request.form.get('reason', '不適切な投稿')
    db.session.add(Report(
        reporter_id=current_user.id,
        tweet_id=tweet.id,
        reported_user_id=tweet.user_id,
        reason=reason[:200],
    ))
    tweet.moderation_status = 'review'
    tweet.moderation_reason = 'ユーザー通報により確認待ち'
    audit('tweet_report', current_user.id, f'{tweet.id}:{reason}')
    db.session.commit()
    flash('通報を受け付けました。', 'info')
    return redirect(request.referrer or url_for('main.index'))


@bp.route('/notifications')
def notifications():
    current_user = require_login()
    if not current_user:
        return redirect(url_for('auth.login'))
    items = Notification.query.filter_by(user_id=current_user.id).order_by(Notification.created_at.desc()).limit(50).all()
    Notification.query.filter_by(user_id=current_user.id, is_read=False).update({'is_read': True})
    db.session.commit()
    return render_template('notifications.html', user=current_user, notifications=items)


@bp.route('/messages', methods=['GET', 'POST'])
def messages():
    current_user = require_login()
    if not current_user:
        return redirect(url_for('auth.login'))
    if request.method == 'POST':
        if not validate_csrf():
            flash('セッションの有効期限が切れました。', 'danger')
            return redirect(url_for('main.messages'))
        recipient = User.query.filter_by(username=request.form.get('recipient')).first()
        body = request.form.get('body', '').strip()
        if not recipient or not body:
            flash('宛先と本文を入力してください。', 'danger')
            return redirect(url_for('main.messages'))
        status, reason = moderate_text(body)
        db.session.add(DirectMessage(
            sender_id=current_user.id,
            recipient_id=recipient.id,
            body=body[:1000],
            moderation_status=status,
        ))
        notify(recipient.id, 'dm', f'{current_user.username} さんからメッセージが届きました。', current_user.id)
        audit('dm_send', current_user.id, recipient.username)
        db.session.commit()
        flash('メッセージを送信しました。' if status == 'approved' else 'メッセージはモデレーション待ちです。', 'success' if status == 'approved' else 'warning')
        return redirect(url_for('main.messages'))
    inbox = DirectMessage.query.filter(
        or_(DirectMessage.sender_id == current_user.id, DirectMessage.recipient_id == current_user.id)
    ).order_by(DirectMessage.created_at.desc()).limit(50).all()
    users = User.query.filter(User.id != current_user.id).order_by(User.username).all()
    return render_template('messages.html', user=current_user, messages=inbox, users=users)


@bp.route('/discover')
def discover():
    current_user = require_login()
    if not current_user:
        return redirect(url_for('auth.login'))
    zone = request.args.get('zone') or current_user.public_age_zone
    tweets = visible_tweets_query().filter(Tweet.age_zone == zone).order_by(Tweet.timestamp.desc()).limit(50).all()
    return render_template('discover.html', user=current_user, tweets=tweets, selected_zone=zone)
