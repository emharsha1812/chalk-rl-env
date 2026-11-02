"""Tests for the local-only environment update workflow."""

import importlib
import json
import subprocess
import tomllib
from pathlib import Path

import pytest

from chalk.create_env import create_env, vendored_hash
from chalk.update_env import UpdateMigration, update_env

create_module = importlib.import_module("chalk.create_env")


@pytest.fixture
def local_template(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    templates = tmp_path / "templates"
    template = templates / "simple"
    template.mkdir(parents=True)
    (template / "template.toml").write_text('description = "A test template"\n')
    (template / "notes.txt").write_text("first\n2\n3\n4\n5\n6\n7\n8\n9\nlast\n")
    monkeypatch.setattr(create_module, "TEMPLATES_DIR", templates)

    def no_migrations() -> list[UpdateMigration]:
        return []

    monkeypatch.setattr("chalk.update_env._migrations", no_migrations)
    return template


def test_versioned_chalk_dependencies_use_the_local_source(
    tmp_path: Path, local_template: Path
) -> None:
    project = '[project]\nname = "example"\nversion = "1.0"\n' + (
        'dependencies = ["Chalk_RL_Env[gcs]>=3"]\n'
    )
    (local_template / "pyproject.toml").write_text(project)
    nested = local_template / "venvs/student"
    nested.mkdir(parents=True)
    (nested / "pyproject.toml").write_text(project)
    env = tmp_path / "env"
    create_env(env, ["simple"], no_lock=True)

    root_doc = tomllib.loads((env / "pyproject.toml").read_text())
    nested_doc = tomllib.loads((env / "venvs/student/pyproject.toml").read_text())
    assert root_doc["tool"]["uv"]["sources"]["chalk-rl-env"]["path"] == ".chalk"
    assert nested_doc["tool"]["uv"]["sources"]["chalk-rl-env"]["path"] == "../../.chalk"


def test_a_template_cannot_accidentally_depend_on_the_unrelated_chalk_package(
    tmp_path: Path, local_template: Path
) -> None:
    (local_template / "pyproject.toml").write_text(
        '[project]\nname = "example"\nversion = "1.0"\ndependencies = ["chalk>=1"]\n'
    )
    env = tmp_path / "env"
    with pytest.raises(ValueError, match="unrelated chalk distribution"):
        create_env(env, ["simple"], no_lock=True)
    assert not env.exists()


def test_update_merges_local_changes_and_new_template_changes(
    tmp_path: Path, local_template: Path
) -> None:
    env = tmp_path / "env"
    create_env(env, ["simple"], no_lock=True)
    notes = env / "notes.txt"
    notes.write_text(notes.read_text().replace("last", "my edit"))
    source = local_template / "notes.txt"
    source.write_text(source.read_text().replace("first", "new template"))

    assert update_env(env) == []
    assert notes.read_text().startswith("new template\n")
    assert notes.read_text().endswith("my edit\n")
    assert (
        (env / ".chalk-template-base/notes.txt")
        .read_text()
        .startswith("new template\n")
    )


def test_update_protects_edits_to_local_framework(
    tmp_path: Path, local_template: Path
) -> None:
    assert local_template.is_dir()
    env = tmp_path / "env"
    create_env(env, ["simple"], no_lock=True)
    readme = env / ".chalk/README.md"
    readme.write_text(readme.read_text() + "\nMy change\n")

    with pytest.raises(RuntimeError, match="has been edited"):
        update_env(env)
    assert readme.read_text().endswith("My change\n")


def test_conflict_can_be_resolved_without_losing_the_new_baseline(
    tmp_path: Path, local_template: Path
) -> None:
    source = local_template / "notes.txt"
    source.write_text("original\n")
    env = tmp_path / "env"
    create_env(env, ["simple"], no_lock=True)
    notes = env / "notes.txt"
    notes.write_text("local change\n")
    source.write_text("template change\n")

    assert update_env(env) == [Path("notes.txt")]
    assert "<<<<<<<" in notes.read_text()
    notes.write_text("resolved change\n")
    assert update_env(env) == []
    assert notes.read_text() == "resolved change\n"


def test_adds_a_template_to_an_existing_environment(
    tmp_path: Path, local_template: Path
) -> None:
    env = tmp_path / "env"
    create_env(env, ["simple"], no_lock=True)
    addon = local_template.parent / "addon"
    addon.mkdir()
    (addon / "template.toml").write_text(
        'description = "Add-on"\nrequires = ["simple"]\n'
    )
    (addon / "extra.txt").write_text("added\n")

    assert update_env(env, add_templates=["addon"]) == []
    assert (env / "extra.txt").read_text() == "added\n"
    assert json.loads((env / ".manifest.json").read_text())["templates"] == [
        "simple",
        "addon",
    ]


def test_update_calls_installed_migration_hooks(
    tmp_path: Path, local_template: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    assert local_template.is_dir()
    env = tmp_path / "env"
    create_env(env, ["simple"], no_lock=True)
    calls: list[str] = []

    class Migration:
        def prepare(self, project_dir: Path) -> None:
            assert project_dir == env
            calls.append("prepare")

        def migrate(
            self, baseline_dir: Path, project_dir: Path, old_version: str
        ) -> None:
            assert (baseline_dir / "notes.txt").is_file()
            assert baseline_dir != env / ".chalk-template-base"
            assert project_dir == env
            calls.append(f"migrate {old_version}")

    def migrations() -> list[UpdateMigration]:
        return [Migration()]

    monkeypatch.setattr("chalk.update_env._migrations", migrations)
    assert update_env(env) == []
    assert calls == ["prepare", "migrate 3.0.0"]


def test_failed_relock_restores_the_original_framework_copy(
    tmp_path: Path, local_template: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    (local_template / "pyproject.toml").write_text(
        '[project]\nname = "example"\nversion = "1.0"\n'
        + 'dependencies = ["chalk-rl-env"]\n'
    )
    env = tmp_path / "env"
    create_env(env, ["simple"], no_lock=True)
    before = vendored_hash(env / ".chalk")
    manifest = (env / ".manifest.json").read_text()
    original_run = subprocess.run

    def fail_lock(cmd: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
        if cmd[:2] == ["uv", "lock"]:
            raise subprocess.CalledProcessError(1, cmd)
        return original_run(cmd, **kwargs)  # pyright: ignore[reportCallIssue, reportArgumentType]

    monkeypatch.setattr("chalk.update_env.subprocess.run", fail_lock)
    with pytest.raises(subprocess.CalledProcessError):
        update_env(env)
    assert vendored_hash(env / ".chalk") == before
    assert (env / ".manifest.json").read_text() == manifest
    assert not (env / ".chalk-update-backup").exists()


@pytest.mark.parametrize(
    "var", ["UV_INDEX", "UV_DEFAULT_INDEX", "UV_INDEX_URL", "UV_EXTRA_INDEX_URL"]
)
def test_update_refuses_index_overrides_before_changes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, var: str
) -> None:
    monkeypatch.setenv(var, "https://example.invalid/simple")
    with pytest.raises(RuntimeError, match=var):
        update_env(tmp_path)


def test_legacy_manifest_is_not_silently_converted(tmp_path: Path) -> None:
    env = tmp_path / "env"
    env.mkdir()
    manifest = env / ".manifest.json"
    original = {"karotte_version": "3.0.0", "templates": ["default"]}
    manifest.write_text(json.dumps(original))

    with pytest.raises(RuntimeError, match="older Karotte environment"):
        update_env(env)
    assert json.loads(manifest.read_text()) == original
