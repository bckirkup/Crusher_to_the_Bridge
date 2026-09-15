"""The sanitary structure readout: witness, pairing and graded contrast.

The instrument has to say three separable things — whether the heads ran,
whether the pairing is intact, and how much the visits arm moved on the
same seeds — so the tests are about each of those in turn: a baseline arm
reads all-zero witness counters as executed-and-silent rather than absent,
an arm whose imports drift is flagged by the identical-imports fraction,
and a larger injected effect reads as a larger paired difference.
"""

from __future__ import annotations

import json
import zipfile
from pathlib import Path
from typing import Any

import pytest

from telemetry_buffer.observation_model.posting_tail_sensitivity import (
    MIN_PAIRED_SEEDS,
)
from telemetry_buffer.observation_model.sanitary_structure_readout import (
    WITNESS_KEYS,
    build_report,
    collect_rows,
    render_markdown,
    witness_block,
)

PAX = 400
CREW = 50
N_SEEDS = MIN_PAIRED_SEEDS + 5


def _summary(
    seed: int,
    *,
    mode: str,
    infections_pax: int,
    reported_pax: int,
    witness: dict[str, float] | None,
    fomite: int = 0,
) -> dict[str, Any]:
    block: dict[str, Any] = {
        "infections_by_dominant_route": {"fomite": fomite},
        "infection_dose_share_by_route": {},
    }
    if witness is not None:
        block["sanitary_activity"] = witness
    return {
        "run_id": f"san_{mode}_{seed}",
        "parameters": {
            "tier_id": "san_exp_7d",
            "platform_id": "expedition_cruise_450",
            "surveillance": "syndromic_comp65",
            "dose_adjustment": 4.0,
            "num_epochs": 168,
            "num_agents": PAX + CREW,
            "seed": seed,
            "boarding_mechanism_rung": "reportable",
            "sanitary_visit_mode": mode,
        },
        "derived": {
            "reported_case_attack_rate_passenger": reported_pax / PAX,
            "reported_case_attack_rate_crew": 0.0,
            "infection_attack_rate_passenger": infections_pax / PAX,
            "infection_attack_rate_crew": 0.0,
            "ever_ill_attack_rate_passenger": 0.0,
            "passenger_complement": PAX,
            "crew_complement": CREW,
        },
        "summary": block,
    }


def _profile(drawn_pax: int) -> dict[str, Any]:
    return {
        "initiation": {
            "mode": "boarding",
            "boarding": {
                "norwalk_gi": {
                    "drawn_by_role": {"passenger": drawn_pax, "crew": 0},
                    "composition": {"never_symptomatic": drawn_pax},
                },
            },
        },
    }


def _zero_witness() -> dict[str, float]:
    return dict.fromkeys(WITNESS_KEYS, 0.0)


def _visits_witness(recipients: int) -> dict[str, float]:
    return {
        "visits": 12_000.0,
        "person_seconds": 2.0e6,
        "stool_visits": 40.0,
        "unresolved": 0.0,
        "recipients": float(recipients),
        "dose_delivered": 1e-5 * recipients,
    }


def _archive(
    root: Path, arm: str, summaries: list[tuple[dict[str, Any], dict[str, Any]]],
) -> Path:
    root.mkdir(parents=True, exist_ok=True)
    path = root / f"{arm}.zip"
    with zipfile.ZipFile(path, "w") as archive:
        for summary, profile in summaries:
            prefix = f"{summary['run_id']}/"
            archive.writestr(f"{prefix}summary.json", json.dumps(summary))
            archive.writestr(
                f"{prefix}resolved_pathogen_profiles.json", json.dumps(profile),
            )
    return path


def _arm_rows(
    tmp_path: Path,
    arm: str,
    *,
    mode: str,
    extra_secondaries: int,
    imports: int = 3,
    import_drift: int = 0,
) -> list[dict[str, Any]]:
    """One arm: every seed imports ``imports`` and adds ``extra_secondaries``.

    ``import_drift`` moves the cohort on odd seeds, the signature of an arm
    that consumed a shared random stream.
    """
    summaries = []
    for seed in range(N_SEEDS):
        drawn = imports + (import_drift if seed % 2 else 0)
        witness = (
            _zero_witness() if mode == "none"
            else _visits_witness(recipients=5 * extra_secondaries)
        )
        summaries.append((
            _summary(
                seed, mode=mode,
                infections_pax=drawn + extra_secondaries,
                reported_pax=extra_secondaries,
                witness=witness,
                fomite=extra_secondaries,
            ),
            _profile(drawn),
        ))
    _archive(tmp_path / arm, arm, summaries)
    return collect_rows(tmp_path / arm, arm)


