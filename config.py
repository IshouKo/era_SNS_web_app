import os

class Config:
    # Docker Composeで定義するPostgreSQLサービス名と、ユーザー、パスワード、DB名を指定
    # Docker Composeのservice名がdbなので、ホスト名をdbにする
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or \
                              'postgresql://user:password@db:5432/sns_db'
    SQLALCHEMY_TRACK_MODIFICATIONS = False # シグナル追跡を無効化 (非推奨機能のため)

    # セッション管理などに使用する秘密鍵
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'your_super_secret_key_here'
    WTF_CSRF_ENABLED = True
    
    # JWTの設定
    JWT_SECRET_KEY = os.environ.get('JWT_SECRET_KEY') or 'super-secret-jwt-key'

    # Optional OpenAI Moderation. Keep blank until you obtain a key.
    OPENAI_API_KEY = os.environ.get('OPENAI_API_KEY', '')
    OPENAI_MODERATION_MODEL = os.environ.get('OPENAI_MODERATION_MODEL', 'omni-moderation-latest')

    # Upload storage. Local storage is the default; S3-compatible storage can be wired later.
    STORAGE_BACKEND = os.environ.get('STORAGE_BACKEND', 'local')
    UPLOAD_FOLDER = os.environ.get('UPLOAD_FOLDER', 'static/uploads')

    # Simple in-app rate limiting.
    RATE_LIMIT_WINDOW_SECONDS = int(os.environ.get('RATE_LIMIT_WINDOW_SECONDS', '60'))
    RATE_LIMIT_MAX_REQUESTS = int(os.environ.get('RATE_LIMIT_MAX_REQUESTS', '30'))

    # Mail settings. In development, email is printed to the console.
    MAIL_FROM = os.environ.get('MAIL_FROM', 'noreply@era.local')
    APP_BASE_URL = os.environ.get('APP_BASE_URL', 'http://localhost:5000')

    # デバッグモードの設定
    DEBUG = os.environ.get('FLASK_DEBUG', '1') == '1'
