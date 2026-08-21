from __future__ import annotations

from typing import Any

import plotly.express as px
import streamlit as st

from cakrawala.terminal.public_data import market_risk_stats

_PUBLIC_SOURCE_KEYS = (
    "earthquake",
    "population",
    "gdp",
    "inflation",
    "market",
    "news",
    "futures",
    "calendar",
    "cot",
)


def render_overview(snapshot: dict[str, Any]) -> None:
    market = snapshot.get("market")
    earthquake = snapshot.get("earthquake")
    inflation = snapshot.get("inflation")
    futures = snapshot.get("futures")
    news = snapshot.get("news") or []
    risk = market_risk_stats(market["frame"]) if market else {}

    online = sum(snapshot.get(key) is not None for key in _PUBLIC_SOURCE_KEYS)
    metrics = st.columns(6)
    metrics[0].metric("Sources online", f"{online}/{len(_PUBLIC_SOURCE_KEYS)}")
    metrics[1].metric(
        "BTC 1D",
        f"{market['latest']['change_1d_pct']:+.2f}%" if market else "N/A",
    )
    momentum = risk.get("momentum")
    metrics[2].metric(
        "BTC 30D momentum",
        f"{momentum:+.2f}%" if momentum is not None else "N/A",
    )
    volatility = risk.get("volatility")
    metrics[3].metric(
        "BTC 30D vol",
        f"{volatility:.1f}%" if volatility is not None else "N/A",
    )
    long_share = None
    if futures:
        long_share = float(futures["latest"]["long_account"]) * 100
    metrics[4].metric(
        "Futures long",
        f"{long_share:.1f}%" if long_share is not None else "N/A",
    )
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
        if futures:
            funding = float(futures["latest"]["last_funding_rate"]) * 100
            st.write(f"**BTC funding:** {funding:+.4f}%")
        if news:
            top_item = news[0]
            st.write(f"**Top news watch:** {top_item['title']}")
            st.caption(top_item["watch_reason"])
        st.divider()
        st.caption(
            "Overview bersifat deskriptif. Bias riset, model, dan execution policy tetap "
            "dipisahkan agar satu indikator tidak berubah menjadi keputusan otomatis."
        )
