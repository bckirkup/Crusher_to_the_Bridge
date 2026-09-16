# Which decade of the flush aerosol fraction first moves an outcome: stage 1

Posting rule: reported cases >= 3% of passengers or of crew. `f_aero` is each arm's own archived `flush_aerosol_fraction`, read from the run parameters and not from a prefix. `ev. v.` and `rec. v.` count voyages with any emitting flush and any exposure event; `recipients` counts exposure events, not hosts. `dose/exp` is pooled inhaled particles per exposure event, against N50 = 16,871. `sec/import` is pooled secondaries over pooled imports. Every `off` row must show zero flush events: the baseline is the item-42 `dwell_weighted` configuration with the route off.

| platform | days | arm | f_aero | voyages | ev. v. | rec. v. | emitted | recipients | dose/exp | sec/import | mean sec | zero | flush % | fomite % | post/1,000 | posting CI | median pax AR |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| classic_cruise_1900 | 7 | off | 0.00e+00 | 100 | 0 | 0 | 0.00e+00 | 0.0 | n/a | 0.002 | 0.01 | 0.990 | 0.0% | 100.0% | 0.0 | [0.0000, 0.0247] | n/a |
| classic_cruise_1900 | 7 | 1e-9 | 1.00e-09 | 100 | 94 | 93 | 1.74e+05 | 128.4 | 1.59e+00 | 0.004 | 0.02 | 0.980 | 100.0% | 0.0% | 0.0 | [0.0000, 0.0247] | n/a |
| classic_cruise_1900 | 7 | 1e-7 | 1.00e-07 | 100 | 94 | 93 | 1.15e+07 | 142.7 | 1.38e+02 | 0.584 | 2.67 | 0.790 | 30.0% | 70.0% | 0.0 | [0.0000, 0.0247] | n/a |
| classic_cruise_1900 | 7 | 1e-5 | 1.00e-05 | 100 | 94 | 93 | 2.38e+09 | 216.7 | 1.36e+04 | 3.737 | 17.08 | 0.310 | 75.4% | 24.6% | 30.0 | [0.0085, 0.0779] | 0.0314 |
| classic_cruise_1900 | 12 | off | 0.00e+00 | 100 | 0 | 0 | 0.00e+00 | 0.0 | n/a | 0.002 | 0.01 | 0.990 | 0.0% | 100.0% | 0.0 | [0.0000, 0.0247] | n/a |
| classic_cruise_1900 | 12 | 1e-9 | 1.00e-09 | 100 | 95 | 94 | 1.71e+05 | 177.7 | 1.12e+00 | 0.002 | 0.01 | 0.990 | 100.0% | 0.0% | 0.0 | [0.0000, 0.0247] | n/a |
| classic_cruise_1900 | 12 | 1e-7 | 1.00e-07 | 100 | 95 | 94 | 1.34e+07 | 215.4 | 1.13e+02 | 0.481 | 2.20 | 0.780 | 52.3% | 47.7% | 0.0 | [0.0000, 0.0247] | n/a |
| classic_cruise_1900 | 12 | 1e-5 | 1.00e-05 | 100 | 95 | 94 | 2.05e+10 | 603.8 | 4.71e+04 | 13.214 | 60.39 | 0.200 | 69.9% | 29.9% | 190.0 | [0.1225, 0.2751] | 0.0456 |
| expedition_cruise_450 | 7 | off | 0.00e+00 | 100 | 0 | 0 | 0.00e+00 | 0.0 | n/a | 0.167 | 0.17 | 0.980 | 0.0% | 100.0% | 0.0 | [0.0000, 0.0247] | n/a |
| expedition_cruise_450 | 7 | 1e-9 | 1.00e-09 | 100 | 35 | 33 | 2.04e+04 | 6.0 | 1.58e+01 | 0.176 | 0.18 | 0.980 | 5.6% | 94.4% | 0.0 | [0.0000, 0.0247] | n/a |
| expedition_cruise_450 | 7 | 1e-7 | 1.00e-07 | 100 | 35 | 33 | 5.64e+06 | 6.2 | 1.48e+03 | 0.569 | 0.58 | 0.910 | 55.2% | 44.8% | 0.0 | [0.0000, 0.0247] | n/a |
| expedition_cruise_450 | 7 | 1e-5 | 1.00e-05 | 100 | 35 | 33 | 2.66e+08 | 11.3 | 7.70e+04 | 1.892 | 1.93 | 0.820 | 63.9% | 36.1% | 0.0 | [0.0000, 0.0247] | n/a |
| expedition_cruise_450 | 12 | off | 0.00e+00 | 100 | 0 | 0 | 0.00e+00 | 0.0 | n/a | 0.235 | 0.24 | 0.970 | 0.0% | 100.0% | 0.0 | [0.0000, 0.0247] | n/a |
| expedition_cruise_450 | 12 | 1e-9 | 1.00e-09 | 100 | 38 | 35 | 2.09e+04 | 9.4 | 9.73e+00 | 0.186 | 0.19 | 0.970 | 5.3% | 94.7% | 0.0 | [0.0000, 0.0247] | n/a |
| expedition_cruise_450 | 12 | 1e-7 | 1.00e-07 | 100 | 38 | 35 | 7.66e+06 | 10.8 | 9.42e+02 | 0.480 | 0.49 | 0.910 | 63.3% | 36.7% | 0.0 | [0.0000, 0.0247] | n/a |
| expedition_cruise_450 | 12 | 1e-5 | 1.00e-05 | 100 | 38 | 35 | 1.82e+09 | 21.8 | 8.31e+04 | 3.461 | 3.53 | 0.800 | 72.0% | 28.0% | 40.0 | [0.0136, 0.0923] | 0.0364 |
| spirit_cruise_3000 | 7 | off | 0.00e+00 | 100 | 0 | 0 | 0.00e+00 | 0.0 | n/a | 0.242 | 1.61 | 0.880 | 0.0% | 100.0% | 0.0 | [0.0000, 0.0247] | n/a |
| spirit_cruise_3000 | 7 | 1e-9 | 1.00e-09 | 100 | 99 | 97 | 1.26e+05 | 231.6 | 8.14e-01 | 0.135 | 0.90 | 0.800 | 13.3% | 86.7% | 0.0 | [0.0000, 0.0247] | n/a |
| spirit_cruise_3000 | 7 | 1e-7 | 1.00e-07 | 100 | 99 | 97 | 3.17e+07 | 314.6 | 8.43e+01 | 1.271 | 8.45 | 0.390 | 61.1% | 38.9% | 0.0 | [0.0000, 0.0247] | n/a |
| spirit_cruise_3000 | 7 | 1e-5 | 1.00e-05 | 100 | 99 | 97 | 1.53e+10 | 718.5 | 2.22e+04 | 11.385 | 75.71 | 0.130 | 75.4% | 24.6% | 190.0 | [0.1225, 0.2751] | 0.0057 |
| spirit_cruise_3000 | 12 | off | 0.00e+00 | 100 | 0 | 0 | 0.00e+00 | 0.0 | n/a | 0.105 | 0.70 | 0.900 | 0.0% | 100.0% | 0.0 | [0.0000, 0.0247] | n/a |
| spirit_cruise_3000 | 12 | 1e-9 | 1.00e-09 | 100 | 99 | 97 | 1.41e+05 | 313.5 | 4.14e-01 | 0.108 | 0.72 | 0.780 | 19.4% | 80.6% | 0.0 | [0.0000, 0.0247] | n/a |
| spirit_cruise_3000 | 12 | 1e-7 | 1.00e-07 | 100 | 99 | 97 | 7.41e+07 | 524.1 | 1.59e+02 | 2.585 | 17.19 | 0.420 | 51.0% | 48.9% | 30.0 | [0.0085, 0.0779] | 0.0000 |
| spirit_cruise_3000 | 12 | 1e-5 | 1.00e-05 | 100 | 99 | 97 | 9.07e+10 | 1730.2 | 7.67e+04 | 29.462 | 195.92 | 0.120 | 68.8% | 31.2% | 470.0 | [0.3742, 0.5675] | 0.0457 |

