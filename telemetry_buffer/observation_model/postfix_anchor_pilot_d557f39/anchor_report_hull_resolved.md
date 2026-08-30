# Literature anchor scoring

Conditional on take-off (peak prevalence >= 10). Ratios are per-seed medians; the ratio-of-medians is given alongside because the two diverge when a denominator is small. Targets and definitions: `anchor_measurement_spec.md`.

| Hull | Response | Dose | Takeoff | A1 ever-ill | inf AR (pax) | A2 ill/inf | A3 rep/ill | A4 reported | A5 pax/crew | Verdicts |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---|
| classic_cruise_1900 | none_response | 2.0 | 9/10 | 0.1622 | 0.4649 | 0.364 (0.349) | 0.216 (0.240) | 0.0389 | 0.85 (1.01) | FAIL: A2,A3,A4,A5 |
| classic_cruise_1900 | none_response | 2.5 | 9/10 | 0.0516 | 0.3303 | 0.186 (0.156) | 0.260 (0.262) | 0.0135 | 1.28 (0.96) | FAIL: A1,A2,A3,A4,A5 |
| classic_cruise_1900 | none_response | 3.0 | 9/10 | 0.0187 | 0.2048 | 0.179 (0.091) | 0.247 (0.241) | 0.0045 | 0.53 (0.52) | FAIL: A1,A2,A3,A4,A5 |
| classic_cruise_1900 | syndromic_comp85 | 2.0 | 8/10 | 0.0030 | 0.0938 | 0.054 (0.031) | 0.302 (0.373) | 0.0011 | 0.25 (0.21) | FAIL: A1,A2,A3,A4,A5 |
| classic_cruise_1900 | syndromic_comp85 | 2.5 | 6/10 | 0.0015 | 0.0426 | 0.087 (0.035) | 0.358 (0.733) | 0.0011 | 0.98 (0.42) | FAIL: A1,A2,A4,A5 |
| classic_cruise_1900 | syndromic_comp85 | 3.0 | 5/10 | 0.0060 | 0.0396 | 0.166 (0.152) | 0.975 (0.250) | 0.0015 | 1.18 (-) | FAIL: A1,A2,A3,A4,A5 |
| expedition_cruise_450 | none_response | 2.0 | 8/10 | 0.1487 | 0.4067 | 0.341 (0.366) | 0.259 (0.234) | 0.0348 | 0.97 (1.17) | FAIL: A2,A3,A4,A5 |
| expedition_cruise_450 | none_response | 2.5 | 9/10 | 0.0759 | 0.3196 | 0.237 (0.237) | 0.291 (0.250) | 0.0190 | 0.81 (1.28) | FAIL: A1,A2,A3,A4,A5 |
| expedition_cruise_450 | none_response | 3.0 | 6/10 | 0.0379 | 0.1946 | 0.196 (0.195) | 0.377 (0.458) | 0.0174 | 1.27 (2.32) | FAIL: A1,A2,A4,A5 |
| expedition_cruise_450 | syndromic_comp85 | 2.0 | 7/10 | 0.1392 | 0.2880 | 0.360 (0.483) | 0.508 (0.386) | 0.0538 | 1.69 (3.61) | FAIL: A2,A3,A5 |
| expedition_cruise_450 | syndromic_comp85 | 2.5 | 4/10 | 0.0332 | 0.1661 | 0.185 (0.200) | 0.900 (0.715) | 0.0238 | 1.48 (1.59) | FAIL: A1,A2,A3,A4,A5 |
| expedition_cruise_450 | syndromic_comp85 | 3.0 | 4/10 | 0.0538 | 0.1930 | 0.327 (0.279) | 0.814 (0.882) | 0.0474 | 2.03 (1.81) | FAIL: A1,A2,A3,A5 |

## Undefined ratios (zero denominators, excluded)

- classic_cruise_1900 / none_response / 2.5: A5_passenger_crew_ratio=2
- classic_cruise_1900 / none_response / 3.0: A5_passenger_crew_ratio=2
- classic_cruise_1900 / syndromic_comp85 / 2.0: A5_passenger_crew_ratio=2
- classic_cruise_1900 / syndromic_comp85 / 2.5: A5_passenger_crew_ratio=2
- classic_cruise_1900 / syndromic_comp85 / 3.0: A5_passenger_crew_ratio=3
- expedition_cruise_450 / none_response / 2.0: A5_passenger_crew_ratio=1
- expedition_cruise_450 / none_response / 2.5: A5_passenger_crew_ratio=3
- expedition_cruise_450 / none_response / 3.0: A5_passenger_crew_ratio=1
- expedition_cruise_450 / syndromic_comp85 / 2.0: A5_passenger_crew_ratio=1
- expedition_cruise_450 / syndromic_comp85 / 2.5: A5_passenger_crew_ratio=1

