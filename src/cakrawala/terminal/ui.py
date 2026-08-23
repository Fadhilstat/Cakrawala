from __future__ import annotations

from typing import Any

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from cakrawala.config import load_yaml
from cakrawala.terminal.public_data import market_risk_stats


def _number(value: float | int | None, digits: int = 2) -> str:
    if value is None:
        return "N/A"
    return f"{value:,.{digits}f}"


def _percent(value: float | None, digits: int = 2) -> str:
    if value is None:
        return "N/A"
    return f"{value:+.{digits}f}%"


def _header() -> None:
    st.markdown(
        """
        <style>
        .block-container {
            padding-top: 1.35rem;
            padding-bottom: 3rem;
            max-width: 1450px;
        }
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
        .terminal-lead {
            max-width: 980px;
            opacity: 0.78;
            line-height: 1.6;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )
    st.markdown(
        '<div class="terminal-kicker">Evidence first research terminal</div>',
        unsafe_allow_html=True,
    )
    st.title("Cakrawala Intelligence Terminal")
    st.markdown(
        '<div class="terminal-lead">'
        "News, macro, market structure, risk, dan tool research disatukan dalam "
        "satu alur. Signal hanya dianggap valid setelah data, model, dan policy "
        "lolos gate."
        "</div>",
        unsafe_allow_html=True,
    )


def _source_count(snapshot: dict[str, Any]) -> str:
    total = 6
    return f"{total - len(snapshot['errors'])}/{total}"


def _overview(snapshot: dict[str, Any]) -> None:
    market = snapshot.get("market")
    earthquake = snapshot.get("earthquake")
    inflation = snapshot.get("inflation")
    news = snapshot.get("news") or []
    risk = market_risk_stats(market["frame"]) if market else {}

    metrics = st.columns(6)
    metrics[0].metric("Sources", _source_count(snapshot))
    metrics[1].metric(
        "BTC 1D",
        _percent(market["latest"]["change_1d_pct"]) if market else "N/A",
    )
    metrics[2].metric("30D momentum", _percent(risk.get("momentum")))
    volatility = risk.get("volatility")
    metrics[3].metric(
        "30D annualized vol",
        f"{volatility:.1f}%" if volatility is not None else "N/A",
    )
    magnitude = earthquake.get("magnitude") if earthquake else None
    metrics[4].metric("Latest quake", f"M {magnitude}" if magnitude else "N/A")
    high_attention = sum(item["attention_score"] >= 5 for item in news)
    metrics[5].metric("News watch", str(high_attention))

    left, right = st.columns([1.5, 1])
    with left:
        st.markdown("### Market pulse")
        if market:
            frame = market["frame"].tail(45)
            figure = px.line(frame, x="time", y="close")
            figure.update_layout(
                height=330,
                margin=dict(l=10, r=10, t=10, b=10),
                xaxis_title=None,
                yaxis_title="BTC/USDT",
                showlegend=False,
            )
            st.plotly_chart(figure, use_container_width=True)
        else:
            st.warning("Market source sedang tidak tersedia.")

    with right:
        st.markdown("### Today at a glance")
        if inflation:
            latest = inflation["latest"]
            st.write(
                f"**Inflation Indonesia:** {latest['value']:.2f}% "
                f"({latest['year']})"
            )
        if earthquake:
            st.write(
                f"**BMKG:** M {earthquake.get('magnitude', 'N/A')} | "
                f"{earthquake.get('depth', 'N/A')}"
            )
            st.caption(earthquake.get("region") or "Wilayah belum tersedia")
        if news:
            top_item = news[0]
            st.write(f"**Top news watch:** {top_item['title']}")
            st.caption(top_item["watch_reason"])
        st.divider()
        st.caption(
            "Overview bersifat deskriptif. Signal eksekusi tetap terpisah dan "
            "harus lolos evidence gate."
        )


def _news_research(snapshot: dict[str, Any]) -> None:
    st.subheader("News & Daily Research")
    st.write(
        "Headline resmi dipakai sebagai evidence tambahan. Skor perhatian membantu "
        "prioritas baca, bukan memprediksi arah harga."
    )
    news = snapshot.get("news") or []
    if not news:
        st.warning("Feed Federal Reserve atau BIS belum dapat dimuat.")
        return

    query = st.text_input(
        "Search headlines",
        placeholder="rates, liquidity, regulation, stablecoin...",
    )
    available_tags = sorted({tag for item in news for tag in item["tags"]})
    selected_tags = st.multiselect("Filter themes", available_tags)

    filtered = []
    for item in news:
        if query and query.lower() not in item["title"].lower():
            continue
        if selected_tags and not any(tag in item["tags"] for tag in selected_tags):
            continue
        filtered.append(item)

    left, right = st.columns([1.6, 1])
    with left:
        st.markdown("### Headline monitor")
        for item in filtered[:12]:
            published = item["published_at"]
            published_text = "time unavailable"
            if published:
                published_text = published.strftime("%d %b %Y %H:%M UTC")
            st.markdown(f"**{item['title']}**")
            st.caption(
                f"{item['source']} | attention {item['attention_score']}/10 | "
                f"{', '.join(item['tags'])} | {published_text}"
            )
            st.write(item["watch_reason"])
            st.link_button("Open source", item["link"])
            st.divider()

    with right:
        st.markdown("### Research brief")
        counts: dict[str, int] = {}
        for item in news:
            for tag in item["tags"]:
                counts[tag] = counts.get(tag, 0) + 1
        if counts:
            chart = pd.DataFrame(
                [{"theme": key, "headlines": value} for key, value in counts.items()]
            ).sort_values("headlines")
            figure = px.bar(
                chart,
                x="headlines",
                y="theme",
                orientation="h",
            )
            figure.update_layout(
                height=300,
                margin=dict(l=10, r=10, t=10, b=10),
                xaxis_title=None,
                yaxis_title=None,
                showlegend=False,
            )
            st.plotly_chart(figure, use_container_width=True)
        st.info(
            "Before execution, read the highest-attention headlines, compare them "
            "with market volatility, then recheck model freshness and signal policy."
        )
        st.caption(
            "Live feeds: Federal Reserve and BIS. Bank Indonesia remains an official "
            "source watch until a stable machine-readable interface is approved."
        )


def _market(snapshot: dict[str, Any]) -> None:
    st.subheader("Market Structure")
    market = snapshot.get("market")
    if not market:
        st.warning("Binance public market data sedang tidak tersedia.")
        return

    frame = market["frame"].copy()
    latest = market["latest"]
    risk = market_risk_stats(frame)
    volatility = risk["volatility"]

    metrics = st.columns(6)
    metrics[0].metric("BTC/USDT", _number(latest["close"]))
    metrics[1].metric("1D", _percent(latest["change_1d_pct"]))
    metrics[2].metric("30D momentum", _percent(risk["momentum"]))
    metrics[3].metric(
        "30D annualized vol",
        f"{volatility:.1f}%" if volatility is not None else "N/A",
    )
    metrics[4].metric("Drawdown", _percent(risk["drawdown"]))
    metrics[5].metric("Volume", _number(latest["volume"]))

    price_tab, returns_tab, range_tab = st.tabs(["Price", "Returns", "Range"])
    with price_tab:
        figure = go.Figure(
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
        figure.update_layout(
            height=470,
            xaxis_rangeslider_visible=False,
            margin=dict(l=10, r=10, t=10, b=10),
        )
        st.plotly_chart(figure, use_container_width=True)

    with returns_tab:
        returns = frame.dropna(subset=["return"]).copy()
        returns["return_pct"] = returns["return"] * 100
        figure = px.bar(returns, x="time", y="return_pct")
        figure.update_layout(
            height=400,
            margin=dict(l=10, r=10, t=10, b=10),
            xaxis_title=None,
        )
        st.plotly_chart(figure, use_container_width=True)

    with range_tab:
        ranges = frame.tail(30).copy()
        ranges["range_pct"] = (
            (ranges["high"] - ranges["low"]) / ranges["open"] * 100
        )
        figure = px.line(ranges, x="time", y="range_pct", markers=True)
        figure.update_layout(
            height=400,
            margin=dict(l=10, r=10, t=10, b=10),
            xaxis_title=None,
        )
        st.plotly_chart(figure, use_container_width=True)


def _macro(snapshot: dict[str, Any]) -> None:
    st.subheader("Indonesia & Macro")
    population = snapshot.get("population")
    gdp = snapshot.get("gdp")
    inflation = snapshot.get("inflation")

    metrics = st.columns(3)
    if population:
        latest = population["latest"]
        metrics[0].metric(
            "Population",
            f"{int(latest['value']):,}",
            str(latest["year"]),
        )
    else:
        metrics[0].metric("Population", "N/A")
    if gdp:
        latest = gdp["latest"]
        metrics[1].metric("GDP growth", f"{latest['value']:.2f}%", str(latest["year"]))
    else:
        metrics[1].metric("GDP growth", "N/A")
    if inflation:
        latest = inflation["latest"]
        metrics[2].metric("Inflation", f"{latest['value']:.2f}%", str(latest["year"]))
    else:
        metrics[2].metric("Inflation", "N/A")

    rows: list[dict[str, Any]] = []
    for label, payload in (("GDP growth", gdp), ("Inflation", inflation)):
        if not payload:
            continue
        rows.extend(
            {
                "year": row["year"],
                "value": row["value"],
                "series": label,
            }
            for row in payload["observations"]
        )
    if rows:
        chart = pd.DataFrame(rows)
        figure = px.line(
            chart,
            x="year",
            y="value",
            color="series",
            markers=True,
        )
        figure.update_layout(
            height=390,
            margin=dict(l=10, r=10, t=10, b=10),
            legend_title=None,
        )
        st.plotly_chart(figure, use_container_width=True)

    st.caption(
        "Official Indonesia source watch: Bank Indonesia and BPS remain part of "
        "the approved source universe."
    )


def _tool_radar() -> None:
    st.subheader("Bot & Tool Radar")
    st.write(
        "Setiap kandidat diperlakukan sebagai software pihak ketiga yang belum "
        "dipercaya. Radar membantu riset, bukan melakukan instalasi otomatis."
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
        "Weekly research may move a tool only to sandbox candidate. Production use "
        "still needs dependency review, secret isolation, paper trading, execution "
        "tests, and explicit approval."
    )


def _execution(snapshot: dict[str, Any]) -> None:
    st.subheader("Execution Readiness")
    models = load_yaml("configs/models.yaml")
    roles = models.get("roles", {})
    promotion = models.get("promotion", {})
    promoted = sum(value is not None for value in roles.values())
    news = snapshot.get("news") or []
    high_attention = sum(item["attention_score"] >= 5 for item in news)

    metrics = st.columns(5)
    metrics[0].metric("Market data", "LIVE" if snapshot.get("market") else "DOWN")
    metrics[1].metric("News feed", "LIVE" if snapshot.get("news") else "DOWN")
    metrics[2].metric("High-attention news", str(high_attention))
    metrics[3].metric("Model roles promoted", f"{promoted}/{len(roles)}")
    metrics[4].metric("Signal", "NO SIGNAL" if promoted == 0 else "POLICY CHECK")

    left, right = st.columns([1.2, 1])
    with left:
        st.markdown("### Pre-execution checklist")
        checklist = [
            ("Market source healthy", snapshot.get("market") is not None),
            ("News evidence loaded", snapshot.get("news") is not None),
            ("Provider failures visible", True),
            ("Model champion available", promoted > 0),
            ("Personal execution route authorized", False),
        ]
        for label, passed in checklist:
            st.write(f"{'OK' if passed else 'WAIT'}  {label}")

    with right:
        st.markdown("### Promotion policy")
        minimum_health = float(promotion.get("minimum_health", 0))
        improvement = float(promotion.get("minimum_relative_improvement", 0)) * 100
        st.write(f"Minimum health: **{minimum_health:.2f}**")
        st.write(f"Minimum benchmark improvement: **{improvement:.1f}%**")
        walk_forward = "Yes" if promotion.get("require_walk_forward") else "No"
        point_in_time = "Yes" if promotion.get("require_point_in_time_features") else "No"
        st.write(f"Walk-forward required: **{walk_forward}**")
        st.write(f"Point-in-time features required: **{point_in_time}**")

    if promoted == 0:
        st.warning(
            "Execution remains blocked. No model role has been promoted, so Cakrawala "
            "must not invent a BUY or SELL decision."
        )


def run() -> None:
    from cakrawala.terminal.enhanced_ui import run as run_public_terminal

    run_public_terminal()

