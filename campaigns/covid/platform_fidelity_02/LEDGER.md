# PLATFORM-FIDELITY-02 campaign ledger

Larger-seed Diamond Princess follow-up to the platform-fidelity study.
Pre-registration: `docs/covid/covid_platform_fidelity_02_prereg.md`; design:
`picard_framework/runs/covid_platform_fidelity_02_dp_design.json`; power
calculation: `campaigns/covid/platform_fidelity_02/power_analysis.py` +
`power_analysis.json`. GM untouched.

## 1. Design (frozen)

- Scenario `diamond_princess_2020`, voyage declared; Θ = 7.9e6,
  infection_age_days 6.8, imports 1, sanitary_visit_mode dwell_weighted.
- Seeds 20200205–20200404 (200/arm), contiguous `seed_base + i` extension of
  the frozen 01b series; CRN pairing proxy vs dedicated on the same seeds.
- Protocols `data/config/protocols_covid_pf_dp_01b.json` (SOP-017-MESSBOX,
  union `exempt_work_zones`, frozen — not retuned).
- Both arms rerun over the full 200-seed series (400 cells) so the campaign is
  self-contained; the first 20 dedicated seeds (20200205–20200224) are the
  canary/replication row against PLATFORM-FIDELITY-01b.
- Power basis: smallest grid n with ≥0.90 power on P(takeoff) and
  both-takeoff paired size at the observed 01b plug-in rates, and ≥0.80 on
  both under halved event rates → **200 seeds/arm**.

## 2. Preflight status

- [x] Power calculation committed and reproducible from the synced S3 cells
      (`power_analysis.py`; S3 prefixes are the PF-01 proxy and PF-01b
      dedicated 20-seed cells).
- [x] Local smoke proving the `platform_id` override + witness contract.
- [x] `scripts/campaign describe covid/platform_fidelity_02` (arrays 20 +
      180 + 200 = 400) and canary `--dry-run` render; count == design file.
- [x] Image built and pinned by digest.
- [x] Canary `dp_t7e6_dedicated_canary` (20 cells) submitted and read out —
      STOP per the gate; owner decides the remaining 380 cells.

## 3. Local smoke (2026-11-08, dev venv)

- Dedicated `dedicated_diamond_princess` seed 20200205, Θ 7.9e6, full
  288-epoch voyage: PASS.
- `platform_fidelity` echo: resolved `diamond_princess` vs scenario-declared
  `mega_cruise_5000`; protocols `data/config/protocols_covid_pf_dp_01b.json`;
  fired `SOP-017-MESSBOX`; no `close_zones`; 8 input hashes echoed.
- Witness audit clean (`platform_fidelity_01b.readout._witness_audit`): working
  crew 120/1045 at activation, posted zones ⊆ the 7 DP-native essential IDs,
  boxed `crew_meal_service` active_epochs 360.
- Replication check vs the 01b S3 cell for the same seed: 395 leaf fields,
  3 differences, all metadata echoes (`cell.index`, `design_id`,
  `design_sha256`); every epidemiological field bit-identical.

## 4. Image

| Field | Value |
|---|---|
| Tag | `covid-platform-fidelity-02` |
| Digest | `sha256:d641a0d69e54b4e054b2f9237ddb7d689d75413aaba2760c8f9cf8f0060c6705` |
| Built from | `db95a4f2` (root `Dockerfile` base + `deploy/aws/Dockerfile.campaign` overlay, stamped `ENGINE_GIT_SHA=db95a4f2`) |
| Preflight | ENTRYPOINT `["python3"]`; `ENGINE_GIT_SHA` `db95a4f2b63c3dc115100c7421e1261fcf61bfd7`; PF-02 worker/entry/campaign/design/protocols and `deploy/aws/campaign_entrypoint.py` present in-container |
| ECR | `994254241749.dkr.ecr.us-east-1.amazonaws.com/picard-campaign:covid-platform-fidelity-02`, pushed 2026-11-08T20:18:21Z |

## 5. Blocks

