import os

os.environ['DATABASE_URL'] = 'sqlite:///:memory:'
os.environ['SECRET_KEY'] = 'test-secret'
os.environ['JWT_SECRET_KEY'] = 'test-jwt-secret'
os.environ['OPENAI_API_KEY'] = ''

from app import create_app
from db_instance import db
from models import User, age_zone_for_age


def test_age_zone_does_not_expose_exact_age():
    assert age_zone_for_age(21) == 'Z世代ゾーン'


def test_app_creates_admin_user():
    app = create_app()
    with app.app_context():
        admin = User.query.filter_by(username='admin').first()
        assert admin is not None
        assert admin.public_age_zone == 'シニアゾーン'


def test_login_page_loads():
    app = create_app()
    app.config['TESTING'] = True
    client = app.test_client()
    response = client.get('/auth/login')
    assert response.status_code == 200
    assert 'Era'.encode() in response.data
