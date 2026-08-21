import pytest
from flask import Flask

from cakrawala.data.providers.ecb_fx import parse_ecb_pairs
from cakrawala.web import personal_forex
from cakrawala.web.personal_forex import install_personal_forex_route


def _ecb_xml() -> str:
    return """<?xml version="1.0" encoding="UTF-8"?>
    <Envelope>
      <Cube>
        <Cube time="2026-08-18">
          <Cube currency="USD" rate="1.20"/>
          <Cube currency="JPY" rate="180"/>
          <Cube currency="GBP" rate="0.86"/>
          <Cube currency="CHF" rate="0.94"/>
          <Cube currency="AUD" rate="1.78"/>
          <Cube currency="CAD" rate="1.62"/>
          <Cube currency="NZD" rate="1.94"/>
        </Cube>
        <Cube time="2026-08-19">
          <Cube currency="USD" rate="1.18"/>
          <Cube currency="JPY" rate="181"/>
          <Cube currency="GBP" rate="0.85"/>
          <Cube currency="CHF" rate="0.93"/>
          <Cube currency="AUD" rate="1.77"/>
          <Cube currency="CAD" rate="1.61"/>
          <Cube currency="NZD" rate="1.92"/>
        </Cube>
      </Cube>
    </Envelope>"""


def test_ecb_pair_parser_builds_exact_cross_rates() -> None:
    rows = {item.pair: item for item in parse_ecb_pairs(_ecb_xml())}
    assert rows["EURUSD"].rate == pytest.approx(1.18)
    assert rows["USDJPY"].rate == pytest.approx(181 / 1.18)
    assert rows["GBPUSD"].rate == pytest.approx(1.18 / 0.85)
    assert rows["EURGBP"].rate == pytest.approx(0.85)
    assert rows["EURUSD"].change_1d_pct is not None


def test_personal_forex_route_is_owner_only(monkeypatch: pytest.MonkeyPatch) -> None:
    app = Flask(__name__)
    app.secret_key = "test-secret"
    install_personal_forex_route(app)

    client = app.test_client()
    response = client.get("/personal/forex")
    assert response.status_code == 302
    assert response.headers["Location"].endswith("/login")

    monkeypatch.setattr(personal_forex, "_page", lambda display_name: f"owner:{display_name}")
    with client.session_transaction() as owner_session:
        owner_session["owner_verified"] = True
        owner_session["display_name"] = "Owner"

    response = client.get("/personal/forex")
    assert response.status_code == 200
    assert response.get_data(as_text=True) == "owner:Owner"
