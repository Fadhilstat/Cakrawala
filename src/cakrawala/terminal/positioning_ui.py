from __future__ import annotations

from typing import Any

import pandas as pd
import streamlit as st

from cakrawala.terminal.trading_ui import render_positioning


def _signed(value: float | None) -> str:
    if value is None:
        return "N/A"
    return f"{value:+,.0f}"


def render_positioning_hub(snapshot: dict[str, Any]) -> None:
    crowd_tab, institutional_tab = st.tabs(["Crowd Futures", "Institutional COT"])

    with crowd_tab:
        render_positioning(snapshot)

    with institutional_tab:
        st.subheader("Institutional Positioning")
        st.write(
            "CFTC Traders in Financial Futures membantu melihat perubahan posisi kategori "
            "institusi. Data ini mingguan dan tidak boleh diperlakukan sebagai sinyal intraday."
        )
        cot = snapshot.get("cot") or []
        if not cot:
            st.warning("CFTC TFF positioning sedang tidak tersedia untuk market yang dipantau.")
            return

        rows = []
        for item in cot:
            rows.append(
                {
                    "Market": item["market"],
                    "Report date": item["report_date"].strftime("%d %b %Y"),
                    "Open interest": item["open_interest"],
                    "Asset manager net": item["asset_manager_net"],
                    "WoW asset manager": item["asset_manager_change"],
                    "Leveraged funds net": item["leveraged_funds_net"],
                    "WoW leveraged": item["leveraged_funds_change"],
                    "Dealer net": item["dealer_net"],
                    "Source": item["source_url"],
                }
            )
        frame = pd.DataFrame(rows)
        display = frame.copy()
        for column in (
            "Open interest",
            "Asset manager net",
            "WoW asset manager",
            "Leveraged funds net",
            "WoW leveraged",
            "Dealer net",
        ):
            display[column] = display[column].map(
                lambda value: _signed(float(value)) if pd.notna(value) else "N/A"
            )
        st.dataframe(
            display,
            use_container_width=True,
            hide_index=True,
            column_config={"Source": st.column_config.LinkColumn("Official CFTC")},
        )
        st.caption(
            "Net positions are long minus short for each CFTC category. Weekly changes compare "
            "the latest available report with the previous configured observation."
        )
        st.info(
            "Institutional positioning adds context to a thesis. It does not override price, "
            "event risk, model health, or the execution policy."
        )
