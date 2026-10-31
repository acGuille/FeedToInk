# FeedToInk

Automated, zero-cost RSS-to-ePub aggregation pipeline built with Python and GitHub Actions, specifically tailored for ultra-compact e-ink readers such as the **Xteink X4 Pro**.

## Features

- **Full-Text Extraction & Sanitation**: Uses `feedparser`, `trafilatura`, and `BeautifulSoup` (`lxml`) to fetch full articles, strip ads, scripts, trackers, and promotional clutter, and fall back gracefully to RSS summaries when needed.
- **Xteink X4 Pro Optimization**: Generates clean semantic XHTML styled with high-contrast, ultra-low-margin CSS (`style/xteink.css`), hyphenation, and hierarchical NCX/Nav Table of Contents for effortless hardware-button navigation on a compact 4.3" e-ink screen.
- **Zero-Cost Dual Hosting**: Runs daily at `06:00 UTC` via GitHub Actions and publishes `noticias_latest.epub` both to **GitHub Pages** (with a mobile-friendly one-tap landing page) and to a rolling **GitHub Release** (`latest`).

## Repository Structure

```text
FeedToInk/
├── .github/
│   └── workflows/
│       └── daily-epub.yml   # Daily cron + manual GitHub Actions pipeline
├── src/
│   ├── __init__.py
│   ├── models.py            # Data structures for feeds, articles, and config
│   ├── fetcher.py           # RSS parsing and HTTP article downloading
│   ├── sanitizer.py         # Trafilatura extraction and DOM sanitization
│   └── epub_builder.py      # ePub compilation and GitHub Pages HTML builder
├── feeds.yaml               # Declarative list of Spanish news & opinion feeds
├── main.py                  # CLI entry point
├── requirements.txt         # Python dependencies
└── README.md
```

## Local Usage

1. Create a virtual environment and install dependencies:

   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   ```

2. Run the generator:

   ```bash
   python main.py --output-dir dist --filename noticias_latest.epub
   ```

   You can also test a quick build with fewer articles per feed:

   ```bash
   python main.py --max-articles 2
   ```

3. Find the compiled book at `dist/noticias_latest.epub` and the companion web page at `dist/index.html`.

## Customizing Feeds

Edit `feeds.yaml` to add, remove, or reorder RSS sources and tweak global parameters:

```yaml
settings:
  title_prefix: "Prensa Diaria"
  language: "es"
  author: "FeedToInk Automated Press"
  max_articles_per_feed: 5
  request_timeout: 15
  include_images: false

feeds:
  - name: "El País - Opinión"
    url: "https://feeds.elpais.com/mrss-s/pages/ep/site/elpais.com/section/opinion/portada"
    category: "Opinión y Análisis"
```

## GitHub Actions & Hosting Setup

1. **Workflow Permissions**:
   - Navigate to **Settings → Actions → General** in your GitHub repository.
   - Under **Workflow permissions**, select **Read and write permissions** and click **Save**.
2. **GitHub Pages Setup**:
   - Navigate to **Settings → Pages**.
   - Under **Build and deployment → Source**, select **GitHub Actions**.
3. **Download URLs**:
   - **GitHub Pages Landing Page**: `https://acguille.github.io/FeedToInk/`
   - **Direct ePub Link (Pages)**: `https://acguille.github.io/FeedToInk/noticias_latest.epub`
   - **Direct ePub Link (Releases)**: `https://github.com/acGuille/FeedToInk/releases/latest/download/noticias_latest.epub`
