from __future__ import annotations

from dataclasses import asdict
from math import sqrt

import pandas as pd
import plotly.express as px
import streamlit as st

from cakrawala.intelligence.trader_tools import (
    compound_projection,
    pip_or_tick_value,
    position_pnl,
    prop_risk_budget,
)


@st.cache_data(ttl=900, show_spinner=False)
def _fx_strength() -> list[dict[str, object]]:
    from cakrawala.data.providers.ecb_fx import fetch_currency_strength

    result = fetch_currency_strength()
    return [asdict(item) for item in result.data]


@st.cache_data(ttl=300, show_spinner=False)
def _crypto_universe() -> pd.DataFrame:
    from cakrawala.data.providers.binance import fetch_klines

    rows: list[dict[str, object]] = []
    for symbol in ("BTCUSDT", "ETHUSDT", "BNBUSDT", "SOLUSDT"):
        result = fetch_klines(symbol, interval="1d", limit=31)
        closes = [
            float(row[4])
            for row in result.data
            if isinstance(row, list) and len(row) > 4
        ]
        if len(closes) < 2:
            continue
        series = pd.Series(closes, dtype="float64")
        returns = series.pct_change().dropna()
        rows.append(
            {
                "symbol": symbol,
                "close": closes[-1],
                "change_1d_pct": (closes[-1] / closes[-2] - 1) * 100,
                "momentum_30d_pct": (closes[-1] / closes[0] - 1) * 100,
                "volatility_30d_pct": float(returns.std(ddof=1) * sqrt(365) * 100),
                "returns": returns.tolist(),
            }
        )
    if not rows:
        raise ValueError("No crypto market rows were available")
    return pd.DataFrame(rows)


def render_market_desk() -> None:
    st.subheader("Market Desk")
    st.write(
        "Ringkas currency strength, crypto breadth, correlation, dan regime risk dalam satu layar. "
        "Semua angka bersifat research context, bukan instruksi transaksi."
    )

    fx_tab, crypto_tab = st.tabs(["Currency Strength", "Crypto Breadth"])
    with fx_tab:
        try:
            frame = pd.DataFrame(_fx_strength())
        except Exception as exc:
            st.warning(f"ECB currency strength belum tersedia: {type(exc).__name__}")
        else:
            st.caption(
                "Sumber: European Central Bank reference rates. Nilai ini untuk konteks riset, "
                "bukan harga transaksi."
            )
            columns = [
                "currency",
                "change_1d_pct",
                "change_5d_pct",
                "change_20d_pct",
                "as_of",
            ]
            st.dataframe(frame[columns], use_container_width=True, hide_index=True)
            chart = frame.sort_values("change_5d_pct")
            st.plotly_chart(
                px.bar(chart, x="change_5d_pct", y="currency", orientation="h"),
                use_container_width=True,
            )

    with crypto_tab:
        try:
            frame = _crypto_universe()
        except Exception as exc:
            st.warning(f"Crypto breadth belum tersedia: {type(exc).__name__}")
            return
        columns = [
            "symbol",
            "close",
            "change_1d_pct",
            "momentum_30d_pct",
            "volatility_30d_pct",
        ]
        st.dataframe(frame[columns], use_container_width=True, hide_index=True)
        momentum_positive = int((frame["momentum_30d_pct"] > 0).sum())
        average_vol = float(frame["volatility_30d_pct"].mean())
        regime = "RISK ON" if momentum_positive >= 3 and average_vol < 80 else "CAUTIOUS"
        if momentum_positive <= 1:
            regime = "RISK OFF"
        left, right = st.columns(2)
        left.metric("Crypto breadth", f"{momentum_positive}/{len(frame)} positive")
        right.metric("Research regime", regime)
        st.caption(
            "Desk regime memakai rule transparan: breadth positif minimal 3 dari 4 dan "
            "rata-rata volatilitas tahunan di bawah 80% untuk RISK ON. Ini bukan signal."
        )

        returns = pd.DataFrame(
            {
                row["symbol"]: pd.Series(row["returns"], dtype="float64")
                for _, row in frame.iterrows()
            }
        )
        corr = returns.corr().round(2)
        st.markdown("### 30D correlation")
        st.dataframe(corr, use_container_width=True)
        st.caption(
            "Correlation membantu mendeteksi posisi yang terlihat berbeda tetapi membawa risiko "
            "yang sama. Nilai historis dapat berubah saat regime berubah."
        )


