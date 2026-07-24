# Era — Safe Zone SNS Prototype

Era is a Flask-based social networking prototype for safer, generation-aware online communities.

Eraは、本人確認と生年月日にもとづいてユーザーを抽象化された **Safe Zone** に案内し、実年齢を直接公開せずに世代別のタイムラインや交流を提供するSNSプロトタイプです。

## Features / 実装済み機能

- 生年月日ベースの年齢検証と Safe Zone 分類
- 実年齢を公開しないプロフィール/API設計
- 世代別タイムライン、発見ページ、おすすめユーザー
- 投稿、画像添付、フォロー、プロフィール編集
- いいね、返信、通知、DM
- 投稿の通報、管理者モデレーション
- ルールベース有害コンテンツ検知
- OpenAI Moderation API 連携準備
- メール認証、パスワードリセット
- CSRF対策、簡易レート制限、監査ログ
- ローカル画像保存ユーティリティ
- Flask-Migrate / Alembic マイグレーション
- pytest、GitHub Actions CI
- Gunicorn によるWSGI起動
- React + TypeScript + Vite frontend
- スクリーンショット風の Era ダークUI

## Safe Zone Design

Era does not expose exact age in public timelines or profile API responses.

```text
Birth Date
    |
    v
Age Calculation
    |
    v
Identity / Admin Verification
    |
    v
Safe Zone
    |
    v
Generation-aware Timeline
```

Current Safe Zone examples:

| Age | Zone |
|---:|---|
| < 13 | キッズゾーン |
| 13-17 | ティーンゾーン |
| 18-29 | Z世代ゾーン |
| 30-44 | ミレニアルゾーン |
| 45-59 | アダルトゾーン |
| 60+ | シニアゾーン |

## Tech Stack

| Layer | Technology |
|---|---|
| Backend | Flask |
| ORM | Flask-SQLAlchemy |
| Migration | Flask-Migrate / Alembic |
| Database | PostgreSQL 15, SQLite for local smoke tests |
| Auth | Flask Session, Flask-JWT-Extended |
| Password Security | Werkzeug |
| Moderation | Rule-based detection, optional OpenAI Moderation |
| Frontend | Jinja2, HTML, CSS, JavaScript |
| SPA Frontend | React, TypeScript, Vite, lucide-react |
| Testing | pytest, GitHub Actions |
| Production Server | Gunicorn |
| Development | Docker, Docker Compose |

## Project Structure

```text
era_SNS_web_app/
├── app.py
├── config.py
├── db_instance.py
├── models.py
├── services.py
├── routes/
│   ├── auth_routes.py
│   ├── main_routes.py
│   ├── api_routes.py
│   ├── verification_routes.py
│   └── admin_routes.py
├── templates/
│   ├── auth/
│   ├── admin/
│   ├── verification/
│   ├── index.html
│   ├── profile.html
│   ├── discover.html
│   ├── messages.html
│   └── notifications.html
├── static/
│   ├── css/era.css
│   └── img/Eraicon.png
├── frontend/
│   ├── package.json
│   ├── vite.config.ts
│   └── src/
│       ├── App.tsx
│       ├── api.ts
│       ├── types.ts
│       └── styles.css
├── migrations/
├── tests/
├── .github/workflows/ci.yml
├── requirements.txt
├── Dockerfile
├── docker-compose.yml
└── README.md
```

## File Responsibilities / ファイルの役割

### Backend Core

| File | Role |
|---|---|
| `app.py` | Flaskアプリの生成地点です。設定読み込み、DB/JWT/Migrate初期化、Blueprint登録、CSRFトークン登録、簡易レート制限、初期管理者作成を担当します。 |
| `config.py` | 環境変数からDB接続先、秘密鍵、OpenAI Moderation、アップロード保存先、メール送信元、レート制限などの設定をまとめます。 |
| `db_instance.py` | SQLAlchemyの `db` インスタンスだけを定義します。循環importを避けるため、モデルやルートから共通で参照します。 |
| `models.py` | DBテーブル定義です。`User`, `Tweet`, `Follow`, `Like`, `Notification`, `DirectMessage`, `Report`, `AuditLog` と、Safe Zone分類ロジックを持ちます。 |
| `services.py` | ルート間で共有する補助処理です。CSRF、レート制限、監査ログ、通知作成、画像保存、Base64画像保存、有害コンテンツ検知、メールログ出力、トークン生成を担当します。 |

### Flask Routes

| File | Role |
|---|---|
| `routes/auth_routes.py` | 登録、ログイン、ログアウト、メール認証、パスワードリセット、多段階本人確認登録、JWT発行を担当します。 |
| `routes/main_routes.py` | Flask/Jinja版のSNS画面用ルートです。ホーム、投稿、プロフィール、フォロー、いいね、返信、通報、通知、DM、発見ページを担当します。 |
| `routes/api_routes.py` | React + TypeScript frontend が使うJSON APIとJWT保護APIを担当します。`/api/me`, `/api/timeline`, 投稿作成、いいね、返信、通知、DMなどがあります。 |
| `routes/verification_routes.py` | ログイン済みユーザーが後から本人確認を行うためのルートです。身分証アップロード、顔写真撮影、確認ステータス取得を担当します。 |
| `routes/admin_routes.py` | 管理者用ルートです。本人確認の承認/拒否、モデレーションキュー、通報確認、監査ログ閲覧を担当します。 |

