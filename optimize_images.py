#!/usr/bin/env python3
"""
optimize_images.py — Batch WebP optimizer for the BSLC website

All site images are already .webp, so this script doesn't convert formats.
It does two things:
  1. Caps any image larger than it needs to be for how it's actually used
     (resizing is where most of the real savings come from).
  2. Re-encodes with libwebp's best compression method (method=6), which is
     often noticeably smaller than default-settings webp with no visible
     quality difference.

HOW SIZE RULES WORK
--------------------
Different images play different roles on the site (full-width hero photos,
small carousel thumbnails, blog inline images), so a single max-width
doesn't fit all of them. Edit the RULES list below to match your actual
folder/filename conventions. Each rule is:
    (substring to match in the image's relative path, max_width, max_height, quality)
Checked top to bottom, first match wins. Anything matching nothing falls
through to DEFAULT.

ALWAYS run with --dry-run first. It shows which rule each image matches
without changing anything -- fix up the RULES list until the categorization
looks right before doing a real run.

By default this overwrites files in place (same filename, same folder --
no HTML changes needed). Back up your images folder yourself before
running for real; there's no undo.

Usage:
  python optimize_images.py --src ./images --dry-run
  python optimize_images.py --src ./images              # overwrites in place

Requires: pip install Pillow
"""

import argparse
import io
import sys
from pathlib import Path

from PIL import Image

# Edit these to match how your images are actually organized/named.
# (substring to match in relative path, max_width, max_height, quality)
# Order matters: checked top to bottom, FIRST match wins. More specific
# names must come before substrings they contain (e.g. "jayjay" before
# "jay", or "jayjay.webp" would match the "jay" rule instead).
RULES = [
    # Board photos -- tiny 88x88 circles (.board-photo)
    ("keith",   220, 220, 78),
    ("chandu",  220, 220, 78),
    ("susan",   220, 220, 78),
    ("ilana",   220, 220, 78),
    ("erin",    220, 220, 78),

    # Liberated Learners network logo -- 150x150 (.ll-logo). Graphic/text
    # content compresses worse at low quality than photos, hence q90.
    ("liberated_learners_logo", 300, 300, 90),

    # Homepage BSLC wordmark -- 620px display (.logo-img), and it's the
    # LCP (largest contentful paint) element on the homepage, so keep
    # quality high.
    ("home-01-bslc-logo", 700, 700, 88),

    # Staff portraits -- 500x500 display (.staff-photo img)
    # "jayjay" must be listed before "jay" -- see note above.
    ("jayjay",  700, 700, 83),
    ("george",  700, 700, 83),
    ("terry",   700, 700, 83),
    ("amelia",  700, 700, 83),
    ("jon",     700, 700, 83),
    ("jay",     700, 700, 83),

    # Volunteer/Donate page photo -- clamp(160px, 18vw, 260px) (.donate-photo)
    ("donate",  320, 320, 80),

    # Carousel photos -- ~500px display (.sample-day-photo .carousel)
    ("carousel", 500, 500, 80),

    # Exception: this research poster is linked to itself as "view full
    # size in a new tab" -- if it's capped at the same 720px as its inline
    # display, that link does nothing. Keep it genuinely bigger.
    ("engagement-poster", 1700, 1700, 88),

    # True full-bleed hero/split photos -- half viewport wide, up to
    # 100vh tall (.pillar-photo, .split-photo). This is a short, stable
    # list -- add to it only when a new full-bleed photo band is built.
    ("community",         1900, 1900, 85),
    ("mentoring",         1900, 1900, 85),
    ("classes",           1900, 1900, 85),
    ("freedom",           1900, 1900, 85),
    ("light painting",    1900, 1900, 85),
    ("front_page_group",  1900, 1900, 85),
]
# Fallback for anything unmatched above. In practice this means new blog
# post images going forward -- they only ever display up to 720px wide
# (.post-wrap), so this stays modest on purpose. If you add a new
# full-bleed hero/split photo, add it to RULES above rather than relying
# on this default, or it'll come out too small.
DEFAULT = (1000, 1000, 82)


def human(n):
    n = float(n)
    for unit in ["B", "KB", "MB"]:
        if n < 1024:
            return f"{n:.0f}{unit}" if unit == "B" else f"{n:.1f}{unit}"
        n /= 1024
    return f"{n:.1f}GB"


def rule_for(rel_path):
    s = str(rel_path).lower()
    for match, mw, mh, q in RULES:
        if match in s:
            return match, mw, mh, q
    name, (mw, mh, q) = "default", DEFAULT
    return name, mw, mh, q


def optimize_image(path, out_path, max_width, max_height, quality):
    original_size = path.stat().st_size

    # Read the whole file into memory before doing anything else. This
    # matters because by default out_path == path (we're overwriting the
    # original file in place) -- reading everything up front means we're
    # never simultaneously reading from and writing to the same file.
    data = path.read_bytes()
    img = Image.open(io.BytesIO(data))

    if getattr(img, "is_animated", False):
        # Leave animated webp alone -- frame-by-frame handling is a
        # different job. If overwriting in place, there's nothing to do;
        # if writing elsewhere, just copy the bytes through untouched.
        if out_path != path:
            out_path.parent.mkdir(parents=True, exist_ok=True)
            out_path.write_bytes(data)
        return original_size, path.stat().st_size, True

    if img.width > max_width or img.height > max_height:
        img.thumbnail((max_width, max_height), Image.LANCZOS)

    out_path.parent.mkdir(parents=True, exist_ok=True)
    img.save(out_path, "WEBP", quality=quality, method=6)

    new_size = out_path.stat().st_size
    return original_size, new_size, False


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--src", required=True, help="Source directory of images")
    parser.add_argument("--out", help="Write to a separate directory instead of overwriting in place (optional -- useful for a first look before committing to in-place edits)")
    parser.add_argument("--dry-run", action="store_true", help="Report matched rules and sizes, change nothing")
    args = parser.parse_args()

    src_dir = Path(args.src)
    if not src_dir.is_dir():
        print(f"Source directory not found: {src_dir}", file=sys.stderr)
        sys.exit(1)

    out_dir = Path(args.out) if args.out else src_dir

    total_before = 0
    total_after = 0
    count = 0

    for path in sorted(src_dir.rglob("*.webp")):
        rel = path.relative_to(src_dir)
        rule_name, mw, mh, q = rule_for(rel)

        if args.dry_run:
            with Image.open(path) as im:
                w, h = im.size
            size = path.stat().st_size
            print(f"{rel}: {human(size)}  ({w}x{h})  -> rule '{rule_name}' (max {mw}x{mh}, q{q})")
            total_before += size
            count += 1
            continue

        out_path = out_dir / rel
        try:
            before, after, animated = optimize_image(path, out_path, mw, mh, q)
        except Exception as e:
            print(f"  ! skipped {rel}: {e}", file=sys.stderr)
            continue

        total_before += before
        total_after += after
        count += 1
        note = "(animated, copied as-is)" if animated else ""
        pct = (1 - after / before) * 100 if before else 0
        print(f"{rel} [{rule_name}]: {human(before)} -> {human(after)}  ({pct:.0f}% smaller) {note}")

    print()
    if count == 0:
        print("No .webp images found under", src_dir)
    elif args.dry_run:
        print(f"{count} images, total {human(total_before)}")
    else:
        pct = (1 - total_after / total_before) * 100 if total_before else 0
        print(f"{count} images: {human(total_before)} -> {human(total_after)} total ({pct:.0f}% reduction)")


if __name__ == "__main__":
    main()
