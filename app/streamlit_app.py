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
from cakrawala.data.providers.world_bank import fetch_indicator
from cakrawala.personal.storage import list_portfolio_transactions


st.set_page_config(
    page_title="Cakrawala Intelligence Terminal",
    page_icon="C",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
    <style>
    .block-container {padding-top: 1.7rem; padding-bottom: 3rem;}
    [data-testid="stMetric"] {
        border: 1px solid rgba(128, 128, 128, 0.20);
        border-radius: 12px;
        padding: 14px 16px;
    }
    [data-testid="stMetricLabel"] {font-size: 0.82rem;}
    .cakrawala-kicker {
        letter-spacing: 0.09em;
        text-transform: uppercase;
        font-size: 0.76rem;
        font-weight: 700;
        opacity: 0.65;
    }
    .cakrawala-lead {
        max-width: 900px;
        font-size: 1.02rem;
        line-height: 1.65;
        opacity: 0.82;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


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
        "provider": result.provider,
    }


@st.cache_data(ttl=1800, show_spinner=False)
def load_macro_indicator(indicator: str, date_range: str = "2018:2024") -> dict[str, Any]:
    result = fetch_indicator("IDN", indicator, date_range)
    rows = result.data[1] if len(result.data) > 1 else []
    observations = [
        {
            "year": int(row["date"]),
            "value": float(row["value"]),
        }
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
        "provider": result.provider,
    }


@st.cache_data(ttl=300, show_spinner=False)
def load_market_history(symbol: str = "BTCUSDT", limit: int = 90) -> dict[str, Any]:
    result = fetch_klines(symbol, interval="1d", limit=limit)
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
            "time": latest["time"],
            "open": float(latest["open"]),
            "high": float(latest["high"]),
            "low": float(latest["low"]),
            "close": float(latest["close"]),
            "volume": float(latest["volume"]),
            "change_1d_pct": (float(latest["close"]) / float(previous["close"]) - 1.0) * 100,
        },
        "fetched_at": result.provenance.fetched_at,
        "source_url": result.provenance.source_url,
        "provider": result.provider,
    }


def market_risk_stats(frame: pd.DataFrame) -> dict[str, float | None]:
    returns = frame["return"].dropna()
    if returns.empty:
        return {
            "volatility_30d_pct": None,
            "drawdown_pct": None,
            "momentum_30d_pct": None,
        }

    last_30 = returns.tail(30)
    volatility = float(last_30.std(ddof=1) * sqrt(365) * 100) if len(last_30) > 1 else None
    closes = frame["close"].astype(float)
    running_peak = closes.cummax()
    drawdowns = closes / running_peak - 1.0
    drawdown = float(drawdowns.iloc[-1] * 100)
    lookback_index = max(len(closes) - 31, 0)
    momentum = float((closes.iloc[-1] / closes.iloc[lookback_index] - 1.0) * 100)
    return {
        "volatility_30d_pct": volatility,
        "drawdown_pct": drawdown,
        "momentum_30d_pct": momentum,
    }


def source_age_minutes(fetched_at: datetime) -> float:
    return max((utc_now() - fetched_at.astimezone(timezone.utc)).total_seconds() / 60, 0.0)


def source_badge(age_minutes: float, stale_after: float) -> str:
    return "LIVE" if age_minutes <= stale_after else "STALE"


def load_public_snapshot() -> dict[str, Any]:
    snapshot: dict[str, Any] = {"errors": {}}
    loaders: dict[str, Callable[[], Any]] = {
        "earthquake": load_earthquake,
        "population": lambda: load_macro_indicator("SP.POP.TOTL"),
        "gdp_growth": lambda: load_macro_indicator("NY.GDP.MKTP.KD.ZG"),
        "inflation": lambda: load_macro_indicator("FP.CPI.TOTL.ZG"),
        "market": load_market_history,
    }
    for name, loader in loaders.items():
        try:
            snapshot[name] = loader()
        except Exception as exc:
            snapshot["errors"][name] = type(exc).__name__
            snapshot[name] = None
    return snapshot


