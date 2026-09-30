# NORO-HAND-STATIONARY-01
**Date:** 2026-09-30
**Commit:** b548056b
**Pathogens:** norwalk_gi
**Status:** declared

`NORO-EXP-FOMITE-RECONCILE-01` filed this entry; `NORO-DOSE-BLOCK-01` named it
"the mechanism study behind" the unexplained 2.7-log10 surface→hand spread.
It is upstream of every fomite dose in the model: every hand→surface deposit
and every hand→mouth dose scales the same per-host-per-epoch hand load.

## Question

What is the hand reservoir's *occupancy* distribution as shipped — how often
is a shedding host's hand carrying norovirus above the Liu rinse LOD — and is
that distribution the intended reading of the mechanism, or a defect
candidate?

## As shipped (measured, settled — do not re-derive)

`_replenish_hand` (`engines/transmission_core.py`) spikes the hand to the Liu
ceiling `10^3.86 × 10^(curve[idx] − 11)` at propensity-thinned defecation
events (per-host `Beta(0.911, 3.489)` thinning of the stool-event rate), then
decays it at `hand_inactivation_rate_per_hour ∈ U(0.61, 1.7)` — the
spike-and-crash pattern `NORO-EXP-FOMITE-RECONCILE-01` measured:
`_stationary_hand_load` underflows (1.6e-217 GEC; 867/960 target-positive
calls underflowed on classic 8105), hand at ceiling ~1% of shedding epochs.
The `−7.14` bridge and the inactivation range stay shipped
(joint-with-curve-peak per register #47). Liu 2013 (tranche 40, PMC3837815)
measured the actual rinse distribution this mechanism should occupy.

## Literature comparison set (tranche 40, settled)

Liu et al. 2013 (PMC3837815), infected-subject hand rinses:

- 18/71 (25.4%) positive at LOD 2.15 log10 copies/hand;
- positive-rinse mean 3.86 log10, per-subject positive means 3.30–4.45 log10;
- per-subject positivity 12/22, 2/8, 2/8, 2/12, 0/12, 0/9 → 2/6 subjects
  never positive, 4/6 positive at least once;
- post-bathroom rinses were LOWER than routine rinses
  (11/89 = 12.4% @ 2.30 mean vs 6/16 = 37.5% @ 3.32 mean, P<0.05) — the
  opposite ordering sign to the engine's defecation-event replenishment.

## Instrument

Read-only census, no RNG consumed by any wrapper. New shared module
`tools/noro_diag/hand_occupancy.py` wraps `_replenish_hand` (per host-epoch
row: pre/post load, target, defecation-event flag, first-seen stationary
init, propensity, inactivation rate, symptomatic flag, confined flag, call
site), `_stool_event_occurs`, `_stationary_hand_load`,
`_hand_carriage_propensity`, `_apply_hand_hygiene` (end-of-epoch post-hygiene
load onto the same row), and `_pathway_fomite` (epoch stamp only). The module
is installed inside the existing `instrumented()` of:

- `tools/noro_diag/growth_chain_census.py` — the `fl_spr_12d` cells (verbatim
  tier spec from `noro_dose_refit_01_manifest.json`);
- `tools/noro_diag/fomite_mass_balance.py` — the `classic_cruise_1900` cells
  (EMESIS-SIZE-01 block spec: shipped bundle, declared complement, no
  override, 288 epochs).

**Draw neutrality (measured before the array):** for one seed per cell, the
instrumented run and an uninstrumented control run of the identical spec
produced byte-identical voyage fingerprints (`timeseries`, `summary`,
`derived`, `cost_accounting`, `trigger_status` via the campaign
`_attach_voyage_blocks`): `verify_draws_classic_cruise_1900.json`
(seed 8000, 24 epochs) and `verify_draws_fl_spr_12d.json` (seed 8105,
overridden smoke shape) under `docs/norovirus/noro_hand_stationary_01/` —
both `PASS`. The instrument consumed no draws on either driver.

**Sampling map (declared, not measured yet):** Liu's rinse is a point-in-time
sample of an infected subject's hand. The model analogue is the *end-of-epoch
realized load* (post-replenish, post-deposit, post-hygiene) on each
shedding-host epoch row — one sample per host-epoch. The "post-defecation"
analogue is the post-replenish load on rows where a stool event fired; the
"routine" analogue is the end-of-epoch load on rows where none did. Both
samplings of the ordering are reported (post-replenish event vs routine;
end-of-epoch event vs routine).

## Cells, frozen before any cell runs

| Hull / cell | Seeds | Agents | Epochs | Cells |
| --- | --- | --- | --- | --- |
| `fl_spr_12d` (spirit_cruise_3000, dose_adjustment 7.57, syndromic_comp65, dwell_weighted, cabin_compartment, pool airflow) | ignited subset: 8105, 8107, 8110, 8112, 8113, 8114, 8115, 8117, 8121, 8123, 8124, 8129, 8132, 8135, 8137, 8148, 8149, 8156, 8158, 8159, 8162, 8163 | 3,000 | 288 | 22 |
| `classic_cruise_1900` (shipped default bundle, declared complement, no override) | 8000–8019 | 1,910 | 288 | 20 |

The `fl_spr_12d` seeds are the NORO-GROWTH-01 ignited subset — voyages whose
import shedded — so the occupancy census covers the hosts the fomite chain
depends on. Output per seed under
`docs/norovirus/noro_hand_stationary_01/<cell>/`, run on AWS Batch
(`campaign/noro_hand_stationary_01/` prefix).

## Criteria, declared before any cell runs

**Admissibility.** A cell is *void* if the run raises, or if it records zero
`norwalk_gi` fomite deliveries (no fomite chain exists whose hand reading
matters). Void cells are reported and excluded, never re-seeded. >4 void
cells of 42 → study NO-GO.

**Draw neutrality.** The instrumented-vs-control fingerprint must be
byte-identical on both verified seeds. Failure → cells void, instrument
fixed, declared criteria re-opened.

**Primary reading — positivity rate.** Let `pos_share` be the share of
shedding host-epoch rows whose end-of-epoch load ≥ 10^2.15 GEC, pooled per
cell. `R = pos_share / 0.254` (Liu 18/71). Verdict `defect_candidate` if
`R > 5` or `R < 0.2` (the prompt's report-immediately trigger: a >5×
mismatch either direction is messaged to the user the moment it is measured).

**Secondary readings (declared thresholds, verdict-active).**

- *Positive-mean:* geometric mean of end-of-epoch loads on positive rows,
  vs Liu's per-subject positive-mean band [3.30, 4.45] log10. Defect-class
  if the pooled mean log10 falls below 2.30 or above 5.45 (band ±1.0 log10).
- *Never-positive share:* share of shedding hosts (≥1 shedding epoch) whose
  hand never exceeds LOD in any shedding epoch, vs Liu's 2/6 = 33%.
  Defect-class if the model's share is ≥80% (Liu's hosts were not
  systematically always-clean: 4/6 rinsed positive at least once) or ≤5%
  (Liu's hosts were not systematically always-contaminated).
- *Ordering sign:* positivity of the post-defecation analogue vs the routine
  analogue within the model, compared to Liu's finding (post-bathroom LOWER
  than routine). The model's event-vs-routine ordering and Liu's are
  reported side by side; a same-sign model ordering is itself evidence the
  replenishment mechanism answers a question the data does not ask — it
  weighs toward `defect_candidate` but does not alone decide the verdict,
  since model routine rows are near-underflow by construction of the same
  mechanism being measured.

**Verdict.** `defect_candidate` iff the primary reading misses, or ≥2 of the
three secondary readings miss. Otherwise `intended_reading`. A primary miss
is reported to the user immediately on measurement, before the readout
finishes.

**If defect-class:** report the three repair options — persistent reservoir
(hand relaxed toward a sustained non-ceiling level), event-windowed (load
carried only inside a post-defecation window), explicit washing (hygiene
events with Liu-informed frequency/efficacy shaping the occupancy) — and
stop. No repair implementation in this entry.
