"""Regression checks for source-only originals and explicit delivery assets."""
import importlib.util
import tempfile
import unittest
from html import escape
from pathlib import Path
from unittest.mock import patch


spec = importlib.util.spec_from_file_location(
    "optimize_images", Path(__file__).with_name("optimize-images.py"))
images = importlib.util.module_from_spec(spec)
spec.loader.exec_module(images)


class ImageDeliveryTests(unittest.TestCase):
    def test_audits_escaped_rss_images_and_all_srcset_candidates(self):
        with tempfile.TemporaryDirectory() as work:
            site = Path(work)
            html = ('<img src="https://narravaganza.lol/assets/images/old.png" '
                    'srcset="https://narravaganza.lol/assets/images/small.avif 640w, '
                    'https://narravaganza.lol/assets/images/large.avif 1280w">')
            (site / "feed.xml").write_text(
                '<rss><channel><item><description>' + escape(html) +
                '</description></item></channel></rss>')
            parser = images.parse_site_images(site, "https://narravaganza.lol/")
            self.assertEqual(parser.paths, {
                "/assets/images/old.png", "/assets/images/small.avif",
                "/assets/images/large.avif"})
            problems = images.published_image_problems(site, parser.paths)
            self.assertEqual(len(problems), 3)
            self.assertTrue(any("old.png" in problem for problem in problems))
            for path in parser.paths:
                target = site / path.lstrip("/")
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(b"fixture")
            self.assertEqual(images.published_image_problems(site, parser.paths), [])

    def test_audits_atom_html_and_xhtml_content(self):
        with tempfile.TemporaryDirectory() as work:
            site = Path(work)
            (site / "atom.xml").write_text('''
                <feed xmlns="http://www.w3.org/2005/Atom">
                  <entry><summary type="html">&lt;img src="/assets/images/a.avif"&gt;</summary></entry>
                  <entry><content type="xhtml"><div xmlns="http://www.w3.org/1999/xhtml">
                    <img src="/assets/images/b.avif" />
                  </div></content></entry>
                </feed>
            ''')
            parser = images.parse_site_images(site, "https://narravaganza.lol/")
            self.assertEqual(parser.paths, {"/assets/images/a.avif", "/assets/images/b.avif"})

    def test_discovers_local_content_and_social_images_without_fetching_external_images(self):
        parser = images.Images("https://narravaganza.lol/")
        parser.feed('''
            <img src="/assets/images/story.png">
            <meta property="og:image" content="https://narravaganza.lol/assets/images/cover.jpg">
            <meta name="twitter:image" content="/assets/images/social/cover.jpg">
            <img src="https://elsewhere.test/assets/images/remote.png">
            <meta property="og:image" content="https://elsewhere.test/assets/images/remote.jpg">
        ''')
        self.assertEqual(parser.paths, {"/assets/images/story.png"})
        self.assertEqual(parser.social_paths, {
            "/assets/images/cover.jpg", "/assets/images/social/cover.jpg"})

    def test_rejects_copied_originals_but_allows_avifs_and_explicit_social_jpegs(self):
        with tempfile.TemporaryDirectory() as work:
            root = Path(work)
            delivery = root / "static/assets/images"
            delivery.mkdir(parents=True)
            for name in ("painting.png", "painting-640.avif", "cover.jpg"):
                (delivery / name).write_bytes(b"fixture")
            manifest = {"/assets/images/source.jpg": {
                "social": {"src": "/assets/images/cover.jpg"}}}
            with patch.multiple(images, ROOT=root, PUBLISHED_IMAGES=delivery):
                problems = images.delivery_problems(manifest)
            self.assertEqual(len(problems), 1)
            self.assertIn("painting.png", problems[0])

    def test_reports_missing_social_delivery_and_changed_source(self):
        with tempfile.TemporaryDirectory() as work:
            root = Path(work)
            originals = root / "assets/images/originals"
            originals.mkdir(parents=True)
            source = originals / "cover.jpg"
            source.write_bytes(b"original")
            manifest = {"/assets/images/cover.jpg": {"social": {
                "src": "/assets/images/social/cover.jpg", "quality": 85,
                "source_sha256": images.sha256(source)}}}
            with patch.multiple(images, ROOT=root, ORIGINALS=originals):
                problems = images.check_social({"/assets/images/social/cover.jpg"}, manifest)
                self.assertIn("missing social derivative", problems[0])
                source.write_bytes(b"changed")
                problems = images.check_social({"/assets/images/social/cover.jpg"}, manifest)
                self.assertIn("stale social derivative", problems[0])


if __name__ == "__main__":
    unittest.main()
