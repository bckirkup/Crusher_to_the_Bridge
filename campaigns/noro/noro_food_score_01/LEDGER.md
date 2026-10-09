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
| wave 1 | landed | exp + cls 12,000/12,000 SUCCEEDED, 0 FAILED — zips under `campaign/noro_food_score_01/fl_{exp,cls}_*/`; see Wave 1 submission |
| wave 2 | landed | spr 6,000/6,000 SUCCEEDED, 0 FAILED — zips under `campaign/noro_food_score_01/fl_spr_*/`; see Wave 2 submission |
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

## Wave 1 submission (2026-10-08, at `3b5b52fb`)

exp+cls fleet wave — 12 blocks × 1,000 seeds = 12,000 voyages on
`picard-campaign-queue` (Spot FIFO). Same image as the canary —
`picard-campaign@sha256:29ea170eaede08d02566910967bfbda879a3656ceb3a40cf3ef45201fc5d9599`
(built at `40862b8c`; no rebuild). Jobdef `picard-noro-food-score-01`
revs :2–:13 — one per block submit, each digest-pinned like rev :1,
retryStrategy ×10 (`Host EC2*`).

exp arrays (seeds 8000–8999): off `3412a5e2` (:2), ind `1e36a0f1` (:3),
ol1 `fa8fa934` (:4), ol2 `1f9f0948` (:5), ol3 `6c241515` (:6), ship
`f0a35d00` (:7). cls arrays (seeds 8105–9104): off `f1b92642` (:8),
ind `aac25cb0` (:9), ol1 `d2e5b001` (:10), ol2 `2e8d746f` (:11),
ol3 `0e6b064c` (:12), ship `a5ee53f8` (:13). Submitted 10:38 UTC via
`scripts/campaign`-equivalent submit (rendered jobdef + literal
`--container-overrides` argv per block; committed `campaign.json`
untouched).

Health ~8 min in: 553 SUCCEEDED / 108 RUNNING+STARTING / 11,339
RUNNABLE / **0 FAILED** — no materialization or app failures; Spot
dispatching ~70 cells/min on the lead (off) array. Zips landing under
`campaign/noro_food_score_01/fl_{exp,cls}_12d_scr_<arm>/`; canary dirs
untouched. Spot-checked `fl_exp_12d_scr_off` s8000: 3-member zip
contract, `common_source.mode="off"` echo, `agent_class_fractions`
stamped, non-degenerate 288-epoch voyage.

Housekeeping: `campaign/noro_food_score_01/manifest.json` was absent at
submit (canary cells read the manifest from the image, so nothing
needed it); uploaded the frozen manifest once for record parity with
AGE-FOOD-01. The canary dedup witness zip already noted under
image build sits under `canary_exp_ship/` — accounted for; fleet
blocks write their own `fl_*` prefixes.

No report-immediately trigger fired. Recovery if Spot reclaims bite:
`Host EC2*` retries self-heal (×10); any seeds still missing post-drain
backfill via filtered `--seeds` resubmit per the AGE-FOOD-01 playbook —
`_already_uploaded` dedup-skips landed cells.

**Wave 1 landed (2026-10-08 ~15:30 UTC):** 12,000/12,000 zips across the
12 `fl_{exp,cls}` prefixes — 0 FAILED, zero Spot reclaims surfaced all
wave (retry×10 may have absorbed any silently). ~4.9 h wall on Spot.

## Wave 2 submission (2026-10-08, at `e74a2fcb`)

spr fleet wave — 6 blocks × 1,000 seeds = 6,000 voyages on
`picard-campaign-queue` (Spot FIFO), approved by user after wave-1
preview. Same image `picard-campaign@sha256:29ea170e…` (still the
design SHA build; spec/manifest unchanged). Jobdef
`picard-noro-food-score-01` revs :14–:19, digest-pinned, retry×10 —
same wrapper submit as wave 1.

