from cakrawala.config import load_yaml


ALLOWED_TOOL_STATES = {
    "observe only",
    "observe and sandbox",
    "sandbox candidate",
    "exclude",
}


def test_tool_radar_never_auto_installs() -> None:
    radar = load_yaml("configs/tool_radar.yaml")
    policy = radar["review_policy"]
    assert policy["install_automatically"] is False
    assert policy["sandbox_required_before_use"] is True
    assert policy["execution_policy_override_allowed"] is False


def test_tool_radar_items_have_primary_sources() -> None:
    radar = load_yaml("configs/tool_radar.yaml")
    for item in radar["items"]:
        assert str(item["source"]).startswith("https://")
        assert item["status"] in ALLOWED_TOOL_STATES
