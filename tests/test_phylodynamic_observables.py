"""Phylodynamic observables: diversity, detection speed, and information gain.

Behavioural tests rather than golden numbers: each knob a Paper 3 arm sweeps
(mutation rate as extra lineages, sequencing depth as extra calls, assay
turnaround as later evidence) must move the observable it is supposed to move,
and every reported quantity must stay inside its mathematical bounds.
"""

from __future__ import annotations

import json
import math
import shutil
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest

from picard_framework.analysis.phylodynamics import (
    CHANNEL_CLINICAL,
    CHANNEL_WASTEWATER,
    DetectionRow,
    LineageCensusError,
    MissingCensusError,
    all_diversity_rows,
    bray_curtis_turnover,
    build_report,
    census_from_dict,
    completeness,
    detection_rows,
    detection_speed_curve,
    detection_summary,
    diversity_rows,
    diversity_summary,
    effective_lineages,
    entropy_bits,
    genotype_emergence_hours,
    information_gain_bits,
    information_rows,
    js_distance,
    load_census,
    observed_composition,
    shannon_bits,
    truth_composition,
    write_report,
)
from picard_framework.analysis.phylodynamics.artifact import LINEAGE_CENSUS_SCHEMA_VERSION
from picard_framework.analysis.sentinel.observations import bundle_from_dict

REPO_ROOT = Path(__file__).resolve().parents[1]
PATHOGEN = "norwalk_gi"


def _strain(strain_id: str, genotype: str, **kwargs: Any) -> dict[str, Any]:
    entry = {
        "strain_id": strain_id,
        "pathogen_id": PATHOGEN,
        "genotype": genotype,
        "generation": 0,
        "n_mutations": 0,
        "origin": "founder",
        "recombinant": False,
        "immune_escape": 0.0,
    }
    entry.update(kwargs)
    return entry


def _snapshot(epoch: int, counts: dict[str, int], pathogen: str = PATHOGEN) -> dict[str, Any]:
    total = sum(counts.values())
    dominant = max(counts.items(), key=lambda kv: kv[1])[0] if counts else ""
    return {
        "epoch": epoch,
        "pathogen_id": pathogen,
        "lineage_counts": counts,
        "total_carriers": total,
        "num_lineages": len(counts),
        "dominant_strain_id": dominant,
        "dominant_fraction": (counts[dominant] / total) if total else 0.0,
    }


def _payload(
    snapshots: list[dict[str, Any]],
    strains: list[dict[str, Any]] | None = None,
    *,
    epoch_duration_hours: float = 1.0,
    clock: str = "hours",
) -> dict[str, Any]:
    return {
        "schema_version": LINEAGE_CENSUS_SCHEMA_VERSION,
        "voyage_id": "v1",
        "ship_id": "classic_cruise_1900",
        "epoch_duration_hours": epoch_duration_hours,
        "natural_history_clock": clock,
        "founders": {PATHOGEN: ["s0"]},
        "strains": strains
        if strains is not None
        else [
            _strain("s0", "GII.4"),
            _strain("s1", "GII.17", generation=1, n_mutations=2, origin="mutation"),
            _strain("s2", "GII.2", generation=2, n_mutations=3, recombinant=True),
        ],
        "snapshots": snapshots,
    }


def _census(
    snapshots: list[dict[str, Any]],
    **kwargs: Any,
) -> Any:
    return census_from_dict(_payload(snapshots, **kwargs))


ONE_LINEAGE = [_snapshot(0, {"s0": 4}), _snapshot(1, {"s0": 6})]
THREE_LINEAGES = [
    _snapshot(0, {"s0": 4}),
    _snapshot(1, {"s0": 4, "s1": 2, "s2": 2}),
]


def _bundle(
    clinical: list[dict[str, Any]] | None = None,
    wastewater: list[dict[str, Any]] | None = None,
) -> Any:
    return bundle_from_dict(
        {
            "voyage_id": "v1",
            "ship_id": "classic_cruise_1900",
            "n_passengers": 100,
            "n_crew": 20,
            "observation_end_epoch": 10,
            "clinical_cases": clinical or [],
            "wastewater_samples": wastewater or [],
        },
    )


def _case(
    person_id: str,
    onset_epoch: int,
    genotype: str | None,
    report_epoch: int | None = None,
) -> dict[str, Any]:
    return {
        "person_id": person_id,
        "onset_epoch": onset_epoch,
        "crew": False,
        "pathogen": PATHOGEN,
        "genotype": genotype,
        "hours_ashore": {},
        "reported_via": "sick_call",
        "report_epoch": report_epoch if report_epoch is not None else onset_epoch,
    }


def _sample(
    sample_epoch: int,
    calls: list[tuple[str, int]],
    *,
    turnaround_hours: float | None = None,
    pathogen: str = PATHOGEN,
    pathogen_id: str | None = None,
) -> dict[str, Any]:
    reads = sum(n for _, n in calls)
    row_id = {} if pathogen_id is None else {"pathogen_id": pathogen_id}
    return {
        **row_id,
        "sample_epoch": sample_epoch,
        "collection_point": "tank_a",
        "pathogen": pathogen,
        "pathogen_reads": max(reads, 1),
        "total_reads": max(reads, 1) * 10,
        "clr_anomaly_score": 0.5,
        "concentration_copies_per_l": 1000.0,
        "assay_mode": "metagenomic",
        "turnaround_hours": turnaround_hours,
        "lineage_calls": [
            {"genotype": g, "reads": n, "fraction": n / max(reads, 1)} for g, n in calls
        ],
        "lineage_unresolved_reads": 0,
    }


# ── artifact contract ──────────────────────────────────────────────────────


def test_hours_are_epochs_times_the_declared_duration() -> None:
    """The reporting axis is physical, and the artifact supplies the factor."""
    census = _census(ONE_LINEAGE, epoch_duration_hours=6.0)
    assert census.hours(4) == pytest.approx(24.0)


def test_a_zero_epoch_duration_is_refused() -> None:
    """A zero-length epoch would make every per-hour rate infinite."""
    with pytest.raises(LineageCensusError, match="must be > 0"):
        _census(ONE_LINEAGE, epoch_duration_hours=0.0)


def test_a_non_numeric_epoch_duration_is_refused() -> None:
    """The clock is a number, not a label."""
    with pytest.raises(LineageCensusError, match="must be a number"):
        census_from_dict(
            {"epoch_duration_hours": "hourly", "snapshots": ONE_LINEAGE},
        )


def test_missing_snapshots_are_refused() -> None:
    """A payload with no census series is not a census."""
    with pytest.raises(LineageCensusError, match="snapshots"):
        census_from_dict({"epoch_duration_hours": 1.0})


