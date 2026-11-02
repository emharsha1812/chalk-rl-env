<p align="left"><img src="docs/assets/chalk-logo.png" alt="Chalk" width="430"></p>

# Chalk

**RL environments for coding and mathematical reasoning.**

Chalk is an open-source framework for writing tasks, running agents in isolated
containers or virtual machines, scoring their work, and recording transcripts.
The existing templates include a small Python example, an experimental
language-toolchains template, and an experimental Lean proof task adapted from
FineEnvs/openai-math. This release does not add a training system.

## Install locally

Install [Python 3.12+](https://www.python.org/) and [uv](https://docs.astral.sh/uv/).
Use Linux or macOS; on Windows, run the commands in WSL. Clone this repository
and install Chalk from the checkout:

```sh
git clone https://github.com/emharsha1812/chalk-rl-env.git
cd chalk-rl-env
uv tool install .
chalk --version
chalk --help
```

The Python distribution is called `chalk-rl-env`; `chalk` is the Python import
and command. See
[installation](docs/getting-started/installation.md) for runtime requirements.

To create the optional Lean maths environment, run
`chalk create-env my_lean_env --template lean-math`. See the [task guide](docs/environments/lean-math.md)
and its generated `LEAN_MATH.md`. It needs a separate image build and
substantially more memory and disk space. The [GPU machine guide](docs/running/small-model-vm.md)
shows how to connect a small model.

## Create an environment

```sh
chalk create-env my_env
cd my_env
uv sync --extra dev
uv run setup_data.py
uv run chalk tasks list
```

The generated environment contains a local `.chalk/` copy and an explicit path
dependency. It does not download an unrelated `chalk` package. Its example task
asks an agent to find its Python executable and write its Python version to a file.
To run it, configure a supported runtime and model as described in the
[quick start](docs/getting-started/quick-start.md). The dashboard remains available
with `uv run chalk dashboard out/` after a run.

## Website and documentation

```sh
uv run --group docs python scripts/build_sites.py
uv run --group docs python scripts/preview_sites.py
```

Open `http://127.0.0.1:8000/` for the website and
`http://127.0.0.1:8000/docs/` for the documentation. Their source trees and
build outputs are separate. See [site configuration](docs/extending/developing-chalk.md#website-and-documentation) for deployment settings.

## Development

Run `uv sync --extra dev --group docs`, then `just fix`, `just lint`, and
`just test` where supported. Some runtime and isolation checks require Linux,
root privileges, a container runtime, or external services; see the relevant
test and runtime documentation before running them.

## Credits and licenses

Chalk is derived from Karotte by Preference Model. See the
[upstream repository](https://github.com/preferencemodel/karotte).
The framework is under the [MIT license](LICENSE); the templates in
[`src/chalk/templates/`](src/chalk/templates/) use the
[MIT No Attribution license](src/chalk/templates/LICENSE).

Built images contain third-party software under its own licenses, including
Amazon Linux 2023. The optional language-toolchains template can include GPL,
LGPL, EPL and other licensed software. Check the licenses of the components
selected before distributing an image.
