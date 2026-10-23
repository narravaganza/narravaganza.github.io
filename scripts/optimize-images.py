#!/usr/bin/env python3
"""Create or verify responsive quality-80 AVIFs and social-preview JPEGs.

Run after adding an image: python3 scripts/optimize-images.py
Verify committed derivatives: python3 scripts/optimize-images.py --check
Store originals in assets/images/originals; AVIFs go in static/assets/images.
Originals are source-only. Explicit social-preview derivatives are JPEGs.
Write alt text in the content, or add an "alt" entry to data/images.json.
"""
import argparse
import hashlib
import json
import re
import shutil
import subprocess
import tempfile
import xml.etree.ElementTree as ET
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "data/images.json"
ORIGINALS = ROOT / "assets/images/originals"
PUBLISHED_IMAGES = ROOT / "static/assets/images"
QUALITY = 80
SOCIAL_QUALITY = 85
SOCIAL_WIDTH = 1200
WIDTHS = (640, 1280)
RASTER_EXTENSIONS = {".jpeg", ".jpg", ".png", ".tif", ".tiff", ".webp"}


class Images(HTMLParser):
    def __init__(self, base_url=""):
        super().__init__()
        self.paths = set()
        self.social_paths = set()
        self.origin = urlsplit(base_url).netloc

    def local_image(self, url):
        parsed = urlsplit(url)
        if parsed.netloc and parsed.netloc != self.origin:
            return None
        if parsed.path.startswith("/assets/images/"):
            return parsed.path
        return None

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        src = self.local_image(attrs.get("src", ""))
        if tag == "img" and src:
            self.paths.add(src)
        if tag == "img":
            for candidate in attrs.get("srcset", "").split(","):
                if candidate.strip():
                    src = self.local_image(candidate.strip().split()[0])
                    if src:
                        self.paths.add(src)
        if tag == "meta" and attrs.get("property", attrs.get("name")) in {
                "og:image", "twitter:image"}:
            src = self.local_image(attrs.get("content", ""))
            if src:
                self.social_paths.add(src)


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


def encode_social(source, destination, width):
    tool = image_tool()
    if tool == "sips":
        run("sips", "--resampleWidth", str(width), "-s", "format", "jpeg",
            "-s", "formatOptions", str(SOCIAL_QUALITY), str(source),
            "--out", str(destination))
    else:
        run(tool, str(source), "-resize", f"{width}x", "-background", "white",
            "-alpha", "remove", "-alpha", "off", "-quality",
            str(SOCIAL_QUALITY), str(destination))


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


def parse_site_images(site, base_url):
    """RSS/Atom embeds escaped HTML, so parse its decoded descriptions too."""
    parser = Images(base_url)
    for html in site.rglob("*.html"):
        parser.feed(html.read_text())
    for xml in site.rglob("*.xml"):
        for element in ET.parse(xml).iter():
            name = element.tag.rsplit("}", 1)[-1]
            if name in {"description", "summary", "content", "encoded"}:
                parser.feed(element.text or "")
                for child in element:
                    # XHTML namespaces serialize as prefixed tags; normalize
                    # them so HTMLParser recognizes img and its attributes.
                    for node in child.iter():
                        node.tag = node.tag.rsplit("}", 1)[-1]
                    parser.feed(ET.tostring(child, encoding="unicode"))
    return parser


def published_image_problems(site, paths):
    return [f"published image is missing: {path}" for path in sorted(paths)
            if not (site / path.lstrip("/")).is_file()]


def referenced_images(build_drafts=False, verify_delivery=False):
    with tempfile.TemporaryDirectory(prefix="narravaganza-images-site-") as work:
        site = Path(work) / "site"
        command = ["hugo", "--source", str(ROOT), "--destination", str(site)]
        if build_drafts:
            command.append("--buildDrafts")
        run(*command)
        config = json.loads(run("hugo", "config", "--source", str(ROOT),
                                "--format", "json"))
        parser = parse_site_images(site, config["baseurl"])
        problems = []
        for original in ORIGINALS.rglob("*"):
            if original.is_file():
                relative = original.relative_to(ORIGINALS)
                if (site / "assets/images" / relative).exists():
                    problems.append(f"original published by Hugo: {relative}")
        if verify_delivery:
            problems.extend(published_image_problems(
                site, parser.paths | parser.social_paths))
        if problems:
            raise SystemExit("Invalid image delivery:\n- " + "\n- ".join(problems))
        return parser.paths, parser.social_paths


def expected_variants(relative, width):
    variants = []
    for size in sorted({min(width, candidate) for candidate in WIDTHS}):
        destination = PUBLISHED_IMAGES / relative.parent / f"{relative.stem}-{size}.avif"
        variants.append({
            "src": "/" + str(destination.relative_to(ROOT / "static")),
            "width": size,
        })
    return variants


