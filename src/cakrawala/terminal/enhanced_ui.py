from __future__ import annotations

from dataclasses import asdict
from datetime import UTC, datetime

import pandas as pd
import streamlit as st

from cakrawala.personal.storage import (
    add_journal_entry,
    add_playbook_entry,
    add_trade_plan,
    list_journal_entries,
    list_playbook_entries,
    list_portfolio_transactions,
    list_trade_plans,
)
from cakrawala.terminal.overview_ui import render_overview
from cakrawala.terminal.public_data import public_snapshot
from cakrawala.terminal.trading_ui import (
    render_events,
    render_positioning,
    render_research_desk,
    render_risk_tools,
)
from cakrawala.terminal.ui import (
    _execution,
    _header,
    _macro,
    _market,
    _news_research,
    _owner_config,
    _tool_radar,
)


def _personal_workspace() -> None:
    st.subheader("Owner Research Workspace")
    configured, owner_sub, database_url = _owner_config()
    if not configured:
        st.warning(
            "Personal Mode belum aktif. OIDC owner dan private database harus dikonfigurasi "
            "di Streamlit Secrets."
        )
        st.write(
            "Saat aktif, workspace ini menyimpan trade plan, journal, playbook, dan portfolio "
            "secara terpisah dari data publik."
        )
        return

    if not st.user.is_logged_in:
        st.button("Log in with Google", on_click=st.login, use_container_width=True)
        return
    if str(st.user.get("sub", "")) != owner_sub:
        st.error("Akun terautentikasi tetapi tidak memiliki akses owner.")
        st.button("Log out", on_click=st.logout)
        return

    top_left, top_right = st.columns([4, 1])
    top_left.success("Owner identity verified")
    top_right.button("Log out", on_click=st.logout, use_container_width=True)
    if not database_url:
        st.warning("Private database belum dikonfigurasi.")
        return

    portfolio_tab, plans_tab, journal_tab, playbook_tab = st.tabs(
        ["Portfolio", "Trade Plans", "Journal", "Playbook"]
    )

    with portfolio_tab:
        try:
            transactions = list_portfolio_transactions(database_url, owner_sub)
        except Exception as exc:
            st.warning("Portfolio ledger belum dapat dimuat.")
            st.caption(type(exc).__name__)
        else:
            if transactions:
                st.dataframe(
                    [asdict(item) for item in transactions],
                    use_container_width=True,
                    hide_index=True,
                )
            else:
                st.info("Belum ada transaksi pada private ledger.")

    with plans_tab:
        st.markdown("### Build a trade plan")
        with st.form("trade_plan_form"):
            asset = st.text_input("Asset", value="BTCUSDT")
            direction = st.selectbox("Direction", ["WAIT", "LONG", "SHORT"])
            risk_percent = st.number_input(
                "Risk budget (%)",
                min_value=0.1,
                max_value=10.0,
                value=1.0,
                step=0.1,
            )
            include_levels = st.checkbox("Include entry, stop, and target")
            entry = stop = target = None
            if include_levels:
                col1, col2, col3 = st.columns(3)
                entry = col1.number_input(
                    "Entry",
                    min_value=0.000001,
                    value=100.0,
                    format="%.6f",
                )
                stop = col2.number_input(
                    "Stop",
                    min_value=0.000001,
                    value=98.0,
                    format="%.6f",
                )
                target = col3.number_input(
                    "Target",
                    min_value=0.000001,
                    value=104.0,
                    format="%.6f",
                )
            thesis = st.text_area(
                "Thesis",
                placeholder="Apa yang harus benar agar setup ini layak?",
            )
            invalidation = st.text_area(
                "Invalidation",
                placeholder="Kondisi apa yang membuat ide ini batal?",
            )
            submitted = st.form_submit_button("Save plan")
        if submitted:
            try:
                add_trade_plan(
                    database_url,
                    owner_sub,
                    asset=asset,
                    direction=direction,
                    entry=entry,
                    stop=stop,
                    target=target,
                    risk_percent=risk_percent,
                    thesis=thesis,
                    invalidation=invalidation,
                )
            except Exception as exc:
                st.error(f"Trade plan tidak tersimpan: {type(exc).__name__}")
            else:
                st.success("Trade plan tersimpan sebagai immutable research record.")
                st.rerun()

        try:
            plans = list_trade_plans(database_url, owner_sub)
        except Exception as exc:
            st.caption(f"Plan history unavailable: {type(exc).__name__}")
        else:
            if plans:
                st.dataframe(
                    [asdict(item) for item in plans],
                    use_container_width=True,
                    hide_index=True,
                )

    with journal_tab:
        st.markdown("### Post-trade journal")
        with st.form("journal_form"):
            asset = st.text_input("Journal asset", value="BTCUSDT")
            direction = st.selectbox("Executed direction", ["LONG", "SHORT"])
            result_r = st.number_input("Result (R)", value=0.0, step=0.25)
            notes = st.text_area("What happened?")
            lesson = st.text_area("What will I repeat or change?")
            submitted = st.form_submit_button("Add journal entry")
        if submitted:
            try:
                add_journal_entry(
                    database_url,
                    owner_sub,
                    asset=asset,
                    direction=direction,
                    result_r=result_r,
                    notes=notes,
                    lesson=lesson,
                    executed_at=datetime.now(UTC),
                )
            except Exception as exc:
                st.error(f"Journal tidak tersimpan: {type(exc).__name__}")
            else:
                st.success("Journal entry tersimpan.")
                st.rerun()

        try:
            entries = list_journal_entries(database_url, owner_sub)
        except Exception as exc:
            st.caption(f"Journal history unavailable: {type(exc).__name__}")
        else:
            if entries:
                frame = pd.DataFrame([asdict(item) for item in entries])
                st.dataframe(frame, use_container_width=True, hide_index=True)
                st.metric("Average result", f"{frame['result_r'].astype(float).mean():+.2f} R")

    with playbook_tab:
        st.markdown("### Playbook")
        with st.form("playbook_form"):
            name = st.text_input("Setup name")
            setup = st.text_area("Market condition and setup")
            entry_rules = st.text_area("Entry rules")
            risk_rules = st.text_area("Risk rules")
            exit_rules = st.text_area("Exit rules")
            submitted = st.form_submit_button("Save playbook entry")
        if submitted:
            try:
                add_playbook_entry(
                    database_url,
                    owner_sub,
                    name=name,
                    setup=setup,
                    entry_rules=entry_rules,
                    risk_rules=risk_rules,
                    exit_rules=exit_rules,
                )
            except Exception as exc:
                st.error(f"Playbook tidak tersimpan: {type(exc).__name__}")
            else:
                st.success("Playbook entry tersimpan.")
                st.rerun()

        try:
            playbooks = list_playbook_entries(database_url, owner_sub)
        except Exception as exc:
            st.caption(f"Playbook unavailable: {type(exc).__name__}")
        else:
            for item in playbooks:
                with st.expander(item.name):
                    st.write(f"**Setup:** {item.setup}")
                    st.write(f"**Entry:** {item.entry_rules}")
                    st.write(f"**Risk:** {item.risk_rules}")
                    st.write(f"**Exit:** {item.exit_rules}")
                    st.caption(item.created_at.isoformat())


