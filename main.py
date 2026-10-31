#!/usr/bin/env python3
"""
Main entry point for the FeedToInk RSS-to-ePub pipeline.
"""
import argparse
from datetime import datetime, timezone
import logging
from pathlib import Path
import sys
import yaml

from src.epub_builder import build_pages_index_html, compile_epub
from src.fetcher import fetch_all_feeds
from src.models import DigestConfig


def load_config(config_path: Path, max_articles_override: int | None = None) -> DigestConfig:
    """Load feed configuration and settings from a YAML file."""
    if not config_path.exists():
        raise FileNotFoundError(f"Configuration file not found: {config_path}")

    with config_path.open("r", encoding="utf-8") as fh:
        raw = yaml.safe_load(fh) or {}

    settings = raw.get("settings", {})
    feeds = raw.get("feeds", [])

    max_articles = (
        max_articles_override
        if max_articles_override is not None
        else int(settings.get("max_articles_per_feed", 5))
    )

    return DigestConfig(
        title_prefix=settings.get("title_prefix", "Prensa Diaria"),
        language=settings.get("language", "es"),
        author=settings.get("author", "FeedToInk Automated Press"),
        max_articles_per_feed=max_articles,
        request_timeout=int(settings.get("request_timeout", 15)),
        include_images=bool(settings.get("include_images", False)),
        feeds=feeds,
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Aggregate RSS feeds and compile an ePub optimized for the Xteink X4 Pro."
    )
    parser.add_argument(
        "-c",
        "--config",
        type=Path,
        default=Path("feeds.yaml"),
        help="Path to the YAML feed configuration file (default: feeds.yaml).",
    )
    parser.add_argument(
        "-o",
        "--output-dir",
        type=Path,
        default=Path("dist"),
        help="Output directory for generated artifacts (default: dist).",
    )
    parser.add_argument(
        "-f",
        "--filename",
        type=str,
        default="noticias_latest.epub",
        help="Output ePub filename (default: noticias_latest.epub).",
    )
    parser.add_argument(
        "-m",
        "--max-articles",
        type=int,
        default=None,
        help="Override max_articles_per_feed from feeds.yaml.",
    )
    return parser.parse_args()


def main() -> int:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )
    args = parse_args()

    try:
        config = load_config(args.config, args.max_articles)
    except Exception as exc:
        logging.error("Failed to load configuration: %s", exc)
        return 1

    sections = fetch_all_feeds(config)
    if not sections:
        logging.error("No articles were retrieved from any configured RSS feed.")
        return 1

    now = datetime.now(timezone.utc)
    epub_path = args.output_dir / args.filename

    compile_epub(
        sections=sections,
        config=config,
        output_path=epub_path,
        generated_at=now,
    )
    index_path = build_pages_index_html(
        sections=sections,
        epub_filename=args.filename,
        output_dir=args.output_dir,
        generated_at=now,
    )
    logging.info("Generated GitHub Pages landing index at %s", index_path)
    return 0


if __name__ == "__main__":
    sys.exit(main())
