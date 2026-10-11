# NORO-ENTRAIN-01 ledger

Design-of-record: `docs/norovirus/noro_entrain_01_sweep_design.md`
(frozen). Ledger entry: `docs/ledger/NORO-ENTRAIN-01.md`.

| Stage | State | Notes |
|---|---|---|
| design | frozen | two levers + design-note-only full entrainment |
| campaign package | built | `design/build.py` → manifest (27 tiers) + campaign.json (31 blocks) |
| local smoke | done | `fl_exp_12d_scr_bc80` index 0 (seed 8000): crew prevalence echo 0.08, `agent_class_fractions` stamp, 3-member zip, `drawn_by_role`/`composition` present under `summary.json.initiation.manifest.boarding` |
| image | done | `picard-campaign:noro-entrain01` built at merge SHA `dbbd5395` (root Dockerfile + literal `Dockerfile.campaign` overlay), digest `sha256:c57df157ec9d97f75bf7b465482dc035302308aec589fb778017f6345db8b896`; verified in-container (deploy/aws + tools + campaigns trees, `ENGINE_GIT_SHA` = `dbbd5395…`, 27-tier manifest, one real cell ran a full voyage in-image bit-identical to local smoke) |
| canary | done | 48/48 SUCCEEDED on `picard-campaign-queue` (Spot); all frozen gates green — see Canary readout |
| waves | submitted | all 27 fleet blocks (27,000 cells) submitted in frozen order on user go 2026-10-10; see Wave submissions |

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

(2026-10-10, all at `dbbd5395`)

Jobdef `picard-noro-entrain-01:1` (digest-pinned
`picard-campaign@sha256:c57df157…8b896`, retryStrategy ×10 `Host EC2*`).
Arrays on `picard-campaign-queue` (Spot): `canary_exp_bc80`
`d61395e4-667c-43ce-9752-c0db5e49f253` (24), `canary_exp_a_ext`
`f91a380d-0782-4976-b916-2840cf3ba31e` (12), `canary_exp_ship`
`24de221a-d8be-4a52-bbe5-23fcb5c2080c` (8), `canary_exp_off`
`bd3effaf-acba-4b31-8e90-5e904487ed7b` (4). 48/48 SUCCEEDED, 0 FAILED;
submitted 16:49 UTC, all zips landed 16:52:59–16:53:23 (~4 min wall
once Spot dispatched, ≈12 cells/min — the wave-planning drain anchor
for exp cells; spr cells run ~6× slower per SCORE-01 conventions).
Zips under `campaign/noro_entrain_01/{canary_exp_bc80,canary_exp_a_ext,canary_exp_ship,canary_exp_off}/`.

Frozen gates — all green:

- **(a) Override echo, every zip** — 48/48. bc80:
  `boarding_crew_prevalence` 0.08 + passenger 0.0325 + shipped
  `common_source` object dict; a_ext: `common_source` carries
  `lot_shelf_life_days` [4,7]; ship: shipped dict +
  `boarding_crew_prevalence` 0.0185; off: `common_source.mode` `"off"`.
  `agent_class_fractions` stamped on all 48.
- **(b) Zip member contract** — 48/48 exactly `summary.json`,
  `growth_census.json.gz`, `rss_samples.json`.
- **(c) Witness fields** — bc80: `drawn_by_role.crew` mean 9.38
  (n=24, range 2–15) vs shipped-arm mean 2.25 — the 0.08 prevalence
  point reached the engine (~10.7 expected, in noise);
  `composition` carries shedding-state rows on every cell
  (block totals: never_symptomatic 127, presymptomatic 14,
  convalescent 275). a_ext: 33 objects (25 ill_handler / 8 ill_diner);
  ship: 22 objects (18/4); every object row carries `object_id` +
  `seeded_epoch`, every event row `object_id` + `pan_serial`
  (0 missing on both arms).
- **(d) off arm zero-witness** — 0 objects, 0 events, dose_credited
  0.000 across 4 cells.
- **(e) Engine status** — 48/48 Batch SUCCEEDED, all summaries parse.

Design §8 per-block expectations:

- bc80 handler-span channel: **64 `ill_handler` objects seeded
  ≤48 ep across 17 of 24 voyages — every source agent is `gen == 0`
  (a boarding import); 0 onboard-acquired sources.** The arriving-
  shedder channel demonstrably feeds early handler spans; the
  per-source attribution read works on `host.gen` (note:
  `emitting_imports` is a narrower emit-log set, not the import
  roll — `gen == 0` is the import key). The declared
  `source_boarding_state` shortfall (§9) stands for arrival-state
  identity, not needed for this gate.