def test_a_collected_lineage_has_no_genotype_rather_than_a_fake_one() -> None:
    """Extinct lineages leave the strain table; that is absence, not a variant."""
    census = _census([_snapshot(0, {"gone": 3})], strains=[])
    assert census.genotype_of("gone") == ""


def test_empty_census_series_yields_no_rows() -> None:
    """An arm that tracked nothing produces an empty table, not a crash."""
    assert all_diversity_rows(_census([])) == ()


def test_pathogen_ids_cover_every_tracked_pathogen() -> None:
    """A two-pathogen run must not collapse into one trajectory."""
    census = _census(
        [_snapshot(0, {"s0": 2}), _snapshot(0, {"s0": 1}, pathogen="sars_cov2_resp")],
    )
    assert census.pathogen_ids() == ("norwalk_gi", "sars_cov2_resp")


# ── diversity ──────────────────────────────────────────────────────────────


def test_richness_rises_with_more_lineages() -> None:
    """The mutation-rate knob has to move measured richness, or it is dead."""
    low = diversity_rows(_census(ONE_LINEAGE), PATHOGEN)[-1].richness
    high = diversity_rows(_census(THREE_LINEAGES), PATHOGEN)[-1].richness
    assert high > low


def test_shannon_entropy_rises_with_evenness() -> None:
    """Diversity is composition, not only count."""
    assert shannon_bits({"a": 5, "b": 5}) > shannon_bits({"a": 9, "b": 1})


def test_a_single_lineage_carries_no_entropy() -> None:
    """A clonal outbreak has nothing for a sequencer to resolve."""
    assert shannon_bits({"a": 7}) == pytest.approx(0.0)


def test_effective_lineages_equals_richness_when_even() -> None:
    """``exp(H)`` is calibrated: four equal lineages are four effective ones."""
    assert effective_lineages({"a": 2, "b": 2, "c": 2, "d": 2}) == pytest.approx(4.0)


def test_effective_lineages_is_below_richness_when_skewed() -> None:
    """A rare variant is not a resolvable one, and the measure says so."""
    assert effective_lineages({"a": 99, "b": 1}) < 2.0


def test_effective_lineages_of_nothing_is_zero() -> None:
    """No carriers, no diversity."""
    assert effective_lineages({}) == pytest.approx(0.0)


def test_turnover_is_zero_for_an_unchanged_composition() -> None:
    """Nothing replaced means no turnover."""
    assert bray_curtis_turnover({"a": 3}, {"a": 6}) == pytest.approx(0.0)


def test_turnover_is_one_for_a_complete_replacement() -> None:
    """A lineage sweep is total dissimilarity."""
    assert bray_curtis_turnover({"a": 3}, {"b": 3}) == pytest.approx(1.0)


def test_turnover_of_two_empty_epochs_is_zero() -> None:
    """Absence followed by absence is not a sweep."""
    assert bray_curtis_turnover({}, {}) == pytest.approx(0.0)


def test_turnover_from_nothing_to_something_is_one() -> None:
    """An introduction into an empty ship replaces the whole composition."""
    assert bray_curtis_turnover({}, {"a": 2}) == pytest.approx(1.0)


def test_cumulative_lineages_never_decreases() -> None:
    """Cumulative counts are cumulative even when lineages go extinct."""
    census = _census(
        [_snapshot(0, {"s0": 3}), _snapshot(1, {"s1": 3}), _snapshot(2, {"s2": 3})],
    )
    values = [row.cumulative_lineages for row in diversity_rows(census, PATHOGEN)]
    assert values == sorted(values)


def test_diversity_rows_report_physical_hours() -> None:
    """The axis every figure is drawn on is hours, converted from the artifact."""
    census = _census(ONE_LINEAGE, epoch_duration_hours=6.0)
    assert [row.voyage_hours for row in diversity_rows(census, PATHOGEN)] == [0.0, 6.0]


def test_mutation_load_is_carrier_weighted() -> None:
    """Mean mutations track the lineages hosts actually carry."""
    rows = diversity_rows(_census(THREE_LINEAGES), PATHOGEN)
    assert rows[-1].mean_mutations == pytest.approx((0 * 4 + 2 * 2 + 3 * 2) / 8)


def test_recombinant_fraction_is_bounded_and_positive_when_present() -> None:
    """The recombination knob shows up as carriers of a recombinant lineage."""
    rows = diversity_rows(_census(THREE_LINEAGES), PATHOGEN)
    assert 0.0 < rows[-1].recombinant_fraction <= 1.0


def test_unknown_lineages_do_not_break_trait_weighting() -> None:
    """A collected lineage contributes no traits rather than a KeyError."""
    census = _census([_snapshot(0, {"s0": 2, "ghost": 2})], strains=[_strain("s0", "GII.4")])
    assert diversity_rows(census, PATHOGEN)[0].mean_mutations == pytest.approx(0.0)


def test_every_diversity_quantity_is_finite_and_in_range() -> None:
    """Bounds, so no arm can report a NaN fraction or a negative count."""
    for row in all_diversity_rows(_census(THREE_LINEAGES)):
        assert row.carriers >= 0
        assert row.richness >= 0
        assert math.isfinite(row.shannon_bits)
        assert row.shannon_bits >= 0.0
        assert 0.0 <= row.dominant_fraction <= 1.0
        assert 0.0 <= row.turnover <= 1.0
        assert 0.0 <= row.recombinant_fraction <= 1.0
        assert row.voyage_hours >= 0.0


def test_diversity_summary_of_an_empty_trajectory_is_zeroed() -> None:
    """An untracked arm summarises to zeros, not to ``None`` arithmetic."""
    assert diversity_summary(())["peak_richness"] == 0


def test_diversity_summary_reports_the_peak_in_hours() -> None:
    """Where the peak fell is a physical time, and quotable as one."""
    census = _census(THREE_LINEAGES, epoch_duration_hours=6.0)
    summary = diversity_summary(diversity_rows(census, PATHOGEN))
    assert summary["peak_richness_hours"] == pytest.approx(6.0)


# ── detection ──────────────────────────────────────────────────────────────


def test_emergence_is_the_first_hour_a_genotype_is_carried() -> None:
    """Truth is when it was aboard, not when it was noticed."""
    census = _census(THREE_LINEAGES, epoch_duration_hours=2.0)
    emergence = genotype_emergence_hours(census)
    assert emergence[(PATHOGEN, "GII.17")] == pytest.approx(2.0)


