# era/routes/api_routes.py
from flask import Blueprint, request, jsonify, g # g はリクエスト固有のデータを保存するオブジェクト
from db_instance import db
import models
from flask_jwt_extended import jwt_required, get_jwt_identity, JWTManager # JWTManagerもインポート
from sqlalchemy import desc, func, or_
from services import audit, moderate_text, notify

# API用のBlueprintを作成
bp = Blueprint('api', __name__, url_prefix='/api')


def current_user_from_jwt():
    username = get_jwt_identity()
    return models.User.query.filter_by(username=username).first()


def serialize_user(user):
    return {
        "id": user.id,
        "username": user.username,
        "age_zone": user.public_age_zone,
        "bio": user.bio,
        "profile_image": user.profile_image,
        "following_count": user.following.count(),
        "followers_count": user.followers.count(),
        "role": user.role,
    }


def serialize_tweet(tweet, viewer=None):
    liked = False
    if viewer:
        liked = models.Like.query.filter_by(user_id=viewer.id, tweet_id=tweet.id).first() is not None
    return {
        "id": tweet.id,
        "body": tweet.body,
        "timestamp": tweet.timestamp.isoformat(),
        "author": serialize_user(tweet.author),
        "image_url": tweet.image_url,
        "topic": tweet.topic,
        "age_zone": tweet.age_zone or tweet.author.public_age_zone,
        "likes_count": tweet.likes.count(),
        "replies_count": tweet.replies.count(),
        "liked_by_me": liked,
        "moderation_status": tweet.moderation_status,
    }

# JWTManagerのインスタンスは app.py で作成し、ここで参照できるようにする
# ここではjwtオブジェクトを直接使わず、デコレータとヘルパー関数のみ使用

# ロールチェック用デコレータ (オプション: 管理者権限などが必要なAPI用)
def role_required(required_roles):
    def decorator(fn):
        @jwt_required()
        def wrapper(*args, **kwargs):
            username = get_jwt_identity() # トークンからユーザー名取得
            user = models.User.query.filter_by(username=username).first()
            if user and user.role in required_roles:
                g.current_user = user # 現在のユーザー情報をgオブジェクトに保存
                return fn(*args, **kwargs)
            else:
                return jsonify({'message': 'Permission denied'}), 403
        wrapper.__name__ = fn.__name__ # デコレータが関数の名前を変更しないようにする
        return wrapper
    return decorator

# --- コアAPIエンドポイント ---

# 投稿作成API (認証必須)
@bp.route('/tweets', methods=['POST'])
@jwt_required() # JWT認証必須
def create_tweet_api():
    # トークンから認証済みのユーザー名を取得
    username = get_jwt_identity()
    current_user = models.User.query.filter_by(username=username).first()

    if not current_user:
        return jsonify({"message": "User not found (from token)"}), 404

    data = request.get_json() # JSON形式のリクエストボディを取得
    body = (data.get('body') or '').strip()

    if not body:
        return jsonify({"message": "Tweet body is required"}), 400
    if len(body) > 280:
        return jsonify({"message": "Tweet body must be 280 characters or less"}), 400

    status, reason = moderate_text(body)
    tweet = models.Tweet(
        body=body,
        user_id=current_user.id,
        topic=data.get('topic'),
        image_url=data.get('image_url'),
        age_zone=current_user.public_age_zone,
        moderation_status=status,
        moderation_reason=reason,
    )
    db.session.add(tweet)
    audit('api_tweet_create', current_user.id, status)
    db.session.commit()

    return jsonify({"message": "Tweet created successfully", "tweet": serialize_tweet(tweet, current_user)}), 201

# 自分のツイート取得API (認証必須)
@bp.route('/my_tweets', methods=['GET'])
@jwt_required() # JWT認証必須
def get_my_tweets_api():
    username = get_jwt_identity()
    current_user = models.User.query.filter_by(username=username).first()

    if not current_user:
        return jsonify({"message": "User not found (from token)"}), 404

    # 自分のツイートを新しい順に取得
    tweets = current_user.tweets.order_by(models.Tweet.timestamp.desc()).all()

    # ツイートのリストをJSON形式で整形して返す
    tweet_list = []
    for tweet in tweets:
        tweet_list.append({
            "id": tweet.id,
            "body": tweet.body,
            "timestamp": tweet.timestamp.isoformat(), # 日時をISO形式の文字列に変換
            "author_username": current_user.username
        })
    return jsonify(tweet_list), 200


