# QUAR-CONTAMX-01
**Date:** 2026-10-29
**Commit:** b77e42d0
**Pathogens:** sars_cov2_resp
**Status:** measured
**Measured at:** b77e42d0

Re-ran one settled transport-sensitive QUAR-ATTR-V2 cell — `A0_declared` at
Θ 1e9 on `diamond_princess_2020` (`mega_cruise_5000`), the 20 seeds
20200205–20200224 — under `hvac.transport_engine: contamx`, local only, via
`tools/covid_attribution_arm_smoke.py --transport-engine contamx`. Engine
identity proven per cell by the payload `transport_engine` block: all 20
probe cells built `ContamXTransportEngine` (2182 airflow paths); the
4-seed native parity lane built `ContamTransportEngine` (2258).
Runs executed on the working tree at b77e42d0 plus this change's tool
files. Readout: `docs/covid/covid_quar_attr_contamx_probe_readout.md`;
per-seed surface: `docs/covid/covid_quar_attr_contamx_probe_surface.csv`.

Measured:

- **The solver swap does not move the verdict.** On the four seeds run in
  both local lanes (20200205, 20200206, 20200215, 20200220), ContamX and
  native agree within seed noise: median paired delta −5 on
  `infections_during_quarantine`, −2.5 on `infections_total`; identical
  takeoff sets; conditional-median shift −1.35% →
  `non_load_bearing_shift` on the design's 20/50 bands.
- **The settled cell is stale at HEAD, independent of solver.** The
  native parity lane is not byte-identical to the settled
  `covid_quarantine_attribution_v2_surface.csv` rows on any of the four
  parity seeds — the design's own run-invalidation clause. Probe vs
  settled: takeoff probability 0.6 → 0.95 (19/20, with seven settled
  non-takeoff seeds taking off and none lost), all-seed
  during-quarantine median 71.5 → 537.0, shared-takeoff conditional
  median 829.5 → 526.5 (−36.5%, design band: indeterminate). ~573 merges
  sit between `d62f10d` and HEAD; the covid anchor was already recorded
  drifting (CAREGIVER-V1, PROPENSITY-V1).
- The probe lane is deterministic on this box: the ad-hoc and scripted
  contamx re-runs of seed 20200205 both give during-quarantine 562.

Open (not run — attribution is a separate campaign): which merge(s)
moved the A0 surface; whether the −66% pool-transport arm contrast
(A0 vs A2) survives the drift.
