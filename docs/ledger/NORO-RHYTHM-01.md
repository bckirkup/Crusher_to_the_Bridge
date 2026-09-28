# NORO-RHYTHM-01
**Date:** 2026-09-28
**Commit:** 3d9d59c64cbe0473603ec26d1452361229268575
**Pathogens:** norwalk_gi
**Status:** measured
**Measured at:** 3d9d59c64cbe0473603ec26d1452361229268575

Paired A/B readout of the schedule-conditioned rhythm layer
(`rhythm.enabled`, `engines/rhythm_layer.py`) on the norovirus arm, dose
`dose_adjustment` 7.57 fixed (the NORO-DOSE-REFIT-01 value — withdrawn
pending refit like every dose figure in the repo; used here only because
both arms share it and the comparison is differential).

## Claims under test (spec §5)

- secondary-vomit placement shifts onto non-immune occupancy;
- post-prandial timing couples emesis to meal endings;
- ashore/queue structure changes port-heavy hulls;
- confinement-conditioned SOP decay leaves cabin landing as correct.

## Design

One cell = one voyage (one seed × one tier). Two arms over the same cell
layout: `rhythm.enabled: false` (labelled baseline) and `true`. Tiers:

| tier | platform | epochs | cells/arm | seeds |
|---|---|---|---|---|
| fl_exp_7d | expedition_cruise_450 | 168 | 1000 | 8000–8999 |
| fl_exp_12d | expedition_cruise_450 | 288 | 1000 | 8000–8999 |
| fl_spr_12d | spirit_cruise_3000 | 288 | 200 | 8105–8304 |
| fl_cls_12d | classic_cruise_1900 | 288 | 200 | 8105–8304 |
| fl_mega_12d | mega_cruise_5000 | 288 | 200 | 8105–8304 |

Attribution declared before the runs: an effect is real only if it moves
beyond paired-seed spread; rare-event cells report Wilson CIs, not point
rates.

Campaign artifacts: image
`picard-campaign@sha256:94a61d5832655484e0dbb14d848981e3024aac21af48f42e9580ada89d75ea09`
(tag `rhythm-ab-v1-3d9d59c`, `ENGINE_GIT_SHA=3d9d59c6`), job definition
`picard-rhythm-ab:1`. The landing-partition instrument was corrected
mid-campaign (see §7): class tiers reran on
`picard-campaign@sha256:3a50c5015b1b5f72eda42eec05f323acf2939daf6314f1ffec816a461798df4a`
(tag `rhythm-ab-v2-3d9d59c`), job definition `picard-rhythm-ab:2`,
results under `s3://crusherbucket-994254241749-us-east-1-an/campaign/noro_rhythm_01_v2/`.
Only `n_occupants`/`n_susceptible` fields on emesis rows changed; every
other reported number is from the v1 run
(`…/campaign/noro_rhythm_01/`), which is unaffected by the fix.

## Gates

- **Byte-identity: PASS.** `rhythm.enabled: false` reproduces
  pre-rhythm `ef81d2d3` byte-for-byte (per-epoch agent-state digest chain)
  on expedition 7d s8000 (`3a2c6899b388f2c3…`) and classic 12d s8105,
  checked on py3.12 local, py3.12 worktree, and the py3.11 Batch
  container. The v2 occupancy fix is draw-neutral: off-arm exp7d_s8000
  digest re-verified identical after it.
- **Flag consumption: PASS.** On-arm `attached=True` on 2600/2600 cells;
  commitments dealt (expedition ~8.3k, spirit ~106k dealt events on the
  canary); `emit_calls` splits into `post_prandial` vs `outside_window`;
  off arm emits the same call volume all `outside_window`.
- **Canary: PASS** (spirit-12d + expedition cells, off/on via `--index`)
  — the flag moves claimed metrics before arrays were submitted.

## 1. Takeoff / establishment

Ignition = ≥1 onboard acquisition; takeoff = `peak_prevalence ≥ 10`;
posted = VSP trigger epoch set.

