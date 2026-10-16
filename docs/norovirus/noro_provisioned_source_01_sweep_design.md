# NORO-PROVISIONED-SOURCE-01 — provisioned-source sweep design (frozen, declared)

**Status: frozen design — declared before cells.** All gates, seed lists,
draw specifications, and expected values in this file are declared now,
before any cell submits, and may not be tightened after readout. Any
amendment lands as its own ledger entry naming what changed and why.
Mechanism contract: `docs/provisioned_source_01_design.md`
(PROVISIONED-SOURCE-01 — the contract this campaign measures).
Ledger: `docs/ledger/PROVISIONED-SOURCE-01.md`.
Campaign package: `campaigns/noro/provisioned_source_01/`,
`campaigns/noro/provisioned_source_01_mega/`.

**Branch:** off `origin/main` at `f7bbec40`. Engine line numbers cited
below are at that SHA. **The campaign does not submit until the
implementation leg lands the mechanism and its witness fields
(§5.3) and the image pins a SHA containing them** — this doc freezes
the arm table and the arithmetic; nothing in it depends on unshipped
behaviour being correct, only on the contract being the shipped one.

**Amendment A1 (pre-submit):** (a) §1 window citation and the §2
derived chain updated to the MINT-RATE-01 measured brackets (was
the pre-readout predictions) — measured brackets re-centre the
common-q window on the declared q03 point; (b) §5.3-2 gate
rewritten — bit-identity vs landed cells is unmeasurable under F0
(MINT-RATE-01 LEDGER: host-level nondeterminism; same image
diverges by host) — replaced by the convention MINT-RATE-01
adopted: minted-set identity + statistical parity. No arm, q value,
seed list, or admissibility criterion changed.

## 1. What is being measured and why

FOOD-SHAPES-01 measured that the mint gate is the only surviving margin
that reproduces the posting signature (`ind`-parity per hull), and
MINT-RATE-01 measured the required per-hull gate windows
**exp [0.005, 0.0105] / cls [0.005, ~0.020] / spr [0.008, 0.024]**
(27,000 cells, readout `docs/norovirus/noro_mint_rate_01_readout.md`)
— the fiat gate's p*(hull) ladder, hull-parametrized because the fiat
mechanism is a dial. NORO-HULL-SCALE-01 measured that the carrier is a hull-FLAT
per-lot yield (~104 takers / ~30–37 cs cases per object); mega arms and
fires but needs p* ≈ 0.09–0.25, outside the shipped U(0.02, 0.15).

PROVISIONED-SOURCE-01 derives the mint: objects-per-voyage =
Binomial(N_lots, q_source), N_lots = served-venue × item-line station
census, q_source hull-invariant. **The testable claim** (contract §5):
station-N scales like the measured required-object scale, so ONE
q_source puts all three small hulls in-band — the admissible region
becomes hull-free, the headline read is whether measured marginals
match. Second headline: where mega's in-band window lands vs the
single-lot extrapolation q_mega ≈ [1.5e-3, 4.1e-3] (and whether
multi-lot voyages pull it below).

## 2. Measured inputs (locked, do not re-derive)

- Posting band: D1 marginal 0.4–0.9 pp (exp observed +0.65 pp).
- `P(post | ≥1 lot object)` ≈ 0.93 / 0.58 / 0.36 exp→cls→spr
  (SHAPES-01 readout §7); hull-flat ~104 takers / ~30–37 cs cases per
  object (HULL-SCALE-01 §1–§2).
- Required E[objects] (measured gate window × geometric-tail factor
  1.163): exp [0.0058, 0.0122]; cls [0.0058, 0.0233];
  spr [0.0093, 0.0279].
- Station censuses (contract §1.2): **N_lots = 21 / 35 / 63 / 70**
  exp / cls / spr / mega.
