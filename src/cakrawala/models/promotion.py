from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class PromotionEvidence:
    model_name: str
    healthy: bool
    health_score: float
    relative_improvement: float
    secondary_metric_regression: float
    walk_forward_complete: bool
    point_in_time_features: bool


@dataclass(frozen=True)
class PromotionDecision:
    promoted: bool
    reasons: tuple[str, ...]


def assess_promotion(
    evidence: PromotionEvidence,
    *,
    minimum_health: float = 0.80,
    minimum_relative_improvement: float = 0.02,
    maximum_secondary_metric_regression: float = 0.03,
) -> PromotionDecision:
    reasons: list[str] = []
    if not evidence.healthy or evidence.health_score < minimum_health:
        reasons.append("model_health_below_gate")
    if evidence.relative_improvement < minimum_relative_improvement:
        reasons.append("benchmark_improvement_below_gate")
    if evidence.secondary_metric_regression > maximum_secondary_metric_regression:
        reasons.append("secondary_metric_regression_above_gate")
    if not evidence.walk_forward_complete:
        reasons.append("walk_forward_incomplete")
    if not evidence.point_in_time_features:
        reasons.append("point_in_time_evidence_missing")
    return PromotionDecision(promoted=not reasons, reasons=tuple(reasons))
