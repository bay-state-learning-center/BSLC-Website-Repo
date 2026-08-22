#!/usr/bin/env python3
"""
add_ga4_tag.py

Inserts the Google Analytics 4 (gtag.js) snippet into every .html file
in a directory tree, right before the closing </head> tag.

Safe to re-run: if a file already contains the snippet (matched by the
GA4 Measurement ID), it's skipped rather than duplicated.

Usage:
    python3 add_ga4_tag.py --id G-XXXXXXXXXX
    python3 add_ga4_tag.py --id G-XXXXXXXXXX --dir . --dry-run

Run this from the root of your site repo (or pass --dir to point at it).
Includes the blog post template used by build_blog.py, since that's
just another .html file on disk -- but remember: editing the template
only affects posts generated AFTER you re-run build_blog.py. Existing
blog post .html files on disk won't retroactively get the tag until
you rebuild them.
"""

import argparse
import sys
from pathlib import Path

SNIPPET_TEMPLATE = """<!-- Google tag (gtag.js) -->
<script async src="https://www.googletagmanager.com/gtag/js?id={measurement_id}"></script>
<script>
  window.dataLayer = window.dataLayer || [];
  function gtag(){{dataLayer.push(arguments);}}
  gtag('js', new Date());
  gtag('config', '{measurement_id}');
</script>
"""

# Directories we never want to touch
SKIP_DIRS = {".git", "node_modules", ".netlify", "dist", "_site"}


def find_html_files(root: Path):
    for path in root.rglob("*.html"):
        if any(part in SKIP_DIRS for part in path.parts):
            continue
        yield path


def already_tagged(content: str, measurement_id: str) -> bool:
    return measurement_id in content


def insert_snippet(content: str, measurement_id: str) -> str | None:
    """Returns updated content, or None if no </head> tag was found."""
    snippet = SNIPPET_TEMPLATE.format(measurement_id=measurement_id)
    lower = content.lower()
    idx = lower.rfind("</head>")
    if idx == -1:
        return None
    return content[:idx] + snippet + content[idx:]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--id", required=True, help="Your GA4 Measurement ID, e.g. G-XXXXXXXXXX")
    parser.add_argument("--dir", default=".", help="Root directory to scan (default: current directory)")
    parser.add_argument("--dry-run", action="store_true", help="Show what would change without writing files")
    args = parser.parse_args()

    root = Path(args.dir).resolve()
    if not root.exists():
        print(f"Directory not found: {root}")
        sys.exit(1)

    updated, skipped_tagged, skipped_no_head = [], [], []

    for path in find_html_files(root):
        content = path.read_text(encoding="utf-8")

        if already_tagged(content, args.id):
            skipped_tagged.append(path)
            continue

        new_content = insert_snippet(content, args.id)
        if new_content is None:
            skipped_no_head.append(path)
            continue

        if not args.dry_run:
            path.write_text(new_content, encoding="utf-8")
        updated.append(path)

    print(f"\n{'Would update' if args.dry_run else 'Updated'} {len(updated)} file(s):")
    for p in updated:
        print(f"  + {p.relative_to(root)}")

    if skipped_tagged:
        print(f"\nAlready tagged, skipped {len(skipped_tagged)} file(s):")
        for p in skipped_tagged:
            print(f"  = {p.relative_to(root)}")

    if skipped_no_head:
        print(f"\nNo </head> tag found, skipped {len(skipped_no_head)} file(s) -- check these manually:")
        for p in skipped_no_head:
            print(f"  ! {p.relative_to(root)}")

    if args.dry_run:
        print("\nDry run only -- no files were changed. Remove --dry-run to apply.")


if __name__ == "__main__":
    main()