- Implied per-hull in-band q under the mechanism (presence ≈ N·q,
  measured windows): exp ≈ [2.4e-4, 5.0e-4];
  cls ≈ [1.4e-4, 5.7e-4]; spr ≈ [1.3e-4, 3.8e-4];
  common window ≈ [2.4e-4, 3.8e-4] centred at **q ≈ 3e-4** — the
  declared `q03` rung lands inside all three measured brackets
  (frozen prediction: +0.59 / +0.61 / +0.68 pp at `q03`).
- mega: E[objects] ∈ [0.105, 0.29] ⇒ q ∈ [1.5e-3, 4.1e-3]; at common q
  mega carries ~0.02 objects/voyage — near-absent under the census.
- Fiat bridges: `ship` U(0.001, 0.02) presence ≈ 0.0105 (vacuous,
  ~6 minted voyages/1000), `mint` U(0.02, 0.15) presence ≈ 0.0831
  (over-posting at ind level, full signature).
- Objects/minted-voyage ~1.2 measured; geometric tail only on fiat
  arms. The mechanism has no tail — contaminated stations mint
  independently; E[objects] = N·q exactly.
- ~95% of early objects in the ENTRAIN-01 census were import-sourced
  (ill_handler/ill_diner) — the worker channel stays mechanistic and
  is the counterfactual share the readout splits against.

## 3. Grid

### 3.1 Arm table (frozen)

All arms: `norwalk_gi`, `syndromic_comp65`, boarding `shipped`
(0.0325/0.0185), nsf 0.29, 288 epochs, standard bundle (§4). Runs listed
once; exp/cls/spr take every row, mega takes all rows except the two
fiat bridge arms.

| arm | `common_source` override | role |
|---|---|---|
| `off` | `{mode:"off"}` | floor |
| `ind` | `{"handler_mode":"independent","diner_mode":"independent","lot_mode":"independent"}` | signature denominator |
| `ship` | `{"lot_mint_model":"fiat","lot_object_probability":[0.001,0.02],"extra_lot_probability":[0.02,0.25]}` (object modes) | fiat bridge (vacuous anchor) + minted-set & statistical parity vs landed cells |
| `mint` | `{"lot_mint_model":"fiat","lot_object_probability":[0.02,0.15],"extra_lot_probability":[0.02,0.25]}` (object modes) | fiat bridge (powered anchor) + minted-set & statistical parity |
| `ps_ship` | `{"lot_mint_model":"provisioned_source","provisioned_source":{"source_id":"generic_cruise_port","q_source":[2e-4,5e-4]}}` (object modes) | the shipped default configuration under the new mechanism |
| `q01` | same as `ps_ship`, `"q_source":0.0001` | scalar rung — below all bands |
| `q02` | `"q_source":0.0002` | scalar rung — band floor |
| `q03` | `"q_source":0.0003` | scalar rung — **predicted hull-free point** |
| `q05` | `"q_source":0.0005` | scalar rung — band ceiling / over edge |
| `q08` | `"q_source":0.0008` | scalar rung — small-hull over; mega multi-lot onset |
| `q15` | `"q_source":0.0015` | scalar rung — mega extrapolation floor |
| `q30` | `"q_source":0.0030` | scalar rung — mega extrapolation centre |

Rung rationale: the measured common window sits at 2–4e-4 — rungs
bracket it at 1e-4 / 5e-4 with `q03` declared the predicted common
point; `q08`–`q30` trace mega's window and measure the multi-lot
lift curve (P(K≥2) = 0.017 / 0.14 / 0.39 of minted voyages at
q08/q15/q30 on N=70). The ladder also answers the failure question —
if no common band exists, where the hulls split.

### 3.2 Declared E[objects] per hull (N·q — the §5.4 expectation gate)

| rung | exp (21) | cls (35) | spr (63) | mega (70) |
|---|---|---|---|---|
| q01 | 0.0021 | 0.0035 | 0.0063 | 0.0070 |
| q02 | 0.0042 | 0.0070 | 0.0126 | 0.0140 |
| q03 | 0.0063 | 0.0105 | 0.0189 | 0.0210 |
| q05 | 0.0105 | 0.0175 | 0.0315 | 0.0350 |
| q08 | 0.0168 | 0.0280 | 0.0504 | 0.0560 |
| q15 | 0.0315 | 0.0525 | 0.0945 | 0.1050 |
| q30 | 0.0630 | 0.1050 | 0.1890 | 0.2100 |
| ps_ship (drawn [2e-4,5e-4], E q=3.5e-4) | 0.0074 | 0.0123 | 0.0221 | 0.0245 |

