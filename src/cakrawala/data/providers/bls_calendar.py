from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from urllib.parse import urljoin
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from cakrawala.data.http import HttpPolicy, get_text
from cakrawala.data.provenance import build_provenance
from cakrawala.data.providers.base import ProviderResult


CALENDAR_URL = "https://www.bls.gov/schedule/news_release/bls.ics"
BASE_URL = "https://www.bls.gov"


@dataclass(frozen=True)
class EconomicEvent:
    title: str
    starts_at: datetime
    source: str
    link: str


def _unfold_lines(text: str) -> list[str]:
    unfolded: list[str] = []
    for raw_line in text.replace("\r\n", "\n").split("\n"):
        if raw_line.startswith((" ", "\t")) and unfolded:
            unfolded[-1] += raw_line[1:]
        else:
            unfolded.append(raw_line)
    return unfolded


def _parse_datetime(value: str, timezone_name: str | None = None) -> datetime:
    clean = value.strip()
    if clean.endswith("Z"):
        return datetime.strptime(clean, "%Y%m%dT%H%M%SZ").replace(tzinfo=UTC)

    if "T" in clean:
        parsed = datetime.strptime(clean, "%Y%m%dT%H%M%S")
        if timezone_name:
            try:
                return parsed.replace(tzinfo=ZoneInfo(timezone_name)).astimezone(UTC)
            except ZoneInfoNotFoundError as exc:
                raise ValueError("calendar timezone is unavailable") from exc
        return parsed.replace(tzinfo=UTC)

    return datetime.strptime(clean, "%Y%m%d").replace(tzinfo=UTC)


def _calendar_field(key_part: str, value: str) -> tuple[str, str, str | None]:
    segments = key_part.split(";")
    key = segments[0]
    timezone_name = None
    for segment in segments[1:]:
        if segment.startswith("TZID="):
            timezone_name = segment.removeprefix("TZID=")
    return key, value.strip(), timezone_name


def parse_calendar(text: str) -> list[EconomicEvent]:
    events: list[EconomicEvent] = []
    current: dict[str, str] | None = None
    current_timezone: str | None = None
    for line in _unfold_lines(text):
        if line == "BEGIN:VEVENT":
            current = {}
            current_timezone = None
            continue
        if line == "END:VEVENT":
            if current and "SUMMARY" in current and "DTSTART" in current:
                link = current.get("URL", BASE_URL)
                if link.startswith("/"):
                    link = urljoin(BASE_URL, link)
                events.append(
                    EconomicEvent(
                        title=current["SUMMARY"].replace("\\,", ",").strip(),
                        starts_at=_parse_datetime(current["DTSTART"], current_timezone),
                        source="U.S. Bureau of Labor Statistics",
                        link=link,
                    )
                )
            current = None
            current_timezone = None
            continue
        if current is None or ":" not in line:
            continue
        key_part, value = line.split(":", 1)
        key, clean_value, timezone_name = _calendar_field(key_part, value)
        if key in {"SUMMARY", "DTSTART", "URL"}:
            current[key] = clean_value
        if key == "DTSTART" and timezone_name:
            current_timezone = timezone_name
    return sorted(events, key=lambda item: item.starts_at)


def fetch_bls_calendar() -> ProviderResult:
    policy = HttpPolicy(
        allowed_hosts=frozenset({"www.bls.gov"}),
        accepted_content_types=("text/calendar", "text/plain"),
        max_bytes=2 * 1024 * 1024,
    )
    response = get_text(CALENDAR_URL, policy=policy)
    events = parse_calendar(response.text)
    if not events:
        raise ValueError("BLS calendar returned no usable events")
    return ProviderResult(
        provider="bls_economic_calendar",
        data=events,
        provenance=build_provenance(
            "bls_economic_calendar",
            response.url,
            response.raw,
        ),
    )
