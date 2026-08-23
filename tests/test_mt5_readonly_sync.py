from __future__ import annotations

from pathlib import Path

import pytest

from cakrawala.personal.mt5_collector import MT5CollectorError
from scripts import mt5_readonly_sync


def _payload() -> dict[str, object]:
    return {
        "account": {"account_name": "ACCOUNT_SECRET_MARKER"},
        "positions": [],
        "deals": [],
    }


def test_dry_run_collects_without_uploading(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    calls: dict[str, object] = {}

    def fake_collect_payload(*, history_days: int, terminal_path: str | None) -> dict[str, object]:
        calls.update(history_days=history_days, terminal_path=terminal_path)
        return _payload()

    def fail_upload(*_args: object, **_kwargs: object) -> dict[str, object]:
        raise AssertionError("dry run must not upload private data")

    monkeypatch.setattr(mt5_readonly_sync, "collect_payload", fake_collect_payload)
    monkeypatch.setattr(mt5_readonly_sync, "post_payload", fail_upload)

    result = mt5_readonly_sync.main(
        ["--dry-run", "--history-days", "30", "--terminal-path", "terminal64.exe"]
    )

    assert result == 0
    assert calls == {"history_days": 30, "terminal_path": "terminal64.exe"}
    output = capsys.readouterr().out
    assert "0 open positions" in output
    assert "No private data was uploaded" in output
    assert "ACCOUNT_SECRET_MARKER" not in output


def test_connection_failure_is_human_readable(monkeypatch: pytest.MonkeyPatch) -> None:
    def fail_collection(**_kwargs: object) -> dict[str, object]:
        raise MT5CollectorError(
            "Keep the terminal open and log into the intended broker account."
        )

    monkeypatch.setattr(mt5_readonly_sync, "collect_payload", fail_collection)

    with pytest.raises(SystemExit, match="log into the intended broker account"):
        mt5_readonly_sync.main(["--dry-run"])


def test_cli_uses_hardened_shared_collector() -> None:
    root = Path(__file__).resolve().parents[1]
    source = (root / "scripts" / "mt5_readonly_sync.py").read_text(encoding="utf-8")

    assert "from cakrawala.personal.mt5_collector import" in source
    assert "order_send(" not in source
    assert "urllib.request" not in source

