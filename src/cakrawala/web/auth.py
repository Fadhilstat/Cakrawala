from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any

from authlib.integrations.flask_client import OAuth
from flask import Flask, redirect, session, url_for
from werkzeug.middleware.proxy_fix import ProxyFix


@dataclass(frozen=True)
class WebAuthConfig:
    client_id: str
    client_secret: str
    owner_sub: str
    session_secret: str
    metadata_url: str = "https://accounts.google.com/.well-known/openid-configuration"


def load_web_auth_config() -> WebAuthConfig | None:
    values = {
        "client_id": os.environ.get("GOOGLE_OIDC_CLIENT_ID", "").strip(),
        "client_secret": os.environ.get("GOOGLE_OIDC_CLIENT_SECRET", "").strip(),
        "owner_sub": os.environ.get("GOOGLE_OWNER_SUB", "").strip(),
        "session_secret": os.environ.get("WEB_SESSION_SECRET", "").strip(),
    }
    if not all(values.values()):
        return None
    return WebAuthConfig(**values)


def install_owner_auth(server: Flask) -> WebAuthConfig | None:
    config = load_web_auth_config()
    server.wsgi_app = ProxyFix(  # type: ignore[method-assign]
        server.wsgi_app,
        x_for=1,
        x_proto=1,
        x_host=1,
    )
    if config is None:
        return None

    server.secret_key = config.session_secret
    server.config.update(
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SECURE=True,
        SESSION_COOKIE_SAMESITE="Lax",
    )
    oauth = OAuth(server)
    google = oauth.register(
        name="google",
        client_id=config.client_id,
        client_secret=config.client_secret,
        server_metadata_url=config.metadata_url,
        client_kwargs={"scope": "openid email profile"},
    )

    @server.get("/login")
    def login() -> Any:
        redirect_uri = url_for("auth_callback", _external=True, _scheme="https")
        return google.authorize_redirect(redirect_uri)

    @server.get("/auth/callback")
    def auth_callback() -> Any:
        token = google.authorize_access_token()
        userinfo = token.get("userinfo")
        if not isinstance(userinfo, dict):
            userinfo = google.userinfo()
        subject = str(userinfo.get("sub", "")).strip()
        session.clear()
        session["owner_verified"] = subject == config.owner_sub
        session["user_sub"] = subject
        session["display_name"] = str(userinfo.get("name", "")).strip()
        return redirect("/")

    @server.get("/logout")
    def logout() -> Any:
        session.clear()
        return redirect("/")

    return config


def owner_session_state() -> dict[str, Any]:
    return {
        "verified": bool(session.get("owner_verified", False)),
        "sub": str(session.get("user_sub", "")),
        "display_name": str(session.get("display_name", "")),
    }
