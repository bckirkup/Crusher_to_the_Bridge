# NORO-MEGA-IMPACT-01 readout — 2×2 mechanism-attribution factorial on mega_cruise_5000

> **Status:** Resolved

Measured over 926 zips (zero child failures) per the frozen readout
list in `noro_mega_impact_01_design.md`. Arms: A1/A2/A3/a1_bp40c30 ran
on fleet image `campaign-7e1b54bc` (sha256:60793dd3…, engine SHA
`7e1b54bc` = the #893 census-witness merge, `--payload lean`, 6144
MB/child, `picard-campaign-queue`, ~4.5 h Spot wall); A0 is the
existing NORO-MEGA-01 `fl_mega_12d_scr` bp25c7 zips re-read through the
same row extractor (engine `1e158d47`, CAREGIVER-V1 + PROPENSITY-V1 —
pre-food, pre-witness image: no `mechanisms` block, but the
route-mix/funnel summary fields are present and identical in shape).
A1↔A0 pairing is per-seed on the dedicated `SeedSequence(spawn_key=
0xF00D)` stream — 287 shared seeds (the fleets' seed windows differ by
one at the top: A0 carries 8288, A1 stops at 8287). The a1_bp40c30
slice is distributional only — no A0 exists at bp40c30.

Posting wires on mega (`A9_POSTING_THRESHOLD = 0.03` of complement,
rounded up): **147 passenger / 63 crew** reported cases. Tool:
`tools/noro_diag/mega_impact_fleet_readout.py` (regenerates
`results/mega_impact_fleet.{md,json}`); census witness pass adds the
food-event aggregates (`--census`).

## 1. Arm table — who posts on mega

| arm | config | n | posted | detected | med rep pax (of 147) | med rep crew (of 63) | max ratio | ≥80% | ≥90% |
|---|---|---|---|---|---|---|---|---|---|
| A0 | cg on / food off | 288 | 0 | 29 (10%) | 56 (0.378) | 18 (0.286) | 0.746 | 0 | 0 |
| A1 | cg on / food on | 288 | 0 | 35 (12%) | 56 (0.381) | 18 (0.286) | 0.810 | 1 | 0 |
| A2 | cg off / food off | 150 | 0 | 5 (3%) | 42 (0.286) | 11 (0.175) | 0.497 | 0 | 0 |
| A3 | cg off / food on | 150 | 0 | 10 (7%) | 42 (0.286) | 10 (0.167) | 0.762 | 0 | 0 |
| A1 | bp40c30 | 50 | 0 | 18 (36%) | 61 (0.415) | 25 (0.397) | 0.857 | 1 | 0 |

(A0 restricted to the a2/a3 seed window 8000–8149 is unchanged: med
55.5 / 18, max 0.746, detected 15/150 — the mechanism-off baseline is
seed-window-insensitive.)

**No arm posts to VSP — 0/926 voyages.** The design's honest
expectation confirmed, with the attribution it was built to measure:

- **Caregiver is the mega report channel.** Dropping it (A2 vs A0)
  removes ~25% of passenger reports (med 56→42) and ~39% of crew
  reports (18→11), and collapses detection (29/288 ≈ 15/150 → 5/150).
  On the pooled funnel 87.9% of A1 reports arrive via the caregiver
  stamp — vs ~half on the expedition hull in CHANNEL-04. On a
  7,000-agent voyage the discovered-illness stamp, not the self-report
  hazard, is what reports are made of.
- **Food moves only the tail.** Medians are identical to A0 (paired
  deltas below); the maximum reach extends 0.746 → **0.810** and
  produces the first ≥80%-of-wire voyage ever measured on mega (seed
  8119, crew channel, a `common_source_food`+31 excursion voyage). It
  still stops ~19% short of the 63-report crew wire.
- **Boarding prevalence lifts the whole curve without changing its
  shape** — bp40c30 med ratios +3–4pp, detection 12%→36%, max 0.857,
  but 0 posts and the same clipped-ramp onset.

## 2. Paired A1-vs-A0 deltas (the food mechanism's per-seed effect)

287 same-seed pairs. Median delta is **0 on every field** — the
mechanism is invisible on the median voyage because ~90% of voyages
never schedule a provisioned lot. The effect lives in the top decile:
p90 deltas +9 pax reports / +5 crew reports / +21 acquisitions.

