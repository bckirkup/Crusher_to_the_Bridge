"""Tests for tools/noro_diag/route_attribution_readout.py.

Synthetic per-seed cells only -- no simulation is run. Each cell is the
shape ``per_host_dose_challenge.py`` writes: ``transmission.acquisitions``
rows with ``acquired_particles_by_route``/``dominant_route`` and a
``transmission.route_attribution.recomputed`` block.
"""

from __future__ import annotations

import gzip
import json
import shutil
import sys
import tempfile
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from tools.noro_diag import route_attribution_readout as readout  # noqa: E402


def _acq(
    agent_id: int, dominant: str, ledger: dict[str, float] | None = None,
) -> dict:
    return {
        "agent_id": agent_id,
        "epoch": 10,
        "dose_read": 1.5,
        "dominant_route": dominant,
        "acquired_particles_by_route": ledger if ledger is not None else {
            dominant: 1.0,
        },
    }


def _cell(
    seed: int,
    acquisitions: list[dict] | None = None,
    secondaries: int | None = None,
    fomite_share: float = 0.0,
) -> dict:
    acq = acquisitions if acquisitions is not None else []
    return {
        "seed": seed,
        "transmission": {
            "secondaries": len(acq) if secondaries is None else secondaries,
            "acquisitions": acq,
            "route_attribution": {
                "engine_tally": {},
                "recomputed": {
                    "infections_by_dominant_route": {},
                    "infection_dose_share_by_route": {"fomite": fomite_share},
                },
            },
        },
    }


def test_wilson_interval_bounds_and_edges() -> None:
    assert readout.wilson_interval(0, 0) == {
        "p": 0.0, "lo": 0.0, "hi": 0.0, "n": 0, "k": 0,
    }
    w = readout.wilson_interval(31, 43)
    assert w["p"] == pytest.approx(31 / 43)
    assert 0.0 <= w["lo"] < w["p"] < w["hi"] <= 1.0
    all_true = readout.wilson_interval(43, 43)
    assert all_true["p"] == pytest.approx(1.0)
    assert all_true["hi"] == pytest.approx(1.0)


def test_sign_test_pvalue() -> None:
    assert readout.sign_test_pvalue(0, 0) == pytest.approx(1.0)
    assert readout.sign_test_pvalue(1, 4) == pytest.approx(0.375)
    assert readout.sign_test_pvalue(5, 0) == pytest.approx(0.0625)


def test_jaccard_vacuous_and_partial() -> None:
    assert readout.jaccard(set(), set()) == (1.0, True)
    assert readout.jaccard({1}, {1}) == (1.0, False)
    value, vacuous = readout.jaccard({1, 2}, {2, 3})
    assert value == pytest.approx(1.0 / 3.0)
    assert vacuous is False


def test_route_composition_tallies_dominant_routes() -> None:
    cells = {
        1: _cell(1, [_acq(1, "fomite"), _acq(2, "fomite")]),
        2: _cell(2, [_acq(3, "emesis_aerosol")]),
        3: _cell(3),
    }
    comp = readout._route_composition(cells)
    assert comp["total_secondaries"] == 3
    assert comp["informative_seeds"] == 2
    assert comp["dominant_route_counts"] == {
        "fomite": 2, "emesis_aerosol": 1,
    }
    assert comp["fomite_share"]["k"] == 2
    assert comp["fomite_share"]["n"] == 3


def test_paired_deltas_and_sign_test() -> None:
    base = {1: _cell(1, [_acq(1, "fomite")]), 2: _cell(2)}
    arm = {1: _cell(1), 2: _cell(2), 3: _cell(3)}
    delta = readout._paired_deltas(base, arm)
    assert delta["seeds"] == [1, 2]
    assert delta["deltas"] == [-1, 0]
    assert delta["negative"] == 1
    assert delta["zero"] == 1
    assert delta["median"] == pytest.approx(-0.5)


def test_fomite_set_jaccard_flags_differing_and_vacuous() -> None:
    base = {
        1: _cell(1, [_acq(1, "fomite"), _acq(2, "emesis_aerosol")]),
        2: _cell(2),
    }
    arm = {
        1: _cell(1, [_acq(2, "emesis_aerosol")]),
        2: _cell(2),
    }
    result = readout._fomite_set_jaccard(base, arm)
    assert result["median_jaccard"] == pytest.approx(0.5)
    assert result["vacuous_seeds"] == [2]
    assert result["fomite_set_differs"] == [1]
    assert result["infected_set_differs"] == [1]


