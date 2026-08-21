from __future__ import annotations

import argparse
import os
import tomllib
from pathlib import Path
from typing import Any


PERSONAL_REQUIREMENTS = (
    ("auth.redirect_uri", "auth", "redirect_uri", "AUTH_REDIRECT_URI"),
    ("auth.cookie_secret", "auth", "cookie_secret", "AUTH_COOKIE_SECRET"),
    ("auth.client_id", "auth", "client_id", "AUTH_CLIENT_ID"),
    ("auth.client_secret", "auth", "client_secret", "AUTH_CLIENT_SECRET"),
    (
        "auth.server_metadata_url",
        "auth",
        "server_metadata_url",
        "AUTH_SERVER_METADATA_URL",
    ),
    ("cakrawala.owner_sub", "cakrawala", "owner_sub", "CAKRAWALA_OWNER_SUB"),
    (
        "cakrawala.database_personal_url",
        "cakrawala",
        "database_personal_url",
        "DATABASE_PERSONAL_URL",
    ),
)
OPTIONAL_PROVIDER_KEYS = ("BPS_API_KEY", "FRED_API_KEY")


def load_settings(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    with path.open("rb") as handle:
        data = tomllib.load(handle)
    if not isinstance(data, dict):
        raise ValueError("Streamlit secrets file must contain a TOML mapping")
    return data


def configured(
    settings: dict[str, Any],
    section: str,
    key: str,
    environment_name: str,
) -> bool:
    if os.environ.get(environment_name):
        return True
    values = settings.get(section, {})
    return isinstance(values, dict) and bool(values.get(key))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=("public", "personal"), default="public")
    parser.add_argument(
        "--secrets",
        type=Path,
        default=Path(".streamlit/secrets.toml"),
    )
    args = parser.parse_args()

    if args.mode == "public":
        print("Public Mode preflight: ready for stateless public-source deployment.")
        print("Run scripts/check_sources.py from the target runtime before sharing the URL.")
        return 0

    settings = load_settings(args.secrets)
    missing: list[str] = []
    for label, section, key, environment_name in PERSONAL_REQUIREMENTS:
        is_configured = configured(settings, section, key, environment_name)
        print(f"{label}: {'configured' if is_configured else 'missing'}")
        if not is_configured:
            missing.append(label)

    for name in OPTIONAL_PROVIDER_KEYS:
        value = "configured" if os.environ.get(name) else "optional or missing"
        print(f"{name}: {value}")

    if missing:
        print("Personal Mode is not ready. Missing server-side settings remain.")
        return 1

    print("Personal Mode server-side settings are configured. Values were not printed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
