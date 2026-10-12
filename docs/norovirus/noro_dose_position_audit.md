# ENTRAIN-01 dose-position audit + unposted mint census

> **Status:** Measured — all figures below are computed from the already-landed
> `campaign/noro_entrain_01/` zips at engine `dbbd5395`, zero new voyages.
> Two passes: a `summary.json`-only pass over all 27,000 design cells
> (0 errors) fixing the posted/unposted split at the A9 threshold (0.03
> reported-case AR, either cohort — `score_anchors.POSTING_THRESHOLD`), and a
> `growth_census.json.gz` pass over 2,740 voyages: all 310 posted cells plus a
> seeded-stratified unposted sample (150/arm on exp, 60/arm on cls and spr,
> 0 errors). Ordered steps 1–2 of
> [noro_entrain_01_implications.md](noro_entrain_01_implications.md) §4.
> Scan tool: `tools/noro_diag/entrain_01_dose_audit.py`; tables:
> `tools/noro_diag/entrain_01_dose_audit_analysis.py`.

**Dose-unit caveat.** Per the open ledger, every absolute dose figure in the
repository is void pending refit. All dose numbers below are reported only as
*position on the declared Hill* — where the delivered dose sits inside the
`illness_probability` response curve — never as calibrated magnitudes.

## 0. What the Hill consumes, verbatim

The presentation draw is dose-conditional on `acquired_particles` —
the engine's `cumulative_exposure` ledger at the converting epoch, i.e. the
sum of `effective_dose` credited on every susceptible-epoch challenge since
the previous establishment (`engines/transmission_core.py` 6412–6455:
`agent.cumulative_exposure[pathogen_id] = cumulative_dose`, passed into
`_establish(..., cumulative_dose, ...)` which writes `acquired_particles`,
then reset to 0). The Hill
(`engines/natural_history.py` 271–276, `data/pathogens/active_profiles.json`
60–63):

```python
probability = 1.0 - math.pow(
    1.0 + eta_p * inf["acquired_particles"], -gamma_p
)
```

with `eta = 0.508`, `gamma = 0.095`; `age_factor_by_age_band` multiplies the
result by 0.51 on the `0-4`/`5-17`/`child` bands (provenance: the
`age_factor_by_age_band_notes` block — child community cohorts'
symptomatic share ~0.365 over adult challenge-cohort midpoint 0.71,
interval [0.64, 0.78]; unnamed bands ×1.0). Downstream,
`draw_symptom_onset` adds `get_chronic_illness_boost` then multiplies by
`illness_multiplier` (pharma state; 1.0 on these arms), and on `presents`
draws severity renormalized over the four non-asymptomatic states —
so the severity prior **cannot** eat symptomatic share at the presentation
hop (natural_history.py 385–411). Boarding/import hosts bypass the Hill via
`will_present`; the `acquisitions[]` stream contains only challenge-acquired
hosts — the clean Hill cohort.

