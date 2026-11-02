# Developing Chalk

From the local project checkout:

```sh
uv sync --extra dev --group docs
just fix
just lint
just test
```

Some tests require Linux, root privileges, an isolated runtime, model credentials, or a service. Read the test and runtime requirements before running them. Generated environments contain their own `.chalk/` copy. After changing the local checkout, reinstall the local tool and run `chalk update path/to/my_env` outside the environment's virtual environment. See [Updating environments](../environments/updating.md).

The package includes copies of the root `pyproject.toml`, `README.md`, and `LICENSE` under `src/chalk/` so an installed Chalk can create its local source copy. Keep each packaged copy identical to the root file when changing it; the package tests check this.

The full GitHub test workflow runs when started manually. The website build is also checked when its files change.

## Website and documentation

Both sites use Zensical, with one documentation tree in `docs/` and a separate public-site source in `website/content/`. Build both and preview them together:

```sh
uv run --group docs python scripts/build_sites.py
uv run --group docs python scripts/preview_sites.py
```

The website is at `http://127.0.0.1:8000/` and the documentation at `http://127.0.0.1:8000/docs/`. Their outputs are `website/site/` and `site/`. The preview maps these separate directories to one local origin, matching a shared-domain deployment.

To build and preview either site on its own, add `--site website` or `--site docs` to both commands. The documentation preview still uses the `/docs/` path. The combined preview is the easiest way to check links between the two sites.

For separate domains or different paths, set `CHALK_DOCS_URL` and `CHALK_WEBSITE_URL` before building; use full URLs or absolute paths ending in `/`.

### Cloudflare Pages

The website and documentation can share one Cloudflare Pages project. Use this build command:

```sh
python -m pip install uv==0.12.1 && python -m uv run --frozen --only-group docs python scripts/build_cloudflare.py
```

Set the build output directory to `website/site` and Python to version 3.12. The script builds both sites, puts the documentation under `/docs/`, and sets links for that layout. The two source trees remain separate. Connecting a repository and choosing when to publish are done in the Cloudflare account; this repository does not publish a package.
