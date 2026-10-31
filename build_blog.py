#!/usr/bin/env python3
"""
build_blog.py — BSLC blog build script

Converts Markdown blog post drafts into HTML pages matching the site's
existing post template, and regenerates the post listing on blog.html.

This runs automatically as Netlify's build command on every deploy. You
can also run it locally first to preview changes before pushing:

    python3 build_blog.py

INPUT:
  drafts/*.md               one file per post, Markdown + a frontmatter block
  posts/post-template.html  HTML skeleton with {{TOKEN}} placeholders

OUTPUT:
  posts/<slug>.html   one generated HTML page per post
  blog.html           the section between <!-- POSTS START --> and
                       <!-- POSTS END --> is fully replaced every run

IMPORTANT — never hand-edit:
  - Any file in posts/ except post-template.html
  - The listing section of blog.html (between the POSTS markers)
  Both are regenerated from scratch every time this script runs, so any
  manual edits there will be silently overwritten on the next build.
  Make changes in the .md files in drafts/ instead.

DRAFT FILE FORMAT (drafts/your-post-name.md):

    ---
    title: Your Post Title
    date: 2026-07-10
    author: Your Name
    description: A 1-2 sentence summary for search engines, under ~160 chars.
    teaser: The preview text shown on the blog listing page.
    hero_image: some-photo.webp
    hero_alt: Alt text describing the hero image.
    ---

    Your post body, written in Markdown.

    Supported: paragraphs, **bold**, *italic* (or _italic_), ## and ###
    headings, "- " bulleted lists, and images as their own paragraph:

    ![Alt text for the image](filename.webp "Optional caption")

    Anything beyond that — a linked image, an embedded file download link,
    or any custom markup — can be written as raw HTML directly: a block
    whose first character is '<' is passed through completely untouched.

Frontmatter fields that are optional:
  hero_image / hero_alt   — omit both entirely if the post has no hero image
  teaser_alt              — alt text for the thumbnail on blog.html, if you
                             want it to differ from hero_alt (defaults to
                             hero_alt if not set)
  slug                    — overrides the auto-generated filename/URL slug.
                             REQUIRED if you want the output filename to be
                             different from what the title would produce —
                             e.g. to preserve an existing post's URL exactly.
  page_title               — overrides the <title> tag (browser tab / search
                             result title) so it can differ from the on-page
                             H1 heading. Defaults to 'title' if not set.

A line inside the frontmatter block starting with '#' is treated as a
comment and ignored — useful for leaving guidance notes in a template file.
"""

import re
import sys
from pathlib import Path
from datetime import datetime

DRAFTS_DIR = Path("drafts")
POSTS_DIR = Path("posts")
TEMPLATE_PATH = POSTS_DIR / "post-template.html"
BLOG_INDEX_PATH = Path("blog.html")

# BSLC's production domain. Used to build absolute URLs for og:image /
# og:url, which social platforms and messaging apps require in full (a
# relative path like "images/foo.webp" won't work for link-preview cards).
SITE_URL = "https://www.baystatelearning.org"

# Used as the social-preview image for any post with no hero_image set.
DEFAULT_OG_IMAGE = "og-image.png"
DEFAULT_OG_IMAGE_ALT = "Bay State Learning Center logo on a charcoal background"

START_MARKER = "<!-- POSTS START -->"
END_MARKER = "<!-- POSTS END -->"

REQUIRED_FIELDS = ("title", "date", "author", "description", "teaser")


def slugify(title):
    slug = title.lower().strip()
    slug = re.sub(r"[^a-z0-9]+", "-", slug)
    return slug.strip("-")


def parse_frontmatter(text, filename):
    text = text.lstrip()
    match = re.match(r"^---[ \t]*\n(.*?)\n---[ \t]*\n?(.*)$", text, re.DOTALL)
    if not match:
        if not text.startswith("---"):
            raise ValueError("missing opening '---' frontmatter delimiter")
        raise ValueError("frontmatter block is not closed with a second '---'")
    front, body = match.groups()
    meta = {}
    for line_num, line in enumerate(front.strip().splitlines(), start=1):
        stripped = line.strip()
        if not stripped:
            continue
        if stripped.startswith("#"):
            continue
        if ":" not in line:
            raise ValueError(f"frontmatter line {line_num} has no ':' — '{line}'")
        key, _, value = line.partition(":")
        meta[key.strip()] = value.strip()
    for field in REQUIRED_FIELDS:
        if field not in meta:
            raise ValueError(f"missing required '{field}:' field")
    if meta.get("hero_image") and not meta.get("hero_alt"):
        raise ValueError("'hero_image' is set but 'hero_alt' is missing")
    return meta, body.strip()


