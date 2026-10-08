# NORO-FOOD-SCORE-01 sweep design — scoring the contamination-object mechanism

> **Status:** frozen — grid, pairings, per-diagnostic scored criteria,
> and the must-not-move list are frozen before any array submits. No
> criterion in this file may be altered after a surface exists.

First fleet measurement of FOOD-COMMON-SOURCE-02's contamination
objects (spec `docs/food_common_source_02_design.md`; leg 1 + leg 2
shipped default-ON at main — `lot_mode` / `handler_mode` /
`diner_mode: "object"`, `"independent"` the labelled v1 baseline per
arm). This campaign executes the spec's pre-declared measurement plan:
it scores the shipped mechanism against the four settled diagnostics
and checks the spec's must-not-move invariants. Nothing is fitted;
every rung below is a declared point on a declared sweep axis.

Settled diagnostics being scored (from `noro_food_01_readout.md`,
`noro_food_02_readout.md`, `campaigns/noro/age_food_01/LEDGER.md` — do
not re-measure):

1. **Posting frequency** — real anchor ~0.3–0.5% of voyages posted
   (VSP/Mouchtouri); FOOD-02 located it at v1 event frequency
   E ≲ 0.4–0.9%/voyage; the v1 shipped interval ran ~10–20× high.
2. **Thin posted-conditional AR** — v1 posted-conditional reported pax
   AR 0.019–0.032 vs class IQRs ~0.04–0.10: one-pan events are too
   small to look like a foodborne outbreak.
3. **Hull-scaling compression** — v1 posting ceilings ~6.3% (exp) /
   ~4.2% (cls) / ~1.7–1.9% (spr): a fixed-size event buys less of the
   3%-of-population wire as the hull grows.
4. **Outbreak shape** — burst12 resolved the excursion signature on
   exp only (excursion med 0.36–0.45 vs ~0.13 background). Under
   objects the signature SPREADS over contiguous windows — the
   discriminator is re-declared below (spec measurement point 4).

## Arm semantics

`transmission.common_source` per-tier `config_overrides` (resolution:
profile block > `transmission.common_source.<name>` > frozen default
— `_cs_spec_range`):

| arm | modes | `lot_object_probability` | meaning |
|-----|-------|--------------------------|---------|
| `off` | `mode: off` | — | whole-mechanism labelled baseline; no stream spawned; the in-campaign posting floor on the current engine |
| `ind` | all three arms `"independent"` | — (v1 `lot_event_probability` U[0.02,0.15] etc.) | v1 shipped mechanism on the CURRENT engine — the contrast runs in-campaign on identical seed lists, not against an old commit |
| `ol1` | all three arms `"object"` | [0.0005, 0.0025] → E ≈ 0.15% | below the declared interval's lo edge — the tail probe if objects post hard |
| `ol2` | " | [0.001, 0.006] → E ≈ 0.35% | inside, near the v1-equivalent anchor's lower edge |
| `ol3` | " | [0.002, 0.012] → E ≈ 0.70% | inside, the composed point's lower half |
| `ship` | " | [0.001, 0.02] → E ≈ 1.05% | **the shipped declared interval — the scored configuration** |

E = interval mean = P(≥1 object voyage) at these rates (rare-event);
each object voyage carries a geometric count tail via the shipped
`extra_lot_probability` U[0.02,0.25] (E[K] ≈ 1.16 per object voyage).
Handler/diner arms run their shipped object intervals
(`handler_span_contamination_probability` U[0.01,0.30],
`diner_course_contamination_probability` U[0.005,0.15]) on every
object rung — not swept; their unswept contribution is the residual
floor read exactly as in FOOD-02 §4.

## Grid and fixed coordinates

3 hulls × 6 arms = 18 cells × 1,000 seeds = **18,000 voyages**, tier
ids `fl_<hull>_12d_scr_<arm>`; builder
`campaigns/noro/noro_food_score_01/design/build.py` (every arm and
seed declared there — regenerate, never hand-edit); manifest
`picard_framework/runs/mega_cruise_campaign/noro_food_score_01_manifest.json`;
campaign spec `campaigns/noro/noro_food_score_01/campaign.json`.

