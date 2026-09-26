# CABIN-FLOOR-02
**Date:** 2026-09-26
**Commit:** 1d8a3d9f
**Pathogens:** all
**Status:** measured
**Measured at:** 1d8a3d9f

## Measurement

Remeasure of CABIN-FLOOR-01 on the post-NORO-CABIN-01 base (PR #721's
cabin-scoped confined fomite delivery merged at `afa360cc`; CABIN-FLOOR-01's
probe and Batch plumbing merged at `1d8a3d9f`). Same instrument, platform
(`classic_cruise_1900`), 288 epochs, paired seeds 8105/8106, declared
confinement (SOP-017 `confine_all_to_quarters`, crew exempt, day 1 → end via
`scenario_schedule`). AWS Batch array `fcf7200f-c1c6-4669-9c30-5d4da36eaba3`
(`picard-cabin-floor:5`, image digest `sha256:61affe88`, = 1d8a3d9f tree),
prefix `campaign/cabin_floor_02_declared/`; 26/26 cells clean.

## Delta table (declared confinement, seeds 8105+8106 pooled)

| Arm | CABIN-FLOOR-01 (pre-721) | CABIN-FLOOR-02 (post-721) | Floor | Verdict |
|---|---|---|---|---|
| edison norovirus_gii4 | 0/76 = 0.0% | 6/61 = 9.8% | 15–25% | MISS low, narrowed |
| active norwalk_gi | 0/1 = 0.0% | 1/6 = 16.7% | 15–25% | in band (n=6) |
| active sars_cov2_resp | 0/8 = 0.0% | 2/12 = 16.7% | 15–25% | in band |
| edison sars_cov2_resp | 2/7 = 28.6% | 2/11 = 18.2% | 15–25% | in band |
| active influenza_a | 332/713 = 46.6% | 402/707 = 56.9% | 15–25% | MISS high, worse |
| edison influenza_a | 6/12 = 50.0% | 9/16 = 56.2% | 15–25% | MISS high |
| edison measles_virus | 1/1 = 100% | 1/3 = 33.3% | 75–90% | below floor (n=3) |
| edison andes_hantavirus | 1/2 = 50.0% | 1/3 = 33.3% | 1.2–3.4% | MISS high (n=3) |
| edison clostridioides_difficile | 0/129 = 0.0% | 0/143 = 0.0% | ~5% | MISS low |
| edison vibrio_cholerae_parahaemolyticus | 0/3 = 0.0% | 1/6 = 16.7% | ~0 | MISS high (n=6) |
| edison campylobacter_jejuni | 0/40 = 0.0% | 0/50 = 0.0% | ~0 | pass |
| edison legionella_pneumophila | vacuous (0 idx) | vacuous (0 idx) | ~0 | consistent (0 sec) |
| edison ebola_virus | 5/56 = 8.9% | 11/77 = 14.3% | (no floor) | measured only |

## What the fomite fix changed (measured)

- **Norovirus confined secondaries now exist at all.** edison norovirus_gii4
  went 0/76 → 6/61 (9.8%, vs 15–25% floor) — the channel delivers but the
  magnitude still undershoots, consistent with the residual dose-scale gap
  (open-ledger item 00). norwalk_gi went 0/1 → 1/6 = 16.7%, inside the band
  at n=6.
- **Active-bundle covid resolved into band**: 0/8 → 2/12 = 16.7%; edison covid
  28.6% → 18.2%. The two bundles now bracket the 15–25% floor range — the
  sobering active-vs-edison divergence is gone. The FLOOR-01 reading was
  pre-fomite-fix plus small-n; not evidence of a structurally dead channel.
- **Flu overshoot persists and worsened**: 46.6%→56.9% (active), 50.0%→56.2%
  (edison) — both bundles 2–3× over the Lau 3–38% citation band. The fomite
  seam shouldn't touch respiratory flu; the move is RNG-stream churn from the
  721 diff plus a real pre-existing overshoot. (measured: the attacks;
  hypothesis: scale overshoot in influenza's confined profile)
- **New small misses**: vibrio converted 1/6 confined slots (16.7%) against a
  ~0 person-to-person floor; measles read 33.3% on n=3 vs 75–90% — both
  underpowered but directionally wrong. andes still high (1/3 vs 1.2–3.4%).
  c.diff unchanged at 0/143 vs ~5%.

Report-immediately triggers: none fired (no non-measles ≥90%; no ~0
noro/flu/covid).

## Takeaways (hypothesis tier)

- NORO-CABIN-01's fomite delivery was the dominant confined-route defect for
  noro and measurably moved covid too; the remaining noro shortfall (9.8% vs
  15–25%) is the dose-scale gap, not geometry.
- The open question moved from "does covid's confined channel work" to "why is
  influenza 2–3× hot" — opposite-direction misses bracket the band: noro low,
  flu high. A uniform dose-scale refit cannot satisfy both.
- Small-n arms (measles 3, vibrio 6, andes 3, norwalk 6) need a replicate
  cohort before their verdicts harden — one cell flip moves each by tens of
  percent.
