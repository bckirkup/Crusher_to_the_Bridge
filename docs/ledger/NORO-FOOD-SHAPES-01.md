# NORO-FOOD-SHAPES-01
**Date:** 2026-10-12
**Commit:** #993
**Pathogens:** norwalk_gi
**Status:** measured

Frozen evaluation design — the next measurement stage on the
SCORE-01/ENTRAIN-01 frame, crossing the three axes the measured
baselines point at, all config-expressible on the current engine:

- **Implicated titre denominator** (`titre_draw_mode`, #990): shipped
  `two_mode` mints every provisioned_lot titre — object mints and v1
  `independent` lot events alike — from the implicated census band
  logU(1.5e2, 5e3); `"background"` restores the single-mode draw
  verbatim (same uniform, same stream position) as the labelled
  pre-change baseline and the bit-identity bridge to the `dbbd5395`
  grid.
- **Cadence dose shape** (#991): `lot_state_redraw: "per_window"`
  re-mints titre + take-share per served window off the object's own
  stream partition — resolved through the two-mode site rule, so
  re-mints land inside the implicated band (pinned engine-side by
  #992, tests+ledger only); `lot_extent_mode: "declared"` meters
  `lot_servings` uniformly across a minted `extent_windows` count
  (`fx_wide` (12,24) / `fx_narrow` (2,4) overrides — the ENTRAIN-01
  §4.3 contract arms, landed here because the cadence pairing
  surface must be the `two_mode` image).
- **Mint-rate** (channel absence is measured — provisioned_lot
  objects minted on 2/1,620 unposted object-arm cells at
  `dbbd5395`): `mint`-family arms set `lot_object_probability` to
  (0.02, 0.15), the v1 `lot_event_probability` voyage-gate interval
  re-expressed verbatim on the object grammar — `ind`-frequency
  channel presence, declared not fit.

Arm set (11): `off`/`ind`/`ind_bg`/`ship`/`bg` baselines and bridges;
`mint`/`bg_mint` the {titre}×{mint} factorial; `redraw`/`redraw_mint`
the {cadence}×{mint} factorial and the conjunction cell;
`fx_wide`/`fx_narrow` the iso-dose extent legs. 3 hulls × 1,000
seeds = 33,000 voyages on the SCORE-01 seed lists and fixed
coordinates; mega excluded. Frozen admissibility (D1–D4), mechanism
integrity gates (witness echo, re-mints inside the implicated band,
extent bookkeeping, bit-identity bridges, mint census) and
canary-then-STOP (108 cells on exp) in
`docs/norovirus/noro_food_shapes_01_sweep_design.md`; package
`campaigns/noro/food_shapes_01/` (manifest
`noro_food_shapes_01_manifest.json`, 33 tiers). Carries no numbers;
nothing submitted under this design until the user gates image
build, canary and each wave.

**Measured at `45b2bf18` (wave 1, exp hull, 11,000/11,000 cells, 0
FAILED, census re-parse — no new voyages):**
`docs/norovirus/noro_food_shapes_01_wave1_readout.md`. The mint gate
is the posting-rate control — 82/1,000 mint-family voyages mint a
`provisioned_lot` (8.2%, inside the declared (0.02,0.15) interval) and
~93% post, so posting lands `ind`-like (8.2–8.6%), over the D1 band;
thin arms hold D1 (+0.3–0.6 pp marginal). Titre denominator is the
material margin on the v1 draw path (`ind − ind_bg` +13.8 pp
excursion conversion) but modest on objects (`mint − bg_mint` +4.9 pp);
cadence (`per_window` re-mint) and `declared` extent are measured
nulls on every D-metric. D3 recovered at/above `ind` (mint family
87.8–93.9% excursion conversion, n=82; thin arms n=6, pooled read);
D4 recovered with mint-family postings themselves bursting
(0.70–0.75 vs `ind` 0.538). D2 met on `mint` only (0.0411; `ind`
0.0380). `redraw_mint` is the closest object-grammar reproduction of
`ind` measured (8.6% posting, 93.9% conversion, 0.748 posted burst48,
posted-AR 0.0379 vs `ind` 0.0380). All six §7.4 integrity gates pass;
bridge minted-voyage parity exact (34/34 `ind_bg`, 78/78 `bg`),
non-object voyages bit-identical; no vacuity, no corruption class.
Wave-2/3 decision is the user's.

Tools: `tools/noro_diag/food_shapes_01_{scan,report,bridge}.py` +
`entrain_01_dose_audit.py` re-run on the six dose-relevant arms.

**Measured at `45b2bf18` (final, all 3 hulls — 25,000/25,000 cells,
0 errors; exp carried from wave 1, 14,000 cls+spr census re-parse):**
`docs/norovirus/noro_food_shapes_01_readout.md`. The mint gate is the
signature carrier on every hull: posting at `ind` level
(8.6/4.9/3.1% vs `ind` 8.2/4.8/2.7%), excursion conversion at
`ind`×1.0–1.2, posted voyages burst above rest, posted acquisitions
ride the dose tail. Every exp-calibrated absolute gate compresses with
hull — D1 thin-arm marginals +0.6→+0.2→+0.1 pp, D2 ≥0.04 met only on
exp (`mint` 0.0411; cls `mint` 0.0389 with `ind` itself 0.0352; spr
`ind` tops the table at 0.0310) — and on spr the excursion-vs-rest
burst48 separation is gone even on `ind` (0.257 vs 0.271) while
postings still burst (0.326 vs 0.272). `ind` excursion conversion
re-measures 77.7→50.0→26.3%, the SCORE-01 hull-compression ordering.
Bridges hold on the binding invariant on both new hulls (`off`
bit-identical; all diverged seeds cs-active on both sides — the
declared machinery delta amplified by cs density, not changed). Mint
census is seed-paired identical across cls/spr (84 cells/96 objects
mint-family). All §7.4 gates PASS; no vacuity, no corruption. Verdict:
**exp admissible; cls/spr admissible-with-caveat** — relative
signatures recover on every hull; the absolute bands don't carry.
