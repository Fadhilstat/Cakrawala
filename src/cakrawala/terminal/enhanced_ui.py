from __future__ import annotations

from datetime import UTC, datetime
from importlib.resources import files
from typing import Any

import streamlit as st

from cakrawala.terminal.ai_council_ui import render_ai_council
from cakrawala.terminal.desk_v2 import render_market_desk, render_trader_tools
from cakrawala.terminal.overview_ui import render_overview
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
    "AI Research Council",
    "News & Research",
    "Positioning",
    "Market Desk",
    "Market Structure",
    "Macro & Events",
    "Research Desk",
    "Risk Tools",
    "Trader Toolkit",
    "Bot & Tool Radar",
    "Execution Readiness",
)

_WORKSPACE_LABELS = {
    "Command / Overview": "Overview",
    "Command / AI Research Council": "AI Research Council",
    "Intelligence / News & Research": "News & Research",
    "Intelligence / Positioning": "Positioning",
    "Markets / Market Desk": "Market Desk",
    "Markets / Market Structure": "Market Structure",
    "Markets / Macro & Events": "Macro & Events",
    "Research / Research Desk": "Research Desk",
    "Risk / Risk Tools": "Risk Tools",
    "Risk / Trader Toolkit": "Trader Toolkit",
    "Governance / Bot & Tool Radar": "Bot & Tool Radar",
    "Governance / Execution Readiness": "Execution Readiness",
}

_WORKSPACE_CONTEXT = {
    "Overview": (
        "Command center",
        "Kondisi pasar, kualitas sumber, dan perhatian utama dalam satu tampilan.",
    ),
    "AI Research Council": (
        "Evidence council",
        "Sintesis multi-peran yang tetap tunduk pada freshness, model, dan risk gate.",
    ),
    "News & Research": (
        "Official intelligence",
        "Berita resmi diprioritaskan untuk dibaca, diverifikasi, lalu diberi konteks.",
    ),
    "Positioning": (
        "Positioning monitor",
        "Crowding ritel dan positioning institusional ditampilkan tanpa mencampur definisi.",
    ),
    "Market Desk": (
        "Cross-asset desk",
        "Currency strength, breadth, korelasi, dan regime risk untuk riset harian.",
    ),
    "Market Structure": (
        "Price structure",
        "Pergerakan, volatilitas, volume, dan drawdown dari observasi yang tersedia.",
    ),
    "Macro & Events": (
        "Macro calendar",
        "Konteks makro dan event risk dengan kegagalan sumber yang tetap terlihat.",
    ),
    "Research Desk": (
        "Research workflow",
        "Ruang untuk mengubah evidence menjadi skenario yang dapat diuji.",
    ),
    "Risk Tools": (
        "Risk controls",
        "Perhitungan risiko yang membantu disiplin tanpa mengirim order broker.",
    ),
    "Trader Toolkit": (
        "Planning tools",
        "Kalkulator dan checklist lokal untuk memeriksa rencana sebelum mengambil keputusan.",
    ),
    "Bot & Tool Radar": (
        "Technology governance",
        "Kandidat alat dinilai berdasarkan lisensi, keamanan, biaya, dan bukti manfaat.",
    ),
    "Execution Readiness": (
        "Decision gate",
        "Evidence, freshness, model health, dan policy harus lolos sebelum bias digunakan.",
    ),
}

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


def _load_public_styles() -> None:
    stylesheet = files("app").joinpath("assets/public_terminal.css")
    try:
        css = stylesheet.read_text(encoding="utf-8")
    except OSError:
        return
    st.markdown(f"<style>{css}</style>", unsafe_allow_html=True)


def _source_health(snapshot: dict[str, Any]) -> tuple[int, int, str]:
    total = len(_PUBLIC_SOURCE_KEYS)
    healthy = sum(snapshot.get(key) is not None for key in _PUBLIC_SOURCE_KEYS)
    if healthy == total:
        return healthy, total, "OPERATIONAL"
    if healthy == 0:
        return healthy, total, "UNAVAILABLE"
    return healthy, total, "DEGRADED"