## Paired contrasts (arm − off, seed by seed)

`identical imports` must be 1.000: the flush route draws no rng of its own, so a pair whose boarding cohort moved is a leak rather than a result. `gained/lost` are McNemar's discordant postings.

| platform | days | arm | seeds | identical imports | Δ flush exposures | Δ sec/import | × sec/import | Δ secondaries (CI) | Δ flush dominant | Δ margin (CI) | gained/lost | exact p |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| classic_cruise_1900 | 7 | 1e-9 | 100 | 1.000 | 128.4 | 0.002 | 2.00 | 0.010 [-0.020, 0.050] | 0.020 | 0.00000 [-0.00002, 0.00002] | 0/0 | n/a |
| classic_cruise_1900 | 7 | 1e-7 | 100 | 1.000 | 142.7 | 0.582 | 267.00 | 2.660 [0.489, 5.431] | 0.800 | 0.00007 [0.00000, 0.00021] | 0/0 | n/a |
| classic_cruise_1900 | 7 | 1e-5 | 100 | 1.000 | 216.7 | 3.735 | 1708.00 | 17.070 [10.870, 24.511] | 12.900 | 0.00245 [0.00118, 0.00398] | 3/0 | 0.250 |
| classic_cruise_1900 | 12 | 1e-9 | 100 | 1.000 | 177.7 | 0.000 | 1.00 | 0.000 [-0.030, 0.030] | 0.010 | -0.00000 [-0.00003, 0.00003] | 0/0 | n/a |
| classic_cruise_1900 | 12 | 1e-7 | 100 | 1.000 | 215.4 | 0.479 | 220.00 | 2.190 [0.540, 4.653] | 1.150 | 0.00029 [0.00003, 0.00071] | 0/0 | n/a |
| classic_cruise_1900 | 12 | 1e-5 | 100 | 1.000 | 603.8 | 13.212 | 6039.00 | 60.380 [41.093, 79.550] | 42.350 | 0.01283 [0.00855, 0.01739] | 19/0 | 0.000 |
| expedition_cruise_450 | 7 | 1e-9 | 100 | 1.000 | 6.0 | 0.010 | 1.06 | 0.010 [-0.030, 0.060] | 0.010 | 0.00003 [0.00000, 0.00009] | 0/0 | n/a |
| expedition_cruise_450 | 7 | 1e-7 | 100 | 1.000 | 6.2 | 0.402 | 3.41 | 0.410 [0.040, 0.951] | 0.320 | 0.00028 [0.00005, 0.00064] | 0/0 | n/a |
| expedition_cruise_450 | 7 | 1e-5 | 100 | 1.000 | 11.3 | 1.725 | 11.35 | 1.760 [0.670, 3.190] | 1.240 | 0.00070 [0.00020, 0.00141] | 0/0 | n/a |
| expedition_cruise_450 | 12 | 1e-9 | 100 | 1.000 | 9.4 | -0.049 | 0.79 | -0.050 [-0.150, 0.000] | 0.010 | -0.00016 [-0.00045, 0.00000] | 0/0 | n/a |
| expedition_cruise_450 | 12 | 1e-7 | 100 | 1.000 | 10.8 | 0.245 | 2.04 | 0.250 [0.020, 0.670] | 0.310 | 0.00013 [-0.00019, 0.00063] | 0/0 | n/a |
| expedition_cruise_450 | 12 | 1e-5 | 100 | 1.000 | 21.8 | 3.225 | 14.71 | 3.290 [1.450, 5.501] | 2.550 | 0.00220 [0.00092, 0.00383] | 4/0 | 0.125 |
| spirit_cruise_3000 | 7 | 1e-9 | 100 | 1.000 | 231.6 | -0.107 | 0.56 | -0.710 [-2.501, 0.240] | 0.120 | -0.00013 [-0.00050, 0.00002] | 0/0 | n/a |
| spirit_cruise_3000 | 7 | 1e-7 | 100 | 1.000 | 314.6 | 1.029 | 5.25 | 6.840 [2.939, 10.522] | 5.160 | 0.00045 [0.00007, 0.00077] | 0/0 | n/a |
| spirit_cruise_3000 | 7 | 1e-5 | 100 | 1.000 | 718.5 | 11.143 | 47.02 | 74.100 [54.802, 94.899] | 57.090 | 0.01122 [0.00784, 0.01467] | 19/0 | 0.000 |
| spirit_cruise_3000 | 12 | 1e-9 | 100 | 1.000 | 313.5 | 0.003 | 1.03 | 0.020 [-0.370, 0.230] | 0.140 | -0.00000 [-0.00006, 0.00005] | 0/0 | n/a |
| spirit_cruise_3000 | 12 | 1e-7 | 100 | 1.000 | 524.1 | 2.480 | 24.56 | 16.490 [10.259, 24.075] | 8.780 | 0.00279 [0.00140, 0.00458] | 3/0 | 0.250 |
| spirit_cruise_3000 | 12 | 1e-5 | 100 | 1.000 | 1730.2 | 29.356 | 279.89 | 195.220 [155.132, 237.075] | 134.950 | 0.02982 [0.02379, 0.03611] | 47/0 | 0.000 |

