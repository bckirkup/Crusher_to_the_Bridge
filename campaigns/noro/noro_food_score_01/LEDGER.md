# NORO-FOOD-SCORE-01 ledger

Scores the shipped FOOD-COMMON-SOURCE-02 contamination objects
against the spec's frozen measurement plan. Design:
`docs/norovirus/noro_food_score_01_sweep_design.md`; entry:
`docs/ledger/NORO-FOOD-SCORE-01.md`.

## Status

| stage | state | notes |
|-------|-------|-------|
| design freeze | done | grid + scored criteria + must-not-move frozen before any cell ran |
| build/gen | done | `design/build.py` → manifest (18 tiers) + `campaign.json` (21 blocks) |
| local smoke | done | `fl_exp_12d_scr_ship` index 0: voyage clean, 3-member zip, ship-rung echo, 1 ill_handler object (4 pans / 4 windows) |
| image build | gated | `picard-campaign:noro-food-score01` at merged SHA — user gates |
| canary | gated | `canary_exp_ship` 24 / `canary_exp_ind` 12 / `canary_exp_off` 8, then STOP |
| wave 1 | gated | exp + cls tiers (12,000 voyages) |
| wave 2 | gated | spr tiers (6,000 voyages) |
| readout | pending | `outbreak_anchor_readout.py` + `common_source_readout.py` + `onset_curve_readout.py` per the design |

## Grid

3 hulls × 6 arms × 1,000 seeds = 18,000 voyages, tier
`fl_<hull>_12d_scr_<arm>`, arms `off | ind | ol1 | ol2 | ol3 | ship`
(`lot_object_probability` ladder; shipped interval = `ship`
[0.001,0.02]). Fixed coordinates identical to FOOD-01/02 and
AGE-FOOD-01; seeds exp 8000–8999, cls/spr 8105–9104.

## Findings

_None — no cell has run at fleet scale._
