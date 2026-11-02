# Run a small model on a GPU machine

This example connects Chalk's experimental Lean task to a separately hosted
model. It uses [Qwen2.5-1.5B-Instruct](https://huggingface.co/Qwen/Qwen2.5-1.5B-Instruct),
a 1.5-billion-parameter model, as a starting point. You can choose another model
if its server supports the same chat and tool-calling API.

The model and task run in separate Docker containers. The model uses the GPU;
the Lean task uses the machine's CPUs, memory, and disk. The model attempts the
task and the checker gives a score. This is an evaluation run, not model training.

This guide has not yet been tested on a GPU machine. Follow the model and vLLM
documentation for your hardware, and try a short run before committing to a
longer job. The proof is difficult; a score of 0 is a normal possible result.

## Before you start

Use an x86-64 Linux machine with an NVIDIA GPU, a compatible driver, Docker
with BuildKit, the NVIDIA Container Toolkit, Python 3.12+, and uv. A full GPU VM
with permission to run Docker is suitable; some hosted notebook containers cannot
run their own Docker service. For example, see [Jarvislabs VM documentation](https://docs.jarvislabs.ai/vm/).

Check `nvidia-smi` and `docker info` on the machine first. The Lean base image
is about 10 GB and builds can take an hour or longer. The model, its server,
the final Chalk image, and build files need additional disk and memory. GPU
memory needs depend on the model, server version, and context length. We have
not measured a minimum VM size for the full setup.

As a starting estimate for this single-model evaluation, consider a VM with one
NVIDIA GPU with around 16 GB of GPU memory, 32 GB of system memory, and 100 GB
of free disk. This is a planning estimate, not a tested requirement. Other
models, longer conversations, concurrent runs, or training may need different
resources.

## Create the task

From a Chalk checkout that includes the `lean-math` template:

```sh
uv tool install .
chalk create-env my_lean_env --template lean-math
cd my_lean_env
uv sync --extra dev
uv run setup_data.py
```

The last command downloads the task files and builds the Lean base image. The
generated `LEAN_MATH.md` explains the alternative for a trusted prebuilt image
and how to test the task without a model.

## Start a model server

This example uses the official [vLLM Docker image](https://docs.vllm.ai/en/v0.17.0/deployment/docker/).
The server is attached to Docker's default bridge network without publishing a
port on the VM. Other containers on that bridge can still reach it. The first
run downloads the model and image.

```sh
mkdir -p "$HOME/.cache/huggingface"
docker run -d --name chalk-model --gpus all --shm-size=4g \
  -v "$HOME/.cache/huggingface:/root/.cache/huggingface" \
  vllm/vllm-openai:v0.17.0 \
  --model Qwen/Qwen2.5-1.5B-Instruct \
  --host 0.0.0.0 --port 8000 --max-model-len 8192 \
  --enable-auto-tool-choice --tool-call-parser hermes
docker logs -f chalk-model
```

Wait for the server to report that it is ready. Press Ctrl-C to stop following
the logs; that does not stop the server. vLLM documents the
[`hermes` tool parser for Qwen2.5](https://docs.vllm.ai/en/v0.17.0/features/tool_calling/).
If you use a different model, check its tool parser and license.

## Run the task

From `my_lean_env`, get the model container's address on the Docker bridge:

```sh
MODEL_IP=$(docker inspect -f '{{range .NetworkSettings.Networks}}{{.IPAddress}}{{end}}' chalk-model)
echo "$MODEL_IP"
```

Create a small run configuration:

```json
{
  "run_id": "small-lean-01",
  "task_id": "finite-congruence-graph",
  "model": "hosted_vllm/Qwen/Qwen2.5-1.5B-Instruct",
  "max_output_tokens": 512,
  "turn_limit": 20,
  "step_time_limit_seconds": 600,
  "on_step_time_limit": "score",
  "transcript_file": "out/small-lean-01.json"
}
```

Save it as `small-model-run.json`, then run:

```sh
uv run chalk run --config small-model-run.json \
  --runtime docker --proxy "http://$MODEL_IP:8000" --no-ui
```

`max_output_tokens` limits each response; the prompt and earlier messages must
also fit inside the server's context window. Reaching the turn limit ends the
run with an error. The time limit scores the current submission. Review the
transcript and any errors as well as the reward.

When finished, stop the model server with `docker stop chalk-model`. Delete or
retain the VM and its storage according to your provider's billing rules.
