# /// script
# requires-python = ">=3.11"
# dependencies = ["Markdown==3.7"]
# ///
"""Compile local Markdown into a self-contained static site. Run with uv."""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from datetime import date
from functools import partial
from hashlib import sha256
from html import escape
from html.parser import HTMLParser
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import shutil
from string import Template
import sys
from tempfile import TemporaryDirectory
import tomllib
from urllib.parse import unquote, urljoin, urlsplit

import markdown

ROOT = Path(__file__).resolve().parent


@dataclass
class Document:
    metadata: dict
    html: str


def load_document(path: Path) -> Document:
    """Read Markdown with a small, optional +++ TOML metadata block."""
    text = path.read_text(encoding="utf-8")
    lines = text.splitlines()
    metadata = {}
    if lines and lines[0] == "+++":
        try:
            end = lines.index("+++", 1)
        except ValueError as error:
            raise ValueError(f"{path}: missing closing +++ metadata delimiter") from error
        try:
            metadata = tomllib.loads("\n".join(lines[1:end]))
        except tomllib.TOMLDecodeError as error:
            raise ValueError(f"{path}: {error}") from error
        text = "\n".join(lines[end + 1:])
    # Content is trusted, locally authored Markdown, not visitor input.
    return Document(metadata, markdown.markdown(text, extensions=["extra", "sane_lists"]))

STROKE_ICONS = {
    "arrow_up": '<path d="M5 19 19 5M5 5h14v14"/>',
    "arrow_right": '<path d="M4 12h16m-6-6 6 6-6 6"/>',
    "download": '<path d="M12 3v12m-5-5 5 5 5-5M4 16v5h16v-5"/>',
}
# Platform marks, drawn in currentColor so they follow the accent in both themes.
BRAND_ICONS = {
    "github": '<path d="M12 .297c-6.63 0-12 5.373-12 12 0 5.303 3.438 9.8 8.205 11.385.6.113.82-.258.82-.577 0-.285-.01-1.04-.015-2.04-3.338.724-4.042-1.61-4.042-1.61C4.422 18.07 3.633 17.7 3.633 17.7c-1.087-.744.084-.729.084-.729 1.205.084 1.838 1.236 1.838 1.236 1.07 1.835 2.809 1.305 3.495.998.108-.776.417-1.305.76-1.605-2.665-.3-5.466-1.332-5.466-5.93 0-1.31.465-2.38 1.235-3.22-.135-.303-.54-1.523.105-3.176 0 0 1.005-.322 3.3 1.23.96-.267 1.98-.399 3-.405 1.02.006 2.04.138 3 .405 2.28-1.552 3.285-1.23 3.285-1.23.645 1.653.24 2.873.12 3.176.765.84 1.23 1.91 1.23 3.22 0 4.61-2.805 5.625-5.475 5.92.42.36.81 1.096.81 2.22 0 1.606-.015 2.896-.015 3.286 0 .315.21.69.825.57C20.565 22.092 24 17.592 24 12.297c0-6.627-5.373-12-12-12"/>',
    "linkedin": '<path d="M20.447 20.452h-3.554v-5.569c0-1.328-.027-3.037-1.852-3.037-1.853 0-2.136 1.445-2.136 2.939v5.667H9.351V9h3.414v1.561h.046c.477-.9 1.637-1.85 3.37-1.85 3.601 0 4.267 2.37 4.267 5.455v6.286zM5.337 7.433c-1.144 0-2.063-.926-2.063-2.065 0-1.138.92-2.063 2.063-2.063 1.14 0 2.064.925 2.064 2.063 0 1.139-.925 2.065-2.064 2.065zm1.782 13.019H3.555V9h3.564v11.452zM22.225 0H1.771C.792 0 0 .774 0 1.729v20.542C0 23.227.792 24 1.771 24h20.451C23.2 24 24 23.227 24 22.271V1.729C24 .774 23.2 0 22.222 0h.003z"/>',
    "orcid": '<path d="M12 0C5.372 0 0 5.372 0 12s5.372 12 12 12 12-5.372 12-12S18.628 0 12 0zM7.369 4.378c.525 0 .947.431.947.947s-.422.947-.947.947a.95.95 0 0 1-.947-.947c0-.525.422-.947.947-.947zm-.722 3.038h1.444v10.041H6.647V7.416zm3.562 0h3.9c3.712 0 5.344 2.653 5.344 5.025 0 2.578-2.016 5.025-5.325 5.025h-3.919V7.416zm1.444 1.303v7.444h2.297c3.272 0 4.022-2.484 4.022-3.722 0-2.016-1.284-3.722-4.097-3.722h-2.222z"/>',
}


def icon(name: str) -> str:
    if name in BRAND_ICONS:
        return (
            f'<svg class="icon icon-{name}" viewBox="0 0 24 24" fill="currentColor" '
            f'aria-hidden="true">{BRAND_ICONS[name]}</svg>'
        )
    return (
        f'<svg class="icon icon-{name}" viewBox="0 0 24 24" fill="none" '
        f'stroke="currentColor" stroke-width="1.4" stroke-linecap="round" '
        f'stroke-linejoin="round" aria-hidden="true">{STROKE_ICONS[name]}</svg>'
    )


