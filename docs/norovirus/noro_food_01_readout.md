# NORO-FOOD-01 readout — 9 scr cells, first fleet measurement of FOOD-COMMON-SOURCE-01

> **Status:** Resolved

Measured over 9,000 voyages, zero child failures, at engine `8e8ebc79`
(the FOOD-COMMON-SOURCE-01 merge SHA — the mechanism is in the image
natively, no in-container splices). Image `picard-campaign:campaign-
8e8ebc79-food01`, digest `sha256:75931b1d…` (the prompt-pinned
`46a46aa` digest turned out to be the base image — root-Dockerfile
`ENTRYPOINT`, no `deploy/aws/` or `tools/` — so an overlay was built per
`deploy/aws/Dockerfile.noro_food_01` and the jobdef repinned). Jobdef
`picard-noro-food-01:2`, prefix `campaign/noro_food_01/`, 9 arrays ×
1,000 children on `picard-campaign-queue` (~7.2 h wall). Canary
`bf81820c` (20 seeds, fl_exp_12d_scr bp32.5c18.5) verified zips,
`common_source_events` telemetry presence, and ≥1 event fired before the
fleet ran. Witness rows are harvested by the census driver because
`history_retention: compact` drops them from run zips otherwise — the
fleet image carried an epoch-observer harvest emitting the top-level
`common_source_events`/`exposures`/`telemetry` keys this readout reads;
on main the equivalent witness now ships as `payload["common_source"]`
(`{events, telemetry}` from `core._cs_event_log`, #893), which
`common_source_readout.py` also accepts.

Cell set: the three `*_12d_scr` tiers of `noro_outbreak_01_manifest.json`
× the shipped-rung diagonal bp25c7 / bp32.5c18.5 / bp40c30, nsf29, 288
epochs, dose_adjustment 7.57; seeds 8000–8999 (exp) / 8105–9104 (cls,
spr) — voyage-for-voyage paired with NORO-OUTBREAK-02/03/04.

## 1. Mechanism telemetry (per cell)

Full census reads (all 9,000 zips) via
`tools/noro_diag/common_source_readout.py`. `cs_food inf` = infections
dominant-route-attributed `common_source_food`; `(voy)` = voyages
carrying ≥1 such infection ("excursion voyages"). `zero-dose ev` counts
event rows whose realized `per_serving_dose` is 0.

| cell | voyages | w/event | ev/voy med (p90,max) | arm L/H/D % | takers/ev | zero-dose ev | cs_food inf (voy) | dose credited |
|---|---|---|---|---|---|---|---|---|
| exp 12d scr bp25c7 nsf29 | 1000 | 432 (43.2%) | 0 (6,23) | L25.6/H33.7/D40.7 | 10.7 | 809 | 1436 (94 voy) | 9.17e8 |
| exp 12d scr bp32.5c18.5 nsf29 | 1000 | 650 (65.0%) | 1 (8,33) | L15.8/H36.9/D47.2 | 10.7 | 1426 | 1454 (94 voy) | 1.02e9 |
| exp 12d scr bp40c30 nsf29 | 1000 | 780 (78.0%) | 3 (10,45) | L11.1/H39.7/D49.2 | 10.5 | 2037 | 1451 (94 voy) | 1.00e9 |
| cls 12d scr bp25c7 nsf29 | 1000 | 994 (99.4%) | 15 (32,89) | L2.7/H28.3/D69.0 | 26.4 | 10057 | 2878 (96 voy) | 1.81e9 |
| cls 12d scr bp32.5c18.5 nsf29 | 1000 | 1000 (100.0%) | 23 (42,79) | L1.9/H31.2/D66.9 | 26.4 | 14312 | 2985 (97 voy) | 1.74e9 |
| cls 12d scr bp40c30 nsf29 | 1000 | 998 (99.8%) | 28 (50,86) | L1.6/H33.6/D64.8 | 26.4 | 17354 | 3131 (96 voy) | 2.06e9 |
| spr 12d scr bp25c7 nsf29 | 1000 | 998 (99.8%) | 27 (49,114) | L1.7/H29.2/D69.1 | 25.8 | 17027 | 2546 (97 voy) | 1.36e9 |
| spr 12d scr bp32.5c18.5 nsf29 | 1000 | 1000 (100.0%) | 39 (67,125) | L1.2/H33.3/D65.5 | 25.2 | 23814 | 2592 (102 voy) | 1.72e9 |
| spr 12d scr bp40c30 nsf29 | 1000 | 1000 (100.0%) | 50 (80,131) | L1.0/H36.1/D62.9 | 25.0 | 29401 | 2452 (103 voy) | 1.42e9 |

Notes on reading it:

- **Event rows are per-epoch slices, not per-pan.** A scheduled
  provisioned lot emits one witness row per epoch of its pan window
  (~5–6 rows per lot, verified on s8105: five rows on one PizzaGrill
  lunch pan). The per-voyage lot draw is once per voyage per spec —
  dividing lot rows by ~5.5 gives ~82–87 lot voyages per cell, matching
  both the declared `lot_event_probability` U[0.02,0.15] interval
  (E[p] ≈ 8.5%) and the measured excursion-voyage share (§ below).
- **Handler/diner event counts scale with shedder population**, not
  per-epoch misfire: exp fires 0–3/voyage, cls 15–28, spr 27–50. Each
  shedding handler/diner present draws once per service window per
  spec, and the bigger hulls carry more simultaneous shedders.
- **~58% of event rows are zero-dose** on cls/spr (the realized deposit
  draws below a serving); on exp the share is ~46–50% by events.
- **Arm mix is diner-dominant** (D 63–69%, H 28–36% on the big hulls;
  D 41–49%, H 34–40%, L 11–26% on exp) — reversed vs the Clough prior's
  handler-favored ordering, consistent with the shipped duty-exclusion
  gate: reported symptomatic handlers never source an event, so only
  asymptomatic/unreported shedders feed the handler arm. Realized mix
  is a measurement, not a prior — flagged here for the design owner.
- **`common_source_food` carries 1.2–2.5% of infections on cls/spr and
  6.6–8.9% on exp** — far under the spec's >50% over-delivery alarm.
- **Excursion voyages = 873/9,000 (9.7%)**, remarkably flat across
  cells (94–103 per 1,000): essentially every voyage that schedules a
  lot produces `common_source_food` infections, and ~10–12 voyages per
  cell gain a few through the handler/diner arms without a lot.

## 2. Posting rate — paired vs NORO-OUTBREAK-02/03/04

`tools/noro_diag/outbreak_anchor_readout.py`, `--import-root` per
baseline campaign, same-seed pairing (n=1,000 pairs per cell).

| cell | baseline posted | food posted (Wilson 95%) | paired gained/lost |
|---|---|---|---|
| exp bp25c7 | 0.10% | 5.9% [4.6,7.5] | 58/0 |
| exp bp32.5c18.5 | 0.70% | 6.8% [5.4,8.5] | 61/0 |
| exp bp40c30 | 0.80% | 6.9% [5.5,8.6] | 62/1 |
| cls bp25c7 | 0.10% | 3.7% [2.7,5.1] | 37/1 |
| cls bp32.5c18.5 | 0.50% | 5.0% [3.8,6.5] | 47/2 |
| cls bp40c30 | 0.70% | 5.7% [4.4,7.3] | 53/3 |
| spr bp25c7 | 0.00% | 1.8% [1.1,2.8] | 18/0 |
| spr bp32.5c18.5 | 0.00% | 2.0% [1.3,3.1] | 20/0 |
| spr bp40c30 | 0.30% | 2.0% [1.3,3.1] | 18/1 |

Total paired: **374 gained, 8 lost** postings. The gain rides the
excursion tail and shrinks with hull size (exp ~+6pp → cls ~+4.5pp →
spr ~+2pp): an excursion delivers ~15 acquired on exp vs ~25–30 on
cls/spr, but the bigger hull's larger complement and larger propagated
background make that excursion a smaller passenger attack-rate share,
so fewer excursion voyages cross the A9 wire.

Anchor deltas vs baselines are modest and unalarming — Δtakeoff ≤ +2.4pp
everywhere; Δacq med +0 to +3; detect epoch shifts earlier on the
excursion-carrying cells (exp −139 to −28.5 epochs); A8 pax/crew counts
rise on posted voyages (+11 to +18 pax on exp). Full anchor tables:
`results/food01_anchor_{exp,cls,spr}.{md,json}` (untracked working
artifacts; the committed numbers are above).

## 3. Onset-curve re-readout — the falsifier

`tools/noro_diag/onset_curve_readout.py`, `--sample-per-cell 200`
(stride by seed; 147–186 measurable rows on exp, 200/200 elsewhere —
voyages with zero acquisitions contribute no burst). Baseline:
NORO-ONSET-CURVE-01 measured burst12 med **0.06–0.10** and share
burst12>0.5 = **0.00 on all six scr cells + mega**.

| cell | med acq | burst48 med | burst12 med | burst6 med | share burst12>0.5 |
|---|---|---|---|---|---|
| exp bp25c7 | 18 | 0.42 | 0.24 | 0.19 | 6% (147 sampled) |
| exp bp32.5c18.5 | 20 | 0.40 | 0.22 | 0.18 | 2% (173) |
| exp bp40c30 | 22 | 0.38 | 0.20 | 0.17 | 2% (186) |
| cls bp25c7 | 109 | 0.30 | 0.14 | 0.10 | 1% (200) |
| cls bp32.5c18.5 | 124 | 0.29 | 0.13 | 0.09 | 0% (200) |
| cls bp40c30 | 129 | 0.28 | 0.12 | 0.09 | 0% (200) |
| spr bp25c7 | 186 | 0.28 | 0.12 | 0.08 | 0% (200) |
| spr bp32.5c18.5 | 195 | 0.27 | 0.12 | 0.08 | 0% (200) |
| spr bp40c30 | 205 | 0.27 | 0.11 | 0.08 | 0% (200) |

**Excursion subset join** (burst rows × `cs_infections>0` from the
telemetry readout, same sampled voyages):

| cell | excursion n | burst12 med | >0.5 | rest n | burst12 med | >0.5 |
|---|---|---|---|---|---|---|
| exp bp25c7 | 19 | 0.45 | 8/19 | 181 | 0.19 | 1/181 |
| exp bp32.5c18.5 | 19 | 0.38 | 4/19 | 181 | 0.21 | 0/181 |
| exp bp40c30 | 19 | 0.36 | 4/19 | 181 | 0.19 | 0/181 |
| cls bp25c7 | 20 | 0.18 | 1/20 | 180 | 0.13 | 0/180 |
| cls bp32.5c18.5 | 21 | 0.22 | 0/21 | 179 | 0.13 | 0/179 |
| cls bp40c30 | 20 | 0.21 | 0/20 | 180 | 0.12 | 0/180 |
| spr bp25c7 | 22 | 0.13 | 0/22 | 178 | 0.12 | 0/178 |
| spr bp32.5c18.5 | 20 | 0.13 | 0/20 | 180 | 0.12 | 0/180 |
| spr bp40c30 | 22 | 0.12 | 0/22 | 178 | 0.11 | 0/178 |

**Verdict: the excursion signature is produced, and the burst metric
sees it where the hull is small enough to resolve it.** On expedition
cells, excursion voyages carry burst12 med ~0.36–0.45 with 16/57 sampled
excursions over the >0.5 point-source bar (vs 1/543 of ordinary
voyages) — the densest 12-epoch window holds ~40% of a voyage's
acquisitions, a real single-meal spike on a small hull. On classic the
excursion elevates burst12 (0.18–0.22 vs ~0.13 rest) but rarely crosses
0.5; on spirit it is invisible in burst12 (~0.13 ≈ rest) — a ~25-case
event dissolves into ~190–205 median acquisitions. The signature is in
the output, hull-scale-diluted: it shows in the onsets on exp, in the
posting counters on every hull (§2), and in the telemetry table (§1).

## 4. Incidence vs the real-world anchor

Baseline posted share (0.1–0.8% on scr cells) sat near real cruise
norovirus posting incidence (~0.3–0.5% per voyage from VSP/Mouchtouri
rates). The mechanism lifts posted share to ~2–7% — an order of
magnitude over the real anchor, driven by `lot_event_probability`
U[0.02,0.15] firing ~8.5–10% of voyages where roughly all scheduled
lots convert at least one infection. The interval is declared (not fit),
and the spec marks it a declared sweep axis: the incidence overcorrection
is a *measurement*, the expected reading of an unfitted interval —
viable candidate for a posture/probability sweep in the next stage, not
a mechanism defect.

## 5. Report-trigger audit (spec §"Report-immediately")

- Events ≫1/voyage: handler/diner draws scale with shedder count by
  spec; medians 0–50/voyage across hulls, ~58% zero-dose — consistent
  with per-(shedder, window) draws, not a per-epoch detector bug.
- `common_source_food` >50% of transmissions: no — 1.2–8.9% per cell.
- Zero events under forced lot=1: n/a (no forced cells); unforced lot
  incidence ~8.5–10%/voyage is alive.
- Dose to absent agent / oversized cohort: cohort ≤ venue capacity
  (servings_taken ≤ pan_servings ≤ 80, observed takers 8–26/ev).
- Arm mix vs Clough prior: diner-dominant — flagged in §1; consistent
  with duty-exclusion suppressing reported symptomatic handlers, worth
  a design-owner look before any sweep.
- Posting order-of-magnitude: moved ~7–20× upward — reported to the
  user mid-campaign; mechanism-intended direction.

## Fleet ledger

Arrays (picard-campaign-queue, jobdef `picard-noro-food-01:2`, image
`campaign-8e8ebc79-food01` @75931b1d):

- exp: `6b814f25` / `343940fc` / `02f294d5` (offsets 0/1000/2000)
- cls: `d62bc6e0` / `c34eba87` / `fadd6344`
- spr: `4e5cec59` / `96937758` / `95e786b5`
- canary: `bf81820c` (20/20 SUCCEEDED); dead rev-1 canary `d24c617a`
  (terminated — base-image entrypoint, fixed by overlay)

9,000 children, 0 failures, ~7.2 h wall on Spot (no drought; On-Demand
escalation not needed). Deviations from the brief: (a) prompt-pinned
image was the base layer — overlay built and jobdef repinned;
(b) a census witness harvest was needed to keep telemetry in zips
(observation-only) — the merged tree converges on #893's
`_cs_event_log` harvest rather than the fleet image's epoch-observer
variant. No engine/constant changes, no mechanism edits.
