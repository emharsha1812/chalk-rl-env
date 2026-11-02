# Run from a folder or repo

`chalk run` runs the environment in the current folder.
Give it a source to run another environment, without cloning it or cd-ing into it first:

```sh
chalk run ./my-env --task my-task --model anthropic/claude-opus-5-5
chalk run https://github.com/org/repo --task my-task --model anthropic/claude-opus-5-5
chalk run https://github.com/org/repo/tree/main/envs/my-env --task my-task --model anthropic/claude-opus-5-5
chalk run "git+ssh://git@example.com/org/repo.git@v1.2#subdirectory=envs/my-env" --task my-task --model anthropic/claude-opus-5-5
```

A source is one of:

- A folder.
- A GitHub repo URL, or the URL of a folder in it as GitHub shows it (`.../tree/<ref>/<path>`).
- `git+<url>@<ref>#subdirectory=<path>`, as pip and uv write it, for any git host. The ref and subdirectory are optional.

Without a ref, chalk fetches the repo's default branch.
It fetches only the environment's folder, into `~/.cache/chalk/sources`, and reuses a commit it has fetched before.
Git does the fetching, so private repos work with your SSH keys or git credential helper.
When a GitHub URL fails over HTTPS for lack of credentials, chalk tries SSH.

## What happens

1. chalk fetches the environment, if it's remote.
2. Without `--task`, it runs the environment's task if it has only one, and lists the tasks to pick from otherwise.
3. It runs the environment's `setup_data.py`, if it has one (see [Data and dependencies](../tasks/data-and-dependencies.md)).
4. It runs `uv run chalk run` in the environment's folder, with your other options.

The run uses the chalk version the environment pins in its `uv.lock`, not the one you started it with.

The transcript, `--config`, `--mount` and `--build-secret` paths are relative to the folder you run the command from, not the environment's.

!!! warning

    Running an environment runs its code on your machine, outside the sandbox: `setup_data.py`, and its task definitions when chalk loads them.
    Only run sources you trust.

## Scripts before the build

`--pre-build SCRIPT` replaces `setup_data.py` with the scripts you name.
Repeat it to run several, in order.
Each one runs with `uv run SCRIPT` in the environment's folder, and the run stops if one fails.
`--no-pre-build` runs none, and `--dev` skips them, since it builds no image.
