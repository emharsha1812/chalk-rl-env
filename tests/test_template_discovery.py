# pyright: reportPrivateUsage=false
"""Templates provided by other packages through the `chalk.templates` entry point."""

import json
import subprocess
import sys
from pathlib import Path
from unittest.mock import patch

import pytest
from loguru import logger

from chalk.create_env import EnvManifest, create_env
from chalk.templates import (
    TEMPLATES_DIR,
    InstalledTemplate,
    discover_templates,
    load_templates,
)


def _install_template_package(
    site: Path,
    dist: str,
    version: str,
    templates: dict[str, dict[str, str]],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Write an importable package plus its dist-info into `site` and put it on `sys.path`."""
    module = dist.replace("-", "_")
    pkg = site / module
    pkg.mkdir(parents=True)
    (pkg / "__init__.py").write_text(
        "from pathlib import Path\nTEMPLATES_DIR = Path(__file__).parent / 'templates'\n"
    )
    for template_id, files in templates.items():
        for name, content in files.items():
            path = pkg / "templates" / template_id / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content)
    info = site / f"{module}-{version}.dist-info"
    info.mkdir()
    (info / "METADATA").write_text(
        f"Metadata-Version: 2.1\nName: {dist}\nVersion: {version}\n"
    )
    (info / "entry_points.txt").write_text(
        f"[chalk.templates]\n{module} = {module}:TEMPLATES_DIR\n"
    )
    monkeypatch.syspath_prepend(str(site))
    monkeypatch.setitem(sys.modules, module, None)
    del sys.modules[module]


@pytest.fixture
def extra_site(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    site = tmp_path / "site"
    _install_template_package(
        site,
        "extra-templates-pkg",
        "1.2.3",
        {
            "extra-overlay": {
                "template.toml": 'description = "Overlay"\nrequires = ["default"]\n',
                "extra.txt": "from extra {{ env_name }}\n",
                "pyproject.toml.jinja": (
                    '{% extends "default/pyproject.toml.jinja" %}\n'
                    "{% block indexes %}{{ super() }}\n[[tool.uv.index]]\n"
                    'name = "extra"\nurl = "https://extra.example/simple"\n{% endblock %}\n'
                    "{% block tail %}{{ super() }}\n[tool.extra]\nx = 1\n{% endblock %}\n"
                ),
            }
        },
        monkeypatch,
    )
    return site


def test_chalk_ships_two_templates() -> None:
    assert {t.id for t in load_templates(TEMPLATES_DIR)} == {
        "default",
        "language-toolchains",
    }


def test_builtin_templates_have_no_requirement() -> None:
    found = discover_templates()
    assert found["default"].dir == TEMPLATES_DIR / "default"
    assert found["default"].requirement is None


def test_entry_point_templates_are_discovered(extra_site: Path) -> None:
    found = discover_templates()
    extra = found["extra-overlay"]
    assert extra.template.requires == ["default"]
    assert (
        extra.dir == extra_site / "extra_templates_pkg" / "templates" / "extra-overlay"
    )
    assert extra.requirement == "extra-templates-pkg==1.2.3"
    assert found["default"].requirement is None


@pytest.mark.usefixtures("extra_site")
def test_list_names_the_providing_package(capsys: pytest.CaptureFixture[str]) -> None:
    from chalk.cli.templates import list_templates

    list_templates(json_output=False)
    out = capsys.readouterr().out
    assert "extra-overlay" in out
    assert "(from extra-templates-pkg==1.2.3)" in out
    assert "default — " in out


@pytest.mark.usefixtures("extra_site")
def test_list_json_carries_the_requirement(capsys: pytest.CaptureFixture[str]) -> None:
    from chalk.cli.templates import list_templates

    list_templates(json_output=True)
    by_id = {t["id"]: t for t in json.loads(capsys.readouterr().out)}
    assert by_id["extra-overlay"]["requirement"] == "extra-templates-pkg==1.2.3"
    assert by_id["default"]["requirement"] is None


def test_entry_point_template_shadows_a_builtin(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _install_template_package(
        tmp_path / "dup",
        "dup-pkg",
        "0.1",
        {"default": {"template.toml": 'description = "shadow"\n'}},
        monkeypatch,
    )
    found = discover_templates()["default"]
    assert found.requirement == "dup-pkg==0.1"
    assert found.template.description == "shadow"


def test_two_entry_point_packages_with_the_same_id_is_an_error(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    for name in ("pkg-a", "pkg-b"):
        _install_template_package(
            tmp_path / name,
            name,
            "0.1",
            {"clash": {"template.toml": 'description = "x"\n'}},
            monkeypatch,
        )
    with pytest.raises(ValueError, match="'clash'") as exc_info:
        discover_templates()
    assert "pkg-a" in str(exc_info.value) and "pkg-b" in str(exc_info.value)


def _discover_logging_warnings() -> tuple[dict[str, InstalledTemplate], list[str]]:
    warnings: list[str] = []
    handler = logger.add(lambda m: warnings.append(str(m)), level="WARNING")
    try:
        return discover_templates(), warnings
    finally:
        logger.remove(handler)


@pytest.mark.usefixtures("extra_site")
def test_a_plugin_that_fails_to_import_is_skipped(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _install_template_package(
        tmp_path / "broken",
        "broken-pkg",
        "0.1",
        {"broken": {"template.toml": 'description = "x"\n'}},
        monkeypatch,
    )
    (tmp_path / "broken" / "broken_pkg" / "__init__.py").write_text(
        "raise ImportError('missing dependency')\n"
    )

    found, warnings = _discover_logging_warnings()

    assert "broken" not in found
    assert "extra-overlay" in found
    assert any("broken_pkg" in w and "missing dependency" in w for w in warnings)


@pytest.mark.usefixtures("extra_site")
def test_a_plugin_with_an_invalid_template_is_skipped(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _install_template_package(
        tmp_path / "invalid",
        "invalid-pkg",
        "0.1",
        {"invalid": {"README.md": "no template.toml\n"}},
        monkeypatch,
    )

    found, warnings = _discover_logging_warnings()

    assert "invalid" not in found
    assert "extra-overlay" in found
    assert any("invalid_pkg" in w for w in warnings)


@pytest.mark.usefixtures("extra_site")
def test_create_env_renders_cross_package_overlay(tmp_path: Path) -> None:
    with patch("chalk.create_env.subprocess.check_call"):
        create_env(tmp_path / "my_env", templates=["extra-overlay"])
    env = tmp_path / "my_env"
    assert (env / "extra.txt").read_text() == "from extra my_env\n"
    pyproject = (env / "pyproject.toml").read_text()
    assert 'name = "environment"' in pyproject
    assert "[tool.extra]\nx = 1" in pyproject
    assert pyproject.index('name = "pypi"') < pyproject.index('name = "extra"')
    manifest = EnvManifest.model_validate_json((env / ".manifest.json").read_text())
    assert manifest.templates == ["default", "extra-overlay"]
    assert manifest.extra_deps == ["extra-templates-pkg==1.2.3"]


def test_create_env_builtin_only_records_no_extra_deps(tmp_path: Path) -> None:
    with patch("chalk.create_env.subprocess.check_call"):
        create_env(tmp_path / "my_env", templates=["default"])
    manifest = EnvManifest.model_validate_json(
        (tmp_path / "my_env" / ".manifest.json").read_text()
    )
    assert manifest.extra_deps == []


def test_manifest_without_extra_deps_parses() -> None:
    manifest = EnvManifest.model_validate_json(
        '{"chalk_version": "0.0.0", "templates": ["default"]}'
    )
    assert manifest.extra_deps == []


@pytest.mark.usefixtures("extra_site")
def test_update_adds_an_installed_template_package(tmp_path: Path) -> None:
    from chalk.update_env import update_env

    env = tmp_path / "my_env"
    create_env(env, templates=["default"], no_lock=True)
    original_run = subprocess.run

    def run_without_lock(
        cmd: list[str], **kwargs: object
    ) -> subprocess.CompletedProcess[str]:
        if cmd[:2] == ["uv", "lock"]:
            return subprocess.CompletedProcess(cmd, 0, stdout="", stderr="")
        return original_run(cmd, **kwargs)  # pyright: ignore[reportCallIssue, reportArgumentType]

    with patch("chalk.update_env.subprocess.run", side_effect=run_without_lock):
        assert update_env(env, add_templates=["extra-overlay"]) == []

    assert (env / "extra.txt").read_text() == "from extra my_env\n"
    manifest = EnvManifest.model_validate_json((env / ".manifest.json").read_text())
    assert manifest.templates == ["default", "extra-overlay"]
    assert manifest.extra_deps == ["extra-templates-pkg==1.2.3"]
