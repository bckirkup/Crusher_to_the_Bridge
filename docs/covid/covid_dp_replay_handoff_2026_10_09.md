# COVID DP replay: state of play at 2026-10-09 handoff

> **Status:** Handoff record (2026-10-09), authored at the close of the
> Diamond Princess replay-believability session. It states where the DP line
> stands after the meal-service, crew-structure, observation-funnel, and
> dating-residual legs, what is measured on record's own metrics, and the
> single open decision. It reports no new numbers: every figure is quoted
> from the ledger entry or readout that measured it, with that entry's own
> `Measured at` SHA. Nothing here is a fit.

## 1. The question

Does the boxed DP replica (`sect_mess_boxed` base, θ 7.9e6, seeds
20200205–20200224) reproduce the voyage record's observable structure —
and where it does not, is the gap transmission or observation? Scored
observables, as they evolved this session:

- confined-pax during-window bound [26,160] (the MEAL-SVC deliverable);
- crew share of the record's **confirmed** cases: 0.29 (declared band
  (0.2,0.4)) — clarified mid-session that the comparator is lab_confirmed,
  total voyage, conditioned on comparable realized outbreak scale;
- dated-onset share of confirmed: 197/712 = 0.277;
- asymptomatic-at-specimen share of confirmed: ~0.49 (Mizumoto 2020);
- confirmed-case scale: 712.

Success = each observable lands its declared band under record-faithful
structure only. Failure = a gap reachable only by fitting constants to the
anchor — which is forbidden (§9).

## 2. Current hypothesis

The DP replay is resolved on the record's own metrics at the record's own
scale. Crew share is physics (lands in-band under the record's full
ascertainment structure); the confirmed-case mix's shortfall was
ascertainment structure, since repaired with record-faithful serial testing
+ crew reach. The one standing residual — dated share ~0.42–0.47 vs 0.277 —
is decomposed to a pre-onset-catch deficit whose root is the model's
incidence tail dying ~3–5 days before the last specimen mass. That is a
transmission-tail-timing question, not an observation-channel one, and no
record-faithful observation lever remains against it.

## 3. Evidence for

- **Confined-pax bound landed.** `MEAL-SVC-02` full grid, measured at
  `54086e4c` (`docs/ledger/MEAL-SVC-02.md`, readout
  `docs/covid/covid_meal_service_02_readout.md`): MAGNITUDE-LANDED on the
  section arm, median confined pax in [26,160].
- **Crew dining cannot reach 0.29.** `CREW-MESS-01` canary, measured at
  `cca98cdc` (open ledger §3): boxed mess closure moves crew share only
  0.841 → 0.727; residual ~73% occupational + ~27% berth per the berth
  attribution (#957, `tools/covid_berth_attribution.py`, same-realization
  rerun on `cca98cdc` cells).
- **Berth/mess intervention ceiling exhausted.** `CREW-BERTH-01` canary,
  measured at `2d70237c` (`docs/ledger/CREW-BERTH-01.md`): maximal arm
  0.727 → 0.662 — every truthful contact-structure lever saturates well
  above the band.