| field | median Δ | p90 Δ | share >0 |
|---|---|---|---|
| rep_pax | 0 | +9 | 0.31 |
| rep_crew | 0 | +5 | 0.29 |
| n_acquired | 0 | +21 | 0.30 |
| ever_ill_pax | 0 | +8 | 0.29 |
| ever_ill_crew | 0 | +6 | 0.28 |
| burst12 | 0 | +0.006 | — |

**Posting transitions: +0 / −0 / 287 unchanged.** (FOOD-01 measured
374 gained / 8 lost on the small hulls — same tail mechanism, but on
mega the excursion dilutes into a ~490-acquisition baseline and the
3%-of-7,000 wire sits further out.)

## 3. Onset shape — still a propagated ramp everywhere

| arm | burst12 med | p90 | max | >0.5 | still climbing | peak_ep med | det_ep med |
|---|---|---|---|---|---|---|---|
| A0 | 0.183 | 0.204 | 0.243 | 0 | 271/288 | 287 | 282 |
| A1 | 0.183 | 0.204 | 0.256 | 0 | 272/288 | 287 | 279 |
| A2 | 0.186 | 0.210 | 0.234 | 0 | 142/150 | 287 | 283 |
| A3 | 0.186 | 0.211 | 0.240 | 0 | 143/150 | 287 | 275 |
| A1 bp40c30 | 0.283 | 0.300 | 0.333 | 0 | 46/50 | 286 | 278 |

Zero voyages over the >0.5 point-source bar on any arm — now
**926/926 on mega plus the ~10,000 small-hull voyages of
FOOD-01/OUTBREAK-02/03/04**. Every curve peaks at epoch 287 (the last
epoch): the ramp is still rising when the voyage ends on ~94% of
voyages.

The excursion voyages themselves carry no visible signature at this
scale: A1 excursion-voyage burst12 med 0.185 vs 0.183 on ordinary
voyages (max 0.256). A ~19–65-infection common-source event inside a
~490–580-acquisition ramp is a single-window bump below the ramp's own
variance — the signature FOOD-01 resolved on the expedition hull
(excursion burst12 0.36–0.45) is structurally diluted on mega, not
absent.

bp40c30's burst12 med 0.283 is the boarding-prevalence wave
(concentrated early imports), not event clustering.

## 4. Pathway mix + funnel rungs

| arm | aboard pathway mix (share of acquisitions) | cs_food inf | voyages w/ cs_food |
|---|---|---|---|
| A0 | fomite 96.1%, caregiver 3.4%, emesis_aerosol 0.5% | 0 | 0 |
| A1 | fomite 95.6%, caregiver 3.4%, emesis_aerosol 0.5%, common_source_food 0.5% | 643 | 28 (9.7%) |
| A2 | fomite 99.4%, emesis_aerosol 0.5% | 0 | 0 |
| A3 | fomite 99.1%, emesis_aerosol 0.5%, common_source_food 0.4% | 257 | 10 (6.7%) |
| A1 bp40c30 | fomite 95.6%, caregiver 3.7%, emesis_aerosol 0.5%, common_source_food 0.2% | 48 | 1 (2%) |

Funnel (pooled over each arm):

| arm | ill/inf | rep/ill | reports via caregiver | ill→reported |
|---|---|---|---|---|
| A0 | 0.186 | 0.669 | — (pre-mechanisms image) | 0.125 |
| A1 | 0.187 | 0.678 | 0.879 | 0.127 |
| A2 | 0.180 | 0.500 | — | 0.090 |
| A3 | 0.180 | 0.515 | — | 0.093 |
| A1 bp40c30 | 0.173 | 0.723 | 0.923 | 0.125 |

- **ill/inf ≈ 0.18 on every arm and mechanism combination** — the
  CHANNEL-03 first-link gap (symptomatic-course draw 0.17–0.41 on the
  small hulls) reproduces at 7,000-agent scale, hull-invariant and
  mechanism-invariant.
- **rep/ill lifts +0.17–0.21 with the caregiver on** (0.67–0.72 vs
  0.50–0.52) — a bigger second-link lift than the +0.05 CHANNEL-04
  measured on the expedition hull, because on mega the stamp does most
  of the reporting (§1).
- Caregiver share of aboard acquisitions is 3.4–3.7%, well under the
  design's >10% deeper-look trigger — the transmission contribution is
  small; its role is the report channel.
