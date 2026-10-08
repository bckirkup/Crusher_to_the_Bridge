# ASYM-CONF-01
**Date:** 2026-10-08
**Commit:** #976
**Pathogens:** sars_cov2_resp
**Status:** measured
**Measured at:** 29f5e8d1

The asymptomatic-confirmation shortfall on the boxed Diamond Princess
configuration (`sect_mess_boxed`, θ7.9e6) decomposed on five stratified
seeds by same-realization rerun — 20200218 (293 conf), 20200223 (209),
20200210 (76), 20200208 (33), 20200211 (14) — covering fizzle through
DP-scale. Tool `tools/covid_asym_conf_attribution.py`; evidence
`reports/funnel_attr/asym_conf_attr.json`; per-cell confirmed tallies
reconcile exactly with `reports/funnel_attr/boxed20.json`. Asymptomatic
means *not presented (no presentation onset) by specimen epoch* — the
record's own definition (`symptomatic_at_specimen` in
`_campaign_specimen_log`).

## Measurement

Pooled: **625 confirmed of 1,117 infected; asymptomatic-at-specimen
share 0.237 vs the record's ~0.49.** Per-cell shares 0.242 / 0.191 /
0.303 / 0.263 / 0.500 (the two DP-scale cells read 0.242/0.191 — the
shortfall is largest exactly where the record lives).

Confirmed by channel × presentation status, pooled:

| channel | crew | pax | total |
|---|---|---|---|
| campaign, symptomatic-at-specimen | 108 | 160 | 268 |
| passive sick-call, symptomatic | 78 | 141 | 219 |
| campaign, asymptomatic-at-specimen | 37 | 108 | 145 |
| passive, asymptomatic | 3 | 0 | 3 |

(Every asymptomatic confirmation comes through the campaign roster —
the two zero `lab_sampling` rungs close the passive channel by
declaration, as designed.)

The 492 unconfirmed infected decompose:

| drain | crew | pax | total |
|---|---|---|---|
| never swabbed, never presented | **254** | 10 | **264** |
| swabbed while infected, negative | 91 | 73 | 164 |
| swabbed only pre-infection | 14 | 44 | 58 |
| never swabbed, presented | 1 | 5 | 6 |

Three structural findings:

1. **Capacity binds every day.** `specimens == capacity` on 70/70
   campaign days across all five cells — the ladder always holds more
   eligible hosts than slots; nothing under-spends.
2. **The crew-last ordering is the single largest leak.** 254 of the
   264 never-swabbed-never-presented are crew; crew specimens only
   reach double digits on the high-capacity tail days (31–42 swabs/day
   on days 28–31).
3. **The ladder does nominate asymptomatics — the pool is just
   uninfected.** 14,773 of 15,315 campaign specimens (96%) went to
   not-yet-presented hosts yielding 145 positives (1.0% yield). The
   missing mass is not "asymptomatics aren't reached"; it is infected
   hosts below the ladder cutoff plus 222 burned by a negative inside
   the low-sensitivity window (negative swabs cluster at dpi 0–6) or a
   pre-infection swab — negatives retest only through the step-1
   indication tier, never in sweep tiers.

End-voyage catch-all bound (every missed host swabbed once at voyage
end at declared Kucirka sensitivity): ~130 expected positives pooled,
~103 never-presented → asym share would reach only ~0.33. Declining
sensitivity at high dpi caps a one-shot sweep; serial retesting inside
the ladder (what the record actually ran) recovers at mid-dpi values
0.5–0.8.

## Arm-family verdict: nothing expressible through the arm grammar

- **Capacity/order** — binding and structure-bearing, but the ladder
  lives in `data/observation/covid_testing_campaigns.json` + scenario
  wiring (`testing_campaign.start_day`, `retest_negatives_on_indication`),
  outside `ARM_OVERRIDE_KEYS`; a bounded capacity axis is also gated by
  the declared-volumes non-goal.
- **`active_screening`** — armable via `pathogen_overrides`
  (`observation_model.active_screening.enabled`,
  `selection_probability_per_day`) but reaches only symptomatic
  non-presenters (`_specimen_probability` returns 0.0 for
  never-symptomatic hosts) — it would *lower* the asym share.
- **`lab_sampling` non-presenting rungs** — forbidden (declared
  observation model).
- No other override key touches the specimen channel
  (`infection_counters`/`participation_propensity`/`info_suppression`
  are instrumentation or behaviour, not specimens).

## Mechanism seam specified (for a successor leg with engine scope)

- **S1 — retest-negative sweep tiers.** Extend `INDICATION_RULES` /
  `_specimen_barred` (`crusher_labs/modalities/syndromic.py`,
  `crusher_labs/testing_campaign.py`) with a per-tier declared
  `retest_negatives` flag in the campaign JSON schema so DP's serial
  testing (the record retested negatives) can re-swab burned hosts at
  mid-dpi sensitivity. Reach: 164 infected-negative + 58
  pre-infection-negative hosts; expected recovery ~0.5–0.8/host at
  mid-dpi.
- **S2 — crew-reach.** The 254 crew never-swabbed sit below the
  ladder cutoff every day; a declared crew lane or tier reorder in
  `covid_testing_campaigns.json` (record: crew were tested, late) is
  data-side provenance work, not an arm.
- Both are engine/data seams: no `covid_asym_conf_01_design.json` or
  `campaigns/covid/asym_conf_01/` was created — the canary stage is
  void by the deliverable contract (no expressible arm).

Residual honesty note: even perfect capture leaves the share below
~0.4 on these cells — the never-presented share of infections itself
(~38% pooled) bounds the metric from the transmission side, so closing
to ~0.49 may need the infection mix measured next, not only the
observation channel.