@bp.route('/me', methods=['GET'])
@jwt_required()
def me_api():
    current_user = current_user_from_jwt()
    if not current_user:
        return jsonify({"message": "User not found"}), 404
    unread_count = models.Notification.query.filter_by(user_id=current_user.id, is_read=False).count()
    return jsonify({"user": serialize_user(current_user), "unread_count": unread_count}), 200


@bp.route('/timeline', methods=['GET'])
@jwt_required()
def timeline_api():
    current_user = current_user_from_jwt()
    if not current_user:
        return jsonify({"message": "User not found"}), 404
    zone = request.args.get('zone') or current_user.public_age_zone
    followed_ids = [f.followed_id for f in current_user.following]
    display_ids = followed_ids + [current_user.id]
    tweets = models.Tweet.query.filter(
        models.Tweet.is_deleted.is_(False),
        models.Tweet.moderation_status == 'approved',
        models.Tweet.parent_id.is_(None),
        or_(models.Tweet.user_id.in_(display_ids), models.Tweet.age_zone == zone),
    ).order_by(models.Tweet.timestamp.desc()).limit(50).all()
    trends = db.session.query(models.Tweet.topic, func.count(models.Tweet.id)).filter(
        models.Tweet.topic.isnot(None),
        models.Tweet.age_zone == zone,
        models.Tweet.moderation_status == 'approved',
    ).group_by(models.Tweet.topic).order_by(desc(func.count(models.Tweet.id))).limit(5).all()
    suggested = models.User.query.filter(
        models.User.id != current_user.id,
        models.User.age_band == current_user.public_age_zone,
        models.User.is_verified.is_(True),
    ).limit(4).all()
    return jsonify({
        "tweets": [serialize_tweet(tweet, current_user) for tweet in tweets],
        "trends": [{"topic": topic, "count": count} for topic, count in trends],
        "suggested_users": [serialize_user(user) for user in suggested],
        "selected_zone": zone,
    }), 200


@bp.route('/tweets/<int:tweet_id>/like', methods=['POST'])
@jwt_required()
def like_tweet_api(tweet_id):
    current_user = current_user_from_jwt()
    tweet = models.Tweet.query.get_or_404(tweet_id)
    like = models.Like.query.filter_by(user_id=current_user.id, tweet_id=tweet.id).first()
    if like:
        db.session.delete(like)
        audit('api_tweet_unlike', current_user.id, str(tweet.id))
    else:
        db.session.add(models.Like(user_id=current_user.id, tweet_id=tweet.id))
        notify(tweet.user_id, 'like', f'{current_user.username} さんが投稿にいいねしました。', current_user.id, tweet.id)
        audit('api_tweet_like', current_user.id, str(tweet.id))
    db.session.commit()
    return jsonify({"tweet": serialize_tweet(tweet, current_user)}), 200


@bp.route('/tweets/<int:tweet_id>/replies', methods=['POST'])
@jwt_required()
def reply_tweet_api(tweet_id):
    current_user = current_user_from_jwt()
    parent = models.Tweet.query.get_or_404(tweet_id)
    data = request.get_json()
    body = (data.get('body') or '').strip()
    if not body:
        return jsonify({"message": "Reply body is required"}), 400
    status, reason = moderate_text(body)
    reply = models.Tweet(
        body=body[:280],
        user_id=current_user.id,
        parent_id=parent.id,
        age_zone=current_user.public_age_zone,
        moderation_status=status,
        moderation_reason=reason,
    )
    db.session.add(reply)
    notify(parent.user_id, 'reply', f'{current_user.username} さんが投稿に返信しました。', current_user.id, parent.id)
    audit('api_tweet_reply', current_user.id, str(parent.id))
    db.session.commit()
    return jsonify({"reply": serialize_tweet(reply, current_user)}), 201


