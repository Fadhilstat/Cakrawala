from __future__ import annotations

import os
from dataclasses import asdict
from pathlib import Path
from typing import Any

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import yaml
from dash import Dash, Input, Output, State, callback, dash_table, dcc, html
from flask import jsonify

from cakrawala.config import load_yaml
from cakrawala.intelligence.ai_council import load_council_brief
from cakrawala.intelligence.execution_guard import (
    ExecutionEvidence,
    assess_execution_readiness,
)
from cakrawala.intelligence.risk import build_position_plan, expectancy_r
from cakrawala.web.auth import install_owner_auth, owner_session_state
from cakrawala.web.cache import PUBLIC_CACHE
from cakrawala.web.public_service import (
    load_cot_context,
    load_currency_strength,
    load_economic_calendar,
    load_futures_context,
    load_macro_indicator,
    load_market_history,
    load_news,
    market_risk_stats,
    public_snapshot,
)

ROOT = Path(__file__).resolve().parents[1]
ASSETS = Path(__file__).resolve().parent / "assets"

app = Dash(
    __name__,
    assets_folder=str(ASSETS),
    suppress_callback_exceptions=True,
    title="Cakrawala Intelligence Terminal",
)
server = app.server
auth_config = install_owner_auth(server)


@server.get("/healthz")
def healthz() -> Any:
    return jsonify({"status": "ok", "service": "cakrawala-dash"})


def _metric(label: str, value: str, note: str = "") -> html.Div:
    children: list[Any] = [
        html.Div(label, className="metric-label"),
        html.Div(value, className="metric-value"),
    ]
    if note:
        children.append(html.Div(note, className="metric-note"))
    return html.Div(children, className="metric-card")


def _panel(title: str, children: Any, note: str | None = None) -> html.Div:
    body: list[Any] = [html.H3(title), children]
    if note:
        body.append(html.P(note, className="muted"))
    return html.Div(body, className="panel")


def _warning(message: str) -> html.Div:
    return html.Div(message, className="warning-box")


def _safe_number(value: float | None, suffix: str = "", digits: int = 2) -> str:
    if value is None:
        return "N/A"
    return f"{value:,.{digits}f}{suffix}"


def _source_health(snapshot: dict[str, Any]) -> tuple[int, int]:
    names = (
        "earthquake",
        "population",
        "gdp",
        "inflation",
        "market",
        "news",
        "futures",
        "calendar",
        "cot",
        "currency_strength",
    )
    healthy = sum(snapshot.get(name) is not None for name in names)
    return healthy, len(names)


def render_overview() -> html.Div:
    snapshot = public_snapshot()
    healthy, total = _source_health(snapshot)
    market = snapshot.get("market")
    earthquake = snapshot.get("earthquake")
    inflation = snapshot.get("inflation")
    futures = snapshot.get("futures")
    risk = market_risk_stats(market["frame"]) if market else {}

    long_share = None
    funding = None
    if futures:
        long_share = float(futures["latest"].get("long_account", 0)) * 100
        funding = float(futures["latest"].get("last_funding_rate", 0)) * 100

    cards = html.Div(
        [
            _metric("Sources online", f"{healthy}/{total}"),
            _metric(
                "BTC 1D",
                _safe_number(market["latest"]["change_1d_pct"], "%")
                if market
                else "N/A",
            ),
            _metric("30D momentum", _safe_number(risk.get("momentum"), "%")),
            _metric("30D volatility", _safe_number(risk.get("volatility"), "%", 1)),
            _metric("Crowd long", _safe_number(long_share, "%", 1)),
            _metric("Funding", _safe_number(funding, "%", 4)),
        ],
        className="metric-grid",
    )

    market_panel: Any
    if market:
        frame = market["frame"].tail(45)
        fig = px.line(frame, x="time", y="close")
        fig.update_layout(
            template="plotly_dark",
            height=330,
            margin=dict(l=10, r=10, t=20, b=10),
        )
        market_panel = dcc.Graph(figure=fig, config={"displayModeBar": False})
    else:
        market_panel = _warning("Market evidence sedang tidak tersedia.")

    context: list[Any] = []
    if earthquake:
        context.append(
            html.P(
                f"BMKG: M {earthquake.get('magnitude', 'N/A')} | "
                f"{earthquake.get('region', 'N/A')}"
            )
        )
    if inflation:
        latest = inflation["latest"]
        context.append(
            html.P(f"Inflasi Indonesia: {latest['value']:.2f}% ({latest['year']})")
        )
    if snapshot["errors"]:
        context.append(
            html.P(
                "Sebagian source gagal. Terminal tidak menggantinya dengan data sintetis.",
                className="muted",
            )
        )

    return html.Div(
        [
            html.Div(
                [
                    html.P("COMMAND CENTER", className="eyebrow"),
                    html.H2("Market and evidence pulse"),
                ]
            ),
            cards,
            html.Div(
                [
                    _panel("Market pulse", market_panel),
                    _panel("Indonesia context", context or html.P("Evidence belum cukup.")),
                ],
                className="two-column",
            ),
        ]
    )


