"""Regression tests for bundled-hull resolution in the paired diagnostic."""

from __future__ import annotations

import math
import sys
from pathlib import Path
from typing import Any

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from tools.diag import contam_paired_diagnostic as paired  # noqa: E402
from tools.diag.contam_envelope_leak_enumeration import bundled_hulls  # noqa: E402


def test_parser_accepts_every_committed_contam_bundle() -> None:
    for hull in bundled_hulls():
        args = paired._parse_args(["--hull", hull, "--source", "Witness"])
        assert args.hull == [hull]


def test_parser_rejects_a_platform_without_a_committed_bundle() -> None:
    bundled = set(bundled_hulls())
    platform_dirs = {
        path.name for path in (REPO_ROOT / "data" / "platforms").iterdir() if path.is_dir()
    }
    missing = sorted(platform_dirs - bundled)
    if not missing:
        pytest.skip("every platform has a committed Contam bundle")
    with pytest.raises(SystemExit) as exc_info:
        paired._parse_args(["--hull", missing[0]])
    assert exc_info.value.code == 2


def test_unmapped_bundled_hull_requires_an_explicit_source() -> None:
    spatial, _airflow = paired._load_platform("midway_cv41")
    with pytest.raises(ValueError, match="pass --source"):
        paired._sources_for("midway_cv41", spatial, None)
    assert paired._sources_for("midway_cv41", spatial, ["Flight_Deck"]) == ["Flight_Deck"]


def test_run_matrix_emits_paired_rows_for_a_newly_bundled_hull(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Lock hull/source/lane plumbing; the field solve itself needs ContamX."""
    monkeypatch.setattr(paired, "_contamx_binary", lambda _lanes: "unused")

    real_lane_engine = paired._lane_engine

    def lane_engine(
        hull: str,
        lane: str,
        spatial: dict[str, Any],
        airflow: dict[str, Any],
        binary: str | None,
        envelope_leak_mode: str = paired.ENVELOPE_LEAK_BOUNDARY_SINK,
    ) -> Any:
        if lane == "commissioned":
            return paired._native_engine(spatial, airflow)
        return real_lane_engine(hull, lane, spatial, airflow, binary, envelope_leak_mode)

    monkeypatch.setattr(paired, "_lane_engine", lane_engine)
    args = paired._parse_args([
        "--hull", "midway_cv41",
        "--lane", "native",
        "--lane", "commissioned",
        "--source", "Flight_Deck",
        "--timing", "pulse_t0",
    ])
    payload = paired._run_matrix(args)

    assert payload["meta"]["hulls"] == ["midway_cv41"]
    assert {(cell["hull"], cell["lane"]) for cell in payload["cells"]} == {
        ("midway_cv41", "native"),
        ("midway_cv41", "commissioned"),
    }
    assert all(cell["source_zone"] == "Flight_Deck" for cell in payload["cells"])
    assert all(cell["timing"] == "pulse_t0" for cell in payload["cells"])
    assert len(payload["cells"]) == 2
    assert all(math.isfinite(cell["whole_hull_material_time_h"]) for cell in payload["cells"])
