from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from config import Config

db = SQLAlchemy()
limiter = Limiter(key_func=get_remote_address)


def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    db.init_app(app)
    limiter.init_app(app)
    CORS(app, resources={r"/*": {"origins": "*"}})

    from app.routes import bp
    from app.auth import auth_bp
    from app.logger import init_logger

    app.register_blueprint(bp)
    app.register_blueprint(auth_bp)
    init_logger(app)

    # Apply rate limits
    limiter.limit("10 per minute")(auth_bp)
    limiter.limit("60 per minute")(bp)

    with app.app_context():
        db.create_all()

    return app
