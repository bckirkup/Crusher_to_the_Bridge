# Pre-boarding assessment — the VSP §4.1.1.2 declaration screen

**Status: Implemented — the reference crew clause is the default under
renewal mode** (unstated block → lookback 3, crew enabled at c=1, h=null,
reportable, denial 0; under screening-prevalence an unstated block stays off).
The arm lives in `engines/initiation.py`
(`preboarding_assessment` inside each pathogen's `boarding` block), is swept
by `boarding_axis.py` (`preboarding_crew_points`, `preboarding_passenger_points`,
`preboarding_crew_reportable_values`), and consumes no draw when off — the
inertness fingerprint in `tests/test_preboarding_assessment.py` is the pre-arm
draw of `main` reproduced by stating every arm explicitly off.

## The clause

VSP 2018 Operations Manual §4.1.1.2 (manual p. 31 / PDF p. 60), under
"Pre-boarding Medical Screening", writes the three-day crew assessment:

> "The REPORTABLE AGE CASES must include crew members with a symptom onset
> time of up to 3 days before boarding the vessel. Maintain documentation of
> the 3-day assessment for each crew member with symptoms on the vessel for
> review during inspections. Retain this documentation for 12 months."

§4.1.2.3.1 (manual p. 36 / PDF p. 65) repeats the retention clause. The only
passenger instrument in the manual is the §4.1.2.2.1 72-hour questionnaire
(manual p. 35 / PDF p. 64), administered to already-identified cases and
looking back before *illness onset* — it is not a gangplank screen. The
passenger side is therefore sourced to Neri et al. 2008's *recommendation* of
embarking-passenger screening, declared as industry practice rather than
regulation.

## The mechanism

The boarding cohort already stamps each post-onset boarder with
`days_since_onset_at_boarding` (convalescent boarders carry
`age − incubation`; symptomatic-stream boarders carry the elapsed illness
`a`). The assessment reads that stamp:

- **Eligibility** is onset-indexed: `0.0 <= a <= lookback_days`
  (`lookback_days = 3`, the sourced crew clause). A host with no onset —
  presymptomatic, incubating, never-symptomatic — has no onset age and is
  not eligible; no draw is consumed for it.
- **Declaration**: one draw per eligible host,
  `p(a) = c · 2^(−a/h)` with `c = declaration_compliance` and
  `h = recall_halflife_days`; `h` null is perfect recall (`p = c`).
- **Reportable**: a declared *crew* case is a reportable AGE case at epoch 0
  and lands in `ever_reported_ids` directly — it cannot come through the
  sick-call ladder, which intersects reports with the currently symptomatic
  roster and would miss a host whose illness resolved ashore. Passenger
  `reportable: true` is a load error: the case definition is crew-only.
- **Denial**: one further draw per declared host against
  `denial_probability`; a denied host never boards — no infection record, no
  membership of `drawn_by_role` or `composition`, counted in `screened_out`.
  Denial is drawn before the reportable id is recorded, so a denied host is
  structurally never reportable.

In party mode the screen is a no-op: party members board `incubating`
(the common-exposure state replaces convalescent), so no party host carries
an onset age and none is eligible — they are skipped, not refused.

## Why two arms separately switchable

Reportability and truncation are the two consequences of one declaration
event, but they move different readouts: the first raises epoch-0 reported
cases (posting frequency, A8 vs MIDRS) without touching incidence; the
second removes infected hosts and moves attack rates. A campaign measuring
them apart needs the split, so `reportable` and `denial_probability` are
independent coordinates.

## Coordinates and provenance

`lookback_days = 3` is sourced (VSP 2018 §4.1.1.2, crew-only). The rest are
**operational sweep coordinates with no licensed point and no evidence
grade**: `c = 0` and `denial = 0` are the admissible no-screen corner;
`h = null` (perfect recall) is the upper bound on what the structure can
remove; `denial` is industry practice the manual never states. No arm of
this PR may be read as a measurement.

## Readout

The initiation manifest's `boarding[pid].preboarding_assessment` carries the
effective coordinates plus, per role, `eligible`, `declared`,
`screened_out`, and `preboarding_reportable`. `drawn_by_role` remains the
count of hosts that actually boarded infected; `screened_out` is its own
field on the report, never a `composition` bucket.

## Inertness

A block absent or with both roles `enabled: false` consumes exactly the
draws the pre-arm code consumed: a disabled role is skipped before
eligibility is tested, so no rng call is ever reached. The fingerprint
test captures the pre-arm draw of merged `main`.

When a role *is* enabled the declaration/denial draws share
`boarding_rng`, so on-vs-off matched-seed runs are not host-paired — a
denial draw shifts every subsequent host's stream position. The campaign
readout therefore compares distributions across matched seeds, never
which hosts were drawn.
