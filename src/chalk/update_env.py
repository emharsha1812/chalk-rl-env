import json
import os
import re
import shutil
import subprocess
import sys
import sysconfig
import tomllib
from collections.abc import Collection, Mapping, Sequence
from importlib.metadata import PackageNotFoundError, distribution, entry_points
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Protocol
from urllib.parse import urlsplit
from urllib.request import url2pathname

from loguru import logger

from chalk.create_env import EnvManifest
from chalk.uv_supply_chain import env_with_age_delay, run_uv

# Files/directories to skip during merge
SKIP_PATTERNS = {
    ".git",
    "__pycache__",
    ".ruff_cache",
    ".venv",
    ".manifest.json",
    ".chalk",
    ".chalk-template-base",
    ".chalk-update-backup",
    "uv.lock",
}

INDEX_OVERRIDE_VARS = (
    "UV_INDEX",
    "UV_DEFAULT_INDEX",
    "UV_INDEX_URL",
    "UV_EXTRA_INDEX_URL",
)
"""uv prefers these over a project's own indexes."""

MIGRATION_ENTRY_POINT_GROUP = "chalk.update_migrations"


class MergeFileError(RuntimeError):
    pass


class UpdateMigration(Protocol):
    """Moves an env made by an older release to the current names; registered
    under `chalk.update_migrations`."""

    def prepare(self, project_dir: Path) -> None:
        """Runs before the project's manifest is read."""
        ...

    def migrate(self, baseline_dir: Path, project_dir: Path, old_version: str) -> None:
        """Runs on the old-version render and the project before the merge."""
        ...


def _migrations() -> list[UpdateMigration]:
    migrations: list[UpdateMigration] = []
    for ep in entry_points(group=MIGRATION_ENTRY_POINT_GROUP):
        try:
            migrations.append(ep.load())
        except Exception as e:  # noqa: BLE001 - a broken plugin must not break chalk
            logger.warning("Ignoring update migration {!r}: {}", ep.name, e)
    return migrations


RELAUNCHED_ENV_VAR = "CHALK_UPDATE_RELAUNCHED"


def missing_template_packages(
    project_dir: Path, extra_with: Collection[str]
) -> list[str]:
    """Template packages the manifest or `extra_with` names that are not installed here.

    Their update migrations only run if they are installed next to this chalk.
    """
    try:
        manifest = json.loads((project_dir / ".manifest.json").read_text())
    except (OSError, ValueError):
        return []
    recorded = manifest.get("extra_deps") or []
    missing: list[str] = []
    for requirement in dict.fromkeys([*map(_unpinned, recorded), *extra_with]):
        try:
            distribution(_package_name(requirement))
        except PackageNotFoundError:
            missing.append(requirement)
    return missing


def relaunch_with(
    project_dir: Path, packages: Sequence[str], args: Sequence[str]
) -> int:
    """Rerun `chalk <args>` with `packages` installed next to it; returns its exit code."""
    logger.info(f"Restarting with {', '.join(packages)} installed")
    return run_uv(
        ("tool", "run"),
        *_env_uv_flags(project_dir),
        *_with_flags(packages),
        *_this_chalk(),
        *args,
        env=_uv_env(env_with_age_delay()) | {RELAUNCHED_ENV_VAR: "1"},
    ).returncode


def _this_chalk() -> list[str]:
    """Use only the local source from which this installation was installed."""
    dist = distribution("chalk-rl-env")
    direct_url = json.loads(dist.read_text("direct_url.json") or "{}").get("url", "")
    if direct_url.startswith("file://"):
        return ["--from", url2pathname(urlsplit(direct_url).path), "chalk"]
    raise RuntimeError(
        "Chalk has no configured published distribution. Install it from a local "
        + "checkout before adding template packages."
    )


def check_index_overrides() -> None:
    """Refuse ambient index settings that would change the project's lock."""
    for var in INDEX_OVERRIDE_VARS:
        if os.environ.get(var):
            raise RuntimeError(
                f"{var} overrides the environment's package indexes. "
                + "Unset it before updating."
            )


