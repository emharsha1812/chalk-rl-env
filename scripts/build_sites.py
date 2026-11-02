"""Build the two local sites and set their cross-site links."""

import argparse
import html
import json
import os
import subprocess
from pathlib import Path
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[1]


def destination(name: str, default: str) -> str:
    value = os.environ.get(name, default)
    parsed = urlsplit(value)
    if (
        parsed.query
        or parsed.fragment
        or not value.endswith("/")
        or not (
            (value.startswith("/") and not value.startswith("//"))
            or (parsed.scheme in {"http", "https"} and parsed.netloc)
        )
    ):
        raise ValueError(f"{name} must be an absolute path or HTTP URL ending in /")
    return html.escape(value, quote=True)


def fix_not_found(content: str, output: Path, site_url: str, *, docs: bool) -> str:
    """Make Zensical's root-relative 404 assets work below a site prefix."""
    for directory in output.iterdir():
        if not directory.is_dir():
            continue
        for attribute in ("href", "src"):
            content = content.replace(
                f'{attribute}="/{directory.name}/',
                f'{attribute}="{site_url}{directory.name}/',
            )
    content = content.replace(
        'href="/" class="md-nav__link"', f'href="{site_url}" class="md-nav__link"'
    )
    if not docs:
        content = content.replace(
            'href="/" title="Chalk"', f'href="{site_url}" title="Chalk"'
        )
    json_url = json.dumps(html.unescape(site_url), ensure_ascii=True)[1:-1]
    content = content.replace('"base":"/"', f'"base":"{json_url}"')
    content = content.replace('"search":"/assets/', f'"search":"{json_url}assets/')
    return content


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--site", choices=("both", "website", "docs"), default="both")
    args = parser.parse_args()
    links = {
        "/__chalk_docs__/": destination("CHALK_DOCS_URL", "/docs/"),
        "/__chalk_home__/": destination("CHALK_WEBSITE_URL", "/"),
    }
    for name, config, output in (
        ("docs", "zensical.toml", ROOT / "site"),
        ("website", "website/zensical.toml", ROOT / "website/site"),
    ):
        if args.site not in ("both", name):
            continue
        subprocess.run(
            ["zensical", "build", "--clean", "--strict", "--config-file", config],
            cwd=ROOT,
            check=True,
        )
        for page in output.rglob("*.html"):
            content = page.read_text(encoding="utf-8")
            for marker, url in links.items():
                content = content.replace(marker, url)
            if page == output / "404.html":
                site_url = (
                    links["/__chalk_docs__/"]
                    if name == "docs"
                    else links["/__chalk_home__/"]
                )
                content = fix_not_found(content, output, site_url, docs=name == "docs")
            page.write_text(content, encoding="utf-8")
    print(f"Built {args.site}. Run scripts/preview_sites.py to view it.")


if __name__ == "__main__":
    main()
