from __future__ import annotations

from cakrawala.data.providers.binance import fetch_klines
from cakrawala.data.providers.binance_futures import fetch_futures_positioning
from cakrawala.data.providers.bls_calendar import fetch_bls_calendar
from cakrawala.data.providers.bmkg import fetch_latest_earthquake
from cakrawala.data.providers.cftc import fetch_tff_market
from cakrawala.data.providers.ecb_fx import fetch_currency_strength
from cakrawala.data.providers.news_feeds import fetch_macro_news
from cakrawala.data.providers.world_bank import fetch_indicator
from cakrawala.observability.source_health import run_check


def main() -> int:
    checks = [
        run_check("bmkg_earthquake", fetch_latest_earthquake),
        run_check("world_bank", lambda: fetch_indicator("IDN", "SP.POP.TOTL", "2024")),
        run_check("binance_market_data", lambda: fetch_klines("BTCUSDT", limit=2)),
        run_check("binance_futures", lambda: fetch_futures_positioning("BTCUSDT")),
        run_check("ecb_fx_reference_rates", fetch_currency_strength),
        run_check("federal_reserve_bis_news", lambda: fetch_macro_news(limit_per_source=2)),
        run_check("bls_calendar", fetch_bls_calendar),
        run_check("cftc_tff", lambda: fetch_tff_market("EURO FX")),
    ]
    for item in checks:
        print(f"{item.name}: {item.status} ({item.detail})")
    return 0 if all(item.status == "healthy" for item in checks) else 1


if __name__ == "__main__":
    raise SystemExit(main())
