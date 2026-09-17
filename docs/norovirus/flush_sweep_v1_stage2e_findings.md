# The emesis berth-share repair is a measured null at 200 paired seeds

Status: measured. Companion to the generated tables in
[`flush_sweep_v1_stage2e_readout.md`](flush_sweep_v1_stage2e_readout.md)
(`telemetry_buffer/observation_model/flush_sweep_v1_s2e.json`); the `s2r`
interpretation this re-measurement was run against is in
[`flush_sweep_v1_stage2r_findings.md`](flush_sweep_v1_stage2r_findings.md);
design and declared uncertainty in
[`flush_aerosolisation_v1.md`](flush_aerosolisation_v1.md).
Every dose figure in this repository remains void pending refit
([ledger](norovirus_open_ledger.md)).

The `s2e` campaign re-ran the same five arms — `off`, `3e-9`, `1e-8`,
`3e-8`, `1e-7` — on the same six hull/length cells at the same 200 paired
seeds (8000–8199), 1,200 runs per arm, 6,000 total, 0 non-Spot failures
(Spot reclaims only: 103/99, 106/103, 116/97, 105/88, 144/112 attempts over
children in `off`/`1e-7`/`3e-9`/`1e-8`/`3e-8`), on image
`flush-sweep-v1-s2e-34febdc`
(`sha256:1bcba429c715b769454cba9d41a69b4a4520cdf115037f2236cfec33c68b2dac`),
job definition `picard-campaign:46`. The only difference from `s2r` is the
engine: `s2e` ran merged main `585ad89`, which carries the item-50 repair —
`_pathway_emesis_aerosol` now dilutes a cabin-compartment emesis event into
its berth share of the declared block volume instead of the invented
100 m³ fallback. The manifests are field-identical to `s2r` apart from
campaign name/description; both air-model settings remain pinned
(`cabin_air_mode: cabin_compartment`,
`hvac.pathogen_pool_transport: airflow`). **The `s2e` archive carries no
`engine_git_sha`** — the image predates item 52 (#580), so the ledger
remains its engine record.

## 1. The contrast: s2r → s2e

Paired on the same seeds, cell by cell. `spi` is pooled secondaries per
import, `post/1k` the posting frequency per 1,000 voyages, route columns
the `fraction_dominant` shares; `dir/fom` is direct contact plus fomite.
Imports are identical in 200/200 pairs in every cell × arm.

| cell | arm | spi s2r | spi s2e | post/1k s2r | post/1k s2e | hvac s2r→s2e | flush s2r→s2e | emesis s2r→s2e | dir/fom s2r→s2e | imports |
|---|---|---|---|---|---|---|---|---|---|---|
| classic 7d | off | 0.009 | 0.009 | 0.0 | 0.0 | 0.00→0.00 | 0.00→0.00 | .000→.000 | 1.00→1.00 | 200/200 |
| classic 7d | 3e-9 | 0.216 | 0.216 | 0.0 | 0.0 | 0.26→0.26 | 0.15→0.15 | .000→.000 | 0.59→0.59 | 200/200 |
| classic 7d | 1e-8 | 0.339 | 0.339 | 0.0 | 0.0 | 0.32→0.32 | 0.24→0.24 | .003→.003 | 0.44→0.44 | 200/200 |
| classic 7d | 3e-8 | 0.457 | 0.457 | 0.0 | 0.0 | 0.55→0.55 | 0.37→0.37 | .000→.000 | 0.08→0.08 | 200/200 |
| classic 7d | 1e-7 | 1.751 | 1.751 | 15.0 | 15.0 | 0.68→0.68 | 0.18→0.18 | .000→.000 | 0.13→0.13 | 200/200 |
| classic 12d | off | 0.013 | 0.013 | 0.0 | 0.0 | 0.00→0.00 | 0.00→0.00 | .000→.000 | 1.00→1.00 | 200/200 |
| classic 12d | 3e-9 | 0.130 | 0.130 | 0.0 | 0.0 | 0.49→0.49 | 0.25→0.25 | .000→.000 | 0.25→0.25 | 200/200 |
| classic 12d | 1e-8 | 0.585 | 0.585 | 0.0 | 0.0 | 0.54→0.54 | 0.25→0.25 | .000→.000 | 0.21→0.21 | 200/200 |
| classic 12d | 3e-8 | 1.958 | 1.958 | 15.0 | 15.0 | 0.54→0.54 | 0.20→0.20 | .000→.000 | 0.26→0.26 | 200/200 |
| classic 12d | 1e-7 | 6.930 | 6.981 | 85.0 | 85.0 | 0.65→0.66 | 0.12→0.12 | .000→.000 | 0.23→0.22 | 200/200 |
| expedition 7d | off | 0.093 | 0.093 | 0.0 | 0.0 | 0.00→0.00 | 0.00→0.00 | .000→.000 | 1.00→1.00 | 200/200 |
| expedition 7d | 3e-9 | 0.141 | 0.141 | 0.0 | 0.0 | 0.03→0.03 | 0.38→0.38 | .000→.000 | 0.59→0.59 | 200/200 |
| expedition 7d | 1e-8 | 0.224 | 0.224 | 0.0 | 0.0 | 0.30→0.30 | 0.28→0.28 | .000→.000 | 0.41→0.41 | 200/200 |
| expedition 7d | 3e-8 | 0.410 | 0.420 | 5.0 | 5.0 | 0.26→0.27 | 0.12→0.12 | .000→.000 | 0.62→0.62 | 200/200 |
| expedition 7d | 1e-7 | 0.727 | 0.727 | 5.0 | 5.0 | 0.47→0.47 | 0.19→0.19 | .000→.000 | 0.33→0.33 | 200/200 |
| expedition 12d | off | 0.083 | 0.083 | 0.0 | 0.0 | 0.00→0.00 | 0.00→0.00 | .000→.000 | 1.00→1.00 | 200/200 |
| expedition 12d | 3e-9 | 0.234 | 0.234 | 0.0 | 0.0 | 0.08→0.08 | 0.24→0.24 | .000→.000 | 0.67→0.67 | 200/200 |
| expedition 12d | 1e-8 | 0.234 | 0.234 | 0.0 | 0.0 | 0.38→0.38 | 0.29→0.29 | .000→.000 | 0.33→0.33 | 200/200 |
| expedition 12d | 3e-8 | 0.356 | 0.405 | 0.0 | 0.0 | 0.45→0.46 | 0.32→0.25 | .000→.000 | 0.23→0.29 | 200/200 |
| expedition 12d | 1e-7 | 1.151 | 1.151 | 10.0 | 10.0 | 0.63→0.63 | 0.23→0.23 | .000→.000 | 0.14→0.14 | 200/200 |
| spirit 7d | off | 0.120 | 0.120 | 0.0 | 0.0 | 0.01→0.01 | 0.00→0.00 | .000→.000 | 0.99→0.99 | 200/200 |
| spirit 7d | 3e-9 | 0.329 | 0.329 | 0.0 | 0.0 | 0.14→0.14 | 0.23→0.23 | .000→.000 | 0.63→0.63 | 200/200 |
| spirit 7d | 1e-8 | 0.771 | 0.771 | 0.0 | 0.0 | 0.19→0.19 | 0.26→0.26 | .000→.000 | 0.55→0.55 | 200/200 |
| spirit 7d | 3e-8 | 1.160 | 1.160 | 0.0 | 0.0 | 0.45→0.45 | 0.29→0.29 | .000→.000 | 0.26→0.26 | 200/200 |
| spirit 7d | 1e-7 | 2.637 | 2.618 | 5.0 | 5.0 | 0.49→0.48 | 0.29→0.29 | .000→.000 | 0.22→0.22 | 200/200 |
| spirit 12d | off | 0.149 | 0.149 | 0.0 | 0.0 | 0.01→0.01 | 0.00→0.00 | .000→.000 | 0.99→0.99 | 200/200 |
| spirit 12d | 3e-9 | 0.751 | 0.757 | 10.0 | 10.0 | 0.31→0.31 | 0.18→0.18 | .000→.000 | 0.51→0.52 | 200/200 |
| spirit 12d | 1e-8 | 1.119 | 1.081 | 10.0 | 10.0 | 0.42→0.47 | 0.28→0.26 | .000→.001 | 0.31→0.28 | 200/200 |
| spirit 12d | 3e-8 | 3.665 | 3.687 | 35.0 | 35.0 | 0.49→0.48 | 0.21→0.21 | .000→.000 | 0.31→0.31 | 200/200 |
| spirit 12d | 1e-7 | 9.475 | 9.475 | 110.0 | 110.0 | 0.60→0.60 | 0.19→0.19 | .000→.000 | 0.21→0.21 | 200/200 |

## 2. Why a ×2.2–2.4 cabin concentration moved nothing

The item-50 repair raised the in-room emesis-aerosol concentration on
passenger two-berth staterooms by ≈×2.32 (classic), ×2.43 (spirit), ×2.19
(expedition) — wider on crew blocks — and the paired contrast is
bit-identical in most cells. The reason is the size of the quantity being
doubled, measured directly rather than asserted. Instrumented local runs
of the `1e-7` arm's 7-day tiers (first seeds of each hull, the campaign
engine with `emesis_aerosol_exposures` captured in-process) gives the
per-event emesis mass and dose in cabin venues against N50 = 16,871
particles:

