from __future__ import annotations

import streamlit as st


st.set_page_config(page_title="Cakrawala Intelligence Terminal", layout="wide")

st.title("Cakrawala Intelligence Terminal")
st.caption("Open intelligence for Indonesia and the world")

st.info(
    "Public Mode is designed for transparent public evidence. Personal Mode remains owner-only "
    "and is activated only when production identity and database secrets are configured."
)

public_tab, personal_tab = st.tabs(["Public Mode", "Personal Mode"])

with public_tab:
    st.subheader("Public evidence")
    st.write(
        "Cakrawala brings together approved public sources while keeping freshness, provenance, "
        "and uncertainty visible. Live production data appears only after deployment credentials "
        "and persistent storage are configured."
    )
    st.caption("BMKG attribution is required when BMKG data is displayed.")
    st.caption(
        "This product uses the FRED API but is not endorsed or certified by the Federal Reserve "
        "Bank of St. Louis."
    )

with personal_tab:
    st.subheader("Owner research terminal")
    st.warning(
        "Personal Mode fails closed in this public build. Owner OIDC and private database roles "
        "must be configured server-side before access is enabled."
    )
    st.write(
        "Signals are deterministic research outputs from versioned policy and stored predictions. "
        "The language model may explain evidence, but it cannot create or override a signal."
    )
