# SUPPRESS-V1
**Date:** 2026-09-30
**Commit:** <fill at merge>
**Pathogens:** sars_cov2_resp
**Status:** declared

The SUPPRESS-V1 conditioned array: mid-voyage suppression dynamics —
the surviving suspect class after six measured retirements (COOP-V1
dose law, Θ V12/V13 + SERO-CHANNEL-V1, ASCERTAIN-V1 `channel_only`,
SEED-GEOM-V1 `geometry_incapable`, SUSCEPT-V1 susceptibility structure,
HEAT-V1 `delivery_incapable`). The axis is the DP scenario's **single
scheduled-protocol slot** swept over {protocol × window}: scheduled
(forced) protocols bypass the trigger/escalation/activation-delay
gates, so any shipped protocol can occupy the slot at any declared
window.

## Lattice (declared verbatim)

- **SOP-017 retimed** start_day {4, 6, 8, 10, 12, 14} (end 30) — the
  deep corners bound the axis; day 4 fires ~11 days before the record's
  order while the burn is still exponential.
- **SOP-009** {10, 12} — the LOCKDOWN-grade order: confine_all + hard
  channel scalars {contact 0.1, droplet 0.1, fomite 0.2, hvac 0.7} +
  galley/mess closed; only medical/engineering crew exempt.
- **SOP-017-ALLHANDS** {12} — zero exemptions (historically false:
  real DP crew kept working). **Non-scoring diagnostic**: isolates the
  crew-exemption leak.
- **SOP-011** {10} — symptomatic-only confinement, the honest
  pre-Feb-5 signature.
- **SOP-007** {10, 12} — galley + crew-mess closure + occupancy cap 2,
  no confinement: venue removal vs the dominant zone-pool venue.
- **SOP-017 {40,45}** — never-binds witness (voyage ends day 32).
- **D0_declared + REF_M0P56** — paired baseline + the ASCERTAIN-V1
  count-matched channel row.

15 arms × θ {1e11, 2.37e11, 1e12} × seeds 20200205–14 = **450 cells**
(anchor-first, canary arms front-loaded: cells 0–9 D0, 10–19
SOP017_D4, 20–29 SOP009_D12). Arithmetic flagged to the author at
design time: the task's ~540–660 estimate and ≥20-seeds/row canary
both imply a wider seed block — declared at the canonical 10-seed
matched block pending his call (seeds 14 → 630; seeds 20 → 900).

## Legs

Takeoff-conditional `infections_total` vs held-out band [712, 960];
`recorded_onsets` vs 197; `before_share` vs 0.173 ± 0.10 at the
**record's** day-16 boundary on every arm (a retimed window moves the
arm's kink, not the record's split). Shape discriminators:
during-window-dominant + cabin/crew-mess concentration + crew lag =
truncation; starved during stratum = ceiling; mass deferred across the
arm's own start day = HEAT-V1's deferral (converse of record). All
timing landings require nonzero seed-paired Δ vs D0 — in-band medians
with Δ≈0 are takeoff-set composition.

## Harness notes (readouts only, no physics)

`_quarantine_window` generalized: SOP-017-prefix match first, else the
run's single scheduled entry — the swap arms put a non-SOP-017 id in
the one slot and would otherwise raise at payload build.
`_attribution_block` emits `infections_during_window` +
`during_window_by_{role,zone_class,route}` +
`confined_passenger_infections_during_window` **unconditionally**
(whole-body-gated `during_quarantine_*` fields unchanged) so the
SOP-011/SOP-007/never-binds arms keep the shape discriminators.
`tools/covid_screen_readout_common.py` gains an optional `paired_rows`
hook for cross-row seed-paired deltas.

## Gate

Canary = cells 0–29 (D0 + SOP017_D4 + SOP009_D12 at θ 2.37e11,
INDEX_OFFSET 0 / ARRAY_SIZE 30). **Stop and report after the canary;
the remaining 420 cells run only on the author's go-ahead.**

Verdict grammar (frozen): `suppression_capable_at_corner` /
`deferral_only` / `suppression_incapable`. Design
`picard_framework/runs/covid_suppress_v1_design.json`; readout
`tools/covid_suppress_v1_readout.py`.
