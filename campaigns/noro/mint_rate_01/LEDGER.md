# NORO-MINT-RATE-01 — campaign ledger

Design of record:
`docs/norovirus/noro_mint_rate_01_sweep_design.md` (frozen before any
cell ran). Question: channel presence — the provisioned_lot voyage
gate `lot_object_probability` — is the measured operative margin on
the object grammar. Where along the gate does the D1 posting marginal
land in the 0.4–0.9 pp band per hull, and does the D2/D3/D4 signature
(`ind`-level posted pax-AR, excursion→posting conversion, posted
burst48) survive at that rate?

## Stage table

| stage | state | evidence |
|-------|-------|----------|
| design frozen | done | `docs/norovirus/noro_mint_rate_01_sweep_design.md`; this package (27 tiers, 33 blocks) |
| image built | pending | tag `noro-mint-rate01`; eval SHA + digest + jobdef revision recorded here at submit — never a bare tag |
| local smoke | pending | `fl_exp_12d_scr_p012` index 0: zip contract + scalar override echo (`"lot_object_probability": 0.012`) + object-mode echo |
| canary (116 cells, exp) | pending | `canary_exp_{mint 48, p024 24, p005 24, ind 8, ship 8, off 4}` — hard gates in design §7 |
| wave 1 — exp, all 9 arms | pending | 9,000 cells; `fl_exp_12d_scr_mint` first as the probe array |
| wave 2 — cls + spr, all 9 arms | pending | 18,000 cells |

## Grid

3 hulls (exp 8000–8999, cls/spr 8105–9104, 1,000 seeds/cell; mega
excluded — objects never armed there) × 9 arms = 27,000 voyages,
fixed coordinates identical to FOOD-01/02, AGE-FOOD-01, SCORE-01,
ENTRAIN-01 and FOOD-SHAPES-01 (rung `shipped`, bp32.5c18.5, nsf29,
288 epochs, comp65, dose 7.57, embarkation 2026-01-10, shipped class
mix stamped).

| arm | `lot_object_probability` | role |
|-----|--------------------------|------|
| `off` | `mode: off` | mechanism-absence floor; bit-identical to prior `off` |
| `ind` | — (v1 `lot_event_probability` U(0.02,0.15)) | the per-hull signature denominator |
| `ship` | U(0.001, 0.02) — shipped | bracket bottom anchor; SHAPES-01 `ship` bridge |
| `p005` | 0.005 | rung — E[minted] 5/1,000 |
| `p008` | 0.008 | rung — 8/1,000 |
| `p012` | 0.012 | rung — 12/1,000 |
| `p017` | 0.017 | rung — 17/1,000 |
| `p024` | 0.024 | rung — 24/1,000 |
| `mint` | U(0.02, 0.15) — powered | bracket top anchor; signature carrier; SHAPES-01 `mint` bridge |

Per-rung E[objects] and per-hull margin expectations: design §3.2/§3.3.
Scalar rungs gate on the same stream position per seed — minted sets
must nest p005 ⊆ p008 ⊆ p012 ⊆ p017 ⊆ p024 (integrity gate, design
§5.4-3).

## Mechanism contracts

None required — every arm is a shipped `common_source` config
override (verified against `engines/transmission_core.py` @
`9039e234`; `_cs_plan_objects` ≈:12538, `_cs_draw_voyage_rates`
≈:3491, `lot_posture_coupling` default `false`). Rung values are
declared arm configuration, not provenance-registered constants.
Pruned (design §3.5): `bg`/`ind_bg`/`bg_mint` titre margin,
`redraw`/`fx` cadence-extent arms, `extra_lot` ladder, handler/diner
mint, `ind`-gate mint, mega.

## Canary readout

(Not yet submitted.)

## Wave submissions

(Not yet submitted.)

## Findings

(Not yet read out.)
