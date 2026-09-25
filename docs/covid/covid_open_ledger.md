# SARS-CoV-2 fit: open ledger

> **Status:** Living. Head commit of record: `37dc215` (fill with the
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

**REINFECT-01 voids every `infections_before/during/after_quarantine`
figure measured at or before `861a0b9` as a count of hosts infected in the
window.** A cleared host acquired no immunity without a strain registry and
its second infection overwrote the record, so the truth channel dated the
latest episode (`docs/ledger/REINFECT-01.md`, measured at `861a0b9`): 32% of
the Θ 1e9 `A0` during-quarantine count and 96% in the saturated seed
`20200205` were reinfections; 37.6% of infected hosts in the probe cell were
infected twice. **Fixed at `7f105a7`** (unlabeled clearance immunity +
refractory protection without a registry, episode bookkeeping, syndromic
onset re-dating); the paired in-image canary moved `A0` seed `20200205`
during-quarantine counts 455 → 198 (Θ 1e5) and 973 → 43 (Θ 1e9), so all
`861a0b9` during-quarantine figures — including every arm count in the
`covid_quarantine_attribution_v1` campaign — are superseded as first-infection
windows. `infections_total`, `attack_rate` and `recorded_onsets` counted
distinct hosts and stand in count. The "outbreak continues through enforced
quarantine" reading at truth-channel scale (handoff §12, v9 readout §6) is
superseded by `docs/covid/covid_quarantine_attribution_v1_readout.md` §4–6.

**QUAR-EXEMPT-01 moves every post-`1a25c24` confinement-sensitive figure.**
`exempt_classes` is now scoped to the protocol that declares it
(`docs/ledger/QUAR-EXEMPT-01.md`); symptomatic crew are confined by
`SOP-008`/`010`/`016` while `SOP-011` is active, where the old union never
confined them. THETA-SCREEN-V9 figures stay valid at their own `Measured at`
SHA `0fb186b` and are not re-run; the same cells at HEAD are a different
trajectory. S3 cells reproduce only inside the campaign image
(`python:3.11-slim`, numpy 2.4.6), not on a CPython 3.12 / numpy 2.5.0 host.

**AERO-NEAR-02 invalidates prior near-field-sensitive COVID figures.** The
QUAR-ORDER-01 burning and intermediate-cell figures are superseded by the
AERO-NEAR-02 measurement (§2). The two diagnostic cells are not paired with
their QUAR-ORDER-01 runs: per-meal table dealing consumes RNG, so the same seed
follows a different trajectory.

**AERO-SPLIT-01 supersedes every figure produced under the unbounded
droplet far field.** The droplet pathway's zone pool now carries only the
declared `far_field_share` (0.175, midpoint of [0.05, 0.30], Grade C) of
continuous emission; the rest reaches a partner-bounded proximity ring at
plume concentration, bounded by the CONTACT-ARCH-01 activity rates
(`docs/ledger/AERO-SPLIT-01.md`, `docs/droplet_field_split_spec.md`,
`transmission.droplet_field_split`, labelled pre-change baseline `mode:
off`). Every measured figure whose mechanism was the well-mixed room pool —
the v11 stage-2 ~17.7× onset overproduction and ~0.96 attack on takeoff
seeds, the assay-1 arm table and its ~68%-day-0–2 route attribution, every
Θ surface and admissible set on this arm, and all droplet route shares —
is superseded pending remeasurement on the partition tree. `off` is
bit-identical to the pre-change engine (no proximity draws on the shared
stream), so paired-seed contrasts stay attributable.

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

**The upstream AGID attack-rate fit may not be quoted as validation of this
port's arrest layer or dose scale.** Ledger `AGID-UPSTREAM-AR-01` settles the
provenance question: the upstream paper (PNAS 10.1073/pnas.2422574123) does
report a Diamond Princess fit — 18.6% against the observed 19%, RMSE 23.73 on
the daily series — but that run carries no arrest layer, while DP's 19.2% is a
post-quarantine outcome, and upstream's own Isolation arm on the same
parameterisation lands at 4%. The published engine
(`bckirkup/infection-dynamics` `8d159f4`) also has no active environmental
route, caps transmission at one to two proximity targets per shedder per 20
minutes, and decides infection by a deterministic `P > 0.5` threshold on the
source's shedding, so its attack rate is a contact-opportunity count that
pathogen quantity cannot move. Neither its fit nor its calibration transfers to
a summed-dose engine with shared-air routes. The same applies to the VSP-shadow
monograph (`docs/reports/05_vsp.tex`), whose attack-rate band is post-response
norovirus at `dose_adjustment` 10.6, not a COVID fit.

## 2. Last measurement of record

`QUAR-ATTR-V2`, measured at `d62f10d` (`docs/ledger/QUAR-ATTR-V2.md`,
`docs/covid/covid_quarantine_attribution_v2_readout.md`): the same 240 cells
re-run post-REINFECT-01. On the now-valid frozen criterion at Θ 1e9, crew
confinement (−74%, n = 12) and pool-transport removal (−66%, n = 8) are each
load-bearing, near-field air is not (+19%, n = 8); the combined arm (−50%,
n = 7) also suppresses takeoff 12 → 8. Nothing decidable at Θ 1e5 (3/20
takeoff). `infections_during_quarantine == ledger_events_during` in 240/240
cells. The v1 reading (`861a0b9`, `docs/ledger/QUAR-ATTR-V1.md`) that no
channel is load-bearing is superseded — its measure counted second
episodes; its post-hoc ledger shifts are confirmed. Removing all shared air
still collapses takeoff (0/20, 1/20). Conditional-on-takeoff attack rate is
0.79–0.90 across A0–A4 at 1e9 (A1 0.824 vs A0 0.865; A2/A4 move the all-seed
AR by suppressing takeoff, not the taken-off voyage). No Θ is
fitted; A1–A5 score no anchor. Successor prompt for the Θ re-screen:
`docs/covid/covid_theta_handoff_2026_09_19.md` §16.

Before that — `AERO-NEAR-02`, measured at `7d8b0d2` (`docs/ledger/AERO-NEAR-02.md`): seed
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

- **`AERO-SPLIT-01` shipped and its paired-seed probe is measured
  (`docs/ledger/AERO-SPLIT-01.md`, `e20008d`).** `transmission.droplet_field_split`
  defaults to `partition` (spec `docs/droplet_field_split_spec.md`): the room
  pool carries `far_field_share` = 0.175 of continuous droplet emission
  (declared interval [0.05, 0.30], Grade C, swept-never-fitted) and the near
  share reaches only a partner-bounded proximity ring at the AERO-NEAR-02
  plume concentration. On the takeoff seed the early spike survives
  (3574 -> 3561 events, day-0–2 68.7% -> 57.1%) — the plume's per-partner
  concentration keeps each ring infection near-certain, so ~2 partners/h
  still branches at this Θ; on the non-takeoff seed the sustained phase
  halves (3548 -> 1675) and the residual concentrates in the crew messes
  and confinement exposure. Follow-on work, in order: re-run the
  declared replay at the fleet-admissible Θs, re-run `covid_sensitivity_assay_v2`
  (it was stood down for this change), and a declared `far_field_share`
  sweep over [0.05, 0.30] — none of it fitted to 197.
- **`PARTNER-RATE-V1` measured its canary arm and stood down: the ring is not
  reach-limited.** At `rates_per_hour` ×0.25 (the bottom of the declared
  sweep), all 20 takeoff seeds still record 1,275–3,525 onsets (q05 2,457 /
  median 3,474 / q95 3,518) vs the record's 197 — inside the partition tree's
  shipped-rate band (~3,470–3,520, cross-campaign contrast). The assay's
  declared counterfactual fired: four times fewer partner draws does not move
  the conditional mass, so the ~18× gap is bounded by per-partner plume dose
  (β) or the ring's definition, not by reach. The response-curve arms (R0,
  R2–R7, R8 witness, 160 cells) are unmeasured and stood down; reopening is a
  new decision (`docs/ledger/PARTNER-RATE-V1.md`,
  `docs/covid/covid_partner_rate_assay_v1_readout.md`, measured at `37dc215`,
  Batch job-def rev 19, image digest `sha256:7528dcd1…`).
