from __future__ import annotations

from datetime import UTC, datetime, timedelta
from html import escape
from typing import Any

from flask import Flask, Response, redirect, session

from cakrawala.config import load_yaml
from cakrawala.data.providers.bls_calendar import fetch_bls_calendar
from cakrawala.data.providers.ecb_fx import fetch_forex_pairs
from cakrawala.intelligence.decision_prep import assess_fx_decision_prep


def _event_risk() -> bool:
    try:
        events = fetch_bls_calendar().data
    except Exception:
        return False
    now = datetime.now(UTC)
    cutoff = now + timedelta(hours=24)
    return any(now <= event.starts_at <= cutoff for event in events)


def _prep_rows() -> str:
    try:
        result = fetch_forex_pairs()
    except Exception as exc:
        return f"<p>Decision prep unavailable: {escape(type(exc).__name__)}</p>"

    event_risk = _event_risk()
    today = datetime.now(UTC).date()
    rows: list[str] = []
    for item in result.data:
        stale = (today - item.as_of).days > 4
        prep = assess_fx_decision_prep(
            pair=item.pair,
            change_1d_pct=item.change_1d_pct,
            change_5d_pct=item.change_5d_pct,
            change_20d_pct=item.change_20d_pct,
            event_risk=event_risk,
            stale=stale,
        )
        reasons = " ".join(prep.reasons)
        rows.append(
            "<tr>"
            f"<td>{escape(item.pair)}</td>"
            f"<td>{escape(prep.evidence_state)}</td>"
            f"<td>{escape(prep.trend_alignment)}</td>"
            f"<td>{prep.confidence * 100:.0f}%</td>"
            f"<td>{escape(reasons)}</td>"
            "</tr>"
        )
    return (
        "<table><thead><tr><th>Pair</th><th>State</th><th>Trend</th>"
        "<th>Alignment</th><th>Why</th></tr></thead><tbody>"
        + "".join(rows)
        + "</tbody></table>"
    )


def _radar_rows() -> str:
    try:
        payload = load_yaml("configs/ai_research_radar.yaml")
    except Exception as exc:
        return f"<p>AI research radar unavailable: {escape(type(exc).__name__)}</p>"

    rows = []
    for item in payload.get("candidates", []):
        rows.append(
            "<tr>"
            f"<td>{escape(str(item.get('name', '')))}</td>"
            f"<td>{escape(str(item.get('type', '')))}</td>"
            f"<td>{escape(str(item.get('status', '')))}</td>"
            f"<td>{escape(str(item.get('free_fit', '')))}</td>"
            f"<td>{escape(str(item.get('license', '')))}</td>"
            "</tr>"
        )
    return (
        "<table><thead><tr><th>Candidate</th><th>Role</th><th>Status</th>"
        "<th>Free fit</th><th>License</th></tr></thead><tbody>"
        + "".join(rows)
        + "</tbody></table>"
    )


def _page(display_name: str) -> str:
    owner = escape(display_name or "Owner")
    return "".join(
        [
            "<!doctype html><html><head><meta charset='utf-8'>",
            "<meta name='viewport' content='width=device-width,initial-scale=1'>",
            "<title>Cakrawala AI Decision Lab</title><style>",
            "body{font-family:Inter,system-ui,sans-serif;background:#0b1020;",
            "color:#edf2f7;margin:0}",
            "main{max-width:1280px;margin:auto;padding:28px 22px 60px}",
            "a{color:#8cc8ff} .muted{color:#9fb0c7} .panel{background:#121a2b;",
            "border:1px solid #253047;border-radius:14px;padding:18px;margin-top:16px}",
            "table{width:100%;border-collapse:collapse;font-size:13px}",
            "th,td{padding:10px 8px;border-bottom:1px solid #253047;",
            "text-align:left;vertical-align:top}",
            "th{color:#aebdd1}</style></head><body><main>",
            f"<div class='muted'>Verified owner: {owner}</div>",
            "<h1>AI Decision Lab</h1>",
            "<p><a href='/personal/forex'>Forex Desk</a> | <a href='/'>Terminal</a> | ",
            "<a href='/logout'>Logout</a></p>",
            "<div class='panel'><h2>Decision-prep matrix</h2>",
            "<p class='muted'>Deterministic alignment from official ECB ",
            "reference-rate horizons. A nearby BLS event forces WAIT_EVENT. ",
            "This is evidence triage, not a trade signal.</p>",
            _prep_rows(),
            "</div><div class='panel'><h2>AI research radar</h2>",
            "<p class='muted'>Candidates stay observe-only or sandboxed until license, leakage, ",
            "benchmark, and walk-forward gates are satisfied.</p>",
            _radar_rows(),
            "</div><div class='panel'><h2>Research stack</h2><ul>",
            "<li>Daily multi-agent forex council with mandatory risk challenge</li>",
            "<li>Probabilistic forecasting candidates: Chronos-Bolt and TinyTimeMixer</li>",
            "<li>Financial sentiment candidate: FinBERT after license confirmation</li>",
            "<li>Offline research architecture references: FinRL and Microsoft Qlib</li>",
            "<li>Model output never overrides freshness, authorization, or risk gates</li>",
            "</ul></div></main></body></html>",
        ]
    )


def install_personal_ai_lab_route(server: Flask) -> None:
    @server.get("/personal/ai-lab")
    def personal_ai_lab() -> Any:
        if not bool(session.get("owner_verified", False)):
            return redirect("/login")
        display_name = str(session.get("display_name", "")).strip()
        return Response(_page(display_name), mimetype="text/html")
