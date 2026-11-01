# FLU-CONTAMX-01
**Date:** 2026-11-01
**Commit:** d74365ba
**Pathogens:** influenza_a
**Status:** measured
**Measured at:** d74365ba

Re-ran one settled flu cell — the conditioned `influenza_a` confined
cabinmate cell on `classic_cruise_1900` (`ACTIVE` bundle, 2 explicit seeds
at epoch 0, `confinement: declared` SOP-017 day 1 → end, `k = 6e-4`, 288
epochs) — under `hvac.transport_engine: contamx` with seeds 8105/8106/8112/
8184, plus a native parity lane at the same HEAD, local only, via
`tools/flu_confined_contamx_probe.py --transport-engine <lane>`. Engine
identity proven per cell by the payload `transport_engine` block: all four
probe cells built `ContamXTransportEngine` (666 airflow paths, ~410,834
m³/h); the native lane built `ContamTransportEngine` (705, ~391,683). Runs
executed on the working tree at d74365ba plus this change's tool files.
Readout: `docs/flu/flu_confined_contamx_probe_readout.md`; per-seed surface:
`docs/flu/flu_confined_contamx_probe_surface.csv`.

Measured:

- **The settled confined-SAR cell does not load on the transported pool at
  HEAD.** Summed over all 34 confined slots, the `hvac` channel (the only
  pathway reading the solver-written `zone_pathogen_mass`) totals 0.0076
  copies native / 0.0077 contamx — ~0.0002% of confined dose. The cell
  loads on `plume` (~66%) and the local `pool` (~34%), both
  solver-independent. The withdrawn FLU-DOSE-01 (pre-`1b9d37ca`) had `hvac`
  at ~33% of confined copies — the far-field rework removed the transported
  channel from this verdict rather than breaking it.
- **The verdict does not move under ContamX.** Identical `confined_slots`,
  `confined_secondaries`, and `observed_mate_case_attack_confined` per
  seed; pooled attack 2/34 = 5.88% [Wilson-95 1.6–19.1] in both lanes —
  inside the CABIN-FLOOR-03 on-arm band [4.5%, 14.7%] and consistent with
  the settled FLU-SOCIAL-01 point estimate (6.5%, n=856) under the spec's
  small-n scatter rule. `non_load_bearing_shift`.
- **No settled flu verdict routes through the transported pool:**
  FLU-OPEN-01 attributes `hvac_airborne` ≤1% of onboard-acquired and
  FLU-VIS-01 ≤~1%; flu's airborne dose is droplet (plume + local pool) and
  caregiver. Environmental dosages are similar across solvers (plume +1.9%,
  pool +2.7%, hvac ~equal) — RNG-stream jitter, not a delivery change.
