# COVID-ONSET-FUNNEL-01
**Date:** 2026-11-20
**Commit:** c053e15f
**Pathogens:** sars_cov2_resp
**Status:** measured
**Measured at:** c053e15f

Channel attribution of the onset→specimen→record funnel at the fitted
operating point Θ=3.162e11, executed as option (i) of the
`covid_theta_handoff_2026_11_20.md` open decision: is the residual "too
many infections declared symptomatic" (truth side) or "the observation
layer dating/recording events the record never saw" (channel side)?
Method: pure readout of the committed `funnel_echo` payloads from
COVID-THETA-REFIT-01 (the same 20 DP `boxed_s1s2` cells + 50 GM
`hygiene_cycle` cells the campaign scored — no re-run, same
realizations), decomposed by `tools/covid_onset_funnel_readout.py`;
evidence `reports/onset_funnel/dp_theta_11p50.json`,
`reports/onset_funnel/gm_theta_11p50.json`. Record anchors from
`data/observation/covid_fit_targets.json`.

## Result — not a symptomatic-declaration defect: the residual factorizes into infection-volume overshoot × ungated dating × passive-channel over-confirmation

**DP `boxed_s1s2`, 20 cells (19 takeoff; seed 20200217 dead with 1
infection/0 confirmed), θ=3.162e11 — per-seed medians:**

| stage | model | record | factor |
|---|---|---|---|
| infections | 3,574 (96% attack) | ≤960 (serology band covid.H5 [712,960]) | **~4.4× over** |
| presented symptomatic | 2,955 (82.7% of infected) | ~0.82 share (never-symptomatic ~0.179) | share matches |
| lab_confirmed total | 3,274 | 712 | **4.6× over** |
| recorded_onsets | 2,879 | 197 | **14.6× over** |
| dated share of confirmed | 0.883 | 0.318 | 2.8× |
| campaign_positives | 460 | 634 | 0.73× (under) |
| campaign asym share | 0.841 | 0.505 | over |

The 14.6× recorded-onset overshoot factorizes as ~4.6× confirmed
volume × ~2.8× dating share (residual ~1.14 composition). Presented
share 0.827 ≈ the record's ~0.82 — **option (a), "too many infections
declared symptomatic", is rejected as a share**: symptomatic
declarations are right-sized; their count overshoots only because the
infection count does.

**Channel split (pooled, 19 takeoff cells):** 59,726 confirmed =
8,326 campaign (14%) + **51,400 passive (86%)** — ~2,700
passive-channel confirmations per seed that sit outside the record's
published specimen volumes. The passive channel confirms presenters
before the campaign days run, so the residual campaign pool is
enriched for never-presented hosts: of 8,326 campaign-positive hosts,
6,367 (76.5%) never presented, 278 (3.3%) pre-onset catches, 1,681
(20%) post-onset — the pre-onset catch deficit DATING-RES-01 named
persists (3.3% vs the record's ~31%), and the never-presented
dominance is what pushes the campaign asym share to 0.841 (over the
record's 0.505).

**Unconfirmed infected drains (pooled):** 1,269 never swabbed · 1
swabbed only pre-infection · 6,873 swabbed while infected but negative
— the sensitivity loss sits overwhelmingly in swabbed-and-missed, not
coverage.

**GM `hygiene_cycle`, 50 cells (all takeoff):** aboard 223; infections
median 180 (81%); presented 141.5 (~79% of infected — again
share-consistent); lab_confirmed 110.5 ≈ campaign_positives 108.5 (the
passive channel is nearly silent on GM — 58 pooled confirmations vs
DP's 86%); dpi at confirmation median 11.5 because the single test day
lands day 20: positive hosts are 75% post-onset, 23% never-presented,
2.6% pre-onset — the specimen-vs-course timing that makes GM asym read
0.272 vs the record's 0.8125.

## Verdict

The residual is **(b) the observation layer plus a truth-side volume
overshoot — not (a) symptomatic declarations**:

1. **Infection volume ~4.4× (DP)** — the dominant term. The fit's
   scored channels do not bound total attack: takeoff is binary and
   campaign_positives saturates (~440 pool after the passive channel
   skims presenters) while infections reach 96%. Θ restored record
   *observable* magnitude by saturating *true* incidence — a real
   landing on the scored axes, degenerate on the unscored one.
2. **Passive-confirmation architecture** — 86% of DP confirmations
   ride the sick-call→lab channel; outside the record's accounting.
   Its byproduct is the DP campaign-asym over-share (residual-pool
   enrichment), mirroring how GM's near-silent passive channel leaves
   campaign positives ≈ confirmed.
3. **Dating share 0.883 vs 0.318** — the shipped DP profile arms no
   `onset_recording` block, so every confirmed presenter is dated;
   ONSET-REC-01's armed channel bounds this to ~0.42–0.47 (still
   ~1.4× over the record).
4. **Specimen-vs-course timing** — the DATING-RES-01 seam, unchanged:
   DP incidence median infection day 7 (before quarantine day 16) →
   pre-onset catch deficit; GM's day-20 test lands post-onset (dpi
   11.5) → asym under-share. A transmission-tail-timing question, not
   a recording-channel one.

No constants touched, no re-runs, no gate changes — a measurement
entry only. The next bounded lever is the truth-side one: the scored
contract needs an attack-size/serology-aware observable (covid.H5
exists as a band but enters no scored term), so Θ cannot land
magnitude by saturating incidence the observation layer cannot see.
