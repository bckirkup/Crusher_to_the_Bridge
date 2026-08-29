# Observation-model calibration

The severity hazards were calibrated with `none_response`, dose adjustment
2.5, one seeded infection, and 168 hourly epochs on the expedition and
classic hulls.  The final profile values are daily hazards:

| Stratum | Weight | Sick-call hazard |
|---|---:|---:|
| mild | 0.35 | 0.30/day |
| moderate | 0.50 | 0.56/day |
| severe | 0.15 | 0.90/day |

The four calibration runs used seeds 940 and 941.  Episode capture is
reported as reported symptomatic episodes divided by ever-ill symptomatic
episodes:

| Hull | Seed | Reported / passenger | Ever ill / passenger | Episode capture |
|---|---:|---:|---:|---:|
| expedition_cruise_450 | 940 | 0.0158 | 0.0380 | 0.416 |
| expedition_cruise_450 | 941 | 0.0032 | 0.0222 | 0.144 |
| classic_cruise_1900 | 940 | 0.4335 | 0.6143 | 0.706 |
| classic_cruise_1900 | 941 | 0.0800 | 0.1868 | 0.428 |

Pooling the passenger-rate numerators and denominators across the two hulls
gives an episode capture of approximately 0.64, within the requested
approximately 0.60 ± 0.05 anchor.  Hull-specific estimates remain noisy
because the two seeds produce very different numbers and timings of illness
episodes.  The dose-conditioned infection-to-illness model and provisional
severity weights were not changed.
