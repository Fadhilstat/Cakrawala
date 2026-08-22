from __future__ import annotations

import json
from dataclasses import asdict
from datetime import UTC, datetime
from pathlib import Path

import torch
from chronos import BaseChronosPipeline

from cakrawala.data.providers.ecb_fx import fetch_forex_pair_history
from cakrawala.models.fx_foundation import ForecastPoint, evaluate_forecasts, walk_forward_origins

MODEL_ID = "amazon/chronos-bolt-tiny"
MODEL_REVISION = "059e58e2d88886bc5254bceb365ffe5c71bcc261"
PAIRS = ("EURUSD", "GBPUSD", "USDJPY", "USDCHF", "AUDUSD", "USDCAD")
HORIZON = 5
ORIGIN_COUNT = 8
MIN_CONTEXT = 256
MAX_HISTORY = 1200
QUANTILES = [0.1, 0.5, 0.9]


def main() -> None:
    pipeline = BaseChronosPipeline.from_pretrained(
        MODEL_ID,
        revision=MODEL_REVISION,
        device_map="cpu",
    )
    pair_results: dict[str, object] = {}

    for pair in PAIRS:
        result = fetch_forex_pair_history(pair)
        history = result.data[-MAX_HISTORY:]
        dates = [item[0] for item in history]
        values = [float(item[1]) for item in history]
        origins = walk_forward_origins(
            len(values), min_context=MIN_CONTEXT, horizon=HORIZON, count=ORIGIN_COUNT
        )
        contexts = [
            torch.tensor(values[:origin], dtype=torch.float32)
            for origin in origins
        ]
        quantile_tensor, _ = pipeline.predict_quantiles(
            inputs=contexts,
            prediction_length=HORIZON,
            quantile_levels=QUANTILES,
        )
        quantiles = quantile_tensor.detach().cpu().numpy()

        points: list[ForecastPoint] = []
        for row_index, origin in enumerate(origins):
            origin_value = values[origin - 1]
            actuals = values[origin : origin + HORIZON]
            for step, actual in enumerate(actuals):
                points.append(
                    ForecastPoint(
                        actual=actual,
                        low=float(quantiles[row_index, step, 0]),
                        median=float(quantiles[row_index, step, 1]),
                        high=float(quantiles[row_index, step, 2]),
                        origin_value=origin_value,
                    )
                )

        metrics = evaluate_forecasts(points)
        pair_results[pair] = {
            "history_start": dates[0].isoformat(),
            "history_end": dates[-1].isoformat(),
            "origins": len(origins),
            "horizon_observations": HORIZON,
            "metrics": asdict(metrics),
            "source_url": result.provenance.source_url,
        }

    improvements = [
        float(item["metrics"]["mae_improvement"])
        for item in pair_results.values()
    ]
    direction_scores = [
        float(item["metrics"]["direction_accuracy"])
        for item in pair_results.values()
    ]
    research_gate = all(value > 0 for value in improvements) and sum(direction_scores) / len(
        direction_scores
    ) >= 0.5

    payload = {
        "schema_version": 1,
        "generated_at": datetime.now(UTC).isoformat(),
        "model": MODEL_ID,
        "model_revision": MODEL_REVISION,
        "model_role": "research_only_fx_foundation_forecast",
        "pairs": pair_results,
        "research_gate_passed": research_gate,
        "production_promoted": False,
        "notes": [
            "ECB observations are official reference rates, not executable broker prices.",
            "Forecast horizons count ECB observations rather than calendar days.",
            "The last-value forecast is the MAE benchmark.",
            "A research-gate pass never promotes the model automatically.",
        ],
    }
    output = Path("artifacts/backtests/fx_foundation_latest.json")
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(payload, indent=2))


if __name__ == "__main__":
    main()
