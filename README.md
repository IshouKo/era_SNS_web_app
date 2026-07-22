# Era — Generation-Aware Social Networking Prototype

> A Flask-based SNS prototype exploring safer, age-aware online communities.

Eraは、世代ごとの文化・共通言語・安全性を考慮したコミュニティ設計を目指すSNSプロトタイプです。現在の実装では、アカウント登録、本人確認、投稿、フォロー、プロフィール、管理者確認、JWT APIなど、SNSの基盤機能を構築しています。

## Concept / コンセプト

一般的なSNSでは、年齢や生活背景が大きく異なるユーザーが同一空間に集まり、コミュニケーションの摩擦や安全上の問題が生じることがあります。

Eraは将来的に、ユーザーを年齢層に応じた**Safe Zone**へ案内し、世代特有の文化や共通言語に基づくコミュニケーションを促進することを目指しています。

```text
Registration
     |
     v
Identity and Age Verification
     |
     v
Age-aware Community Assignment (Roadmap)
     |
     v
Generation-specific Timeline and Recommendations (Roadmap)
```

> **Important:** 年齢層別Safe Zoneへの自動振り分けと推薦アルゴリズムは、現在のリポジトリでは未実装です。現在は、その前提となるSNS・認証基盤を実装しています。

## Implemented Features / 実装済み機能

### Account and Authentication

- ユーザー名、年齢、メールアドレス、パスワードによる登録
- Werkzeugによるパスワードハッシュ化
- セッションベースのWebログイン
- JWTベースのAPI認証
- ログアウト
- ユーザー／管理者ロール

### Identity Verification Prototype

- 身分証明書画像のアップロード
- ブラウザカメラで撮影した顔画像の受付
- `face_recognition`による身分証画像と顔写真の照合
- 管理者による確認キュー
- 承認・却下ステータス管理
- アップロード画像の管理

### Social Features

- 280文字以内の投稿
- フォロー／フォロー解除
- 自分とフォロー中ユーザーのタイムライン
- ユーザープロフィール
- 自己紹介の編集
- プロフィール画像のアップロード
- 投稿を新しい順に表示
- ユーザー年齢の表示

### REST API

- JSONによるユーザー登録
- JWTアクセストークン発行
- 投稿作成
- 自分の投稿取得
- ユーザープロフィール取得
- 自分のプロフィール更新
- ロールベース認可用デコレータ

## Architecture / アーキテクチャ

```text
Browser / API Client
        |
        v
Flask Application
        |
        +--> Auth Blueprint
        |      ├── Registration
        |      ├── Login / Logout
        |      └── Face Verification
        |
        +--> Main Blueprint
        |      ├── Timeline
        |      ├── Posts
        |      ├── Profiles
        |      └── Follow / Unfollow
        |
        +--> API Blueprint
        |      └── JWT-protected REST endpoints
        |
        +--> Admin Blueprint
               └── Verification review
        |
        v
SQLAlchemy
        |
        v
PostgreSQL
```

## Data Model / データモデル

### User

- Username
- Email
- Age
- Password hash
- Role
- Bio
- Profile image
- Identity-document image
- Face-scan image
- Verification status
- Created timestamp

### Tweet

- Body
- Timestamp
- Author

### Follow

- Follower
- Followed user
- Timestamp

## Tech Stack / 技術スタック

| Layer | Technology |
|---|---|
| Backend | Flask |
| ORM | Flask-SQLAlchemy |
| Database | PostgreSQL 15 |
| Authentication | Flask Session, Flask-JWT-Extended |
| Password Security | Werkzeug |
| Face Matching | face_recognition, OpenCV, NumPy |
| Frontend | Jinja2, HTML, CSS, JavaScript |
| Development | Docker, Docker Compose |
| Language | Python |

## Project Structure / ディレクトリ構成

```text
era_SNS_web_app/
├── app.py
├── config.py
├── db_instance.py
├── models.py
├── routes/
│   ├── auth_routes.py
│   ├── main_routes.py
│   ├── api_routes.py
│   ├── verification_routes.py
│   └── admin_routes.py
├── templates/
│   ├── auth/
│   ├── admin/
│   ├── index.html
│   └── profile.html
├── static/
├── requirements.txt
├── Dockerfile
├── docker-compose.yml
└── README.md
```