def test_a_never_typed_genotype_is_censored_not_dropped() -> None:
    """Censoring is evidence; discarding it would flatter every arm."""
    rows = detection_rows(_census(THREE_LINEAGES), _bundle())
    assert [row.detected for row in rows] == [False, False, False]


def test_clinical_typing_detects_the_genotype_it_called() -> None:
    """The clinical channel is a real detection path, at its report epoch."""
    rows = detection_rows(
        _census(THREE_LINEAGES),
        _bundle(clinical=[_case("p1", 1, "GII.17")]),
    )
    detected = {row.genotype: row.clinical_detection_hours for row in rows}
    assert detected["GII.17"] == pytest.approx(1.0)


def test_wastewater_detection_waits_for_turnaround() -> None:
    """A library is evidence when it comes back, not when it was collected."""
    rows = detection_rows(
        _census(THREE_LINEAGES),
        _bundle(wastewater=[_sample(1, [("GII.17", 40)], turnaround_hours=12.0)]),
    )
    detected = {row.genotype: row.wastewater_detection_hours for row in rows}
    assert detected["GII.17"] == pytest.approx(13.0)


def test_the_assay_label_does_not_have_to_be_the_profile_id() -> None:
    """Real runs label sewage ``norovirus`` and truth ``norwalk_gi``.

    The delay catalog the fit filters on and the ABM profile are different
    vocabularies by design, so the join reads the id the row carries; without
    this, every genotype the sequencer typed comes back censored.
    """
    rows = detection_rows(
        _census(THREE_LINEAGES),
        _bundle(
            wastewater=[
                _sample(
                    1,
                    [("GII.17", 40)],
                    pathogen="norovirus",
                    pathogen_id=PATHOGEN,
                ),
            ],
        ),
    )
    detected = {row.genotype: row.detected for row in rows}
    assert detected["GII.17"] is True


def test_a_row_with_no_profile_id_falls_back_to_its_label() -> None:
    """Bundles written before the id was carried still join on the label."""
    rows = detection_rows(
        _census(THREE_LINEAGES),
        _bundle(wastewater=[_sample(1, [("GII.17", 40)], pathogen_id=None)]),
    )
    detected = {row.genotype: row.detected for row in rows}
    assert detected["GII.17"] is True


def test_a_foreign_profile_id_is_not_credited_to_this_pathogen() -> None:
    """Resolving the vocabulary must not turn the join into a wildcard."""
    rows = detection_rows(
        _census(THREE_LINEAGES),
        _bundle(
            wastewater=[
                _sample(
                    1,
                    [("GII.17", 40)],
                    pathogen="norovirus",
                    pathogen_id="sars_cov2_resp",
                ),
            ],
        ),
    )
    assert [row.detected for row in rows] == [False, False, False]


def test_typed_sewage_reads_inform_even_under_a_config_label() -> None:
    """Information gain is about what was typed, not how it was labelled."""
    census = _census(THREE_LINEAGES)
    bundle = _bundle(
        wastewater=[
            _sample(
                1,
                [("GII.4", 40), ("GII.17", 20), ("GII.2", 20)],
                pathogen="norovirus",
                pathogen_id=PATHOGEN,
            ),
        ],
    )
    rows = information_rows(census, bundle, CHANNEL_WASTEWATER)
    assert max(row.information_gain_bits for row in rows) > 0.0


def test_detection_lag_is_measured_from_emergence() -> None:
    """The Paper 3 observable is a lag in hours, not an absolute timestamp."""
    rows = detection_rows(
        _census(THREE_LINEAGES),
        _bundle(wastewater=[_sample(1, [("GII.17", 40)], turnaround_hours=12.0)]),
    )
    lags = {row.genotype: row.wastewater_lag_hours for row in rows}
    assert lags["GII.17"] == pytest.approx(12.0)


def test_lags_are_never_negative() -> None:
    """A channel cannot report a lineage before it existed."""
    rows = detection_rows(
        _census([_snapshot(5, {"s1": 3})]),
        _bundle(clinical=[_case("p1", 1, "GII.17")]),
    )
    assert rows[0].clinical_lag_hours == pytest.approx(0.0)


def test_the_faster_channel_owns_the_first_detection() -> None:
    """First detection is the minimum over channels, and it is attributed."""
    rows = detection_rows(
        _census(THREE_LINEAGES),
        _bundle(
            clinical=[_case("p1", 9, "GII.17")],
            wastewater=[_sample(1, [("GII.17", 40)])],
        ),
    )
    summary = detection_summary(rows)
    assert summary["wastewater_first_count"] == 1


def test_deeper_sequencing_detects_more_genotypes() -> None:
    """Sequencing depth is a sweep axis: more calls, more genotypes detected."""
    shallow = detection_summary(
        detection_rows(
            _census(THREE_LINEAGES),
            _bundle(wastewater=[_sample(1, [("GII.4", 100)])]),
        ),
    )
    deep = detection_summary(
        detection_rows(
            _census(THREE_LINEAGES),
            _bundle(
                wastewater=[_sample(1, [("GII.4", 100), ("GII.17", 20), ("GII.2", 5)])],
            ),
        ),
    )
    assert deep["detected_fraction"] > shallow["detected_fraction"]


def test_a_zero_read_call_is_not_a_detection() -> None:
    """A call with no reads behind it is a reporting artefact."""
    rows = detection_rows(
        _census(THREE_LINEAGES),
        _bundle(wastewater=[_sample(1, [("GII.17", 0)])]),
    )
    assert not any(row.detected for row in rows)


def test_detection_speed_curve_is_monotone_in_hours() -> None:
    """Detected genotypes never un-detect as the voyage proceeds."""
    rows = detection_rows(
        _census(THREE_LINEAGES),
        _bundle(clinical=[_case("p1", 1, "GII.17")]),
    )
    fractions = [
        point["detected_fraction"]
        for point in detection_speed_curve(rows, (0.0, 1.0, 2.0, 3.0))
    ]
    assert fractions[-1] >= fractions[0]


def test_detection_curve_denominator_excludes_unemerged_genotypes() -> None:
    """At hour zero only the founder existed, so it is a complete read."""
    rows = detection_rows(
        _census(THREE_LINEAGES),
        _bundle(wastewater=[_sample(0, [("GII.4", 40)])]),
    )
    first = detection_speed_curve(rows, (0.0,))[0]
    assert first["detected_fraction"] == pytest.approx(1.0)


def test_detection_curve_fractions_stay_in_the_unit_interval() -> None:
    """A fraction outside [0, 1] would be a counting bug in a figure."""
    rows = detection_rows(
        _census(THREE_LINEAGES),
        _bundle(clinical=[_case("p1", 1, "GII.17")]),
    )
    for point in detection_speed_curve(rows, (0.0, 1.0, 5.0)):
        assert 0.0 <= point["detected_fraction"] <= 1.0


