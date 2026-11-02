"""Helpers for detecting whether we're running inside a chalk container."""

import os
from pathlib import Path

from loguru import logger

# The sentry publishes this; no other kernel does.
GVISOR_SENTRY_PROC = "/proc/sentry-meminfo"

MOUNTS = Path("/proc/self/mounts")

_MOUNT_ESCAPES = {"\\040": " ", "\\011": "\t", "\\012": "\n", "\\134": "\\"}


def mount_points() -> list[Path]:
    """Every mount point in this namespace, in mount order."""
    try:
        table = MOUNTS.read_text()
    except OSError as e:
        logger.warning(f"Could not read {MOUNTS}: {e}")
        return []

    points: list[Path] = []
    for line in table.splitlines():
        fields = line.split(" ")
        if len(fields) < 2:
            continue
        point = fields[1]
        for escape, char in _MOUNT_ESCAPES.items():
            point = point.replace(escape, char)
        points.append(Path(point))
    return points


def is_containerized() -> bool:
    """Return True if the current process is running inside a chalk container.

    Checks the CHALK_CONTAINERIZED env var which is set by the Containerfile.
    """
    return "CHALK_CONTAINERIZED" in os.environ


def is_gvisor() -> bool:
    """Return True if this container is sandboxed by gVisor."""
    return os.path.exists(GVISOR_SENTRY_PROC)


def demoted_uid_gid() -> int | None:
    """The uid/gid tool subprocesses should drop to, or ``None``.

    Reads ``CHALK_DEMOTE_ID``. Returns ``None`` outside a container (nothing to
    demote to). Raises ``RuntimeError`` when ``CHALK_CONTAINERIZED`` is set but
    ``CHALK_DEMOTE_ID`` is not — silently skipping demotion there would let a
    misconfigured launcher run student subprocesses as root.

    The value is suitable for both a ``preexec_fn`` (see
    :func:`chalk.subprocess.make_demote_fn`) and the ``user``/``group``
    arguments of ``subprocess``/``anyio.run_process``.
    """
    demote_id = os.environ.get("CHALK_DEMOTE_ID")
    if demote_id is None:
        if is_containerized():
            raise RuntimeError(
                "CHALK_DEMOTE_ID is unset inside a chalk container (CHALK_CONTAINERIZED=1). Refusing to skip privilege demotion."
            )
        return None

    return int(demote_id)
