# /// script
# requires-python = ">=3.12"
# dependencies = []
# ///
"""Fetch the pinned task and prepare its upstream Lean image."""

import argparse
import hashlib
import shutil
import subprocess
from pathlib import Path
from urllib.request import urlopen

ROOT = Path(__file__).resolve().parent
REVISION = "d7056fd31c19fd1a0aed0a0bc3e99026d412b2ca"
BASE_URL = f"https://huggingface.co/datasets/FineEnvs/openai-math/resolve/{REVISION}/"
TASK = "tasks/finite-congruence-graph/"
IMAGE = "chalk-fineenvs-lean-base:d7056fd"

# Upstream source, local destination, SHA-256. Reference proofs are not downloaded.
FILES = [
    (
        TASK + "environment/Dockerfile",
        "intermediate_data/lean_image/Dockerfile",
        "aba8167ea57eb438929ec48b71112a7f649ad2d0fb63917b287f5e7a0c32d89d",
    ),
    (
        TASK + "environment/fetch_mathlib.sh",
        "intermediate_data/lean_image/fetch_mathlib.sh",
        "138eacbae14a38eed0e28db80d38e243c71ff981e9cce7f25ebeaa5e31d6aee0",
    ),
    (
        TASK + "environment/lake-manifest.json",
        "intermediate_data/lean_image/lake-manifest.json",
        "37bab58d7abff5810acc399bcd9378426a4457496253a5428040a506d7752196",
    ),
    (
        TASK + "environment/lakefile.lean",
        "intermediate_data/lean_image/lakefile.lean",
        "eaf0da37b98b5d7002e72faa20e6296b5c0d5b855c471c802541484cf9afcd46",
    ),
    (
        TASK + "environment/lean_setup.sh",
        "intermediate_data/lean_image/lean_setup.sh",
        "4c7495f3b91f7e3b36c8908a4fa7b2b63d9367c20e864f1ab23a03447ba67d0d",
    ),
    (
        TASK + "environment/pack_submission.py",
        "intermediate_data/lean_image/pack_submission.py",
        "b3cd4ed6be296c47d287ab1f0fb8effc759eed6964b0f124aad80162c962fa5b",
    ),
    (
        TASK + "instruction.md",
        "shared_data/openai_math/instruction.md",
        "ec5bc6be17a94ae1cf0aac8ff0fa0045ef798c49ee68c81566731dcc816de92e",
    ),
    (
        TASK + "tests/Challenge.lean",
        "root_data/openai_math/tests/Challenge.lean",
        "2ee495def2e1228bf13df520f6c66699ec22b2cd3bc1ae7383a30957aae9f967",
    ),
    (
        TASK + "tests/task.json",
        "root_data/openai_math/tests/task.json",
        "efbf74c37a219db8c07c53307e4f0f8ef0d87193461c263e38bfef9fecbb15a3",
    ),
    (
        TASK + "tests/grade.py",
        "root_data/openai_math/tests/grade.py",
        "5df01e10cbf349ed4c81be9be1493480764b4828867d91eff1ede3ca58a4ce9d",
    ),
    (
        "LICENSE",
        "third_party/openai_math/LICENSE",
        "c71d239df91726fc519c6eb72d318ec65820627232b2f796219e87dcf35d0ab4",
    ),
    (
        "LICENSE-openai-math",
        "third_party/openai_math/LICENSE-openai-math",
        "c71d239df91726fc519c6eb72d318ec65820627232b2f796219e87dcf35d0ab4",
    ),
    (
        "NOTICE",
        "third_party/openai_math/NOTICE",
        "7e49bf81f61100f4334e9621baf475ec679ee7813de54f78e75874dac16a6f9f",
    ),
]


def fetch(source: str, destination: str, expected: str) -> None:
    path = ROOT / destination
    if path.is_file() and hashlib.sha256(path.read_bytes()).hexdigest() == expected:
        return
    with urlopen(BASE_URL + source, timeout=90) as response:
        data = response.read()
    if hashlib.sha256(data).hexdigest() != expected:
        raise ValueError(f"Downloaded file does not match its expected hash: {source}")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)
    print(f"Downloaded {source}")