def render_source_error(source_name: str, error_name: str | None) -> None:
    st.warning(
        f"{source_name} sedang tidak tersedia. Terminal tidak mengganti data yang gagal "
        "dengan angka buatan."
    )
    if error_name:
        st.caption(f"Status teknis: {error_name}")


def render_provenance(label: str, payload: dict[str, Any] | None, stale_after: float) -> None:
    if not payload:
        st.caption(f"{label}: unavailable")
        return
    age = source_age_minutes(payload["fetched_at"])
    status = source_badge(age, stale_after)
    st.caption(
        f"{label}: {status} | fetched {age:.1f} min ago | "
        f"{payload['source_url']}"
    )


def render_command_center(snapshot: dict[str, Any]) -> None:
    st.markdown('<div class="cakrawala-kicker">Workspace 01</div>', unsafe_allow_html=True)
    st.subheader("Command Center")
    st.write(
        "Ringkasan cepat untuk melihat apakah lingkungan informasi hari ini normal, berubah, "
        "atau perlu diperiksa lebih dalam."
    )

    earthquake = snapshot.get("earthquake")
    market = snapshot.get("market")
    inflation = snapshot.get("inflation")
    healthy_count = sum(
        snapshot.get(name) is not None
        for name in ("earthquake", "population", "gdp_growth", "inflation", "market")
    )

    cols = st.columns(5)
    cols[0].metric("Sources online", f"{healthy_count}/5")
    cols[1].metric(
        "BTC 1D",
        format_percent(market["latest"]["change_1d_pct"]) if market else "N/A",
    )
    risk = market_risk_stats(market["frame"]) if market else {}
    cols[2].metric(
        "BTC 30D vol",
        f"{risk.get('volatility_30d_pct'):.1f}%" if risk.get("volatility_30d_pct") is not None else "N/A",
    )
    cols[3].metric(
        "Latest quake",
        f"M {earthquake.get('magnitude')}" if earthquake and earthquake.get("magnitude") else "N/A",
    )
    latest_inflation = inflation["latest"] if inflation else None
    cols[4].metric(
        "ID inflation",
        f"{latest_inflation['value']:.2f}%" if latest_inflation else "N/A",
        f"{latest_inflation['year']}" if latest_inflation else None,
    )

    left, right = st.columns([1.45, 1])
    with left:
        st.markdown("#### Market pulse")
        if not market:
            render_source_error("Binance market data", snapshot["errors"].get("market"))
        else:
            frame = market["frame"].tail(30)
            fig = px.line(frame, x="time", y="close")
            fig.update_layout(
                height=310,
                margin=dict(l=10, r=10, t=15, b=10),
                xaxis_title=None,
                yaxis_title="BTC/USDT",
                showlegend=False,
            )
            st.plotly_chart(fig, use_container_width=True)
            st.caption(
                "Ini adalah harga publik dan statistik deskriptif. Belum ada model yang berhak "
                "mengubahnya menjadi rekomendasi transaksi."
            )

    with right:
        st.markdown("#### Indonesia now")
        if earthquake:
            st.write(f"**Gempa:** M {earthquake.get('magnitude', 'N/A')} | {earthquake.get('depth', 'N/A')}")
            st.write(earthquake.get("region") or "Wilayah belum tersedia")
            st.caption(earthquake.get("potential") or "Informasi potensi belum tersedia")
        else:
            render_source_error("BMKG", snapshot["errors"].get("earthquake"))

        if inflation:
            latest = inflation["latest"]
            st.write(f"**Inflasi:** {latest['value']:.2f}% ({latest['year']})")
        if snapshot.get("gdp_growth"):
            latest = snapshot["gdp_growth"]["latest"]
            st.write(f"**Pertumbuhan PDB:** {latest['value']:.2f}% ({latest['year']})")
        st.divider()
        st.markdown("**Evidence policy**")
        st.caption(
            "Sumber yang gagal atau stale tidak diganti dengan data sintetis. Model dan signal "
            "juga tidak ditampilkan sebagai valid tanpa evidence yang lolos gate."
        )