def update_env(
    project_dir: Path,
    add_templates: Collection[str] = (),
    extra_with: Collection[str] = (),
) -> list[Path]:
    """Merge current local templates against the saved creation baseline.

    The running Chalk installation supplies the target; no registry lookup is
    made for Chalk. The managed source copy is refreshed only if untouched.
    """
    from chalk.create_env import create_env, vendored_hash

    project_dir = project_dir.resolve()
    check_index_overrides()
    migrations = _migrations()
    for migration in migrations:
        migration.prepare(project_dir)
    manifest_path = project_dir / ".manifest.json"
    if not manifest_path.is_file():
        raise FileNotFoundError(f"No .manifest.json found in {project_dir}.")
    raw = json.loads(manifest_path.read_text(encoding="utf-8"))
    if "karotte_version" in raw and "chalk_version" not in raw:
        raise RuntimeError(
            "This is an older Karotte environment. Create a new Chalk environment "
            + "and move your task code and data after reviewing the changes; "
            + "automatic conversion is not supported."
        )
    manifest = EnvManifest.model_validate(raw)
    baseline = project_dir / ".chalk-template-base"
    vendor = project_dir / ".chalk"
    if not baseline.is_dir() or not manifest.vendored_sha256 or not vendor.is_dir():
        raise RuntimeError(
            "The saved Chalk template baseline or local source copy is missing. "
            + "Restore them from your environment backup before updating."
        )
    if vendored_hash(vendor) != manifest.vendored_sha256:
        raise RuntimeError(
            "The local .chalk source copy has been edited. Save your changes and "
            + "restore the original copy before updating, so they are not lost."
        )
    additions = list(add_templates)
    if len(set(additions)) != len(additions):
        raise ValueError("A template was listed more than once.")
    additions = [name for name in additions if name not in manifest.templates]
    # Templates from extra packages must be installed beside the running Chalk.
    missing = missing_template_packages(project_dir, extra_with)
    if missing:
        raise RuntimeError(
            "Install these template packages beside Chalk: " + ", ".join(missing)
        )

    with TemporaryDirectory() as tmp:
        baseline_copy = Path(tmp) / "baseline"
        shutil.copytree(baseline, baseline_copy)
        target = Path(tmp) / "target" / project_dir.name
        create_env(
            target,
            [*manifest.templates, *additions],
            agents=manifest.agents,
            no_lock=True,
        )
        target_base = target / ".chalk-template-base"
        target_manifest = EnvManifest.model_validate_json(
            (target / ".manifest.json").read_text(encoding="utf-8")
        )
        for migration in migrations:
            migration.migrate(baseline_copy, project_dir, manifest.chalk_version)
        do_not_recreate = _merge_do_not_recreate(
            base=_read_do_not_recreate(baseline_copy),
            theirs=target_manifest.do_not_recreate_if_deleted or [],
            ours=manifest.do_not_recreate_if_deleted,
        )
        before = _venv_pyprojects(project_dir)
        conflicts = _merge_projects(
            project_dir, baseline_copy, target_base, do_not_recreate
        )
        pyproject = project_dir / "pyproject.toml"
        pyproject_conflicted = Path("pyproject.toml") in conflicts
        if pyproject.exists() and not pyproject_conflicted:
            config = tomllib.loads(pyproject.read_text(encoding="utf-8"))
            source = (
                config.get("tool", {})
                .get("uv", {})
                .get("sources", {})
                .get("chalk-rl-env")
            )
            deps = config.get("project", {}).get("dependencies", [])
            needs_chalk = any(
                re.match(r"\s*chalk[-_.]rl[-_.]env(?:\b|\[)", dep, re.I) for dep in deps
            )
            if needs_chalk and (
                not isinstance(source, dict) or source.get("path") != ".chalk"
            ):
                raise RuntimeError(
                    "The Chalk dependency must use the local .chalk source."
                )

        # A backup makes a failed copy recoverable. Never overwrite an existing one.
        backup = project_dir / ".chalk-update-backup"
        if backup.exists():
            raise RuntimeError(f"Remove or restore the existing backup {backup} first.")
        vendor.rename(backup)
        try:
            shutil.copytree(target / ".chalk", vendor)
            target_manifest.do_not_recreate_if_deleted = sorted(do_not_recreate)
            target_manifest.vendored_sha256 = vendored_hash(vendor)
            if pyproject.exists() and not pyproject_conflicted:
                subprocess.run(["uv", "lock"], cwd=project_dir, check=True)
            _relock_changed_venvs(project_dir, before, conflicts)
        except BaseException:
            if vendor.exists():
                shutil.rmtree(vendor)
            backup.rename(vendor)
            raise
        shutil.rmtree(backup)
        # These files are managed by Chalk and excluded from template merging.
        shutil.rmtree(baseline)
        shutil.copytree(target_base, baseline)
        manifest_path.write_text(
            target_manifest.model_dump_json(indent=2), encoding="utf-8"
        )
        if conflicts:
            logger.warning(
                "Resolve the reported template conflicts before using the environment."
            )
            for path in conflicts:
                logger.warning("  - {}", path)
            if pyproject_conflicted:
                logger.warning(
                    "After resolving pyproject.toml, run `uv lock` in the environment."
                )
        else:
            logger.info("Updated the local Chalk copy and templates.")
        return conflicts


