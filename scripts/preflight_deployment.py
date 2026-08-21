from __future__ import annotations

import os


REQUIRED = (
    "DATABASE_PUBLIC_URL",
    "DATABASE_PERSONAL_URL",
    "GOOGLE_OIDC_CLIENT_ID",
    "GOOGLE_OWNER_SUB",
)
OPTIONAL_PROVIDER_KEYS = ("BPS_API_KEY", "FRED_API_KEY")


def status(name: str) -> str:
    return "configured" if os.environ.get(name) else "missing"


def main() -> int:
    missing = [name for name in REQUIRED if not os.environ.get(name)]
    for name in REQUIRED + OPTIONAL_PROVIDER_KEYS:
        print(f"{name}: {status(name)}")
    if missing:
        print("Deployment is not ready. Required server-side settings are missing.")
        return 1
    print("Required server-side settings are configured. Values were not printed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
