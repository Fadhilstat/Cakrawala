from __future__ import annotations

from dataclasses import asdict
from datetime import datetime, timezone
from math import sqrt
from typing import Any, Callable

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from cakrawala.config import load_yaml
from cakrawala.data.providers.binance import fetch_klines
from cakrawala.data.providers.bmkg import earthquake_summary, fetch_latest_earthquake
from cakrawala.data.providers.news_feeds import fetch_macro_news
from cakrawala.data.providers.world_bank import fetch_indicator
from cakrawala.intelligence.news import assess_news
from cakrawala.personal.storage import list_portfolio_transactions


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def format_number(value: float | int | None, digits: int = 2) -> str:
    if value is None:
        return "N/A"
    return f"{value:,.{digits}f}"


def format_percent(value: float | None, digits: int = 2) -> str:
    if value is None:
        return "N/A"
    return f"{value:+.{digits}f}%"


@st.cache_data(ttl=600, show_spinner=False)
def load_earthquake() -> dict[str, Any]:
    result = fetch_latest_earthquake()
    summary = earthquake_summary(result.data)
    return {
        **summary,
        "fetched_at": result.provenance.fetched_at,
        "source_url": result.provenance.source_url,
    }


@st.cache_data(ttl=1800, show_spinner=False)
def load_macro_indicator(indicator: str, date_range: str = "2018:2024") -> dict[str, Any]:
    result = fetch_indicator("IDN", indicator, date_range)
    rows = result.data[1] if len(result.data) > 1 else []
    observations = [
        {"year": int(row["date"]), "value": float(row["value"])}
        for row in rows
        if isinstance(row, dict)
        and row.get("value") is not None
        and str(row.get("date", "")).isdigit()
    ]
    observations.sort(key=lambda row: row["year"])
    if not observations:
        raise ValueError("World Bank returned no usable observations")
    return {
        "observations": observations,
        "latest": observations[-1],
        "fetched_at": result.provenance.fetched_at,
        "source_url": result.provenance.source_url,
    }


@st.cache_data(ttl=300, show_spinner=False)
def load_market_history(limit: int = 90) -> dict[str, Any]:
    result = fetch_klines("BTCUSDT", interval="1d", limit=limit)
    records: list[dict[str, Any]] = []
    for row in result.data:
        if not isinstance(row, list) or len(row) < 7:
            continue
        records.append(
            {
                "time": pd.to_datetime(int(row[0]), unit="ms", utc=True),
                "open": float(row[1]),
                "high": float(row[2]),
                "low": float(row[3]),
                "close": float(row[4]),
                "volume": float(row[5]),
            }
        )
    if len(records) < 2:
        raise ValueError("Binance returned insufficient market history")
    frame = pd.DataFrame(records).sort_values("time").reset_index(drop=True)
    frame["return"] = frame["close"].pct_change()
    latest = frame.iloc[-1]
    previous = frame.iloc[-2]
    return {
        "frame": frame,
        "latest": {
            "close": float(latest["close"]),
            "volume": float(latest["volume"]),
            "change_1d_pct": (float(latest["close"]) / float(previous["close"]) - 1.0) * 100,
        },
        "fetched_at": result.provenance.fetched_at,
        "source_url": result.provenance.source_url,
    }


@st.cache_data(ttl=600, show_spinner=False)
def load_news() -> list[dict[str, Any]]:
    items = fetch_macro_news(limit_per_source=8)
    return [asdict(item) for item in assess_news(items)]


def market_risk_stats(frame: pd.DataFrame) -> dict[str, float | None]:
    returns = frame["return"].dropna()
    closes = frame["close"].astype(float)
    if returns.empty:
        return {"volatility": None, "drawdown": None, "momentum": None}
    last_30 = returns.tail(30)
    volatility = float(last_30.std(ddof=1) * sqrt(365) * 100) if len(last_30) > 1 else None
    drawdown = float((closes.iloc[-1] / closes.cummax().iloc[-1] - 1.0) * 100)
    lookback = max(len(closes) - 31, 0)
    momentum = float((closes.iloc[-1] / closes.iloc[lookback] - 1.0) * 100)
    return {"volatility": volatility, "drawdown": drawdown, "momentum": momentum}


