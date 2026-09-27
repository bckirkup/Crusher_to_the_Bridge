# NORO-DOSE-REFIT-01

**Date:** 2026-09-27
**Commit:** 4a619493
**Pathogens:** norwalk_gi
**Status:** measured

## What this does

`environmental_faecal_release_log10_g_per_epoch` (shipped as
`dose_adjustment`) was void: last fitted against a contact layer removed by
#351-#353, and measured inert on shipped modes (register row, audit §2a —
the plateau edge is 12). This entry re-derives the constant as the physical
quantity the key asserts, −log10 grams of stool-equivalent released to the
environment per ill host-day, from the deposit/pickup chain on the post-#724
engine, and records the emesis-ignition-conditioned establishment readout
the refit produces. Anchor agreement is the check, not the gradient: no
value inside the derivation was selected to move an anchor.

## Derivation (basis)

On the post-#724 engine at shipped modes, the deposit chain that carries
non-emesis mass is the hand route: a host defecating this epoch recontaminates
its hand iff the per-event draw `stool_events_per_day × propensity` fires,
and `_replenish_hand` resets the load to `get_pathogen_hand_target` =
`10^(3.86 + curve[t] − 11)` GEC. Expressed in the stool mass that produced
it, that load is `10^−7.14` g — **titre-independent**: the shedding curve
appears in both the GEC load and the GEC-per-gram conversion and cancels.
So the released mass per ill host-day is

```
release_g = propensity × stool_events_per_day × 10^−7.14
```

composed over the 15-day shedding window with the profile's rate split
(diarrhoeal 5.63/d during the ~2.54-day emetic/acute window, baseline 1.0/d
otherwise, giving a window-mean 1.785 events/day) and the Liu-2013
Beta(0.911, 3.489) carriage propensity (mean 0.207):

* central (window mean): **2.68e-8 g → `dose_adjustment` = 7.57**
* interval, propensity 5–95%: **[7.14, 8.86]**
* reading on acute days only: 7.07; on non-acute days: 7.82

Computation: `tools/noro_diag/dose_release_composition.py` (constants
imported from `engines/infection_dynamics_bridge.py` and
`engines/transmission_core.py`, rates from `data/pathogens/norwalk_only.json`).

The emesis chain is **not** folded in: emesis mass is emitted by
`_emit_emesis` under its own Kirby titre × volume draw (1.6e5–8.0e5 GEC/mL ×
50–800 mL, ~5.0e7 GEC/episode, ~1.4e8 GEC ≈ 1.4e-3 g stool-equivalent per
vomiting illness) and never reads the constant; adding it would double-count
the bolus. The constant therefore names only the hand-route release — and
is recorded as such in the provenance register.

## Why the shipped 4.0 could not stay

4.0 asserts ~10^4 g (~10 kg) of stool-equivalent released per ill host-day —
an artifact-era figure that survived only because no shipped consumer reads
it. The refit adopts **7.57** in `norwalk_only.json` and
`active_profiles.json`.

## Campaign instrument

`tools/noro_diag/per_host_dose_challenge.py --manifest/--tier/--index` runs
each spec of
`picard_framework/runs/mega_cruise_campaign/noro_dose_refit_01_manifest.json`
verbatim (boarding rung `reportable`, `syndromic_comp65`, `dwell_weighted`,
flush aerosol 0.0, `cabin_compartment`, pool `airflow`) under read-only
wrappers that record, per voyage:

* per-host emesis schedule and emit records (`vomiting_axis`, `censored`,
  titre, `emitted_episodes`, `patch_mass_gec`), joined to the import census;
* deposit callsite and venue-class totals, sanitary-delivered mass, and the
  infected census summed to ill host-days;
