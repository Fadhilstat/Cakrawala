from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from types import ModuleType

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = ROOT / "scripts" / "preflight_deployment.py"


def _load_preflight_module() -> ModuleType:
    spec = importlib.util.spec_from_file_location("preflight_deployment", SCRIPT_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError("Unable to load preflight deployment script")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


preflight_deployment = _load_preflight_module()


@pytest.fixture(autouse=True)
def clear_preflight_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    names = (
        *preflight_deployment.AUTH_REQUIREMENTS,
        *preflight_deployment.STORAGE_REQUIREMENTS,
        *preflight_deployment.MT5_REQUIREMENTS,
        *preflight_deployment.EQUITY_REQUIREMENTS,
    )
    for name in names:
        monkeypatch.delenv(name, raising=False)


def _set_auth(monkeypatch: pytest.MonkeyPatch) -> None:
    for name in preflight_deployment.AUTH_REQUIREMENTS:
        monkeypatch.setenv(name, "configured-for-test")


def test_public_mode_passes_without_secrets(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(sys, "argv", ["preflight_deployment.py", "--mode", "public"])
    assert preflight_deployment.main() == 0


def test_personal_mode_requires_owner_auth(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(sys, "argv", ["preflight_deployment.py", "--mode", "personal"])
    assert preflight_deployment.main() == 1


def test_personal_mode_allows_optional_integrations(monkeypatch: pytest.MonkeyPatch) -> None:
    _set_auth(monkeypatch)
    monkeypatch.setattr(sys, "argv", ["preflight_deployment.py", "--mode", "personal"])
    assert preflight_deployment.main() == 0


def test_storage_can_be_promoted_to_required(monkeypatch: pytest.MonkeyPatch) -> None:
    _set_auth(monkeypatch)
    monkeypatch.setattr(
        sys,
        "argv",
        ["preflight_deployment.py", "--mode", "personal", "--require-storage"],
    )
    assert preflight_deployment.main() == 1

    monkeypatch.setenv("DATABASE_PERSONAL_URL", "postgresql://test.invalid/db")
    assert preflight_deployment.main() == 0


def test_equity_requires_key_and_watchlist_together(monkeypatch: pytest.MonkeyPatch) -> None:
    _set_auth(monkeypatch)
    monkeypatch.setenv("TWELVE_DATA_API_KEY", "private-test-key")
    monkeypatch.setattr(
        sys,
        "argv",
        ["preflight_deployment.py", "--mode", "personal", "--require-equity"],
    )
    assert preflight_deployment.main() == 1

    monkeypatch.setenv("PERSONAL_EQUITY_WATCHLIST", "BBCA@XIDX")
    assert preflight_deployment.main() == 0
