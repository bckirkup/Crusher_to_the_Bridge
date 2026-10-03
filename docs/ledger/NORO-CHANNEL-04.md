# NORO-CHANNEL-04
**Date:** 2026-10-03
**Commit:** #856
**Pathogens:** norwalk_gi
**Status:** declared

## Question

NORO-CAREGIVER-01 (merged `a78c942e`, default-ON) ships the
party-mediated caregiver mechanism aimed at both broken funnel links
measured by NORO-CHANNEL-03 (`d6c51c14`): infected -> symptomatic-course
0.170-0.413 vs 0.6, eligible -> reported 0.168-0.321 vs 0.4. Does the
CHANNEL-03 rung chain move on the identical 9 cells x 20 seeds, and is
any lift channel-attributed (discovery stamp vs cleanup dose)?

## Instrument

`tools/noro_diag/observation_channel_funnel.py` extended read-only:
`caregiver_report_ids`/`caregiver_report_due_epoch` capture, the
reported rung's `via_caregiver` split, per-infection dominant route for
the caregiver share of aboard transmissions, and the engine's
`caregiver_telemetry` counters. `tools/noro_diag/channel_03_readout.py`
adds `viaCG`/`CGtx` columns and evaluates the frozen triggers.
Identical spec source (`noro_outbreak_01_manifest.json`), cells and
seeds as CHANNEL-03; fresh prefix `campaign/noro_channel_04/` pairs
each new dump against the `campaign/noro_channel_03/` baseline at the
same spec+seed. Design: `docs/norovirus/noro_channel_04_design.md`.

## Admissibility (frozen)

- caregiver share of aboard transmissions > 10% on any pooled cell ->
  over-delivery, report immediately;
- any caregiver report on a non-emetic course -> stamp-integrity
  defect, report immediately;
- vomiting-course voyages with zero caregiver+steward responses ->
  report the count per cell;
- rep/elig > ~0.6 anywhere -> over-reporting (carried);
- infected -> symptomatic-course near zero at takeoff -> contradicts
  the shipped never_symptomatic reading (carried).

## Scope

- Reads the shipped mechanism; fits nothing. No mode:off arm — the
  d6c51c14 dumps are the labelled baseline.
- The funnel-vs-map `took_off` join is reported as a mechanism-effect
  witness (divergence = takeoff change), no longer a void condition.
- Anchor re-score (OUTBREAK-01-scale) is the following decision, not
  this campaign.