def _render_workspace_header(
    page: str,
    snapshot: dict[str, Any],
    snapshot_time: datetime,
) -> None:
    eyebrow, description = _WORKSPACE_CONTEXT[page]
    healthy, total, status = _source_health(snapshot)
    status_class = status.lower()
    st.markdown(
        f"""
        <section class="workspace-header" aria-labelledby="workspace-title">
            <div>
                <p class="workspace-eyebrow">{eyebrow}</p>
                <h2 id="workspace-title">{page}</h2>
                <p class="workspace-description">{description}</p>
            </div>
            <div class="workspace-status" aria-label="System status">
                <span class="status-dot {status_class}"></span>
                <span>{status}</span>
            </div>
        </section>
        <div class="evidence-strip" role="status">
            <div>
                <span class="evidence-label">Sumber aktif</span>
                <strong>{healthy}/{total}</strong>
            </div>
            <div>
                <span class="evidence-label">Snapshot UTC</span>
                <strong>{snapshot_time:%d %b %Y, %H:%M}</strong>
            </div>
            <div>
                <span class="evidence-label">Safety boundary</span>
                <strong>Decision support only</strong>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _render_system_status(
    snapshot: dict[str, Any],
    snapshot_time: datetime,
) -> None:
    healthy, total, status = _source_health(snapshot)
    with st.expander("System status and source diagnostics"):
        left, center, right = st.columns(3)
        left.metric("Source availability", f"{healthy}/{total}")
        center.metric("Runtime state", status)
        right.metric("Order execution", "DISABLED")
        st.caption(f"Snapshot dibuat {snapshot_time.isoformat()}.")
        if snapshot["errors"]:
            st.warning(
                "Sebagian sumber tidak tersedia. Cakrawala mempertahankan status gagal "
                "dan tidak membuat data pengganti."
            )
            st.json(snapshot["errors"])
        else:
            st.success("Semua sumber publik pada snapshot ini merespons dengan baik.")


def _render_public_workspace(page: str, snapshot: dict[str, object]) -> None:
    if page == "Overview":
        render_overview(snapshot)
    elif page == "AI Research Council":
        render_ai_council()
    elif page == "News & Research":
        _news_research(snapshot)
    elif page == "Positioning":
        render_positioning_hub(snapshot)
    elif page == "Market Desk":
        render_market_desk()
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
    elif page == "Trader Toolkit":
        render_trader_tools()
    elif page == "Bot & Tool Radar":
        _tool_radar()
    else:
        _execution(snapshot)


def run() -> None:
    st.set_page_config(
        page_title="Cakrawala Intelligence Terminal",
        page_icon="C",
        layout="wide",
        initial_sidebar_state="collapsed",
    )
    _load_public_styles()
    _header()

    with st.sidebar:
        st.markdown(
            """
            <div class="sidebar-brand">
                <span class="sidebar-mark">C</span>
                <div>
                    <strong>Cakrawala</strong>
                    <small>Public intelligence</small>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        st.divider()
        if st.button("Refresh evidence", use_container_width=True):
            st.cache_data.clear()
            st.rerun()
        st.caption(
            "Refresh mengambil ulang sumber publik. Kegagalan tetap ditampilkan "
            "dan tidak diganti dengan data sintetis."
        )

    selected_workspace = st.selectbox(
        "Pilih workspace",
        tuple(_WORKSPACE_LABELS),
        key="public_workspace",
    )
    page = _WORKSPACE_LABELS[selected_workspace]
    assert page in _WORKSPACES

    with st.spinner("Menyusun snapshot evidence..."):
        snapshot = public_snapshot()
    snapshot_time = datetime.now(UTC)
    _render_workspace_header(page, snapshot, snapshot_time)
    _render_public_workspace(page, snapshot)
    _render_system_status(snapshot, snapshot_time)
