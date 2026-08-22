from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.request
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from cakrawala.personal.mt5_normalize import (  # noqa: E402
    aggregate_closed_positions,
    normalize_account,
    normalize_positions,
)


def _load_mt5() -> Any:
    try:
        import MetaTrader5 as mt5
    except ImportError as exc:
        raise RuntimeError(
            "MetaTrader5 is not installed. Install it only on the local collector machine."
        ) from exc
    return mt5


def _initialize(mt5: Any, terminal_path: str | None) -> None:
    initialized = mt5.initialize(terminal_path) if terminal_path else mt5.initialize()
    if not initialized:
        error = mt5.last_error()
        raise RuntimeError(f"MT5 initialize failed: {error}")


def _build_payload(mt5: Any, history_days: int) -> dict[str, Any]:
    captured_at = datetime.now(UTC)
    account = mt5.account_info()
    if account is None:
        raise RuntimeError(f"MT5 account_info failed: {mt5.last_error()}")

    account_row = normalize_account(account, captured_at)
    account_name = str(account_row["account_name"])

    positions = mt5.positions_get()
    if positions is None:
        raise RuntimeError(f"MT5 positions_get failed: {mt5.last_error()}")

    history_from = captured_at - timedelta(days=history_days)
    history = mt5.history_deals_get(history_from, captured_at)
    if history is None:
        raise RuntimeError(f"MT5 history_deals_get failed: {mt5.last_error()}")

    return {
        "source": "mt5_local_readonly_bridge",
        "captured_at": captured_at.isoformat(),
        "account": account_row,
        "positions": normalize_positions(positions, account_name, captured_at),
        "deals": aggregate_closed_positions(history, account_name),
    }


def _post_payload(url: str, token: str, payload: dict[str, Any]) -> dict[str, Any]:
    body = json.dumps(payload, separators=(",", ":")).encode("utf-8")
    request = urllib.request.Request(
        url,
        data=body,
        method="POST",
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "User-Agent": "Cakrawala-MT5-Readonly-Collector/1.0",
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            response_body = response.read(200_000)
    except urllib.error.HTTPError as exc:
        detail = exc.read(4_000).decode("utf-8", errors="replace")
        raise RuntimeError(f"Sync endpoint returned HTTP {exc.code}: {detail}") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"Sync endpoint is unreachable: {exc.reason}") from exc

    result = json.loads(response_body.decode("utf-8"))
    if not isinstance(result, dict):
        raise RuntimeError("Sync endpoint returned an unexpected response")
    return result


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Read MT5 account state locally and sync normalized records to Cakrawala."
    )
    parser.add_argument(
        "--history-days",
        type=int,
        default=120,
        help="Number of calendar days of deal history to inspect, default 120.",
    )
    parser.add_argument(
        "--terminal-path",
        default=None,
        help="Optional local MetaTrader 5 terminal executable path.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Validate local collection and print record counts without uploading.",
    )
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    if not 1 <= args.history_days <= 3650:
        raise SystemExit("--history-days must be between 1 and 3650")

    mt5 = _load_mt5()
    try:
        _initialize(mt5, args.terminal_path)
        payload = _build_payload(mt5, args.history_days)
    finally:
        mt5.shutdown()

    print(
        "Collected "
        f"{len(payload['positions'])} open positions and "
        f"{len(payload['deals'])} closed positions."
    )
    if args.dry_run:
        print("Dry run complete. No private data was uploaded.")
        return 0

    url = os.environ.get("CAKRAWALA_FOREX_SYNC_URL", "").strip()
    token = os.environ.get("CAKRAWALA_FOREX_SYNC_TOKEN", "").strip()
    if not url.startswith("https://"):
        raise SystemExit("CAKRAWALA_FOREX_SYNC_URL must be an HTTPS URL")
    if not token:
        raise SystemExit("CAKRAWALA_FOREX_SYNC_TOKEN is required")

    result = _post_payload(url, token, payload)
    print(
        "Sync complete. "
        f"positions inserted={result.get('inserted_positions', 0)}, "
        f"deals inserted={result.get('inserted_deals', 0)}, "
        f"duplicate_batch={result.get('duplicate_batch', False)}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
