# FLU-CONTAM-SOLVER-01 — Paired ContamX vs. Native Influenza Comparison Across Current Cruise Ships

> **Status:** Specced — criteria frozen. Design of record for
> `campaigns/flu/contam_solver_01`. Commit `d200817b` era.

## 1. Question

Across all current commissioned cruise-ship platforms (excluding historic naval
vessels), how much do the NIST ContamX airflow solver (`contamx`) and the
shipped native airflow solver (`native`) differ in:

1. **Influenza outbreak predictions** (ever-infected, onboard-acquired,
   ever-ill, ever-reported, passenger/crew split, organic confinement/escalation);
2. **Characteristic outbreak dynamics** (daily incidence curve, cumulative
   attack trajectory, peak day, peak daily incidence, onset timing, acquisition
   route attribution);
3. **Compute consumption** (in-process Python CPU time, ContamX subprocess CPU
   time, wall time split into init vs. simulation run, peak RSS, and AWS Batch
   billed wall time / vCPU-seconds).

## 2. Eligible Cruise Roster (Historic Naval Vessels Excluded)

No disease model is run on any historic naval vessel. Of the nine cruise
platform directories in `data/platforms/`:

- **Included (7 commissioned cruise platforms with current `contam/` bundles and `voyage_config.json`)**:
  1. `greg_mortimer` (243 agents, 50 zones, 22 HVAC)
  2. `expedition_cruise_450` (450 agents, 47 zones, 22 HVAC)
  3. `classic_cruise_1900` (1,910 agents, 79 zones, 30 HVAC)
  4. `spirit_cruise_3000` (3,000 agents, 115 zones, 45 HVAC)
  5. `diamond_princess` (3,810 agents, 159 zones, 57 HVAC)
  6. `explorer_seas_06` (4,428 agents, 119 zones, 49 HVAC)
  7. `mega_cruise_5000` (7,000 agents, 192 zones, 83 HVAC)
- **Excluded (2 uncommissioned directories lacking both `contam/` and `voyage_config.json`)**:
  - `expedition_cruise_300`
  - `messy_cruise_500`

## 3. Cell Definition (Frozen)

Each cell uses `FLU-OPEN-01`'s open-voyage `influenza_a` specification
(`tools.diag.conditioned_cell.conditioned_spec(..., confinement="organic")`):

- Bundle: `active_profiles`, isolated to `influenza_a` (shipped `k = 6e-4`, no
  constant overrides);
- Index: 2 passengers at epoch 0 via `initiation.explicit_seeds` plus shipped
  boarding prevalence draw;
- Horizon: 288 epochs (12 days);
- Observation / escalation stack: free-running (`confinement="organic"`);
- Paired arm axis: **only** `config_overrides.hvac.transport_engine` varies
  between `native` (`ContamTransportEngine`) and `contamx`
  (`ContamXTransportEngine` solving the hull's committed `contam/platform.prj`
  with the SHA-256-pinned NIST ContamX 3.4.0.3 Linux binary);
- Seeds: paired per hull starting at `8105` (`8105..8124`, 20 seeds per arm in
  the canary and default 7-hull roster).

## 4. Audit Invariants (Fail-Closed)

- **Solver resolution**: every `contamx` cell must resolve
  `type(sim.contam_engine).__name__ == "ContamXTransportEngine"`; every
  `native` cell must resolve `"ContamTransportEngine"`. Silent fallback fails
  the worker.
- **ContamX binary integrity**: fetched S3 binary must match SHA-256
  `d14dc8020bd5e9f95962af52f46b7ce85e2899b63306309d6590cec652274b2b`.
- **Index presence**: every cell must carry `index_cases >= 2`
  (`first_infection_epoch == 0`).
- **Paired seed coverage**: readout pairs cells strictly on `(platform, seed)`.

## 5. Execution & Gating Plan

1. **Local smoke**: verify both `native` and `contamx` resolve and pass all
   invariants across all 7 cruise hulls (short epoch cap for large hulls + full
   288-epoch pair on `expedition_cruise_450`).
2. **AWS Batch canary**: 20 paired seeds (`8105..8124`, 40 jobs total) on
   `expedition_cruise_450` (`exp450_native_canary`, `exp450_contamx_canary`),
   using a pinned ECR image digest built from `deploy/aws/Dockerfile.campaign`.
3. **Stop & report**: read out canary predictions, dynamics, route shifts, and
   wall/CPU/vCPU timing; present per-hull cost/time projections for user
   approval before submitting the remaining 6 cruise hulls.
4. **Edison return**: package per-seed CSV, per-hull summary JSON/CSV, daily
   dynamics CSV, and Batch timing CSV under the campaign S3 prefix for bounded
   retrieval via `campaign-collect`.