def test_dose_share_deltas_on_informative_seeds() -> None:
    base = {1: _cell(1, [_acq(1, "fomite")], fomite_share=1.0),
            2: _cell(2)}
    arm = {1: _cell(1, [_acq(1, "fomite")], fomite_share=0.4),
           2: _cell(2)}
    result = readout._dose_share_deltas(base, arm)
    assert result["informative_seeds"] == [1]
    assert result["fomite_share_delta_by_seed"][1] == pytest.approx(-0.6)
    assert result["median_delta"] == pytest.approx(-0.6)


def test_discordant_acquisitions_split_by_kind() -> None:
    base = {
        1: _cell(1, [_acq(1, "fomite"), _acq(2, "droplet")]),
    }
    arm = {
        1: _cell(1, [_acq(2, "fomite"), _acq(9, "fomite")]),
    }
    disc = readout._discordant(base, arm)
    assert disc["n_one_arm_only"] == 2  # agents 1 and 9
    assert disc["n_route_differs"] == 1  # agent 2 droplet -> fomite
    assert disc["dominant_route_differs"][0]["declared_route"] == "fomite"


def test_disagg_witness_event_sets_and_ulp() -> None:
    base_acq = _acq(1, "fomite")
    same = _acq(1, "fomite")
    drift = _acq(1, "fomite")
    drift["dose_read"] = 1.5000000000000002
    moved = _acq(1, "fomite")
    moved["epoch"] = 11
    base = {
        1: _cell(1, [base_acq]),
        2: _cell(2, [base_acq]),
        3: _cell(3, [base_acq]),
    }
    pooled = {
        1: _cell(1, [same]),
        2: _cell(2, [drift]),
        3: _cell(3, [moved]),
    }
    witness = readout._disagg_witness(base, pooled)
    assert witness["seeds_checked"] == 3
    assert witness["mismatched_seeds"] == [3]
    assert witness["ulp_drift_seeds"] == [2]


def _write_cell(directory: Path, tag: str, cell: dict) -> None:
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / (
        f"per_host_dose_challenge_{tag}_seed{cell['seed']}.json.gz"
    )
    with gzip.open(path, "wt", encoding="utf-8") as handle:
        json.dump(cell, handle)


def test_readout_end_to_end_over_gz_cells(tmp_path: Path) -> None:
    for seed in (7, 8):
        _write_cell(tmp_path / "a", "per_surface_areal", _cell(
            seed, [_acq(1, "fomite")],
        ))
        _write_cell(tmp_path / "d", "per_surface_declared", _cell(
            seed, [_acq(1, "fomite")],
        ))
        _write_cell(tmp_path / "p", "pooled", _cell(
            seed, [_acq(1, "fomite")],
        ))
    result = readout.readout(
        tmp_path / "a", tmp_path / "d", tmp_path / "p",
    )
    assert result["n_seeds_areal"] == 2
    assert result["route_composition"]["areal"]["total_secondaries"] == 2
    assert result["disagg01_witness"]["mismatched_seeds"] == []
    assert result["discordant_acquisitions"]["n_one_arm_only"] == 0


def test_safe_path_refuses_outside() -> None:
    with pytest.raises(ValueError, match="outside the allowed directory"):
        readout._safe_path("/etc/hostname")


def test_print_and_main_write_output(tmp_path: Path) -> None:
    for tag, d in (("per_surface_areal", "a"), ("per_surface_declared", "d"),
                   ("pooled", "p")):
        _write_cell(tmp_path / d, tag, _cell(1, [_acq(1, "fomite")]))
    scratch = Path(tempfile.mkdtemp(dir=REPO_ROOT))
    try:
        rc = readout.main([
            "--areal-dir", str(tmp_path / "a"),
            "--declared-dir", str(tmp_path / "d"),
            "--pooled-dir", str(tmp_path / "p"),
            "--out", str(scratch),
        ])
        assert rc == 0
        written = scratch / "route_attribution_readout.json"
        assert written.exists()
        payload = json.loads(written.read_text())
        assert payload["n_seeds_areal"] == 1
    finally:
        shutil.rmtree(scratch)