def run() -> None:
    st.set_page_config(
        page_title="Cakrawala Intelligence Terminal",
        page_icon="C",
        layout="wide",
        initial_sidebar_state="expanded",
    )
    _header()

    with st.sidebar:
        st.header("Cakrawala")
        mode = st.radio(
            "Access",
            ["Public Mode", "Personal Mode"],
            label_visibility="collapsed",
        )
        st.divider()
        st.caption("Public: evidence, research, and risk tools")
        st.caption("Personal: plans, journal, playbook, private portfolio")
        if st.button("Refresh evidence", use_container_width=True):
            st.cache_data.clear()
            st.rerun()

    if mode == "Personal Mode":
        _personal_workspace()
        return

    snapshot = public_snapshot()
    page = st.selectbox(
        "Workspace",
        [
            "Overview",
            "News & Research",
            "Positioning",
            "Market Structure",
            "Macro & Events",
            "Research Desk",
            "Risk Tools",
            "Bot & Tool Radar",
            "Execution Readiness",
        ],
        label_visibility="collapsed",
    )
    st.divider()

    if page == "Overview":
        render_overview(snapshot)
    elif page == "News & Research":
        _news_research(snapshot)
    elif page == "Positioning":
        render_positioning(snapshot)
    elif page == "Market Structure":
        _market(snapshot)
    elif page == "Macro & Events":
        macro_tab, events_tab = st.tabs(["Indonesia & Macro", "Event Risk"])
        with macro_tab:
            _macro(snapshot)
        with events_tab:
            render_events(snapshot)
    elif page == "Research Desk":
        render_research_desk(snapshot)
    elif page == "Risk Tools":
        render_risk_tools()
    elif page == "Bot & Tool Radar":
        _tool_radar()
    else:
        _execution(snapshot)

    with st.expander("System status"):
        st.write(f"Snapshot: {datetime.now(UTC).isoformat()}")
        if snapshot["errors"]:
            st.warning("Some public sources are unavailable in this snapshot.")
            st.json(snapshot["errors"])
        else:
            st.success("All public sources used in this snapshot responded successfully.")
