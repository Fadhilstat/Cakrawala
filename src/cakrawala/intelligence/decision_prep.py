from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class DecisionPrep:
    pair: str
    evidence_state: str
    trend_alignment: str
    confidence: float
    valid_horizons: int
    event_risk: bool
    reasons: tuple[str, ...]


def _direction(value: float | None, threshold: float = 0.05) -> int:
    if value is None:
        return 0
    if value > threshold:
        return 1
    if value < -threshold:
        return -1
    return 0


def assess_fx_decision_prep(
    *,
    pair: str,
    change_1d_pct: float | None,
    change_5d_pct: float | None,
    change_20d_pct: float | None,
    event_risk: bool,
    stale: bool = False,
) -> DecisionPrep:
    horizons = (
        ("1D", change_1d_pct, 1.0),
        ("5D", change_5d_pct, 2.0),
        ("20D", change_20d_pct, 3.0),
    )
    directions = [(_direction(value), weight, label) for label, value, weight in horizons]
    valid = [
        (direction, weight, label)
        for direction, weight, label in directions
        if direction != 0
    ]

    if stale:
        return DecisionPrep(
            pair=pair,
            evidence_state="INSUFFICIENT",
            trend_alignment="STALE",
            confidence=0.0,
            valid_horizons=len(valid),
            event_risk=event_risk,
            reasons=("Reference-rate evidence is stale.",),
        )

    if len(valid) < 2:
        return DecisionPrep(
            pair=pair,
            evidence_state="INSUFFICIENT",
            trend_alignment="NEUTRAL",
            confidence=0.0,
            valid_horizons=len(valid),
            event_risk=event_risk,
            reasons=("Fewer than two trend horizons provide directional evidence.",),
        )

    weighted_score = sum(direction * weight for direction, weight, _ in valid)
    max_score = sum(weight for _, weight, _ in valid)
    confidence = abs(weighted_score) / max_score if max_score else 0.0

    if weighted_score > 0:
        alignment = "UP"
    elif weighted_score < 0:
        alignment = "DOWN"
    else:
        alignment = "MIXED"

    reasons: list[str] = []
    positive = [label for direction, _, label in valid if direction > 0]
    negative = [label for direction, _, label in valid if direction < 0]
    if positive:
        reasons.append("Positive horizons: " + ", ".join(positive) + ".")
    if negative:
        reasons.append("Negative horizons: " + ", ".join(negative) + ".")

    if event_risk:
        reasons.append("A scheduled macro release is close enough to raise event risk.")
        evidence_state = "WAIT_EVENT"
    elif confidence >= 0.75:
        evidence_state = "ALIGNED"
    else:
        evidence_state = "MIXED"

    return DecisionPrep(
        pair=pair,
        evidence_state=evidence_state,
        trend_alignment=alignment,
        confidence=confidence,
        valid_horizons=len(valid),
        event_risk=event_risk,
        reasons=tuple(reasons),
    )
