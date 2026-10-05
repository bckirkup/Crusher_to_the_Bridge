# NORO-FOOD-02 sweep design — `lot_event_probability` ladder

> **Status:** frozen — grid, pairing, target band, and exclusion
> rationale are frozen before any array submits.

Config-only rescale of the declared provisioned-lot interval — same
image, same seeds, same hull family as NORO-FOOD-01 (PR #894, readout
`docs/norovirus/noro_food_01_readout.md`, ledger
`docs/ledger/NORO-FOOD-01.md`, mechanism design
`docs/food_common_source_01_design.md`). FOOD-01 measured the free top
rung at the shipped interval U[0.02, 0.15] (E ≈ 8.5%): 873/9,000
excursion voyages flat across cells, ~43% of excursion voyages
converting to a posting, posted share lifted 0–0.8% → 1.8–6.9% vs the
real cruise anchor ~0.3–0.5%. The interval is declared, not fit — this
sweep asks where the real anchor sits on its ladder.

## Sweep axis and semantics

Axis: `transmission.common_source.lot_event_probability`, carried as a
fleet-wide `[lo, hi]` override via tier `config_overrides`
(`engines/transmission_core.py` `_COMMON_SOURCE_SPECS`; resolution order
profile block > `transmission.common_source.<name>` > frozen default,
`_cs_spec_range`). Semantics verified at `8e8ebc79`: `_cs_plan_lots`
makes ONE Bernoulli draw per voyage per armed pathogen on the drawn
per-voyage rate → at most one scheduled lot per voyage →
P(excursion voyage) ≈ interval mean E = (lo+hi)/2.

## Grid — four rungs, ~7.5× lo:hi ratio preserved

| rung | interval | E (mean) | predicted posting gain* |
|---|---|---|---|
| L1 | [0.001, 0.0075] | ~0.43% | ≈ +0.2 pp |
| L2 | [0.002, 0.015]  | ~0.85% | ≈ +0.4 pp |
| L3 | [0.004, 0.030]  | ~1.7%  | ≈ +0.7 pp |
| L4 | [0.010, 0.075]  | ~4.25% | ≈ +1.8 pp |
| FOOD-01 (free top rung) | [0.02, 0.15] | ~8.5% | +1.8..+6.1 pp measured |

\* predicted ≈ linear in E through the measured ~43%
excursion→posting conversion on the same cells.

The real anchor (~0.3–0.5% posted share) should fall near L1–L2. If no
rung lands total posted share in the band, that is itself the finding.

## Cells — mid diagonal only

3 hulls × 4 rungs = 12 tier-cells, `*_12d_scr` at the mid boarding
diagonal point bp32.5c18.5, nsf29, 288 epochs, dose_adjustment 7.57,
surveillance `syndromic_comp65`, rung `shipped` — identical to the
FOOD-01 mid column. 1,000 seeds per cell = 12,000 voyages.

Pairing: SAME seeds as FOOD-01 — exp 8000–8999, cls+spr 8105–9104 — so
every voyage pairs seed-for-seed with the FOOD-01 free rung and with the
NORO-OUTBREAK-02/03/04 baselines (the posting gain/loss contrast).

Manifest tiers are named per rung (`fl_exp_12d_scr_l1` …
`fl_spr_12d_scr_l4`); each carries
`config_overrides.transmission.common_source.lot_event_probability:
[lo, hi]` plus the unchanged FOOD-01 transmission/hvac block. The
jobdef's `-c` bootstrap additionally patches
`campaign_runner._TRANSMISSION_PARAM_MAP` to record `common_source` in
`parameters` — observation-only — so each run zip echoes the interval
it ran at (the canary gate reads it).

## Exclusions (settled, do not re-derive)

- **`food_safety_posture` stays 1.0 and `lot_posture_coupling` stays
  false.** The posture scalar multiplies ONLY the handler/diner
  per-window rates (`transmission_core.py` L11787/L11818); the lot arm
  is deliberately decoupled — ship food-safety practice cannot move
  supplier-side lot contamination. A posture sweep cannot reach the
  posting overshoot; it is not a lever on this axis.
