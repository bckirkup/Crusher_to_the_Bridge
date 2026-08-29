"""Guards for the EC2 scale-to-zero Batch pathways under deploy/aws/.

These lock the properties that are expensive to discover in AWS: a job
definition that silently keeps Fargate keys, a compute environment that no
longer scales to zero, or a simulation container with no budget timeout.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

AWS_DIR = Path(__file__).resolve().parent.parent / "deploy" / "aws"
JOB_DEFS = sorted(AWS_DIR.glob("batch_job_definition*.json"))
PATHWAYS = json.loads((AWS_DIR / "instance_pathways.json").read_text(encoding="utf-8"))

# Batch rejects a sixth rule outright.
MAX_EVALUATE_ON_EXIT = 5
# No unmonitored container runs longer than a day.
MAX_ATTEMPT_SECONDS = 86400
FARGATE_ONLY_KEYS = ("fargatePlatformConfiguration", "networkConfiguration", "ephemeralStorage")


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


@pytest.mark.parametrize("path", JOB_DEFS, ids=lambda p: p.name)
def test_job_definition_targets_ec2(path: Path) -> None:
    assert _load(path)["platformCapabilities"] == ["EC2"]


@pytest.mark.parametrize("path", JOB_DEFS, ids=lambda p: p.name)
def test_job_definition_drops_fargate_only_keys(path: Path) -> None:
    container = _load(path)["containerProperties"]
    assert [key for key in FARGATE_ONLY_KEYS if key in container] == []


@pytest.mark.parametrize("path", JOB_DEFS, ids=lambda p: p.name)
def test_job_definition_sizes_shared_memory(path: Path) -> None:
    shm = _load(path)["containerProperties"]["linuxParameters"]["sharedMemorySize"]
    assert shm >= 512


@pytest.mark.parametrize("path", JOB_DEFS, ids=lambda p: p.name)
def test_job_definition_has_bounded_timeout(path: Path) -> None:
    seconds = _load(path)["timeout"]["attemptDurationSeconds"]
    assert 0 < seconds <= MAX_ATTEMPT_SECONDS


@pytest.mark.parametrize("path", JOB_DEFS, ids=lambda p: p.name)
def test_job_definition_retries_host_loss_first(path: Path) -> None:
    rules = _load(path)["retryStrategy"]["evaluateOnExit"]
    assert len(rules) <= MAX_EVALUATE_ON_EXIT
    assert rules[0] == {"onStatusReason": "Host EC2*", "action": "retry"}


@pytest.mark.parametrize("pathway", [k for k in PATHWAYS if not k.startswith("_")])
def test_pathway_offers_diverse_instance_types(pathway: str) -> None:
    families = {
        arch: types
        for arch, types in PATHWAYS[pathway].items()
        if not arch.startswith("_")
    }
    assert "x86_64" in families
    for arch, types in families.items():
        assert len(types) >= 3, f"{pathway}/{arch} spot pool is too narrow"
        assert len({t.split(".")[0] for t in types}) >= 2, f"{pathway}/{arch} is single-family"


def test_memory_pathway_uses_memory_optimised_families() -> None:
    for types in ("x86_64", "arm64"):
        assert all(t.startswith("r") for t in PATHWAYS["analysis_memory"][types])


def test_compute_pathways_use_compute_optimised_families() -> None:
    for pathway in ("abm_campaign", "analysis_compute"):
        assert all(t.startswith("c") for t in PATHWAYS[pathway]["x86_64"])


@pytest.mark.parametrize("capacity,expected", [("spot", "SPOT"), ("on_demand", "EC2")])
def test_compute_environment_scales_to_zero(capacity: str, expected: str) -> None:
    out = subprocess.run(  # noqa: S603 - fixed argv, no shell
        [
            sys.executable,
            str(AWS_DIR / "ensure_batch_pathways.py"),
            "--pathway",
            "analysis_compute",
            "--queue",
            "picard-analysis-queue",
            "--capacity",
            capacity,
            "--dry-run",
        ],
        capture_output=True,
        text=True,
        check=True,
    )
    resources = json.loads(out.stdout)["computeResources"]
    assert resources["type"] == expected
    assert resources["minvCpus"] == 0
    assert resources["desiredvCpus"] == 0
