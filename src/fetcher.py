from datetime import datetime
from email.utils import parsedate_to_datetime
import html
import logging
from typing import List, Optional
import feedparser
import requests

from src.models import Article, DigestConfig, FeedSection
from src.sanitizer import extract_clean_article_html

logger = logging.getLogger(__name__)

DEFAULT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36 FeedToInk/1.0"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "es-ES,es;q=0.9,en;q=0.8",
}


def _extract_rss_body(entry: dict) -> str:
    """Retrieve the richest HTML snippet available inside the RSS entry itself."""
    if "content" in entry and entry["content"]:
        for item in entry["content"]:
            if item.get("value"):
                return item["value"]
    if entry.get("summary"):
        return entry["summary"]
    if entry.get("description"):
        return entry["description"]
    return ""


def _format_published_date(entry: dict) -> Optional[str]:
    """Normalize the entry publication date into a compact human-readable string."""
    raw_date = entry.get("published") or entry.get("updated")
    if not raw_date:
        return None
    try:
        dt = parsedate_to_datetime(raw_date)
        return dt.strftime("%d/%m/%Y %H:%M")
    except Exception:
        return raw_date[:25]


def fetch_url_html(url: str, timeout: int = 15) -> Optional[str]:
    """Fetch full HTML from an article URL with graceful timeout and error handling."""
    if not url:
        return None
    try:
        response = requests.get(url, headers=DEFAULT_HEADERS, timeout=timeout)
        response.raise_for_status()
        if not response.encoding or response.encoding.lower() == "iso-8859-1":
            response.encoding = response.apparent_encoding
        return response.text
    except requests.RequestException as exc:
        logger.warning("Could not fetch full page for %s: %s", url, exc)
        return None


def fetch_feed_section(feed_meta: dict, config: DigestConfig) -> FeedSection:
    """Parse a single RSS feed and scrape/sanitize up to max_articles_per_feed entries."""
    name = feed_meta.get("name", "Untitled Feed")
    url = feed_meta.get("url", "")
    category = feed_meta.get("category", "Actualidad")

    section = FeedSection(name=name, url=url, category=category)
    if not url:
        logger.warning("Skipping feed '%s' with empty URL.", name)
        return section

    logger.info("Fetching RSS feed: %s (%s)", name, url)
    try:
        resp = requests.get(url, headers=DEFAULT_HEADERS, timeout=config.request_timeout)
        resp.raise_for_status()
        parsed_feed = feedparser.parse(resp.content)
    except requests.RequestException as exc:
        logger.error("Failed to download RSS feed %s: %s", name, exc)
        return section

    entries = parsed_feed.entries[: config.max_articles_per_feed]
    for entry in entries:
        raw_title = entry.get("title", "Sin título").strip()
        title = html.unescape(raw_title)
        link = entry.get("link", "").strip()
        author = entry.get("author")
        published = _format_published_date(entry)
        rss_fallback_html = _extract_rss_body(entry)

        logger.info("  -> Processing article: %s", title)
        raw_page_html = fetch_url_html(link, timeout=config.request_timeout)
        clean_html = extract_clean_article_html(
            raw_page_html=raw_page_html,
            fallback_rss_html=rss_fallback_html,
            include_images=config.include_images,
        )

        if not clean_html:
            logger.warning("  -> Skipping empty article: %s", title)
            continue

        section.articles.append(
            Article(
                title=title,
                url=link,
                source_name=name,
                author=author,
                published=published,
                content_html=clean_html,
            )
        )

    return section


def fetch_all_feeds(config: DigestConfig) -> List[FeedSection]:
    """Fetch all configured feeds and return only sections that contain valid articles."""
    sections: List[FeedSection] = []
    for feed_meta in config.feeds:
        section = fetch_feed_section(feed_meta, config)
        if section.articles:
            sections.append(section)
    return sections
