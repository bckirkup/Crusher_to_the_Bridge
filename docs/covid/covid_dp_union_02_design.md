# DP-UNION-02: post-shape Diamond Princess union refit

**Status: design frozen before any scored DP-UNION-02 cell. No pilot, canary,
or array has been submitted.**

DP-UNION-02 is the first Diamond Princess theta refit under the replacement
COVID source law. It inherits the DP-UNION-01 union arm and joint conditioned
contract, but not its numerical theta conclusion: COVID-SHED-SHAPE-01 withdrew
all pre-shape measurements on the source-emission channel. Greg Mortimer
remains validation-only and H5 remains permanently held out.

## 1. Why a new lattice is required

`COVID-SHED-SHAPE-01` replaced deterministic positive shedding with the Zhou
onset-aligned zero-inflated occurrence shape and the persistent high/low
emitter mixture. The fitted quantity remains the composite

\[
\Theta = \text{emission scale}\times\text{per-copy risk},
\]

so no theta fitted under the old emission law converts into the new law. The
two source representations are both normalized to unit peak before theta is
fitted; their normalized lifetime areas are the same order (implemented-shape
expectation 1.7217 versus legacy normalized area 1.6777, ratio 1.0262). That
similarity is a bound on the required search span, not a scalar conversion:
the day-resolved support, zero-inflated occurrence process, and high/low
persistent emitter mixture all change who emits early and when transmission
can occur.

The runnable lattice therefore remains the deliberately broad half-decade grid
`1e5, 3.16e5, ..., 1e10`. The pilot redoes grid selection under the post-shape
law. An edge failure is evidence that the composite operating point lies
outside the declared bracket and must be reported as such; it is not license
to extend the grid after seeing outcome-dependent results.

## 2. Inherited union arm

The only scored arm is `union_niid`. Relative to DP-FIT-01 `replay_niid`, it is
exactly the DP-UNION-01 union:

- dedicated protocols catalog `data/config/protocols_covid_dp_dedicated.json`;
- quartermaster testing order `SOP-017-DEDQUARTER` replaces
  `SOP-017-DEDICATED` while preserving the parent order's other behavior;
- general-crew test exemption is the fraction draw `crew_general: 0.25`;
- crew duty exclusion is enabled;
- negative retesting is enabled on sweeps;
- the day-34 `crew_wave` campaign wave is armed;
- the NIID index clock remains `onset_day = 3.0`,
  `infection_age_days = 2.8` in the explicit seed patch. The inherited lattice
  axis echo `infection_age_days = 6.8` is not the index geometry; the worker
  reads the patched explicit seed age back from the resolved run spec.

Theta remains the only swept quantity. Alpha/beta, shedding shape, emitter
mixture, onset/incubation, testing behavior, ship geometry, and intervention
rules are not fitted here.

## 3. Ascertainment-conditioned seed cohort

`COVID-SEED-ASCERTAIN-01` defines the replay event class: DP and GM are
scored conditional on a day-0 index that actually emits at boarding. A silent
day-0 occurrence is a valid physical draw but is outside the event class.

Under the NIID clock the index boards at onset-relative day approximately -3.
The active shape row at day -3 has detection probability 0.1, so the legacy
24 contiguous seeds cannot supply a 24-seed conditioned cohort. Two precursor
corrections make that row reachable: the owner-approved
`COVID-PRESHED-GATE-01` change widens the profile gate to the Zhou shape's
negative support (day -5), and the explicit-seed onset stamp now uses the
engine-represented infection age after epoch rounding so the declared onset
voyage day is preserved rather than drifting across a shape-row boundary.
DP-UNION-02 therefore freezes an explicit seed cohort instead of pretending
that the unconditioned seed list is the replay class.

The cohort was selected before any scored cell by this rule:

1. predeclare the 360 calendar-date integer candidate seeds beginning at
   `20200205` and ending at `20210129`;
2. run zero-epoch initialization-only cells under `union_niid` at
   `theta = 1e8`;
3. read only `index_shedding_at_day0` — no attack, onset, founder, testing,
   capture, or other outcome observable;
4. take the first 24 positive-emission candidates in candidate order.

The committed probe record is
`campaigns/covid/dp_union_02/ascertainment_probe.json`; the runnable probe is
`campaigns/covid/dp_union_02/probe.py`. Because occurrence assignment is part
of seed initialization and precedes transmission dynamics, theta is not
expected to alter the bit. Regardless of that expectation, every scored cell
is independently audited for `index_shedding_at_day0 is true`; a false bit is
an audit deviation, not a seed to silently drop or replace.

Frozen selected cohort:

```text
20200208, 20200213, 20200302, 20200320, 20200321, 20200323,
20200324, 20200412, 20200507, 20200509, 20200520, 20200525,
20200530, 20200610, 20200612, 20200621, 20200703, 20200713,
20200715, 20200721, 20200722, 20200724, 20200725, 20200727
```

