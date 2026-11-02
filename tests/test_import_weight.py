"""Importing the CLI or chalk's schemas must not load an LLM client or an MCP server."""

import subprocess
import sys

import pytest

HEAVY_MODULES = ["litellm", "anthropic", "openai", "mcp.server", "modal"]


@pytest.mark.parametrize(
    "module",
    [
        "chalk",
        "chalk.cli",
        "chalk.schemas.transcript",
        "chalk.schemas.evaluation_run_config",
        "chalk.model_catalog",
        "chalk.transcript_markdown",
    ],
)
def test_importing_chalk_loads_no_llm_client(module: str):
    result = subprocess.run(
        [
            sys.executable,
            "-c",
            f"import sys, {module}; "
            + f"print(' '.join(m for m in {HEAVY_MODULES!r} if m in sys.modules))",
        ],
        capture_output=True,
        text=True,
        check=True,
    )
    assert result.stdout.strip() == ""
