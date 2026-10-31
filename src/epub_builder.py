from datetime import datetime, timezone
import html
import logging
from pathlib import Path
from typing import List
from ebooklib import epub

from src.models import DigestConfig, FeedSection

logger = logging.getLogger(__name__)

# CSS specifically tuned for the ultra-compact Xteink X4 Pro e-ink screen:
# - Minimal outer margins to maximize characters per line on a ~4.3" display
# - High contrast, no background colors or grey text that triggers dithering
# - Clean typography with controlled line-height and hyphenation
XTEINK_X4_CSS = """
@namespace epub "http://www.idpf.org/2007/ops";

body {
    font-family: Georgia, "Literata", "Bookerly", serif;
    line-height: 1.38;
    margin: 0.25em 0.35em;
    padding: 0;
    color: #000000;
    background-color: #ffffff;
    text-align: justify;
    hyphens: auto;
    -webkit-hyphens: auto;
}

h1 {
    font-size: 1.22em;
    line-height: 1.2;
    font-weight: bold;
    text-align: left;
    margin: 0.2em 0 0.35em 0;
    padding-bottom: 0.2em;
    border-bottom: 1px solid #000000;
}

h2 {
    font-size: 1.08em;
    line-height: 1.25;
    font-weight: bold;
    text-align: left;
    margin: 0.75em 0 0.3em 0;
}

h3, h4 {
    font-size: 1.0em;
    font-weight: bold;
    text-align: left;
    margin: 0.6em 0 0.25em 0;
}

p {
    margin: 0 0 0.55em 0;
    text-indent: 0;
}

.meta {
    font-size: 0.82em;
    font-style: italic;
    text-align: left;
    margin-bottom: 0.7em;
}

.kicker {
    font-size: 0.78em;
    font-weight: bold;
    text-transform: uppercase;
    letter-spacing: 0.04em;
    text-align: left;
    margin-bottom: 0.15em;
}

blockquote {
    margin: 0.5em 0 0.5em 0.6em;
    padding-left: 0.5em;
    border-left: 2px solid #000000;
    font-style: italic;
}

ul, ol {
    margin: 0.4em 0 0.6em 1.1em;
    padding: 0;
}

li {
    margin-bottom: 0.25em;
    text-align: left;
}

hr {
    border: none;
    border-top: 1px solid #000000;
    margin: 0.8em 0;
}

a {
    color: #000000;
    text-decoration: underline;
}

.toc-list {
    list-style-type: none;
    margin-left: 0;
    padding-left: 0;
}

.toc-list li {
    margin-bottom: 0.45em;
}
"""


def compile_epub(
    sections: List[FeedSection],
    config: DigestConfig,
    output_path: Path,
    generated_at: datetime | None = None,
) -> Path:
    """
    Compile scraped feed sections into an ePub file optimized for the Xteink X4 Pro.
    """
    if generated_at is None:
        generated_at = datetime.now(timezone.utc)

    date_str = generated_at.strftime("%Y-%m-%d")
    human_date = generated_at.strftime("%d/%m/%Y %H:%M UTC")
    book_title = f"{config.title_prefix} - {date_str}"

    book = epub.EpubBook()
    book.set_identifier(f"feedtoink-{date_str}")
    book.set_title(book_title)
    book.set_language(config.language)
    book.add_author(config.author)

    # Attach e-ink stylesheet
    style_item = epub.EpubItem(
        uid="style_xteink",
        file_name="style/xteink.css",
        media_type="text/css",
        content=XTEINK_X4_CSS.encode("utf-8"),
    )
    book.add_item(style_item)

    spine: list = ["nav"]
    toc: list = []
    all_chapters: List[epub.EpubHtml] = []

    # Build frontpage / edition summary chapter with quick links
    cover_links_html: List[str] = []
    article_counter = 0

    for sec_idx, section in enumerate(sections, start=1):
        section_chapters: List[epub.EpubHtml] = []
        sec_title_escaped = html.escape(section.name)

        # Create a compact section divider page
        sec_file = f"sec_{sec_idx:02d}.xhtml"
        sec_items_html: List[str] = []

        for art_idx, article in enumerate(section.articles, start=1):
            article_counter += 1
            chap_file = f"art_{sec_idx:02d}_{art_idx:02d}.xhtml"
            art_title_escaped = html.escape(article.title)

            meta_parts = [sec_title_escaped]
            if article.author:
                meta_parts.append(html.escape(article.author))
            if article.published:
                meta_parts.append(html.escape(article.published))
            meta_line = " · ".join(meta_parts)

            chapter_xhtml = f"""<?xml version="1.0" encoding="utf-8"?>
<!DOCTYPE html>
<html xmlns="http://www.w3.org/1999/xhtml" xml:lang="{config.language}" lang="{config.language}">
<head>
    <title>{art_title_escaped}</title>
    <link rel="stylesheet" type="text/css" href="style/xteink.css"/>
</head>
<body>
    <p class="kicker">{sec_title_escaped}</p>
    <h1>{art_title_escaped}</h1>
    <p class="meta">{meta_line}</p>
    <div class="article-body">
        {article.content_html}
    </div>
</body>
</html>"""

            chap = epub.EpubHtml(
                title=article.title,
                file_name=chap_file,
                lang=config.language,
            )
            chap.set_content(chapter_xhtml.encode("utf-8"))
            chap.add_item(style_item)

            book.add_item(chap)
            section_chapters.append(chap)
            all_chapters.append(chap)
            sec_items_html.append(
                f'<li><a href="{chap_file}">{art_title_escaped}</a></li>'
            )

        section_intro_xhtml = f"""<?xml version="1.0" encoding="utf-8"?>
<!DOCTYPE html>
<html xmlns="http://www.w3.org/1999/xhtml" xml:lang="{config.language}" lang="{config.language}">
<head>
    <title>{sec_title_escaped}</title>
    <link rel="stylesheet" type="text/css" href="style/xteink.css"/>
</head>
<body>
    <p class="kicker">{html.escape(section.category)}</p>
    <h1>{sec_title_escaped}</h1>
    <ul class="toc-list">
        {"".join(sec_items_html)}
    </ul>
</body>
</html>"""

        sec_chap = epub.EpubHtml(
            title=section.name,
            file_name=sec_file,
            lang=config.language,
        )
        sec_chap.set_content(section_intro_xhtml.encode("utf-8"))
        sec_chap.add_item(style_item)
        book.add_item(sec_chap)

        spine.append(sec_chap)
        spine.extend(section_chapters)

        toc.append((epub.Section(section.name, sec_file), section_chapters))
        cover_links_html.append(
            f'<li><strong><a href="{sec_file}">{sec_title_escaped}</a></strong> '
            f'({len(section.articles)})</li>'
        )

    # Create edition overview chapter placed right at the start of the book
    overview_xhtml = f"""<?xml version="1.0" encoding="utf-8"?>
<!DOCTYPE html>
<html xmlns="http://www.w3.org/1999/xhtml" xml:lang="{config.language}" lang="{config.language}">
<head>
    <title>{html.escape(book_title)}</title>
    <link rel="stylesheet" type="text/css" href="style/xteink.css"/>
</head>
<body>
    <p class="kicker">Edición Xteink X4 Pro</p>
    <h1>{html.escape(book_title)}</h1>
    <p class="meta">Generado: {human_date} · {article_counter} artículos</p>
    <h2>Secciones</h2>
    <ul class="toc-list">
        {"".join(cover_links_html)}
    </ul>
</body>
</html>"""

    overview_chap = epub.EpubHtml(
        title="Portada y Sumario",
        file_name="overview.xhtml",
        lang=config.language,
    )
    overview_chap.set_content(overview_xhtml.encode("utf-8"))
    overview_chap.add_item(style_item)
    book.add_item(overview_chap)

    spine.insert(0, overview_chap)
    toc.insert(0, epub.Link("overview.xhtml", "Portada y Sumario", "overview"))

    book.toc = toc
    book.spine = spine
    book.add_item(epub.EpubNcx())
    book.add_item(epub.EpubNav())

    output_path.parent.mkdir(parents=True, exist_ok=True)
    epub.write_epub(str(output_path), book, {})
    logger.info("Successfully compiled ePub at %s (%d articles)", output_path, article_counter)
    return output_path


