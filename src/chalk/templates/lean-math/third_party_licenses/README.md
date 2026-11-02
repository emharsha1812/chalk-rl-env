# Lean tool licenses

These files accompany binaries built by the pinned upstream image setup:

- `comparator-Apache-2.0.txt`: [Comparator](https://github.com/leanprover/comparator/tree/d03acab154d269c06e60e4de7e4cc85deebff94b), Apache 2.0. The upstream image setup changes Comparator to pass `LEAN_NUM_THREADS` to its sandbox.
- `lean4export-Apache-2.0.txt`: [lean4export](https://github.com/leanprover/lean4export/tree/076e8e57707e813375e8f9da8bf989799ace9680), Apache 2.0.
- `landrun-MIT.txt`: [landrun](https://github.com/zouuup/landrun/tree/811cfff51ceaf3d9843708aa6d22e9b84ccac8b4), MIT.

The landrun build uses Go 1.24.7 and the Go modules go-landlock 0.9.0,
urfave/cli 3.6.2, golang.org/x/sys 0.40.0, and libcap/psx 1.2.77. Their
license and patent files are included here. The psx source includes copyright
notices for Andrew G. Morgan, 2019–2021 and 2024–2025; psx offers a choice
between BSD 3-clause and GPL 2.0.

The pinned FineEnvs setup installs these tools and identifies their licenses in
its own notice. The image also contains other software under its own licenses.
