from __future__ import annotations

import argparse
import json
from dataclasses import asdict
from pathlib import Path

import pandas as pd

from cakrawala.data.providers.binance import fetch_klines
from cakrawala.models.direction_baseline import BacktestConfig, walk_forward_backtest
from cakrawala.models.promotion import PromotionEvidence, assess_promotion


def _frame_from_klines(rows: list[list[object]]) -> pd.DataFrame:
    if not rows:
        raise ValueError("Binance kline payload is empty")
    records: list[dict[str, object]] = []
    for row in rows:
        if len(row) < 6:
            raise ValueError("Binance kline row does not contain the required fields")
        records.append(
            {
                "open_time": pd.to_datetime(int(row[0]), unit="ms", utc=True),
                "open": float(row[1]),
                "high": float(row[2]),
                "low": float(row[3]),
                "close": float(row[4]),
                "volume": float(row[5]),
            }
        )
    return pd.DataFrame.from_records(records)


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the Cakrawala BTC direction baseline backtest")
    parser.add_argument("--symbol", default="BTCUSDT")
    parser.add_argument("--limit", type=int, default=1000)
    parser.add_argument("--output", default="artifacts/backtests/btc_direction_latest.json")
    args = parser.parse_args()

    provider_result = fetch_klines(args.symbol, interval="1d", limit=args.limit)
    frame = _frame_from_klines(provider_result.data)
    config = BacktestConfig()
    result = walk_forward_backtest(frame, config)
    promotion = assess_promotion(PromotionEvidence(**result.promotion_inputs))

    payload = result.to_dict()
    payload["symbol"] = args.symbol.upper()
    payload["source"] = {
        "provider": provider_result.provider,
        "url": provider_result.provenance.source_url,
        "fetched_at": provider_result.provenance.fetched_at.isoformat(),
        "sha256": provider_result.provenance.sha256,
        "byte_count": provider_result.provenance.byte_count,
    }
    payload["config"] = asdict(config)
    payload["promotion"] = {
        "promoted": promotion.promoted,
        "reasons": list(promotion.reasons),
    }
    payload["disclaimer"] = (
        "Research backtest only. The result does not enable production signals, "
        "execution, or real-money trading."
    )

    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
