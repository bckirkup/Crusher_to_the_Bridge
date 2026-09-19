# COVID Theta calibration: state of play at 2026-09-19 handoff

> **Status:** Handoff record (2026-09-19), authored against `main` after #609
> merged; amended at `main` = `46cff41` with §7 (the v8 probe result) and §8 (the
> merged, unsubmitted v9 screen and the state of its preflight gate) — read §8
> before acting on §4. It states where the Theta calibration stands, what is declared but
> not yet run, and what must not be reopened. It reports no new numbers: every
> figure it refers to is quoted from the ledger entry or readout that measured
> it, with that entry's own `Measured at` SHA. Nothing here is a fit.

## 1. The question

One susceptibility scale Theta must reproduce, on one hull, both halves of the
real record at once: the Diamond Princess trajectory (a big, long outbreak along
a dated path) and the `covid.H3` fleet shape (79 ships, 104 voyages to October
2020 — median voyage attack rate 0.2%, IQR 0.03–1.5%, mean 3.7%, with Diamond
Princess an outlier at 712 cases). A Theta that makes every voyage burn is as
wrong as one that makes none burn: the admissible arm is near-critical, most
voyages extinguishing and a minority burning. Bimodality is therefore not a
failure criterion, and its absence is not a success criterion — this was
pre-registered before the v7 surface existed and is unchanged.

The norovirus arm on the same hull is scored on different observables (rate of
voyages crossing the VSP 3% threshold, and attack rates conditioned on
crossing), so every COVID screen records per-cell
`vsp_threshold_crossing_fraction` and the conditional attack-rate quantiles for
comparison. Neither arm constrains the other's Theta.

## 2. What landed this session

Four repairs, in dependency order. Each is one ledger entry; quote numbers from
the entry, not from here.

