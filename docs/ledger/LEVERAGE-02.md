# LEVERAGE-02
**Date:** 2026-09-28
**Commit:** 6085e726
**Pathogens:** norwalk_gi, sars_cov2_resp
**Status:** measured
**Measured at:** 6085e726

## Contract and method

Same mechanics as LEVERAGE-01 (`docs/ledger/LEVERAGE-01.md`): one-at-a-time
endpoint perturbation across each register row's declared interval, scored
through the two live channels. **L2** = an endpoint flips an anchor verdict;
**L1** = an endpoint moves a scored quantity measurably without flipping;
**L0** = no detectable movement across the whole interval. Scored outputs are
unchanged (A1/A2/A5/A8/A9 noro anchors; H1/H2/H3 covid hull anchors); the
noro scored set is `A1_ever_ill_passenger`, infection/reported-case attack
rates, `A5_passenger_crew_ratio`, `vsp_posted`. Noise gate = paired-seed
spread (8105/8106 noro; 20200205/06, 20200315/16 covid).

Frozen design: `picard_framework/runs/leverage02_design.json` (49 axes over
38 register rows, 250 cells; transforms and endpoint realizations recorded
there). Driver `picard_framework/leverage_screen.py` (unchanged harness;
new transform kinds for rhythm/catalog scopes), Batch worker
`deploy/aws/leverage01_entrypoint.py`, image `leverage02-55239a2d`
(digest `sha256:33a3c7caf0571b3a14cf6899a9c03af1b056ef74e7c80d2f18fd85630df4d599`),
jobdef `picard-leverage02:4`.

## What changed since LEVERAGE-01 (why the re-rank exists)

- `rhythm.enabled` default-on for catalogued cruise platforms
  (SHIP-RHYTHM-02) — day-cycle event cohorts partition onboard contact.
- `transmission.exposure_cap.enabled` default-on (EXPO-CAP-01, `429fe0f9`) —
  per-shedder contact budget bounds event reach.