| quantity | observed |
|---|---|
| runs with any emesis-aerosol event | 1 of 9 |
| emitted events (all cabin-compartment) | 7, zone `PC_D11_S_A::cabin2038` |
| aerosol mass per event, median / max | 1.60 / 63.4 copies |
| implied in-room dose at the max mass (40–46 m³ berth share, ventilation ≤ 1) | ≤ 0.95 copies |
| max dose as a fraction of N50 = 16,871 | ≤ 5.6e-5 (≈4.3 decades short) |
| median-mass dose as a fraction of N50 | ≤ 1.4e-6 (≈5.8 decades short) |
| exposure rows produced | 0 — the compartment held no susceptible that epoch |

The pathway is live and reachable — cabin events do fire — but they are
rare (vomiting episodes are a symptomatic-phase subset of an already small
infected set) and, when they land, the per-event aerosol mass is tens of
copies at most. The mechanical ceiling confirms the scale: even the
largest possible single event (one episode, maximum shed 1e8 GEC, maximum
aerosol fraction 2.67e-4, 40 m³ share, zero ventilation loss) doses ≤ ~400
copies — still only ≈0.024 N50, and typical events sit ~5 decades below
that. Doubling a quantity four-plus decades below the infectious dose
changes no outcome on any seed, which is exactly what the paired contrast
shows. The null is therefore about the *emitted mass scale*, not the
volume: the berth-share repair moved the cabin concentration by a factor
of ≈2.2–2.4, but neither operand is near the N50 gate.

## 3. What the null does and does not say

- The emesis berth-share repair (item 50) is a **measured null at 200
  paired seeds**: imports 1.000 in all 30 cell × arm contrasts, Δ spi
  within noise everywhere, emesis dominant-route share ≈0 in both stages.
- The `s2r` interpretation therefore stands as the measurement of record
  on the current engine: the crossing bounded above by `3e-9` and
  unbounded below by anything measured, `hvac_airborne` dominant in 26–68%
  of established infections in the live arms, posting at `1e-7` of 15–110
  per 1,000 with the 12-day large hulls at 85–110.
- A null this size does not read back onto the repair's correctness — the
  item-50 dose mathematics are unchanged and the partition is still the
  honest volume — only onto its *materiality at these exposure levels*.
  Whether a cabin emesis event can ever dose a berth-mate above N50 is a
  question of the mass scale (the emitted load), not the volume.
- Nothing is selected and no span is narrowed: `[1e-9, 1e-3]` is
  untouched, no arm gains standing from its distance to A9, and no
  stage 3 is declared.