| tier | arm | ignited | takeoff | posted |
|---|---|---|---|---|
| exp_7d | off | 57/1000 (5.7%, CI 4.4–7.3) | 0/1000 | 0/1000 |
| exp_7d | on | 59/1000 (5.9%, CI 4.6–7.5) | 0/1000 | 0/1000 |
| exp_12d | off | 57/1000 (5.7%, CI 4.4–7.3) | 0/1000 | 0/1000 |
| exp_12d | on | 59/1000 (5.9%, CI 4.6–7.5) | 0/1000 | 0/1000 |
| spr_12d | off | 67/200 (33.5%, CI 27.3–40.3) | 21/200 (10.5%, CI 7.0–15.5) | 0/200 |
| spr_12d | on | 67/200 (33.5%) | 21/200 (10.5%) | 0/200 |
| cls_12d | off | 52/200 (26.0%, CI 20.4–32.5) | 4/200 (2.0%, CI 0.8–5.0) | 0/200 |
| cls_12d | on | 50/200 (25.0%, CI 19.5–31.4) | 2/200 (1.0%, CI 0.3–3.6) | 0/200 |
| mega_12d | off | 126/200 (63.0%, CI 56.1–69.4) | 194/200 (97.0%, CI 93.6–98.6) | 0/200 |
| mega_12d | on | 127/200 (63.5%, CI 56.6–69.9) | 194/200 (97.0%) | 0/200 |

Paired ignition discordance (same seed, off vs on): exp 0 off-only /
2 on-only / 57 both (n=1000 per duration); spr 2/2/65 (n=200); cls
2/0/50; mega 1/2/125. Every discordance count is inside paired-seed
spread.

**Expedition does not convert under rhythm.** Combined expedition takeoff
0/2000 per arm. Measured against the NORO-REBASE-01 0/2000 baseline block
the upper bound tightens to ~0.19%/voyage at 95% Wilson on each arm;
ignition ~5.7–5.9% both arms, driven by the import stream, unchanged.

## 2. Secondary-vomit landing partition

Measured on the corrected instrument (v2 rerun, class tiers; expedition
contributes only 13 cabin landings total and was recorded under the v1
instrument — excluded here, see §7). Cabin landings split by stateroom
occupancy at emission epoch:

| tier | arm | cabin landings | solo shedder (occ=1) | non-susceptible occupancy (occ>0, susc=0) | susceptible present | shared-venue landings |
|---|---|---|---|---|---|---|
| spr_12d | off | 28 | 12 | 24 (85.7%) | 4 | 4 |
| spr_12d | on | 50 | 13 | 36 (72.0%) | 14 | 5 |
| cls_12d | off | 15 | 4 | 13 (86.7%) | 2 | 1 |
| cls_12d | on | 7 | 1 | 4 (57.1%) | 3 | 0 |
| mega_12d | off | 47 | 17 | 40 (85.1%) | 7 | 1 |
| mega_12d | on | 53 | 20 | 45 (84.9%) | 8 | 4 |

The GROWTH-01 "immune cabin" finding resolves on the corrected
instrument: **the cabin is the shedder's own stateroom** (median 2
occupants — the cabin pair), and the apparent immunity is structural, not
acquired. ~85% of secondary vomits land where no susceptible is present,
in two modes: the shedder vomits alone (~40% of cabin landings are solo
at emission epoch), or every co-occupant is already infected — on
non-solo non-susceptible landings, all occupants are infected in 95/95
cases (both arms), i.e. the cabinmate sits earlier on the same fomite
chain. The layer was asked to move
placement onto non-immune occupancy; measured movement is spirit-only and
within CIs (susceptible-present share of cabin landings off 4/28 vs on
14/50 — CIs overlap at 95%), zero on mega, opposite-sign on classic.
Placement does not move: **the rhythm layer is inert on the GROWTH-01
defect**.

## 3. Growth-chain depth

Concurrent-peak distribution on ignited voyages (median, max):

| tier | off | on |
|---|---|---|
| exp (both durations) | 2, max 5 | 2, max 5 |
| spr_12d | 8, max 14 | 8, max 17 |
| cls_12d | 5, max 11 | 5, max 9 |
| mega_12d | 16, max 29 | 17, max 29 |

Per-generation reproduction is **unmeasurable** with the current
instrument: 100% of sampled acquisitions (71/71 inspected) ride the
`fomite:norwalk_gi` reservoir pathway, which names a strain but no
`source_agent_id`, so every pedigree generation resolves `unresolved`.
The concurrent-peak table is the growth-depth readout for this campaign;
per-gen R needs a transmission-event source field that reservoir
acquisitions populate.

## 4. Anchor readout (scored, not shaped)

A8 attack-rate means and A9 posting rate per tier/arm; infection and
reported attack-rate channels on passenger and crew splits:

| tier | arm | A8 pax | A8 crew | A9 posting | pax infection AR | pax reported AR | crew infection AR |
|---|---|---|---|---|---|---|---|
| cls_12d | off | 1.07 | 2.63 | 0 | 0.0064 | 0.0004 | 0.0035 |
| cls_12d | on | 0.83 | 2.56 | 0 | 0.0060 | 0.0004 | 0.0035 |
| exp_7d | off | 1.87 | 3.96 | 0 | — | — | — |
| exp_7d | on | 1.92 | 3.96 | 0 | — | — | — |
| exp_12d | off | 0.99 | 2.06 | 0 | — | — | — |
| exp_12d | on | 1.12 | 2.19 | 0 | — | — | — |
| mega_12d | off | 1.12 | 1.90 | 0 | 0.0022 | 0.0000 | 0.0024 |
| mega_12d | on | 1.20 | 2.05 | 0 | 0.0022 | 0.0002 | 0.0024 |
| spr_12d | off | 1.64 | 2.29 | 0 | 0.0038 | 0.0005 | 0.0044 |
| spr_12d | on | 1.58 | 2.25 | 0 | 0.0038 | 0.0005 | 0.0033 |

All within paired-seed noise; nothing posts (0/5200 cells on either arm),
matching the cold-cell baseline.

## 5. Clock correlation

Post-prandial marking is live: 14.5–18.3% of `emit_emesis` calls on the
on arm carry `post_prandial=True` (mega 14.5%, spirit 15.5%, classic
16.3%, expedition 18.3%). The emesis timing histograms cluster
post-prandial events at meal hours (mega: hours 6–14 and 18–21
populated; expedition: 6–15 and 18–21) while non-post-prandial events
spread near-uniform across the clock — real timing modulation, measured.

Occupancy correlation with catalog event endings, however, runs opposite
the dispersal intuition: corridor occupancy is **depressed** at egress
epochs vs baseline (mega 736 vs 3084; spirit 707 vs 1187; classic 356 vs
789; expedition 58 vs 160), and dining means move mixed (mega 1797 vs
1297 up, expedition 136 vs 102 up; spirit 538 vs 677 down, classic 460 vs
428 roughly flat). Egress epochs capture the in-session epoch; agents
never spike corridors at +1 either — the catalog ending lands before the
physical dispersal. Schedule conditioning modulates *timing* of emesis
but does not create a corridor surge the rhythm claims lean on.

## 6. Defect witnesses

- Ashore dosing: 0 ashore-dosed epochs on 5200 cells (both arms) — the
  ashore-dosing defect does not reproduce under this campaign's
  configuration.
- Occupancy registering: fixed mid-campaign (see §2 note); compartment
  landings now record real stateroom occupancy.
- Emesis modulation: live (§5).
- Flag attachment: 2600/2600 on-arm, 0 failures.

## 7. Instrument defect (corrected mid-campaign)

`tools/noro_diag/rhythm_ab_probe.py` snapshotted occupancy from the
parent-zone map while emesis deposits address cabin-compartment keys, so
every cabin landing recorded `n_occupants=0` — this made all cabin
landings read as "empty" and, under an earlier `n_susceptible==0`
classification, as "immune-occupied". An interim report quoted the
artifact as "100% immune-cabin landing"; that number was the instrument
miss, not epidemiology. Fixed in `f22c7f9b`; class tiers rerun on the
corrected image (`rhythm-ab-v2-3d9d59c`, jobdef `picard-rhythm-ab:2`),
expedition tiers retained from v1 (they contribute ~0 secondary emesis
rows — 7/6 cabin landings across 2000 cells per arm — and their takeoff,
anchor, and clock numbers do not read the corrected fields). The class-tier
rerun reproduced every v1 number cell-for-cell (takeoff, anchors, clock,
defect witnesses identical between the v1 and v2 readouts), confirming the
fix is draw-neutral.

## Verdict

The rhythm layer is live everywhere it should be — attached on 2600/2600
on-arm cells, dealing commitments, marking post-prandial emesis, shifting
emesis timing onto meal hours — and **epidemiologically null on
norovirus at dose 7.57** on every measured channel: ignition, takeoff,
posting, growth depth, anchors, and secondary-vomit placement all sit
within paired-seed spread. Expedition stays at 0/2000 takeoff → tighter
upper bound (~0.19%/voyage at 95%). On this evidence the rhythm layer
does not gate a Lev re-rank by itself; the surviving path to expedition
takeoff and posting remains in the dose/import structure, not the
schedule layer.
