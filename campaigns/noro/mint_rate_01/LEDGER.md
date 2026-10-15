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
| image built | done | `picard-campaign:noro-mint-rate01` @ `49e1993b` → digest `sha256:05cba8f22b747ca47c13a1e885581263e51b5320ab931250767a33b82bac38ea`; jobdef `picard-noro-mint-rate-01:1` (digest-pinned, ACTIVE, retry ×10 `Host EC2*`); manifest mirrored to `s3://crusherbucket-994254241749-us-east-1-an/campaign/noro_mint_rate_01/manifest.json` |
| local smoke | done | `fl_exp_12d_scr_p012` index 0: 3-member zip contract + scalar echo `"lot_object_probability": 0.012` + object modes; 31 infected, 0 cs objects at E≈0.012 — passed |
| canary (116 cells, exp) | done — 5/6 gates green; `off` bit-identity FAILED (see Findings: host-level nondeterminism) | arrays `42a34b4d` mint 48, `08a78c9c` p024 24, `745b3af6` p005 24, `6304cc2f` ind 8, `30229fac` ship 8, `4a7bff20` off 4 — 116/116 SUCCEEDED, 0 retries |
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

Submitted 2026-10-15 on `picard-noro-mint-rate-01:1`, image digest
`sha256:05cba8f22b…` @ `49e1993b` (merge of #999). 116/116 cells
SUCCEEDED first attempt. `parameters.common_source` echo verified
verbatim in every cell.

| block | cells | gate | result |
|-------|------:|------|--------|
| `canary_exp_mint` | 48 | ≥1 `provisioned_lot`; echo `[0.02,0.15]`; titres in (1.5e2,5e3); single titre/object | PASS — 4 objects (E≈4.1), titres 272.7/605.0/3213.3/4635.8 GEC/g all in band, 84 minted events, single titre each, interval echo verbatim |
| `canary_exp_p024` | 24 | scalar echo `0.024` verbatim; zero-lot declared non-failing | PASS — echo verbatim, 0 objects (P(0)≈0.50) |
| `canary_exp_p005` | 24 | scalar echo `0.005` verbatim; zero-lot declared non-failing | PASS — echo verbatim, 0 objects (P(0)≈0.87) |
| `canary_exp_ind` | 8 | independent-modes echo; `object_id: null` rows; no object mint | PASS — echo verbatim, 9 events all `object_id: null`, 0 objects minted |
| `canary_exp_ship` | 8 | shipped echo + `titre_draw_mode` → `two_mode`; handler/diner objects | PASS — echo `[0.001,0.02]` + object modes, `titre_draw_mode` absent→default, 20 handler + 4 diner objects |
| `canary_exp_off` | 4 | zero-witness + bit-identical to prior `off` | HALF — zero-witness PASS (0 objects, 0 events, dose 0.0); **bit-identity FAIL — see Findings** |

## Wave submissions

(Not yet submitted.)

## Findings

### F0 (2026-10-15, canary) — bit-identity across runs is host-level,
not image-level

§9 report-immediately trigger. `canary_exp_off` s8000–8003 diverge
wholesale from SHAPES-01 `fl_exp_12d_scr_off` (same seeds): ~9k field
diffs per cell (e.g. s8000 infected 31 vs 38). Controlled
measurements on the same cell (off, s8000):

- SHAPES-01 canary (`45b2bf18`, Oct-12 Batch) vs SHAPES-01 wave
  (same image, Oct-12 Batch): near-identical — last-ulp dust in
  `removal_totals` + RSS/timing fields only.
- This repo's `.venv` (2× local runs): near-identical to each other
  and to the new `49e1993b` Batch canary (trajectory-equal).
- **`noro-food-shapes01` image run on this VM**: trajectory-equal to
  the `49e1993b` Batch cells (1 ulp-diff), **not** to its own Oct-12
  wave cells (~9k diffs).
- Code per-file sha256 inside both images: identical except the new
  manifest. Python 3.11.17 both; glibc 2.41-12+deb13u4 both; deps
  hash-locked via `uv sync --locked`.

Conclusion: same image on different hosts gives different
trajectories — the voyage is host-sensitive (CPU-dependent float
dispatch is the prime suspect; `PYTHONHASHSEED` is unset but
same-host reruns are stable, so hash-order does not feed draws).
Bit-identity bridge clauses (`off`/ship/mint/ind vs SHAPES-01 cells,
design §3.4) are **unmeasurable in this environment** — the same
image diverges by host. In-campaign statistical bridges remain valid:
D1 is defined vs in-campaign `off`, and every arm's cells in a wave
share the same fleet-day float path as that wave's `off`.

Implication for readout: cross-campaign pairing must be statistical
(distributional), not bitwise. A fix for true bit-identity would need
CPU-independent float behaviour or a pinned instance type — an
engineering change, not config; report to user before any wave.
