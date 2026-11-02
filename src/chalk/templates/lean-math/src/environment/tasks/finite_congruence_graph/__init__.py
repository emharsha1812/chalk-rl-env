"""A Chalk version of one FineEnvs/openai-math Lean task."""

import os
import shutil
from pathlib import Path
from typing import final

from chalk import FileLimit, Step, Task, get_resource_limits, limit_resources

from environment import STUDENT_UID
from environment.paths import SHARED_DATA_DIR, STUDENT_WORKDIR
from environment.submissions import collect_submission
from environment.system_prompts import get_system_prompt
from environment.tasks.finite_congruence_graph.judge import LeanProofJudge

LEAN_ENV = Path("/opt/lean-env")
GIB = 1024**3


def set_lean_limits() -> dict[str, str]:
    """Keep the student's limits within the space needed for this task."""
    current = get_resource_limits()
    memory_cap = 7 * GIB
    if current.memory_bytes is not None:
        memory_cap = min(memory_cap, current.memory_bytes)
    try:
        machine_memory = os.sysconf("SC_PHYS_PAGES") * os.sysconf("SC_PAGE_SIZE")
    except (AttributeError, OSError, ValueError):
        machine_memory = None
    if machine_memory is not None and machine_memory > GIB:
        memory_cap = min(memory_cap, machine_memory - GIB)
    contracts = limit_resources(memory_bytes=memory_cap)

    if current.file is not None:
        current_bytes = current.file.bytes
        file_cap = (
            min(current_bytes, 10 * GIB) if current_bytes is not None else 10 * GIB
        )
        contracts.update(
            limit_resources(
                file=FileLimit(
                    path=current.file.path,
                    bytes=file_cap,
                    count=current.file.count,
                )
            )
        )
    return {name: str(contract) for name, contract in contracts.items()}


@final
class FiniteCongruenceGraph(Task):
    id = "finite-congruence-graph"

    @property
    def system_prompt(self) -> str:
        return get_system_prompt(self.config.model, self.config.extra_config)

    @property
    def tools(self) -> list[str]:
        return ["bash", "view_lines_in_file", "replace_in_file"]

    @property
    def steps(self):
        return [ProofStep(config=self.config)]

    def pre_hook(self):
        contracts = set_lean_limits()
        # Reuse the pinned, root-owned library; the student can write only the
        # project and its own build products, never the library itself.
        for name in ("lakefile.lean", "lake-manifest.json", "lean-toolchain"):
            dest = STUDENT_WORKDIR / name
            shutil.copyfile(LEAN_ENV / name, dest)
            os.chown(dest, STUDENT_UID, STUDENT_UID)
        lake_dir = STUDENT_WORKDIR / ".lake"
        lake_dir.mkdir(exist_ok=True)
        os.chown(lake_dir, STUDENT_UID, STUDENT_UID)
        (lake_dir / "packages").symlink_to(LEAN_ENV / ".lake/packages")
        return {"source": "FineEnvs/openai-math", "task": self.id, "limits": contracts}


class ProofStep(Step):
    saved_submissions: tuple[Path, ...] = ()

    @property
    def submission_paths(self) -> tuple[Path, ...]:
        return (STUDENT_WORKDIR / "Submission.lean", STUDENT_WORKDIR / "Submission")

    @property
    def instructions(self) -> str:
        text = (SHARED_DATA_DIR / "openai_math/instruction.md").read_text(
            encoding="utf-8"
        )
        text = text.replace("/workspace", str(STUDENT_WORKDIR))
        text = text.replace(
            "The sandbox has 4 CPUs and 8 GB of memory; `LEAN_NUM_THREADS=3` keeps `lake build` to three\n"
            "  parallel jobs.",
            "`LEAN_NUM_THREADS=2` limits `lake build` to two parallel jobs.",
        )
        text = text.replace(
            "There is no internet access. OpenAI's own proofs are not installed.",
            "OpenAI's own proofs are not installed. Network access depends on "
            "the selected Chalk runtime and its settings.",
        )
        return text.replace(
            "copied to a fresh machine and",
            "copied into a fresh Lean project after the student's processes stop, and",
        )

    def pre_scoring_hook(self):
        self.saved_submissions = collect_submission(
            self.config,
            self.submission_paths,
            save_submission_kwargs={
                "max_file_bytes": 64 << 20,
                "max_total_bytes": 768 << 20,
            },
        )

    @property
    def judge(self):
        if len(self.saved_submissions) != 2:
            raise RuntimeError("The student's submission has not been collected")
        return LeanProofJudge(*self.saved_submissions)
