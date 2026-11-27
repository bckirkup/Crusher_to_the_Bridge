# DP-UNION-02-DESIGN-REVIEW-01
**Date:** 2026-11-27
**Commit:** 3fe48d8b1916e1c06cdc92cc2d9c757574f9c53b
**Pathogens:** sars_cov2_resp
**Status:** measured
**Measured at:** f585f710299040c374a02e94fe1afa563cb90f74

Bounded design review of the post-shape DP-UNION-02 union arm after the
authorized theta `1e8` canary. No new voyage simulation, AWS execution, GM/H5
validation, constant fitting, or lattice cell is part of this entry. Evidence
is the frozen design (`docs/covid/covid_dp_union_02_design.md`), machine design
(`picard_framework/runs/covid_dp_union_02_design.json`), execution ledger
(`campaigns/covid/dp_union_02/LEDGER.md`), canonical readout
(`docs/covid/dp_union_02_union_t1e8_canary_readout.json`), the 20 synced
artifacts under `out/dp_union02_canary_sync/union_t1e8_canary/`, and the
pre-existing measurement ledgers named below. Local artifact inspection was
read-only.

## Verdict

The theta `1e8` canary is a clean measurement of one badly inconsistent cell,
not evidence that the union arm is impossible at every theta. Mechanically,
the artifacts and merged readout agree: the conditioned seeds ignite, almost
all incidence occurs before quarantine, almost none occurs during quarantine,
and the testing legs land far below target even though the day-31 specimen
denominator is exactly reproduced. The canary therefore rules out theta `1e8`
under the frozen joint contract, but it does not separate theta mis-scale
from the post-shape early-generation structure, and it does not justify
invoking a new biological mechanism before the declared cross-decade pilot.
The weakest-assumption next step is to repair the two readout/design
mismatches without moving any scored threshold, then complete the already
frozen 30-cell pilot (25 cells remain unrun) and stop. A broader
observational-architecture correction is a real open design question, but it
was already measured in the pre-shape ascertainment campaign and must not be
silently substituted into DP-UNION-02 after seeing this canary.

## What is measured, inferred, and hypothetical

### Measured

All canary measurements below are at `Measured at`
`f585f710299040c374a02e94fe1afa563cb90f74`, theta `1e8`, arm `union_niid`,
the first 20 frozen seeds, image digest
`sha256:40b95eb4b84c681ce0fb4020cbb0b11fc751c9b7a677d3109b40c80f7405b3e9`:

- all 20 artifacts are audit-clean and have `index_shedding_at_day0` true;
  the canonical readout path is
  `docs/covid/dp_union_02_union_t1e8_canary_readout.json`;
- medians: ignition day 1, before-share 0.9833114203981133,
  infections 3255.5, during-quarantine infections 1.5, conditioned capture
  0.6047256797732786, P31/P34 positives 188.5;
- per-seed ranges are one-sided and narrow: infections 3218-3302,
  during-quarantine 0-5, capture 0.429-0.732, before-share 0.974-0.988,
  P31/P34 156-229;
- median specimens through day 31 are exactly 3063 and through day 34 are
  3586 in the canonical readout; the low positive count is not a missing
  published-volume test denominator;
- median day-0-through-day-4 acquisition mass is 3080.5, median 94.47% of
  total infections (per-seed range 83.03%-98.36%), computed directly from
  each artifact's `acquisition_curve.total_by_day`; testing starts on day 16;
- median recorded onsets 1755.5, of which 1722.5 are before the split day;
  the artifact echo `onset_recording` is null;
- median `lab_confirmed_total` is 1959.0 while median campaign positives are
  188.5; the median outside-campaign confirmation count is therefore
  1769.5, or 90.1% of lab confirmations when campaign positives are treated
  as the campaign subset;
- crew duty exclusion removes a median 703.5 hosts and median realized
  working exempt share at activation is 0.0086; implementation reads duty
  exclusion through `quarantined_ids`, so this small working share is not by
  itself evidence that the quartermaster exemption draw failed;
