from functools import wraps
from datetime import datetime, timezone
import jwt
from flask import request, jsonify, current_app
from app.models import User


def get_token_from_header():
    auth = request.headers.get("Authorization", "")
    if auth.startswith("Bearer "):
        return auth.split(" ", 1)[1]
    return None


def require_auth(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if request.headers.get("X-API-Version") != "1":
            return jsonify({"status": "error", "message": "API version header required"}), 400

        token = get_token_from_header()
        if not token:
            return jsonify({"status": "error", "message": "Authentication required"}), 401

        try:
            payload = jwt.decode(token, current_app.config["JWT_SECRET_KEY"], algorithms=["HS256"])
        except jwt.ExpiredSignatureError:
            return jsonify({"status": "error", "message": "Token expired"}), 401
        except jwt.InvalidTokenError:
            return jsonify({"status": "error", "message": "Invalid token"}), 401

        user = User.query.get(payload.get("sub"))
        if not user:
            return jsonify({"status": "error", "message": "User not found"}), 401
        if not user.is_active:
            return jsonify({"status": "error", "message": "Account disabled"}), 403

        request.current_user = user
        return f(*args, **kwargs)
    return decorated


def admin_required(f):
    @wraps(f)
    @require_auth
    def decorated(*args, **kwargs):
        if request.current_user.role != "admin":
            return jsonify({"status": "error", "message": "Admin access required"}), 403
        return f(*args, **kwargs)
    return decorated