* `summary.json` in the campaign layout (parameters, summary record block,
  `derived` computed by the campaign's own `compute_derived_metrics`), so
  `score_anchors` scores the probe output unmodified.

`dose_adjustment` does not reach a dose-bearing consumer on these cells
(hand target, emesis emitter and fomite pickup all run on measured
constants; droplet/environmental-reservoir consumers are off or absent),
so the refit value is asserted, and the campaign measures the chain it
asserts.

## Canary: AWS Batch `picard-dose-refit-20260927-030237`

* job `c10796e0-dd9f-46f6-b7a6-98f8c16e62a3`, queue `picard-campaign-queue`,
  jobdef `picard-dose-refit:1`, image
  `picard-boundary-analysis:dose-refit-v1`
  (`sha256:ac1466737c1df296bdb543759499d530d0154d7a3e5a78265206da1789ee9cb0`)
* 120 array children: `fl_spr_12d` (spirit_cruise_3000, n=3000, 288 epochs)
  and `fl_mega_12d` (mega_cruise_5000, n=7000, 288 epochs), contiguous seeds
  **8105–8164** each — a block powered for the ignition rate, not the
  conversion rate (per-import P(ignite) ≈ 4.7% ⇒ per-voyage ≈ 45% spirit,
  ≈ 75% mega).
* results: `s3://crusherbucket-994254241749-us-east-1-an/campaign/noro_dose_refit_01/<tier>/<run_id>.zip`,
  each zip = `summary.json` + `refit.json`.
* readout: `tools/noro_diag/dose_refit_readout.py` (ignition chain,
  conditioned establishment, release composition) + `score_anchors`
  (A1/A2/A5/A8/A9, era `pre`).

## Canary readout (measured)

**Measured at:** `4a619493` (image `dose-refit-v1`, digest
`sha256:ac1466737c1df296bdb543759499d530d0154d7a3e5a78265206da1789ee9cb0`;
`ENGINE_GIT_SHA` unstamped in-image — zips report `unknown`), seeds
8105–8164 per cell, `dose_adjustment` 7.57 everywhere.

### Ignition chain

| cell | voyages | imports | P(axis\|import) | P(emits\|import) | ignited |
|---|---:|---:|---:|---:|---:|
| fl_spr_12d | 60 | 418 (6.97/voy) | 0.124 [0.096, 0.160] | 0.067 [0.047, 0.095] | **22/60 = 0.367** [0.256, 0.493] |
| fl_mega_12d | 60 | 981 (16.35/voy) | 0.111 [0.093, 0.132] | 0.062 [0.049, 0.079] | **42/60 = 0.700** [0.575, 0.801] |

The P(index vomits \| index ill) term the brief asks for is measured as
two separable gates: the vomiting-axis draw (0.11–0.12 per import, below
the symptomatic-stream share because `stationary_detectable` ages most
imports past the acute vomiting window) and the in-window emit draw
(~0.54 of axis hosts actually emit before censoring).

### Establishment conditioned on ignition

Two establishment labels are reported because they answer different
questions:

| cell | peak ≥10, ignited | peak ≥10, cold | VSP take-off (`outbreak_occurred`) | secondaries ign / cold |
|---|---|---|---|---|
| fl_spr_12d | **9/22 = 0.41** | 2/38 (both at exactly 10) | 0/60 | 19 / 5 |
| fl_mega_12d | 41/42 (saturated — 16 imports/voy exceed the label alone) | 18/18 | 0/60 | 14 / 1 |

On spirit the conditioning is discriminating: ignition moves the
peak-prevalence distribution from a cold ceiling of ~10 to 5–13 with the
mass above the gate. On mega the label saturates under import flow and is
not informative. Under the strict VSP label (trigger fires while
incidence accelerates) no voyage in either cell posts — 0/120. This
reproduces NORO-REBASE-01's post-724 baseline at a higher seed count and
with the mechanism attached: initiation fires and the emesis patch
converts (~0.9 secondaries per ignited spirit voyage; fewer on mega's
more dilute hull), but growth never compounds past ~13 concurrent. The
deposit path is exercised and transmitting — the growth collapse sits
downstream of the emesis footprint localisation (#604), which
NORO-DEPOSIT-ATTR-01 already declared correct.

### Release composition (deposit side of the asserted constant)

| cell | `_shedder_surface_deposits` | `_sanitary_venue_deposits` | sanitary-delivered | ill host-days | deposit GEC/ill-day | −log10 g-equiv |
|---|---:|---:|---:|---:|---:|---:|
| fl_spr_12d | 1.71e6 | 1.44e4 | — | 4022.7 | **428** | 8.37 |
| fl_mega_12d | 4.18e6 | 1.01e4 | — | 8579.7 | **488** | 8.31 |

(g-equiv at the code's own stool conversion, 10^11 GEC/g.) The delivered
deposit per ill host-day lands inside the composed interval
**[7.14, 8.86]**, toward the low-propensity edge — the expected
direction, since the constant names the hand-route release while the
callsite measures what fractional touch transfers then delivered to
surfaces. Emesis mass is separate: 1.14e9 GEC patch + 2.8e5 GEC aerosol
on spirit (22 ignited voyages, 36 emitting hosts), 7.5e8 + 2.9e5 on
mega (42 ignited, 66 emitting hosts) — the bolus, not the constant.

### Anchor table (score_anchors, era `pre`)

| cell | takeoff | A1 (0.10–0.22) | inf AR pax | A2 (0.59–0.81) | A4 | A5 (2.5–4.5) | A8 pax/crew | A9 | verdict |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---|
| fl_spr_12d | 11/60 | 0.0010 | 0.0038 | 0.263 | 0.0005 | 0.68 | 2.35 / 2.75 | 0.0000 | FAIL A1,A2,A4,A5,A8,A9 |
| fl_mega_12d | 59/60 | 0.0004 | 0.0024 | 0.167 | 0.0002 | 0.00 | 1.25 / 1.79 | 0.0000 | FAIL A1,A2,A4,A5,A8,A9 |

Same verdict pattern as NORO-REBASE-01's post-724 spirit cell at the old
dose — expected: the constant is inert, so the anchors stand as the
*check* that the refit did not move the transmission surface. They are
not passed and were not tuned toward.

### Readout tooling caveats (recorded)

* Canary zips predate two probe fixes and were stamped at aggregation:
  `natural_history_clock` = `hours` (the manifest-declared value, which
  is the clock the engine ran) added to each `summary.json`; the six
  per-role rate fields rewritten as `count / emitted complement` at full
  precision because score_anchors' complement recovery rounds 6dp rates
  to an off-by-one complement on low-count runs. Both fixes are in the
  probe (`e6ad46e9`) so later campaigns emit them directly; no measured
  quantity was altered by the stamps.
* `dose_refit_readout.py` aggregates `refit.json` members; per-run zips
  live at
  `s3://crusherbucket-994254241749-us-east-1-an/campaign/noro_dose_refit_01/<tier>/<run_id>.zip`.

## Un-voiding

The `dose_adjustment` figure itself is replaced: **7.57, interval
[7.14, 8.86]**, basis "chain-composed deposit mass per ill host-day
(`dose_release_composition.py`), measured against the canary deposit
callsite accounting". Everything else under the open ledger's "every dose
figure is void" stamp (attack rates, route shares, ladder tables measured
pre-refit) stays void; the canary table above is its post-refit reading on
the two declared cells only.
