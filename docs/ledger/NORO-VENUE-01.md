# NORO-VENUE-01
**Date:** 2026-09-28
**Commit:** 27d818d8 (instrument merge; census driver `tools/noro_diag/venue_placement_census.py`, readout `tools/noro_diag/venue_census_readout.py`)
**Pathogens:** norwalk_gi
**Status:** measured
**Measured at:** 27d818d8 — AWS Batch `picard-venue-census:1` on image `picard-campaign@sha256:4a0f4165a73721e98db18f287ded159dd0a79e1eca659eb682adc05bf7f67fcc` (tag `venue-census-27d818d8`, `ENGINE_GIT_SHA=27d818d8`); spirit block also reproduced locally on the same tree.

Emesis-vs-confinement placement census on the norovirus arm,
`dose_adjustment` 7.57 (the NORO-DOSE-REFIT-01 value — withdrawn pending
refit like every dose figure in the repo; reported for cell identity
only, not as an absolute dose claim).

## Claim under test

Confinement latency vs emesis timing gates venue placement: if hosts are
flagged and confined before they vomit, all emesis lands in
structurally-immune staterooms and the chain dies by construction. Live
alternatives: (a) the pre-confinement mobile window on symptomatic
cases; (b) never-symptomatic hosts emitting to shared space
indefinitely.

## Cells

| cell | runs | ignited | ignition basis |
|---|---|---|---|
| fl_spr_12d (spirit_cruise_3000, 3000) | 12 | 10 | ignited seed set from NORO-GROWTH-01/RERANK + paired 8106 |
| classic_cruise_1900 (1910, post-mutated spirit spec) | 60 | 13 | contiguous 8105–8164; ignition discovered per cell |
| fl_mega_12d (mega_cruise_5000, 7000) | 60 | 43 | contiguous 8105–8164; ignition discovered per cell |

Classic ignition 13/60 (~22%), mega 43/60 (~72%) — the mega rate matches
the manifest's predicted ~0.75. Spirit block restricted to the known
ignited set; mega/classic ran the full contiguous block because
per-hull ignition is seed-dependent.

Join attribution: **224/224 emit events attributed** to a confinement
class, 0 unattributed (≥99% gate satisfied on every hull).
`_emit_emesis` invocation counts (10.37M spirit / 33.0M classic / 120.96M
mega) are once-per-agent-epoch plumbing, not emit attempts.

## 1. Emesis × confinement join

All 224 events were emitted by `symptomatic_onboard` hosts; the
`never_symptomatic` emitter class contributes **zero** events and zero
emesis mass on all three hulls.

| confinement class | spirit | classic | mega | total |
|---|---|---|---|---|
| pre_confinement | 0 | 0 | 0 | 0 |
| post_confinement | 29 (72.5%) | 23 (76.7%) | 122 (79.2%) | 174 (77.7%) |
| never_confined_at_emit | 0 | 1 | 0 | 1 (0.4%) |
| never_confined | 11 (27.5%) | 6 (20.0%) | 32 (20.8%) | 49 (21.9%) |

## 2. Landing-site taxonomy (confinement × site)

Events (emesis mass in parentheses, readout units — relative only):

| class \ site | stateroom_pax | stateroom_crew | dining_pax | venue_free |
|---|---|---|---|---|
| post_confinement | 133 (9.31e9) | 41 (3.18e9) | 0 | 0 |
| never_confined_at_emit | 1 (4.09e7) | 0 | 0 | 0 |
| never_confined | 16 (1.64e9) | 2 (4.04e6) | 11 (9.35e8) | 20 (1.68e9) |

Every post-confinement event lands in a stateroom — confinement is
absolute for compliant hosts. **31/31 shared-venue landings
(dining_pax + venue_free) belong to `never_confined` hosts**, and all
of those carry `order_subclass = ordered_refused`: the refuser channel
is the sole venue-emesis pathway. The one `never_confined_at_emit`
event (classic) is an ordered-but-never-admitted host; there are no
`ordered_mobile` events — no host vomits between order and admission
because admission is same-epoch.

## 3. Placement quality (≥1 susceptible co-occupant)