The census row that feeds this audit: `acquisitions[]` carries
`dose_read` (per-epoch credited dose at conversion — equal to
`effective_dose` on every sampled row) and `effective_dose` (converting
hazard evaluation); the Hill input itself is reconstructed as
`cum = Σ hazards[].effective_dose` per agent over `(prev_acq_epoch,
acq_epoch]`, matching `cumulative_exposure` semantics exactly (hazard rows
are emitted only on susceptible-epoch challenges — residents return early
under noro's closed superinfection).

## 1. Dose-position census — the Hill predicts the realized share

219,468 acquisition rows across the 2,740 censused voyages. `E[p]` is the
mean declared-Hill value over each cell's acquisition dose distribution;
`realized` is the fraction of those acquisitions whose host has
`symptomatic_epochs > 0` (`illness_status == SYMPTOMATIC`, the same axis
`ever_ill` counts).

| cell set | voyages | acq | cum dose med (p10–p90) | E[p] mean | realized |
|---|---|---|---|---|---|
| exp posted | 203 | 6,774 | 107 (6.7–46,179) | 0.353 | **0.400** |
| exp unposted | 1,333 | 24,521 | 27.1 (3.8–176) | 0.228 | **0.190** |
| cls posted | 73 | 11,356 | 75.1 (6.8–25,785) | 0.327 | **0.335** |
| cls unposted | 540 | 65,027 | 35.5 (4.5–223) | 0.243 | **0.214** |
| spr posted | 34 | 8,093 | 64.4 (6.4–18,188) | 0.314 | **0.312** |
| spr unposted | 540 | 103,697 | 35.9 (4.6–228) | 0.244 | **0.218** |

Dose-band check (all cells pooled) — realized tracks E[p] monotonically:

| cum dose band | n | E[p] | realized |
|---|---|---|---|
| <4 | 19,147 | 0.060 | 0.074 |
| 4–7 | 13,173 | 0.118 | 0.125 |
| 7–22 | 48,057 | 0.176 | 0.175 |
| 22–2,900 | 129,572 | 0.299 | 0.258 |
| ≥2,900 | 9,519 | 0.574 | 0.553 |

Host-level per-voyage medians (unique acquired hosts presenting / unique
acquired hosts): unposted 0.182/0.211/0.217 vs median per-voyage E[p]
0.224/0.241/0.243 (exp/cls/spr); posted 0.391/0.320/0.298 vs
0.317/0.316/0.302.

**Verdict (measured):** the delivered-dose distribution *does* predict the
realized presentation — E[Hill(dose)] ≈ realized within ~4 points on the
unposted cohort and within ~5 on posted, and the dose-band ladder tracks
monotonically with no systematic sign flip. The severity prior is
eliminated as a candidate sink (it renormalizes inside presentation).
Realized sits slightly **below** E[p] on unposted cells (−0.03 to −0.04),
the direction of the child-band ×0.51 factor (a few % of passengers are
children) rather than a defect; the residual on posted cells runs the other
way (reinfection marking + chronic-illness boost), consistent with the
declared modifiers.

The fleet's ~0.13–0.17 `ill/infected` funnel sits ~0.06–0.08 below the
acquisition-level E[p] (per-voyage medians: E[p] 0.228/0.243/0.244 vs
funnel ill/inf 0.125/0.164/0.166). Bounded composition, not a mechanism
mismatch: the funnel denominator counts every ever-infected host —
boarding imports (which present at their `will_present` share), children
(drawn at ×0.51), and crew — while the acquisition cohort above is the
clean Hill population.

**Where doses sit on the curve** (landmarks, same η/γ): p=0.05 at dose
1.4; p=0.10 at 4.0; p=0.15 at 8.9; p=0.20 at 18.6; p=0.30 at 82.1;
p=0.50 at 2,901; **p=0.71 (the challenge-cohort reference share) at
~8.98×10⁵**. Median delivered cumulative dose is 27–36 units on unposted
voyages and 64–107 on posted ones — the realized ~0.2 presentation is what
the declared Hill returns for doses at the left end of the curve. The
challenge-cohort share is unreachable at these delivered doses by ~5
orders of magnitude *in the ledger's dose units* — converting "thin" from
a mechanism mystery into a dose-magnitude measurement (the dose scale is
itself withdrawn; position-on-curve only).

## 2. Unposted mint census — under-conversion AND channel absence

Fraction of unposted voyages per hull × arm minting ≥1 object or firing
≥1 event by `source_kind` (n: 150/arm exp, 60/arm cls/spr; `imports` is
`n_imports` from summary — arriving-shedder presence):

| hull/arm | ≥1 object | ≥1 lot obj | ≥1 handler obj | ≥1 diner obj | ≥1 event (any) | lot event | takers | dose>0 | mean objs | mean imports |
|---|---|---|---|---|---|---|---|---|---|---|
| exp off | 0.000 | 0 | 0 | 0 | 0.000 | 0.000 | 0.000 | 0.000 | 0 | 10.7 |
| exp ind | 0.000 | 0 | 0 | 0 | 0.653 | 0.053 | 0.653 | 0.600 | 0 | 10.7 |
| exp ship | 0.687 | 0 | 0.587 | 0.313 | 0.440 | 0.000 | 0.440 | 0.393 | 3.85 | 10.4 |
| exp a_ext | 0.667 | 0 | 0.607 | 0.307 | 0.420 | 0.000 | 0.420 | 0.360 | 3.97 | 10.0 |
| exp a_thin | 0.660 | 0 | 0.553 | 0.320 | 0.413 | 0.000 | 0.413 | 0.360 | 3.61 | 10.1 |
| exp bc40 | 0.833 | 0 | 0.787 | 0.440 | 0.640 | 0.000 | 0.640 | 0.620 | 7.41 | 12.4 |
| exp bc80 | 0.927 | 0 | 0.880 | 0.560 | 0.733 | 0.000 | 0.733 | 0.680 | 10.93 | 16.5 |
| exp bi50 | 0.507 | 0.007 | 0.407 | 0.180 | 0.327 | 0.007 | 0.327 | 0.273 | 2.13 | 9.6 |
| exp bmix | 0.840 | 0 | 0.760 | 0.460 | 0.587 | 0.000 | 0.587 | 0.527 | 6.96 | 13.6 |
| cls off | 0.000 | 0 | 0 | 0 | 0.000 | 0.000 | 0.000 | 0.000 | 0 | 43.9 |
| cls ind | 0.000 | 0 | 0 | 0 | 1.000 | 0.067 | 1.000 | 1.000 | 0 | 44.0 |
| cls ship | 1.000 | 0 | 1.000 | 0.917 | 0.967 | 0.000 | 0.967 | 0.967 | 33.9 | 45.7 |
| cls a_ext | 1.000 | 0 | 1.000 | 0.950 | 1.000 | 0.000 | 1.000 | 1.000 | 32.4 | 43.3 |
| cls a_thin | 1.000 | 0 | 0.983 | 0.933 | 0.983 | 0.000 | 0.983 | 0.950 | 31.6 | 43.4 |
| cls bc40 | 1.000 | 0 | 1.000 | 0.983 | 1.000 | 0.000 | 1.000 | 1.000 | 47.4 | 52.3 |
| cls bc80 | 1.000 | 0.017 | 1.000 | 0.983 | 1.000 | 0.017 | 1.000 | 1.000 | 73.4 | 71.3 |
| cls bi50 | 0.967 | 0 | 0.950 | 0.900 | 0.967 | 0.000 | 0.967 | 0.967 | 19.8 | 41.4 |
| cls bmix | 1.000 | 0 | 1.000 | 0.900 | 1.000 | 0.000 | 1.000 | 0.983 | 43.6 | 59.3 |
| spr off | 0.000 | 0 | 0 | 0 | 0.000 | 0.000 | 0.000 | 0.000 | 0 | 66.5 |
| spr ind | 0.000 | 0 | 0 | 0 | 1.000 | 0.117 | 1.000 | 1.000 | 0 | 67.1 |
| spr ship | 1.000 | 0 | 1.000 | 0.967 | 1.000 | 0.000 | 1.000 | 1.000 | 53.7 | 67.4 |
| spr a_ext | 1.000 | 0 | 1.000 | 0.983 | 1.000 | 0.000 | 1.000 | 1.000 | 53.6 | 67.3 |
| spr a_thin | 1.000 | 0 | 0.967 | 1.000 | 1.000 | 0.000 | 1.000 | 1.000 | 55.7 | 67.4 |
| spr bc40 | 1.000 | 0 | 0.983 | 0.967 | 1.000 | 0.000 | 1.000 | 0.983 | 87.4 | 83.3 |
| spr bc80 | 1.000 | 0 | 0.983 | 1.000 | 1.000 | 0.000 | 1.000 | 1.000 | 118.1 | 111.3 |
| spr bi50 | 1.000 | 0 | 0.983 | 0.967 | 1.000 | 0.000 | 1.000 | 1.000 | 38.0 | 62.9 |
| spr bmix | 1.000 | 0 | 1.000 | 0.967 | 1.000 | 0.000 | 1.000 | 1.000 | 76.3 | 88.2 |

Field semantics, verified on the payload: `ind` is `independent` mode —
its common-source exposures are **window events** (rows in `events[]`,
`source_kind` ∈ {provisioned_lot, ill_handler, ill_diner}) with no
persistent `objects[]` rows; the object arms mint persistent objects
(`objects[]` with `seeded_epoch` set — every sampled object row was
seeded, none emergent).

**Two-factor decomposition (measured):**

- **Object arms never mint the lot channel.** Unposted `provisioned_lot`
  object mints: 2 cells of 1,620 sampled (bi50 exp 0.7%, bc80 cls 1.7%);
  `provisioned_lot` *events*: ≤1.7% of unposted cells on every object arm.
  Meanwhile handler/diner objects mint at 0.51–1.00 (exp) and ~1.00
  (cls/spr), and handler/diner *events* — with takers and credited dose —
  fire on ~0.87–1.00 of unposted cls/spr voyages. **Non-posting on object
  arms is not a no-event problem; the events and the dose are there —
  the lot channel is simply absent.**
- **`ind` mints the lot channel rarely, and it converts.** Unposted `ind`
  cells show ≥1 provisioned_lot event at 0.053/0.067/0.117 (exp/cls/spr);
  posted `ind` cells show one at 0.868/1.000/1.000 (n=68/39/16). Cells
  with ≥1 lot event on `ind`: 133 total; of those, 114 posted —
  **P(posted | ≥1 lot event on `ind`) ≈ 0.88 / 0.91 / 0.70** per hull.
  Overall on `ind`: mint-rate ≈ 4–12% × conversion ≈ 0.7–0.9 ≈ the
  observed posting rates (6.8/3.9/1.6%). The implications doc's §3.1
  pre-check resolves to: **channel presence lives** — object arms do not
  mint lots at `ind` rates (they mint ~none), so the `cs_extent`
  redraw's discriminant is cadence-with-lot-minting, exactly as §2.3
  reframed it.
- Arriving shedders on bc*/bmix are present at roughly arm-labelled rates
  (mean imports 12.4–16.5 exp, 52.3–71.3 cls, 83.3–111.3 spr vs ~10–67 on
  off/ind/ship) — import presence does not discriminate posting on its
  own (unposted bc80 carries the highest import mass and posts at 0.5–3.7%).

## 3. Cross-check arm `ind` — posting rides the dose tail

Same Hill, same arm, split by outcome:

| ind cells | voyages | acq | cum dose med (p25–p75) | E[p] | realized | p>0.5 frac |
|---|---|---|---|---|---|---|
| exp posted | 68 | 2,536 | 537 (37.7–13,145) | 0.400 | 0.423 | 0.372 |
| exp unposted | 149 | 2,786 | 28.2 (10.5–75.3) | 0.236 | 0.195 | 0.036 |
| cls posted | 39 | 6,611 | 96.2 (23.7–1,870) | 0.344 | 0.343 | 0.228 |
| cls unposted | 60 | 7,537 | 35.6 (12.8–94.1) | 0.246 | 0.221 | 0.027 |
| spr posted | 16 | 4,184 | 68.5 (19.9–461) | 0.314 | 0.313 | 0.165 |
| spr unposted | 60 | 11,635 | 37.4 (13.3–101) | 0.250 | 0.224 | 0.035 |

**Measured:** posted `ind` voyages' acquired infections sit far higher on
the Hill — median cumulative dose 2–10× the unposted median and a 5–10×
larger >0.5 tail — with acq-per-voyage also ~2× higher. Posting correlates
with the *dose tail* (concentrated high-dose acquisition, lot-window
sourcing), not merely infection count: unposted `ind` infections pool at
the same ~35-unit position as every other arm's unposted infections.

## 4. What this resolves in the implication tree

1. **Branch 2 sub-branch 1 (dose-position audit) — resolved, measured.**
   Realized ≈ Hill expectation on the acquired cohort (Δ ≤ ~4 pts, sign
   explained by declared modifiers). No presentation-draw defect; the
   severity prior cannot absorb symptomatic share. The residual question
   is dose magnitude: delivered cumulative doses sit at p≈0.2–0.35 while
   the profile's own challenge-cohort regime (~0.71) sits ~5 orders
   higher on the same declared curve.
2. **Branch 1 pre-check (lot-mint census) — resolved, measured.** Object
   arms mint provisioned_lot objects at ~0% (2/1,620 cells) and
   provisioned_lot events at ≤1.7% — not `ind` rates (4–12%). The
   channel-presence story survives; the `cs_extent` redraw remains the
   discriminating arm, now sharpened to cadence-with-lot.
3. **Branch 2 sub-branch 2 (anchor semantics) — sharpened.** If real VSP
   outbreaks deliver challenge-like doses to their cases, the model's
   reported-ill AR is honest about infection but under-dosed — the same
   conclusion as (1) from the anchor side, now with the position-on-curve
   quantified per hull.

Measured/inferred/hypothesis: everything in §1–§3 is measured on the
stated cell sets (n on every number). Inferred: the residual −0.03/−0.04
unposted deficit as child-band factor, and the posted-side surplus as
reinfection marking + chronic boost (directions match the declared
modifiers; not separately identified). Hypothesis (unchanged): that real
outbreaks' delivered doses reach the challenge regime — untestable in
this census.

## 5. Reproduction

```bash
# 27,000-cell summary pass (posted split, funnel fields, imports):
python3 tools/noro_diag/entrain_01_dose_audit.py --member summary \
    --out summary_rows.jsonl --prefix campaign/noro_entrain_01/<tier>/ ...

# 2,740-cell census pass (posted all + seeded unposted sample):
python3 tools/noro_diag/entrain_01_dose_audit.py --member both \
    --out census_rows.jsonl --keys census_keys.txt --workers 16 --resume

# tables:
python3 tools/noro_diag/entrain_01_dose_audit_analysis.py
```

Sample selection: `random.seed(20261011)` over unposted keys,
150/arm on exp and 60/arm on cls/spr; posted cells are all 310 of 27,000
design cells (canary_* prefixes excluded). Fields read: summary —
`cumulative_ever_infected_*`, `cumulative_ever_ill_*`,
`cumulative_reported_cases_*`, complements, `n_imports`, `n_acquired`,
boarding params, `posted` via `score_anchors.POSTING_THRESHOLD` (0.03);
census — `hosts[].symptomatic_epochs`, `hazards[].{epoch,agent_id,
effective_dose}`, `acquisitions[].{epoch,agent_id,gen,dose_read,
effective_dose,dominant_pathway}`, `common_source.{telemetry,events[]
.source_kind,objects[].{source_kind,seeded_epoch}}`.
