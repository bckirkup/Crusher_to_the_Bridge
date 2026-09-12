# Posting frequency and posting-conditional attack rate

Posting rule: reported cases >= 3% of passengers or of crew. Attack rate is the reported passenger attack rate over posted voyages. Release scale is `environmental_faecal_release_log10_g_per_epoch` and cells are never pooled across it.

| platform | surveillance | release | days | voyages | posted | P(post) | P(post) 95% CI | n posted | median pax AR | IQR |
|---|---|---|---|---|---|---|---|---|---|---|
| classic_cruise_1900 | none_response | 4.0 | 7.0 | 150 | 2 | n/a | n/a | 2 | 0.0023 | 0.0019-0.0026 |
| classic_cruise_1900 | syndromic_comp25 | 4.0 | 7.0 | 150 | 5 | 0.0333 | 0.0128-0.0715 | 5 | 0.0007 | 0.0007-0.0433 |
| classic_cruise_1900 | syndromic_comp45 | 4.0 | 7.0 | 150 | 5 | 0.0333 | 0.0128-0.0715 | 5 | 0.0112 | 0.0007-0.0478 |
| classic_cruise_1900 | syndromic_comp65 | 1.0 | 7.0 | 150 | 91 | 0.6067 | 0.5271-0.6822 | 91 | 0.0680 | 0.0497-0.0886 |
| classic_cruise_1900 | syndromic_comp65 | 2.0 | 7.0 | 150 | 39 | 0.2600 | 0.1949-0.3343 | 39 | 0.0404 | 0.0149-0.0576 |
| classic_cruise_1900 | syndromic_comp65 | 2.0 | 12.0 | 150 | 108 | 0.7200 | 0.6444-0.7872 | 108 | 0.0759 | 0.0478-0.1325 |
| classic_cruise_1900 | syndromic_comp65 | 3.0 | 7.0 | 150 | 9 | 0.0600 | 0.0301-0.1066 | 9 | 0.0329 | 0.0321-0.0396 |
| classic_cruise_1900 | syndromic_comp65 | 4.0 | 7.0 | 1000 | 10 | 0.0100 | 0.0052-0.0177 | 10 | 0.0329 | 0.0306-0.0506 |
| classic_cruise_1900 | syndromic_comp65 | 4.0 | 12.0 | 1000 | 75 | 0.0750 | 0.0599-0.0926 | 75 | 0.0359 | 0.0067-0.0568 |
| classic_cruise_1900 | syndromic_comp65 | 5.0 | 7.0 | 150 | 3 | 0.0200 | 0.0057-0.0524 | 3 | 0.0030 | 0.0019-0.0209 |
| classic_cruise_1900 | syndromic_comp65 | 6.0 | 7.0 | 150 | 2 | 0.0133 | 0.0028-0.0421 | 2 | 0.0019 | 0.0013-0.0024 |
| classic_cruise_1900 | syndromic_comp65 | 6.0 | 12.0 | 150 | 3 | 0.0200 | 0.0057-0.0524 | 3 | 0.0553 | 0.0534-0.0568 |
| classic_cruise_1900 | syndromic_comp85 | 4.0 | 7.0 | 150 | 3 | 0.0200 | 0.0057-0.0524 | 3 | 0.0007 | 0.0007-0.0333 |
| spirit_cruise_3000 | none_response | 4.0 | 7.0 | 150 | 1 | n/a | n/a | 1 | 0.0010 | 0.0010-0.0010 |
| spirit_cruise_3000 | syndromic_comp25 | 4.0 | 7.0 | 150 | 1 | 0.0067 | 0.0007-0.0307 | 1 | 0.0205 | 0.0205-0.0205 |
| spirit_cruise_3000 | syndromic_comp45 | 4.0 | 7.0 | 150 | 1 | 0.0067 | 0.0007-0.0307 | 1 | 0.0176 | 0.0176-0.0176 |
| spirit_cruise_3000 | syndromic_comp65 | 1.0 | 7.0 | 150 | 89 | 0.5933 | 0.5136-0.6695 | 89 | 0.0662 | 0.0224-0.0833 |
| spirit_cruise_3000 | syndromic_comp65 | 2.0 | 7.0 | 150 | 32 | 0.2133 | 0.1536-0.2840 | 32 | 0.0438 | 0.0103-0.0553 |
| spirit_cruise_3000 | syndromic_comp65 | 2.0 | 12.0 | 150 | 115 | 0.7667 | 0.6943-0.8288 | 115 | 0.0829 | 0.0522-0.1212 |
| spirit_cruise_3000 | syndromic_comp65 | 3.0 | 7.0 | 150 | 4 | 0.0267 | 0.0091-0.0621 | 4 | 0.0538 | 0.0466-0.0597 |
| spirit_cruise_3000 | syndromic_comp65 | 4.0 | 7.0 | 1000 | 6 | 0.0060 | 0.0025-0.0123 | 6 | 0.0276 | 0.0052-0.0386 |
| spirit_cruise_3000 | syndromic_comp65 | 4.0 | 12.0 | 1000 | 64 | 0.0640 | 0.0501-0.0804 | 64 | 0.0369 | 0.0027-0.0516 |
| spirit_cruise_3000 | syndromic_comp65 | 5.0 | 7.0 | 150 | 0 | 0.0000 | 0.0000-0.0166 | 0 | n/a | n/a-n/a |
| spirit_cruise_3000 | syndromic_comp65 | 6.0 | 7.0 | 150 | 0 | 0.0000 | 0.0000-0.0166 | 0 | n/a | n/a-n/a |
| spirit_cruise_3000 | syndromic_comp65 | 6.0 | 12.0 | 150 | 1 | 0.0067 | 0.0007-0.0307 | 1 | 0.0324 | 0.0324-0.0324 |
| spirit_cruise_3000 | syndromic_comp85 | 4.0 | 7.0 | 150 | 1 | 0.0067 | 0.0007-0.0307 | 1 | 0.0176 | 0.0176-0.0176 |

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
