# Lean maths

The experimental `lean-math` template adds one proof task adapted from
[FineEnvs/openai-math](https://huggingface.co/datasets/FineEnvs/openai-math).
It uses Lean 4 and the upstream Comparator checker.
The agent completes a proof; a passing proof earns 1 and an incomplete or
incorrect proof earns 0.

```sh
chalk create-env my_lean_env --template lean-math
cd my_lean_env
uv sync --extra dev
uv run setup_data.py
```

The image is large and takes time to build. See `LEAN_MATH.md` in the generated
environment for requirements, an API-free check, attribution, and the difference
between Chalk's scoring isolation and the upstream Harbor task.

## Check the task without a model

Create a file named `smoke-config.json` in `my_lean_env`:

```json
{
  "run_id": "lean-smoke",
  "task_id": "finite-congruence-graph",
  "model": "fake",
  "use_fake_model": true,
  "transcript_file": "out/lean-smoke.json"
}
```

Then run:

```sh
uv run chalk run --config smoke-config.json --runtime docker --no-ui
```

This uses a scripted agent and needs no model or API key. It submits an
unfinished proof, so a score of 0 is expected. The check does not show that a
valid proof passes or that a model can solve the task.

## Use a model

Configure your model's API key, then replace `MODEL_NAME` with a supported
model name:

```sh
uv run chalk run --task finite-congruence-graph --model MODEL_NAME --runtime docker
```

If you have a trusted prebuilt Lean base image, `uv run setup_data.py
--base-image IMAGE_REFERENCE` pulls it instead of building that base locally.
The later Chalk image build still installs Chalk and the task. The base image is
separate from the model and does not contain model weights.

For an example using a small model on a GPU machine, see [Running a small model
on a GPU machine](../running/small-model-vm.md). Chalk runs and scores the task;
a separate training system is needed to update model weights with reinforcement
learning.