def _venv_pyprojects(project_dir: Path) -> dict[Path, str]:
    return {
        p.relative_to(project_dir): p.read_text()
        for p in project_dir.glob("venvs/*/pyproject.toml")
    }


def _relock_changed_venvs(
    project_dir: Path, before: dict[Path, str], conflicts: Collection[Path]
) -> None:
    """Lock each venv whose pyproject the merge added or changed; its old lock
    may point at indexes the pyproject no longer declares. With conflicts, a
    failure is only logged so the conflicts still reach the caller."""
    for rel, text in sorted(_venv_pyprojects(project_dir).items()):
        if before.get(rel) == text or rel in conflicts:
            continue
        venv = rel.parent
        logger.info(f"Regenerating {venv}/uv.lock")
        try:
            subprocess.run(
                ["uv", "lock"],
                cwd=project_dir / venv,
                capture_output=True,
                text=True,
                check=True,
                env=_uv_env(os.environ),
            )
        except subprocess.CalledProcessError as e:
            message = f"Failed to regenerate {venv}/uv.lock: {e.stderr.strip()}"
            if not conflicts:
                raise RuntimeError(message) from e
            logger.warning(
                f"{message}\nRun `uv lock` in {venv} once the conflicts are resolved."
            )


def _merge_do_not_recreate(
    base: Collection[str],
    theirs: Collection[str],
    ours: Collection[str] | None,
) -> set[str]:
    """3-way merge a do-not-recreate list.

    When `ours` is None the manifest predates the field and was never seeded, so
    adopt the current template's list (`theirs`) wholesale. Otherwise apply the
    template's delta (`base` -> `theirs`) to the user-edited list (`ours`): paths
    the new template added are picked up, paths it removed are dropped, and the
    user's own additions/removals are otherwise preserved.
    """
    if ours is None:
        return set(theirs)
    base, theirs, ours = set(base), set(theirs), set(ours)
    return (ours | (theirs - base)) - (base - theirs)


_REQUIREMENT_NAME = re.compile(r"^\s*([A-Za-z0-9][A-Za-z0-9._-]*)(\[[^\]]*\])?")


def _unpinned(requirement: str) -> str:
    """`name[extras]` without the version specifier."""
    match = _REQUIREMENT_NAME.match(requirement)
    return match.group(1) + (match.group(2) or "") if match else requirement


def _package_name(requirement: str) -> str:
    match = _REQUIREMENT_NAME.match(requirement)
    return match.group(1) if match else requirement


def _read_do_not_recreate(env_dir: Path) -> list[str]:
    """Read the do-not-recreate list from a generated env's manifest.

    Returns an empty list for envs generated by a chalk version predating the
    field (it parses as None).
    """
    manifest_path = env_dir / ".manifest.json"
    if not manifest_path.exists():
        return []
    return (
        EnvManifest.model_validate_json(
            manifest_path.read_text()
        ).do_not_recreate_if_deleted
        or []
    )


def _env_uv_flags(project_dir: Path) -> list[str]:
    """The project's non-explicit indexes and keyring provider as uv flags, which
    `uv tool run` would otherwise ignore."""
    try:
        doc = tomllib.loads((project_dir / "pyproject.toml").read_text())
    except (FileNotFoundError, tomllib.TOMLDecodeError):
        return []
    uv = doc.get("tool", {}).get("uv", {})
    flags: list[str] = []
    for index in uv.get("index", []):
        if index.get("explicit") or "url" not in index:
            continue
        if index.get("default"):
            flags.append(f"--default-index={index['url']}")
        elif "name" in index:
            flags.append(f"--index={index['name']}={index['url']}")
    if provider := uv.get("keyring-provider"):
        flags.append(f"--keyring-provider={provider}")
    return flags


def _uv_env(base: Mapping[str, str]) -> dict[str, str]:
    """`base` without this venv's scripts dir on PATH, where chalk's dependencies
    put a `keyring` that would shadow the one uv needs for index credentials."""
    env = dict(base)
    if sys.prefix == sys.base_prefix:
        return env
    scripts = os.path.normpath(sysconfig.get_path("scripts"))
    env["PATH"] = os.pathsep.join(
        entry
        for entry in env.get("PATH", "").split(os.pathsep)
        if os.path.normpath(entry) != scripts
    )
    return env


