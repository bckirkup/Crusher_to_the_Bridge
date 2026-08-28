# Post-#332 dose pilot (local, 3 seeds)

Purpose: relocate the norovirus dose ladder on the airborne-corrected model before
committing a 1680-run campaign to Spot, and check whether the monotone hull-size
dose gradient seen in `common_dose_containment_v1` survives the correction.

Setup: merged main at 65d1a33 (includes PR #332), hourly clock, transmission-only
`none_response` branch, constant-prevalence seeding (1/4/11), doses 2.0-7.0,
seeds 930-932, 168 epochs. Mega was abandoned after one run (~45 min/run on a
2-core box); its remaining cells move to Spot.

## Median reported passenger case rate

| dose | expedition (VSP 8.56%, 4.51-13.60) | classic (VSP 5.59%, 4.46-7.76) |
|---:|---:|---:|
| 2.0 | 29.75% | 32.29% |
| 3.0 | 17.41% | 26.46% |
| 4.0 | 19.62% | 20.25% |
| 5.0 | 12.34% (in IQR) | 13.68% |
| 6.0 | 2.85% | 7.40% (in IQR) |
| 7.0 | 0.32% | 2.54% |

## Findings

1. The hull gradient is roughly halved but not gone. Expedition crosses its VSP
   interval near dose 5.0-5.5 and classic near 6.0 — about one rung apart, where
   the pre-#332 campaign put expedition at 5.0-5.5 and classic at 7.0 (two rungs),
   with spirit and mega further up again. The airborne correction removed part of
   the size dependence; whether the remainder is real requires spirit and mega on
   the corrected model, which is what the v2 campaign measures.
2. Infection attack rate is still pinned at exactly 0.800 — the entire susceptible
   complement — at every dose up to 6.0 on both hulls. The dose parameter is
   moving P(ill | infected) through the Teunis term, not the size of the epidemic.
   Any VSP fit obtained in this regime fits an illness probability against a
   saturating epidemic, and the saturation itself is the next thing to explain.
3. Expedition is essentially unmoved by the airborne correction (crossing at 5.0
   before and after), consistent with the fix mattering in proportion to zone
   volume: cabins were the least affected geometry, large public rooms the most.

## Consequences for the v2 campaign

- Dose ladder moves to 4.5-8.0 in half-rung steps: the pilot places the two
  smallest hulls at 5.0-6.0 and the ladder needs headroom above the largest hull.
- Seeds 940-949, held out from both the v1 campaign (920-929) and this pilot.
- Everything else is unchanged from v1 so the two campaigns stay comparable.