def safe_load(name: str, loader: Callable[[], Any], snapshot: dict[str, Any]) -> None:
    try:
        snapshot[name] = loader()
    except Exception as exc:
        snapshot[name] = None
        snapshot["errors"][name] = type(exc).__name__


def public_snapshot() -> dict[str, Any]:
    snapshot: dict[str, Any] = {"errors": {}}
    safe_load("earthquake", load_earthquake, snapshot)
    safe_load("population", lambda: load_macro_indicator("SP.POP.TOTL"), snapshot)
    safe_load("gdp", lambda: load_macro_indicator("NY.GDP.MKTP.KD.ZG"), snapshot)
    safe_load("inflation", lambda: load_macro_indicator("FP.CPI.TOTL.ZG"), snapshot)
    safe_load("market", load_market_history, snapshot)
    safe_load("news", load_news, snapshot)
    return snapshot


def source_status(snapshot: dict[str, Any], key: str) -> str:
    return "LIVE" if snapshot.get(key) is not None else "DOWN"


def render_header() -> None:
    st.markdown(
        """
        <style>
        .block-container {padding-top: 1.35rem; padding-bottom: 3rem; max-width: 1450px;}
        [data-testid="stMetric"] {
            border: 1px solid rgba(220, 235, 224, 0.10);
            border-radius: 12px;
            padding: 14px 16px;
            background: rgba(255, 255, 255, 0.015);
        }
        .terminal-kicker {
            font-size: 0.72rem;
            letter-spacing: 0.12em;
            text-transform: uppercase;
            opacity: 0.62;
            font-weight: 700;
        }
        .terminal-lead {max-width: 980px; opacity: 0.78; line-height: 1.6;}
        .status-live {color: #72df7f; font-weight: 700;}
        </style>
        """,
        unsafe_allow_html=True,
    )
    st.markdown('<div class="terminal-kicker">Evidence first research terminal</div>', unsafe_allow_html=True)
    st.title("Cakrawala Intelligence Terminal")
    st.markdown(
        '<div class="terminal-lead">'
        "News, macro, market structure, risk, dan tool research disatukan dalam satu alur. "
        "Tidak ada signal yang dianggap valid tanpa data segar, model sehat, dan policy yang lolos gate."
        "</div>",
        unsafe_allow_html=True,
    )


def render_overview(snapshot: dict[str, Any]) -> None:
    market = snapshot.get("market")
    earthquake = snapshot.get("earthquake")
    inflation = snapshot.get("inflation")
    news = snapshot.get("news") or []
    risk = market_risk_stats(market["frame"]) if market else {}

    cols = st.columns(6)
    cols[0].metric("Sources", f"{6 - len(snapshot['errors'])}/6")
    cols[1].metric("BTC 1D", format_percent(market["latest"]["change_1d_pct"]) if market else "N/A")
    cols[2].metric("30D momentum", format_percent(risk.get("momentum")))
    cols[3].metric(
        "30D annualized vol",
        f"{risk['volatility']:.1f}%" if risk.get("volatility") is not None else "N/A",
    )
    cols[4].metric(
        "Latest quake",
        f"M {earthquake.get('magnitude')}" if earthquake and earthquake.get("magnitude") else "N/A",
    )
    high_attention = sum(int(item["attention_score"] >= 5) for item in news)
    cols[5].metric("News watch", str(high_attention))

    left, right = st.columns([1.5, 1])
    with left:
        st.markdown("### Market pulse")
        if market:
            frame = market["frame"].tail(45)
            fig = px.line(frame, x="time", y="close")
            fig.update_layout(
                height=330,
                margin=dict(l=10, r=10, t=10, b=10),
                xaxis_title=None,
                yaxis_title="BTC/USDT",
                showlegend=False,
            )
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.warning("Market source sedang tidak tersedia.")

    with right:
        st.markdown("### Today at a glance")
        if inflation:
            latest = inflation["latest"]
            st.write(f"**Inflation Indonesia:** {latest['value']:.2f}% ({latest['year']})")
        if earthquake:
            st.write(f"**BMKG:** M {earthquake.get('magnitude', 'N/A')} | {earthquake.get('depth', 'N/A')}")
            st.caption(earthquake.get("region") or "Wilayah belum tersedia")
        if news:
            top = news[0]
            st.write(f"**Top news watch:** {top['title']}")
            st.caption(top["watch_reason"])
        st.divider()
        st.caption(
            "Overview bersifat deskriptif. Signal eksekusi tetap terpisah dan harus lolos evidence gate."
        )