| block | arm | seeds | cells | status |
|---|---|---:|---:|---|
| `dp_t7e6_dedicated_canary` | `dedicated_diamond_princess` | 20200205–20200224 | 20 | complete — 20/20 SUCCEEDED; replication clean |
| `dp_t7e6_dedicated_rest` | `dedicated_diamond_princess` | 20200225–20200404 | 180 | running (submitted 2026-11-08) |
| `dp_t7e6_proxy` | `proxy_mega_cruise` | 20200205–20200404 | 200 | running (submitted 2026-11-08) |

Total new executions: 400. No GM cells.

## 6. Runs

| Date | Block | Seeds | Cells | Job | SHA | Digest | Jobdef rev | Wall | Result |
|---|---|---|---:|---:|---|---|---|---|---|
| 2026-11-08 | `dp_t7e6_dedicated_canary` index 0 | 20200205 | 1 | `015a87fb-faf2-4bd1-9008-164ae1765816` | `db95a4f2` | `sha256:d641a0d6…` | `:1` | ~8.9 min | SUCCEEDED; S3 payload contract-clean, 395 leaf fields vs 01b with only `cell.index`/`design_id`/`design_sha256` metadata diffs |
| 2026-11-08 | `dp_t7e6_dedicated_canary` | 20200205–20200224 | 20 | `a63d7a13-408b-45cf-b8f1-539b462fbacd` | `db95a4f2` | `sha256:d641a0d6…` | `:2` | ~26 min | SUCCEEDED 20/20 (index 0 skipped the already-uploaded inspected artifact) |
| 2026-11-08 | `dp_t7e6_dedicated_rest` | 20200225–20200404 | 180 | `982768ff-930c-4c80-a45e-da8dab93a115` | `db95a4f2` | `sha256:d641a0d6…` | `:3` | — | RUNNING |
| 2026-11-08 | `dp_t7e6_proxy` | 20200205–20200404 | 200 | `0f3e898f-35ba-490d-ab89-fe04a6f98201` | `db95a4f2` | `sha256:d641a0d6…` | `:4` | — | RUNNING |

## 7. Canary readout (2026-11-08)

- Batch: inspected child `015a87fb-faf2-4bd1-9008-164ae1765816` (jobdef `:1`)
  plus array `a63d7a13-408b-45cf-b8f1-539b462fbacd` (jobdef `:2`); array
  `statusSummary` SUCCEEDED 20 / FAILED 0. Index 0 reused the inspected child's
  S3 artifact, so the block has 20 cell payloads from 19 additional array
  simulations plus the inspected child.
- S3 prefix: `s3://crusherbucket-994254241749-us-east-1-an/campaign/covid_platform_fidelity_02/dp_t7e6_dedicated_canary/`.
- Replication vs PLATFORM-FIDELITY-01b dedicated cells (same 20 seeds): all 20
  PF-02 payloads present; `recorded_onsets` identical on every seed (0
  mismatches); P(takeoff) = 6/20 = 0.30, matching 01b. Witness audit clean on
  all 20 (resolved `diamond_princess`, fired `SOP-017-MESSBOX`, no
  `close_zones`, working-crew band, DP-native posted zones, boxed meal service
  active).
- Leaf-level replication: per-cell diffs vs 01b are only `cell.index`,
  `design_id`, and `platform_fidelity.input_hashes.design_sha256`; no
  unexpected diffs (leaf-field counts 370–500 by seed).
- Gate decision: STOP. `dp_t7e6_dedicated_rest` (180) and `dp_t7e6_proxy`
  (200) were not submitted; owner decides whether the remaining 380 cells run.

## 8. Full array (owner-approved 2026-11-08)

- Owner approved the remaining 380 cells ("go ahead with them") after the
  canary readout above.
- Submitted `dp_t7e6_dedicated_rest` (180 cells, job
  `982768ff-930c-4c80-a45e-da8dab93a115`, jobdef `:3`) and `dp_t7e6_proxy`
  (200 cells, job `0f3e898f-35ba-490d-ab89-fe04a6f98201`, jobdef `:4`) through
  `scripts/campaign submit` on the same digest-pinned image. ETA to be filled
  from Batch status; the 20-cell canary wall was ~26 min.
