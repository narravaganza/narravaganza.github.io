#!/usr/bin/env python3
"""Create responsive quality-75 AVIFs using local sips and avifenc.

Run after adding an image: python3 scripts/optimize-images.py
Store originals in assets/images/originals; AVIFs go in static/assets/images.
Hugo mounts originals at their existing URLs for social previews and old links.
Write alt text in the content, or add an "alt" entry to data/images.json.
"""
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


def dimensions(path):
    result = run("sips", "-g", "pixelWidth", "-g", "pixelHeight", str(path))
    return tuple(int(re.search(rf"{name}: (\d+)", result)[1])
                 for name in ("pixelWidth", "pixelHeight"))


def main():
    for tool in ("hugo", "sips", "avifenc", "avifdec"):
        if not shutil.which(tool):
            raise SystemExit(f"Required local tool missing: {tool}")
    manifest = json.loads(MANIFEST.read_text()) if MANIFEST.exists() else {}
    total_before = total_after = 0
    with tempfile.TemporaryDirectory(prefix="narravaganza-images-") as work:
        work = Path(work)
        run("hugo", "--source", str(ROOT), "--destination", str(work / "site"))
        parser = Images()
        for html in (work / "site").rglob("*.html"):
            parser.feed(html.read_text())
        # A subsequent build references AVIFs; recover their original paths.
        originals = {entry["src"]: src for src, entry in manifest.items()}
        paths = {originals.get(src, src) for src in parser.paths}
        for src in sorted(paths):
            relative = Path(src.removeprefix("/assets/images/"))
            original = ORIGINALS / relative
            width, _ = dimensions(original)
            variants = []
            for size in sorted({min(width, 640), min(width, 1280)}):
                destination = PUBLISHED_IMAGES / relative.parent / f"{original.stem}-{size}.avif"
                destination.parent.mkdir(parents=True, exist_ok=True)
                if (not destination.exists()
                        or original.stat().st_mtime > destination.stat().st_mtime
                        or manifest.get(src, {}).get("quality") != QUALITY):
                    resized = work / "resized.png"
                    run("sips", "--resampleWidth", str(size), "-s", "format", "png",
                        str(original), "--out", str(resized))
                    # 4:4:4 preserves colored lettering in illustrations/screenshots.
                    run("avifenc", "-q", str(QUALITY), "-s", "6", "-j", "4", "-y", "444",
                        "--ignore-exif", "--ignore-xmp", str(resized), str(destination))
                variants.append({"src": "/" + str(destination.relative_to(ROOT / "static")),
                                 "width": size})
            result = run("avifdec", "--info", str(destination))
            encoded_width, encoded_height = map(int, re.search(r"Resolution\s+: (\d+)x(\d+)", result).groups())
            entry = manifest.get(src, {})
            entry.update(src=variants[-1]["src"], width=encoded_width,
                         height=encoded_height, variants=variants, quality=QUALITY)
            manifest[src] = entry
            total_before += original.stat().st_size
            total_after += (ROOT / "static" / entry["src"].lstrip("/")).stat().st_size
            print(f"{original.name}: {original.stat().st_size:,} → "
                  f"{(ROOT / 'static' / entry['src'].lstrip('/')).stat().st_size:,} bytes", flush=True)
    MANIFEST.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n")
    print(f"Largest variants: {total_before:,} → {total_after:,} bytes "
          f"({100 * (1 - total_after / total_before):.1f}% smaller)")


if __name__ == "__main__":
    main()