def render_news() -> html.Div:
    try:
        rows = load_news()
    except Exception as exc:
        return _warning(f"News evidence belum tersedia: {type(exc).__name__}")

    records = []
    for item in rows[:40]:
        records.append(
            {
                "Source": item.get("source", ""),
                "Headline": item.get("title", ""),
                "Attention": item.get("attention_score", 0),
                "Theme": ", ".join(item.get("tags", [])),
                "Why watch": item.get("watch_reason", ""),
                "URL": item.get("link", ""),
            }
        )
    columns = []
    if records:
        columns = [
            {
                "name": key,
                "id": key,
                "presentation": "markdown" if key == "URL" else "input",
            }
            for key in records[0]
        ]
    return html.Div(
        [
            html.P("NEWS INTELLIGENCE", className="eyebrow"),
            html.H2("Official headline watch"),
            html.P(
                "Attention score membantu prioritas membaca. Ini bukan sentiment forecast "
                "dan bukan arah transaksi.",
                className="muted",
            ),
            dash_table.DataTable(
                data=records,
                columns=columns,
                page_size=12,
                sort_action="native",
                filter_action="native",
                style_table={"overflowX": "auto"},
                style_cell={
                    "textAlign": "left",
                    "whiteSpace": "normal",
                    "height": "auto",
                },
            ),
        ]
    )


def render_positioning() -> html.Div:
    children: list[Any] = [
        html.P("POSITIONING", className="eyebrow"),
        html.H2("Crowd and institutional context"),
    ]
    try:
        futures = load_futures_context()
    except Exception as exc:
        children.append(_warning(f"Futures crowding belum tersedia: {type(exc).__name__}"))
    else:
        latest = futures["latest"]
        children.append(
            html.Div(
                [
                    _metric(
                        "Crowd long",
                        _safe_number(float(latest["long_account"]) * 100, "%", 1),
                    ),
                    _metric(
                        "Crowd short",
                        _safe_number(float(latest["short_account"]) * 100, "%", 1),
                    ),
                    _metric(
                        "Long/short ratio",
                        _safe_number(float(latest["long_short_ratio"]), "", 2),
                    ),
                    _metric(
                        "Open interest",
                        _safe_number(float(latest["open_interest"]), "", 0),
                    ),
                    _metric(
                        "Funding",
                        _safe_number(float(latest["last_funding_rate"]) * 100, "%", 4),
                    ),
                ],
                className="metric-grid",
            )
        )

    try:
        cot = load_cot_context()
    except Exception as exc:
        children.append(_warning(f"CFTC positioning belum tersedia: {type(exc).__name__}"))
    else:
        frame = pd.DataFrame(cot)
        columns = [
            column
            for column in (
                "market_name",
                "report_date",
                "asset_manager_net",
                "asset_manager_change",
                "leveraged_funds_net",
                "leveraged_funds_change",
            )
            if column in frame.columns
        ]
        table = dash_table.DataTable(
            data=frame[columns].to_dict("records"),
            columns=[
                {"name": column.replace("_", " ").title(), "id": column}
                for column in columns
            ],
            style_table={"overflowX": "auto"},
        )
        children.append(_panel("Institutional COT", table))
        children.append(
            html.P(
                "COT adalah evidence mingguan, bukan live institutional flow.",
                className="muted",
            )
        )
    return html.Div(children)


