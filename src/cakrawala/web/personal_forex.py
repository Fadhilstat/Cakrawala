from __future__ import annotations

import calendar
import os
from datetime import UTC, date, datetime, timedelta
from html import escape
from typing import Any

from flask import Flask, Response, redirect, session

from cakrawala.data.providers.bls_calendar import fetch_bls_calendar
from cakrawala.data.providers.cftc import fetch_tff_market
from cakrawala.data.providers.ecb_fx import fetch_forex_pairs
from cakrawala.data.providers.news_feeds import fetch_macro_news
from cakrawala.intelligence.sessions import current_sessions
from cakrawala.personal.forex_analytics import (
    AccountSnapshot,
    ForexDeal,
    daily_pnl,
    performance_summary,
    pnl_by_symbol,
)

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


def _money(value: float | None) -> str:
    return "N/A" if value is None else f"${value:+,.2f}"


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


def _metric(label: str, value: str, note: str = "", tone: str = "") -> str:
    tone_class = f" {tone}" if tone else ""
    return (
        f"<div class='metric{tone_class}'><div class='metric-label'>{escape(label)}</div>"
        f"<div class='metric-value'>{escape(value)}</div>"
        f"<div class='metric-note'>{escape(note)}</div></div>"
    )


def _pair_section(errors: list[str]) -> tuple[str, list[str]]:
    try:
        result = fetch_forex_pairs()
    except Exception as exc:
        errors.append(f"ECB FX: {type(exc).__name__}")
        return "<p class='warning'>ECB reference-rate data is unavailable.</p>", []

    rows = []
    pairs = []
    for item in result.data:
        pairs.append(item.pair)
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
    return _table(["Pair", "Reference", "1D", "5D", "20D", "As of"], rows), pairs


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
        [
            "Currency",
            "Report",
            "Asset mgr net",
            "Weekly change",
            "Lev funds net",
            "Weekly change",
        ],
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


def _session_section() -> tuple[str, str]:
    sessions = current_sessions()
    rows = [
        [item.name, item.timezone, str(item.local_hour), "OPEN" if item.is_open else "CLOSED"]
        for item in sessions
    ]
    active = [item.name for item in sessions if item.is_open]
    label = ", ".join(active) if active else "Between core sessions"
    return _table(["Session", "Timezone", "Local hour", "State"], rows), label


def _load_private_command_center(
    errors: list[str],
) -> tuple[AccountSnapshot | None, list[ForexDeal]]:
    database_url = os.environ.get("DATABASE_PERSONAL_URL", "").strip()
    owner_sub = str(session.get("owner_id", "")).strip()
    if not database_url:
        return None, []
    try:
        from cakrawala.personal.forex_storage import (
            latest_account_snapshot,
            list_forex_deals,
        )

        return (
            latest_account_snapshot(database_url, owner_sub),
            list_forex_deals(database_url, owner_sub, limit=250),
        )
    except Exception as exc:
        errors.append(f"Private forex storage: {type(exc).__name__}")
        return None, []


def _account_metrics(snapshot: AccountSnapshot | None, deals: list[ForexDeal]) -> str:
    performance = performance_summary(deals)
    today = datetime.now(UTC).date()
    today_pnl = daily_pnl(deals).get(today, 0.0)
    if snapshot is None:
        return "".join(
            [
                _metric("Balance", "Not synced", "Private snapshot required"),
                _metric("Equity", "Not synced", "No fabricated broker value"),
                _metric("Floating P/L", "Not synced", "Read-only bridge planned"),
                _metric("Today P/L", _money(today_pnl), "Closed deals, UTC day"),
            ]
        )
    margin = (
        f"Margin {snapshot.margin_level_percent:,.0f}%"
        if snapshot.margin_level_percent is not None
        else "Margin unavailable"
    )
    pnl_tone = "positive" if snapshot.floating_pnl >= 0 else "negative"
    today_tone = "positive" if today_pnl >= 0 else "negative"
    return "".join(
        [
            _metric("Current balance", f"${snapshot.balance:,.2f}", snapshot.account_name),
            _metric("Current equity", f"${snapshot.equity:,.2f}", margin),
            _metric("Floating P/L", _money(snapshot.floating_pnl), "Latest snapshot", pnl_tone),
            _metric("Today P/L", _money(today_pnl), "Closed deals, UTC day", today_tone),
        ]
    )