@bp.route('/notifications', methods=['GET'])
@jwt_required()
def notifications_api():
    current_user = current_user_from_jwt()
    items = models.Notification.query.filter_by(user_id=current_user.id).order_by(models.Notification.created_at.desc()).limit(50).all()
    models.Notification.query.filter_by(user_id=current_user.id, is_read=False).update({'is_read': True})
    db.session.commit()
    return jsonify({"notifications": [{
        "id": item.id,
        "kind": item.kind,
        "message": item.message,
        "created_at": item.created_at.isoformat(),
        "is_read": item.is_read,
    } for item in items]}), 200


@bp.route('/messages', methods=['GET', 'POST'])
@jwt_required()
def messages_api():
    current_user = current_user_from_jwt()
    if request.method == 'POST':
        data = request.get_json()
        recipient = models.User.query.filter_by(username=data.get('recipient')).first()
        body = (data.get('body') or '').strip()
        if not recipient or not body:
            return jsonify({"message": "Recipient and body are required"}), 400
        status, _reason = moderate_text(body)
        message = models.DirectMessage(
            sender_id=current_user.id,
            recipient_id=recipient.id,
            body=body[:1000],
            moderation_status=status,
        )
        db.session.add(message)
        notify(recipient.id, 'dm', f'{current_user.username} さんからメッセージが届きました。', current_user.id)
        audit('api_dm_send', current_user.id, recipient.username)
        db.session.commit()
        return jsonify({"message": "sent"}), 201
    messages = models.DirectMessage.query.filter(
        or_(models.DirectMessage.sender_id == current_user.id, models.DirectMessage.recipient_id == current_user.id)
    ).order_by(models.DirectMessage.created_at.desc()).limit(50).all()
    return jsonify({"messages": [{
        "id": message.id,
        "sender": serialize_user(message.sender),
        "recipient": serialize_user(message.recipient),
        "body": message.body,
        "created_at": message.created_at.isoformat(),
        "moderation_status": message.moderation_status,
    } for message in messages]}), 200

# ユーザープロフィール取得API (誰でもアクセス可能)
@bp.route('/users/<username>', methods=['GET'])
def get_user_profile_api(username):
    user = models.User.query.filter_by(username=username).first()
    if not user:
        return jsonify({"message": "User not found"}), 404

    # プロフィール情報をJSONで返す
    return jsonify({
        "username": user.username,
        "age_zone": user.public_age_zone,
        "created_at": user.created_at.isoformat(),
        "bio": user.bio, # 新しく追加したbioカラム
        "profile_image": user.profile_image, # 新しく追加したprofile_imageカラム
        "role": user.role # 役割
    }), 200


# プロフィール編集API (認証必須: 自分のプロフィールのみ)
@bp.route('/profile/edit', methods=['PUT']) # PUTメソッドで更新
@jwt_required() # JWT認証必須
def edit_profile_api():
    username = get_jwt_identity() # トークンからユーザー名取得
    current_user = models.User.query.filter_by(username=username).first()

    if not current_user:
        return jsonify({"message": "User not found (from token)"}), 404

    data = request.get_json() # JSON形式のリクエストボディを取得

    # bioとprofile_imageの更新（存在する場合のみ）
    if 'bio' in data:
        current_user.bio = data['bio']
    if 'profile_image' in data:
        current_user.profile_image = data['profile_image']
    
    # 必要に応じて、他のプロフィール項目（例: user_age, email）もここで更新可能
    # ただし、username の変更は通常別途ロジックが必要（ユニーク制約など）

    try:
        db.session.commit() # 変更をコミット
        return jsonify({"message": "Profile updated successfully"}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({"message": f"Failed to update profile: {str(e)}"}), 500


# 例: 管理者のみがアクセスできるAPI (role_requiredデコレータの使用例)
# @bp.route('/admin/users', methods=['GET'])
# @role_required(['admin']) # 'admin'ロールを持つユーザーのみアクセス可能
# def get_all_users_admin_api():
#    users = models.User.query.all()
#    user_list = [{"username": u.username, "email": u.email, "role": u.role} for u in users]
#    return jsonify(user_list), 200
