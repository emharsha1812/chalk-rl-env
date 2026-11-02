import shlex
import subprocess
from pathlib import Path
from typing import Annotated

import typer


def create_env(
    output_dir: Annotated[
        Path,
        typer.Argument(
            help="Directory where the environment should be created.",
        ),
    ],
    template: Annotated[
        list[str] | None,
        typer.Option(
            help="""Templates to use for environment creation.
            Can specify multiple templates to be stacked on top of each other.
            For example, `--template default --template custom` overlay the
            `custom` template on top of the `default` template.

            Defaults to the `default` template if none is specified.
            """,
        ),
    ] = None,
    agent: Annotated[
        list[str] | None,
        typer.Option(
            help="""CLI agent(s) to bake into the image (e.g. `--agent mistral-vibe`).
            Repeatable. Recorded in the manifest; the installed chalk pins each
            agent's version. Defaults to none (builtin/external only).
            """,
        ),
    ] = None,
    vendor_chalk: Annotated[
        bool,
        typer.Option(
            "--vendor-chalk",
            help="Copy the local Chalk source into the environment (the default).",
        ),
    ] = False,
    no_lock: Annotated[
        bool,
        typer.Option(
            "--no-lock",
            hidden=True,
            help="Skip running uv lock after creation.",
        ),
    ] = False,
) -> None:
    """Create a new environment in the output directory."""
    from chalk.create_env import create_env as create_env_func

    templates = template or ["default"]

    try:
        create_env_func(
            templates=templates,
            output_dir=output_dir,
            agents=agent or [],
            vendor_chalk=vendor_chalk,
            no_lock=no_lock,
        )
    except subprocess.CalledProcessError as e:
        cmd = e.cmd if isinstance(e.cmd, str) else shlex.join(map(str, e.cmd))
        typer.secho(
            f"`{cmd}` failed with exit code {e.returncode}.", fg="red", err=True
        )
        raise typer.Exit(1)

    steps = [f"cd {shlex.quote(str(output_dir))}", "uv sync --extra dev"]
    if (output_dir / "setup_data.py").is_file():
        steps.append("uv run setup_data.py")
    steps += [
        "uv run chalk tasks list",
        "export ANTHROPIC_API_KEY=...",
        "uv run chalk run --task <task-id> --model anthropic/claude-opus-5-5",
    ]
    typer.secho("\nNext steps:", bold=True)
    for step in steps:
        typer.echo(f"  {step}")
