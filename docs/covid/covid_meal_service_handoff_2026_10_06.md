# Meal-service handoff — 2026-10-06

Status: handoff record. Reports no new numbers — every figure below is
quoted from the readout or ledger entry that measured it, with that
entry's `Measured at` SHA. Retires the MEAL-SVC-01 session at the
canary's frozen stop rule.

## 1. The question

On the verbatim `diamond_princess_2020` replay at θ7.9e6: **what does
the confinement meal-delivery channel have to be before the passenger
side of the share defect closes?** CW-02 measured the channel hot and
under-converting — 128k–166k steward deliveries/cell, passengers
acquiring ~4–19 during-window vs the record-implied bound ≥52
(F13/F14), crew share ~0.97 vs the record's 0.29 — because
`_caregiver_service_epoch` credited each delivery's dose to the
steward only; the steward→host direction did not exist.

## 2. Current hypothesis — resolved to a measurement

The missing direction was the conversion defect: arming
`direction: "both"` (roles-swap `_caregiver_pair_dose` credited to the
host under route `service_to_host`) converts deliveries into
confined-passenger infections immediately and at large magnitude.
What remains open is not whether the channel exists but where its
declared magnitude sits between 0 and this arm's full pair dose.

## 3. Evidence for

- Canary measured (`32b11ccf`, image
  `picard-campaign@sha256:2f2f27c9`, 20/20 cells, 0 failures):
  `zone_narrow_svc_dir` confined-passenger takeoff-conditional median
  **804** vs bound ≥52 → CHANNEL-FOUND; during median 1,267 (band
  [150,350] beside); crew share median 0.379 vs record 0.29 (CW-02
  ~0.97). Readout `docs/covid/covid_meal_service_01_readout.md`;
  ledger `docs/ledger/MEAL-SVC-01.md`.
- Mechanism witnesses clean: direction echo `both` every cell,
  host-credited dose >0 on all 19 takeoff cells and exactly 0 on the
  no-takeoff cell (no shedding steward by construction — audit now
  takeoff-conditional), deliveries median 166,150 inside the CW-02
  band, stewards/host median 44 consistent with the uniform draw.
- Per-seed structure: confined-pax 84→1,290 scaling with voyage
  shedder mass; `service_to_host` is the dominant during-window route
  on takeoff cells (up to 1,337/cell).

## 4. Evidence against / unexplained

- The declared full pair-dose magnitude overcorrects ~15× on the
  primary surface and pushes crew share past the record the other way
  (0.379 vs 0.29). Nothing in this stage attenuates the direction —
  that is the sweep axis, not a defect (declared arm, unfitted).
- The `*_svc_base` rows did not run, so the CW-02 drift witness is
  unpaired — whether #936's default-ON `contact_factor` moved the
  base surface at all is unmeasured (deliveries parity suggests not
  materially).
- The SECT structure arm is unarmed evidence: whether sticky
  10–15-cabin steward sections change the conversion per delivery is
  unknown.

## 5. PRs landed this session (dependency order)

- #937: MEAL-SVC-01 implementation + frozen design — service
  `direction` / `service_responder_mode` / `service_section_cabins`
  grammar at `transmission.caregiver.service`, roles-swap host credit
  under `service_to_host`, section binding on a dedicated stream,
  per-direction tallies + structure witness in `crew_window`,
  campaign spec + cell + readout. Union-merged #936's door-drop
  `contact_factor` (one realized draw shared by both dose directions;
  `paired_vs_cw02` amended to deliveries parity).
- (this close-out): canary readout doc, `docs/ledger/MEAL-SVC-01.md`,
  open-ledger §2 update, README rows, LEDGER ops record, readout
  takeoff-conditional audit fix.

## 6. Running jobs / artifacts

None running — the frozen stop rule held back the remaining 100 cells.
Canary results at
`s3://crusherbucket-994254241749-us-east-1-an/campaign/covid_meal_service_01/`
(manifest + `design.json`/`design.md` at prefix root, 20 `cell_*.json`
under `zone_narrow_svc_dir/`). Jobs: chain-check
`5b58924d-ee61-4d9c-b0fd-7ca4d3a9443b`, canary array
`72a36039-6d83-4e1f-be6d-eea60db2b4ef`. Image
`picard-campaign@sha256:2f2f27c9` (tag `covid-meal-svc-01`); jobdef
`picard-covid-meal-service-01` rev 1 (digest-pinned).

## 7. What is now void / superseded

Nothing withdrawn. CW-02's share measurement stands — MEAL-SVC-01
explains it: the passenger side of the defect was the absent
direction, not attenuation failure of an existing channel. The
confined-passenger bound (≥52) is reachable on this channel at the
declared magnitude — the believability map's F13 under-delivery leg is
informed (channel exists; magnitude unsourced).

## 8. The single open decision

Which attenuation axis sweeps `service_to_host` between 0 and the
full pair dose — candidates already named in the design: a
host-direction efficiency/contact factor, asymmetric application of
the door-drop `contact_factor`, episode share, or delivery cadence.
The SECT arm and the `*_svc_base` drift pairing ride along on
whichever grid that stage declares.

## 9. Do not reopen

- The replay contract is frozen (SOP-017 days 16–30, infection_age
  6.8, imports 1, seeds 20200205–20200224, `dwell_weighted`).
- The direction magnitude is a declared structural arm; whatever
  factor lands next is a magnitude to source, never a constant tuned
  to ≥52 or 0.29.
- `service_deliveries` cadence parity is a binding invariant on any
  magnitude arm — an axis that changes the delivery count is a
  different mechanism, not an attenuation.