def test_detection_summary_median_is_none_when_nothing_was_seen() -> None:
    """No detections means no median lag, not a zero-hour lag."""
    assert detection_summary(())["median_detection_lag_hours"] is None


def test_detection_summary_median_of_two_lags_is_their_mean() -> None:
    """The even-length median is interpolated, as a median should be."""
    rows = (
        DetectionRow(
            PATHOGEN, "a", 0.0, 2.0, None, 2.0, 2.0, None, 2.0, True,
        ),
        DetectionRow(
            PATHOGEN, "b", 0.0, 4.0, None, 4.0, 4.0, None, 4.0, True,
        ),
    )
    assert detection_summary(rows)["median_detection_lag_hours"] == pytest.approx(3.0)


def test_detection_ignores_a_bundle_absent_entirely() -> None:
    """An arm with no sequencing is fully censored, and analysable."""
    rows = detection_rows(_census(THREE_LINEAGES), None)
    assert detection_summary(rows)["detected_fraction"] == pytest.approx(0.0)


# ── information ────────────────────────────────────────────────────────────


def test_a_perfect_read_has_zero_divergence() -> None:
    """Reporting the truth exactly is a distance of zero."""
    assert js_distance({"a": 2, "b": 2}, {"a": 10, "b": 10}) == pytest.approx(0.0)


def test_a_wrong_dominant_call_diverges() -> None:
    """Getting the dominant lineage backwards is measurably wrong."""
    assert js_distance({"a": 9, "b": 1}, {"a": 1, "b": 9}) > 0.5


def test_divergence_against_an_empty_report_is_maximal() -> None:
    """Reporting nothing is the worst possible read of a real mixture."""
    assert js_distance({"a": 1}, {}) == pytest.approx(1.0)


def test_divergence_of_two_empty_compositions_is_zero() -> None:
    """No truth and no report agree trivially."""
    assert js_distance({}, {}) == pytest.approx(0.0)


def test_divergence_stays_in_the_unit_interval() -> None:
    """A metric outside [0, 1] would break every comparison across arms."""
    assert 0.0 <= js_distance({"a": 1, "b": 3, "c": 5}, {"a": 5, "c": 1}) <= 1.0


def test_a_channel_reporting_nothing_gains_no_bits() -> None:
    """The uniform baseline is the floor: silence scores exactly zero."""
    assert information_gain_bits({"a": 3, "b": 1}, {}) == pytest.approx(0.0)


def test_a_faithful_channel_gains_bits() -> None:
    """A correct read of a skewed mixture beats a genotype-blind guess."""
    assert information_gain_bits({"a": 9, "b": 1}, {"a": 9, "b": 1}) > 0.0


def test_a_confidently_wrong_channel_loses_bits() -> None:
    """Worse than ignorance is a real outcome and is reported as negative."""
    assert information_gain_bits({"a": 9, "b": 1}, {"b": 100}) < 0.0


def test_information_gain_is_zero_without_truth() -> None:
    """No lineages aboard, nothing to learn."""
    assert information_gain_bits({}, {"a": 5}) == pytest.approx(0.0)


def test_a_closer_read_gains_more_bits_than_a_coarser_one() -> None:
    """Graded, not binary: accuracy buys bits monotonically."""
    truth = {"a": 8, "b": 2}
    close = information_gain_bits(truth, {"a": 78, "b": 22})
    coarse = information_gain_bits(truth, {"a": 55, "b": 45})
    assert close > coarse


def test_entropy_of_a_clonal_truth_is_zero() -> None:
    """One genotype is no uncertainty."""
    assert entropy_bits({"a": 4}) == pytest.approx(0.0)


def test_entropy_of_an_even_pair_is_one_bit() -> None:
    """The units are bits, and calibrated against the obvious case."""
    assert entropy_bits({"a": 4, "b": 4}) == pytest.approx(1.0)


def test_completeness_counts_named_truth_mass() -> None:
    """Completeness is the share of real circulation the report named."""
    assert completeness({"a": 8, "b": 2}, {"a": 1}) == pytest.approx(0.8)


def test_completeness_without_truth_is_zero() -> None:
    """Nothing circulating, nothing to be complete about."""
    assert completeness({}, {"a": 1}) == pytest.approx(0.0)


# ── truth versus observed, per channel ─────────────────────────────────────


def test_truth_composition_aggregates_lineages_into_genotypes() -> None:
    """Sequencing reports genotypes, so truth is compared at that resolution."""
    census = _census([_snapshot(0, {"s0": 3, "s1": 1})])
    assert truth_composition(census, PATHOGEN, 0) == {"GII.4": 3.0, "GII.17": 1.0}


def test_observed_composition_is_cumulative_in_the_clinical_channel() -> None:
    """A programme knows every call returned so far, not only this hour's."""
    bundle = _bundle(clinical=[_case("p1", 1, "GII.4"), _case("p2", 2, "GII.17")])
    observed = observed_composition(bundle, PATHOGEN, 2, 1.0, CHANNEL_CLINICAL)
    assert observed == {"GII.4": 1.0, "GII.17": 1.0}


def test_observed_composition_excludes_calls_not_yet_returned() -> None:
    """Evidence from the future is not evidence."""
    bundle = _bundle(wastewater=[_sample(1, [("GII.17", 40)], turnaround_hours=12.0)])
    observed = observed_composition(bundle, PATHOGEN, 2, 1.0, CHANNEL_WASTEWATER)
    assert observed == {}


def test_observed_composition_weights_wastewater_by_reads() -> None:
    """Read depth is the wastewater channel's evidence, so it is the weight."""
    bundle = _bundle(wastewater=[_sample(0, [("GII.4", 90), ("GII.17", 10)])])
    observed = observed_composition(bundle, PATHOGEN, 0, 1.0, CHANNEL_WASTEWATER)
    assert observed == {"GII.4": 90.0, "GII.17": 10.0}


def test_observed_composition_ignores_another_pathogen() -> None:
    """A SARS-CoV-2 library says nothing about norovirus lineages."""
    sample = _sample(0, [("GII.4", 50)])
    sample["pathogen"] = "sars_cov2_resp"
    observed = observed_composition(
        _bundle(wastewater=[sample]), PATHOGEN, 0, 1.0, CHANNEL_WASTEWATER,
    )
    assert observed == {}


