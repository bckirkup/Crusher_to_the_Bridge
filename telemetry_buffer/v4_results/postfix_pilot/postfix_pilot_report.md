# Post-confinement-fix ladder pilot

Executed on confinement branch commit `9d06492`.

| Hull | Branch | Dose | Takeoff | Reported median (takeoff) | Q1-Q3 | Ever-ill median (takeoff) | Attack median (takeoff) | Reported/ever-ill | Quarantine PE median | Peak median |
|---|---|---:|---:|---:|---|---:|---:|---:|---:|---:|
| classic_cruise_1900 | none_response | 2 | 10/10 | 0.0258 | 0.01325–0.04125 | 0.19915 | 0.7995 | 0.129551 | 0 | 1525.5 |
| classic_cruise_1900 | none_response | 2.5 | 10/10 | 0.0105 | 0.003525–0.022425 | 0.0841 | 0.70625 | 0.124851 | 0 | 1348.5 |
| classic_cruise_1900 | none_response | 3 | 9/10 | 0.0082 | 0.0037–0.0142 | 0.0643 | 0.5691 | 0.127135 | 0 | 1063 |
| classic_cruise_1900 | syndromic_comp85 | 2 | 9/10 | 0.012 | 0.0007–0.0546 | 0.0127 | 0.4691 | 0.930876 | 1293 | 693 |
| classic_cruise_1900 | syndromic_comp85 | 2.5 | 7/10 | 0.0022 | 0.00035–0.03695 | 0.006 | 0.0853 | 0.378378 | 396 | 43 |
| classic_cruise_1900 | syndromic_comp85 | 3 | 6/10 | 0.00185 | 0.000175–0.037725 | 0.0138 | 0.19945 | 0.233333 | 350.5 | 24.5 |
| expedition_cruise_450 | none_response | 2 | 10/10 | 0.0364 | 0.022975–0.05935 | 0.21675 | 0.79445 | 0.167935 | 0 | 357 |
| expedition_cruise_450 | none_response | 2.5 | 10/10 | 0.0174 | 0.001575–0.038 | 0.11865 | 0.63775 | 0.14665 | 0 | 285.5 |
| expedition_cruise_450 | none_response | 3 | 8/10 | 0.01425 | 0–0.021375 | 0.0886 | 0.52 | 0.12537 | 0 | 171.5 |
| expedition_cruise_450 | syndromic_comp85 | 2 | 6/10 | 0.0459 | 0.038–0.0538 | 0.1788 | 0.60335 | 0.526622 | 1258 | 174.5 |
| expedition_cruise_450 | syndromic_comp85 | 2.5 | 4/10 | 0.0079 | 0.005525–0.016625 | 0.03005 | 0.1911 | 0 | 318.5 | 2.5 |
| expedition_cruise_450 | syndromic_comp85 | 3 | 4/10 | 0.0063 | 0.004725–0.017375 | 0.02215 | 0.26 | 0 | 316.5 | 3 |

## Requested answers

### Ladder
- expedition_cruise_450: VSP median 0.0856; first crossing dose None.
- classic_cruise_1900: VSP median 0.0559; first crossing dose None.

### Containment

- expedition_cruise_450 dose 2: paired ever-ill reduction median 0.10765 (0.563421 relative).
- expedition_cruise_450 dose 2.5: paired ever-ill reduction median 0.1076 (0.872089 relative).
- expedition_cruise_450 dose 3: paired ever-ill reduction median 0.02375 (0.826662 relative).
- classic_cruise_1900 dose 2: paired ever-ill reduction median 0.14235 (0.905713 relative).
- classic_cruise_1900 dose 2.5: paired ever-ill reduction median 0.0606 (0.7375 relative).
- classic_cruise_1900 dose 3: paired ever-ill reduction median 0.04415 (0.846848 relative).

### Surveillance capture

- classic_cruise_1900 dose 2: ratio of medians 0.930876; median per-seed ratio 0.414966.
- classic_cruise_1900 dose 2.5: ratio of medians 0.378378; median per-seed ratio 0.342424.
- classic_cruise_1900 dose 3: ratio of medians 0.233333; median per-seed ratio 0.0590551.
- expedition_cruise_450 dose 2: ratio of medians 0.526622; median per-seed ratio 0.229001.
- expedition_cruise_450 dose 2.5: ratio of medians 0; median per-seed ratio 0.
- expedition_cruise_450 dose 3: ratio of medians 0; median per-seed ratio 0.