def original_sources(manifest):
    """Map every rendered AVIF variant back to its source image URL."""
    originals = {entry["src"]: src
                 for src, entry in manifest.items() if "src" in entry}
    originals.update({variant["src"]: src
                      for src, entry in manifest.items()
                      for variant in entry.get("variants", [])})
    originals.update({entry["social"]["src"]: src
                      for src, entry in manifest.items() if "social" in entry})
    return originals


def social_path(src):
    relative = Path(src.removeprefix("/assets/images/"))
    return "/assets/images/social/" + str(relative.with_suffix(".jpg"))


def delivery_problems(manifest):
    """Only AVIFs and explicitly generated social JPEGs belong in delivery."""
    allowed = {entry["social"]["src"]
               for entry in manifest.values() if "social" in entry}
    problems = []
    for path in PUBLISHED_IMAGES.rglob("*"):
        if path.is_file() and path.suffix.lower() in RASTER_EXTENSIONS:
            src = "/" + str(path.relative_to(ROOT / "static"))
            if src not in allowed:
                problems.append(f"unexpected raster delivery asset: {path.relative_to(ROOT)}")
    return problems


def check_social(paths, manifest):
    problems = []
    originals = original_sources(manifest)
    for rendered_src in sorted(paths):
        src = originals.get(rendered_src, rendered_src)
        original = ORIGINALS / src.removeprefix("/assets/images/")
        if not original.is_file():
            problems.append(f"missing social original: {src}")
            continue
        social = manifest.get(src, {}).get("social", {})
        if (social.get("src") != social_path(src)
                or social.get("quality") != SOCIAL_QUALITY
                or social.get("source_sha256") != sha256(original)):
            problems.append(f"stale social derivative: {src}")
            continue
        destination = ROOT / "static" / social["src"].lstrip("/")
        if not destination.is_file():
            problems.append(f"missing social derivative: {social['src']}")
            continue
        width, height = dimensions(destination)
        original_width, original_height = dimensions(original)
        expected_width = min(original_width, SOCIAL_WIDTH)
        expected_height = round(original_height * expected_width / original_width)
        if (width != expected_width or abs(height - expected_height) > 1
                or social.get("width") != width or social.get("height") != height):
            problems.append(f"wrong social dimensions: {social['src']}")
    return problems


def check(paths, manifest, social_paths=()):
    problems = []
    originals = original_sources(manifest)
    checked = 0
    for src in sorted({originals.get(path, path) for path in paths}):
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
    problems.extend(check_social(social_paths, manifest))
    problems.extend(delivery_problems(manifest))
    if problems:
        raise SystemExit("Image derivatives are stale:\n- " + "\n- ".join(problems) +
                         "\nRun: python3 scripts/optimize-images.py")
    print(f"Image derivatives are current ({checked} content images and "
          f"{len(social_paths)} social preview(s) checked).")


def optimize(paths, manifest, social_paths=()):
    total_before = total_after = 0
    originals = original_sources(manifest)
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
    for rendered_src in sorted(social_paths):
        src = originals.get(rendered_src, rendered_src)
        original = ORIGINALS / src.removeprefix("/assets/images/")
        if not original.is_file():
            raise SystemExit(f"Social image is missing: {original.relative_to(ROOT)}")
        width, _ = dimensions(original)
        destination = ROOT / "static" / social_path(src).lstrip("/")
        previous = manifest.get(src, {}).get("social", {})
        source_sha256 = sha256(original)
        if (not destination.exists()
                or previous.get("source_sha256") != source_sha256
                or previous.get("width") != min(width, SOCIAL_WIDTH)
                or previous.get("quality") != SOCIAL_QUALITY):
            destination.parent.mkdir(parents=True, exist_ok=True)
            encode_social(original, destination, min(width, SOCIAL_WIDTH))
        width, height = dimensions(destination)
        manifest.setdefault(src, {})["social"] = dict(
            src=social_path(src), width=width, height=height,
            quality=SOCIAL_QUALITY, source_sha256=source_sha256)
        print(f"Social preview: {destination.relative_to(ROOT)}", flush=True)
    MANIFEST.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n")
    if total_before:
        print(f"Largest variants: {total_before:,} → {total_after:,} bytes "
              f"({100 * (1 - total_after / total_before):.1f}% smaller)")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true",
                        help="verify image delivery and committed derivatives without modifying files")
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
    paths, social_paths = referenced_images(args.include_drafts, args.check)
    if args.check:
        check(paths, manifest, social_paths)
    else:
        optimize(paths, manifest, social_paths)


if __name__ == "__main__":
    main()
