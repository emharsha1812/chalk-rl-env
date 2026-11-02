# pyright: reportPrivateUsage=false
import json
import subprocess
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest
from loguru import logger

from chalk.update_env import (
    MergeFileError,
    UpdateMigration,
    _env_uv_flags,
    _is_binary,
    _merge_do_not_recreate,
    _merge_file,
    _merge_projects,
    _migrations,
    _should_skip,
)


class TestMergeDoNotRecreate:
    def test_picks_up_template_additions(self):
        merged = _merge_do_not_recreate(base=["a"], theirs=["a", "b"], ours=["a"])
        assert merged == {"a", "b"}

    def test_drops_template_removals(self):
        merged = _merge_do_not_recreate(base=["a", "b"], theirs=["a"], ours=["a", "b"])
        assert merged == {"a"}

    def test_preserves_user_additions(self):
        merged = _merge_do_not_recreate(base=["a"], theirs=["a"], ours=["a", "mine"])
        assert merged == {"a", "mine"}

    def test_preserves_user_removals(self):
        merged = _merge_do_not_recreate(base=["a", "b"], theirs=["a", "b"], ours=["a"])
        assert merged == {"a"}

    def test_unseeded_env_adopts_theirs(self):
        """Manifest predating the field (ours=None) adopts the template's list
        wholesale, even when the baseline already shipped those paths."""
        merged = _merge_do_not_recreate(base=["a", "b"], theirs=["a", "b"], ours=None)
        assert merged == {"a", "b"}

    def test_unseeded_env_adopts_theirs_from_empty_baseline(self):
        merged = _merge_do_not_recreate(base=[], theirs=["a", "b"], ours=None)
        assert merged == {"a", "b"}

    def test_cleared_list_is_respected(self):
        """An explicit empty list means the user cleared it; keep it empty."""
        merged = _merge_do_not_recreate(base=["a"], theirs=["a", "b"], ours=[])
        assert merged == {"b"}


class TestShouldSkip:
    def test_skips_git_directory(self):
        assert _should_skip(Path(".git/config"))
        assert _should_skip(Path("foo/.git/objects"))

    def test_skips_pycache(self):
        assert _should_skip(Path("__pycache__/module.pyc"))
        assert _should_skip(Path("src/__pycache__/test.pyc"))

    def test_skips_manifest(self):
        assert _should_skip(Path(".manifest.json"))

    def test_skips_uv_lock(self):
        assert _should_skip(Path("uv.lock"))

    def test_does_not_skip_normal_files(self):
        assert not _should_skip(Path("pyproject.toml"))
        assert not _should_skip(Path("src/main.py"))
        assert not _should_skip(Path("README.md"))


class TestIsBinary:
    def test_text_file_is_not_binary(self, tmp_path: Path):
        text_file = tmp_path / "test.txt"
        text_file.write_text("Hello, world!")
        assert not _is_binary(text_file)

    def test_binary_file_is_binary(self, tmp_path: Path):
        binary_file = tmp_path / "test.bin"
        binary_file.write_bytes(b"Hello\x00World")
        assert _is_binary(binary_file)


