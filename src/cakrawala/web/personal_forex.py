from __future__ import annotations

from datetime import UTC, datetime, timedelta
from html import escape
from typing import Any

from flask import Flask, Response, redirect, session

from cakrawala.data.providers.bls_calendar import fetch_bls_calendar
from cakrawala.data.providers.cftc import fetch_tff_market
from cakrawala.data.providers.ecb_fx import fetch_forex_pairs
from cakrawala.data.providers.news_feeds import fetch_macro_news
from cakrawala.intelligence.sessions import current_sessions

CURRENCY_FUTURES = (
    ("EUR", "EURO FX"),
    ("GBP", "BRITISH POUND STERLING"),
    ("JPY", "JAPANESE YEN"),
    ("CHF", "SWISS FRANC"),
    ("AUD", "AUSTRALIAN DOLLAR"),
    ("CAD", "CANADIAN DOLLAR"),
    ("NZD", "NZ DOLLAR"),
)


def _pct(value: float | None) -> str:
    return "N/A" if value is None else f"{value:+.2f}%"


def _number(value: float | None, digits: int = 2) -> str:
    return "N/A" if value is None else f"{value:,.{digits}f}"


def _table(headers: list[str], rows: list[list[str]]) -> str:
    head = "".join(f"<th>{escape(item)}</th>" for item in headers)
    body = "".join(
        "<tr>" + "".join(f"<td>{escape(cell)}</td>" for cell in row) + "</tr>"
        for row in rows
    )
    return (
        "<div class='table-wrap'><table><thead><tr>"
        f"{head}</tr></thead><tbody>{body}</tbody></table></div>"
    )


def _pair_section(errors: list[str]) -> str:
    try:
        result = fetch_forex_pairs()
    except Exception as exc:
        errors.append(f"ECB FX: {type(exc).__name__}")
        return "<p class='warning'>ECB reference-rate data is unavailable.</p>"

    rows = []
    for item in result.data:
        rows.append(
            [
                item.pair,
                f"{item.rate:.5f}",
                _pct(item.change_1d_pct),
                _pct(item.change_5d_pct),
                _pct(item.change_20d_pct),
                item.as_of.isoformat(),
            ]
        )
    return _table(["Pair", "Reference", "1D", "5D", "20D", "As of"], rows)


def _cot_section(errors: list[str]) -> str:
    rows: list[list[str]] = []
    for currency, market in CURRENCY_FUTURES:
        try:
            result = fetch_tff_market(market)
        except Exception as exc:
            errors.append(f"CFTC {currency}: {type(exc).__name__}")
            continue
        latest = result.data[0]
        previous = result.data[1] if len(result.data) > 1 else None
        asset_change = (
            latest.asset_manager_net - previous.asset_manager_net if previous else None
        )
        leveraged_change = (
            latest.leveraged_funds_net - previous.leveraged_funds_net if previous else None
        )
        rows.append(
            [
                currency,
                latest.report_date.date().isoformat(),
                _number(latest.asset_manager_net, 0),
                _number(asset_change, 0),
                _number(latest.leveraged_funds_net, 0),
                _number(leveraged_change, 0),
            ]
        )
    if not rows:
        return "<p class='warning'>CFTC currency positioning is unavailable.</p>"
    return _table(
        ["Currency", "Report", "Asset mgr net", "Weekly change", "Lev funds net", "Weekly change"],
        rows,
    )


def _events_section(errors: list[str]) -> str:
    try:
        result = fetch_bls_calendar()
    except Exception as exc:
        errors.append(f"BLS calendar: {type(exc).__name__}")
        return "<p class='warning'>BLS event calendar is unavailable.</p>"
    now = datetime.now(UTC)
    cutoff = now + timedelta(days=10)
    rows = [
        [event.starts_at.isoformat(), event.title]
        for event in result.data
        if now <= event.starts_at <= cutoff
    ][:12]
    if not rows:
        return "<p class='muted'>No BLS release is scheduled in the next 10 days.</p>"
    return _table(["Time UTC", "Official event"], rows)


def _news_section(errors: list[str]) -> str:
    try:
        items = fetch_macro_news(limit_per_source=5)
    except Exception as exc:
        errors.append(f"Macro news: {type(exc).__name__}")
        return "<p class='warning'>Official macro news feeds are unavailable.</p>"
    cards = []
    for item in items[:12]:
        published = item.published_at.isoformat() if item.published_at else "time unavailable"
        cards.append(
            "<article class='news-card'>"
            f"<div class='source'>{escape(item.source)} | {escape(published)}</div>"
            f"<a href='{escape(item.link)}' rel='noopener noreferrer' target='_blank'>"
            f"{escape(item.title)}</a>"
            "</article>"
        )
    return "".join(cards)


