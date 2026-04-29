from datetime import datetime
from app import db
from uuid6 import uuid7


class Profile(db.Model):
    id = db.Column(db.String, primary_key=True, default=lambda: str(uuid7()))
    name = db.Column(db.String, unique=True, nullable=False)
    gender = db.Column(db.String)
    gender_probability = db.Column(db.Float)
    age = db.Column(db.Integer)
    age_group = db.Column(db.String)
    country_id = db.Column(db.String(2))
    country_name = db.Column(db.String)
    country_probability = db.Column(db.Float)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class User(db.Model):
    __tablename__ = "users"
    id = db.Column(db.String, primary_key=True, default=lambda: str(uuid7()))
    github_id = db.Column(db.String, unique=True, nullable=False)
    username = db.Column(db.String)
    email = db.Column(db.String)
    avatar_url = db.Column(db.String)
    role = db.Column(db.String, default="analyst")
    is_active = db.Column(db.Boolean, default=True)
    last_login_at = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    tokens = db.relationship("RefreshToken", backref="user", lazy=True, cascade="all, delete-orphan")


class RefreshToken(db.Model):
    __tablename__ = "refresh_tokens"
    id = db.Column(db.String, primary_key=True, default=lambda: str(uuid7()))
    token = db.Column(db.String, unique=True, nullable=False)
    user_id = db.Column(db.String, db.ForeignKey("users.id"), nullable=False)
    expires_at = db.Column(db.DateTime, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)