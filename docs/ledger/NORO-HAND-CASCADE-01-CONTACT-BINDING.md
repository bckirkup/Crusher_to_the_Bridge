# NORO-HAND-CASCADE-01-CONTACT-BINDING
**Date:** 2026-11-14
**Commit:** b47596b1
**Pathogens:** norwalk_gi
**Status:** measured
**Measured at:** b47596b1

Read-only contact/behaviour-binding probe for the posted
`fl_exp_12d_sens_p06_paxv` cell (`expedition_cruise_450`, `norwalk_gi`, 288
epochs). Arm is `carriers_ordered` at M=1; the probe adds the existing
fomite-mass-balance, hand-occupancy, cascade, sanitary-telemetry, and
acquired-route-ledger readouts without changing engine defaults. All five
seed processes ran with `PYTHONHASHSEED=1`.

Seeds: 8073, 8038, 8046, 8047, 8077. Local artifacts:
`results/noro_contact_binding_probe/hash1/s<seed>/contact_binding_fl_exp_12d_sens_p06_paxv.json.gz`;
neutrality controls: `results/noro_contact_binding_probe/hash1/hc_s8073/` and
`hc_s8077/`.

## Neutrality and baseline comparability

Measured: the probe is neutral on the two seeds re-run through the plain
`hand_cascade_witness` path. Fresh single-arm `carriers_ordered` controls on
current `main` exactly match the probe rows:

- seed 8073: 103 infected / 56 symptomatic / 1,691,447 dose / 62,124,301
  delivered / 31,038,693 deposited GEC;
- seed 8077: 80 / 37 / 1,769,838 / 60,172,074 / 25,595,073 GEC.

Measured: these current-main M=1 rows do **not** match the fixed-engine DS-M
pilot artifacts at `94daa3bf`
(`NORO-HAND-CASCADE-01-SUBSTEPS-FIXED`). `git diff 94daa3bf..HEAD` shows no
engine changes, but post-pilot merges changed every platform's
`data/platforms/*/air_flow_paths.json`; for `expedition_cruise_450` the diff is
13 added `"direction": "oneway"` fields on `Sanitary_Makeup` legs, plus
Contam/sanity tooling and docs. Current-vs-fixed M=1 ratios are non-uniform:
delivered 0.82x-4.19x, deposited 1.16x-3.36x, witness dose 0.67x-6.72x across
the five seeds. Inferred: the posted witnesses moved because platform/HVAC
data changed after the DS-M pilot and the stochastic ABM amplified the
perturbation; hypothesis: the near-zero norovirus HVAC/droplet route dose means
the large outbreak movement is chaotic amplification rather than a large direct
HVAC effect. DS-M pilot comparisons are historical until rerun on the same
commit as any new arm.

## Witness and cascade mass

| seed | infected | symptomatic | witness dose GEC | delivered GEC | deposited GEC | surface deposit GEC / calls | food deposit GEC / calls | sanitary deposit GEC / calls |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 8073 | 103 | 56 | 1,691,447 | 62,124,301 | 31,038,693 | 30,862,095 / 5,774 | 34,307 / 1,119 | 18,384 / 420 |
| 8038 | 122 | 64 | 202,555 | 8,940,024 | 7,242,986 | 7,023,550 / 6,362 | 18,162 / 1,580 | 11,045 / 567 |
| 8046 | 102 | 52 | 2,276,008 | 60,484,349 | 25,143,961 | 25,017,036 / 6,773 | 12,531 / 829 | 5,137 / 393 |
| 8047 | 77 | 46 | 1,076,319 | 37,769,902 | 21,697,113 | 21,581,656 / 4,042 | 3,124 / 947 | 926 / 297 |
| 8077 | 80 | 37 | 1,769,838 | 60,172,074 | 25,595,073 | 25,480,039 / 8,862 | 50,343 / 2,994 | 14,127 / 1,046 |

Carrier hand mass presented at surface deposit calls is much larger than the
deposited mass, as expected from the transfer kernel: e.g. seed 8073 surface
carrier hand 72,351,857 GEC over 5,774 calls and food carrier hand 901,591 GEC
over 1,119 calls. Food hand deposit mass is only 0.014%-0.259% of surface
deposit mass across the five seeds; sanitary deposit mass is 0.004%-0.153% of
total deposited mass.