def format_date(iso_date):
    """'2026-07-10' -> 'July 10, 2026', matching the site's existing date style."""
    dt = datetime.strptime(iso_date, "%Y-%m-%d")
    return f"{dt.strftime('%B')} {dt.day}, {dt.year}"


def inline_format(text):
    """Bold/italic within a line. Anything else (including raw HTML) passes through."""
    text = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", text)
    text = re.sub(r"(?<!\*)\*(?!\*)(.+?)(?<!\*)\*(?!\*)", r"<em>\1</em>", text)
    text = re.sub(r"(?<!\w)_(.+?)_(?!\w)", r"<em>\1</em>", text)
    return text


IMAGE_RE = re.compile(r'^!\[(.*?)\]\(([^\s")]+)(?:\s+"([^"]*)")?\)$')


def is_list_block(block):
    lines = [line for line in block.splitlines() if line.strip()]
    return bool(lines) and all(line.strip().startswith("- ") for line in lines)


def render_body(markdown_body):
    """Small Markdown -> HTML converter tailored to this site's post template.

    Supports paragraphs, **bold**, *italic*/_italic_, ## and ### headings,
    "- " bulleted lists, and ![alt](file.webp "caption") images.

    Anything else — a linked image, an embedded PDF link, a custom <figure>,
    or any markup this parser doesn't cover — can be written as raw HTML
    directly in the draft: any block whose first character is '<' is passed
    through completely untouched (no <p> wrapping, no bold/italic parsing).
    """
    html_blocks = []
    blocks = re.split(r"\n\s*\n", markdown_body.strip())
    for block in blocks:
        block = block.strip()
        if not block:
            continue
        if block.startswith("<"):
            html_blocks.append(block)
            continue
        image_match = IMAGE_RE.match(block)
        if image_match:
            alt, filename, caption = image_match.groups()
            figcaption = f"\n      <figcaption>{caption}</figcaption>" if caption else ""
            html_blocks.append(
                f'    <figure>\n'
                f'      <img src="../images/{filename}" alt="{alt}" loading="lazy">'
                f'{figcaption}\n'
                f'    </figure>'
            )
        elif block.startswith("### "):
            html_blocks.append(f"    <h3>{inline_format(block[4:].strip())}</h3>")
        elif block.startswith("## "):
            html_blocks.append(f"    <h2>{inline_format(block[3:].strip())}</h2>")
        elif is_list_block(block):
            items = [line.strip()[2:].strip() for line in block.splitlines() if line.strip()]
            li_html = "\n".join(f"      <li>{inline_format(item)}</li>" for item in items)
            html_blocks.append(f"    <ul>\n{li_html}\n    </ul>")
        else:
            html_blocks.append(f"    <p>{inline_format(block)}</p>")
    return "\n\n".join(html_blocks)


def render_post_html(meta, body_html, template_text, slug):
    hero_block = ""
    if meta.get("hero_image"):
        hero_block = (
            f'<img class="post-hero" src="../images/{meta["hero_image"]}" '
            f'alt="{meta["hero_alt"]}" fetchpriority="high">'
        )
        og_image, og_image_alt = meta["hero_image"], meta["hero_alt"]
    else:
        og_image, og_image_alt = DEFAULT_OG_IMAGE, DEFAULT_OG_IMAGE_ALT

    page_title = meta.get("page_title") or meta["title"]
    post_url = f"{SITE_URL}/posts/{slug}"
    og_image_url = f"{SITE_URL}/images/{og_image}"

    html = template_text
    html = html.replace("{{PAGE_TITLE}}", page_title)
    html = html.replace("{{TITLE}}", meta["title"])
    html = html.replace("{{DESCRIPTION}}", meta["description"])
    html = html.replace("{{AUTHOR}}", meta["author"])
    html = html.replace("{{DATE}}", format_date(meta["date"]))
    html = html.replace("{{HERO_IMAGE_BLOCK}}", hero_block)
    html = html.replace("{{BODY}}", body_html)
    html = html.replace("{{POST_URL}}", post_url)
    html = html.replace("{{OG_IMAGE_URL}}", og_image_url)
    html = html.replace("{{OG_IMAGE_ALT}}", og_image_alt)
    return html


