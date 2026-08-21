from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

import pandas as pd
import plotly.express as px
import streamlit as st

from cakrawala.intelligence.bias import BiasInput, assess_research_bias
from cakrawala.intelligence.risk import build_position_plan, expectancy_r, projected_equity
from cakrawala.intelligence.sessions import current_sessions
from cakrawala.terminal.public_data import market_risk_stats


def render_positioning(snapshot: dict[str, Any]) -> None:
    st.subheader("Positioning & Crowding")
    st.write(
        "Crowding membantu melihat apakah pasar futures terlalu berat di satu sisi. "
        "Data ini adalah konteks, bukan sinyal untuk melawan crowd secara otomatis."
    )
    futures = snapshot.get("futures")
    if not futures:
        st.warning("Binance futures positioning sedang tidak tersedia.")
        return

    latest = futures["latest"]
    funding_pct = float(latest["last_funding_rate"]) * 100
    metrics = st.columns(5)
    metrics[0].metric("Long accounts", f"{float(latest['long_account']) * 100:.1f}%")
    metrics[1].metric("Short accounts", f"{float(latest['short_account']) * 100:.1f}%")
    metrics[2].metric("Long/short ratio", f"{float(latest['long_short_ratio']):.2f}")
    metrics[3].metric("Open interest", f"{float(latest['open_interest']):,.2f}")
    metrics[4].metric("Funding", f"{funding_pct:.4f}%")

    history_rows = []
    for row in futures.get("ratio_history", []):
        history_rows.append(
            {
                "time": pd.to_datetime(int(row["timestamp"]), unit="ms", utc=True),
                "Long": float(row["longAccount"]) * 100,
                "Short": float(row["shortAccount"]) * 100,
            }
        )
    if history_rows:
        frame = pd.DataFrame(history_rows).melt(
            id_vars="time",
            value_vars=["Long", "Short"],
            var_name="side",
            value_name="percent",
        )
        figure = px.line(frame, x="time", y="percent", color="side")
        figure.update_layout(
            height=360,
            margin=dict(l=10, r=10, t=10, b=10),
            xaxis_title=None,
            yaxis_title="Accounts (%)",
            legend_title=None,
        )
        st.plotly_chart(figure, use_container_width=True)

    long_share = float(latest["long_account"])
    if long_share >= 0.68:
        st.warning(
            "Long positioning is crowded. Treat this as a risk flag and recheck price, "
            "funding, news, and model evidence before acting."
        )
    elif long_share <= 0.32:
        st.warning(
            "Short positioning is crowded. Treat this as a risk flag and recheck price, "
            "funding, news, and model evidence before acting."
        )
    else:
        st.info("Crowd positioning is not at the terminal's current extreme threshold.")

    with st.expander("Source details"):
        for label, source in futures.get("sources", {}).items():
            st.caption(f"{label}: {source}")
        st.caption(
            "Binance global long/short ratios cover public USD-M futures positioning and are "
            "limited to recent history by the provider."
        )


def render_events(snapshot: dict[str, Any]) -> None:
    st.subheader("Economic Calendar & Event Risk")
    st.write(
        "Kalender dipakai untuk menghindari eksekusi buta menjelang rilis data penting. "
        "Versi gratis saat ini memakai jadwal resmi U.S. Bureau of Labor Statistics."
    )
    events = snapshot.get("calendar") or []
    if not events:
        st.warning("Tidak ada event BLS yang berhasil dimuat untuk 14 hari ke depan.")
        return

    now = datetime.now(UTC)
    rows = []
    for event in events:
        starts_at = event["starts_at"]
        hours = (starts_at - now).total_seconds() / 3600
        rows.append(
            {
                "UTC": starts_at.strftime("%d %b %Y %H:%M"),
                "Event": event["title"],
                "Time to event": f"{hours:.1f} h" if hours < 48 else f"{hours / 24:.1f} d",
                "Source": event["source"],
                "Link": event["link"],
            }
        )
    st.dataframe(
        pd.DataFrame(rows),
        use_container_width=True,
        hide_index=True,
        column_config={"Link": st.column_config.LinkColumn("Official link")},
    )
    nearest = events[0]
    hours_to_nearest = (nearest["starts_at"] - now).total_seconds() / 3600
    if hours_to_nearest <= 24:
        st.warning(
            "A scheduled BLS release is within 24 hours. Recheck spreads, volatility, "
            "position size, and whether the setup should wait until after the release."
        )


