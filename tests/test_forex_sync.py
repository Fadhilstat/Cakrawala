from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
from flask import Flask

from cakrawala.personal.forex_analytics import ForexDeal
from cakrawala.personal.forex_storage import SyncIngestResult
from cakrawala.personal.forex_sync import canonical_payload_hash, parse_sync_payload
from cakrawala.personal.mt5_normalize import aggregate_closed_positions
from cakrawala.web import personal_forex_sync
from cakrawala.web.personal_forex_sync import install_personal_forex_sync_route


def _payload(captured_at: datetime | None = None) -> dict[str, object]:
    captured = captured_at or datetime.now(UTC)
    timestamp = captured.isoformat()
    return {
        "source": "test_readonly_bridge",
        "captured_at": timestamp,
        "account": {
            "account_name": "12345",
            "balance": 10000,
            "equity": 10025,
            "floating_pnl": 25,
            "margin_level_percent": 650,
            "captured_at": timestamp,
        },
        "positions": [
            {
                "ticket": "77",
                "symbol": "EURUSD",
                "side": "BUY",
                "volume": 0.1,
                "entry_price": 1.1,
                "current_price": 1.101,
                "stop_loss": 1.095,
                "take_profit": 1.11,
                "floating_pnl": 10,
                "captured_at": timestamp,
            }
        ],
        "deals": [
            {
                "ticket": "88",
                "symbol": "GBPUSD",
                "side": "SELL",
                "volume": 0.2,
                "entry_price": 1.3,
                "exit_price": 1.29,
                "opened_at": (captured - timedelta(hours=2)).isoformat(),
                "closed_at": (captured - timedelta(hours=1)).isoformat(),
                "realized_pnl": 40,
                "commission": -2,
                "swap": -1,
                "fee": -0.5,
                "result_r": 1.2,
            }
        ],
    }


def test_sync_payload_parses_bounded_private_records() -> None:
    parsed = parse_sync_payload(_payload())

    assert parsed.account.account_name == "12345"
    assert parsed.positions[0].symbol == "EURUSD"
    assert parsed.deals[0].net_pnl == pytest.approx(36.5)
    assert len(parsed.payload_hash) == 64


def test_sync_payload_rejects_duplicate_and_nonfinite_values() -> None:
    duplicate = _payload()
    positions = duplicate["positions"]
    assert isinstance(positions, list)
    positions.append(dict(positions[0]))
    with pytest.raises(ValueError, match="duplicate position"):
        parse_sync_payload(duplicate)

    invalid = _payload()
    account = invalid["account"]
    assert isinstance(account, dict)
    account["balance"] = float("nan")
    with pytest.raises(ValueError, match="finite"):
        parse_sync_payload(invalid)


def test_canonical_payload_hash_does_not_depend_on_key_order() -> None:
    first = {"b": 2, "a": {"y": 2, "x": 1}}
    second = {"a": {"x": 1, "y": 2}, "b": 2}
    assert canonical_payload_hash(first) == canonical_payload_hash(second)


def test_mt5_normalizer_aggregates_only_complete_simple_positions() -> None:
    raw = [
        {
            "ticket": 1,
            "position_id": 900,
            "entry": 0,
            "type": 0,
            "symbol": "EURUSD",
            "volume": 0.2,
            "price": 1.10,
            "time": 1000,
            "time_msc": 1000000,
            "profit": 0,
            "commission": -1,
            "swap": 0,
            "fee": 0,
        },
        {
            "ticket": 2,
            "position_id": 900,
            "entry": 1,
            "type": 1,
            "symbol": "EURUSD",
            "volume": 0.2,
            "price": 1.11,
            "time": 2000,
            "time_msc": 2000000,
            "profit": 50,
            "commission": -1,
            "swap": -0.5,
            "fee": -0.25,
        },
    ]

    rows = aggregate_closed_positions(raw, "12345")

    assert len(rows) == 1
    assert rows[0]["ticket"] == "900"
    assert rows[0]["side"] == "BUY"
    assert rows[0]["realized_pnl"] == pytest.approx(50)
    assert rows[0]["commission"] == pytest.approx(-2)
    assert rows[0]["fee"] == pytest.approx(-0.25)


def test_forex_deal_net_pnl_includes_fee() -> None:
    now = datetime.now(UTC)
    deal = ForexDeal(
        ticket="1",
        account_name="12345",
        symbol="EURUSD",
        side="BUY",
        volume=0.1,
        entry_price=1.1,
        exit_price=1.2,
        opened_at=now - timedelta(hours=1),
        closed_at=now,
        realized_pnl=20,
        commission=-1,
        swap=-0.5,
        fee=-0.25,
    )
    assert deal.net_pnl == pytest.approx(18.25)


def test_sync_endpoint_requires_token_and_accepts_valid_payload(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    app = Flask(__name__)
    install_personal_forex_sync_route(app)
    monkeypatch.setenv("PERSONAL_FOREX_INGEST_TOKEN", "collector-secret")
    monkeypatch.setenv("DATABASE_PERSONAL_URL", "postgresql://private")
    monkeypatch.setenv("PERSONAL_OWNER_ID", "owner-1")

    captured: dict[str, object] = {}

    def fake_ingest(database_url: str, owner_sub: str, payload: object) -> SyncIngestResult:
        captured["database_url"] = database_url
        captured["owner_sub"] = owner_sub
        captured["payload"] = payload
        return SyncIngestResult(False, 1, 1)

    monkeypatch.setattr(personal_forex_sync, "ingest_sync_payload", fake_ingest)
    client = app.test_client()

    unauthorized = client.post("/personal/forex/sync", json=_payload())
    assert unauthorized.status_code == 401

    response = client.post(
        "/personal/forex/sync",
        json=_payload(),
        headers={"Authorization": "Bearer collector-secret"},
    )
    assert response.status_code == 200
    assert response.json["inserted_positions"] == 1
    assert response.json["inserted_deals"] == 1
    assert captured["owner_sub"] == "owner-1"


def test_sync_endpoint_rejects_stale_payload(monkeypatch: pytest.MonkeyPatch) -> None:
    app = Flask(__name__)
    install_personal_forex_sync_route(app)
    monkeypatch.setenv("PERSONAL_FOREX_INGEST_TOKEN", "collector-secret")
    monkeypatch.setenv("DATABASE_PERSONAL_URL", "postgresql://private")
    monkeypatch.setenv("PERSONAL_OWNER_ID", "owner-1")
    stale = datetime.now(UTC) - timedelta(hours=1)

    response = app.test_client().post(
        "/personal/forex/sync",
        json=_payload(stale),
        headers={"Authorization": "Bearer collector-secret"},
    )
    assert response.status_code == 400
    assert response.json["status"] == "stale_payload"
