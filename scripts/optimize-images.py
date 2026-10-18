#!/usr/bin/env python3
"""Create or verify responsive quality-75 AVIFs.

Run after adding an image: python3 scripts/optimize-images.py
Verify committed derivatives: python3 scripts/optimize-images.py --check
Store originals in assets/images/originals; AVIFs go in static/assets/images.
Hugo mounts originals at their existing URLs for social previews and old links.
Write alt text in the content, or add an "alt" entry to data/images.json.
"""
import argparse
import hashlib
import json
import re
import shutil
import subprocess
import tempfile
from html.parser import HTMLParser
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "data/images.json"
ORIGINALS = ROOT / "assets/images/originals"
PUBLISHED_IMAGES = ROOT / "static/assets/images"
QUALITY = 75
WIDTHS = (640, 1280)
RASTER_EXTENSIONS = {".jpeg", ".jpg", ".png", ".tif", ".tiff", ".webp"}


class Images(HTMLParser):
    def __init__(self):
        super().__init__()
        self.paths = set()

    def handle_starttag(self, tag, attrs):
        src = dict(attrs).get("src", "")
        if tag == "img" and src.startswith("/assets/images/"):
            self.paths.add(src)


def run(*args):
    return subprocess.run(args, check=True, capture_output=True, text=True).stdout


def image_tool():
    if shutil.which("sips"):
        return "sips"
    if shutil.which("magick"):
        return "magick"
    if shutil.which("convert") and shutil.which("identify"):
        return "convert"
    raise SystemExit("Required image tool missing: install sips or ImageMagick")


def dimensions(path):
    tool = image_tool()
    if tool == "sips":
        result = run("sips", "-g", "pixelWidth", "-g", "pixelHeight", str(path))
        return tuple(int(re.search(rf"{name}: (\d+)", result)[1])
                     for name in ("pixelWidth", "pixelHeight"))
    if tool == "magick":
        result = run("magick", "identify", "-format", "%w %h", str(path))
    else:
        result = run("identify", "-format", "%w %h", str(path))
    return tuple(map(int, result.split()))


def resize(source, destination, width):
    tool = image_tool()
    if tool == "sips":
        run("sips", "--resampleWidth", str(width), "-s", "format", "png",
            str(source), "--out", str(destination))
    elif tool == "magick":
        run("magick", str(source), "-resize", f"{width}x", str(destination))
    else:
        run("convert", str(source), "-resize", f"{width}x", str(destination))