def prepare_build_context() -> Path:
    """Keep the verified sources intact while making their long download resumable."""
    original = ROOT / "intermediate_data/lean_image"
    build = ROOT / "intermediate_data/lean_image_build"
    build.mkdir(parents=True, exist_ok=True)
    for name in ("lakefile.lean", "lake-manifest.json", "pack_submission.py"):
        shutil.copyfile(original / name, build / name)

    setup = (original / "lean_setup.sh").read_text(encoding="utf-8")
    marker = "bash /opt/build/fetch_mathlib.sh\n"
    header_end = "GO_VERSION=1.24.7\n"
    if setup.count(marker) != 1 or setup.count(header_end) != 1:
        raise ValueError("Unexpected upstream Lean setup; cannot prepare the build")
    before, after = setup.split(marker)
    header = setup.split(header_end)[0] + header_end
    (build / "lean_prepare.sh").write_text(before, encoding="utf-8", newline="\n")
    finish = header + "\nexport ELAN_HOME=/opt/elan PATH=/opt/elan/bin:$PATH\n" + after
    (build / "lean_finish.sh").write_text(
        finish,
        encoding="utf-8",
        newline="\n",
    )

    # The original full-library smoke test passed upstream, but importing the
    # whole library three times is expensive locally. Test this task's imports,
    # and only change permissions that are not already readable.
    full_smoke = r"import Mathlib\n\nexample : (2 : ℕ) + 2 = 4 := by norm_num\n"
    task_smoke = (
        r"import Mathlib.Data.Finset.Lattice.Fold\n"
        r"import Mathlib.Data.Fintype.Defs\n"
        r"import Mathlib.Data.Setoid.Basic\n"
        r"import Mathlib.Order.Hom.Basic\n\nexample : True := by trivial\n"
    )
    chmod = "chmod -R a+rX /opt/elan /opt/lean-env /opt/openai-math\n"
    if finish.count(full_smoke) != 2 or finish.count(chmod) != 1:
        raise ValueError(
            "Unexpected upstream Lean smoke test; cannot prepare the build"
        )
    make_readable = """python3 - <<'PY'
import os, stat
for root in ('/opt/elan', '/opt/lean-env', '/opt/openai-math'):
    for parent, dirs, files in os.walk(root, followlinks=False):
        for name in dirs + files:
            path = os.path.join(parent, name)
            mode = os.lstat(path).st_mode
            if stat.S_ISDIR(mode):
                want = stat.S_IMODE(mode) | 0o555
            elif stat.S_ISREG(mode):
                want = stat.S_IMODE(mode) | 0o444
            else:
                continue
            if want != stat.S_IMODE(mode):
                os.chmod(path, want)
PY
"""
    fast_finish = finish.replace(full_smoke, task_smoke).replace(chmod, make_readable)
    (build / "lean_finish_fast.sh").write_text(
        fast_finish, encoding="utf-8", newline="\n"
    )

    fetch_script = (original / "fetch_mathlib.sh").read_text(encoding="utf-8")
    strict_mode = "set -euo pipefail\n"
    if (
        fetch_script.count(strict_mode) != 1
        or fetch_script.count("lake exe cache get") != 2
    ):
        raise ValueError("Unexpected upstream Mathlib setup; cannot prepare the build")
    retry = """\nretry_cache() {
  local attempt
  for attempt in 1 2 3 4 5; do
    lake exe cache get "$@" && return 0
    echo "Mathlib download failed; retrying ($attempt/5)." >&2
    sleep 5
  done
  return 1
}
"""
    fetch_script = fetch_script.replace("lake exe cache get", "retry_cache")
    fetch_script = fetch_script.replace(strict_mode, strict_mode + retry)
    (build / "fetch_mathlib.sh").write_text(
        fetch_script, encoding="utf-8", newline="\n"
    )

    # The upstream image downloads the library in many batches to fit a 10 GB
    # build disk. A local build can use more temporary disk to fetch it once.
    fetch_all = (
        "#!/usr/bin/env bash\n"
        + strict_mode
        + retry
        + """
cd /opt/lean-env
retry_cache
find -H .lake/packages -path '*/.lake/build/*' \\
  \\( -name '*.c' -o -name '*.ilean' \\) -size +0 -exec truncate -s 0 {} +
rm -rf "${HOME:-/root}/.cache/mathlib"
"""
    )
    (build / "fetch_all.sh").write_text(fetch_all, encoding="utf-8", newline="\n")

    dockerfile = """# syntax=docker/dockerfile:1
FROM ubuntu:24.04@sha256:fe81560990fae86dc4743202b2cb4d3df98d0bcf949173cecef15ce1127ef852
ENV ELAN_HOME=/opt/elan \\
    PATH=/opt/elan/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin \\
    LANG=C.UTF-8 LEAN_NUM_THREADS=2
COPY lean_prepare.sh lean_finish.sh fetch_mathlib.sh lakefile.lean lake-manifest.json pack_submission.py /opt/build/
RUN bash /opt/build/lean_prepare.sh && mv /opt/lean-env/.lake/packages /opt/lean-packages-seed
COPY fetch_all.sh /opt/build/fetch_all.sh
RUN --mount=type=cache,id=chalk-openai-math-d7056fd,target=/opt/lean-package-cache,sharing=locked \\
    cp -an /opt/lean-packages-seed/. /opt/lean-package-cache/ \\
    && ln -s /opt/lean-package-cache /opt/lean-env/.lake/packages \\
    && if [ ! -f /opt/lean-package-cache/.chalk-complete-d7056fd ]; then \\
         bash /opt/build/fetch_all.sh && touch /opt/lean-package-cache/.chalk-complete-d7056fd; \\
       fi \\
    && chmod -R a+rX /opt/lean-package-cache \\
    && rm /opt/lean-env/.lake/packages \\
    && cp -a /opt/lean-package-cache /opt/lean-env/.lake/packages
COPY lean_finish_fast.sh /opt/build/lean_finish_fast.sh
RUN rm -rf /opt/lean-packages-seed && bash /opt/build/lean_finish_fast.sh
WORKDIR /workspace
"""
    (build / "Dockerfile").write_text(dockerfile, encoding="utf-8", newline="\n")
    return build


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    image_options = parser.add_mutually_exclusive_group()
    image_options.add_argument(
        "--data-only", action="store_true", help="Do not build the Lean image."
    )
    image_options.add_argument(
        "--rebuild-image", action="store_true", help="Build even if the image exists."
    )
    image_options.add_argument(
        "--base-image",
        metavar="IMAGE",
        help=(
            "Pull a trusted prebuilt Lean base image and use it instead of "
            "building from source. Prefer an image reference pinned by digest."
        ),
    )
    args = parser.parse_args()
    for source, destination, expected in FILES:
        fetch(source, destination, expected)
    if args.data_only:
        return
    if args.base_image:
        subprocess.run(
            ["docker", "pull", "--platform", "linux/amd64", args.base_image],
            check=True,
        )
        subprocess.run(["docker", "tag", args.base_image, IMAGE], check=True)
        print(f"Using {args.base_image} as {IMAGE}")
        return
    found = subprocess.run(["docker", "image", "inspect", IMAGE], capture_output=True)
    if found.returncode == 0 and not args.rebuild_image:
        print(f"Using existing image {IMAGE}")
        return
    print(
        "Building the Lean image. This can take an hour or longer.",
        flush=True,
    )
    build_context = prepare_build_context()
    subprocess.run(
        [
            "docker",
            "buildx",
            "build",
            "--resource",
            "memory=5g",
            "--resource",
            "cpu-quota=200000",
            "--resource",
            "cpu-period=100000",
            "--output",
            f"type=image,name={IMAGE},compression=uncompressed",
            str(build_context),
        ],
        check=True,
    )


if __name__ == "__main__":
    main()