def render_trader_tools() -> None:
    st.subheader("Trader Toolkit")
    st.write("Calculator lokal tanpa API berbayar. Tidak ada tombol yang mengirim order.")

    pip_tab, pnl_tab, compound_tab, prop_tab, checklist_tab = st.tabs(
        ["Pip Value", "Position PnL", "Compound", "Prop Risk", "Checklist"]
    )
    with pip_tab:
        lot_size = st.number_input("Units per lot", min_value=1.0, value=100000.0)
        pip_size = st.number_input(
            "Pip or tick size",
            min_value=0.000001,
            value=0.0001,
            format="%.6f",
        )
        lots = st.number_input("Lots", min_value=0.0, value=0.1, step=0.01)
        quote_to_account = st.number_input(
            "Quote currency to account conversion",
            min_value=0.000001,
            value=1.0,
            format="%.6f",
        )
        pip_value = pip_or_tick_value(
            units_per_lot=lot_size,
            tick_size=pip_size,
            lots=lots,
            quote_to_account=quote_to_account,
        )
        st.metric("Approximate pip or tick value", f"{pip_value:,.2f}")

    with pnl_tab:
        side = st.selectbox("Side", ["LONG", "SHORT"], key="pnl_side")
        entry = st.number_input("Entry price", min_value=0.000001, value=100.0, key="pnl_entry")
        exit_price = st.number_input(
            "Exit price",
            min_value=0.000001,
            value=102.0,
            key="pnl_exit",
        )
        quantity = st.number_input("Quantity", min_value=0.0, value=1.0, key="pnl_qty")
        value = position_pnl(
            side=side,
            entry=entry,
            exit_price=exit_price,
            quantity=quantity,
        )
        st.metric("Gross PnL", f"{value:+,.2f}")

    with compound_tab:
        capital = st.number_input("Starting capital", min_value=1.0, value=10000.0)
        monthly = st.number_input("Monthly change assumption (%)", value=2.0, step=0.25)
        months = st.slider("Months", 1, 60, 12)
        try:
            projected = compound_projection(
                starting_capital=capital,
                period_change_percent=monthly,
                periods=months,
            )
        except ValueError as exc:
            st.warning(str(exc))
        else:
            st.metric("Deterministic projection", f"{projected:,.2f}")
        st.caption("Ini ilustrasi matematika, bukan forecast return.")

    with prop_tab:
        equity = st.number_input("Evaluation equity", min_value=1.0, value=100000.0)
        daily_limit = st.number_input("Max daily loss (%)", min_value=0.1, value=5.0)
        total_limit = st.number_input("Max total loss (%)", min_value=0.1, value=10.0)
        planned_risk = st.number_input(
            "Planned risk per trade (%)",
            min_value=0.1,
            value=1.0,
        )
        current_daily_pnl = st.number_input("Current daily PnL", value=0.0)
        budget = prop_risk_budget(
            equity=equity,
            daily_loss_limit_percent=daily_limit,
            total_loss_limit_percent=total_limit,
            planned_risk_percent=planned_risk,
            current_daily_pnl=current_daily_pnl,
        )
        cols = st.columns(3)
        cols[0].metric("Daily loss budget", f"{budget.daily_loss_budget:,.2f}")
        cols[1].metric("Remaining daily buffer", f"{budget.remaining_daily_buffer:,.2f}")
        cols[2].metric(
            "Full-risk losses to daily cap",
            f"{budget.full_risk_losses_to_daily_cap:.1f}",
        )
        st.caption(
            f"Total evaluation loss budget: {budget.total_loss_budget:,.2f}. "
            "Rules differ by provider, so enter the limits that actually apply."
        )

    with checklist_tab:
        items = [
            "Thesis jelas",
            "Invalidation jelas",
            "Event risk sudah dicek",
            "Position size sesuai batas risiko",
            "Tidak mengejar move yang sudah jauh",
            "News dan positioning tidak bertentangan ekstrem",
            "Rencana exit sudah tertulis",
        ]
        passed = sum(
            st.checkbox(item, key=f"check_{index}")
            for index, item in enumerate(items)
        )
        st.progress(passed / len(items))
        if passed == len(items):
            st.success(
                "Checklist lengkap. Tetap jalankan model, freshness, dan authorization gate."
            )
        else:
            st.info(
                f"{passed}/{len(items)} checklist selesai. "
                "Belum siap dianggap execution-ready."
            )
