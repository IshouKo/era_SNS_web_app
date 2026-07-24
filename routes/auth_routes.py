from flask import Blueprint, render_template, redirect, url_for, flash, request, session, jsonify, current_app
from db_instance import db
import models
from werkzeug.security import generate_password_hash
from flask_jwt_extended import create_access_token
from datetime import datetime
import os
try:
    import face_recognition
except ImportError:
    face_recognition = None
from services import (
    audit,
    generate_token,
    parse_birth_date,
    reset_link,
    reset_token_is_valid,
    save_base64_image,
    save_upload,
    send_email,
    validate_csrf,
    verification_link,
    verified_age_band,
)

bp = Blueprint('auth', __name__, url_prefix='/auth')

@bp.route('/register', methods=['GET', 'POST'])
def register():
    """ステップ1: ユーザー基本情報登録"""
    # API経由でのJSONデータ登録 (既存のロジックを保持)
    if request.is_json:
        # TODO: APIからの登録も多段階にする場合はこのロジックを変更する必要あり
        # 現状は単一リクエストで完結する従来のロジックを保持
        username = request.json.get('username', None)
        user_age = request.json.get('user_age', None)
        birth_date = parse_birth_date(request.json.get('birth_date')) if request.json.get('birth_date') else None
        email = request.json.get('email', None)
        password = request.json.get('password', None)
        
        # バリデーション
        if not user_age or not username or not email or not password:
            return jsonify({'message': 'Username, email, password, and age are required'}), 400
        try:
            user_age = int(user_age)
            if user_age <= 0:
                return jsonify({'message': 'Age must be a positive integer'}), 400
        except ValueError:
            return jsonify({'message': 'Age must be a number'}), 400
        
        # ユーザー名またはメールアドレスが既に存在するかチェック
        existing_user = models.User.query.filter((models.User.username == username) | (models.User.email == email)).first()
        if existing_user:
            return jsonify({'message': 'Username or email already exists'}), 400

        # 新規ユーザー作成
        token = generate_token()
        user = models.User(
            username=username,
            user_age=user_age,
            birth_date=birth_date,
            age_band=verified_age_band(birth_date, user_age),
            email=email,
            role='user',
            email_verification_token=token,
        )
        user.set_password(password)
        try:
            db.session.add(user)
            audit('register_api', detail=username)
            db.session.commit()
            send_email(email, 'Era メール認証', f'以下のURLでメール認証してください。\n{verification_link(token)}')
            return jsonify({'message': 'User registered successfully'}), 201
        except Exception as e:
            db.session.rollback()
            return jsonify({'message': f'Registration failed: {str(e)}'}), 500

    # HTMLフォームからの登録（多段階登録の開始）
    if request.method == 'POST':
        if not validate_csrf():
            flash('セッションの有効期限が切れました。もう一度お試しください。', 'danger')
            return redirect(url_for('auth.register'))
        # フォームデータをセッションに保存して次のステップへ
        username = request.form['username']
        birth_date_value = request.form.get('birth_date')
        user_age = request.form.get('user_age')
        email = request.form['email']
        password = request.form['password']
        bio = request.form.get('bio', None)
        profile_image_file = request.files.get('profile_image_file')

        # バリデーション
        if not username or not email or not password or not birth_date_value:
            flash('全ての必須項目を入力してください。', 'danger')
            return redirect(url_for('auth.register'))
        try:
            birth_date = parse_birth_date(birth_date_value)
            user_age = models.calculate_age(birth_date)
            if user_age <= 0:
                flash('生年月日を正しく入力してください。', 'danger')
                return redirect(url_for('auth.register'))
        except ValueError:
            flash('生年月日を正しく入力してください。', 'danger')
            return redirect(url_for('auth.register'))

        existing_user = models.User.query.filter((models.User.username == username) | (models.User.email == email)).first()
        if existing_user:
            flash('ユーザー名またはメールアドレスは既に登録されています。', 'danger')
            return redirect(url_for('auth.register'))
        
        # プロフィール画像のアップロードと保存
        profile_image_path = None
        if profile_image_file and profile_image_file.filename != '':
            try:
                profile_image_path = save_upload(profile_image_file, 'profiles')
            except Exception as e:
                flash(f'プロフィール画像の保存に失敗しました: {str(e)}', 'danger')
                return redirect(url_for('auth.register'))

        # フォームデータをセッションに保存して次のステップへ
        session['registration_data'] = {
            'username': username,
            'user_age': user_age,
            'birth_date': birth_date.isoformat(),
            'age_band': verified_age_band(birth_date, user_age),
            'email': email,
            'password_hash': generate_password_hash(password),
            'bio': bio,
            'profile_image': profile_image_path
        }
        
        flash('基本情報の登録が完了しました。次に身分証明書をアップロードしてください。', 'success')
        return redirect(url_for('auth.register_id_card'))

    # GETリクエストの場合、またはPOSTでエラーがあった場合
    return render_template('auth/register.html')


