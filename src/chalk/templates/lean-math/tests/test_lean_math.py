"""Checks of the task's submission handling, without a Lean installation."""

import json
import tarfile
from pathlib import Path

import pytest
from chalk import EvaluationRunConfig, FileLimit
from chalk.confinement import ResourceLimits
from chalk.schemas.transcript import Transcript

from environment.tasks import finite_congruence_graph as task
from environment.tasks.finite_congruence_graph import judge


def test_lean_limits_keep_lower_existing_caps(monkeypatch):
    existing = ResourceLimits(
        memory_bytes=3 * task.GIB,
        process_count=200,
        file=FileLimit(path=("/workdir", "/tmp"), bytes=2 * task.GIB, count=500),
    )
    monkeypatch.setattr(task, "get_resource_limits", lambda: existing)
    calls = []

    def apply_limit(**kwargs):
        calls.append(kwargs)
        return {next(iter(kwargs)): "detected_and_reaped"}

    monkeypatch.setattr(task, "limit_resources", apply_limit)
    task.set_lean_limits()
    assert calls[0]["memory_bytes"] <= 3 * task.GIB
    assert calls[1]["file"] == existing.file


def test_instructions_match_the_chalk_runtime(tmp_path: Path, monkeypatch):
    source = tmp_path / "openai_math/instruction.md"
    source.parent.mkdir()
    source.write_text(
        "The sandbox has 4 CPUs and 8 GB of memory; `LEAN_NUM_THREADS=3` keeps `lake build` to three\n"
        "  parallel jobs.\n"
        "There is no internet access. OpenAI's own proofs are not installed.\n"
        "copied to a fresh machine and checked at /workspace/Submission.lean\n"
    )
    monkeypatch.setattr(task, "SHARED_DATA_DIR", tmp_path)
    instructions = task.ProofStep(
        config=EvaluationRunConfig(
            run_id="test", task_id=task.FiniteCongruenceGraph.id, model="fake"
        )
    ).instructions
    assert "LEAN_NUM_THREADS=2" in instructions
    assert "4 CPUs and 8 GB" not in instructions
    assert "Network access depends" in instructions
    assert "fresh machine" not in instructions
    assert str(task.STUDENT_WORKDIR / "Submission.lean") in instructions


def test_only_lean_files_are_sent_to_the_checker(tmp_path: Path):
    proof = tmp_path / "Submission.lean"
    proof.write_text("import Submission.Helper\n")
    modules = tmp_path / "Submission"
    modules.mkdir()
    (modules / "Helper.lean").write_text("example : True := trivial\n")
    (modules / "notes.txt").write_text("not a Lean file")
    archive = tmp_path / "submission.tar"

    judge.pack_submission(proof, modules, archive)

    with tarfile.open(archive) as result:
        assert result.getnames() == ["Submission.lean", "Submission/Helper.lean"]


@pytest.mark.parametrize("reward", [0, 1])
def test_checker_reward_reaches_chalk(tmp_path: Path, monkeypatch, reward: int):
    class Checker:
        def main(self):
            self.VERIFIER_DIR.mkdir()
            (self.VERIFIER_DIR / "grading.json").write_text(
                json.dumps({"reward": reward, "reason": "test result"})
            )

    monkeypatch.setattr(judge, "load_upstream_checker", Checker)
    result = judge.LeanProofJudge(
        tmp_path / "missing", tmp_path / "missing-dir"
    ).evaluate(Transcript(run_id="test"))
    assert result.score == reward
    assert result.continue_task is bool(reward)


def test_checker_error_is_not_reported_as_a_zero(tmp_path: Path, monkeypatch):
    class Checker:
        def main(self):
            self.VERIFIER_DIR.mkdir()
            (self.VERIFIER_DIR / "grading.json").write_text(
                json.dumps({"reward": None, "reason": "checker unavailable"})
            )

    monkeypatch.setattr(judge, "load_upstream_checker", Checker)
    with pytest.raises(RuntimeError, match="checker unavailable"):
        judge.LeanProofJudge(tmp_path / "missing", tmp_path / "missing-dir").evaluate(
            Transcript(run_id="test")
        )
