# PLATFORM-FIDELITY-01B
**Date:** 2026-11-08
**Commit:** 7d79b7d0
**Pathogens:** sars_cov2_resp
**Status:** measured
**Measured at:** 7d79b7d0

Cells ran on image
`picard-campaign:covid-platform-fidelity-01b@sha256:ed4700c6ce9a8b47b66fbba4e7a2f54b36e12a218504259fa3c614511e52bdfc`,
built at `7d79b7d0` (root `Dockerfile` + `deploy/aws/Dockerfile.campaign`
overlay).

PLATFORM-FIDELITY-01b is the DP-only corrective rerun of
PLATFORM-FIDELITY-01's Diamond Princess pair, authorized by the addendum
`docs/covid/covid_platform_fidelity_01b_addendum.md` (merged in #1182)
after the PF-01 DP row was found confounded: the frozen PF-01 DP protocols
file declared 11 `exempt_work_zones`, all `mega_cruise_5000` IDs, of which
the event-faithful `diamond_princess` hull carries only `Bridge`, so the
dedicated arm quarantined ~318 more crew than the proxy arm (working crew
at activation 10–21 vs 295–368 of 1045). The PF-01 DP cells are preserved
and marked confounded/superseded for hull-fidelity inference; they remain
evidence of a zone-name-dependent intervention defect. GM is untouched.

The repair maps essential workplaces by function to each hull's native
zone IDs (galley, engineering/waste, bridge, stores, laundry, crew-mess
operations; 17-ID union in `data/config/protocols_covid_pf_dp_01b.json`,
hull IDs kept real, list not tuned to any count) and reruns ONLY the 20
dedicated cells (Θ 7.9e6, seeds 20200205–20200224, frozen). The 20 PF-01
proxy cells are reused as the baseline on proven behavioral equivalence
(addendum §3: union list inert on the proxy per-seed at init, and one full
local proxy cell bit-identical in every epidemiological field to its PF-01
payload). Campaign `campaigns/covid/platform_fidelity_01b/`: 20/20 cells,
0 technical failures, witness audit clean (working crew 98–135 at
activation, posted zones ⊆ the 7 hull-native essential IDs, boxed service
active, `SOP-017-MESSBOX` fired, no `close_zones`).

Corrected DP contrast (readout
`docs/covid/covid_platform_fidelity_readout.md` §01b; q05–q95 are seedwise
spreads, NOT confidence intervals; unconditional burden reported alongside
the takeoff-conditional endpoint):

- P(takeoff): proxy 0.50 vs dedicated 0.30 (n = 20 each).
- Takeoff-conditional paired Δ onsets (n = 5 both-takeoff seeds): median
  +114, q05–q95 [−66.6, +358.6] — the spread includes zero; no platform
  equivalence is concluded from that.
- Unconditional onset burden (all 20 seeds): median 12.5 (proxy) vs 2.0
  (dedicated); totals 1103 vs 1457.
- Takeoff-conditional asymptomatic share: 0.367 (proxy) vs 0.427
  (dedicated). CRN ρ = −0.137 → unpaired analysis declared.

With the intervention repaired, the dedicated Diamond Princess hull shows
a LOWER takeoff probability but LARGER outbreaks when takeoff occurs —
the same directional pattern PF-01's confounded row hinted at (dedicated
conditional median 243 vs 64), now measured under the same effective
quarantine policy on both hulls. At n = 20 seeds/arm the contrast remains
unresolved by the frozen criteria; no platform is selected, no Θ refit,
the train/test split untouched.
