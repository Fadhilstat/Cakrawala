from __future__ import annotations

import argparse
import os

AUTH_REQUIREMENTS = (
    "PERSONAL_AUTH_USERNAME",
    "PERSONAL_AUTH_PASSWORD_HASH",
    "WEB_SESSION_SECRET",
    "PERSONAL_OWNER_ID",
)
STORAGE_REQUIREMENTS = ("DATABASE_PERSONAL_URL",)
MT5_REQUIREMENTS = ("PERSONAL_FOREX_INGEST_TOKEN",)
EQUITY_REQUIREMENTS = ("TWELVE_DATA_API_KEY", "PERSONAL_EQUITY_WATCHLIST")


def _status(name: str) -> bool:
    configured = bool(os.environ.get(name, "").strip())
    print(f"{name}: {'configured' if configured else 'missing'}")
    return configured


def _check_group(title: str, names: tuple[str, ...], *, required: bool) -> bool:
    print(f"\n{title}")
    results = [_status(name) for name in names]
    complete = all(results)
    if complete:
        print("status: ready")
    elif required:
        print("status: blocked")
    else:
        print("status: optional or incomplete")
    return complete or not required


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Check server-side deployment readiness without printing secret values."
    )
    parser.add_argument("--mode", choices=("public", "personal"), default="public")
    parser.add_argument(
        "--require-storage",
        action="store_true",
        help="Require the private PostgreSQL connection for this check.",
    )
    parser.add_argument(
        "--require-mt5",
        action="store_true",
        help="Require the MT5 ingest token for this check.",
    )
    parser.add_argument(
        "--require-equity",
        action="store_true",
        help="Require the private Twelve Data key and equity watchlist.",
    )
    args = parser.parse_args()

    if args.mode == "public":
        print("Public Mode preflight: ready for stateless public-source deployment.")
        print("Run scripts/check_sources.py from the target runtime before sharing the URL.")
        return 0

    ready = True
    ready &= _check_group("Owner authentication", AUTH_REQUIREMENTS, required=True)
    ready &= _check_group(
        "Private PostgreSQL",
        STORAGE_REQUIREMENTS,
        required=args.require_storage,
    )
    ready &= _check_group("MT5 read-only sync", MT5_REQUIREMENTS, required=args.require_mt5)
    ready &= _check_group(
        "Private equity intelligence",
        EQUITY_REQUIREMENTS,
        required=args.require_equity,
    )

    if not ready:
        print("\nPersonal Mode preflight failed. Required server-side settings are missing.")
        return 1

    print("\nPersonal Mode preflight passed. Secret values were not printed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
