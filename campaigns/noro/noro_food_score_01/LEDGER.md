# NORO-FOOD-SCORE-01 ledger

Scores the shipped FOOD-COMMON-SOURCE-02 contamination objects
against the spec's frozen measurement plan. Design:
`docs/norovirus/noro_food_score_01_sweep_design.md`; entry:
`docs/ledger/NORO-FOOD-SCORE-01.md`.

## Status

| stage | state | notes |
|-------|-------|-------|
| design freeze | done | grid + scored criteria + must-not-move frozen before any cell ran |
| build/gen | done | `design/build.py` → manifest (18 tiers) + `campaign.json` (21 blocks); regen deterministic (sha256-stable on re-run) |
| local smoke | done | `fl_exp_12d_scr_ship` index 0: voyage clean, 3-member zip, ship-rung echo, 1 ill_handler object (4 pans / 4 windows) |
| image build | done | `picard-campaign:noro-food-score01` built at merged design SHA `40862b8c` (root `Dockerfile` + literal `Dockerfile.campaign` overlay), digest `sha256:29ea170eaede08d02566910967bfbda879a3656ceb3a40cf3ef45201fc5d9599`; verified in-container (deploy/aws + tools + campaigns trees, `ENGINE_GIT_SHA` = `40862b8c…`, one real cell ran a full voyage in-image and self-uploaded under the canary prefix — the ship array's index-0 dedup-skipped it) |
| canary | done | 44/44 SUCCEEDED on `picard-campaign-queue` (Spot); all frozen gates green — see Canary readout |
| wave 1 | gated | exp + cls tiers (12,000 voyages) — user decides |
| wave 2 | gated | spr tiers (6,000 voyages) — user decides |
| readout | pending | `outbreak_anchor_readout.py` + `common_source_readout.py` + `onset_curve_readout.py` per the design |

## Canary readout (2026-10-08, all at `40862b8c`)

Jobdef `picard-noro-food-score-01:1` (digest-pinned, retryStrategy ×10
Host EC2*). Arrays: `canary_exp_ship` `dc32ca44-deaa-481d-883f-2d4ae19d1170`
(24), `canary_exp_ind` `ff4c703c-bc9d-462e-95d4-a3bca242d816` (12),
`canary_exp_off` `a36bf39a-3317-496e-ba05-45afbac5d523` (8). 44/44
SUCCEEDED (~5 min on Spot once dispatched; index-0 ship child
dedup-skipped the pre-landed witness zip). Zips under
`campaign/noro_food_score_01/{canary_exp_ship,canary_exp_ind,canary_exp_off}/`.

Frozen gates — all green:

- **Override echo** — `parameters.common_source` verbatim per arm,
  44/44: ship `{lot_mode,handler_mode,diner_mode: "object",
  lot_object_probability: [0.001,0.02]}`; ind all `"independent"`;
  off `{mode: "off"}`. `agent_class_fractions` stamped on every cell.
- **Zip contract** — 44/44 zips are exactly `summary.json`,
  `growth_census.json.gz`, `rss_samples.json`.
- **Object firing (ship)** — 84 objects across 24 cells (73
  `ill_handler`, 11 `ill_diner`, 0 `provisioned_lot` — the lot arm is
  not gated at E ≈ 1.05%, P(0 in 24) ≈ 78%; 127/127 event rows carry
  `object_id` + `pan_serial`; 84/84 object rows carry close fields
  (`end_reason`: source_excluded 73 / voyage_end 6 / shedding_ended 5);
  dose_credited 27.8 total.
- **ind arm** — 23 v1-style events (`object_id`/`pan_serial` null),
  zero `objects` rows.
- **off arm** — zero events, zero objects, zero dose_credited.
- **Non-degenerate** — n_acquired 1–33 (ship) / 1–28 (ind, off);
  peak_prevalence on every cell; 1 posted voyage on ship
  (vsp_trigger_epoch + outbreak_occurred set), 0 on ind/off — sane at
  n=24/12/8.

No report-immediately trigger fired. Per the frozen stop order: canary
is down and clean — the user decides whether the fleet waves go.

## Grid

3 hulls × 6 arms × 1,000 seeds = 18,000 voyages, tier
`fl_<hull>_12d_scr_<arm>`, arms `off | ind | ol1 | ol2 | ol3 | ship`
(`lot_object_probability` ladder; shipped interval = `ship`
[0.001,0.02]). Fixed coordinates identical to FOOD-01/02 and
AGE-FOOD-01; seeds exp 8000–8999, cls/spr 8105–9104.

## Findings

_None — no cell has run at fleet scale._
