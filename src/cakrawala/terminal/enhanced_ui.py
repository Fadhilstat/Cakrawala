from __future__ import annotations

from datetime import UTC, datetime

import streamlit as st

from cakrawala.terminal.overview_ui import render_overview
from cakrawala.terminal.personal_ui import render_personal_workspace
from cakrawala.terminal.positioning_ui import render_positioning_hub
from cakrawala.terminal.public_data import public_snapshot
from cakrawala.terminal.trading_ui import (
    render_events,
    render_research_desk,
    render_risk_tools,
)
from cakrawala.terminal.ui import (
    _execution,
    _header,
    _macro,
    _market,
    _news_research,
    _tool_radar,
)

_WORKSPACES = (
    "Overview",
    "News & Research",
    "Positioning",
    "Market Structure",
    "Macro & Events",
    "Research Desk",
    "Risk Tools",
    "Bot & Tool Radar",
    "Execution Readiness",
)


def _render_public_workspace(page: str, snapshot: dict[str, object]) -> None:
    if page == "Overview":
        render_overview(snapshot)
    elif page == "News & Research":
        _news_research(snapshot)
    elif page == "Positioning":
        render_positioning_hub(snapshot)
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
        st.caption("Public: evidence, research, positioning, and risk tools")
        st.caption("Personal: plans, journal, playbook, private portfolio")
        if st.button("Refresh evidence", use_container_width=True):
            st.cache_data.clear()
            st.rerun()

    if mode == "Personal Mode":
        render_personal_workspace()
        return

    snapshot = public_snapshot()
    page = st.selectbox(
        "Workspace",
        _WORKSPACES,
        label_visibility="collapsed",
    )
    st.divider()
    _render_public_workspace(page, snapshot)

    with st.expander("System status"):
        st.write(f"Snapshot: {datetime.now(UTC).isoformat()}")
        if snapshot["errors"]:
            st.warning("Some public sources are unavailable in this snapshot.")
            st.json(snapshot["errors"])
        else:
            st.success("All public sources used in this snapshot responded successfully.")
