from __future__ import annotations

import os
from datetime import UTC, datetime
from html import escape
from typing import Any

from flask import Flask, Response, redirect, session

from cakrawala.personal.forex_analytics import AccountSnapshot, ForexDeal
from cakrawala.personal.forex_review import (
    GroupPerformance,
    cumulative_equity_points,
    performance_by_hour_utc,
    performance_by_side,
    performance_by_symbol,
    performance_by_weekday,
    review_summary,
)
from cakrawala.personal.forex_sync import PositionSnapshot


def _money(value: float | None) -> str:
    return "N/A" if value is None else f"${value:+,.2f}"


def _number(value: float | None, digits: int = 2) -> str:
    return "N/A" if value is None else f"{value:,.{digits}f}"


def _metric(label: str, value: str, note: str = "") -> str:
    return (
        "<div class='metric'>"
        f"<div class='label'>{escape(label)}</div>"
        f"<div class='value'>{escape(value)}</div>"
        f"<div class='note'>{escape(note)}</div>"
        "</div>"
    )


def _table(headers: list[str], rows: list[list[str]]) -> str:
    if not rows:
        return "<p class='muted'>No records available yet.</p>"
    head = "".join(f"<th>{escape(value)}</th>" for value in headers)
    body = "".join(
        "<tr>"
        + "".join(f"<td>{escape(value)}</td>" for value in row)
        + "</tr>"
        for row in rows
    )
    return (
        "<div class='table-wrap'><table><thead><tr>"
        f"{head}</tr></thead><tbody>{body}</tbody></table></div>"
    )


def _group_table(rows: list[GroupPerformance]) -> str:
    data = [
        [
            row.label,
            str(row.trades),
            _money(row.net_pnl),
            _number(row.win_rate_percent) + "%" if row.win_rate_percent is not None else "N/A",
            _money(row.average_pnl),
        ]
        for row in rows
    ]
    return _table(["Group", "Trades", "Net P/L", "Win rate", "Average"], data)


def _positions_table(positions: list[PositionSnapshot]) -> str:
    rows = [
        [
            item.symbol,
            item.side,
            _number(item.volume, 2),
            _number(item.entry_price, 5),
            _number(item.current_price, 5),
            _number(item.stop_loss, 5),
            _number(item.take_profit, 5),
            _money(item.floating_pnl),
            item.captured_at.isoformat(),
        ]
        for item in positions
    ]
    return _table(
        ["Symbol", "Side", "Lots", "Entry", "Current", "SL", "TP", "P/L", "Captured"],
        rows,
    )


