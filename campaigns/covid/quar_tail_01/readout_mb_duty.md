# QUAR-TAIL-SEAM-01 readout

- source: `/tmp/qt_mb_duty/t8p50_mb_duty`
- design: `picard_framework/runs/covid_quar_tail_01_design.json`
- coverage: 20/80 cells (partial: True)
- audit invariants: 0 violation(s)

| theta | arm | n | takeoff | during med (all) | during med (takeoff) | capture med (takeoff) | before med | Δbefore med / max abs | crew share | realized exempt | duty excluded med | min deliveries | verdict |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 3.16228e+08 | MB_DUTY | 20 | 15 | 302.5 | 425.0 | 0.519 | 53.5 | None / None | 0.669 | 0.316 | 168.000 | 191052 | UNDER-DAMPED |

## Baseline trajectory clause (D0, takeoff seeds)


Record-informed band (150.0, 350.0); capture rise criterion >= 0.8 (record ~0.85, committed D0 pooled 0.723 / median 0.525); record crew share 0.29 (whole-voyage confirmed basis — direction, not magnitude). UNMOVED reach echoes audited before the median read.

## Audit-invariant violations

- none

## Report flags

- none

## Committed dp_theta_8p50 drift witness


## MB_DUTY vs committed dp_theta_8p50 — seed-paired deltas

| seed | Δbefore | Δduring | off-duty at end |
|---|---|---|---|
| 20200205 | 6 | 146 | 208 |
| 20200206 | 0 | 0 | 17 |
| 20200207 | 38 | 61 | 173 |
| 20200208 | 1 | -78 | 152 |
| 20200209 | 0 | 0 | 0 |
| 20200210 | 33 | 46 | 192 |
| 20200211 | 0 | 0 | 0 |
| 20200212 | 498 | -209 | 60 |
| 20200213 | 0 | -114 | 136 |
| 20200214 | 0 | -42 | 127 |
| 20200215 | 0 | 134 | 203 |
| 20200216 | 0 | -18 | 45 |
| 20200217 | 0 | 0 | 0 |
| 20200218 | 0 | 74 | 152 |
| 20200219 | 52 | -9 | 210 |
| 20200220 | 0 | 24 | 163 |
| 20200221 | 0 | -133 | 80 |
| 20200222 | -442 | 269 | 74 |
| 20200223 | 0 | -52 | 1 |
| 20200224 | -78 | -483 | 17 |

Committed baseline synced from s3://crusherbucket-994254241749-us-east-1-an/campaign/covid_theta_refit_01/dp_theta_8p50/ (20 cells).