def test_an_unknown_channel_is_refused() -> None:
    """Channels are a closed set; a typo must not silently return nothing."""
    bundle = _bundle()
    with pytest.raises(ValueError, match="unknown detection channel"):
        observed_composition(bundle, PATHOGEN, 0, 1.0, "surface_swab")


def test_information_rows_cover_every_census_epoch() -> None:
    """One comparison row per pathogen-epoch, so the trajectory is plottable."""
    rows = information_rows(_census(THREE_LINEAGES), _bundle(), CHANNEL_CLINICAL)
    assert [row.epoch for row in rows] == [0, 1]


def test_information_rows_report_hours_not_epoch_indices() -> None:
    """Same lesson as the diversity table: physical time, or nothing."""
    census = _census(THREE_LINEAGES, epoch_duration_hours=6.0)
    rows = information_rows(census, _bundle(), CHANNEL_CLINICAL)
    assert [row.voyage_hours for row in rows] == [0.0, 6.0]


def test_a_typing_channel_beats_a_silent_one_in_bits() -> None:
    """The whole Paper 3 claim: typing buys information about the mixture."""
    census = _census(THREE_LINEAGES)
    silent = information_rows(census, _bundle(), CHANNEL_WASTEWATER)[-1]
    typed = information_rows(
        census,
        _bundle(wastewater=[_sample(0, [("GII.4", 4), ("GII.17", 2), ("GII.2", 2)])]),
        CHANNEL_WASTEWATER,
    )[-1]
    assert typed.information_gain_bits > silent.information_gain_bits


def test_a_typing_channel_reduces_divergence() -> None:
    """And the same evidence must also move the divergence measure."""
    census = _census(THREE_LINEAGES)
    silent = information_rows(census, _bundle(), CHANNEL_WASTEWATER)[-1]
    typed = information_rows(
        census,
        _bundle(wastewater=[_sample(0, [("GII.4", 4), ("GII.17", 2), ("GII.2", 2)])]),
        CHANNEL_WASTEWATER,
    )[-1]
    assert typed.js_distance < silent.js_distance


def test_every_information_quantity_is_finite() -> None:
    """No NaN or infinity may reach a figure or a summary table."""
    rows = information_rows(
        _census(THREE_LINEAGES),
        _bundle(clinical=[_case("p1", 1, "GII.17")]),
        CHANNEL_CLINICAL,
    )
    for row in rows:
        assert math.isfinite(row.js_distance)
        assert math.isfinite(row.information_gain_bits)
        assert math.isfinite(row.truth_entropy_bits)
        assert 0.0 <= row.completeness <= 1.0


# ── report assembly and I/O ────────────────────────────────────────────────


@pytest.fixture
def out_root() -> Iterator[Path]:
    """Repo-root-relative output directory (analysis writers are confined)."""
    root = REPO_ROOT / "telemetry_buffer" / "_tmp_pr13_report"
    shutil.rmtree(root, ignore_errors=True)
    root.mkdir(parents=True)
    try:
        yield root
    finally:
        shutil.rmtree(root, ignore_errors=True)


def test_report_records_the_arm_it_was_built_from() -> None:
    """Two clock arms must never be pooled, so each report names its own."""
    report = build_report(_census(THREE_LINEAGES, clock="legacy_epoch_day"), None)
    assert report["arm"]["natural_history_clock"] == "legacy_epoch_day"


def test_report_records_whether_anything_was_observed() -> None:
    """An unobserved arm is a truth-only report and is labelled as one."""
    assert build_report(_census(THREE_LINEAGES), None)["arm"]["observed"] is False


def test_report_summarises_both_channels() -> None:
    """Clinical and wastewater are compared, never merged into one number."""
    report = build_report(_census(THREE_LINEAGES), _bundle())
    assert set(report["summary"]["information"]) == {
        CHANNEL_CLINICAL,
        CHANNEL_WASTEWATER,
    }


def test_write_report_emits_the_tables(out_root: Path) -> None:
    """The campaign-facing artefacts: one CSV per observable, plus a summary."""
    source = out_root / "run"
    source.mkdir()
    (source / "lineage_census.json").write_text(
        json.dumps(_payload(THREE_LINEAGES)), encoding="utf-8",
    )
    result = write_report(str(source), str(out_root / "out"))
    assert set(result["tables"]) >= {
        "lineage_diversity.csv",
        "genotype_detection.csv",
        "phylodynamic_summary.json",
    }


def test_written_summary_is_valid_json_with_its_arm(out_root: Path) -> None:
    """A downstream reader must be able to tell arms apart from the file alone."""
    source = out_root / "run"
    source.mkdir()
    (source / "lineage_census.json").write_text(
        json.dumps(_payload(THREE_LINEAGES, epoch_duration_hours=6.0)),
        encoding="utf-8",
    )
    out = out_root / "out"
    write_report(str(source), str(out))
    payload = json.loads((out / "phylodynamic_summary.json").read_text(encoding="utf-8"))
    assert payload["arm"]["epoch_duration_hours"] == pytest.approx(6.0)


def test_write_report_reads_a_campaign_result_zip(out_root: Path) -> None:
    """Campaign runs arrive zipped, so the analysis reads them zipped."""
    import zipfile

    zip_path = out_root / "run42.zip"
    with zipfile.ZipFile(zip_path, "w") as zf:
        zf.writestr("run42/lineage_census.json", json.dumps(_payload(THREE_LINEAGES)))
    result = write_report(str(zip_path), str(out_root / "out_zip"))
    assert result["arm"]["voyage_id"] == "v1"


def test_a_run_without_a_census_is_reported_as_such(out_root: Path) -> None:
    """An unarmed run is a missing-input error, not an empty figure set."""
    source = out_root / "bare"
    source.mkdir()
    with pytest.raises(MissingCensusError, match="variant surveillance"):
        load_census(str(source))


def test_the_cli_reports_a_missing_census_without_crashing(out_root: Path) -> None:
    """Exit code, not a traceback, for a run that tracked no lineages."""
    from picard_framework.analysis.phylodynamics.__main__ import main

    source = out_root / "bare_cli"
    source.mkdir()
    assert main([str(source), "--out", str(out_root / "cli_out")]) == 2


def test_the_cli_writes_a_report(out_root: Path) -> None:
    """The documented entry point works end to end."""
    from picard_framework.analysis.phylodynamics.__main__ import main

    source = out_root / "cli_run"
    source.mkdir()
    (source / "lineage_census.json").write_text(
        json.dumps(_payload(THREE_LINEAGES)), encoding="utf-8",
    )
    out = out_root / "cli_report"
    assert main([str(source), "--out", str(out)]) == 0
    assert (out / "lineage_diversity.csv").exists()


