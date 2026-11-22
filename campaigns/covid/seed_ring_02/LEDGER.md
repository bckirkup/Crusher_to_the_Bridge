# Campaign Ledger — covid_seed_ring_02

Pathogens: COVID-19 (SARS-CoV-2)

Status: **registered, awaiting canary gate** — no cells run yet.

## Design

Frozen design: `picard_framework/runs/covid_seed_ring_02_design.json`
(design doc `docs/covid/covid_seed_ring_02_design.md`, evidence memo
`docs/covid/covid_voyage_stage_contacts_evidence.md`).

θ = 3.162e8 (`dp_theta_8p50`) × 5 arms × 20 seeds on the verbatim
boxed_s1s2 replay. Mechanism: the voyage itinerary layer —
`voyage_overrides` writes `config_overrides.voyage`; no engine change
beyond a per-entry `contact_rate_multiplier` pin on itinerary days.

Arms:

| arm | declaration |
|---|---|
| D0_declared | boxed_s1s2 verbatim — pairing base + drift witness |
| WINDOW_W1_A2 | day-1 embarkation, α=2 |
| WINDOW_W1_A4 | day-1 embarkation, α=4 |
| WINDOW_W1_A8 | day-1 embarkation, α=8 — canary |
| WINDOW_W5_A8 | day-1 embarkation + days 2–5 sea_day pinned α=8 |

W5 note (deviation from the design doc's first wording): days 2–5 are
typed `sea_day` with a per-entry `contact_rate_multiplier` pin rather
than `embarkation`, because the embarkation day type re-deals the
boarding-flow rhythm template each day — repeated boarding crowds are
not part of the declaration. The pinned sea day is the honest
"elevated-contact settling window"; only day 1 carries the turnaround
ops (embarkation template + 06:00–17:00 buffet-surge window).

## Frozen prediction (declared before any cell ran)

- Leg 1: `WINDOW_W1_A8` founder median ≥ 10 AND takeoff ignition
  median ≤ 9 (takeoff-conditional, censored median).
- Leg 2: record-timed cells (ign ≤ 9) hold d15 cumulative-infection
  median ≤ 960.
- Grammar: WINDOW-LANDED / FOUNDERS-ONLY / SPLIT-STAGE /
  NULL-WINDOW / DRIFT-WITNESS-FAIL.
- EARLY-GROWTH-01's reading: leg 2 fails — d15 is already 1,292 at
  α=1 and the window only adds mass — which names the routine field
  itself as the residual.

## Gate

Canary `t8p50_w1_a8_canary` (20 cells, `WINDOW_W1_A8`) submits first at
the merged-main image; read out and reported before `t8p50_d0` and the
remaining W-blocks per the campaign-preflight rule.

## Findings

_(none yet — campaign not run)_
