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

(to be filled per wave — job ids, s3 prefixes, seed gates)

## Findings

(to be filled at readout — `docs/norovirus/noro_entrain_01_readout.md`)
