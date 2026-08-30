"""What the COVID-discontinuity estimator recovers, against a known answer.

The VSP series is a *posted* sample: CDC publishes a voyage when 3% or more of
passengers or crew report AGE. That truncation interacts with the quantity being
measured, so before any of these statistics can be pointed at the model they
have to be run against synthetic voyages whose true era shift is known.

These tests are the source of the bias figures quoted in
`telemetry_buffer/observation_model/vsp_covid_discontinuity_design.md` §7. They
assert the properties the design relies on, not the exact numbers.

The generator is deliberately not the ship model: lognormal passenger attack
rates, crew rates a fixed share of passenger rates with a tunable correlation,
and the published posting rule. Its only job is to have a known answer.
"""

from __future__ import annotations

import importlib.util
import random
import statistics
import sys
from pathlib import Path
from types import ModuleType

import pytest

HARNESS = (
    Path(__file__).resolve().parents[1]
    / "telemetry_buffer"
    / "observation_model"
    / "vsp_discontinuity_analysis.py"
)

# Posting rule: 3% of passengers or crew reporting to medical staff.
POSTING_THRESHOLD_PCT = 3.0
# Passenger attack rates over posted outbreaks are right-skewed with a median
# near 6%; these lognormal parameters put the synthetic median and tail in that
# neighbourhood so the truncation bites the way it bites the real sample.
LOG_MEAN = 1.7
LOG_SIGMA = 0.55
CREW_SHARE = 1.0 / 2.9  # A5's passenger/crew ratio, as a plausible baseline.
# Large enough that what the assertions see is bias rather than noise.
ASYMPTOTIC_N = 20000


def _load_harness() -> ModuleType:
    spec = importlib.util.spec_from_file_location("vsp_discontinuity_analysis", HARNESS)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    # `dataclass` resolves annotations through `sys.modules`, so the module has
    # to be registered before its body runs.
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


analysis = _load_harness()


def _posted_voyages(
    *,
    n: int,
    era: str,
    pax_multiplier: float,
    crew_multiplier: float,
    correlation: float,
    seed: int,
) -> list:
    """`n` synthetic voyages that pass the posting rule.

    `correlation` = 1 makes crew rates track passenger rates exactly within a
    voyage; 0 draws them independently. The real dependence is unknown, which is
    why the design has to hold across the range.
    """
    rng = random.Random(seed)
    posted = []
    while len(posted) < n:
        shared = rng.lognormvariate(LOG_MEAN, LOG_SIGMA)
        independent = rng.lognormvariate(LOG_MEAN, LOG_SIGMA)
        pax = shared * pax_multiplier
        crew_latent = correlation * shared + (1.0 - correlation) * independent
        crew = crew_latent * CREW_SHARE * crew_multiplier
        if max(pax, crew) < POSTING_THRESHOLD_PCT:
            continue
        posted.append(
            analysis.Outbreak(
                year=2015 if era == "pre" else 2024,
                era=era,
                agent="norovirus",
                pax_rate=pax,
                crew_rate=crew,
            )
        )
    return posted


def _arms(
    pax_multiplier: float,
    crew_multiplier: float,
    correlation: float,
    n: int = ASYMPTOTIC_N,
) -> tuple[list, list]:
    pre = _posted_voyages(
        n=n,
        era="pre",
        pax_multiplier=1.0,
        crew_multiplier=1.0,
        correlation=correlation,
        seed=7,
    )
    post = _posted_voyages(
        n=n,
        era="post",
        pax_multiplier=pax_multiplier,
        crew_multiplier=crew_multiplier,
        correlation=correlation,
        seed=9,
    )
    return pre, post


def _statistic(key: str, pre: list, post: list) -> float:
    value = analysis.STATISTICS[key](pre, post)
    assert value is not None
    return value


def test_null_era_shift_recovers_unity() -> None:
    """With nothing changed, every ratio must read 1, truncation notwithstanding."""
    pre, post = _arms(1.0, 1.0, 0.7)
    for key in ("A7a_pax_median_ratio", "A7b_crew_median_ratio", "A7c_did_pax_over_crew"):
        assert _statistic(key, pre, post) == pytest.approx(1.0, abs=0.02)


