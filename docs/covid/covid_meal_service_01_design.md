# MEAL-SVC-01 design — the confinement meal-delivery channel on the DP replay

Status: declared, pre-run. Criteria in this file are frozen before any
cell runs; nothing below is altered after the surface is seen.

## Question

CREW-WINDOW-02 (measured at `2df542ff`, 240/240 cells; readout
`docs/covid/covid_crew_window_02_readout.md`, ledger
`docs/ledger/CREW-WINDOW-02.md`) landed the during-quarantine mass —
FRAC_25 (301) and ZONE_NARROW (334) CHANNEL-LANDED at Θ7.9e6 — and in
doing so measured the surviving crew↔passenger channel hot and
under-converting: R3 cabin meal delivery fires 128k–166k
`service_deliveries` per cell while confined passengers acquire ~4–19
during-window infections against the record-implied bound ≥52
(`covid_believability_map_v1.md` F13/F14), and crew share holds ~0.97
against the record's 0.29.

The inspection finding is one missing direction:
`_caregiver_service_epoch` credits the pair dose to the steward only —
`emitted = _get_shedders([host])`, target = steward — so a shedding
steward delivering to a healthy confined passenger delivers zero dose.
The passenger mass is not under-dosed; the steward→host direction does
not exist.

The question this design answers: **what does the meal-delivery channel
have to be before the passenger side of the share defect closes?**

## Arm semantics (fixed here before cells run)

Grammar lives on `transmission.caregiver.service` (the shipped role
layout — role blocks sit directly under `transmission.caregiver`),
parsed in `_init_caregiver` and echoed verbatim in the resolved block
(`delivery.caregiver.roles.service` in the cell payload) on every cell:

- `direction` ∈ {"responder", "both"} — shipped default `"responder"`
  is the status quo (the pair dose credits the responder only; zero
  behaviour change). `"both"` adds the roles-swap call:
  `_caregiver_pair_dose(steward_emitting, host_inhaling, …, site=host)`
  computed per delivery and credited to the host when susceptible under
  route `service_to_host`, beside the steward-side `caregiver` tally.
  `site=host` pins the contact in the CONFINED host's cabin — the host
  unit carries the volume, ventilation and residence terms; the 5-minute
  episode share (`_caregiver_service_share`) is the same presence/plume
  factor in both directions, and the delivery's door-drop
  `service.contact_factor` (CAREGIVER-SVC-01, #936 — one realized
  draw per delivery) attenuates both directions identically. On an
  `emesis_conditioned` profile the
  reverse dose is 0 by construction: an emetic pathogen has no
  continuous emission for the host to inhale, and the surface channel
  is steward-pickup only.
- `service_responder_mode` ∈ {"uniform", "section"} — shipped default
  `"uniform"` is the status quo (any unconfined crew member drawn per
  delivery on the voyage stream). `"section"` binds each confined host
  to the steward of its cabin section: the Cabin_Corridor units are
  partitioned once into contiguous sections whose sizes draw per section
  from the declared `service_section_cabins` interval **[10, 15] cabins**
  (the record's room-steward section, declared Grade C — DP room stewards
  held a fixed section of cabins, ~10–15 each; no passenger-manifest
  source, carried as an interval); each section's steward is drawn once
  on the dedicated digest-seeded stream (`_SERVICE_SECTION_STREAM_KEY`,
  the `exempt_fraction`/`_FRAILTY_STREAM_KEY` precedent — no voyage-stream
  consumption, so `uniform` cells stay bit-identical to SVC_BASE) and
  reused while `_responder_available`; an unavailable bound steward is
  replaced by one sticky re-draw on the same stream.

The three channel arms on the single arm axis, crossed with the two
replay arms:

| arm_id | `scheduled_protocol_id` | `direction` | `service_responder_mode` |
|---|---|---|---|
| `D0_declared_svc_base` | shipped SOP-017 (unchanged) | responder | uniform |
| `D0_declared_svc_dir` | shipped SOP-017 | both | uniform |
| `D0_declared_svc_dir_sect` | shipped SOP-017 | both | section |
| `zone_narrow_svc_base` | SOP-017-NARROW | responder | uniform |
| `zone_narrow_svc_dir` | SOP-017-NARROW | both | uniform |
| `zone_narrow_svc_dir_sect` | SOP-017-NARROW | both | section |

`SVC_BASE` is the shipped default verbatim on each replay arm — the
pairing baseline vs the CW-02 rows (`D0_declared_svc_base` pairs against
CW-02 `t7p9e6_d0` for the engine-delta drift witness; `zone_narrow_*`
pairs against `t7p9e6_zone_narrow`). A pure `SECT`-without-`DIR` arm is
excluded by owner decision: structure alone cannot infect a passenger.