def render_index_entry(meta, slug, is_first):
    teaser_alt = meta.get("teaser_alt") or meta.get("hero_alt", "")
    if meta.get("hero_image"):
        priority_attr = 'fetchpriority="high"' if is_first else 'loading="lazy"'
        photo_block = (
            '    <div class="blog-entry-photo">\n'
            f'      <img src="images/{meta["hero_image"]}" alt="{teaser_alt}" {priority_attr}>\n'
            '    </div>'
        )
    else:
        photo_block = '    <div class="blog-entry-photo placeholder"></div>'

    return (
        '  <article class="blog-entry">\n'
        '    <div class="blog-entry-text">\n'
        '      <div class="blog-meta">\n'
        f'        <span class="blog-author">{meta["author"]}</span>\n'
        f'        <span class="blog-date">{format_date(meta["date"])}</span>\n'
        '      </div>\n'
        '      <h2 class="blog-entry-title">\n'
        f'        <a href="posts/{slug}">{meta["title"]}</a>\n'
        '      </h2>\n'
        f'      <p class="blog-teaser">{meta["teaser"]}</p>\n'
        f'      <a class="blog-read-more" href="posts/{slug}">Read more</a>\n'
        '    </div>\n'
        f'{photo_block}\n'
        '  </article>'
    )


def main():
    if not TEMPLATE_PATH.exists():
        sys.exit(f"ERROR: missing template at {TEMPLATE_PATH}")
    template_text = TEMPLATE_PATH.read_text(encoding="utf-8")

    if not DRAFTS_DIR.exists():
        sys.exit(f"ERROR: missing {DRAFTS_DIR}/ folder")

    draft_files = sorted(
        f for f in DRAFTS_DIR.glob("*.md") if not f.name.startswith(("_", "."))
    )
    if not draft_files:
        print("No drafts found in drafts/ — nothing to build.")
        return

    posts = []
    for draft_path in draft_files:
        text = draft_path.read_text(encoding="utf-8")
        try:
            meta, body_md = parse_frontmatter(text, draft_path.name)
        except ValueError as e:
            sys.exit(f"ERROR in {draft_path.name}: {e}")

        slug = meta.get("slug") or slugify(meta["title"])
        if slug == "post-template":
            sys.exit(
                f"ERROR in {draft_path.name}: the slug 'post-template' is reserved "
                "(it's the template's filename). Set an explicit 'slug:' field to "
                "something else, or adjust the title."
            )
        posts.append((meta, slug, body_md, draft_path.name))

    # Guard against two drafts accidentally producing the same output filename
    seen_slugs = {}
    for meta, slug, _, filename in posts:
        if slug in seen_slugs:
            sys.exit(
                f"ERROR: both {filename} and {seen_slugs[slug]} produce the slug "
                f"'{slug}'. Set an explicit 'slug:' field on one of them."
            )
        seen_slugs[slug] = filename

    posts.sort(key=lambda p: p[0]["date"], reverse=True)  # newest first

    for meta, slug, body_md, _ in posts:
        body_html = render_body(body_md)
        post_html = render_post_html(meta, body_html, template_text, slug)
        out_path = POSTS_DIR / f"{slug}.html"
        out_path.write_text(post_html, encoding="utf-8")
        print(f"Wrote {out_path}")

    if not BLOG_INDEX_PATH.exists():
        sys.exit(f"ERROR: missing {BLOG_INDEX_PATH}")
    blog_text = BLOG_INDEX_PATH.read_text(encoding="utf-8")
    if START_MARKER not in blog_text or END_MARKER not in blog_text:
        sys.exit(
            f"ERROR: {BLOG_INDEX_PATH} is missing the {START_MARKER} / {END_MARKER} "
            "markers. Add them once, wrapping the post listing inside <div class="
            '"blog-list">, then commit and push again.'
        )

    divider = '\n\n  <div class="blog-divider-wrap"><hr class="blog-divider"></div>\n\n'
    entries_html = divider.join(
        render_index_entry(meta, slug, is_first=(i == 0))
        for i, (meta, slug, _, _) in enumerate(posts)
    )
    new_section = f"{START_MARKER}\n{entries_html}\n{END_MARKER}"

    start_idx = blog_text.index(START_MARKER)
    end_idx = blog_text.index(END_MARKER) + len(END_MARKER)
    blog_text = blog_text[:start_idx] + new_section + blog_text[end_idx:]
    BLOG_INDEX_PATH.write_text(blog_text, encoding="utf-8")
    print(f"Updated {BLOG_INDEX_PATH} with {len(posts)} post(s).")


if __name__ == "__main__":
    main()
