from datetime import date

from cakrawala.models.health import load_model_health


def test_current_configuration_is_explicitly_baseline_only() -> None:
    summary = load_model_health(today=date(2026, 8, 23))
    states = {item.role: item.state for item in summary.roles}

    assert states["expected_return"] == "BASELINE_ONLY"
    assert states["direction_probability"] == "BASELINE_ONLY"
    assert states["volatility"] == "BASELINE_ONLY"
    assert summary.production_ready is False


def test_baseline_only_roles_are_not_marked_stale() -> None:
    summary = load_model_health(today=date(2026, 8, 23))

    assert summary.roles
    assert all(item.stale is False for item in summary.roles)
    assert all(item.model_name is None for item in summary.roles)
