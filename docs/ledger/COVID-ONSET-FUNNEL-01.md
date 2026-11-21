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
`data/observation/covid_fit_targets.json`. Specimen-row shares (what the
scored channel weights) classify positive rows by their own
`symptomatic_at_specimen` flag, preserving within-day order; takeoff
uses the scorer's gate (`recorded_onsets >= 10`).

## Result — not a symptomatic-declaration defect: the residual factorizes into infection-volume overshoot × ungated dating × passive-channel over-confirmation

**DP `boxed_s1s2`, 20 cells (19 takeoff under the scorer gate; seed
20200217 dead with 1 infection/0 confirmed), θ=3.162e11 — per-seed
medians:**

| stage | model | record | factor |
|---|---|---|---|
| infections | 3,574 (96% attack) | serology band covid.H5 [712,960] | **~4.3× vs midpoint 836 (range 3.7–5.0)** |
| presented symptomatic | 2,955 (82.7% of infected) | ~0.82 share of cases | share matches |
| lab_confirmed total | 3,274 | 712 | **4.6× over** |
| recorded_onsets | 2,879 | 197 | **14.6× over** |
| dated share of confirmed | 0.883 | 0.277 | 3.2× |
| campaign_positives | 460 | 634 | 0.73× (under) |
| campaign asym share | 0.841 | 0.505 | over |

The 14.6× recorded-onset overshoot factorizes as ~4.6× confirmed
volume × ~3.2× dating share (4.6 × 3.19 ≈ 14.7); the 4.6 confirmed
factor itself decomposes into ~4.3× infections (vs the band midpoint
836; the combined confirmed ratio is denominator-free, the split is
not) × ~1.05 ascertainment.
Presented share of *infected* is 0.827 ≈ the record's ~0.82
never-symptomatic complement — on the infected population the share is
right-sized. Honest caveat: the record's share is of confirmed cases,
so the check cannot prove the truth-side share is declared correctly —
what it rules out is over-declaration as the residual's *explanation*:
a share shift cannot produce a 14.6× volume overshoot, and on the
*confirmed* population the model's never-presented share is 0.111 <
the record's 0.179, i.e. the confirmed pool is directionally *more*
symptomatic-heavy, consistent with presenters being confirmed
preferentially by the passive skim (below).

**Channel split (pooled, all 20 cells):** 59,726 confirmed =
8,326 campaign (14%) + **51,400 passive (86%)** — ~2,700
passive-channel confirmations per seed that sit outside the record's
published specimen volumes. The passive channel confirms presenters
before the campaign days run, so the residual campaign pool is
enriched for never-presented hosts: of the **8,694 positive specimen
rows** (the rows the scored asym share weights — 8,326 distinct hosts),
6,692 (77.0%) never-presented, 408 (4.7%) pre-onset catches, 1,594
(18.3%) post-onset → asym-of-positive-rows 0.817 ≈ the observable
0.841. The pre-onset catch deficit DATING-RES-01 named persists
(4.7% vs the record's ~31%); the never-presented dominance drives the
asym over-share.

**Unconfirmed infected drains (pooled):** 1,269 never swabbed · 1
swabbed only pre-infection · 6,873 swabbed while infected but negative
— the sensitivity loss sits overwhelmingly in swabbed-and-missed, not
coverage.

**GM `hygiene_cycle`, 50 cells (48 takeoff under the scorer gate):**
aboard 223; infections median 181 (81%); presented 144.5; lab_confirmed
111 ≈ campaign_positives 110 (the passive channel is nearly silent on
GM — 58 pooled confirmations vs DP's 86%); dpi at confirmation median
11.5 because the single test day lands day 20: positive specimen rows
are 73.5% post-onset, 23% never-presented, 3.7% pre-onset
(asym-of-rows 0.265 vs the record's 0.8125) — the specimen-vs-course
timing that makes GM asym read under.

## Verdict

The residual is **(b) the observation layer plus a truth-side volume
overshoot — not (a) symptomatic declarations**:

1. **Infection volume ~4.3× (DP, vs band midpoint; 3.7–5.0 across the
   serology band)** — the dominant term. The fit's
   scored channels do not bound total attack: takeoff is binary and
   campaign_positives saturates (~440 pool after the passive channel
   skims presenters) while infections reach 96%. Θ restored record
   *observable* magnitude by saturating *true* incidence — a real
   landing on the scored axes, degenerate on the unscored one.
2. **Passive-confirmation architecture** — 86% of DP confirmations
   ride the sick-call→lab channel, outside the record's accounting.
   Its byproducts: the confirmed pool's never-presented share 0.111 <
   record 0.179, and the campaign asym over-share (residual-pool
   enrichment). GM's near-silent passive channel leaves campaign
   positives ≈ confirmed — same architecture, opposite asym sign.
3. **Dating share 0.883 vs 0.277** — the shipped DP profile arms no
   `onset_recording` block, so every confirmed presenter is dated;
   ONSET-REC-01's armed channel bounds this to ~0.42–0.47 (still
   ~1.5× over the record).
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