## Binding diagnostics

| seed | hand+ rows / share | sanitary visits | sanitary person-hours | sanitary dose GEC | sanitary recipients | flush events | `common_source_food` acquired share | `fomite` acquired share | dominant routes (CS/food-pool/fomite/caregiver hosts) |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| 8073 | 6,498 / 22,780 = 28.5% | 21,046 | 999.2 | 8,215 | 840 | 0 | 99.85% | 0.14% | 87 / 0 / 7 / 3 |
| 8038 | 6,543 / 27,411 = 23.9% | 20,705 | 988.4 | 3,099 | 1,140 | 0 | 98.92% | 0.67% | 94 / 0 / 17 / 6 |
| 8046 | 6,814 / 24,008 = 28.4% | 21,412 | 1,026.7 | 637 | 1,012 | 0 | 98.28% | 1.03% | 69 / 0 / 16 / 9 |
| 8047 | 5,271 / 17,503 = 30.1% | 21,057 | 1,002.5 | 178 | 481 | 0 | 97.65% | 0.73% | 57 / 0 / 5 / 9 |
| 8077 | 5,626 / 17,869 = 31.5% | 20,785 | 999.8 | 3,752 | 2,112 | 0 | 95.79% | 4.09% | 45 / 0 / 21 / 3 |

Hand+ rows are shedding host-epochs whose end-of-epoch hand load is at or above
the Liu rinse LOD (`10^2.15` ≈ 141 GEC). Route shares are fractions of the
`acquired_particles_by_route` ledger mass for hosts with route ledgers
(69-117 hosts per seed), not the witness `dose_gec` accounting. `food` in the
dominant-route column would be the hand-mediated food-pool route; it is zero as
a dominant route on every seed, while `common_source_food` is the supply-chain
common-source pan route (`engines/transmission_core.py` credits it separately
from the `food` pool route).

## Measured

- The hand-carrier redeposition arm is active and moves large surface mass, but
  almost none of it enters the food pool: food hand deposits are 0.014%-0.259%
  of surface deposit mass.
- Sanitary visits are realised at scale (~20.7k-21.4k visits per voyage,
  ~988-1,027 person-hours, 76-139 stool visits), but sanitary deposited mass is
  tiny and delivered sanitary dose is 178-8,215 GEC with zero flush events.
- Acquired route dose is dominated by `common_source_food` on every posted seed
  (95.79%-99.85% of route-ledger mass). `fomite` is the only other material
  share (0.14%-4.09%); `food`, `direct_contact`, `droplet`, and `hvac_airborne`
  are negligible.
- Dominant-route host counts agree: `common_source_food` is the majority
  dominant route on every seed (45-94 hosts), `fomite` is a minority (5-21), and
  `caregiver` is rare (3-9).

## Inferred

- For these five posted expedition cells, the binding constraint is upstream of
  the hand-contamination solver: the dominant infection route is the
  supply-chain/common-source food mechanism, not hand-mediated surface or food
  redeposition. Per-contact hand/contact geometry is unlikely to move the
  posted-event tail unless it is coupled to that common-source food mechanism.
- The existing person-contact constants are probably not the main binding
  constant here: direct contact, droplet, and HVAC acquired shares are ~0 on
  these cells. This is scoped to these posted seeds; it does not exonerate
  contact constants for other hulls, anchors, or milder outbreaks.
- The contact-audit gaps remain real, but their binding-constant priority is
  lower than the common-source food magnitude/timing parameters already flagged
  by the onset-curve and mega-impact readouts (`pan_mass`, servings/lot,
  multi-meal lots, synchronized meal-window dosing).

## Hypothesis and next decision

Hypothesis: adding per-contact CE for hand/surface/food transfer would not
create the missing posted-event tail because the model's posted infections are
already dominated by `common_source_food`; the next diagnostic should measure
common-source food parameter/mechanism binding rather than hand-contact
geometry. Before any further DS-M or CE solver comparison, rerun the arms on
the current commit or pin the comparison to `94daa3bf`; this entry's rows are
current-main only. No constants were fitted and no defaults were flipped.
