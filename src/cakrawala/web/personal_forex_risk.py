from __future__ import annotations

import os
from html import escape
from typing import Any

from flask import Flask, Response, redirect, session

from cakrawala.config import load_yaml
from cakrawala.personal.forex_analytics import AccountSnapshot, ForexDeal
from cakrawala.personal.forex_risk import (
    ForexRiskAssessment,
    ForexRiskState,
    assess_forex_risk,
    policy_from_mapping,
)
from cakrawala.personal.forex_sync import PositionSnapshot


def _pct(value: float | None) -> str:
    return "N/A" if value is None else f"{value:+.2f}%"


def _metric(label: str, value: str, note: str = "", tone: str = "") -> str:
    tone_class = f" {tone}" if tone else ""
    return (
        f"<div class='metric{tone_class}'>"
        f"<div class='label'>{escape(label)}</div>"
        f"<div class='value'>{escape(value)}</div>"
        f"<div class='note'>{escape(note)}</div>"
        "</div>"
    )


def _load_private() -> tuple[AccountSnapshot | None, list[PositionSnapshot], list[ForexDeal], str]:
    database_url = os.environ.get("DATABASE_PERSONAL_URL", "").strip()
    owner_sub = str(session.get("owner_id", "")).strip()
    if not database_url:
        return None, [], [], "Private database is not configured."
    try:
        from cakrawala.personal.forex_storage import (
            latest_account_snapshot,
            latest_position_snapshots,
            list_forex_deals,
        )

        return (
            latest_account_snapshot(database_url, owner_sub),
            latest_position_snapshots(database_url, owner_sub, limit=200),
            list_forex_deals(database_url, owner_sub, limit=500),
            "",
        )
    except Exception as exc:
        return None, [], [], f"Private storage unavailable: {type(exc).__name__}"


def _tone(state: ForexRiskState) -> str:
    if state == ForexRiskState.SAFE:
        return "safe"
    if state == ForexRiskState.CAUTION:
        return "caution"
    if state == ForexRiskState.LOCKED:
        return "locked"
    return "muted-state"


