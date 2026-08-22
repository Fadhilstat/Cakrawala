from __future__ import annotations

import argparse
import os
from pathlib import Path

from cakrawala.personal.migrations import (
    MigrationError,
    MigrationStatus,
    apply_migrations,
    discover_migrations,
    inspect_database,
)

DEFAULT_DIRECTORY = Path("migrations/personal")


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Check or apply versioned migrations for the owner-only personal database."
    )
    actions = parser.add_mutually_exclusive_group()
    actions.add_argument(
        "--check",
        action="store_true",
        help="Inspect migration state without applying pending SQL. This is the default.",
    )
    actions.add_argument(
        "--apply",
        action="store_true",
        help="Apply pending migrations. This requires an explicit flag.",
    )
    parser.add_argument(
        "--directory",
        type=Path,
        default=DEFAULT_DIRECTORY,
        help="Migration directory. Defaults to migrations/personal.",
    )
    return parser


def _print_status(rows: list[MigrationStatus]) -> None:
    for row in rows:
        migration = row.migration
        print(f"{migration.version:03d} {row.state:<7} {migration.name}")


def main() -> int:
    args = _parser().parse_args()
    database_url = os.environ.get("DATABASE_PERSONAL_URL", "")
    try:
        migrations = discover_migrations(args.directory)
        if args.apply:
            result = apply_migrations(database_url, migrations)
            _print_status(result)
            print("Personal database migrations are up to date.")
            return 0

        result = inspect_database(database_url, migrations)
        _print_status(result)
        pending = [item for item in result if item.state == "PENDING"]
        if pending:
            print(f"Pending migrations: {len(pending)}")
            return 2
        print("Personal database migration check passed.")
        return 0
    except MigrationError as exc:
        print(f"Migration safety check failed: {exc}")
        return 1
    except Exception as exc:
        print(f"Personal database check failed: {type(exc).__name__}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
