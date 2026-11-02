"""Pluggable agents for the evaluation runner.

An `Agent` produces a run's transcript one step at a time; the runner keeps the
task lifecycle (hooks, judging, artifacts, event bookkeeping). Builtin and
external agents share `MessageLoopAgent`, differing only in their
`MessageSource` -- builtin drives the litellm API loop itself, external fetches
messages from the backend (training rollouts). Fake replays env-authored
messages.
"""

from chalk.agents.agent import (
    Agent,
    CliAgentExitedError,
    EmptyTurnLimitReachedError,
    RunContext,
    TurnLimitReachedError,
)
from chalk.agents.agy import AgyAgent
from chalk.agents.backend_source import EXTERNAL_MESSAGE_TIMEOUT_S, BackendSource
from chalk.agents.builtin import BuiltinAgent
from chalk.agents.builtin_source import BuiltinSource
from chalk.agents.claude_code import ClaudeCodeAgent
from chalk.agents.cli_agent import (
    CliAgent,
    cli_agent_types,
    get_cli_agent_type,
    register_cli_agent,
)
from chalk.agents.codex import CodexAgent
from chalk.agents.external import ExternalAgent
from chalk.agents.fake_source import FakeSource
from chalk.agents.grok_build import GrokBuildAgent
from chalk.agents.message_loop import MessageLoopAgent
from chalk.agents.message_source import MessageSource
from chalk.agents.mistral_vibe import MistralVibeAgent

__all__ = [
    "AgyAgent",
    "EXTERNAL_MESSAGE_TIMEOUT_S",
    "Agent",
    "BackendSource",
    "BuiltinAgent",
    "BuiltinSource",
    "ClaudeCodeAgent",
    "CliAgent",
    "CliAgentExitedError",
    "CodexAgent",
    "EmptyTurnLimitReachedError",
    "ExternalAgent",
    "FakeSource",
    "GrokBuildAgent",
    "MessageLoopAgent",
    "MessageSource",
    "MistralVibeAgent",
    "RunContext",
    "TurnLimitReachedError",
    "cli_agent_types",
    "get_cli_agent_type",
    "register_cli_agent",
]
