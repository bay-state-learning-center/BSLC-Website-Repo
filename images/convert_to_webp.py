#!/usr/bin/env python3
"""
convert_to_webp.py

Batch-converts JPEG/PNG images to WebP, recursively, while leaving your
originals untouched. Run it against your site's images folder any time
you add new photos.

SETUP (one-time):
    pip install Pillow

USAGE:
    python3 convert_to_webp.py /path/to/images
    python3 convert_to_webp.py /path/to/images --quality 80
    python3 convert_to_webp.py /path/to/images --max-width 1800
    python3 convert_to_webp.py /path/to/images --overwrite

By default this SKIPS any image that already has a matching .webp file
next to it, so it's safe to re-run after adding new photos -- only the
new ones get converted. Use --overwrite to force re-conversion of
everything (e.g. after changing --quality or --max-width).

--max-width caps the image's pixel width, resizing (never upscaling)
before compression. This is usually the biggest lever for file size --
a camera photo that's 4000px wide but only ever displayed at a few
hundred pixels on your site is wasting most of its bytes on detail no
one can see. Height scales automatically to preserve the aspect ratio.
"""

import argparse
import sys
from pathlib import Path

try:
    from PIL import Image
except ImportError:
    print("Pillow isn't installed. Run: pip install Pillow")
    sys.exit(1)

SOURCE_EXTENSIONS = {".jpg", ".jpeg", ".png"}


def human_size(num_bytes: int) -> str:
    size = float(num_bytes)
    for unit in ("B", "KB", "MB", "GB"):
        if size < 1024:
            return f"{size:.1f}{unit}"
        size /= 1024
    return f"{size:.1f}TB"


def convert_folder(root: Path, quality: int, overwrite: bool, max_width: int | None) -> None:
    source_files = [
        p for p in root.rglob("*")
        if p.is_file() and p.suffix.lower() in SOURCE_EXTENSIONS
    ]

    if not source_files:
        print(f"No JPEG/PNG images found under {root}")
        return

    converted = 0
    skipped = 0
    failed = 0
    total_before = 0
    total_after = 0

    for src in sorted(source_files):
        dest = src.with_suffix(".webp")

        if dest.exists() and not overwrite:
            skipped += 1
            continue

        try:
            with Image.open(src) as img:
                # Flatten transparency onto white for JPEG-sourced images;
                # PNG transparency (RGBA) is preserved as-is.
                if img.mode in ("P", "LA"):
                    img = img.convert("RGBA")

                orig_dims = img.size
                resized_note = ""
                if max_width and img.width > max_width:
                    new_height = round(img.height * (max_width / img.width))
                    img = img.resize((max_width, new_height), Image.LANCZOS)
                    resized_note = f"  [{orig_dims[0]}x{orig_dims[1]} -> {img.width}x{img.height}]"

                img.save(dest, "WEBP", quality=quality, method=6)

            before = src.stat().st_size
            after = dest.stat().st_size
            total_before += before
            total_after += after
            converted += 1

            pct = 100 * (1 - after / before) if before else 0
            print(f"  {src.relative_to(root)}  "
                  f"{human_size(before)} -> {human_size(after)} "
                  f"({pct:.0f}% smaller){resized_note}")

        except Exception as e:
            failed += 1
            print(f"  FAILED: {src.relative_to(root)} -- {e}")

    print()
    print(f"Converted: {converted}   Skipped (already exist): {skipped}   Failed: {failed}")
    if total_before:
        pct = 100 * (1 - total_after / total_before)
        print(f"Total size: {human_size(total_before)} -> {human_size(total_after)} "
              f"({pct:.0f}% smaller)")

    if converted:
        print()
        print("Originals were left in place. Once you've spot-checked the .webp")
        print("files, update your HTML <img src=\"...\"> references to point at")
        print("the .webp versions, then delete the old JPEG/PNG files yourself.")


def main():
    parser = argparse.ArgumentParser(description="Batch-convert images to WebP.")
    parser.add_argument("folder", type=str, help="Path to your images folder")
    parser.add_argument("--quality", type=int, default=80,
                         help="WebP quality, 0-100 (default: 80)")
    parser.add_argument("--max-width", type=int, default=None,
                         help="Cap pixel width, resizing larger images down "
                              "(never upscales). e.g. --max-width 1800")
    parser.add_argument("--overwrite", action="store_true",
                         help="Re-convert images even if a .webp already exists")
    args = parser.parse_args()

    root = Path(args.folder).expanduser().resolve()
    if not root.is_dir():
        print(f"Not a folder: {root}")
        sys.exit(1)

    convert_folder(root, quality=args.quality, overwrite=args.overwrite,
                   max_width=args.max_width)


if __name__ == "__main__":
    main()