def render_research_desk(snapshot: dict[str, Any]) -> None:
    st.subheader("Research Desk")
    st.write(
        "Satu tempat untuk menyatukan sesi pasar, price context, crowding, news risk, dan bias "
        "riset yang transparan. Bias ini bukan trade signal."
    )

    sessions = current_sessions()
    session_columns = st.columns(3)
    for column, session in zip(session_columns, sessions, strict=True):
        column.metric(session.name, "OPEN" if session.is_open else "CLOSED")
        column.caption(f"Local hour: {session.local_hour:02d}:00")

    market = snapshot.get("market")
    futures = snapshot.get("futures")
    news = snapshot.get("news") or []
    risk = market_risk_stats(market["frame"]) if market else {}
    latest_futures = futures["latest"] if futures else {}
    high_attention = sum(item["attention_score"] >= 5 for item in news)
    assessment = assess_research_bias(
        BiasInput(
            momentum_30d_pct=risk.get("momentum"),
            drawdown_pct=risk.get("drawdown"),
            volatility_30d_pct=risk.get("volatility"),
            long_account=float(latest_futures["long_account"]) if latest_futures else None,
            funding_rate=float(latest_futures["last_funding_rate"]) if latest_futures else None,
            high_attention_news=high_attention,
        )
    )

    left, right = st.columns([1, 1.4])
    with left:
        st.markdown("### Bias board")
        st.metric("Research bias", assessment.label)
        st.metric("Evidence confidence", assessment.confidence.upper())
        st.caption(f"Transparent score: {assessment.score:+d}")
    with right:
        st.markdown("### Why")
        for reason in assessment.reasons:
            st.write(f"- {reason}")
        st.caption(
            "This board uses transparent rules only. It does not replace model promotion or the "
            "deterministic execution policy."
        )


def render_risk_tools() -> None:
    st.subheader("Risk & Position Toolkit")
    st.write(
        "Hitung ukuran posisi dari risiko yang bersedia ditanggung. "
        "Calculator tidak mengirim order."
    )

    left, right = st.columns([1, 1])
    with left:
        account_size = st.number_input("Account size", min_value=1.0, value=10000.0, step=500.0)
        risk_percent = st.number_input(
            "Risk per trade (%)",
            min_value=0.1,
            max_value=10.0,
            value=1.0,
            step=0.1,
        )
        entry = st.number_input("Entry", min_value=0.000001, value=100.0, format="%.6f")
        stop = st.number_input("Stop", min_value=0.000001, value=98.0, format="%.6f")
        target = st.number_input("Target", min_value=0.000001, value=104.0, format="%.6f")
        try:
            plan = build_position_plan(
                account_size=account_size,
                risk_percent=risk_percent,
                entry=entry,
                stop=stop,
                target=target,
            )
        except ValueError as exc:
            st.warning(str(exc))
        else:
            metrics = st.columns(3)
            metrics[0].metric("Risk amount", f"{plan.risk_amount:,.2f}")
            metrics[1].metric("Quantity", f"{plan.quantity:,.4f}")
            rr_text = "N/A" if plan.reward_risk is None else f"{plan.reward_risk:.2f} R"
            metrics[2].metric("Reward/risk", rr_text)

    with right:
        win_rate = st.slider("Historical win rate (%)", 0, 100, 45)
        avg_win = st.number_input("Average win (R)", min_value=0.0, value=2.0, step=0.1)
        avg_loss = st.number_input("Average loss (R)", min_value=0.0, value=1.0, step=0.1)
        trades = st.slider("Projection trades", 10, 200, 50)
        expectancy = expectancy_r(
            win_rate_percent=float(win_rate),
            average_win_r=avg_win,
            average_loss_r=avg_loss,
        )
        curve = projected_equity(
            starting_equity=account_size,
            risk_percent=risk_percent,
            expectancy_per_trade_r=expectancy,
            trades=trades,
        )
        st.metric("Historical expectancy", f"{expectancy:+.2f} R/trade")
        projection = pd.DataFrame({"trade": range(len(curve)), "expected_equity": curve})
        figure = px.line(projection, x="trade", y="expected_equity")
        figure.update_layout(
            height=300,
            margin=dict(l=10, r=10, t=10, b=10),
            xaxis_title="Trade",
            yaxis_title="Expected equity",
        )
        st.plotly_chart(figure, use_container_width=True)
        st.caption(
            "The curve is a deterministic expectancy illustration, not a forecast of "
            "actual returns."
        )
