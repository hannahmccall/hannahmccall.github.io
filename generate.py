from jinja2 import Environment, FileSystemLoader
import markdown2
from collections import namedtuple
from glob import glob
from pathlib import Path


Info = namedtuple("Info", ["name", "profession", "email"])
Site = namedtuple("Site", ["title", "url", "content"])

if __name__ == "__main__":
    info = Info(
        "Hannah E. McCall", "Astrophysics PhD Candidate", "hannahemccall@email.com"
    )

    contents = sorted(glob("content/*.md"))
    sites = []
    for i, content in enumerate(contents):
        with open(content, "r") as f:
            content = f.read()
            title = content.splitlines()[0].strip("# ")
            html = markdown2.markdown(content, extras=["tables"])
            if i == 0:
                url = "index.html"
            else:
                url = title.lower().replace(" ", "_") + ".html"
            site = Site(title, url, html)
            sites.append(site)

    build_path = Path("..")

    env = Environment(loader=FileSystemLoader("."))
    template = env.get_template("template.html")

    for site in sites:
        html_site = template.render(content=site.content, info=info, links=sites)
        filename = site.url
        with open(build_path / filename, "w") as f:
            f.write(html_site)