def _performance_metrics(deals: list[ForexDeal]) -> str:
    performance = performance_summary(deals)
    return "".join(
        [
            _metric("Closed trades", str(performance.total_closed), "Imported history"),
            _metric(
                "Win rate",
                _pct(performance.win_rate_percent),
                f"{performance.winners} win / {performance.losers} loss",
            ),
            _metric(
                "Profit factor",
                _number(performance.profit_factor),
                "Gross profit / absolute gross loss",
            ),
            _metric("Expectancy", _money(performance.expectancy), "Average net P/L per trade"),
            _metric("Average R", _number(performance.average_r), "Only deals with R recorded"),
            _metric("Max drawdown", f"${performance.max_drawdown:,.2f}", "Closed-deal equity curve"),
        ]
    )


def _trade_history(deals: list[ForexDeal]) -> str:
    if not deals:
        return (
            "<p class='muted'>No private forex deal history is synced yet. "
            "The terminal intentionally shows an empty state instead of sample trades.</p>"
        )
    rows = []
    for deal in deals[:60]:
        status = "CLOSED" if deal.closed_at else "OPEN"
        result = _money(deal.net_pnl) if deal.closed_at else "Floating not stored"
        rows.append(
            [
                deal.symbol,
                deal.side,
                _number(deal.volume, 2),
                _number(deal.entry_price, 5),
                _number(deal.exit_price, 5),
                status,
                result,
                deal.opened_at.isoformat(),
                deal.closed_at.isoformat() if deal.closed_at else "Active",
            ]
        )
    return _table(
        ["Symbol", "Side", "Lots", "Entry", "Exit", "Status", "Net P/L", "Open", "Close"],
        rows,
    )


def _pnl_calendar(deals: list[ForexDeal]) -> str:
    totals = daily_pnl(deals)
    today = datetime.now(UTC).date()
    year = today.year
    month = today.month
    cal = calendar.Calendar(firstweekday=0)
    weeks = cal.monthdatescalendar(year, month)
    weekday_headers = "".join(f"<th>{name}</th>" for name in ("Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"))
    body_rows = []
    for week in weeks:
        cells = []
        for day in week:
            if day.month != month:
                cells.append("<td class='calendar-cell outside'></td>")
                continue
            value = totals.get(day)
            tone = ""
            pnl = ""
            if value is not None:
                tone = " gain" if value >= 0 else " loss"
                pnl = f"<strong>{escape(_money(value))}</strong>"
            cells.append(
                f"<td class='calendar-cell{tone}'><span>{day.day}</span>{pnl}</td>"
            )
        body_rows.append("<tr>" + "".join(cells) + "</tr>")
    title = f"{calendar.month_name[month]} {year}"
    return (
        f"<div class='calendar-title'>{escape(title)}</div>"
        "<div class='table-wrap'><table class='calendar'><thead><tr>"
        + weekday_headers
        + "</tr></thead><tbody>"
        + "".join(body_rows)
        + "</tbody></table></div>"
    )


def _symbol_breakdown(deals: list[ForexDeal]) -> str:
    values = pnl_by_symbol(deals)
    if not values:
        return "<p class='muted'>Symbol performance appears after closed deals are synced.</p>"
    rows = [[symbol, _money(value)] for symbol, value in values.items()]
    return _table(["Symbol", "Net P/L"], rows)


def _pair_chips(pairs: list[str]) -> str:
    if not pairs:
        return "<span class='chip muted-chip'>ECB board unavailable</span>"
    return "".join(f"<span class='chip'>{escape(pair)} ONLINE</span>" for pair in pairs[:10])