## Replay contract (verbatim CW-02)

`diamond_princess_2020`, `voyage_mode: declared`, SOP-017 days 16–30,
`infection_age_days` 6.8, `imports` 1, `sanitary_visit_mode`
`dwell_weighted`, seeds 20200205–20200224 (the matched 20-seed set —
every row pairs seed-for-seed against the recorded CW-02 cells),
`takeoff_recorded_onsets` 10, `seed_ring_readout` true, Θ7.9e6 only —
the landed surface; θ1e6's share is pinned ~1.000 and is a lower-bound
reading, not scored (owner decision 2).

Cells: 2 replay arms × 3 channel arms × 20 seeds = **120**
declared-replay cells.

## Scoring surface (frozen)

- **Primary:** passenger during-window acquisitions vs the
  record-implied bound ≥52 —
  `confined_passenger_infections_during_quarantine` (the F13/F14 field),
  takeoff-conditional medians per arm row; `during_window_by_role
  .passenger` reported beside it.
- **Direction witness:** during-window crew share vs the record's 0.29 —
  reported as a direction (toward/away), never a threshold.
- **During-window total** reported beside the record-informed [150,350]
  band — **not gating** (owner decision 4): the two-sided defect cannot
  be scored on one total, and closing the passenger side on top of
  ZONE_NARROW's crew-driven 334 legitimately overshoots the band.
- **Cadence parity:** `service_deliveries` per cell within noise of the
  CW-02 rows (128k–166k @7.9e6) — the mechanism must not silently change
  delivery cadence.

## Verdict grammar (frozen)

- **CHANNEL-FOUND** — a DIR arm moves the takeoff-conditional passenger
  during-window median materially toward ≥52 with deliveries parity:
  the channel, armed in both directions, carries the missing mass.
- **DOSE-EMPTY** — host-credited dose tally >0 (the direction fired) but
  passenger acquisitions unmoved: conversion is blocked downstream, a
  different address.
- **MASS-ONLY** — passenger side unmoved AND host-credited dose ~0 (or
  never reaching susceptible hosts): the channel's contribution stays
  crew-side; the missing mass lives elsewhere.

Every arm row reports: takeoff-conditional median/quartiles of
`infections_during_window`, `confined_passenger_infections_during_
quarantine`, `during_window_by_role` (crew share), `service_deliveries`,
the per-direction dose tallies, and the structure witness.

## Audit invariants (frozen — a failure halts the readout)

- `quarantine_witness.window_days == [16,30]` and `activated` true on
  every cell; `exempt_classes` == shipped four crew classes on every
  arm (carried from CW-02 unchanged).
- `index_onset_day == -1.0` and `index_shedding_at_day0` true on every
  cell; `propensity_draw.units_drawn > 0`;
  `presentation_draw_mode == 'once_per_course'`;
  `hand_reservoir_mode == 'hygiene_cycle'`; delivery echo
  `droplet_field_split` matches shipped values on every arm (carried
  unchanged).
- `crew_window` block on every cell: `total_crew == 1045`;
  `confined_crew_count + working_crew_count == total_crew` at activation
  and at end (carried unchanged).
- **Direction echo:** `delivery.caregiver.roles.service.direction`
  resolves `"responder"` on `*_svc_base` cells and `"both"` on every
  `*_svc_dir*` cell, echoed in `crew_window.service_direction`;
  `service_dose_to_host_credited > 0` iff a DIR arm (a `>0` on BASE or a
  `0` on DIR is a defect — DOSE-EMPTY still requires delivered >0 to
  distinguish "channel dead" from "conversion blocked").
- **Realized structure witness:** `crew_window.service_stewards_per_
  confined_host` — `.median`/`max` large (dozens) on uniform arms and
  ≈1–2 on `*_svc_dir_sect` cells; `service_section_steward_draws > 0`
  iff section mode. A SECT arm whose realized steward count doesn't
  collapse is not armed — halt.
- **Deliveries parity:** `service_deliveries` per arm row within noise
  of the CW-02 row band (128k–166k); a systematic departure is a cadence
  defect, reported immediately.
- `crew_window.exempt_work_zones` echoes the NARROW list verbatim on
  `zone_narrow_*` cells (null on `d0_declared_*`); realized exempt share
  strictly in (0,1) on `zone_narrow_*` (carried from CW-02).
- Reach: `doses` per susceptible host still recorded via the attribution
  ledger (carried unchanged).

