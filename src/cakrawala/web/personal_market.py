from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from html import escape
from typing import Any

from flask import Flask, Response, redirect, session

from cakrawala.data.providers.bls_calendar import fetch_bls_calendar
from cakrawala.data.providers.ecb_fx import fetch_forex_pairs
from cakrawala.data.providers.twelve_data import fetch_daily_equity_history
from cakrawala.intelligence.economic_calendar_evidence import (
    EconomicCalendarSnapshot,
    load_calendar_snapshot,
    macro_context_for_pair,
)
from cakrawala.intelligence.market_brief import (
    DecisionTrace,
    MarketAssessment,
    MarketBias,
    apply_fx_context_gates,
    assess_change_windows,
    assess_daily_prices,
    build_fx_decision_trace,
)
from cakrawala.models.health import load_model_health


@dataclass(frozen=True)
class EquityWatch:
    symbol: str
    mic_code: str | None


def _watchlist() -> list[EquityWatch]:
    raw = os.environ.get("PERSONAL_EQUITY_WATCHLIST", "").strip()
    if not raw:
        return []
    output: list[EquityWatch] = []
    seen: set[tuple[str, str | None]] = set()
    for token in raw.split(","):
        cleaned = token.strip()
        if not cleaned:
            continue
        parts = [part.strip().upper() for part in cleaned.split("@", 1)]
        symbol = parts[0]
        mic_code = parts[1] if len(parts) == 2 and parts[1] else None
        key = (symbol, mic_code)
        if key not in seen:
            output.append(EquityWatch(symbol=symbol, mic_code=mic_code))
            seen.add(key)
    return output[:20]


def _pct(value: float | None) -> str:
    return "N/A" if value is None else f"{value:+.2f}%"


def _tone(bias: MarketBias) -> str:
    return {
        MarketBias.BUY_BIAS: "positive",
        MarketBias.SELL_BIAS: "negative",
        MarketBias.WAIT: "neutral",
        MarketBias.INSUFFICIENT: "muted",
    }[bias]


def _assessment_row(
    item: MarketAssessment,
    source: str,
    trace: DecisionTrace | None = None,
) -> str:
    as_of = item.as_of.isoformat() if item.as_of else "N/A"
    rationale = " ".join(item.rationale)
    return "".join(
        [
            "<tr>",
            f"<td><strong>{escape(item.symbol)}</strong></td>",
            f"<td class='{_tone(item.bias)}'>{escape(item.bias.value)}</td>",
            f"<td>{escape(_pct(item.change_1d_pct))}</td>",
            f"<td>{escape(_pct(item.change_5d_pct))}</td>",
            f"<td>{escape(_pct(item.change_20d_pct))}</td>",
            f"<td>{escape(as_of)}</td>",
            f"<td>{escape(source)}</td>",
            f"<td>{escape(trace.summary() if trace else 'Price evidence only')}</td>",
            f"<td>{escape(rationale)}</td>",
            f"<td>{escape(item.invalidation)}</td>",
            "</tr>",
        ]
    )


def _event_gate(errors: list[str]) -> tuple[bool, bool]:
    try:
        events = fetch_bls_calendar().data
    except Exception as exc:
        errors.append(f"BLS event calendar unavailable: {type(exc).__name__}")
        return False, False

    now = datetime.now(UTC)
    cutoff = now + timedelta(hours=24)
    event_risk = any(now <= item.starts_at <= cutoff for item in events)
    return True, event_risk


def _calendar_snapshot(errors: list[str]) -> EconomicCalendarSnapshot | None:
    try:
        snapshot = load_calendar_snapshot()
    except Exception as exc:
        errors.append(f"Macro surprise snapshot unavailable: {type(exc).__name__}")
        return None
    if not snapshot.is_fresh():
        errors.append("Macro surprise snapshot is stale and excluded from FX gating.")
        return None
    return snapshot


