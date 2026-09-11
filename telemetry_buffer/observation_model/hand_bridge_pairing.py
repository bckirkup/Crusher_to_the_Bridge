"""The hand release bridge, paired within Liu's own subjects -- a refutation, not a candidate.

`HAND_LOAD_LOG10_GEC` (3.86, Liu 2013) is read against
`HAND_LOAD_REFERENCE_PEAK_LOG10` (11.0), and their -7.14 difference is the
peak-normalised anchor ledger items 22(d), 23 and 24 record as a Class X
convention: 11.0 is the shipped curve's own peak (`max(SYMPTOMATIC_SHEDDING)`),
so `curve - 11.0` is the distance below the host's own peak and 3.86 is the
hand load AT peak -- the quantity Liu measures in the subjects she measures it
in. This harness computes the within-subject pairing Liu's Table 3 reports --
each subject's own maximum stool titre against that subject's own mean
positive hand load -- as the REFUTATION input, not a candidate offset:
applied to the shipped curve the -4.14 mean difference would put a peak-day
hand at 6.86 log10 GEC, above the largest per-subject mean Liu ever measured
(4.45), so the pairing contradicts the hand column it was read from. What
survives Table 3 is host-level carriage heterogeneity, which
HAND_CARRIAGE_PROPENSITY_BETA implements; the printed comparison below keeps
the -4.14 arm visible only as the record of the rejected value.

Definitional check, from Liu's Statistical analysis section, quoted verbatim:
"NV concentrations in stool samples and hand rinse samples were expressed as
log10 GEC per gram of feces and total log10 GEC per hand, respectively." The
numerator and the denominator are therefore the same unit class as the shipped
curve, which Atmar reports as genomic copies/g feces. No unit conversion is
applied or needed.

No anchor -- VSP, Park, A1-A5, the passenger/crew ratio -- is read anywhere in
this file, and nothing here is adopted: the engine constants are imported and
printed, never written.

Usage: python3 telemetry_buffer/observation_model/hand_bridge_pairing.py
"""

from __future__ import annotations

import math
import statistics
import sys
from pathlib import Path

from scipy.special import betainc

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from engines.infection_dynamics_bridge import (  # noqa: E402
    ALPHA,
    BETA,
    HAND_LOAD_LOG10_GEC,
    HAND_LOAD_REFERENCE_PEAK_LOG10,
    SYMPTOMATIC_SHEDDING,
)
from engines.transmission_core import (  # noqa: E402
    HAND_TO_MOUTH_NORMAL,
    MOUTH_CONTACT_FRACTION_RANGE,
)

# Liu et al. 2013, Appl Environ Microbiol 79:7875 (DOI 10.1128/AEM.02576-13),
# Table 3, read from the PMC3837815 full text. Six experimentally infected
# GI.1 (Norwalk) subjects. Columns: "Max titer (log10/g)" over the day 0-4
# sampling window, and "Mean log10 (no. of GEC/hand)" over that subject's
# positive rinses. `None` is a subject with no positive hand rinse, which is
# data -- two of six -- and not a missing value.
LIU_TABLE_3: tuple[tuple[int, float, float | None], ...] = (
    (34, 8.3, 3.94),
    (36, 8.1, 3.74),
    (37, 7.4, None),
    (40, 7.5, None),
    (46, 7.4, 3.30),
    (54, 8.2, 4.45),
)

# Liu, Results: 18/71 rinses from infected subjects positive at a combined-assay
# limit of detection of 2.15 log10 GEC per 50 ml rinse.
LIU_POSITIVE_RINSES = 18
LIU_TOTAL_RINSES = 71
LIU_POOLED_HAND_LOG10 = 3.86

# Atmar et al. 2008, Emerg Infect Dis 14:1553, abstract and Results: median
# peak 95e9 genomic copies/g faeces, range 0.5e9-1640e9. This is the source of
# the shipped curve (see SYMPTOMATIC_SHEDDING's provenance comment).
ATMAR_PEAK_MEDIAN_LOG10 = math.log10(95e9)
ATMAR_PEAK_MIN_LOG10 = math.log10(0.5e9)
ATMAR_PEAK_MAX_LOG10 = math.log10(1640e9)

# Comparison arms for the donor->recipient hand transfer step, carried over
# unchanged from `direct_contact_hand_composition.md`. Tranche 12 returned a
# literature null for person-to-person transfer, so these are explicit
# analogies used to bracket an ordering. NOT adopted constants.
TRANSFER_ARMS = (0.30, 0.13, 0.01)

HOURS_PER_DAY = 24.0


def _hand_to_mouth_midpoint() -> float:
    """Shipped hand-to-mouth ingestion fraction at its central values."""
    used_fraction = sum(MOUTH_CONTACT_FRACTION_RANGE) / 2.0
    return used_fraction * HAND_TO_MOUTH_NORMAL[0]


def _p_infection(dose: float) -> float:
    """Shipped Teunis hypergeometric dose-response."""
    if dose <= 0.0:
        return 0.0
    return 1.0 - math.pow(1.0 + dose / BETA, -ALPHA)


