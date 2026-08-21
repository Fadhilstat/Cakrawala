from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class ReadinessState(StrEnum):
    BLOCKED = "BLOCKED"
    OBSERVE = "OBSERVE"
    PAPER_READY = "PAPER READY"
    OWNER_READY = "OWNER READY"


@dataclass(frozen=True)
class ExecutionEvidence:
    source_healthy: bool
    evidence_fresh: bool
    model_promoted: bool
    model_healthy: bool
    risk_check_passed: bool
    owner_authorized: bool
    paper_mode: bool = True
    emergency_stop: bool = False


@dataclass(frozen=True)
class ExecutionReadiness:
    state: ReadinessState
    reasons: tuple[str, ...]


def assess_execution_readiness(values: ExecutionEvidence) -> ExecutionReadiness:
    reasons: list[str] = []

    if values.emergency_stop:
        return ExecutionReadiness(
            state=ReadinessState.BLOCKED,
            reasons=("emergency stop is active",),
        )
    if not values.source_healthy:
        reasons.append("one or more required sources are unhealthy")
    if not values.evidence_fresh:
        reasons.append("required evidence is stale")
    if not values.model_promoted:
        reasons.append("no model champion is promoted for this decision role")
    if not values.model_healthy:
        reasons.append("model health gate is not satisfied")
    if not values.risk_check_passed:
        reasons.append("risk gate is not satisfied")

    if reasons:
        return ExecutionReadiness(ReadinessState.OBSERVE, tuple(reasons))

    if values.paper_mode:
        return ExecutionReadiness(
            ReadinessState.PAPER_READY,
            ("all research gates passed for paper-mode review",),
        )

    if not values.owner_authorized:
        return ExecutionReadiness(
            ReadinessState.BLOCKED,
            ("owner authorization is required outside paper mode",),
        )

    return ExecutionReadiness(
        ReadinessState.OWNER_READY,
        ("all configured research and owner authorization gates passed",),
    )