- the day-34 crew wave adds zero positive specimens on 19 of 20 measured
  cells and one positive specimen on the remaining cell; the median wave
  increment is zero, and the median crew-wave specimen count is 523, within
  the 831 cap.

Pre-existing measured context, independent of this canary:

- `COVID-ONSET-FUNNEL-01` measured 86% of Diamond Princess confirmations on
  the passive sick-call-to-lab channel outside the published specimen
  volumes on the pre-shape replay operating point, with campaign-positive
  composition distorted accordingly;
- `ASCERTAIN-V1` measured that onset-recording arms can move the recorded
  onset count but do not move infections or before-share materially; its
  truth/timing residual remained infections about 3.5-4x the serology band
  and before-share about 0.6-0.84 versus 0.173 on that older configuration;
- `ONSET-REC-01` measured the frozen period onset-recording channel as
  channel-insufficient by itself;
- `DP-UNION-01` already measured T3 compression/nonmonotonicity near high
  incidence: pilot medians rose then fell across theta, and no consistent
  theta existed under the pre-shape law.

### Inferred

- The coherent early-burn-out interpretation remains an inference, not a
  mechanism attribution: early incidence, very low during-quarantine
  incidence, low old-infection PCR capture, and low campaign positives are
  correlated legs of one timing pattern.
- Low measured positives despite high incidence are plausibly produced by
  the joint observation process: most infections are days 0-4, the first
  published test day is day 16, and the declared Kucirka sensitivity curve
  has already fallen from its day-8 peak by those infection ages. This
  artifact set does not preserve enough per-specimen infection-age detail
  to quantify the exact fraction attributable to sensitivity decline versus
  passive-channel skimming.
- Theta mis-scale is a plausible partial explanation for the size legs:
  theta is still the composite emission scale times per-copy risk, and the
  post-shape law re-denominates daily emission even though normalized
  lifetime area is nearly unchanged. A lower lattice row may move attack
  and during incidence in the right direction. That would be grid location,
  not a structural repair.
- Ascertainment conditioning is intentional but consequential. Scoring is
  conditional on actual day-0 index emission at onset-relative day about
  -3; it is not an unconditional index-introduction experiment. At theta
  `1e8`, founder-class conditioning no longer discriminates because every
  measured seed has thousands of day-0-through-day-4 acquisitions.

### Hypothesis

- The Zhou zero-inflated onset-negative support, high/low emitter mixture,
  and dose-dependent incubation shortening may together make generation
  time too short under the post-shape law. This is biologically plausible
  but unmeasured in the canary artifacts.
- The missing routine-stage growth coolant or participation structure may
  still be required. The canary is consistent with that suspicion but does
  not prove it, because only one theta ran.
- RNA emission in the Zhou mask shape may overstate viable-virus emission
  early in infection. That is a source-law interpretation question, not a
  measured defect of the implementation.

## Machinery/readout audit

No artifact/readout contradiction was found. The compact artifacts and the
merged readout agree on the inspected aggregates. The correct design,
theta, arm, seed cohort, index geometry, protocol, testing wave, retest
switches, duty exclusion, and capture blocks resolve. The specimen-count
denominator is present by construction.

Two readout/design mismatches are measured and must be repaired or explicitly
re-frozen before any further row is interpreted:

1. **Dead-row definition.** DP-UNION-02 freezes `dead` as at least 20 of 24
   seeds with no aboard-window acquisitions
   (`docs/covid/covid_dp_union_02_design.md`), while the inherited readout
   implements DP-UNION-01's `P31 == 0` test. This does not change the theta
   `1e8` verdict: every measured seed has both positive P31 and thousands of
   aboard-window acquisitions. It does matter for low-theta pilot edge
   classification.
