from __future__ import annotations

from types import SimpleNamespace

import pytest

from cakrawala.personal.mt5_collector import (
    DEFAULT_SYNC_URL,
    MT5CollectorError,
    build_payload,
    mask_account_name,
    validate_mt5_runtime,
    validate_sync_url,
)


def test_validate_sync_url_accepts_only_canonical_private_endpoint() -> None:
    assert validate_sync_url(DEFAULT_SYNC_URL) == DEFAULT_SYNC_URL

    rejected = [
        "http://cakrawala-intelligence-native.vercel.app/personal/forex/sync",
        "https://example.com/personal/forex/sync",
        "https://cakrawala-intelligence-native.vercel.app/",
        "https://cakrawala-intelligence-native.vercel.app/personal/forex/sync?next=x",
        "https://cakrawala-intelligence-native.vercel.app:444/personal/forex/sync",
    ]
    for url in rejected:
        with pytest.raises(MT5CollectorError):
            validate_sync_url(url)


def test_mask_account_name_keeps_only_last_four_characters() -> None:
    assert mask_account_name("12345678") == "****5678"
    assert mask_account_name("1234") == "****"
    assert mask_account_name("") == "account"


def test_validate_mt5_runtime_requires_read_only_calls() -> None:
    valid = SimpleNamespace(
        initialize=lambda: True,
        shutdown=lambda: None,
        account_info=lambda: None,
        positions_get=lambda: (),
        history_deals_get=lambda *_args: (),
    )
    validate_mt5_runtime(valid)

    incomplete = SimpleNamespace(initialize=lambda: True)
    with pytest.raises(MT5CollectorError, match="runtime is incomplete"):
        validate_mt5_runtime(incomplete)


class FakeMT5:
    def account_info(self) -> SimpleNamespace:
        return SimpleNamespace(
            login=12345678,
            balance=1000.0,
            equity=1010.0,
            profit=10.0,
            margin_level=500.0,
        )

    def positions_get(self) -> tuple[SimpleNamespace, ...]:
        return (
            SimpleNamespace(
                ticket=11,
                symbol="EURUSD",
                type=0,
                volume=0.1,
                price_open=1.10,
                price_current=1.11,
                sl=1.09,
                tp=1.12,
                profit=10.0,
            ),
        )

    def history_deals_get(self, _start: object, _end: object) -> tuple[SimpleNamespace, ...]:
        return ()

    def last_error(self) -> tuple[int, str]:
        return (0, "ok")


def test_build_payload_reads_account_and_positions_without_execution_calls() -> None:
    payload = build_payload(FakeMT5(), history_days=30)

    assert payload["source"] == "mt5_local_readonly_bridge"
    assert payload["account"]["account_name"] == "12345678"
    assert len(payload["positions"]) == 1
    assert payload["positions"][0]["symbol"] == "EURUSD"
    assert payload["deals"] == []
