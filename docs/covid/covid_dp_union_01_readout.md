# DP-UNION-01 — pilot and canary readout

> **Status:** measured, provisional (20 of 24 seeds at one θ; 5-seed pilot
> rows elsewhere). No final consistency verdict exists. The array has not
> run; that decision is Benjamin's.

**Measured at:** c7f7f927 (image
`picard-campaign@sha256:0d01dae0f057770933b610346604875f05bf0fcd62b6f06145e5c19efeb049aa`,
job definition `picard-covid-dp-union-01` revisions 1–7). Readout code and
selected grid at c8b7315d. Machine-readable:
`docs/covid/dp_union_01_readout.json`. Cells:
`s3://crusherbucket-994254241749-us-east-1-an/campaign/covid_dp_union_01/`.
Design: `docs/covid/covid_dp_union_01_design.md`.

All 50 cells succeeded and none shows an audit
deviation.

## Pilot (5 seeds 20200205–20200209 per decade, T3 side only)

| θ | P31 per seed | median P31 (target 634) | median secondaries | seeds with ≥10 founders |
|---|---|---|---|---|
| 1e5 | 0, 0, 0, 0, 0 | 0 | 0 | 0 |
| 1e6 | 0, 0, 0, 0, 0 | 0 | 0 | 0 |
| 1e7 | 589, 107, 0, 0, 0 | 0 | 1 | 0 |
| 1e8 | 716, 494, 815, 314, 0 | 494 | 2,444 | 0 |
| 1e9 | 747, 886, 887, 843, 879 | 879 | 3,289 | 1 |
| 1e10 | 490, 951, 400, 625, 896 | 625 | 3,445 | 2 |

By the rule frozen before the pilot: θ_lo = 1e8, θ_hi = 1e9, scored grid
{1e8, 3.16e8, 1e9, 3.16e9}, canary at 3.16e8. The 1e10 median falls back
below 634 while its attack rate is the highest of the pilot (0.93); by the
rule this is reported and does not move the grid. Why P31 drops there is
not investigated.

## Canary (θ = 3.16e8, seeds 20200205–20200224, 20 of 20)

**The scored row does not exist.** One seed of 20 (20200205, 13 founders)
is in the founder class; the contract needs five. Every leg's verdict is
"insufficient class mass". Not dead (7 of 20 seeds have P31 = 0; the edge
needs 20 of 24), not saturated.

Reported only — not the scored contract:

| Leg | Record | Takeoff class (13 seeds) | All seeds (20) |
|---|---|---|---|
| Ignition day (≤ 9) | — | 13 | 15 (7 never ignite) |
| `before_share` (0.173 ± 0.10) | 0.173 | 0.004 | 0.004 |
| Attack, secondaries [712, 960] | 712 | 3,124 | 2,598.5 |
| During-quarantine [150, 350] | — | 1,919 | 725.5 |
| Conditioned capture (≥ 0.80) | — | 0.887 | 0.823 |
| T3, P31 vs 634 | 634 | 793, compatible (9 above, 4 below) | 622.5, compatible (9 above, 11 below) |
| Onboard table, P34 vs 691 | 691 | 830, compatible | 659, compatible |

- **Outcomes are bimodal.** Seven seeds produce no secondary infection at
  all. Of the other 13, eleven infect 2,198–3,268 of 3,710, one 1,367 and
  one 946. Only that last seed (20200208) lies in the attack band.
- **T3 is compatible while attack is 3–4× the band.** On the takeoff
  class the testing legs sit near the record and the attack, during and
  timing legs do not. This is one θ; whether a lower θ brings attack into
  the band on taken-off seeds without losing T3 is what the array would
  measure. In the pilot, 1e7 already shows 2,553 secondaries on one seed
  and extinction on three (5 seeds — hypothesis).
- **Founder class is nearly empty at every θ run.** Median founder yield
  is 1 at the canary; the largest class mass anywhere is 2 of 5 seeds
  (1e10). The one founder-class canary seed ignites on day 8; the takeoff
  median is day 13.
- **Crew wave under-fills when attack is high.** Median specimens through
  day 34 is 3,353 against the record's 3,894. Seeds with no outbreak draw
  the full 831 wave specimens (3,894 total); seeds with outbreaks draw
  fewer (266 and 256 on two pilot seeds at 1e8). Confirmed hosts are not
  re-swabbed. The 3,894 denominator is therefore not reproduced on
  taken-off seeds.
- **`machinery_gap_seeds` lists the seven extinct seeds.** Each has one
  reachable infection — the index — and zero positives. No seed with a secondary infection has zero positives, so
  this is not a testing-machinery gap; the flag should exclude the index.

## What this does and does not establish

- Measured: the canary numbers above (20 seeds, one θ) and the pilot T3
  sides (5 seeds per decade).
- Not established: any pass or fail of the frozen contract — the scored
  class has no row. A "leg fails at every run θ" claim would need the
  array.
- Hypothesis: the founder-conditioned contract cannot be scored on this
  arm at any θ in the lattice, because index-driven founder yield ≥ 10 is
  rare (1 of 20 here). If it holds on the array, the conditioning class,
  not θ, is the binding constraint; that points at Suite 2 (index
  participation) rather than more θ.

## Open decision

Whether the array runs: the remaining 4 seeds at 3.16e8 and 24 seeds at
1e8, 1e9 and 3.16e9 (5 pilot seeds already exist at 1e8 and 1e9), 66
cells. On the canary evidence it would most likely return "insufficient
class mass" at every θ.