- **`PLUME-DOSE-V1` measured its full array and stands negative on both
  axes: the conditional gap is not borne on the sampled proximity ring at
  all.** The dose sweep (β {4080, 2040, 816, 408} = dose ×{0.05–0.50} under
  the partition's 1/β scaling, D0 shipped β 204) leaves conditional recorded
  mass flat at medians 3,435–3,486 across the 20× range (log-log elasticity
  0.004); no arm's q05–q95 contains 197 anywhere on the grid — no dose-only
  closure scale exists — and the takeoff gate never collapses (lowest dose
  still 19/20). The four per-activity ring knockouts (dining, work,
  cabin+corridor, leisure) are equally flat (medians 3,441–3,492, 20/20
  takeoff each): no single sampled venue's ring is load-bearing, and the
  pool witness (3,517 vs D0 3,486) says the partition architecture itself
  is not the carrier. Per the design's declared counterfactual the standing
  suspects are, in order, the **fixed ring structure** (cabin-mate and
  meal-table rings that survive every knockout), the **seeded index's
  day-0 exposure geometry**, and the **observational channel** — consistent
  with before_share ~0.95 vs the record's 0.173 (most recorded mass is
  pre-quarantine burn the record never dated as onsets). Next assay, if
  pursued: knock out the fixed rings or interrogate onset-dating — the
  sampled-ring grammar is exhausted. 200/200 cells, 0% failures
  (`docs/ledger/PLUME-DOSE-V1.md`,
  `docs/covid/covid_plume_dose_assay_v1_readout.md`, measured at `2bcdeb7`,
  Batch job-def rev 20, image digest `sha256:aca8d6b8…`).
