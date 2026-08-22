from __future__ import annotations

import hmac
import os
import secrets
from dataclasses import dataclass
from datetime import timedelta
from typing import Any

from flask import Flask, Response, redirect, request, session
from werkzeug.middleware.proxy_fix import ProxyFix
from werkzeug.security import check_password_hash

from cakrawala.web.personal_ai_lab import install_personal_ai_lab_route
from cakrawala.web.personal_forex import install_personal_forex_route
from cakrawala.web.personal_forex_review import install_personal_forex_review_route
from cakrawala.web.personal_forex_risk import install_personal_forex_risk_route
from cakrawala.web.personal_forex_sync import install_personal_forex_sync_route
from cakrawala.web.personal_forex_system import install_personal_forex_system_route
from cakrawala.web.personal_market import install_personal_market_route


@dataclass(frozen=True)
class WebAuthConfig:
    username: str
    password_hash: str
    session_secret: str
    owner_id: str


def _looks_like_password_hash(value: str) -> bool:
    return value.startswith(("scrypt:", "pbkdf2:")) and "$" in value


def load_web_auth_config() -> WebAuthConfig | None:
    username = os.environ.get("PERSONAL_AUTH_USERNAME", "").strip()
    password_hash = os.environ.get("PERSONAL_AUTH_PASSWORD_HASH", "").strip()
    session_secret = os.environ.get("WEB_SESSION_SECRET", "").strip()
    owner_id = os.environ.get("PERSONAL_OWNER_ID", "").strip() or username

    if not username or not session_secret or not _looks_like_password_hash(password_hash):
        return None
    return WebAuthConfig(
        username=username,
        password_hash=password_hash,
        session_secret=session_secret,
        owner_id=owner_id,
    )


def _login_page(message: str = "") -> Response:
    note = f"<p class='error'>{message}</p>" if message else ""
    csrf_token = str(session.get("login_csrf", ""))
    body = "".join(
        [
            "<!doctype html><html lang='en'><head><meta charset='utf-8'>",
            "<meta name='viewport' content='width=device-width,initial-scale=1'>",
            "<meta name='robots' content='noindex,nofollow'>",
            "<title>Cakrawala Personal Login</title><style>",
            "body{margin:0;background:#0b1020;color:#edf2f7;font-family:Inter,system-ui,",
            "sans-serif;display:grid;min-height:100vh;place-items:center}",
            ".card{width:min(420px,calc(100% - 40px));background:#121a2b;",
            "border:1px solid #253047;border-radius:16px;padding:26px;box-sizing:border-box}",
            "h1{margin:4px 0 8px;font-size:25px}.muted{color:#9fb0c7;line-height:1.5}",
            "label{display:block;margin:16px 0 6px;color:#b9c7d9;font-size:13px}",
            "input[type=text],input[type=password]{width:100%;padding:11px 12px;",
            "box-sizing:border-box;border:1px solid #34425c;border-radius:9px;",
            "background:#0d1424;color:#fff}.remember{display:flex;gap:8px;align-items:center;",
            "margin:16px 0}.remember input{margin:0}button{width:100%;padding:11px 14px;",
            "border:0;border-radius:9px;font-weight:700;cursor:pointer}.error{color:#ffb4b4}",
            "</style></head><body><main class='card'>",
            "<div class='muted'>PRIVATE RESEARCH WORKSPACE</div>",
            "<h1>Cakrawala Login</h1>",
            "<p class='muted'>Streamlit tetap publik. Vercel ini khusus penggunaan pribadi.</p>",
            note,
            "<form method='post' action='/login' autocomplete='on'>",
            f"<input type='hidden' name='csrf_token' value='{csrf_token}'>",
            "<label for='username'>Username</label>",
            "<input id='username' name='username' type='text' autocomplete='username' ",
            "required autofocus>",
            "<label for='password'>Password</label>",
            "<input id='password' name='password' type='password' ",
            "autocomplete='current-password' required>",
            "<label class='remember'><input type='checkbox' name='remember' value='yes'>",
            "Remember this device for 7 days</label>",
            "<button type='submit'>Open private workspace</button></form>",
            "</main></body></html>",
        ]
    )
    response = Response(body, mimetype="text/html")
    response.headers["Cache-Control"] = "no-store"
    response.headers["X-Robots-Tag"] = "noindex, nofollow"
    response.headers["Referrer-Policy"] = "no-referrer"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Content-Security-Policy"] = (
        "default-src 'none'; style-src 'unsafe-inline'; form-action 'self'; "
        "base-uri 'none'; frame-ancestors 'none'"
    )
    return response


def install_owner_auth(server: Flask) -> WebAuthConfig | None:
    config = load_web_auth_config()
    server.wsgi_app = ProxyFix(  # type: ignore[method-assign]
        server.wsgi_app,
        x_for=1,
        x_proto=1,
        x_host=1,
    )

    if config is not None:
        server.secret_key = config.session_secret
        server.config.update(
            PERMANENT_SESSION_LIFETIME=timedelta(days=7),
            SESSION_COOKIE_HTTPONLY=True,
            SESSION_COOKIE_NAME="cakrawala_personal_session",
            SESSION_COOKIE_SAMESITE="Lax",
            SESSION_COOKIE_SECURE=True,
            SESSION_REFRESH_EACH_REQUEST=True,
        )

    @server.before_request
    def protect_personal_vercel() -> Any:
        public_paths = {"/healthz", "/login", "/personal/forex/sync"}
        if request.path in public_paths:
            return None
        if config is None:
            return Response(
                "Personal Vercel authentication is not configured.",
                status=503,
                mimetype="text/plain",
            )
        if not bool(session.get("owner_verified", False)):
            return redirect("/login")
        return None

    @server.route("/login", methods=["GET", "POST"])
    def login() -> Any:
        if config is None:
            return Response(
                "Personal Vercel authentication is not configured.",
                status=503,
                mimetype="text/plain",
            )
        if bool(session.get("owner_verified", False)):
            return redirect("/personal/forex")

        if request.method == "GET":
            session["login_csrf"] = secrets.token_urlsafe(32)
            return _login_page()

        submitted_csrf = request.form.get("csrf_token", "")
        expected_csrf = str(session.get("login_csrf", ""))
        csrf_valid = bool(expected_csrf) and hmac.compare_digest(
            submitted_csrf,
            expected_csrf,
        )
        username = request.form.get("username", "")
        password = request.form.get("password", "")
        username_valid = hmac.compare_digest(username, config.username)
        password_valid = check_password_hash(config.password_hash, password)

        if not csrf_valid or not username_valid or not password_valid:
            session.clear()
            session["login_csrf"] = secrets.token_urlsafe(32)
            return _login_page("Credential tidak valid."), 401

        session.clear()
        session["owner_verified"] = True
        session["owner_id"] = config.owner_id
        session["display_name"] = config.username
        session.permanent = request.form.get("remember") == "yes"
        return redirect("/personal/forex")

    @server.get("/logout")
    def logout() -> Any:
        session.clear()
        return redirect("/login")

    install_personal_forex_sync_route(server)
    install_personal_forex_route(server)
    install_personal_forex_review_route(server)
    install_personal_forex_risk_route(server)
    install_personal_forex_system_route(server)
    install_personal_market_route(server)
    install_personal_ai_lab_route(server)
    return config


def owner_session_state() -> dict[str, Any]:
    owner_id = str(session.get("owner_id", ""))
    return {
        "verified": bool(session.get("owner_verified", False)),
        "owner_id": owner_id,
        "sub": owner_id,
        "display_name": str(session.get("display_name", "")),
    }
