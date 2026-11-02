"""Run the pinned FineEnvs checker on Chalk's safely collected submission."""

import importlib.util
import json
import tarfile
import tempfile
from pathlib import Path

from chalk.judges.judge import Judge
from chalk.schemas.scoring import Scoring
from chalk.schemas.transcript import Transcript

from environment.paths import ROOT_DATA_DIR

TESTS = ROOT_DATA_DIR / "openai_math/tests"


def pack_submission(proof: Path, modules: Path, output: Path) -> None:
    """Only the collected Lean files go into the checker archive."""
    with tarfile.open(output, "w", format=tarfile.PAX_FORMAT) as archive:
        if proof.is_file():
            archive.add(proof, arcname="Submission.lean", recursive=False)
        if modules.is_dir():
            for path in sorted(modules.rglob("*.lean")):
                if path.is_file():
                    archive.add(
                        path,
                        arcname=f"Submission/{path.relative_to(modules).as_posix()}",
                        recursive=False,
                    )


def load_upstream_checker():
    path = TESTS / "grade.py"
    spec = importlib.util.spec_from_file_location("fineenvs_grade", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Cannot load the checker at {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class LeanProofJudge(Judge):
    def __init__(self, proof: Path, modules: Path) -> None:
        self.proof = proof
        self.modules = modules

    def evaluate(self, transcript: Transcript) -> Scoring:
        del transcript
        with tempfile.TemporaryDirectory(prefix="chalk-lean-grade-") as directory:
            root = Path(directory)
            archive = root / "submission.tar"
            pack_submission(self.proof, self.modules, archive)
            checker = load_upstream_checker()
            checker.TESTS = TESTS
            checker.SUBMISSION_TAR = archive
            checker.VERIFIER_DIR = root / "verifier"
            checker.main()
            result_path = checker.VERIFIER_DIR / "grading.json"
            if not result_path.is_file():
                raise RuntimeError("The Lean checker did not write a result")
            result = json.loads(result_path.read_text(encoding="utf-8"))
            reward = result.get("reward")
            if type(reward) is not int or reward not in (0, 1):
                raise RuntimeError(
                    f"Lean checking failed: {result.get('reason', 'no reward')}"
                )
            return Scoring(
                score=float(reward),
                metadata={
                    "checker": "FineEnvs Comparator",
                    "reason": result.get("reason", ""),
                },
                continue_task=bool(reward),
            )