### Flask Templates

| Path | Role |
|---|---|
| `templates/base.html` | Jinja版ページの共通レイアウトです。上部ナビゲーション、ログイン状態表示、共通CSS読み込み、フラッシュメッセージを提供します。 |
| `templates/index.html` | Jinja版ホームタイムラインです。投稿フォーム、タイムライン、左ナビ、右サイドバーを表示します。 |
| `templates/profile.html` | Jinja版プロフィール画面です。Safe Zone、自己紹介、フォロー状態、投稿一覧、プロフィール編集フォームを表示します。 |
| `templates/discover.html` | Safe Zone別の発見ページです。選択された世代ゾーンの投稿を表示します。 |
| `templates/messages.html` | Jinja版DM画面です。メッセージ送信フォームと送受信履歴を表示します。 |
| `templates/notifications.html` | Jinja版通知画面です。いいね、返信、フォロー、DM通知を表示します。 |
| `templates/auth/` | 登録、ログイン、メール/パスワード関連、登録時の身分証/顔写真アップロード画面を置きます。 |
| `templates/admin/` | 管理者向けの本人確認、モデレーション、監査ログ画面を置きます。 |
| `templates/verification/` | ログイン済みユーザー向けの後続本人確認画面を置きます。 |
| `templates/vertification/` | 旧typo名の本人確認テンプレートです。互換用に残っていますが、新規利用は `templates/verification/` を使います。 |

### Static Assets

| Path | Role |
|---|---|
| `static/css/era.css` | Flask/Jinja版UIのスタイルです。スクリーンショット風の暗色レイアウト、サイドバー、投稿カード、認証画面などを定義します。 |
| `static/img/Eraicon.png` | Eraロゴ画像です。FlaskテンプレートとReact frontendの両方から参照します。 |
| `static/uploads/` | 開発用のアップロード保存先です。`.gitignore` 対象で、本番ではオブジェクトストレージへの置き換えを想定しています。 |

### React + TypeScript Frontend

| File | Role |
|---|---|
| `frontend/package.json` | React/Vite/TypeScript/lucide-reactなどの依存関係と、`dev`, `build`, `preview`, `lint` scriptsを定義します。 |
| `frontend/index.html` | ViteのHTMLエントリです。`src/main.tsx` を読み込み、Reactアプリを `#root` にマウントします。 |
| `frontend/vite.config.ts` | Vite設定です。開発時に `/api`, `/auth`, `/static` をFlask backendへproxyします。`VITE_API_PROXY_TARGET` で向き先を変更できます。 |
| `frontend/tsconfig.json` | frontend TypeScriptの型チェック設定です。strict modeを有効にしています。 |
| `frontend/tsconfig.node.json` | Vite設定ファイルなどNode側TypeScript用の設定です。 |
| `frontend/eslint.config.js` | ESLint flat configです。TypeScriptとReact Hooksの基本ルールを適用します。 |
| `frontend/src/main.tsx` | Reactアプリのエントリです。`App` をDOMにマウントし、共通CSSを読み込みます。 |
| `frontend/src/App.tsx` | React frontendの中心です。ログイン、ホーム、発見、通知、DM、投稿、いいね、返信、左右サイドバーをコンポーネントとして実装します。 |
| `frontend/src/api.ts` | Flask JSON APIを呼び出すTypeScript clientです。JWTを `localStorage` に保存し、認証付きリクエストを送ります。 |
| `frontend/src/types.ts` | APIレスポンスの型定義です。`EraUser`, `Tweet`, `TimelineResponse`, `NotificationItem`, `DirectMessage` などを定義します。 |
| `frontend/src/styles.css` | React frontend用のUIスタイルです。Jinja版とは独立して、同じEraデザインをSPA用に定義しています。 |

### Database, Tests, and Operations

| Path | Role |
|---|---|
| `migrations/` | Flask-Migrate/Alembicのマイグレーション管理ディレクトリです。DBスキーマ変更を追跡します。 |
| `migrations/versions/0001_initial_schema.py` | 初期スキーマのマイグレーションです。ユーザー、投稿、いいね、通知、DM、通報、監査ログなどのテーブルを作成します。 |
| `tests/test_app.py` | pytestの最小スモークテストです。Safe Zone分類、アプリ生成、ログイン画面ロードを確認します。 |
| `.github/workflows/ci.yml` | GitHub Actions CI設定です。push/PR時に依存をインストールしてpytestを実行します。 |
| `requirements.txt` | Python依存関係です。Flask、SQLAlchemy、JWT、Migrate、Gunicorn、OpenAI、pytestなどを定義します。 |
| `Dockerfile` | Flask backend用のPythonコンテナ定義です。Compose側でコマンドを上書きして使います。 |
| `docker-compose.yml` | PostgreSQL、Flask backend、React frontendをまとめて起動する開発用Compose設定です。 |
| `.env` | ローカル開発用の環境変数例です。`OPENAI_API_KEY=` は空のままにしてあり、キー取得後に追加します。 |
| `.gitignore` | Pythonキャッシュ、pytestキャッシュ、アップロード画像、frontend build成果物、node_modulesなどを除外します。 |
| `README.md` | このドキュメントです。セットアップ、構成、API、セキュリティ注意点、ファイル役割を説明します。 |

