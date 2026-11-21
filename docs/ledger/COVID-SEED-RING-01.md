# COVID-SEED-RING-01
**Date:** 2026-11-21
**Commit:** 87e8e3bb2f756c6698be5fe337814a955c2a40e4
**Pathogens:** sars_cov2_resp
**Status:** measured
**Measured at:** 87e8e3bb2f756c6698be5fe337814a955c2a40e4 (image digest sha256:87bc852a27f52cf476d09e417df6845a4c66aa9485490785d40b9d1a160b4773)

Declared seam probe from COVID-IGNITION-01, run as designed: 1 θ × 2 arms ×
20 seeds (20200205–20200224) at θ=3.162e8 (`dp_theta_8p50`) on the boxed_s1s2
DP replay. `PLACEMENT_BUFFET` constrains the explicit-seed draw to agents with
`placement.dining_service_type = "buffet"`; `D0_declared` is the verbatim-base
pairing/drift witness. 40 cells on AWS Batch, audit invariants clean on every
cell.

## Verdict: NULL-PLACEMENT (founder leg fails; the embarkation-day crowd
structure is under-declared)

Founder median on the placement arm is **2.0** (takeoff-conditional; 2.0 over
all 20 cells) against the frozen ≥10 leg — identical to the drawn-placement
committed median of 2.5 within noise. Ignition median 21 on the 17/20 ignited
cells; recorded_onsets q05–q95 42–1754 vs record 197; before_share median
0.040 vs 0.173. All three legs fail.

The drift witness is **CLEAN**: the 20 in-design D0 cells pair seed-for-seed
against the committed `dp_theta_8p50` cells with recorded_onsets deltas
nonzero on 0/20 seeds — the new image replays boxed_s1s2 bit-identically, so
the null is a physics/declaration result, not image drift.

Placement was exercised as declared: 17/20 placement-arm indices seated
Windjammer (the rest Pool_Bar_Grill / CafeBakery, all buffet service type);
founder routes remain droplet + caregiver only; audit invariants (departure
epoch 120, quarantine witness window + activation, propensity units_drawn > 0,
delivery echoes, droplet split vs shipped constants) pass on every cell.

## What the null measures

Dining-zone assignment was a *correlative* footprint, not the mechanism.
Inside the arm, two seeds did produce record-class pools (20200214: 19
founders, 16 on day 0; 20200215: 25 founders, 0 on day 0) — the surge-buffet
venue supports the record footprint, but realized embarkation-day surge
participation is rare under the declared schedule rather than absent. The D0
witness shows the same heavy tail from the opposite side: its three
record-timed ignitions (ign 6/8/6) all came on drawn Windjammer indices
(20200212/19/22) with day-0 bursts 6/25/1 — i.e. the *draw* picks the surge
participant, not the seat assignment.

Reading (Arm-B of the frozen design): the missing declaration is the
embarkation-day crowd/muster geometry itself — the index's realized
day-0 itinerary through the boarding surge, not its dining venue. A
founder-lifting declaration has to place the index in the day-0 crowd
event(s) (muster stations, boarding buffet crush, embarkation queues), which
are not currently schedule-determined by `dining_service_type`.

## Standing

- The measured IGNITION-01 blocker stands unchanged: Θ is not scorable at
  θ=3.162e8 because the drawn founder pool is a lottery the record's
  ~10-founder cells won. The declared placement lever is dead; the seam
  candidate that remains is an explicit embarkation-day index-exposure
  declaration (schedule/itinerary-level, not dining assignment).
- The `placement.dining_service_type` seed-pool constraint and the
  `seed_patch.placement` arm grammar remain in the tree as declared
  mechanism — usable by any later seam probe, not reverted.
- GM scoring remains gated on the same blocker; H5 stays held-out-forever.

Readout: `campaigns/covid/seed_ring_01/seed_ring_01_readout.md`;
ops record: `campaigns/covid/seed_ring_01/LEDGER.md`.
