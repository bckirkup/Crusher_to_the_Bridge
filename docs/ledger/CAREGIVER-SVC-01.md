# CAREGIVER-SVC-01
**Date:** 2026-10-06
**Commit:** f71b26bb
**Pathogens:** all
**Status:** measured
**Measured at:** f71b26bb

R3 `service` now carries a door-drop contact discount:
`transmission.caregiver.service.contact_factor`, declared U(0.05, 0.3) and
shipped default-ON. The R1 `cleanup` role has always discounted the steward's
dose (`responder_protection_factor.steward` U[0.3,0.7], gloves/procedure);
the R3 dose carried no equivalent term — every meal delivery to a confined
cabin was treated as a full 5-minute near-field contact. The new factor is
the "the steward delivers at the door, masked, and does not enter" discount,
declared strictly below the R1 bound because that posture is more protected
than hands-on cleanup. DP crews still seroconverted on door-drop service, so
the interval is bounded above zero, not at it. Grade C declared — the same
`service_episode_minutes` field gap; nobody has measured a door-drop dose
discount. Origin: Tr.

Application is per-branch so mass conservation holds: the respiratory
channel scales the pair dose; the emetic channel scales each patch's nominal
`take` (limited contact lifts less mass off the deposit *and* removes less —
the steward does not carry mass the posture never touched). Draws run on a
dedicated spawn stream (`_SERVICE_CONTACT_STREAM_KEY`), so a uniform factor
never reorders the shared stream. Grammar: scalar spells a fixed corner;
`contact_factor: 1.0` is the labelled un-discounted baseline — it spawns no
stream and multiplies nothing, bit-identical to the pre-factor engine.

## Why now — the FLU-VIS-01 attribution

The exp `r200` sign-reversal (hot reporting *adding* onboard infections on
expedition_cruise_450 while quadrupling confinement) attributed to the
serviced-quarantine crew bridge: confined cohort ×5 → service deliveries
×2.6 → crew caregiver infections → exempt crew seed a late passenger droplet
wave (docs/flu/flu_visibility_01_readout.md §4, PR #934). The bridge ran on
the un-discounted R3 dose — this factor is the "account for limited contact"
fix for it.

## Measured response surface (paired 8-seed probe, exp `r200_dec`,
`ca775a0b`, dedicated-stream arms — onboard-acquired infections)

| seed | baseline (r100) | f=1.0 | U[0.3,0.7] | U[0.05,0.3] | 0.05 | f=0 |
|------|------|------|------|------|------|------|
| 8188 | 12 | 59 | 9 | 3 | 2 | 2 |
| 8105 | 2 | 23 | 4 | 2 | 2 | 2 |
| 8171 | 11 | 6 | 4 | 1 | 1 | 1 |
| 8162 | 29 | 67 | 68 | 73 | 59 | 18 |
| 8112 | 26 | 71 | 63 | 62 | 59 | 49 |
| 8184 | 9 | 49 | 43 | 36 | 36 | 49 |
| 8120 | 2 | 11 | 11 | 11 | 11 | 11 |
| 8142 | 28 | 2 | 1 | 1 | 1 | 1 |

- The factor works: median onboard 36 → ~7 under any nonzero discount; the
  R3 sub-channel collapses even at the mildest U[0.3,0.7]. Differences
  between candidate windows are second-order on this sample — the window
  choice is semantic, and U[0.05,0.3] carries the honest semantics.
- **The surplus is not unitary.** On 8112/8184/8120 the excess persists at
  f=0 (+23/+40/+9 vs baseline): a second confinement-mediated channel,
  showing as a passenger/droplet wave, not crew — attributed in
  `docs/ledger/FLU-SVC-RESIDUAL-01.md`: the candidate co-confined pooling
  is real but ~15% (late tail); the dominant term is a free-pool droplet
  wave sustained by the admission lottery — refused hosts are permanently
  free symptomatic shedders, and refusal realization scales with order
  volume.
- f=0 verified semantics: deliveries fire, dose_credited=0, report stamps
  still land — the discount keeps the discovery channel intact.
- 8 seeds is a mechanism probe, not an effect-size run; the fleet-scale
  effect on the flu arm wants ≥100 paired seeds if a campaign re-scores the
  r200 surface.

## Conformance

- `tests/test_caregiver_mechanism.py`: fixed factor scales pair dose
  exactly (dose(f) = f × dose(1.0) at one seed — dedicated stream never
  touches shared draws); emetic pickup drain halves at 0.5 with patch mass
  conserved; f=0 keeps deliveries + report stamps; `1.0` spawns no stream;
  malformed factors fail at spec-lands.
- Resolved-config echo: `contact_factor` lands in
  `caregiver_resolved_block().roles.service` — arm arms can stamp the
  resolved factor per cell.
