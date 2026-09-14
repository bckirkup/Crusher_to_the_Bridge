# Posting as a tail probability: the estimators, side by side

Posting rule: margin = max(reported AR passenger, crew) >= 3%, so posting is exactly a threshold crossing of a continuous quantity. `direct` is the binomial estimate; `modelled` is a generalised Pareto tail fitted above the 85% margin quantile and extrapolated to the threshold. The two check columns repeat both estimates at 2%, where the direct one is still well resolved: a model that misses there is not licensed to extrapolate, and `modelled/direct@2%` states that miss as a ratio rather than leaving it to be read off. `anchor scan` is the range the modelled estimate covers as the anchor is moved across 30%-5% exceedance: an estimate that moves with the anchor is fitting the body, not a tail. `xi` is the fitted shape; xi < 0 is a bounded tail.

| arm | platform | days | rung | crew c/h/d | voyages | crossings | direct | direct CI | modelled | modelled CI | direct@2% | modelled@2% | modelled/direct@2% | anchor scan | xi |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| ladder | classic_cruise_1900 | 7.0 | renewal_stationary | n/a/n/a/n/a | 1000 | 47 | 0.0470 | 0.0352-0.0614 | 0.0347 | 0.0254-0.0489 | 0.067 | 0.056 | 0.84 | 0.0237-0.0477 | 0.151 |
| ladder | classic_cruise_1900 | 7.0 | reportable | 0.00/n/a/0.00 | 200 | 15 | 0.0750 | 0.0445-0.1177 | 0.0543 | 0.0254-0.0943 | 0.090 | 0.082 | 0.92 | 0.0323-0.0543 | -0.138 |
| ladder | classic_cruise_1900 | 7.0 | reportable | 0.25/0.5/0.00 | 200 | 15 | 0.0750 | 0.0445-0.1177 | 0.0543 | 0.0312-0.0943 | 0.090 | 0.082 | 0.92 | 0.0317-0.0543 | -0.138 |
| ladder | classic_cruise_1900 | 7.0 | reportable | 0.25/1.0/0.00 | 200 | 15 | 0.0750 | 0.0445-0.1177 | 0.0534 | 0.0300-0.0917 | 0.090 | 0.081 | 0.90 | 0.0314-0.0534 | -0.114 |
| ladder | classic_cruise_1900 | 7.0 | reportable | 0.25/2.0/0.00 | 200 | 15 | 0.0750 | 0.0445-0.1177 | 0.0534 | 0.0281-0.0919 | 0.090 | 0.081 | 0.90 | 0.0314-0.0534 | -0.114 |
| ladder | classic_cruise_1900 | 7.0 | reportable | 0.25/n/a/0.00 | 200 | 15 | 0.0750 | 0.0445-0.1177 | 0.0534 | 0.0320-0.0889 | 0.090 | 0.081 | 0.90 | 0.0306-0.0534 | -0.114 |
| ladder | classic_cruise_1900 | 7.0 | reportable | 0.50/0.5/0.00 | 200 | 15 | 0.0750 | 0.0445-0.1177 | 0.0543 | 0.0305-0.0945 | 0.090 | 0.082 | 0.92 | 0.0317-0.0543 | -0.138 |
| ladder | classic_cruise_1900 | 7.0 | reportable | 0.50/1.0/0.00 | 200 | 15 | 0.0750 | 0.0445-0.1177 | 0.0534 | 0.0280-0.0924 | 0.090 | 0.081 | 0.90 | 0.0418-0.0534 | -0.114 |
| ladder | classic_cruise_1900 | 7.0 | reportable | 0.50/2.0/0.00 | 200 | 15 | 0.0750 | 0.0445-0.1177 | 0.0534 | 0.0305-0.0927 | 0.090 | 0.081 | 0.90 | 0.0418-0.0534 | -0.114 |
| ladder | classic_cruise_1900 | 7.0 | reportable | 0.50/n/a/0.00 | 200 | 15 | 0.0750 | 0.0445-0.1177 | 0.0611 | 0.0328-0.1047 | 0.095 | 0.089 | 0.94 | 0.0456-0.0611 | -0.313 |
| ladder | classic_cruise_1900 | 7.0 | reportable | 0.75/0.5/0.00 | 200 | 15 | 0.0750 | 0.0445-0.1177 | 0.0534 | 0.0299-0.0888 | 0.090 | 0.081 | 0.90 | 0.0418-0.0534 | -0.114 |
| ladder | classic_cruise_1900 | 7.0 | reportable | 0.75/1.0/0.00 | 200 | 14 | 0.0700 | 0.0407-0.1116 | 0.0532 | 0.0293-0.0886 | 0.090 | 0.081 | 0.90 | 0.0416-0.0532 | -0.110 |
| ladder | classic_cruise_1900 | 7.0 | reportable | 0.75/2.0/0.00 | 200 | 13 | 0.0650 | 0.0369-0.1055 | 0.0504 | 0.0252-0.0935 | 0.085 | 0.077 | 0.91 | 0.0392-0.0504 | -0.076 |
| ladder | classic_cruise_1900 | 7.0 | reportable | 0.75/n/a/0.00 | 200 | 14 | 0.0700 | 0.0407-0.1116 | 0.0591 | 0.0328-0.0980 | 0.095 | 0.088 | 0.93 | 0.0470-0.0591 | -0.216 |
| ladder | classic_cruise_1900 | 7.0 | reportable | 1.00/0.5/0.00 | 200 | 15 | 0.0750 | 0.0445-0.1177 | 0.0534 | 0.0282-0.0959 | 0.090 | 0.081 | 0.90 | 0.0418-0.0534 | -0.114 |
| ladder | classic_cruise_1900 | 7.0 | reportable | 1.00/1.0/0.00 | 200 | 13 | 0.0650 | 0.0369-0.1055 | 0.0490 | 0.0256-0.0921 | 0.085 | 0.076 | 0.90 | 0.0391-0.0490 | -0.014 |
| ladder | classic_cruise_1900 | 7.0 | reportable | 1.00/2.0/0.00 | 200 | 14 | 0.0700 | 0.0407-0.1116 | 0.0568 | 0.0293-0.0949 | 0.090 | 0.085 | 0.94 | 0.0448-0.0568 | -0.189 |
| ladder | classic_cruise_1900 | 7.0 | reportable | 1.00/n/a/0.00 | 200 | 14 | 0.0700 | 0.0407-0.1116 | 0.0592 | 0.0308-0.0966 | 0.095 | 0.088 | 0.93 | 0.0470-0.0592 | -0.219 |
| ladder | classic_cruise_1900 | 7.0 | reportable | 1.00/n/a/0.50 | 200 | 17 | 0.0850 | 0.0523-0.1296 | 0.0709 | 0.0403-0.1171 | 0.105 | 0.099 | 0.94 | 0.0404-0.0709 | -0.458 |
| ladder | classic_cruise_1900 | 7.0 | reportable | 1.00/n/a/1.00 | 200 | 15 | 0.0750 | 0.0445-0.1177 | 0.0638 | 0.0344-0.1043 | 0.100 | 0.092 | 0.92 | 0.0399-0.0638 | -0.365 |
| ladder | classic_cruise_1900 | 7.0 | reportable | n/a/n/a/n/a | 200 | 10 | 0.0500 | 0.0260-0.0869 | 0.0383 | 0.0173-0.0667 | 0.075 | 0.063 | 0.85 | 0.0319-0.0383 | 0.067 |
| ladder | classic_cruise_1900 | 7.0 | reportable | n/a/n/a/n/a | 200 | 10 | 0.0500 | 0.0260-0.0869 | 0.0375 | 0.0205-0.0730 | 0.070 | 0.061 | 0.87 | 0.0324-0.0375 | 0.050 |
| ladder | classic_cruise_1900 | 7.0 | reportable | n/a/n/a/n/a | 200 | 11 | 0.0550 | 0.0296-0.0932 | 0.0411 | 0.0205-0.0732 | 0.075 | 0.066 | 0.88 | 0.0246-0.0411 | 0.029 |
| ladder | classic_cruise_1900 | 7.0 | reportable | n/a/n/a/n/a | 1000 | 41 | 0.0410 | 0.0300-0.0546 | 0.0295 | 0.0199-0.0400 | 0.062 | 0.050 | 0.81 | 0.0249-0.0420 | 0.213 |
| ladder | classic_cruise_1900 | 7.0 | symptomatic | n/a/n/a/n/a | 1000 | 39 | 0.0390 | 0.0283-0.0524 | 0.0274 | 0.0194-0.0375 | 0.058 | 0.047 | 0.82 | 0.0165-0.0392 | 0.186 |
| ladder | classic_cruise_1900 | 12.0 | renewal_stationary | n/a/n/a/n/a | 1000 | 220 | 0.2200 | 0.1952-0.2465 | n/a | n/a | 0.249 | n/a | n/a | n/a | n/a |
| ladder | classic_cruise_1900 | 12.0 | reportable | 0.00/n/a/0.00 | 200 | 39 | 0.1950 | 0.1447-0.2541 | n/a | n/a | 0.210 | n/a | n/a | n/a | n/a |
| ladder | classic_cruise_1900 | 12.0 | reportable | 0.25/0.5/0.00 | 200 | 39 | 0.1950 | 0.1447-0.2541 | n/a | n/a | 0.210 | n/a | n/a | n/a | n/a |
| ladder | classic_cruise_1900 | 12.0 | reportable | 0.25/1.0/0.00 | 200 | 40 | 0.2000 | 0.1491-0.2595 | n/a | n/a | 0.215 | n/a | n/a | n/a | n/a |
| ladder | classic_cruise_1900 | 12.0 | reportable | 0.25/2.0/0.00 | 200 | 40 | 0.2000 | 0.1491-0.2595 | n/a | n/a | 0.215 | n/a | n/a | n/a | n/a |
| ladder | classic_cruise_1900 | 12.0 | reportable | 0.25/n/a/0.00 | 200 | 39 | 0.1950 | 0.1447-0.2541 | n/a | n/a | 0.215 | n/a | n/a | n/a | n/a |
| ladder | classic_cruise_1900 | 12.0 | reportable | 0.50/0.5/0.00 | 200 | 39 | 0.1950 | 0.1447-0.2541 | n/a | n/a | 0.210 | n/a | n/a | n/a | n/a |
| ladder | classic_cruise_1900 | 12.0 | reportable | 0.50/1.0/0.00 | 200 | 39 | 0.1950 | 0.1447-0.2541 | n/a | n/a | 0.215 | n/a | n/a | n/a | n/a |
| ladder | classic_cruise_1900 | 12.0 | reportable | 0.50/2.0/0.00 | 200 | 39 | 0.1950 | 0.1447-0.2541 | n/a | n/a | 0.215 | n/a | n/a | n/a | n/a |
| ladder | classic_cruise_1900 | 12.0 | reportable | 0.50/n/a/0.00 | 200 | 40 | 0.2000 | 0.1491-0.2595 | n/a | n/a | 0.220 | n/a | n/a | n/a | n/a |
| ladder | classic_cruise_1900 | 12.0 | reportable | 0.75/0.5/0.00 | 200 | 39 | 0.1950 | 0.1447-0.2541 | n/a | n/a | 0.215 | n/a | n/a | n/a | n/a |
| ladder | classic_cruise_1900 | 12.0 | reportable | 0.75/1.0/0.00 | 200 | 39 | 0.1950 | 0.1447-0.2541 | n/a | n/a | 0.215 | n/a | n/a | n/a | n/a |
| ladder | classic_cruise_1900 | 12.0 | reportable | 0.75/2.0/0.00 | 200 | 38 | 0.1900 | 0.1403-0.2486 | n/a | n/a | 0.210 | n/a | n/a | n/a | n/a |
| ladder | classic_cruise_1900 | 12.0 | reportable | 0.75/n/a/0.00 | 200 | 41 | 0.2050 | 0.1535-0.2649 | n/a | n/a | 0.220 | n/a | n/a | n/a | n/a |
| ladder | classic_cruise_1900 | 12.0 | reportable | 1.00/0.5/0.00 | 200 | 39 | 0.1950 | 0.1447-0.2541 | n/a | n/a | 0.215 | n/a | n/a | n/a | n/a |
| ladder | classic_cruise_1900 | 12.0 | reportable | 1.00/1.0/0.00 | 200 | 39 | 0.1950 | 0.1447-0.2541 | n/a | n/a | 0.215 | n/a | n/a | n/a | n/a |
| ladder | classic_cruise_1900 | 12.0 | reportable | 1.00/2.0/0.00 | 200 | 40 | 0.2000 | 0.1491-0.2595 | n/a | n/a | 0.220 | n/a | n/a | n/a | n/a |
| ladder | classic_cruise_1900 | 12.0 | reportable | 1.00/n/a/0.00 | 200 | 41 | 0.2050 | 0.1535-0.2649 | n/a | n/a | 0.220 | n/a | n/a | n/a | n/a |
| ladder | classic_cruise_1900 | 12.0 | reportable | 1.00/n/a/0.50 | 200 | 43 | 0.2150 | 0.1624-0.2758 | n/a | n/a | 0.230 | n/a | n/a | n/a | n/a |
| ladder | classic_cruise_1900 | 12.0 | reportable | 1.00/n/a/1.00 | 200 | 40 | 0.2000 | 0.1491-0.2595 | n/a | n/a | 0.210 | n/a | n/a | n/a | n/a |
| ladder | classic_cruise_1900 | 12.0 | reportable | n/a/n/a/n/a | 200 | 37 | 0.1850 | 0.1359-0.2431 | n/a | n/a | 0.215 | n/a | n/a | n/a | n/a |
| ladder | classic_cruise_1900 | 12.0 | reportable | n/a/n/a/n/a | 200 | 35 | 0.1750 | 0.1272-0.2321 | n/a | n/a | 0.200 | n/a | n/a | n/a | n/a |
| ladder | classic_cruise_1900 | 12.0 | reportable | n/a/n/a/n/a | 200 | 38 | 0.1900 | 0.1403-0.2486 | n/a | n/a | 0.200 | n/a | n/a | n/a | n/a |
| ladder | classic_cruise_1900 | 12.0 | reportable | n/a/n/a/n/a | 1000 | 205 | 0.2050 | 0.1809-0.2309 | n/a | n/a | 0.229 | n/a | n/a | n/a | n/a |
| ladder | classic_cruise_1900 | 12.0 | symptomatic | n/a/n/a/n/a | 1000 | 203 | 0.2030 | 0.1789-0.2288 | n/a | n/a | 0.225 | n/a | n/a | n/a | n/a |
| ladder | expedition_cruise_450 | 7.0 | renewal_stationary | n/a/n/a/n/a | 1000 | 7 | 0.0070 | 0.0031-0.0137 | 0.0064 | 0.0005-0.0108 | 0.013 | 0.015 | 1.14 | 0.0062-0.0064 | -0.016 |
| ladder | expedition_cruise_450 | 7.0 | reportable | n/a/n/a/n/a | 1000 | 7 | 0.0070 | 0.0031-0.0137 | 0.0035 | 0.0000-0.0099 | 0.014 | 0.017 | 1.21 | 0.0035-0.0074 | -0.228 |
| ladder | expedition_cruise_450 | 7.0 | symptomatic | n/a/n/a/n/a | 1000 | 3 | 0.0030 | 0.0008-0.0080 | 0.0003 | 0.0000-0.0061 | 0.010 | 0.009 | 0.91 | 0.0003-0.0045 | -0.332 |
| ladder | expedition_cruise_450 | 12.0 | renewal_stationary | n/a/n/a/n/a | 1000 | 33 | 0.0330 | 0.0232-0.0455 | 0.0270 | 0.0185-0.0355 | 0.041 | 0.044 | 1.07 | 0.0270-0.0311 | -0.004 |
| ladder | expedition_cruise_450 | 12.0 | reportable | n/a/n/a/n/a | 1000 | 26 | 0.0260 | 0.0175-0.0373 | 0.0272 | 0.0198-0.0363 | 0.049 | 0.047 | 0.97 | 0.0272-0.0316 | 0.092 |
| ladder | expedition_cruise_450 | 12.0 | symptomatic | n/a/n/a/n/a | 1000 | 25 | 0.0250 | 0.0166-0.0361 | 0.0260 | 0.0184-0.0349 | 0.047 | 0.045 | 0.95 | 0.0253-0.0297 | 0.048 |
| ladder | spirit_cruise_3000 | 7.0 | renewal_stationary | n/a/n/a/n/a | 1000 | 52 | 0.0520 | 0.0395-0.0671 | 0.0390 | 0.0284-0.0520 | 0.077 | 0.064 | 0.83 | 0.0261-0.0522 | -0.017 |
| ladder | spirit_cruise_3000 | 7.0 | reportable | n/a/n/a/n/a | 1000 | 39 | 0.0390 | 0.0283-0.0524 | 0.0260 | 0.0173-0.0359 | 0.062 | 0.046 | 0.74 | 0.0195-0.0395 | 0.289 |
| ladder | spirit_cruise_3000 | 7.0 | symptomatic | n/a/n/a/n/a | 1000 | 44 | 0.0440 | 0.0326-0.0581 | 0.0295 | 0.0211-0.0416 | 0.064 | 0.051 | 0.79 | 0.0200-0.0438 | 0.197 |
| ladder | spirit_cruise_3000 | 12.0 | renewal_stationary | n/a/n/a/n/a | 1000 | 244 | 0.2440 | 0.2181-0.2713 | n/a | n/a | 0.284 | n/a | n/a | n/a | n/a |
| ladder | spirit_cruise_3000 | 12.0 | reportable | n/a/n/a/n/a | 1000 | 270 | 0.2700 | 0.2432-0.2982 | n/a | n/a | 0.318 | n/a | n/a | n/a | n/a |
| ladder | spirit_cruise_3000 | 12.0 | symptomatic | n/a/n/a/n/a | 1000 | 258 | 0.2580 | 0.2316-0.2858 | n/a | n/a | 0.307 | n/a | n/a | n/a | n/a |
| shipped | classic_cruise_1900 | 7.0 | shipped | n/a/n/a/n/a | 150 | 58 | 0.3867 | 0.3115-0.4662 | n/a | n/a | 0.460 | n/a | n/a | n/a | n/a |
| shipped | classic_cruise_1900 | 7.0 | shipped | n/a/n/a/n/a | 150 | 79 | 0.5267 | 0.4469-0.6054 | n/a | n/a | 0.640 | n/a | n/a | n/a | n/a |
| shipped | classic_cruise_1900 | 7.0 | shipped | n/a/n/a/n/a | 150 | 69 | 0.4600 | 0.3816-0.5399 | n/a | n/a | 0.580 | n/a | n/a | n/a | n/a |
| shipped | classic_cruise_1900 | 7.0 | shipped | n/a/n/a/n/a | 1150 | 638 | 0.5548 | 0.5260-0.5833 | n/a | n/a | 0.656 | n/a | n/a | n/a | n/a |
| shipped | classic_cruise_1900 | 7.0 | shipped | n/a/n/a/n/a | 150 | 78 | 0.5200 | 0.4403-0.5989 | n/a | n/a | 0.640 | n/a | n/a | n/a | n/a |
| shipped | classic_cruise_1900 | 7.0 | shipped | n/a/n/a/n/a | 150 | 85 | 0.5667 | 0.4867-0.6441 | n/a | n/a | 0.673 | n/a | n/a | n/a | n/a |
| shipped | classic_cruise_1900 | 7.0 | shipped | n/a/n/a/n/a | 150 | 104 | 0.6933 | 0.6164-0.7629 | n/a | n/a | 0.767 | n/a | n/a | n/a | n/a |
| shipped | classic_cruise_1900 | 12.0 | shipped | n/a/n/a/n/a | 150 | 116 | 0.7733 | 0.7015-0.8347 | n/a | n/a | 0.820 | n/a | n/a | n/a | n/a |
| shipped | classic_cruise_1900 | 12.0 | shipped | n/a/n/a/n/a | 150 | 136 | 0.9067 | 0.8524-0.9455 | n/a | n/a | 0.927 | n/a | n/a | n/a | n/a |
| shipped | classic_cruise_1900 | 12.0 | shipped | n/a/n/a/n/a | 150 | 138 | 0.9200 | 0.8685-0.9555 | n/a | n/a | 0.933 | n/a | n/a | n/a | n/a |
| shipped | classic_cruise_1900 | 12.0 | shipped | n/a/n/a/n/a | 1150 | 1086 | 0.9443 | 0.9300-0.9565 | n/a | n/a | 0.963 | n/a | n/a | n/a | n/a |
| shipped | classic_cruise_1900 | 12.0 | shipped | n/a/n/a/n/a | 150 | 140 | 0.9333 | 0.8850-0.9652 | n/a | n/a | 0.960 | n/a | n/a | n/a | n/a |
| shipped | classic_cruise_1900 | 12.0 | shipped | n/a/n/a/n/a | 150 | 142 | 0.9467 | 0.9019-0.9745 | n/a | n/a | 0.967 | n/a | n/a | n/a | n/a |
| shipped | classic_cruise_1900 | 12.0 | shipped | n/a/n/a/n/a | 150 | 145 | 0.9667 | 0.9285-0.9872 | n/a | n/a | 0.980 | n/a | n/a | n/a | n/a |
| shipped | expedition_cruise_450 | 7.0 | shipped | n/a/n/a/n/a | 150 | 18 | 0.1200 | 0.0753-0.1791 | n/a | n/a | 0.180 | n/a | n/a | 0.1218-0.1243 | n/a |
| shipped | expedition_cruise_450 | 7.0 | shipped | n/a/n/a/n/a | 1150 | 124 | 0.1078 | 0.0909-0.1267 | 0.1080 | 0.0897-0.1263 | 0.163 | n/a | n/a | 0.1080-0.1127 | -0.626 |
| shipped | expedition_cruise_450 | 7.0 | shipped | n/a/n/a/n/a | 150 | 18 | 0.1200 | 0.0753-0.1791 | n/a | n/a | 0.187 | n/a | n/a | 0.1274-0.1284 | n/a |
| shipped | expedition_cruise_450 | 12.0 | shipped | n/a/n/a/n/a | 1000 | 304 | 0.3040 | 0.2761-0.3330 | n/a | n/a | 0.405 | n/a | n/a | n/a | n/a |
| shipped | spirit_cruise_3000 | 7.0 | shipped | n/a/n/a/n/a | 1000 | 695 | 0.6950 | 0.6659-0.7229 | n/a | n/a | 0.786 | n/a | n/a | n/a | n/a |
| shipped | spirit_cruise_3000 | 12.0 | shipped | n/a/n/a/n/a | 1000 | 992 | 0.9920 | 0.9850-0.9962 | n/a | n/a | 0.996 | n/a | n/a | n/a | n/a |