- **`ROUTE-ATTR-V1` measured the whole-voyage routes and the observation
  channel on the declared replay.** `tools/covid_route_attribution.py`
  attributes every infection event (not just the during-quarantine slice):
  the saturating seed burns 99.8% pre-quarantine, 90% droplet, in `other`
  venues + crew mess; the slow seeds re-centre during quarantine on cabin
  zones — the confinement channel. The droplet dose reaching infected
  agents is ~98% ring-side (near-field plume 60–69%, cabin-mate addback
  30–40%, far-field pool ~2%), bimodal per-agent — both channels sit above
  the infection threshold for most hosts, which is why every sampled-ring
  knob measured flat. The observation channel confirms ~76% of infected and
  dates 93–100% of confirmed datable-course cases at exact onset — vs the
  record's 197 of ~712 (0.28); 85–89% of the dated mass is mild, the
  stratum a real investigation dates worst. Dating ascertainment alone is
  ~3.4× of the ~18× gap. Remaining declared suspects: the cabin-mate
  addback / fixed rings (now the largest measured channel, ~⅓ of dose
  weight, inexpressible in the current arm grammar), the index's day-0
  exposure geometry, and an ascertainment arm that would split channel vs
  transmission shares of the gap
  (`docs/ledger/ROUTE-ATTR-V1.md`,
  `docs/covid/covid_route_attribution_v1_readout.md`, measured at
  `be121a0` locally on CPython 3.12).