class TestMergeFile:
    def test_clean_merge(self, tmp_path: Path):
        """Test merging when changes are far apart (no overlap)."""
        base = tmp_path / "base.txt"
        current = tmp_path / "current.txt"
        other = tmp_path / "other.txt"

        # Changes need to be far enough apart to not overlap
        base.write_text("line 1\nline 2\nline 3\nline 4\nline 5\nline 6\nline 7\n")
        current.write_text(
            "user modified line 1\nline 2\nline 3\nline 4\nline 5\nline 6\nline 7\n"
        )
        other.write_text(
            "line 1\nline 2\nline 3\nline 4\nline 5\nline 6\ntemplate modified line 7\n"
        )

        has_conflict = _merge_file(current, base, other)

        assert not has_conflict
        content = current.read_text()
        assert "user modified line 1" in content
        assert "template modified line 7" in content

    def test_conflicting_merge(self, tmp_path: Path):
        """Test merging when both sides modify the same line."""
        base = tmp_path / "base.txt"
        current = tmp_path / "current.txt"
        other = tmp_path / "other.txt"

        base.write_text("line 1\n")
        current.write_text("user change\n")
        other.write_text("template change\n")

        has_conflict = _merge_file(current, base, other)

        assert has_conflict
        content = current.read_text()
        # Git merge conflict markers should be present
        assert "<<<<<<<" in content or "=======" in content

    def test_git_error_leaves_the_file_alone(self, tmp_path: Path):
        base = tmp_path / "base.txt"
        current = tmp_path / "current.txt"
        other = tmp_path / "other.txt"
        base.write_text("line 1\n")
        current.write_bytes(b"user\x00data\n")
        other.write_text("template change\n")

        with pytest.raises(MergeFileError, match="Cannot merge binary files"):
            _merge_file(current, base, other)

        assert current.read_bytes() == b"user\x00data\n"