@bp.route('/register/id_card', methods=['GET', 'POST'])
def register_id_card():
    """ステップ2: 身分証明書アップロード"""
    # セッションに登録データがなければ最初の登録ページに戻す
    if 'registration_data' not in session:
        flash('アカウント登録を最初からやり直してください。', 'warning')
        return redirect(url_for('auth.register'))

    if request.method == 'POST':
        if not validate_csrf():
            flash('セッションの有効期限が切れました。もう一度お試しください。', 'danger')
            return redirect(request.url)
        if 'id_card_file' not in request.files or request.files['id_card_file'].filename == '':
            flash('身分証明書のファイルを選択してください。', 'danger')
            return redirect(request.url)
        
        file = request.files['id_card_file']
        try:
            # セッションに画像パスを保存
            session['registration_data']['id_card_image'] = save_upload(file, 'verification')
            flash('身分証明書がアップロードされました。次に顔写真を撮影してください。', 'success')

            return redirect(url_for('auth.register_face_scan'))
        except Exception as e:
            flash(f'アップロードに失敗しました: {str(e)}', 'danger')
            return redirect(request.url)

    return render_template('auth/register_id_card.html')


@bp.route('/register/face_scan', methods=['GET'])
def register_face_scan():
    """ステップ3: 顔写真撮影と認証"""
    if 'registration_data' not in session or 'id_card_image' not in session['registration_data']:
        flash('アカウント登録を最初からやり直してください。', 'warning')
        return redirect(url_for('auth.register'))
    
    return render_template('auth/register_face_scan.html')


@bp.route('/register/verify_face', methods=['POST'])
def register_verify_face():
    """顔写真のアップロードと顔照合のAPIエンドポイント"""
    if 'registration_data' not in session or 'id_card_image' not in session['registration_data']:
        return jsonify({'message': 'セッション情報が無効です。アカウント登録を最初からやり直してください。', 'redirect_url': url_for('auth.register')}), 400

    data = request.get_json()
    face_scan_image_data = data.get('image')
    if not face_scan_image_data:
        return jsonify({'message': '顔画像データがありません。'}), 400

    try:
        # 身分証明書の画像パスを取得
        id_card_image_path = session['registration_data']['id_card_image']
        id_card_image_full_path = os.path.join(current_app.root_path, id_card_image_path.lstrip('/'))
        
        face_scan_file_path, face_scan_image_path = save_base64_image(face_scan_image_data, 'face_scan', 'verification')

        # --- 顔照合ロジック ---
        is_match = False
        try:
            if face_recognition is None:
                is_match = True
            else:
                id_card_img_np = face_recognition.load_image_file(id_card_image_full_path)
                id_card_face_encodings = face_recognition.face_encodings(id_card_img_np)
                face_scan_img_np = face_recognition.load_image_file(face_scan_file_path)
                face_scan_face_encodings = face_recognition.face_encodings(face_scan_img_np)

                if id_card_face_encodings and face_scan_face_encodings:
                    matches = face_recognition.compare_faces([id_card_face_encodings[0]], face_scan_face_encodings[0])
                    is_match = matches[0]
                else:
                    return jsonify({'message': '顔を検出できませんでした。もう一度お試しください。', 'status': 'failed', 'redirect_url': url_for('auth.register_face_scan')}), 400
        except Exception as e:
            # 認証失敗時の画像ファイル削除
            if os.path.exists(face_scan_file_path):
                os.remove(face_scan_file_path)
            return jsonify({'message': f'顔認証処理中にエラーが発生しました: {str(e)}', 'status': 'error', 'redirect_url': url_for('auth.register_face_scan')}), 500

        if is_match:
            # 照合成功、データベースにユーザーを登録（Adminの年齢確認待ち）
            registration_data = session.pop('registration_data')
            token = generate_token()
            new_user = models.User(
                username=registration_data['username'],
                user_age=registration_data['user_age'],
                birth_date=parse_birth_date(registration_data.get('birth_date')),
                age_band=registration_data.get('age_band'),
                email=registration_data['email'],
                password_hash=registration_data['password_hash'],
                bio=registration_data['bio'],
                profile_image=registration_data['profile_image'],
                id_card_image=registration_data['id_card_image'],
                face_scan_image=face_scan_image_path,
                is_verified=False, # ここはFalseのまま
                verification_status='uploaded_both', # Adminの確認待ち
                email_verification_token=token,
                role='user'
            )
            db.session.add(new_user)
            audit('register_uploaded_verification', detail=new_user.username)
            db.session.commit()
            send_email(new_user.email, 'Era メール認証', f'以下のURLでメール認証してください。\n{verification_link(token)}')
            
            return jsonify({'message': '顔認証が成功しました。次に、Adminが生年月日と年齢を照合します。', 'status': 'success', 'redirect_url': url_for('auth.login')}), 200
        else:
            # 認証失敗、最初からやり直させる
            if os.path.exists(face_scan_file_path):
                os.remove(face_scan_file_path)
            session.pop('registration_data', None)
            return jsonify({'message': '顔認証に失敗しました。もう一度登録し直してください。', 'status': 'failed', 'redirect_url': url_for('auth.register')}), 400
    
    except Exception as e:
        db.session.rollback()
        session.pop('registration_data', None)
        return jsonify({'message': f'登録中にエラーが発生しました: {str(e)}', 'status': 'error', 'redirect_url': url_for('auth.register')}), 500

    return jsonify({'message': '無効なリクエストです。'}), 400


