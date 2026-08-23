from __future__ import annotations

import argparse
import os
import sys
from collections.abc import Sequence
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from cakrawala.personal.mt5_collector import (  # noqa: E402
    DEFAULT_SYNC_URL,
    MT5CollectorError,
    collect_payload,
    post_payload,
)


def _parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
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
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = _parse_args(argv)
    if not 1 <= args.history_days <= 3650:
        raise SystemExit("--history-days must be between 1 and 3650")

    try:
        payload = collect_payload(
            history_days=args.history_days,
            terminal_path=args.terminal_path,
        )
    except MT5CollectorError as exc:
        raise SystemExit(f"MT5 connection could not be completed. {exc}") from None

    print(
        "Collected "
        f"{len(payload['positions'])} open positions and "
        f"{len(payload['deals'])} closed positions."
    )
    if args.dry_run:
        print("Dry run complete. No private data was uploaded.")
        return 0

    url = os.environ.get("CAKRAWALA_FOREX_SYNC_URL", DEFAULT_SYNC_URL).strip()
    url = url or DEFAULT_SYNC_URL
    token = os.environ.get("CAKRAWALA_FOREX_SYNC_TOKEN", "").strip()
    if not token:
        raise SystemExit("CAKRAWALA_FOREX_SYNC_TOKEN is required")

    try:
        result = post_payload(token, payload, url=url)
    except MT5CollectorError as exc:
        raise SystemExit(f"Private sync could not be completed. {exc}") from None
    print(
        "Sync complete. "
        f"positions inserted={result.get('inserted_positions', 0)}, "
        f"deals inserted={result.get('inserted_deals', 0)}, "
        f"duplicate_batch={result.get('duplicate_batch', False)}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