Fixed on every cell — identical to NORO-FOOD-01/02 and AGE-FOOD-01 so
cells pair voyage-for-voyage: boarding rung `shipped`, prevalence
point bp32.5c18.5, `nsf29`, 288 epochs (12 d), `dose_adjustment`
7.57, surveillance `syndromic_comp65`, the FOOD-02 transmission/hvac
block unchanged (`sanitary_visit_mode: dwell_weighted`, flush
aerosol 0.0 / cabin emission on, `cabin_air_mode: cabin_compartment`,
`hvac.pathogen_pool_transport: airflow`), escalation defaults. The
generic shipped passenger mix (AGE-FOOD-01's `gen` arm — the age arms
are not the question here); `ship_graph.agent_classes` declared
verbatim on every tier so `agent_class_fractions` stamps on every
arm's parameters (resolved config identical, voyages bit-identical to
the un-declared mix).

Seeds — the AGE-FOOD-01 lists, pairing free with FOOD-01/02 and
OUTBREAK-02/03/04: exp 8000–8999, cls + spr 8105–9104.

**Attribution discipline (frozen):** inside the re-roll band the
voyage draw changes shape (Bernoulli+geometric count vs one
Bernoulli), so per-seed pairing cannot attribute mechanism effects —
arms contrast **distribution-level on identical seed lists**, per the
stochastic-attribution skill. Paired per-seed counts are reported only
for the binary posting outcome (gained/lost vs `off`, the reporting
convention FOOD-01/02 used); no claim that seed N's ind voyage maps
to seed N's object voyage. The `ind` arm exists so the v1 contrast
runs on the current engine; FOOD-01/02's old-engine cells are a
secondary, looser reference (engine drift is flagged, not hidden).

## Scored criteria per diagnostic (what "scored" means)

The campaign is a measurement: no cell is admissible or inadmissible
by outcome. Each diagnostic is scored when its listed rows exist in
the readout; the decision reads are declared now.

### D1 — posting frequency (the anchor)

- Per hull per arm: posted share per 1,000 voyages (Wilson 95% CI)
  and paired gained/lost vs the `off` arm —
  `tools/noro_diag/outbreak_anchor_readout.py`.
