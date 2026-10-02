# NORO-OUTBREAK-01 design — small-hull outbreaks vs the anchors

Status: declared, pre-run. Criteria in this file are frozen before any cell
runs; nothing below is altered after the surface is seen. Companion campaign
to NORO-IMPORT-01 (`docs/ledger/NORO-IMPORT-01.md`), whose import-region map
is the settled input this campaign does not re-derive.

## Question

With the hand-reservoir rebuild (hygiene_cycle + protected sequestration +
own-pool, shipped default through `a3c76061`) and the presentation-share
repair (`presentation_draw_mode: once_per_course`, `890bfce3`) landed, how do
simulated norovirus outbreaks on the smaller VSP hull classes score against
the anchor set: frequency (posting probability, takeoff, establishment),
progression (within-voyage epidemic curve), and ultimate attack rate
(reported passenger AR vs the hull-class IQR, infection/ever-ill AR)?

## Cell layout

Two scored hulls, IMPORT-01's axis pins reduced to the axes that bind:

- expedition_cruise_450 at 168 epochs (7 d) and 288 epochs (12 d);
- classic_cruise_1900 at 288 epochs (12 d).

Per hull × length, four cells:

| cell | rung | prevalence (pax, crew) | nsf |
|---|---|---|---|
| scr-lo | `shipped` (screening comparator) | (0.025, 0.007) | 0.29 |
| scr-mid | `shipped` | (0.0325, 0.0185) | 0.29 |
| scr-hi | `shipped` | (0.040, 0.030) | 0.29 |
| ren | `reportable` (shipped default: renewal + stream + crew clause) | derived (~0.42%) | 0.29 |

`dose_adjustment` fixed 7.57 (void pending refit; every dose figure quoted
is void — the axis exists only because the zip contract requires it).
Surveillance `syndromic_comp65` (diagnostic cascade disabled; quarantine
compliance crew 0.65 / pax elderly 0.54 / pax young 0.34). IMPORT-01's
`config_overrides` pins verbatim (sanitary_visit_mode dwell_weighted,
flush aerosol 0, cabin compartment air, hvac pathogen_pool_transport
airflow). `embarkation_date` 2026-01-10, clock `hours`, `norwalk_gi`
under `active_profiles` with `sars_cov2_resp` removed.

nsf is fixed at the shipped 0.29: IMPORT-01 measured it a weak axis and the
question here is the anchor score, not re-mapping the licensed region.
`renewal_stationary` (stream off) is dropped for the same reason — the ren
arm is what the model ships.

## Seeds and pairing

- expedition: 1000 seeds per cell, `8000-8999` — voyage-for-voyage paired
  with NORO-IMPORT-01's nsf-0.29 cells on the same seeds.
- classic: 1000 seeds per cell, `8105-9104`; the leading 200
  (`8105-8304`) pair with NORO-IMPORT-01's classic cells.

12 cells x 1000 = 12,000 voyages.

At the A9 interval midpoint (0.49%), 1000 seeds yield ~5 postings and a
Wilson 95% interval spanning roughly [0.2%, 1.1%] — enough to separate
"still at the quiet-region floor" (~3%) from "inside A9", not enough for a
fine rate. Posting-frequency resolution finer than that is deferred to the
full-campaign decision.

## Instruments (reported; none selected on)

Per cell, from each run zip's `summary.json` / `growth_census.json.gz` /
`initiation` block:

- frequency: emesis-ignited, imported (`n_imports > 0`), established
  (`n_acquired > 0`), takeoff (`peak_prevalence >= 10`), posted
  (`vsp_trigger_epoch` set AND exceeding the reported-case counter
  threshold) — each as a fraction with Wilson 95% CI;
- progression: among takeoff voyages — distributions of onset epoch,
  `detection_epoch`, `peak_epoch`, `vsp_trigger_epoch`, outbreak span
  (last epoch with new infections, minus onset), peak prevalence, and
  first-doubling time; a median curve summary (per-epoch quantile band of
  `infected`/`new_infections`/`cumulative_reported_cases_passenger`);
- attack rate: the anchor table per `telemetry_buffer/observation_model/
  score_anchors.py` (`row_from_summary` -> `summarise_cell` -> `verdicts`,
  era `pre`) — A1 ever-ill pax (0.10-0.22), infection AR, A2 ill/infected
  (0.59-0.81), A4 reported pax AR vs the hull-class IQR
  (`vsp_outbreak_series.csv` runtime targets: expedition
  4.00/5.32/10.45%, classic 4.15/5.52/7.82%), A5 pax/crew ratio
  (2.5-4.5), A8 incidence per 100k travel-days, A9 posting probability;
- paired delta vs NORO-IMPORT-01 on shared seeds: discordant
  establishment/takeoff pairs and the signed shift in acquired/onset
  distributions, attributing the hand + presentation merges.

A3 (reported/ever-ill) remains a reported-but-not-scored construction
band; A10 is proposed, not scored; A6/A7 not in this cell set.

## Report-immediately triggers

- Any cell posts materially above A9's ceiling (Wilson upper bound
  clearly above ~3%: the pre-hand quiet-region floor, i.e. a reversal of
  the frequency direction).
- Any license-mid cell's posted-outbreak reported pax AR lands above the
  hull-class IQR ceiling (a new defect direction: outbreaks too large,
  not just too frequent).
- Establishment/takeoff changes vs IMPORT-01 paired seeds indistinguishable
  from zero on every cell (the hand rebuild would be inert at voyage scale,
  contradicting the census measurements — escalate as evidence-against).

## Gates (campaign-preflight)

1. This file + the manifest committed before any cell runs (this PR).
2. Local smoke: one voyage locally on the smoke cell, asserting the
   swept prevalence resolves into `summary.json.parameters`
   (`boarding_passenger_prevalence`/`boarding_crew_prevalence`,
   `boarding_mechanism_rung`, `boarding_rate_mode`) and the zip contract
   is intact (summary/timeseries/census/initiation blocks).
3. Image built at the PR's merged SHA (overlay on the
   `flu-rhythm-02-1ab8dd98` base; `natural_history.py` + schema + `tools/`
   + manifest at HEAD); jobdef `picard-noro-outbreak-01` registered at
   that image digest, recorded below.
4. Canary >= 20 seeds on `fl_exp_12d_scr` cell interior (index_offset 1000
   lands inside the scr-mid cell), read out with the anchor readout —
   then STOP and report; the full array waits for the user's decision.

## Artifacts (fill at submission)

- manifest: `picard_framework/runs/mega_cruise_campaign/noro_outbreak_01_manifest.json`
- readout: `tools/noro_diag/outbreak_anchor_readout.py`
- image tag: `picard-campaign:noro-outbreak-01-<sha>` (digest recorded in
  ledger)
- jobdef: `picard-noro-outbreak-01:<rev>` (revision recorded in ledger)
- S3 prefix: `s3://<bucket>/campaign/noro_outbreak_01/`

## Non-goals

- Spirit/mega hulls (the larger classes follow in a later stage).
- Re-fitting `dose_adjustment` or any constant; the A4/A9 targets are
  scored, never selected on.
- Voyage-length product beyond 7d/12d on expedition and 12d on classic.