def _fx_rows(errors: list[str]) -> list[str]:
    try:
        result = fetch_forex_pairs()
    except Exception as exc:
        errors.append(f"ECB FX unavailable: {type(exc).__name__}")
        return []

    event_calendar_available, event_risk = _event_gate(errors)
    calendar_snapshot = _calendar_snapshot(errors)
    try:
        model_context = load_model_health().decision_support_state
    except Exception as exc:
        errors.append(f"Model context unavailable: {type(exc).__name__}")
        model_context = "UNAVAILABLE"
    rows: list[str] = []
    for snapshot in result.data:
        base_assessment = assess_change_windows(
            snapshot.pair,
            as_of=snapshot.as_of,
            change_1d_pct=snapshot.change_1d_pct,
            change_5d_pct=snapshot.change_5d_pct,
            change_20d_pct=snapshot.change_20d_pct,
        )
        macro_alignment = "NO_CONTEXT"
        if calendar_snapshot is not None:
            macro_alignment = macro_context_for_pair(
                snapshot.pair,
                calendar_snapshot,
            ).alignment
        assessment = apply_fx_context_gates(
            base_assessment,
            event_calendar_available=event_calendar_available,
            event_risk=event_risk,
            macro_alignment=macro_alignment,
        )
        trace = build_fx_decision_trace(
            base_assessment,
            assessment,
            event_calendar_available=event_calendar_available,
            event_risk=event_risk,
            macro_alignment=macro_alignment,
            model_context=model_context,
        )
        rows.append(
            _assessment_row(
                assessment,
                "ECB reference rates + BLS event gate + macro evidence",
                trace,
            )
        )
    return rows


def _equity_rows(errors: list[str]) -> tuple[list[str], str]:
    watches = _watchlist()
    if not watches:
        return [], (
            "Set PERSONAL_EQUITY_WATCHLIST with entries such as BBCA@XIDX or AAPL@XNAS. "
            "No placeholder equity data is generated."
        )
    if not os.environ.get("TWELVE_DATA_API_KEY", "").strip():
        return [], (
            "TWELVE_DATA_API_KEY is not configured. Equity analysis remains unavailable "
            "instead of falling back to synthetic data."
        )

    rows: list[str] = []
    for watch in watches:
        try:
            result = fetch_daily_equity_history(
                watch.symbol,
                mic_code=watch.mic_code,
                outputsize=60,
            )
            assessment = assess_daily_prices(watch.symbol, result.data["bars"])
        except Exception as exc:
            label = f"{watch.symbol}@{watch.mic_code}" if watch.mic_code else watch.symbol
            errors.append(f"{label} unavailable: {type(exc).__name__}")
            continue
        source = "Twelve Data personal/internal source"
        rows.append(_assessment_row(assessment, source))
    return rows, ""


def _table(rows: list[str]) -> str:
    if not rows:
        return "<p class='muted'>No validated assessments available.</p>"
    return "".join(
        [
            "<div class='table-wrap'><table><thead><tr>",
            "<th>Instrument</th><th>State</th><th>1D</th><th>5D</th><th>20D</th>",
            "<th>As of</th><th>Source</th><th>Decision path</th><th>Why</th>",
            "<th>Invalidation</th>",
            "</tr></thead><tbody>",
            "".join(rows),
            "</tbody></table></div>",
        ]
    )


def _model_health_panel() -> str:
    try:
        summary = load_model_health()
    except Exception as exc:
        return (
            "<div class='warning'><strong>Model health unavailable:</strong> "
            f"{escape(type(exc).__name__)}</div>"
        )

    rows: list[str] = []
    for item in summary.roles:
        model_name = item.model_name or "none"
        verified = item.latest_verified_run.isoformat() if item.latest_verified_run else "N/A"
        freshness = "STALE" if item.stale else "CURRENT"
        rows.append(
            "<tr>"
            f"<td>{escape(item.role)}</td>"
            f"<td>{escape(item.state)}</td>"
            f"<td>{escape(model_name)}</td>"
            f"<td>{escape(verified)}</td>"
            f"<td>{escape(freshness)}</td>"
            f"<td>{escape(item.message)}</td>"
            "</tr>"
        )

    overall = "PRODUCTION MODEL READY" if summary.production_ready else "BASELINE OR RESEARCH ONLY"
    return "".join(
        [
            "<div class='panel'><h2>Model health and role status</h2>",
            f"<p><strong>{escape(overall)}</strong></p>",
            "<p class='muted'>A directional daily state does not imply model confirmation. "
            "When no promoted model is assigned, the dashboard is explicitly baseline-only.</p>",
            "<div class='table-wrap'><table><thead><tr>",
            "<th>Role</th><th>State</th><th>Model</th><th>Verified run</th>",
            "<th>Freshness</th><th>Meaning</th></tr></thead><tbody>",
            "".join(rows),
            "</tbody></table></div></div>",
        ]
    )