2. **Representativeness formula.** DP-UNION-02's text describes an attack
   representativeness flag, while the inherited implementation applies the
   legacy FIT-01 P31 band `[317, 1268]`. The flag is report-only and changes
   no pass/fail leg, so it did not alter the canary result, but the current
   wording/implementation pair is not a frozen criterion. The minimum repair
   is to freeze the legacy P31 diagnostic in the design text rather than
   invent a new report-only statistic.

A third issue is not a readout implementation error but a comparator
limitation: `campaign_specimen_log` contains only specimens represented in
the published campaign roster, while `lab_confirmed_total` pools passive
sick-call specimens as well. In the canary, outside-campaign confirmations
are about 90% of all confirmations. This architecture was already measured
in `COVID-ONSET-FUNNEL-01`; it means low T3/P34 cannot be read as low
incidence, and high incidence does not imply high campaign positives. It is
part of the model/observation design the union arm inherited, not evidence
that the DP-UNION-02 readout failed to score its declared blocks.

## Ascertainment and onset geometry audit

The seed cohort did what the design says: the probe selected the first 24
positive-emission candidates before outcome scoring, every scored artifact
audits `index_shedding_at_day0` true, and the patched NIID onset geometry is
present. This is not a machinery failure.

It is nevertheless a different experiment from an unconditional physical
introduction. The conditioning guarantees emission on a low-probability
onset-negative day (the day -3 row has occurrence probability 0.1) and then
asks what outbreak follows. That is the owner-approved ascertainment-event
class from `COVID-SEED-ASCERTAIN-01`, but it bounds interpretation: theta
measured here is conditional on that event class and cannot be quoted as an
unconditional introduction-scale constant.

The onset channel is weaker. The artifact echo shows no `onset_recording`
block, and median recorded onsets are 1755.5 against the record's 197 dated
onsets. The contract's before-share leg is therefore not a strict comparison
of like-for-like dating channels. However, `ASCERTAIN-V1` already measured
that arming the existing recording channel does not repair before-share or
truth incidence; that prior measurement limits how much of the present
failure can be attributed to onset recording alone.

## Emission timing and testing capture audit

The shape implementation matches its documented mechanics: occurrence is
zero-inflated by onset-relative day, conditional positive mass is separate,
support extends from day -5 through day +13, emission is clamped at the
acquisition epoch, and high/low multipliers are persistent and mean-one.
The implementation is therefore not obviously scoring the wrong emission
law.

The timing consequence is large. Under the legacy smooth curve, pre-onset
emission was effectively negligible; under the active Zhou shape the
expected onset-negative linear mass share is explicitly documented as about
16.8%, with day -2 carrying conditional peak mass when it occurs. The
conditioned index emits at boarding on day -3, and subsequent infections can
emit before their own onset. This can produce fast early amplification even
when normalized lifetime area is nearly unchanged.

Testing then arrives late relative to the measured incidence. Median 94.47%
of infections are already acquired by day 4, while the campaign starts day
16. By then those infections are roughly 12-21 days post infection over the
main campaign window. The declared PCR sensitivity curve peaks at day 8
(0.8) and declines to 0.517, 0.375, and 0.34 at days 16, 20, and 21. Finite
daily capacity, one-specimen/retest rules, and passive prior confirmation
further restrict who remains swabbable. Low positives with high cumulative
incidence are therefore an expected geometry of this experiment, not a
paradox. Exact attribution cannot be recovered from the compact artifacts
because bulky specimen/funnel echoes are dropped by design.

## Theta denomination assessment

Theta `1e8` is not a fitted operating point and was not selected by the
post-shape pilot; it is one authorized canary cell. The measurement says
that this row is far too hot on truth incidence and far too early on timing.
It does not say the lattice is hopeless.

The normalized lifetime-area ratio of new to old shape is about 1.0262, but
that is not a conversion factor. Zero inflation concentrates emission into
stochastic positive days, the negative-onset support moves some emission
earlier, the persistent high/low mixture changes who transmits, and the
seed cohort conditions on one early positive day. A theta row lower in the
already declared grid is therefore a legitimate test of mis-scale. Moving
down the grid is not a structural fix and must not be reported as one; it is
only evidence about the composite's denomination.

