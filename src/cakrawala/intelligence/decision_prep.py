from dataclasses import dataclass


_ALLOWED_MACRO_ALIGNMENTS = {
    "SUPPORTS_UP",
    "SUPPORTS_DOWN",
    "MIXED",
    "NO_CONTEXT",
}


@dataclass(frozen=True)
class DecisionPrep:
    pair: str
    evidence_state: str
    trend_alignment: str
    confidence: float
    valid_horizons: int
    event_risk: bool
    macro_alignment: str
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
    macro_alignment: str = "NO_CONTEXT",
) -> DecisionPrep:
    normalized_macro = macro_alignment.strip().upper()
    if normalized_macro not in _ALLOWED_MACRO_ALIGNMENTS:
        raise ValueError("macro_alignment is not supported")

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
            macro_alignment=normalized_macro,
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
            macro_alignment=normalized_macro,
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

    macro_conflict = (
        (alignment == "UP" and normalized_macro == "SUPPORTS_DOWN")
        or (alignment == "DOWN" and normalized_macro == "SUPPORTS_UP")
    )
    macro_support = (
        (alignment == "UP" and normalized_macro == "SUPPORTS_UP")
        or (alignment == "DOWN" and normalized_macro == "SUPPORTS_DOWN")
    )

    if normalized_macro == "MIXED":
        reasons.append("Recent macro surprise evidence is mixed for this currency pair.")
    elif macro_support:
        reasons.append("Recent macro surprise evidence supports the price-trend direction.")
    elif macro_conflict:
        reasons.append("Recent macro surprise evidence conflicts with the price-trend direction.")

    if event_risk:
        reasons.append("A scheduled macro release is close enough to raise event risk.")
        evidence_state = "WAIT_EVENT"
    elif macro_conflict:
        evidence_state = "WAIT_MACRO_CONFLICT"
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
        macro_alignment=normalized_macro,
        reasons=tuple(reasons),
    )
