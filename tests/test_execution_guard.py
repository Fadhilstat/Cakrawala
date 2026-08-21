from cakrawala.intelligence.execution_guard import (
    ExecutionEvidence,
    ReadinessState,
    assess_execution_readiness,
)


def base_evidence(**overrides: bool) -> ExecutionEvidence:
    values = {
        "source_healthy": True,
        "evidence_fresh": True,
        "model_promoted": True,
        "model_healthy": True,
        "risk_check_passed": True,
        "owner_authorized": False,
        "paper_mode": True,
        "emergency_stop": False,
    }
    values.update(overrides)
    return ExecutionEvidence(**values)


def test_emergency_stop_blocks_everything() -> None:
    result = assess_execution_readiness(base_evidence(emergency_stop=True))
    assert result.state == ReadinessState.BLOCKED
    assert result.reasons == ("emergency stop is active",)


def test_missing_model_keeps_terminal_in_observe_state() -> None:
    result = assess_execution_readiness(base_evidence(model_promoted=False))
    assert result.state == ReadinessState.OBSERVE
    assert "no model champion is promoted for this decision role" in result.reasons


def test_all_research_gates_allow_paper_ready_state() -> None:
    result = assess_execution_readiness(base_evidence())
    assert result.state == ReadinessState.PAPER_READY


def test_live_owner_state_requires_verified_owner() -> None:
    result = assess_execution_readiness(
        base_evidence(paper_mode=False, owner_authorized=False)
    )
    assert result.state == ReadinessState.BLOCKED

    verified = assess_execution_readiness(
        base_evidence(paper_mode=False, owner_authorized=True)
    )
    assert verified.state == ReadinessState.OWNER_READY
