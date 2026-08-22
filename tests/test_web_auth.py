from __future__ import annotations

import re

import pytest
from flask import Flask
from werkzeug.security import generate_password_hash

from cakrawala.web.auth import install_owner_auth


@pytest.fixture
def protected_app(monkeypatch: pytest.MonkeyPatch) -> Flask:
    monkeypatch.setenv("PERSONAL_AUTH_USERNAME", "owner")
    monkeypatch.setenv(
        "PERSONAL_AUTH_PASSWORD_HASH",
        generate_password_hash("correct horse battery staple"),
    )
    monkeypatch.setenv("WEB_SESSION_SECRET", "test-session-secret-with-enough-entropy")
    monkeypatch.setenv("PERSONAL_OWNER_ID", "owner-local")

    app = Flask(__name__)

    @app.get("/")
    def index() -> str:
        return "private root"

    @app.get("/healthz")
    def healthz() -> dict[str, str]:
        return {"status": "ok"}

    install_owner_auth(app)
    return app


def _csrf_token(html: str) -> str:
    match = re.search(r"name='csrf_token' value='([^']+)'", html)
    assert match is not None
    return match.group(1)


def test_unauthenticated_requests_are_redirected(protected_app: Flask) -> None:
    client = protected_app.test_client()

    root = client.get("/", base_url="https://localhost")
    assert root.status_code == 302
    assert root.headers["Location"].endswith("/login")

    health = client.get("/healthz", base_url="https://localhost")
    assert health.status_code == 200
    assert health.get_json() == {"status": "ok"}


def test_login_requires_csrf_and_valid_credentials(protected_app: Flask) -> None:
    client = protected_app.test_client()
    login_page = client.get("/login", base_url="https://localhost")
    assert login_page.status_code == 200
    assert login_page.headers["Cache-Control"] == "no-store"
    assert login_page.headers["X-Robots-Tag"] == "noindex, nofollow"
    token = _csrf_token(login_page.get_data(as_text=True))

    missing_csrf = client.post(
        "/login",
        data={"username": "owner", "password": "correct horse battery staple"},
        base_url="https://localhost",
    )
    assert missing_csrf.status_code == 401

    login_page = client.get("/login", base_url="https://localhost")
    token = _csrf_token(login_page.get_data(as_text=True))
    wrong_password = client.post(
        "/login",
        data={
            "csrf_token": token,
            "username": "owner",
            "password": "wrong password",
        },
        base_url="https://localhost",
    )
    assert wrong_password.status_code == 401


def test_valid_login_opens_private_application(protected_app: Flask) -> None:
    client = protected_app.test_client()
    login_page = client.get("/login", base_url="https://localhost")
    token = _csrf_token(login_page.get_data(as_text=True))

    response = client.post(
        "/login",
        data={
            "csrf_token": token,
            "username": "owner",
            "password": "correct horse battery staple",
            "remember": "yes",
        },
        base_url="https://localhost",
    )
    assert response.status_code == 302
    assert response.headers["Location"].endswith("/personal/ai-lab")

    root = client.get("/", base_url="https://localhost")
    assert root.status_code == 200
    assert root.get_data(as_text=True) == "private root"

    with client.session_transaction() as owner_session:
        assert owner_session["owner_verified"] is True
        assert owner_session["owner_id"] == "owner-local"
        assert owner_session.permanent is True


def test_missing_auth_configuration_fails_closed(monkeypatch: pytest.MonkeyPatch) -> None:
    for name in (
        "PERSONAL_AUTH_USERNAME",
        "PERSONAL_AUTH_PASSWORD_HASH",
        "WEB_SESSION_SECRET",
        "PERSONAL_OWNER_ID",
    ):
        monkeypatch.delenv(name, raising=False)

    app = Flask(__name__)

    @app.get("/")
    def index() -> str:
        return "must not be public"

    install_owner_auth(app)
    client = app.test_client()
    response = client.get("/", base_url="https://localhost")
    assert response.status_code == 503
    assert "not configured" in response.get_data(as_text=True)