## Diagnostics (frozen)

- `paired_vs_in_design_base`: each `*_svc_dir*` row pairs seed-for-seed
  with its `*_svc_base` row at the same replay arm — Δ passenger
  acquisitions, Δ crew share, Δ `infections_before_quarantine` (expected
  ~0 — every channel arm fires only inside the window).
- `paired_vs_cw02`: `*_svc_base` rows pair against CW-02's `t7p9e6_d0` /
  `t7p9e6_zone_narrow` rows at `2df542ff` — the armed-tree drift
  witness. **Not expected bit-identical**: CAREGIVER-SVC-01 (#936) landed
  the door-drop `service.contact_factor` — a (0.05, 0.3) per-delivery
  draw on `_SERVICE_CONTACT_STREAM_KEY`, default-ON — between the CW-02
  measurement SHA and this campaign's, so every delivery's steward-side
  dose is discounted and downstream trajectories diverge. The binding
  CW-02 comparison is deliveries parity (a count the factor does not
  touch); dose-side deltas are the expected contact-factor discount,
  reported as the armed-tree delta, not read as drift.
- `crew_side_witness`: `service_dose_credited` (steward-side) and crew
  acquisitions per arm — the channel is symmetric in the record; both
  directions reported.
- `route_attribution`: `during_quarantine_by_route.service_to_host` on
  DIR arms (new named key — it tallies infections whose dominant
  acquisition route was the reverse-direction credit; `caregiver` gets
  the same named-key promotion so the steward side stops landing in
  `unknown`).

## Report immediately if

- The DIR canary moves passenger acquisitions into the ≥52 neighbourhood
  (CHANNEL-FOUND — stop, report, do not submit the array).
- Host-credited dose >0 but acquisitions unmoved (DOSE-EMPTY).
- A SECT arm's realized distinct-steward count doesn't collapse
  (mechanism not armed).
- `service_deliveries` departs the CW-02 rows (cadence defect).
- Child failure rate > 5%.

## Execution (frozen)

AWS Batch via `campaigns/covid/meal_service_01/` through
`scripts/campaign`: 6 blocks (arm) × 20 seeds; jobdef
`picard-covid-meal-svc-01`, image `covid-meal-svc-01` pinned by digest
built at the merged implementation SHA, S3 prefix
`campaign/covid_meal_service_01/`, queue `picard-analysis-queue`
(On-Demand; Fargate fallback `picard-analysis-fargate-queue`),
1 vCPU / 2048 MB per cell (~10–25 min declared-replay cell).

Preflight per `campaign-preflight`: this file + the design JSON frozen
before any cell runs; local smoke on capped voyages proving both new
arms fire; `--dry-run` count = 120; pinned image digest + jobdef
revision recorded; manifest in S3; canary `zone_narrow_svc_dir`
@Θ7.9e6 (20 seeds) read out and reported before the remaining 5 blocks
submit — the canary is the arm most likely to show the passenger side
moving on the landed crew-window row.

## Non-goals

- No fitting: direction/structure/section-size are declared arms;
  whichever lands is a magnitude to source afterward, not a constant to
  adopt. Never tuned to the ≥52 bound or the 0.29 share.
- No crew subclassing — `CREW_DUTY_MIX` remains its own stage; SECT is
  a confinement-time assignment on `crew_general`, not a spawn-time
  roster.
- `SVC_DOSE` corners (`service_episode_minutes`, deliveries per token,
  steward protection) are subordinate probes deferred until after a DIR
  arm's verdict — a factor on a missing direction reads zero
  everywhere.
- No R1/R2 changes, no pre-quarantine caregiver leg (CG-FLOOR's
  DELIVERY-STRUCTURAL stands on that surface); no re-running the CW-02
  ladder; no mid-campaign arms.

## Rejected alternatives

- `SECT`-only arm — excluded by owner decision: without `direction:
  both` the host can never receive dose regardless of which steward
  delivers; a pure-structure arm spends 40 cells proving nothing.
- θ1e6 slice — excluded: the crew share is pinned ~1.000 there; a
  lower-bound reading that cannot move the verdict.
- Crediting under the existing `caregiver` route key — rejected in
  favour of `service_to_host`: route attribution must survive the
  cell payload (`during_quarantine_by_route` carries a named key for
  it); blending it into `caregiver` loses the direction witness.
- Host-side cabin confinement factor re-use on the emitting steward —
  not applicable: the steward is unconfined by construction; the swap
  takes the *host's* `target_factor` (target-side susceptibility
  scaling), the emitter's confinement emission factor stays 1.0.
