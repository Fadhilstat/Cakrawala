from datetime import UTC, datetime

import cakrawala.data.providers.news_feeds as news_feeds
from cakrawala.data.providers.news_feeds import NewsItem, _parse_rss
from cakrawala.intelligence.news import assess_news_item


def test_rss_parser_keeps_source_and_link() -> None:
    xml = """
    <rss><channel><item>
      <title>Central bank policy update</title>
      <link>https://example.com/item</link>
      <pubDate>Thu, 20 Aug 2026 10:00:00 GMT</pubDate>
      <description>Policy rates remain in focus.</description>
    </item></channel></rss>
    """
    items = _parse_rss(xml, "Example", 5)
    assert len(items) == 1
    assert items[0].source == "Example"
    assert items[0].link == "https://example.com/item"
    assert items[0].published_at is not None


def test_news_assessment_is_transparent_keyword_priority() -> None:
    item = NewsItem(
        source="Example",
        title="Monetary policy and interest rate decision",
        link="https://example.com/policy",
        published_at=datetime.now(UTC),
        summary="Inflation and policy rate conditions were reviewed.",
    )
    result = assess_news_item(item)
    assert "monetary policy" in result.tags
    assert result.attention_score >= 5
    assert "Policy-sensitive" in result.watch_reason


def test_macro_news_keeps_healthy_sources_when_one_feed_fails(monkeypatch) -> None:
    item = NewsItem(
        source="ECB",
        title="Policy communication",
        link="https://example.com/ecb",
        published_at=datetime(2026, 8, 21, tzinfo=UTC),
        summary="Policy update",
    )

    def fail(_: int) -> list[NewsItem]:
        raise RuntimeError("feed unavailable")

    monkeypatch.setattr(news_feeds, "fetch_fed_press_releases", fail)
    monkeypatch.setattr(news_feeds, "fetch_bis_press_releases", fail)
    monkeypatch.setattr(news_feeds, "fetch_ecb_press_releases", lambda _: [item])

    result = news_feeds.fetch_macro_news(2)
    assert result == [item]