- `common_source_food` dose share of acquisitions: 0.2–0.5% — far
  under the spec's >50% over-delivery alarm, same as FOOD-01's
  1.2–8.9% on the small hulls.

## 5. Food mechanism — census witness (a1 / a3 / a1_bp40c30)

Full census reads on the 488 food-arm zips
(`mega_impact_fleet_readout.py --census`). Telemetry counters are
ground truth everywhere; the `events[]` row set is populated on the
fleet image only — the 20 a1 canary-window zips (seeds 8000–8019,
pre-#893 image) report correct telemetry with `events: []`, so the
arm-mix shares below cover the 268 post-fix zips. Cross-check: a1's
event-row total (25,567) equals the summary `common_source_events`
counter exactly; census telemetry (27,391) additionally covers the
canary zips.

| arm | zips | telemetry events | ev/voy med | arm L/H/D % | takers | servings | zero-dose | max cohort | max per-serving dose | lot-positive |
|---|---|---|---|---|---|---|---|---|---|---|
| a1 | 288 | 27,391 | 95 | 0.4 / 28.9 / 70.7 | 781,637 | 956,863 | 55.5% | 438 | 1.98e6 | 21 (7.3%) |
| a3 | 150 | 14,176 | 97 | 0.3 / 27.5 / 72.2 | 403,274 | 529,194 | 58.6% | 433 | 1.41e6 | 8 (5.3%) |
| a1 bp40c30 | 50 | 7,173 | 146.5 | 0.1 / 35.1 / 64.8 | 204,788 | 267,169 | 60.0% | 429 | 1.35e6 | 1 (2%) |

- **The mechanism fires at mega galley scale**: ~95–146 scheduled
  service windows per voyage (bigger complements → more simultaneous
  shedders), ~28 takers per event — same per-event take-up as the
  cls/spr hulls (25–26), an order of magnitude more events per
  voyage than any small-hull cell.
- **Provisioned-lot rate is on-spec**: 21/288 (7.3%) on a1, inside
  the declared U(0.02,0.15) interval (E≈8.5%); each lot emits ~5
  per-epoch witness rows (104 lot rows / ~19 lot voyages on post-fix
  zips).
- **Realized arm mix is diner-dominant everywhere** (D 65–72%,
  H 27–35%, L <1%) — same ordering as FOOD-01's big hulls,
  consistent with duty-exclusion suppressing symptomatic handlers.
- **Zero-dose share ~56–60%** — matches FOOD-01's ~58%.

## 6. Excursion-voyage split (voyages carrying `common_source_food` infections)

| arm | set | n | rep pax med | rep crew med | max ratio | burst12 med | acquired med | cs_food inf med |
|---|---|---|---|---|---|---|---|---|
| a1 | excursion | 28 | 63.5 | 23 | 0.810 | 0.185 | 517.5 | 18.5 |
| a1 | rest | 260 | 55 | 18 | 0.762 | 0.183 | 487 | 0 |
| a3 | excursion | 10 | 48 | 8 | 0.762 | 0.200 | 488.5 | 31 |
| a3 | rest | 140 | 41 | 11 | 0.508 | 0.185 | 473 | 0 |
| a1 bp40c30 | excursion | 1 | 101 | 40 | 0.687 | 0.249 | 577 | 48 |
| a1 bp40c30 | rest | 49 | 61 | 25 | 0.857 | 0.283 | 514 | 0 |

Excursion voyages carry ~+8 pax / +5 crew median reports on a1 and
are where the food arm's tail extension lives (a3: max 0.762 vs rest
0.508). But on burst12 they are indistinguishable from background —
the signature is diluted at mega scale (§3), not absent.

## 7. Structural trends — cross-campaign assessment of the current model

What the current version of the model does, assembled across
MEGA-IMPACT-01 (this readout, `7e1b54bc`), NORO-FOOD-01 (`8e8ebc79`),
NORO-CHANNEL-03/04 (`d6c51c14`/`1e158d47`), NORO-ONSET-CURVE-01 and
NORO-MEGA-01:

**Measured:**

1. **Ignition and spread are settled at every hull scale.** 100%
   takeoff on all 926 mega voyages (as on all FOOD-01/OUTBREAK cells);
   ~470–580 aboard acquisitions per mega voyage. Acquisition is not
   the limiting layer anywhere.