- `fred_behavior.escort_delay_hours` default-on at 1 h (NORO-VENUE-02,
  PR #764 / `6085e726`) — order→admission escort latency; the user added
  it mid-campaign, so the whole ranked set was re-measured on the
  post-764 stack (baselines confirmed byte-identical on both channels).

## Ranked set

1. **Never-ranked (first rank):** nine §3.6 rhythm constants
   (`meal_/event_participation_fraction`, `occupancy_share`,
   `post_prandial_emesis_multiplier`, `post_prandial_window_minutes`,
   `asleep_in_cabin_share`, `port_day_onboard_fraction`,
   `port_return_front_concentration`, `sop_capacity_multiplier`),
   two cap rows (`voyage_contact_multiplier`, the
   CONTACT-ARCH-01/POLYMOD `activity_contact_rate` axis), and the
   NORO-VENUE-02 `escort_delay_hours` k-axis (declared [0, 3] h).
2. **Reopened L0s (34 axes):** reopened iff the row's scored channel runs
   through event-cohort partitioning (rhythm: any onboard contact or
   meal/egress timing row) or the per-shedder budget (exposure cap: any
   contact-rate or partner-rate row). Under that criterion the reopened
   set is the noro route/deposit/stool/symptom family, the shared food and
   sanitary rows, HVAC/blackwater config rows, and all six covid route
   multipliers plus `airborne_half_life`, `symptomatic_fraction`,
   `surface_decay`.
3. **L1 re-confirmation:** `import_prevalence`, `never_symptomatic`,
   `illness_duration` re-measured at the same endpoints on the new stack.

## Campaign record

Bucket `s3://crusherbucket-994254241749-us-east-1-an/campaign/leverage02/`.

- **Canary v1 (18 cells):** `noro_rhythm_meal_participation` resolved and
  consumed (`rhythm.event_overrides` wiring added by the harness PR — the
  §3.6 catalog constants had no consumed config path before it);
  `cov_voyage_contact_multiplier` was **byte-identical across the 6×
  sweep** — a dead channel: `resolve_epoch_state` returns the identity
  state unless `effects_enabled` AND a non-empty `itinerary` are present.
  Fix: the transform now also declares a sea-day itinerary entry so
  `effects_active` engages; verified locally that day type, onboard
  share and dining weights stay identical so the endpoint is the single
  moved quantity.
- **Re-measurement (22 cells):** PR #764 landed mid-campaign and changed
  the default-on stack; all 18 canary cells plus the 4 escort cells were
  re-run on the post-764 image (records overwritten in place — no
  S3 delete permission). Baselines confirmed byte-identical pre/post-764
  on both channels: k=1 default-on never fires on the exercised cells
  (zero confinement orders → empty escort queue).
- **Spot drought** parked the re-run queue ~1 h; moved to the on-demand
  queue `picard-analysis-queue` under the standing approval.
- **Array `b9ea7d2e-23fd-4fee-9d69-eebabe1557af`, size 250, 250/250
  SUCCEEDED, 0 FAILED** on jobdef rev 4; dedup skipped the 22
  re-measured cells. All 250 records uploaded; every perturbation's
  `resolved_witness` confirms the override reached the engine.

## Results — per-row endpoint outcomes

| Axis group | Lev | Outcome |
|---|---|---|
| `noro_import_prevalence` (row 296) | **L1** | 0.0164 moves A1 ever-ill + infection + reported-case AR; 0.0014 no move — re-confirmed |
| `noro_never_symptomatic` (row 341) | **L1** | 0.68 moves infection AR; 0.22/0.36/0.59 no move — re-confirmed |
| `noro_illness_duration` (row 284) | **L1** | 13 d moves A1 + reported-case AR; 1 d no move — re-confirmed |
| all 46 remaining axes | **L0** | no movement at any endpoint beyond the paired-seed gate |

### Highlights inside the L0 mass

- **`noro_escort_delay_hours` (row 659, the added k-axis):** k=0 and k=3
  are byte-identical to baseline on every scored output, both seeds —
  conditional-L0 by construction on the exercised cell. The witness
  resolves (0.0/3.0) and the mechanism is live in NORO-VENUE-02's own
  warm cell, but the leverage cell issues **zero confinement orders**
  (`total_quarantine_person_epochs: 0`, reported-case rate 0.0 on both
  seeds), so nothing enters the escort queue for the delay to gate.
  Ranked L0 conditional on the exercised cell; reopens the moment a cell
  fires an order (the noro import path is the candidate — it moved under
  `import_prevalence`'s high endpoint).
- **`cov_voyage_contact_multiplier` (row 639, cap row):** channel live
  and strongly asymmetric — 0.2 collapses DP-20200206 to **0 onsets**
  (vs 3528 baseline) and greg-0315 56→10; 1.2 moves greg upward
  (56→79, 31→51) while DP saturates both directions (1903→1836/2807).
  Movement is on `recorded_onsets`/placement — real channel movement
  that does not reach an H-anchor verdict flip, so L0 by contract.
- **`noro_rhythm_meal_participation` (row 609):** the 0.95 endpoint moved
  raw attack rate on both seeds (0.0021→0.0026 / 0.0037→0.0052) but no
  *scored* quantity cleared the paired-seed gate — L0 by contract; the
  lever is live, the cell is cold.
- Every other §3.6 rhythm constant, both cap axes, and all 34 reopened
  rows: no scored movement at either endpoint — conditional-L0, same
  standing caveat as LEVERAGE-01 (cold noro cell; the covid arm is
  dose-saturated on its route ring).

## Report-trigger check

- **Declared-basis row reads L2:** none — no L2 anywhere in the set.
- **Rhythm/cap flags not consumed:** not observed — every cell's
  `resolved_witness` resolved; the one dead channel found (voyage
  itinerary short-circuit) was fixed before the array.
- **`import_prevalence`/`never_symptomatic` loses L1:** did not happen —
  all three L1s re-confirmed; the parallel noro import session's scope
  stands.

## Carry-over lists (unchanged conventions)

- **Override-blocked:** the 22-row LEVERAGE-01 list still applies — no new
  rows were wired; the appended blocked list lives in LEVERAGE-01 §last.
- **Not rankable (≠ L0):** flu/c.diff/measles/legionella arms still have
  no scored channel; rows with no declared interval stay `L?`.
- **Noro cold-cell caveat:** most noro route/deposit rows stay
  conditional-L0 by construction until establishment exists; their L0 is
  "no movement on the exercised cell", not "no leverage anywhere".

## What the new L1/L2 set buys

Nothing joined the L1 set and no L2 emerged: the post-764 leverage
surface is the same three noro L1s plus the still-sole L2 `cov_theta`
(untouched this campaign — its channel was not reopened). The rhythm and
cap instruments are proven live-but-cold on the exercised cells; the
escort latency is the newest conditional-L0, gated on confinement orders
the cold cell never issues.