def build_pages_index_html(
    sections: List[FeedSection],
    epub_filename: str,
    output_dir: Path,
    generated_at: datetime | None = None,
) -> Path:
    """
    Generate a clean, mobile-friendly index.html for GitHub Pages so the user can
    download `noticias_latest.epub` with a single tap on their smartphone.
    """
    if generated_at is None:
        generated_at = datetime.now(timezone.utc)

    human_date = generated_at.strftime("%d/%m/%Y %H:%M UTC")
    total_articles = sum(len(s.articles) for s in sections)

    sections_markup: List[str] = []
    for section in sections:
        items = "".join(
            f'<li><a href="{html.escape(a.url)}" target="_blank" rel="noopener">'
            f'{html.escape(a.title)}</a></li>'
            for a in section.articles
        )
        sections_markup.append(
            f"<section><h2>{html.escape(section.name)}</h2><ul>{items}</ul></section>"
        )

    index_html = f"""<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="utf-8"/>
    <meta name="viewport" content="width=device-width, initial-scale=1"/>
    <title>FeedToInk · Prensa Diaria (Xteink X4 Pro)</title>
    <style>
        :root {{
            color-scheme: light dark;
        }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
            max-width: 640px;
            margin: 0 auto;
            padding: 1.25rem;
            line-height: 1.5;
        }}
        .card {{
            border: 2px solid currentColor;
            border-radius: 10px;
            padding: 1.25rem;
            margin-bottom: 1.5rem;
            text-align: center;
        }}
        .btn {{
            display: inline-block;
            margin-top: 0.75rem;
            padding: 0.85rem 1.4rem;
            font-size: 1.05rem;
            font-weight: 700;
            text-decoration: none;
            border-radius: 8px;
            background: #111;
            color: #fff;
            border: 2px solid #111;
        }}
        @media (prefers-color-scheme: dark) {{
            .btn {{
                background: #f5f5f5;
                color: #111;
                border-color: #f5f5f5;
            }}
        }}
        h1 {{ margin: 0 0 0.35rem 0; font-size: 1.5rem; }}
        h2 {{ font-size: 1.15rem; border-bottom: 1px solid currentColor; padding-bottom: 0.25rem; }}
        .meta {{ font-size: 0.9rem; opacity: 0.8; margin: 0; }}
        ul {{ padding-left: 1.2rem; }}
        li {{ margin-bottom: 0.4rem; }}
        a {{ color: inherit; }}
    </style>
</head>
<body>
    <div class="card">
        <h1>Prensa Diaria · Xteink X4 Pro</h1>
        <p class="meta">Última actualización: {human_date} ({total_articles} artículos)</p>
        <a class="btn" href="./{html.escape(epub_filename)}" download="{html.escape(epub_filename)}">
            Descargar {html.escape(epub_filename)}
        </a>
    </div>
    {"".join(sections_markup)}
</body>
</html>
"""
    output_dir.mkdir(parents=True, exist_ok=True)
    index_path = output_dir / "index.html"
    index_path.write_text(index_html, encoding="utf-8")
    return index_path