def test_figures_are_written_when_matplotlib_is_available(out_root: Path) -> None:
    """Figures are the point of the visualization lesson, so they are tested."""
    from picard_framework.analysis.phylodynamics.figures import have_matplotlib

    if not have_matplotlib():
        pytest.skip("matplotlib not installed")
    source = out_root / "fig_run"
    source.mkdir()
    (source / "lineage_census.json").write_text(
        json.dumps(_payload(THREE_LINEAGES)), encoding="utf-8",
    )
    out = out_root / "fig_out"
    result = write_report(str(source), str(out))
    assert "lineage_diversity_hours.png" in result["figures"]


def test_figure_titles_name_the_clock_arm() -> None:
    """A figure that does not say which arm it is cannot be compared."""
    from picard_framework.analysis.phylodynamics.figures import clock_caption

    caption = clock_caption(_census(ONE_LINEAGE, clock="legacy_epoch_day"))
    assert "legacy_epoch_day" in caption


def test_figure_axis_label_states_the_unit() -> None:
    """'epochs' hid a 24x error; 'voyage hours' would not have."""
    from picard_framework.analysis.phylodynamics.figures import HOURS_AXIS_LABEL

    assert "hours" in HOURS_AXIS_LABEL


# ── malformed input and empty-arm edges ────────────────────────────────────


def test_lineage_counts_must_be_an_object() -> None:
    """A list of counts has no lineage names, so it is not a census."""
    with pytest.raises(LineageCensusError, match="lineage_counts"):
        census_from_dict(
            {"epoch_duration_hours": 1.0, "snapshots": [{"lineage_counts": [1, 2]}]},
        )


def test_a_snapshot_that_is_not_an_object_is_refused() -> None:
    """Silent skipping would drop epochs out of a trajectory."""
    with pytest.raises(LineageCensusError, match="each snapshot"):
        census_from_dict({"epoch_duration_hours": 1.0, "snapshots": ["epoch0"]})


def test_snapshots_must_be_a_list() -> None:
    """A mapping of snapshots has no defined order."""
    with pytest.raises(LineageCensusError, match="snapshots list"):
        census_from_dict({"epoch_duration_hours": 1.0, "snapshots": {"0": {}}})


def test_strains_must_be_a_list() -> None:
    """The registry writes a list; anything else is a different schema."""
    with pytest.raises(LineageCensusError, match="strains must be a list"):
        census_from_dict(
            {"epoch_duration_hours": 1.0, "snapshots": [], "strains": {"s0": {}}},
        )


def test_each_strain_entry_must_be_an_object() -> None:
    """A bare strain id carries no genotype and would type as empty."""
    with pytest.raises(LineageCensusError, match="each strain entry"):
        census_from_dict(
            {"epoch_duration_hours": 1.0, "snapshots": [], "strains": ["s0"]},
        )


def test_founders_must_be_an_object() -> None:
    """Founders are per pathogen, so the shape is a mapping."""
    with pytest.raises(LineageCensusError, match="founders"):
        census_from_dict(
            {"epoch_duration_hours": 1.0, "snapshots": [], "founders": ["s0"]},
        )


def test_traits_of_an_empty_epoch_are_zero() -> None:
    """An epoch with no carriers has no mutation load to average."""
    row = diversity_rows(_census([_snapshot(0, {})]), PATHOGEN)[0]
    assert (row.mean_generation, row.mean_mutations) == (0.0, 0.0)


def test_an_empty_lineage_is_not_an_emergence() -> None:
    """A zero count is a lineage that has gone, not one that arrived."""
    census = _census([_snapshot(0, {"s1": 0})])
    assert genotype_emergence_hours(census) == {}


def test_an_untyped_clinical_case_is_not_a_detection() -> None:
    """A case with no genotype call carries no variant information."""
    rows = detection_rows(
        _census(THREE_LINEAGES), _bundle(clinical=[_case("p1", 1, None)]),
    )
    assert not any(row.detected for row in rows)


def test_another_pathogens_case_does_not_detect_this_one() -> None:
    """Channels are per pathogen; cross-attribution would flatter detection."""
    case = _case("p1", 1, "GII.17")
    case["pathogen"] = "sars_cov2_resp"
    rows = detection_rows(_census(THREE_LINEAGES), _bundle(clinical=[case]))
    assert not any(row.detected for row in rows)


def test_a_clinical_case_without_a_report_epoch_falls_back_to_onset() -> None:
    """Presentation is evidence even when the report epoch is unrecorded."""
    case = _case("p1", 2, "GII.17")
    case["report_epoch"] = None
    observed = observed_composition(
        _bundle(clinical=[case]), PATHOGEN, 2, 1.0, CHANNEL_CLINICAL,
    )
    assert observed == {"GII.17": 1.0}


def test_a_truthless_trajectory_summarises_to_the_uninformative_floor() -> None:
    """No lineages aboard: zero bits gained and maximal divergence by fiat."""
    from picard_framework.analysis.phylodynamics.compare import (
        channel_information_summary,
    )

    summary = channel_information_summary(())
    assert summary["mean_js_distance"] == pytest.approx(1.0)
    assert summary["mean_information_gain_bits"] == pytest.approx(0.0)


def test_hours_grid_of_an_empty_census_is_empty() -> None:
    """Nothing to sweep over, so no curve."""
    from picard_framework.analysis.phylodynamics.report import hours_grid

    assert hours_grid(_census([])) == ()


def test_hours_grid_of_a_single_point_is_the_end_hour() -> None:
    """A one-point curve is the voyage end, not a division by zero."""
    from picard_framework.analysis.phylodynamics.report import hours_grid

    assert hours_grid(_census(THREE_LINEAGES), points=1) == (1.0,)


def test_hours_grid_of_a_zero_length_voyage_is_the_origin() -> None:
    """A single-epoch run has no span to divide."""
    from picard_framework.analysis.phylodynamics.report import hours_grid

    assert hours_grid(_census([_snapshot(0, {"s0": 1})])) == (0.0,)


def test_hours_grid_spans_the_voyage_in_physical_hours() -> None:
    """The curve's x-axis ends at the last observed hour, not epoch count."""
    from picard_framework.analysis.phylodynamics.report import hours_grid

    grid = hours_grid(_census(THREE_LINEAGES, epoch_duration_hours=6.0), points=3)
    assert grid == (0.0, 3.0, 6.0)


def test_a_run_without_a_line_list_loads_no_bundle(out_root: Path) -> None:
    """Truth-only arms are legal, and produce a censored report."""
    from picard_framework.analysis.phylodynamics.report import load_bundle

    source = out_root / "truth_only"
    source.mkdir()
    (source / "lineage_census.json").write_text(
        json.dumps(_payload(THREE_LINEAGES)), encoding="utf-8",
    )
    assert load_bundle(str(source)) is None


