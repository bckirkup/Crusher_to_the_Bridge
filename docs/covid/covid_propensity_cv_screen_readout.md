# PROPENSITY-CV-01 readout — the cv sensitivity screen at the Θ1e9 anchor: the whole declared dispersion range is dead

> **Status:** Findings (2026-10-03). Screen measured at `e0d43979`
> (image `picard-campaign@sha256:a5a9bdd7…` / tag
> `campaign-e0d43979-cvscreen` — a thin overlay on the canary's
> `campaign-e0d43979` adding only the design file; the merged tree
> `e0d43979..d0f03fa3` carries zero engine/spec/worker-path change —
> jobdef `picard-covid-boarding-screen:48`, queue
> `picard-analysis-queue`, prefix
> `campaign/covid_propensity_cv_screen/e0d43979/cells/`; the submitting
> prefix was passed one level deep so the originals also remain under
> `cells/cells/` — non-canonical duplicates of the same bytes; the flat
> `cells/` set is canonical).

PROPENSITY-V1 (PR #860, ledger `docs/ledger/PROPENSITY-V1.md`, spec
`docs/propensity_v1_spec.md`) shipped the persistent per-party
contact-propensity term with `cv` 0.8 at the centre of a declared Grade C
cell — the spec's widest unmeasured point. The `covid_propensity_v1`
canary (PR #868, `docs/covid/covid_propensity_v1_readout.md`) measured the
shipped 0.8 dead at this anchor: clause FAIL on both arms, seed-paired
footprint noise. PROPENSITY-CV-01 (design
`picard_framework/runs/covid_propensity_cv_screen_design.json`, PR #869)
asks the screen question that decides whether any of the mechanism's
declared range is still live: score the frozen v11-lineage clause at
cv ∈ {0.2, 0.4, 0.8, 1.2, 2.0} on the identical replay contract, and read
the seed-paired cv-response curve. No cv is selected; the clause is
scored per arm, never an admission.

Campaign gate executed: design PR merged (`d690fc02`, under
`d0f03fa3`) → local `echo_screen_cell` audit resolved each arm's declared
cv/mode + fixed echoes → image at the engine SHA → digest-pinned jobdef
(`:48`) → 120-cell array (`0a938afd`, `picard-covid-screen-20261003-223402`).
All 120/120 cells SUCCEEDED, zero failures, zero audit failures; ~100 min
wall on On-Demand (`picard-analysis-queue`).

## Clause scorecard (per arm, takeoff-conditional)

| arm | cv | takeoff | rec q05/med/q95 | before_share med [q05,q95] | clause |
|-----|---:|--------:|------------------|---------------------------|--------|
| CV020 | 0.2 | 20/20 | 1,411 / 2,385 / 2,453 | 0.427 [0.157, 0.809] | FAIL both legs |
| CV040 | 0.4 | 20/20 | 1,007 / 2,333 / 2,486 | 0.428 [0.186, 0.838] | FAIL both legs |
| D0_declared | 0.8 | 19/20 | 1,518 / 2,321 / 2,445 | 0.452 [0.234, 0.900] | FAIL both legs |
| CV120 | 1.2 | 20/20 | 1,005 / 2,231 / 2,441 | 0.377 [0.233, 0.859] | FAIL both legs |
| CV200 | 2.0 | 20/20 | 1,795 / 2,357 / 2,441 | 0.427 [0.220, 0.863] | FAIL both legs |
| PROP_OFF | — | 20/20 | 1,190 / 2,343 / 2,443 | 0.397 [0.213, 0.649] | FAIL both legs |

`mass_near_t1` = 0 on every arm — no takeoff seed lands within
[98.5, 394] of the record under any declared dispersion. No
report-immediately trigger fired (`triggered_rows` empty;
`tools/covid_propensity_cv_screen_readout.py`).

## The mechanism exercised at every cv, and the response curve is flat

The pairing audit passed verbatim: `propensity_draw.units_drawn` med
2,091 per armed cell (0 on all 20 PROP_OFF cells — the bit-identity
witness), and the per-arm multiplier q95 widens monotonically in cv
exactly as the audit invariant requires:

| arm | cv | multiplier q05 / med / q95 |
|-----|---:|----------------------------|
| CV020 | 0.2 | 0.708 / 0.979 / 1.354 |
| CV040 | 0.4 | 0.493 / 0.925 / 1.739 |
| D0_declared | 0.8 | 0.246 / 0.776 / 2.455 |
| CV120 | 1.2 | 0.136 / 0.635 / 2.981 |
| CV200 | 2.0 | 0.056 / 0.442 / 3.531 |

The declared dispersion genuinely reached the deal on every arm
(q95 ~1.4 → ~3.6 across the grid) — and the anchor does not respond.

The cv-response curve — seed-paired (arm − PROP_OFF) medians with
q05–q95, the deliverable of this screen:

| arm | cv | Δ recorded_onsets | Δ before_share | Δ infections_total |
|-----|---:|--------------------|----------------|--------------------|
| CV020 | 0.2 | +58 [−909, +1211] | +0.129 [−0.229, +0.262] | +79 [−1113, +1618] |
| CV040 | 0.4 | +15 [−360, +1099] | +0.043 [−0.160, +0.266] | +6 [−521, +1493] |
| D0_declared | 0.8 | −12 [−657, +923] | +0.047 [−0.171, +0.494] | +23 [−857, +1164] |
| CV120 | 1.2 | 0 [−486, +667] | +0.033 [−0.173, +0.288] | −11 [−606, +967] |
| CV200 | 2.0 | +31 [−323, +1151] | +0.077 [−0.205, +0.211] | +44 [−377, +1539] |

Every interval straddles zero, the medians show no monotone ordering in
cv, and no leg approaches the record — the count leg misses 197 by ~10×
at every cv; the timing leg misses 0.173 by ~0.2+ at every cv. The fleet
shape indicator confirms the saturation does not move: takeoff 19–20/20
and attack-rate medians ~0.86–0.88 on every arm (record ~0.19 attack).

## Cross-run replication: the baseline arms are bit-identical to the canary's

`paired_vs_canary` (declared diagnostic): all 20 seed-paired cells on
D0_declared and all 20 on PROP_OFF reproduce the `covid_propensity_v1`
canary's recorded_onsets / onsets_before_split_day / infections_total
**exactly** (max |Δ| = 0) — the e0d43979 overlay is engine-equivalent to
the canary generation, as the `e0d43979..d0f03fa3` diff promised. The
canary's dead-at-anchor verdict is therefore re-measured, not inherited.

`paired_vs_v15_anchor` (declared diagnostic, reported never selected):
every arm sits ~+1,600 to +2,080 recorded onsets above the v15
`6efec855` row seed-paired (e.g. PROP_OFF +1,634 med, D0 +1,785 med —
the identical number the canary measured, as bit-identity requires), and
v15's 10/20 takeoff is now 19–20/20 on every arm. The engine drift
between the generations stands as the canary recorded it; nothing in
this screen changes that attribution.

## Verdict

**Measured:** at the Θ1e9 anchor, participation-propensity dispersion is
a noise-level axis across its entire declared range — 0.2 through 2.0
span a factor-10 tail ratio in the dealt multipliers and move neither
clause leg, with seed-paired medians of −12 to +58 onsets against ~2,300
cell mass and every interval straddling zero. The PROPENSITY-V1
mechanism family is dead at anchor at every declared dispersion —
retired on its own declared test, alongside RING-CAP-V1, SUSCPOOL-V1,
the frailties, and suppression.

**Inferred (not measured):** since the curve is flat where the clause
was ever scored and the canary found no systematic footprint even at
best-case leverage, a band-stage sweep of this axis is unlikely to show
anything different; the binding residual does not live in per-party
participation heterogeneity. The remaining heterogeneity surfaces are
the ones the spec and ledgers never shipped or never measured at anchor:
symptom-expression/severity structure (the channel the noro funnel
blames in the other direction), immune/secretor-structure per-host
terms, and the CAREGIVER-V1 interval bounds awaiting their funnel
license.

**Open decision for the user:** retire the propensity family (this
screen is the measurement of record) and point the heterogeneity hunt at
the next declared layer, or spend a band stage on cv anyway. The
screen's own read is that the family is closed.
