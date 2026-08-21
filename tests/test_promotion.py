from cakrawala.models.promotion import PromotionEvidence, assess_promotion


def test_promotion_requires_all_gates() -> None:
    evidence = PromotionEvidence(
        model_name="challenger",
        healthy=True,
        health_score=0.91,
        relative_improvement=0.04,
        secondary_metric_regression=0.01,
        walk_forward_complete=True,
        point_in_time_features=True,
    )
    assert assess_promotion(evidence).promoted


def test_promotion_fails_closed() -> None:
    evidence = PromotionEvidence(
        model_name="challenger",
        healthy=False,
        health_score=0.2,
        relative_improvement=0.20,
        secondary_metric_regression=0.0,
        walk_forward_complete=True,
        point_in_time_features=True,
    )
    decision = assess_promotion(evidence)
    assert not decision.promoted
    assert "model_health_below_gate" in decision.reasons
