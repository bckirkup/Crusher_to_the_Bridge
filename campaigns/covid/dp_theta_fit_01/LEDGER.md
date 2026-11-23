# covid_dp_theta_fit_01 — campaign ledger

Declared 2026-11-23 (ledger `docs/ledger/DP-THETA-FIT-01.md`, design
doc `docs/covid/covid_dp_theta_fit_01_design.md`).

- **Matrix:** 168 cells = 1 arm (`replay_niid`) × 24 seeds
  (20200205–20200228) × θ {1e7, 3.16e7, 1e8, 3.16e8, 1e9, 3.16e9,
  1e10}; full declared voyage (840 epochs), no horizon arg.
- **Blocks:** 8 — `niid_t1e9_canary` (20), `niid_t1e9_rest` (4), six
  other θ-blocks (24 each).
- **Jobdef rev / image digest:** `picard-covid-dp-theta-fit-01:1` →
  `picard-campaign@sha256:8891880d99c2b2d533d62af077602873141f201be55bd4a762514b34acf4b954`
  (built at 6e23f0d9).
- **Canary:** `niid_t1e9_canary`, Batch array
  `653e82d7-351e-48c5-8362-dae004d96601`, 20/20 succeeded; readout
  `docs/covid/dp_theta_fit_01_canary_readout.json`.
- **Remaining blocks:** not submitted; gated on Benjamin's decision.