def render_market() -> html.Div:
    try:
        market = load_market_history("BTCUSDT", 90)
    except Exception as exc:
        return _warning(f"Market structure belum tersedia: {type(exc).__name__}")
    frame = market["frame"]
    risk = market_risk_stats(frame)
    fig = go.Figure(
        data=[
            go.Candlestick(
                x=frame["time"],
                open=frame["open"],
                high=frame["high"],
                low=frame["low"],
                close=frame["close"],
            )
        ]
    )
    fig.update_layout(
        template="plotly_dark",
        height=500,
        xaxis_rangeslider_visible=False,
        margin=dict(l=10, r=10, t=20, b=10),
    )

    try:
        strength = pd.DataFrame(load_currency_strength())
    except Exception:
        strength_component: Any = _warning("ECB currency strength sedang tidak tersedia.")
    else:
        columns = [
            column
            for column in (
                "currency",
                "change_1d_pct",
                "change_5d_pct",
                "change_20d_pct",
                "as_of",
            )
            if column in strength.columns
        ]
        strength_component = dash_table.DataTable(
            data=strength[columns].to_dict("records"),
            columns=[
                {"name": column.replace("_", " ").title(), "id": column}
                for column in columns
            ],
            page_size=10,
        )

    return html.Div(
        [
            html.P("MARKET DESK", className="eyebrow"),
            html.H2("Structure, risk and currency context"),
            html.Div(
                [
                    _metric("BTC close", _safe_number(market["latest"]["close"])),
                    _metric(
                        "1D",
                        _safe_number(market["latest"]["change_1d_pct"], "%"),
                    ),
                    _metric("30D momentum", _safe_number(risk.get("momentum"), "%")),
                    _metric(
                        "30D volatility",
                        _safe_number(risk.get("volatility"), "%", 1),
                    ),
                    _metric("Drawdown", _safe_number(risk.get("drawdown"), "%")),
                ],
                className="metric-grid",
            ),
            _panel(
                "BTC/USDT 90D",
                dcc.Graph(figure=fig, config={"displayModeBar": False}),
            ),
            _panel(
                "ECB currency strength",
                strength_component,
                "Reference-rate context only. Bukan executable FX pricing.",
            ),
        ]
    )


def render_macro() -> html.Div:
    rows: list[dict[str, Any]] = []
    for label, indicator in (
        ("Population", "SP.POP.TOTL"),
        ("GDP growth", "NY.GDP.MKTP.KD.ZG"),
        ("Inflation", "FP.CPI.TOTL.ZG"),
    ):
        try:
            payload = load_macro_indicator(indicator)
        except Exception:
            continue
        for item in payload["observations"]:
            rows.append(
                {"Series": label, "Year": item["year"], "Value": item["value"]}
            )

    chart: Any = _warning("Macro history belum tersedia.")
    if rows:
        frame = pd.DataFrame(rows)
        pct = frame[frame["Series"].isin(["GDP growth", "Inflation"])]
        fig = px.line(pct, x="Year", y="Value", color="Series", markers=True)
        fig.update_layout(
            template="plotly_dark",
            height=380,
            margin=dict(l=10, r=10, t=20, b=10),
        )
        chart = dcc.Graph(figure=fig, config={"displayModeBar": False})

    try:
        events = load_economic_calendar(14)
    except Exception as exc:
        event_component: Any = _warning(
            f"Event calendar belum tersedia: {type(exc).__name__}"
        )
    else:
        event_rows = [
            {"Event": item.get("title", ""), "Time": str(item.get("starts_at", ""))}
            for item in events
        ]
        event_component = dash_table.DataTable(
            data=event_rows,
            columns=[{"name": key, "id": key} for key in ("Event", "Time")],
            page_size=10,
        )

    return html.Div(
        [
            html.P("MACRO AND EVENTS", className="eyebrow"),
            html.H2("Indonesia context and scheduled risk"),
            _panel("Indonesia macro history", chart),
            _panel("Upcoming BLS releases", event_component),
        ]
    )


