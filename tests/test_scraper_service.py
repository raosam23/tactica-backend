"""
Unit tests for scraper service functions.

Tests cover:
- scrape_wikipedia_articles - Wikipedia API scraping
- scrape_rss_feeds - RSS feed parsing

All tests mock HTTP requests to be deterministic and avoid network calls.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.scraper_service import scrape_rss_feeds, scrape_wikipedia_articles


class TestScrapeWikipediaArticles:
    """Tests for scrape_wikipedia_articles function."""

    @pytest.mark.asyncio
    async def test_scrape_single_article_success(self):
        """Should return article content with metadata."""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "query": {
                "pages": {
                    "12345": {
                        "title": "Lionel Messi",
                        "extract": "Lionel Messi is an Argentine footballer.",
                    }
                }
            }
        }
        mock_response.raise_for_status = MagicMock()

        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.get = AsyncMock(
                return_value=mock_response
            )

            results = await scrape_wikipedia_articles(
                ["Lionel Messi"], sport="football"
            )

        assert len(results) == 1
        assert results[0]["title"] == "Lionel Messi"
        assert "footballer" in results[0]["content"]
        assert results[0]["source"] == "wikipedia"
        assert results[0]["sport"] == "football"
        assert "en.wikipedia.org" in results[0]["url"]

    @pytest.mark.asyncio
    async def test_scrape_multiple_articles(self):
        """Should handle multiple article titles."""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "query": {
                "pages": {
                    "12345": {"title": "Lionel Messi", "extract": "Messi content"},
                    "67890": {
                        "title": "Cristiano Ronaldo",
                        "extract": "Ronaldo content",
                    },
                }
            }
        }
        mock_response.raise_for_status = MagicMock()

        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.get = AsyncMock(
                return_value=mock_response
            )

            results = await scrape_wikipedia_articles(
                ["Lionel Messi", "Cristiano Ronaldo"], sport="football"
            )

        assert len(results) == 2
        titles = {r["title"] for r in results}
        assert "Lionel Messi" in titles
        assert "Cristiano Ronaldo" in titles

    @pytest.mark.asyncio
    async def test_scrape_article_not_found(self):
        """Should skip articles with no content."""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "query": {"pages": {"-1": {"title": "Nonexistent Article", "missing": ""}}}
        }
        mock_response.raise_for_status = MagicMock()

        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.get = AsyncMock(
                return_value=mock_response
            )

            results = await scrape_wikipedia_articles(["Nonexistent Article"])

        assert len(results) == 0

    @pytest.mark.asyncio
    async def test_scrape_handles_http_error(self):
        """Should return empty list on HTTP errors."""
        import httpx

        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.get = AsyncMock(
                side_effect=httpx.HTTPError("Connection failed")
            )

            results = await scrape_wikipedia_articles(["Any Title"])

        assert results == []

    @pytest.mark.asyncio
    async def test_scrape_handles_timeout(self):
        """Should return empty list on timeout."""
        import httpx

        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.get = AsyncMock(
                side_effect=httpx.TimeoutException("Timeout")
            )

            results = await scrape_wikipedia_articles(["Any Title"])

        assert results == []

    @pytest.mark.asyncio
    async def test_scrape_without_sport_tag(self):
        """Should work without sport parameter."""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "query": {
                "pages": {"12345": {"title": "Test Article", "extract": "Test content"}}
            }
        }
        mock_response.raise_for_status = MagicMock()

        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.get = AsyncMock(
                return_value=mock_response
            )

            results = await scrape_wikipedia_articles(["Test Article"])

        assert len(results) == 1
        assert results[0]["sport"] is None

    @pytest.mark.asyncio
    async def test_scrape_generates_tags_from_title(self):
        """Should generate tags from article title."""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "query": {
                "pages": {
                    "12345": {"title": "FC Barcelona", "extract": "A football club"}
                }
            }
        }
        mock_response.raise_for_status = MagicMock()

        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.get = AsyncMock(
                return_value=mock_response
            )

            results = await scrape_wikipedia_articles(["FC Barcelona"])

        assert len(results) == 1
        assert "fc" in results[0]["tags"]
        assert "barcelona" in results[0]["tags"]

    @pytest.mark.asyncio
    async def test_scrape_url_replaces_spaces(self):
        """Wikipedia URLs should have spaces replaced with underscores."""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "query": {
                "pages": {
                    "12345": {
                        "title": "Real Madrid CF",
                        "extract": "Spanish football club",
                    }
                }
            }
        }
        mock_response.raise_for_status = MagicMock()

        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.get = AsyncMock(
                return_value=mock_response
            )

            results = await scrape_wikipedia_articles(["Real Madrid CF"])

        assert "Real_Madrid_CF" in results[0]["url"]


class TestScrapeRSSFeeds:
    """Tests for scrape_rss_feeds function."""

    @pytest.mark.asyncio
    async def test_scrape_rss_feed_success(self):
        """Should parse RSS feed and return articles."""
        mock_feed = MagicMock()
        mock_feed.feed.get.return_value = "ESPN Sports"

        entry1 = MagicMock()
        entry1.get = lambda key, default="": {
            "title": "Messi scores again",
            "summary": "Messi scored a beautiful goal",
            "link": "https://espn.com/article/1",
            "published": "Mon, 01 Jan 2024 12:00:00 GMT",
        }.get(key, default)

        entry2 = MagicMock()
        entry2.get = lambda key, default="": {
            "title": "Barcelona wins",
            "summary": "Barcelona secured a victory",
            "link": "https://espn.com/article/2",
            "published": "Tue, 02 Jan 2024 12:00:00 GMT",
        }.get(key, default)

        for entry in [entry1, entry2]:
            if hasattr(entry, "content"):
                delattr(entry, "content")

        mock_feed.entries = [entry1, entry2]

        with patch("feedparser.parse", return_value=mock_feed):
            results = await scrape_rss_feeds(
                ["https://espn.com/rss/feed"], sport="football"
            )

        assert len(results) == 2
        titles = {r["title"] for r in results}
        assert "Messi scores again" in titles
        assert "Barcelona wins" in titles
        assert all(r["source"] == "ESPN Sports" for r in results)
        assert all(r["sport"] == "football" for r in results)

    @pytest.mark.asyncio
    async def test_scrape_multiple_feeds(self):
        """Should combine articles from multiple feeds."""
        mock_feed1 = MagicMock()
        mock_feed1.feed.get.return_value = "ESPN"
        entry1 = MagicMock()
        entry1.get = lambda key, default="": {
            "title": "ESPN Article",
            "summary": "Content 1",
            "link": "http://espn.com/1",
            "published": None,
        }.get(key, default)
        mock_feed1.entries = [entry1]

        mock_feed2 = MagicMock()
        mock_feed2.feed.get.return_value = "BBC"
        entry2 = MagicMock()
        entry2.get = lambda key, default="": {
            "title": "BBC Article",
            "summary": "Content 2",
            "link": "http://bbc.com/1",
            "published": None,
        }.get(key, default)
        mock_feed2.entries = [entry2]

        for entry in [entry1, entry2]:
            if hasattr(entry, "content"):
                delattr(entry, "content")

        def feed_selector(url):
            if "espn" in url:
                return mock_feed1
            return mock_feed2

        with patch("feedparser.parse", side_effect=feed_selector):
            results = await scrape_rss_feeds(
                ["https://espn.com/rss", "https://bbc.com/rss"], sport="football"
            )

        assert len(results) == 2
        sources = {r["source"] for r in results}
        assert "ESPN" in sources
        assert "BBC" in sources

    @pytest.mark.asyncio
    async def test_scrape_rss_uses_content_over_summary(self):
        """Should prefer entry.content over entry.summary when available."""
        mock_feed = MagicMock()
        mock_feed.feed.get.return_value = "Test Feed"

        entry = MagicMock()
        entry.get = lambda key, default="": {
            "title": "Test",
            "summary": "Short summary",
            "link": "http://test.com",
            "published": None,
        }.get(key, default)
        entry.content = [{"value": "Full article content here"}]
        mock_feed.entries = [entry]

        with patch("feedparser.parse", return_value=mock_feed):
            results = await scrape_rss_feeds(["https://test.com/rss"])

        assert len(results) == 1
        assert results[0]["content"] == "Full article content here"

    @pytest.mark.asyncio
    async def test_scrape_rss_generates_tags_from_title(self):
        """Should generate tags from article title."""
        mock_feed = MagicMock()
        mock_feed.feed.get.return_value = "Sports News"

        entry = MagicMock()
        entry.get = lambda key, default="": {
            "title": "Champions League Final",
            "summary": "Content",
            "link": "http://test.com",
            "published": None,
        }.get(key, default)
        if hasattr(entry, "content"):
            delattr(entry, "content")
        mock_feed.entries = [entry]

        with patch("feedparser.parse", return_value=mock_feed):
            results = await scrape_rss_feeds(["https://test.com/rss"])

        assert "champions" in results[0]["tags"]
        assert "league" in results[0]["tags"]
        assert "final" in results[0]["tags"]

    @pytest.mark.asyncio
    async def test_scrape_rss_without_sport(self):
        """Should work without sport parameter."""
        mock_feed = MagicMock()
        mock_feed.feed.get.return_value = "News"

        entry = MagicMock()
        entry.get = lambda key, default="": {
            "title": "Article",
            "summary": "Content",
            "link": "http://test.com",
            "published": None,
        }.get(key, default)
        if hasattr(entry, "content"):
            delattr(entry, "content")
        mock_feed.entries = [entry]

        with patch("feedparser.parse", return_value=mock_feed):
            results = await scrape_rss_feeds(["https://test.com/rss"])

        assert len(results) == 1
        assert results[0]["sport"] is None

    @pytest.mark.asyncio
    async def test_scrape_empty_feed(self):
        """Should handle feeds with no entries."""
        mock_feed = MagicMock()
        mock_feed.feed.get.return_value = "Empty Feed"
        mock_feed.entries = []

        with patch("feedparser.parse", return_value=mock_feed):
            results = await scrape_rss_feeds(["https://test.com/rss"])

        assert results == []

    @pytest.mark.asyncio
    async def test_scrape_rss_preserves_published_date(self):
        """Should preserve the published date from feed entries."""
        mock_feed = MagicMock()
        mock_feed.feed.get.return_value = "News"

        entry = MagicMock()
        entry.get = lambda key, default="": {
            "title": "Article",
            "summary": "Content",
            "link": "http://test.com",
            "published": "Mon, 15 Jan 2024 10:30:00 GMT",
        }.get(key, default)
        if hasattr(entry, "content"):
            delattr(entry, "content")
        mock_feed.entries = [entry]

        with patch("feedparser.parse", return_value=mock_feed):
            results = await scrape_rss_feeds(["https://test.com/rss"])

        assert results[0]["published_date"] == "Mon, 15 Jan 2024 10:30:00 GMT"

    @pytest.mark.asyncio
    async def test_scrape_rss_handles_empty_title(self):
        """Should handle entries with empty title."""
        mock_feed = MagicMock()
        mock_feed.feed.get.return_value = "News"

        entry = MagicMock()
        entry.get = lambda key, default="": {
            "title": "",
            "summary": "Content",
            "link": "http://test.com",
            "published": None,
        }.get(key, default)
        if hasattr(entry, "content"):
            delattr(entry, "content")
        mock_feed.entries = [entry]

        with patch("feedparser.parse", return_value=mock_feed):
            results = await scrape_rss_feeds(["https://test.com/rss"])

        assert len(results) == 1
        assert results[0]["title"] == ""
        assert results[0]["tags"] == []
