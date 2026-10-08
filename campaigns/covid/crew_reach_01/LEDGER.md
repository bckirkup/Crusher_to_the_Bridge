# CREW-REACH-01 ledger

**Status:** submitted-build stage — canary pending readout.
**Design:** `picard_framework/runs/covid_crew_reach_01_design.json` (frozen pre-run).
**Question:** does the record's serial-testing + crew-reach observation structure move the crew-share landing? (honesty test for ASYM-CONF-01's resolved crew share 0.293 DP-scale vs record 0.29.)

## Arms
- `boxed_declared` — baseline, empty overrides; bit-identity vs landed sect_mess_boxed cells on the day≤31 slice.
- `boxed_s1` — `retest_negative_sweeps` (15–20 Feb retest_tiers).
- `boxed_s2` — `campaign_waves: [crew_wave]` (23 Feb, 831 tests, crew tier).
- `boxed_s1s2` — both.

## Record anchors
- Yamahata & Shibata 2020 (JMIR PHS 6(2):e18821) Table 1: cumulative 3,894 tests vs 3,711 aboard (footnote b: retests documented); 23 Feb = 831 tests / 57 positive = crew wave.
- Retest-tier day placement (15–20 Feb + 23 Feb) is Grade C declared — the record documents retests happened, not their schedule.

## Execution
- Queue `picard-analysis-fargate-queue`, 80 cells, image `covid-crew-reach-01` (digest pinned at submit time — fill in below).
- S3: `s3://crusherbucket-994254241749-us-east-1-an/campaign/covid_crew_reach_01/`.

## Results
_(fill at readout)_
