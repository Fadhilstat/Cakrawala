from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from html.parser import HTMLParser
from urllib.parse import urljoin
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from cakrawala.data.http import HttpPolicy, ProviderRequestError, TextResponse, get_text
from cakrawala.data.provenance import build_provenance
from cakrawala.data.providers.base import ProviderResult

CALENDAR_URL = "https://www.bls.gov/schedule/news_release/bls.ics"
BASE_URL = "https://www.bls.gov"
REPOSITORY_URL = "https://github.com/Fadhilstat/Cakrawala"
BLS_USER_AGENT = f"Cakrawala/0.2 (+{REPOSITORY_URL}; public research calendar client)"
CACHE_TTL = timedelta(minutes=30)

_cached_result: ProviderResult | None = None
_cached_at: datetime | None = None


@dataclass(frozen=True)
class EconomicEvent:
    title: str
    starts_at: datetime
    source: str
    link: str


class _ReleaseTableParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.rows: list[list[str]] = []
        self._row: list[str] | None = None
        self._cell: list[str] | None = None

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        del attrs
        if tag == "tr":
            self._row = []
        elif tag in {"td", "th"} and self._row is not None:
            self._cell = []

    def handle_data(self, data: str) -> None:
        if self._cell is not None:
            self._cell.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag in {"td", "th"} and self._row is not None and self._cell is not None:
            text = " ".join("".join(self._cell).split())
            self._row.append(text)
            self._cell = None
            return
        if tag == "tr" and self._row is not None:
            if any(self._row):
                self.rows.append(self._row)
            self._row = None
            self._cell = None


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


def parse_release_schedule_html(
    text: str,
    *,
    source_url: str,
) -> list[EconomicEvent]:
    parser = _ReleaseTableParser()
    parser.feed(text)
    eastern = ZoneInfo("America/New_York")
    events: list[EconomicEvent] = []
    for row in parser.rows:
        if len(row) < 3:
            continue
        date_text = row[0].strip()
        time_text = row[1].strip()
        title = " ".join(part for part in row[2:] if part).strip()
        if not date_text or not time_text or not title:
            continue
        try:
            local_time = datetime.strptime(
                f"{date_text} {time_text}",
                "%A, %B %d, %Y %I:%M %p",
            ).replace(tzinfo=eastern)
        except ValueError:
            continue
        events.append(
            EconomicEvent(
                title=title,
                starts_at=local_time.astimezone(UTC),
                source="U.S. Bureau of Labor Statistics",
                link=source_url,
            )
        )
    return sorted(events, key=lambda item: item.starts_at)


def _request_headers(accept: str) -> dict[str, str]:
    return {
        "User-Agent": BLS_USER_AGENT,
        "Accept": accept,
        "Accept-Language": "en-US,en;q=0.8",
    }


def _calendar_result(response: TextResponse, events: list[EconomicEvent]) -> ProviderResult:
    if not events:
        raise ProviderRequestError("BLS calendar returned no usable events")
    return ProviderResult(
        provider="bls_economic_calendar",
        data=events,
        provenance=build_provenance(
            "bls_economic_calendar",
            response.url,
            response.raw,
        ),
    )


def _fetch_calendar_ics() -> ProviderResult:
    policy = HttpPolicy(
        allowed_hosts=frozenset({"www.bls.gov"}),
        accepted_content_types=("text/calendar", "text/plain"),
        max_bytes=2 * 1024 * 1024,
        attempts=2,
    )
    response = get_text(
        CALENDAR_URL,
        policy=policy,
        headers=_request_headers("text/calendar, text/plain;q=0.9, */*;q=0.1"),
    )
    return _calendar_result(response, parse_calendar(response.text))


def _fetch_calendar_html(year: int) -> ProviderResult:
    source_url = f"{BASE_URL}/schedule/{year}/home.htm"
    policy = HttpPolicy(
        allowed_hosts=frozenset({"www.bls.gov"}),
        accepted_content_types=("text/html",),
        max_bytes=2 * 1024 * 1024,
        attempts=2,
    )
    response = get_text(
        source_url,
        policy=policy,
        headers=_request_headers("text/html,application/xhtml+xml;q=0.9,*/*;q=0.1"),
    )
    events = parse_release_schedule_html(response.text, source_url=source_url)
    return _calendar_result(response, events)


def fetch_bls_calendar() -> ProviderResult:
    global _cached_at, _cached_result

    now = datetime.now(UTC)
    if (
        _cached_result is not None
        and _cached_at is not None
        and now - _cached_at < CACHE_TTL
    ):
        return _cached_result

    try:
        result = _fetch_calendar_ics()
    except (ProviderRequestError, ValueError):
        result = _fetch_calendar_html(now.year)

    _cached_result = result
    _cached_at = now
    return result