def render_news_research(snapshot: dict[str, Any]) -> None:
    st.subheader("News & Daily Research")
    st.write(
        "Headline resmi dipakai sebagai evidence tambahan. Skor perhatian hanya membantu prioritas baca, "
        "bukan prediksi arah harga."
    )
    news = snapshot.get("news") or []
    if not news:
        st.warning("Feed Federal Reserve atau BIS belum dapat dimuat.")
        return

    query = st.text_input("Search headlines", placeholder="rates, liquidity, regulation, stablecoin...")
    tags = sorted({tag for item in news for tag in item["tags"]})
    selected_tags = st.multiselect("Filter themes", tags)

    filtered = []
    for item in news:
        if query and query.lower() not in item["title"].lower():
            continue
        if selected_tags and not any(tag in item["tags"] for tag in selected_tags):
            continue
        filtered.append(item)

    top_left, top_right = st.columns([1.6, 1])
    with top_left:
        st.markdown("### Headline monitor")
        for item in filtered[:12]:
            published = item["published_at"]
            published_text = published.strftime("%d %b %Y %H:%M UTC") if published else "time unavailable"
            st.markdown(f"**{item['title']}**")
            st.caption(
                f"{item['source']} | attention {item['attention_score']}/10 | "
                f"{', '.join(item['tags'])} | {published_text}"
            )
            st.write(item["watch_reason"])
            st.link_button("Open source", item["link"])
            st.divider()

    with top_right:
        st.markdown("### Research brief")
        counts: dict[str, int] = {}
        for item in news:
            for tag in item["tags"]:
                counts[tag] = counts.get(tag, 0) + 1
        if counts:
            chart = pd.DataFrame(
                [{"theme": key, "headlines": value} for key, value in counts.items()]
            ).sort_values("headlines", ascending=True)
            fig = px.bar(chart, x="headlines", y="theme", orientation="h")
            fig.update_layout(
                height=300,
                margin=dict(l=10, r=10, t=10, b=10),
                xaxis_title=None,
                yaxis_title=None,
                showlegend=False,
            )
            st.plotly_chart(fig, use_container_width=True)
        st.info(
            "Before execution: read the highest-attention headlines, compare them with market volatility, "
            "then recheck model freshness and signal policy."
        )
        st.caption(
            "Current live feeds: Federal Reserve press releases and BIS press releases. "
            "Bank Indonesia remains an official source watch and will be added only through a stable interface."
        )


def render_market(snapshot: dict[str, Any]) -> None:
    st.subheader("Market Structure")
    market = snapshot.get("market")
    if not market:
        st.warning("Binance public market data sedang tidak tersedia.")
        return
    frame = market["frame"].copy()
    latest = market["latest"]
    risk = market_risk_stats(frame)

    cols = st.columns(6)
    cols[0].metric("BTC/USDT", format_number(latest["close"]))
    cols[1].metric("1D", format_percent(latest["change_1d_pct"]))
    cols[2].metric("30D momentum", format_percent(risk["momentum"]))
    cols[3].metric(
        "30D annualized vol",
        f"{risk['volatility']:.1f}%" if risk["volatility"] is not None else "N/A",
    )
    cols[4].metric("Drawdown", format_percent(risk["drawdown"]))
    cols[5].metric("Volume", format_number(latest["volume"]))

    candle, returns, range_tab = st.tabs(["Price", "Returns", "Range"])
    with candle:
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
        fig.update_layout(height=470, xaxis_rangeslider_visible=False, margin=dict(l=10, r=10, t=10, b=10))
        st.plotly_chart(fig, use_container_width=True)
    with returns:
        temp = frame.dropna(subset=["return"]).copy()
        temp["return_pct"] = temp["return"] * 100
        fig = px.bar(temp, x="time", y="return_pct")
        fig.update_layout(height=400, margin=dict(l=10, r=10, t=10, b=10), xaxis_title=None)
        st.plotly_chart(fig, use_container_width=True)
    with range_tab:
        temp = frame.tail(30).copy()
        temp["range_pct"] = (temp["high"] - temp["low"]) / temp["open"] * 100
        fig = px.line(temp, x="time", y="range_pct", markers=True)
        fig.update_layout(height=400, margin=dict(l=10, r=10, t=10, b=10), xaxis_title=None)
        st.plotly_chart(fig, use_container_width=True)


