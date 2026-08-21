from __future__ import annotations

from cakrawala.data.providers.binance import fetch_klines
from cakrawala.data.providers.bmkg import fetch_latest_earthquake
from cakrawala.data.providers.world_bank import fetch_indicator
from cakrawala.observability.source_health import run_check


def main() -> int:
    checks = [
        run_check("bmkg_earthquake", fetch_latest_earthquake),
        run_check("world_bank", lambda: fetch_indicator("IDN", "SP.POP.TOTL", "2024")),
        run_check("binance_market_data", lambda: fetch_klines("BTCUSDT", limit=2)),
    ]
    for item in checks:
        print(f"{item.name}: {item.status} ({item.detail})")
    return 0 if all(item.status == "healthy" for item in checks) else 1


if __name__ == "__main__":
    raise SystemExit(main())
