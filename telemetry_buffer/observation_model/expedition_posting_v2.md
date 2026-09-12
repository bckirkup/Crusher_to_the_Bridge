# Expedition posting frequency and posting-conditional attack rate

Posting rule: reported cases >= 3% of passengers or of crew. Attack rate is the reported passenger attack rate over posted voyages. Release scale is `environmental_faecal_release_log10_g_per_epoch` and cells are never pooled across it.

| surveillance | release | days | voyages | posted | P(post) | P(post) 95% CI | n posted | median pax AR | IQR |
|---|---|---|---|---|---|---|---|---|---|
| none_response | 4.0 | 7.0 | 200 | 19 | n/a | n/a | 19 | 0.0348 | 0.0032-0.0396 |
| syndromic_comp25 | 4.0 | 7.0 | 200 | 4 | 0.0200 | 0.0068-0.0468 | 4 | 0.0032 | 0.0032-0.0111 |
| syndromic_comp45 | 4.0 | 7.0 | 200 | 3 | 0.0150 | 0.0042-0.0395 | 3 | 0.0032 | 0.0032-0.0032 |
| syndromic_comp65 | 1.0 | 7.0 | 200 | 91 | 0.4550 | 0.3870-0.5242 | 91 | 0.0506 | 0.0316-0.0743 |
| syndromic_comp65 | 2.0 | 7.0 | 200 | 19 | 0.0950 | 0.0602-0.1414 | 19 | 0.0380 | 0.0063-0.0490 |
| syndromic_comp65 | 2.0 | 12.0 | 200 | 121 | 0.6050 | 0.5361-0.6708 | 121 | 0.0854 | 0.0475-0.1139 |
| syndromic_comp65 | 3.0 | 7.0 | 200 | 7 | 0.0350 | 0.0158-0.0675 | 7 | 0.0032 | 0.0032-0.0316 |
| syndromic_comp65 | 4.0 | 7.0 | 1000 | 9 | 0.0090 | 0.0045-0.0164 | 9 | 0.0348 | 0.0032-0.0348 |
| syndromic_comp65 | 4.0 | 12.0 | 1000 | 54 | 0.0540 | 0.0413-0.0693 | 54 | 0.0348 | 0.0135-0.0570 |
| syndromic_comp65 | 5.0 | 7.0 | 200 | 2 | 0.0100 | 0.0021-0.0317 | 2 | 0.0032 | 0.0032-0.0032 |
| syndromic_comp65 | 6.0 | 7.0 | 200 | 2 | 0.0100 | 0.0021-0.0317 | 2 | 0.0032 | 0.0032-0.0032 |
| syndromic_comp65 | 6.0 | 12.0 | 200 | 2 | 0.0100 | 0.0021-0.0317 | 2 | 0.0712 | 0.0657-0.0767 |
| syndromic_comp85 | 4.0 | 7.0 | 200 | 1 | 0.0050 | 0.0005-0.0231 | 1 | 0.0032 | 0.0032-0.0032 |

Observed comparators, reported and not fitted: A4 expedition reported passenger AR over pre-2020 postings, and A9 posting probability per 1,000 voyages (fleet-pooled and by voyage-length band). A9 publishes no per-hull numerator, so the fleet and length rows are the only observed posting comparators available.

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
