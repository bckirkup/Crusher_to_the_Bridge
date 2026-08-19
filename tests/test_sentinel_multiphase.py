"""The multiphase staircase: one fit per phase, port channels only as a check.

Contract tests on the phase machinery — which channels a phase retains, what a
comparison excludes, and the invariant that no port signal can reach the
shipboard likelihood. The estimator itself is tested in
``test_sentinel_fleet_fit``; here the fit is a short reference-walker smoke or a
stub, because the question is the staging, not the posterior.

Paths stay inside the repository: ``picard_framework.analysis._io`` confines
reads and writes to the process CWD, so a scratch directory under the repo
replaces ``tmp_path``.
"""

from __future__ import annotations

import csv
import json
import os
import shutil
import sys
from typing import Any, Iterator

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from picard_framework.analysis._fit_exit import EXIT_NO_POSTERIOR
from picard_framework.analysis.sentinel import multiphase
from picard_framework.analysis.sentinel.multiphase import (
    CHANNEL_SIGNALS,
    DEFAULT_PHASES,
    PHASE_CLINICAL_ONLY,
    PHASE_CLINICAL_WASTEWATER,
    PHASE_FULL,
    PHASE_PORT_WBE,
    SurveillancePhase,
    compare_channel,
    pearson,
    phase_by_name,
    resolve_phases,
    run_multiphase,
    spearman,
    truth_comparison,
)
from picard_framework.analysis.sentinel.port_health import (
    CHANNEL_LAB,
    CHANNEL_SYNDROMIC,
    CHANNEL_WBE,
    CHANNELS,
)
from picard_framework.analysis.sentinel.port_ledger import build_port_ledger

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(REPO, "picard_framework", "analysis", "sentinel", "data")
FLEET_MANIFEST = os.path.join(DATA, "example_fleet.json")
PATHOGEN = "norovirus"

# Four ports spanning the scan's hazard ladder, so a correlation has something
# to correlate: background, moderate, high, and a hazard-free control.
HAZARDS = {
    "USMIA": 1e-4,
    "MXCZM": 1e-3,
    "ESPMI": 5e-3,
    "DKCPH": 1.5e-2,
}


@pytest.fixture
def scratch() -> Iterator[str]:
    path = os.path.join(REPO, "tmp_multiphase_test")
    shutil.rmtree(path, ignore_errors=True)
    os.makedirs(path, exist_ok=True)
    yield path
    shutil.rmtree(path, ignore_errors=True)


def _ledger(days: int = 14, seed: int = 909) -> dict[str, Any]:
    return build_port_ledger(
        port_hazards=HAZARDS,
        pathogen=PATHOGEN,
        n_days=days,
        seed=seed,
        genotype="GII.4",
    )


def _write_ledger(directory: str, **kwargs: Any) -> str:
    path = os.path.join(directory, "ledger.json")
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(_ledger(**kwargs), fh)
    return path


def _hazards_like_truth() -> dict[str, float]:
    """Inferred hazards that happen to equal the truth: a perfect-recovery stub."""
    return dict(HAZARDS)


# --- phase definitions ---------------------------------------------------


def test_default_staircase_adds_one_channel_at_a_time():
    names = [p.name for p in DEFAULT_PHASES]
    assert names[0] == PHASE_CLINICAL_ONLY
    assert names[1] == PHASE_CLINICAL_WASTEWATER
    assert names[-1] == PHASE_FULL
    widths = [len(p.port_channels) for p in DEFAULT_PHASES]
    assert widths == [0, 0, 1, 1, 1, 1, len(CHANNELS)]


def test_clinical_only_is_the_no_wastewater_baseline():
    baseline = phase_by_name(PHASE_CLINICAL_ONLY)
    assert baseline.wastewater is False
    assert baseline.port_channels == ()
    assert phase_by_name(PHASE_CLINICAL_WASTEWATER).wastewater is True


def test_every_channel_has_a_numeric_port_summary():
    assert set(CHANNEL_SIGNALS) == set(CHANNELS)


def test_unknown_phase_and_unknown_channel_are_refused():
    with pytest.raises(ValueError, match="unknown phase"):
        phase_by_name("clinical_telepathy")
    with pytest.raises(ValueError, match="unknown channels"):
        SurveillancePhase(name="bad", wastewater=True, port_channels=("aura",))


