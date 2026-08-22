from __future__ import annotations

from flask import Flask

from cakrawala.web import personal_market


def test_personal_market_redirects_without_owner_session() -> None:
    app = Flask(__name__)
    app.secret_key = "test-secret"
    personal_market.install_personal_market_route(app)
    response = app.test_client().get("/personal/market")
    assert response.status_code == 302
    assert response.headers["Location"].endswith("/login")


def test_personal_market_is_private_and_no_store(monkeypatch) -> None:
    app = Flask(__name__)
    app.secret_key = "test-secret"
    monkeypatch.setattr(personal_market, "_fx_rows", lambda errors: [])
    monkeypatch.setattr(personal_market, "_equity_rows", lambda errors: ([], "not configured"))
    personal_market.install_personal_market_route(app)

    client = app.test_client()
    with client.session_transaction() as session:
        session["owner_verified"] = True
        session["display_name"] = "owner"

    response = client.get("/personal/market")
    assert response.status_code == 200
    assert b"Daily Market Brief" in response.data
    assert response.headers["Cache-Control"] == "no-store"
    assert response.headers["X-Robots-Tag"] == "noindex, nofollow"
    assert response.headers["Referrer-Policy"] == "no-referrer"
    assert response.headers["X-Frame-Options"] == "DENY"


def test_equity_watchlist_is_bounded_and_deduplicated(monkeypatch) -> None:
    monkeypatch.setenv(
        "PERSONAL_EQUITY_WATCHLIST",
        "BBCA@XIDX, bbca@xidx, AAPL@XNAS, MSFT@XNAS",
    )
    items = personal_market._watchlist()
    assert [(item.symbol, item.mic_code) for item in items] == [
        ("BBCA", "XIDX"),
        ("AAPL", "XNAS"),
        ("MSFT", "XNAS"),
    ]