def _styles() -> str:
    return """
<style>
:root { color-scheme: dark; --bg:#071019; --panel:#0d1824; --line:#223246;
  --text:#e6edf5; --muted:#91a3b7; --green:#5ed6a0; --red:#ff7f88; --amber:#e9bd67; }
* { box-sizing: border-box; }
body { margin:0; background:var(--bg); color:var(--text); font-family:Inter,system-ui,sans-serif; }
main { width:min(1500px,calc(100% - 28px)); margin:0 auto; padding:24px 0 48px; }
a { color:#8ecbff; text-decoration:none; }
.top {
  display:flex; align-items:flex-start; justify-content:space-between;
  gap:18px; margin-bottom:18px;
}
.eyebrow { color:var(--green); font-size:11px; letter-spacing:.12em; font-weight:800; }
h1 { margin:6px 0 6px; font-size:29px; } h2 { margin:0 0 10px; font-size:17px; }
.muted { color:var(--muted); line-height:1.55; }
.panel {
  background:var(--panel); border:1px solid var(--line); border-radius:12px;
  padding:16px; margin:14px 0;
}
.warning {
  border:1px solid #6b5735; border-radius:10px; padding:11px 13px;
  margin:12px 0; color:#f3d9a0;
}
.table-wrap { overflow:auto; } table { width:100%; border-collapse:collapse; font-size:11px; }
th,td {
  padding:9px 8px; text-align:left; vertical-align:top;
  border-bottom:1px solid var(--line); min-width:72px;
}
th { color:#aebdd1; position:sticky; top:0; background:var(--panel); }
td:nth-child(8),td:nth-child(9),td:nth-child(10) {
  min-width:280px; white-space:normal; line-height:1.45;
}
.positive { color:var(--green); font-weight:800; } .negative { color:var(--red); font-weight:800; }
.neutral { color:var(--amber); font-weight:800; } .muted { color:var(--muted); }
@media(max-width:760px){ .top{flex-direction:column;} main{width:min(100% - 20px,1500px);} }
</style>
"""


def _page(display_name: str) -> str:
    errors: list[str] = []
    fx_rows = _fx_rows(errors)
    equity_rows, equity_note = _equity_rows(errors)
    warnings = "".join(f"<div class='warning'>{escape(item)}</div>" for item in errors)
    owner = escape(display_name or "Owner")
    return "".join(
        [
            "<!doctype html><html lang='en'><head><meta charset='utf-8'>",
            "<meta name='viewport' content='width=device-width,initial-scale=1'>",
            "<meta name='robots' content='noindex,nofollow'>",
            "<title>Cakrawala Daily Market Brief</title>",
            _styles(),
            "</head><body><main>",
            "<div class='top'><div><div class='eyebrow'>OWNER-ONLY DECISION SUPPORT</div>",
            "<h1>Daily Market Brief</h1>",
            f"<div class='muted'>Verified owner: {owner}</div></div><div>",
            "<a href='/personal/forex'>Forex Desk</a> | ",
            "<a href='/personal/ai-lab'>AI Lab</a> | <a href='/logout'>Logout</a>",
            "</div></div>",
            "<div class='panel'><strong>Interpretation boundary:</strong> ",
            "BUY BIAS and SELL BIAS require aligned completed-price momentum. FX states are ",
            "also gated by official scheduled-event availability and recent macro conflict. ",
            "They are not broker orders, guaranteed returns, or permission to ignore spread, ",
            "liquidity, position sizing, model health, or risk checks.</div>",
            warnings,
            _model_health_panel(),
            "<div class='panel'><h2>FX decision-support board</h2>",
            "<p class='muted'>Official ECB reference rates provide the price context. The BLS ",
            "calendar is used as a fail-closed near-term event gate. Fresh bounded macro ",
            "surprise evidence may support or veto the directional state. ECB rates are not ",
            "executable broker quotes. The Decision path keeps every gate visible.</p>",
            _table(fx_rows),
            "</div>",
            "<div class='panel'><h2>Equity watchlist</h2>",
            "<p class='muted'>Optional Twelve Data feed is restricted to this owner-only ",
            "internal workspace. Raw provider data is not published by Cakrawala.</p>",
            f"<p class='muted'>{escape(equity_note)}</p>" if equity_note else "",
            _table(equity_rows),
            "</div>",
            "<div class='panel'><strong>Daily workflow:</strong> validate source freshness, ",
            "review macro and event risk, check model-role health, compare the directional ",
            "state with broker prices, write invalidation, size risk, and record the outcome. ",
            "WAIT and INSUFFICIENT are valid decisions when evidence is mixed, stale, or ",
            "unavailable.</div>",
            "</main></body></html>",
        ]
    )


def install_personal_market_route(server: Flask) -> None:
    @server.get("/personal/market")
    def personal_market() -> Any:
        if not bool(session.get("owner_verified", False)):
            return redirect("/login")
        display_name = str(session.get("display_name", "")).strip()
        response = Response(_page(display_name), mimetype="text/html")
        response.headers["Cache-Control"] = "no-store"
        response.headers["X-Robots-Tag"] = "noindex, nofollow"
        response.headers["Referrer-Policy"] = "no-referrer"
        response.headers["X-Frame-Options"] = "DENY"
        return response

