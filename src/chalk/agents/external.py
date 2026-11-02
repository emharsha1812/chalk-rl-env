from typing import final

from chalk.agents.backend_source import BackendSource
from chalk.agents.message_loop import MessageLoopAgent
from chalk.backend_client import BackendClient


@final
class ExternalAgent(MessageLoopAgent):
    """An external model produces the messages; chalk fetches them from the
    backend and still drives the step loop and tool execution."""

    def __init__(self, backend_client: BackendClient, run_id: str) -> None:
        super().__init__(BackendSource(backend_client, run_id))