- **Handler/diner arms NOT swept** — they stay at the declared
  U[0.005, 0.10] / U[0.001, 0.05]; their unswept contribution IS the
  residual-floor measurement at L1.
- **bp diagonal collapsed to mid** — FOOD-01 measured excursion share
  and posting gain flat across bp25c7/bp32.5c18.5/bp40c30 (9.4–10.3%,
  1.8–6.9% posted); the diagonal adds nothing to a dose-response on E.
- No ren cells, no 7d tiers, no mega cells, no engine/constant changes,
  no platform wiring changes.

## AWS wiring (frozen)

- Image: `994254241749.dkr.ecr.us-east-1.amazonaws.com/picard-campaign
  @sha256:75931b1d015986db46b9687bc55ecad254cde712373c78817dc14e11a54e
  23c2` — the FOOD-01 overlay (`campaign-8e8ebc79-food01`); engine
  unchanged, no rebuild.
- Jobdef `picard-noro-food-02` rev1 = clone of `picard-noro-food-01:2`
  (describe → strip read-only fields → register), same digest, with the
  NORO-FOOD-02 manifest embedded in the `-c` bootstrap (the image
  predates the manifest file) exactly as FOOD-01 rev1 did, plus the
  param-map patch above.
- Output prefix `s3://crusherbucket-994254241749-us-east-1-an/
  campaign/noro_food_02/` — confirmed free; nothing writes into
  existing `campaign/*` prefixes.
- Spot queue `picard-campaign-queue`; On-Demand
  `picard-analysis-queue` is the user-approved escalation if Spot parks
  arrays >1 h.

## Campaign gate (canary first)

20 seeds at `fl_exp_12d_scr_l2` ([0.002, 0.015], indices 0–19 → seeds
8000–8019). MUST verify:

- zips land under `campaign/noro_food_02/fl_exp_12d_scr_l2/`;
- `common_source` telemetry fields present in the census member;
- `parameters.common_source.lot_event_probability` echoes
  `[0.002, 0.015]` in run summaries (the param-map patch working);
- handler/diner arms still firing (zero *lot* events in 20 seeds is
  EXPECTED at E ≈ 0.85% — P(0 lots in 20 draws) ≈ 72% — the gate is the
  override echo + handler/diner activity, not lot firing);
- posted/vsp fields sane.

If clean → all 12 arrays without re-asking (scope pre-approved). If
anomalous → stop and report.

## Report immediately if

- excursion share does not shrink roughly linearly with E across rungs
  (nonlinearity = mechanism surprise);
- any rung's excursion share ≫ its E (lot misfire);
- >5% child failures on a cell;
- Spot parks arrays >1 h;
- telemetry shows draws at the shipped interval (override not applied).

## Readout plan (the deliverable)

1. Dose-response per hull: excursion-voyage share vs E at the 4 rungs +
   FOOD-01's 8.5% (5 points); events/takers/zero-dose/cs_food-share
   telemetry per rung (`tools/noro_diag/common_source_readout.py` on
   the parent prefix `campaign/noro_food_02/`).
2. Posting-rate paired table per rung × hull vs the matching
   OUTBREAK-02/03/04 baseline cell — Wilson 95% CIs, paired-seed
   gained/lost (`tools/noro_diag/outbreak_anchor_readout.py
   --import-root`): which rung(s) land total posted share in the
   ~0.3–0.5% real band.
3. Onset re-check on the rung nearest the anchor: do excursion voyages
   still carry the burst12 signature at anchor-consistent rates?
   (`tools/noro_diag/onset_curve_readout.py`; exp resolves it, cls/spr
   mostly cannot — report what each hull shows.)
4. Residual floor at L1: excursion/posting remaining from the unswept
   handler/diner arms alone.

## Non-goals

No `food_safety_posture` sweep, no `lot_posture_coupling`, no
handler/diner arm rescale, no ren cells, no 7d tiers, no mega, no
engine/constant changes, no platform wiring changes, no UI testing.
Observe and report only.