@pytest.mark.parametrize("correlation", [1.0, 0.7, 0.0])
def test_level_ratio_is_attenuated_by_the_posting_floor(correlation: float) -> None:
    """A7a understates a real shift, because the floor removes what moved below it.

    This is why "posted rates fell x%" may not be read as "transmission fell
    x%", and why the model is filtered rather than the observation corrected.
    """
    pre, post = _arms(0.8, 1.0, correlation)
    measured = _statistic("A7a_pax_median_ratio", pre, post)
    assert 0.8 < measured < 0.92


@pytest.mark.parametrize("correlation", [1.0, 0.7, 0.0])
def test_crew_ratio_rises_when_crew_did_not_move(correlation: float) -> None:
    """A7b above 1 is an artifact of selection, not crew faring worse.

    When passenger rates fall, posting increasingly depends on the crew arm
    clearing 3%, which selects high-crew voyages into the sample.
    """
    pre, post = _arms(0.8, 1.0, correlation)
    assert _statistic("A7b_crew_median_ratio", pre, post) > 1.0


@pytest.mark.parametrize(
    ("pax_multiplier", "crew_multiplier"),
    [(0.8, 1.0), (0.8, 0.8), (0.65, 0.9)],
)
def test_did_recovers_the_passenger_specific_shift(
    pax_multiplier: float,
    crew_multiplier: float,
) -> None:
    """A7c is the identified quantity: exact when the arms move together.

    Its residual error is the untruncated crew arm, bounded below.
    """
    pre, post = _arms(pax_multiplier, crew_multiplier, 1.0)
    truth = pax_multiplier / crew_multiplier
    assert _statistic("A7c_did_pax_over_crew", pre, post) == pytest.approx(
        truth, rel=0.02
    )


def test_did_residual_stays_small_across_unknown_arm_dependence() -> None:
    """The dependence between the arms is unknown, so the bound must hold for all of it.

    5% relative is the budget: any measured A7c within 5% of 1 is not evidence
    of a passenger-specific effect on its own.
    """
    truth = 0.8
    for correlation in (1.0, 0.7, 0.0):
        pre, post = _arms(truth, 1.0, correlation)
        measured = _statistic("A7c_did_pax_over_crew", pre, post)
        assert abs(measured - truth) / truth < 0.05


def test_tail_ratio_is_not_a_bootstrap_statistic() -> None:
    """The reason A7d is not in STATISTICS, asserted rather than asserted-in-prose.

    At the real sample size the post-era tail above 15% can be empty. Every
    resample of an empty tail is empty, so a percentile interval on the ratio
    collapses to a point at 0 — an interval that excludes 1 and would read as a
    decisive collapse while resting on zero observations. Exact intervals on the
    counts are used instead.
    """
    assert "A7d_tail_share_ratio" not in analysis.STATISTICS
    pre, post = _arms(0.8, 1.0, 0.7, n=64)
    assert analysis._tail_share(post, analysis.TAIL_THRESHOLD_PCT) == pytest.approx(0.0)
    rng = random.Random(analysis.SEED)
    degenerate = analysis.bootstrap_interval(
        lambda a, b: analysis._ratio(
            analysis._tail_share(b, analysis.TAIL_THRESHOLD_PCT),
            analysis._tail_share(a, analysis.TAIL_THRESHOLD_PCT),
        ),
        pre,
        post,
        rng,
    )
    assert degenerate == (0.0, 0.0)


def test_exact_tail_test_is_honest_about_an_empty_tail() -> None:
    """Fisher's exact test on the tail counts does not call an empty tail decisive."""
    # 13 of 261 pre-era voyages above the threshold, none of 64 post-era: the
    # shape of the real comparison. Suggestive, not significant.
    p_empty = analysis.fisher_exact_p(13, 261, 0, 64)
    assert 0.05 < p_empty < 0.5
    # The same pre-era tail against a post era that kept it: no signal at all.
    assert analysis.fisher_exact_p(13, 261, 3, 64) > 0.5
    # A tail that genuinely vanishes from a large post-era sample does register.
    assert analysis.fisher_exact_p(13, 261, 0, 400) < 0.01
    # Symmetric margins, identical shares: p must be 1.
    assert analysis.fisher_exact_p(10, 100, 10, 100) == pytest.approx(1.0, abs=1e-9)


