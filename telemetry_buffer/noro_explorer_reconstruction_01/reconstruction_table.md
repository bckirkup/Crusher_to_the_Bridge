# noro_explorer_reconstruction_01 reconstruction table

Cells read: 20 of 600. Engine: bf0ec16825ed15176fe0362459a72a7be1667f41. Audit defects: 0.

Status: **partial** -- fl_exp_8d_recon_declared_five: 80 seeds missing; fl_exp_8d_recon_background_only: 100 seeds missing; fl_meg_8d_recon_declared_five: 100 seeds missing; fl_meg_8d_recon_background_only: 100 seeds missing; fl_exp_8d_recon_declared_five_rhythm_off: 100 seeds missing; fl_meg_8d_recon_declared_five_rhythm_off: 100 seeds missing. A readout is complete only when coverage is exact, no audit defects stand, and --expect-sha named the source reference.

Model entries are median [5th, 95th percentile] over seeds. Peak days count from 0 = embarkation day (Feb 26). Peaks and the lag use onsets excluding the declared seeds, on evaluable cells only.

| Tier | Cells | Evaluable | Pax peak day | Crew peak day | Lag (crew - pax) | P(lag = target) | Pax onset AR | Crew onset AR | Target lag in central 90% |
|---|---:|---:|---|---|---|---:|---|---|---|
| Empirical (Explorer of the Seas, Feb 26 - Mar 5 2006) | | | 2 | 4 | 2 | | 0.0777 | 0.0169 | |
| `fl_exp_8d_recon_declared_five` | 20 | 0 | n/a [n/a, n/a] | n/a [n/a, n/a] | n/a [n/a, n/a] | n/a | 0.0020 [0.0015, 0.0031] | 0.0008 [0.0000, 0.0155] | n/a |
| `fl_exp_8d_recon_background_only` | 0 | 0 | n/a [n/a, n/a] | n/a [n/a, n/a] | n/a [n/a, n/a] | n/a | n/a [n/a, n/a] | n/a [n/a, n/a] | n/a |
| `fl_meg_8d_recon_declared_five` | 0 | 0 | n/a [n/a, n/a] | n/a [n/a, n/a] | n/a [n/a, n/a] | n/a | n/a [n/a, n/a] | n/a [n/a, n/a] | n/a |
| `fl_meg_8d_recon_background_only` | 0 | 0 | n/a [n/a, n/a] | n/a [n/a, n/a] | n/a [n/a, n/a] | n/a | n/a [n/a, n/a] | n/a [n/a, n/a] | n/a |
| `fl_exp_8d_recon_declared_five_rhythm_off` | 0 | 0 | n/a [n/a, n/a] | n/a [n/a, n/a] | n/a [n/a, n/a] | n/a | n/a [n/a, n/a] | n/a [n/a, n/a] | n/a |
| `fl_meg_8d_recon_declared_five_rhythm_off` | 0 | 0 | n/a [n/a, n/a] | n/a [n/a, n/a] | n/a [n/a, n/a] | n/a | n/a [n/a, n/a] | n/a [n/a, n/a] | n/a |

Reported-case attack rates against the posting figures (cross-posting comparison only):

| Tier | Pax reported AR | Crew reported AR | Embarkation declarations, max (pax / crew) | Reported by end of epoch 0, max (pax / crew) | Cells with SOP-007 / SOP-009 |
|---|---|---|---|---|---|
| Posting | 0.0749 | 0.0160 | | | |
| `fl_exp_8d_recon_declared_five` | 0.0018 [0.0012, 0.0028] | 0.0008 [0.0000, 0.0086] | 0 / 1 | 1 / 1 | 1 / 0 |
| `fl_exp_8d_recon_background_only` | n/a [n/a, n/a] | n/a [n/a, n/a] | 0 / 0 | 0 / 0 | 0 / 0 |
| `fl_meg_8d_recon_declared_five` | n/a [n/a, n/a] | n/a [n/a, n/a] | 0 / 0 | 0 / 0 | 0 / 0 |
| `fl_meg_8d_recon_background_only` | n/a [n/a, n/a] | n/a [n/a, n/a] | 0 / 0 | 0 / 0 | 0 / 0 |
| `fl_exp_8d_recon_declared_five_rhythm_off` | n/a [n/a, n/a] | n/a [n/a, n/a] | 0 / 0 | 0 / 0 | 0 / 0 |
| `fl_meg_8d_recon_declared_five_rhythm_off` | n/a [n/a, n/a] | n/a [n/a, n/a] | 0 / 0 | 0 / 0 | 0 / 0 |

Hull-dependent effective state and timing sensitivity (share of evaluable cells with the peak within one day of the target; Explorer onset totals over the first seven days):

| Tier | Exposure cap requested / active | Rhythm layer active | Pax peak within 1 day | Crew peak within 1 day | Pax onsets, days 0-6 | Crew onsets, days 0-6 |
|---|---|---|---:|---:|---|---|
| `fl_exp_8d_recon_declared_five` | yes / yes | no | n/a | n/a | n/a [n/a, n/a] | n/a [n/a, n/a] |
| `fl_exp_8d_recon_background_only` |  |  | n/a | n/a | n/a [n/a, n/a] | n/a [n/a, n/a] |
| `fl_meg_8d_recon_declared_five` |  |  | n/a | n/a | n/a | n/a |
| `fl_meg_8d_recon_background_only` |  |  | n/a | n/a | n/a | n/a |
| `fl_exp_8d_recon_declared_five_rhythm_off` |  |  | n/a | n/a | n/a [n/a, n/a] | n/a [n/a, n/a] |
| `fl_meg_8d_recon_declared_five_rhythm_off` |  |  | n/a | n/a | n/a | n/a |

