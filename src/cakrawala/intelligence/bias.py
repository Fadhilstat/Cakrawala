from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class BiasInput:
    momentum_30d_pct: float | None
    drawdown_pct: float | None
    volatility_30d_pct: float | None
    long_account: float | None
    funding_rate: float | None
    high_attention_news: int


@dataclass(frozen=True)
class BiasAssessment:
    label: str
    score: int
    confidence: str
    reasons: tuple[str, ...]


def assess_research_bias(values: BiasInput) -> BiasAssessment:
    score = 0
    reasons: list[str] = []

    if values.momentum_30d_pct is not None:
        if values.momentum_30d_pct >= 5:
            score += 2
            reasons.append("30-day momentum is positive")
        elif values.momentum_30d_pct <= -5:
            score -= 2
            reasons.append("30-day momentum is negative")

    if values.drawdown_pct is not None:
        if values.drawdown_pct <= -12:
            score -= 1
            reasons.append("price remains in a material drawdown")
        elif values.drawdown_pct >= -3:
            score += 1
            reasons.append("price is trading near its recent peak")

    if values.long_account is not None:
        if values.long_account >= 0.68:
            score -= 1
            reasons.append("crowd positioning is heavily long")
        elif values.long_account <= 0.32:
            score += 1
            reasons.append("crowd positioning is heavily short")

    if values.funding_rate is not None:
        if values.funding_rate >= 0.0008:
            score -= 1
            reasons.append("positive funding is elevated")
        elif values.funding_rate <= -0.0008:
            score += 1
            reasons.append("negative funding is elevated")

    if values.volatility_30d_pct is not None and values.volatility_30d_pct >= 80:
        reasons.append("realized volatility is high")

    if values.high_attention_news >= 3:
        reasons.append("several high-attention headlines need review")

    if score >= 2:
        label = "Bullish research bias"
    elif score <= -2:
        label = "Bearish research bias"
    else:
        label = "Neutral research bias"

    evidence_count = sum(
        value is not None
        for value in (
            values.momentum_30d_pct,
            values.drawdown_pct,
            values.volatility_30d_pct,
            values.long_account,
            values.funding_rate,
        )
    )
    confidence = "high" if evidence_count >= 5 else "medium" if evidence_count >= 3 else "low"
    if not reasons:
        reasons.append("insufficient directional evidence")

    return BiasAssessment(
        label=label,
        score=score,
        confidence=confidence,
        reasons=tuple(reasons),
    )
