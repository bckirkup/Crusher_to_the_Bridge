# NORO-ENTRAIN-01 ledger

Design-of-record: `docs/norovirus/noro_entrain_01_sweep_design.md`
(frozen). Ledger entry: `docs/ledger/NORO-ENTRAIN-01.md`.

| Stage | State | Notes |
|---|---|---|
| design | frozen | two levers + design-note-only full entrainment |
| campaign package | built | `design/build.py` → manifest (27 tiers) + campaign.json (31 blocks) |
| local smoke | pending | `fl_exp_12d_scr_bc80` index 0 — prevalence echo, class-mix stamp, 3-member zip |
| image | pending | tag `noro-entrain01`, pinned at merge SHA |
| canary | pending | `canary_exp_bc80` (24) + `canary_exp_a_ext` (12) + `canary_exp_ship` (8) + `canary_exp_off` (4), then STOP |
| waves | pending | exp all arms → cls/spr ship/bc80/a_ext → remainder; user gates each |

## Grid

3 hulls (exp/cls/spr; mega excluded — objects never armed there, v1
saturates short of its wire) × 9 arms × 1,000 seeds = 27,000 voyages.

| Arm | Lever | Delta vs `ship` |
|---|---|---|
| off | baseline | mechanism absent, bit-identical |
| ind | baseline | all arms `"independent"` (v1 on current engine) |
| ship | baseline | scored shipped object config |
| a_ext | A (shape) | `lot_shelf_life_days` (4, 7) |
| a_thin | A (shape) | `item_take_share` (0.04, 0.20) |
| bc40 | B (entrain) | crew boarding prevalence 0.040 |
| bc80 | B (entrain) | crew boarding prevalence 0.080 |
| bi50 | B (entrain) | `crew_immune_fraction` 0.5 |
| bmix | B (entrain) | crew prevalence 0.080 + immunity 0.5 |

Fixed coordinates: rung `shipped`, bp32.5 (passenger pinned on all
arms), nsf29, 288 epochs, comp65, dose 7.57, embarkation 2026-01-10;
seed lists identical to SCORE-01 (exp 8000–8999, cls/spr 8105–9104).

## Mechanism contracts (spec'd in design, no engine work this stage)

- `cs_extent` (design §4.3): `lot_extent_mode` declared / `lot_state_redraw`
  per-window → arms `fx_wide`, `fx_narrow`, `redraw` append on the
  same seed lists when implemented.
- `arriving_shedder` (design §5.4): crew-fraction mid-shedding
  embarkation draw, class-weighted → arms `as40`, `as80`, `as80g`
  append when implemented; canary `canary_exp_as80` (24) gates the
  echo + composition row + `source_boarding_state` attribution.

## Canary readout

(to be filled at canary close — witnesses per design §8)

## Wave submissions

(to be filled per wave — job ids, s3 prefixes, seed gates)

## Findings

(to be filled at readout — `docs/norovirus/noro_entrain_01_readout.md`)
