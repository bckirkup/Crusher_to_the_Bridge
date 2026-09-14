# Posting as a tail probability: the estimators, side by side

Posting rule: margin = max(reported AR passenger, crew) >= 3%, so posting is exactly a threshold crossing of a continuous quantity. `direct` is the binomial estimate; `modelled` is a generalised Pareto tail fitted above the 85% margin quantile and extrapolated to the threshold. The two check columns repeat both estimates at 2%, where the direct one is still well resolved: a model that misses there is not licensed to extrapolate, and `modelled/direct@2%` states that miss as a ratio rather than leaving it to be read off. `anchor scan` is the range the modelled estimate covers as the anchor is moved across 30%-5% exceedance: an estimate that moves with the anchor is fitting the body, not a tail. `xi` is the fitted shape; xi < 0 is a bounded tail.

| arm | platform | days | rung | crew c/h/d | voyages | crossings | direct | direct CI | modelled | modelled CI | direct@2% | modelled@2% | modelled/direct@2% | anchor scan | xi |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| hull | classic_cruise_1900 | 7.0 | reportable | n/a/n/a/n/a | 500 | 12 | 0.0240 | 0.0132-0.0403 | 0.0130 | 0.0073-0.0220 | 0.042 | 0.024 | 0.57 | 0.0130-0.0198 | 0.489 |
| hull | classic_cruise_1900 | 7.0 | reportable | n/a/n/a/n/a | 500 | 16 | 0.0320 | 0.0192-0.0502 | 0.0175 | 0.0094-0.0269 | 0.048 | 0.032 | 0.67 | 0.0150-0.0333 | 0.319 |
| hull | classic_cruise_1900 | 7.0 | reportable | n/a/n/a/n/a | 500 | 13 | 0.0260 | 0.0147-0.0428 | 0.0163 | 0.0080-0.0270 | 0.042 | 0.030 | 0.70 | 0.0160-0.0301 | 0.441 |
| hull | classic_cruise_1900 | 7.0 | reportable | n/a/n/a/n/a | 300 | 281 | 0.9367 | 0.9048-0.9601 | n/a | n/a | 0.937 | n/a | n/a | n/a | n/a |
| hull | classic_cruise_1900 | 7.0 | reportable | n/a/n/a/n/a | 300 | 293 | 0.9767 | 0.9547-0.9895 | n/a | n/a | 0.977 | n/a | n/a | n/a | n/a |
| hull | classic_cruise_1900 | 7.0 | reportable | n/a/n/a/n/a | 300 | 292 | 0.9733 | 0.9503-0.9873 | n/a | n/a | 0.977 | n/a | n/a | n/a | n/a |
| hull | classic_cruise_1900 | 7.0 | reportable | n/a/n/a/n/a | 300 | 11 | 0.0367 | 0.0196-0.0626 | 0.0279 | 0.0152-0.0465 | 0.063 | 0.049 | 0.78 | 0.0239-0.0372 | 0.231 |
| hull | classic_cruise_1900 | 7.0 | reportable | n/a/n/a/n/a | 300 | 0 | 0.0000 | 0.0000-0.0083 | 0.0000 | 0.0000-0.0000 | 0.000 | 0.000 | n/a | 0.0000-0.0000 | -1.469 |
| hull | classic_cruise_1900 | 7.0 | reportable | n/a/n/a/n/a | 300 | 6 | 0.0200 | 0.0084-0.0408 | 0.0120 | 0.0044-0.0236 | 0.030 | 0.021 | 0.71 | 0.0112-0.0120 | 0.468 |
| hull | classic_cruise_1900 | 12.0 | reportable | n/a/n/a/n/a | 500 | 103 | 0.2060 | 0.1723-0.2431 | n/a | n/a | 0.228 | n/a | n/a | n/a | n/a |
| hull | classic_cruise_1900 | 12.0 | reportable | n/a/n/a/n/a | 500 | 97 | 0.1940 | 0.1612-0.2304 | n/a | n/a | 0.236 | n/a | n/a | n/a | n/a |
| hull | classic_cruise_1900 | 12.0 | reportable | n/a/n/a/n/a | 500 | 97 | 0.1940 | 0.1612-0.2304 | n/a | n/a | 0.234 | n/a | n/a | n/a | n/a |
| hull | expedition_cruise_450 | 7.0 | reportable | n/a/n/a/n/a | 500 | 4 | 0.0080 | 0.0027-0.0189 | 0.0055 | 0.0000-0.0122 | 0.016 | 0.017 | 1.05 | 0.0055-0.0075 | -0.063 |
| hull | expedition_cruise_450 | 7.0 | reportable | n/a/n/a/n/a | 500 | 5 | 0.0100 | 0.0038-0.0218 | 0.0076 | 0.0000-0.0147 | 0.016 | 0.019 | 1.21 | 0.0076-0.0095 | 0.017 |
| hull | expedition_cruise_450 | 7.0 | reportable | n/a/n/a/n/a | 500 | 1 | 0.0020 | 0.0002-0.0093 | 0.0000 | 0.0000-0.0050 | 0.012 | 0.007 | 0.58 | 0.0000-0.0006 | -0.491 |
| hull | expedition_cruise_450 | 7.0 | reportable | n/a/n/a/n/a | 300 | 119 | 0.3967 | 0.3425-0.4528 | n/a | n/a | 0.450 | n/a | n/a | n/a | n/a |
| hull | expedition_cruise_450 | 7.0 | reportable | n/a/n/a/n/a | 300 | 121 | 0.4033 | 0.3490-0.4596 | n/a | n/a | 0.437 | n/a | n/a | n/a | n/a |
| hull | expedition_cruise_450 | 7.0 | reportable | n/a/n/a/n/a | 300 | 123 | 0.4100 | 0.3554-0.4663 | n/a | n/a | 0.450 | n/a | n/a | n/a | n/a |
| hull | expedition_cruise_450 | 12.0 | reportable | n/a/n/a/n/a | 500 | 14 | 0.0280 | 0.0161-0.0453 | 0.0274 | 0.0169-0.0433 | 0.044 | 0.045 | 1.03 | 0.0250-0.0274 | 0.052 |
| hull | expedition_cruise_450 | 12.0 | reportable | n/a/n/a/n/a | 500 | 18 | 0.0360 | 0.0223-0.0551 | 0.0333 | 0.0208-0.0490 | 0.050 | 0.052 | 1.04 | 0.0304-0.0381 | 0.032 |
| hull | expedition_cruise_450 | 12.0 | reportable | n/a/n/a/n/a | 500 | 20 | 0.0400 | 0.0254-0.0599 | 0.0291 | 0.0184-0.0430 | 0.048 | 0.047 | 0.99 | 0.0275-0.0350 | 0.075 |
| hull | spirit_cruise_3000 | 7.0 | reportable | n/a/n/a/n/a | 300 | 2 | 0.0067 | 0.0014-0.0212 | n/a | n/a | 0.007 | n/a | n/a | 0.0025-0.0025 | n/a |
| hull | spirit_cruise_3000 | 7.0 | reportable | n/a/n/a/n/a | 500 | 22 | 0.0440 | 0.0286-0.0647 | 0.0351 | 0.0199-0.0533 | 0.070 | 0.059 | 0.84 | 0.0240-0.0467 | 0.139 |
| hull | spirit_cruise_3000 | 7.0 | reportable | n/a/n/a/n/a | 500 | 25 | 0.0500 | 0.0334-0.0718 | 0.0340 | 0.0206-0.0519 | 0.072 | 0.058 | 0.80 | 0.0226-0.0465 | 0.151 |
| hull | spirit_cruise_3000 | 7.0 | reportable | n/a/n/a/n/a | 500 | 22 | 0.0440 | 0.0286-0.0647 | 0.0300 | 0.0173-0.0478 | 0.066 | 0.051 | 0.78 | 0.0214-0.0439 | 0.256 |
| hull | spirit_cruise_3000 | 7.0 | reportable | n/a/n/a/n/a | 300 | 298 | 0.9933 | 0.9788-0.9986 | n/a | n/a | 0.993 | n/a | n/a | n/a | n/a |
| hull | spirit_cruise_3000 | 7.0 | reportable | n/a/n/a/n/a | 300 | 299 | 0.9967 | 0.9845-0.9996 | n/a | n/a | 0.997 | n/a | n/a | n/a | n/a |
| hull | spirit_cruise_3000 | 7.0 | reportable | n/a/n/a/n/a | 300 | 299 | 0.9967 | 0.9845-0.9996 | n/a | n/a | 0.997 | n/a | n/a | n/a | n/a |
| hull | spirit_cruise_3000 | 7.0 | reportable | n/a/n/a/n/a | 300 | 14 | 0.0467 | 0.0270-0.0750 | 0.0415 | 0.0225-0.0706 | 0.077 | 0.065 | 0.85 | 0.0260-0.0511 | 0.049 |
| hull | spirit_cruise_3000 | 7.0 | reportable | n/a/n/a/n/a | 300 | 0 | 0.0000 | 0.0000-0.0083 | 0.0001 | 0.0000-0.0035 | 0.007 | 0.003 | 0.50 | 0.0000-0.0001 | -0.174 |
| hull | spirit_cruise_3000 | 12.0 | reportable | n/a/n/a/n/a | 500 | 135 | 0.2700 | 0.2325-0.3102 | n/a | n/a | 0.308 | n/a | n/a | n/a | n/a |
| hull | spirit_cruise_3000 | 12.0 | reportable | n/a/n/a/n/a | 500 | 153 | 0.3060 | 0.2668-0.3474 | n/a | n/a | 0.340 | n/a | n/a | n/a | n/a |
| hull | spirit_cruise_3000 | 12.0 | reportable | n/a/n/a/n/a | 500 | 150 | 0.3000 | 0.2611-0.3412 | n/a | n/a | 0.352 | n/a | n/a | n/a | n/a |