def test_figures_are_skipped_when_there_is_nothing_to_draw(out_root: Path) -> None:
    """An empty arm writes no figures rather than blank axes."""
    from picard_framework.analysis.phylodynamics import figures as fig

    census = _census([])
    out = str(out_root / "empty_figs")
    assert fig.plot_lineage_diversity(out, census, ()) is None
    assert fig.plot_dominance(out, census, ()) is None
    assert fig.plot_detection_speed(out, census, ()) is None
    assert fig.plot_detection_lags(out, census, ()) is None
    assert fig.plot_information_gain(out, census, {CHANNEL_CLINICAL: ()}) is None


def test_the_detection_lag_figure_is_drawn_for_a_detected_genotype(
    out_root: Path,
) -> None:
    """The lag figure is the one a reviewer reads, so it is exercised."""
    from picard_framework.analysis.phylodynamics import figures as fig

    if not fig.have_matplotlib():
        pytest.skip("matplotlib not installed")
    census = _census(THREE_LINEAGES)
    rows = detection_rows(census, _bundle(clinical=[_case("p1", 1, "GII.17")]))
    path = fig.plot_detection_lags(str(out_root / "lag_fig"), census, rows)
    assert path == "detection_lag_hours.png"


def test_the_information_figure_skips_a_channel_with_no_rows(
    out_root: Path,
) -> None:
    """One silent channel must not suppress the other's curve."""
    from picard_framework.analysis.phylodynamics import figures as fig

    if not fig.have_matplotlib():
        pytest.skip("matplotlib not installed")
    census = _census(THREE_LINEAGES)
    rows = information_rows(census, _bundle(), CHANNEL_CLINICAL)
    path = fig.plot_information_gain(
        str(out_root / "info_fig"),
        census,
        {CHANNEL_CLINICAL: rows, CHANNEL_WASTEWATER: ()},
    )
    assert path == "information_gain_hours.png"


def test_an_untyped_wastewater_sample_detects_nothing() -> None:
    """A library with no pathogen attribution cannot detect that pathogen."""
    sample = _sample(1, [("GII.17", 40)])
    sample["pathogen"] = ""
    rows = detection_rows(_census(THREE_LINEAGES), _bundle(wastewater=[sample]))
    assert not any(row.detected for row in rows)


def test_another_pathogens_library_does_not_detect_this_one() -> None:
    """Genotype labels can collide across pathogens; attribution must not."""
    sample = _sample(1, [("GII.17", 40)])
    sample["pathogen"] = "sars_cov2_resp"
    rows = detection_rows(_census(THREE_LINEAGES), _bundle(wastewater=[sample]))
    assert not any(row.detected for row in rows)


def test_a_lineage_with_no_registry_entry_is_absent_from_truth() -> None:
    """An unnamed lineage cannot be compared at genotype resolution."""
    census = _census([_snapshot(0, {"ghost": 3})], strains=[])
    assert truth_composition(census, PATHOGEN, 0) == {}


def test_truth_composition_ignores_other_epochs() -> None:
    """Each comparison row reads its own epoch, not the whole voyage."""
    assert truth_composition(_census(THREE_LINEAGES), PATHOGEN, 0) == {"GII.4": 4.0}


def test_observed_composition_skips_an_untyped_case() -> None:
    """A case with no genotype adds no genotype evidence."""
    bundle = _bundle(clinical=[_case("p1", 1, None)])
    assert observed_composition(bundle, PATHOGEN, 2, 1.0, CHANNEL_CLINICAL) == {}


def test_observed_composition_skips_a_zero_read_call() -> None:
    """A call with no reads is not evidence about the mixture."""
    bundle = _bundle(wastewater=[_sample(0, [("GII.4", 0)])])
    assert observed_composition(bundle, PATHOGEN, 0, 1.0, CHANNEL_WASTEWATER) == {}


def test_channel_summaries_cover_both_channels() -> None:
    """Every report compares the two channels, never one merged number."""
    from picard_framework.analysis.phylodynamics.compare import channel_summaries

    summaries = channel_summaries(_census(THREE_LINEAGES), _bundle())
    assert set(summaries) == {CHANNEL_CLINICAL, CHANNEL_WASTEWATER}


def test_an_unnamed_lineage_has_no_emergence_hour() -> None:
    """A collected lineage cannot emerge as an empty-string genotype."""
    census = _census([_snapshot(0, {"ghost": 4})], strains=[])
    assert genotype_emergence_hours(census) == {}


def test_a_non_object_line_list_loads_no_bundle(out_root: Path) -> None:
    """A malformed line list is treated as absent, not parsed hopefully."""
    from picard_framework.analysis.phylodynamics.report import load_bundle

    source = out_root / "bad_bundle"
    source.mkdir()
    (source / "sentinel_line_list.json").write_text("[]", encoding="utf-8")
    assert load_bundle(str(source)) is None


