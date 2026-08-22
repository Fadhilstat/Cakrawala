from cakrawala.intelligence.decision_prep import assess_fx_decision_prep


def test_aligned_trend_without_event_risk() -> None:
    result = assess_fx_decision_prep(
        pair="EURUSD",
        change_1d_pct=0.2,
        change_5d_pct=0.8,
        change_20d_pct=1.7,
        event_risk=False,
    )
    assert result.evidence_state == "ALIGNED"
    assert result.trend_alignment == "UP"
    assert result.confidence == 1.0
    assert result.macro_alignment == "NO_CONTEXT"


def test_event_risk_forces_wait_state() -> None:
    result = assess_fx_decision_prep(
        pair="USDJPY",
        change_1d_pct=-0.3,
        change_5d_pct=-0.7,
        change_20d_pct=-1.2,
        event_risk=True,
        macro_alignment="SUPPORTS_DOWN",
    )
    assert result.evidence_state == "WAIT_EVENT"
    assert result.event_risk is True


def test_stale_evidence_is_insufficient() -> None:
    result = assess_fx_decision_prep(
        pair="GBPUSD",
        change_1d_pct=0.4,
        change_5d_pct=0.6,
        change_20d_pct=0.9,
        event_risk=False,
        stale=True,
    )
    assert result.evidence_state == "INSUFFICIENT"
    assert result.trend_alignment == "STALE"


def test_macro_conflict_forces_wait_even_when_price_trend_is_aligned() -> None:
    result = assess_fx_decision_prep(
        pair="EURUSD",
        change_1d_pct=0.2,
        change_5d_pct=0.8,
        change_20d_pct=1.7,
        event_risk=False,
        macro_alignment="SUPPORTS_DOWN",
    )
    assert result.evidence_state == "WAIT_MACRO_CONFLICT"
    assert result.trend_alignment == "UP"
    assert result.macro_alignment == "SUPPORTS_DOWN"
    assert any("conflicts" in reason for reason in result.reasons)