def sha256(path):
    digest = hashlib.sha256()
    with path.open("rb") as image:
        for chunk in iter(lambda: image.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def avif_dimensions(path):
    result = run("avifdec", "--info", str(path))
    match = re.search(r"Resolution\s+: (\d+)x(\d+)", result)
    if not match:
        raise SystemExit(f"Could not read AVIF dimensions: {path}")
    return tuple(map(int, match.groups()))


def referenced_images(build_drafts=False):
    with tempfile.TemporaryDirectory(prefix="narravaganza-images-site-") as work:
        site = Path(work) / "site"
        command = ["hugo", "--source", str(ROOT), "--destination", str(site)]
        if build_drafts:
            command.append("--buildDrafts")
        run(*command)
        parser = Images()
        for html in site.rglob("*.html"):
            parser.feed(html.read_text())
        return parser.paths


def expected_variants(relative, width):
    variants = []
    for size in sorted({min(width, candidate) for candidate in WIDTHS}):
        destination = PUBLISHED_IMAGES / relative.parent / f"{relative.stem}-{size}.avif"
        variants.append({
            "src": "/" + str(destination.relative_to(ROOT / "static")),
            "width": size,
        })
    return variants


def check(paths, manifest):
    problems = []
    originals = {entry["src"]: src for src, entry in manifest.items() if "src" in entry}
    checked = 0
    for rendered_src in sorted(paths):
        src = originals.get(rendered_src, rendered_src)
        relative = Path(src.removeprefix("/assets/images/"))
        if relative.suffix.lower() not in RASTER_EXTENSIONS:
            continue
        checked += 1
        original = ORIGINALS / relative
        if not original.is_file():
            problems.append(f"missing original: {original.relative_to(ROOT)}")
            continue
        width, _ = dimensions(original)
        variants = expected_variants(relative, width)
        entry = manifest.get(src)
        if not entry:
            problems.append(f"missing manifest entry: {src}")
            continue
        if entry.get("quality") != QUALITY:
            problems.append(f"wrong quality in manifest: {src}")
        if entry.get("source_sha256") != sha256(original):
            problems.append(f"source changed since optimization: {src}")
        if entry.get("variants") != variants or entry.get("src") != variants[-1]["src"]:
            problems.append(f"wrong variants in manifest: {src}")
        for variant in variants:
            destination = ROOT / "static" / variant["src"].lstrip("/")
            if not destination.is_file():
                problems.append(f"missing AVIF: {destination.relative_to(ROOT)}")
                continue
            encoded_width, _ = avif_dimensions(destination)
            if encoded_width != variant["width"]:
                problems.append(f"wrong AVIF width: {destination.relative_to(ROOT)}")
    if problems:
        raise SystemExit("Image derivatives are stale:\n- " + "\n- ".join(problems) +
                         "\nRun: python3 scripts/optimize-images.py")
    print(f"Image derivatives are current ({checked} raster images checked).")


def optimize(paths, manifest):
    total_before = total_after = 0
    originals = {entry["src"]: src for src, entry in manifest.items() if "src" in entry}
    paths = {originals.get(src, src) for src in paths}
    with tempfile.TemporaryDirectory(prefix="narravaganza-images-") as work:
        resized = Path(work) / "resized.png"
        for src in sorted(paths):
            relative = Path(src.removeprefix("/assets/images/"))
            if relative.suffix.lower() not in RASTER_EXTENSIONS:
                continue
            original = ORIGINALS / relative
            if not original.is_file():
                raise SystemExit(f"Referenced image is missing: {original.relative_to(ROOT)}")
            width, _ = dimensions(original)
            source_sha256 = sha256(original)
            variants = expected_variants(relative, width)
            previous = manifest.get(src, {})
            previous_hash = previous.get("source_sha256")
            for variant in variants:
                size = variant["width"]
                destination = ROOT / "static" / variant["src"].lstrip("/")
                destination.parent.mkdir(parents=True, exist_ok=True)
                if (not destination.exists()
                        or original.stat().st_mtime > destination.stat().st_mtime
                        or (previous_hash is not None and previous_hash != source_sha256)
                        or previous.get("quality") != QUALITY):
                    resize(original, resized, size)
                    # 4:4:4 preserves colored lettering in illustrations/screenshots.
                    run("avifenc", "-q", str(QUALITY), "-s", "6", "-j", "4", "-y", "444",
                        "--ignore-exif", "--ignore-xmp", str(resized), str(destination))
            encoded_width, encoded_height = avif_dimensions(destination)
            entry = manifest.get(src, {})
            entry.update(src=variants[-1]["src"], width=encoded_width,
                         height=encoded_height, variants=variants, quality=QUALITY,
                         source_sha256=source_sha256)
            manifest[src] = entry
            total_before += original.stat().st_size
            total_after += destination.stat().st_size
            print(f"{original.name}: {original.stat().st_size:,} → "
                  f"{destination.stat().st_size:,} bytes", flush=True)
    MANIFEST.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n")
    if total_before:
        print(f"Largest variants: {total_before:,} → {total_after:,} bytes "
              f"({100 * (1 - total_after / total_before):.1f}% smaller)")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true",
                        help="verify committed AVIFs without modifying files")
    parser.add_argument("--include-drafts", action="store_true",
                        help="also optimize images referenced only by draft content")
    args = parser.parse_args()

    for tool in ("hugo", "avifdec"):
        if not shutil.which(tool):
            raise SystemExit(f"Required local tool missing: {tool}")
    if not args.check and not shutil.which("avifenc"):
        raise SystemExit("Required local tool missing: avifenc")
    image_tool()

    manifest = json.loads(MANIFEST.read_text()) if MANIFEST.exists() else {}
    paths = referenced_images(args.include_drafts)
    if args.check:
        check(paths, manifest)
    else:
        optimize(paths, manifest)


if __name__ == "__main__":
    main()
