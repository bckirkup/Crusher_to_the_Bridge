"""The decision runtime's inputs must reach every image, or refuse to run.

A container that cannot find the class-interaction matrix, the diffusion
configuration or the global-health timeline used to fall back to empty
defaults, so the same run spec scored one model in a checkout and a different
one on Batch. These tests hold both halves of the repair: the files travel in
the build context, and an absent file is an error rather than a default.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from decision_engine.agent_profile import default_bundle_path  # noqa: E402
from decision_engine.information.diffusion import InformationDiffusionEngine  # noqa: E402
from decision_engine.intelligence import default_timeline_path  # noqa: E402
from decision_engine.runtime import DecisionRuntime  # noqa: E402
from decision_engine.social.class_interactions import ClassInteractionMatrix  # noqa: E402

DEFAULT_INPUT_PATHS = (
    default_bundle_path(str(REPO_ROOT)),
    default_timeline_path(str(REPO_ROOT)),
    ClassInteractionMatrix.default_path(str(REPO_ROOT)),
    InformationDiffusionEngine.default_path(str(REPO_ROOT)),
)

IMAGES = (
    REPO_ROOT / "Dockerfile",
    REPO_ROOT / "deploy" / "aws" / "Dockerfile.design",
    REPO_ROOT / "deploy" / "aws" / "Dockerfile.analysis",
)


def _copied_sources(dockerfile: Path) -> list[str]:
    sources: list[str] = []
    for line in dockerfile.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped.startswith("COPY ") or "--from=" in stripped:
            continue
        parts = stripped.split()[1:-1]
        sources.extend(parts)
    return sources


@pytest.mark.parametrize("path", DEFAULT_INPUT_PATHS)
def test_every_default_runtime_input_exists_in_the_checkout(path: str) -> None:
    assert os.path.isfile(path), path


@pytest.mark.parametrize("dockerfile", IMAGES, ids=lambda p: p.name)
@pytest.mark.parametrize("path", DEFAULT_INPUT_PATHS)
def test_every_image_running_the_model_carries_its_runtime_inputs(
    dockerfile: Path,
    path: str,
) -> None:
    relative = Path(path).relative_to(REPO_ROOT)
    sources = _copied_sources(dockerfile)
    assert any(
        str(relative) == source or str(relative).startswith(source.rstrip("/") + "/")
        for source in sources
    ), f"{dockerfile.name} does not copy {relative}"


def test_a_missing_runtime_input_is_refused_rather_than_defaulted(
    tmp_path: Path,
) -> None:
    with pytest.raises(FileNotFoundError, match="decision runtime input missing"):
        DecisionRuntime._required_input(
            str(tmp_path), None, ClassInteractionMatrix.default_path,
        )


def test_a_present_runtime_input_resolves_to_its_absolute_path() -> None:
    resolved = DecisionRuntime._required_input(
        str(REPO_ROOT), None, ClassInteractionMatrix.default_path,
    )
    assert resolved == ClassInteractionMatrix.default_path(str(REPO_ROOT))
