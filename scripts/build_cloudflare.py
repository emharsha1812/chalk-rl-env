"""Build the website and documentation for one Cloudflare Pages project."""

import os
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    env = {"CHALK_DOCS_URL": "/docs/", "CHALK_WEBSITE_URL": "/"} | os.environ
    subprocess.run(
        [sys.executable, str(ROOT / "scripts/build_sites.py")],
        cwd=ROOT,
        env=env,
        check=True,
    )
    output = ROOT / "website/site"
    shutil.copytree(ROOT / "site", output / "docs")
    print(f"Cloudflare Pages output: {output}")


if __name__ == "__main__":
    main()