def _with_flags(extra_deps: Sequence[str]) -> list[str]:
    """`--with` for each package, exempt from the age delay: template packages
    are first-party by construction and a fresh release must be visible."""
    return [arg for dep in extra_deps for arg in ("--with", dep)] + [
        f"--exclude-newer-package={_package_name(dep)}=false" for dep in extra_deps
    ]


def _should_skip(rel_path: Path) -> bool:
    """Check if a file should be skipped during merge."""
    parts = rel_path.parts
    for pattern in SKIP_PATTERNS:
        if pattern in parts or str(rel_path) == pattern:
            return True
    return False


def _do_not_recreate(rel_path: Path, do_not_recreate_paths: Collection[str]) -> bool:
    """Whether an absent path should be left absent rather than (re)created."""
    rel_str = rel_path.as_posix()
    for pattern in do_not_recreate_paths:
        if rel_str == pattern or rel_str.startswith(pattern + "/"):
            return True
    return False


def _is_binary(file_path: Path) -> bool:
    """Check if a file is binary by reading first chunk."""
    try:
        with open(file_path, "rb") as f:
            chunk = f.read(8192)
            return b"\x00" in chunk
    except OSError:
        return False


def _merge_projects(
    project: Path,
    baseline: Path,
    target: Path,
    do_not_recreate_paths: Collection[str] = (),
) -> list[Path]:
    """
    3-way merge between baseline, target, and current project.

    `do_not_recreate_paths` are repo-relative paths (files or directories) that
    must not be (re)created in the project if they are absent there.

    Returns list of files with conflicts.
    """
    conflicts: list[Path] = []

    baseline_files = {
        f.relative_to(baseline)
        for f in baseline.rglob("*")
        if f.is_file() and not _should_skip(f.relative_to(baseline))
    }
    target_files = {
        f.relative_to(target)
        for f in target.rglob("*")
        if f.is_file() and not _should_skip(f.relative_to(target))
    }
    all_files = baseline_files | target_files

    for relative_path in sorted(all_files):
        baseline_file = baseline / relative_path
        target_file = target / relative_path
        project_file = project / relative_path

        in_baseline = baseline_file.exists()
        in_target = target_file.exists()

        if in_baseline and in_target:
            # File exists in both versions
            if not project_file.exists():
                if _do_not_recreate(relative_path, do_not_recreate_paths):
                    # User deleted it and the env opts out of recreating it.
                    logger.info(f"Preserving user deletion: {relative_path}")
                    continue
                # User deleted it, recreate from target
                logger.info(f"Recreating deleted file: {relative_path}")
                project_file.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy(target_file, project_file)
            elif _is_binary(target_file):
                # Binary file: copy from target
                logger.info(f"Updating binary file: {relative_path}")
                shutil.copy(target_file, project_file)
            else:
                # Text file: 3-way merge
                try:
                    has_conflict = _merge_file(project_file, baseline_file, target_file)
                except MergeFileError as e:
                    logger.warning(
                        f"Could not merge {relative_path}, kept your version; "
                        + f"apply the template's changes by hand: {e}"
                    )
                    has_conflict = True
                if has_conflict:
                    conflicts.append(relative_path)

        elif in_target and not in_baseline:
            if not project_file.exists() and _do_not_recreate(
                relative_path, do_not_recreate_paths
            ):
                # Opt-out path the project doesn't have; don't add it.
                logger.info(f"Skipping opt-out path not in project: {relative_path}")
                continue
            # New file in template: add to project
            logger.info(f"Adding new file: {relative_path}")
            project_file.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy(target_file, project_file)

        elif in_baseline and not in_target:
            # File removed from template: delete from project
            if project_file.exists():
                logger.info(f"Removing deleted file: {relative_path}")
                project_file.unlink()

    return conflicts


def _merge_file(current: Path, base: Path, other: Path) -> bool:
    """3-way merge `other`'s changes since `base` into `current`; True on conflicts.

    Raises MergeFileError, leaving `current` untouched, if git cannot merge.
    """
    result = subprocess.run(
        ["git", "merge-file", "-p", str(current), str(base), str(other)],
        capture_output=True,
        text=True,
    )
    # Exit status is the conflict count, capped at 127; errors exit negative (255).
    if not 0 <= result.returncode <= 127:
        raise MergeFileError(result.stderr.strip())
    current.write_text(result.stdout)
    return result.returncode > 0