## Paired contrasts

Cells differing in exactly one coordinate, matched seed by seed. `identical imports` is the fraction of shared seeds whose realised boarding cohort is unchanged — a pairing validity check, since an arm that consumes a shared random stream decorrelates the pair. `var reduction` is how much less variance the paired difference carries than the unpaired one. `gained/lost` are McNemar's discordant pairs, and `predicted` is the delta-method posting change implied by the margin shift, printed for contrast with the observed one rather than in place of it.

| coordinate | platform | days | seeds | identical imports | margin shift | shift CI | var reduction | gained/lost | observed | predicted | exact p |
|---|---|---|---|---|---|---|---|---|---|---|---|
| contact_class_exponent | classic_cruise_1900 | 7.0 | 500 | 1.000 | 0.00012 | -0.00026-0.00049 | 6.7 | 8/4 | 0.0080 | 0.0002 | 0.388 |
| contact_class_exponent | classic_cruise_1900 | 7.0 | 500 | 1.000 | 0.00017 | -0.00029-0.00061 | 5.3 | 6/5 | 0.0020 | 0.0002 | 1.000 |
| num_epochs | classic_cruise_1900 | 7.0 | 500 | 1.000 | 0.00980 | 0.00841-0.01143 | 1.6 | 91/0 | 0.1820 | 0.0196 | 0.000 |
| contact_class_exponent | classic_cruise_1900 | 7.0 | 500 | 1.000 | 0.00005 | -0.00040-0.00056 | 4.3 | 4/7 | -0.0060 | 0.0001 | 0.549 |
| num_epochs | classic_cruise_1900 | 7.0 | 500 | 1.000 | 0.00999 | 0.00844-0.01164 | 1.7 | 82/1 | 0.1620 | 0.0180 | 0.000 |
| num_epochs | classic_cruise_1900 | 7.0 | 500 | 1.000 | 0.00959 | 0.00809-0.01100 | 1.7 | 86/2 | 0.1680 | 0.0269 | 0.000 |
| density_exponent | classic_cruise_1900 | 7.0 | 300 | 1.000 | 0.01569 | 0.01308-0.01829 | 4.9 | 13/1 | 0.0400 | 0.0026 | 0.002 |
| density_exponent | classic_cruise_1900 | 7.0 | 300 | 1.000 | 0.01841 | 0.01626-0.02072 | 5.3 | 11/0 | 0.0367 | 0.0031 | 0.001 |
| density_exponent | classic_cruise_1900 | 7.0 | 300 | 1.000 | 0.00272 | 0.00030-0.00506 | 4.3 | 3/4 | -0.0033 | 0.0009 | 1.000 |
| num_agents | classic_cruise_1900 | 7.0 | 300 | 0.047 | -0.00313 | -0.00432--0.00209 | 1.0 | 0/11 | -0.0367 | -0.0021 | 0.001 |
| num_agents | classic_cruise_1900 | 7.0 | 300 | 0.133 | -0.00176 | -0.00323--0.00007 | 1.0 | 6/11 | -0.0167 | -0.0018 | 0.332 |
| num_agents | classic_cruise_1900 | 7.0 | 300 | 0.277 | 0.00137 | 0.00060-0.00239 | 1.0 | 6/0 | 0.0200 | 0.0005 | 0.031 |
| contact_class_exponent | classic_cruise_1900 | 12.0 | 500 | 1.000 | 0.00031 | -0.00124-0.00161 | 3.9 | 26/32 | -0.0120 | 0.0007 | 0.512 |
| contact_class_exponent | classic_cruise_1900 | 12.0 | 500 | 1.000 | -0.00004 | -0.00162-0.00123 | 3.6 | 29/35 | -0.0120 | -0.0001 | 0.532 |
| contact_class_exponent | classic_cruise_1900 | 12.0 | 500 | 1.000 | -0.00035 | -0.00174-0.00074 | 4.5 | 26/26 | 0.0000 | -0.0010 | 1.000 |
| contact_class_exponent | expedition_cruise_450 | 7.0 | 500 | 1.000 | 0.00011 | -0.00016-0.00043 | 4.9 | 3/2 | 0.0020 | 0.0001 | 1.000 |
| contact_class_exponent | expedition_cruise_450 | 7.0 | 500 | 1.000 | -0.00013 | -0.00034-0.00006 | 7.7 | 0/3 | -0.0060 | -0.0001 | 0.250 |
| num_epochs | expedition_cruise_450 | 7.0 | 500 | 1.000 | 0.00140 | 0.00086-0.00197 | 2.7 | 10/0 | 0.0200 | 0.0008 | 0.002 |
| contact_class_exponent | expedition_cruise_450 | 7.0 | 500 | 1.000 | -0.00024 | -0.00052--0.00003 | 6.5 | 0/4 | -0.0080 | -0.0001 | 0.125 |
| num_epochs | expedition_cruise_450 | 7.0 | 500 | 1.000 | 0.00164 | 0.00104-0.00239 | 3.0 | 14/1 | 0.0260 | 0.0013 | 0.001 |
| num_epochs | expedition_cruise_450 | 7.0 | 500 | 1.000 | 0.00167 | 0.00102-0.00233 | 2.2 | 19/0 | 0.0380 | 0.0015 | 0.000 |
| density_exponent | expedition_cruise_450 | 7.0 | 300 | 1.000 | 0.00065 | -0.00189-0.00325 | 5.4 | 24/22 | 0.0067 | 0.0026 | 0.883 |
| density_exponent | expedition_cruise_450 | 7.0 | 300 | 1.000 | 0.00149 | -0.00088-0.00454 | 5.5 | 19/15 | 0.0133 | 0.0054 | 0.608 |
| density_exponent | expedition_cruise_450 | 7.0 | 300 | 1.000 | 0.00084 | -0.00180-0.00351 | 6.4 | 17/15 | 0.0067 | 0.0034 | 0.860 |
| contact_class_exponent | expedition_cruise_450 | 12.0 | 500 | 1.000 | 0.00036 | -0.00021-0.00088 | 4.7 | 7/3 | 0.0080 | 0.0003 | 0.344 |
| contact_class_exponent | expedition_cruise_450 | 12.0 | 500 | 1.000 | 0.00014 | -0.00031-0.00062 | 6.0 | 8/2 | 0.0120 | 0.0001 | 0.109 |
| contact_class_exponent | expedition_cruise_450 | 12.0 | 500 | 1.000 | -0.00022 | -0.00081-0.00041 | 4.7 | 7/5 | 0.0040 | -0.0003 | 0.774 |
| num_agents | spirit_cruise_3000 | 7.0 | 300 | 0.083 | 0.00329 | 0.00206-0.00450 | 1.1 | 13/1 | 0.0400 | 0.0033 | 0.002 |
| num_agents | spirit_cruise_3000 | 7.0 | 300 | 0.143 | -0.00025 | -0.00090-0.00030 | 1.0 | 0/2 | -0.0067 | -0.0001 | 0.500 |
| contact_class_exponent | spirit_cruise_3000 | 7.0 | 500 | 1.000 | -0.00004 | -0.00064-0.00051 | 5.4 | 8/5 | 0.0060 | -0.0001 | 0.581 |
| contact_class_exponent | spirit_cruise_3000 | 7.0 | 500 | 1.000 | -0.00024 | -0.00080-0.00034 | 5.8 | 8/8 | 0.0000 | -0.0004 | 1.000 |
| num_epochs | spirit_cruise_3000 | 7.0 | 500 | 1.000 | 0.01393 | 0.01209-0.01582 | 1.9 | 114/1 | 0.2260 | 0.0348 | 0.000 |
| contact_class_exponent | spirit_cruise_3000 | 7.0 | 500 | 1.000 | -0.00020 | -0.00068-0.00029 | 7.4 | 6/9 | -0.0060 | -0.0005 | 0.607 |
| num_epochs | spirit_cruise_3000 | 7.0 | 500 | 1.000 | 0.01478 | 0.01293-0.01649 | 1.8 | 128/0 | 0.2560 | 0.0547 | 0.000 |
| num_epochs | spirit_cruise_3000 | 7.0 | 500 | 1.000 | 0.01518 | 0.01341-0.01694 | 1.8 | 128/0 | 0.2560 | 0.0395 | 0.000 |
| density_exponent | spirit_cruise_3000 | 7.0 | 300 | 1.000 | 0.01085 | 0.00909-0.01252 | 4.0 | 1/0 | 0.0033 | 0.0036 | 1.000 |
| density_exponent | spirit_cruise_3000 | 7.0 | 300 | 1.000 | 0.01482 | 0.01306-0.01666 | 2.8 | 2/1 | 0.0033 | 0.0025 | 1.000 |
| density_exponent | spirit_cruise_3000 | 7.0 | 300 | 1.000 | 0.00397 | 0.00194-0.00568 | 3.0 | 1/1 | 0.0000 | 0.0007 | 1.000 |
| num_agents | spirit_cruise_3000 | 7.0 | 300 | 0.007 | -0.00354 | -0.00480--0.00224 | 1.0 | 0/14 | -0.0467 | -0.0047 | 0.000 |
| contact_class_exponent | spirit_cruise_3000 | 12.0 | 500 | 1.000 | 0.00082 | -0.00082-0.00242 | 3.8 | 49/31 | 0.0360 | 0.0035 | 0.057 |
| contact_class_exponent | spirit_cruise_3000 | 12.0 | 500 | 1.000 | 0.00102 | -0.00055-0.00258 | 3.8 | 49/34 | 0.0300 | 0.0036 | 0.124 |
| contact_class_exponent | spirit_cruise_3000 | 12.0 | 500 | 1.000 | 0.00020 | -0.00128-0.00189 | 3.8 | 35/38 | -0.0060 | 0.0008 | 0.815 |