- **Scored read:** mechanism-attributable posting = posted_arm −
  posted_off per hull; the anchor is located by the dose-response of
  that contribution vs E across ol1/ol2/ol3/ship — not each rung
  independently inside the band (at n=1,000, ~3-posting cells carry
  CIs wider than the band; the ladder resolves it jointly, exactly
  as FOOD-02's verdict did).
- **Band-consistent:** a rung whose marginal contribution sits at
  ≈0.3–0.5pp within CI on the clean-floor hull (spr floor ~0.0%
  measured by FOOD-02; this campaign re-measures floors in-campaign
  on `off`). On cls/exp the floor sits at/above the band, so the read
  is floor-aware: total posted ≈ off-floor + band-consistent
  contribution.
- **Shipped verdict:** `ship`'s marginal contribution vs the
  ~0.3–0.5pp band — "signature recovered, interval sits high/low"
  framing applies per the recurring-defect convention (a declared
  interval landing off-anchor is a measurement, not a defect).

### D2 — thin posted-conditional AR (the "shape of the outbreak")

- `posted_pax_ar` (quantiles of
  `reported_case_attack_rate_passenger` among posted voyages) per
  cell where n_posted ≥ 10, else pooled across that hull's object
  cells (declared pooling rule: report per-cell where powered, pooled
  otherwise, never mixed silently).
- **Scored read:** object-mode pooled median vs the class-IQR band
  ~0.04–0.10 AND vs the `ind` arm's same statistic on the current
  engine. **Recovered** = pooled object median ≥ 0.04 (band lower
  edge); below that = the thin signature persists — reported either
  way; no criterion was chosen after seeing the surface.

### D3 — hull-scaling compression

- Per hull per arm: excursion→posting conversion (posted | ≥1
  object/event voyage) — v1's ~43% is re-measured on `ind` on the
  current engine and compared to the object rungs' conversion per
  hull.
- Posted ceiling comparison: `ship` and `ind` posted share per hull
  vs FOOD-01's measured ceilings (6.3/4.2/~1.7–1.9%).
- **Scored read:** whether a bigger object buys more of the 3% wire
  on the 3,000-agent hull — spr's conversion and ceiling under
  objects vs under `ind`.

### D4 — outbreak shape (declared honestly, per spec point 4)

- `tools/noro_diag/onset_curve_readout.py` (stride-200 sample per
  cell plus every excursion voyage forced in via `--also-seeds`),
  reporting **burst48 AND burst12** excursion-vs-rest per hull — the
  spec re-declares burst48 (or a declared cluster-window metric) as
  the discriminator for window-spanning objects; burst12 may FALL
  vs v1's exp 0.36–0.45 and a fall is not a failure.
- Declared secondary metric: **object-window-aligned acquisition
  share** — the share of a voyage's `common_source_food` acquisitions
  whose acquisition epoch falls inside an emitting object's live
  span (offline join of the census `objects` rows and emit records —
  both already in the run zips; computed by the readout tooling, no
  engine change).
- **Scored read:** shape recovered = excursion-vs-rest separation on
  burst48 (medians) on ≥1 hull, with per-hull reads reported (exp
  resolves, cls/spr dilution is expected and reported as such). The
  failure mode is no separation on any window at any hull while the
  posting tail exists — that combination says the objects are not
  producing outbreak-shaped clusters.

### Witness diagnostics (reported, never selected on)

Per `common_source_readout.py` object view: objects/voyage, pans/
object, windows/object, `end_reason` mix, `multi_pan_windows`,
objects-per-voyage distribution, zero-dose event-row share (should
fall vs v1's ~58% — lot pans carry titre > 0 always), takers/event,
arm-mix L/H/D, cs_food route share per cell.

## Must-not-move (a move here is a defect signal, not a failed arm)

Distribution-level vs the `off` arm on identical seeds, per hull:

1. **Median infection AR** — flat across arms; paired per-seed median
   Δ vs `off` within noise (recorded references ~7.3% exp /
   ~9.4% cls+spr pax from the AGE-FOOD-01-era engine — report drift
   vs them explicitly; they are engine-drift references, not the
   criterion).
2. **Unrelated pathway counts** — contact, aerosol, HVAC, fomite,
   pool routes distribution-equal to `off`; `common_source_food`
   remains a small route share (the >50% over-delivery alarm stands;
   FOOD-01 measured 1.2–8.9%).
3. **Non-object voyages** on object-run cells: distribution-
   indistinguishable from the `ind` arm's no-lot voyages.
4. **Baseline arms:** `off` cells show zero objects, zero events,
   zero credited dose on every voyage; `ind` cells show zero
   `common_source_objects` rows (v1 path emits events only).
5. **Object integrity (fleet census):** every event row's `object_id`
   resolves to an `objects` row; per lot object `servings_served` ≤
   `lot_servings`; only `norwalk_gi` is armed (`sars_cov2_resp`
   removed by the manifest; every other profile zero-rate by
   construction — zero objects of any other pathogen).

## Canary and waves (the stop order)

1. **Local smoke** (done, this checkout): `fl_exp_12d_scr_ship`
   index 0 via `scripts/campaign run` — voyage clean (28 acquired),
   3-member zip contract (summary.json, growth_census.json.gz,
   rss_samples.json), `parameters.common_source` echoes the ship rung,
   `agent_class_fractions` stamped, one `ill_handler` object with
   `pans_emitted`/`object_windows`/`end_reason` populated and event
   rows carrying `object_id`/`pan_serial`.
2. **Canaries** (44 voyages, submitted first, then STOP for the
   user): `canary_exp_ship` (24 seeds — the scored configuration;
   satisfies the ≥20-seed gate), `canary_exp_ind` (12), `canary_exp_off`
   (8). Verify per arm:
   - zips land under `campaign/noro_food_score_01/<block>/` with the
     3-member contract;
   - `parameters.common_source` echoes the arm's modes + rung;
   - `ship`: `common_source` witness block present with `objects`
     list and object telemetry; handler/diner objects firing (a lot
     object in 24 seeds is NOT gated — P(0 lot objects) ≈ 78% at
     E ≈ 1.05%; the gate is the echo + leg-2 objects);
   - `ind`: events fire v1-style, zero objects rows;
   - `off`: zero events, zero objects, zero dose;
   - posted/vsp fields sane, non-degenerate voyages.
   Anomalous → stop and report. Clean → the user decides the fleet.
3. **Wave 1:** `fl_exp_*` + `fl_cls_*` (12 cells, 12,000 voyages).
4. **Wave 2:** `fl_spr_*` (6 cells, 6,000 voyages) — independent
   submission; spirit is the ~4×-classic per-voyage cost and the wave
   to trim first if the budget says so.

No mega cells: the four diagnostics resolve on the 3 scored hulls;
mega is a possible later wave and needs an explicit go-ahead (its own
cost class). No array is submitted under this design — the user gates
image build, canary, and every wave.

## AWS wiring (frozen)

- Image: `picard-campaign:noro-food-score01` built at the merged
  design SHA via root `Dockerfile` + `deploy/aws/Dockerfile.campaign`
  overlay — **build is a post-merge step** (the image pins the SHA);
  digest recorded in the campaign LEDGER at build time.
- Jobdef `picard-noro-food-score-01` rendered by
  `scripts/campaign submit` from `deploy/aws/campaign_jobdef.json`;
  the digest-pinned revision (never a bare tag) is recorded per array.
- Output prefix `s3://crusherbucket-994254241749-us-east-1-an/
  campaign/noro_food_score_01/` — verified free before first submit.
- Queue `picard-campaign-queue` (Spot); `picard-analysis-queue`
  (On-Demand) is the user-approved escalation if Spot parks arrays
  >1 h. Resources 1 vCPU / 4096 MB / shm 512 — the AGE-FOOD-01
  non-mega class.
- Worker `tools/noro_diag/growth_chain_census.py` — its census member
  already emits `payload["common_source"] = {telemetry, events,
  objects}` (the leg-1/leg-2 object witness included); the readout
  tools accept this shape.

## Report immediately if

- any rung's lot-object-voyage share ≫ its E (override not applied /
  misfire);
- objects or events appear on `off` cells, or object rows appear on
  `ind` cells (arm-mode wiring defect);
- zero handler/diner objects across the whole `ship` canary (the
  leg-2 pipeline is dead at fleet scale);
- any must-not-move fails (median AR moved, a non-cs route moved, a
  cs_food share > 50%);
- >5% child failures on a cell, or Spot parks arrays >1 h;
- posted voyages are too rare to score D2 even pooled across object
  cells on a hull (the AR criterion is then unmeasurable — report,
  don't relax it silently);
- object integrity breaks (unresolvable `object_id`, servings_served
  > lot_servings, objects on unarmed profiles).

## Readout plan (the deliverable at fleet time)

1. `outbreak_anchor_readout.py` over the parent prefix — per-cell
   posted share + Wilson CIs, paired gained/lost vs `off`, posted_pax_ar
   quantiles, median infection/reported ARs (D1, D2, must-not-move 1).
2. `common_source_readout.py` object view — objects/voyage, pans/
   object, windows/object, `end_reason` mix, zero-dose share,
   multi-pan tail, arm mix (D3 inputs + witness diagnostics).
3. `onset_curve_readout.py` with the excursion join — burst48 +
   burst12 excursion-vs-rest per hull (D4).
4. Object-window-aligned acquisition share — offline join over census
   `objects` + emit records (D4 secondary).
5. Residual floor at `ol1` — handler/diner-only excursions and their
   posting contribution (FOOD-02 §4's read, repeated under objects).

## Exclusions (settled, do not re-derive)

- No engine or constant changes; every override is a declared
  `config_overrides` interval on an existing sweep axis.
- No handler/diner probability rungs, no posture arms
  (`food_safety_posture` 1.0, `lot_posture_coupling` false
  throughout), no per-arm object/independent mixes beyond the two
  labelled columns — the diagnostics score the shipped configuration,
  not a per-arm decomposition.
- No age arms (gen only — the age question was AGE-FOOD-01), no
  bp-diagonal expansion (FOOD-01 measured the excursion share flat
  across it), no 7-day tiers, no ren rung, no mega (declared above),
  no flu/covid/vibrio/campylobacter arms.
- No UI work. Campaign artifacts regenerate from `design/build.py`
  only — never hand-edit `campaign.json` or the manifest.

## Non-goals

No array submission under this design (not even the canary — the user
gates everything after the frozen design lands), no image build, no
readout tooling changes beyond what the plan names at readout time,
no mechanism or schema changes.
