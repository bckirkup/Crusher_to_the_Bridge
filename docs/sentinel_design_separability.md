# Sentinel design separability

The Sentinel fleet model observes a port hazard and a fleet-time effect
together. Before fitting the model, the itinerary can therefore be checked for
whether the port effects are identifiable from the calendar-week effects.

## Identification convention

Fleet time is **uncentered**. A single global level shift is consequently
always unidentified: adding a constant to every port effect and subtracting it
from every fleet-time effect leaves the linear predictor unchanged. With `P`
ports and `W` weeks, the identified rank is therefore `P + W - 1`.

The per-port quantity is not a naive VIF on a port level. A level is not
estimable under the global shift (or under disconnected port-week components).
Instead, the diagnostic uses the within-component estimable contrast: one port
minus the mean of the other ports in its connected component. Its contrast
variance is compared with the port-only variance to report variance inflation.
An infinite variance and inflation mean that the contrast is not estimable.

Structural weighting treats each visit as one unit of information. Exposure
weighting scales information by ashore person-hours at the reference hazard.
The structural result answers **whether** the design separates effects; the
exposure-weighted result answers **how precisely** it does so for the available
exposure.

## CLI

Diagnose every bundled design and write the summary and per-port outputs:

```bash
python3 -m picard_framework.analysis.sentinel.separability \
  --all-presets --write-visits --out separability_run
```

Use `--preset NAME` for one or more named designs, or `--visits table.json`
for a JSON or CSV visit table. Output paths are confined to the working
directory.

## Bundled designs

| preset | verdict | P | W | S | visits | cells | rank | excess | comps | calls/ship-week | structural VIF | exposure SE | hours/port |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- | --- | ---: |
| caribbean_partial_overlap | identifiable | 40 | 12 | 120 | 5244 | 480 | 51/51 | 0 | 1 | 3.64 | median 1.0005, max 1.0069 | median 0.0679, max 0.3734 | median 2.21e6 |
| alaska_full_overlap | identifiable | 10 | 12 | 25 | 1500 | 120 | 21/21 | 0 | 1 | 5.00 | median 1.0000, max 1.0000 | median 0.0673, max 0.0692 | median 1.99e6 |
| mediterranean_sparse | identifiable | 60 | 14 | 80 | 3716 | 672 | 73/73 | 0 | 1 | — | median 1.009, max 1.033 | max 0.1882 | — |
| pilot_eight_ship | identifiable | 6 | 8 | 8 | 184 | — | 13/13 | 0 | 1 | — | max 1.036 | max 0.1853 | — |
| degenerate_lockstep | degenerate | 6 | 12 | 12 | 144 | 12 | 12/17 | 5 | 6 | — | inf; all 6 ports non-separable | — | — |
| staggered_control | identifiable | 6 | 12 | 12 | 144 | 72 | 17/17 | 0 | 1 | — | 1.0000 | max 0.1881 | — |

## Sensitivity findings

Ship-to-ship itinerary overlap is **not** what breaks separability of
`lambda_port` from `fleet_time`. Near-total overlap (Alaska) produces a
balanced, essentially orthogonal port-by-week table (VIF 1.0000) and the
tightest standard errors of any preset. What destroys identifiability is a
week in which the whole fleet calls at only one port: that port hazard and
that week's fleet-time effect are literally the same column. The
`degenerate_lockstep` design has rank 12/17 and six disconnected blocks, while
`staggered_control` reaches 17/17 by spreading ships across ports within a
week. The fix is within-week spreading, not sail-day staggering by itself.

The measured sensitivity checks support that interpretation:

* Caribbean with `port_step=0` remains identifiable at rank 51/51, but its
  structural VIF median/max rise from 1.0005/1.0069 to 1.2277/1.3313.
* Alaska with `sail_day_stagger=7` changes VIF median only from 1.0000 to
  1.0012.
* Alaska with 120 ships reduces exposure SE from 0.0673 to 0.0308.
* Caribbean with 25 ships becomes `weak`; exposure SE rises to median 0.1518
  and max 0.8453.

Thus overlap costs at most roughly 20–30% in contrast variance in the
Caribbean example, while exposure dilution costs much more: at 25 ships the
per-port result is about 2.2 times worse and tips to `weak`. Alaska's real
advantage is concentration—25 ships' person-hours over 10 ports rather than
40—not overlap. Its limitation is that only 10 port hazards are estimable.
