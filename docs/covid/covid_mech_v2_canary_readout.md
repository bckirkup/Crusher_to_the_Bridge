# COVID-RINGCAP-V1 + COVID-SUSCPOOL-V1 — v2 canary read-out (anchor re-measured under `once_per_course`)

**Status: anchor-row canary re-measured under the repaired presentation
draw.** The v1 canary readings (`472cdf13`, `daily_hazard`-era image)
are stale and superseded by this file. The full replay arrays
(240 + 480 cells) and the fleet designs (500 + 1000 cells) are NOT
submitted; this file records the declared anchor-row canary only.

Engine commit `def39066` (design-amendment PR #850, merged). Image
`picard-campaign:covid-mech-v2-def39066`, digest
`sha256:516b0b57b7f7aebea3b301c891d5dfdb10599e9cca271db69fa1610d983484fd`
(built via `deploy/aws/Dockerfile.covid_hull`; the committed
`Dockerfile.covid_mech_v2` in this PR fixes a missing
`covid_hull_entrypoint.py` COPY and produces an identical image).
Job definition `picard-covid-boarding-screen:46` (digest-pinned).
Queue `picard-analysis-queue` (On-Demand CE, max 256 vCPU).

Ring canary: Batch job `e9ee6725-93a7-4b5e-ad27-9ae95cc45a80`
(40 children, indices 0–39 = Theta1e9 anchor row, arms
{cap_on, rings_first} × 20 seeds). Susc canary:
`781041e0-a622-4d49-95d3-f4b6813bf4da` (80 children, indices 0–79,
arms {declared, f025, f050, f075} × 20 seeds). Cells under
`s3://crusherbucket-994254241749-us-east-1-an/campaign/covid_mech_v2/def39066/cells/`
with `manifest.json` + both design JSONs beside it.
**120/120 children SUCCEEDED; 0 failures (0% < the 5% trigger).**

## Flag-landed evidence (audit echoes — new in this campaign)

PR #850 added the echoes the v1 canary lacked: every cell payload now
carries `delivery.exposure_cap_include_fixed_rings_engine` (the
tx-core-resolved flag beside the spec echo) and a `secretor_negative`
declared/resolved/realized block. Readout-side `_audit_cell` verified
every landed cell:

- `rings_first`: spec echo `True`, engine flag `True` — the override
  reached the engine on 20/20 cells.
- `f025`/`f050`/`f075`: declared fraction resolved AND realized —
  epoch-0 drawn fractions sit at the declared values within binomial
  noise (~0.25 / 0.50 / 0.75 over ~3,711 hosts) and every drawn
  secretor-negative host carries `susceptibility_multiplier == 0.0`
  (rel_susc 0.0 landed) on 60/60 cells.
- `cap_on`/`declared` baselines: all nulls — the grammar is inert
  where not declared.
- `delivery.presentation_draw_mode = once_per_course` and
  `hand_reservoir_mode = hygiene_cycle` on all 120 cells — the cells
  ran the repaired draw.
- Audit invariant `index_onset_day = -1.0` +
  `index_shedding_at_day0 = true` on 120/120 cells.

## v15 pairing (the drift audit)

`cap_on` and `declared` reproduce the v15 stage-2 parent row
(`campaign/covid_theta_screen_v15_stage2/6efec855`, base 20200205)
**seed-for-seed exactly**: paired delta medians 0.0 on recorded_onsets,
before_share and infections_total, 0 takeoff-class flips on both
baseline arms. The pairing premise is intact — arm deltas attribute to
the overrides, not stream drift.

## Conditional clause at the Theta1e9 anchor row

Frozen clause (verbatim, unchanged): among takeoff seeds
(recorded_onsets ≥ 10), q05–q95 contains 197 AND median before_share
within 0.10 of 0.173; ≥5 takeoff seeds required.

| arm | takeoff n | q05 | med | q95 | before_share med | clause |
|-----|-----------|-----|-----|-----|------------------|--------|
| ring `cap_on`      | 10 | 153 | 1882 | 2438 | 0.090 | PASS (baseline anchor) |
| ring `rings_first` | 11 | 405 | 2343 | 2460 | 0.343 | **FAIL — both legs** |
| susc `declared`    | 10 | 153 | 1882 | 2438 | 0.090 | PASS (baseline anchor) |
| susc `f025`        | 8  | 227 | 1119 | 1812 | 0.100 | FAIL (q05 floor above 197) |
| susc `f050`        | 6  | 169 | 865  | 1193 | 0.150 | **PASS** |
| susc `f075`        | 5  | 61  | 151  | 553  | 0.410 | FAIL (share leg) |

Report-immediately triggers fired: `anchor_premise_collapsed` on
`rings_first`. Informational `anchor_clause_fail` on `f025`/`f075`
(non-premise arms — they failed the stale canary too).

## Read

**The `rings_first` premise collapsed under the repaired draw.** The
stale canary's only ring-side PASS (n6, [133–3146] ∋ 197, share 0.128
at `daily_hazard`) is gone: under `once_per_course` the q05 floor sits
at 405 (>197) and before_share rises to 0.343 — the mechanism still
moves the row (paired vs v15: 7 takeoff-class flips, q05 −1079 /
q95 +2356 spread vs the parent's fizzle-heavy row) but away from the
record, not toward it. Ring-first budgeting does not rescue the anchor
when the presentation spend is repaired.

**`f050` survives** — the only anchor PASS left standing: takeoff
6/20 ≥ the floor, band 169–1193 ∋ 197, before_share 0.150
(|Δ| = 0.023 < 0.10). Half the pool drawn secretor-negative moves the
anchor row into the clause window.

`f025` fails the count leg from above (q05 227 > 197) — same
direction as the stale run (441), consistent with an under-dosed
response. `f075`'s count leg now *contains* 197 (61–553; median 151
sits just under) but its share leg fails at 0.410 — suppression went
too deep before the split. The fraction response is monotone in the
recorded-count leg (1882 → 1119 → 865 → 151 medians), the mechanism's
declared signature.

Anchor-row takeoff mass under `once_per_course` is higher than the
stale canary's (baseline 10/20 vs 6): fewer courses present → fewer
recorded onsets at fixed truth, so the ≥10-onset takeoff floor is met
more often at Θ1e9.

## Non-goals held

No shipped-default change; no Θ refit; no new mechanisms or arms; no
engine constants touched; no v15 re-run. A clause PASS at the anchor
is a premise-survived measurement only — the admissible-band rows
({1.78e11…5.62e11}, 5 θ × arms × 20 seeds each) are what decide
measured vs dead under the current engine.