Observed comparators, reported and not fitted: A4 reported passenger AR over pre-2020 postings by hull, and A9 posting probability per 1,000 voyages.

```json
{
 "A4_reported_passenger_ar_over_postings_by_hull": {
  "classic_cruise_1900": {
   "median": 0.05518945634266886,
   "n": 95.0,
   "q1": 0.04148771722542215,
   "q3": 0.07820870359866389
  },
  "expedition_cruise_450": {
   "median": 0.0532258064516129,
   "n": 21.0,
   "q1": 0.04,
   "q3": 0.1044776119402985
  },
  "mega_cruise_5000": {
   "median": 0.060037301484954994,
   "n": 16.0,
   "q1": 0.03547007602769624,
   "q3": 0.07489444602199992
  },
  "spirit_cruise_3000": {
   "median": 0.05260409128190283,
   "n": 130.0,
   "q1": 0.041835460931410134,
   "q3": 0.07239561073520678
  }
 },
 "A9_posting_probability_per_1000_voyages": {
  "fleet": {
   "definitions": {
    "investigated": "MMWR investigated passenger outbreaks",
    "posted": "project VSP posted series"
   },
   "denominator": {
    "source": "Jenkins 2021 (MMWR SS 70(6)), Table 1",
    "unit": "unduplicated voyage reports, pooled 2006-2019",
    "voyages": 37258,
    "window": [
     2006,
     2019
    ]
   },
   "interval": [
    4.1870202372644805,
    5.582693649685973
   ],
   "investigated": 4.1870202372644805,
   "posted": 5.582693649685973
  },
  "passenger_by_voyage_length": {
   "11-14": 18.32208293153327,
   "15-21": 28.50356294536817,
   "3-5": 0.5082776648271856,
   "6-7": 0.331619963521804,
   "8-10": 2.4511806520140533
  },
  "per_hull": {
   "classic_cruise_1900": {
    "reason": "per-hull outbreak numerator unpublished",
    "target": null
   },
   "expedition_cruise_450": {
    "reason": "per-hull outbreak numerator unpublished",
    "target": null
   },
   "mega_cruise_5000": {
    "reason": "per-hull outbreak numerator unpublished",
    "target": null
   },
   "spirit_cruise_3000": {
    "reason": "per-hull outbreak numerator unpublished",
    "target": null
   }
  },
  "per_length": {
   "11-14": 18.32208293153327,
   "15-21": 28.50356294536817,
   "3-5": 0.5082776648271856,
   "6-7": 0.331619963521804,
   "8-10": 2.4511806520140533
  }
 },
 "note": "Reported for contrast only. No arm was selected, and no fraction adopted, on its distance to any of them."
}
```
