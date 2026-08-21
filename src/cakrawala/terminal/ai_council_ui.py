from __future__ import annotations

import streamlit as st

from cakrawala.intelligence.ai_council import load_council_brief


def _list_items(items: tuple[str, ...], empty: str) -> None:
    if not items:
        st.caption(empty)
        return
    for item in items:
        st.markdown(f"- {item}")


def render_ai_council() -> None:
    st.subheader("AI Research Council")
    st.write(
        "Beberapa role analisis membaca evidence yang sama dari sudut berbeda. "
        "Hasilnya adalah research brief, bukan sinyal transaksi otomatis."
    )

    try:
        brief = load_council_brief()
    except Exception as exc:
        st.warning(
            "AI brief belum dapat divalidasi. Terminal tetap memakai evidence deterministik."
        )
        st.caption(f"Status teknis: {type(exc).__name__}")
        return

    fresh = brief.is_fresh()
    top = st.columns(4)
    top[0].metric("Brief status", "FRESH" if fresh else "STALE")
    top[1].metric("Research stance", brief.research_stance)
    top[2].metric("Analyst roles", len(brief.roles))
    top[3].metric("Verified sources", brief.source_count)

    if not fresh:
        st.warning(
            "Brief ini lebih lama dari freshness window. Gunakan sebagai konteks historis, "
            "bukan current research."
        )

    st.markdown("### Council synthesis")
    st.write(brief.headline or "Belum ada synthesis headline.")

    consensus_tab, disagreement_tab, risk_tab, next_tab = st.tabs(
        ["Consensus", "Disagreements", "Risk Flags", "Next Checks"]
    )
    with consensus_tab:
        _list_items(brief.consensus, "Belum ada konsensus yang tercatat.")
    with disagreement_tab:
        _list_items(brief.disagreements, "Tidak ada disagreement material yang tercatat.")
    with risk_tab:
        _list_items(brief.risk_flags, "Tidak ada risk flag tambahan dari AI brief.")
    with next_tab:
        _list_items(brief.next_checks, "Belum ada follow-up check.")

    st.markdown("### Analyst views")
    if not brief.roles:
        st.info("Scheduled research run pertama belum menerbitkan analyst views.")
    for role in brief.roles:
        with st.expander(f"{role.role} | confidence: {role.confidence}"):
            st.write(role.summary)
            st.markdown("**Evidence used**")
            _list_items(role.evidence, "Tidak ada evidence item yang tercatat.")
            st.markdown("**Risks and caveats**")
            _list_items(role.risks, "Tidak ada caveat tambahan yang tercatat.")

    if brief.citations:
        st.markdown("### Sources")
        for citation in brief.citations:
            st.markdown(f"- [{citation['label']}]({citation['url']})")

    st.divider()
    st.caption(
        f"Generated {brief.generated_at.isoformat()} | as of {brief.as_of} | {brief.status}"
    )
    st.info(
        brief.signal_policy_note
        or "AI analysis cannot create or replace Cakrawala's deterministic signal policy."
    )
