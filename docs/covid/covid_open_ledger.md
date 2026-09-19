# SARS-CoV-2 fit: open ledger

> **Status:** Living. Head commit of record: `4d016c5` (fill with the
> `main` SHA this file was authored against). If that is not the current head,
> treat every number here as unverified.

What is currently withdrawn on the `sars_cov2_resp` arm, what the last
measurement of record is, and what is outstanding. The permanent defect record
for shared mechanics is `docs/ledger/` (entries tagged `sars_cov2_resp` or
`all`) together with the frozen numbered history in
`docs/norovirus/norovirus_open_ledger.md`; readouts live in `docs/covid/`.

Read this before quoting any Θ, attack-rate, onset-curve or route-share figure
for the COVID arm.

---

## 1. Currently withdrawn

**AERO-NEAR-02 invalidates prior near-field-sensitive COVID figures.** The
QUAR-ORDER-01 burning and intermediate-cell figures are superseded by the
AERO-NEAR-02 measurement (§2). The two diagnostic cells are not paired with
their QUAR-ORDER-01 runs: per-meal table dealing consumes RNG, so the same seed
follows a different trajectory.

**DOSE-FRAIL-01 invalidates every Θ-arm figure measured on identical hosts.**
The Θ arm previously installed an exponential dose-response, which gave every
host the same susceptibility; it now scales the profile's own per-host
`Beta(0.18, 58)` draw so that the arm's mean susceptibility is Θ
(`docs/ledger/DOSE-FRAIL-01.md`). The AERO-NEAR-02 crew-mess trace below, and
every Θ-arm figure of record, were measured with identical hosts and are
superseded on this arm pending remeasurement. A rescaling will not recover
them: frailty spreads a threshold that previously fired for a whole room at
once.

**Every fitted Θ is void pending a refit on the repaired airborne subsystem.**
The fits of record (`covid_first_look_v1`–`v6`, the 1b boarding screen, and the
three-stage imports × Θ sweep) were all measured before at least one of:

