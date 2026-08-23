"""Tests for the Docker build context exclusions."""

from __future__ import annotations

import fnmatch
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
DOCKERIGNORE = REPO_ROOT / ".dockerignore"


def _ignored_by_dockerignore(path: str) -> bool:
    ignored = False
    for raw_pattern in DOCKERIGNORE.read_text(encoding="utf-8").splitlines():
        pattern = raw_pattern.strip()
        if not pattern or pattern.startswith("#"):
            continue
        negated = pattern.startswith("!")
        if negated:
            pattern = pattern[1:]
        matches = fnmatch.fnmatchcase(path, pattern)
        if pattern.endswith("/*"):
            matches = path.startswith(pattern[:-1])
        if matches:
            ignored = not negated
    return ignored


def test_dockerignore_scopes_telemetry_buffer_to_importable_modules() -> None:
    excluded = (
        "telemetry_buffer/mega_cruise_campaign/run.zip",
        "telemetry_buffer/extracted_cdc_data/records.json",
        "telemetry_buffer/stray.zip",
    )
    included = (
        "telemetry_buffer/__init__.py",
        "telemetry_buffer/agent_axes.py",
        "telemetry_buffer/schema.py",
        "engines/sim_clock.py",
    )

    assert all(_ignored_by_dockerignore(path) for path in excluded)
    assert not any(_ignored_by_dockerignore(path) for path in included)