def _page(display_name: str) -> str:
    errors: list[str] = []
    pairs_table, pairs = _pair_section(errors)
    positioning = _cot_section(errors)
    events = _events_section(errors)
    news = _news_section(errors)
    sessions, active_session = _session_section()
    snapshot, deals = _load_private_command_center(errors)

    error_note = ""
    if errors:
        error_note = (
            "<div class='warning'><strong>Partial source availability:</strong> "
            + escape(", ".join(errors))
            + "</div>"
        )

    owner = escape(display_name or "Owner")
    parts = [
        "<!doctype html>",
        '<html lang="en">',
        "<head>",
        '<meta charset="utf-8">',
        '<meta name="viewport" content="width=device-width, initial-scale=1">',
        '<meta name="robots" content="noindex,nofollow">',
        "<title>Cakrawala Personal Forex Command Center</title>",
        "<style>",
        ":root{color-scheme:dark;--bg:#080d15;--panel:#101827;--line:#223047;",
        "--text:#eef4fb;--muted:#91a2b8;--cyan:#65c7ff;--green:#4de0a6;",
        "--red:#ff7f91;--amber:#f6c66d}",
        "*{box-sizing:border-box}body{font-family:Inter,system-ui,sans-serif;background:var(--bg);",
        "color:var(--text);margin:0}main{max-width:1480px;margin:auto;padding:22px 22px 60px}",
        "a{color:var(--cyan)}.top{display:flex;justify-content:space-between;gap:18px;",
        "align-items:center;padding-bottom:18px;border-bottom:1px solid var(--line)}",
        ".eyebrow{font-size:11px;letter-spacing:.14em;color:var(--cyan);font-weight:800}",
        "h1{margin:5px 0 3px;font-size:28px}h2{font-size:17px;margin:0 0 14px}",
        ".muted{color:var(--muted);line-height:1.5}.status{border:1px solid rgba(77,224,166,.3);",
        "background:rgba(77,224,166,.08);color:var(--green);border-radius:999px;padding:7px 10px;",
        "font-size:11px;font-weight:800}.metric-grid{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));",
        "gap:12px;margin:16px 0}.metric{background:var(--panel);border:1px solid var(--line);",
        "border-radius:13px;padding:15px}.metric-label{color:var(--muted);font-size:11px}",
        ".metric-value{font-size:22px;font-weight:800;margin-top:7px}.metric-note{color:var(--muted);",
        "font-size:10px;margin-top:5px}.metric.positive .metric-value{color:var(--green)}",
        ".metric.negative .metric-value{color:var(--red)}.panel{background:var(--panel);",
        "border:1px solid var(--line);border-radius:14px;padding:17px;margin-top:14px}",
        ".grid{display:grid;grid-template-columns:minmax(0,1.35fr) minmax(340px,.85fr);gap:14px}",
        ".triple{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:14px}",
        ".pairbar{display:flex;gap:8px;align-items:center;overflow:auto;padding:10px 0}",
        ".chip{white-space:nowrap;border:1px solid rgba(77,224,166,.25);background:rgba(77,224,166,.07);",
        "color:var(--green);padding:6px 9px;border-radius:999px;font-size:10px;font-weight:800}",
        ".muted-chip{color:var(--muted);border-color:var(--line)}.warning{padding:12px 14px;",
        "background:rgba(246,198,109,.09);border:1px solid rgba(246,198,109,.3);",
        "border-radius:10px;margin:12px 0;color:#f7d99c}.table-wrap{overflow:auto}",
        "table{width:100%;border-collapse:collapse;font-size:12px}th,td{padding:9px 7px;",
        "border-bottom:1px solid var(--line);text-align:left;white-space:nowrap}th{color:#aebdd1}",
        ".news-card{padding:9px 0;border-bottom:1px solid var(--line)}.source{font-size:10px;",
        "color:var(--muted);margin-bottom:3px}.calendar-title{font-weight:800;margin-bottom:9px}",
        ".calendar th{text-align:center}.calendar-cell{height:70px;min-width:72px;vertical-align:top;",
        "background:#0c1421}.calendar-cell span{display:block;color:var(--muted);margin-bottom:8px}",
        ".calendar-cell.gain{background:rgba(77,224,166,.08)}.calendar-cell.loss{background:rgba(255,127,145,.08)}",
        ".calendar-cell.gain strong{color:var(--green)}.calendar-cell.loss strong{color:var(--red)}",
        ".calendar-cell.outside{opacity:.28}.notice{line-height:1.55}",
        "@media(max-width:1050px){.metric-grid{grid-template-columns:repeat(2,1fr)}",
        ".grid,.triple{grid-template-columns:1fr}}@media(max-width:620px){main{padding:16px 14px 40px}",
        ".top{align-items:flex-start;flex-direction:column}.metric-grid{grid-template-columns:1fr 1fr}}",
        "</style>",
        "</head>",
        "<body><main>",
        '<div class="top"><div><div class="eyebrow">OWNER-ONLY FX RESEARCH WORKSPACE</div>',
        '<h1>Forex Command Center</h1>',
        f'<div class="muted">Verified owner: {owner}</div></div>',
        f'<div><span class="status">{escape(active_session)} SESSION</span> &nbsp; ',
        '<a href="/personal/ai-lab">AI Lab</a> &nbsp; <a href="/">Terminal</a> &nbsp; ',
        '<a href="/logout">Logout</a></div></div>',
        '<div class="metric-grid">',
        _account_metrics(snapshot, deals),
        "</div>",
        '<div class="panel"><div class="eyebrow">MONITORED FX BOARD</div><div class="pairbar">',
        _pair_chips(pairs),
        "</div></div>",
        error_note,
        '<div class="panel"><h2>Trading performance snapshot</h2><div class="metric-grid">',
        _performance_metrics(deals),
        "</div></div>",
        '<div class="grid"><div class="panel"><h2>Executed trade history and outcomes</h2>',
        _trade_history(deals),
        '</div><div class="panel"><h2>Daily P/L calendar</h2>',
        _pnl_calendar(deals),
        "</div></div>",
        '<div class="grid"><div class="panel"><h2>G10 reference board</h2>',
        '<p class="muted">Official ECB daily reference rates. These are context prices, not broker quotes.</p>',
        pairs_table,
        '</div><div class="panel"><h2>P/L by symbol</h2>',
        _symbol_breakdown(deals),
        "</div></div>",
        '<div class="triple"><div class="panel"><h2>Market sessions</h2>',
        sessions,
        '</div><div class="panel"><h2>Upcoming U.S. macro risk</h2>',
        events,
        '</div><div class="panel"><h2>Workflow boundary</h2><p class="notice muted">',
        "Cakrawala is a decision-support and review layer. Broker execution remains manual. ",
        "Live balance and trade history appear only after private read-only snapshots are synced. ",
        "No broker password is stored in this web application.</p></div></div>",
        '<div class="panel"><h2>CFTC currency positioning</h2>',
        '<p class="muted">Weekly futures positioning. Use it as positioning context, not live order flow.</p>',
        positioning,
        "</div>",
        '<div class="panel"><h2>Official macro and central-bank headlines</h2>',
        news,
        "</div>",
        '<div class="panel notice"><strong>Pre-trade discipline:</strong> ',
        "confirm broker price, spread and liquidity; check event risk; write thesis and invalidation; ",
        "size risk before entry; avoid trading when evidence conflicts; record the outcome in the private journal.",
        "</div>",
        "</main></body></html>",
    ]
    return "".join(parts)


def install_personal_forex_route(server: Flask) -> None:
    @server.get("/personal/forex")
    def personal_forex() -> Any:
        if not bool(session.get("owner_verified", False)):
            return redirect("/login")
        display_name = str(session.get("display_name", "")).strip()
        response = Response(_page(display_name), mimetype="text/html")
        response.headers["Cache-Control"] = "no-store"
        response.headers["X-Robots-Tag"] = "noindex, nofollow"
        response.headers["Referrer-Policy"] = "no-referrer"
        response.headers["X-Frame-Options"] = "DENY"
        return response