def render_links(links: list[dict]) -> str:
    rendered = []
    for link in links:
        href = escape(link["url"], quote=True)
        label = escape(link["label"])
        if link.get("icon"):
            rendered.append(
                f'<a class="text-link small-link social-link" href="{href}">'
                f'{icon(link["icon"])}<span>{label}</span></a>'
            )
        else:
            rendered.append(
                f'<a class="text-link small-link" href="{href}">{label} {icon("arrow_up")}</a>'
            )
    return "\n".join(rendered)


def render_project(path: Path, index: int) -> str:
    document = load_document(path)
    fields = {key: escape(str(value), quote=True) for key, value in document.metadata.items()}
    fields.update(body=document.html, links=render_links(document.metadata["links"]), number=f"{index:02}")
    return Template((ROOT / "templates/project.html").read_text(encoding="utf-8")).substitute(fields)


class PageReferences(HTMLParser):
    """Collect local links to catch typos before publishing."""

    def __init__(self):
        super().__init__()
        self.ids: set[str] = set()
        self.references: list[str] = []

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if "id" in attrs:
            if attrs["id"] in self.ids:
                raise ValueError(f'Duplicate HTML id: {attrs["id"]}')
            self.ids.add(attrs["id"])
        for name in ("src", "href"):
            if attrs.get(name):
                self.references.append(attrs[name])
        if attrs.get("srcset"):
            self.references.extend(item.strip().split()[0] for item in attrs["srcset"].split(","))


def validate_output(output: Path) -> None:
    page = PageReferences()
    page.feed((output / "index.html").read_text(encoding="utf-8"))
    for reference in page.references:
        url = urlsplit(reference)
        if url.scheme or url.netloc:
            continue
        if url.path:
            target = (output / unquote(url.path)).resolve()
            if not target.is_relative_to(output.resolve()) or not target.is_file():
                raise ValueError(f"Missing or invalid local file: {reference}")
        elif url.fragment and unquote(url.fragment) not in page.ids:
            raise ValueError(f"Missing anchor: {reference}")


def build() -> Path:
    content = ROOT / "content"
    documents = {
        name: load_document(content / f"{name}.md")
        for name in ("site", "home", "about", "research", "current", "cv", "contact")
    }
    context = {}
    for name, document in documents.items():
        context[f"{name}_body"] = document.html
        for key, value in document.metadata.items():
            if isinstance(value, str):
                context[f"{name}_{key}"] = escape(value, quote=True).replace("\n", "<br>")

    site = documents["site"].metadata
    home = documents["home"].metadata
    context.update(
        year=str(date.today().year),
        navigation="\n".join(
            f'<a href="#{escape(item["id"], quote=True)}">{escape(item["label"])}</a>'
            for item in site["navigation"]
        ),
        interests="".join(f"<li>{escape(item)}</li>" for item in home["interests"]),
        projects="\n".join(
            render_project(path, index)
            for index, path in enumerate(sorted((content / "projects").glob("*.md")), 1)
        ),
        social_links=render_links(documents["contact"].metadata["links"]),
        social_image=escape(urljoin(site["url"], home["portrait"]), quote=True),
        theme_init=(ROOT / "templates/theme-init.js").read_text(encoding="utf-8"),
        css_version=sha256((ROOT / "static/style.css").read_bytes()).hexdigest()[:10],
        js_version=sha256((ROOT / "static/site.js").read_bytes()).hexdigest()[:10],
    )
    for name in ("arrow_up", "arrow_right", "download"):
        context[f"{name}_icon"] = icon(name)

    template = Template((ROOT / "templates/index.html").read_text(encoding="utf-8"))
    html = template.substitute(context)
    output = ROOT / "dist"
    if output.is_symlink():
        raise ValueError("Refusing to replace a symlink at dist/")
    # Render and validate in staging first, leaving the previous build intact on errors.
    with TemporaryDirectory(prefix=".site-build-", dir=ROOT) as temporary:
        staging = Path(temporary) / "dist"
        shutil.copytree(ROOT / "static", staging)
        (staging / "index.html").write_text(html, encoding="utf-8")
        (staging / ".nojekyll").touch()
        for old_page, anchor in {"research": "research", "cv": "cv", "contact": "contact"}.items():
            (staging / f"{old_page}.html").write_text(
                '<!doctype html><html lang="en"><meta charset="utf-8">'
                '<meta name="viewport" content="width=device-width, initial-scale=1">'
                f'<meta http-equiv="refresh" content="0;url=./#{anchor}">'
                f'<title>{escape(site["title"])}</title>'
                f'<link rel="canonical" href="{escape(site["url"], quote=True)}#{anchor}">'
                f'<p>This page has moved. <a href="./#{anchor}">Continue to {old_page}</a>.</p></html>',
                encoding="utf-8",
            )
        validate_output(staging)
        if output.exists():
            shutil.rmtree(output)
        shutil.move(str(staging), output)
    return output


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--serve", action="store_true", help="Build, then preview at http://localhost:8000")
    parser.add_argument("--port", type=int, default=8000, help="Preview port (default: 8000)")
    args = parser.parse_args()
    try:
        output = build()
    except (OSError, ValueError, KeyError) as error:
        sys.exit(f"Build failed: {error}")
    print(f"Built {output / 'index.html'}")
    if args.serve:
        handler = partial(SimpleHTTPRequestHandler, directory=str(output))
        with ThreadingHTTPServer(("127.0.0.1", args.port), handler) as server:
            print(f"Preview: http://localhost:{args.port} (Ctrl+C to stop)", flush=True)
            try:
                server.serve_forever()
            except KeyboardInterrupt:
                pass


if __name__ == "__main__":
    main()