class TestMergeProjects:
    def test_adds_new_files_from_target(self, tmp_path: Path):
        """Files that exist only in target are added to project."""
        project = tmp_path / "project"
        baseline = tmp_path / "baseline"
        target = tmp_path / "target"

        project.mkdir()
        baseline.mkdir()
        target.mkdir()

        # New file only in target
        (target / "new_file.txt").write_text("new content")

        conflicts = _merge_projects(project, baseline, target)

        assert not conflicts
        assert (project / "new_file.txt").read_text() == "new content"

    def test_removes_deleted_files_from_project(self, tmp_path: Path):
        """Files removed from template are deleted from project."""
        project = tmp_path / "project"
        baseline = tmp_path / "baseline"
        target = tmp_path / "target"

        project.mkdir()
        baseline.mkdir()
        target.mkdir()

        # File exists in baseline and project, but not in target
        (baseline / "old_file.txt").write_text("old content")
        (project / "old_file.txt").write_text("old content")

        conflicts = _merge_projects(project, baseline, target)

        assert not conflicts
        assert not (project / "old_file.txt").exists()

    def test_recreates_user_deleted_files(self, tmp_path: Path):
        """Files deleted by user but still in template are recreated."""
        project = tmp_path / "project"
        baseline = tmp_path / "baseline"
        target = tmp_path / "target"

        project.mkdir()
        baseline.mkdir()
        target.mkdir()

        # File exists in both baseline and target, but user deleted from project
        (baseline / "important.txt").write_text("content")
        (target / "important.txt").write_text("updated content")

        conflicts = _merge_projects(project, baseline, target)

        assert not conflicts
        assert (project / "important.txt").read_text() == "updated content"

    def test_does_not_recreate_deleted_claude_md(self, tmp_path: Path):
        """CLAUDE.md deleted by the user is not recreated by update."""
        project = tmp_path / "project"
        baseline = tmp_path / "baseline"
        target = tmp_path / "target"

        project.mkdir()
        baseline.mkdir()
        target.mkdir()

        (baseline / "CLAUDE.md").write_text("content")
        (target / "CLAUDE.md").write_text("updated content")

        conflicts = _merge_projects(
            project, baseline, target, do_not_recreate_paths={"CLAUDE.md"}
        )

        assert not conflicts
        assert not (project / "CLAUDE.md").exists()

    def test_does_not_recreate_deleted_example_task(self, tmp_path: Path):
        """example_task files deleted by the user are not recreated by update."""
        project = tmp_path / "project"
        baseline = tmp_path / "baseline"
        target = tmp_path / "target"

        project.mkdir()
        baseline.mkdir()
        target.mkdir()

        task_rel = Path("src/environment/tasks/example_task/__init__.py")
        for root in (baseline, target):
            (root / task_rel).parent.mkdir(parents=True, exist_ok=True)
            (root / task_rel).write_text("task")

        conflicts = _merge_projects(
            project,
            baseline,
            target,
            do_not_recreate_paths={"src/environment/tasks/example_task"},
        )

        assert not conflicts
        assert not (project / task_rel).exists()

    def test_does_not_add_new_example_task(self, tmp_path: Path):
        """A newly-introduced example_task the user lacks is not added."""
        project = tmp_path / "project"
        baseline = tmp_path / "baseline"
        target = tmp_path / "target"

        project.mkdir()
        baseline.mkdir()
        target.mkdir()

        task_rel = Path("src/environment/tasks/example_task/__init__.py")
        (target / task_rel).parent.mkdir(parents=True, exist_ok=True)
        (target / task_rel).write_text("task")

        conflicts = _merge_projects(
            project,
            baseline,
            target,
            do_not_recreate_paths={"src/environment/tasks/example_task"},
        )

        assert not conflicts
        assert not (project / task_rel).exists()

    def test_still_merges_present_claude_md(self, tmp_path: Path):
        """CLAUDE.md the user kept is still merged, not preserved-as-is."""
        project = tmp_path / "project"
        baseline = tmp_path / "baseline"
        target = tmp_path / "target"

        project.mkdir()
        baseline.mkdir()
        target.mkdir()

        base_content = "\n".join([f"line{i}=original" for i in range(1, 10)]) + "\n"
        project_content = (
            "line1=user\n"
            + "\n".join([f"line{i}=original" for i in range(2, 10)])
            + "\n"
        )
        target_content = (
            "\n".join([f"line{i}=original" for i in range(1, 9)]) + "\nline9=template\n"
        )

        (baseline / "CLAUDE.md").write_text(base_content)
        (project / "CLAUDE.md").write_text(project_content)
        (target / "CLAUDE.md").write_text(target_content)

        conflicts = _merge_projects(
            project, baseline, target, do_not_recreate_paths={"CLAUDE.md"}
        )

        assert not conflicts
        content = (project / "CLAUDE.md").read_text()
        assert "line1=user" in content
        assert "line9=template" in content

    def test_merges_modified_files(self, tmp_path: Path):
        """Files modified in both project and template are merged."""
        project = tmp_path / "project"
        baseline = tmp_path / "baseline"
        target = tmp_path / "target"

        project.mkdir()
        baseline.mkdir()
        target.mkdir()

        # Changes need to be far apart to avoid git merge-file treating them as conflicts
        base_content = "\n".join([f"line{i}=original" for i in range(1, 10)]) + "\n"
        project_content = (
            "line1=user\n"
            + "\n".join([f"line{i}=original" for i in range(2, 10)])
            + "\n"
        )
        target_content = (
            "\n".join([f"line{i}=original" for i in range(1, 9)]) + "\nline9=template\n"
        )

        (baseline / "config.txt").write_text(base_content)
        (project / "config.txt").write_text(project_content)
        (target / "config.txt").write_text(target_content)

        conflicts = _merge_projects(project, baseline, target)

        assert not conflicts
        content = (project / "config.txt").read_text()
        assert "line1=user" in content
        assert "line9=template" in content

    def test_unmergeable_file_keeps_the_user_version(self, tmp_path: Path):
        project, baseline, target = (tmp_path / n for n in ("p", "b", "t"))
        for d in (project, baseline, target):
            d.mkdir()
        (baseline / "data.txt").write_bytes(b"old\x00binary\n")
        (project / "data.txt").write_bytes(b"user\x00binary\n")
        (target / "data.txt").write_text("now text\n")
        warnings: list[str] = []
        handler = logger.add(lambda m: warnings.append(str(m)), level="WARNING")
        try:
            conflicts = _merge_projects(project, baseline, target)
        finally:
            logger.remove(handler)

        assert conflicts == [Path("data.txt")]
        assert (project / "data.txt").read_bytes() == b"user\x00binary\n"
        assert any(
            "data.txt" in w and "Cannot merge binary files" in w for w in warnings
        )