def _paired_rows() -> tuple[tuple[int, float, float], ...]:
    """Subjects with both a stool titre and a positive hand load."""
    return tuple(
        (sid, stool, hand)
        for sid, stool, hand in LIU_TABLE_3
        if hand is not None
    )


def _ols(xs: list[float], ys: list[float]) -> tuple[float, float, float]:
    """Slope, intercept and Pearson r for a paired sample."""
    mx = statistics.fmean(xs)
    my = statistics.fmean(ys)
    sxy = sum((x - mx) * (y - my) for x, y in zip(xs, ys, strict=True))
    sxx = sum((x - mx) ** 2 for x in xs)
    syy = sum((y - my) ** 2 for y in ys)
    slope = sxy / sxx
    r = sxy / math.sqrt(sxx * syy)
    return slope, my - slope * mx, r


def _two_sided_p(r: float, n: int) -> float:
    """Two-sided Student-t p-value for a Pearson correlation."""
    df = n - 2
    if df <= 0 or abs(r) >= 1.0:
        return float("nan")
    t = abs(r) * math.sqrt(df / (1.0 - r * r))
    # Two-sided tail of t_df is the regularised incomplete beta
    # I_x(df/2, 1/2) evaluated at x = df / (df + t^2).
    return float(betainc(df / 2.0, 0.5, df / (df + t * t)))


def report_bridge() -> tuple[float, float, float]:
    """Print the within-subject bridge and return mean, min and max."""
    rows = _paired_rows()
    bridges = [hand - stool for _, stool, hand in rows]
    mean_bridge = statistics.fmean(bridges)

    print("=" * 74)
    print("LIU TABLE 3, PAIRED WITHIN SUBJECT")
    print("=" * 74)
    print(f"{'subject':>8}  {'max stool':>10}  {'mean hand':>10}  {'bridge':>8}")
    print(f"{'':>8}  {'log10/g':>10}  {'log10/hand':>10}  {'log10 g':>8}")
    for (sid, stool, hand), bridge in zip(rows, bridges, strict=True):
        print(f"{sid:>8}  {stool:>10.2f}  {hand:>10.2f}  {bridge:>8.2f}")
    for sid, stool, hand in LIU_TABLE_3:
        if hand is None:
            print(f"{sid:>8}  {stool:>10.2f}  {'no positive':>10}  {'--':>8}")

    print()
    print(f"within-subject bridge   mean {mean_bridge:+.2f} log10 g/hand")
    print(
        f"                        range {min(bridges):+.2f} .. "
        f"{max(bridges):+.2f}  (SD {statistics.stdev(bridges):.2f}, "
        f"n = {len(bridges)} subjects)",
    )
    shipped = HAND_LOAD_LOG10_GEC - HAND_LOAD_REFERENCE_PEAK_LOG10
    print(f"shipped anchor          {shipped:+.2f} log10 g/hand")
    print(
        f"                        = {HAND_LOAD_LOG10_GEC:.2f} (Liu, hands) "
        f"- {HAND_LOAD_REFERENCE_PEAK_LOG10:.2f} (shipped curve's own peak)",
    )
    print(f"difference              {mean_bridge - shipped:+.2f} log10")
    print(
        "  REFUTED as an engine offset: shipped onto the curve it predicts "
        f"{11.0 + mean_bridge:.2f} log10 GEC/hand at peak,",
    )
    print("  above Liu's largest measured per-subject mean (4.45).")
    return mean_bridge, min(bridges), max(bridges)


def report_scaling() -> None:
    """Report the paired log-log slope, which does not reach the form the engine assumes."""
    rows = _paired_rows()
    xs = [stool for _, stool, _ in rows]
    ys = [hand for _, _, hand in rows]
    slope, intercept, r = _ols(xs, ys)
    p = _two_sided_p(r, len(rows))

    print()
    print("=" * 74)
    print("A SLOPE THAT IS NOT A TEST OF THE SCALING ASSUMPTION")
    print("=" * 74)
    print("The engine assumes hand load tracks the stool titre one-for-one:")
    print("  hand_gec = 10^HAND_LOAD_LOG10_GEC * 10^(curve - REFERENCE_PEAK)")
    print("which is a log-log slope of exactly 1.")
    print()
    print(f"  OLS slope   {slope:+.2f} log10 hand per log10 stool")
    print(f"  intercept   {intercept:+.2f}")
    print(f"  Pearson r   {r:+.2f}   n = {len(rows)} subjects   p = {p:.2f}")
    print()
    print("  But this slope is ACROSS subjects, each at its own peak -- a")
    print("  between-subject level relation, not a within-host time course.")
    print("  It never tested the engine's curve-tracking assumption.")