class TestWitness:
    def test_zero_counters_read_as_executed_and_silent(self, tmp_path: Path) -> None:
        rows = _arm_rows(tmp_path, "baseline", mode="none", extra_secondaries=0)
        block = witness_block(rows)
        assert block["witness_present_fraction"] == 1.0
        assert block["voyages_with_visits"]["count"] == 0
        assert block["voyages_with_recipients"]["count"] == 0
        assert block["visits_per_person_day"] == 0.0

    def test_a_missing_witness_block_is_absent_not_zero(self, tmp_path: Path) -> None:
        summary = _summary(
            0, mode="dwell_weighted", infections_pax=0, reported_pax=0,
            witness=None,
        )
        _archive(tmp_path / "old", "old", [(summary, _profile(0))])
        (row,) = collect_rows(tmp_path / "old", "old")
        assert row["sanitary_witness_present"] is False
        assert row["sanitary_visits"] is None
        assert witness_block([row])["witness_present_fraction"] == 0.0

    def test_visit_rate_is_normalised_by_complement_and_length(self, tmp_path: Path) -> None:
        rows = _arm_rows(tmp_path, "visits", mode="dwell_weighted", extra_secondaries=1)
        block = witness_block(rows)
        expected = 12_000.0 / ((PAX + CREW) * 7.0)
        assert block["visits_per_person_day"] == pytest.approx(expected)
        assert block["voyages_with_recipients"]["count"] == N_SEEDS
        assert 0.0 <= block["voyages_with_recipients"]["ci95"][0] <= 1.0

    def test_duplicate_archives_do_not_double_count(self, tmp_path: Path) -> None:
        _arm_rows(tmp_path, "dup", mode="none", extra_secondaries=0)
        first = tmp_path / "dup" / "dup.zip"
        (tmp_path / "dup" / "again.zip").write_bytes(first.read_bytes())
        assert len(collect_rows(tmp_path / "dup", "dup")) == N_SEEDS


class TestContrast:
    def test_identical_arms_produce_a_zero_contrast(self, tmp_path: Path) -> None:
        rows = (
            _arm_rows(tmp_path, "baseline", mode="none", extra_secondaries=0)
            + _arm_rows(tmp_path, "visits", mode="dwell_weighted", extra_secondaries=0)
        )
        report = build_report(rows, "pre")
        (cell,) = report["cells"]
        contrast = cell["contrast"]
        assert contrast["n_shared_seeds"] == N_SEEDS
        assert contrast["identical_import_fraction"] == 1.0
        assert contrast["differences"]["secondary_infections"]["mean_difference"] == 0.0
        assert contrast["posting"]["n_gained"] == contrast["posting"]["n_lost"] == 0
        assert cell["arms"]["baseline"]["sanitary_visit_mode"] == "none"
        assert cell["arms"]["visits"]["sanitary_visit_mode"] == "dwell_weighted"

    @pytest.mark.parametrize("extra", [1, 3, 9])
    def test_a_larger_injected_effect_reads_as_a_larger_difference(
        self, tmp_path: Path, extra: int,
    ) -> None:
        rows = (
            _arm_rows(tmp_path, "baseline", mode="none", extra_secondaries=0)
            + _arm_rows(tmp_path, "visits", mode="dwell_weighted", extra_secondaries=extra)
        )
        (cell,) = build_report(rows, "pre")["cells"]
        diffs = cell["contrast"]["differences"]
        assert diffs["secondary_infections"]["mean_difference"] == pytest.approx(extra)
        assert diffs["route_dom_fomite"]["mean_difference"] == pytest.approx(extra)
        assert diffs["sanitary_recipients"]["mean_difference"] == pytest.approx(5 * extra)
        assert cell["contrast"]["secondaries_per_import_difference"] == pytest.approx(extra / 3)
        assert diffs["posting_margin"]["mean_difference"] == pytest.approx(extra / PAX)

    def test_import_drift_is_flagged_not_hidden(self, tmp_path: Path) -> None:
        rows = (
            _arm_rows(tmp_path, "baseline", mode="none", extra_secondaries=0)
            + _arm_rows(
                tmp_path, "visits", mode="dwell_weighted", extra_secondaries=0,
                import_drift=1,
            )
        )
        (cell,) = build_report(rows, "pre")["cells"]
        fraction = cell["contrast"]["identical_import_fraction"]
        assert fraction == pytest.approx((N_SEEDS + 1) // 2 / N_SEEDS)

    def test_a_lone_arm_has_no_contrast_and_still_renders(self, tmp_path: Path) -> None:
        rows = _arm_rows(tmp_path, "visits", mode="dwell_weighted", extra_secondaries=2)
        report = build_report(rows, "pre")
        (cell,) = report["cells"]
        assert cell["contrast"] is None
        text = render_markdown(report)
        assert "unpaired" in text
        assert "expedition_cruise_450" in text

    def test_posting_gained_is_counted_from_discordant_pairs(self, tmp_path: Path) -> None:
        posting = int(0.03 * PAX) + 1
        rows = (
            _arm_rows(tmp_path, "baseline", mode="none", extra_secondaries=0)
            + _arm_rows(
                tmp_path, "visits", mode="dwell_weighted",
                extra_secondaries=posting,
            )
        )
        (cell,) = build_report(rows, "pre")["cells"]
        assert cell["contrast"]["posting"]["n_gained"] == N_SEEDS
        assert cell["contrast"]["posting"]["n_lost"] == 0
        assert cell["arms"]["visits"]["posting_frequency"] == 1.0
        assert cell["arms"]["baseline"]["posting_frequency"] == 0.0
