# NORO-EXPOCAP-EXPLORER-01
**Date:** 2026-11-21
**Commit:** 70e833b6
**Pathogens:** all
**Status:** measured
**Measured at:** 70e833b6

Resolved-state divergence on `explorer_seas_06` under the Paper-1 frozen
block, found by Edison's freeze review (required correction 2) and corrected
for the exposure cap only. Initialize-only resolution; no epoch was stepped
and no epidemiological number is reported or moved here.

## What was measured

The frozen block of `docs/norovirus/paper1_freeze_design_contract_2026_11_20.md`
loaded through `scripts/paper1_freeze_block_check.py` on the five reference
hulls, state read after `ShipSimulation.initialize()`.

| Hull | Cap active at af0640d4 | Cap active at 70e833b6 | RhythmLayer attached (both) |
|---|---|---|---|
| `expedition_cruise_450` | True | True | yes |
| `classic_cruise_1900` | True | True | yes |
| `spirit_cruise_3000` | True | True | yes |
| `mega_cruise_5000` | True | True | yes |
| `explorer_seas_06` | **False** | True | **no** |

`include_fixed_rings` resolved False on all five hulls at both commits.

## Cause

EXPO-CAP-01's platform gate was `platform_has_rhythm_catalog`: membership in
a `platforms` list of `data/rhythm/event_catalogs.json`. Explorer is in no
list, so `transmission.exposure_cap.enabled: true` resolved inactive there.

## Correction (70e833b6)

The same membership also attaches a class's SHIP-RHYTHM-02 day program and
venue map. A catalog row for Explorer would therefore have imported another
ship's schedule. The cap instead has its own scope,
`platform_in_exposure_cap_scope`: the catalogued classes plus
`explorer_seas_06` by platform id. The cap reads no catalog data (its budget
is the contact-architecture rate), so eligibility was its only dependency.
The rhythm catalog is unchanged. The checker now resolves the cap's effective
state on every reference hull and fails on any divergence from the request.

## Consequences

- Every `explorer_seas_06` run made before 70e833b6 with the cap requested on
  ran with the cap inactive. Such a run is a cap-off measurement and is not
  comparable with an archetype run under the same block. No Explorer
  epidemiological figure is recorded in the norovirus open ledger.
- `transmission.exposure_cap.enabled: false` remains the labelled baseline on
  Explorer and reproduces the pre-change state.

## Still open

Explorer runs without the SHIP-RHYTHM-02 layer while the four archetypes run
with it, and the frozen block carries no `rhythm` key. This is a second
same-block, different-mechanism divergence. It is not corrected here:
attaching a catalogued program to Explorer is the schedule import the review
ruled out, and the alternatives (a transcribed 2006 Explorer program, pinning
`rhythm.enabled: false` on all five hulls, or labelling Explorer a deferred
exception) are design choices for the freeze contract.