def report_cohort_gap() -> None:
    """The 3-log discrepancy the shipped pairing spans."""
    stools = [stool for _, stool, _ in LIU_TABLE_3]
    print()
    print("=" * 74)
    print("WHAT THE SHIPPED PAIRING SPANS")
    print("=" * 74)
    print(
        f"Liu, max stool titre over day 0-4   "
        f"{min(stools):.1f} .. {max(stools):.1f} log10 GEC/g  (n = 6)",
    )
    print(
        f"Atmar, peak stool titre             "
        f"{ATMAR_PEAK_MIN_LOG10:.1f} .. {ATMAR_PEAK_MAX_LOG10:.1f} log10 "
        f"copies/g  (n = 16, median {ATMAR_PEAK_MEDIAN_LOG10:.1f})",
    )
    print(f"shipped curve peak                  {max(SYMPTOMATIC_SHEDDING):.1f}")
    print()
    print(
        f"Every one of Liu's six maxima is below Atmar's minimum "
        f"({ATMAR_PEAK_MIN_LOG10:.1f}); the gap to Atmar's median is "
        f"{ATMAR_PEAK_MEDIAN_LOG10 - max(stools):.1f}-"
        f"{ATMAR_PEAK_MEDIAN_LOG10 - min(stools):.1f} log10.",
    )
    print("Both report the same unit on the same genogroup by RT-qPCR, so this")
    print("is a cohort or assay-standard discrepancy, not a unit error. Two")
    print("bounds act on it in opposite directions and neither is quantified:")
    print("  - Liu's window is day 0-4, while Atmar's peak falls at a median of")
    print("    day 4 and was highest after symptom resolution in 11/16")
    print("    subjects, so Liu's maxima are lower bounds on those subjects'")
    print("    peaks. This biases the within-subject bridge HIGH.")
    print("  - Hand rinse recovery efficiency is unmeasured, so 3.86 is a lower")
    print("    bound on what was on the hand. This biases the bridge LOW.")


def report_composed_contact(mean_bridge: float) -> None:
    """Per-contact dose and establishment probability under each bridge."""
    peak = max(SYMPTOMATIC_SHEDDING)
    h2m = _hand_to_mouth_midpoint()
    shipped_bridge = HAND_LOAD_LOG10_GEC - HAND_LOAD_REFERENCE_PEAK_LOG10

    print()
    print("=" * 74)
    print("A HAND-COMPOSED CONTACT AT THE CURVE PEAK, SHIPPED VS REFUTED")
    print("=" * 74)
    print(f"curve peak {peak:.1f} log10 GEC/g; hand-to-mouth midpoint {h2m:.5f}")
    print("Transfer arms are explicit analogies over a literature null.")
    print("The Liu-paired column is the refutation record, not a candidate.")
    print()
    header = (
        f"{'bridge':>8}  {'hand load':>11}  {'transfer':>8}  "
        f"{'ingested':>10}  {'P(inf)':>7}"
    )
    for label, bridge in (
        ("shipped", shipped_bridge),
        ("refuted", mean_bridge),
    ):
        hand_load = math.pow(10.0, peak + bridge)
        print(f"-- {label}, bridge {bridge:+.2f} log10 g/hand")
        print(header)
        for arm in TRANSFER_ARMS:
            dose = hand_load * arm * h2m
            print(
                f"{bridge:>8.2f}  {hand_load:>11.3e}  {arm:>8.2f}  "
                f"{dose:>10.3e}  {_p_infection(dose):>7.4f}",
            )
        print()

    print("For the same contact, the uncomposed route the engine ships today:")
    emission = math.pow(10.0, peak - 4.0) / HOURS_PER_DAY
    shipped_dose = 0.35 * emission
    print(
        f"  whole-body emission x route efficiency = {shipped_dose:.3e} GEC, "
        f"P(inf) {_p_infection(shipped_dose):.4f}",
    )
    print()
    print("The composed route's dose stands on the shipped anchor; the")
    print("Liu-paired offset is not a value the model can carry -- it would")
    print("put every peak-day hand above every hand Liu measured.")


def report_intermittency() -> None:
    """The part of Liu's table that is not a level at all."""
    positivity = LIU_POSITIVE_RINSES / LIU_TOTAL_RINSES
    never = sum(1 for _, _, hand in LIU_TABLE_3 if hand is None)
    print()
    print("=" * 74)
    print("WHAT LIU MEASURES THAT IS NOT A LEVEL")
    print("=" * 74)
    print(
        f"rinse positivity, symptomatic stool-positive hosts   "
        f"{LIU_POSITIVE_RINSES}/{LIU_TOTAL_RINSES} = {positivity:.1%}",
    )
    print(
        f"infected subjects never hand-positive                "
        f"{never}/{len(LIU_TABLE_3)}",
    )
    print("per-subject positivity                               0% .. 54.5%")
    print()
    print("These are properties of the process, not of its mean, and they")
    print("survive whatever the bridge turns out to be: a composed hand route")
    print("carries nothing on roughly three contacts in four, and a third of")
    print("shedding hosts never present a positive hand at all. The engine's")
    print("non-event hand mode -- every shedding host at the ceiling every")
    print("epoch -- cannot express either, which is ledger item 24(c).")


def main() -> None:
    mean_bridge, _, _ = report_bridge()
    report_scaling()
    report_cohort_gap()
    report_composed_contact(mean_bridge)
    report_intermittency()
    print()
    print("=" * 74)
    print("Nothing above is adopted. No constant, interval or default moved.")
    print("=" * 74)


if __name__ == "__main__":
    main()