2. **The funnel's broken rung is the infected→ill draw, and it is
   hull-invariant.** ill/inf 0.17–0.19 on every mega arm reproduces
   CHANNEL-03's symp/inf 0.17–0.41 measured on all nine small-hull
   cells — the same first-link failure at ~70× the agent count. No
   shipped mechanism touches it (caregiver: rep/ill moves, ill/inf
   flat; food: cs_food adds infections at the input end).
3. **The second link is caregiver-shaped, increasingly so with hull
   size.** rep/ill pooled: 0.22 on exp (CHANNEL-04) → 0.67–0.72 on
   mega with the mechanism on, vs 0.50–0.52 off. The discovered-illness
   stamp scales with emesis frequency, which scales with complement —
   the self-report hazard does not.
4. **The food excursion tail exists and converts at every scale**:
   ~9.7% of voyages carry `common_source_food` infections on mega
   (28/288) — the same rate FOOD-01 measured (873/9,000) — but the
   excursion's magnitude is bounded by pan size and service windows,
   not by hull. Consequence: on small hulls the tail posts (+374
   paired postings) and resolves burst12 >0.5 only on the expedition
   hull; on mega the same tail produces the best-ever mega reach
   (0.81 of the crew wire) and zero posting transitions.
5. **Every measured voyage on every hull and mechanism combination is
   a propagated ramp** — burst12 ≤ 0.5 on all ~10,900 voyages now
   read, peak epoch = last epoch on all mega arms. The point-source
   signature is real on the expedition hull only; on mega it is
   structurally diluted even on voyages where the event fired.
6. **The crew wire is the reachable wire.** Every posting recorded to
   date came over the crew channel (OUTBREAK-04, FOOD-01); mega's best
   reach is crew 0.810 vs pax max 0.735 — the pax wire (147) needs
   ~2.6× the median voyage's 56 reports.
7. **Detection is a caregiver artifact.** A2 collapses it 15/150→5/150
   (vs A0 same-window); with caregiver, 10–36% of mega voyages detect
   in the final days. An early-warning layer exists and precedes
   posting — it just never reaches posting.

**Inferred:**

8. The excursion-generator ceiling on mega is **event magnitude, not
   event rate**: provisioned lots fire at the declared ~8.5%/voyage
   rate and convert, but a ≤65-infection event cannot carry a 147/63
   report wire by itself. Closing the last ~19% plausibly needs either
   bigger events (more servings/lot, multi-meal lots) or stacking —
   the best mega voyage (seed 8119) combined an excursion with an
   above-median crew ramp.
9. The three levers are **orthogonal**: prevalence moves the median,
   food moves the tail, caregiver moves the report rate. No single
   one closes the gap; a configuration that posts on mega plausibly
   needs all three plus the first-link fix.
10. Memory quote validated in production: lean peak RSS med ~4.2 GB,
    fleet max 4,355 MB (a1_bp40c30) — under the 6144 MB quote with
    ~29% headroom; the canary-derived quote held at fleet scale.

**Hypothesis:**

11. If the infected→ill draw were lifted into its declared band
    (~0.6–0.8 by the A2 anchor), mega median reports would scale
    ~3–4× (56→~170–220 pax) — enough to post on the median voyage
    without any excursion. The funnel first link is the highest-leverage
    unfixed rung in the model; it is also the one every measured anchor
    (A1 ever-ill, A2 conversion) fails on. Next-stage candidate: the
    symptom-course draw against the NORO-CHANNEL-03 cell set, plus a
    mega excursion-magnitude sweep (`pan_mass`, servings/lot,
    multi-meal lots) as the second axis.

## Fleet ledger

- Arrays (all `picard-campaign-queue`, jobdef `picard-noro-mega-impact-01:6`):
  a1 `3dd8057e` (268 cells — canary seeds 8000–8019 already on record),
  a2 `551bb8b7` (150), a3 `a280586c` (150), a1_bp40c30 `2a1f11f7` (50).
  618/618 SUCCEEDED, zero failures, ~4.5 h Spot wall.
- Zips read: 288 a0 + 288 a1 + 150 a2 + 150 a3 + 50 bp40c30 = 926
  (`campaign/noro_mega_01/fl_mega_12d_scr` bp25c7-filtered +
  `campaign/fl_mega_impact_*`); ranged `summary.json` +
  `rss_samples.json` reads; census pass over the 488 food-arm zips.
- No engine or constant changes in this stage; nothing fitted to
  anchors. Measured at `7e1b54bc` (fleet) / `1e158d47` (A0 baseline).
