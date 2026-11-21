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

