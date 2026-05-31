"""Shared fixtures for the Crusher-to-the-Bridge test suite."""

from __future__ import annotations

import os
import sys

import pytest


def pytest_configure(config: pytest.Config) -> None:
    """Register custom markers so pytest doesn't warn about them."""
    config.addinivalue_line("markers", "timeout: mark test with a timeout (seconds)")


REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO_ROOT)


@pytest.fixture
def repo_root() -> str:
    return REPO_ROOT