- `AERO-CABIN-04` (#583): HVAC-downstream inhalation ignored cabin confinement.
- `AERO-CABIN-05` (#588): each room's standing air was inhaled once per upstream
  shedding zone (measured mean 5.2×, up to 82×) instead of once per epoch.
- `AERO-CABIN-06` (#591): the airborne reservoir was keyed on the whole cabin
  block, so a confined shedder's aerosol reached every stateroom on the block.

`v6` (#565) additionally carried `AERO-CABIN-03` (#561) and the two realistic
air defaults, but not 04–06. Its selected Θ = 3.16e11 and every earlier
Θ (3.16e7 on pooled air, v4/v5) belong to the air model they were measured on
and are not carried forward.

Every prior Θ figure and the v6 readout were also measured with the voluntary
FRED draw applied to scheduled SOP-017, so they are void pending remeasurement
under the authority-enforced quarantine declaration.

**The declared index case is wrong by about six days and never disembarks.**
The record's index boarded 20 Jan already symptomatic (onset 19 Jan) and left
at Hong Kong on 25 Jan (Yamagishi 2020); the scenario seeds him at infection
age 0 on day 0 and keeps him aboard. There is no per-agent permanent
disembarkation in the engine. Every fit above scores a curve that includes a
host the record excludes.

**INDEX-GEOM-01 supersedes every Θ-arm figure measured with the index case
aboard for the whole voyage.** Declared per-agent departure now exists
(`docs/ledger/INDEX-GEOM-01.md`) and the seed disembarks on day 5 as the
record states, so every Θ-arm figure of record — which scores a curve that
includes a host the record excludes — is superseded pending remeasurement.
The infection-age component of the geometry is NOT resolved: the seed still
arrives at declared age 0, and the infection-age × Θ screen remains open in
§3.

## 2. Last measurement of record

`AERO-NEAR-02`, measured at `7d8b0d2` (`docs/ledger/AERO-NEAR-02.md`): seed
`20200206`, Θ = 3.16e7 — 2 infections (extinction); seed `20200210`, Θ = 1e9 —
1,390 infections (37.5%), 952 of them in the two crew messes after 5 Feb, 303
in confined passengers, Windjammer 0. One crew-mess epoch (242 occupants, 2
shedders) infected 140 hosts at one identical far-field dose: the roomful-at-once
behaviour is now the well-mixed far field on identical hosts, not the near
field or the dining topology.

Prior to that — local burning cell, seed `20200206`, Θ = 3.16e7, full voyage, after
`AERO-CABIN-06` (#591): 2,759 infection events, 2,732 distinct hosts infected,
final attack 73.6%; HVAC-route infections in confined cabin hosts 32 (was 1,591
before `AERO-CABIN-04`). Six-seed probe at the same Θ: 3, 2,759, 2,011, 1, 4,
2,009 — still extinction-or-burn; at Θ = 1e9 two intermediate cells appear
(48 and 347). Change-detector cell: CPython 3.12 `(105, 51, 217, 118, 20)`.

## 3. Outstanding

- **Missing intermediate attack rates.** The route trace (QUAR-ORDER-01,
  AERO-NEAR-02) placed the burn in public dining, not in a leak through
  confinement. With enforced quarantine and dining tables in place, what
  remains is the well-mixed venue far field clearing threshold for a roomful
  of hosts whose susceptibilities now differ (DOSE-FRAIL-01). No constant is to
  be moved to produce a 19% attack rate.
- **Crew-mess seating structure.** Crew-mess tables are now dealt within
  department (DINE-CREW-01), while the venue far-field pool is unchanged.
  AERO-NEAR-02 figures are pending remeasurement
  (`docs/ledger/DINE-CREW-01.md`).
- **Windjammer 100× pool-mass jump at 1 → 2 shedders** (QUAR-ORDER-01 trace):
  the trajectory did not recur under AERO-NEAR-02; mechanism untraced.
- **Incubation dose reference on the Θ arm.** Host frailty is restored
  (DOSE-FRAIL-01), but `dose_reference_log10` is referenced to the mean host,
  `ln 2 / Θ`. `Beta(0.18, 58)` is strongly right-skewed, so the median host sits
  well below the mean; whether the reference belongs at the mean, the median, or
  the realised infecting dose is unresolved.
- **795 repeat infection events at Θ = 1e9.** Hosts re-enter the susceptible
  pool; lifecycle not yet traced.
- **Index-case geometry.** Declared per-agent departure shipped
  (INDEX-GEOM-01): the index disembarks on day 5 per Yamagishi 2020. The
  resolved infection-age × Θ screen has now run (THETA-V7-01, below) and
  exposed the remaining half, which SEED-ONSET-01 then closed: the seed
  channel can now declare the index's *observed onset date* (onset day
  −1, grade A), making the implied incubation a consequence of the record
  rather than a free draw.
- **`covid_theta_screen_v7` ran; the admissible region is empty.** The
  pre-registered Θ × infection-age screen on the repaired arm (host frailty
  restored, index departing day 5;
  `picard_framework/runs/covid_theta_screen_v7_design.json`, 11 half-decade
  Thetas × 7 ages × 40 seeds) completed 3,080/3,080 cells with zero failures at
  `main` = `e32272d`. **No Θ is admissible**: zero of 77 cells satisfy index
  geometry, covid.T1 and covid.T3 jointly, and none satisfy geometry and T1
  together at any Θ (`docs/ledger/THETA-V7-01.md`,
  `docs/covid/covid_theta_screen_v7_readout.md`). Outstanding from it
  (geometry rows superseded by SEED-ONSET-01, which makes the onset day
  declared rather than drawn — every `index_geometry_pass_fraction` on the
  v7 surface is an artifact of the free incubation draw and is void, so the
  empty admissible region is not a statement about Θ):
  - ~~the explicit-seed channel cannot declare the index's observed onset
    date~~ — fixed by SEED-ONSET-01: `ExplicitSeed.onset_day` stamps the
    declared onset and the symptomatic history directly;
  - the asymptomatic share caps at 0.43 median anywhere on the surface and falls
    with Θ, against covid.T4 0.50 and held-out covid.H2 0.81 — it is emergent
    from delivered dose rather than a natural-history parameter;
  - covid.T3 is non-discriminating on this hull (specimens saturate at
    ~1,600–3,063 across five decades of Θ) and must not carry selection weight
    in a successor design;
  - Θ 3.16e7–3.16e9 at index ages 0–5 d remains the nearest region as a
    fleet-shape observation — eleven cells passing covid.T1 (four of them
    covid.T3), reproducing DP-sized takeoffs and the covid.H3 fleet shape —
    but its geometry pass fractions are void with the others; under a
    declared onset the gate is satisfied by construction at the record's
    geometry.
  Stages 2–3 of the design are gated on a non-empty shortlist and were not run.
- **`covid_theta_screen_v8` is declared and not yet run.** The successor screen
  re-screens the Θ 3.16e7–3.16e9 corner (seven half-decade Θ from 1e7 to 1e10 ×
  six index infection ages × 40 matched seeds = 1,680 cells) with the index
  geometry true by construction under SEED-ONSET-01, `covid.T1` as the sole
  selection criterion verbatim from v7, and covid.T3 demoted to a diagnostic on
  v7's own saturation evidence
  (`picard_framework/runs/covid_theta_screen_v8_design.json`,
  `docs/ledger/THETA-SCREEN-V8.md`). It is declared-and-tested but not
  smoke-confirmed end-to-end: the first action is to confirm
  `index_onset_day == -1.0` on one real cell, before the array submits. Session
  state of play, including what may not be reopened:
  `docs/covid/covid_theta_handoff_2026_09_19.md`.
