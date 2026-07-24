"""initial schema

Revision ID: 0001_initial_schema
Revises:
Create Date: 2026-07-24
"""

from alembic import op
import sqlalchemy as sa


revision = '0001_initial_schema'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'users',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('username', sa.String(length=80), nullable=False),
        sa.Column('user_age', sa.Integer(), nullable=False),
        sa.Column('birth_date', sa.Date(), nullable=True),
        sa.Column('age_verified_at', sa.DateTime(), nullable=True),
        sa.Column('age_band', sa.String(length=40), nullable=True),
        sa.Column('email', sa.String(length=120), nullable=False),
        sa.Column('password_hash', sa.String(length=128), nullable=True),
        sa.Column('role', sa.String(length=50), nullable=True),
        sa.Column('bio', sa.String(length=500), nullable=True),
        sa.Column('profile_image', sa.String(length=200), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('email_verified', sa.Boolean(), nullable=True),
        sa.Column('email_verification_token', sa.String(length=128), nullable=True),
        sa.Column('password_reset_token', sa.String(length=128), nullable=True),
        sa.Column('password_reset_sent_at', sa.DateTime(), nullable=True),
        sa.Column('id_card_image', sa.String(length=200), nullable=True),
        sa.Column('face_scan_image', sa.String(length=200), nullable=True),
        sa.Column('is_verified', sa.Boolean(), nullable=True),
        sa.Column('verification_status', sa.String(length=50), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('email'),
        sa.UniqueConstraint('username'),
    )
    op.create_index(op.f('ix_users_email_verification_token'), 'users', ['email_verification_token'], unique=False)
    op.create_index(op.f('ix_users_password_reset_token'), 'users', ['password_reset_token'], unique=False)

    op.create_table(
        'audit_logs',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=True),
        sa.Column('action', sa.String(length=80), nullable=False),
        sa.Column('ip_address', sa.String(length=64), nullable=True),
        sa.Column('user_agent', sa.String(length=255), nullable=True),
        sa.Column('detail', sa.String(length=500), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_audit_logs_action'), 'audit_logs', ['action'], unique=False)
    op.create_index(op.f('ix_audit_logs_created_at'), 'audit_logs', ['created_at'], unique=False)
    op.create_index(op.f('ix_audit_logs_user_id'), 'audit_logs', ['user_id'], unique=False)

    op.create_table(
        'direct_messages',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('sender_id', sa.Integer(), nullable=False),
        sa.Column('recipient_id', sa.Integer(), nullable=False),
        sa.Column('body', sa.String(length=1000), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('read_at', sa.DateTime(), nullable=True),
        sa.Column('moderation_status', sa.String(length=30), nullable=True),
        sa.ForeignKeyConstraint(['recipient_id'], ['users.id']),
        sa.ForeignKeyConstraint(['sender_id'], ['users.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_direct_messages_created_at'), 'direct_messages', ['created_at'], unique=False)
    op.create_index(op.f('ix_direct_messages_recipient_id'), 'direct_messages', ['recipient_id'], unique=False)
    op.create_index(op.f('ix_direct_messages_sender_id'), 'direct_messages', ['sender_id'], unique=False)

    op.create_table(
        'follows',
        sa.Column('follower_id', sa.Integer(), nullable=False),
        sa.Column('followed_id', sa.Integer(), nullable=False),
        sa.Column('timestamp', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['followed_id'], ['users.id']),
        sa.ForeignKeyConstraint(['follower_id'], ['users.id']),
        sa.PrimaryKeyConstraint('follower_id', 'followed_id'),
    )

    op.create_table(
        'tweets',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('body', sa.String(length=280), nullable=False),
        sa.Column('timestamp', sa.DateTime(), nullable=True),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('parent_id', sa.Integer(), nullable=True),
        sa.Column('image_url', sa.String(length=300), nullable=True),
        sa.Column('video_url', sa.String(length=300), nullable=True),
        sa.Column('topic', sa.String(length=80), nullable=True),
        sa.Column('age_zone', sa.String(length=40), nullable=True),
        sa.Column('moderation_status', sa.String(length=30), nullable=True),
        sa.Column('moderation_reason', sa.String(length=300), nullable=True),
        sa.Column('is_deleted', sa.Boolean(), nullable=True),
        sa.ForeignKeyConstraint(['parent_id'], ['tweets.id']),
        sa.ForeignKeyConstraint(['user_id'], ['users.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_tweets_age_zone'), 'tweets', ['age_zone'], unique=False)
    op.create_index(op.f('ix_tweets_moderation_status'), 'tweets', ['moderation_status'], unique=False)
    op.create_index(op.f('ix_tweets_timestamp'), 'tweets', ['timestamp'], unique=False)

    op.create_table(
        'likes',
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('tweet_id', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['tweet_id'], ['tweets.id']),
        sa.ForeignKeyConstraint(['user_id'], ['users.id']),
        sa.PrimaryKeyConstraint('user_id', 'tweet_id'),
    )

    op.create_table(
        'notifications',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('actor_id', sa.Integer(), nullable=True),
        sa.Column('tweet_id', sa.Integer(), nullable=True),
        sa.Column('kind', sa.String(length=40), nullable=False),
        sa.Column('message', sa.String(length=220), nullable=False),
        sa.Column('is_read', sa.Boolean(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['actor_id'], ['users.id']),
        sa.ForeignKeyConstraint(['tweet_id'], ['tweets.id']),
        sa.ForeignKeyConstraint(['user_id'], ['users.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_notifications_created_at'), 'notifications', ['created_at'], unique=False)
    op.create_index(op.f('ix_notifications_is_read'), 'notifications', ['is_read'], unique=False)
    op.create_index(op.f('ix_notifications_user_id'), 'notifications', ['user_id'], unique=False)

    op.create_table(
        'reports',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('reporter_id', sa.Integer(), nullable=False),
        sa.Column('tweet_id', sa.Integer(), nullable=True),
        sa.Column('reported_user_id', sa.Integer(), nullable=True),
        sa.Column('reason', sa.String(length=200), nullable=False),
        sa.Column('status', sa.String(length=30), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['reported_user_id'], ['users.id']),
        sa.ForeignKeyConstraint(['reporter_id'], ['users.id']),
        sa.ForeignKeyConstraint(['tweet_id'], ['tweets.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_reports_created_at'), 'reports', ['created_at'], unique=False)
    op.create_index(op.f('ix_reports_reporter_id'), 'reports', ['reporter_id'], unique=False)
    op.create_index(op.f('ix_reports_status'), 'reports', ['status'], unique=False)
    op.create_index(op.f('ix_reports_tweet_id'), 'reports', ['tweet_id'], unique=False)


def downgrade():
    op.drop_index(op.f('ix_reports_tweet_id'), table_name='reports')
    op.drop_index(op.f('ix_reports_status'), table_name='reports')
    op.drop_index(op.f('ix_reports_reporter_id'), table_name='reports')
    op.drop_index(op.f('ix_reports_created_at'), table_name='reports')
    op.drop_table('reports')
    op.drop_index(op.f('ix_notifications_user_id'), table_name='notifications')
    op.drop_index(op.f('ix_notifications_is_read'), table_name='notifications')
    op.drop_index(op.f('ix_notifications_created_at'), table_name='notifications')
    op.drop_table('notifications')
    op.drop_table('likes')
    op.drop_index(op.f('ix_tweets_timestamp'), table_name='tweets')
    op.drop_index(op.f('ix_tweets_moderation_status'), table_name='tweets')
    op.drop_index(op.f('ix_tweets_age_zone'), table_name='tweets')
    op.drop_table('tweets')
    op.drop_table('follows')
    op.drop_index(op.f('ix_direct_messages_sender_id'), table_name='direct_messages')
    op.drop_index(op.f('ix_direct_messages_recipient_id'), table_name='direct_messages')
    op.drop_index(op.f('ix_direct_messages_created_at'), table_name='direct_messages')
    op.drop_table('direct_messages')
    op.drop_index(op.f('ix_audit_logs_user_id'), table_name='audit_logs')
    op.drop_index(op.f('ix_audit_logs_created_at'), table_name='audit_logs')
    op.drop_index(op.f('ix_audit_logs_action'), table_name='audit_logs')
    op.drop_table('audit_logs')
    op.drop_index(op.f('ix_users_password_reset_token'), table_name='users')
    op.drop_index(op.f('ix_users_email_verification_token'), table_name='users')
    op.drop_table('users')