class TestManifestCreation:
    """Test that create_env writes .manifest.json correctly."""

    def test_creates_manifest_with_version_and_templates(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ):
        from chalk import create_env as create_env_module
        from chalk.create_env import create_env

        # Create minimal template
        templates_dir = tmp_path / "templates" / "test"
        templates_dir.mkdir(parents=True)
        (templates_dir / "template.toml").write_text('description = "Test"\n')
        (templates_dir / "file.txt").write_text("content")

        monkeypatch.setattr(create_env_module, "TEMPLATES_DIR", tmp_path / "templates")

        with patch("chalk.create_env.pkg_version", return_value="1.2.3"):
            create_env(tmp_path / "my_env", templates=["test"])

        manifest_path = tmp_path / "my_env" / ".manifest.json"
        assert manifest_path.exists()

        manifest = json.loads(manifest_path.read_text())
        assert manifest["chalk_version"] == "1.2.3"
        assert manifest["templates"] == ["test"]

    def test_no_lock_skips_uv_lock(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ):
        from chalk import create_env as create_env_module
        from chalk.create_env import create_env

        # Create template with pyproject.toml
        templates_dir = tmp_path / "templates" / "test"
        templates_dir.mkdir(parents=True)
        (templates_dir / "template.toml").write_text('description = "Test"\n')
        (templates_dir / "pyproject.toml").write_text("[project]\nname = 'test'\n")

        monkeypatch.setattr(create_env_module, "TEMPLATES_DIR", tmp_path / "templates")

        with patch("chalk.create_env.subprocess.check_call") as mock_check_call:
            create_env(tmp_path / "my_env", templates=["test"], no_lock=True)

        # uv lock should not have been called
        mock_check_call.assert_not_called()


class TestForwardsEnvIndexes:
    PYPROJECT: str = """
[tool.uv]
keyring-provider = "subprocess"

[[tool.uv.index]]
name = "private"
url = "https://private.example/simple/"

[[tool.uv.index]]
name = "pytorch"
url = "https://download.pytorch.org/whl/cu126"
explicit = true

[[tool.uv.index]]
name = "pypi"
url = "https://pypi.org/simple"
default = true
"""

    def test_reads_indexes_and_keyring_provider(self, tmp_path: Path):
        (tmp_path / "pyproject.toml").write_text(self.PYPROJECT)
        assert _env_uv_flags(tmp_path) == [
            "--index=private=https://private.example/simple/",
            "--default-index=https://pypi.org/simple",
            "--keyring-provider=subprocess",
        ]

    def test_no_pyproject(self, tmp_path: Path):
        assert _env_uv_flags(tmp_path) == []

    def test_unparseable_pyproject(self, tmp_path: Path):
        (tmp_path / "pyproject.toml").write_text("<<<<<<< ours\n")
        assert _env_uv_flags(tmp_path) == []


def test_a_migration_that_fails_to_load_is_skipped(
    monkeypatch: pytest.MonkeyPatch,
):
    def broken() -> UpdateMigration:
        raise ImportError("missing dependency")

    ok = _Migration()
    monkeypatch.setattr(
        "chalk.update_env.entry_points",
        lambda *, group: [  # pyright: ignore[reportUnknownLambdaType]
            SimpleNamespace(name="broken", load=broken),
            SimpleNamespace(name="ok", load=lambda: ok),
        ],
    )
    warnings: list[str] = []
    handler = logger.add(lambda m: warnings.append(str(m)), level="WARNING")
    try:
        assert _migrations() == [ok]
    finally:
        logger.remove(handler)
    assert any("broken" in w and "missing dependency" in w for w in warnings)


