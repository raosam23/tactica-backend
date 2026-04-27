import httpx
import feedparser
from typing import Optional, List, Dict, Any

async def scrape_wikipedia_articles(
    titles: List[str],
    sport: Optional[str] = None
) -> List[Dict[str, Any]]:
    """
    Scrapes Wikipedia articles and return their content with metadata.
    
    Args:
        titles (List[str]): A List of Wikipedia article titles (underscores for spaces).
        sport (Optional[str]): An optional sport category to tag all articles with

    Returns:
        List[Dict[str, Any]]: A List of Dictionaries with title, content, url, source, sport, tags
    """

    titles_param = "|".join(titles)
    url = "https://en.wikipedia.org/w/api.php"
    params = {
        "action": "query",
        "titles": titles_param,
        "prop": "extracts",
        "explaintext": "1",
        "format": "json",
    }

    async with httpx.AsyncClient() as client:
        response = await client.get(url, params=params)
        response.raise_for_status()
        data = response.json()

    results = []
    for page in data["query"]["pages"].values():
        tags = page["title"].lower().split()
        results.append({
            "title": page["title"],
            "content": page["extract"],
            "url": f"https://en.wikipedia.org/wiki/{page['title'].replace(' ', '_')}",
            "source": "wikipedia",
            "sport": sport,
            "tags": tags,
        })
    return results


def scrape_rss_feeds(
    urls: List[str],
    sport: Optional[str] = None
) -> List[Dict[str, Any]]:
    """
    Scrapes RSS feeds and return article content with metadata.

    Args:
        urls (List[str]): A list of RSS feed URLs to scrape.
        sport (Optional[str]): An optional sport category to tag all articles with

    Returns:
        List[Dict[str, Any]]: A List of Dictionaries with title, content, url, source, sport, tags, published_date
    """

    results = []

    for url in urls:
        feed = feedparser.parse(url)
        source_name = feed.feed.get("title", url)

        for entry in feed.entries:
            title = entry.get("title", "")
            content = entry.get("summary", "")
            link = entry.get("link", "")
            published_date = entry.get("published", None)

            if hasattr(entry, "content") and len(entry.content) > 0:
                content = entry.content[0].get("value", content)
            
            tags = title.lower().split() if title else []
            
            results.append({
                "title": title,
                "content": content,
                "url": link,
                "source": source_name,
                "sport": sport,
                "tags": tags,
                "published_date": published_date,
            })
    return results
