from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime

from cakrawala.data.providers.news_feeds import NewsItem


@dataclass(frozen=True)
class NewsAssessment:
    source: str
    title: str
    link: str
    published_at: datetime | None
    tags: tuple[str, ...]
    attention_score: int
    watch_reason: str


TAG_KEYWORDS: dict[str, tuple[str, ...]] = {
    "monetary policy": (
        "interest rate",
        "policy rate",
        "fomc",
        "monetary policy",
        "inflation",
    ),
    "liquidity": (
        "liquidity",
        "balance sheet",
        "reserves",
        "funding",
    ),
    "financial stability": (
        "financial stability",
        "stress test",
        "distress",
        "default",
        "debt",
    ),
    "regulation": (
        "regulation",
        "supervision",
        "rule",
        "enforcement",
        "capital requirement",
    ),
    "digital assets": (
        "stablecoin",
        "crypto",
        "digital asset",
        "token",
    ),
}


def _freshness_points(published_at: datetime | None) -> int:
    if published_at is None:
        return 0
    age_seconds = (datetime.now(UTC) - published_at.astimezone(UTC)).total_seconds()
    age_hours = max(age_seconds / 3600, 0)
    if age_hours <= 24:
        return 3
    if age_hours <= 72:
        return 2
    if age_hours <= 168:
        return 1
    return 0


def assess_news_item(item: NewsItem) -> NewsAssessment:
    searchable = f"{item.title} {item.summary}".lower()
    tags = tuple(
        tag
        for tag, keywords in TAG_KEYWORDS.items()
        if any(keyword in searchable for keyword in keywords)
    )
    attention_score = min(_freshness_points(item.published_at) + len(tags) * 2, 10)
    if not tags:
        reason = "Monitor for context. No high-priority macro or risk keyword matched."
    elif "monetary policy" in tags:
        reason = (
            "Policy-sensitive headline. Check rates, FX, and risk-asset reaction "
            "before execution."
        )
    elif "financial stability" in tags:
        reason = "Risk-sensitive headline. Recheck liquidity, volatility, and exposure limits."
    elif "regulation" in tags:
        reason = (
            "Regulatory headline. Confirm whether the affected venue or instrument "
            "is in scope."
        )
    else:
        reason = "Relevant macro evidence. Compare it with price action and model freshness."

    return NewsAssessment(
        source=item.source,
        title=item.title,
        link=item.link,
        published_at=item.published_at,
        tags=tags or ("context",),
        attention_score=attention_score,
        watch_reason=reason,
    )


def assess_news(items: list[NewsItem]) -> list[NewsAssessment]:
    assessments = [assess_news_item(item) for item in items]
    oldest = datetime.min.replace(tzinfo=UTC)
    return sorted(
        assessments,
        key=lambda item: (item.attention_score, item.published_at or oldest),
        reverse=True,
    )