## Ranked explanations, weakest assumption first

1. **Readout edge-definition mismatches.** Real, small, and repairable; no
   effect on the theta `1e8` median verdict, material for pilot edges.
2. **Theta mis-scale.** Untested and plausible for attack/during magnitude.
   Only the frozen cross-decade pilot can measure it without inventing a
   mechanism.
3. **Observation/ascertainment comparator mismatch.** Real and previously
   measured: passive confirmations outside published volumes, missing onset
   recording in the arm, and one-specimen/retest dynamics make T3/P34 a
   compressed ascertainment observable. This explains why T3 must not be
   read as incidence, but prior ASCERTAIN-V1 evidence says it cannot by
   itself repair truth timing or attack size.
4. **Post-shape early-generation structure.** Plausible and strongly
   suggested by the timing pattern: zero-inflated pre-onset emission,
   ascertainment-conditioned day-0 emission, and dose-shortened incubation
   can burn the ship before quarantine. Not yet proven at other theta.
5. **Missing participation/routine-stage coolant or another structural
   transmission mechanism.** Still possible, especially if the pilot shows
   only dead/saturated or early-burning rows. Invoking it from one theta is
   over-attribution.

## Recommended single next step

**Complete the already frozen DP-UNION-02 cross-decade pilot, after an
audit-only readout repair, and stop at its readout.** The first five theta
`1e8` artifacts are already exactly that decade's pilot slice, so the
remaining execution is five seeds at each of the five unrun decade values:
25 new cells, not 30. Do not redesign the scored contract, rerun theta
`1e8`, run `_rest`, submit any 20-seed canary, or implement a new biological
mechanism in that step.

Frozen admissibility criteria before any pilot cell runs:

1. The readout implements the frozen design text's dead-row rule:
   `aboard_window_acquisitions == 0` on at least 20 of 24 seeds. No scored
   threshold or target moves.
2. The design text is corrected to name the inherited report-only
   representativeness diagnostic exactly: fewer than 6 of 24 seeds with P31
   in `[317, 1268]` labels the row `median_not_representative`. Because it
   is report-only, this repair must not change any pass/fail criterion.
3. The pilot is exactly the first five frozen conditioned seeds at each of
   the six already declared decade lattice values (`1e5` through `1e10`),
   arm `union_niid`: 30 cells total, of which the five theta `1e8` cells
   already exist and only 25 cells remain to run. No other theta, arm, seed,
   or mechanism variant is added.
4. Every cell must pass the existing audit invariants, including
   `index_shedding_at_day0` true, the correct theta susceptibility scale,
   epoch-391 quarantine witness, correct dedicated protocol, correct
   exemption echo, duty exclusion enabled, retest/wave arming, specimen
   bounds, and capture-funnel presence. An audit failure is machinery noise,
   not evidence for or against theta.
5. Pilot medians are reported theta-by-theta for P31, infections,
   before-share, during-window infections, capture, ignition, founder yield,
   specimen counts, and dead/saturated edge counts. If P31 is nonmonotone,
   the nonmonotonicity is reported rather than smoothed.
6. The original frozen selection rule may be applied only after the clean
   pilot readout. If no decade reaches the rule's threshold, or live rows
   are split into extinct and saturated/early-burned classes, that is the
   result; the grid is not extended and theta is not interpolated in this
   step.
7. Execution stops after the pilot readout. Benjamin decides whether a
   20-seed canary at the selected cell, a design correction, or a structural
   suite is next.

Rationale: this is the smallest experiment that separates theta
re-denomination from structural timing without changing frozen criteria
after seeing the canary. Existing artifacts are sufficient for the review;
no new simulation evidence was needed to reach this recommendation.
