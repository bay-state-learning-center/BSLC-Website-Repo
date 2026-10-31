#!/usr/bin/env python3
"""
build_sitemap.py — BSLC sitemap generator

Walks the site project and writes a sitemap.xml listing every live HTML
page, for Google Search Console submission.

Run it locally to preview before committing:

    python3 build_sitemap.py

Or add it to Netlify's build command alongside build_blog.py, so new
pages and blog posts get picked up automatically on every deploy:

    python3 build_blog.py && python3 build_sitemap.py

OUTPUT:
  sitemap.xml   written to the project root

WHAT'S INCLUDED:
  Every *.html file found anywhere in the project (found automatically —
  you don't need to update this script when you add a page or a post).

WHAT'S EXCLUDED:
  - posts/post-template.html   (the blog template, not a real page)
  - 404.html                   (an error page, not meant to be indexed)
  - anything inside drafts/, .git/, node_modules/, .netlify/

If a future page shouldn't be indexed (a work-in-progress page, an
internal/admin page, etc.), add its path to EXCLUDE_FILES below, or its
containing folder to EXCLUDE_DIRS.

URL FORMAT:
  Every page on the site -- posts included -- uses a clean URL with no
  ".html" as its canonical form (build_blog.py and every top-level page
  were updated together to agree on this). This script strips ".html"
  from every discovered file accordingly. If that ever changes for
  posts specifically, flip POSTS_KEEP_EXTENSION back to True.
"""

import sys
from pathlib import Path
from datetime import date

SITE_ROOT = Path(".")
SITE_URL = "https://www.baystatelearning.org"
OUTPUT_PATH = Path("sitemap.xml")

EXCLUDE_DIRS = {".git", "node_modules", "drafts", ".netlify"}
EXCLUDE_FILES = {"posts/post-template.html", "404.html"}

POSTS_KEEP_EXTENSION = False


def find_html_files(root):
    files = []
    for path in root.rglob("*.html"):
        rel = path.relative_to(root)
        if any(part in EXCLUDE_DIRS for part in rel.parts):
            continue
        if str(rel) in EXCLUDE_FILES:
            continue
        files.append(rel)
    return sorted(files)


def to_url_path(rel_path):
    """index.html -> directory root | posts/x.html -> /posts/x.html |
    everything else -> extension stripped."""
    parts = list(rel_path.parts)
    if parts[-1] == "index.html":
        parts = parts[:-1]
        joined = "/".join(parts)
        return f"/{joined}/" if joined else "/"
    if parts[0] == "posts" and POSTS_KEEP_EXTENSION:
        return "/" + "/".join(parts)
    parts[-1] = parts[-1][: -len(".html")]
    return "/" + "/".join(parts)


def build_sitemap(files):
    # Using today's date for every entry rather than a per-file last-
    # modified timestamp: Netlify's build environment is a fresh clone
    # each time, so filesystem mtimes don't reliably reflect real edit
    # history. Google treats <lastmod> as informational and doesn't
    # weight it heavily, so this is a reasonable simplification rather
    # than a real limitation.
    today = date.today().isoformat()
    lines = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">',
    ]
    for rel_path in files:
        url = SITE_URL + to_url_path(rel_path)
        lines += [
            "  <url>",
            f"    <loc>{url}</loc>",
            f"    <lastmod>{today}</lastmod>",
            "  </url>",
        ]
    lines.append("</urlset>")
    return "\n".join(lines) + "\n"


def main():
    files = find_html_files(SITE_ROOT)
    if not files:
        sys.exit(
            "ERROR: no HTML files found. Run this from the site project's "
            "root directory, or check EXCLUDE_DIRS/EXCLUDE_FILES above."
        )
    xml = build_sitemap(files)
    OUTPUT_PATH.write_text(xml, encoding="utf-8")
    print(f"Wrote {OUTPUT_PATH} with {len(files)} URL(s):")
    for rel_path in files:
        print(f"  {to_url_path(rel_path)}")


if __name__ == "__main__":
    main()
