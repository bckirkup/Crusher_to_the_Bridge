# CREW-MESS-01 ledger — crew-dining attenuation arms during the DP confinement order

Status: **declared, pre-run** — canary `sect_mess_boxed` pending.

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
- [ ] image `covid-crew-mess-01` built at implementation SHA,
      digest-pinned (see Canaries / runs)
- [ ] jobdef `picard-covid-crew-mess-01` registered (+ Fargate variant)
- [ ] manifest in S3 under `campaign/covid_crew_mess_01/`
      (campaign.json + design json + design md)
- [ ] canary `sect_mess_boxed` (designer's pick, recorded in the
      design) — single cell contract check, then 20-seed array —
      read out, reported, STOP before the other blocks

## Canaries / runs

(pending)
