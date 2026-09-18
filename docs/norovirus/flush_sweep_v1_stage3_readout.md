# Which decade of the flush aerosol fraction first moves an outcome: the s3 re-bracket on the current engine

**Measured at:** `65d9fb2821c4d389eb92d3470d61f0ab06b84b3a` (`parameters.engine_git_sha`, read from every archived run).

Posting rule: reported cases >= 3% of passengers or of crew. `f_aero` is each arm's own archived `flush_aerosol_fraction`, read from the run parameters and not from a prefix. `ev. v.` counts voyages with any emitting flush; `recipients` counts exposure events, not hosts. `dose/exp` is pooled inhaled particles per exposure event, against N50 = 16,871. `mean ever` is mean cumulative ever-infected per voyage and `zero` the fraction of voyages with no establishment beyond the boarding cohort. Route columns are shares of dominant-route attributions. Every `off` row must show zero flush events: the baseline is the disabled path, not the sweep evaluated at zero.

| platform | days | arm | f_aero | voyages | ev. v. | emitted | recipients | dose/exp | mean ever | zero | flush % | hvac % | fomite % | post/1,000 | posting CI | median pax reported AR |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| expedition_cruise_450 | 7 | off | 0.00e+00 | 100 | 0 | 0.00e+00 | 0 | n/a | 1.13 | 0.960 | 0.0% | 0.0% | 100.0% | 0.0 | [0.0000, 0.0370] | n/a |
| expedition_cruise_450 | 7 | 1e-9 | 1.00e-09 | 100 | 35 | 2.23e+06 | 417 | 5.38e+01 | 1.13 | 0.960 | 18.2% | 9.1% | 72.7% | 0.0 | [0.0000, 0.0370] | n/a |
| expedition_cruise_450 | 7 | 1e-7 | 1.00e-07 | 100 | 35 | 5.66e+08 | 754 | 4.03e+03 | 1.69 | 0.930 | 37.3% | 23.9% | 38.8% | 0.0 | [0.0000, 0.0370] | n/a |
| expedition_cruise_450 | 7 | 1e-5 | 1.00e-05 | 100 | 35 | 6.73e+11 | 1139 | 2.95e+05 | 4.93 | 0.810 | 27.0% | 48.0% | 25.0% | 10.0 | [0.0018, 0.0545] | 0.1108 |
| expedition_cruise_450 | 12 | off | 0.00e+00 | 100 | 0 | 0.00e+00 | 0 | n/a | 1.12 | 0.960 | 0.0% | 0.0% | 100.0% | 0.0 | [0.0000, 0.0370] | n/a |
| expedition_cruise_450 | 12 | 1e-9 | 1.00e-09 | 100 | 39 | 2.62e+06 | 768 | 3.44e+01 | 1.16 | 0.960 | 28.6% | 7.1% | 64.3% | 0.0 | [0.0000, 0.0370] | n/a |
| expedition_cruise_450 | 12 | 1e-7 | 1.00e-07 | 100 | 39 | 6.36e+08 | 1239 | 2.70e+03 | 1.93 | 0.930 | 36.3% | 22.0% | 41.8% | 0.0 | [0.0000, 0.0370] | n/a |
| expedition_cruise_450 | 12 | 1e-5 | 1.00e-05 | 100 | 39 | 6.16e+11 | 3151 | 1.08e+06 | 10.78 | 0.800 | 30.0% | 52.1% | 17.9% | 50.0 | [0.0215, 0.1118] | 0.0475 |
| classic_cruise_1900 | 7 | off | 0.00e+00 | 100 | 0 | 0.00e+00 | 0 | n/a | 4.64 | 0.910 | 0.0% | 0.0% | 88.9% | 0.0 | [0.0000, 0.0370] | n/a |
| classic_cruise_1900 | 7 | 1e-9 | 1.00e-09 | 100 | 94 | 1.36e+07 | 13732 | 1.81e+00 | 4.97 | 0.920 | 4.8% | 2.4% | 92.9% | 0.0 | [0.0000, 0.0370] | n/a |
| classic_cruise_1900 | 7 | 1e-7 | 1.00e-07 | 100 | 94 | 2.10e+09 | 15174 | 1.74e+02 | 7.17 | 0.680 | 27.9% | 48.1% | 24.0% | 0.0 | [0.0000, 0.0370] | n/a |
| classic_cruise_1900 | 7 | 1e-5 | 1.00e-05 | 100 | 94 | 1.19e+12 | 41889 | 5.49e+04 | 90.59 | 0.190 | 28.4% | 45.2% | 26.3% | 130.0 | [0.0776, 0.2098] | 0.0419 |
| classic_cruise_1900 | 12 | off | 0.00e+00 | 100 | 0 | 0.00e+00 | 0 | n/a | 4.64 | 0.910 | 0.0% | 0.0% | 88.9% | 0.0 | [0.0000, 0.0370] | n/a |
| classic_cruise_1900 | 12 | 1e-9 | 1.00e-09 | 100 | 95 | 1.29e+07 | 19627 | 1.28e+00 | 4.64 | 0.920 | 33.3% | 0.0% | 66.7% | 0.0 | [0.0000, 0.0370] | n/a |
| classic_cruise_1900 | 12 | 1e-7 | 1.00e-07 | 100 | 95 | 3.20e+10 | 35976 | 1.28e+03 | 24.48 | 0.670 | 21.5% | 13.1% | 65.2% | 60.0 | [0.0278, 0.1248] | 0.0553 |
| classic_cruise_1900 | 12 | 1e-5 | 1.00e-05 | 100 | 95 | 1.40e+13 | 118757 | 4.30e+05 | 245.17 | 0.140 | 30.7% | 42.7% | 26.5% | 420.0 | [0.3280, 0.5179] | 0.0725 |
| spirit_cruise_3000 | 7 | off | 0.00e+00 | 100 | 0 | 0.00e+00 | 0 | n/a | 7.89 | 0.850 | 0.0% | 0.0% | 99.2% | 0.0 | [0.0000, 0.0370] | n/a |
| spirit_cruise_3000 | 7 | 1e-9 | 1.00e-09 | 100 | 99 | 1.76e+07 | 21519 | 9.95e-01 | 7.32 | 0.830 | 14.5% | 2.9% | 82.6% | 0.0 | [0.0000, 0.0370] | n/a |
| spirit_cruise_3000 | 7 | 1e-7 | 1.00e-07 | 100 | 99 | 1.65e+10 | 37498 | 1.47e+03 | 30.45 | 0.470 | 19.7% | 8.0% | 71.8% | 30.0 | [0.0103, 0.0845] | 0.0581 |
| spirit_cruise_3000 | 7 | 1e-5 | 1.00e-05 | 100 | 99 | 1.88e+12 | 95572 | 1.28e+05 | 196.99 | 0.090 | 31.7% | 38.7% | 29.4% | 200.0 | [0.1334, 0.2888] | 0.0479 |
| spirit_cruise_3000 | 12 | off | 0.00e+00 | 100 | 0 | 0.00e+00 | 0 | n/a | 7.22 | 0.860 | 0.0% | 0.0% | 98.3% | 0.0 | [0.0000, 0.0370] | n/a |
| spirit_cruise_3000 | 12 | 1e-9 | 1.00e-09 | 100 | 99 | 4.01e+07 | 30135 | 9.41e+00 | 9.30 | 0.840 | 4.9% | 1.9% | 92.1% | 10.0 | [0.0018, 0.0545] | 0.0486 |
| spirit_cruise_3000 | 12 | 1e-7 | 1.00e-07 | 100 | 99 | 4.25e+10 | 76453 | 1.71e+03 | 59.31 | 0.420 | 21.5% | 7.5% | 70.5% | 80.0 | [0.0411, 0.1500] | 0.0710 |
| spirit_cruise_3000 | 12 | 1e-5 | 1.00e-05 | 100 | 99 | 3.02e+13 | 226155 | 7.26e+05 | 506.46 | 0.070 | 30.0% | 42.3% | 27.5% | 520.0 | [0.4232, 0.6154] | 0.0850 |