def render_macro_workspace(snapshot: dict[str, Any]) -> None:
    st.markdown('<div class="cakrawala-kicker">Workspace 02</div>', unsafe_allow_html=True)
    st.subheader("Indonesia & Macro")
    st.write(
        "Konteks Indonesia dengan indikator yang bisa ditelusuri ke sumbernya, bukan angka tanpa asal."
    )

    population = snapshot.get("population")
    gdp = snapshot.get("gdp_growth")
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

    chart_rows: list[dict[str, Any]] = []
    for label, payload in (("GDP growth", gdp), ("Inflation", inflation)):
        if not payload:
            continue
        for row in payload["observations"]:
            chart_rows.append({"year": row["year"], "value": row["value"], "series": label})

    if chart_rows:
        chart_frame = pd.DataFrame(chart_rows)
        fig = px.line(chart_frame, x="year", y="value", color="series", markers=True)
        fig.update_layout(
            height=380,
            margin=dict(l=10, r=10, t=20, b=10),
            xaxis_title=None,
            yaxis_title="Percent",
            legend_title=None,
        )
        st.plotly_chart(fig, use_container_width=True)
    else:
        render_source_error("World Bank macro indicators", snapshot["errors"].get("gdp_growth"))

    with st.expander("Source provenance"):
        render_provenance("Population", population, 1440)
        render_provenance("GDP growth", gdp, 1440)
        render_provenance("Inflation", inflation, 1440)


def render_market_workspace(snapshot: dict[str, Any]) -> None:
    st.markdown('<div class="cakrawala-kicker">Workspace 03</div>', unsafe_allow_html=True)
    st.subheader("Market Intelligence")
    st.write(
        "Pasar publik dibaca sebagai evidence: trend, risk, drawdown, dan volume. "
        "Tidak ada BUY atau SELL yang dibuat dari statistik ini saja."
    )

    market = snapshot.get("market")
    if not market:
        render_source_error("Binance market data", snapshot["errors"].get("market"))
        return

    frame = market["frame"].copy()
    latest = market["latest"]
    risk = market_risk_stats(frame)

    cols = st.columns(6)
    cols[0].metric("BTC/USDT", format_number(latest["close"]))
    cols[1].metric("1D change", format_percent(latest["change_1d_pct"]))
    cols[2].metric("30D momentum", format_percent(risk["momentum_30d_pct"]))
    cols[3].metric(
        "30D ann. vol",
        f"{risk['volatility_30d_pct']:.1f}%" if risk["volatility_30d_pct"] is not None else "N/A",
    )
    cols[4].metric("Current drawdown", format_percent(risk["drawdown_pct"]))
    cols[5].metric("Volume", format_number(latest["volume"]))

    price_tab, return_tab, range_tab = st.tabs(["Price", "Returns", "Trading range"])
    with price_tab:
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
            height=480,
            margin=dict(l=10, r=10, t=20, b=10),
            xaxis_rangeslider_visible=False,
            yaxis_title="BTC/USDT",
        )
        st.plotly_chart(fig, use_container_width=True)
    with return_tab:
        return_frame = frame.dropna(subset=["return"]).copy()
        return_frame["return_pct"] = return_frame["return"] * 100
        fig = px.bar(return_frame, x="time", y="return_pct")
        fig.update_layout(
            height=420,
            margin=dict(l=10, r=10, t=20, b=10),
            xaxis_title=None,
            yaxis_title="Daily return (%)",
        )
        st.plotly_chart(fig, use_container_width=True)
    with range_tab:
        range_frame = frame.tail(30).copy()
        range_frame["intraday_range_pct"] = (
            (range_frame["high"] - range_frame["low"]) / range_frame["open"] * 100
        )
        fig = px.line(range_frame, x="time", y="intraday_range_pct", markers=True)
        fig.update_layout(
            height=420,
            margin=dict(l=10, r=10, t=20, b=10),
            xaxis_title=None,
            yaxis_title="High-low range (%)",
        )
        st.plotly_chart(fig, use_container_width=True)

    with st.expander("Source provenance and interpretation"):
        render_provenance("Binance public market data", market, 30)
        st.caption(
            "Volatility, momentum, and drawdown on this page are descriptive analytics, not forecasts."
        )


