# COVID-EXPOCAP-01
**Date:** 2026-09-28
**Commit:** 27efdbd4
**Pathogens:** sars_cov2_resp
**Status:** measured
**Measured at:** 429fe0f9

EXPO-CAP-01 bounded re-rank of the COVID-TAKEOFF-ATTR-01 (`bcf2ac95`)
exposure-set metrics — per-epoch dosed-set size and
`challenged_share_of_aboard` — with the per-shedder per-epoch contact
budget ON (`transmission.exposure_cap.enabled`, default-on for catalogued
cruise platforms). Same instrument
(`tools/covid_takeoff_attribution.py`), same Θ = 2.37e11 (admissible-band
midpoint, unchanged — Θ moves are a non-goal), same cell family as the
rhythm re-rank: 10 cells, seeds 20200205–20200214, 768 epochs,
diamond_princess_2020 (mega_cruise_5000). Baseline column: the
rhythm-on RERANK record (`264fa5cb`) — `engines/` between 264fa5cb and
429fe0f9 is exactly the EXPO-CAP-01 diff, and the flag-off arm is
byte-identical to the pre-change tree (per-epoch agent-state digests
match on the spec-json replay, seeds 20200205/20200206:
`8bc0362e…`, `8033309d…`). Two local jobs (5 cells each); raw cell JSONs
at `telemetry_buffer/expo_cap_gate/attr01/`.

## Mechanism under test

Per (epoch, pathogen, shedder) budget K ~ Poisson(activity rate —
CONTACT-ARCH-01 saturation-adjusted per-unit rate, else POLYMOD
13.4/day — times `voyage_contact_multiplier`). Each shedder samples
min(K_remaining, n_susceptibles) distinct susceptibles per epoch; the
union cohort is the only set that can form droplet zone-pool or HVAC
airborne dose. Partner-bounded routes (cabin-mate addback, near-field
plume, dining partner, direct contact) are unchanged by construction.
Budget magnitude sourced, not fitted: Pung et al. 2022 (cruise wearables,
pax ~20 / crew ~10 close contacts/day) and POLYMOD 13.4/day; venue
capacity rejected by Shirreff et al. 2024 (contacts do not scale with
occupancy). Spec: `docs/exposure_cap_spec.md`.

## Headline moves vs RERANK baseline

| seed | onsets (RERANK) | onsets (cap) | infections (cap) | dosed med (RERANK) | dosed med (cap) | challenged (cap) |
|---|---|---|---|---|---|---|
| 20200205 | 1,520 | 1,964 | 3,569 | 657 | 219 | 1.000 |
| 20200206 | 3,497 | 3,549 | 3,571 | 644 | 246 | 1.000 |
| 20200207 | 3,567 | **0** | 0 | 558 | 1 | 0.008 |
| 20200208 | 1,911 | 2,210 | 3,587 | 730 | 241 | 1.000 |
| 20200209 | 3,091 | 3,351 | 3,405 | 811 | 238 | 1.000 |
| 20200210 | 3,542 | **0** | 1 | 618 | 1 | 0.090 |
| 20200211 | 3,340 | **0** | 0 | 607 | 1 | 0.010 |
| 20200212 | 3,528 | 3,422 | 3,452 | 659 | 249 | 1.000 |
| 20200213 | 3,466 | 3,522 | 3,582 | 690 | 250 | 1.000 |
| 20200214 | 3,433 | 3,525 | 3,546 | 604 | 199 | 1.000 |

- **Ignition now fails on 3/10 seeds** (207, 210, 211: 0 recorded onsets,
  ≤1 infection each — the import). Baseline was 10/10.
- **Ignited per-epoch dosed-set median: 650.5 → 241** (per-seed range
  199–250, ~2.7× down). On extinct cells the set collapses to ~1/epoch —
  the index's cohort draw alone.
- **Channel footprints split exactly as designed.** Median-of-medians:
  hvac ~460 → ~20, zone_pool ~20 → ~12 (the two pooled, cohort-bounded
  routes collapse); cabin_mate_ring ~135 → ~145, contact ~60 → ~60,
  near_field_plume ~7.5 → ~12, dining_ring ~8.5 → ~14 (partner-bounded
  routes unchanged or slightly up with burn scale). The residual
  ~240/epoch is dominated by the cabin-mate ring plus contact partners —
  the uncapped residue the spec predicted.
- **`challenged_share_of_aboard` now discriminates ignition:** 1.0 on
  the seven burns (a saturated union once compounding starts) vs
  0.008–0.090 on the three extinctions. Under the unbounded regime it
  was 1.0 unconditionally because ~600/epoch saturated the union within
  days; it could never move. Now it reports whether a voyage ignited.
- **Burn size on ignited cells is comparable to baseline** (onsets
  median ~3,422 vs 3,449.5) — once past the early bottleneck,
  Σ_shedders K_s scales with prevalence and the burn runs to the
  susceptible wall. Two RERANK-low seeds (205, 208) burn bigger; stream
  reorder, not systematic suppression.
- Onset route mix shifts off the corridor pool: zone_pool share of
  onsets 53% → 25–37% median, with dining (~24–33%) and plume (~24%)
  carrying relatively more — partner channels are unbound.
- Infecting λ medians 1.1–2.5 (RERANK 0.49–1.75): the lottery signature
  persists on the smaller challenged set.
- `droplet_unattributed_onsets` = 0 across all 10 cells.

## Verdict

The challenge-count deficit ATTR-01 named is **closed by the mechanism
class it prescribed**: a sourced per-host contact budget bounds dosed-set
formation to contact scale per shedder per epoch. Two consequences,
measured not tuned:

1. The pooled droplet/HVAC footprint that carried the ~650/epoch
   residual is bounded at ~20–30/epoch; the residual dosed set is
   partner-route mass (cabin ring + contacts).
2. At Θ = 2.37e11 — admitted under unbounded reach — the bounded model
   fails to ignite on 3/10 seeds and once ignited burns at baseline
   size. The cap suppresses ignition probability (a ~0.56-mean cohort
   draw per shedder-epoch makes the index case's challenge lottery
   thin), not burn size. Whether the admissible Θ band survives under
   the capped reach regime is a separate bounded job — Θ moves are a
   declared non-goal of this entry.

The ~50–100 hosts/epoch bound implied by the 197 record was context, not
a target; measured reach now runs below it at low shedder counts
(~1–8/epoch, extinction regime) and above it at high prevalence
(~240/epoch, burn regime) — per-shedder reach never exceeds the contact
record, which is what the bound constrains.

## Caveats

- No Θ or dose-ledger change (non-goal): cap-on cells run the same
  admissible-band midpoint under bounded reach, so ignition-frequency
  moves confound bounded reach with a Θ admitted under unbounded reach.
- Budgets key per pathogen per shedder; a shedder carrying two pathogens
  spends an independent budget per pathogen (declared simplification).
- `reach_per_shedder_epoch.zone_pool` still reads ~300+ — it counts
  susceptible occupancy of units containing an emitter (potential
  reach), not dosed targets; the bound is visible in
  `dosed_targets_by_epoch` and `footprint_targets_by_epoch`.
- Cap-on RNG draws run on a spawned stream (`seed_seq.spawn(1)`);
  flag-off consumes zero extra draws and is byte-identical.
