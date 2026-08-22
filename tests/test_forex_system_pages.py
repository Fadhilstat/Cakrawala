from __future__ import annotations

import pytest
from flask import Flask

from cakrawala.web import personal_forex_risk, personal_forex_system
from cakrawala.web.personal_forex_risk import install_personal_forex_risk_route
from cakrawala.web.personal_forex_system import install_personal_forex_system_route


def test_forex_risk_route_is_owner_only(monkeypatch: pytest.MonkeyPatch) -> None:
    app = Flask(__name__)
    app.secret_key = "test-secret"
    install_personal_forex_risk_route(app)
    client = app.test_client()

    response = client.get("/personal/forex/risk")
    assert response.status_code == 302
    assert response.headers["Location"].endswith("/login")

    monkeypatch.setattr(personal_forex_risk, "_page", lambda display_name: f"risk:{display_name}")
    with client.session_transaction() as owner_session:
        owner_session["owner_verified"] = True
        owner_session["display_name"] = "Owner"

    response = client.get("/personal/forex/risk")
    assert response.status_code == 200
    assert response.get_data(as_text=True) == "risk:Owner"
    assert response.headers["Cache-Control"] == "no-store"


def test_forex_system_route_is_owner_only(monkeypatch: pytest.MonkeyPatch) -> None:
    app = Flask(__name__)
    app.secret_key = "test-secret"
    install_personal_forex_system_route(app)
    client = app.test_client()

    response = client.get("/personal/forex/system")
    assert response.status_code == 302
    assert response.headers["Location"].endswith("/login")

    monkeypatch.setattr(personal_forex_system, "_page", lambda display_name: f"system:{display_name}")
    with client.session_transaction() as owner_session:
        owner_session["owner_verified"] = True
        owner_session["display_name"] = "Owner"

    response = client.get("/personal/forex/system")
    assert response.status_code == 200
    assert response.get_data(as_text=True) == "system:Owner"
    assert response.headers["X-Robots-Tag"] == "noindex, nofollow"
