# NORO-CHANNEL-03
**Date:** 2026-10-02
**Commit:** #848
**Pathogens:** norwalk_gi
**Status:** measured
**Measured at:** d6c51c14

## Question

NORO-OUTBREAK-01 (`bc4de6f5`, 12,000 voyages, small hulls) measured the
anchor deficit as *conversion*, not transmission: A1 ever-ill 0.0-2.0%
vs (10%, 22%), A2 ill/infected 6-17% vs (59%, 81%), A4 reported AR ~0 vs
class IQRs, A8 acquisition incidence 2.4-9.5x over reference. Which link
of infection -> illness -> report carries the gap?

## Instrument

`tools/noro_diag/observation_channel_funnel.py` (the CHANNEL-01/02
per-host funnel) run at the NORO-OUTBREAK-01 cells themselves — spec
verbatim from `generate_tier_runs(noro_outbreak_01_manifest.json, tier)`
at matched seeds, so each funnel voyage is the same voyage the anchor
map scored. New observer field: `peak_infected`/`took_off` per run
(campaign `peak_prevalence` semantics) for takeoff conditioning.

Cells: per hull {scr-mid, scr-hi, ren} at 12 d, 20 seeds each —
180 runs (exp 8000-8019, cls/spr 8105-8124). Design:
`docs/norovirus/noro_channel_03_design.md`.

## Scope

- Reads the declared channel (eligibility, reporting hazards, trust
  scaling, severity) under outbreak conditions; fits nothing.
- Takeoff-conditional pooling is declared pre-run.

## Measured

180/180 runs succeeded; zero takeoff join violations against the scored
map voyages. Canonical table:
`docs/norovirus/noro_channel_03_readout.md`. The gap is **shared** —
the symptom-course draw is the first broken link on all 9 cells
(symp/infected 0.170-0.413 vs 0.6) and the report hazard also
under-fires on 8/9 (rep/elig 0.168-0.321 vs 0.4); no severity wall
(elig/symp = 1.000 everywhere).
