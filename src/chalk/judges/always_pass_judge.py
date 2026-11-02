from typing import override

from chalk.judges.judge import Judge
from chalk.schemas.scoring import Scoring
from chalk.schemas.transcript import Transcript


class AlwaysPassJudge(Judge):
    @override
    def evaluate(self, transcript: Transcript) -> Scoring:
        return Scoring(score=1.0, metadata={}, continue_task=True)
