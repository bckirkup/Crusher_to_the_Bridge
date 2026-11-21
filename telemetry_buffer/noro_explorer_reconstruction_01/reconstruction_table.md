# noro_explorer_reconstruction_01 reconstruction table

Cells read: 600 of 600. Engine: bf0ec16825ed15176fe0362459a72a7be1667f41. Audit defects: 0.

Status: **complete**. A readout is complete only when coverage is exact, no audit defects stand, and --expect-sha named the source reference.

Model entries are median [5th, 95th percentile] over seeds. Peak days count from 0 = embarkation day (Feb 26). Peaks and the lag use onsets excluding the declared seeds, on evaluable cells only.

| Tier | Cells | Evaluable | Pax peak day | Crew peak day | Lag (crew - pax) | P(lag = target) | Pax onset AR | Crew onset AR | Target lag in central 90% |
|---|---:|---:|---|---|---|---:|---|---|---|
| Empirical (Explorer of the Seas, Feb 26 - Mar 5 2006) | | | 2 | 4 | 2 | | 0.0777 | 0.0169 | |
| `fl_exp_8d_recon_declared_five` | 100 | 5 | 1 [1.0, 2.0] | 4 [2.2, 4.8] | 2 [1.2, 3.0] | 0.40 | 0.0022 [0.0015, 0.0112] | 0.0008 [0.0000, 0.0163] | yes |
| `fl_exp_8d_recon_background_only` | 100 | 4 | 2.0 [1.1, 2.8] | 6.0 [4.2, 7.0] | 3.5 [2.1, 5.7] | 0.25 | 0.0003 [0.0000, 0.0084] | 0.0000 [0.0000, 0.0163] | no |
| `fl_meg_8d_recon_declared_five` | 100 | 4 | 2.0 [1.0, 3.0] | 4.5 [0.6, 5.0] | 1.5 [-0.7, 3.7] | 0.25 | 0.0014 [0.0010, 0.0114] | 0.0005 [0.0000, 0.0102] | yes |
| `fl_meg_8d_recon_background_only` | 100 | 4 | 1.5 [1.0, 2.8] | 4.5 [4.0, 5.8] | 3.0 [2.1, 3.8] | 0.25 | 0.0004 [0.0000, 0.0103] | 0.0005 [0.0000, 0.0098] | no |
| `fl_exp_8d_recon_declared_five_rhythm_off` | 100 | 5 | 1 [1.0, 2.0] | 4 [2.2, 4.8] | 2 [1.2, 3.0] | 0.40 | 0.0022 [0.0015, 0.0112] | 0.0008 [0.0000, 0.0163] | yes |
| `fl_meg_8d_recon_declared_five_rhythm_off` | 100 | 6 | 1.5 [1.0, 3.8] | 5.0 [4.0, 5.8] | 3.0 [1.5, 3.8] | 0.00 | 0.0014 [0.0010, 0.0130] | 0.0010 [0.0000, 0.0095] | yes |

Reported-case attack rates against the posting figures (cross-posting comparison only):

| Tier | Pax reported AR | Crew reported AR | Embarkation declarations, max (pax / crew) | Reported by end of epoch 0, max (pax / crew) | Cells with SOP-007 / SOP-009 |
|---|---|---|---|---|---|
| Posting | 0.0749 | 0.0160 | | | |
| `fl_exp_8d_recon_declared_five` | 0.0018 [0.0012, 0.0081] | 0.0008 [0.0000, 0.0119] | 0 / 3 | 1 / 3 | 6 / 1 |
| `fl_exp_8d_recon_background_only` | 0.0003 [0.0000, 0.0056] | 0.0000 [0.0000, 0.0102] | 0 / 3 | 1 / 3 | 5 / 1 |
| `fl_meg_8d_recon_declared_five` | 0.0012 [0.0008, 0.0064] | 0.0005 [0.0000, 0.0068] | 0 / 2 | 2 / 2 | 3 / 0 |
| `fl_meg_8d_recon_background_only` | 0.0002 [0.0000, 0.0054] | 0.0005 [0.0000, 0.0063] | 0 / 2 | 1 / 2 | 4 / 0 |
| `fl_exp_8d_recon_declared_five_rhythm_off` | 0.0018 [0.0012, 0.0081] | 0.0008 [0.0000, 0.0119] | 0 / 3 | 1 / 3 | 6 / 1 |
| `fl_meg_8d_recon_declared_five_rhythm_off` | 0.0012 [0.0008, 0.0092] | 0.0005 [0.0000, 0.0073] | 0 / 2 | 2 / 2 | 6 / 0 |