def _reason_list(assessment: ForexRiskAssessment) -> str:
    return "<ul>" + "".join(f"<li>{escape(reason)}</li>" for reason in assessment.reasons) + "</ul>"


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
  --green: #4de0a6;
  --amber: #f6c66d;
  --red: #ff7f91;
  --blue: #65c7ff;
}
* { box-sizing: border-box; }
body { margin: 0; background: var(--bg); color: var(--text); font-family: Inter, system-ui; }
main { max-width: 1380px; margin: auto; padding: 24px 22px 60px; }
a { color: var(--blue); }
.top { display: flex; justify-content: space-between; gap: 18px; align-items: center; }
.eyebrow { color: var(--blue); font-size: 11px; font-weight: 800; letter-spacing: .14em; }
h1 { margin: 6px 0; }
h2 { margin: 0 0 13px; font-size: 17px; }
.muted, .note, .label { color: var(--muted); }
.grid { display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 12px; }
.metric, .panel { background: var(--panel); border: 1px solid var(--line); border-radius: 13px; }
.metric { padding: 15px; }
.panel { padding: 17px; margin-top: 14px; }
.label, .note { font-size: 11px; }
.value { font-size: 22px; font-weight: 800; margin: 6px 0; }
.metric.safe .value, .state.safe { color: var(--green); }
.metric.caution .value, .state.caution { color: var(--amber); }
.metric.locked .value, .state.locked { color: var(--red); }
.state { font-size: 34px; font-weight: 900; }
ul { margin-bottom: 0; line-height: 1.7; }
.policy { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 8px 18px; }
.policy div { border-bottom: 1px solid var(--line); padding: 8px 0; }
.warning { border: 1px solid #6c5835; border-radius: 10px; padding: 12px 14px; }
@media (max-width: 850px) {
  .grid, .policy { grid-template-columns: repeat(2, 1fr); }
}
@media (max-width: 560px) {
  .grid, .policy { grid-template-columns: 1fr; }
  .top { align-items: flex-start; flex-direction: column; }
}
</style>
"""


def _page(display_name: str) -> str:
    config = load_yaml("configs/personal_forex.yaml")
    risk_values = dict(config.get("risk", {}))
    policy = policy_from_mapping(risk_values)
    snapshot, positions, deals, storage_error = _load_private()
    assessment = assess_forex_risk(snapshot, positions, deals, policy)
    tone = _tone(assessment.state)
    warning = (
        f"<div class='warning'>{escape(storage_error)}</div>"
        if storage_error
        else ""
    )
    margin = "N/A"
    if snapshot is not None and snapshot.margin_level_percent is not None:
        margin = f"{snapshot.margin_level_percent:,.0f}%"

    policy_rows = [
        ("Daily closed loss limit", f"{policy.daily_closed_loss_limit_percent:.1f}%"),
        ("Floating loss limit", f"{policy.floating_loss_limit_percent:.1f}%"),
        ("Closed-deal drawdown limit", f"{policy.closed_deal_drawdown_limit_percent:.1f}%"),
        ("Minimum margin level", f"{policy.minimum_margin_level_percent:.0f}%"),
        ("Maximum open positions", str(policy.maximum_open_positions)),
        ("Positions without stop", str(policy.maximum_positions_without_stop)),
        ("Snapshot stale after", f"{policy.snapshot_stale_minutes} min"),
    ]
    policy_html = "".join(
        f"<div><strong>{escape(label)}</strong><br><span class='muted'>{escape(value)}</span></div>"
        for label, value in policy_rows
    )

    return "".join(
        [
            "<!doctype html><html lang='en'><head><meta charset='utf-8'>",
            "<meta name='viewport' content='width=device-width,initial-scale=1'>",
            "<meta name='robots' content='noindex,nofollow'>",
            "<title>Cakrawala Forex Risk</title>",
            _styles(),
            "</head><body><main>",
            "<div class='top'><div><div class='eyebrow'>RISK COMMAND CENTER</div>",
            "<h1>Personal Forex Risk Guard</h1>",
            f"<div class='muted'>Verified owner: {escape(display_name or 'Owner')}</div></div>",
            "<div><a href='/personal/forex'>Command Center</a> | ",
            "<a href='/personal/forex/review'>Summary Analytics</a> | ",
            "<a href='/logout'>Logout</a></div></div>",
            warning,
            "<div class='panel'><div class='eyebrow'>CURRENT REVIEW STATE</div>",
            f"<div class='state {tone}'>{escape(assessment.state.value)}</div>",
            "<p class='muted'>This state is a personal risk review gate. It does not send, block, ",
            "or modify broker orders.</p>",
            _reason_list(assessment),
            "</div>",
            "<div class='grid'>",
            _metric("Daily closed P/L", _pct(assessment.daily_closed_pnl_percent), "Percent of current balance", tone),
            _metric("Floating P/L", _pct(assessment.floating_pnl_percent), "Percent of current balance", tone),
            _metric("Closed-deal drawdown", _pct(assessment.closed_deal_drawdown_percent), "Imported closed-deal curve", tone),
            _metric("Margin level", margin, "Latest private account snapshot", tone),
            _metric("Open positions", str(assessment.open_positions), "Latest synchronized snapshot"),
            _metric("Without stop", str(assessment.positions_without_stop), "Policy check"),
            _metric(
                "Snapshot age",
                "N/A" if assessment.snapshot_age_minutes is None else f"{assessment.snapshot_age_minutes:.1f} min",
                "Freshness check",
            ),
            _metric("Execution", "MANUAL", "No broker order endpoint"),
            "</div>",
            "<div class='panel'><h2>Configured personal policy</h2>",
            "<div class='policy'>",
            policy_html,
            "</div></div>",
            "<div class='panel'><h2>Interpretation boundary</h2>",
            "<p class='muted'>Drawdown here comes from the imported closed-deal P/L series and is ",
            "scaled against the latest balance. It is useful for discipline, but it is not a ",
            "replacement for the broker's complete historical equity curve.</p></div>",
            "</main></body></html>",
        ]
    )


def install_personal_forex_risk_route(server: Flask) -> None:
    @server.get("/personal/forex/risk")
    def personal_forex_risk() -> Any:
        if not bool(session.get("owner_verified", False)):
            return redirect("/login")
        display_name = str(session.get("display_name", "")).strip()
        response = Response(_page(display_name), mimetype="text/html")
        response.headers["Cache-Control"] = "no-store"
        response.headers["X-Robots-Tag"] = "noindex, nofollow"
        response.headers["Referrer-Policy"] = "no-referrer"
        response.headers["X-Frame-Options"] = "DENY"
        return response
