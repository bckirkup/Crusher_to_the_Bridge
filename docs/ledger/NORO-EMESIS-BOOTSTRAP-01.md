# NORO-EMESIS-BOOTSTRAP-01
**Date:** 2026-11-25
**Commit:** #1419
**Pathogens:** norwalk_gi
**Status:** measured
**Measured at:** e3817535e9

Post-hoc decomposition of the emesis patch → pickup → conversion chain,
plus a local instrumented occupancy/placement probe. Motivation: the hot
cells of the 8000–8019 cohort are food-dominated in route tally, and the
user's reframed target (99.5% cold is correct; hot cruises must transmit
through the right routes at the right AR) requires a person-to-person
ignition route that is currently not competitive with contaminated
provisions. No new campaign cells; no constants moved.

## 1. Per-event yield: the chain is near-critical, not dead

Carrier-R+D arm artifacts, crossing/hot seeds:

| seed | emesis events | patch mass GEC | picked up | pickups (count) | secondaries | yield/event |
|---|---|---|---|---|---|---|
| 8002 | 6 | 11.6M | 1.7% | 40 | 4 | 0.7 |
| 8005 | 6 | 18.8M | 4.2% | 48 | 5 | 0.8 |
| 8009 | 5 | 57M | 2.5% | 12 | 5 | 1.0 |
| 8018 | 1 | 1.3M | 77% | 47 | 10 | 10.0 |
| 8006 | 150 | 1.24B | 4.4% | 4,246 | 193 | 1.3 |

Witness counter fields: `emesis_witness` per artifact. Subcritical cells
(~0.7–1.0 yield) fade; 8018 proves a single event can yield 10
secondaries when its pickup connects.

## 2. Which links are NOT the constraint (measured)

- **Patch persistence**: patches live 83–264 of 288 epochs (`sweeps_with_filed_patch`).
- **Dose per pickup**: 22k–117k GEC/pickup vs ~2.6e3 GEC hazard need at best frailty — 10–40× sufficient.
- **Venue occupancy** (local instrumented probe, seed 8001, 72 epochs, n=1910): cabin share of aboard agent-epochs **9.2%**; venues dense — LidoBuffet ~90 occupants/epoch mean, MainTheater 238, PoolDeck 115, MainDining_U/L ~98–100. No occupancy starvation.
- **Withdrawal timing**: moot — there is no withdrawal at all (below).

## 3. There is no symptom-driven withdrawal (measured)

Local probe, seed 8002, 288 epochs, per-epoch location tally by symptomatic status:

| group | cabin share day | cabin share night |
|---|---|---|
| symptomatic | 6.8% (n=2828 host-epochs) | 7.3% (n=1326) |
| well | 5.8% | 15.3% |

Symptomatic hosts circulate at occupancy rates — nobody retreats.
Realism questionable in the transmission-*favorable* direction;
recorded, not acted on.

## 4. Episode placement follows occupancy; the cabin-mass attribution was geometric

Instrumented emit logging (seed 8002): episodes fire in the zone the
host physically occupies — the observed episode landed in `MainDining_U`
while the host dined. The `patch_by_venue_class` split that showed 95–98%
`cabin_fittings` (NORO-HOT-VOYAGE-VALIDATION-01 era reading) is a
deposition-geometry artifact: `touchable_fraction = high_touch_area /
max(floor_area, footprint)` is near 1 in cabins and 1–10% in large
venues, so 90–99% of venue bolus mass is floor-loss and never enters the
touchable record. **Episodes were in venues all along; recorded mass
collapses there.** This entry supersedes the cabin-placement reading.

## 5. The binding constraint: pickup COUNT per event, and why pans win

- 2–10 pickups per emesis event shipwide; cumulative susceptible
  occupants of patch-matched units run 1–4k over patch lifetime
  (8009: 3,914 matched susceptibles → 12 pickups, ~0.3% conversion of
  exposure to pickup).
- The pan route dominates because it is delivery-efficient by
  construction: contaminated food carries dose directly to ingestion in
  dozens–hundreds of diners. The emesis route bleeds mass at every step:
  90–99% floor-loss in venues, then ~0.3% exposure→pickup conversion.
- User's framing (2026-11-24): "food attracts people and mess repulses
  them" — in venues the post-event exposure tail is behaviorally moot
  (avoidance + cleanup), so the entire venue-emesis transmission budget
  is the **event-moment co-exposure pulse**: what co-present patrons
  receive in the seconds-to-minutes before the room reacts.
- The modeled event-moment channel is thin: emesis aerosol mass per
  voyage measured at 9–906 GEC (vs 1M–1.24B patch) across the cohort
  artifacts. Tranche-28 records the airborne mechanism as real
  (emesis-conditioned, measured concentrations in patient air) but
  undecidable in magnitude from Alsved/Bonifait/Rupprom alone.

## 6. Lever candidates in measured order of leverage

1. **Event-moment co-exposure** — the aerosol plume + settling-radius
   dose to co-located diners during the episode itself, before any
   avoidance/cleanup. Largest structural gap vs the documented
   venue-outbreak pattern. Needs a literature measurement (tranche-style)
   before any design.
2. **Floor-loss boundary** — the all-or-nothing high-touch classification
   discards settling onto tables/chairs/service items near the event.
   Structural boundary, not a measured constant.
3. Explicitly not candidates: persistence, dose-per-pickup, occupancy,
   withdrawal timing.

## 7. Provenance

Probes: `/tmp/occprobe/probe*.py` on the session VM (ephemeral; the
method is one paragraph: wrap `TransmissionCore._epoch_zone_occupants`
and the harness `_record_emit` in `tools/noro_diag/per_host_dose_challenge.py`
and run `run_seed` locally at small epochs — reproducible in minutes).
Artifact numbers: the 60 downloaded artifacts of
`noro_external_sequester_01` / `noro_carrier_distribute_01`
(`s3://crusherbucket-994254241749-us-east-1-an/campaign/`).
**Nothing in this entry moves a constant or selects a value.**
