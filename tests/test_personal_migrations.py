from __future__ import annotations

from pathlib import Path
from urllib.parse import parse_qs, urlsplit

import pytest

from cakrawala.personal.migrations import (
    MigrationError,
    discover_migrations,
    migration_plan,
    secured_database_url,
)


def _write(directory: Path, name: str, sql_text: str = "SELECT 1;\n") -> None:
    (directory / name).write_text(sql_text, encoding="utf-8")


def test_discovers_versioned_migrations_in_order(tmp_path: Path) -> None:
    _write(tmp_path, "002_second.sql")
    _write(tmp_path, "001_first.sql")

    migrations = discover_migrations(tmp_path)

    assert [item.version for item in migrations] == [1, 2]
    assert [item.name for item in migrations] == ["001_first.sql", "002_second.sql"]
    assert all(len(item.checksum) == 64 for item in migrations)


def test_rejects_nonconforming_migration_filename(tmp_path: Path) -> None:
    _write(tmp_path, "migration.sql")

    with pytest.raises(MigrationError, match="filenames"):
        discover_migrations(tmp_path)


def test_rejects_duplicate_migration_versions(tmp_path: Path) -> None:
    _write(tmp_path, "001_first.sql")
    _write(tmp_path, "001_second.sql")

    with pytest.raises(MigrationError, match="duplicate migration version"):
        discover_migrations(tmp_path)


def test_remote_database_url_adds_tls_when_missing() -> None:
    secured = secured_database_url("postgresql://user:secret@db.example.com/app")
    query = parse_qs(urlsplit(secured).query)

    assert query["sslmode"] == ["require"]
    assert "secret" in secured


def test_remote_database_url_rejects_disabled_tls() -> None:
    with pytest.raises(MigrationError, match="cannot disable TLS"):
        secured_database_url(
            "postgresql://user:secret@db.example.com/app?sslmode=disable"
        )


def test_local_database_url_can_disable_tls() -> None:
    value = "postgresql://user:secret@localhost/app?sslmode=disable"
    assert secured_database_url(value) == value


def test_plan_marks_pending_and_applied_migrations(tmp_path: Path) -> None:
    _write(tmp_path, "001_first.sql")
    _write(tmp_path, "002_second.sql")
    migrations = discover_migrations(tmp_path)
    applied = {
        1: (migrations[0].name, migrations[0].checksum),
    }

    plan = migration_plan(migrations, applied)

    assert [item.state for item in plan] == ["APPLIED", "PENDING"]


def test_plan_rejects_changed_applied_migration(tmp_path: Path) -> None:
    _write(tmp_path, "001_first.sql")
    migration = discover_migrations(tmp_path)[0]

    with pytest.raises(MigrationError, match="changed after it was applied"):
        migration_plan([migration], {1: (migration.name, "0" * 64)})


def test_plan_rejects_unknown_database_migration(tmp_path: Path) -> None:
    _write(tmp_path, "001_first.sql")
    migration = discover_migrations(tmp_path)[0]

    with pytest.raises(MigrationError, match="unknown migration versions"):
        migration_plan(
            [migration],
            {
                1: (migration.name, migration.checksum),
                99: ("099_unknown.sql", "0" * 64),
            },
        )