| landing | spirit | classic | mega | pooled |
|---|---|---|---|---|
| never_confined → shared_venue | 8/8 (CI 68–100) | 4/4 (CI 51–100) | 19/19 (CI 83–100) | **31/31** |
| never_confined → own_stateroom | 2/3* | 2/2* | 7/13* | 11/18 (61%) |
| post_confinement → own_stateroom | 9/29 (31%) | 10/23 (43%) | 28/122 (23%) | 47/174 (27%) |

(*small denominators; Wilson 95% CIs in the readout.)

Venue landings are perfectly susceptible-rich. Even post-confinement
stateroom landings find an uninfected cabinmate ~27% of the time — the
NORO-RHYTHM-01 structural-immunity partition (~85% no-susceptible)
repeats at ~73% here, same order.

## 4. Confinement-latency distribution

| latency (epochs) | spirit | classic | mega |
|---|---|---|---|
| onset → order | 0 (n=28) | 0 (n=43) | 0 (n=162) |
| order → confined | 0 (n=23) | 0 (n=35) | 0 (n=136) |
| onset → confined | 0 | 0 | 0 |
| detect → reported | median 8, max 147 | median 7, max 101 | median 15.5, max 137 |

Per-host: every symptomatic host is ordered **the same epoch it
presents**; compliant hosts are admitted that epoch and emit their first
vomit 3–102 epochs later (all mass lands post-confinement stateroom).
The reporting channel has a real median 7–15 epoch lag (tail to ~147)
but does not gate confinement — orders fire on symptom presentation,
not on reports. The latency question is therefore **order-limited and
the order latency is zero**; the only mobile-emesis pathway would be
refusal, and refusers emit at full mobility.

Action mix across hulls: 194 `immediate_compliance`, 39
`refused_quarantine` (+1 ordered-not-admitted). Confined hosts are
`symptomatic_onboard` to a host (194/194).

## 5. Verdict — (b): the barrier is downstream of placement

- Zero pre-confinement events on any hull: the confinement clock wins
  every race it enters, so **confinement latency is not the named gap**
  for placement — it is already zero-latency on order and admission.
- Venue emesis already lands susceptible-rich: 31/31 shared-venue
  landings (dining, lounge/transit) found ≥1 susceptible co-occupant,
  at ~14% of emesis events and ~22% of emesis mass.
- The entire venue pathway is the **defiant-refuser channel** — hosts
  ordered at symptom onset who never confine. FRED refusal rate here is
  ~17% of ordered hosts (39/233) and they carry ~22% of emesis mass at
  full mobility.
- Zero never-symptomatic emitters: the never_symptomatic import axis in
  NORO-IMPORT-01 does **not** translate into venue emesis in this stack
  — symptomatic refusers dominate that channel instead. Cross-report to
  NORO-IMPORT-01: if the import mix shifts toward never-symptomatic
  emitters, venue mass could move even though placement is already
  good.
- Placement is therefore not the binding constraint: with venue
  landings already 100% susceptible-rich, the starvation observed in
  NORO-GROWTH-01/EXPOCAP-01 sits downstream (pickup/conversion under
  the exposure cap), not in emesis placement.

## Caveats

- Emesis-mass figures are engine-internal units; valid for relative
  comparisons only (dose ledger withdrawn).
- 2/12 spirit seeds were non-ignited (8106, 8159 — the latter boarded
  an infected host but produced no vomit); classic/mega ignition was
  discovered, not conditioned.
- `detect → reported` latency is the reporting counter's lag; it does
  not enter the confinement order path, so it is reported as context,
  not a gating distribution.

Artifacts: `out/noro_diag/venue_census/{fl_spr_12d,classic_cruise_1900,fl_mega_12d}/*.zip`
(local mirror of `s3://crusherbucket-994254241749-us-east-1-an/campaign/noro_venue_01/`);
readouts `out/noro_diag/venue_readout_{spirit,classic,mega}.json`;
array jobs `f822cadb-980b-49a4-b189-6f63b386ffe7` (mega, 60/60),
`d6449cee-4475-41d8-bc2f-e0fc3a3654ea` (classic, 60/60); canary
`be34c2e4-006e-424a-897c-020af60ba8b6`.
