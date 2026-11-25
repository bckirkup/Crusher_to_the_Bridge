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

| seed | emesis events | patch mass GEC | picked up | pickups (count) | onboard acquisitions (all routes) |
|---|---|---|---|---|---|
| 8002 | 6 | 11.6M | 1.7% | 40 | 4 |
| 8005 | 6 | 18.8M | 4.2% | 48 | 5 |
| 8009 | 5 | 57M | 2.5% | 12 | 5 |
| 8018 | 1 | 1.3M | 77% | 47 | 10 |
| 8006 | 150 | 1.24B | 4.4% | 4,246 | 193 |

Witness counter fields: `emesis_witness` per artifact. Caveats, stated
not softened: `secondaries`/`acquisitions` counts **every onboard
acquisition regardless of route** — the artifact carries no
emesis-attributed secondary count, so these figures are voyage totals
that upper-bound emesis yield rather than measure it (on the cold cells
no food events fired, so non-emesis routes contribute, but how much is
not separable here); likewise `pickups` is a voyage total across
possibly-concurrent patches and is not per-event attributable. With
those caveats the qualitative read stands: 8002/8005/8009 fade at single-digit
acquisitions while 8018 — one event, 47 pickups, 77% of its patch mass
picked up — reached 10.

## 2. Which links are NOT the constraint (measured)

- **Patch persistence**: at least one patch is filed in 83–264 of the
  288 pickup sweeps on these cells (`sweeps_with_filed_patch` counts
  sweeps with *any* patch present, not individual patch lifetimes —
  per-patch lifetime is unmeasured; the directional evidence is that
  exposure opportunity is not sweep-scarce).
- **Dose per pickup**: 22k–117k GEC/pickup vs ~2.6e3 GEC hazard need at
  best frailty — a 10–40× margin. Caveat: the norovirus open ledger
  marks all dose figures void pending refit; this comparison is internal
  to one consistent unit system (same GEC on both sides) so the ratio
  survives any rescaling, but absolute figures carry the void mark.
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

## 4. The cabin-mass attribution was geometric, not placement evidence

Instrumented emit logging (seed 8002): the one episode observed in the
probe fired in the zone the host physically occupied — `MainDining_U`
mid-meal — consistent with occupancy-driven placement, but a single
observation in a single seed does not establish placement cohort-wide.
What *is* established: `patch_by_venue_class` records mass, not event
counts, so it cannot speak to placement at all — the 95–98%
`cabin_fittings` mass split (the NORO-HOT-VOYAGE-VALIDATION-01 era
reading) is dominated by deposition geometry: `touchable_fraction =
high_touch_area / max(floor_area, footprint)` is near 1 in cabins and
1–10% in large venues, so most venue bolus mass is floor-loss and never
enters the touchable record. Placement per se is therefore *unmeasured*
cohort-wide; the cabin-placement reading is withdrawn as unsupported
either way, and the mass-split inversion (recorded mass collapses in
venues even if episodes occur there) stands as the geometric fact.

## 5. The binding constraint: pickup COUNT per event, and why pans win

- Pickups per event run ~2–8 on the fading cells (8002/8005/8009) and
  28–47 where the chain connects (8018/8006) — voyage-total counts, not
  per-event attributable (§1 caveat); cumulative susceptible
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
