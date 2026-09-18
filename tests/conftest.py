"""Shared fixtures for the Crusher-to-the-Bridge test suite."""

from __future__ import annotations

import os
import sys
import zlib

import pytest

pytest_plugins = ["pytester"]


def pytest_addoption(parser: pytest.Parser) -> None:
    group = parser.getgroup("ci-shard", "split the collected suite across CI jobs")
    group.addoption(
        "--ci-shard-count", type=int, default=1,
        help="number of CI jobs the collected test files are split across",
    )
    group.addoption(
        "--ci-shard-index", type=int, default=0,
        help="which of the --ci-shard-count slices this job runs (0-based)",
    )


def pytest_configure(config: pytest.Config) -> None:
    """Register custom markers so pytest doesn't warn about them."""
    config.addinivalue_line("markers", "timeout: mark test with a timeout (seconds)")
    worker = os.environ.get("PYTEST_XDIST_WORKER")
    if worker and not os.environ.get("CTTB_TELEMETRY_DIR"):
        worker_dir = os.path.join(REPO_ROOT, "telemetry_buffer", ".xdist", worker)
        os.makedirs(worker_dir, exist_ok=True)
        os.environ["CTTB_TELEMETRY_DIR"] = worker_dir
    count = config.getoption("--ci-shard-count")
    index = config.getoption("--ci-shard-index")
    if count < 1 or not 0 <= index < count:
        raise pytest.UsageError(
            f"--ci-shard-index must be in [0, --ci-shard-count); got {index} of {count}",
        )


def shard_of(module_relpath: str, shard_count: int) -> int:
    """Map a test module (path relative to the rootdir) to a shard.

    Splitting by module, not by test, keeps module-scoped fixtures on one job.
    The slot is a checksum of the relative path, so every job computes the same
    assignment with no shared state (the union of all shards is exactly the
    full selection) and adding a module never moves the others.
    """
    return zlib.crc32(module_relpath.replace(os.sep, "/").encode("utf-8")) % shard_count


def pytest_collection_modifyitems(config: pytest.Config, items: list[pytest.Item]) -> None:
    count = config.getoption("--ci-shard-count")
    if count == 1:
        return
    index = config.getoption("--ci-shard-index")
    root = str(config.rootpath)
    keep: list[pytest.Item] = []
    dropped: list[pytest.Item] = []
    for item in items:
        relpath = os.path.relpath(str(item.path), root)
        (keep if shard_of(relpath, count) == index else dropped).append(item)
    items[:] = keep
    config.hook.pytest_deselected(items=dropped)


REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO_ROOT)


@pytest.fixture
def repo_root() -> str:
    return REPO_ROOT
