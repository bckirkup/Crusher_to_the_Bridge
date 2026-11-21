# covid_quar_tail_01 — ledger

Seam-probe campaign executing the frozen
`picard_framework/runs/covid_quar_tail_01_design.json`
(QUAR-TAIL-SEAM-01): does a reduced-exempt confinement declaration —
the CW-02 grammar at the right-sized truth θ=3.162e8 — land the dual
prediction declared in COVID-QUAR-TAIL-01 (during-window median into
[150,350] AND confirmed-per-infection capture ≥ 0.80)?

1 theta × 4 arms × 20 seeds = 80 declared-replay cells on the verbatim
DP contract. Follows `campaigns/covid/crew_window_02/` as the working
template: the boarding-screen cell map decomposes into 4 blocks (arm) ×
20 seeds; `entry.py` translates block args + seed into `cell.py` argv;
`run_cell`/`merge_screen` are reused unmodified. No engine delta — every
mechanism (SOP-017-NARROW / -QUARTER, crew_duty_exclusion, crew_window
witnesses) already ships from the CW-01/CW-02 legs.

Layout notes:

- `cell.py` — worker: one (theta, arm_id, seed) cell → `cell_<seed>.json`.
- `entry.py` — argv hook; block `args` carry `theta` + `arm_id`.
- `readout.py` — dual-prediction verdict grammar + audit invariants +
  duty-exclusion echoes + committed dp_theta_8p50 drift witness.
- Block order in campaign.json is cell-order: arm, then seed.

Ops status, verdicts, and follow-ups are appended below as the campaign runs.

## 2026-11-21 — registration

- Spec registered: `campaigns/covid/quar_tail_01/`, queue
  `picard-analysis-queue`, image tag `covid-quar-tail-01`, resources
  1 vCPU / 4096 MB (matching the THETA-REFIT-01 DP jobdef).
- Every cell runs the design's `base_overrides` (boxed_s1s2 verbatim:
  SOP-017-MESSBOX + section steward + retest tiers + crew wave) with the
  arm's delta composed on top; `funnel_echo` armed for the CAPTURE-01
  decomposition.
- Arms: D0_declared (boxed_s1s2 verbatim; drift witness vs committed
  8p50 cells), MB_DUTY (boxed + VSP duty exclusion — the record-warding
  single-lever arm; canary), FRAQMB (boxed, exact-quarter fraction via
  SOP-017-QUARTERMB), FRAQMB_DUTY (fraction + duty).
- Canary per the campaign-preflight gate: `t8p50_mb_duty` (20 cells)
  read out before the remaining 60 submit.
- Local smoke (430-epoch cap, seed 20200205): MB_DUTY reads
  SOP-017-MESSBOX + 11-zone exempt echo + duty exclusion resolved
  (43 off-duty at end); FRAQMB_DUTY reads SOP-017-QUARTERMB +
  exempt_fraction_drawn {QUARTERMB: crew_general 261} + duty resolved
  (44 off-duty); funnel_hosts populated on both.

## 2026-11-21 — canary submitted + read out

- Image `picard-campaign:covid-quar-tail-01` built at merged main
  43e45aeda07894f164a48180e39034f48ae26292, pushed digest
  `sha256:39eb3d53b9f6310f7047a6db66eafe0d716ccc6d77e6885b6fdf1e156cf28a34`;
  jobdef `picard-covid-quar-tail-01:1` pins the digest.
- Single-cell gate (`--canary --index 0`, job
  `2365f804-d8d4-4965-8ede-f948d9fecb42`): SUCCEEDED, verified MESSBOX +
  11 zones + duty resolved + funnel_hosts populated + share@act 0.315.
- Canary block array `a1b8ffb5-a014-4b2d-83f0-d27306bcc65a` (20 seeds,
  `t8p50_mb_duty`): 20/20 SUCCEEDED, ~30 min; prefix
  `s3://crusherbucket-994254241749-us-east-1-an/campaign/covid_quar_tail_01/`
  (design.json alongside).
- Readout `readout_mb_duty.md`: **UNDER-DAMPED** — takeoff-conditional
  during median 425 vs band [150,350]; capture median 0.519 vs ≥0.80;
  15/20 takeoff; 0 audit violations. Mechanism fired (duty excluded
  median 168; off-duty-at-end 1–210), but paired vs committed
  `dp_theta_8p50` cells the before/during deltas are symmetric scatter
  (median 0, [-483,+269]) — no systematic damping from symptomatic-crew
  removal alone. Consistent with the cabin-resident-tail hypothesis;
  FRAQMB is the remaining share-axis discriminator.

## 2026-11-21 — full campaign submitted + read out

- Remaining 60 cells submitted under jobdef rev :3 (same pinned digest):
  t8p50_d0 `41ec8037-3eb1-432a-b84d-25b4c891cfca`,
  t8p50_fraqmb `9f102ca2-82e7-4f00-8fc1-b0735569faf0`,
  t8p50_fraqmb_duty `cbcd3f60-418e-4d9d-89e8-57c8b0c0e424`.
- 80/80 cells SUCCEEDED, 0 audit violations.
- Frozen-grammar verdicts: D0_declared BASELINE (bit-exact replay —
  paired during-median delta 0.0 vs committed dp_theta_8p50, n=16);
  FRAQMB UNDER-DAMPED (394); MB_DUTY UNDER-DAMPED (425);
  **FRAQMB_DUTY HALF-LANDED-MASS (257, in [150,350] band)** — paired
  13/16 negative, median -62.5. The tail is crew-service-fed only
  jointly: neither lever alone damps it.
- Conditioned capture (CAPTURE-01 basis, confirmed/infections_reachable):
  0.811–0.843 on every arm — the ≥0.80 criterion is already met on
  reachable infections; the unconditioned ~0.52 is the structural
  post-window residual. On the conditioned basis FRAQMB_DUTY is
  SEAM-LANDED.
- Residual Θ blocker: the trajectory clause (before_share 0.059 vs
  record 0.173 — the ~10d-late ignition) untouched by every arm.
- Committed readout: `docs/covid/covid_quar_tail_01_readout.md`;
  ledger entry `docs/ledger/COVID-QUAR-TAIL-SEAM-01.md`.
