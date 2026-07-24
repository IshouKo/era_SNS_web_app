from db_instance import db
from datetime import date, datetime
from werkzeug.security import generate_password_hash, check_password_hash


def calculate_age(birth_date):
    if not birth_date:
        return None
    today = date.today()
    return today.year - birth_date.year - ((today.month, today.day) < (birth_date.month, birth_date.day))


def age_zone_for_age(age):
    if age is None:
        return '未確認ゾーン'
    if age < 13:
        return 'キッズゾーン'
    if age < 18:
        return 'ティーンゾーン'
    if age < 30:
        return 'Z世代ゾーン'
    if age < 45:
        return 'ミレニアルゾーン'
    if age < 60:
        return 'アダルトゾーン'
    return 'シニアゾーン'

class User(db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    user_age = db.Column(db.Integer, nullable=False) # 後方互換用。公開表示には使わない。
    birth_date = db.Column(db.Date, nullable=True)
    age_verified_at = db.Column(db.DateTime, nullable=True)
    age_band = db.Column(db.String(40), nullable=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(128))
    role = db.Column(db.String(50), default='user') # ユーザーの役割 ('user', 'admin'など)
    bio = db.Column(db.String(500), nullable=True) # 自己紹介
    profile_image = db.Column(db.String(200), nullable=True) # プロフィール画像URL
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    email_verified = db.Column(db.Boolean, default=False)
    email_verification_token = db.Column(db.String(128), nullable=True, index=True)
    password_reset_token = db.Column(db.String(128), nullable=True, index=True)
    password_reset_sent_at = db.Column(db.DateTime, nullable=True)

    # --- 本人確認機能のために追加するカラム ---
    id_card_image = db.Column(db.String(200), nullable=True)  # 身分証明書の画像パス
    face_scan_image = db.Column(db.String(200), nullable=True) # 顔スキャン（カメラ撮影）の画像パス
    is_verified = db.Column(db.Boolean, default=False)      # 本人確認が完了したかどうかのフラグ
    verification_status = db.Column(db.String(50), default='pending') # 本人確認のステータス (例: 'pending', 'approved', 'rejected')
    # ----------------------------------------

    tweets = db.relationship('Tweet', backref='author', lazy='dynamic')
    following = db.relationship(
        'Follow',
        foreign_keys='Follow.follower_id',
        backref='follower',
        lazy='dynamic'
    )
    followers = db.relationship(
        'Follow',
        foreign_keys='Follow.followed_id',
        backref='followed',
        lazy='dynamic'
    )

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    @property
    def current_age(self):
        return calculate_age(self.birth_date) or self.user_age

    @property
    def public_age_zone(self):
        return self.age_band or age_zone_for_age(self.current_age)
    
    def is_admin(self): # 管理者かどうかをチェックするヘルパーメソッド
        return self.role == 'admin'

    def __repr__(self):
        return f'<User {self.username}>'


class Tweet(db.Model):
    __tablename__ = 'tweets'
    id = db.Column(db.Integer, primary_key=True)
    body = db.Column(db.String(280), nullable=False)
    timestamp = db.Column(db.DateTime, index=True, default=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    parent_id = db.Column(db.Integer, db.ForeignKey('tweets.id'), nullable=True)
    image_url = db.Column(db.String(300), nullable=True)
    video_url = db.Column(db.String(300), nullable=True)
    topic = db.Column(db.String(80), nullable=True)
    age_zone = db.Column(db.String(40), nullable=True, index=True)
    moderation_status = db.Column(db.String(30), default='approved', index=True)
    moderation_reason = db.Column(db.String(300), nullable=True)
    is_deleted = db.Column(db.Boolean, default=False)
    replies = db.relationship('Tweet', backref=db.backref('parent', remote_side=[id]), lazy='dynamic')
    likes = db.relationship('Like', backref='tweet', lazy='dynamic', cascade='all, delete-orphan')

    def __repr__(self):
        return f'<Tweet {self.id}: {self.body[:20]}...>'


class Follow(db.Model):
    __tablename__ = 'follows'
    follower_id = db.Column(db.Integer, db.ForeignKey('users.id'), primary_key=True)
    followed_id = db.Column(db.Integer, db.ForeignKey('users.id'), primary_key=True)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f'<Follower {self.follower_id} follows {self.followed_id}>'


class Like(db.Model):
    __tablename__ = 'likes'
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), primary_key=True)
    tweet_id = db.Column(db.Integer, db.ForeignKey('tweets.id'), primary_key=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    user = db.relationship('User', backref=db.backref('likes', lazy='dynamic'))


class Notification(db.Model):
    __tablename__ = 'notifications'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    actor_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    tweet_id = db.Column(db.Integer, db.ForeignKey('tweets.id'), nullable=True)
    kind = db.Column(db.String(40), nullable=False)
    message = db.Column(db.String(220), nullable=False)
    is_read = db.Column(db.Boolean, default=False, index=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    user = db.relationship('User', foreign_keys=[user_id], backref=db.backref('notifications', lazy='dynamic'))
    actor = db.relationship('User', foreign_keys=[actor_id])
    tweet = db.relationship('Tweet')


class DirectMessage(db.Model):
    __tablename__ = 'direct_messages'
    id = db.Column(db.Integer, primary_key=True)
    sender_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    recipient_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    body = db.Column(db.String(1000), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    read_at = db.Column(db.DateTime, nullable=True)
    moderation_status = db.Column(db.String(30), default='approved')
    sender = db.relationship('User', foreign_keys=[sender_id], backref=db.backref('sent_messages', lazy='dynamic'))
    recipient = db.relationship('User', foreign_keys=[recipient_id], backref=db.backref('received_messages', lazy='dynamic'))


class Report(db.Model):
    __tablename__ = 'reports'
    id = db.Column(db.Integer, primary_key=True)
    reporter_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    tweet_id = db.Column(db.Integer, db.ForeignKey('tweets.id'), nullable=True, index=True)
    reported_user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    reason = db.Column(db.String(200), nullable=False)
    status = db.Column(db.String(30), default='open', index=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    reporter = db.relationship('User', foreign_keys=[reporter_id])
    reported_user = db.relationship('User', foreign_keys=[reported_user_id])
    tweet = db.relationship('Tweet', backref=db.backref('reports', lazy='dynamic'))


class AuditLog(db.Model):
    __tablename__ = 'audit_logs'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True, index=True)
    action = db.Column(db.String(80), nullable=False, index=True)
    ip_address = db.Column(db.String(64), nullable=True)
    user_agent = db.Column(db.String(255), nullable=True)
    detail = db.Column(db.String(500), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    user = db.relationship('User')