Embarkation declarations are the engine's pre-boarding report counter (crew only; the VSP 4.1.1.2 reportable clause does not cover passengers). Reports by the end of epoch 0 add sick-call reports made during that epoch.

Explorer minus mega on shared seed labels. The two hulls differ in geometry and in complement, so a difference is attributed to the bundle, not to geometry:

| Introduction | Pairs | Both evaluable | Lag diff | Pax peak-day diff | Crew peak-day diff | Pax onset AR diff | Crew onset AR diff |
|---|---:|---:|---|---|---|---|---|
| declared_five | 0 | 0 | n/a [n/a, n/a] | n/a [n/a, n/a] | n/a [n/a, n/a] | n/a [n/a, n/a] | n/a [n/a, n/a] |
| background_only | 0 | 0 | n/a [n/a, n/a] | n/a [n/a, n/a] | n/a [n/a, n/a] | n/a [n/a, n/a] | n/a [n/a, n/a] |

Temporal comparators. The main window pairs each of the eight date labels with a model day (the declared inclusive-day approximation); the first block here restricts the same metrics to the first seven elapsed days. The incident curve drops every agent infected at initialize -- all prevalent boarders, not only the five declared seeds -- and answers the incident-onset question the observed-onset curve cannot:

| Tier | Pax peak, days 0-6 | Crew peak, days 0-6 | Lag, days 0-6 | Pax incident peak | Crew incident peak | Incident lag | Pax incident onsets | Crew incident onsets |
|---|---|---|---|---|---|---|---|
| `fl_exp_8d_recon_declared_five` | n/a [n/a, n/a] | n/a [n/a, n/a] | n/a [n/a, n/a] | n/a [n/a, n/a] | n/a [n/a, n/a] | n/a [n/a, n/a] | 0 [0, 2] | 1 [0, 18] |
| `fl_exp_8d_recon_background_only` | n/a [n/a, n/a] | n/a [n/a, n/a] | n/a [n/a, n/a] | n/a [n/a, n/a] | n/a [n/a, n/a] | n/a [n/a, n/a] | n/a [n/a, n/a] | n/a [n/a, n/a] |
| `fl_meg_8d_recon_declared_five` | n/a [n/a, n/a] | n/a [n/a, n/a] | n/a [n/a, n/a] | n/a [n/a, n/a] | n/a [n/a, n/a] | n/a [n/a, n/a] | n/a [n/a, n/a] | n/a [n/a, n/a] |
| `fl_meg_8d_recon_background_only` | n/a [n/a, n/a] | n/a [n/a, n/a] | n/a [n/a, n/a] | n/a [n/a, n/a] | n/a [n/a, n/a] | n/a [n/a, n/a] | n/a [n/a, n/a] | n/a [n/a, n/a] |
| `fl_exp_8d_recon_declared_five_rhythm_off` | n/a [n/a, n/a] | n/a [n/a, n/a] | n/a [n/a, n/a] | n/a [n/a, n/a] | n/a [n/a, n/a] | n/a [n/a, n/a] | n/a [n/a, n/a] | n/a [n/a, n/a] |
| `fl_meg_8d_recon_declared_five_rhythm_off` | n/a [n/a, n/a] | n/a [n/a, n/a] | n/a [n/a, n/a] | n/a [n/a, n/a] | n/a [n/a, n/a] | n/a [n/a, n/a] | n/a [n/a, n/a] | n/a [n/a, n/a] |

`(approx.)` marks incident columns read from an archive written before the incident curve existed: the value is the excluding-declared-seeds curve, which still counts boarding prevalence beyond the five declared seeds.

Declared arm `rhythm_off` (`rhythm.enabled` True → False). Reference tier minus arm tier on paired seeds of the same hull: what the changed path contributes. All pairs, quiet cells included; reported, never judged:

| Arm tier | Pairs | Identical curves | Pax onset AR diff | Crew onset AR diff | Pax reported AR diff | Crew reported AR diff |
|---|---:|---:|---|---|---|---|
| `fl_exp_8d_recon_declared_five_rhythm_off` | 0 | 0 | n/a [n/a, n/a] | n/a [n/a, n/a] | n/a [n/a, n/a] | n/a [n/a, n/a] |
| `fl_meg_8d_recon_declared_five_rhythm_off` | 0 | 0 | n/a [n/a, n/a] | n/a [n/a, n/a] | n/a [n/a, n/a] | n/a [n/a, n/a] |

Mean paired difference by voyage day (reference minus arm):

| Arm tier | Curve | Passengers | Crew |
|---|---|---|---|
| `fl_exp_8d_recon_declared_five_rhythm_off` | daily onsets | — | — |
| `fl_exp_8d_recon_declared_five_rhythm_off` | cumulative reported | — | — |
| `fl_meg_8d_recon_declared_five_rhythm_off` | daily onsets | — | — |
| `fl_meg_8d_recon_declared_five_rhythm_off` | cumulative reported | — | — |

Explorer minus mega within arm `rhythm_off` (both hulls on the arm value):

| Introduction | Pairs | Both evaluable | Lag diff | Pax onset AR diff | Crew onset AR diff |
|---|---:|---:|---|---|---|
| declared_five | 0 | 0 | n/a [n/a, n/a] | n/a [n/a, n/a] | n/a [n/a, n/a] |
