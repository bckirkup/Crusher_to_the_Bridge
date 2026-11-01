# QUAR-CONTRAST-01
**Date:** 2026-11-01
**Commit:** `668fe379`
**Pathogens:** sars_cov2_resp
**Status:** measured
**Measured at:** `668fe379`

Re-ran both arms of the settled QUAR-ATTR-V2 pool-transport contrast —
`A0_declared` vs `A2_pool_transport_off` at Θ 1e9 on `diamond_princess_2020`
(`mega_cruise_5000`), seeds 20200205–20200224 — at HEAD under
`hvac.transport_engine: native` (primary) and `contamx` (parity), local
only, via `tools/covid_attribution_arm_smoke.py --num-epochs 0` (the
declared 35-day voyage, matching the settled campaign cells). Engine
identity proven per cell by the payload `transport_engine` block; scorer
`tools/covid_quar_head_contrast.py` applies the design's frozen criterion
verbatim. Readout: `docs/covid/covid_quar_contrast_head_readout.md`;
surface: `docs/covid/covid_quar_contrast_head_surface.csv`.

Measured:

- The −66% pool-transport anchor does NOT survive at HEAD. Frozen
  criterion on 20 seeds: conditional median A0_declared 573.0 →
  A2_pool_transport_off 607.0 = **+5.9%**, band `non_load_bearing_shift`
  (settled at `d62f10d`: 348.5 → 119 = −65.9%, `load_bearing`,
  n = 8 shared takeoffs). Takeoff moved with the surface drift: 19/20 in
  both arms (was 12/20, 9/20); all-seed medians rose 567.5 → 595.0.
- Engine parity: contamx reads the same dead contrast — conditional
  542.0 → 607.0 = +12.0%, `non_load_bearing_shift`; paired-seed median
  delta vs native −3.0 (A0) / 0.0 (A2, 19/20 seeds bit-identical: the
  arm excises the pathway the engines differ on). The collapse is
  solver-clean.
- Route attribution at HEAD: during-quarantine infections ~90% droplet +
  ~9% caregiver; pool route ~0 in both arms. The outbreak regime moved to
  a larger, droplet/caregiver-dominated state in which pool transport
  carries no load. The A2 arm still expresses (not an expressibility
  no-op).

Open (not run): which merge(s) between `d62f10d` and HEAD moved the arm
surfaces — the drift attribution campaign flagged by QUAR-CONTAMX-01.