Hull-dependent effective state and timing sensitivity (share of evaluable cells with the peak within one day of the target; Explorer onset totals over the first seven days):

| Tier | Exposure cap requested / active | Rhythm layer active | Pax peak within 1 day | Crew peak within 1 day | Pax onsets, days 0-6 | Crew onsets, days 0-6 |
|---|---|---|---:|---:|---|---|
| `fl_exp_8d_recon_declared_five` | yes / yes | no | 1.00 | 0.80 | 40 [31, 112] | 6 [5, 14] |
| `fl_exp_8d_recon_background_only` | yes / yes | no | 1.00 | 0.50 | 42 [33, 109] | 6 [2, 10] |
| `fl_meg_8d_recon_declared_five` | yes / yes | yes | 1.00 | 0.75 | n/a | n/a |
| `fl_meg_8d_recon_background_only` | yes / yes | yes | 1.00 | 0.75 | n/a | n/a |
| `fl_exp_8d_recon_declared_five_rhythm_off` | yes / yes | no | 1.00 | 0.80 | 40 [31, 112] | 6 [5, 14] |
| `fl_meg_8d_recon_declared_five_rhythm_off` | yes / yes | no | 0.83 | 0.83 | n/a | n/a |

Embarkation declarations are the engine's pre-boarding report counter (crew only; the VSP 4.1.1.2 reportable clause does not cover passengers). Reports by the end of epoch 0 add sick-call reports made during that epoch.

Explorer minus mega on shared seed labels. The two hulls differ in geometry and in complement, so a difference is attributed to the bundle, not to geometry:

| Introduction | Pairs | Both evaluable | Lag diff | Pax peak-day diff | Crew peak-day diff | Pax onset AR diff | Crew onset AR diff |
|---|---:|---:|---|---|---|---|---|
| declared_five | 100 | 2 | 0.0 [-0.9, 0.9] | -2.0 [-2.0, -2.0] | -2.0 [-2.9, -1.1] | 0.0006 [-0.0006, 0.0022] | 0.0004 [-0.0015, 0.0069] |
| background_only | 100 | 2 | 0.5 [-1.8, 2.8] | -0.5 [-1.9, 0.8] | 0.0 [-0.9, 0.9] | 0.0001 [-0.0019, 0.0031] | 0.0000 [-0.0014, 0.0044] |

Temporal comparators. The main window pairs each of the eight date labels with a model day (the declared inclusive-day approximation); the first block here restricts the same metrics to the first seven elapsed days. The incident curve drops every agent infected at initialize -- all prevalent boarders, not only the five declared seeds -- and answers the incident-onset question the observed-onset curve cannot:

| Tier | Pax peak, days 0-6 | Crew peak, days 0-6 | Lag, days 0-6 | Pax incident peak | Crew incident peak | Incident lag | Pax incident onsets | Crew incident onsets |
|---|---|---|---|---|---|---|---|
| `fl_exp_8d_recon_declared_five` | 1 [1.0, 2.0] | 4 [2.2, 4.8] | 2 [1.2, 3.0] | 1.0 [1.0, 2.0] | 4.0 [2.2, 4.8] | 2.0 [1.2, 3.0] | 0 [0, 29] | 1 [0, 19] |
| `fl_exp_8d_recon_background_only` | 2.0 [1.1, 2.8] | 4.5 [4.0, 5.0] | 2.5 [2.0, 3.0] | 2.0 [1.1, 2.8] | 6.0 [4.2, 7.0] | 3.5 [2.1, 5.7] | 0 [0, 25] | 0 [0, 19] |
| `fl_meg_8d_recon_declared_five` | 2.0 [1.0, 3.0] | 4.5 [0.6, 5.0] | 1.5 [-0.7, 3.7] | 2.0 [1.0, 3.0] | 4.5 [3.1, 5.0] | 2.0 [1.1, 3.7] | 0 [0, 51] | 1 [0, 21] |
| `fl_meg_8d_recon_background_only` | 1.5 [1.0, 2.8] | 4.5 [4.0, 5.8] | 3.0 [2.1, 3.8] | 1.5 [1.0, 2.8] | 4.5 [4.0, 5.8] | 3.0 [2.1, 3.8] | 0 [0, 50] | 0 [0, 21] |
| `fl_exp_8d_recon_declared_five_rhythm_off` | 1 [1.0, 2.0] | 4 [2.2, 4.8] | 2 [1.2, 3.0] | 1.0 [1.0, 2.0] | 4.0 [2.2, 4.8] | 2.0 [1.2, 3.0] | 0 [0, 29] | 1 [0, 19] |
| `fl_meg_8d_recon_declared_five_rhythm_off` | 1.5 [1.0, 3.8] | 5.0 [4.0, 5.8] | 3.0 [1.5, 3.8] | 1.5 [1.0, 3.8] | 5.0 [4.0, 5.8] | 3.0 [1.5, 3.8] | 0 [0, 59] | 1 [0, 20] |

`(approx.)` marks incident columns read from an archive written before the incident curve existed: the value is the excluding-declared-seeds curve, which still counts boarding prevalence beyond the five declared seeds.

Declared arm `rhythm_off` (`rhythm.enabled` True → False). Reference tier minus arm tier on paired seeds of the same hull: what the changed path contributes. All pairs, quiet cells included; reported, never judged:

| Arm tier | Pairs | Identical curves | Pax onset AR diff | Crew onset AR diff | Pax reported AR diff | Crew reported AR diff |
|---|---:|---:|---|---|---|---|
| `fl_exp_8d_recon_declared_five_rhythm_off` | 100 | 100 | 0.0000 [0.0000, 0.0000] | 0.0000 [0.0000, 0.0000] | 0.0000 [0.0000, 0.0000] | 0.0000 [0.0000, 0.0000] |
| `fl_meg_8d_recon_declared_five_rhythm_off` | 100 | 4 | 0.0000 [-0.0021, 0.0002] | 0.0000 [-0.0024, 0.0010] | 0.0000 [-0.0021, 0.0004] | 0.0000 [-0.0019, 0.0005] |

Mean paired difference by voyage day (reference minus arm):

| Arm tier | Curve | Passengers | Crew |
|---|---|---|---|
| `fl_exp_8d_recon_declared_five_rhythm_off` | daily onsets | +0.00, +0.00, +0.00, +0.00, +0.00, +0.00, +0.00, +0.00 | +0.00, +0.00, +0.00, +0.00, +0.00, +0.00, +0.00, +0.00 |
| `fl_exp_8d_recon_declared_five_rhythm_off` | cumulative reported | +0.00, +0.00, +0.00, +0.00, +0.00, +0.00, +0.00, +0.00 | +0.00, +0.00, +0.00, +0.00, +0.00, +0.00, +0.00, +0.00 |
| `fl_meg_8d_recon_declared_five_rhythm_off` | daily onsets | -0.02, -0.77, -0.58, -0.51, -0.18, -0.07, +0.03, -0.01 | +0.01, -0.09, -0.37, -0.11, -0.10, -0.02, -0.04, -0.04 |
| `fl_meg_8d_recon_declared_five_rhythm_off` | cumulative reported | -0.14, -0.31, -0.72, -1.54, -1.97, -2.09, -2.09, -2.03 | +0.01, +0.00, -0.18, -0.72, -0.79, -0.86, -0.86, -0.92 |

Explorer minus mega within arm `rhythm_off` (both hulls on the arm value):

| Introduction | Pairs | Both evaluable | Lag diff | Pax onset AR diff | Crew onset AR diff |
|---|---:|---:|---|---|---|
| declared_five | 100 | 3 | -1.0 [-1.9, 0.8] | 0.0006 [-0.0036, 0.0018] | 0.0004 [-0.0016, 0.0052] |