def render_macro(snapshot: dict[str, Any]) -> None:
    st.subheader("Indonesia & Macro")
    population = snapshot.get("population")
    gdp = snapshot.get("gdp")
    inflation = snapshot.get("inflation")
    cols = st.columns(3)
    if population:
        latest = population["latest"]
        cols[0].metric("Population", f"{int(latest['value']):,}", str(latest["year"]))
    else:
        cols[0].metric("Population", "N/A")
    if gdp:
        latest = gdp["latest"]
        cols[1].metric("GDP growth", f"{latest['value']:.2f}%", str(latest["year"]))
    else:
        cols[1].metric("GDP growth", "N/A")
    if inflation:
        latest = inflation["latest"]
        cols[2].metric("Inflation", f"{latest['value']:.2f}%", str(latest["year"]))
    else:
        cols[2].metric("Inflation", "N/A")

    rows: list[dict[str, Any]] = []
    for label, payload in (("GDP growth", gdp), ("Inflation", inflation)):
        if payload:
            rows.extend(
                {"year": row["year"], "value": row["value"], "series": label}
                for row in payload["observations"]
            )
    if rows:
        chart = pd.DataFrame(rows)
        fig = px.line(chart, x="year", y="value", color="series", markers=True)
        fig.update_layout(height=390, margin=dict(l=10, r=10, t=10, b=10), legend_title=None)
        st.plotly_chart(fig, use_container_width=True)

    st.caption("Official Indonesia source watch: Bank Indonesia and BPS remain part of the approved source universe.")


def render_tool_radar() -> None:
    st.subheader("Bot & Tool Radar")
    st.write(
        "Setiap kandidat diperlakukan sebagai software pihak ketiga yang belum dipercaya. "
        "Radar ini membantu riset, bukan melakukan instalasi otomatis."
    )
    radar = load_yaml("configs/tool_radar.yaml")
    st.caption(f"Last reviewed: {radar.get('as_of', 'unknown')}")
    for item in radar.get("items", []):
        with st.container(border=True):
            left, right = st.columns([3, 1])
            left.markdown(f"### {item['name']}")
            left.caption(item["category"])
            right.markdown(f"**{item['status']}**")
            st.write(item["latest_verified_activity"])
            st.write(item["rationale"])
            st.link_button("Primary source", item["source"])
            with st.expander("Security and operational risks"):
                for risk in item.get("risks", []):
                    st.write(f"- {risk}")

    st.info(
        "Weekly research may promote a tool only to sandbox candidate. Production use still needs "
        "dependency review, secret isolation, paper trading, execution tests, and explicit approval."
    )


def render_execution(snapshot: dict[str, Any]) -> None:
    st.subheader("Execution Readiness")
    models = load_yaml("configs/models.yaml")
    roles = models.get("roles", {})
    promotion = models.get("promotion", {})
    promoted = sum(value is not None for value in roles.values())
    news = snapshot.get("news") or []
    high_attention = sum(int(item["attention_score"] >= 5) for item in news)
    market = snapshot.get("market")
    market_live = market is not None

    cols = st.columns(5)
    cols[0].metric("Market data", "LIVE" if market_live else "DOWN")
    cols[1].metric("News feed", source_status(snapshot, "news"))
    cols[2].metric("High-attention news", str(high_attention))
    cols[3].metric("Model roles promoted", f"{promoted}/{len(roles)}")
    cols[4].metric("Signal", "NO SIGNAL" if promoted == 0 else "POLICY CHECK")

    left, right = st.columns([1.2, 1])
    with left:
        st.markdown("### Pre-execution checklist")
        checklist = [
            ("Market source healthy", market_live),
            ("News evidence loaded", snapshot.get("news") is not None),
            ("No source error hidden", True),
            ("Model champion available", promoted > 0),
            ("Personal execution route authorized", False),
        ]
        for label, passed in checklist:
            st.write(f"{'OK' if passed else 'WAIT'}  {label}")
    with right:
        st.markdown("### Promotion policy")
        st.write(f"Minimum health: **{float(promotion.get('minimum_health', 0)):.2f}**")
        st.write(
            "Minimum benchmark improvement: "
            f"**{float(promotion.get('minimum_relative_improvement', 0)) * 100:.1f}%**"
        )
        st.write(f"Walk-forward required: **{'Yes' if promotion.get('require_walk_forward') else 'No'}**")
        st.write(
            "Point-in-time features required: "
            f"**{'Yes' if promotion.get('require_point_in_time_features') else 'No'}**"
        )

    if promoted == 0:
        st.warning(
            "Execution remains blocked. No model role has been promoted, so Cakrawala must not invent a BUY or SELL decision."
        )


