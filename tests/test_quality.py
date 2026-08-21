from cakrawala.data.quality import require_mapping, require_sequence


def test_mapping_gate_reports_missing_key() -> None:
    result = require_mapping({"a": 1}, ("a", "b"))
    assert not result.passed
    assert result.errors == ("missing_key:b",)


def test_sequence_gate_requires_items() -> None:
    assert not require_sequence([], 1).passed
    assert require_sequence([1], 1).passed