def render_ai_council() -> html.Div:
    try:
        brief = load_council_brief(ROOT / "data" / "ai_briefs" / "latest.json")
    except Exception as exc:
        return _warning(f"AI Research Council brief belum valid: {type(exc).__name__}")

    cards = html.Div(
        [
            _metric("Freshness", "FRESH" if brief.is_fresh() else "STALE"),
            _metric("Research stance", brief.research_stance),
            _metric("Analysts", str(len(brief.roles))),
            _metric("Verified sources", str(brief.source_count)),
        ],
        className="metric-grid",
    )
    analyst_cards = []
    for role in brief.roles:
        analyst_cards.append(
            html.Div(
                [
                    html.H4(role.role),
                    html.Span(role.confidence.upper(), className="status-chip"),
                    html.P(role.summary),
                    html.P(
                        "Evidence: " + "; ".join(role.evidence),
                        className="muted",
                    )
                    if role.evidence
                    else None,
                    html.P(
                        "Risks: " + "; ".join(role.risks),
                        className="muted",
                    )
                    if role.risks
                    else None,
                ],
                className="analyst-card",
            )
        )
    return html.Div(
        [
            html.P("AI RESEARCH COUNCIL", className="eyebrow"),
            html.H2("Multi-role research synthesis"),
            cards,
            _panel(
                "Chief editor",
                html.Div(
                    [
                        html.H4(brief.headline),
                        html.P(brief.signal_policy_note, className="muted"),
                    ]
                ),
            ),
            html.Div(analyst_cards, className="analyst-grid"),
        ]
    )


def _tool_radar_rows() -> list[dict[str, str]]:
    path = ROOT / "configs" / "tool_radar.yaml"
    payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    rows = []
    for item in payload.get("items", []):
        rows.append(
            {
                "Tool": str(item.get("name", "")),
                "Category": str(item.get("category", "")),
                "Status": str(item.get("status", "")),
                "Latest verified activity": str(
                    item.get("latest_verified_activity", "")
                ),
                "Source": str(item.get("source", "")),
            }
        )
    return rows


def render_tool_radar() -> html.Div:
    rows = _tool_radar_rows()
    return html.Div(
        [
            html.P("TOOL RADAR", className="eyebrow"),
            html.H2("Open trading architecture watch"),
            html.P(
                "Framework baru hanya masuk observe atau sandbox. "
                "Tidak ada auto-install ke production.",
                className="muted",
            ),
            dash_table.DataTable(
                data=rows,
                columns=[{"name": key, "id": key} for key in rows[0]] if rows else [],
                page_size=10,
                style_table={"overflowX": "auto"},
            ),
        ]
    )


def render_personal() -> html.Div:
    if auth_config is None:
        return html.Div(
            [
                html.P("PRIVATE WORKSPACE", className="eyebrow"),
                html.H2("Personal Mode"),
                _warning(
                    "OIDC belum dikonfigurasi di Render. Personal Mode tetap fail-closed."
                ),
            ]
        )

    state = owner_session_state()
    if not state["verified"]:
        return html.Div(
            [
                html.P("PRIVATE WORKSPACE", className="eyebrow"),
                html.H2("Personal Mode"),
                html.P(
                    "Login Google diperlukan dan hanya stable owner sub yang diizinkan."
                ),
                html.A(
                    "Login with Google",
                    href="/login",
                    className="primary-button",
                ),
            ]
        )

    database_url = os.environ.get("DATABASE_PERSONAL_URL", "").strip()
    if not database_url:
        return _warning("Owner verified, tetapi private database belum dikonfigurasi.")

    try:
        from cakrawala.personal.storage import (
            list_journal_entries,
            list_playbook_entries,
            list_portfolio_transactions,
            list_trade_plans,
        )

        owner_sub = state["sub"]
        transactions = [
            asdict(item) for item in list_portfolio_transactions(database_url, owner_sub)
        ]
        plans = [asdict(item) for item in list_trade_plans(database_url, owner_sub)]
        journal = [asdict(item) for item in list_journal_entries(database_url, owner_sub)]
        playbook = [asdict(item) for item in list_playbook_entries(database_url, owner_sub)]
    except Exception as exc:
        return _warning(f"Private storage belum dapat dibaca: {type(exc).__name__}")

    def table(rows: list[dict[str, Any]]) -> Any:
        if not rows:
            return html.P("Belum ada data.", className="muted")
        normalized = [
            {key: str(value) for key, value in row.items()}
            for row in rows
        ]
        return dash_table.DataTable(
            data=normalized,
            columns=[
                {"name": key.replace("_", " ").title(), "id": key}
                for key in normalized[0]
            ],
            page_size=8,
            style_table={"overflowX": "auto"},
        )

    return html.Div(
        [
            html.P("PRIVATE WORKSPACE", className="eyebrow"),
            html.Div(
                [
                    html.H2("Owner Research Terminal"),
                    html.A("Logout", href="/logout", className="text-link"),
                ],
                className="title-row",
            ),
            html.P(
                f"Owner verified: {state['display_name'] or 'Google identity'}",
                className="muted",
            ),
            _panel("Portfolio ledger", table(transactions)),
            _panel("Trade plans", table(plans)),
            _panel("Journal", table(journal)),
            _panel("Playbook", table(playbook)),
        ]
    )


