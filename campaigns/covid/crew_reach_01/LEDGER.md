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
- Queue `picard-analysis-fargate-queue`, 80 cells (4 arrays × 20), submitted 2026-10-08 ~20:58 UTC.
- Image `picard-campaign:covid-crew-reach-01` @ `sha256:6f0f72bc23503f0513702fc0698711617872700229b70f3adc2b1e1b2297ef4d` (merged SHA `90b2fdae`, PR #977).
- Jobdef `picard-covid-crew-reach-01:1` (Fargate, `assignPublicIp: ENABLED`; revs :2–:5 are stale EC2-shape re-registers from `scripts/campaign submit` — pinned to :1 explicitly).
- Arrays: boxed_declared `81e81604-9543-4da8-a2fe-1399ba62c253`; boxed_s1 `3e9af4f2-7187-4302-8a46-5462510e4c2f`; boxed_s2 `8b61962b-89e5-4f00-9528-616ccf22eea9`; boxed_s1s2 `231ceb90-65c2-4730-8dc0-d5f839797f24`.
- S3: `s3://crusherbucket-994254241749-us-east-1-an/campaign/covid_crew_reach_01/`.

## Results
Measured 2026-10-08 at `90b2fdae` — 80/80 cells, zero child failures.
Readout: `reports/crew_reach_01/readout.md`; full entry:
`docs/ledger/CREW-REACH-01.md`.

| arm | pooled lab_conf | Δ vs parent boxed (819) | crew share pooled / DP-scale | verdict |
|---|---|---|---|---|
| boxed_declared | 1354 | +535 | 0.399 / 0.308 | record-truth base |
| boxed_s1 | 1333 | +514 | 0.398 / 0.315 | NO-MOVE |
| boxed_s2 | 1453 | +634 | 0.440 / 0.350 | MOVES-TOWARD-RECORD |
| boxed_s1s2 | 1451 | +632 | 0.447 / 0.358 | MOVES-TOWARD-RECORD |

- **Honesty test: physics holds.** DP-scale crew share 0.308 → 0.350/0.358
  under crew reach — inside the declared 0.29–0.4 band; the >0.5 hot-crew
  alarm does not trip.
- Declared `retest_tiers` alone recapture +535 pooled (~87% of the
  burned-negatives drain, ~656 pooled-equiv); `crew_wave` adds +97–99;
  S1 sweep re-nomination adds nothing (−21) while churning ~41k specimens.
- asym share 0.184 → 0.23–0.25 (correct direction, under the ~0.4 bound);
  dated share ~0.69–0.76 vs record 0.277 — dominant residual unchanged.
- Errata (recorded in `docs/ledger/CREW-REACH-01.md`): the frozen
  bit-identity clause is unmeetable — retest tiers are declared scenario
  data, not arm-gated, so the "unarmed" arm fires retests and consumes
  RNG (14/20 seed DIFF on day≤31 infections = re-realization). The
  parent's boxed cells are the labelled pre-change baseline. Deliveries
  median 192,772 vs band top 186,814 is the declared 32→35-day voyage
  extension (uniform +30.5k, identical across arms — parity holds).
