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


def test_event_risk_forces_wait_state() -> None:
    result = assess_fx_decision_prep(
        pair="USDJPY",
        change_1d_pct=-0.3,
        change_5d_pct=-0.7,
        change_20d_pct=-1.2,
        event_risk=True,
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
