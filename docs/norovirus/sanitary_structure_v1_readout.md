# Shared heads without a flush term: the structure-only matched arm

Posting rule: reported cases >= 3% of passengers or of crew. `visits/p-d` is shared-head visits per person-day aboard; `stool v.` and `recip v.` count voyages with any stool event landing on a shared head and any susceptible pickup off one. `recipients` counts pickup events, not hosts. `sec/import` is pooled secondaries over pooled imports. The fomite column is the share of dominant-attributed infections booked to `fomite`, which is where sanitary pickups land.

| platform | agents | days | arm | mode | voyages | visits/p-d | stool v. | recip v. | recipients | dose | sec/import | mean sec | zero | fomite % | post/1,000 | posting CI | median pax AR |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| classic_cruise_1900 | 1910 | 7 | baseline | none | 500 | 0.00 | 0 | 0 | 0.0 | 0.00000 | 0.040 | 0.18 | 0.944 | 100.0% | 0.0 | [0.0000, 0.0050] | n/a |
| classic_cruise_1900 | 1910 | 7 | visits | dwell_weighted | 500 | 3.98 | 483 | 405 | 5901.8 | 170.10177 | 0.055 | 0.25 | 0.948 | 100.0% | 0.0 | [0.0000, 0.0050] | n/a |
| classic_cruise_1900 | 1910 | 12 | baseline | none | 500 | 0.00 | 0 | 0 | 0.0 | 0.00000 | 0.109 | 0.50 | 0.948 | 100.0% | 2.0 | [0.0002, 0.0093] | 0.0366 |
| classic_cruise_1900 | 1910 | 12 | visits | dwell_weighted | 500 | 3.98 | 487 | 424 | 12318.4 | 45.40524 | 0.034 | 0.16 | 0.948 | 98.7% | 0.0 | [0.0000, 0.0050] | n/a |
| expedition_cruise_450 | 450 | 7 | baseline | none | 500 | 0.00 | 0 | 0 | 0.0 | 0.00000 | 0.056 | 0.06 | 0.982 | 100.0% | 0.0 | [0.0000, 0.0050] | n/a |
| expedition_cruise_450 | 450 | 7 | visits | dwell_weighted | 500 | 3.98 | 287 | 145 | 312.3 | 44.84236 | 0.048 | 0.05 | 0.988 | 100.0% | 0.0 | [0.0000, 0.0050] | n/a |
| expedition_cruise_450 | 450 | 12 | baseline | none | 500 | 0.00 | 0 | 0 | 0.0 | 0.00000 | 0.056 | 0.06 | 0.982 | 100.0% | 0.0 | [0.0000, 0.0050] | n/a |
| expedition_cruise_450 | 450 | 12 | visits | dwell_weighted | 500 | 3.98 | 300 | 169 | 665.6 | 37.89900 | 0.045 | 0.05 | 0.988 | 100.0% | 0.0 | [0.0000, 0.0050] | n/a |
| spirit_cruise_3000 | 3000 | 7 | baseline | none | 500 | 0.00 | 0 | 0 | 0.0 | 0.00000 | 0.144 | 1.01 | 0.896 | 99.6% | 0.0 | [0.0000, 0.0050] | n/a |
| spirit_cruise_3000 | 3000 | 7 | visits | dwell_weighted | 500 | 3.98 | 499 | 474 | 10003.2 | 588.16260 | 0.118 | 0.82 | 0.914 | 99.8% | 0.0 | [0.0000, 0.0050] | n/a |
| spirit_cruise_3000 | 3000 | 12 | baseline | none | 500 | 0.00 | 0 | 0 | 0.0 | 0.00000 | 0.156 | 1.09 | 0.888 | 98.9% | 0.0 | [0.0000, 0.0050] | n/a |
| spirit_cruise_3000 | 3000 | 12 | visits | dwell_weighted | 500 | 3.98 | 500 | 480 | 20709.5 | 970.43330 | 0.159 | 1.11 | 0.904 | 99.3% | 0.0 | [0.0000, 0.0050] | n/a |

## Paired contrasts (visits − baseline, seed by seed)

`identical imports` must be 1.000: the visit stream has its own rng, so a pair whose boarding cohort moved is a leak, not a result. `gained/lost` are McNemar's discordant postings.

| platform | days | seeds | identical imports | Δ recipients | Δ sec/import | Δ secondaries (CI) | Δ fomite dominant | Δ margin (CI) | var reduction | gained/lost | exact p |
|---|---|---|---|---|---|---|---|---|---|---|---|
| classic_cruise_1900 | 7 | 500 | 1.000 | 5901.8 | 0.015 | 0.070 [-0.084, 0.292] | 0.068 | 0.00001 [-0.00002, 0.00003] | 18.0 | 0/0 | n/a |
| classic_cruise_1900 | 12 | 500 | 1.000 | 12318.4 | -0.075 | -0.340 [-0.800, 0.016] | -0.344 | -0.00012 [-0.00029, 0.00000] | 1.4 | 0/1 | 1.000 |
| expedition_cruise_450 | 7 | 500 | 1.000 | 312.3 | -0.007 | -0.008 [-0.026, 0.006] | -0.008 | 0.00001 [-0.00004, 0.00007] | 13.6 | 0/0 | n/a |
| expedition_cruise_450 | 12 | 500 | 1.000 | 665.6 | -0.011 | -0.012 [-0.032, 0.002] | -0.012 | -0.00001 [-0.00005, 0.00001] | 51.7 | 0/0 | n/a |
| spirit_cruise_3000 | 7 | 500 | 1.000 | 10003.2 | -0.027 | -0.188 [-0.476, 0.070] | -0.186 | 0.00004 [0.00000, 0.00009] | 10.4 | 0/0 | n/a |
| spirit_cruise_3000 | 12 | 500 | 1.000 | 20709.5 | 0.003 | 0.024 [-0.545, 0.510] | 0.028 | 0.00006 [-0.00002, 0.00017] | 3.3 | 0/0 | n/a |

Observed comparators, reported and not fitted: A4 reported passenger AR over pre-2020 postings by hull, and A9 posting probability per 1,000 voyages, fleet-pooled and by voyage-length band.

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
 "note": "Reported for contrast only. No value in this campaign was selected to move any of them."
}
```