- a_ext: `lot_shelf_life_days` [4,7] echoed 12/12; **zero
  `provisioned_lot` objects in 12 seeds** (E ≈ 0.13/voyage,
  P(0) ≈ 0.88 — consistent with the frozen rule that ≥1 object is
  not gated). The lot-extent draw is unexercised at canary scale;
  the object-level extent check carries to the wave (1,000 seeds →
  ~10 lot objects expected).
- ship: echo + 22 handler/diner objects on the campaign image.
- Object integrity: 0 bad `end_reason` across 342 armed-arm objects;
  dose_credited bc80 71.3 / a_ext 23.9 / ship 23.4.
- Non-degenerate: n_acquired bc80 3–33, a_ext/ship 1–28, off 17–28.

No report-immediately trigger fired. Per the frozen stop order the
canary is down and clean — the user reads it before any wave.

## Wave submissions

User go for the full campaign received 2026-10-10; all 27 fleet blocks
(27,000 cells) submitted in one pass 18:57 UTC in the design's frozen
order — exp all arms → cls/spr `ship`,`bc80`,`a_ext` → remainder — so
the FIFO queue drains exp first. Jobdef `picard-noro-entrain-01:1`
(digest-pinned `c57df157…`, retry ×10); every array is
`arrayProperties.size=1000` with literal container-overrides argv
(--campaign/--block/--seeds/--manifest/--pathogen-id/--epochs 288).
Manifest uploaded to `s3://crusherbucket-994254241749-us-east-1-an/campaign/noro_entrain_01/manifest.json`
for record parity (cells read it in-image).

Canary-seed overlap: the 48 canary seeds are inside the fleet exp
ranges (8000–8999) and re-fly — deterministic, ~48 cells of duplicate
work, keeps the grid whole.

First-landing health check at +5 min: `fl_exp_12d_scr_off` 230
SUCCEEDED / 115 RUNNING, zips already landing under
`campaign/noro_entrain_01/fl_exp_12d_scr_off/` (~10 MB each,
`…_s<seed>.zip`). No FAILED children.

| # | Block | n | Array job ID |
|---|---|---|---|
| 1 | fl_exp_12d_scr_off | 1000 | 1adf326b-6e16-4e4f-b598-a4bdb18b98fe |
| 2 | fl_exp_12d_scr_ind | 1000 | 5836af31-10a4-45d2-bff3-cd6c7df23ad8 |
| 3 | fl_exp_12d_scr_ship | 1000 | 1c3220b4-67e2-4b8c-8bf1-ba37bab22f3d |
| 4 | fl_exp_12d_scr_a_ext | 1000 | 045538f2-4738-4b91-8756-f750abd5974e |
| 5 | fl_exp_12d_scr_a_thin | 1000 | 29b94717-0d7d-4f5e-8a10-7f734fe673c2 |
| 6 | fl_exp_12d_scr_bc40 | 1000 | a7044a77-7b62-4181-ac5e-48d1df85b19d |
| 7 | fl_exp_12d_scr_bc80 | 1000 | 983c2b7a-7ecd-4f11-a4d5-c0e1c7b7554b |
| 8 | fl_exp_12d_scr_bi50 | 1000 | 355c1b55-5ec8-48bd-9911-720175bb4b3d |
| 9 | fl_exp_12d_scr_bmix | 1000 | 4bb35915-3082-49e7-9c80-ec96706e3221 |
| 10 | fl_cls_12d_scr_ship | 1000 | ba38165c-60d9-46c2-8f07-239853eb3c0a |
| 11 | fl_spr_12d_scr_ship | 1000 | e67293e2-7f9b-4bba-944c-c1d41d7961a2 |
| 12 | fl_cls_12d_scr_bc80 | 1000 | cd7b9ee2-c61b-47ce-a6d1-59a95255f12b |
| 13 | fl_spr_12d_scr_bc80 | 1000 | 05a314b8-e788-492e-8b5c-e103fc1dc0e9 |
| 14 | fl_cls_12d_scr_a_ext | 1000 | 50c17417-de17-4aa6-9498-c8eb2bd23978 |
| 15 | fl_spr_12d_scr_a_ext | 1000 | 5c271d41-2c6e-4607-8ed5-0f120a4e9fcc |
| 16 | fl_cls_12d_scr_off | 1000 | 15d2a915-30aa-42c1-a3f4-abca32b348dc |
| 17 | fl_spr_12d_scr_off | 1000 | fffdd2f5-8544-43e9-9ccb-3a587c4e3f77 |
| 18 | fl_cls_12d_scr_ind | 1000 | a9952c26-ed4f-4731-a807-139684b50ad1 |
| 19 | fl_spr_12d_scr_ind | 1000 | e72ff3bd-1690-4a45-916c-89e8d947fb21 |
| 20 | fl_cls_12d_scr_a_thin | 1000 | 486651cb-a277-489b-a73d-55c566bce1ac |
| 21 | fl_spr_12d_scr_a_thin | 1000 | aa9fd4cf-7f84-4d91-a6d1-933b1ba7ab6a |
| 22 | fl_cls_12d_scr_bc40 | 1000 | ce2c7229-c5c0-4152-9a9b-e7327028605c |
| 23 | fl_spr_12d_scr_bc40 | 1000 | 9fd52fbd-cd0d-4552-afb1-ee0f7343863a |
| 24 | fl_cls_12d_scr_bi50 | 1000 | 00310d06-3865-4651-b0e3-7dc148dc15d2 |
| 25 | fl_spr_12d_scr_bi50 | 1000 | b6a3c48b-0e28-498c-8ac7-e62f290ee9fd |
| 26 | fl_cls_12d_scr_bmix | 1000 | 85bfdb8f-d92c-4c38-af6c-398a36672260 |
| 27 | fl_spr_12d_scr_bmix | 1000 | d840a4d8-b381-4e74-862a-f4d747b3c8e2 |

