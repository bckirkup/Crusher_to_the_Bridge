Status: measured readout (frozen design `noro_channel_03_design.md`).

# NORO-CHANNEL-03 measured readout — conversion-link attribution

Measured at `d6c51c14` (jobdef `picard-noro-channel-03:1`, image
`picard-campaign:noro-channel-03-d6c51c14`). 180 funnel voyages over 9
declared cells — per hull {scr-mid, scr-hi, ren} at 12 d, 20 seeds each
(exp 8000-8019, cls/spr 8105-8124) — executed as the *same* spec+seed
voyages NORO-OUTBREAK-01 scored.

## Join verification

Zero disagreements across all 180 seeds: every funnel voyage's `took_off`
matches its scored map voyage's `peak_prevalence >= 10` status. The
determinism premise (same spec + seed → same voyage) holds at scale.

## Pooled conversion chain (takeoff-conditional)

Ratios are pooled counts over takeoff voyages. Verdict applies the frozen
thresholds: symp <0.6 → A2 link; elig <0.7 → severity wall; rep <0.4 →
report hazard.

| cell | n (tookoff) | symp/infected | elig/symp | rep/elig | conf/rep | dated/conf | verdict |
|---|---|---|---|---|---|---|---|
| fl_cls_12d_ren/rung-reportable | 20 (13) | 0.222 | 1.000 | 0.321 | 0.241 | 0.846 | A2 link — symptom-course draw under-fires (0.222 < 0.6) |
| fl_cls_12d_scr/rung-shipped-bp32p5c18p5 | 20 (20) | 0.363 | 1.000 | 0.242 | 0.368 | 0.717 | A2 link — symptom-course draw under-fires (0.363 < 0.6) |
| fl_cls_12d_scr/rung-shipped-bp40c30 | 20 (20) | 0.371 | 1.000 | 0.239 | 0.398 | 0.740 | A2 link — symptom-course draw under-fires (0.371 < 0.6) |
| fl_exp_12d_ren/rung-reportable | 20 (2) | 0.280 | 1.000 | 0.429 | 0.333 | 1.000 | A2 link — symptom-course draw under-fires (0.280 < 0.6) |
| fl_exp_12d_scr/rung-shipped-bp32p5c18p5 | 20 (18) | 0.413 | 1.000 | 0.172 | 0.371 | 1.000 | A2 link — symptom-course draw under-fires (0.413 < 0.6) |
| fl_exp_12d_scr/rung-shipped-bp40c30 | 20 (19) | 0.390 | 1.000 | 0.168 | 0.263 | 0.700 | A2 link — symptom-course draw under-fires (0.390 < 0.6) |
| fl_spr_12d_ren/rung-reportable | 20 (19) | 0.170 | 1.000 | 0.316 | 0.324 | 0.743 | A2 link — symptom-course draw under-fires (0.170 < 0.6) |
| fl_spr_12d_scr/rung-shipped-bp32p5c18p5 | 20 (20) | 0.333 | 1.000 | 0.238 | 0.279 | 0.632 | A2 link — symptom-course draw under-fires (0.333 < 0.6) |
| fl_spr_12d_scr/rung-shipped-bp40c30 | 20 (20) | 0.368 | 1.000 | 0.267 | 0.402 | 0.820 | A2 link — symptom-course draw under-fires (0.368 < 0.6) |

## Reading

- **The A2 link (symptom-course draw) is the primary gap on every cell** —
  pooled symptomatic courses per infected host run 0.170-0.413 against the
  declared 0.6 threshold (A2's anchor band is 0.59-0.81). Renewal-rung
  cells sit lowest (0.170 spr, 0.222 cls): imports arriving already ill
  thin the denominator's convertable population less than their rungs
  suggest — the draw still misses.
- **No severity/eligibility wall**: elig/symp = 1.000 on all 9 cells.
  Every symptomatic course is syndrome-eligible.
- **The report link shares the deficit**: rep/elig is under the 0.4
  threshold on 8 of 9 cells (0.168-0.321; only exp_ren's n=2 cell reads
  0.429). Attribution verdicts name A2 because it is the first broken
  link, but a symptomatic host only reports on ~17-32% of shipped cells —
  both links must move to reach the anchors; neither alone suffices.
- **Not-reported decomposition** (hosts with exposure): on scr cells
  `course_not_symptomatic_onboard` dominates (exp ~148-161, cls ~599-767,
  spr ~921-1182) over `visible_whole_course_draw_missed` (~30-424) —
  most symptomatic courses on screening rungs happen off-voyage (imports
  presenting pre-boarding), so the onboard-eligible pool is thin AND the
  onboard draw under-fires. On ren cells the draw-miss dominates spr
  (166 vs 73) and cls (79 vs 59).
- **Downstream leaks are secondary**: lab confirmation retains only
  0.24-0.40 of reported cases, onset dating 0.63-1.0 of confirmed — they
  compound the visible shortfall but are not the first-order gap.

Measured basis for the open-ledger conversion question: of the A1/A2/A4
deficit OUTBREAK-01 found, the conversion gap is **shared** between the
symptom-course draw (A2 link) and the infirmary report hazard (A4 link),
with A2 primary on all cells.
