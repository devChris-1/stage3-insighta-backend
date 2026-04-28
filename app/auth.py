import jwt
import httpx
import secrets
from datetime import datetime, timedelta, timezone
from flask import Blueprint, request, jsonify, redirect, current_app
from app import db
from app.models import User, RefreshToken

auth_bp = Blueprint("auth", __name__)


def make_access_token(user_id, secret):
    payload = {
        "sub": user_id,
        "exp": datetime.now(timezone.utc) + timedelta(minutes=3)
    }
    return jwt.encode(payload, secret, algorithm="HS256")


def make_refresh_token(user):
    raw = secrets.token_urlsafe(64)
    expires = datetime.now(timezone.utc) + timedelta(minutes=5)
    rt = RefreshToken(token=raw, user_id=user.id, expires_at=expires)
    db.session.add(rt)
    db.session.commit()
    return raw


@auth_bp.route("/auth/github")
def github_login():
    state = request.args.get("state", secrets.token_urlsafe(16))
    code_challenge = request.args.get("code_challenge")
    code_challenge_method = request.args.get("code_challenge_method", "S256")

    params = (
        f"client_id={current_app.config['GITHUB_CLIENT_ID']}"
        f"&redirect_uri={current_app.config['GITHUB_REDIRECT_URI']}"
        f"&scope=read:user user:email"
        f"&state={state}"
    )
    return redirect(f"https://github.com/login/oauth/authorize?{params}")


@auth_bp.route("/auth/github/callback")
def github_callback():
    code = request.args.get("code")
    code_verifier = request.args.get("code_verifier")

    if not code:
        return jsonify({"status": "error", "message": "Missing code"}), 400

    resp = httpx.post(
        "https://github.com/login/oauth/access_token",
        json={
            "client_id": current_app.config["GITHUB_CLIENT_ID"],
            "client_secret": current_app.config["GITHUB_CLIENT_SECRET"],
            "code": code,
            "redirect_uri": current_app.config["GITHUB_REDIRECT_URI"],
        },
        headers={"Accept": "application/json"},
    )
    github_token = resp.json().get("access_token")
    if not github_token:
        return jsonify({"status": "error", "message": "GitHub auth failed"}), 400

    user_resp = httpx.get(
        "https://api.github.com/user",
        headers={"Authorization": f"Bearer {github_token}"}
    )
    gh_user = user_resp.json()

    email = gh_user.get("email")
    if not email:
        emails_resp = httpx.get(
            "https://api.github.com/user/emails",
            headers={"Authorization": f"Bearer {github_token}"}
        )
        primary = next((e for e in emails_resp.json() if e.get("primary")), None)
        email = primary["email"] if primary else None

    user = User.query.filter_by(github_id=str(gh_user["id"])).first()
    if not user:
        user = User(github_id=str(gh_user["id"]))
        db.session.add(user)

    user.username = gh_user.get("login")
    user.email = email
    user.avatar_url = gh_user.get("avatar_url")
    user.last_login_at = datetime.now(timezone.utc)
    db.session.commit()

    secret = current_app.config["JWT_SECRET_KEY"]
    access_token = make_access_token(user.id, secret)
    refresh_token = make_refresh_token(user)

    # CLI request — code_verifier is present, return JSON
    if code_verifier:
        return jsonify({
            "status": "success",
            "access_token": access_token,
            "refresh_token": refresh_token,
            "user": {
                "id": user.id,
                "username": user.username,
                "email": user.email,
                "avatar_url": user.avatar_url,
                "role": user.role
            }
        })

    # Browser/web portal request — set cookies and redirect
    frontend_url = current_app.config["FRONTEND_URL"]
    response = make_response(redirect(f"{frontend_url}/auth/callback"))
    response.set_cookie("access_token", access_token, httponly=True, samesite="Lax")
    response.set_cookie("refresh_token", refresh_token, httponly=True, samesite="Lax")
    response.set_cookie("username", user.username or "", httponly=True, samesite="Lax")
    response.set_cookie("role", user.role, httponly=True, samesite="Lax")
    response.set_cookie("avatar_url", user.avatar_url or "", httponly=True, samesite="Lax")
    return response