`seed_values` in `picard_framework/runs/covid_dp_union_02_design.json` is the
machine-readable source of truth. `seed_base` remains the first candidate date
for provenance only; it does not generate the cohort when `seed_values` is
present.

## 4. Frozen joint conditioned contract

The scored class is the founder class: seeds with at least 10 aboard-window
acquisitions. A theta row is scored only when at least 5 founder-class cells
exist. Takeoff-class seeds (at least 10 recorded onsets) and all-seed
summaries are reported but never selected.

A theta is **consistent** only when every leg below passes on the founder
class:

| leg | frozen rule |
|---|---|
| `timing_ignition` | median ignition day is at most 9; ignition is the first day aboard-window acquisition mass reaches 50 |
| `timing_before_share` | median before-quarantine recorded-onset share within 0.173 ± 0.100 |
| `attack` | median total infections in [712, 960] |
| `during` | median during-quarantine infections in [150, 350] |
| `capture` | median conditioned confirmed/reachable capture at least 0.8, with reachable infections truncated at infection day 29 |
| `t3` | cumulative positives through day 31 are compatible with 634 under FIT-01's side rule: neither strictly-above nor strictly-below counts reaches 75% of scored-class cells; the median is reported, not the pass criterion |
| `onboard_table` | cumulative positives through day 34, including the crew wave, are compatible with 691 under the same side rule; the median is reported, not the pass criterion |

Specimen-count side rules are reported, never selected: at least 75% of
scored-class cells have day-31 specimens within ±50% of 3063 and day-34
specimens within ±50% of 3894. Negative leg counts, missing medians, and
non-representative rows fail rather than being coerced into pass.

Failure flags frozen before cells:

- `dead`: at least 20 of 24 seeds have no aboard-window acquisitions;
- `saturated`: at least 95% of the aboard population infected;
- `median_not_representative`: median attack lies outside [0.5, 2.0] times
  the per-seed mean for fewer than 6 founder-class cells or for the class as
  declared in the readout implementation;
- edge rows that pass or fail only because the lattice ended are reported as
  edge evidence, not silently extrapolated.

## 5. Audit invariants

Every cell audit must pass before its theta row is interpreted:

- resolved platform is `diamond_princess`;
- index onset day is 3.0;
- `index_shedding_at_day0` is true;
- dose-response susceptibility scale equals `theta * (alpha + beta) / alpha`
  with `alpha = 0.18`, `beta = 58.0`;
- quarantine witness activates at epoch 391;
- close-zone protocol never fires;
- testing ran before the scored day;
- onboard-table positives agree with campaign observables;
- no specimen occurs after day 34;
- all post-day-31 specimens are the tagged `crew_wave`, occur on day 34, and
  are within the 831-test wave cap;
- dedicated protocol path resolves;
- `SOP-017-DEDQUARTER` fires and parent `SOP-017-DEDICATED` does not;
- exemption echo is exactly `crew_general: 0.25`, no work-zone map;
- realized exempt draw is `round(0.25 * total_crew)`;
- crew duty exclusion resolves enabled;
- negative retesting and the single `crew_wave` campaign wave resolve;
- capture funnel exists whenever infections exist.

Any audit deviation is a machinery defect report. It is not a modeling result
and is not hidden inside a passing median.

## 6. Execution order and stop gates

No AWS submission is part of this design-freeze change. When execution is
separately authorized, the order is frozen as:

1. local smoke: one declared cell proves the theta override reaches the
   engine, the union arm resolves, the conditioned seed emits at day 0, and
   the downstream `dp_union` output contract is present;
2. `scripts/campaign run covid/dp_union_02 --block ... --index 0` local smoke;
3. build/push the post-shape image and pin the image digest plus registered
   job-definition revision in the execution record — never a bare tag;
4. dry-run submission count must equal the design file's 264 cells
   (11 theta lattice points x 24 seeds);
5. pilot: first 5 seeds of the decade canary blocks only;
6. apply the frozen pilot grid-selection rule inherited from DP-UNION-01;
7. canary: the remaining seeds needed to read 20 total at the selected
   decade/cell, with exactly the frozen cohort order;
8. stop after canary readout and report. The user decides whether the rest of
   the array runs.

If any gate fails, execution stops at that gate. There is no automatic
repair-and-resubmit loop inside the campaign.

## 7. Storage contract

DP-UNION-02 writes one compact `cell_{seed}.json` per task through the generic
campaign entrypoint. The worker drops bulky specimen/funnel echo objects after
extracting the scored contract blocks. No run zips or per-epoch telemetry
archives are part of this campaign contract. The S3 prefix is
`campaign/covid_dp_union_02/`; DP-UNION-01 artifacts remain provenance and are
not overwritten.
