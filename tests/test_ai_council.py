from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from cakrawala.intelligence.ai_council import parse_council_brief


def _payload() -> dict[str, object]:
    return {
        "schema_version": 1,
        "generated_at": datetime.now(UTC).isoformat(),
        "as_of": "2026-08-21",
        "status": "ready",
        "source_count": 1,
        "roles": [
            {
                "role": "News Analyst",
                "summary": "Policy headlines remain the main event risk.",
                "confidence": "medium",
                "evidence": ["Federal Reserve press release"],
                "risks": ["Headline interpretation can change quickly"],
            }
        ],
        "synthesis": {
            "headline": "Evidence is mixed and event risk remains elevated.",
            "research_stance": "MIXED",
            "consensus": ["Avoid overconfidence before scheduled releases"],
            "disagreements": [],
            "risk_flags": ["Macro event risk"],
            "next_checks": ["Recheck after the next official release"],
            "signal_policy_note": "AI cannot override deterministic signals.",
        },
        "citations": [
            {
                "label": "Federal Reserve",
                "url": "https://www.federalreserve.gov/",
                "verified_at": datetime.now(UTC).isoformat(),
            }
        ],
    }


def test_parse_ai_council_brief() -> None:
    brief = parse_council_brief(_payload())
    assert brief.research_stance == "MIXED"
    assert brief.source_count == 1
    assert brief.roles[0].role == "News Analyst"
    assert brief.is_fresh()
    assert brief.is_publishable
    assert brief.presentation_status == "FRESH"


def test_ai_council_rejects_unapproved_stance() -> None:
    payload = _payload()
    synthesis = payload["synthesis"]
    assert isinstance(synthesis, dict)
    synthesis["research_stance"] = "STRONG BUY"
    with pytest.raises(ValueError, match="research_stance"):
        parse_council_brief(payload)


def test_ai_council_requires_https_citations() -> None:
    payload = _payload()
    payload["citations"] = [{"label": "Bad", "url": "http://example.com"}]
    with pytest.raises(ValueError, match="HTTPS URL"):
        parse_council_brief(payload)


def test_ai_council_ready_status_requires_roles_and_verified_sources() -> None:
    payload = _payload()
    payload["roles"] = []
    with pytest.raises(ValueError, match="analyst roles"):
        parse_council_brief(payload)

    payload = _payload()
    payload["source_count"] = 0
    payload["citations"] = []
    with pytest.raises(ValueError, match="verified sources"):
        parse_council_brief(payload)


def test_ai_council_source_count_matches_unique_citations() -> None:
    payload = _payload()
    payload["source_count"] = 2
    with pytest.raises(ValueError, match="source_count"):
        parse_council_brief(payload)


def test_ai_council_waiting_status_is_not_publishable() -> None:
    payload = _payload()
    payload["status"] = "waiting_for_first_scheduled_brief"
    payload["source_count"] = 0
    payload["roles"] = []
    payload["citations"] = []
    brief = parse_council_brief(payload)

    assert not brief.is_publishable
    assert brief.presentation_status == "WAITING FOR FIRST SCHEDULED BRIEF"


def test_ai_council_rejects_future_generation_and_invalid_source_count() -> None:
    payload = _payload()
    payload["generated_at"] = (datetime.now(UTC) + timedelta(days=1)).isoformat()
    with pytest.raises(ValueError, match="future"):
        parse_council_brief(payload)

    payload = _payload()
    payload["source_count"] = True
    with pytest.raises(ValueError, match="integer"):
        parse_council_brief(payload)

