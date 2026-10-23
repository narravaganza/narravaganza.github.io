"""Check language links and publication listings against Hugo's rendered output."""
import subprocess
import tempfile
import unittest
import xml.etree.ElementTree as ET
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlsplit


ROOT = Path(__file__).resolve().parent.parent
PAIRS = (
    ("/stories/comet-jordi/", "/stories/el-cometa-jordi/", "es"),
    ("/stories/the-flavour-of-facts/", "/stories/el-sabor-de-los-hechos/", "es"),
    ("/stories/the-boiled-tomato-technique/", "/stories/la-tecnica-del-pomodoro-bollito/", "it"),
    ("/essays/the-turia-trooper/", "/essays/el-tropelero-del-turia/", "es"),
)
ITALIAN_ORIGINAL = "/sketches/guerra-fredda-al-pistacchio/"


class Page(HTMLParser):
    def __init__(self, source):
        super().__init__()
        self.elements = []
        self.anchor_depth = 0
        self.nested_anchors = False
        self.feed(source)

    def handle_starttag(self, tag, attributes):
        attrs = dict(attributes)
        self.elements.append((tag, attrs))
        if tag == "a":
            self.nested_anchors |= self.anchor_depth > 0
            self.anchor_depth += 1

    def handle_endtag(self, tag):
        if tag == "a":
            self.anchor_depth -= 1


class TranslationTests(unittest.TestCase):
    def test_published_versions_and_listings(self):
        (ROOT / "tmp").mkdir(exist_ok=True)
        for drafts in (False, True):
            with self.subTest(build_drafts=drafts), tempfile.TemporaryDirectory(
                prefix="translations-", dir=ROOT / "tmp"
            ) as destination:
                command = ["hugo", "--destination", destination]
                if drafts:
                    command.append("--buildDrafts")
                subprocess.run(command, cwd=ROOT, check=True, capture_output=True)
                site = Path(destination)

                def page(url):
                    return Page((site / url.lstrip("/") / "index.html").read_text())

                collection = page("/collection/")
                self.assertFalse(collection.nested_anchors)
                listed = [attrs["href"] for tag, attrs in collection.elements
                          if tag == "a" and "list-item" in attrs.get("class", "").split()]
                feed = ET.parse(site / "feed.xml")
                feed_paths = [urlsplit(item.findtext("link")).path
                              for item in feed.findall("./channel/item")]
                self.assertCountEqual(listed, feed_paths)
                self.assertEqual(len(listed), len(set(listed)))
                self.assertIn(ITALIAN_ORIGINAL, listed)
                self.assertFalse(any(url.startswith("/drafts/") for url in listed))
                self.assertIn(("html", {"lang": "it"}), page(ITALIAN_ORIGINAL).elements)

                for original, translated, language in PAIRS:
                    self.assertIn(original, listed)
                    self.assertNotIn(translated, listed)
                    self.assertFalse(any(tag == "a" and attrs.get("href") == translated
                                         for tag, attrs in collection.elements))
                    for url, code, other, other_code in (
                        (original, "en", translated, language),
                        (translated, language, original, "en"),
                    ):
                        rendered = page(url)
                        self.assertIn(("html", {"lang": code}), rendered.elements)
                        self.assertTrue(any(tag == "a" and attrs.get("href") == other
                                            and attrs.get("hreflang") == other_code
                                            for tag, attrs in rendered.elements))
                        alternates = {attrs["hreflang"]: urlsplit(attrs["href"]).path
                                      for tag, attrs in rendered.elements
                                      if tag == "link" and attrs.get("rel") == "alternate"}
                        self.assertEqual(alternates, {"en": original, language: translated})
                        canonical = [urlsplit(attrs["href"]).path for tag, attrs in rendered.elements
                                     if tag == "link" and attrs.get("rel") == "canonical"]
                        self.assertEqual(canonical, [url])


if __name__ == "__main__":
    unittest.main()
