# covid_seed_ring_02 readout — s3://crusherbucket-994254241749-us-east-1-an/campaign/covid_seed_ring_02/

## Campaign verdict: **NULL-WINDOW — leg 1 fails at alpha=8; the founder channel is narrower than voyage-stage mixing (Arm-B continuation)**

## Arm legs

- WINDOW_W1_A8@3.16228e+08: **leg1 fail / leg2 fail** — n=20 (takeoff 17); founder median 4.000 takeoff-conditional (3.000 all cells); ignition median 13.000 (ignited 17/17); record-timed 6 cells, d15 median 2404.000 vs <= 960; routes {'caregiver': 38, 'droplet': 207}
  trajectory: recorded_onsets q05-q95 86-2628 (record 197), before_share median 0.062 (record 0.173) -> outside the clause

### WINDOW_W1_A8@3.16228e+08 — per-cell

| seed | founders | clean | d0 | routes | ign | takeoff | d15 | onsets | before_share | voyage |
|---|---|---|---|---|---|---|---|---|---|---|
| 20200205 | 1 | 1 | 1 | caregiver:1 | - | no | 1 | 0 | n/a | eff:True a:8.0 |
| 20200206 | 2 | 2 | 0 | droplet:1,caregiver:1 | 9 | yes | 653 | 1220 | 0.108 | eff:True a:8.0 |
| 20200207 | 4 | 3 | 1 | caregiver:2,droplet:2 | 23 | yes | 12 | 142 | 0.021 | eff:True a:8.0 |
| 20200208 | 60 | 31 | 40 | caregiver:2,droplet:58 | 3 | yes | 3015 | 2653 | 0.658 | eff:True a:8.0 |
| 20200209 | 2 | 1 | 1 | droplet:1,caregiver:1 | 22 | yes | 8 | 113 | 0.027 | eff:True a:8.0 |
| 20200210 | 2 | 2 | 1 | caregiver:2 | 22 | yes | 10 | 145 | 0.028 | eff:True a:8.0 |
| 20200211 | 1 | 1 | 1 | caregiver:1 | - | no | 1 | 0 | n/a | eff:True a:8.0 |
| 20200212 | 41 | 15 | 19 | droplet:40,caregiver:1 | 5 | yes | 2918 | 2622 | 0.584 | eff:True a:8.0 |
| 20200213 | 2 | 2 | 0 | droplet:1,caregiver:1 | 25 | yes | 12 | 91 | 0.011 | eff:True a:8.0 |
| 20200214 | 2 | 2 | 1 | droplet:1,caregiver:1 | 21 | yes | 22 | 133 | 0.045 | eff:True a:8.0 |
| 20200215 | 3 | 1 | 1 | caregiver:3 | 13 | yes | 184 | 589 | 0.034 | eff:True a:8.0 |
| 20200216 | 5 | 2 | 0 | caregiver:2,droplet:3 | 13 | yes | 131 | 388 | 0.062 | eff:True a:8.0 |
| 20200217 | 0 | 0 | 0 | - | - | no | 0 | 0 | n/a | eff:True a:8.0 |
| 20200218 | 3 | 3 | 1 | droplet:1,caregiver:2 | 17 | yes | 34 | 240 | 0.029 | eff:True a:8.0 |
| 20200219 | 56 | 12 | 41 | droplet:52,caregiver:4 | 4 | yes | 2654 | 2525 | 0.471 | eff:True a:8.0 |
| 20200220 | 23 | 3 | 3 | droplet:20,caregiver:3 | 9 | yes | 706 | 1274 | 0.151 | eff:True a:8.0 |
| 20200221 | 5 | 0 | 0 | caregiver:4,droplet:1 | 12 | yes | 123 | 450 | 0.067 | eff:True a:8.0 |
| 20200222 | 21 | 6 | 5 | droplet:18,caregiver:3 | 8 | yes | 2154 | 2342 | 0.325 | eff:True a:8.0 |
| 20200223 | 10 | 4 | 4 | droplet:6,caregiver:4 | 13 | yes | 293 | 663 | 0.107 | eff:True a:8.0 |
| 20200224 | 2 | 2 | 2 | droplet:2 | 27 | yes | 4 | 67 | 0.015 | eff:True a:8.0 |


Frozen legs: leg 1 founder median >= 10 AND ignition median <= 9 (takeoff cells); leg 2 d15 cumulative infections median <= 960 on record-timed cells (ign <= 9). Min takeoff 5 cells. Grammar: WINDOW-LANDED / FOUNDERS-ONLY / SPLIT-STAGE / NULL-WINDOW.

## Audit-invariant violations

- none

## Report flags

- none

## Committed dp_theta_8p50 drift witness

- skipped (--no-refit)
