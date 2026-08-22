from datetime import UTC

import pytest

from cakrawala.data.providers.binance_futures import _symbol
from cakrawala.data.providers.bls_calendar import (
    parse_calendar,
    parse_release_schedule_html,
)
from cakrawala.data.providers.cftc import parse_tff_row


def test_cftc_tff_parser_builds_net_positions() -> None:
    row = {
        "market_and_exchange_names": "EURO FX - CHICAGO MERCANTILE EXCHANGE",
        "report_date_as_yyyy_mm_dd": "2026-08-04T00:00:00.000",
        "open_interest_all": "1000",
        "asset_mgr_positions_long": "420",
        "asset_mgr_positions_short": "180",
        "lev_money_positions_long": "220",
        "lev_money_positions_short": "310",
        "dealer_positions_long_all": "120",
        "dealer_positions_short_all": "270",
    }
    parsed = parse_tff_row(row)
    assert parsed.open_interest == pytest.approx(1000)
    assert parsed.asset_manager_net == pytest.approx(240)
    assert parsed.leveraged_funds_net == pytest.approx(-90)
    assert parsed.dealer_net == pytest.approx(-150)


def test_bls_calendar_converts_tzid_to_utc() -> None:
    sample = """BEGIN:VCALENDAR
BEGIN:VEVENT
DTSTART;TZID=America/New_York:20260825T083000
SUMMARY:Consumer Price Index
URL:https://www.bls.gov/news.release/cpi.toc.htm
END:VEVENT
END:VCALENDAR
"""
    events = parse_calendar(sample)
    assert len(events) == 1
    assert events[0].starts_at.tzinfo is UTC
    assert events[0].starts_at.hour == 12
    assert events[0].starts_at.minute == 30


def test_bls_html_schedule_parser_handles_official_table_rows() -> None:
    sample = """
    <table>
      <tr><th>Date</th><th>Time</th><th>Release</th></tr>
      <tr>
        <td>Friday, September 4, 2026</td>
        <td>08:30 AM</td>
        <td><a>Employment Situation for August 2026</a></td>
      </tr>
      <tr>
        <td>Monday, September 7, 2026</td>
        <td></td>
        <td>Labor Day</td>
      </tr>
    </table>
    """
    source_url = "https://www.bls.gov/schedule/2026/home.htm"
    events = parse_release_schedule_html(sample, source_url=source_url)

    assert len(events) == 1
    assert events[0].title == "Employment Situation for August 2026"
    assert events[0].starts_at.isoformat() == "2026-09-04T12:30:00+00:00"
    assert events[0].link == source_url


def test_binance_futures_symbol_validation() -> None:
    assert _symbol("btcusdt") == "BTCUSDT"
    with pytest.raises(ValueError):
        _symbol("BTC/USDT")
