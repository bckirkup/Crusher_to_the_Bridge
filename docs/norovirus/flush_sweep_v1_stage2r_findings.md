# The repaired transport engine moves the flush crossing below the bracket that was built to contain it

Status: measured. Companion to the generated tables in
[`flush_sweep_v1_stage2r_readout.md`](flush_sweep_v1_stage2r_readout.md)
(`telemetry_buffer/observation_model/flush_sweep_v1_s2r.json`); design and
declared uncertainty in [`flush_aerosolisation_v1.md`](flush_aerosolisation_v1.md);
the pre-repair measurement of the same five arms in
[`flush_sweep_v1_stage2_findings.md`](flush_sweep_v1_stage2_findings.md).
Every dose figure in this repository remains void pending refit
([ledger](norovirus_open_ledger.md)).

The `s2r` campaign re-ran stage 2 exactly as declared — `off`, `3e-9`, `1e-8`,
`3e-8`, `1e-7` on the same six hull/length cells at the same 200 paired seeds
(8000–8199), 1,200 runs per arm, 6,000 total, 0 non-Spot failures — on an
engine carrying two repairs the original stage 2 predates: per-pathogen
airborne pool transport (ledger item 47, PR #561), without which the
norovirus drift route was inert in every arm, and the cabin-venue event drain
(item 48, PR #563), without which a stateroom flush's aerosol mass was
dropped instead of credited to the corridor block that shares its HVAC
branch. Both air-model settings are pinned in the manifests
(`cabin_air_mode: cabin_compartment`, `hvac.pathogen_pool_transport: airflow`)
rather than inherited, so this archive records the engine it measured.
Imports are identical in 1.000 of pairs in all 24 contrasts.

## 1. The bracket no longer contains the crossing

Stage 2's arms were placed to bracket the first resolvable decade. Under the
repaired engine, five of the six cells are already resolved at the bracket's
floor:

| cell | first arm whose paired Δ secondaries excludes zero | | |
|---|---|---|---|
| | pre-repair (s2) | repaired (s2r) | Δ secondaries at `3e-9`, s2r |
| classic 7 d | `3e-9` | `3e-9` | +0.94 [+0.20, +2.01] |
| classic 12 d | `3e-9` | `3e-9` | +0.53 [+0.20, +0.98] |
| spirit 7 d | `1e-8` | **`3e-9`** | +1.38 [+0.54, +2.51] |
| spirit 12 d | `3e-8` | **`3e-9`** | +3.96 [+1.57, +6.98] |
| expedition 7 d | `1e-8` | `1e-8` | +0.05 [−0.01, +0.13] |
| expedition 12 d | `3e-8` | **`3e-9`** | +0.15 [+0.03, +0.37] |

So the measurement's own answer is that **the crossing has moved to or below
`3e-9` in five cells, and the bracket's lower edge is no longer a bound.**
The honest reading is not "the crossing is (1e-9, 3e-9]" — that interval rests
on stage 1's `1e-9` null, which was measured on the pre-repair engine and is
itself withdrawn. Under the repaired engine the crossing is bounded above by
`3e-9` and unbounded below by anything currently measured. Locating it
requires arms at and below `1e-9`; none is declared here.

## 2. What the repairs did, mechanically

The multiplier on secondaries per import at `1e-7` rose from ×52 to ×197
(classic 7 d), ×97 to ×520 (classic 12 d), ×7.6 to ×22 (spirit 7 d), ×10.4 to
×63 (spirit 12 d), ×4.4 to ×7.8 and ×4.9 to ×13.9 (expedition 7 d / 12 d). The
route attribution says where the increase went: `hvac_airborne` is now the
dominant route in **26–68% of established infections** across the live arms,
against effectively zero pre-repair, while `flush_aerosol` itself holds
12–38%. The flush route's in-room dose per exposure is unchanged — the added
infections are the same emitted mass now reaching susceptibles *elsewhere on
the branch*, which is exactly what item 48 credited and item 47 transported.

The amplification is partly a feedback, not only a dose increase: flush events
per voyage themselves rise with the arm (classic 12 d 14.3 → 42.7 at `1e-7`;
spirit 12 d 33.5 → 72.8), because every newly infected host defecates and
flushes too. This is the same trajectory-level compounding that falsified the
stage-1 saturation argument, now operating through a live drift path.

The `off` baseline also moved (secondaries/import: classic 12 d 0.009 → 0.013,
expedition 12 d 0.137 → 0.083, spirit 7 d 0.161 → 0.120) because the emesis
path shares the repaired drain and transport. The contrasts are therefore
re-based, not merely re-scaled, and no s2 number may be quoted against an s2r
number as if only the flush term had changed.

## 3. Posting now overshoots at the top of the bracket

Posting frequency per 1,000 voyages at `1e-7`, up from 0 in the `off` arm of
every cell: classic 15.0 and **85.0** (7 d / 12 d), spirit 5.0 and **110.0**,
expedition 5.0 and 10.0 — McNemar exact p = 1.5e-5 (classic 12 d) and 4.8e-7
(spirit 12 d), with 0 discordant pairs in the losing direction. Against A9's
observed 0.33 per 1,000, the top of the bracket now overshoots the comparator
by two orders of magnitude, where before the repairs every 7-day cell posted
zero.

That is the first time the swept span has produced observed-scale posting from
both directions — under-powered at its floor, over-powered near `1e-7` — which
means the comparator lies inside the declared span rather than outside it.
**No value is selected on that basis.** The span `[1e-9, 1e-3]` is not
narrowed, `f_aero` is not chosen, and the fact that some arm reproduces A9 is
recorded as a property of the span, not as evidence for that arm: the
vacuum-versus-gravity gap and the Johnson/Boles disagreement are unchanged by
this campaign, and the posting comparator itself may reflect VSP reporting and
investigation selection rather than population truth.

## 4. Carried forward

- Stage 1 (`1e-9`, `1e-7`, `1e-5` at 100 seeds) and stage 2 are both
  pre-repair archives; their arm placements stand as history and their nulls
  may not be used as bounds on the repaired engine.
- Pairing holds on the boarding cohort and not past the first flush exposure
  (item 46(a)); means are unbiased, pair-level exactness is not available.
- The emesis path still dilutes into the invented 100 m³ compartment fallback
  (item 45), which now matters more than it did, because emesis mass reaches
  the branch.