def test_wilson_interval_covers_zero_and_unity() -> None:
    low, high = analysis.wilson_interval(0, 64)
    assert low == pytest.approx(0.0)
    assert 0.0 < high < 0.1
    low, high = analysis.wilson_interval(64, 64)
    assert high == pytest.approx(1.0)
    assert 0.9 < low < 1.0
    assert analysis.wilson_interval(0, 0) is None


def test_bootstrap_interval_covers_the_truth_at_the_real_sample_size() -> None:
    """The interval is what the model is scored against, so it has to cover."""
    truth = 0.8
    pre = _posted_voyages(
        n=261, era="pre", pax_multiplier=1.0, crew_multiplier=1.0,
        correlation=1.0, seed=7,
    )
    post = _posted_voyages(
        n=64, era="post", pax_multiplier=truth, crew_multiplier=1.0,
        correlation=1.0, seed=9,
    )
    rng = random.Random(analysis.SEED)
    interval = analysis.bootstrap_interval(
        analysis.STATISTICS["A7c_did_pax_over_crew"], pre, post, rng
    )
    assert interval is not None
    assert interval[0] <= truth <= interval[1]


def test_loader_recomputes_rates_and_tolerates_missing_crew(tmp_path: Path) -> None:
    """Counts are authoritative over the page's printed percentage, and crew may be absent."""
    csv_path = tmp_path / "series.csv"
    csv_path.write_text(
        "year,cruise_line,ship,voyage_dates_raw,voyage_end,causative_agent,"
        "pax_ill,pax_total,pax_pct_page,crew_ill,crew_total,crew_pct_page,"
        "era,source_url,retrieved\n"
        "2015,x,y,,,Norovirus,135,1318,10.24,12,600,2.00,pre,u,2026-08-30\n"
        "2024,x,y,,,norovirus,134,3914,3.4,,,,post,u,2026-08-30\n"
        "2024,x,y,,,unknown,,,,7,1266,0.6,post,u,2026-08-30\n",
        encoding="utf-8",
    )
    outbreaks = analysis.load_series(csv_path)
    assert len(outbreaks) == 2, "a row with no passenger counts carries no rate"
    assert outbreaks[0].pax_rate == pytest.approx(10.2428, abs=1e-3)
    assert outbreaks[0].agent == "norovirus"
    assert outbreaks[1].crew_rate is None
    assert statistics.median([o.pax_rate for o in outbreaks]) > 3.0


def test_report_covers_arm_summaries_and_yearly_breakdown() -> None:
    """The published report includes summaries, intervals, and yearly counts."""
    outbreaks = [
        analysis.Outbreak(2015, "pre", "norovirus", 5.0, 2.0, 1200),
        analysis.Outbreak(2016, "pre", "unknown", 16.0, 4.0, 1400),
        analysis.Outbreak(2024, "post", "norovirus", 4.0, 3.0, 1300),
        analysis.Outbreak(2025, "post", "unknown", 20.0, None, 1500),
    ]
    report = analysis.build_report(outbreaks)
    assert "A7a_pax_median_ratio" in report
    assert "A7d, the upper tail" in report
    assert "| 2015 | 1 | 1 | 1.00 |" in report
    assert "| 2025 | 1 | 0 | 0.00 |" in report


def test_empty_and_degenerate_statistics_are_reportable() -> None:
    """Undefined statistics remain explicit rather than being coerced to zero."""
    assert analysis._describe_arm("empty", []) == [
        "- **empty**: no posted outbreaks with passenger counts."
    ]
    assert analysis._format_statistic("A7x", None, None, None).endswith(
        "| undefined | | |"
    )
    assert analysis.permutation_p(
        analysis.STATISTICS["A7a_pax_median_ratio"],
        [],
        [],
        random.Random(analysis.SEED),
    ) is None