### 3.3 Cells

exp / cls / spr: 12 arms × 1,000 seeds = **12,000 voyages each**
(36,000). mega: 10 arms × 1,000 = **10,000** (fiat bridges omitted —
mega's fiat cells are vacuous and have no landed bridge target).
**Total 46,000 cells + ~128 canary.** Seeds: exp 8000–8999,
cls/spr/mega 8105–9104 (the SCORE-01 lists; mega reuses the
HULL-SCALE-01/MEGA-IMPACT list).

Mega cells are the heavy leg: the tier requests `memory: 8192` in its
jobdef resources (MEGA-IMPACT's working point after AGE-FOOD's 6144
OOM; pending canary `rss_samples` read — if the canary peaks
under ~6 GB the array may resubmit at 6144, declared not frozen).
Mega runs in its own wave and its own campaign spec
(`campaigns/noro/provisioned_source_01_mega/`) sharing the manifest,
the AGE-FOOD-01 split precedent.

## 4. Frozen configuration overrides

Identical to MINT-RATE-01 §4 except the common_source block. Standard
bundle per tier: `pathogen_scenarios` entries (`norwalk_gi` +
`active_profiles` minus `sars_cov2_resp`), `seasonal_forcing 0.29`,
`num_epochs 288`, `embarkation_date 2026-01-10`,
`syndromic_comp65` + `dose_unit_scale 7.57`, `norwalk_gi` agent_class
7-entry mix, `boarding_infection_profile` `shipped`
(0.0325/0.0185), `cabin_air_mode`, `sanitary_visit_mode`,
flush flags, `hvac.pathogen_pool_transport` = `airflow`.
`common_source` per §3.1 — the exact key sets are frozen in
`campaigns/noro/provisioned_source_01/design/build.py`
(`FOOD_OVERRIDES`): object-mode arms carry `lot_mode`/`handler_mode`/
`diner_mode` = `"object"` (the MINT-RATE-01 mode keys verbatim) plus
the arm's mint keys; `ps_ship`/rung arms add
`lot_mint_model:"provisioned_source"` and the `provisioned_source`
block whose explicit `q_source`/`source_id` win over the registry per
contract §1.1; fiat bridges carry `lot_mint_model:"fiat"` +
`lot_object_probability` (extra_lot unoverridden — shipped U(0.02,0.25)
applies).

## 5. Gates

### 5.1 Admissibility (D1–D4, adapted from MINT-RATE-01 §5)

- **D1 (posting marginal)** — per arm × hull, reported posting marginal
  over `off` in the 0.4–0.9 pp band. The headline read is the SET of
  rungs simultaneously in-band on exp+cls+spr (the hull-free claim;
  frozen prediction `{q03}` plus edge neighbours), and mega's in-band
  set (predicted `{q15, q30}`-region). `ps_ship` is read separately —
  it is the shipped-config check, not a rung.
- **D2 (severity)** — per in-band rung per hull: pooled posted-pax-AR
  median within [0.5×, 2.0×] the in-campaign `ind` median for that
  hull (verdict reads vs `ind`, the proven comparator — not vs
  truth, same convention as #998/#999). Mega's `ind` median comes
  from its own `ind` arm.
- **D3 (conversion)** — median converted-pax-AR among posted voyages
  within [0.5×, 2.0×] `ind` per hull, pooled in-band read.
- **D4 (shape)** — posted bursts not collapsed to rest (the HULL-SCALE
  mechanism unchanged, expected-pass); the spr excursion-vs-rest
  comparison stays declared unreadable (largest-ship cohort reads
  compound atop multiple pool excursions); mega's D4 declared TBD —
  posted bursts have never been measured on mega, the campaign posts
  the first number.
- **Vacuity** — arms with <20 object-carrying voyages report the
  presence census + marginal only (the `ship` bridge on small hulls
  and `q01`–`q02` on exp/mega will land here); not a gate failure.

### 5.2 Verdicts (declared)

- **Common-q band** = intersection of in-band rung sets across
  exp+cls+spr. Prediction: non-empty, contains `q03`. Empty ⇒
  hull-free claim dead ⇒ venue-station N_lots wrong (revisit §1.2's
  recorded alternative before any tuning).
- **Mechanism admissible** = non-empty common band AND `ps_ship`'s
  interval-marginal lands inside it AND D2/D3 pass per hull.
- **Mega** = in-band rung set exists (read vs its own `ind`) — lands
  at/below the extrapolation (multi-lot lift measured) or stays
  empty (yield ceiling, a finding not a defect).
- **Ship-vs-fiat check** — `ps_ship` marginal vs `ship`/`mint` anchors
  must sit between them ordered by realized E[objects]; an inversion
  is a mechanism defect, not a tuning signal.

### 5.3 Integrity gates (extends contract §4)

1. **Nested station sets** — per seed, contaminated-station identity
   (zone×item of provisioned_lot objects) at q_a ⊆ that at q_b for
   q_a < q_b, rung pairs (q01,q02,q03,q05,q08,q15,q30) per hull.
   Violation ⇒ stream-layout defect, full stop.
2. **Baseline parity (amended A1 — was bit-identity)** — `ship`/`mint`
   cells at shared seeds are checked against the landed
   MINT-RATE-01/SHAPES-01 cells on two axes, matching the convention
   MINT-RATE-01 adopted under F0 (bit-identity across hosts is
   unmeasurable; the seed-paired minted SET draws are bit-stable,
   trajectories are not):
   a. **Minted-set identity** — per shared seed, the set of voyages
      minting ≥1 provisioned_lot (and the per-voyage object census)
      is identical to the landed cell's set.
   b. **Statistical parity** — cell marginals (posted counts,
      excursion counts, AR distributions) statistically consistent
      with the landed cells at 1,000-seed power, via paired-seed
      comparison (`tools/noro_diag/food_shapes_01_bridge.py`
      compare-mode in its statistical form).
   A minted-set mismatch ⇒ the fiat draw sequence changed ⇒ stream
   defect, array STOPs. Statistical drift beyond tolerance ⇒ the
   fiat path isn't preserved ⇒ array STOPs.
3. **Declared expectation** — object counts track N·q within
   binomial tolerance per (rung, hull); `n_stations` echoes
   21/35/63/70.
4. **Station witness** — every provisioned_lot object's (zone, item)
   ∈ the voyage's station census; `q_source_drawn` echoes the arm.
5. **Witness presence** — `common_source.provisioned_source` voyage
   block (source_id, q_source_drawn, n_stations, n_contaminated),
   `provisioned_source_id` on provisioned_lot rows, and the
   `reported_cases_by_dominant_route` summary block per §3 of the
   contract. Absence ⇒ the implementation leg is incomplete ⇒
   canary STOPs.
6. **Import share** — the census's per-source_kind split
   (provisioned_lot vs ill_handler/ill_diner) lands ≈ the ENTRAIN-01
   ~95% import share at thin rungs where provisioned objects are
   rare; a collapse of the worker share flags span-channel drift,
   not a lot-gate issue.

## 6. Canary (~128 cells, then STOP)

| block | cells | purpose |
|---|---|---|
| `canary_exp_mint` | 48 | fiat bridge — interval echo, objects fire, minted-set + statistical parity spot-check vs landed cell |
| `canary_exp_q30` | 24 | mechanism machinery — scalar q echo, n_stations=21, objects bind stations, E≈1.5 objects expected |
| `canary_exp_q03` | 24 | echo + nested-set spot-check vs q30 at shared seeds (q03 sets ⊆ q30) |
| `canary_exp_ps_ship` | 8 | shipped-default block — interval echo [2e-4,5e-4], registry resolution of `generic_cruise_port` |
| `canary_exp_ind` | 8 | baseline echo |
| `canary_exp_off` | 4 | floor echo |
| `canary_mega_q30` | 12 | mega arming on the new mode — n_stations=70 census echo, ≥1 object expected (P(0)≈0.08), rss_samples for the jobdef-memory read |

Gates per block before wave 1: echo present and equal, census block
present, objects bind census stations, worker-channel objects present,
no `simulation_error`/`hang_watchdog`. Then STOP and report: emitted
marginals, object census by source_kind, minted-set + statistical
parity result vs landed cells (gate 5.3-2 as amended), mega RSS read.
User decides wave 1.

## 7. Wave order

1. exp — 12 arms × 1000 (proof of mechanism + signature bracket)
2. cls + spr — 12 arms each (the hull-free test lands here)
3. mega — 10 arms (heaviest; user-gated; the second headline)

Each wave gated by user review of the previous wave's marginals +
integrity reads.

## 8. Readout plan

- `tools/noro_diag/food_shapes_01_scan.py` (walker — extends for the
  `provisioned_source` voyage block + station census; the extension
  lands in the implementation or readout leg, declared not built here)
- `tools/noro_diag/food_shapes_01_report.py` — D1 marginals + census
- `tools/noro_diag/outbreak_anchor_readout.py` — D1/D2 anchor rows
- `tools/noro_diag/early_event_scan.py` + `early_event_report.py` —
  D3 conversion
- `tools/noro_diag/growth_chain_census.py` — `common_source` block:
  per-source_kind object split, station census, q echo
- `tools/noro_diag/hull_scale_01_scan.py` — the objects → takers →
  cases → reported → posted chain re-read under the mechanism per hull
  (where N·q enters the chain and where it compresses)
- `tools/noro_diag/food_shapes_01_bridge.py` — minted-set identity +
  statistical parity vs landed cells (gate 5.3.2 as amended A1)
- `tools/noro_diag/entrain_01_dose_audit.py` — dose positions only
  (dose ledger withdrawn; no absolute figures anywhere in the readout)
- `reported_cases_by_dominant_route` — the posted-vs-acquired
  decomposition per rung: how much of each rung's posted count is
  lot-sourced vs worker-sourced vs import — the number that explains
  the common band (or its absence).

## 9. Expected results (frozen)

| quantity | exp | cls | spr | mega |
|---|---|---|---|---|
| E[objects] at q03 | 0.0063 | 0.0105 | 0.0189 | 0.0210 |
| predicted q03 marginal | +0.59 pp | +0.61 pp | +0.68 pp | ≈ +0.1–0.3 pp (below band) |
| in-band rung set | {q03} ±edges | {q03} ±edges | {q03} ±edges | {q15,q30}-region |
| verdict | common band exists | common band exists | common band exists | own window |

`ps_ship` interval-marginal prediction: +0.45–0.85 pp each small hull
(E[q]=3.5e-4 centred in the common window); mega below band.

## 10. Fail-informative reads

- No common-q band ⇒ venue-station N_lots wrong ⇒ revisit the recorded
  consumption-throughput alternative (contract §1.2) before tuning.
- `ps_ship` over-band on all hulls ⇒ shipped default interval
  too high (declare narrower); under-band ⇒ too low. Either is a
  defaults fix, not a mechanism defect — IF gate 5.3.3 held.
- Bit-identity failure ⇒ engine drift on the fiat path; the campaign's
  bridge arms are void until re-based.
- Mega in-band at `q03` ⇒ multi-lot lift much stronger than
  extrapolated — good news; revise the compression law's mega tail.
- Nested-set violation ⇒ stream contract broken at the draw level;
  STOP, mechanism bug, no tuning proceeds.

## 11. Non-goals

No dose-ledger numbers (positions only); no sourcing leg for q_source
or port registry (declared Grade C); no restock cadence; no new worker
mechanics; no Batch submit in the design PR; no platform registry rows
beyond cruises this campaign (the registry is the seam, cruises the
first consumer).