def owner_runtime_config() -> tuple[bool, str | None, str | None]:
    try:
        auth = st.secrets.get("auth", {})
        cakrawala = st.secrets.get("cakrawala", {})
    except FileNotFoundError:
        return False, None, None
    owner_sub = cakrawala.get("owner_sub")
    database_url = cakrawala.get("database_personal_url")
    required = ("redirect_uri", "cookie_secret", "client_id", "client_secret", "server_metadata_url")
    configured = bool(owner_sub) and all(auth.get(key) for key in required)
    return configured, str(owner_sub) if owner_sub else None, str(database_url) if database_url else None


def render_personal() -> None:
    st.subheader("Owner Research")
    configured, owner_sub, database_url = owner_runtime_config()
    if not configured:
        st.warning("Personal Mode belum aktif. OIDC owner dan private database belum dikonfigurasi.")
        st.write("Public research tetap dapat digunakan tanpa membuka data pribadi.")
        return
    if not st.user.is_logged_in:
        st.button("Log in with Google", on_click=st.login, use_container_width=True)
        return
    if str(st.user.get("sub", "")) != owner_sub:
        st.error("Akun terautentikasi tetapi tidak memiliki akses owner.")
        st.button("Log out", on_click=st.logout)
        return
    st.success("Owner identity verified")
    st.button("Log out", on_click=st.logout)
    if not database_url:
        st.warning("Private database belum dikonfigurasi.")
        return
    try:
        transactions = list_portfolio_transactions(database_url, owner_sub)
    except Exception as exc:
        st.warning("Portfolio ledger tidak dapat dimuat. Data pribadi tetap ditutup.")
        st.caption(f"Status teknis: {type(exc).__name__}")
        return
    if transactions:
        st.dataframe([asdict(item) for item in transactions], use_container_width=True, hide_index=True)
    else:
        st.info("Belum ada transaksi pada private ledger.")


def run() -> None:
    st.set_page_config(
        page_title="Cakrawala Intelligence Terminal",
        page_icon="C",
        layout="wide",
        initial_sidebar_state="expanded",
    )
    render_header()

    with st.sidebar:
        st.header("Cakrawala")
        mode = st.radio("Access", ["Public Mode", "Personal Mode"], label_visibility="collapsed")
        st.divider()
        st.caption("Public: research and public evidence")
        st.caption("Personal: owner-only private state")
        if st.button("Refresh evidence", use_container_width=True):
            st.cache_data.clear()
            st.rerun()

    if mode == "Personal Mode":
        render_personal()
        return

    snapshot = public_snapshot()
    page = st.radio(
        "Workspace",
        ["Overview", "News & Research", "Market", "Indonesia & Macro", "Tool Radar", "Execution"],
        horizontal=True,
        label_visibility="collapsed",
    )
    st.divider()

    if page == "Overview":
        render_overview(snapshot)
    elif page == "News & Research":
        render_news_research(snapshot)
    elif page == "Market":
        render_market(snapshot)
    elif page == "Indonesia & Macro":
        render_macro(snapshot)
    elif page == "Tool Radar":
        render_tool_radar()
    else:
        render_execution(snapshot)

    with st.expander("System status"):
        st.write(f"Snapshot: {utc_now().isoformat()}")
        if snapshot["errors"]:
            st.warning("Some public sources are unavailable in this snapshot.")
            st.json(snapshot["errors"])
        else:
            st.success("All public sources used in this snapshot responded successfully.")