def _equity_svg(deals: list[ForexDeal]) -> str:
    points = cumulative_equity_points(deals)
    if len(points) < 2:
        return "<p class='muted'>Equity curve appears after at least two closed trades.</p>"

    values = [value for _, value in points]
    low = min(values)
    high = max(values)
    span = high - low or 1.0
    width = 760.0
    height = 180.0
    coords: list[str] = []
    for index, (_, value) in enumerate(points):
        x = index / (len(points) - 1) * width
        y = height - ((value - low) / span * height)
        coords.append(f"{x:.1f},{y:.1f}")
    polyline = " ".join(coords)
    return (
        "<div class='chart'>"
        f"<svg viewBox='0 0 {width:.0f} {height:.0f}' role='img' "
        "aria-label='Cumulative closed trade P and L'>"
        f"<polyline points='{polyline}' fill='none' stroke='currentColor' "
        "stroke-width='3' vector-effect='non-scaling-stroke'/></svg>"
        f"<div class='chart-note'>Range {_money(low)} to {_money(high)}</div>"
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

        snapshot = latest_account_snapshot(database_url, owner_sub)
        positions = latest_position_snapshots(database_url, owner_sub, limit=200)
        deals = list_forex_deals(database_url, owner_sub, limit=500)
        return snapshot, positions, deals, ""
    except Exception as exc:
        return None, [], [], f"Private storage unavailable: {type(exc).__name__}"


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
  --accent: #65c7ff;
  --green: #4de0a6;
}
* { box-sizing: border-box; }
body { margin: 0; background: var(--bg); color: var(--text); font-family: Inter, system-ui; }
main { max-width: 1480px; margin: auto; padding: 24px 22px 60px; }
a { color: var(--accent); }
.top { display: flex; justify-content: space-between; gap: 18px; align-items: center; }
.eyebrow { color: var(--accent); font-size: 11px; font-weight: 800; letter-spacing: .14em; }
h1 { margin: 6px 0; }
h2 { font-size: 17px; margin: 0 0 14px; }
.muted, .note { color: var(--muted); }
.grid { display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 12px; }
.two { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 14px; }
.metric, .panel { background: var(--panel); border: 1px solid var(--line); border-radius: 13px; }
.metric { padding: 15px; }
.panel { padding: 17px; margin-top: 14px; }
.label, .note { font-size: 11px; }
.value { font-size: 22px; font-weight: 800; margin: 6px 0; }
.table-wrap { overflow: auto; }
table { width: 100%; border-collapse: collapse; font-size: 12px; }
th, td { padding: 9px 7px; border-bottom: 1px solid var(--line); text-align: left; white-space: nowrap; }
th { color: #aebdd1; }
.warning { border: 1px solid #6c5835; padding: 12px 14px; border-radius: 10px; margin-top: 14px; }
.chart { color: var(--green); }
.chart svg { width: 100%; height: 180px; }
.chart-note { color: var(--muted); font-size: 11px; margin-top: 8px; }
@media (max-width: 900px) {
  .grid, .two { grid-template-columns: 1fr 1fr; }
}
@media (max-width: 620px) {
  .grid, .two { grid-template-columns: 1fr; }
  .top { align-items: flex-start; flex-direction: column; }
}
</style>
"""


def _page(display_name: str) -> str:
    snapshot, positions, deals, error = _load_private()
    summary = review_summary(deals)
    captured_note = "No account snapshot"
    if snapshot is not None:
        age = datetime.now(UTC) - snapshot.captured_at.astimezone(UTC)
        captured_note = f"Snapshot age {max(age.total_seconds(), 0) / 60:.1f} min"

    current_streak = "None"
    if summary.current_streak:
        current_streak = f"{summary.current_streak} {summary.current_streak_kind.lower()}"

    owner = escape(display_name or "Owner")
    warning = f"<div class='warning'>{escape(error)}</div>" if error else ""
    account_label = snapshot.account_name if snapshot is not None else "Not synced"
    return "".join(
        [
            "<!doctype html><html lang='en'><head><meta charset='utf-8'>",
            "<meta name='viewport' content='width=device-width,initial-scale=1'>",
            "<meta name='robots' content='noindex,nofollow'>",
            "<title>Cakrawala Forex Review</title>",
            _styles(),
            "</head><body><main>",
            "<div class='top'><div><div class='eyebrow'>SUMMARY ANALYTICS</div>",
            "<h1>Forex Review Workspace</h1>",
            f"<div class='muted'>Verified owner: {owner}</div></div>",
            "<div><a href='/personal/forex'>Command Center</a> | ",
            "<a href='/personal/ai-lab'>AI Lab</a> | <a href='/logout'>Logout</a></div></div>",
            warning,
            "<div class='grid'>",
            _metric("Account", account_label, captured_note),
            _metric("Open positions", str(len(positions)), "Latest synchronized snapshot"),
            _metric("Average hold", _number(summary.average_hold_minutes, 0) + " min"),
            _metric("Current streak", current_streak, "Closed trades only"),
            _metric("Best trade", _money(summary.best_trade)),
            _metric("Worst trade", _money(summary.worst_trade)),
            _metric("Longest win streak", str(summary.longest_win_streak)),
            _metric("Longest loss streak", str(summary.longest_loss_streak)),
            "</div>",
            "<div class='panel'><h2>Open positions</h2>",
            _positions_table(positions),
            "</div>",
            "<div class='panel'><h2>Cumulative closed-trade equity</h2>",
            _equity_svg(deals),
            "</div>",
            "<div class='two'><div class='panel'><h2>Performance by symbol</h2>",
            _group_table(performance_by_symbol(deals)),
            "</div><div class='panel'><h2>Performance by side</h2>",
            _group_table(performance_by_side(deals)),
            "</div></div>",
            "<div class='two'><div class='panel'><h2>Performance by weekday</h2>",
            _group_table(performance_by_weekday(deals)),
            "</div><div class='panel'><h2>Performance by UTC close hour</h2>",
            _group_table(performance_by_hour_utc(deals)),
            "</div></div>",
            "</main></body></html>",
        ]
    )


def install_personal_forex_review_route(server: Flask) -> None:
    @server.get("/personal/forex/review")
    def personal_forex_review() -> Any:
        if not bool(session.get("owner_verified", False)):
            return redirect("/login")
        display_name = str(session.get("display_name", "")).strip()
        response = Response(_page(display_name), mimetype="text/html")
        response.headers["Cache-Control"] = "no-store"
        response.headers["X-Robots-Tag"] = "noindex, nofollow"
        response.headers["Referrer-Policy"] = "no-referrer"
        response.headers["X-Frame-Options"] = "DENY"
        return response
