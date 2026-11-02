import importlib.util
from pathlib import Path

import pytest

spec = importlib.util.spec_from_file_location(
    "chalk_site_builder",
    Path(__file__).resolve().parent.parent / "scripts/build_sites.py",
)
assert spec and spec.loader
site_builder = importlib.util.module_from_spec(spec)
spec.loader.exec_module(site_builder)


def test_docs_not_found_page_uses_docs_prefix(tmp_path: Path) -> None:
    (tmp_path / "assets").mkdir()
    (tmp_path / "getting-started").mkdir()
    page = (
        '<a href="/" title="Chalk Documentation">website</a>'
        + '<a href="/" class="md-nav__link">docs</a>'
        + '<a href="/getting-started/">start</a>'
        + '<script src="/assets/app.js"></script>'
        + '{"base":"/","search":"/assets/search.js"}'
    )
    result = site_builder.fix_not_found(page, tmp_path, "/docs/", docs=True)
    assert 'href="/" title="Chalk Documentation"' in result
    assert 'href="/docs/" class="md-nav__link"' in result
    assert 'href="/docs/getting-started/"' in result
    assert 'src="/docs/assets/app.js"' in result
    assert '"base":"/docs/"' in result
    assert '"search":"/docs/assets/search.js"' in result


def test_destination_requires_a_complete_base_path(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("CHALK_DOCS_URL", "https://docs.example.invalid/?x=/")
    with pytest.raises(ValueError):
        site_builder.destination("CHALK_DOCS_URL", "/docs/")