def render_model_workspace(snapshot: dict[str, Any]) -> None:
    st.markdown('<div class="cakrawala-kicker">Workspace 04</div>', unsafe_allow_html=True)
    st.subheader("Risk & Model Evidence")
    st.write(
        "Ruang ini menunjukkan apa yang sudah punya evidence dan apa yang belum. "
        "Terminal tidak mengarang prediksi hanya supaya dashboard terlihat pintar."
    )

    market = snapshot.get("market")
    risk = market_risk_stats(market["frame"]) if market else {}
    models = load_yaml("configs/models.yaml")
    roles = models.get("roles", {})
    promotion = models.get("promotion", {})

    promoted_roles = sum(value is not None for value in roles.values())
    total_roles = len(roles)
    cols = st.columns(4)
    cols[0].metric("Promoted model roles", f"{promoted_roles}/{total_roles}")
    cols[1].metric(
        "Market volatility",
        f"{risk.get('volatility_30d_pct'):.1f}%" if risk.get("volatility_30d_pct") is not None else "N/A",
    )
    cols[2].metric("Signal", "NO SIGNAL")
    cols[3].metric("Policy state", "Fail closed")

    left, right = st.columns([1.15, 1])
    with left:
        st.markdown("#### Model promotion board")
        model_rows = [
            {
                "Role": role.replace("_", " ").title(),
                "Champion": champion or "Not promoted",
                "Status": "Ready" if champion else "Evidence pending",
            }
            for role, champion in roles.items()
        ]
        st.dataframe(model_rows, use_container_width=True, hide_index=True)
        st.caption(
            "A role remains unpromoted until walk-forward, point-in-time, health, and benchmark "
            "requirements are satisfied."
        )

    with right:
        st.markdown("#### Promotion gates")
        st.write(f"Minimum health score: **{float(promotion.get('minimum_health', 0)):.2f}**")
        st.write(
            "Minimum relative improvement: "
            f"**{float(promotion.get('minimum_relative_improvement', 0)) * 100:.1f}%**"
        )
        st.write(
            "Maximum secondary metric regression: "
            f"**{float(promotion.get('maximum_secondary_metric_regression', 0)) * 100:.1f}%**"
        )
        st.write(
            "Walk-forward required: "
            f"**{'Yes' if promotion.get('require_walk_forward') else 'No'}**"
        )
        st.write(
            "Point-in-time features required: "
            f"**{'Yes' if promotion.get('require_point_in_time_features') else 'No'}**"
        )

    st.info(
        "NO SIGNAL di sini bukan fitur yang hilang. Itu perilaku yang disengaja selama belum ada "
        "model champion dan evidence yang cukup untuk membuat keputusan deterministik."
    )


def owner_runtime_config() -> tuple[bool, str | None, str | None]:
    try:
        auth = st.secrets.get("auth", {})
        cakrawala = st.secrets.get("cakrawala", {})
    except FileNotFoundError:
        return False, None, None

    owner_sub = cakrawala.get("owner_sub")
    database_url = cakrawala.get("database_personal_url")
    required_auth = (
        "redirect_uri",
        "cookie_secret",
        "client_id",
        "client_secret",
        "server_metadata_url",
    )
    configured = bool(owner_sub) and all(auth.get(key) for key in required_auth)
    return (
        configured,
        str(owner_sub) if owner_sub else None,
        str(database_url) if database_url else None,
    )