## Paired contrasts

Cells differing in exactly one coordinate, matched seed by seed. `identical imports` is the fraction of shared seeds whose realised boarding cohort is unchanged — a pairing validity check, since an arm that consumes a shared random stream decorrelates the pair. `var reduction` is how much less variance the paired difference carries than the unpaired one. `gained/lost` are McNemar's discordant pairs, and `predicted` is the delta-method posting change implied by the margin shift, printed for contrast with the observed one rather than in place of it.

| coordinate | platform | days | seeds | identical imports | margin shift | shift CI | var reduction | gained/lost | observed | predicted | exact p |
|---|---|---|---|---|---|---|---|---|---|---|---|
| num_epochs | classic_cruise_1900 | 7.0 | 1000 | 1.000 | 0.01058 | 0.00951-0.01183 | 2.0 | 174/1 | 0.1730 | 0.0249 | 0.000 |
| preboarding_crew_declaration_compliance | classic_cruise_1900 | 7.0 | 200 | 0.985 | -0.00000 | -0.00005-0.00003 | 3328.5 | 0/0 | 0.0000 | -0.0000 | n/a |
| preboarding_crew_declaration_compliance | classic_cruise_1900 | 7.0 | 200 | 0.965 | 0.00023 | -0.00003-0.00070 | 37.3 | 1/1 | 0.0000 | 0.0007 | 1.000 |
| preboarding_crew_declaration_compliance | classic_cruise_1900 | 7.0 | 200 | 0.935 | 0.00025 | -0.00033-0.00102 | 13.1 | 2/3 | -0.0050 | 0.0008 | 1.000 |
| preboarding_crew_declaration_compliance | classic_cruise_1900 | 7.0 | 200 | 0.925 | 0.00026 | -0.00032-0.00102 | 13.1 | 2/3 | -0.0050 | 0.0008 | 1.000 |
| num_epochs | classic_cruise_1900 | 7.0 | 200 | 1.000 | 0.00862 | 0.00590-0.01112 | 2.5 | 24/0 | 0.1200 | 0.0172 | 0.000 |
| preboarding_crew_recall_halflife_days | classic_cruise_1900 | 7.0 | 200 | 0.995 | -0.00002 | -0.00005-0.00000 | 4991.2 | 0/0 | 0.0000 | -0.0001 | n/a |
| preboarding_crew_recall_halflife_days | classic_cruise_1900 | 7.0 | 200 | 0.995 | -0.00002 | -0.00005-0.00000 | 4991.2 | 0/0 | 0.0000 | -0.0001 | n/a |
| preboarding_crew_recall_halflife_days | classic_cruise_1900 | 7.0 | 200 | 0.985 | -0.00001 | -0.00006-0.00002 | 3959.1 | 0/0 | 0.0000 | -0.0000 | n/a |
| preboarding_crew_declaration_compliance | classic_cruise_1900 | 7.0 | 200 | 1.000 | 0.00000 | 0.00000-0.00000 | n/a | 0/0 | 0.0000 | 0.0000 | n/a |
| preboarding_crew_declaration_compliance | classic_cruise_1900 | 7.0 | 200 | 0.980 | -0.00000 | -0.00005-0.00003 | 3327.1 | 0/0 | 0.0000 | -0.0000 | n/a |
| preboarding_crew_declaration_compliance | classic_cruise_1900 | 7.0 | 200 | 0.980 | -0.00000 | -0.00005-0.00003 | 3327.1 | 0/0 | 0.0000 | -0.0000 | n/a |
| num_epochs | classic_cruise_1900 | 7.0 | 200 | 1.000 | 0.00865 | 0.00596-0.01114 | 2.5 | 24/0 | 0.1200 | 0.0173 | 0.000 |
| preboarding_crew_recall_halflife_days | classic_cruise_1900 | 7.0 | 200 | 1.000 | 0.00000 | 0.00000-0.00000 | n/a | 0/0 | 0.0000 | 0.0000 | n/a |
| preboarding_crew_recall_halflife_days | classic_cruise_1900 | 7.0 | 200 | 0.990 | 0.00001 | -0.00001-0.00003 | 19410.7 | 0/0 | 0.0000 | 0.0000 | n/a |
| preboarding_crew_declaration_compliance | classic_cruise_1900 | 7.0 | 200 | 0.985 | 0.00001 | -0.00001-0.00004 | 10153.2 | 0/0 | 0.0000 | 0.0000 | n/a |
| preboarding_crew_declaration_compliance | classic_cruise_1900 | 7.0 | 200 | 0.980 | 0.00001 | -0.00002-0.00004 | 7341.9 | 0/1 | -0.0050 | 0.0000 | 1.000 |
| preboarding_crew_declaration_compliance | classic_cruise_1900 | 7.0 | 200 | 0.975 | -0.00012 | -0.00044-0.00008 | 65.1 | 0/2 | -0.0100 | -0.0003 | 0.500 |
| num_epochs | classic_cruise_1900 | 7.0 | 200 | 1.000 | 0.00887 | 0.00612-0.01132 | 2.4 | 25/0 | 0.1250 | 0.0177 | 0.000 |
| preboarding_crew_recall_halflife_days | classic_cruise_1900 | 7.0 | 200 | 0.990 | 0.00001 | -0.00001-0.00003 | 19410.7 | 0/0 | 0.0000 | 0.0000 | n/a |
| preboarding_crew_declaration_compliance | classic_cruise_1900 | 7.0 | 200 | 0.985 | 0.00001 | -0.00001-0.00004 | 10153.2 | 0/0 | 0.0000 | 0.0000 | n/a |
| preboarding_crew_declaration_compliance | classic_cruise_1900 | 7.0 | 200 | 0.975 | -0.00013 | -0.00045-0.00004 | 67.0 | 0/2 | -0.0100 | -0.0004 | 0.500 |
| preboarding_crew_declaration_compliance | classic_cruise_1900 | 7.0 | 200 | 0.955 | 0.00014 | -0.00032-0.00068 | 21.6 | 1/2 | -0.0050 | 0.0004 | 1.000 |
| num_epochs | classic_cruise_1900 | 7.0 | 200 | 1.000 | 0.00887 | 0.00612-0.01132 | 2.4 | 25/0 | 0.1250 | 0.0177 | 0.000 |
| preboarding_crew_declaration_compliance | classic_cruise_1900 | 7.0 | 200 | 0.980 | 0.00024 | -0.00001-0.00068 | 37.7 | 1/1 | 0.0000 | 0.0007 | 1.000 |
| preboarding_crew_declaration_compliance | classic_cruise_1900 | 7.0 | 200 | 0.950 | 0.00025 | -0.00033-0.00103 | 13.2 | 2/3 | -0.0050 | 0.0008 | 1.000 |
| preboarding_crew_declaration_compliance | classic_cruise_1900 | 7.0 | 200 | 0.940 | 0.00026 | -0.00032-0.00103 | 13.2 | 2/3 | -0.0050 | 0.0008 | 1.000 |
| num_epochs | classic_cruise_1900 | 7.0 | 200 | 1.000 | 0.00872 | 0.00607-0.01120 | 2.5 | 24/0 | 0.1200 | 0.0174 | 0.000 |
| preboarding_crew_recall_halflife_days | classic_cruise_1900 | 7.0 | 200 | 0.980 | -0.00000 | -0.00005-0.00003 | 3327.1 | 0/0 | 0.0000 | -0.0000 | n/a |
| preboarding_crew_recall_halflife_days | classic_cruise_1900 | 7.0 | 200 | 0.980 | -0.00000 | -0.00005-0.00003 | 3327.1 | 0/0 | 0.0000 | -0.0000 | n/a |
| preboarding_crew_recall_halflife_days | classic_cruise_1900 | 7.0 | 200 | 0.965 | 0.00022 | -0.00003-0.00067 | 37.4 | 1/1 | 0.0000 | 0.0007 | 1.000 |
| preboarding_crew_declaration_compliance | classic_cruise_1900 | 7.0 | 200 | 0.980 | -0.00000 | -0.00005-0.00003 | 3327.1 | 0/0 | 0.0000 | -0.0000 | n/a |
| preboarding_crew_declaration_compliance | classic_cruise_1900 | 7.0 | 200 | 0.980 | -0.00000 | -0.00005-0.00003 | 3327.1 | 0/0 | 0.0000 | -0.0000 | n/a |
| num_epochs | classic_cruise_1900 | 7.0 | 200 | 1.000 | 0.00865 | 0.00596-0.01114 | 2.5 | 24/0 | 0.1200 | 0.0173 | 0.000 |
| preboarding_crew_recall_halflife_days | classic_cruise_1900 | 7.0 | 200 | 1.000 | 0.00000 | 0.00000-0.00000 | n/a | 0/0 | 0.0000 | 0.0000 | n/a |
| preboarding_crew_recall_halflife_days | classic_cruise_1900 | 7.0 | 200 | 0.985 | 0.00023 | -0.00001-0.00066 | 37.8 | 1/1 | 0.0000 | 0.0007 | 1.000 |
| preboarding_crew_declaration_compliance | classic_cruise_1900 | 7.0 | 200 | 0.995 | -0.00001 | -0.00002-0.00000 | 27111.5 | 0/1 | -0.0050 | -0.0000 | 1.000 |
| preboarding_crew_declaration_compliance | classic_cruise_1900 | 7.0 | 200 | 0.990 | -0.00013 | -0.00045-0.00005 | 65.6 | 0/2 | -0.0100 | -0.0004 | 0.500 |
| num_epochs | classic_cruise_1900 | 7.0 | 200 | 1.000 | 0.00876 | 0.00607-0.01123 | 2.5 | 24/0 | 0.1200 | 0.0175 | 0.000 |
| preboarding_crew_recall_halflife_days | classic_cruise_1900 | 7.0 | 200 | 0.985 | 0.00023 | -0.00001-0.00066 | 37.8 | 1/1 | 0.0000 | 0.0007 | 1.000 |
| preboarding_crew_declaration_compliance | classic_cruise_1900 | 7.0 | 200 | 0.990 | -0.00015 | -0.00045-0.00002 | 67.5 | 0/2 | -0.0100 | -0.0004 | 0.500 |
| preboarding_crew_declaration_compliance | classic_cruise_1900 | 7.0 | 200 | 0.970 | 0.00012 | -0.00034-0.00066 | 21.6 | 1/2 | -0.0050 | 0.0003 | 1.000 |
| num_epochs | classic_cruise_1900 | 7.0 | 200 | 1.000 | 0.00876 | 0.00607-0.01123 | 2.5 | 24/0 | 0.1200 | 0.0175 | 0.000 |
| preboarding_crew_declaration_compliance | classic_cruise_1900 | 7.0 | 200 | 0.970 | 0.00002 | -0.00046-0.00059 | 20.6 | 1/2 | -0.0050 | 0.0001 | 1.000 |
| preboarding_crew_declaration_compliance | classic_cruise_1900 | 7.0 | 200 | 0.960 | 0.00002 | -0.00046-0.00059 | 20.6 | 1/2 | -0.0050 | 0.0001 | 1.000 |
| num_epochs | classic_cruise_1900 | 7.0 | 200 | 1.000 | 0.00879 | 0.00605-0.01123 | 2.5 | 25/0 | 0.1250 | 0.0176 | 0.000 |
| preboarding_crew_recall_halflife_days | classic_cruise_1900 | 7.0 | 200 | 0.995 | -0.00001 | -0.00002-0.00000 | 27111.5 | 0/1 | -0.0050 | -0.0000 | 1.000 |
| preboarding_crew_recall_halflife_days | classic_cruise_1900 | 7.0 | 200 | 0.990 | -0.00015 | -0.00045-0.00002 | 67.5 | 0/2 | -0.0100 | -0.0004 | 0.500 |
| preboarding_crew_recall_halflife_days | classic_cruise_1900 | 7.0 | 200 | 0.955 | 0.00024 | -0.00034-0.00101 | 13.2 | 2/3 | -0.0050 | 0.0007 | 1.000 |
| preboarding_crew_declaration_compliance | classic_cruise_1900 | 7.0 | 200 | 1.000 | 0.00000 | 0.00000-0.00000 | n/a | 0/0 | 0.0000 | 0.0000 | n/a |
| num_epochs | classic_cruise_1900 | 7.0 | 200 | 1.000 | 0.00876 | 0.00607-0.01123 | 2.5 | 24/0 | 0.1200 | 0.0175 | 0.000 |
| preboarding_crew_recall_halflife_days | classic_cruise_1900 | 7.0 | 200 | 0.995 | -0.00014 | -0.00045-0.00002 | 67.5 | 0/1 | -0.0050 | -0.0004 | 1.000 |
| preboarding_crew_recall_halflife_days | classic_cruise_1900 | 7.0 | 200 | 0.960 | 0.00025 | -0.00034-0.00102 | 13.2 | 2/2 | 0.0000 | 0.0008 | 1.000 |
| preboarding_crew_declaration_compliance | classic_cruise_1900 | 7.0 | 200 | 0.995 | -0.00012 | -0.00045-0.00005 | 65.6 | 0/1 | -0.0050 | -0.0003 | 1.000 |
| num_epochs | classic_cruise_1900 | 7.0 | 200 | 1.000 | 0.00886 | 0.00608-0.01135 | 2.5 | 25/0 | 0.1250 | 0.0177 | 0.000 |
| preboarding_crew_recall_halflife_days | classic_cruise_1900 | 7.0 | 200 | 0.965 | 0.00039 | -0.00010-0.00115 | 16.1 | 2/1 | 0.0050 | 0.0011 | 1.000 |
| preboarding_crew_declaration_compliance | classic_cruise_1900 | 7.0 | 200 | 0.980 | 0.00027 | -0.00000-0.00073 | 31.2 | 1/0 | 0.0050 | 0.0007 | 1.000 |
| num_epochs | classic_cruise_1900 | 7.0 | 200 | 1.000 | 0.00857 | 0.00594-0.01108 | 2.5 | 25/0 | 0.1250 | 0.0150 | 0.000 |
| preboarding_crew_declaration_compliance | classic_cruise_1900 | 7.0 | 200 | 0.990 | 0.00001 | 0.00000-0.00002 | 58671.8 | 0/0 | 0.0000 | 0.0000 | n/a |
| num_epochs | classic_cruise_1900 | 7.0 | 200 | 1.000 | 0.00894 | 0.00616-0.01167 | 2.5 | 27/0 | 0.1350 | 0.0156 | 0.000 |
| preboarding_crew_recall_halflife_days | classic_cruise_1900 | 7.0 | 200 | 0.990 | -0.00013 | -0.00045-0.00005 | 65.6 | 0/2 | -0.0100 | -0.0004 | 0.500 |
| preboarding_crew_recall_halflife_days | classic_cruise_1900 | 7.0 | 200 | 0.970 | 0.00012 | -0.00034-0.00066 | 21.6 | 1/2 | -0.0050 | 0.0003 | 1.000 |
| preboarding_crew_recall_halflife_days | classic_cruise_1900 | 7.0 | 200 | 0.945 | 0.00025 | -0.00034-0.00101 | 13.2 | 2/3 | -0.0050 | 0.0008 | 1.000 |
| num_epochs | classic_cruise_1900 | 7.0 | 200 | 1.000 | 0.00876 | 0.00607-0.01123 | 2.5 | 24/0 | 0.1200 | 0.0175 | 0.000 |
| preboarding_crew_recall_halflife_days | classic_cruise_1900 | 7.0 | 200 | 0.980 | 0.00025 | -0.00000-0.00072 | 31.6 | 1/0 | 0.0050 | 0.0006 | 1.000 |
| preboarding_crew_recall_halflife_days | classic_cruise_1900 | 7.0 | 200 | 0.955 | 0.00038 | -0.00010-0.00112 | 16.2 | 2/1 | 0.0050 | 0.0010 | 1.000 |
| num_epochs | classic_cruise_1900 | 7.0 | 200 | 1.000 | 0.00888 | 0.00604-0.01154 | 2.4 | 26/0 | 0.1300 | 0.0155 | 0.000 |
| preboarding_crew_recall_halflife_days | classic_cruise_1900 | 7.0 | 200 | 0.975 | 0.00013 | -0.00022-0.00061 | 33.8 | 1/1 | 0.0000 | 0.0004 | 1.000 |
| num_epochs | classic_cruise_1900 | 7.0 | 200 | 1.000 | 0.00893 | 0.00611-0.01163 | 2.5 | 26/0 | 0.1300 | 0.0156 | 0.000 |
| preboarding_crew_denial_probability | classic_cruise_1900 | 7.0 | 200 | 0.960 | 0.00041 | -0.00011-0.00110 | 14.4 | 3/0 | 0.0150 | 0.0011 | 0.250 |
| preboarding_crew_denial_probability | classic_cruise_1900 | 7.0 | 200 | 0.935 | 0.00001 | -0.00093-0.00095 | 7.2 | 3/2 | 0.0050 | 0.0000 | 1.000 |
| num_epochs | classic_cruise_1900 | 7.0 | 200 | 1.000 | 0.00883 | 0.00609-0.01156 | 2.6 | 27/0 | 0.1350 | 0.0155 | 0.000 |
| preboarding_crew_denial_probability | classic_cruise_1900 | 7.0 | 200 | 0.975 | -0.00040 | -0.00115-0.00013 | 16.2 | 0/2 | -0.0100 | -0.0010 | 0.500 |
| num_epochs | classic_cruise_1900 | 7.0 | 200 | 1.000 | 0.00868 | 0.00608-0.01137 | 2.8 | 26/0 | 0.1300 | 0.0152 | 0.000 |
| num_epochs | classic_cruise_1900 | 7.0 | 200 | 1.000 | 0.00810 | 0.00569-0.01053 | 2.8 | 25/0 | 0.1250 | 0.0142 | 0.000 |
| preboarding_passenger_declaration_compliance | classic_cruise_1900 | 7.0 | 200 | 0.950 | -0.00017 | -0.00041--0.00000 | 81.4 | 0/0 | 0.0000 | -0.0004 | n/a |
| preboarding_passenger_declaration_compliance | classic_cruise_1900 | 7.0 | 200 | 0.880 | -0.00003 | -0.00046-0.00070 | 17.2 | 1/0 | 0.0050 | -0.0001 | 1.000 |
| num_epochs | classic_cruise_1900 | 7.0 | 200 | 1.000 | 0.00892 | 0.00619-0.01165 | 2.2 | 27/0 | 0.1350 | 0.0178 | 0.000 |
| preboarding_passenger_declaration_compliance | classic_cruise_1900 | 7.0 | 200 | 0.910 | 0.00014 | -0.00012-0.00083 | 21.9 | 1/0 | 0.0050 | 0.0004 | 1.000 |
| num_epochs | classic_cruise_1900 | 7.0 | 200 | 1.000 | 0.00836 | 0.00564-0.01101 | 2.2 | 25/0 | 0.1250 | 0.0167 | 0.000 |
| num_epochs | classic_cruise_1900 | 7.0 | 200 | 1.000 | 0.00866 | 0.00583-0.01128 | 2.2 | 27/0 | 0.1350 | 0.0130 | 0.000 |
| boarding_mechanism_rung | classic_cruise_1900 | 7.0 | 1000 | 0.936 | -0.00029 | -0.00061-0.00001 | 8.1 | 5/7 | -0.0020 | -0.0006 | 0.774 |
| num_epochs | classic_cruise_1900 | 7.0 | 1000 | 1.000 | 0.00999 | 0.00880-0.01110 | 2.0 | 164/0 | 0.1640 | 0.0180 | 0.000 |
| num_epochs | classic_cruise_1900 | 7.0 | 1000 | 1.000 | 0.01002 | 0.00896-0.01110 | 1.9 | 164/0 | 0.1640 | 0.0185 | 0.000 |
| preboarding_crew_declaration_compliance | classic_cruise_1900 | 12.0 | 200 | 0.985 | 0.00010 | -0.00042-0.00065 | 85.9 | 1/1 | 0.0000 | 0.0001 | 1.000 |
| preboarding_crew_declaration_compliance | classic_cruise_1900 | 12.0 | 200 | 0.965 | 0.00040 | -0.00028-0.00110 | 48.7 | 2/1 | 0.0050 | 0.0004 | 1.000 |
| preboarding_crew_declaration_compliance | classic_cruise_1900 | 12.0 | 200 | 0.935 | 0.00057 | -0.00081-0.00200 | 10.7 | 4/2 | 0.0100 | 0.0004 | 0.688 |
| preboarding_crew_declaration_compliance | classic_cruise_1900 | 12.0 | 200 | 0.925 | 0.00047 | -0.00095-0.00201 | 10.3 | 4/2 | 0.0100 | 0.0004 | 0.688 |
| preboarding_crew_recall_halflife_days | classic_cruise_1900 | 12.0 | 200 | 0.995 | 0.00020 | 0.00000-0.00060 | 153.2 | 1/0 | 0.0050 | 0.0002 | 1.000 |
| preboarding_crew_recall_halflife_days | classic_cruise_1900 | 12.0 | 200 | 0.995 | 0.00020 | 0.00000-0.00060 | 153.2 | 1/0 | 0.0050 | 0.0002 | 1.000 |
| preboarding_crew_recall_halflife_days | classic_cruise_1900 | 12.0 | 200 | 0.985 | 0.00006 | -0.00045-0.00063 | 88.2 | 1/1 | 0.0000 | 0.0001 | 1.000 |
| preboarding_crew_declaration_compliance | classic_cruise_1900 | 12.0 | 200 | 1.000 | 0.00000 | 0.00000-0.00000 | n/a | 0/0 | 0.0000 | 0.0000 | n/a |
| preboarding_crew_declaration_compliance | classic_cruise_1900 | 12.0 | 200 | 0.980 | 0.00010 | -0.00037-0.00063 | 86.0 | 1/1 | 0.0000 | 0.0001 | 1.000 |
| preboarding_crew_declaration_compliance | classic_cruise_1900 | 12.0 | 200 | 0.980 | 0.00010 | -0.00037-0.00063 | 86.0 | 1/1 | 0.0000 | 0.0001 | 1.000 |
| preboarding_crew_recall_halflife_days | classic_cruise_1900 | 12.0 | 200 | 1.000 | 0.00000 | 0.00000-0.00000 | n/a | 0/0 | 0.0000 | 0.0000 | n/a |
| preboarding_crew_recall_halflife_days | classic_cruise_1900 | 12.0 | 200 | 0.990 | -0.00014 | -0.00050-0.00005 | 213.6 | 0/1 | -0.0050 | -0.0001 | 1.000 |
| preboarding_crew_declaration_compliance | classic_cruise_1900 | 12.0 | 200 | 0.985 | -0.00010 | -0.00050-0.00016 | 201.1 | 0/1 | -0.0050 | -0.0001 | 1.000 |
| preboarding_crew_declaration_compliance | classic_cruise_1900 | 12.0 | 200 | 0.980 | -0.00001 | -0.00042-0.00036 | 157.3 | 0/1 | -0.0050 | -0.0000 | 1.000 |
| preboarding_crew_declaration_compliance | classic_cruise_1900 | 12.0 | 200 | 0.975 | -0.00011 | -0.00124-0.00084 | 19.5 | 1/2 | -0.0050 | -0.0001 | 1.000 |
| preboarding_crew_recall_halflife_days | classic_cruise_1900 | 12.0 | 200 | 0.990 | -0.00014 | -0.00050-0.00005 | 213.6 | 0/1 | -0.0050 | -0.0001 | 1.000 |
| preboarding_crew_declaration_compliance | classic_cruise_1900 | 12.0 | 200 | 0.985 | -0.00010 | -0.00050-0.00016 | 201.1 | 0/1 | -0.0050 | -0.0001 | 1.000 |
| preboarding_crew_declaration_compliance | classic_cruise_1900 | 12.0 | 200 | 0.975 | -0.00044 | -0.00142-0.00023 | 28.2 | 0/2 | -0.0100 | -0.0004 | 0.500 |
| preboarding_crew_declaration_compliance | classic_cruise_1900 | 12.0 | 200 | 0.955 | 0.00019 | -0.00109-0.00149 | 13.0 | 2/2 | 0.0000 | 0.0002 | 1.000 |
| preboarding_crew_declaration_compliance | classic_cruise_1900 | 12.0 | 200 | 0.980 | 0.00030 | -0.00006-0.00082 | 110.5 | 1/0 | 0.0050 | 0.0003 | 1.000 |
| preboarding_crew_declaration_compliance | classic_cruise_1900 | 12.0 | 200 | 0.950 | 0.00047 | -0.00084-0.00180 | 12.1 | 3/1 | 0.0100 | 0.0004 | 0.625 |
| preboarding_crew_declaration_compliance | classic_cruise_1900 | 12.0 | 200 | 0.940 | 0.00037 | -0.00095-0.00171 | 11.7 | 3/1 | 0.0100 | 0.0003 | 0.625 |
| preboarding_crew_recall_halflife_days | classic_cruise_1900 | 12.0 | 200 | 0.980 | 0.00010 | -0.00037-0.00063 | 86.0 | 1/1 | 0.0000 | 0.0001 | 1.000 |
| preboarding_crew_recall_halflife_days | classic_cruise_1900 | 12.0 | 200 | 0.980 | 0.00010 | -0.00037-0.00063 | 86.0 | 1/1 | 0.0000 | 0.0001 | 1.000 |
| preboarding_crew_recall_halflife_days | classic_cruise_1900 | 12.0 | 200 | 0.965 | 0.00036 | -0.00028-0.00107 | 49.3 | 2/1 | 0.0050 | 0.0004 | 1.000 |
| preboarding_crew_declaration_compliance | classic_cruise_1900 | 12.0 | 200 | 0.980 | 0.00010 | -0.00037-0.00063 | 86.0 | 1/1 | 0.0000 | 0.0001 | 1.000 |
| preboarding_crew_declaration_compliance | classic_cruise_1900 | 12.0 | 200 | 0.980 | 0.00010 | -0.00037-0.00063 | 86.0 | 1/1 | 0.0000 | 0.0001 | 1.000 |
| preboarding_crew_recall_halflife_days | classic_cruise_1900 | 12.0 | 200 | 1.000 | 0.00000 | 0.00000-0.00000 | n/a | 0/0 | 0.0000 | 0.0000 | n/a |
| preboarding_crew_recall_halflife_days | classic_cruise_1900 | 12.0 | 200 | 0.985 | 0.00026 | -0.00008-0.00081 | 113.8 | 1/0 | 0.0050 | 0.0003 | 1.000 |
| preboarding_crew_declaration_compliance | classic_cruise_1900 | 12.0 | 200 | 0.995 | 0.00009 | 0.00000-0.00028 | 706.0 | 0/0 | 0.0000 | 0.0001 | n/a |
| preboarding_crew_declaration_compliance | classic_cruise_1900 | 12.0 | 200 | 0.990 | -0.00001 | -0.00107-0.00090 | 21.4 | 1/1 | 0.0000 | -0.0000 | 1.000 |
| preboarding_crew_recall_halflife_days | classic_cruise_1900 | 12.0 | 200 | 0.985 | 0.00026 | -0.00008-0.00081 | 113.8 | 1/0 | 0.0050 | 0.0003 | 1.000 |
| preboarding_crew_declaration_compliance | classic_cruise_1900 | 12.0 | 200 | 0.990 | -0.00034 | -0.00126-0.00026 | 32.6 | 0/1 | -0.0050 | -0.0003 | 1.000 |
| preboarding_crew_declaration_compliance | classic_cruise_1900 | 12.0 | 200 | 0.970 | 0.00029 | -0.00091-0.00149 | 13.7 | 2/1 | 0.0050 | 0.0003 | 1.000 |
| preboarding_crew_declaration_compliance | classic_cruise_1900 | 12.0 | 200 | 0.970 | 0.00017 | -0.00104-0.00142 | 13.6 | 2/1 | 0.0050 | 0.0001 | 1.000 |
| preboarding_crew_declaration_compliance | classic_cruise_1900 | 12.0 | 200 | 0.960 | 0.00007 | -0.00109-0.00134 | 13.1 | 2/1 | 0.0050 | 0.0001 | 1.000 |
| preboarding_crew_recall_halflife_days | classic_cruise_1900 | 12.0 | 200 | 0.995 | 0.00009 | 0.00000-0.00028 | 706.0 | 0/0 | 0.0000 | 0.0001 | n/a |
| preboarding_crew_recall_halflife_days | classic_cruise_1900 | 12.0 | 200 | 0.990 | -0.00034 | -0.00126-0.00026 | 32.6 | 0/1 | -0.0050 | -0.0003 | 1.000 |
| preboarding_crew_recall_halflife_days | classic_cruise_1900 | 12.0 | 200 | 0.955 | 0.00043 | -0.00088-0.00175 | 12.1 | 3/1 | 0.0100 | 0.0003 | 0.625 |
| preboarding_crew_declaration_compliance | classic_cruise_1900 | 12.0 | 200 | 1.000 | 0.00000 | 0.00000-0.00000 | n/a | 0/0 | 0.0000 | 0.0000 | n/a |
| preboarding_crew_recall_halflife_days | classic_cruise_1900 | 12.0 | 200 | 0.995 | -0.00043 | -0.00128-0.00000 | 34.5 | 0/1 | -0.0050 | -0.0004 | 1.000 |
| preboarding_crew_recall_halflife_days | classic_cruise_1900 | 12.0 | 200 | 0.960 | 0.00033 | -0.00091-0.00167 | 12.4 | 3/1 | 0.0100 | 0.0003 | 0.625 |
| preboarding_crew_declaration_compliance | classic_cruise_1900 | 12.0 | 200 | 0.995 | -0.00011 | -0.00126-0.00084 | 22.2 | 1/1 | 0.0000 | -0.0001 | 1.000 |
| preboarding_crew_recall_halflife_days | classic_cruise_1900 | 12.0 | 200 | 0.965 | 0.00076 | -0.00018-0.00196 | 18.8 | 3/0 | 0.0150 | 0.0006 | 0.250 |
| preboarding_crew_declaration_compliance | classic_cruise_1900 | 12.0 | 200 | 0.980 | 0.00063 | -0.00014-0.00178 | 23.2 | 2/0 | 0.0100 | 0.0006 | 0.500 |
| preboarding_crew_declaration_compliance | classic_cruise_1900 | 12.0 | 200 | 0.990 | -0.00010 | -0.00033-0.00002 | 534.3 | 0/0 | 0.0000 | -0.0000 | n/a |
| preboarding_crew_recall_halflife_days | classic_cruise_1900 | 12.0 | 200 | 0.990 | -0.00001 | -0.00107-0.00090 | 21.4 | 1/1 | 0.0000 | -0.0000 | 1.000 |
| preboarding_crew_recall_halflife_days | classic_cruise_1900 | 12.0 | 200 | 0.970 | 0.00029 | -0.00091-0.00149 | 13.7 | 2/1 | 0.0050 | 0.0003 | 1.000 |
| preboarding_crew_recall_halflife_days | classic_cruise_1900 | 12.0 | 200 | 0.945 | 0.00033 | -0.00102-0.00171 | 11.7 | 3/1 | 0.0100 | 0.0002 | 0.625 |
| preboarding_crew_recall_halflife_days | classic_cruise_1900 | 12.0 | 200 | 0.980 | 0.00030 | -0.00021-0.00119 | 37.3 | 1/0 | 0.0050 | 0.0003 | 1.000 |
| preboarding_crew_recall_halflife_days | classic_cruise_1900 | 12.0 | 200 | 0.955 | 0.00034 | -0.00046-0.00141 | 25.3 | 2/0 | 0.0100 | 0.0003 | 0.500 |
| preboarding_crew_recall_halflife_days | classic_cruise_1900 | 12.0 | 200 | 0.975 | 0.00004 | -0.00050-0.00059 | 80.9 | 1/0 | 0.0050 | 0.0000 | 1.000 |
| preboarding_crew_denial_probability | classic_cruise_1900 | 12.0 | 200 | 0.960 | 0.00025 | -0.00086-0.00157 | 16.7 | 3/1 | 0.0100 | 0.0002 | 0.625 |
| preboarding_crew_denial_probability | classic_cruise_1900 | 12.0 | 200 | 0.935 | -0.00072 | -0.00254-0.00086 | 9.1 | 3/4 | -0.0050 | -0.0005 | 1.000 |
| preboarding_crew_denial_probability | classic_cruise_1900 | 12.0 | 200 | 0.975 | -0.00098 | -0.00224--0.00010 | 21.1 | 0/3 | -0.0150 | -0.0010 | 0.250 |
| preboarding_passenger_declaration_compliance | classic_cruise_1900 | 12.0 | 200 | 0.950 | -0.00073 | -0.00174-0.00014 | 19.3 | 0/2 | -0.0100 | -0.0011 | 0.500 |
| preboarding_passenger_declaration_compliance | classic_cruise_1900 | 12.0 | 200 | 0.880 | -0.00029 | -0.00164-0.00108 | 10.4 | 4/3 | 0.0050 | -0.0003 | 1.000 |
| preboarding_passenger_declaration_compliance | classic_cruise_1900 | 12.0 | 200 | 0.910 | 0.00044 | -0.00082-0.00181 | 12.9 | 5/2 | 0.0150 | 0.0004 | 0.453 |
| boarding_mechanism_rung | classic_cruise_1900 | 12.0 | 1000 | 0.936 | -0.00026 | -0.00083-0.00021 | 16.0 | 10/12 | -0.0020 | -0.0005 | 0.832 |
| num_epochs | expedition_cruise_450 | 7.0 | 1000 | 1.000 | 0.00144 | 0.00101-0.00196 | 2.4 | 27/1 | 0.0260 | 0.0007 | 0.000 |
| boarding_mechanism_rung | expedition_cruise_450 | 7.0 | 1000 | 0.987 | -0.00032 | -0.00052--0.00014 | 4.5 | 0/4 | -0.0040 | -0.0000 | 0.125 |
| num_epochs | expedition_cruise_450 | 7.0 | 1000 | 1.000 | 0.00148 | 0.00109-0.00196 | 2.4 | 20/1 | 0.0190 | 0.0016 | 0.000 |
| num_epochs | expedition_cruise_450 | 7.0 | 1000 | 1.000 | 0.00157 | 0.00117-0.00206 | 2.0 | 23/1 | 0.0220 | 0.0015 | 0.000 |
| boarding_mechanism_rung | expedition_cruise_450 | 12.0 | 1000 | 0.987 | -0.00023 | -0.00053-0.00006 | 8.0 | 5/6 | -0.0010 | -0.0004 | 1.000 |
| num_epochs | spirit_cruise_3000 | 7.0 | 1000 | 1.000 | 0.01199 | 0.01095-0.01315 | 2.1 | 192/0 | 0.1920 | 0.0414 | 0.000 |
| boarding_mechanism_rung | spirit_cruise_3000 | 7.0 | 1000 | 0.880 | 0.00001 | -0.00023-0.00030 | 10.6 | 7/2 | 0.0050 | 0.0000 | 0.180 |
| num_epochs | spirit_cruise_3000 | 7.0 | 1000 | 1.000 | 0.01368 | 0.01257-0.01492 | 1.8 | 232/1 | 0.2310 | 0.0356 | 0.000 |
| num_epochs | spirit_cruise_3000 | 7.0 | 1000 | 1.000 | 0.01319 | 0.01201-0.01430 | 1.8 | 214/0 | 0.2140 | 0.0350 | 0.000 |
| boarding_mechanism_rung | spirit_cruise_3000 | 12.0 | 1000 | 0.880 | -0.00049 | -0.00113-0.00015 | 11.4 | 13/25 | -0.0120 | -0.0019 | 0.073 |
| boarding_crew_prevalence | classic_cruise_1900 | 7.0 | 150 | 0.000 | 0.01032 | 0.00706-0.01345 | 2.3 | 33/12 | 0.1400 | 0.0997 | 0.002 |
| boarding_passenger_prevalence | classic_cruise_1900 | 7.0 | 150 | 0.007 | 0.01239 | 0.00872-0.01677 | 1.8 | 38/11 | 0.1800 | 0.1074 | 0.000 |
| num_epochs | classic_cruise_1900 | 7.0 | 150 | 1.000 | 0.03574 | 0.03260-0.03962 | 3.0 | 58/0 | 0.3867 | 0.2145 | 0.000 |
| boarding_passenger_prevalence | classic_cruise_1900 | 7.0 | 150 | 0.020 | 0.01004 | 0.00542-0.01432 | 1.6 | 41/16 | 0.1667 | 0.1038 | 0.001 |
| num_epochs | classic_cruise_1900 | 7.0 | 150 | 1.000 | 0.03445 | 0.03147-0.03729 | 3.5 | 57/0 | 0.3800 | 0.1952 | 0.000 |
| presymptomatic_share_of_presenting | classic_cruise_1900 | 7.0 | 150 | 0.873 | 0.00002 | -0.00232-0.00261 | 5.9 | 6/11 | -0.0333 | 0.0001 | 0.332 |
| presymptomatic_share_of_presenting | classic_cruise_1900 | 7.0 | 150 | 0.620 | 0.00267 | -0.00098-0.00631 | 2.4 | 27/18 | 0.0600 | 0.0231 | 0.233 |
| num_epochs | classic_cruise_1900 | 7.0 | 150 | 1.000 | 0.03957 | 0.03630-0.04268 | 3.2 | 69/0 | 0.4600 | 0.1715 | 0.000 |
| presymptomatic_share_of_presenting | classic_cruise_1900 | 7.0 | 150 | 0.673 | 0.00265 | -0.00061-0.00606 | 2.9 | 25/11 | 0.0933 | 0.0230 | 0.029 |
| num_epochs | classic_cruise_1900 | 7.0 | 1150 | 1.000 | 0.03806 | 0.03705-0.03913 | 3.0 | 449/1 | 0.3896 | 0.1870 | 0.000 |
| num_epochs | classic_cruise_1900 | 7.0 | 150 | 1.000 | 0.03867 | 0.03550-0.04213 | 2.6 | 62/0 | 0.4133 | 0.2320 | 0.000 |
| boarding_crew_prevalence | classic_cruise_1900 | 7.0 | 150 | 0.000 | 0.00797 | 0.00430-0.01146 | 2.0 | 33/14 | 0.1267 | 0.0744 | 0.008 |
| num_epochs | classic_cruise_1900 | 7.0 | 150 | 1.000 | 0.03816 | 0.03532-0.04116 | 3.1 | 58/1 | 0.3800 | 0.1781 | 0.000 |
| num_epochs | classic_cruise_1900 | 7.0 | 150 | 1.000 | 0.03440 | 0.03116-0.03766 | 3.1 | 41/0 | 0.2733 | 0.2064 | 0.000 |
| boarding_crew_prevalence | classic_cruise_1900 | 12.0 | 150 | 0.000 | 0.00902 | 0.00407-0.01352 | 1.7 | 27/7 | 0.1333 | 0.0180 | 0.001 |
| boarding_passenger_prevalence | classic_cruise_1900 | 12.0 | 150 | 0.007 | 0.01481 | 0.00985-0.02028 | 1.4 | 31/5 | 0.1733 | 0.0296 | 0.000 |
| boarding_passenger_prevalence | classic_cruise_1900 | 12.0 | 150 | 0.020 | 0.00999 | 0.00537-0.01464 | 1.2 | 13/4 | 0.0600 | 0.0133 | 0.049 |
| presymptomatic_share_of_presenting | classic_cruise_1900 | 12.0 | 150 | 0.873 | -0.00103 | -0.00379-0.00204 | 4.4 | 4/7 | -0.0200 | -0.0017 | 0.549 |
| presymptomatic_share_of_presenting | classic_cruise_1900 | 12.0 | 150 | 0.620 | 0.00177 | -0.00293-0.00654 | 1.5 | 12/10 | 0.0133 | 0.0030 | 0.832 |
| presymptomatic_share_of_presenting | classic_cruise_1900 | 12.0 | 150 | 0.673 | 0.00280 | -0.00159-0.00671 | 2.0 | 10/5 | 0.0333 | 0.0075 | 0.302 |
| boarding_crew_prevalence | classic_cruise_1900 | 12.0 | 150 | 0.000 | 0.00420 | 0.00034-0.00801 | 1.7 | 6/3 | 0.0200 | 0.0056 | 0.508 |
| presymptomatic_share_of_presenting | expedition_cruise_450 | 7.0 | 150 | 0.960 | 0.00096 | 0.00007-0.00224 | 9.6 | 2/1 | 0.0067 | 0.0086 | 1.000 |
| presymptomatic_share_of_presenting | expedition_cruise_450 | 7.0 | 150 | 0.827 | 0.00092 | -0.00076-0.00248 | 4.7 | 4/4 | 0.0000 | 0.0068 | 1.000 |
| presymptomatic_share_of_presenting | expedition_cruise_450 | 7.0 | 150 | 0.867 | -0.00003 | -0.00125-0.00120 | 8.9 | 2/3 | -0.0067 | -0.0003 | 1.000 |
| num_epochs | expedition_cruise_450 | 7.0 | 1000 | 1.000 | 0.01198 | 0.01073-0.01312 | 2.5 | 213/14 | 0.1990 | 0.0839 | 0.000 |
| num_epochs | spirit_cruise_3000 | 7.0 | 1000 | 1.000 | 0.03785 | 0.03683-0.03898 | 2.6 | 298/1 | 0.2970 | 0.2479 | 0.000 |
