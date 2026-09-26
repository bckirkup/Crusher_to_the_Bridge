# NORO-REBASE-01
**Date:** 2026-09-26
**Commit:** fbad8738
**Pathogens:** norwalk_gi
**Status:** declared

## Declared design (frozen before any cell ran)

Rebaseline of the VSP posting + attack-rate anchors on the post-#724 engine
(`fbad8738`: cabin-fomite channel live since #721 at `afa360cc`, crew watch
schedules since #723 at `790e090c`, secretor-negative fraction 0.2 live in the
`norwalk_gi` profile via NORO-SUSCEPT-04). Every dose figure in
`docs/norovirus/norovirus_open_ledger.md` stays void pending refit — this
entry measures anchors only and publishes no dose numbers.

- **Cell**: the FLUSH-S4 `off`-arm declared-complement cell verbatim —
  `dose_adjustment` 4.0, `syndromic_comp65`, boarding rung `reportable`,
  `sanitary_visit_mode` `dwell_weighted`, `flush_aerosol_fraction` 0.0,
  `flush_cabin_emission` true, `cabin_air_mode` `cabin_compartment`,
  `hvac.pathogen_pool_transport` `airflow` — so the post-724 delta reads
  voyage-for-voyage against the `flush_sweep_v1_off_s4` archive. The #721/#723
  machinery rides at shipped defaults; this cell's overrides do not touch it.
- **Platforms**: `expedition_cruise_450` (450), `classic_cruise_1900` (1,910),
  `spirit_cruise_3000` (3,000), `mega_cruise_5000` (7,000) — declared
  complements.
- **Lengths**: 168 and 288 epochs (`hours` clock), embarkation 2026-01-10.
- **Seeds**: paired 8105/8106 per cell. 8 cells x 2 seeds = 16 runs.
  Manifest `noro_rebase_01_manifest.json` (tiers `fl_{exp,cls,spr,mega}_{7d,12d}`).
- **Canary**: `fl_spr_12d` at seeds 8105-8124 (20 seeds; manifest
  `noro_rebase_01_canary_manifest.json`) — the strongest posting cell in the
  pre-fix baseline (20 per 1,000 at `off` over the 200-seed block). Gate:
  pipeline end-to-end (run -> zip -> summary.json -> score_anchors) parses
  clean, posting field populated, and the cell is read out before the array
  is submitted.
- **AWS**: `picard-campaign-queue`, prefix `campaign/noro_rebase_01/` and
  `campaign/noro_rebase_01_canary/`, jobdef `picard-campaign:49`, image digest
  `sha256:e1f7b0ccff1db48caaed2c021a17015fd658fb573d92f16805cb3ea5d0c3341c`
  (`picard-campaign:noro-rebase-01`, engine SHA 1935b5d4 = fbad8738 +
  manifest/declared-ledger commit only). Canary Batch array
  `de944b89-2b12-4fd8-bec6-4eeb32797cc3` (20 children).
- **Harness**: `telemetry_buffer/observation_model/score_anchors.py`
  (`--vsp-era pre`), scoring A1/A2/A4/A5/A8/A9 conditional on take-off
  (`peak_prevalence >= 10`); A3 is a construction band, reported not scored.

## Pre-fix baseline (archive, engine `7f689b9`, same seeds)

The `flush_sweep_v1_off_s4` archive at seeds 8105/8106, scored by the same
harness on the extracted shard zips — the voyage-for-voyage baseline. Mega has
no pre-fix reading in this cell (the hull never ran it at declared
complement); its baseline column is empty by construction, not zero.

| hull | take-off | A1 | A2 | A4 | A5 | A9 (per voyage) |
|---|---|---|---|---|---|---|
| expedition | 0/4 | — | — | — | — | 0/4 = 0.00 |
| classic | 0/4 | — | — | — | — | 0/4 = 0.00 |
| spirit | 2/4 | 0.1419 | 0.658 | 0.0869 | 12.04 | 2/4 = 0.50 |
| mega | (no baseline) | — | — | — | — | — |

Caveat carried forward from NORO-EMESIS-SIZE-01: the 8105/8106 pair sits below
the heavy tail on classic — 0/4 take-off there is the pair's reading, not the
cell's distribution (200-seed `off` posting was 5/1,000). The pair is the
convention, not a powered estimate.

## Frozen readout criteria

- Per hull x length: A1/A2/A4/A5/A8/A9 verdicts + raw values, paired against
  the baseline table above where a baseline exists.
- Report-immediately trigger: any platform never posts in both lengths, or a
  platform never takes off.
- Deltas are read against which open-ledger items they support or weaken:
  the posting-surplus property, the crew-route overshoot (A5), and the
  take-off tails noted in the ledger.