def test_resolve_phases_honours_order_and_capability_override():
    chosen = resolve_phases([PHASE_FULL, PHASE_CLINICAL_ONLY])
    assert [p.name for p in chosen] == [PHASE_FULL, PHASE_CLINICAL_ONLY]
    ignored = resolve_phases([PHASE_FULL], respect_capability=False)
    assert ignored[0].respect_capability is False
    assert phase_by_name(PHASE_FULL).respect_capability is True


# --- correlation helpers -------------------------------------------------


def test_correlations_recover_direction_and_bounds():
    xs = [1.0, 2.0, 3.0, 4.0]
    rising = pearson(xs, [2.0, 4.1, 5.9, 8.2])
    falling = pearson(xs, [8.0, 6.0, 4.1, 1.9])
    assert rising is not None
    assert falling is not None
    assert 0.9 < rising <= 1.0
    assert -1.0 <= falling < -0.9


def test_spearman_ignores_the_scale_pearson_cares_about():
    xs = [1.0, 2.0, 3.0, 4.0, 5.0]
    ys = [1.0, 2.0, 4.0, 8.0, 1000.0]
    rho = spearman(xs, ys)
    r = pearson(xs, ys)
    assert rho == pytest.approx(1.0)
    assert r is not None
    assert r < 0.95


def test_correlation_refuses_tiny_samples_and_flat_series():
    assert pearson([1.0, 2.0], [1.0, 2.0]) is None
    assert spearman([1.0, 2.0], [1.0, 2.0]) is None
    assert pearson([1.0, 1.0, 1.0], [1.0, 2.0, 3.0]) is None


def test_ties_share_a_rank_rather_than_inventing_an_order():
    assert multiphase._ranks([5.0, 5.0, 9.0]) == [1.5, 1.5, 3.0]


# --- comparisons ---------------------------------------------------------


def _table(ledger: dict[str, Any], channels: Any) -> list[dict[str, Any]]:
    from picard_framework.analysis.sentinel.port_ledger import (
        ablate_ledger,
        port_signal_table,
    )

    return port_signal_table(ablate_ledger(ledger, channels=channels))


def test_syndromic_comparison_tracks_the_hazard_ladder():
    table = _table(_ledger(), (CHANNEL_SYNDROMIC,))
    comparison = compare_channel(_hazards_like_truth(), table, CHANNEL_SYNDROMIC)
    assert comparison.n_ports >= 3
    assert comparison.spearman_rho == pytest.approx(1.0)


def test_ablated_channel_excludes_ports_instead_of_scoring_them_zero():
    table = _table(_ledger(), (CHANNEL_SYNDROMIC,))
    comparison = compare_channel(_hazards_like_truth(), table, CHANNEL_LAB)
    assert comparison.n_ports == 0
    assert set(comparison.excluded_ports) == set(HAZARDS)
    assert comparison.pearson_r is None


def test_uninstrumented_ports_drop_out_of_the_wbe_comparison():
    """Caribbean ports run no municipal WBE; they are excluded, not zeroed."""
    table = _table(_ledger(), (CHANNEL_WBE,))
    comparison = compare_channel(_hazards_like_truth(), table, CHANNEL_WBE)
    assert "MXCZM" in comparison.excluded_ports
    assert comparison.n_ports == len(HAZARDS) - len(comparison.excluded_ports)


def test_truth_comparison_needs_no_capability_at_all():
    table = _table(_ledger(), ())
    truth = truth_comparison(_hazards_like_truth(), table)
    assert truth.excluded_ports == ()
    assert truth.spearman_rho == pytest.approx(1.0)


def test_a_port_the_fit_never_saw_is_excluded():
    table = _table(_ledger(), CHANNELS)
    partial = {k: v for k, v in HAZARDS.items() if k != "DKCPH"}
    comparison = compare_channel(partial, table, CHANNEL_SYNDROMIC)
    assert comparison.excluded_ports == ("DKCPH",)


# --- run_phase / run_multiphase -----------------------------------------


def test_no_port_signal_can_reach_the_fit(monkeypatch, scratch):
    """The likelihood only ever learns the manifest and the wastewater switch."""
    seen: list[dict[str, Any]] = []

    def fake_fit(manifest: str, out: str, **kwargs: Any) -> dict[str, Any]:
        seen.append({"manifest": manifest, **kwargs})
        return {
            "status": "ok",
            "engine": "stub",
            "summary": {"hazard_mean": _hazards_like_truth()},
        }

    monkeypatch.setattr(multiphase, "fit_sentinel_fleet", fake_fit)
    payload = run_multiphase(
        manifest_path=FLEET_MANIFEST,
        ledger_path=_write_ledger(scratch),
        out_dir=os.path.join(scratch, "out"),
    )
    assert len(seen) == len(DEFAULT_PHASES)
    for call in seen:
        assert not [k for k in call if "port" in k]
        assert not [k for k in call if "ledger" in k]
    assert [p["shipboard_wastewater"] for p in payload["phases"]][:2] == [False, True]


