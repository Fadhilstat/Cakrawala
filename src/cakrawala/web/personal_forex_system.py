from __future__ import annotations

import os
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from html import escape
from typing import Any

from flask import Flask, Response, redirect, session

from cakrawala.config import load_yaml
from cakrawala.data.providers.bls_calendar import fetch_bls_calendar
from cakrawala.data.providers.cftc import fetch_tff_market
from cakrawala.data.providers.ecb_fx import fetch_forex_pairs
from cakrawala.data.providers.news_feeds import fetch_macro_news


@dataclass(frozen=True)
class SystemCheck:
    name: str
    status: str
    detail: str


def _run_check(name: str, check: Callable[[], str]) -> SystemCheck:
    try:
        detail = check()
    except Exception as exc:
        return SystemCheck(name, "DEGRADED", type(exc).__name__)
    return SystemCheck(name, "ONLINE", detail)


def _source_checks() -> list[SystemCheck]:
    def ecb() -> str:
        result = fetch_forex_pairs()
        return f"{len(result.data)} configured pair references"

    def bls() -> str:
        result = fetch_bls_calendar()
        return f"{len(result.data)} official release records"

    def cftc() -> str:
        result = fetch_tff_market("EURO FX")
        return f"{len(result.data)} TFF records for EUR"

    def news() -> str:
        result = fetch_macro_news(limit_per_source=1)
        return f"{len(result)} official feed items"

    return [
        _run_check("ECB FX", ecb),
        _run_check("BLS calendar", bls),
        _run_check("CFTC TFF", cftc),
        _run_check("Macro feeds", news),
    ]


def _private_checks() -> list[SystemCheck]:
    auth_ready = all(
        os.environ.get(name, "").strip()
        for name in (
            "PERSONAL_AUTH_USERNAME",
            "PERSONAL_AUTH_PASSWORD_HASH",
            "WEB_SESSION_SECRET",
        )
    )
    database_url = os.environ.get("DATABASE_PERSONAL_URL", "").strip()
    ingest_token = os.environ.get("PERSONAL_FOREX_INGEST_TOKEN", "").strip()
    owner_id = os.environ.get("PERSONAL_OWNER_ID", "").strip()

    auth_detail = (
        "server-side credential gate"
        if auth_ready
        else "required environment values missing"
    )
    database_detail = (
        "configured"
        if database_url
        else "DATABASE_PERSONAL_URL is not configured"
    )
    ingest_detail = (
        "configured, value hidden"
        if ingest_token
        else "PERSONAL_FOREX_INGEST_TOKEN is missing"
    )
    owner_detail = (
        "configured"
        if owner_id
        else "authentication username fallback is active"
    )
    checks = [
        SystemCheck(
            "Owner authentication",
            "READY" if auth_ready else "MISSING",
            auth_detail,
        ),
        SystemCheck(
            "Private database",
            "READY" if database_url else "MISSING",
            database_detail,
        ),
        SystemCheck(
            "MT5 ingest token",
            "READY" if ingest_token else "MISSING",
            ingest_detail,
        ),
        SystemCheck(
            "Stable owner ID",
            "READY" if owner_id else "FALLBACK",
            owner_detail,
        ),
    ]

    if not database_url:
        checks.append(
            SystemCheck(
                "Latest private snapshot",
                "UNAVAILABLE",
                "database not configured",
            )
        )
        return checks

    try:
        from cakrawala.personal.forex_storage import latest_account_snapshot

        owner_sub = str(session.get("owner_id", "")).strip()
        snapshot = latest_account_snapshot(database_url, owner_sub)
        if snapshot is None:
            checks.append(
                SystemCheck(
                    "Latest private snapshot",
                    "EMPTY",
                    "no snapshot ingested yet",
                )
            )
        else:
            age = datetime.now(UTC) - snapshot.captured_at.astimezone(UTC)
            minutes = max(age.total_seconds(), 0) / 60
            checks.append(
                SystemCheck(
                    "Latest private snapshot",
                    "READY",
                    f"{minutes:.1f} minutes old",
                )
            )
    except Exception as exc:
        checks.append(
            SystemCheck(
                "Latest private snapshot",
                "DEGRADED",
                type(exc).__name__,
            )
        )
    return checks


def _status_class(status: str) -> str:
    if status in {"ONLINE", "READY"}:
        return "ok"
    if status in {"DEGRADED", "FALLBACK", "EMPTY"}:
        return "warn"
    return "bad"


def _checks_table(checks: list[SystemCheck]) -> str:
    rows: list[str] = []
    for item in checks:
        status_class = _status_class(item.status)
        rows.append(
            "<tr>"
            f"<td>{escape(item.name)}</td>"
            f"<td><span class='status {status_class}'>"
            f"{escape(item.status)}</span></td>"
            f"<td>{escape(item.detail)}</td>"
            "</tr>"
        )
    return (
        "<div class='table-wrap'><table><thead><tr>"
        "<th>Component</th><th>Status</th><th>Detail</th>"
        "</tr></thead><tbody>"
        + "".join(rows)
        + "</tbody></table></div>"
    )


def _policy_rows(values: dict[str, object]) -> str:
    return "".join(
        "<tr>"
        f"<td>{escape(str(key).replace('_', ' ').title())}</td>"
        f"<td>{escape(str(value))}</td>"
        "</tr>"
        for key, value in values.items()
    )


