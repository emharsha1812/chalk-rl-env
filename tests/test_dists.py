import subprocess
import tarfile
import zipfile
from pathlib import Path

REPO = Path(__file__).parent.parent


def test_packaged_metadata_and_license_match_the_project():
    for name in ("pyproject.toml", "README.md", "LICENSE"):
        assert (REPO / "src/chalk" / name).read_bytes() == (REPO / name).read_bytes()


def _built_metadata(tmp_path: Path, project: str) -> list[tuple[str, set[str]]]:
    """Builds a wheel and sdist of `project`, returning each one's metadata and file names."""
    out = tmp_path / "out"
    subprocess.run(
        [
            "uv",
            "build",
            "--quiet",
            "--no-create-gitignore",
            str(REPO / project),
            "-o",
            str(out),
        ],
        check=True,
    )
    [wheel] = out.glob("*.whl")
    [sdist] = out.glob("*.tar.gz")
    with zipfile.ZipFile(wheel) as zf:
        names = set(zf.namelist())
        [metadata] = [n for n in names if n.endswith(".dist-info/METADATA")]
        built = [(zf.read(metadata).decode(), names)]
    with tarfile.open(sdist) as tf:
        names = set(tf.getnames())
        [pkg_info] = [n for n in names if n.count("/") == 1 and n.endswith("PKG-INFO")]
        member = tf.extractfile(pkg_info)
        assert member is not None
        built.append((member.read().decode(), names))
    return built


def test_chalk_ships_the_mit_license(tmp_path: Path):
    for metadata, names in _built_metadata(tmp_path, "."):
        assert "License-Expression: MIT AND MIT-0" in metadata.splitlines()
        assert "License-File: LICENSE" in metadata.splitlines()
        assert "License-File: src/chalk/templates/LICENSE" in metadata.splitlines()
        assert any(n.endswith("/LICENSE") for n in names)
        assert any(n.endswith("chalk/templates/LICENSE") for n in names)
        assert not any(
            line.startswith("Project-URL: Repository,")
            for line in metadata.splitlines()
        )


def test_chalk_ships_the_readme(tmp_path: Path):
    for metadata, _ in _built_metadata(tmp_path, "."):
        assert "Description-Content-Type: text/markdown" in metadata.splitlines()


def test_chalk_wheel_carries_what_vendoring_copies(tmp_path: Path):
    [(_, names), _] = _built_metadata(tmp_path, ".")
    assert {
        "chalk/pyproject.toml",
        "chalk/LICENSE",
        "chalk/README.md",
        "chalk/templates/LICENSE",
        "chalk/assets/chalk-symbol.png",
    } <= names