spr arrays (seeds 8105–9104): off `0ac9325a` (:14), ind `77310507`
(:15), ol1 `fe259f44` (:16), ol2 `98c4c1ff` (:17), ol3 `78c7006e`
(:18), ship `7426dd03` (:19). Submitted 16:32 UTC.

Health ~5 min in: 120 RUNNING / 5,880 RUNNABLE / 0 FAILED — dispatching
clean, FIFO in submit order. Zips landing under
`campaign/noro_food_score_01/fl_spr_*/`. spr cells run ~4× classic cost
(AGE-FOOD-01 calibration ~12 min/cell at ~118 concurrent) → ETA ~8–9 h
if the Spot capacity holds; drought playbook (resubmit to
`picard-analysis-queue`, `_already_uploaded` dedup covers) applies if
arrays park >1 h.

**Health ~85 min in (18:00 UTC):** 1,008 SUCCEEDED / 119 RUNNING /
4,873 RUNNABLE / **0 FAILED** — no materialization or app failures,
dispatching ~12 cells/min. Per array: off 1000/1000 SUCCEEDED (parent
SUCCEEDED, ~85 min wall); ind 8/127/873; ol1/ol2/ol3/ship all-RUNNABLE
behind ind (FIFO). Spot is holding — no drought trigger; arrays are
dispatching, not parked. Manifest key verified present
(`campaign/noro_food_score_01/manifest.json`, 237,087 B, uploaded
10:38 UTC — record only; cells read the manifest in-image).

Spot-checks on landed zips (both seeds s8105): off — 3-member contract
(`summary.json`, `growth_census.json.gz`, `rss_samples.json`), echo
`common_source={mode:"off"}`, `agent_class_fractions` stamped,
non-degenerate 288-epoch voyage (215 acquired / 64 imports, peak
prevalence 232 ep 282, `common_source_events=0` as armed); ind — same
contract, echo `{lot_mode,handler_mode,diner_mode:"independent"}`,
243 acquired, peak 258, `common_source_events=62` / `takers=1217`
(independent-mode firing, v1-style rows per canary shape). Ship-arm
object-witness fields (`object_id`/`pan_serial`/close fields) can't be
re-checked until ship zips land — ship is last in FIFO order; canary
on the same digest already verified them (84 objects, all close fields).
Deferred to readout stage, which inspects ship cells anyway.

No report-immediately trigger fired.

**Ship-arm witness check (2026-10-09, landed s8105):** echo verbatim
`{lot,handler,diner:"object", lot_object_probability:[0.001,0.02]}`;
`common_source.events` 153/153 rows carry `object_id` + `pan_serial`;
`common_source.objects` 66/66 rows carry close fields (`end_reason`:
source_excluded/exhausted, seeded/exhausted epochs, windows, pans,
dose_credited). Telemetry 147 ill_handler + 6 ill_diner events, 0
provisioned_lot (ungated), 66 objects, 153 pans / 153 windows, 1,237
takers — same shape as canary. Non-degenerate 288-epoch voyage (230
infected, peak 232, outbreak). Deferred gate now verified on fleet
cells.

**Wave 2 landed (2026-10-09 ~01:20 UTC):** ship parent SUCCEEDED —
6,000/6,000 SUCCEEDED across the 6 `fl_spr` prefixes, **0 FAILED** all
wave (retry×10 never surfaced a reclaim), ~8.9 h wall on Spot at a
steady ~12 cells/min. All 18,000 scored cells (exp + cls + spr) now
landed; no resubmit needed anywhere.

## Grid

3 hulls × 6 arms × 1,000 seeds = 18,000 voyages, tier
`fl_<hull>_12d_scr_<arm>`, arms `off | ind | ol1 | ol2 | ol3 | ship`
(`lot_object_probability` ladder; shipped interval = `ship`
[0.001,0.02]). Fixed coordinates identical to FOOD-01/02 and
AGE-FOOD-01; seeds exp 8000–8999, cls/spr 8105–9104.

## Findings

_None — no cell has run at fleet scale._
