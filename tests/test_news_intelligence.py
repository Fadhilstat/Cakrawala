from datetime import datetime, timezone

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
        published_at=datetime.now(timezone.utc),
        summary="Inflation and policy rate conditions were reviewed.",
    )
    result = assess_news_item(item)
    assert "monetary policy" in result.tags
    assert result.attention_score >= 5
    assert "Policy-sensitive" in result.watch_reason