def render_risk_tools() -> html.Div:
    models = load_yaml("configs/models.yaml")
    promoted = sum(value is not None for value in models.get("roles", {}).values())
    total = len(models.get("roles", {}))
    readiness = assess_execution_readiness(
        ExecutionEvidence(
            source_healthy=True,
            evidence_fresh=True,
            model_promoted=promoted > 0,
            model_healthy=promoted > 0,
            risk_check_passed=False,
            owner_authorized=False,
            paper_mode=True,
        )
    )
    return html.Div(
        [
            html.P("RISK AND TOOLS", className="eyebrow"),
            html.H2("Plan risk before execution"),
            html.Div(
                [
                    _metric("Promoted model roles", f"{promoted}/{total}"),
                    _metric("Execution state", readiness.state.value),
                ],
                className="metric-grid",
            ),
            html.Div(
                [
                    html.Div(
                        [
                            html.H3("Position sizing"),
                            html.Label("Account size"),
                            dcc.Input(
                                id="risk-account",
                                type="number",
                                value=10000,
                                min=1,
                            ),
                            html.Label("Risk percent"),
                            dcc.Input(
                                id="risk-percent",
                                type="number",
                                value=1,
                                min=0.01,
                                max=10,
                                step=0.1,
                            ),
                            html.Label("Entry"),
                            dcc.Input(
                                id="risk-entry",
                                type="number",
                                value=100,
                                min=0.000001,
                            ),
                            html.Label("Stop"),
                            dcc.Input(
                                id="risk-stop",
                                type="number",
                                value=98,
                                min=0.000001,
                            ),
                            html.Label("Target"),
                            dcc.Input(
                                id="risk-target",
                                type="number",
                                value=104,
                                min=0.000001,
                            ),
                            html.Button(
                                "Calculate",
                                id="risk-calc",
                                className="primary-button",
                            ),
                            html.Div(id="risk-output"),
                        ],
                        className="panel form-panel",
                    ),
                    html.Div(
                        [
                            html.H3("Expectancy"),
                            html.Label("Win rate percent"),
                            dcc.Input(
                                id="exp-win-rate",
                                type="number",
                                value=50,
                                min=0,
                                max=100,
                            ),
                            html.Label("Average win R"),
                            dcc.Input(
                                id="exp-win",
                                type="number",
                                value=2,
                                min=0,
                            ),
                            html.Label("Average loss R"),
                            dcc.Input(
                                id="exp-loss",
                                type="number",
                                value=1,
                                min=0,
                            ),
                            html.Button(
                                "Calculate",
                                id="exp-calc",
                                className="primary-button",
                            ),
                            html.Div(id="exp-output"),
                        ],
                        className="panel form-panel",
                    ),
                ],
                className="two-column",
            ),
            _panel(
                "Readiness reasons",
                html.Ul([html.Li(reason) for reason in readiness.reasons]),
            ),
        ]
    )


