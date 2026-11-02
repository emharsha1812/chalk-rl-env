# Installation

## Requirements

- Python 3.12 or newer.
- [uv](https://docs.astral.sh/uv/).
- Linux or macOS for the Chalk command. On Windows, use a Linux environment such as WSL; the native Windows command is not currently supported.
- A runtime to run environments in.
  See [below](#runtime-prerequisites).

## Install Chalk locally

Clone the public repository and install from the checkout:

```sh
git clone https://github.com/emharsha1812/chalk-rl-env.git
cd chalk-rl-env
uv tool install .
chalk --version
chalk --help
```

The local distribution is `chalk-rl-env`. The command and Python import are `chalk`. This project has not specified a public package registry destination. Use a local checkout instead of `uv tool install chalk`.

## Runtime prerequisites

`chalk run` and `chalk build` pick a runtime based on your system or you can select one via the `--runtime` option.

| Platform                                | Default runtime   | What you need                                                                                                           |
| --------------------------------------- | ----------------- | ----------------------------------------------------------------------------------------------------------------------- |
| macOS 26+ on Apple silicon              | `apple-container` | Apple [`container`](https://github.com/apple/container/releases) 1.4.1 or newer, started with `container system start`. |
| Linux x86_64 or aarch64 with `/dev/kvm` | `firecracker`     | Membership in the `kvm` group, docker with buildx (it builds the image), and `pasta` (package `passt`).                 |
| Other supported Linux or macOS systems  | `docker`          | docker with [buildx](https://github.com/docker/buildx#installing).                                                      |

You can always explicitly use docker with `--runtime docker`, or podman with `--runtime podman`, instead.
Ubuntu's `docker.io` package lacks buildx; install `docker-buildx` too.

If the default VM runtime isn't set up, Chalk stops before the run and tells you what's missing.

See [Runtimes](../running/runtimes.md) for the full setup of each runtime and what it gives the student.

## Next steps

- [Quick start](quick-start.md): create an environment and run its example task.
- [Concepts](concepts.md): what environments, tasks, steps and judges are.