def render_personal_mode() -> None:
    st.markdown('<div class="cakrawala-kicker">Private workspace</div>', unsafe_allow_html=True)
    st.subheader("Owner Research Terminal")
    configured, owner_sub, database_url = owner_runtime_config()

    if not configured:
        st.warning(
            "Personal Mode belum diaktifkan. OIDC owner dan database privat harus dikonfigurasi "
            "di Streamlit Secrets sebelum login dibuka."
        )
        st.write(
            "Saat aktif, ruang ini menjadi tempat portfolio ledger, watchlist pribadi, dan signal "
            "yang sudah lolos policy. Public Mode tetap tidak bisa membaca data ini."
        )
        return

    if not st.user.is_logged_in:
        st.write("Login Google diperlukan untuk membuka ruang riset owner.")
        st.button("Log in with Google", on_click=st.login, use_container_width=True)
        return

    current_sub = str(st.user.get("sub", ""))
    if not owner_sub or current_sub != owner_sub:
        st.error("Akun terautentikasi, tetapi bukan owner yang diizinkan.")
        st.button("Log out", on_click=st.logout)
        return

    top_left, top_right = st.columns([4, 1])
    top_left.success("Owner identity verified")
    top_right.button("Log out", on_click=st.logout, use_container_width=True)

    if not database_url:
        st.warning(
            "Database privat belum dikonfigurasi. Data owner tidak akan dialihkan ke penyimpanan publik."
        )
        return

    try:
        transactions = list_portfolio_transactions(database_url, owner_sub)
    except Exception as exc:
        st.warning("Portfolio ledger tidak dapat dimuat. Data pribadi tetap ditutup.")
        st.caption(f"Status teknis: {type(exc).__name__}")
        return

    st.markdown("#### Portfolio ledger")
    if transactions:
        st.dataframe(
            [asdict(transaction) for transaction in transactions],
            use_container_width=True,
            hide_index=True,
        )
    else:
        st.info("Belum ada transaksi pada ledger owner.")

    st.caption(
        "Signal personal tetap berasal dari policy deterministik dan model yang lolos promotion gate."
    )


st.markdown('<div class="cakrawala-kicker">Open Intelligence Platform</div>', unsafe_allow_html=True)
st.title("Cakrawala Intelligence Terminal")
st.markdown(
    '<div class="cakrawala-lead">'
    "Satu terminal untuk membaca perubahan, risiko, dan kualitas evidence dari sumber publik. "
    "Angka tidak berdiri sendiri: setiap panel mempertahankan konteks, freshness, dan provenance."
    "</div>",
    unsafe_allow_html=True,
)

with st.sidebar:
    st.header("Cakrawala")
    mode = st.radio("Access mode", ["Public Mode", "Personal Mode"], label_visibility="collapsed")
    st.divider()
    st.caption("Public Mode")
    st.write("Anonymous, evidence-first, no private state.")
    st.caption("Personal Mode")
    st.write("Owner-only, OIDC protected, separate private storage.")
    st.divider()
    if st.button("Refresh public evidence", use_container_width=True):
        st.cache_data.clear()
        st.rerun()

if mode == "Personal Mode":
    render_personal_mode()
    st.stop()

snapshot = load_public_snapshot()

workspace = st.radio(
    "Workspace",
    [
        "Command Center",
        "Indonesia & Macro",
        "Market Intelligence",
        "Risk & Model Evidence",
    ],
    horizontal=True,
    label_visibility="collapsed",
)

st.divider()

if workspace == "Command Center":
    render_command_center(snapshot)
elif workspace == "Indonesia & Macro":
    render_macro_workspace(snapshot)
elif workspace == "Market Intelligence":
    render_market_workspace(snapshot)
else:
    render_model_workspace(snapshot)

st.divider()
with st.expander("System status and data policy"):
    st.write(
        "Public evidence is cached only for short intervals. Private owner data is never placed in "
        "the shared public cache. Provider failures remain visible and do not trigger synthetic data."
    )
    st.write(f"Snapshot generated: {utc_now().isoformat()}")
    if snapshot["errors"]:
        st.warning("Some providers returned errors in this snapshot.")
        st.json(snapshot["errors"])
    else:
        st.success("All public providers used by this terminal snapshot responded successfully.")
