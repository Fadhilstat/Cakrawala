from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from cakrawala.data.http import HttpPolicy, get_json
from cakrawala.data.provenance import build_provenance
from cakrawala.data.providers.base import ProviderResult


DATASET_URL = "https://publicreporting.cftc.gov/resource/gpe5-46if.json"


@dataclass(frozen=True)
class InstitutionalPositioning:
    market: str
    report_date: datetime
    open_interest: float
    asset_manager_net: float
    leveraged_funds_net: float
    dealer_net: float


def _number(row: dict[str, Any], key: str) -> float:
    value = row.get(key)
    if value is None:
        raise ValueError(f"CFTC row is missing {key}")
    return float(value)


def parse_tff_row(row: dict[str, Any]) -> InstitutionalPositioning:
    report_date = datetime.fromisoformat(str(row["report_date_as_yyyy_mm_dd"]).replace("Z", "+00:00"))
    if report_date.tzinfo is None:
        report_date = report_date.replace(tzinfo=UTC)
    return InstitutionalPositioning(
        market=str(row["market_and_exchange_names"]),
        report_date=report_date,
        open_interest=_number(row, "open_interest_all"),
        asset_manager_net=(
            _number(row, "asset_mgr_positions_long")
            - _number(row, "asset_mgr_positions_short")
        ),
        leveraged_funds_net=(
            _number(row, "lev_money_positions_long")
            - _number(row, "lev_money_positions_short")
        ),
        dealer_net=(
            _number(row, "dealer_positions_long_all")
            - _number(row, "dealer_positions_short_all")
        ),
    )


def fetch_tff_market(search_term: str) -> ProviderResult:
    cleaned = search_term.strip().upper()
    if not cleaned or len(cleaned) > 80 or "'" in cleaned:
        raise ValueError("search_term is invalid")

    policy = HttpPolicy(
        allowed_hosts=frozenset({"publicreporting.cftc.gov"}),
        max_bytes=2 * 1024 * 1024,
    )
    params = {
        "$limit": 2,
        "$order": "report_date_as_yyyy_mm_dd DESC",
        "$where": f"upper(market_and_exchange_names) like '%{cleaned}%'",
    }
    response = get_json(DATASET_URL, policy=policy, params=params)
    payload = response.payload
    if not isinstance(payload, list) or not payload:
        raise ValueError("CFTC returned no matching TFF rows")
    rows = [parse_tff_row(row) for row in payload if isinstance(row, dict)]
    if not rows:
        raise ValueError("CFTC TFF rows failed schema validation")
    return ProviderResult(
        provider="cftc_tff_futures_only",
        data=rows,
        provenance=build_provenance(
            "cftc_tff_futures_only",
            response.url,
            response.raw,
        ),
    )
