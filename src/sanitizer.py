import logging
import re
from typing import Optional
from bs4 import BeautifulSoup
import trafilatura

logger = logging.getLogger(__name__)

ALLOWED_TAGS = {
    "p", "h2", "h3", "h4", "blockquote", "ul", "ol", "li",
    "em", "i", "strong", "b", "code", "pre", "br", "hr"
}

NOISE_PATTERNS = re.compile(
    r"(newsletter|suscr[ií]bete|publicidad|lee tambi[eé]n|te puede interesar|"
    r"s[ií]guenos en|compartir en|cookies|pol[ií]tica de privacidad)",
    re.IGNORECASE,
)


def extract_clean_article_html(
    raw_page_html: Optional[str],
    fallback_rss_html: Optional[str] = None,
    include_images: bool = False,
) -> str:
    """
    Extract the main article body from a full web page using Trafilatura,
    then sanitize the resulting HTML for ultra-compact e-ink rendering.
    Falls back to the RSS entry content/summary when full extraction is unavailable.
    """
    extracted_html: Optional[str] = None

    if raw_page_html:
        try:
            extracted_html = trafilatura.extract(
                raw_page_html,
                output_format="html",
                include_comments=False,
                include_tables=False,
                include_images=include_images,
                include_links=False,
                favor_precision=True,
            )
        except Exception as exc:
            logger.warning("Trafilatura extraction error: %s", exc)

    source_html = extracted_html if extracted_html else (fallback_rss_html or "")
    sanitized = sanitize_html_fragment(source_html)

    # If full-page extraction yielded very little text, try fallback RSS HTML
    if len(sanitized) < 120 and fallback_rss_html and source_html is not fallback_rss_html:
        fallback_sanitized = sanitize_html_fragment(fallback_rss_html)
        if len(fallback_sanitized) > len(sanitized):
            return fallback_sanitized

    return sanitized


def sanitize_html_fragment(raw_html: str) -> str:
    """
    Strip scripts, styles, ads, tracking attributes, and unsupported tags,
    returning clean semantic XHTML suitable for ePub readers.
    """
    if not raw_html or not raw_html.strip():
        return ""

    soup = BeautifulSoup(raw_html, "lxml")

    # Remove unwanted noisy elements completely
    for forbidden in soup.find_all([
        "script", "style", "iframe", "noscript", "svg", "canvas",
        "form", "input", "button", "aside", "nav", "footer", "header",
        "figure", "img", "picture", "video", "audio"
    ]):
        forbidden.decompose()

    # Convert top-level h1 inside article body to h2 so chapter title remains h1
    for h1 in soup.find_all("h1"):
        h1.name = "h2"

    # Unwrap disallowed tags while preserving their inner text
    for tag in list(soup.find_all(True)):
        if tag.name in ("html", "body"):
            continue
        if tag.name not in ALLOWED_TAGS:
            tag.unwrap()
            continue

        # Strip all HTML attributes (classes, inline styles, ids, data-* trackers)
        tag.attrs = {}

        # Remove promotional/boilerplate paragraphs and empty blocks
        text_content = tag.get_text(" ", strip=True)
        if tag.name in ("p", "li", "blockquote") and not text_content:
            tag.decompose()
        elif tag.name == "p" and len(text_content) < 90 and NOISE_PATTERNS.search(text_content):
            tag.decompose()

    body = soup.find("body")
    container = body if body else soup

    # If plain text without block tags was passed, wrap paragraphs properly
    if not container.find(["p", "h2", "h3", "blockquote", "ul", "ol"]):
        text = container.get_text("\n", strip=True)
        paragraphs = [
            f"<p>{line.strip()}</p>"
            for line in text.splitlines()
            if line.strip()
        ]
        return "\n".join(paragraphs)

    return "".join(str(child) for child in container.children).strip()
