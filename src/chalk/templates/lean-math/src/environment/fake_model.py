"""Scripted examples for checking the maths task without a model API."""

import json

from chalk import EvaluationRunConfig
from chalk.schemas import ChatCompletionMessageToolCall, Function, Message

from environment.paths import STUDENT_DATA_DIR


def get_messages(config: EvaluationRunConfig) -> list[Message]:
    if config.task_id != "finite-congruence-graph":
        return [
            Message(role="assistant", content="path: /workdir/.venv/bin/python"),
            Message(
                role="assistant",
                content="I will save the Python version.",
                tool_calls=[
                    ChatCompletionMessageToolCall(
                        id="python_version",
                        type="function",
                        function=Function(
                            name="bash",
                            arguments=json.dumps(
                                {
                                    "command": f"echo '3.12.11' > {STUDENT_DATA_DIR}/python_version.txt"
                                }
                            ),
                        ),
                    )
                ],
            ),
            Message(role="assistant", content="Done."),
        ]
    # Leave the original `sorry` in place: the checker must reject it.
    command = "cp /opt/openai-math/challenges/FiniteCongruenceGraph.lean /workdir/Submission.lean"
    return [
        Message(
            role="assistant",
            content="I will submit the incomplete proof.",
            tool_calls=[
                ChatCompletionMessageToolCall(
                    id="copy_challenge",
                    type="function",
                    function=Function(
                        name="bash", arguments=json.dumps({"command": command})
                    ),
                )
            ],
        ),
        Message(role="assistant", content="Done."),
    ]