- **`DOSE-FRAIL-01` (#603).** Theta now scales the profile's per-host
  `Beta(0.18, 58)` frailty draw (mean host susceptibility = Theta) instead of
  replacing dose-response with an exponential `k = Theta`, which had made all
  3,711 hosts identically susceptible on the one arm the Theta grid is scored
  on. Every pre-v7 Theta fit is superseded on this count.
- **`INDEX-GEOM-01` (#605).** Declared per-agent departure: `ashore` was
  re-derived from the itinerary every epoch and read only by the wastewater
  sampler, so no host could leave the ship and shore leave bought nothing
  epidemiologically. The Diamond Princess index case now disembarks at Hong
  Kong on day 5 per the record.
- **`THETA-SCREEN-V8` / v7 (#606, #608).** The pre-registered Theta x
  index-infection-age screen, and its readout:
  `docs/covid/covid_theta_screen_v7_readout.md`.
- **`SEED-ONSET-01` (#609).** `ExplicitSeed.onset_day`: a seed can declare the
  index case's *observed* onset day, so the implied incubation is a consequence
  of the record rather than a draw. The Diamond Princess seed carries
  `onset_day = -1.0` (Yamagishi 2020, grade A: cough onset 19 January, boarding
  20 January) with `infection_age_days = 6.8`, which states nothing independent
  — it only places the implied incubation at the profile's own authored median
  of 5.8 d.

## 3. What v7 measured, and what it means

The screen completed 3,080 of 3,080 cells with zero failures and **no Theta was
admissible**: no cell satisfied index geometry, `covid.T1` and `covid.T3`
jointly, and none satisfied geometry and `covid.T1` together at any Theta. No
criterion was loosened after the surface existed, and none has been since.

The cause was localised to the seeding path, not to Theta: the geometry gate
asked whether the index boarded symptomatic — a dated fact of the record —
while the seeded host's incubation was drawn free from the profile and then
compared against its boarding age, so the gate passed in only 45% of seeds at
the record's own infection age. **Every `index_geometry_pass_fraction` on the
v7 surface is an artifact of that free draw and is void**, which is why the
empty admissible region is not a statement about Theta. `SEED-ONSET-01` closed
the defect; the corner must be re-screened before anything is concluded about
Theta.

Three findings from v7 that stand on their own numbers and are not superseded:

- Theta 3.16e7–3.16e9 at the shorter index ages is the nearest region — eleven
  cells passing `covid.T1`, reproducing Diamond-Princess-sized takeoffs and the
  near-critical `covid.H3` shape. It is a fleet-shape observation, not a fit.
- `covid.T3` is non-discriminating on this hull: the testing campaign saturates
  against its own day capacities across five decades of Theta. It must carry no
  selection weight in any successor design, and carries none in v8.
- The asymptomatic share caps at 0.43 and *falls* as Theta rises, against
  `covid.T4` 0.50 and held-out `covid.H2` 0.81. In this model that share is
  emergent from delivered dose rather than a natural-history parameter, so no
  choice of Theta can meet it. This is an open structural mismatch, not a
  tuning target.

## 4. Declared and ready, not yet run

`covid_theta_screen_v8`
(`picard_framework/runs/covid_theta_screen_v8_design.json`, ledger
`THETA-SCREEN-V8`) re-screens the v7 corner with the index geometry true by
construction: seven half-decade Theta from 1e7 to 1e10 x six index infection
ages (3.3/4.8/6.8/9.8/12.8/15.6 d, i.e. implied incubation at the profile's
authored median and its 95% endpoints) x 40 matched seeds at v7's base =
1,680 cells on `diamond_princess_2020`. `covid.T1` is the sole selection
criterion, verbatim from v7; index geometry is now an audit invariant
(`index_onset_day == -1.0` in every seed — a deviation is a seeding-path defect,
not a failed criterion); `covid.T2`, `covid.T3`, `covid.T4`, the fleet-shape
indicators and the burn tail are reported and never selected on. Stages 2 (the
held-out `covid.H3` fleet shape, which may refuse a Theta but may never pick
among admitted ones) and 3 (the held-out Greg Mortimer hull) are declared in the
same file and gated on a non-empty stage-1 shortlist.

**Next actions, in order — revised by §7 and §8, read both first.** The
successor screen is declared and merged; step (1) is done, and the session
stopped deliberately before submitting anything, so **no array is running and
nothing is orphaned in AWS**. (1) ~~Declare the downward recentring screen~~ —
done: `covid_theta_screen_v9` (§8), which supersedes v8. v8 was never submitted
and must not be. (2) Run the `.agents/skills/campaign-preflight/SKILL.md` gate
for v9 and submit the 600-cell array — see §8 for the exact state of that gate.
(3) Merge with `tools/fit_covid_theta.py screen` and write the readout as a
ledger entry before interpreting anything, reporting the per-seed onset
distribution and `onset_mass_near_target` next to the T1 interval (§7, §8).

## 5. Where the artifacts live

Durable, and all a successor needs:

- v7 cells and merged surface:
  `s3://crusherbucket-994254241749-us-east-1-an/campaign/covid_theta_screen_v7/`;
  the surface itself is committed at
  `docs/covid/covid_theta_screen_v7_surface.csv` with its readout.
- ECR image `picard-campaign:theta-screen-v7-7ff6dd0`, job definition
  `picard-covid-boarding-screen:6`, queue `picard-campaign-queue`. The v9
  submission needs a new image tag off a `main` containing the v9 design (§8);
  no v8 or v9 image was ever built, and no v8 or v9 cell has ever run on AWS.

Nothing in a home directory or `/tmp` on this session's box is required: local
synced copies of the v7 results are reproducible from the S3 prefix, the probe
driver is reproduced verbatim in §7, and no result, design, criterion or
measurement exists only there.

## 6. Do not reopen

- No criterion, threshold or interval from the v7 admissibility block may be
  loosened to produce an admissible cell; the two v8 changes (geometry to an
  invariant, `covid.T3` to a diagnostic) were declared before any v8 cell ran
  and each follows from a v7 measurement.
- No constant may be moved to make `covid.T1`, `covid.T4` or the 19% Diamond
  Princess attack rate come out right
  (`.agents/skills/model-parameter-provenance/SKILL.md`).
- The index infection age is the record's unobserved coordinate: it is screened
  and reported, never chosen by which value reproduces an anchor.

## 7. The v8 smoke probes, and why the array did not go out

The three probe cells were rerun at `main` = `4721b5b` and all three completed.
Full results and their reading are in `docs/ledger/THETA-SCREEN-V8.md`; in short:

- **The invariant holds exactly** — `index_onset_day == -1.0`,
  `index_shedding_at_day0` true, `index_departed_epoch` 120 (day 5) in every
  cell. SEED-ONSET-01 does what it declares, and the defect that emptied v7
  cannot recur.
- **Every cell burns the ship** — 2,843–3,099 recorded onsets of 3,711 against
  `covid.T1`'s 197, *including* the Theta 1e7 floor of the grid. One seed drives
  all three, but v7's 40-seed cells agree wherever its index happened to be
  symptomatic aboard (median attack 0.709 at Theta 1e7, age 11 d). So the quiet
  region of the v7 surface was quiet because the index usually never became
  infectious aboard — not because Theta was small.
- **Therefore the v8 grid is mis-centred**, floor above the near-critical band
  rather than below it, and an admissible Theta (if any) lies below 1e7 where no
  screen has been. Submitting 1,680 cells as declared would buy saturation. The
  successor should declare a coarse wide downward screen first, with `covid.T1`
  and the invariant verbatim.
- **`covid.T1` as declared is weaker than it looks**: all eleven v7 T1-passing
  cells passed by spanning 197 between an extinction floor (p10 = 0) and a burn
  ceiling, not by putting mass near 197. Report the per-seed distribution beside
  the interval from now on; tighten the criterion only in a design file, before
  cells run.

Probe payloads are at `/home/ubuntu/campaign_results/v8_probe_{low,high,mid}.json`
on the session box, which a successor should not rely on — the numbers that
matter are in the ledger entry, and the driver is reproduced here so the cells
can be rerun anywhere (~67 min each locally three-up, ~9 min on a Spot worker):

```python
import json, sys, time
from picard_framework.covid_boarding_screen import (
    ScreenCell, load_design, simulate_screen_cell,
)
th, age = float(sys.argv[1]), float(sys.argv[2])
d = load_design('picard_framework/runs/covid_theta_screen_v8_design.json')
cell = ScreenCell(index=0, scenario_id='diamond_princess_2020', theta=th,
                  infection_age_days=age, imports=1, seed=20200205)
t0 = time.time()
p = simulate_screen_cell(d, cell)
out = {k: p[k] for k in ('index_onset_day', 'index_shedding_at_day0',
                         'index_departed_epoch', 'attack_rate',
                         'infections_total', 'aboard_total',
                         'vsp_reported_case_fraction_max')}
out['recorded_onsets'] = p['observables']['recorded_onsets']
out['minutes'] = round((time.time() - t0) / 60, 1)
print(json.dumps(out))
```

Run from the repository root with `PYTHONPATH=.`, one shell per cell, at
(1e7, 3.3), (1e10, 15.6) and (316227766.01683795, 6.8). Redirect each to a file:
the first attempt was lost with a session restart because the results only ever
existed in shell buffers.

## 8. `covid_theta_screen_v9`: declared, merged, not submitted

The successor screen landed at `main` = `46cff41` (#615) and is the live design:
`picard_framework/runs/covid_theta_screen_v9_design.json`, entry
`docs/ledger/THETA-SCREEN-V9.md`. Ten decade Theta from **1e1** to 1e10 × three
index infection ages (3.3 / 6.8 / 12.8 d) × 20 matched seeds at base 20200205 =
**600 cells** on `diamond_princess_2020`, authored as a refinement of
`covid_theta_screen_v8`. `covid.T1` and the index-geometry invariant carry over
verbatim; `covid.T3` stays a diagnostic; the reason the range moved down six
decades is §7, measured and recorded before the design was written. **v8 is
superseded and must never be submitted**; v9 supersedes it in the same Theta
ceiling so the two surfaces remain readable against each other at 1e7–1e10.

#615 also added the discriminator the readout needs, reported and never selected
on: `onset_mass_near_target` (share of a cell's seeds whose `recorded_onsets`
falls within a factor of two of `covid.T1`'s 197, bounds computed from the target),
with `recorded_onsets_per_seed` aligned to the existing `seeds` key. It exists
because every v7 T1 pass was an interval spanning 197, not mass near it (§7); a
bimodal cell now reports mass 0.0 while `t1_ok` is still true, which is the point.
Any tightening of T1 itself must be declared in the stage-1b design before its
cells run.

**Where the preflight gate stands.** Rule A is satisfied: every criterion,
invariant and diagnostic was frozen in the design file before any v9 cell existed,
and `main` now contains it. Nothing else in
`.agents/skills/campaign-preflight/SKILL.md` has been done — steps 1–6 are all
outstanding, and no image was built, no job definition registered, no canary or
array submitted. The successor runs that gate from the top:

- the design must be **inside** the image, so build from a `main` containing
  `46cff41` and tag it for v9 (v7's image `picard-campaign:theta-screen-v7-7ff6dd0`
  does not contain the v9 design);
- submit against a **pinned job-definition revision and `sha256:` digest**, never
  a bare tag — `picard-covid-boarding-screen:6` and the v7 digest are the last
  known-good pair and are recorded in §5, but the v9 image is a new digest;
- `DESIGN=covid_theta_screen_v9`, `STRIDE=1`, via
  `deploy/aws/submit_covid_boarding_screen.sh`, whose array size is computed from
  `enumerate_cells` and must print **600**;
- one canary child inspected before the array: confirm `index_onset_day == -1.0`
  and `index_shedding_at_day0` true (the §7 invariant), the swept Theta read back
  from the cell's own output rather than the submitted spec, and a non-degenerate
  run;
- then the array, with the ETA announced at submit time (~30 min per cell,
  ~9 min observed per cell on a Spot worker in the §7 probes).

**What the floor is for.** The 1e1 end is *expected to be inert*. An inert floor
is the evidence that the sweep brackets the near-critical band instead of sitting
above it — the mistake v8 would have made. If the admissible set lands on either
boundary, report it as a boundary and extend the sweep in that direction; never
select on a boundary. If the admissible set is empty, report the located band and
the nearest cells and say so: no criterion may be loosened after the surface
exists (§6).

Stage 1b, if stage 1 admits anything: half-decade steps spanning the admitted
band plus one half decade beyond each edge, 40 seeds, the six v8 incubation points
restored, declared in its own design file before its cells run.
