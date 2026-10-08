# CREW-REACH-01
**Date:** 2026-10-08
**Commit:** #977
**Pathogens:** sars_cov2_resp
**Status:** measured
**Measured at:** 90b2fdae

The record's serial-testing + crew-reach observation structure armed on the
boxed Diamond Princess configuration — the honesty test for the crew-share
landing scored in the all-20-seed addendum of the covid open ledger.

Design: `picard_framework/runs/covid_crew_reach_01_design.json`,
doc `docs/covid/covid_crew_reach_01_design.md`. 4 arms × 20 seeds = 80 cells
at θ7.9e6, seeds 20200205–20200224, on `picard-analysis-fargate-queue`,
image `picard-campaign:covid-crew-reach-01` @ `sha256:6f0f72bc`,
jobdef `picard-covid-crew-reach-01:1` (Fargate). All 80 cells landed, zero
child failures.

Mechanisms shipped (PR #977):

- **`retest_tiers` on campaign days** (`data/observation/covid_testing_campaigns.json`,
  DP days Feb 15–20 + Feb 23) — tiers so declared may re-nominate hosts holding
  a negative result; new specimens only, confirmed hosts never re-swabbed.
  Declared record structure: Yamahata & Shibata 2020 documents cumulative
  3,894 tests vs 3,711 aboard (footnote b retests) — the declared DP campaign
  total now lands on exactly 3,894. Retest-tier day placement is Grade C
  declared (the record documents retests happened, not their schedule).
- **`crew_wave` day** (Feb 23, 831 tests / 57 recorded positives, crew-only,
  after passenger disembarkation) — armed only while
  `testing_campaigns.waves` lists it; voyage `duration_days` 32→35 so the
  documented campaign fits.
- **`observation_overrides` arm key** writes only
  `config_overrides.syndromic` (`retest_negative_sweeps`, `campaign_waves`) —
  disjoint from the boxed transmission block.

## Frozen-grammar corrections discovered at readout

Two design statements were written against a wrong arming model. They are
recorded here as errata; the frozen JSON is unchanged.

1. **The bit-identity clause is unmeetable by construction.** The design's
   `bit_identity_clause` assumed "the unarmed mechanisms are inert by
   construction (no retest set is computed; the wave day is filtered)". But
   `retest_tiers` is declared in the *scenario data*, not arm-gated — the
   record ran serial testing, so the truthful DP replica carries it on every
   arm including empty-override `boxed_declared`. The arm flag
   `retest_negative_sweeps` controls only the additional *sweep-tier*
   re-nomination. Retest-tier nomination consumes RNG draws, so day≤31
   infections DIFF vs the parent's archived boxed cells on 14/20 seeds —
   re-realization, not a mechanism-arming defect. The labelled pre-change
   baseline is the parent's boxed cells (pooled lab_confirmed 819); deltas
   are scored against it. A no-retest mode remains selectable by omitting
   `retest_tiers` from scenario data — no arm toggle exists and none is
   required by this leg.
2. **The audit's specimen-count bar was modeled wrong.**
   `campaign_specimen_retests` unions three channels — pre-existing
   indication retests (`retest_negatives_on_indication`, days ~16–24),
   declared retest-tier re-swabs (days 26–31), and S1 sweep re-nominations —
   so "zero retests on an unarmed arm" is not a reachable invariant. Arm
   distinguishability lives in the witness echoes
   (`retest_negatives_on_sweep`, `campaign_waves`), which were correct on
   all 80 cells.

## Readout

Measured at `90b2fdae`. Artifact `reports/crew_reach_01/readout.md`
(`campaigns/covid/crew_reach_01/readout.py`). Parent boxed = the landed
`campaign/covid_crew_mess_01/sect_mess_boxed/` cells, pooled lab_confirmed
819.

| arm | pooled lab_conf | Δ vs parent | crew share pooled | crew share DP-scale | asym share | dated share | deliv med | verdict |
|---|---|---|---|---|---|---|---|---|---|
| boxed_declared | 1354 | +535 | 0.399 | 0.308 | 0.184 | 0.733 | 192772 | record-truth base |
| boxed_s1 | 1333 | +514 | 0.398 | 0.315 | 0.156 | 0.761 | 192772 | NO-MOVE |
| boxed_s2 | 1453 | +634 | 0.440 | 0.350 | 0.246 | 0.689 | 192772 | MOVES-TOWARD-RECORD |
| boxed_s1s2 | 1451 | +632 | 0.447 | 0.358 | 0.231 | 0.696 | 192772 | MOVES-TOWARD-RECORD |

DP-scale cells (n_conf ≥ 100): 4 seeds now reach scale
(20200210, 20200218, 20200222, 20200223) vs 2 on the parent.

**Decomposition.** The declared `retest_tiers` alone (boxed_declared)
recapture +535 pooled — above the declared +250–400 band but consistent
with the drain it targets: 569 retest-confirmed against the ASYM-CONF-01
"burned by negative swab" drain of ~656 pooled-equivalent (~87% recapture;
some retests displace first-swab candidates inside the tier pool). The
`crew_wave` adds +97–99 pooled (161/121 wave-confirmed on armed arms).
S1 sweep re-nomination adds **nothing** (−21, NO-MOVE) while churning
~40,860 retest specimens vs 3,296 — once the record's serial-testing tiers
exist, additional sweep re-nomination finds nothing new.

**Honesty test (the scored question).** Crew share of lab_confirmed on
DP-scale cells moves 0.308 → 0.350/0.358 under crew reach — inside the
declared 0.29–0.4 "physics" band; the >0.5 hot-crew alarm does not trip.
Pooled share rises to 0.44–0.45 because the wave confirms crew that the
crew-starved ladder never reached. **Verdict: the crew-share landing reads
as physics — crew infections are not hot; they were under-ascertained.**

**Asym share** 0.184 → 0.23–0.25: correct direction (retests catch
pre-symptomatic negatives), still below the ~0.4 honest bound — the
never-presented infection share bounds the metric from the transmission
side, unchanged.

**Dated share** ~0.69–0.76 under the shipped channel vs record 0.277 —
the dominant residual gap stands; retesting does not fix dating.

**Guards:** confined-pax takeoff median 98 on DP-scale cells, in-band
[26,160] (per-cell range 0–129 across all arms vs parent 0–131 — same
distribution shape); witness echoes arm-correct on all 80 cells;
`funnel_hosts` + `campaign_specimen_log` present everywhere; zero audit
violations after the specimen-bar model correction.

**Deliveries guard — declared-input breach, not an arm effect.**
`service_deliveries` median 192,772 on every arm vs the declared ±15%
band around ~162k (band top 186,814). The move is +30.5k, uniform across
seeds and *identical* across all four arms — the observation overrides
do not touch service (parity itself is clean). It is the declared
voyage extension 32→35 days: ~3 extra service days including the
evacuation window at parent per-day scale accounts for ~+15k, and the
remainder is confined-population meal service through the longer
quarantine. The band was frozen at the parent's 32-day scale; rescale
the reference ~×1.19 or read it as parity-across-arms (which holds
exactly).

## What this settles / leaves open

- Settles: the crew-share landing (0.29-scale at DP scale) is physics, not
  ascertainment shading — crew reach lifts confirmations without lifting
  the share past the physics band.
- Settles: the record's serial-testing structure recaptures most of the
  burned-negatives drain; the expressible observation channel is now
  fully armed (ladder + retest tiers + crew wave + indication retests).
- Open: pooled lab_confirmed now overshoots the record (1354–1453 pooled
  vs 712/voyage record — the pool is a 20-cell sum; per-voyage scale on
  DP cells is the right comparison, and there the record sits between
  boxed cells' ~209–293 and reality's 712).
- Open: dated share 0.69+ vs record 0.277 remains the largest residual —
  a dating/onset-recording problem, not ascertainment.
