from __future__ import annotations

import json
import urllib.error
import urllib.parse
import urllib.request
from datetime import UTC, datetime, timedelta
from typing import Any

from cakrawala.personal.mt5_normalize import (
    aggregate_closed_positions,
    normalize_account,
    normalize_positions,
)

DEFAULT_SYNC_URL = (
    "https://cakrawala-intelligence-native.vercel.app/personal/forex/sync"
)
ALLOWED_SYNC_HOST = "cakrawala-intelligence-native.vercel.app"
SYNC_PATH = "/personal/forex/sync"
MAX_RESPONSE_BYTES = 200_000
REQUIRED_MT5_CALLS = (
    "initialize",
    "shutdown",
    "account_info",
    "positions_get",
    "history_deals_get",
)


class MT5CollectorError(RuntimeError):
    """Raised when local collection or private sync cannot be completed safely."""


def validate_sync_url(url: str) -> str:
    value = url.strip()
    parsed = urllib.parse.urlsplit(value)
    if parsed.scheme != "https":
        raise MT5CollectorError("Sync URL must use HTTPS.")
    if parsed.hostname != ALLOWED_SYNC_HOST:
        raise MT5CollectorError("Sync URL host is not approved for Cakrawala.")
    if parsed.port not in {None, 443}:
        raise MT5CollectorError("Sync URL must use the standard HTTPS port.")
    if parsed.path != SYNC_PATH or parsed.query or parsed.fragment:
        raise MT5CollectorError("Sync URL path is not the approved collector endpoint.")
    return value


def mask_account_name(account_name: str) -> str:
    value = account_name.strip()
    if not value:
        return "account"
    if len(value) <= 4:
        return "*" * len(value)
    return "*" * (len(value) - 4) + value[-4:]


def validate_mt5_runtime(mt5: Any) -> None:
    missing = [name for name in REQUIRED_MT5_CALLS if not callable(getattr(mt5, name, None))]
    if missing:
        fields = ", ".join(sorted(missing))
        raise MT5CollectorError(f"MetaTrader 5 runtime is incomplete: {fields}")


def load_mt5() -> Any:
    try:
        import MetaTrader5 as mt5
    except ImportError as exc:
        raise MT5CollectorError(
            "MetaTrader 5 support is unavailable in this collector build."
        ) from exc
    validate_mt5_runtime(mt5)
    return mt5


def initialize_mt5(mt5: Any, terminal_path: str | None = None) -> None:
    initialized = mt5.initialize(terminal_path) if terminal_path else mt5.initialize()
    if not initialized:
        error = mt5.last_error()
        raise MT5CollectorError(f"MT5 initialize failed: {error}")


def build_payload(mt5: Any, history_days: int = 120) -> dict[str, Any]:
    if not 1 <= history_days <= 3650:
        raise MT5CollectorError("History days must be between 1 and 3650.")

    captured_at = datetime.now(UTC)
    account = mt5.account_info()
    if account is None:
        raise MT5CollectorError(f"MT5 account_info failed: {mt5.last_error()}")

    account_row = normalize_account(account, captured_at)
    account_name = str(account_row["account_name"])

    positions = mt5.positions_get()
    if positions is None:
        raise MT5CollectorError(f"MT5 positions_get failed: {mt5.last_error()}")

    history_from = captured_at - timedelta(days=history_days)
    history = mt5.history_deals_get(history_from, captured_at)
    if history is None:
        raise MT5CollectorError(f"MT5 history_deals_get failed: {mt5.last_error()}")

    return {
        "source": "mt5_local_readonly_bridge",
        "captured_at": captured_at.isoformat(),
        "account": account_row,
        "positions": normalize_positions(positions, account_name, captured_at),
        "deals": aggregate_closed_positions(history, account_name),
    }


def collect_payload(
    *,
    history_days: int = 120,
    terminal_path: str | None = None,
) -> dict[str, Any]:
    mt5 = load_mt5()
    try:
        initialize_mt5(mt5, terminal_path)
        return build_payload(mt5, history_days)
    finally:
        mt5.shutdown()


def post_payload(
    token: str,
    payload: dict[str, Any],
    *,
    url: str = DEFAULT_SYNC_URL,
) -> dict[str, Any]:
    safe_url = validate_sync_url(url)
    secret = token.strip()
    if not secret:
        raise MT5CollectorError("Private sync token is required.")

    body = json.dumps(payload, separators=(",", ":")).encode("utf-8")
    request = urllib.request.Request(
        safe_url,
        data=body,
        method="POST",
        headers={
            "Authorization": f"Bearer {secret}",
            "Content-Type": "application/json",
            "User-Agent": "Cakrawala-MT5-Readonly-Collector/1.0",
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            response_body = response.read(MAX_RESPONSE_BYTES + 1)
    except urllib.error.HTTPError as exc:
        detail = exc.read(4_000).decode("utf-8", errors="replace")
        raise MT5CollectorError(
            f"Sync endpoint returned HTTP {exc.code}: {detail}"
        ) from exc
    except urllib.error.URLError as exc:
        raise MT5CollectorError(f"Sync endpoint is unreachable: {exc.reason}") from exc

    if len(response_body) > MAX_RESPONSE_BYTES:
        raise MT5CollectorError("Sync endpoint response exceeded the safety limit.")

    try:
        result = json.loads(response_body.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise MT5CollectorError("Sync endpoint returned invalid JSON.") from exc
    if not isinstance(result, dict):
        raise MT5CollectorError("Sync endpoint returned an unexpected response.")
    return result
