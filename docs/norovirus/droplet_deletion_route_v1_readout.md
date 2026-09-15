# The introduction realism ladder: what each rung does to posting

Posting rule: reported cases >= 3% of passengers or of crew. `secondary` infections are infections net of the realised boarding cohort. Screen columns are `mean per voyage / voyages with any`, because an eligible host needs a symptomatic boarder and a per-voyage mean cannot distinguish a rare event from a structural zero. `crew c/h/d` is the declaration compliance, recall half-life in days and denial probability the cell was run at; `n/a` means the tier did not sweep that coordinate. Route columns are the percentage of all dominant-attributed infections in the cell; all-zero routes are omitted.

| rung | platform | days | prev pax/crew | crew c/h/d | voyages | post/1,000 | crew-only | imports | sympt | cleared | eligible | declared | reportable | denied | mean secondary | zero | median pax AR | direct_contact dominant % | droplet dominant % | emesis_aerosol dominant % | fomite dominant % |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---| ---| ---| ---|
| reportable | classic_cruise_1900 | 7.0 | n/a/n/a | n/a/n/a/n/a | 300 | 0.0 | 0 | 4.37 | 0.457 | 2.00 | 0.090/26 | 0.090/26 | 0.090/26 | 0.000/0 | 0.6 | 0.933 | n/a | 0.6% | 0.0% | 0.0% | 99.4% |
| reportable | classic_cruise_1900 | 7.0 | n/a/n/a | n/a/n/a/n/a | 300 | 0.0 | 0 | 1.08 | 0.103 | 0.52 | 0.023/7 | 0.023/7 | 0.023/7 | 0.000/0 | 0.0 | 0.993 | n/a | 25.0% | 0.0% | 0.0% | 75.0% |
| reportable | classic_cruise_1900 | 7.0 | n/a/n/a | n/a/n/a/n/a | 300 | 0.0 | 0 | 2.15 | 0.197 | 1.04 | 0.017/5 | 0.017/5 | 0.017/5 | 0.000/0 | 0.4 | 0.947 | n/a | 0.0% | 0.0% | 0.0% | 100.0% |
| reportable | spirit_cruise_3000 | 7.0 | n/a/n/a | n/a/n/a/n/a | 300 | 0.0 | 0 | 3.49 | 0.330 | 1.54 | 0.067/18 | 0.067/18 | 0.067/18 | 0.000/0 | 0.2 | 0.957 | n/a | 1.9% | 0.0% | 0.0% | 98.1% |
| reportable | spirit_cruise_3000 | 7.0 | n/a/n/a | n/a/n/a/n/a | 300 | 6.7 | 1 | 7.04 | 0.700 | 3.10 | 0.173/50 | 0.173/50 | 0.173/50 | 0.000/0 | 1.8 | 0.907 | 0.0152 | 0.0% | 0.0% | 0.2% | 99.8% |
| reportable | spirit_cruise_3000 | 7.0 | n/a/n/a | n/a/n/a/n/a | 300 | 0.0 | 0 | 1.75 | 0.200 | 0.73 | 0.050/13 | 0.050/13 | 0.050/13 | 0.000/0 | 0.0 | 0.980 | n/a | 0.0% | 0.0% | 0.0% | 100.0% |
| reportable | classic_cruise_1900 | 7.0 | n/a/n/a | n/a/n/a/n/a | 300 | 36.7 | 5 | 4.37 | 0.457 | 2.00 | 0.090/26 | 0.090/26 | 0.090/26 | 0.000/0 | 28.8 | 0.347 | 0.0329 | 0.0% | 84.8% | 0.0% | 15.2% |
| reportable | classic_cruise_1900 | 7.0 | n/a/n/a | n/a/n/a/n/a | 300 | 0.0 | 0 | 1.08 | 0.103 | 0.52 | 0.023/7 | 0.023/7 | 0.023/7 | 0.000/0 | 0.4 | 0.880 | n/a | 0.0% | 99.2% | 0.0% | 0.8% |
| reportable | classic_cruise_1900 | 7.0 | n/a/n/a | n/a/n/a/n/a | 300 | 20.0 | 4 | 2.15 | 0.197 | 1.04 | 0.017/5 | 0.017/5 | 0.017/5 | 0.000/0 | 5.2 | 0.723 | 0.0224 | 0.0% | 91.4% | 0.0% | 8.6% |
| reportable | spirit_cruise_3000 | 7.0 | n/a/n/a | n/a/n/a/n/a | 300 | 6.7 | 2 | 3.49 | 0.330 | 1.54 | 0.067/18 | 0.067/18 | 0.067/18 | 0.000/0 | 6.7 | 0.513 | 0.0134 | 0.0% | 89.1% | 0.0% | 10.9% |
| reportable | spirit_cruise_3000 | 7.0 | n/a/n/a | n/a/n/a/n/a | 300 | 46.7 | 6 | 7.04 | 0.700 | 3.10 | 0.173/50 | 0.173/50 | 0.173/50 | 0.000/0 | 56.0 | 0.213 | 0.0383 | 0.0% | 87.8% | 0.0% | 12.2% |
| reportable | spirit_cruise_3000 | 7.0 | n/a/n/a | n/a/n/a/n/a | 300 | 0.0 | 0 | 1.75 | 0.200 | 0.73 | 0.050/13 | 0.050/13 | 0.050/13 | 0.000/0 | 1.3 | 0.793 | n/a | 0.0% | 88.6% | 0.0% | 11.4% |

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
