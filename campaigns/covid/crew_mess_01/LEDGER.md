# CREW-MESS-01 ledger — crew-dining attenuation arms during the DP confinement order

Status: **canary measured — STOPPED per the gate** — `sect_mess_boxed` 20/20
cells, 0 audit violations: STILL-HIGH (crew share 0.727 median, moved from
the landed 0.841 but above the (0.2,0.4) band; mess mass collapsed to median
0, residual rides cabin/galley/work zones; confined-pax guard 28 ∈ [26,160];
deliveries parity). Readout: `docs/covid/covid_crew_mess_01_readout.md`.

- Design doc: `docs/covid/covid_crew_mess_01_design.md` (frozen pre-run)
- Design JSON: `picard_framework/runs/covid_crew_mess_01_design.json`
  (5 arms × 20 seeds = 100 cells, Θ7.9e6, verbatim CW-02 replay contract)
- Parent line: MEAL-SVC-02 landed config
  (`zone_narrow` + `direction:both` + `service_responder_mode:"section"`
  + `contact_factor_to_host:[0.005,0.02]`), residual during-window crew
  share 0.841 vs the record's 0.29 carried by `crew_mess` zone class
  (44–59% of during-window mass)
- Mechanism: `crew_meal_service` protocol modifier →
  `apply_crew_meal_service` (protocol_engine) →
  `set_crew_meal_directive` (infection_dynamics_bridge) → placement
  redirect + stagger surgery at `_place_agent`; witness echoes through
  `crew_window.crew_meal_service`

## Registration

| item | value |
|---|---|
| campaign dir | `campaigns/covid/crew_mess_01/` |
| blocks | 5 (one per arm) × 20 seeds |
| jobdef | `picard-covid-crew-mess-01` |
| image tag | `covid-crew-mess-01` (pinned digest at the implementation SHA) |
| S3 prefix | `campaign/covid_crew_mess_01/` |
| queue | `picard-analysis-queue` (On-Demand; Fargate fallback `picard-analysis-fargate-queue`) |
| resources | 1 vCPU / 2048 MB per cell |
| readout | `campaigns/covid/crew_mess_01/readout.py` |

## Preflight checklist (campaign-preflight gate)

- [x] design doc + design JSON frozen before any cell ran (frozen
      verdict grammar + audit invariants + admissibility block)
- [x] local smoke: window-retimed probe (SOP-017 → days 2–3), 120
      epochs, all four mess arms — directive reaches the mess zones:
      `boxed` 1,887 diner_redirects, `cap10` 57, `stag4` 784 schedule
      rewrites (restored at the falling edge), `open` all-zero;
      `crew_meal_service` echo present on every cell with unchanged
      output contract (identical payload key sets); protocol swap
      echoes `SOP-017-MESS*`; `exempt_work_zones` 11 verbatim
- [x] `--dry-run` count == 100 cells (5 blocks × 20);
      `enumerate_cells` agrees
- [x] image `covid-crew-mess-01` built at implementation SHA
      `cca98cdc` (root Dockerfile + `deploy/aws/Dockerfile.campaign`
      overlay), ECR digest `sha256:9a3787a7e2cd5b877881ebe03047bf71db5d3a1616f2da98cbcb26fd38d466c2`;
      ENTRYPOINT `["python3"]` and the design/campaign/entrypoint files
      verified in-image
- [x] jobdef `picard-covid-crew-mess-01:1` (EC2, digest-pinned) +
      `picard-covid-crew-mess-01-fargate:1` (Fargate variant:
      `platformCapabilities FARGATE`, no `linuxParameters`,
      `assignPublicIp`, 10800s timeout)
- [x] manifest in S3 under `campaign/covid_crew_mess_01/`
      (campaign.json + design json + design md)
- [x] canary `sect_mess_boxed` (designer's pick, recorded in the
      design) — single cell contract check, then 20-seed array —
      read out (STILL-HIGH), reported, STOPPED before the other blocks

## Canaries / runs

| run | detail |
|---|---|
| image | `covid-crew-mess-01` @ `cca98cdca811676128aeaa54edbcf493f0d369b4` → ECR `sha256:9a3787a7e2cd5b877881ebe03047bf71db5d3a1616f2da98cbcb26fd38d466c2` |
| jobdefs | `picard-covid-crew-mess-01:1` (digest-pinned); `picard-covid-crew-mess-01-fargate:1` (Fargate variant) |
| canary single | `4c107699-3335-4a67-a8f5-4aeae75fedc3` (Fargate) — `sect_mess_boxed` seed 20200205, SUCCEEDED ~22 min; contract verified (mode boxed, 360 active epochs, 13,693 diner_redirects, deliveries 162,238 vs landed 162,447, exempt zones 11, section draws 155, stewards/host 1.0/4, crew_mess during-mass 0). The EC2-queue twin `4783eb89` left queued as the dedup'd no-op (queue was still scale-from-zero at +10 min) |
| canary array | `3123c6d2-4b95-4b72-b1ba-bb4d9f980617` — 20-cell array on `picard-analysis-fargate-queue`, submitted 2026-10-07 19:15Z, 20/20 SUCCEEDED ~19:15–19:40Z |
| canary verdict | **STILL-HIGH** — crew share med 0.727 (takeoff-conditioned 0.68), confined-pax med 28 ∈ [26,160], during med 22, mess mass med 0 (135/1,179 pooled residual on posted-staff cells), deliveries 162,184.5 parity, 0 audit violations, 0 flags |
| stop | HELD per gate — remaining 4 blocks (80 cells) are the owner's call |

## Post-canary analysis

- **Berth attribution** (owner option 1, 2026-10-07): 3 `sect_mess_boxed`
  seeds re-run locally (20200218/20200223/20200210 — same realizations;
  crew counts 154/178/68 match the Batch cells). 400 during-window crew
  events: ~73% occupational (galley 117, mess-posted 65, work zones 64,
  corridor 47), ~27% berth-zone (107: 59 co-berth / 48 corridor-pool);
  74 confined crew infected in own berth — 35 carry-home via
  during-window-infected mate. The 0.29 share is unreachable by dining
  policy; seam named `CREW-BERTH-01` (cohort separation + galley pods).
  Readout section: `docs/covid/covid_crew_mess_01_readout.md`
  §Post-canary; tool `tools/covid_berth_attribution.py`; evidence
  `reports/crew_mess_berth_attr/`.
