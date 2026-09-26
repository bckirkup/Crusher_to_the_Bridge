# CABIN-OCC-01
**Date:** 2026-09-26
**Commit:** #PENDING
**Pathogens:** all
**Status:** measured
**Measured at:** #PENDING

Cabin-mate exposure channels now gate on **time-partitioned co-occupancy**
instead of treating a cabin mate as a breathing-zone contact for all ~24
epochs/day regardless of actual co-presence — the structural defect the
QUAR-ATTR-V2 readout isolated: under enforced cabin confinement the mate's
near-field weight stayed 1.0 and the full pool-share addback ran every
epoch, which is the mechanism that drove confined-pair attack to ~100%
while the held-out literature band (Pluciński 2020: 18%/63%/81% for DP
cabinmates; Wikswo 2011: noro 15.4%; Chimonas 2008: 24.1%) sits far below
saturation. Those attack rates remain a held-out check on this change's
λ instrument, never a fitting target — no constant in this change was
chosen to hit them.

Mechanics (`transmission.cabin_cooccupancy`, default `"time_partitioned"`;
`"off"` kept as the labelled bit-identical baseline for paired-seed
attribution):

- Per epoch, a cabin-mate pair's co-presence `c` is read off agent state:
  a member is present for its share of the epoch — `1.0` while `Sleep`
  occupies the scheduled block; while awake and **confined**, present for
  `1 − confined_absence_hours_per_day/awake_hours`
  (`confined_absence_hours_per_day` default 1.0 h, DP news-record deck
  relief, Grade C declared axis, admissible band [0, 8]). Outside
  confinement, zone occupancy already resolves absence — an agent simply
  is not in the cabin block — so the partition only reshapes *confined*
  pairs.
- The near-field plume weight on the mate path is `c × plume_share` with
  `plume_share` = `sleep_plume_share` (0.5) when both are asleep and
  `awake_plume_share` (0.4) otherwise — a sleeping pair faces each other's
  breathing zone only part of the epoch.
- The cabin-mate pool-share addback multiplies by the pair's copresence —
  a shedder emits to the stateroom air only while inside it, and a mate
  breathes it only while inside it.
- The confined-pair direct-contact factor gates identically: `c ×
  asleep_contact_share` (default 0.0 — sleeping berth-mates do not touch)
  when both asleep, `c × 1.0` awake.
- Pool, fomite, emesis and flush channels are unchanged: shared air and
  surfaces are genuinely shared during co-presence.

No shared-stream draws were added: presence, copresence and state shares
are deterministic functions of schedule tokens and the quarantine set, so
`"off"` vs `"time_partitioned"` differ only in dose, and the paired-seed
RNG-stream-disruption caveat does not apply to this move.

Measurement instrument: `CabinPairChallengeLedger` +
`cabin_pair_challenge_table` in `tools/covid_route_attribution.py` tally
the compartment-channel dose each cabin-mate pair exchanges (droplet
pool/plume split, contact, hvac, emesis, flush) and report per-pair
λ = susceptibility × Σdose with the host's persistent frailty draw —
counterfactual draws on a labelled separate stream for hosts whose engine
challenge never fired (the per_host_dose_challenge convention). The
observed mate-case attack is the household-SAR analogue: one index by
convention, secondaries/(members−1) among pairs where a member carried a
pair pathogen. `tools/noro_diag/cabin_pair_challenge_probe.py` drives the
same instrument on the classic_cruise_1900 voyage at the norovirus paired
seeds 8105/8106.

**Readout** (paired seeds, `time_partitioned` + `first_order` defaults):

Diamond Princess replay, `covid_quarantine_attribution_v1` arm
`A0_declared`, Θ 1e9 — confined-cabinmate check against the held-out
Pluciński 2020 band (18% asymptomatic-index, 63%/81% cabinmate):

| seed | confined pairs w/ index | median λ (confined) | implied SAR median | observed confined mate attack |
|------|------------------------|---------------------|--------------------|-------------------------------|
| 20200205 | 77 | 1.99 | 0.864 | 0.492 |
| 20200206 | 31 | 1.17 | 0.688 | 0.391 |

The observed confined-window mate attack — secondaries among mates who
entered confinement uninfected — lands at 39–49%, inside the held-out
18–81% band; the pre-change mechanism drove it to ~100%. The λ median is
hazard rate, not probability: at Θ 1e9 (the composite-fit scale) the
theta-scaled frailty tail keeps implied SAR hot, which is the fit's
quantity, not this sub-model's geometry.

Classic-cruise voyage, `cabin_pair_challenge_probe`, norwalk_gi +
influenza_a boarding, paired seeds 8105/8106: norwalk_gi's compartment
channel is a structural null (no continuous droplet emission), so the
confined-pair λ rows for noro carry sub-copy doses — implied SAR max
~1e-4, inside the Wikswo/Chimonas ≤24% bound trivially. The
any-pathogen confined-window mate attack reads 31.4%/27.4% — driven by
the influenza co-boarding, not the noro channel.
