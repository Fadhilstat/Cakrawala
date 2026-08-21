from __future__ import annotations

from typing import Any, Callable

import streamlit as st

from cakrawala.data.providers.binance import fetch_klines
from cakrawala.data.providers.bmkg import earthquake_summary, fetch_latest_earthquake
from cakrawala.data.providers.world_bank import fetch_indicator


st.set_page_config(page_title="Cakrawala Intelligence Terminal", layout="wide")


@st.cache_data(ttl=600, show_spinner=False)
def load_earthquake() -> dict[str, Any]:
    result = fetch_latest_earthquake()
    summary = earthquake_summary(result.data)
    return {
        **summary,
        "fetched_at": result.provenance.fetched_at.isoformat(),
        "source_url": result.provenance.source_url,
    }


@st.cache_data(ttl=3600, show_spinner=False)
def load_population() -> dict[str, Any]:
    result = fetch_indicator("IDN", "SP.POP.TOTL", "2024")
    rows = result.data[1] if len(result.data) > 1 else []
    observation = next(
        (row for row in rows if isinstance(row, dict) and row.get("value") is not None),
        None,
    )
    if observation is None:
        raise ValueError("World Bank did not return a usable population observation")
    return {
        "country": observation.get("country", {}).get("value", "Indonesia"),
        "year": observation.get("date"),
        "value": observation.get("value"),
        "fetched_at": result.provenance.fetched_at.isoformat(),
        "source_url": result.provenance.source_url,
    }


@st.cache_data(ttl=300, show_spinner=False)
def load_market() -> dict[str, Any]:
    result = fetch_klines("BTCUSDT", interval="1d", limit=2)
    latest = result.data[-1]
    if not isinstance(latest, list) or len(latest) < 7:
        raise ValueError("Binance returned an unexpected kline row")
    return {
        "open": float(latest[1]),
        "high": float(latest[2]),
        "low": float(latest[3]),
        "close": float(latest[4]),
        "volume": float(latest[5]),
        "fetched_at": result.provenance.fetched_at.isoformat(),
        "source_url": result.provenance.source_url,
    }


def render_source_error(source_name: str, exc: Exception) -> None:
    st.warning(
        f"{source_name} belum bisa dimuat sekarang. Terminal tidak mengganti data yang gagal "
        "dengan angka sintetis."
    )
    st.caption(f"Status teknis: {type(exc).__name__}")


def render_panel(title: str, loader: Callable[[], dict[str, Any]], renderer: Callable[[dict[str, Any]], None]) -> None:
    st.subheader(title)
    try:
        payload = loader()
    except Exception as exc:
        render_source_error(title, exc)
        return
    renderer(payload)
    st.caption(f"Diambil: {payload['fetched_at']}")
    st.caption(f"Sumber: {payload['source_url']}")


def render_earthquake(payload: dict[str, Any]) -> None:
    col1, col2, col3 = st.columns(3)
    col1.metric("Magnitudo", payload.get("magnitude") or "N/A")
    col2.metric("Kedalaman", payload.get("depth") or "N/A")
    col3.metric("Waktu data", payload.get("datetime") or "N/A")
    st.write(payload.get("region") or "Wilayah belum tersedia.")
    st.caption(payload.get("potential") or "Informasi potensi belum tersedia.")
    st.caption("Sumber data: BMKG")


def render_population(payload: dict[str, Any]) -> None:
    value = payload.get("value")
    formatted = f"{int(value):,}" if isinstance(value, (int, float)) else "N/A"
    col1, col2 = st.columns(2)
    col1.metric("Populasi Indonesia", formatted)
    col2.metric("Tahun referensi", payload.get("year") or "N/A")
    st.caption("Nilai ini mengikuti tahun referensi yang tersedia dari World Bank, bukan estimasi real-time.")


def render_market(payload: dict[str, Any]) -> None:
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("BTC/USDT close", f"{payload['close']:,.2f}")
    col2.metric("High", f"{payload['high']:,.2f}")
    col3.metric("Low", f"{payload['low']:,.2f}")
    col4.metric("Volume", f"{payload['volume']:,.2f}")
    st.caption("Public market data only. This is evidence for research, not a trading instruction.")


st.title("Cakrawala Intelligence Terminal")
st.caption("Open intelligence for Indonesia and the world")

st.info(
    "Public Mode membaca sumber publik yang sudah disetujui dan tetap menunjukkan provenance. "
    "Personal Mode tetap tertutup sampai identitas owner dan database privat dikonfigurasi."
)

public_tab, personal_tab = st.tabs(["Public Mode", "Personal Mode"])

with public_tab:
    top_left, top_right = st.columns([4, 1])
    with top_left:
        st.write(
            "Terminal ini memilih untuk gagal secara terbuka ketika sumber sedang bermasalah. "
            "Data yang gagal dimuat tidak diganti dengan angka buatan."
        )
    with top_right:
        if st.button("Refresh evidence", use_container_width=True):
            st.cache_data.clear()
            st.rerun()

    disaster_tab, macro_tab, market_tab = st.tabs(["Disaster", "Macro", "Market"])

    with disaster_tab:
        render_panel("Gempa terbaru BMKG", load_earthquake, render_earthquake)

    with macro_tab:
        render_panel("Konteks populasi Indonesia", load_population, render_population)

    with market_tab:
        render_panel("Snapshot pasar publik", load_market, render_market)

with personal_tab:
    st.subheader("Owner research terminal")
    st.warning(
        "Personal Mode fail closed pada build publik. Google OIDC dan role database privat harus "
        "dikonfigurasi server-side sebelum akses owner diaktifkan."
    )
    st.write(
        "Signal adalah output riset deterministik dari policy yang terversi dan prediksi tersimpan. "
        "Model bahasa boleh menjelaskan evidence, tetapi tidak boleh membuat atau mengganti signal."
    )
    st.caption("Research use only. Model outputs and market signals are uncertain, not guarantees.")
