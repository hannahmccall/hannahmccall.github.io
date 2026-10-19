"""Build checks: uv run --with Markdown==3.7 python -m unittest discover -s tests"""

from html.parser import HTMLParser
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

import compile as compiler


class MarkdownTests(unittest.TestCase):
    def parse(self, text):
        with TemporaryDirectory() as directory:
            path = Path(directory) / "page.md"
            path.write_text(text, encoding="utf-8")
            return compiler.load_document(path)

    def test_markdown_and_toml(self):
        document = self.parse('+++\ntitle = "A title"\n+++\nHello **universe**.\n')
        self.assertEqual(document.metadata["title"], "A title")
        self.assertIn("<strong>universe</strong>", document.html)

    def test_plain_markdown(self):
        document = self.parse("## A heading\n\n[Link](https://example.com)")
        self.assertEqual(document.metadata, {})
        self.assertIn("<h2>A heading</h2>", document.html)

    def test_windows_newlines(self):
        self.assertEqual(self.parse('+++\r\ntitle = "Title"\r\n+++\r\nText').metadata["title"], "Title")

    def test_missing_delimiter(self):
        with self.assertRaisesRegex(ValueError, "missing closing"):
            self.parse('+++\ntitle = "Title"\n')

    def test_invalid_toml(self):
        with self.assertRaisesRegex(ValueError, "page.md"):
            self.parse("+++\ntitle = \n+++\n")

    def test_metadata_links_are_escaped(self):
        html = compiler.render_links([{"label": "A & B", "url": 'https://example.com/?a="&b=2'}])
        self.assertIn("A &amp; B", html)
        self.assertIn("&quot;&amp;b=2", html)

    def test_link_icons(self):
        brand = compiler.render_links([{"label": "Code", "url": "https://github.com/x", "icon": "github"}])
        self.assertIn("icon-github", brand)
        self.assertIn("social-link", brand)
        self.assertNotIn("icon-arrow_up", brand)
        plain = compiler.render_links([{"label": "Paper", "url": "https://example.com"}])
        self.assertIn("icon-arrow_up", plain)
        self.assertNotIn("social-link", plain)


class OutputTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.output = compiler.build()
        cls.html = (cls.output / "index.html").read_text(encoding="utf-8")

    def test_local_files_and_anchors(self):
        compiler.validate_output(self.output)

    def test_all_sections_and_content_are_prerendered(self):
        for anchor in ("about", "research", "cv", "contact"):
            self.assertIn(f'id="{anchor}"', self.html)
            self.assertIn(f'href="#{anchor}"', self.html)
        self.assertIn("Hot gas motions in M87", self.html)
        self.assertIn("Universität Bonn", self.html)
        self.assertEqual(self.html.count("<h1 "), 1)
        self.assertNotIn("${", self.html)
        #self.assertIn("2024 edition", self.html)

    def test_local_runtime_assets_and_image_accessibility(self):
        class Assets(HTMLParser):
            def handle_starttag(self, tag, attrs):
                attrs = dict(attrs)
                if tag in ("img", "script") and "src" in attrs:
                    assert not attrs["src"].startswith(("http", "//")), attrs
                if tag == "img":
                    assert attrs.get("alt"), attrs
                    assert attrs.get("width") and attrs.get("height"), attrs
                if tag == "link" and attrs.get("rel") in ("stylesheet", "preload"):
                    assert not attrs["href"].startswith(("http", "//")), attrs
        Assets().feed(self.html)

    def test_social_links_use_brand_icons(self):
        for icon_name, label in (("orcid", "ORCID"), ("github", "GitHub"), ("linkedin", "LinkedIn")):
            self.assertIn(f'icon-{icon_name}', self.html)
            self.assertIn(f">{label}</span>", self.html)
        self.assertEqual(self.html.count('class="text-link small-link social-link"'), 3)
        # Project links keep the plain arrow rather than a platform mark.
        self.assertIn('class="text-link small-link" href="https://arxiv.org/abs/2512.06596"', self.html)

    def test_cv_and_legacy_redirects(self):
        self.assertTrue((self.output / "files/hannah-mccall-cv.pdf").read_bytes().startswith(b"%PDF"))
        for old_page in ("research", "cv", "contact"):
            html = (self.output / f"{old_page}.html").read_text(encoding="utf-8")
            self.assertIn(f'url=./#{old_page}', html)
        self.assertTrue((self.output / ".nojekyll").is_file())

    def test_deterministic_and_removes_stale_output(self):
        stale = self.output / "stale-file.txt"
        stale.touch()
        compiler.build()
        self.assertFalse(stale.exists())
        self.assertEqual(self.html, (self.output / "index.html").read_text(encoding="utf-8"))

    def test_failed_validation_preserves_previous_build(self):
        with patch.object(compiler, "validate_output", side_effect=ValueError("broken link")):
            with self.assertRaisesRegex(ValueError, "broken link"):
                compiler.build()
        self.assertEqual(self.html, (self.output / "index.html").read_text(encoding="utf-8"))

    def test_validation_rejects_bad_references(self):
        for bad_html in ('<a href="#missing">x</a>', '<img src="missing.png">', '<p id="a"></p><p id="a"></p>'):
            with self.subTest(html=bad_html), TemporaryDirectory() as directory:
                output = Path(directory)
                (output / "index.html").write_text(bad_html, encoding="utf-8")
                with self.assertRaises(ValueError):
                    compiler.validate_output(output)


if __name__ == "__main__":
    unittest.main()
