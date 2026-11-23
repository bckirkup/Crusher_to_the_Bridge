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
- **Jobdef rev / image digest:** `picard-covid-dp-theta-pilot-01:1` →
  `picard-campaign@sha256:a65b9aae29b1ff221649181dbb2ca920c6e2384391f8223ea80df9cb53e6f308`
  (built at 086ecc84, in-container verified: design + campaign tree +
  `ENGINE_GIT_SHA` present).
- **Canary:** `niid_t1e11_canary` submitted 2026-11-23T01:51Z —
  parent array job `b86ab9d7-16de-4149-aa9d-21c22eb701a0` (20 children),
  S3 prefix `campaign/covid_dp_theta_pilot_01/niid_t1e11_canary/`.
- **Canary readout (measured, 20/20 SUCCEEDED, audits clean):**
  θ=1e11 `replay_niid` 120ep — secondaries/seed: median **39**,
  range **0–1516**, 1 zero-secondary seed (20200217). Cell neither
  saturated nor dead → θ=1e11 bracket-admissible on the canary seeds.
  Heavy seed variance (index-identity lottery). Readout committed:
  `docs/covid/dp_theta_pilot_01_canary_readout.json`. Full array
  STOPPED pending user decision per campaign gate.
