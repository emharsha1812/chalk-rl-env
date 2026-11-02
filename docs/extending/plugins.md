# Plugins

A Python package can extend Chalk through [entry points](https://packaging.python.org/en/latest/specifications/entry-points/).
Chalk reads them from every package installed next to it.
Templates have their own entry point, which [Template packages](template-packages.md) describes.

| Entry point                        | Points at                                          | Effect                                                                                                                |
| ---------------------------------- | -------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------- |
| `chalk.cli`                      | a Typer app                                        | Adds a subcommand named after the entry point.                                                                        |
| `chalk.run_config_preprocessors` | `f(config) -> config`                              | Rewrites the run config before a run.                                                                                 |
| `chalk.default_proxy_url`        | a string                                           | The default for `chalk run --proxy`.                                                                                |
| `chalk.harness_secret_env`       | a list of names                                    | Environment variables hidden from the student.                                                                        |
| `chalk.platform_tooling_dirs`    | a list of paths                                    | Directories where a platform mounts its own tooling into every container. They are hidden from graded toolchain runs. |
| `chalk.age_delay_exemptions`     | a list of package names                            | Extra packages exempt from uv's `exclude-newer` delay.                                                                |
| `chalk.update_migrations`        | an object with `prepare` and `migrate`     | During `chalk update`, moves environments made by an older release to the current names.                            |
| `chalk.default_hardware`         | a string                                           | The `required_hardware` of tasks that don't set one.                                                                  |
| `chalk.hardware_limits`          | `f(hardware)` returning `HardwareLimits` or `None` | The memory, disk and CPUs a sandbox on that hardware gets.                                                            |
| `chalk.container_run_args`       | `f(task, runtime) -> list[str]`                    | Extra arguments for the container engine's `run` command.                                                             |
| `chalk.cli_agents`               | a `CliAgent` subclass                              | Adds a [CLI agent](../running/run-config.md) named after the class's `name`.                                          |

## Registering a plugin

Declare entry points in your package's `pyproject.toml`.
Each value has the form `module:attribute`.
Chalk loads the attribute and uses it as described in the table above.

```toml
[project.entry-points."chalk.harness_secret_env"]
my_plugin = "my_plugin:HARNESS_SECRETS"

[project.entry-points."chalk.run_config_preprocessors"]
my_plugin = "my_plugin:preprocess"
```

```python
from chalk.schemas.evaluation_run_config import EvaluationRunConfig

HARNESS_SECRETS = ["MY_SERVICE_TOKEN"]


def preprocess(config: EvaluationRunConfig) -> EvaluationRunConfig:
    return config.model_copy(update={"save_artifacts": False})
```

Install the package into the same environment as Chalk.
For an environment's venv, add it as a dependency.
For a tool install from the local checkout, use `uv tool install . --with my-plugin`.

## Order and merging

If only one value can win, Chalk sorts the entry points by name and takes the first one that loads.
If the values add up, Chalk uses all of them.

| Entry point                                                                                   | When several are installed                                                                                              |
| --------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------- |
| `chalk.cli`                                                                                 | Each one adds its subcommand.                                                                                           |
| `chalk.run_config_preprocessors`                                                            | All of them run, in entry point name order. Each one gets the previous one's output.                                    |
| `chalk.default_proxy_url`                                                                   | The first by name wins.                                                                                                 |
| `chalk.harness_secret_env`, `chalk.platform_tooling_dirs`, `chalk.age_delay_exemptions` | Chalk merges the lists.                                                                                               |
| `chalk.update_migrations`                                                                   | All of them run in installation order (not sorted by name). |
| `chalk.default_hardware`, `chalk.hardware_limits`                                         | The first by name wins.                                                                                                 |
| `chalk.container_run_args`                                                                  | All of them run, in entry point name order, and Chalk concatenates their arguments.                                   |
| `chalk.cli_agents`                                                                          | Each one adds its agent. For two agents with the same `name`, the first by entry point name wins.                       |

## When a plugin fails to load

If a plugin fails to load, Chalk skips it with a warning and carries on without it.
Run config preprocessors are the exception.
If one of them fails to load or raises an exception, the run fails.

## The entry points

### `chalk.cli`

The attribute is a `typer.Typer` app.
It becomes the subcommand `chalk <entry point name>`.
If an entry point has the same name as a built-in command, Chalk ignores it with a warning.
Plugins never replace Chalk's own commands.

```toml
[project.entry-points."chalk.cli"]
mytool = "my_plugin.cli:app"
```

### `chalk.run_config_preprocessors`

The attribute is a function that takes the parsed `EvaluationRunConfig` and returns one.
`chalk run` calls it right after it parses `--config`, before it picks the runtime or loads the task.
See [Run config](../running/run-config.md).

### `chalk.default_proxy_url`

The attribute is a string.
It's the URL that `chalk run` sends model calls to when you don't pass `--proxy`.
If you pass `--no-proxy`, Chalk ignores it.
See [Run config](../running/run-config.md) for how proxies work.

### `chalk.harness_secret_env`

The attribute is a list of environment variable names.
Chalk leaves these variables out of the environment it gives the student's processes, such as `bash` tool calls and CLI agents.
Use it for credentials that the harness needs but the student must not see.
Chalk hides only the names you list, because tasks sometimes hand the student a secret on purpose.

### `chalk.platform_tooling_dirs`

The attribute is a list of directories where the platform running Chalk mounts its own tooling into every container.
During builds and graded runs, the [`language-toolchains`](../environments/language-toolchains.md) template covers each of them with an empty, read-only tmpfs.
That way a submission can't load an interpreter from them.
Paths that don't exist are ignored.

### `chalk.age_delay_exemptions`

The attribute is a list of package names.
When Chalk runs uv outside a project (for `chalk update` and `post_create.py`), it applies a 7-day `exclude-newer` delay.
Packages in these lists are exempt from that delay. Chalk itself is installed from a local source and does not need a registry exemption.
Inside an environment, the delay comes from the environment's own `pyproject.toml`.

### `chalk.update_migrations`

The attribute is an object with two methods.
`chalk update` calls them as follows:

| Method                                            | Called                                                                                          |
| ------------------------------------------------- | ----------------------------------------------------------------------------------------------- |
| `prepare(project_dir)`                            | Before Chalk reads the environment's manifest.                                                |
| `migrate(baseline_dir, project_dir, old_version)` | Before the merge, on a copy of the saved baseline and on the environment.                           |

Use it when a release renames things that the 3-way merge in [Updating environments](../environments/updating.md) can't follow on its own.

### `chalk.default_hardware`

The attribute is a string.
It's the hardware name for tasks that don't set `required_hardware`.
Chalk itself doesn't know any hardware names.
Plugins define them.
See [Tasks and steps](../tasks/tasks-and-steps.md) for the task property.

### `chalk.hardware_limits`

The attribute is a function that takes a hardware name and returns a `HardwareLimits`.
For hardware it doesn't know, it returns `None`.
`HardwareLimits` sets the sandbox's memory, disk and CPUs, and marks hardware that a VM can't provide, such as a GPU.
Tasks on such hardware run under docker by default, and VM runtimes refuse them.

```python
from chalk.hardware import HardwareLimits

GIB = 1024**3


def hardware_limits(hardware: str) -> HardwareLimits | None:
    if hardware == "cpu-large":
        return HardwareLimits(memory_bytes=32 * GIB, disk_bytes=100 * GIB, cpus=8)
    if hardware == "gpu":
        return HardwareLimits(passthrough=True)
    return None
```

A hardware name that no plugin knows is not an error.
Chalk just uses its defaults.
Without an answer from a plugin, a VM gets 2 CPUs and 4 GiB for the sandbox.
On other runtimes, the sandbox's memory comes from `CHALK_SANDBOX_MEMORY_BYTES`.
If that variable isn't set, it comes from the sandbox's cgroup limit or RAM.
The student gets this amount minus 1 GiB.
If the variable isn't set and there's no working cgroup, the student has no memory limit.
See [Runtimes](../running/runtimes.md) and [Student resources](../running/student-resources.md).

### `chalk.container_run_args`

The attribute is a function that takes the task and the runtime name (`docker`, `podman`, `nerdctl`, ...).
It returns extra arguments for the engine's `run` command.
You can use it to pass devices through, for example.
Chalk adds these arguments for `docker`, `podman`, `docker:gvisor` and `nerdctl`.

`chalk run` calls every hook before it launches a container.
If a hook raises an exception, Chalk refuses to launch and shows the exception's message.

```python
def container_run_args(task, runtime: str) -> list[str]:
    if task.required_hardware != "gpu":
        return []
    if runtime != "docker":
        raise RuntimeError("GPU tasks need --runtime docker")
    return ["--gpus", "all"]
```

### `chalk.cli_agents`

The attribute is a subclass of `CliAgent`.
It becomes available as `chalk run --agent <name>`, where `<name>` is the class's `name`, and in `chalk agents list`.
If its `name` is one of Chalk's own agents, Chalk ignores it with a warning.
The package must be installed in the environment's image, since the agent runs there.

```toml
[project.entry-points."chalk.cli_agents"]
my_agent = "my_plugin.agent:MyAgent"
```

A `CliAgent` can override `_step_artifacts()` to return files that Chalk saves as artifacts after each step.
