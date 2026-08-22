from __future__ import annotations

from datetime import UTC, datetime

import pytest

from cakrawala.intelligence.economic_calendar_evidence import (
    macro_context_for_pair,
    parse_calendar_snapshot,
)


def _payload() -> dict[str, object]:
    return {
        "schema_version": 1,
        "generated_at": "2026-08-22T15:41:00Z",
        "as_of": "2026-08-22",
        "events": [
            {
                "event": "Nonfarm Payrolls",
                "currency": "USD",
                "released_at": "2026-08-21T12:30:00Z",
                "importance": "high",
                "actual": "50K",
                "forecast": "100K",
                "previous": "90K",
                "consensus_source": "Investing.com Economic Calendar",
                "consensus_url": "https://www.investing.com/economic-calendar/non-farm-payrolls-227",
                "official_source": "U.S. Bureau of Labor Statistics",
                "official_url": "https://www.bls.gov/news.release/empsit.nr0.htm",
                "actual_verified": True,
            },
            {
                "event": "Consumer Price Index YoY",
                "currency": "EUR",
                "released_at": "2026-08-21T09:00:00Z",
                "importance": "high",
                "actual": "2.8%",
                "forecast": "2.4%",
                "previous": "2.3%",
                "consensus_source": "Investing.com Economic Calendar",
                "consensus_url": "https://www.investing.com/economic-calendar/",
                "official_source": "Official statistics authority",
                "official_url": "https://ec.europa.eu/eurostat/",
                "actual_verified": True,
            },
        ],
    }


def test_parse_snapshot_requires_official_source_for_verified_actual() -> None:
    payload = _payload()
    event = payload["events"][0]
    assert isinstance(event, dict)
    event["official_url"] = None
    with pytest.raises(ValueError, match="verified actual values"):
        parse_calendar_snapshot(payload)


def test_pair_macro_context_compares_base_and_quote_evidence() -> None:
    snapshot = parse_calendar_snapshot(_payload())
    result = macro_context_for_pair(
        "EURUSD",
        snapshot,
        now=datetime(2026, 8, 22, 12, 0, tzinfo=UTC),
    )
    assert result.alignment == "SUPPORTS_UP"
    assert result.relevant_events == 2
    assert result.verified_events == 2
    assert result.score > 0


def test_old_events_do_not_influence_pair_context() -> None:
    payload = _payload()
    events = payload["events"]
    assert isinstance(events, list)
    for item in events:
        assert isinstance(item, dict)
        item["released_at"] = "2026-07-01T12:30:00Z"
    snapshot = parse_calendar_snapshot(payload)
    result = macro_context_for_pair(
        "EURUSD",
        snapshot,
        now=datetime(2026, 8, 22, 12, 0, tzinfo=UTC),
    )
    assert result.alignment == "NO_CONTEXT"
    assert result.relevant_events == 0