def test_figures_are_skipped_without_matplotlib(
    out_root: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Analysis runs in a plotting-free environment; it just emits no PNGs."""
    from picard_framework.analysis.phylodynamics import figures as fig

    monkeypatch.setattr(fig, "have_matplotlib", lambda: False)
    census = _census(THREE_LINEAGES)
    rows = diversity_rows(census, PATHOGEN)
    assert fig.plot_lineage_diversity(str(out_root / "nofig"), census, rows) is None


def test_matplotlib_availability_is_reported_not_assumed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The import probe is the check, so a missing package cannot crash a run."""
    import builtins

    from picard_framework.analysis.phylodynamics import figures as fig

    real_import = builtins.__import__

    def fake_import(name: str, *args: Any, **kwargs: Any) -> Any:
        if name == "matplotlib":
            raise ImportError("no matplotlib")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", fake_import)
    assert fig.have_matplotlib() is False


def test_a_run_with_a_line_list_is_analysed_as_observed(out_root: Path) -> None:
    """The whole point: truth and observation are read from the same run."""
    source = out_root / "observed_run"
    source.mkdir()
    (source / "lineage_census.json").write_text(
        json.dumps(_payload(THREE_LINEAGES)), encoding="utf-8",
    )
    (source / "sentinel_line_list.json").write_text(
        json.dumps(
            {
                "voyage_id": "v1",
                "ship_id": "classic_cruise_1900",
                "n_passengers": 100,
                "n_crew": 20,
                "observation_end_epoch": 10,
                "clinical_cases": [_case("p1", 1, "GII.17")],
                "wastewater_samples": [_sample(1, [("GII.4", 80)])],
            },
        ),
        encoding="utf-8",
    )
    report = write_report(str(source), str(out_root / "observed_out"))
    assert report["arm"]["observed"] is True
    assert report["summary"]["detection"]["detected_fraction"] > 0.0


# ── campaign aggregation: arms are never pooled ─────────────────────────────


def _write_run_zip(root: Path, run_id: str, payload: dict[str, Any]) -> None:
    import zipfile

    with zipfile.ZipFile(root / f"{run_id}.zip", "w") as zf:
        zf.writestr(f"{run_id}/lineage_census.json", json.dumps(payload))


def test_the_incubation_arm_is_read_off_the_run_id() -> None:
    """PR 12 stamps the arm into the run id, so a result zip carries it."""
    from picard_framework.analysis.phylodynamics.campaign import (
        incubation_arm_of_run_id,
    )

    assert incubation_arm_of_run_id("vs1_diversity_hrs_dist_norovirus_s900") == (
        "distribution"
    )
    assert incubation_arm_of_run_id("vs1_diversity_hrs_fixed_norovirus_s900") == (
        "fixed_onset"
    )


def test_an_unlabelled_run_id_is_an_unknown_arm() -> None:
    """Unknown is a label, not a silent default into the drawn arm."""
    from picard_framework.analysis.phylodynamics.campaign import (
        ARM_UNKNOWN,
        incubation_arm_of_run_id,
    )

    assert incubation_arm_of_run_id("legacy_smoke_run") == ARM_UNKNOWN


def test_two_clock_arms_are_summarised_separately(out_root: Path) -> None:
    """The whole reason PR 12 labels runs: no mean may cross a clock arm."""
    from picard_framework.analysis.phylodynamics.campaign import write_campaign_tables

    results = out_root / "results"
    results.mkdir()
    _write_run_zip(results, "vs1_diversity_hrs_dist_norovirus_s900", _payload(THREE_LINEAGES))
    _write_run_zip(
        results,
        "vs1_diversity_legacy_dist_norovirus_s900",
        _payload(ONE_LINEAGE, clock="legacy_epoch_day", epoch_duration_hours=24.0),
    )
    out = out_root / "campaign_out"
    out.mkdir()
    manifest = write_campaign_tables(str(out), str(results))
    assert manifest["n_arms"] == 2
    arms = json.loads((out / "phylodynamic_arms.json").read_text(encoding="utf-8"))["arms"]
    assert all(summary["n_rows"] == 1 for summary in arms.values())


def test_campaign_rows_carry_the_arm_labels(out_root: Path) -> None:
    """A row that cannot name its arm cannot be filtered in analysis."""
    from picard_framework.analysis.phylodynamics.campaign import build_campaign_rows

    results = out_root / "results_rows"
    results.mkdir()
    _write_run_zip(results, "vs1_diversity_hrs_dist_norovirus_s900", _payload(THREE_LINEAGES))
    rows, unarmed = build_campaign_rows(str(results))
    assert unarmed == 0
    assert rows[0]["natural_history_clock"] == "hours"
    assert rows[0]["incubation_arm"] == "distribution"


def test_a_run_that_tracked_no_lineages_is_counted_not_fatal(out_root: Path) -> None:
    """Campaigns mix variant arms with arms that sequence nothing."""
    import zipfile

    from picard_framework.analysis.phylodynamics.campaign import build_campaign_rows

    results = out_root / "results_mixed"
    results.mkdir()
    with zipfile.ZipFile(results / "plain_run.zip", "w") as zf:
        zf.writestr("plain_run/summary.json", "{}")
    rows, unarmed = build_campaign_rows(str(results))
    assert (rows, unarmed) == ([], 1)


def test_a_campaign_with_no_armed_runs_writes_nothing(out_root: Path) -> None:
    """No census anywhere means no phylodynamic artefacts, not empty ones."""
    import zipfile

    from picard_framework.analysis.phylodynamics.campaign import write_campaign_tables

    results = out_root / "results_none"
    results.mkdir()
    with zipfile.ZipFile(results / "plain_run.zip", "w") as zf:
        zf.writestr("plain_run/summary.json", "{}")
    out = out_root / "none_out"
    out.mkdir()
    assert write_campaign_tables(str(out), str(results))["artifacts"] == {}
    assert not (out / "phylodynamic_runs.csv").exists()


def test_one_row_per_pathogen_per_run(out_root: Path) -> None:
    """A two-pathogen run yields two rows; averaging them would be pooling."""
    from picard_framework.analysis.phylodynamics.campaign import build_campaign_rows

    results = out_root / "results_two"
    results.mkdir()
    snapshots = [
        _snapshot(0, {"s0": 3}),
        _snapshot(0, {"s0": 2}, pathogen="sars_cov2_resp"),
    ]
    _write_run_zip(results, "vs1_diversity_hrs_dist_both_s900", _payload(snapshots))
    rows, _ = build_campaign_rows(str(results))
    assert sorted(row["pathogen_id"] for row in rows) == [
        "norwalk_gi",
        "sars_cov2_resp",
    ]


def test_a_richer_arm_reports_a_higher_mean_richness(out_root: Path) -> None:
    """Campaign aggregation must preserve the signal the runs carry."""
    from picard_framework.analysis.phylodynamics.campaign import (
        arm_summaries,
        build_campaign_rows,
    )

    results = out_root / "results_signal"
    results.mkdir()
    _write_run_zip(results, "vs1_diversity_hrs_dist_norovirus_s900", _payload(THREE_LINEAGES))
    _write_run_zip(results, "vs1_diversity_hrs_fixed_norovirus_s900", _payload(ONE_LINEAGE))
    rows, _ = build_campaign_rows(str(results))
    summaries = arm_summaries(rows)
    drawn = next(v for k, v in summaries.items() if "distribution" in k)
    fixed = next(v for k, v in summaries.items() if "fixed_onset" in k)
    assert drawn["mean_peak_richness"] > fixed["mean_peak_richness"]


def test_an_all_censored_arm_has_no_mean_lag(out_root: Path) -> None:
    """A missing mean is None, not a zero-hour detection lag."""
    from picard_framework.analysis.phylodynamics.campaign import (
        arm_summaries,
        build_campaign_rows,
    )

    results = out_root / "results_censored"
    results.mkdir()
    _write_run_zip(results, "vs1_diversity_hrs_dist_norovirus_s900", _payload(THREE_LINEAGES))
    rows, _ = build_campaign_rows(str(results))
    summary = next(iter(arm_summaries(rows).values()))
    assert summary["mean_median_detection_lag_hours"] is None