- **Crew share is physics at record scale.** All-20 funnel attribution
  (#969, `tools/covid_funnel_attribution.py`, `reports/funnel_attr/`):
  pooled lab_confirmed crew share 0.435 unconditional, but share falls
  monotonically with realized outbreak size; on DP-scale cells 0.293 ≈
  record 0.29. The scoring rule (condition on outbreak scale) is committed
  in `docs/covid/covid_open_ledger.md`.
- **Honesty test held.** `CREW-REACH-01` canary, measured at `90b2fdae`
  (`docs/ledger/CREW-REACH-01.md`, `reports/crew_reach_01/readout.md`):
  crew reach lifts confirmations +97–99 pooled while DP-scale crew share
  moves only 0.308 → 0.350–0.358, inside the band — infections were
  under-ascertained, not hot.
- **The record's serial testing recovers the drain.** Same entry: declared
  `retest_tiers` recapture +535 pooled lab_confirmed (~87% of the
  burned-negatives drain); the campaign total now equals the documented
  3,894 cumulative tests.

## 4. Evidence against / unexplained

- **Dated share ~0.42–0.47 vs 0.277** — the standing residual, fully
  decomposed by `DATING-RES-01` (#979, `docs/ledger/DATING-RES-01.md`,
  `tools/covid_specimen_timing_probe.py`, measured on `boxed_s1s2` cells
  by same-realization rerun): the model's asym-at-specimen share ~0.27 =
  never-present ~0.22–0.25 (already ≥ the record's delay-adjusted 0.179)
  + pre-onset catches ~0.04–0.05 vs record ~0.31. Root: confirming
  specimens land median dpi ~6 vs a ~4–5-day pre-onset window, and the
  realized incidence tail dies ~3–5 days before the last specimen mass.
  Decomposed and named; **not** explained away.
- **Confirmed-case scale under the record**: ~193 confirmed/cell pre-reach
  (ASYM-CONF-01, `29f5e8d1`), ~1451 pooled post-reach vs 712 on one voyage
  — F6 shape-right/scale-low territory, unchanged this session.
- **Null diagnostics**: contact-of-confirmed densification counterfactual
  only +10.5/+22 expected pre-onset positives (DATING-RES-01); S1
  re-nomination sweep NO-MOVE (−21, CREW-REACH-01); SENS-ASSAY-V1's
  `A9_perfect_confinement` inert (~−1.3%); corridor-pool audit found no
  defect — 30/31 confined-in-berth no-mate events are `service_to_host`
  door-drop deliveries (declared physics, #964).

## 5. PRs landed this session

Dependency order; child-session PRs marked:

- #952 — MEAL-SVC-02 canary readout (STILL-HIGH on `cf_lo`)
- #953 — MEAL-SVC-02 full-grid readout (MAGNITUDE-LANDED)
- #954 — NORO-SVC-01 isolated-host emesis deposit repair (child
  `e8a6353b`, noro line)
- #955 — CREW-MESS-01 readout (child `6e6a80e9`)
- #957 — berth attribution tool + readout
- #960, #962 — CREW-BERTH-01 mechanism + readout (child `416e0b47`)
- #964 — recorded-onset share cross-check + corridor audit (docs)
- #968 — funnel attribution tool + 3-seed read
- #969 — all-20 funnel attribution + amended scoring rule
- #972 — ONSET-REC-01 design + canary (child `2e57fa57`)
- #976 — ASYM-CONF-01 attribution + arm-family-negative (child `fad08af0`)
- #977, #978 — CREW-REACH-01 mechanism + canary (child `bd224ee2`)
- #979 — DATING-RES-01 specimen-timing decomposition + this handoff

## 6. Running jobs

None. All Batch arrays landed and were read out; all six child sessions
are settled (archived or awaiting instructions). No canary is in flight.

## 7. What is now void

- **Crew-share comparisons scored on acquisitions or during-window
  subsets** — the record's 0.29 is the crew share of *all confirmed cases*
  over the *whole voyage*, conditioned on comparable realized outbreak
  scale. Every earlier during-window vs record comparison (the hot-crew
  readings of this session) was a metric mismatch, superseded by the
  committed scoring rule (#969, open ledger).
- **The 3-seed funnel orientation read (0.322)** — superseded by the
  all-20 conditioned measurement (#969); the orientation sample was the
  three largest cells.
- **Bit-identity clauses vs parent archived cells** for mechanisms shipped
  as scenario data — unmeetable by construction (the mechanism fires on
  every arm; parent archived cells are the labelled baseline). Recorded in
  `docs/ledger/CREW-REACH-01.md` errata.
- **Deliveries-parity bands frozen at the 32-day voyage** — the 32→35-day
  extension shifts deliveries ~162k → ~193k uniformly across arms; bands
  must be rescaled (`docs/ledger/CREW-REACH-01.md`).
- **`covid_meal_service_handoff_2026_10_06.md` §"open decision"** —
  superseded: the section arm landed the bound (MEAL-SVC-02).

## 8. The single open decision

**Close the covid believability line, or open a transmission-tail-timing
investigation.** The line is resolved on the record's metrics at record
scale (confined-pax bound, crew share 0.293 physics) and every remaining
residual is decomposed-and-named. The tail-timing leg would compare the
model's incidence-curve tail (max infection day ~30–31) against the
record's confirmed-case curve — the literature's epidemic curves exist —
to test whether DP transmission really died when ours does. It is honest
work only as a shape comparison; fitting incidence timing to the dating
anchor is forbidden. If the curve matches, the line closes with the
bound statement on record.

## 9. Do not reopen

- The two zero rungs of `lab_sampling_probability_by_severity`
  ([0,0,0.4,0.75,0.95]) — declared observation model, forbidden.
- `report_probability` (0.56) — frozen channel constant; retuning it to
  chase 0.277 is fitting to the anchor.
- Refitting incidence/takeoff timing to the dating residual — the tail is
  a measurement target, not a knob.
- Scoring crew share on any comparator other than lab_confirmed, total
  voyage, conditioned on realized outbreak scale.
- The scoring grammar that produced each verdict above — declared
  pre-run bands stand even where the landing was unfavourable
  (CHANNEL-INSUFFICIENT, CEILING-SHORT, ARM-FAMILY-NEGATIVE are results,
  not failures of the leg).
