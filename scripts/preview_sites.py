"""Preview the separately built sites on one local origin."""

import argparse
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote, urlsplit

ROOT = Path(__file__).resolve().parents[1]


class SiteHandler(SimpleHTTPRequestHandler):
    def translate_path(self, path: str) -> str:
        request = unquote(urlsplit(path).path)
        docs = request == "/docs" or request.startswith("/docs/")
        base = (ROOT / ("site" if docs else "website/site")).resolve()
        relative = request.removeprefix("/docs") if docs else request
        parts = [part for part in relative.split("/") if part not in ("", ".", "..")]
        candidate = base.joinpath(*parts).resolve()
        return str(
            candidate if candidate.is_relative_to(base) else base / "__invalid__"
        )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--site", choices=("both", "website", "docs"), default="both")
    args = parser.parse_args()
    if (
        args.site in ("both", "website")
        and not (ROOT / "website/site/index.html").is_file()
    ):
        parser.error(
            "Build the website first: python scripts/build_sites.py --site website"
        )
    if args.site in ("both", "docs") and not (ROOT / "site/index.html").is_file():
        parser.error(
            "Build the documentation first: python scripts/build_sites.py --site docs"
        )
    server = ThreadingHTTPServer(("127.0.0.1", args.port), partial(SiteHandler))
    if args.site in ("both", "website"):
        print(f"Website: http://127.0.0.1:{args.port}/", flush=True)
    if args.site in ("both", "docs"):
        print(f"Documentation: http://127.0.0.1:{args.port}/docs/", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
