# SARS-CoV-2 arm — execution status and diagnosis

> **Status:** Findings, 2026-09-01. Records what the `sars_cov2_resp` arm of the
> mega cruise campaign actually does. No constant was changed to close any gap
> described here.

The campaign carries two pathogen arms (`picard_framework/runs/mega_cruise_campaign/campaign_manifest.json`):
`norovirus` → `norwalk_gi`, and `sarscov2` → `sars_cov2_resp`, each removing the
other from the bundle. Both were traced end to end — manifest selection, profile
resolution, simulation, telemetry, summary counters — on
`expedition_cruise_450` (316 passengers + 134 crew), 450 agents, seed 42, tier
`t1_pathogen_baselines`, 240 epochs. With `epoch_duration_hours: 1` and
`natural_history_clock: hours`, **240 epochs is a ten-day voyage.**

## What works

Profile resolution is correct in both directions: the removed pathogen id
appears nowhere in the run's history, timeseries or summary — only in the
`pathogen_overrides.remove` list of `run_spec.json`. Role-split counters,
complements and the VSP reported-rate threshold flag are present in both arms.
The resolved profile set is now serialised per run
(`resolved_pathogen_profiles.json`, plus `pathogen_ids` in `summary.json`), so a
campaign that diverges from the validated profile is detectable after the fact;
`tests/test_pathogen_arms_smoke.py` holds both arms to that contract.

## What does not

Ten days, one introduction, seed 42:

| | norovirus | SARS-CoV-2 |
|---|---|---|
| ever infected | 96 (73 pax / 23 crew) | 2 (2 pax / 0 crew) |
| ever ill | 36 | 2 |
| reported cases | 12 | 1 |
| passenger infection attack rate | 0.231 | 0.0063 |

Accumulated dose delivered over the whole run, by pathway:

| pathway | norovirus | SARS-CoV-2 |
|---|---|---|
| direct_contact | 3,257,615 | 0.0114 |
| fomite | 63,652 | ~0 |
| droplet | 7,334 | 0.0001 |
| hvac_airborne | 81 | 0 |
| food | 198 | n/a |

The profile's own beta-Poisson (α 0.18, β 58) puts N50 at ≈2,670 particles. The
respiratory arm delivers five orders of magnitude less than that across an
entire voyage, so no host after the index case is ever meaningfully challenged.
Shedding itself is not absent — 337 shedder-epochs, median 0.0069, max 686
particles/epoch, against norovirus's 14,983 shedder-epochs, median 684, max
6.96e6.

## Four findings, in descending confidence

**1. The only shedding scaler is a faecal-release term, and the respiratory arm
is paying it.** Emission is `10^(curve − adj)` per epoch, where `adj` comes from
`environmental_faecal_release_log10_g_per_epoch()`
(`engines/infection_dynamics_bridge.py`), documented as −log10 of the grams of
stool released to the environment per epoch, with `dose_adjustment` accepted as
a legacy alias. `sars_cov2_resp` carries `dose_adjustment: 3.0`, so every
respiratory emission is divided by a thousand for a stool-mass reason. This is
not a case of a value being off its literature anchor: there is no respiratory
quantity the key denotes. It cannot be repaired by zeroing it either — the
profile's incubation note already references its N50 "in model units", i.e.
units this same key defines, so the emission scale and the dose-response
denominator have to be set together against a respiratory measurement (copies
per expelled respiratory volume) rather than adjusted one at a time.

**2. Voyage geometry cannot resolve a SARS-CoV-2 generation.** Incubation median
is 5.8 days (dispersion 1.57) with a 2.0-day presymptomatic shedding window and
`recovery_day: 7`. Introduced at epoch 6, the index case reaches curve index 2
(7.0 log10) at about day 8 of a ten-day voyage; the 9.0 log10 peak at index 4
falls outside it. Under two generations fit. The COVID evidence base is a
trajectory on a handful of hulls — Diamond Princess was a confined event of
roughly four weeks — so the arm has to be run on a scenario whose duration
matches the trajectory it is scored against, not on cruise-voyage geometry
inherited from the norovirus arm. Some of the gap in the table above is this,
not the profile.

**3. The arm has no `severity_model` and no `observation_model`.**
`orchestrator_init.py` requires the two to be *paired* if either is present; it
permits both to be absent. The consequence is silent rather than fatal:
`_draw_symptom_severity` returns an empty severity string
(`orchestrator_epoch.py`), and `_severity_hazard`
(`crusher_labs/modalities/syndromic.py`) then falls back to the flat base
`sick_call_probability`. Norovirus reporting is severity-graded through five
states; COVID reporting is one flat hazard. Any reported-case channel (A8/A9)
therefore means something different in the two arms, and that difference is
currently invisible in the output.

**4. Declared route weights are not realized shares, on this arm too.** The
profile declares droplet 0.30 and hvac_airborne 0.30; they delivered 1e-4 and 0
of the total dose. This is the same defect already recorded for norovirus in
`docs/norovirus/norovirus_parameter_freedom_audit.md` — the six values act as
independent multipliers, not a partition — now confirmed on the respiratory
arm, where the mismatch is starker because the two nominally dominant routes are
the ones contributing nothing.

## What this does not license

Nothing here justifies moving a biological constant to raise the SARS-CoV-2
attack rate. Findings 1 and 3 are provenance and structure defects with fixes
that must be sourced independently
(`.agents/skills/model-parameter-provenance/SKILL.md`); finding 2 is a scenario
design question, not a parameter; finding 4 is a naming and semantics decision
already open. The honest current statement is that the SARS-CoV-2 arm executes
and is instrumented, and that it is not yet scoreable against the trajectory
evidence.
