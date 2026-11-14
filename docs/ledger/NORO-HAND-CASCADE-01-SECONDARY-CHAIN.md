# NORO-HAND-CASCADE-01-SECONDARY-CHAIN
**Date:** 2026-11-14
**Commit:** 4119dd79
**Pathogens:** norwalk_gi
**Status:** measured
**Measured at:** 4119dd79

Read-only secondary-transmission provenance probe for the posted
`fl_exp_12d_sens_p06_paxv` cell (`expedition_cruise_450`, `norwalk_gi`, 288
epochs). Arm is `carriers_ordered` at M=1 through `growth_chain_census` with
`payload_profile="full"` and `PYTHONHASHSEED=1`. The probe joins
`common_source_food` acquisitions to `common_source.events` and keeps fomite
`delivered_src_*` provenance; `lean` is insufficient because it drops pickup
rows. Local artifacts:
`results/noro_secondary_chain_probe/hash1/s<seed>/secondary_chain_fl_exp_12d_sens_p06_paxv.json.gz`.

Seeds: 8073, 8038, 8046, 8047, 8077. A same-commit `hand_cascade_witness`
recheck on `4119dd79` reproduced the current-main `carriers_ordered` rows
exactly, so the `ed038a9d` contact-binding witness comparison remains valid.

## Measured

| seed | imports | acquired | `common_source_food` acq. | `fomite` acq. | `caregiver` acq. | symptomatic hosts CS/fomite/caregiver | CS source class | CS unmatched | fomite acquired-source GEC |
|---:|---:|---:|---:|---:|---:|---:|---|---:|---:|
| 8073 | 6 | 97 | 87 | 7 | 3 | 52 / 4 / 0 | `provisioned_lot` supply_chain ×87 | 0 | 460,304 |
| 8038 | 5 | 117 | 94 | 18 | 5 | 53 / 8 / 3 | `provisioned_lot` supply_chain ×94 | 0 | 1,903,748 |
| 8046 | 8 | 94 | 67 | 17 | 10 | 43 / 5 / 4 | `provisioned_lot` supply_chain ×67 | 0 | 4,823,510 |
| 8047 | 6 | 71 | 57 | 5 | 9 | 38 / 4 / 4 | `provisioned_lot` supply_chain ×57 | 0 | 945,559 |
| 8077 | 11 | 69 | 45 | 21 | 3 | 28 / 6 / 2 | `provisioned_lot` supply_chain ×45 | 0 | 4,002,885 |

- Every `common_source_food` acquisition matched a `provisioned_lot`
  supply-chain common-source event in `MainDining`; `cs_acq_unmatched` is 0
  on all five seeds. No `ill_handler` or `ill_diner` aboard-source
  common-source acquisitions were matched on these posted cells.
- `acquisitions_by_gen` is `unresolved` for every acquired host because
  `variant_surveillance.enabled` is false in the posted spec; that is a
  pedigree-attribution gap, not evidence against secondary transmission. The
  fomite `delivered_src_acquired_gec` values above are the secondary-mass
  evidence: fomite acquisitions draw on acquired-host contamination with
  import mass ≈ 0.
- Symptomatic acquired hosts are dominated by `common_source_food`
  (28-53 per seed). Fomite contributes only 4-8 symptomatic hosts per seed
  despite carrying 0.46M-4.82M GEC of acquired-source delivered mass;
  caregiver contributes 0-4. Seed 8077 has one additional symptomatic import
  outside the acquisition rows.
- `common_source_food` `delivered_src_*` remains near zero because
  `_cs_credit_pending` exposures are not pickup rows; the event-window join
  above is the correct provenance seam for that pathway.

## Inferred

- These posted expedition outbreaks are provisioned-lot common-source primers
  plus fomite secondary spread. They are not seeded by aboard
  `ill_handler`/`ill_diner` common-source events on these five seeds.
- For the posted-event tail, secondary transmission is present but small in
  symptomatic-host terms: the model already has fomite secondary mass, yet it
  converts to only 4-8 symptomatic hosts per seed. Making the biggest posted
  outbreaks larger without making them common likely requires more fomite
  secondary conversion/chain depth or a different common-source pan
  magnitude/timing structure, not merely more total contamination mass.

## Hypothesis and next decision

Hypothesis: the next binding measurement should be fomite secondary
chain-depth/conversion (who acquires from whom, where/when, and why high
delivered acquired mass produces few symptomatic hosts) together with
common-source pan magnitude/timing. Per-contact hand/contact geometry remains
a lower-priority suspect for these posted cells because acquired route dose is
dominated by `common_source_food` and the only other material share is
fomite. No constants were fitted and no defaults were flipped.
