from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class Article:
    """Represents a single scraped and sanitized news article."""
    title: str
    url: str
    source_name: str
    author: Optional[str] = None
    published: Optional[str] = None
    summary: Optional[str] = None
    content_html: str = ""


@dataclass
class FeedSection:
    """Represents a collection of articles belonging to a specific RSS feed."""
    name: str
    url: str
    category: str = "General"
    articles: List[Article] = field(default_factory=list)


@dataclass
class DigestConfig:
    """Configuration parameters loaded from feeds.yaml."""
    title_prefix: str = "Prensa Diaria"
    language: str = "es"
    author: str = "FeedToInk Automated Press"
    max_articles_per_feed: int = 5
    request_timeout: int = 15
    include_images: bool = False
    feeds: List[dict] = field(default_factory=list)
