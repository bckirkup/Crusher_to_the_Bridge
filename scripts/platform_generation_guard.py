"""Shared overwrite guards for committed platform generators."""

from __future__ import annotations

import os


def ensure_output_absent(
    path: str | os.PathLike[str],
    *,
    description: str,
    overwrite: bool = False,
    dry_run: bool = False,
) -> str:
    """Return *path* unless it exists and overwrite was not requested."""
    resolved = os.fspath(path)
    if dry_run or overwrite or not os.path.exists(resolved):
        return resolved
    raise FileExistsError(
        f"Refusing to overwrite existing {description}: {resolved}. "
        "Committed platform data is authoritative; pass --overwrite to "
        "regenerate deliberately."
    )


def ensure_platform_output_dir(
    platform_dir: str | os.PathLike[str],
    *,
    platform_id: str,
    overwrite: bool = False,
    dry_run: bool = False,
) -> str:
    """Return a platform output directory after the committed-data guard."""
    return ensure_output_absent(
        platform_dir,
        description=f"platform directory for {platform_id!r}",
        overwrite=overwrite,
        dry_run=dry_run,
    )