def _session_section() -> str:
    rows = [
        [item.name, item.timezone, str(item.local_hour), "OPEN" if item.is_open else "CLOSED"]
        for item in current_sessions()
    ]
    return _table(["Session", "Timezone", "Local hour", "State"], rows)


def _page(display_name: str) -> str:
    errors: list[str] = []
    pairs = _pair_section(errors)
    positioning = _cot_section(errors)
    events = _events_section(errors)
    news = _news_section(errors)
    sessions = _session_section()
    error_note = ""
    if errors:
        error_note = (
            "<div class='warning'><strong>Partial source availability:</strong> "
            + escape(", ".join(errors))
            + "</div>"
        )

    owner = escape(display_name or "Google identity")
    parts = [
        "<!doctype html>",
        '<html lang="en">',
        "<head>",
        '<meta charset="utf-8">',
        '<meta name="viewport" content="width=device-width, initial-scale=1">',
        "<title>Cakrawala Personal Forex Desk</title>",
        "<style>",
        "body{font-family:Inter,system-ui,sans-serif;background:#0b1020;",
        "color:#edf2f7;margin:0}",
        "main{max-width:1240px;margin:auto;padding:28px 22px 60px}",
        "a{color:#8cc8ff}",
        ".top{display:flex;justify-content:space-between;gap:18px;align-items:center}",
        ".eyebrow{font-size:12px;letter-spacing:.14em;color:#9fb0c7}",
        "h1{margin:6px 0 4px}",
        ".muted{color:#9fb0c7}",
        ".warning{padding:12px 14px;background:#2b2130;border-radius:10px;margin:12px 0}",
        ".grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(360px,1fr));gap:16px}",
        ".panel{background:#121a2b;border:1px solid #253047;border-radius:14px;",
        "padding:18px;margin-top:16px}",
        ".table-wrap{overflow:auto}",
        "table{width:100%;border-collapse:collapse;font-size:13px}",
        "th,td{padding:10px 8px;border-bottom:1px solid #253047;text-align:left;",
        "white-space:nowrap}",
        "th{color:#aebdd1}",
        ".news-card{padding:10px 0;border-bottom:1px solid #253047}",
        ".source{font-size:12px;color:#91a2bb;margin-bottom:4px}",
        ".notice{line-height:1.55}",
        "</style>",
        "</head>",
        "<body><main>",
        '<div class="top"><div><div class="eyebrow">OWNER-ONLY FOREX INTELLIGENCE</div>',
        '<h1>Personal Forex Desk</h1>',
        f'<div class="muted">Verified owner: {owner}</div></div>',
        '<div><a href="/">Terminal</a> &nbsp; ',
        '<a href="/logout">Logout</a></div></div>',
        '<div class="panel notice"><strong>Research workflow.</strong> ',
        "ECB values are official daily reference rates, not executable broker prices. ",
        "CFTC data is weekly. The private Daily Forex Council adds scenario analysis ",
        "each morning in ChatGPT. Orders remain manual and broker-side.</div>",
        error_note,
        '<div class="panel"><h2>G10 pair reference board</h2>',
        pairs,
        "</div>",
        '<div class="grid"><div class="panel"><h2>Market sessions</h2>',
        sessions,
        '</div><div class="panel"><h2>Upcoming U.S. macro risk</h2>',
        events,
        "</div></div>",
        '<div class="panel"><h2>CFTC currency positioning</h2>',
        '<p class="muted">Weekly futures positioning. ',
        "Use as context, not a live flow signal.</p>",
        positioning,
        "</div>",
        '<div class="panel"><h2>Official macro and central-bank headlines</h2>',
        news,
        "</div>",
        '<div class="panel notice"><strong>Pre-trade discipline:</strong> ',
        "confirm broker price, spread and liquidity; check event risk; write thesis and ",
        "invalidation; size risk before entry; avoid trading when evidence conflicts; ",
        "record the outcome in the private journal.</div>",
        "</main></body></html>",
    ]
    return "".join(parts)


def install_personal_forex_route(server: Flask) -> None:
    @server.get("/personal/forex")
    def personal_forex() -> Any:
        if not bool(session.get("owner_verified", False)):
            return redirect("/login")
        display_name = str(session.get("display_name", "")).strip()
        return Response(_page(display_name), mimetype="text/html")
