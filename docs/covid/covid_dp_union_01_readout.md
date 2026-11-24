# DP-UNION-01 — pilot, canary and staged-array readout

> **Status:** measured. Two of four scored θ are complete (24 seeds at 1e9
> and 3.16e9); 3.16e8 has 20 of 24 and 1e8 has 5. No joint verdict exists
> (it needs every scored θ). The array was staged from 3.16e9 by the rule
> in the design; the two lower cells are Benjamin's decision.

**Measured at:** c7f7f927 (image
`picard-campaign@sha256:0d01dae0f057770933b610346604875f05bf0fcd62b6f06145e5c19efeb049aa`,
job definition `picard-covid-dp-union-01` revisions 1–11). Readout code and
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
  and at most one secondary on three (5 seeds —
  hypothesis).
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

## Staged array (θ = 3.16e9 and 1e9, seeds 20200205–20200228, 24 of 24 each)

Staging rule committed at 11b759e8 before any array cell: 3.16e9 first;
fewer than 5 founder-class seeds stops the array; 5 or more runs 1e9.
Same image digest. No audit deviation on either row. Neither row is dead
or saturated; the representativeness flag is not set.

**3.16e9: the row is scored (7 founder-class seeds).**

| Leg | Target | Founder class (7), scored | Takeoff class (21) | All 24 |
|---|---|---|---|---|
| Ignition day | ≤ 9 | 7, pass | 10 | 10.5 (3 never ignite) |
| `before_share` | 0.173 ± 0.10 | 0.637, fail | 0.094 | 0.094 |
| Attack (secondaries) | 712–960 | 3,452, fail | 3,383 | 3,373 |
| During-quarantine | 150–350 | 112, fail | 992 | 658 |
| Conditioned capture | ≥ 0.80 | 0.964, pass | 0.961 | 0.956 |
| T3 (P31) | 634 | 663, compatible (5 above, 2 below) | 859, above | 811.5, above |
| Onboard table (P34) | 691 | 663, compatible (2 above, 5 below) | 870, compatible | 819, compatible |

Not consistent: `before_share`, attack and during fail. 3 seeds have no
secondary infection; 20 of the other 21 infect 3,341–3,474 of 3,710 and
one infects 2,452. Median specimens through day 34: 3,177 against 3,894.

**1e9: no scored row (4 founder-class seeds; 5 needed).** Every leg reads
"insufficient class mass". Reported only:

| Leg | Target | Founder class (4), not scored | Takeoff class (18) | All 24 |
|---|---|---|---|---|
| Ignition day | ≤ 9 | 8 | 12 | 13 (6 never ignite) |
| `before_share` | 0.173 ± 0.10 | 0.502 | 0.034 | 0.034 |
| Attack (secondaries) | 712–960 | 3,347 | 3,288 | 3,280 |
| During-quarantine | 150–350 | 219.5 | 1,755 | 1,342 |
| Conditioned capture | ≥ 0.80 | 0.961 | 0.937 | 0.911 |
| T3 (P31) | 634 | 697 | 857, above | 758, compatible |
| Onboard table (P34) | 691 | 700.5 | 887, above | 762, compatible |

6 seeds have no secondary infection; the other 18 infect 2,419–3,411.

Founder-class seeds by θ: 1 of 20 at 3.16e8, 4 of 24 at 1e9, 7 of 24 at
3.16e9.

## What this does and does not establish

- Measured: one scored row (3.16e9, 24 seeds, 7 in class) that fails
  three legs; one complete unscored row (1e9); the 20-seed canary; the
  pilot T3 sides.
- Withdrawn: the canary hypothesis that the founder class cannot be
  scored anywhere on the grid. It is scored at 3.16e9.
- Attack fails high in every class at every θ that has an outbreak
  (3.16e8, 1e9, 3.16e9; also the 5-seed pilot at 1e8, median 2,444).
  Outbreak seeds infect about 90% of the ship or go extinct; no run θ
  gives a median inside 712–960. The 1e8 row is 5 seeds, so "fails at
  every scored θ" is measured on three of four.
- The two timing legs pass on different classes at 3.16e9: ignition on
  the founder class, `before_share` on the takeoff class and all seeds.
  Only the founder class is scored.
- Not established: a joint verdict (two scored θ incomplete), and whether
  1e8 or 3.16e8 can be scored at 24 seeds. With 1 of 20 at 3.16e8 and 4
  of 24 at 1e9, they would most likely read "insufficient class mass"
  (inference).

## Open decision

Whether the two lower cells run: 19 seeds at 1e8 and 4 at 3.16e8, 23
cells. They would complete the grid and so allow the joint verdict to be
computed, but are unlikely to add a scored row.
