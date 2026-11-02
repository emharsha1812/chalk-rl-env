import hashlib
import importlib.util
import io
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from chalk.create_env import create_env


def test_lean_template_renders_an_ubuntu_image_and_task(tmp_path: Path):
    target = tmp_path / "lean_env"
    create_env(target, templates=["lean-math"], no_lock=True)

    dockerfile = (target / "Containerfile").read_text(encoding="utf-8")
    assert "FROM chalk-fineenvs-lean-base:d7056fd" in dockerfile
    assert "apt-get install" in dockerfile
    commands = "\n".join(
        line for line in dockerfile.splitlines() if not line.lstrip().startswith("#")
    )
    assert "dnf install" not in commands
    assert "chalk check" in dockerfile
    assert "COPY third_party_licenses/" in dockerfile
    assert (target / "src/environment/tasks/finite_congruence_graph/judge.py").is_file()
    assert (target / "setup_data.py").is_file()
    assert (target / "LEAN_MATH.md").is_file()
    assert (target / "third_party_licenses/landrun-MIT.txt").is_file()


def test_default_template_still_uses_its_original_base(tmp_path: Path):
    target = tmp_path / "default_env"
    create_env(target, templates=["default"], no_lock=True)

    dockerfile = (target / "Containerfile").read_text(encoding="utf-8")
    assert "FROM docker.io/library/amazonlinux:2023.8.20250818.0" in dockerfile
    assert "dnf install" in dockerfile
    assert "apt-get install" not in dockerfile


def test_download_checks_hash_before_replacing_a_file(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    script = Path(__file__).parents[1] / "src/chalk/templates/lean-math/setup_data.py"
    spec = importlib.util.spec_from_file_location("lean_setup_data", script)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    monkeypatch.setattr(module, "ROOT", tmp_path)

    def fake_urlopen(url: str, *, timeout: int) -> io.BytesIO:
        del url, timeout
        return io.BytesIO(b"new")

    monkeypatch.setattr(module, "urlopen", fake_urlopen)
    existing = tmp_path / "file.txt"
    existing.write_bytes(b"old")

    with pytest.raises(ValueError, match="expected hash"):
        module.fetch("file.txt", "file.txt", "wrong")
    assert existing.read_bytes() == b"old"

    module.fetch("file.txt", "file.txt", hashlib.sha256(b"new").hexdigest())
    assert existing.read_bytes() == b"new"


def test_prebuilt_image_is_not_used_when_download_fails(
    monkeypatch: pytest.MonkeyPatch,
):
    script = Path(__file__).parents[1] / "src/chalk/templates/lean-math/setup_data.py"
    spec = importlib.util.spec_from_file_location("lean_setup_data_image", script)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    def ignore_fetch(_source: str, _destination: str, _expected: str) -> None:
        pass

    monkeypatch.setattr(module, "fetch", ignore_fetch)
    monkeypatch.setattr(
        sys, "argv", ["setup_data.py", "--base-image", "example/image:1"]
    )
    calls: list[list[str]] = []

    def failed_pull(command: list[str], *, check: bool) -> None:
        calls.append(command)
        assert check
        raise subprocess.CalledProcessError(1, command)

    monkeypatch.setattr(module.subprocess, "run", failed_pull)
    with pytest.raises(subprocess.CalledProcessError):
        module.main()
    assert len(calls) == 1
    assert calls[0][0:2] == ["docker", "pull"]


@pytest.mark.skipif(shutil.which("bash") is None, reason="requires Bash")
def test_mathlib_download_retries_a_temporary_failure(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    script = Path(__file__).parents[1] / "src/chalk/templates/lean-math/setup_data.py"
    spec = importlib.util.spec_from_file_location("lean_setup_data_retry", script)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    monkeypatch.setattr(module, "ROOT", tmp_path)
    source = tmp_path / "intermediate_data/lean_image"
    source.mkdir(parents=True)
    for name in ("lakefile.lean", "lake-manifest.json", "pack_submission.py"):
        (source / name).write_text("")
    smoke = r"import Mathlib\n\nexample : (2 : ℕ) + 2 = 4 := by norm_num\n"
    (source / "lean_setup.sh").write_text(
        "\n".join(
            [
                "#!/usr/bin/env bash",
                "GO_VERSION=1.24.7",
                "echo before",
                "bash /opt/build/fetch_mathlib.sh",
                "echo after",
                "chmod -R a+rX /opt/elan /opt/lean-env /opt/openai-math",
                smoke,
                smoke,
                "",
            ]
        )
    )
    original = "\n".join(
        [
            "#!/usr/bin/env bash",
            "set -euo pipefail",
            "lake exe cache get first",
            "lake exe cache get second",
            "",
        ]
    )
    (source / "fetch_mathlib.sh").write_text(original)

    build = module.prepare_build_context()
    commands = tmp_path / "commands"
    commands.mkdir()
    lake = commands / "lake"
    lake.write_text(
        r"""#!/bin/sh
if [ ! -f "$CHALK_TEST_COUNTER" ]; then
  touch "$CHALK_TEST_COUNTER"
  exit 1
fi
printf "%s\n" "$*" >> "$CHALK_TEST_LOG"
"""
    )
    lake.chmod(0o755)
    sleep = commands / "sleep"
    sleep.write_text("#!/bin/sh\nexit 0\n")
    sleep.chmod(0o755)
    counter = tmp_path / "counter"
    log = tmp_path / "calls"
    env = os.environ | {
        "PATH": f"{commands}{os.pathsep}{os.environ.get('PATH', '')}",
        "CHALK_TEST_COUNTER": str(counter),
        "CHALK_TEST_LOG": str(log),
    }
    subprocess.run(["bash", str(build / "fetch_mathlib.sh")], env=env, check=True)
    assert log.read_text().splitlines() == [
        "exe cache get first",
        "exe cache get second",
    ]
    assert (source / "fetch_mathlib.sh").read_text() == original
    assert (
        "import Mathlib.Data.Finset.Lattice.Fold"
        in (build / "lean_finish_fast.sh").read_text()
    )
