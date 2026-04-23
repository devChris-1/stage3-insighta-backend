import uuid
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
