# Hannah McCall · Astrophysics

A small, Markdown-authored website for Hannah E. McCall. Warm off-white and forest-green colors, editorial typography, real research imagery, and a responsive single-page layout.

**No Node.js, frontend framework, database, or application server is needed.** Python compiles the Markdown to ordinary HTML. A little vanilla JavaScript adds theme switching, active navigation, and entrance animations. All content and links work without it.

## Build and preview

Install [uv](https://docs.astral.sh/uv/getting-started/installation/), then:

```sh
uv run compile.py
```

The complete website is written to **`dist/`**. `uv` manages Python and the one build dependency, Python-Markdown, using the script’s inline dependency metadata and `compile.py.lock`.

To build and start a local preview:

```sh
uv run compile.py --serve
# Open http://localhost:8000
```

If that port is occupied:

```sh
uv run compile.py --serve --port 8765
```

Run `uv run compile.py` again after editing, then refresh the browser. There is intentionally no watcher or development toolchain. The preview server can keep running while you rebuild. You can also open `dist/index.html` directly; there are no runtime content requests.

## Edit the content

All page copy is in **`content/`**:

| File | Content |
| --- | --- |
| `site.md` | Site title, description, canonical URL, navigation, footer |
| `home.md` | Name, introduction, portrait, affiliation, research interests |
| `about.md` | Biography |
| `research.md` | Research introduction and publications link |
| `projects/*.md` | Research highlights, ordered by filename |
| `current.md` | Current project |
| `cv.md` | Education and CV download |
| `contact.md` | Email, professional profiles, office address |

Each file can begin with a **TOML metadata block** between `+++` lines, followed by ordinary Markdown:

```markdown
+++
label = "About me"
+++
Hello! I’m a PhD candidate at the **University of Chicago**.

Here is a [link](https://astrophysics.uchicago.edu/).
```

Text, links, and image settings in the metadata are part of the content, not Python code. A `\n` in a heading creates a deliberate line break. Markdown supports paragraphs, lists, emphasis, links, and other standard formatting. Only trusted, locally authored content should be used; raw HTML in Markdown is supported, not sanitized.

### Add a research highlight

Copy an existing file in `content/projects/`, give it a new numeric prefix, and update its metadata and text. Every `*.md` file there is included automatically. Put its image in `static/images/`; supply meaningful alternative text and the image’s actual width and height. The `image_full` field can point to a larger figure. The `[[links]]` blocks provide paper, press, or code links.

### Update the CV

Replace **`static/files/hannah-mccall-cv.pdf`**, then update `cv_note` in `content/cv.md`. The supplied file is the **2024 edition from the original website**, explicitly labeled as such; it is not a newly generated or up-to-date CV. The education summary is separate Markdown, so update it there as needed.

### Change the design

- `static/style.css`: layout, colors, fonts, responsive rules, print styles, transitions
- `static/site.js`: theme preference, active navigation, subtle entrance animations
- `templates/index.html`: page structure
- `templates/project.html`: repeated research highlight
- `templates/theme-init.js`: tiny inline initializer to apply the saved theme before first paint

Fonts are self-hosted; there are no Google Fonts requests, analytics, cookies, or third-party scripts. The theme follows the system until the visitor chooses light or dark, then remembers that choice in `localStorage`. It continues to work if storage is unavailable. Motion respects `prefers-reduced-motion`; keyboard focus and a skip link are provided.

## Publish

Upload the **contents of `dist/`** to any static web host. Paths are relative, so the site also works under a subdirectory. Set the production URL in `content/site.md` before building to keep canonical and social-sharing metadata correct.

### GitHub Pages

A deployment workflow is included in `.github/workflows/deploy.yml`:

1. Put this project in the `hannahmccall.github.io` repository on the `main` branch.
2. In **Settings → Pages → Build and deployment**, choose **GitHub Actions**.
3. Push to `main`. The workflow tests, builds, and publishes `dist/`.

Pull requests build and test without deploying. If the repository uses another default branch, update both `main` references in the workflow. Generated output does not need to be committed.

Old `research.html`, `cv.html`, and `contact.html` links redirect to the corresponding sections. There is no client-side router or special server configuration.

## Tests

Build/content checks, including local files, anchor targets, metadata parsing, deterministic output, and preservation of the last good build after validation errors:

```sh
uv run --with Markdown==3.7 python -m unittest discover -s tests -v
```

Optional Chromium smoke tests (test-only dependencies):

```sh
# One-time browser download; Linux CI may also need --with-deps.
uv run --with playwright==1.63.0 playwright install chromium
uv run tests/browser.py
```

The browser tests cover 15 viewport widths (320–1920px), saved/system/cross-tab themes, native anchors and history, images, the PDF download, legacy redirects, keyboard navigation, reduced motion, print colors, no-JavaScript use, and blocked storage. They serve the site under a subdirectory to check relative URLs too.

## Source assets

The biography, research links, portrait, figures, office address, and CV were adapted from [Hannah’s existing website](https://hannahmccall.github.io/). See **`CREDITS.md`** for image provenance and font licenses. Review the current-project description and contact details before publishing.
