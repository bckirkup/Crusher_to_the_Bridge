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
- **Fit blocks run (Benjamin's decision: 52 cells, four θ below 1e9
  skipped):** `niid_t1e9_rest` `d6d64ab8-1665-4f44-a384-4f26afbb101f`
  (jobdef `:2`), `niid_t3e9` `68cf99ae-0553-41fa-9b70-85b30f1a3b13`
  (`:3`), `niid_t1e10` `4c2e5d23-8b90-4f2e-bf6c-43687c01e4fc` (`:4`);
  52/52 succeeded, same image digest. Readout
  `docs/covid/dp_theta_fit_01_array_readout.json`.
- **Not run:** `niid_t1e7`, `niid_t3e7`, `niid_t1e8`, `niid_t3e8`.