def test_phase_outputs_carry_the_provenance_a_reader_needs(monkeypatch, scratch):
    monkeypatch.setattr(
        multiphase,
        "fit_sentinel_fleet",
        lambda *a, **k: {
            "status": "ok",
            "engine": "stub",
            "summary": {"hazard_mean": _hazards_like_truth()},
        },
    )
    out = os.path.join(scratch, "out")
    payload = run_multiphase(
        manifest_path=FLEET_MANIFEST,
        ledger_path=_write_ledger(scratch),
        out_dir=out,
        phases=resolve_phases([PHASE_CLINICAL_ONLY, PHASE_PORT_WBE]),
    )
    assert [p["phase"] for p in payload["phases"]] == [
        PHASE_CLINICAL_ONLY,
        PHASE_PORT_WBE,
    ]
    for phase in payload["phases"]:
        summary = os.path.join(out, phase["phase"], "phase_summary.json")
        assert os.path.isfile(summary)
        assert os.path.isfile(
            os.path.join(out, phase["phase"], "port_signal_table.json"),
        )
        assert phase["ports_in_ledger"] == sorted(HAZARDS)
    with open(os.path.join(out, "multiphase_comparisons.csv"), encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh))
    channels = {r["channel"] for r in rows}
    assert channels == {"truth", CHANNEL_WBE}
    assert {r["phase"] for r in rows} == {PHASE_CLINICAL_ONLY, PHASE_PORT_WBE}


def test_clinical_only_phase_reports_no_channel_comparisons(monkeypatch, scratch):
    monkeypatch.setattr(
        multiphase,
        "fit_sentinel_fleet",
        lambda *a, **k: {
            "status": "ok",
            "summary": {"hazard_mean": _hazards_like_truth()},
        },
    )
    payload = run_multiphase(
        manifest_path=FLEET_MANIFEST,
        ledger_path=_write_ledger(scratch),
        out_dir=os.path.join(scratch, "out"),
        phases=resolve_phases([PHASE_CLINICAL_ONLY]),
    )
    phase = payload["phases"][0]
    assert phase["comparisons"] == []
    assert phase["truth"]["channel"] == "truth"


def test_a_skipped_fit_fails_the_run_rather_than_reading_as_success(
    monkeypatch, scratch,
):
    monkeypatch.setattr(
        multiphase,
        "fit_sentinel_fleet",
        lambda *a, **k: {"status": "skipped", "reason": "no CmdStan"},
    )
    code = multiphase.main([
        FLEET_MANIFEST,
        "--ledger",
        _write_ledger(scratch),
        "--out",
        os.path.join(scratch, "out"),
        "--phase",
        PHASE_CLINICAL_ONLY,
    ])
    assert code == EXIT_NO_POSTERIOR


def test_cli_smoke_runs_the_reference_walker_end_to_end(scratch):
    out = os.path.join(scratch, "out")
    code = multiphase.main([
        FLEET_MANIFEST,
        "--ledger",
        _write_ledger(scratch),
        "--out",
        out,
        "--phase",
        PHASE_CLINICAL_ONLY,
        "--phase",
        PHASE_CLINICAL_WASTEWATER,
        "--smoke",
        "--engine",
        "numpy",
    ])
    assert code == 0
    with open(
        os.path.join(out, "multiphase_summary.json"), encoding="utf-8",
    ) as fh:
        payload = json.load(fh)
    assert payload["pathogen"] == PATHOGEN
    statuses = [p["fit_status"] for p in payload["phases"]]
    assert statuses == ["smoke", "smoke"]
    assert all(p["n_ports_inferred"] > 0 for p in payload["phases"])


def test_ledger_must_be_an_object(scratch):
    path = os.path.join(scratch, "not_a_ledger.json")
    with open(path, "w", encoding="utf-8") as fh:
        json.dump([1, 2, 3], fh)
    out_dir = os.path.join(scratch, "out")
    with pytest.raises(ValueError, match="must be an object"):
        run_multiphase(
            manifest_path=FLEET_MANIFEST,
            ledger_path=path,
            out_dir=out_dir,
        )