# 既存の login と logout ルートは変更なし
@bp.route('/login', methods=['GET', 'POST'])
def login():
    # ... 既存のロジック ...
    if request.is_json:
        username = request.json.get('username', None)
        password = request.json.get('password', None)
        if not username or not password:
            return jsonify({"message": "Username and password are required"}), 400

        user = models.User.query.filter_by(username=username).first()
        if not user or not user.check_password(password):
            return jsonify({"message": "Invalid username or password"}), 401
        
        # 認証済みユーザーのみログイン可能とする場合はここで is_verified をチェック
        # if not user.is_verified:
        #     return jsonify({"message": "アカウントはまだ本人確認が完了していません。"}), 401

        access_token = create_access_token(identity=user.username)
        return jsonify(access_token=access_token), 200

    if request.method == 'POST':
        if not validate_csrf():
            flash('セッションの有効期限が切れました。もう一度お試しください。', 'danger')
            return redirect(url_for('auth.login'))
        username = request.form['username']
        password = request.form['password']
        user = models.User.query.filter_by(username=username).first()
        if user and user.check_password(password):
            if not user.email_verified:
                flash('メール認証がまだ完了していません。開発環境ではログに認証URLが出力されます。', 'warning')
                return render_template('auth/login.html')
            if not user.is_verified:
                flash('アカウントはまだ本人確認が完了していません。', 'warning')
                return render_template('auth/login.html')

            session['user_id'] = user.id
            session['username'] = user.username
            audit('login', user.id)
            db.session.commit()
            flash('ログインしました！', 'success')
            return redirect(url_for('main.index'))
        else:
            flash('ユーザー名またはパスワードが間違っています。', 'danger')
    return render_template('auth/login.html')

@bp.route('/logout')
def logout():
    user_id = session.get('user_id')
    if user_id:
        audit('logout', user_id)
        db.session.commit()
    session.pop('user_id', None)
    session.pop('username', None)
    flash('ログアウトしました。', 'info')
    return redirect(url_for('auth.login'))


@bp.route('/verify-email/<token>')
def verify_email(token):
    user = models.User.query.filter_by(email_verification_token=token).first_or_404()
    user.email_verified = True
    user.email_verification_token = None
    audit('email_verified', user.id)
    db.session.commit()
    flash('メール認証が完了しました。', 'success')
    return redirect(url_for('auth.login'))


@bp.route('/forgot-password', methods=['GET', 'POST'])
def forgot_password():
    if request.method == 'POST':
        if not validate_csrf():
            flash('セッションの有効期限が切れました。もう一度お試しください。', 'danger')
            return redirect(url_for('auth.forgot_password'))
        email = request.form.get('email')
        user = models.User.query.filter_by(email=email).first()
        if user:
            token = generate_token()
            user.password_reset_token = token
            user.password_reset_sent_at = datetime.utcnow()
            audit('password_reset_requested', user.id)
            db.session.commit()
            send_email(user.email, 'Era パスワードリセット', f'以下のURLでパスワードを再設定してください。\n{reset_link(token)}')
        flash('登録済みメールアドレスの場合、リセット用URLを送信しました。', 'info')
        return redirect(url_for('auth.login'))
    return render_template('auth/forgot_password.html')


@bp.route('/reset-password/<token>', methods=['GET', 'POST'])
def reset_password(token):
    user = models.User.query.filter_by(password_reset_token=token).first_or_404()
    if not reset_token_is_valid(user):
        flash('リセットURLの有効期限が切れています。', 'danger')
        return redirect(url_for('auth.forgot_password'))
    if request.method == 'POST':
        if not validate_csrf():
            flash('セッションの有効期限が切れました。もう一度お試しください。', 'danger')
            return redirect(url_for('auth.reset_password', token=token))
        password = request.form.get('password')
        if not password or len(password) < 8:
            flash('パスワードは8文字以上で入力してください。', 'danger')
            return redirect(url_for('auth.reset_password', token=token))
        user.set_password(password)
        user.password_reset_token = None
        user.password_reset_sent_at = None
        audit('password_reset_completed', user.id)
        db.session.commit()
        flash('パスワードを更新しました。', 'success')
        return redirect(url_for('auth.login'))
    return render_template('auth/reset_password.html')
