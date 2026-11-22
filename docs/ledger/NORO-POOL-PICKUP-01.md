# NORO-POOL-PICKUP-01
**Date:** 2026-11-22
**Commit:** 8c6fae12 (`--contamination-solver` worker knob + campaign spec)
**Pathogens:** norwalk_gi
**Status:** declared

D2′ re-spec after NORO-DOSE-LEDGER-01. The 22-cell mass ledger showed the
ordinary zone pool is a write-only reservoir under the frozen
`contamination_solver: continuous` arm: it deposits (up to 215k GEC pooled)
but delivers ~0.3% of all hand-delivered mass — 99.7% of delivered mass
arrives via emesis patches through the discrete `_deliver_fomite_requests`
per-touch path, which the continuous solver never invokes for ordinary
pool pickup (it integrates `pickup_mass` inside the RK4 solve instead).

The D0 readout therefore reframed the D2′ question from
"does a small `high_touch_area` corner deliver" (it cannot — delivery
itself is the broken stage) to: **which upstream stage is binding —
the solver's pickup mechanics, or the absence of localized
contact/contamination structure for ordinary fomite?**

## Question

On the frozen Paper-1 cells, does per-touch pickup of ordinary zone-pool
mass deliver where the continuous solver's integrated `pickup_mass` does
not — and if it delivers, does that delivery ignite the cold cells?

## Arms

All on `classic_cruise_1900`, seeds 8000–8019 + 8105/8106 (22 cells per
arm), 288 epochs, the same instrumented worker and epoch-mass-ledger
witness as NORO-DOSE-LEDGER-01:

- **A — shipped freeze (baseline):** `continuous`. Already measured in
  NORO-DOSE-LEDGER-01; no new cells.
- **B — discrete solver:** `contamination_solver: discrete`. Ordinary
  pool pickup runs through `_fomite_zone_pickup` →
  `_deliver_fomite_requests` per-touch requests — the same path the
  patch uses. New worker flag `--contamination-solver` writes
  `config_overrides.transmission.contamination_solver`.
- **C — itemized pool:** `fomite_representation: per_surface`
  (`--fomite-representation per_surface`, existing knob). Per-item-class
  pools, which also route through the discrete path — the closest
  existing knob to "patchify" ordinary fomite. Coupled arm: it changes
  representation AND solver together; that coupling is the point, and
  B vs C separates solver from itemization.

## Frozen criteria (written before any cell ran)

Audit invariants — a violation is an instrument defect, not a null
result:

- `len(epoch_mass_ledger) == 288` on every cell.
- The four counter reconciliations within 1e-9 relative (net surface
  gain, delivered to hands, mouth channels, hazard).
- The worker stamps `contamination_solver` / `fomite_representation`
  resolved values into the artifact (same "resolved" convention as
  `fomite_representation_resolved`), so a dropped override is a
  witnessed fact.

Reported, never selected on, per cell and per arm:

- `delivered_to_hands_gec` split by delivery path (discrete `_deliver`
  calls vs solver `pickup_mass` vs patch);
- `delivered/deposited`, `swallowed/carried`, `hazard/credited`
  waterfall ratios;
- Σhazard, secondaries, take-off per cell;
- reservoir standing mass (hand, pool, patch) trajectories.

Selection / decision rules:

- If B or C delivers ordinary-pool mass AND ignites cells that were
  cold under A: the binding defect is the solver's pickup mechanics →
  the repair is per-touch pickup for the ordinary pool under
  `continuous`, sized from the measured ratio.
- If B or C delivers more mass but does not ignite: magnitude of
  delivery is not binding; the missing structure is localized
  contact/contamination → the next proposal is a patch-style
  mechanism for ordinary deposits (a model change, separately
  approved).
- If B ≈ A (per-touch pickup also does not deliver): the deficit is
  upstream of pickup — deposit placement or encounter structure —
  and no pool-side delivery fix will help.

## Spend estimate

44 cells (2 arms × 22) on the existing layered image (rebuild only for
the worker flag); ~45–60 min/cell at 1 vCPU. Canopy: same canary gate —
≥20-seed canary on arm B first, stop and report before the rest.
