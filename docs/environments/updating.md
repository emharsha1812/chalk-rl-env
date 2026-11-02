# Updating environments

Chalk saves the original rendered files in `.chalk-template-base/` and a copy of its code in `.chalk/` when it creates an environment. Keep both directories with the environment.

After installing a newer local Chalk checkout, run this outside the environment's own virtual environment:

```sh
chalk update path/to/my_env
```

Chalk compares the saved template files with the current local templates and merges their changes into your files using `git merge-file`. It then refreshes the local `.chalk/` copy and runs `uv lock`. It does not look for a Chalk release on a package registry. You can add a template with `--add-template language-toolchains`; install any template package alongside the local Chalk installation before using it.

Commit or back up your environment before updating. If changes overlap, resolve the reported conflicts. If `pyproject.toml` has a conflict, run `uv lock` in the environment after resolving it. If `.chalk/` was edited, Chalk stops to protect your changes; save those changes and restore the managed copy before updating. Paths in `do_not_recreate_if_deleted` remain deleted when requested.

If a file was present in the saved template but has been removed from the new template, the update deletes it from the environment, even if you edited it. If a new template file has the same path as a file you added yourself, the template file replaces it. Review changes against your backup after updating.

Environments made by Karotte are not automatically converted. Create a new Chalk environment and move your task code and data after reviewing imports, configuration and runtime behavior. Old serialized configurations using the legacy training model identifier remain recognized, but this does not provide a training backend.