Drain expectation for planning: exp ≈50–200 cells/min at 256 concurrent
(canary measured ~12 cells/min ramping cold); cls ~2–3× and spr ~6×
slower per SCORE-01 conventions — the grid is hours-to-a-day of Spot
time, not minutes.

## Findings

Readout of record: `docs/norovirus/noro_entrain_01_readout.md` (engine
`dbbd5395`, all 27,000 cells + 1,480 censused voyages + 1,350 exp head).

- **Lever A (event shape): no movement.** `a_ext`/`a_thin` are
  posting-identical to `ship` on paired seeds (posted sets ⊂ ship's on all
  hulls); conversion stays 0.1–0.2% cls/spr vs `ind` 4.4/1.7%. The
  opposite-direction contrast is null — extent is not the discriminating
  axis. `a_ext` realized ~2.3× events/takers at unchanged per-window mass;
  `a_thin` realized ~3× thinner windows. Neither moved posting.
- **Lever B (arriving shedders): rate in band, shape wrong.** bc40/bc80
  lift posting into band on spr (0.4/0.5%) and cls bc40 (0.8%), above band
  on cls bc80 (1.9%) and exp (2.3/3.7%) — bought by arriving-shedder mass:
  P(early) → 97–100%, ~95% of early objects sourced to gen-0 imports,
  posted voyages mostly new (bc80 exp 5/37 ∩ ship), conversion near `ship`
  rates (denominator-driven), no burst signature (exp posted 0.375 vs rest
  0.400). Posted-conditional pax AR still thin (0.012–0.017 < 0.04).
- **`bmix` net-sign: immunity dominates.** At equal crew prevalence, crew
  0.5 + pax 0.2 immune pools collapse posting to `bi50`/`ship` level
  (0.1% cls/spr) — the bc* gain is import mass, not mechanism.
- **Posted-AR band below 0.04–0.10 on every arm including `ind`** — the
  thin-signature gap is upstream of the cs mechanism entirely.
- **§6.4 mega gate not met:** spr bc80 rate leg in band but burst leg flat
  (0.276 ≈ rest 0.264) — mega stays excluded.
- **Must-not-move clean everywhere:** off zero-witness (0 obj/ev/takers),
  composition == drawn on 27,000 rows, route shares within ~1pp of ship,
  0 integrity violations in 41,732 object rows, immune echo exact
  (130/553/870 vs declared pools).
- Next declared tests: `cs_extent` redraw arm (cadence-vs-extent
  discrimination); `arriving_shedder` contract reparameterization; the
  posted-AR gap is upstream (reporting/case-def), unprobed by this sweep.
