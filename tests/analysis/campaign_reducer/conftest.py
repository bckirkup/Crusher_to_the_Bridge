"""Shared scratch space for campaign_reducer CLI tests.

``scripts/campaign analysis`` confines every CLI path argument to the
directory it was invoked from (Sonar S8707/S2083 hardening, same contract as
``picard_framework/analysis/_io.py``), so request/out paths used here must
live under the repository working tree — a scratch dir inside tests/.
"""

from __future__ import annotations

import os
import shutil
import uuid
from collections.abc import Iterator
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[3]
SCRATCH = REPO_ROOT / "tests" / "analysis" / "campaign_reducer" / ".scratch"


def rel(path: Path | str) -> str:
    """Path handed to the CLI relative to the CWD it confines to."""
    return os.path.relpath(str(path), os.getcwd())


@pytest.fixture
def scratch() -> Iterator[Path]:
    # Per-test unique dir: -n auto workers must not rmtree each other's
    # scratch while still living under the repo tree (CLI confinement).
    root = SCRATCH / f"{os.getpid()}-{uuid.uuid4().hex[:12]}"
    root.mkdir(parents=True)
    try:
        yield root
    finally:
        shutil.rmtree(root, ignore_errors=True)
