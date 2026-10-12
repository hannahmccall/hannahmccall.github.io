# /// script
# requires-python = ">=3.11"
# dependencies = ["playwright==1.63.0"]
# ///
"""Optional browser smoke tests. See README for the one-time browser install."""

from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import re
import subprocess
from threading import Thread

from playwright.sync_api import expect, sync_playwright

ROOT = Path(__file__).resolve().parents[1]


class QuietHandler(SimpleHTTPRequestHandler):
    def log_message(self, *_args):
        pass


def check_browser(base: str) -> None:
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        context = browser.new_context(viewport={"width": 1440, "height": 1000}, color_scheme="light")
        page = context.new_page()
        errors = []
        bad_responses = []
        page.on("pageerror", lambda error: errors.append(str(error)))
        page.on("response", lambda response: bad_responses.append(response.url) if response.status >= 400 else None)
        page.goto(base, wait_until="networkidle")
        page.evaluate("document.fonts.ready")
        expect(page).to_have_title("Hannah E. McCall — Astrophysics")

        # Normal and narrow layouts, including the tablet/mobile breakpoint.
        for width in (320, 360, 375, 390, 414, 540, 700, 701, 768, 800, 900, 1024, 1280, 1440, 1920):
            page.set_viewport_size({"width": width, "height": 900})
            page.wait_for_timeout(100)
            assert page.evaluate("document.documentElement.scrollWidth <= innerWidth"), f"Overflow at {width}px"
        page.set_viewport_size({"width": 1440, "height": 1000})

        # System default, saved choice, reload, cross-tab changes, and reset to OS.
        page.get_by_role("button", name="Switch to dark theme").click()
        expect(page.locator("html")).to_have_attribute("data-theme", "dark")
        page.reload()
        expect(page.get_by_role("button", name="Switch to light theme")).to_be_visible()
        other_tab = context.new_page()
        other_tab.goto(base)
        other_tab.get_by_role("button", name="Switch to light theme").click()
        expect(page.get_by_role("button", name="Switch to dark theme")).to_be_visible()
        other_tab.evaluate("localStorage.removeItem('hannah-theme')")
        page.emulate_media(color_scheme="dark")
        expect(page.get_by_role("button", name="Switch to light theme")).to_be_visible()
        other_tab.close()

        # Native links, active state, history, and deep linking.
        navigation = page.get_by_role("navigation", name="Main navigation")
        navigation.get_by_role("link", name="Research", exact=True).click()
        expect(page).to_have_url(re.compile(r"#research$"))
        expect(navigation.get_by_role("link", name="Research", exact=True)).to_have_attribute("aria-current", "location")
        navigation.get_by_role("link", name="Contact", exact=True).click()
        expect(navigation.get_by_role("link", name="Contact", exact=True)).to_have_attribute("aria-current", "location")
        page.go_back()
        expect(page).to_have_url(re.compile(r"#research$"))
        page.goto(base + "#cv")
        expect(navigation.get_by_role("link", name="CV", exact=True)).to_have_attribute("aria-current", "location")

        # Real local images and the PDF download, rather than placeholder actions.
        for image in page.locator("main img").all():
            image.scroll_into_view_if_needed()
            expect(image).to_be_visible()
            expect(image).to_have_js_property("complete", True)
            assert image.evaluate("image => image.naturalWidth > 0")

        # Research figures expand in a modal lightbox; Esc closes and restores focus.
        first_figure = page.locator(".research-image").first
        first_figure.scroll_into_view_if_needed()
        first_figure.click()
        lightbox = page.locator("dialog.lightbox")
        expect(lightbox).to_be_visible()
        assert lightbox.locator("img").get_attribute("src")
        expect(lightbox.locator(".lightbox-caption")).to_be_visible()
        assert page.evaluate("document.body.classList.contains('lightbox-open')")
        page.keyboard.press("Escape")
        expect(lightbox).to_be_hidden()
        expect(first_figure).to_be_focused()
        page.wait_for_function("() => !document.body.classList.contains('lightbox-open')")
        page.locator(".research-image").nth(1).click()
        expect(lightbox).to_be_visible()
        lightbox.locator(".lightbox-close").click()
        expect(lightbox).to_be_hidden()

        # Platform links carry their brand marks and stay visible in both themes.
        social_links = page.locator(".social-links .social-link")
        assert social_links.count() == 3
        for link in social_links.all():
            expect(link.locator("svg")).to_be_visible()

        with page.expect_download() as download_event:
            page.get_by_role("link", name="Download CV").click()
        assert download_event.value.suggested_filename == "hannah-mccall-cv.pdf"
        for old_page in ("research", "cv", "contact"):
            page.goto(base + old_page + ".html")
            expect(page).to_have_url(base + "#" + old_page)

        # Keyboard skip link and reduced-motion behavior.
        page.goto(base)
        page.keyboard.press("Tab")
        expect(page.get_by_role("link", name="Skip to content")).to_be_focused()
        page.keyboard.press("Enter")
        expect(page).to_have_url(base + "#main")
        page.emulate_media(reduced_motion="reduce")
        assert page.locator("html").evaluate("el => getComputedStyle(el).scrollBehavior") == "auto"
        assert page.locator(".hero-copy").evaluate("el => getComputedStyle(el).animationName") == "none"
        page.emulate_media(media="print")
        assert page.locator("body").evaluate("el => getComputedStyle(el).backgroundColor") == "rgb(255, 255, 255)"

        # Content and native navigation remain usable without JavaScript.
        no_js = browser.new_context(java_script_enabled=False, color_scheme="dark", viewport={"width": 390, "height": 844})
        fallback = no_js.new_page()
        fallback.goto(base)
        expect(fallback.locator(".theme-toggle")).to_be_hidden()
        expect(fallback.get_by_role("heading", name="In the heart of M87")).to_be_visible()
        fallback.get_by_role("navigation").get_by_role("link", name="Contact").click()
        expect(fallback).to_have_url(base + "#contact")
        assert fallback.locator("body").evaluate("el => getComputedStyle(el).backgroundColor") == "rgb(21, 30, 28)"
        no_js.close()

        # Disabled localStorage must not disable the theme button.
        restricted = browser.new_context(color_scheme="light")
        restricted.add_init_script("""
          for (const method of ['getItem', 'setItem']) {
            Object.defineProperty(Storage.prototype, method, { value() { throw new Error('Blocked'); } });
          }
        """)
        private_page = restricted.new_page()
        private_page.on("pageerror", lambda error: errors.append(str(error)))
        private_page.goto(base)
        private_page.get_by_role("button", name="Switch to dark theme").click()
        expect(private_page.locator("html")).to_have_attribute("data-theme", "dark")
        restricted.close()
        assert not errors, errors
        assert not bad_responses, bad_responses
        browser.close()
        print("Browser checks passed: 15 widths, themes, navigation, assets, keyboard, reduced motion, print, no JS, and blocked storage.")


if __name__ == "__main__":
    subprocess.run(["uv", "run", "--frozen", "compile.py"], cwd=ROOT, check=True)
    # Serve under a subdirectory to also verify GitHub project-page compatibility.
    server = ThreadingHTTPServer(("127.0.0.1", 0), partial(QuietHandler, directory=str(ROOT)))
    Thread(target=server.serve_forever, daemon=True).start()
    try:
        check_browser(f"http://127.0.0.1:{server.server_port}/dist/")
    finally:
        server.shutdown()
        server.server_close()
