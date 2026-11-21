# FLU-CONTAM-SOLVER-01 — Campaign Ledger

> **Design:** `campaigns/flu/contam_solver_01/DESIGN.md`
> **Branch / Commit:** `d200817b` era (pre-canary)

## Status

- **Roster:** 7 commissioned current cruise platforms (`greg_mortimer`,
  `expedition_cruise_450`, `classic_cruise_1900`, `spirit_cruise_3000`,
  `diamond_princess`, `explorer_seas_06`, `mega_cruise_5000`). Historic naval
  vessels excluded. Uncommissioned directories `expedition_cruise_300` and
  `messy_cruise_500` (no `contam/` bundle, no `voyage_config.json`) excluded.
- **Local smoke (passed, all 7 hulls, both solvers):**
  - Full 288-epoch pair on `expedition_cruise_450` (seed 8105): `native` (`ContamTransportEngine`) 3 onboard infections, 120.10 s wall; `contamx` (`ContamXTransportEngine`, pinned SHA-256 `d14dc802...`) 2 onboard infections, 103.09 s wall, 0.01 s ContamX child CPU.
  - 24-epoch paired smokes on the other 6 hulls (seed 8105): all 6 resolved cleanly to `ContamTransportEngine` / `ContamXTransportEngine` with zero fallbacks. `diamond_princess` showed an early `hvac_airborne` difference (14 vs 3 onboard infections, 1893.0 vs 111.9 `hvac_airborne` particles in 24 epochs); `mega_cruise_5000` took ~196 s for 24 epochs (~39 min projected for 288 epochs on 1 vCPU).
  - Generic Batch entrypoint check (`deploy/aws/campaign_entrypoint.py --local`) passed on `exp450_contamx`.
- **Preflight:** building ECR image and launching 20-seed `expedition_cruise_450` paired canary (`exp450_native` + `exp450_contamx`).