- **The import x Theta axis is closed as negative, and the confinement leak is
  the live defect (COVID-VENT-AUDIT-01, `#645`).** `COVID-FIT-01` (`a686114`,
  1,180 cells) already swept imports 1-20: matching the early onset count
  overshoots the voyage total by 3-6x on every Theta row, and imports > 1 is not
  licensed by the record (Sekizuka 2020, single introduction before quarantine).
  The audit adds the anchor this arm never carried — DP's effective reproduction
  number **0.1 (SD 0.2) after** quarantine against 3.8 (SD 0.9) before (Azimi
  2021, grade B) — so the target is a sourced decay, not arrest. It also records
  that `hvac.filter_efficiency` = 0.50 is unsourced and its era-correct value
  (0.30) *increases* during-quarantine transport by 1.4x, and that
  `confinement_isolation_factor` 0.05, `corridor_direct_contact_factor` 0.15 and
  `NON_MATE_CONFINEMENT_CONTACT_FACTOR` 0.01 are unlabelled literals that govern
  the whole during-quarantine regime. `#645` adds the graded
  `hvac.outdoor_air_fraction_override` (absent by default) so the recirculation
  channel QUAR-ATTR-V2 measured at -66% can be evaluated between "as shipped"
  and "off"; the paired-seed bracket itself is **not run**
  (`docs/ledger/COVID-VENT-AUDIT-01.md`,
  `docs/covid/covid_dp_ventilation_sourcing.md`).
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
- ~~**795 repeat infection events at Θ = 1e9.** Hosts re-enter the susceptible
  pool; lifecycle not yet traced.~~ Traced: REINFECT-01 (§1). The open
  decision is whether to fix it before any further COVID campaign
  (`docs/ledger/QUAR-ATTR-V1.md`).
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
  `docs/ledger/THETA-SCREEN-V8.md`). Three probe cells at `main` = `4721b5b`
  confirm the invariant end-to-end (`index_onset_day == -1.0`,
  `index_shedding_at_day0` true, departure at epoch 120 in all three), **and say
  the grid is mis-centred**: every probe burns the ship (2,843–3,099 recorded
  onsets of 3,711 against covid.T1's 197) including the Θ 1e7 floor, consistent
  with v7's 40-seed cells wherever its index was in fact symptomatic aboard
  (median attack 0.709 at Θ 1e7, age 11 d). The v8 array should therefore **not**
  be submitted as declared; an admissible Θ, if one exists, lies below 1e7, where
  no screen has been, and the successor should declare a coarse wide downward
  recentring screen first with covid.T1 and the geometry invariant verbatim.
- **`covid_theta_screen_v9` is declared and supersedes v8, which was never
  submitted.** The successor re-centres on the quiet region v8's probes missed:
  ten decade Θ from 1e1 to 1e10 × three index infection ages (3.3 / 6.8 /
  12.8 d) × 20 matched seeds = 600 cells, with covid.T1 and the geometry
  invariant verbatim plus a reported-only `onset_mass_near_target` diagnostic
  (share of seeds inside [0.5×, 2×] the T1 onsets target) that separates a real
  hit from the v7 bimodal pass
  (`picard_framework/runs/covid_theta_screen_v9_design.json`,
  `docs/ledger/THETA-SCREEN-V9.md`).
- **`covid_theta_screen_v9` ran (600/600 at `main` = `0fb186b`); the
  infection-age axis is inert and the one covid.T1 pass is vacuous.**
  Measured (`docs/ledger/THETA-SCREEN-V9.md`,
  `docs/covid/covid_theta_screen_v9_readout.md`): (i) every (Θ, seed) payload is
  byte-identical across the three declared ages — with `onset_day` declared,
  `_apply_one_seed` sets incubation = age + onset_day − seed_day and stamps the
  history from `elapsed_since_onset`, so the age cancels exactly. **Every
  infection-age contrast on `diamond_princess_2020` under a declared
  `onset_day` is void**, including the age axes of v8 (never run) and v9; v9 is
  a 10-Θ × 20-seed locator. (ii) Under covid.T1 verbatim the admissible set is
  {Θ = 1e9}, interior, but it passes by its p10–p90 interval spanning 197 from
  8 extinct seeds to 12 burning seeds; `onset_mass_near_target` = 0.00 there
  and ≤ 0.10 everywhere. (iii) Θ sets the takeoff probability (0 at ≤ 1e3 →
  0.85 at 1e10), not the outbreak size (conditional-on-takeoff median onsets
  1,582–3,391 from 1e6 up); there is no near-critical band in [1e1, 1e10] for
  one declared import. **Θ = 1e9 may not be quoted as a fit or a selected
  value.** The pre-committed stage 1b (half-decade, 40-seed, six-age
  refinement) is withdrawn as a plan; the open decision is the criterion
  (trajectory under T1 with import geometry as the next axis, vs takeoff
  probability against covid.H3 with onsets scored conditional on takeoff),
  to be declared in a v10 design file before any cell runs.
- **covid.T1 as declared is satisfiable without mass near the target.** All
  eleven T1-passing cells on the v7 surface passed by spanning 197 between an
  extinction floor (`recorded_onsets_p10` = 0) and a burn ceiling (p90 316 to
  3,405), with attack q50 = 0.0000 in seven of them. No criterion is rewritten on
  that basis here: readouts must report the per-seed distribution beside the
  interval, and any tightening must be declared in a design file before its cells
  run. Session state of play, including what may not be reopened:
  `docs/covid/covid_theta_handoff_2026_09_19.md`.
- **`covid_theta_screen_v10` is fully measured — 200 of 200 cells — and the
  whole v9 Θ surface survives the repaired engine unchanged.** Measured at
  `main` = `a9b4f1f` on AWS Batch (`docs/ledger/THETA-SCREEN-V10.md`,
  `docs/covid/covid_theta_screen_v10_readout.md` §6): 200/200 children
  succeeded; takeoff fraction identical to v9 at every decade (0 at ≤ 1e3,
  0.10 / 0.15 / 0.10 / 0.20 / 0.35 / 0.60 / 0.90 at 1e4–1e10); **no seed of
  200 changes takeoff class**; `onset_mass_near_target` identical on every
  row; `infections_total` byte-identical to v9 on 154/200 cells including
  every extinct seed but one; `covid.T1` passes only at 1e9 in both. **Every
  v9 row is confirmed on the repaired engine, and the v10 surface CSV
  (`docs/covid/covid_theta_screen_v10_surface.csv`) supersedes the v9 CSV as
  the surface of record.** The v9 structural readings above —
  extinction-or-burn at every decade, Θ moving takeoff probability rather
  than size, no near-critical band — now stand at `a9b4f1f`, not `0fb186b`.
  The canary detail follows. Canary (Θ 1e9 × 20 seeds): the
  shared seed 20200205 reproduces the QUAR-ATTR-V2 `A0_declared` record exactly
  (3458 / 0.9318), takeoff is 0.60 on the same twelve seeds as v9 with
  `infections_total` moving ≤ 2.1% on any takeoff seed and identically zero on
  the eight extinct ones, and the conditional median attack rate is 0.865 in
  both. So QUAR-EXEMPT-01 and REINFECT-01 together do **not** move this row:
  consistent with the reinfection inflation having lived in the
  quarantine-window counts, which the screen payload never carried. Θ 1e9
  still may not be quoted as a fit. The `covid.T3` verdict on this row flips
  fail → pass on the same bimodal interval-span mechanism as covid.T1 and
  changes nothing. The screen payload has no episode or quarantine-window
  fields, so this campaign does not re-read those gates. Next decision (the
  criterion declaration): `docs/covid/covid_theta_handoff_2026_09_21.md` §8.
- **`covid_theta_screen_v11` stage 1 has run: empty admissible set on the
  decade lattice; the covid.H3 window is bracketed between Θ 1e10 and
  1e11** (`7660392`, array `33482fcc-7954-4566-928d-7052d62b83ee`,
  1,600/1,600 cells; readout
  `docs/covid/covid_theta_screen_v11_readout.md`, ledger
  `docs/ledger/THETA-SCREEN-V11.md`). Unconditional covid.T1 is measured
  vacuous (interval-span at 1e9, `onset_mass_near_target` 0.00), so the
  v10 `stage_2_fleet_shape` block is the stage-1 selector on generic 7-day
  voyages (8 decade Θ, 1e4–1e11, × 200 voyages, seed base 20201001);
  P(takeoff) climbs 0.00 → 0.575 and the recorded-attack median jumps
  0.0003 → 0.0158 across the last decade, straddling the H3 window
  [0.0005, 0.008] without a lattice point inside it — nearest cells 1e10
  (median misses floor 1.85×) and 1e11 (median/mean overshoot). Per the
  design, stage 2 does not run and the conditional read is quoted from v10
  (1,582–3,391 vs 197); generic takeoffs independently give DP-order
  recorded mass (median 175 at 1e10) in a 7-day voyage. **covid.H3 stays
  out of the held-out set for this screen**; covid.H1/H2 on
  `greg_mortimer_2020` remain held out (gated stage 3). In-flight
  user-approved amendment (#655): generic mode drops the DP's
  `molecular_ascertainment.start_day` — the day-14 historical testing
  start — so the recorded channel is live on generic voyages; the declared
  replay keeps it. The interior refinement
  `covid_theta_screen_v11_refine` ran at eighth-decade spacing
  ({1.33…7.5}e10 × 200 seeds, `79a3ac3`, array
  `45cfb31d-eb50-4042-9d6d-17499d9a3934`, 1,400/1,400 cells): **the
  stage-1 admissible set is non-empty — Θ ∈ {3.16e10, 4.22e10,
  5.62e10}**, an interior band ~0.25 decades wide (median-floor failures
  below, median+mean overshoot at 7.5e10). Stage 2 then ran
  (`covid_theta_screen_v11_stage2`, `8cda4c7`, 100/100 cells): **the
  conditional clause fails at every row — takeoff-seed recorded_onsets
  ~3,470–3,520 vs the record's 197 (~17.7×), onset-mass-near-target
  0.00, before_share 0.77–0.92 vs 0.173 — so the admissible set is
  empty** and the screen's question is answered: a Θ reproducing the
  covid.H3 fleet shape exists but cannot keep a conditioned declared
  voyage near the record; the deficit is conditional outbreak size (the
  during-quarantine arrest gap of COVID-VENT-AUDIT-01), not takeoff.
  Stage 3 does not run (nothing selected). Readouts
  `docs/covid/covid_theta_screen_v11_refine_readout.md` and
  `docs/covid/covid_theta_screen_v11_stage2_readout.md`, ledgers
  `docs/ledger/THETA-SCREEN-V11-REFINE.md` and
  `docs/ledger/THETA-SCREEN-V11-S2.md`.
- **`covid_sensitivity_assay_v1` is measured — all arms inert except the
  all-shared-air bound, which collapses takeoff**: 240/240 cells at
  `b88e0ad` (canary A0 + A11, array
  `f3065d9e-a605-456d-86b6-b097bbb7ac43`). On the frozen paired-seed
  metric every arm moves the conditional recorded-onset median <20%
  (largest mover: A11 arrest bound, −17.4% → 2,868 vs the record's 197)
  except `A5_all_shared_air_off` (3/20 takeoff → `takeoff_collapse`) —
  so the ~18× gap is measured unreachable inside the transmission layer
  and lives in the observational channel or natural history, per the
  declared decomposition (~4.7× over-burn × ~3.5× dated-onset
  bookkeeping). Structural finding: ~89% of recorded mass lands before
  the day-17 split (median 3,509 before vs 53 during), and the VSP-3%
  counter already confines ~87% of the ship by day 12 — the residual
  burn rides the unconfineable channels (cabin-mate full-dose addback,
  shared-corridor air, presymptomatic shedding). A10 first-report
  confinement was vacuous (bit-identical to A0 on all 19 paired seeds):
  the dense report stream trips both thresholds on the same schedule —
  conundrum, not bug. Readout
  `docs/covid/covid_sensitivity_assay_v1_readout.md`, surface
  `docs/covid/covid_sensitivity_assay_v1_surface.csv`, ledger
  `docs/ledger/SENS-ASSAY-V1.md`.
- **`covid_sensitivity_assay_v2` is declared, stood down
  pre-execution** (assay-1 now measured in full): v1's A11 arrest bound still records
  ~2,868 onsets on takeoff seeds vs the record's 197 under crew
  confinement + pool off + day-12 quarantine + perfect confinement +
  contact ×0.25 — the gap is not reachable inside the transmission
  layer, so v2 interrogates the observational channel (a subclinical/
  datable-onset bookkeeping arm) and natural history / mixing reach
  (symptomatic fraction, infectious window, shedding dispersion,
  effective-susceptible pool via secretor_negative_fraction,
  activity-contacts reach and CONTACT-ARCH-02 saturation). 11 arms × the
  same 20 seeds at Θ 4.22e10, 220 cells, plus a zero-cell observational
  annex scoring the dated-onset-equivalent on v1+v2 payloads. Design
  `picard_framework/runs/covid_sensitivity_assay_v2_design.json`,
  ledger `docs/ledger/SENS-ASSAY-V2.md`. Held pending droplet
  near-field/far-field route surgery: the v1 §2a attribution showed
  ~99% of the burn rides the well-mixed-room droplet pool, which the
  reach arms (B7–B9, `activity_contacts` only) cannot bound — see the
  stood-down note in `docs/ledger/SENS-ASSAY-V2.md`.