def _setup_content() -> str:
    config = load_yaml("configs/personal_forex.yaml")
    pairs = [str(value) for value in config.get("pairs", [])]
    risk = dict(config.get("risk", {}))
    integration = dict(config.get("integration", {}))
    workspace = dict(config.get("workspace", {}))

    pair_html = "".join(
        f"<span class='pair'>{escape(pair)}</span>"
        for pair in pairs
    )
    return "".join(
        [
            "<div class='panel'><h2>Monitored pairs</h2>",
            "<div class='pairs'>",
            pair_html,
            "</div></div>",
            "<div class='three'>",
            "<div class='panel'><h2>Risk policy</h2><table><tbody>",
            _policy_rows(risk),
            "</tbody></table></div>",
            "<div class='panel'><h2>Integration policy</h2><table><tbody>",
            _policy_rows(integration),
            "</tbody></table></div>",
            "<div class='panel'><h2>Workspace policy</h2><table><tbody>",
            _policy_rows(workspace),
            "</tbody></table></div></div>",
            "<div class='panel'><h2>Configuration boundary</h2>",
            "<p class='muted'>These settings are non-secret operating policy ",
            "stored in the repository. Passwords, database URLs, and ingest ",
            "tokens remain environment secrets and are never rendered on this ",
            "page.</p></div>",
        ]
    )


def _styles() -> str:
    return """
<style>
:root {
  color-scheme: dark;
  --bg: #080d15;
  --panel: #101827;
  --line: #223047;
  --text: #eef4fb;
  --muted: #91a2b8;
  --blue: #65c7ff;
  --green: #4de0a6;
  --amber: #f6c66d;
  --red: #ff7f91;
}
* { box-sizing: border-box; }
body {
  margin: 0;
  background: var(--bg);
  color: var(--text);
  font-family: Inter, system-ui;
}
main { max-width: 1450px; margin: auto; padding: 24px 22px 60px; }
a { color: var(--blue); }
.top {
  display: flex;
  justify-content: space-between;
  gap: 18px;
  align-items: center;
}
.eyebrow {
  color: var(--blue);
  font-size: 11px;
  font-weight: 800;
  letter-spacing: .14em;
}
h1 { margin: 6px 0; }
h2 { margin: 0 0 13px; font-size: 17px; }
.muted { color: var(--muted); line-height: 1.55; }
.panel {
  background: var(--panel);
  border: 1px solid var(--line);
  border-radius: 13px;
  padding: 17px;
  margin-top: 14px;
}
.two {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 14px;
}
.three {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 14px;
}
.table-wrap { overflow: auto; }
table { width: 100%; border-collapse: collapse; font-size: 12px; }
th, td {
  padding: 9px 7px;
  border-bottom: 1px solid var(--line);
  text-align: left;
}
th { color: #aebdd1; }
.status {
  display: inline-block;
  padding: 4px 7px;
  border-radius: 999px;
  font-size: 10px;
  font-weight: 800;
}
.status.ok { color: var(--green); border: 1px solid #275f50; }
.status.warn { color: var(--amber); border: 1px solid #6c5835; }
.status.bad { color: var(--red); border: 1px solid #653743; }
.pairs { display: flex; flex-wrap: wrap; gap: 8px; }
.pair {
  border: 1px solid #275f50;
  color: var(--green);
  padding: 7px 10px;
  border-radius: 999px;
  font-size: 11px;
  font-weight: 800;
}
@media (max-width: 960px) {
  .two, .three { grid-template-columns: 1fr; }
}
@media (max-width: 600px) {
  .top { align-items: flex-start; flex-direction: column; }
}
</style>
"""


def _page(display_name: str) -> str:
    source_checks = _source_checks()
    private_checks = _private_checks()
    models = load_yaml("configs/models.yaml")
    roles = dict(models.get("roles", {}))
    promoted = sum(value is not None for value in roles.values())
    model_check = SystemCheck(
        "Promoted model roles",
        "READY" if promoted else "RESEARCH",
        f"{promoted}/{len(roles)} promoted",
    )

    return "".join(
        [
            "<!doctype html><html lang='en'><head><meta charset='utf-8'>",
            "<meta name='viewport' content='width=device-width,initial-scale=1'>",
            "<meta name='robots' content='noindex,nofollow'>",
            "<title>Cakrawala Forex System</title>",
            _styles(),
            "</head><body><main>",
            "<div class='top'><div>",
            "<div class='eyebrow'>INFRASTRUCTURE & TEST BED</div>",
            "<h1>Forex System Health</h1>",
            f"<div class='muted'>Verified owner: "
            f"{escape(display_name or 'Owner')}</div></div>",
            "<div><a href='/personal/forex'>Command Center</a> | ",
            "<a href='/personal/forex/risk'>Risk</a> | ",
            "<a href='/personal/forex/review'>Analytics</a> | ",
            "<a href='/logout'>Logout</a></div></div>",
            "<div class='two'><div class='panel'>",
            "<h2>Live public evidence</h2>",
            _checks_table(source_checks),
            "</div><div class='panel'><h2>Private infrastructure</h2>",
            _checks_table([*private_checks, model_check]),
            "</div></div>",
            "<div class='panel'>",
            "<div class='eyebrow'>CONFIGURATION & PAIR SETUP</div>",
            "<h1>Operating Setup</h1></div>",
            _setup_content(),
            "</main></body></html>",
        ]
    )


def install_personal_forex_system_route(server: Flask) -> None:
    @server.get("/personal/forex/system")
    def personal_forex_system() -> Any:
        if not bool(session.get("owner_verified", False)):
            return redirect("/login")
        display_name = str(session.get("display_name", "")).strip()
        response = Response(_page(display_name), mimetype="text/html")
        response.headers["Cache-Control"] = "no-store"
        response.headers["X-Robots-Tag"] = "noindex, nofollow"
        response.headers["Referrer-Policy"] = "no-referrer"
        response.headers["X-Frame-Options"] = "DENY"
        return response
