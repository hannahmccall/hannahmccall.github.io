from jinja2 import Environment, FileSystemLoader
import markdown2
from collections import namedtuple
from glob import glob
from pathlib import Path


Info = namedtuple(
    "Info", ["name", "profession", "email", "linkedin", "github", "orcid"]
)
Site = namedtuple("Site", ["title", "url", "content"])


def replace_umlauts(html: str) -> str:
    """Replaces German umlauts with their HTML entities"""
    html = html.replace("ä", "&auml;")
    html = html.replace("ö", "&ouml;")
    html = html.replace("ü", "&uuml;")
    html = html.replace("Ä", "&Auml;")
    html = html.replace("Ö", "&Ouml;")
    html = html.replace("Ü", "&Uuml;")
    html = html.replace("ß", "&szlig;")
    return html


if __name__ == "__main__":
    info = Info(
        name="Hannah E. McCall",
        profession="Astrophysics PhD Candidate",
        email="hannahmccall@uchicago.edu",
        linkedin="https://www.linkedin.com/in/hannah-mccall-772194165/",
        github="https://github.com/hannahmccall",
        orcid="https://orcid.org/0000-0003-3537-3491",
    )

    contents = sorted(glob("content/*.md"))
    sites = []
    for i, content in enumerate(contents):
        with open(content, "r") as f:
            content = f.read()
            title = content.splitlines()[0].strip("# ")
            html = replace_umlauts(markdown2.markdown(content, extras=["tables"]))
            if i == 0:
                url = "index.html"
            else:
                url = title.lower().replace(" ", "_") + ".html"
            site = Site(title, url, html)
            sites.append(site)

    build_path = Path("./")

    env = Environment(loader=FileSystemLoader("."))
    template = env.get_template("template.html")

    for site in sites:
        html_site = template.render(content=site.content, info=info, links=sites)
        filename = site.url
        with open(build_path / filename, "w") as f:
            f.write(html_site)
