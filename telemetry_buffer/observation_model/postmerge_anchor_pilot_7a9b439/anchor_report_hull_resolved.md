# Literature anchor scoring

Conditional on take-off (peak prevalence >= 10). Ratios are per-seed medians; the ratio-of-medians is given alongside because the two diverge when a denominator is small. Targets and definitions: `anchor_measurement_spec.md`.

| Hull | Response | Dose | Takeoff | A1 ever-ill | inf AR (pax) | A2 ill/inf | A3 rep/ill | A4 reported | A5 pax/crew | Verdicts |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---|
| classic_cruise_1900 | none_response | 2.0 | 10/10 | 0.1783 | 0.7941 | 0.224 (0.224) | 0.199 (0.218) | 0.0388 | 1.11 (1.14) | FAIL: A2,A3,A4,A5 |
| classic_cruise_1900 | none_response | 2.5 | 10/10 | 0.0571 | 0.6977 | 0.101 (0.082) | 0.254 (0.229) | 0.0131 | 1.48 (1.36) | FAIL: A1,A2,A3,A4,A5 |
| classic_cruise_1900 | none_response | 3.0 | 8/10 | 0.0482 | 0.5982 | 0.090 (0.081) | 0.244 (0.217) | 0.0104 | 0.84 (0.75) | FAIL: A1,A2,A3,A4,A5 |
| classic_cruise_1900 | syndromic_comp85 | 2.0 | 9/10 | 0.0105 | 0.5037 | 0.070 (0.021) | 0.540 (1.000) | 0.0105 | 0.43 (0.29) | FAIL: A1,A2,A3,A4,A5 |
| classic_cruise_1900 | syndromic_comp85 | 2.5 | 9/10 | 0.0030 | 0.0314 | 0.073 (0.096) | 0.733 (0.733) | 0.0022 | 0.41 (0.63) | FAIL: A1,A2,A3,A4,A5 |
| classic_cruise_1900 | syndromic_comp85 | 3.0 | 6/10 | 0.0157 | 0.1875 | 0.074 (0.083) | 1.000 (1.000) | 0.0157 | 1.24 (1.79) | FAIL: A1,A2,A3,A4,A5 |
| expedition_cruise_450 | none_response | 2.0 | 10/10 | 0.2152 | 0.7974 | 0.264 (0.270) | 0.280 (0.280) | 0.0602 | 1.14 (1.79) | FAIL: A2,A3,A5 |
| expedition_cruise_450 | none_response | 2.5 | 10/10 | 0.1202 | 0.7358 | 0.187 (0.163) | 0.312 (0.316) | 0.0380 | 1.69 (2.04) | FAIL: A2,A3,A4,A5 |
| expedition_cruise_450 | none_response | 3.0 | 8/10 | 0.0649 | 0.4889 | 0.131 (0.133) | 0.292 (0.293) | 0.0190 | 1.55 (1.28) | FAIL: A1,A2,A3,A4,A5 |
| expedition_cruise_450 | syndromic_comp85 | 2.0 | 5/10 | 0.2057 | 0.7247 | 0.264 (0.284) | 0.283 (0.262) | 0.0538 | 1.44 (1.44) | FAIL: A2,A3,A5 |
| expedition_cruise_450 | syndromic_comp85 | 2.5 | 3/10 | 0.0665 | 0.3892 | 0.236 (0.171) | 0.621 (0.286) | 0.0190 | 1.53 (-) | FAIL: A1,A2,A3,A4,A5 |
| expedition_cruise_450 | syndromic_comp85 | 3.0 | 4/10 | 0.0332 | 0.2943 | 0.138 (0.113) | 0.671 (0.619) | 0.0205 | 1.04 (1.10) | FAIL: A1,A2,A3,A4,A5 |

## Undefined ratios (zero denominators, excluded)

- classic_cruise_1900 / none_response / 2.0: A5_passenger_crew_ratio=1
- classic_cruise_1900 / none_response / 2.5: A5_passenger_crew_ratio=2
- classic_cruise_1900 / syndromic_comp85 / 2.0: A5_passenger_crew_ratio=2
- classic_cruise_1900 / syndromic_comp85 / 2.5: A5_passenger_crew_ratio=2
- expedition_cruise_450 / none_response / 2.0: A5_passenger_crew_ratio=1
- expedition_cruise_450 / none_response / 2.5: A5_passenger_crew_ratio=2
- expedition_cruise_450 / none_response / 3.0: A5_passenger_crew_ratio=2
- expedition_cruise_450 / syndromic_comp85 / 2.5: A5_passenger_crew_ratio=2
- expedition_cruise_450 / syndromic_comp85 / 3.0: A5_passenger_crew_ratio=2