PAGES = {
    "overview": ("Overview", render_overview),
    "news": ("News", render_news),
    "positioning": ("Positioning", render_positioning),
    "market": ("Market", render_market),
    "macro": ("Macro", render_macro),
    "ai": ("AI Council", render_ai_council),
    "risk": ("Risk & Tools", render_risk_tools),
    "tools": ("Tool Radar", render_tool_radar),
    "personal": ("Personal", render_personal),
}


app.layout = html.Div(
    [
        dcc.Store(id="refresh-token", data=0),
        html.Aside(
            [
                html.Div(
                    [
                        html.P("CAKRAWALA", className="brand"),
                        html.P("Intelligence Terminal", className="brand-sub"),
                    ]
                ),
                dcc.RadioItems(
                    id="page-selector",
                    options=[
                        {"label": label, "value": key}
                        for key, (label, _) in PAGES.items()
                    ],
                    value="overview",
                    className="nav-list",
                    labelClassName="nav-item",
                    inputClassName="nav-radio",
                ),
                html.Button(
                    "Refresh evidence",
                    id="refresh-button",
                    className="secondary-button",
                ),
                html.P(
                    "Evidence first. No synthetic fallback.",
                    className="sidebar-note",
                ),
            ],
            className="sidebar",
        ),
        html.Main(
            [
                html.Header(
                    [
                        html.Div(
                            [
                                html.P("OPEN INTELLIGENCE", className="eyebrow"),
                                html.H1("Cakrawala"),
                            ]
                        ),
                        html.Div(
                            "Public research terminal",
                            className="status-chip",
                        ),
                    ],
                    className="topbar",
                ),
                dcc.Loading(
                    html.Div(id="page-content", className="content"),
                    type="circle",
                ),
            ],
            className="main-shell",
        ),
    ],
    className="app-shell",
)


@callback(
    Output("page-content", "children"),
    Output("refresh-token", "data"),
    Input("page-selector", "value"),
    Input("refresh-button", "n_clicks"),
    State("refresh-token", "data"),
)
def render_page(
    page: str,
    refresh_clicks: int | None,
    refresh_token: int,
) -> tuple[Any, int]:
    if refresh_clicks and refresh_clicks > refresh_token:
        PUBLIC_CACHE.clear()
        refresh_token = refresh_clicks
    renderer = PAGES.get(page, PAGES["overview"])[1]
    return renderer(), refresh_token


@callback(
    Output("risk-output", "children"),
    Input("risk-calc", "n_clicks"),
    State("risk-account", "value"),
    State("risk-percent", "value"),
    State("risk-entry", "value"),
    State("risk-stop", "value"),
    State("risk-target", "value"),
    prevent_initial_call=True,
)
def calculate_risk(
    _: int,
    account: float,
    risk_percent: float,
    entry: float,
    stop: float,
    target: float,
) -> Any:
    try:
        plan = build_position_plan(
            account_size=float(account),
            risk_percent=float(risk_percent),
            entry=float(entry),
            stop=float(stop),
            target=float(target),
        )
    except (TypeError, ValueError) as exc:
        return _warning(str(exc))
    return html.Div(
        [
            _metric("Risk amount", _safe_number(plan.risk_amount)),
            _metric("Quantity", _safe_number(plan.quantity, "", 6)),
            _metric("Reward / risk", _safe_number(plan.reward_risk, "x", 2)),
        ],
        className="metric-grid compact",
    )


@callback(
    Output("exp-output", "children"),
    Input("exp-calc", "n_clicks"),
    State("exp-win-rate", "value"),
    State("exp-win", "value"),
    State("exp-loss", "value"),
    prevent_initial_call=True,
)
def calculate_expectancy(
    _: int,
    win_rate: float,
    average_win: float,
    average_loss: float,
) -> Any:
    try:
        value = expectancy_r(
            win_rate_percent=float(win_rate),
            average_win_r=float(average_win),
            average_loss_r=float(average_loss),
        )
    except (TypeError, ValueError) as exc:
        return _warning(str(exc))
    return _metric("Expectancy", f"{value:+.3f} R/trade")


if __name__ == "__main__":
    app.run(
        debug=False,
        host="0.0.0.0",
        port=int(os.environ.get("PORT", "8050")),
    )