class _Migration:
    """Stands in for a `chalk.update_migrations` plugin that moves envs off an
    older naming scheme."""

    def __init__(self, tool_args: dict[str, list[str]] | None = None) -> None:
        self.tool_args: dict[str, list[str]] = tool_args or {}
        self.calls: list[str] = []

    def prepare(self, project_dir: Path) -> None:
        self.calls.append("prepare")
        path = project_dir / ".manifest.json"
        manifest = json.loads(path.read_text())
        if "old_version" in manifest:
            manifest["chalk_version"] = manifest.pop("old_version")
            path.write_text(json.dumps(manifest))

    def tool(self, version: str) -> list[str] | None:
        return self.tool_args.get(version)

    def migrate(self, baseline_dir: Path, project_dir: Path, old_version: str) -> None:
        self.calls.append(f"migrate {old_version}")
        for root in (baseline_dir, project_dir):
            for path in (root / "pyproject.toml", root / "justfile"):
                if path.is_file():
                    path.write_text(path.read_text().replace("oldname", "chalk"))


class TestRelaunchWithTemplatePackages:
    """Missing template packages can be added alongside the local installation."""

    def _project(self, tmp_path: Path, extra_deps: list[str]) -> Path:
        project = tmp_path / "env"
        project.mkdir()
        (project / ".manifest.json").write_text(
            json.dumps(
                {
                    "pm_env_version": "2.18.708",
                    "templates": ["default"],
                    "extra_deps": extra_deps,
                }
            )
        )
        (project / "pyproject.toml").write_text(
            '[[tool.uv.index]]\nname = "extra"\nurl = "https://extra.example/simple/"\n'
        )
        return project

    def _invoke(self, project: Path, *args: str, env: dict[str, str] | None = None):
        from typer.testing import CliRunner

        from chalk.cli import app

        with (
            patch("chalk.update_env.subprocess.run") as run,
            patch("chalk.update_env.update_env") as update,
        ):
            run.return_value = subprocess.CompletedProcess([], 3)
            result = CliRunner().invoke(app, ["update", str(project), *args], env=env)
        return result, run, update

    def test_relaunches_with_the_packages_it_cannot_import(self, tmp_path: Path):
        project = self._project(tmp_path, ["not-installed-tmpl==1.0"])

        result, run, update = self._invoke(project, "--add-template", "extra")

        update.assert_not_called()
        assert result.exit_code == 3
        command = run.call_args.args[0]
        assert command[:3] == ["uv", "tool", "run"]
        assert "--index=extra=https://extra.example/simple/" in command
        assert command[command.index("--with") + 1] == "not-installed-tmpl"
        assert command[-4:] == ["update", str(project), "--add-template", "extra"]
        assert run.call_args.kwargs["env"]["CHALK_UPDATE_RELAUNCHED"] == "1"

    def test_runs_in_place_when_the_packages_are_installed(self, tmp_path: Path):
        project = self._project(tmp_path, ["loguru==0.0.1"])

        _, run, update = self._invoke(project)

        run.assert_not_called()
        update.assert_called_once()

    def test_relaunches_only_once(self, tmp_path: Path):
        project = self._project(tmp_path, ["not-installed-tmpl==1.0"])

        _, run, update = self._invoke(project, env={"CHALK_UPDATE_RELAUNCHED": "1"})

        run.assert_not_called()
        update.assert_called_once()


class TestThisChalk:
    def test_unknown_distribution_is_not_fetched_from_a_registry(self):
        from importlib.metadata import PathDistribution

        from chalk.update_env import _this_chalk

        dist = MagicMock(spec=PathDistribution, version="3.0.14")
        dist.read_text.return_value = None
        with patch("chalk.update_env.distribution", return_value=dist):
            with pytest.raises(
                RuntimeError, match="no configured published distribution"
            ):
                _this_chalk()

    def test_a_source_install_runs_from_its_tree(self, tmp_path: Path):
        from importlib.metadata import PathDistribution

        from chalk.update_env import _this_chalk

        dist = MagicMock(spec=PathDistribution, version="3.0.0")
        dist.read_text.return_value = json.dumps(
            {"url": tmp_path.as_uri(), "dir_info": {"editable": True}}
        )
        with patch("chalk.update_env.distribution", return_value=dist):
            assert _this_chalk() == ["--from", str(tmp_path), "chalk"]
