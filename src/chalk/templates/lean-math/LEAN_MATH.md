# Lean maths task

This environment contains one experimental task adapted from
[FineEnvs/openai-math](https://huggingface.co/datasets/FineEnvs/openai-math):
`finite-congruence-graph`. It asks the agent to complete a proof in Lean 4.
Chalk runs the task and returns a reward; training a model also requires a
separate training system connected to Chalk.

## Prepare and run

You need Linux or WSL 2 on an x86-64 machine, Python 3.12+, uv, Docker with
BuildKit, and a model endpoint. Run these commands in this environment's
directory:

```sh
uv sync --extra dev
uv run setup_data.py
uv run chalk run --task finite-congruence-graph --model MODEL_NAME --runtime docker
```

Set the API key required by your model before the last command. `setup_data.py`
downloads pinned task files, checks their hashes, and builds a Lean image based
on the upstream setup if it does not already exist. The image build retries
interrupted maths library downloads and keeps a build cache. It downloads the
full library in one pass, which needs more temporary disk space than the
upstream build. It also saves the local image without compression to reduce
the work needed to create it, which uses extra disk space. The source
collection reports an image of about 9 GB and a build of about an hour; allow
extra disk and time. The build requests a 5 GiB memory limit and two CPUs for
each build step; Docker's image-saving process is separate from those limits. Its task
configuration asks for 4 CPUs, 8 GB of memory, and 10 GB of working disk.
These are upstream settings, not a guarantee that the task fits every computer.
Run `uv run setup_data.py --data-only` to fetch files without building the image.

If you have a trusted prebuilt copy of the Lean base image, you can download it
instead of building that base locally:

```sh
uv run setup_data.py --base-image IMAGE_REFERENCE
```

Replace `IMAGE_REFERENCE` with the image name, preferably pinned with its
`@sha256:...` digest. Docker pulls the Linux x86-64 image and tags it for this
template. The later Chalk image build still installs Chalk and the task files.
Only use an image from a source you trust; the script verifies the separately
downloaded task files, not the contents of an arbitrary image.

For a check without a model or API key, create `run_config.json` containing:

```json
{
  "run_id": "lean-smoke",
  "task_id": "finite-congruence-graph",
  "model": "fake",
  "use_fake_model": true,
  "transcript_file": "out/lean-smoke.json"
}
```

Then run `uv run chalk run --config run_config.json --runtime docker --no-ui`.
The scripted agent submits the unfinished proof, which should receive 0. A 0 is
an expected result for that check. It does not show that a valid proof passes.

## Scoring and limits

The task's original statement, Lean toolchain, Comparator configuration, and
checker are downloaded from a fixed dataset revision. Chalk stops the student
processes and copies the submission to a protected location before invoking the
checker. The checker builds a fresh Lean project and checks the exact statement,
permitted axioms, and proof. Checker failures without a verdict become run errors.
Chalk applies its own safe file-collection rules before the upstream checker;
these include a limit on the number of files and rejection of links and special
files. This can reject a submission that exceeds Chalk's limits even if the
upstream task would accept the file collection.

The upstream Harbor task runs its checker in a **separate sandbox**. This Chalk
adaptation runs the checker after the student in the **same sandbox**, using
separate users and the upstream checker's own restrictions. The two security
boundaries are not identical. Do not assume that a test on one proves the
security of the other. Resource limits and network restrictions also depend on
the selected Chalk runtime and its configuration. This task asks Chalk to limit
the student's memory to at most 7 GiB. When Chalk reports an existing file
limit, the task keeps it at 10 GiB or lower. Lower existing limits are kept.
In local Docker these may be monitored limits
rather than limits enforced directly by the operating system; they do not cap
the separate grader user. Check `chalk check confinement` for the selected
runtime. The dataset is experimental and its authors recommend reviewing
successful proofs before relying on them.

The selected task was the fastest by the published reference-proof checking time
in the dataset manifest. That measurement used the authors' infrastructure; it
is not a measurement of this Chalk adaptation or of other parts of the run.

## Attribution

The task, checker and image setup come from FineEnvs/openai-math. The Lean
statement comes from OpenAI's openai/math. Their Apache 2.0 licenses and notice
are downloaded to `third_party/openai_math/` by `setup_data.py`. The source is
fixed to dataset revision `d7056fd31c19fd1a0aed0a0bc3e99026d412b2ca`.
