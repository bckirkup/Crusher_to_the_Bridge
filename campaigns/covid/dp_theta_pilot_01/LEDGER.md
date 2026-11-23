# covid_dp_theta_pilot_01 — campaign ledger

Declared 2026-11-22 (ledger `docs/ledger/DP-THETA-PILOT-01.md`, design
doc `docs/covid/covid_dp_theta_pilot_01_design.md`).

- **Matrix:** 240 cells = 2 arms × 24 seeds (20200205–20200228) ×
  θ {1e10, 3.16e10, 1e11, 3.16e11, 1e12}; declared horizon 120 epochs.
- **Blocks:** 11 — `niid_t1e11_canary` (20), `niid_t1e11_rest` (4),
  four niid + five base θ-blocks (24 each).
- **Local smoke:** `scripts/campaign run --block niid_t1e11_canary
  --index 0` at seed 20200205 — `cell.theta` resolved,
  `susceptibility_scale` = 1e11·(α+β)/α = 3.2322e13, platform
  `diamond_princess`, `close_zones_fired` false, attack_rate 0.331
  (non-degenerate, secondaries compounding).
- **Jobdef rev / image digest:** pending first submit.
- **Canary:** `niid_t1e11_canary` — pending.