## Quick Start with Docker / Dockerでの実行

### 1. Clone the repository

```bash
git clone https://github.com/IshouKo/era_SNS_web_app.git
cd era_SNS_web_app
```

### 2. Configure environment variables

Create a `.env` file:

```env
DATABASE_URL=postgresql://user:password@db:5432/sns_db
SECRET_KEY=replace_with_a_random_secret
JWT_SECRET_KEY=replace_with_another_random_secret
```

### 3. Install missing image-processing dependencies

The current source imports the following packages, but they may not yet be included in `requirements.txt`:

```text
face_recognition
numpy
opencv-python
```

Add them before running the identity-verification feature. Depending on the OS, `face_recognition` may also require CMake, dlib, and system build tools.

### 4. Start the application

```bash
docker compose up --build
```

The current Compose configuration maps the Flask application to:

```text
http://localhost:5001
```

## Local Development / ローカル実行

A local PostgreSQL instance is required.

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pip install face_recognition numpy opencv-python
export DATABASE_URL="postgresql://user:password@localhost:5432/sns_db"
export SECRET_KEY="replace_with_a_random_secret"
export JWT_SECRET_KEY="replace_with_another_random_secret"
flask --app app init-db
python app.py
```

Windows PowerShell:

```powershell
$env:DATABASE_URL="postgresql://user:password@localhost:5432/sns_db"
$env:SECRET_KEY="replace_with_a_random_secret"
$env:JWT_SECRET_KEY="replace_with_another_random_secret"
```

## API Examples / API使用例

### Register a user

```bash
curl -X POST http://localhost:5001/auth/register   -H "Content-Type: application/json"   -d '{
    "username": "example_user",
    "user_age": 22,
    "email": "user@example.com",
    "password": "replace_with_a_secure_password"
  }'
```

### Obtain a JWT token

```bash
curl -X POST http://localhost:5001/auth/login   -H "Content-Type: application/json"   -d '{
    "username": "example_user",
    "password": "replace_with_a_secure_password"
  }'
```

### Create a post

```bash
curl -X POST http://localhost:5001/api/tweets   -H "Content-Type: application/json"   -H "Authorization: Bearer YOUR_ACCESS_TOKEN"   -d '{"body":"Hello, Era!"}'
```

### Get a user profile

```bash
curl http://localhost:5001/api/users/example_user
```

## Security Notice / セキュリティ上の注意

This repository is a research and product-design prototype, not a production-ready identity-verification service.

- ソースコード中のデフォルト秘密鍵・管理者パスワードは開発用です。
- 本番環境では、秘密鍵や認証情報を環境変数またはSecret Managerで管理してください。
- デフォルト管理者アカウントを自動作成する処理は、本番利用前に削除または変更してください。
- 身分証明書・顔画像は極めて機微な個人情報です。暗号化、保存期間、アクセス制御、削除手順、同意取得が必要です。
- 現在の顔照合はプロトタイプであり、本人確認サービスとしての精度・公平性・なりすまし耐性は保証していません。
- CSRF対策、レート制限、監査ログ、メール確認、パスワードポリシーなどの追加対策が必要です。
- アップロードファイルのMIME検査やマルウェア検査も追加してください。

## Current Limitations / 現在の制限

- 年齢層別Safe Zoneへの自動振り分けは未実装
- 世代別タイムラインおよび推薦モデルは未実装
- 投稿への画像添付、いいね、返信、DMは未実装
- 自動テストとCIが未整備
- `requirements.txt`に画像処理依存関係が不足
- 本人確認フローは実験用プロトタイプ
- UIは機能検証を中心とした初期版

## Roadmap / 今後の拡張

- 年齢層を抽象化したSafe Zone設計
- 生年月日・本人確認結果に基づく年齢検証
- 世代別タイムラインと推薦アルゴリズム
- 年齢情報を直接公開しないプライバシー設計
- いいね、返信、通知、DM
- 投稿のモデレーションと通報機能
- 有害コンテンツ検知
- メール認証とパスワードリセット
- CSRF対策、レート制限、監査ログ
- オブジェクトストレージへの安全な画像保存
- pytest、GitHub Actions、マイグレーション
- 本番向けWSGIサーバーとクラウドデプロイ

## Author

**Ishou Ko**  
Keio University — Computer Vision Researcher / AI Engineer

