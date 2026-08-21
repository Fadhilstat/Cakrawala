from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from email.utils import parsedate_to_datetime
from xml.etree import ElementTree

from cakrawala.data.http import HttpPolicy, ProviderRequestError, get_text

FED_PRESS_RELEASES = "https://www.federalreserve.gov/feeds/press_all.xml"
BIS_PRESS_RELEASES = "https://www.bis.org/doclist/all_pressrels.rss"
ECB_PRESS_RELEASES = "https://www.ecb.europa.eu/rss/press.html"


@dataclass(frozen=True)
class NewsItem:
    source: str
    title: str
    link: str
    published_at: datetime | None
    summary: str


def _parse_datetime(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        parsed = parsedate_to_datetime(value)
    except (TypeError, ValueError, OverflowError):
        try:
            parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)


def _clean_text(value: str | None) -> str:
    return " ".join((value or "").split())


def _parse_rss(xml_text: str, source: str, limit: int) -> list[NewsItem]:
    try:
        root = ElementTree.fromstring(xml_text)
    except ElementTree.ParseError as exc:
        raise ProviderRequestError("News provider returned invalid XML") from exc

    items: list[NewsItem] = []
    for node in root.findall(".//item")[:limit]:
        title = _clean_text(node.findtext("title"))
        link = _clean_text(node.findtext("link"))
        if not title or not link:
            continue
        items.append(
            NewsItem(
                source=source,
                title=title,
                link=link,
                published_at=_parse_datetime(node.findtext("pubDate")),
                summary=_clean_text(node.findtext("description")),
            )
        )
    return items


def _validate_limit(limit: int) -> None:
    if not 1 <= limit <= 30:
        raise ValueError("limit must be between 1 and 30")


def fetch_fed_press_releases(limit: int = 10) -> list[NewsItem]:
    _validate_limit(limit)
    policy = HttpPolicy(
        allowed_hosts=frozenset({"www.federalreserve.gov"}),
        max_bytes=2 * 1024 * 1024,
        accepted_content_types=("text/xml", "application/xml", "application/rss+xml"),
    )
    response = get_text(FED_PRESS_RELEASES, policy=policy)
    return _parse_rss(response.text, "Federal Reserve", limit)


def fetch_bis_press_releases(limit: int = 10) -> list[NewsItem]:
    _validate_limit(limit)
    policy = HttpPolicy(
        allowed_hosts=frozenset({"www.bis.org"}),
        max_bytes=2 * 1024 * 1024,
        accepted_content_types=(
            "text/xml",
            "application/xml",
            "application/rss+xml",
            "application/rdf+xml",
        ),
    )
    response = get_text(BIS_PRESS_RELEASES, policy=policy)
    return _parse_rss(response.text, "BIS", limit)


def fetch_ecb_press_releases(limit: int = 10) -> list[NewsItem]:
    _validate_limit(limit)
    policy = HttpPolicy(
        allowed_hosts=frozenset({"www.ecb.europa.eu"}),
        max_bytes=2 * 1024 * 1024,
        accepted_content_types=("text/xml", "application/xml", "application/rss+xml"),
    )
    response = get_text(ECB_PRESS_RELEASES, policy=policy)
    return _parse_rss(response.text, "ECB", limit)


def fetch_macro_news(limit_per_source: int = 8) -> list[NewsItem]:
    _validate_limit(limit_per_source)
    loaders: tuple[Callable[[int], list[NewsItem]], ...] = (
        fetch_fed_press_releases,
        fetch_bis_press_releases,
        fetch_ecb_press_releases,
    )
    items: list[NewsItem] = []
    for loader in loaders:
        try:
            items.extend(loader(limit_per_source))
        except Exception:
            continue
    if not items:
        raise ProviderRequestError("All configured macro news feeds were unavailable")

    oldest = datetime.min.replace(tzinfo=UTC)
    return sorted(
        items,
        key=lambda item: item.published_at or oldest,
        reverse=True,
    )
