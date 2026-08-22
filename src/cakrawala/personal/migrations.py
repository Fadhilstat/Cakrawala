from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

import psycopg
from psycopg import Connection

MIGRATION_NAME = re.compile(r"^(?P<version>[0-9]{3})_[a-z0-9_]+[.]sql$")
TRACKING_TABLE = "cakrawala_schema_migrations"
LOCK_NAME = "cakrawala_personal_migrations_v1"
LOCAL_HOSTS = {"localhost", "127.0.0.1", "::1"}


@dataclass(frozen=True)
class Migration:
    version: int
    name: str
    path: Path
    checksum: str
    sql_text: str


@dataclass(frozen=True)
class MigrationStatus:
    migration: Migration
    state: str


class MigrationError(RuntimeError):
    """Raised when migration state is unsafe or inconsistent."""


def migration_checksum(sql_text: str) -> str:
    return hashlib.sha256(sql_text.encode("utf-8")).hexdigest()


def discover_migrations(directory: Path) -> list[Migration]:
    if not directory.exists() or not directory.is_dir():
        raise MigrationError(f"migration directory does not exist: {directory}")

    migrations: list[Migration] = []
    seen_versions: set[int] = set()
    for path in sorted(directory.glob("*.sql")):
        match = MIGRATION_NAME.fullmatch(path.name)
        if match is None:
            raise MigrationError(
                "migration filenames must use NNN_lowercase_name.sql: " + path.name
            )
        version = int(match.group("version"))
        if version in seen_versions:
            raise MigrationError(f"duplicate migration version: {version:03d}")
        seen_versions.add(version)
        sql_text = path.read_text(encoding="utf-8")
        if not sql_text.strip():
            raise MigrationError(f"migration is empty: {path.name}")
        migrations.append(
            Migration(
                version=version,
                name=path.name,
                path=path,
                checksum=migration_checksum(sql_text),
                sql_text=sql_text,
            )
        )

    if not migrations:
        raise MigrationError("no SQL migrations were found")
    versions = [item.version for item in migrations]
    if versions != sorted(versions):
        raise MigrationError("migration versions are not ordered")
    return migrations


def secured_database_url(database_url: str) -> str:
    value = database_url.strip()
    if not value:
        raise MigrationError("DATABASE_PERSONAL_URL is required")

    parsed = urlsplit(value)
    if parsed.scheme not in {"postgres", "postgresql"}:
        raise MigrationError("DATABASE_PERSONAL_URL must use postgres or postgresql")
    if not parsed.hostname:
        raise MigrationError("DATABASE_PERSONAL_URL must include a hostname")

    query = parse_qsl(parsed.query, keep_blank_values=True)
    options = {key.lower(): val for key, val in query}
    sslmode = options.get("sslmode", "").lower()
    remote = parsed.hostname.lower() not in LOCAL_HOSTS
    if remote and sslmode == "disable":
        raise MigrationError("remote personal database connections cannot disable TLS")
    if remote and not sslmode:
        query.append(("sslmode", "require"))

    return urlunsplit(
        (
            parsed.scheme,
            parsed.netloc,
            parsed.path,
            urlencode(query),
            parsed.fragment,
        )
    )


def _ensure_tracking_table(connection: Connection[object]) -> None:
    connection.execute(
        f"""
        CREATE TABLE IF NOT EXISTS {TRACKING_TABLE} (
            version INTEGER PRIMARY KEY,
            name TEXT NOT NULL UNIQUE,
            checksum TEXT NOT NULL,
            applied_at TIMESTAMPTZ NOT NULL DEFAULT now()
        )
        """
    )
    connection.commit()


def _applied_migrations(connection: Connection[object]) -> dict[int, tuple[str, str]]:
    rows = connection.execute(
        f"SELECT version, name, checksum FROM {TRACKING_TABLE} ORDER BY version"
    ).fetchall()
    return {int(row[0]): (str(row[1]), str(row[2])) for row in rows}


def migration_plan(
    migrations: list[Migration],
    applied: dict[int, tuple[str, str]],
) -> list[MigrationStatus]:
    known_versions = {item.version for item in migrations}
    unexpected = sorted(set(applied) - known_versions)
    if unexpected:
        versions = ", ".join(f"{value:03d}" for value in unexpected)
        raise MigrationError(f"database contains unknown migration versions: {versions}")

    plan: list[MigrationStatus] = []
    for migration in migrations:
        previous = applied.get(migration.version)
        if previous is None:
            plan.append(MigrationStatus(migration=migration, state="PENDING"))
            continue
        previous_name, previous_checksum = previous
        if previous_name != migration.name:
            raise MigrationError(
                f"migration {migration.version:03d} name differs from applied history"
            )
        if previous_checksum != migration.checksum:
            raise MigrationError(
                f"migration {migration.name} changed after it was applied"
            )
        plan.append(MigrationStatus(migration=migration, state="APPLIED"))
    return plan


def inspect_database(
    database_url: str,
    migrations: list[Migration],
) -> list[MigrationStatus]:
    safe_url = secured_database_url(database_url)
    with psycopg.connect(safe_url) as connection:
        _ensure_tracking_table(connection)
        applied = _applied_migrations(connection)
    return migration_plan(migrations, applied)


def apply_migrations(
    database_url: str,
    migrations: list[Migration],
) -> list[MigrationStatus]:
    safe_url = secured_database_url(database_url)
    with psycopg.connect(safe_url) as connection:
        connection.execute("SELECT pg_advisory_lock(hashtext(%s))", (LOCK_NAME,))
        try:
            _ensure_tracking_table(connection)
            applied = _applied_migrations(connection)
            initial_plan = migration_plan(migrations, applied)

            for item in initial_plan:
                if item.state == "APPLIED":
                    continue
                migration = item.migration
                try:
                    connection.execute(migration.sql_text)
                    connection.execute(
                        f"""
                        INSERT INTO {TRACKING_TABLE} (version, name, checksum)
                        VALUES (%s, %s, %s)
                        """,
                        (migration.version, migration.name, migration.checksum),
                    )
                    connection.commit()
                except Exception:
                    connection.rollback()
                    raise

            applied = _applied_migrations(connection)
            return migration_plan(migrations, applied)
        finally:
            connection.execute("SELECT pg_advisory_unlock(hashtext(%s))", (LOCK_NAME,))
            connection.commit()
