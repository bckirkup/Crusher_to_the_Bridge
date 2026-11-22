# Campaign Ledger — covid_seed_ring_02

Pathogens: COVID-19 (SARS-CoV-2)

Status: **closed — NULL-WINDOW measured on the canary arm**; remaining
blocks not run (owner decision at the canary gate, 2026-11-22).

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

### Canary `t8p50_w1_a8_canary` — NULL-WINDOW at α=8 (2026-11-22)

20/20 cells SUCCEEDED on AWS Batch. Array
`9a81af55-29a3-48a4-91fb-e6766e149fc1`, jobdef
`picard-covid-seed-ring-02:1`, image
`picard-campaign@sha256:84dbb44299fd47c714dd98a557e5de416a9c9634907e08963111307796ae6611`
built at merged main `3b355b64` (root Dockerfile +
`deploy/aws/Dockerfile.campaign` overlay — the recipe
`campaigns/README.md` names). Seeds 20200205–20200224.

Leg results on `WINDOW_W1_A8`:

- **Leg 1 fails**: founder median **4.0** takeoff-conditional (3.0 all
  cells) vs ≥10; ignition median **13** on the 17/17 ignited takeoff
  cells vs ≤9; takeoff 17/20.
- **Leg 2 fails**: the 6 record-timed cells (ign ≤9) hold d15
  cumulative-infection median **2,404** vs ≤960 — consistent with
  EARLY-GROWTH-01's frozen reading that the routine field over-produces.
- Trajectory: recorded_onsets q05–q95 86–2628 vs record 197;
  before_share median 0.062 vs 0.173. Routes droplet 207 / caregiver 38.
- Audit invariants clean on every cell: `effects_enabled: true`,
  α=8.0 embarkation multiplier echoed, departure epoch, quarantine
  witness, droplet split vs shipped constants.

The mechanism fired but as a lottery, not a median: 6/20 seeds produced
record-class founder pools (60/41/56/23/21/10) that ignite on days
3–9 — the seeds whose index draw lands inside the day-0 surge geometry.
The other ~3/4 of draws ignite days 12–27 on the routine field alone.
Same participation signature as SEED-RING-01's placement null: the
surge exists; the index rarely rides it.

Drift witness: not run — the `t8p50_d0` block was never submitted
(owner stop at the canary gate). In-cell audits passed on all 20 cells,
but the seed-paired witness against committed `dp_theta_8p50` cells was
not executed, so the null is read against in-cell invariants, not a
paired replay.

Blocks not run (owner decision, 2026-11-22): `t8p50_d0`, `t8p50_w1_a2`,
`t8p50_w1_a4`, `t8p50_w5_a8`. The α=2/α=4 dose-response and the
multi-day W5 declaration are unmeasured — a future session that wants
them should note the canary's bimodal signature (the binding constraint
is participation, not intensity) before spending.

Canonical readout: `seed_ring_02_readout.md` (rendered verdict
NULL-WINDOW, all 20 cells, per-cell evidence table).
