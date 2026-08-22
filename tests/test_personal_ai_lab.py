import pytest
from flask import Flask

from cakrawala.web import personal_ai_lab
from cakrawala.web.personal_ai_lab import install_personal_ai_lab_route


def test_personal_ai_lab_requires_owner_session(monkeypatch: pytest.MonkeyPatch) -> None:
    app = Flask(__name__)
    app.secret_key = "test-secret"
    install_personal_ai_lab_route(app)

    client = app.test_client()
    response = client.get("/personal/ai-lab")
    assert response.status_code == 302
    assert response.headers["Location"].endswith("/login")

    monkeypatch.setattr(personal_ai_lab, "_page", lambda display_name: f"owner:{display_name}")
    with client.session_transaction() as owner_session:
        owner_session["owner_verified"] = True
        owner_session["display_name"] = "Owner"

    response = client.get("/personal/ai-lab")
    assert response.status_code == 200
    assert response.get_data(as_text=True) == "owner:Owner"
