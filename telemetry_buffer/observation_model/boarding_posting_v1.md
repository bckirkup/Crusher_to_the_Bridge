# Introduction mechanism, posting frequency and between-voyage spread

Posting rule: reported cases >= 3% of passengers or of crew. `secondary` infections are infections net of the realised boarding cohort, so the import is not counted as transmission. `zero` is the fraction of voyages with no onward transmission at all and `top10%` the share of all secondary infections held by the largest tenth of voyages; together they say whether the mean is carried by a thin tail.

| arm | platform | surv | release | days | prev pax/crew | presympt | voyages | post/1,000 | crew-only | mean imports | mean secondary | zero | top10% | var/mean | median pax AR |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| boarding | classic_cruise_1900 | syndromic_comp65 | 4.0 | 7.0 | 0.0250/0.0070 | 0.040 | 150 | 386.7 | 10 | 29.78 | 146.5 | 0.007 | 0.209 | 63.3 | 0.0437 |
| boarding | classic_cruise_1900 | syndromic_comp65 | 4.0 | 7.0 | 0.0250/0.0300 | 0.040 | 150 | 526.7 | 30 | 40.45 | 184.5 | 0.000 | 0.192 | 51.3 | 0.0351 |
| boarding | classic_cruise_1900 | syndromic_comp65 | 4.0 | 7.0 | 0.0325/0.0185 | 0.020 | 150 | 460.0 | 11 | 42.85 | 176.3 | 0.000 | 0.190 | 52.3 | 0.0478 |
| boarding | classic_cruise_1900 | syndromic_comp65 | 4.0 | 7.0 | 0.0325/0.0185 | 0.040 | 1150 | 554.8 | 144 | 43.30 | 192.5 | 0.000 | 0.178 | 45.4 | 0.0471 |
| boarding | classic_cruise_1900 | syndromic_comp65 | 4.0 | 7.0 | 0.0325/0.0185 | 0.080 | 150 | 520.0 | 16 | 43.13 | 186.4 | 0.000 | 0.190 | 55.9 | 0.0433 |
| boarding | classic_cruise_1900 | syndromic_comp65 | 4.0 | 7.0 | 0.0400/0.0070 | 0.040 | 150 | 566.7 | 7 | 46.23 | 197.5 | 0.000 | 0.174 | 47.7 | 0.0546 |
| boarding | classic_cruise_1900 | syndromic_comp65 | 4.0 | 7.0 | 0.0400/0.0300 | 0.040 | 150 | 693.3 | 26 | 56.85 | 218.0 | 0.000 | 0.162 | 36.7 | 0.0463 |
| boarding | classic_cruise_1900 | syndromic_comp65 | 4.0 | 12.0 | 0.0250/0.0070 | 0.040 | 150 | 773.3 | 7 | 29.78 | 264.3 | 0.007 | 0.151 | 45.3 | 0.0699 |
| boarding | classic_cruise_1900 | syndromic_comp65 | 4.0 | 12.0 | 0.0250/0.0300 | 0.040 | 150 | 906.7 | 15 | 40.45 | 281.0 | 0.000 | 0.141 | 28.8 | 0.0609 |
| boarding | classic_cruise_1900 | syndromic_comp65 | 4.0 | 12.0 | 0.0325/0.0185 | 0.020 | 150 | 920.0 | 10 | 42.85 | 297.9 | 0.000 | 0.137 | 24.3 | 0.0662 |
| boarding | classic_cruise_1900 | syndromic_comp65 | 4.0 | 12.0 | 0.0325/0.0185 | 0.040 | 1150 | 944.3 | 89 | 43.30 | 299.5 | 0.000 | 0.133 | 17.8 | 0.0680 |
| boarding | classic_cruise_1900 | syndromic_comp65 | 4.0 | 12.0 | 0.0325/0.0185 | 0.080 | 150 | 933.3 | 12 | 43.13 | 295.7 | 0.000 | 0.134 | 22.4 | 0.0692 |
| boarding | classic_cruise_1900 | syndromic_comp65 | 4.0 | 12.0 | 0.0400/0.0070 | 0.040 | 150 | 946.7 | 5 | 46.23 | 299.7 | 0.000 | 0.136 | 18.1 | 0.0770 |
| boarding | classic_cruise_1900 | syndromic_comp65 | 4.0 | 12.0 | 0.0400/0.0300 | 0.040 | 150 | 966.7 | 9 | 56.85 | 308.4 | 0.000 | 0.134 | 15.3 | 0.0680 |
| boarding | expedition_cruise_450 | syndromic_comp65 | 4.0 | 7.0 | 0.0325/0.0185 | 0.020 | 150 | 120.0 | 3 | 10.09 | 17.2 | 0.167 | 0.347 | 20.8 | 0.0380 |
| boarding | expedition_cruise_450 | syndromic_comp65 | 4.0 | 7.0 | 0.0325/0.0185 | 0.040 | 1150 | 107.8 | 39 | 10.13 | 16.4 | 0.156 | 0.339 | 19.6 | 0.0348 |
| boarding | expedition_cruise_450 | syndromic_comp65 | 4.0 | 7.0 | 0.0325/0.0185 | 0.080 | 150 | 120.0 | 3 | 10.20 | 17.0 | 0.147 | 0.368 | 22.3 | 0.0443 |
| boarding | expedition_cruise_450 | syndromic_comp65 | 4.0 | 12.0 | 0.0325/0.0185 | 0.040 | 1000 | 304.0 | 58 | 10.12 | 27.1 | 0.149 | 0.297 | 26.6 | 0.0443 |
| boarding | spirit_cruise_3000 | syndromic_comp65 | 4.0 | 7.0 | 0.0325/0.0185 | 0.040 | 1000 | 695.0 | 140 | 68.21 | 353.5 | 0.000 | 0.154 | 47.7 | 0.0452 |
| boarding | spirit_cruise_3000 | syndromic_comp65 | 4.0 | 12.0 | 0.0325/0.0185 | 0.040 | 1000 | 992.0 | 37 | 68.21 | 510.9 | 0.000 | 0.123 | 12.7 | 0.0733 |
| fiat_exp | expedition_cruise_450 | none_response | 4.0 | 7.0 | n/a/n/a | n/a | 200 | 95.0 | 7 | 1.00 | 31.6 | 0.000 | 0.309 | 30.3 | 0.0348 |
| fiat_exp | expedition_cruise_450 | syndromic_comp25 | 4.0 | 7.0 | n/a/n/a | n/a | 200 | 20.0 | 3 | 1.00 | 3.5 | 0.000 | 0.564 | 11.3 | 0.0032 |
| fiat_exp | expedition_cruise_450 | syndromic_comp45 | 4.0 | 7.0 | n/a/n/a | n/a | 200 | 15.0 | 3 | 1.00 | 3.0 | 0.000 | 0.524 | 8.6 | 0.0032 |
| fiat_exp | expedition_cruise_450 | syndromic_comp65 | 1.0 | 7.0 | n/a/n/a | n/a | 200 | 455.0 | 21 | 1.00 | 97.6 | 0.000 | 0.198 | 41.6 | 0.0506 |
| fiat_exp | expedition_cruise_450 | syndromic_comp65 | 2.0 | 7.0 | n/a/n/a | n/a | 200 | 95.0 | 7 | 1.00 | 30.9 | 0.000 | 0.373 | 44.9 | 0.0380 |
| fiat_exp | expedition_cruise_450 | syndromic_comp65 | 2.0 | 12.0 | n/a/n/a | n/a | 200 | 605.0 | 20 | 1.00 | 86.3 | 0.000 | 0.198 | 41.6 | 0.0854 |
| fiat_exp | expedition_cruise_450 | syndromic_comp65 | 3.0 | 7.0 | n/a/n/a | n/a | 200 | 35.0 | 5 | 1.00 | 7.5 | 0.000 | 0.524 | 22.6 | 0.0032 |
| fiat_exp | expedition_cruise_450 | syndromic_comp65 | 4.0 | 7.0 | n/a/n/a | n/a | 1000 | 9.0 | 3 | 1.00 | 3.1 | 0.003 | 0.573 | 14.0 | 0.0348 |
| fiat_exp | expedition_cruise_450 | syndromic_comp65 | 4.0 | 12.0 | n/a/n/a | n/a | 1000 | 54.0 | 17 | 1.00 | 6.2 | 0.003 | 0.644 | 27.3 | 0.0348 |
| fiat_exp | expedition_cruise_450 | syndromic_comp65 | 5.0 | 7.0 | n/a/n/a | n/a | 200 | 10.0 | 2 | 1.00 | 1.6 | 0.000 | 0.381 | 4.4 | 0.0032 |
| fiat_exp | expedition_cruise_450 | syndromic_comp65 | 6.0 | 7.0 | n/a/n/a | n/a | 200 | 10.0 | 2 | 1.00 | 1.3 | 0.000 | 0.282 | 2.0 | 0.0032 |
| fiat_exp | expedition_cruise_450 | syndromic_comp65 | 6.0 | 12.0 | n/a/n/a | n/a | 200 | 10.0 | 0 | 1.00 | 1.7 | 0.000 | 0.467 | 12.3 | 0.0712 |
| fiat_exp | expedition_cruise_450 | syndromic_comp85 | 4.0 | 7.0 | n/a/n/a | n/a | 200 | 5.0 | 1 | 1.00 | 2.1 | 0.000 | 0.455 | 5.1 | 0.0032 |
| fiat_hull | classic_cruise_1900 | none_response | 4.0 | 7.0 | n/a/n/a | n/a | 150 | 13.3 | 2 | 1.00 | 95.7 | 0.000 | 0.385 | 134.6 | 0.0023 |
| fiat_hull | classic_cruise_1900 | syndromic_comp25 | 4.0 | 7.0 | n/a/n/a | n/a | 150 | 33.3 | 3 | 1.00 | 15.4 | 0.000 | 0.717 | 106.6 | 0.0007 |
| fiat_hull | classic_cruise_1900 | syndromic_comp45 | 4.0 | 7.0 | n/a/n/a | n/a | 150 | 33.3 | 3 | 1.00 | 14.6 | 0.000 | 0.724 | 103.5 | 0.0112 |
| fiat_hull | classic_cruise_1900 | syndromic_comp65 | 1.0 | 7.0 | n/a/n/a | n/a | 150 | 606.7 | 15 | 1.00 | 444.7 | 0.000 | 0.174 | 161.1 | 0.0680 |
| fiat_hull | classic_cruise_1900 | syndromic_comp65 | 2.0 | 7.0 | n/a/n/a | n/a | 150 | 260.0 | 13 | 1.00 | 143.6 | 0.000 | 0.384 | 240.6 | 0.0404 |
| fiat_hull | classic_cruise_1900 | syndromic_comp65 | 2.0 | 12.0 | n/a/n/a | n/a | 150 | 720.0 | 18 | 1.00 | 396.7 | 0.000 | 0.168 | 142.6 | 0.0759 |
| fiat_hull | classic_cruise_1900 | syndromic_comp65 | 3.0 | 7.0 | n/a/n/a | n/a | 150 | 60.0 | 2 | 1.00 | 35.8 | 0.000 | 0.642 | 155.9 | 0.0329 |
| fiat_hull | classic_cruise_1900 | syndromic_comp65 | 4.0 | 7.0 | n/a/n/a | n/a | 1000 | 10.0 | 2 | 1.00 | 7.8 | 0.000 | 0.759 | 75.1 | 0.0329 |
| fiat_hull | classic_cruise_1900 | syndromic_comp65 | 4.0 | 12.0 | n/a/n/a | n/a | 1000 | 75.0 | 31 | 1.00 | 26.0 | 0.000 | 0.746 | 154.4 | 0.0359 |
| fiat_hull | classic_cruise_1900 | syndromic_comp65 | 5.0 | 7.0 | n/a/n/a | n/a | 150 | 20.0 | 2 | 1.00 | 4.9 | 0.000 | 0.758 | 52.9 | 0.0030 |
| fiat_hull | classic_cruise_1900 | syndromic_comp65 | 6.0 | 7.0 | n/a/n/a | n/a | 150 | 13.3 | 2 | 1.00 | 3.8 | 0.000 | 0.743 | 29.6 | 0.0019 |
| fiat_hull | classic_cruise_1900 | syndromic_comp65 | 6.0 | 12.0 | n/a/n/a | n/a | 150 | 20.0 | 0 | 1.00 | 6.8 | 0.000 | 0.842 | 79.7 | 0.0553 |
| fiat_hull | classic_cruise_1900 | syndromic_comp85 | 4.0 | 7.0 | n/a/n/a | n/a | 150 | 20.0 | 2 | 1.00 | 9.3 | 0.000 | 0.785 | 110.9 | 0.0007 |
| fiat_hull | spirit_cruise_3000 | none_response | 4.0 | 7.0 | n/a/n/a | n/a | 150 | 6.7 | 1 | 1.00 | 103.4 | 0.000 | 0.401 | 165.8 | 0.0010 |
| fiat_hull | spirit_cruise_3000 | syndromic_comp25 | 4.0 | 7.0 | n/a/n/a | n/a | 150 | 6.7 | 1 | 1.00 | 13.7 | 0.000 | 0.791 | 117.8 | 0.0205 |
| fiat_hull | spirit_cruise_3000 | syndromic_comp45 | 4.0 | 7.0 | n/a/n/a | n/a | 150 | 6.7 | 1 | 1.00 | 12.6 | 0.000 | 0.829 | 123.6 | 0.0176 |
| fiat_hull | spirit_cruise_3000 | syndromic_comp65 | 1.0 | 7.0 | n/a/n/a | n/a | 150 | 593.3 | 23 | 1.00 | 691.1 | 0.000 | 0.167 | 211.4 | 0.0662 |
| fiat_hull | spirit_cruise_3000 | syndromic_comp65 | 2.0 | 7.0 | n/a/n/a | n/a | 150 | 213.3 | 12 | 1.00 | 211.7 | 0.000 | 0.358 | 307.5 | 0.0438 |
| fiat_hull | spirit_cruise_3000 | syndromic_comp65 | 2.0 | 12.0 | n/a/n/a | n/a | 150 | 766.7 | 14 | 1.00 | 661.7 | 0.000 | 0.153 | 169.6 | 0.0829 |
| fiat_hull | spirit_cruise_3000 | syndromic_comp65 | 3.0 | 7.0 | n/a/n/a | n/a | 150 | 26.7 | 0 | 1.00 | 47.0 | 0.000 | 0.696 | 255.6 | 0.0538 |
| fiat_hull | spirit_cruise_3000 | syndromic_comp65 | 4.0 | 7.0 | n/a/n/a | n/a | 1000 | 6.0 | 3 | 1.00 | 9.5 | 0.001 | 0.789 | 97.4 | 0.0276 |
| fiat_hull | spirit_cruise_3000 | syndromic_comp65 | 4.0 | 12.0 | n/a/n/a | n/a | 1000 | 64.0 | 26 | 1.00 | 33.9 | 0.000 | 0.764 | 221.3 | 0.0369 |
| fiat_hull | spirit_cruise_3000 | syndromic_comp65 | 5.0 | 7.0 | n/a/n/a | n/a | 150 | 0.0 | 0 | 1.00 | 5.1 | 0.000 | 0.797 | 77.2 | n/a |
| fiat_hull | spirit_cruise_3000 | syndromic_comp65 | 6.0 | 7.0 | n/a/n/a | n/a | 150 | 0.0 | 0 | 1.00 | 4.7 | 0.000 | 0.799 | 83.2 | n/a |
| fiat_hull | spirit_cruise_3000 | syndromic_comp65 | 6.0 | 12.0 | n/a/n/a | n/a | 150 | 6.7 | 0 | 1.00 | 4.4 | 0.000 | 0.776 | 63.7 | 0.0324 |
| fiat_hull | spirit_cruise_3000 | syndromic_comp85 | 4.0 | 7.0 | n/a/n/a | n/a | 150 | 6.7 | 1 | 1.00 | 9.0 | 0.000 | 0.812 | 106.6 | 0.0176 |

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