## Environment Variables

`.env` example:

```env
DATABASE_URL=postgresql://user:password@db:5432/sns_db
SECRET_KEY=replace_with_a_random_secret
JWT_SECRET_KEY=replace_with_another_random_secret
OPENAI_API_KEY=
OPENAI_MODERATION_MODEL=omni-moderation-latest
STORAGE_BACKEND=local
UPLOAD_FOLDER=static/uploads
APP_BASE_URL=http://localhost:5001
```

`OPENAI_API_KEY` is intentionally blank. Add your key later to enable OpenAI Moderation API calls. Without a key, Era uses the local rule-based moderation fallback.

## Quick Start with Docker

```bash
docker compose up --build
```

Open the React + TypeScript frontend:

```text
http://localhost:5173
```

The Flask backend is also exposed at:

```text
http://localhost:5001
```

Default admin account:

```text
username: admin
password: admin_password
```

Change or remove the default admin creation before production use.

## Local Development

### Backend

For PostgreSQL:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
export DATABASE_URL="postgresql://user:password@localhost:5432/sns_db"
export SECRET_KEY="replace_with_a_random_secret"
export JWT_SECRET_KEY="replace_with_another_random_secret"
export OPENAI_API_KEY=""
flask --app app init-db
flask --app app run --port 5002
```

For quick local SQLite testing:

```bash
export DATABASE_URL="sqlite:////tmp/era_sns_dev.db"
export SECRET_KEY="dev"
export JWT_SECRET_KEY="dev"
export OPENAI_API_KEY=""
flask --app app run --port 5002
```

Open:

```text
http://127.0.0.1:5002
```

### Frontend

The frontend lives in `frontend/` and uses React + TypeScript + Vite.

```bash
cd frontend
npm install
npm run dev
```

Open:

```text
http://localhost:5173
```

By default, Vite proxies API requests to:

```text
http://127.0.0.1:5002
```

To point the frontend at another backend:

```bash
VITE_API_PROXY_TARGET=http://127.0.0.1:5001 npm run dev
```

Build the frontend:

```bash
cd frontend
npm run build
```

Note: this machine must have Node.js and npm installed to run the Vite frontend locally. Docker Compose can run the frontend with the `node:20-alpine` image.

## Database Migration

Alembic is initialized under `migrations/`.

```bash
flask --app app db upgrade
```

To create a new migration after model changes:

```bash
flask --app app db migrate -m "describe change"
flask --app app db upgrade
```

## Tests and CI

Run tests locally:

```bash
python -m pytest -q
```

GitHub Actions runs the same pytest suite on push and pull request.

## API Examples

### Register

```bash
curl -X POST http://localhost:5001/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "username": "example_user",
    "birth_date": "2002-04-10",
    "user_age": 24,
    "email": "user@example.com",
    "password": "replace_with_a_secure_password"
  }'
```

### Login and Get JWT

```bash
curl -X POST http://localhost:5001/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "username": "example_user",
    "password": "replace_with_a_secure_password"
  }'
```

### Create Post

```bash
curl -X POST http://localhost:5001/api/tweets \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -d '{"body":"Hello, Era!"}'
```

### Public Profile API

```bash
curl http://localhost:5001/api/users/example_user
```

The public profile API returns `age_zone`, not exact age or email.

### React Frontend API

The TypeScript frontend currently uses these JWT-backed endpoints:

- `GET /api/me`
- `GET /api/timeline`
- `POST /api/tweets`
- `POST /api/tweets/<id>/like`
- `POST /api/tweets/<id>/replies`
- `GET /api/notifications`
- `GET /api/messages`
- `POST /api/messages`

## Security Notes

This repository is still a prototype, not a production-ready identity-verification service.

- Replace `SECRET_KEY`, `JWT_SECRET_KEY`, and the default admin password before deployment.
- Store secrets in environment variables or a secret manager.
- ID-card and face images are sensitive personal data. Use encryption, strict access control, retention limits, and consent flows in production.
- The local image backend is suitable for development only. Use S3-compatible object storage or another managed storage service for production.
- `face_recognition` is optional in this repo. If it is not installed, development fallback accepts face capture so the flow can be tested.
- Add MIME sniffing, malware scanning, and more robust abuse prevention before public release.
- Email sending currently logs messages in development; connect a real mail provider for production.

## Remaining Production Work

- Connect real object storage and signed upload/download URLs.
- Replace console email with SMTP or transactional email.
- Harden rate limiting with Redis or another shared backend.
- Use a managed identity verification provider if legal assurance is required.
- Add richer recommendation logic and moderation review tooling.
- Deploy to a cloud platform with managed PostgreSQL, HTTPS, and observability.
