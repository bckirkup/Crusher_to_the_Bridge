# NORO-FOOD-SHAPES-01 — Frozen evaluation design

**Status: frozen — declared before any cell ran.** Grid, arm set,
admissibility criteria, integrity gates, canary spec and readout plan
below are the contract. Any post-readout change goes in a ledger entry
that names what changed and why; it does not retro-edit this file.

**Branch:** off `origin/main` at `36ce23c8` (merge of #991,
NORO-CS-EXTENT-01). The eval image will additionally contain #992
(NORO-CS-EXTENT-02 — tests+ledger pin, **no engine diff**): its two
gates prove `per_window` re-mints resolve through `_cs_titre_spec`, so
under shipped `two_mode` every re-minted window titre lands inside the
implicated band — settled, not a pending patch.

## 0. The question

Do the two measured missing margins — **implicated titre denominator**
(`two_mode`, #990) and **cadence dose shape** (`per_window` re-mints +
`declared` extent, #991) — recover `ind`-like conversion on object arms
and the D2 posted-AR signature, while D1 stays in the posting band and
the D4 burst48 discriminator keeps? **Mint-rate is the third axis**
because channel absence is measured (#988: provisioned_lot objects
minted in 2/1,620 unposted cells). Hypothesis to design against, not a
goal-fit: nothing here is tuned to an anchor; arms are declared
mechanism variations only.

## 1. Settled inputs (measured context, do not re-derive)

All numbers from committed readouts on main; each cites its SHA.

**NORO-FOOD-SCORE-01** (`40862b8c`, #981; readout
`noro_food_score_01_readout.md`, state `docs/ledger/NORO-FOOD-SCORE-01.md`):

- **D2 not recovered**: object-arm posted-pax-AR pooled medians
  0.016–0.021 < the 0.04 recovery edge, every hull.
- **D3 under-conversion**: cls/spr shared-dose excursions convert to
  posting ~0–6% on object arms vs `ind`'s 42.7/13.3%.
- **D1 partial**: honest posting signature (monotone lot-rung
  dose-response, ship marginal +0.6/+0.2/+0.1pp vs `off`,
  channel-clean gained postings) but thin.
- **D4 recovered on exp**: cs-excursion burst48 0.564 vs rest 0.400;
  posted object-arm bursts sit at rest level (~0.389).

**Early-event analysis** (#982): event size is not the discriminator —
object events of 317–959 takers convert ~0.1–0.2% while `ind` events of
26–72 takers convert 1.4–19.5%. The margin is in what is delivered
and how it is shaped over time, not how many servings exist.

**NORO-ENTRAIN-01** (`dbbd5395`, #986; readout
`noro_entrain_01_readout.md`): Lever A (event shape, config axes only)
null; Lever B (arriving-shedder proxy) buys postings via import mass
but AR stays below band on every arm. Measured baselines this design
re-measures at the eval image: posting marginal exp `off` 1.0% /
`ind` 6.8% / `ship` 1.5%; cls `ind` 3.9% / `ship` 0.1%; spr `ind`
1.6% / `ship` 0.2%; all posted pax-AR medians <0.04 (object arms
0.016–0.021); excursion→posting conversion `ind` 14.3/4.4/1.7%
(exp/cls/spr) vs `ship` ~0.1–0.2%; `ind` posted burst48 0.521 vs rest
0.400.

**NORO-DOSE-POS-01** (#988; `noro_dose_position_audit.md`):

- Delivered doses sit at p≈0.2–0.35 on the declared Hill
  (η=0.508, γ=0.095); posting rides the dose tail — posted median
  cumulative dose 537/96/68 vs unposted 28/36/37 (exp/cls/spr).
- **Channel absence**: provisioned_lot objects minted on **2/1,620**
  unposted object-arm cells. `ind` lot-event presence: unposted
  0.053/0.067/0.117, posted 0.868/1.000/1.000;
  P(posted | ≥1 lot event on `ind`) ≈ 0.88/0.91/0.70.

**Implicated-titre review** (#989, `docs/ledger/NORO-IMPLICATED-TITRE-01.md`):
an implicated serving sits at p≈0.5–0.72 on the declared Hill vs
measured point-source attack rates 41–100%.

## 2. Shipped machinery (this image, all measured)

All three mechanism knobs are on main and **default-ON**; the design
crosses them explicitly rather than relying on defaults, so each arm's
semantics are pinned in `config_overrides` (which echo into run
parameters → the canary's first gate).

`transmission.common_source.titre_draw_mode` (#990, `56762131`):

- `"two_mode"` (shipped default): a fired `provisioned_lot` mint —
  every object mint **and every v1 `independent` lot event** — draws
  `lot_titre_implicated_gec_per_g` logU(1.5e2, 5e3) (the census band:
  Lowther 152 floor, Rexin 4,630 ceiling); a `background_stock` titre
  site (none modelled) would draw logU(1e1, 1e3).
- `"background"` (labelled baseline): the pre-change single-mode
  `lot_titre_gec_per_g` logU(1e1, 1e4) — one uniform consumed at the
  same stream position either way, so `"background"` reproduces the
  prior draw **verbatim** (titre values re-map under `two_mode`;
  declared, not a defect).

`transmission.common_source.lot_extent_mode` (#991, `f4c810df`):

- `"emergent"` (shipped default): object's serving span falls out of
  servings/take-share.
- `"declared"`: mints `extent_windows` int from the `lot_extent_windows`
  spec (shipped interval (3,12)), distributes `lot_servings` uniformly
  per window (per-window cap `servings // extent_windows`, leftover to
  the last window), new close reason `extent_met`. Config overrides
  express `fx_wide` (12,24) and `fx_narrow` (2,4) — the ENTRAIN-01
  §4.3 contract arms, landed here (§3.5).

`transmission.common_source.lot_state_redraw` (#991, `f4c810df`; pinned
by #992):

- `"per_object"` (shipped default): titre + take-share minted once at
  realize time.
- `"per_window"`: at each served window the object re-mints
  `lot_titre_gec_per_g` **through `_cs_titre_spec("provisioned_lot")`**
  — the implicated band under `two_mode`, the single-mode spec under
  `"background"` — and re-draws `item_take_share`, off the object's own
  SeedSequence partition (`self._cs_seed_seq.spawn(1)[0]`). The shared
  stream is untouched, so `per_object` stays bit-identical.

Mint machinery (unchanged since SCORE-01): object mode gates the voyage
on Bernoulli(`lot_object_probability` U(0.001, 0.02)) then a geometric
`extra_lot_probability` U(0.02, 0.25) tail;
`food_safety_posture` covariate (VSP per-ship inspection grade) scales
the draw. Independent mode (`ind`) gates on
`lot_event_probability` U(0.02, 0.15), picking one (zone, token, day)
per firing.

## 3. Frozen grid

### 3.1 Hulls

| hull | platform | agents | seeds |
|------|----------|-------:|-------|
| exp  | `expedition_cruise_450` | 450  | 8000–8999 |
| cls  | `classic_cruise_1900`   | 1910 | 8105–9104 |
| spr  | `spirit_cruise_3000`    | 3000 | 8105–9104 |

**mega excluded** — objects are never armed there (the mega manifest
carries no `common_source` block), and v1 saturates short of its wire;
a mega arm would measure nothing.

### 3.2 Arm table (the discriminating subset)

Every arm is a `transmission.common_source` override dict on the
FOOD-01/FOOD-02 transmission block; everything not listed is shipped.
Object-mode arms also carry the ship wiring
`lot_object_probability` (shipped U(0.001, 0.02) unless overridden).

| arm | `common_source` block | physical semantics |
|-----|-----------------------|--------------------|
| `off` | `{"mode": "off"}` | Whole-mechanism absence floor. Draws nothing anywhere → **bit-identical to every prior `off` cell**. |
| `ind` | `{lot/handler/diner_mode: "independent"}` | v1 labelled baseline **at this image**: shipped `two_mode` means its provisioned_lot events already draw the implicated band — the powered titre-sensitive channel. |
| `ind_bg` | `ind` + `titre_draw_mode: "background"` | Verbatim pre-#990 `ind` draw (same uniform, same stream position). **Two jobs**: the powered titre-margin read on the converting channel (`ind` mints ~50–120 lot events/cell) and the bit-identity bridge to ENTRAIN-01 `ind` cells at `dbbd5395`. |
| `ship` | `{lot/handler/diner_mode: "object", lot_object_probability: (0.001,0.02)}` | The **scored shipped configuration** at this image — objects + `two_mode` + `emergent`/`per_object` + shipped mint. Every margin arm modifies this; `ship` mints provisioned_lot objects on ~1%/voyage of cells. |
| `bg` | `ship` + `titre_draw_mode: "background"` | Titre axis on objects at shipped mint (thin by construction — the honest shipped-config check) **and** the bit-identity bridge to ENTRAIN-01 `ship` cells at `dbbd5395`. |
| `mint` | `ship` + `lot_object_probability: (0.02,0.15)` | Mint axis alone: the object-mode voyage gate re-expressed on the **v1 `lot_event_probability` interval verbatim** — `ind`-frequency channel presence on the object grammar. ~85–150 lot-minted voyages/cell expected. |
| `bg_mint` | `ship` + `titre_draw_mode: "background"` + mint | The `{titre} × {mint}` corner — the **powered** titre-margin read on objects (mint lifts the thin-cell problem off the titre comparison). |
| `redraw` | `ship` + `lot_state_redraw: "per_window"` | Cadence margin at shipped mint: persistent-state object vs lottery re-mint per served window — same implicated band (the #992-pinned contract), different temporal correlation structure. Thin posting read; per-object shape reads carry. |
| `redraw_mint` | `ship` + `per_window` + mint | `{cadence} × {mint}` at powered mint — **the conjunction cell**: cadence + mint + implicated denominator together. The campaign's headline cell for the D2/D3 recovery question. |
| `fx_wide` | `ship` + `lot_extent_mode: "declared"`, `lot_extent_windows: (12,24)` | Iso-dose extent leg — same servings spread wider. |
| `fx_narrow` | `ship` + `declared`, `(2,4)` | Iso-dose extent leg — same servings concentrated. |

### 3.3 What was pruned, and why each arm earns its cells

The naive crossing of {titre: two_mode/background} × {cadence:
per_object/per_window/declared-wide/declared-narrow} × {mint:
shipped/elevated} is 16 object-mode arms. The frozen subset is 8
object arms (`ship`, `bg`, `mint`, `bg_mint`, `redraw`, `redraw_mint`,
`fx_wide`, `fx_narrow`) + 3 baselines. Pruned cells:

- **`redraw@background`** — the {titre}×{cadence} corner at shipped
  mint is doubly thin (rare mint × thin conversion); its question (does
  cadence interact with denominator) is answered by the
  `redraw_mint − mint − (redraw − ship)` interaction at powered mint.
  Extension arm if the first-order margins move.
- **`fx@{background, elevated mint}`** — extent cells are the
  *iso-dose* leg (does shape-at-fixed-dose matter); both margins they
  would cross are already measured on their own axes. Extension if
  `fx_wide`/`fx_narrow` separates.
- **`extra_lot_probability` ladder** — second-order: the measured
  margin is *voyage-level channel presence* (≥1 lot event), not
  lot-count density; the shipped geometric tail stays.
- **handler/diner mint arms** — channel absence was measured on the
  provisioned_lot channel only; handler/diner objects mint abundantly.
  The mint axis is the lot gate only.
- **`mint` on `ind`** — `ind`'s voyage gate *is* the (0.02,0.15)
  interval already; the arm would be `ind` verbatim.

Each surviving arm earns its cells as the unique powered read on one
margin or one factorial corner (§3.2 column 3); the two `*_bg` arms
double as bit-identity bridges, without which there is no verified
link between this campaign's cells and the ENTRAIN-01 grid.

### 3.4 Seeds and pairing

Seed lists verbatim from SCORE-01/ENTRAIN-01 — exp 8000–8999,
cls/spr 8105–9104, **1,000 seeds per cell**, 3 hulls × 11 arms =
**33,000 voyages** + canary (§8). Same-seed pairing across arms
within the campaign is exact (identical seed list per hull per arm).

**Cross-campaign pairing, declared honestly.** `two_mode` is
default-ON since `56762131` — after ENTRAIN-01's eval image
(`dbbd5395`) — so the `ind`/`ship` baseline cells **re-run
in-campaign at the eval image**; nothing pairs voyage-for-voyage
with the `dbbd5395` grid on titre/dose fields (titre values re-map;
declared). The bit-identity claims that *do* hold, and are gated:

- `off` ≡ every prior `off` cell (draws nothing).
- `bg` ≡ ENTRAIN-01 `ship` at `dbbd5395` on every field, **iff** no
  other sibling default-ON mechanism lands between `dbbd5395` and the
  eval image — a declared condition re-checked at submit time (the
  campaign LEDGER records the image SHA it was checked against).
- `ind_bg` ≡ ENTRAIN-01 `ind` at `dbbd5395`, same condition.
- `ship` vs `bg` differ **only** on titre-realized fields (same
  uniforms consumed, different band mapping) — witness counts, object
  presence, event presence identical; verified in the readout.

### 3.5 Where the ENTRAIN-01 §4.3 arms went

ENTRAIN-01's extension rule said the `cs_extent` contract arms
(`fx_wide`/`fx_narrow`/`redraw`) would "append to that campaign as new
blocks on the same seed lists." They land **here** instead: the
pairing baseline for any cadence read must be the `two_mode` image —
running them on `dbbd5395` would confound cadence with the titre
denominator, the exact margin this campaign crosses. Declared; the
ENTRAIN-01 campaign keeps its 27,000-cell grid untouched.

### 3.6 Fixed coordinates (identical to FOOD-01/02, AGE-FOOD-01, SCORE-01, ENTRAIN-01)

`boarding_mechanism_rungs: ["shipped"]`;
`boarding_prevalence_points: [{passenger: 0.0325, crew: 0.0185}]`;
`never_symptomatic_fractions: [0.29]`; `epoch_durations: [288]`
(12 days); `dose_adjustments: [7.57]`;
`surveillance_strategies: ["syndromic_comp65"]`
(`quarantine_compliance 0.65` + compliance_by_class);
`pathogen_id: "norwalk_gi"` (bundle `active_profiles`, removes
`sars_cov2_resp`); `embarkation_date "2026-01-10"`;
`natural_history_clock "hours"`. The 7-entry shipped class mix
(`gen`-era fractions: passenger_general .50 / passenger_family .10 /
passenger_elderly .10 / crew_general .10 / crew_medical .05 /
crew_engineering .10 / crew_galley .05) is declared verbatim in every
tier's `ship_graph.agent_classes` so `agent_class_fractions` stamps
into run parameters — resolved config identical to the undeclared
mix, voyages bit-identical. Emit-complement wires unchanged: exp
≥10/≥5, cls ≥41/≥18, spr ≥63/≥27.

## 4. Axis A — the implicated titre denominator (two_mode)

What #990 changed physically: a provisioned_lot mint is, by
construction, conditional on the voyage carrying a contaminated lot —
it **is** the implicated denominator. The single-mode draw
logU(1e1, 1e4) minted mostly background-stock titres on implicated
objects; `two_mode` restricts to the measured implicated census band
logU(1.5e2, 5e3) — higher typical titre (~2.7× at median), lower tail
(above 5e3 removed). #989 measured an implicated *serving* at
p≈0.5–0.72 on the declared Hill; the review is in
`docs/ledger/NORO-IMPLICATED-TITRE-01.md`.

Frozen reads:

- **Titre margin on objects, shipped mint**: `ship` vs `bg` — thin
  (~10 minted-lot cells/hull expected); honesty check on the shipped
  configuration, not the powered read.
- **Titre margin on objects, powered**: `mint` vs `bg_mint` — the
  same comparison at ~85–150 lot-minted voyages/cell. This is the
  primary titre read.
- **Titre margin on the converting channel**: `ind` vs `ind_bg` —
  does re-banding `ind`'s lot events to the single-mode draw cost the
  conversion it had? Powered (ind mints ~50–120 events/cell,
  converts 0.7–0.9 measured).
- **Bit-identity bridges**: `bg` ≡ `dbbd5395` `ship`; `ind_bg` ≡
  `dbbd5395` `ind` (condition §3.4).

Prediction space declared, not fit: if the denominator is the missing
margin, `two_mode` arms sit above their `background` twins on
excursion→posting conversion and posted-AR position; if flat, the
titre re-banding is a null margin and cadence/mint carry the question.

## 5. Axis B — cadence dose shape (redraw + declared extent)

The measured shape defect: object events spread hundreds of servings
of **one minted state** (titre × take-share × strain minted once) over
1–4 shelf-life days, while `ind` events are one-day punctual deposits
and real implicated-lot exposures re-draw per service. Two cadence
variations, both config-expressible:

- **`per_window` re-mint** (`redraw`, `redraw_mint`): titre and
  take-share re-mint per served window off the object's own stream —
  the lottery vs persistent-state isolation. Under `two_mode` every
  re-mint lands in the implicated band (#992 pin), so the arm changes
  *correlation structure*, not the marginal band.
- **`declared` extent** (`fx_wide` (12,24), `fx_narrow` (2,4)):
  forced-extent draw at minted servings — the **iso-dose** leg: same
  total servings spread wider or narrower. Per-window cap +
  `extent_met` close are witness-visible.

Frozen reads:

- `ship` vs `redraw` — cadence at shipped mint (thin; per-object
  shape reads — window-titre variance, take-share variance, event
  temporal spread — are the primary output, posting secondary).
- `mint` vs `redraw_mint` — cadence at powered mint. The conjunction
  cell `redraw_mint` is where the hypothesis lives: cadence + mint +
  implicated denominator, vs `ind`'s signature.
- `ship` vs `fx_wide` vs `fx_narrow` — iso-dose extent direction.
  If spreading the same servings over more windows moves conversion
  toward `ind`, the defect is extent-at-fixed-dose; if `fx_narrow`
  moves it *away*, the direction is monotone in extent, not a
  threshold.

Interaction declared: `(redraw_mint − mint) − (redraw − ship)`
isolates cadence×mint; there is no powered {titre}×{cadence} cell
(pruned, §3.3).

## 6. Axis C — mint-rate (channel absence)

The measured co-constraint: provisioned_lot objects minted on
**2/1,620** unposted object-arm cells while `ind` lot events appear on
5–12% of unposted and 87–100% of posted cells. Whatever the other two
axes buy, the shipped gate U(0.001, 0.02) rarely lets the channel
fire. `mint`/`bg_mint`/`redraw_mint` set
`lot_object_probability = (0.02, 0.15)` — the v1 `lot_event_probability`
interval **re-expressed verbatim on the object grammar**: `ind`-frequency
channel presence without touching the mechanism shape.

Frozen reads:

- `ship` vs `mint` — mint margin on the shipped shape.
- `bg` vs `bg_mint` — mint margin on the single-mode draw.
- `redraw` vs `redraw_mint` — mint margin on the re-mint shape.
- Minted-lot census: `lot_event_presence`/object-presence fraction per
  cell must track the drawn gate (integrity gate, §7.4) — the audit
  tools from #988 rerun on these zips.

What `mint` is **not**: not a fit to `ind`'s measured presence
(0.053–0.117 is the *realized* fraction, the interval is the v1
declared gate), and not an extra_lot change (shipped geometric tail
stays).

## 7. Scored criteria — frozen before any cell runs

### 7.1 Admissibility (the D-criteria)

- **D1 — posting marginal**: each object arm's posting marginal vs the
  in-campaign `off` floor, per hull, floor-aware; reference band
  0.4–0.9% lifted posting. `off` floor re-measured at the eval image
  (last measure: exp 1.0%, cls 0.0%, spr 0.1% at `dbbd5395`).
- **D2 — posted-AR signature**: pooled posted-pax-AR median ≥0.04 on
  object arms, per hull; the pooled-median rule is the SCORE-01 rule —
  thin cells pool within an arm, they do not vote individually.
- **D3 — excursion→posting conversion**: object-arm conversion vs
  in-campaign `ind` per hull (`ind` re-measures its 14.3/4.4/1.7%
  baseline at this image); the read is the ratio, not an absolute —
  `ind` is the denominator.
- **D4 — burst48 discriminator**: excursion cells still read as
  bursts (cs-excursion burst48 vs rest separation on exp, the
  measured 0.564-vs-0.400 direction); postings on object arms must
  not collapse to the rest rate.

An arm is admissible when its cells pass the integrity gates (§7.4)
and its read is reportable under the thin-cell rule (§7.5); a margin
is *recovered* when the powered read crosses its frozen threshold —
not by direction alone.

### 7.2 Margin map (which contrast answers which question)

| margin | powered contrast | thin contrast | read |
|--------|------------------|---------------|------|
| titre denominator | `mint − bg_mint`; `ind − ind_bg` | `ship − bg` | D3 conversion, D2 position, dose-position shift |
| cadence (re-mint) | `redraw_mint − mint` | `ship − redraw` | same + per-window titre/take-share variance |
| cadence (extent, iso-dose) | — | `fx_wide − ship − fx_narrow` | same + extent-windows response |
| mint presence | `mint − ship`; `redraw_mint − redraw`; `bg_mint − bg` | — | channel-presence census → posting/AR |
| conjunction | `redraw_mint` vs `ind` | — | does the three-axis combination recover the `ind` signature |

### 7.3 Must-not-move invariants

- `off` cells: zero object/event witness rows, zero cs postings —
  bit-identical to prior `off` (stream check).
- `ind`/`ind_bg` cells: zero `object_id` witness rows (v1 events only);
  `ship`-family cells: witness `object_id` present iff armed.
- Non-cs routes (contact/droplet/fomite/HVAC dose, non-cs postings):
  paired-seed equal across all arms — any divergence is a defect, not
  a mechanism effect.
- Median (non-excursion) AR vs `off`: flat — the mechanism must not
  raise the background.
- `ship` vs `bg`: identical on every non-titre-realized field
  (uniforms conserved).

### 7.4 New-mechanism integrity gates (frozen)

1. **Witness echo**: object witness rows carry `extent_mode`,
   `redraw`, `extent_windows`, `window_serving_cap`; run parameters
   echo `titre_draw_mode`, `lot_extent_mode`, `lot_state_redraw`,
   `lot_object_probability` exactly as overridden.
2. **Re-mint band**: under `two_mode`, every per-window re-minted
   `lot_titre_gec_per_g` on lot pans lands inside [1.5e2, 5e3] —
   a value outside says re-mints bypass the resolver (the #992 pin is
   the unit-level version of this gate; this is the campaign-level
   one).
3. **Declared-extent bookkeeping**: `extent_windows` drawn inside the
   overridden interval; per-window servings ≤ `window_serving_cap`
   except the last window (leftover sink); `extent_met` close reason
   appears **only** under `lot_extent_mode: "declared"` and only on
   extent-lived objects.
4. **Per-window re-mint presence**: `redraw`/`redraw_mint` multi-window
   objects show varying `lot_titre_gec_per_g` and `item_take_share`
   across pan rows sharing one `object_id` (a constant titre across
   windows means the re-mint didn't fire); `per_object` arms show
   exactly one titre per `object_id`.
5. **Bit-identity bridges**: `bg` vs `dbbd5395` `ship`, `ind_bg` vs
   `dbbd5395` `ind`, `off` vs any prior `off` — identical zips modulo
   declared field-level exceptions (none expected; condition §3.4
   re-checked at submit).
6. **Mint echo**: minted-lot counts per cell track the drawn gate —
   `mint`-family cells show lot-object presence ≈ the (0.02,0.15)
   draw × eligibility (expected ~8.5%+ vs ~1% shipped); a `mint` cell
   at shipped-mint rates says the override didn't reach the engine.

### 7.5 Thin-cell handling

Declared before cells: minted-lot voyages are ~1%/cell at shipped
mint (~10/hull expected), ~8.5%+/cell on `mint` arms. Thin arms
(`ship`, `bg`, `redraw`, `fx_wide`, `fx_narrow`) report pooled reads
and per-object shape reads; **powered conversion/AR reads come only
from `mint`-family cells and `ind`-family cells**. No thin cell's
point estimate is quoted as a recovery/failure verdict; a thin arm
contributes its cells to the pooled D2 median and its objects to the
per-object shape table.

## 8. Canary and stop order

Local smoke first (on the eval image, `fl_exp_12d_scr_redraw_mint`
index 0): 3-member zip contract (summary.json, growth_census.json.gz,
rss_samples.json) + run-parameter echo of the override block +
`redraw: "per_window"` on any minted lot witness. Then canary —
**all on exp, then STOP and report**:

| block | seeds | hard gates |
|-------|------:|------------|
| `canary_exp_redraw_mint` | 8000–8047 (48) | mint echo ≥1 provisioned_lot object (E≈4 at the (0.02,0.15) gate; P(0)≈0.014 — a zero-lot canary fails, declared); `redraw:"per_window"` + `extent_mode:"emergent"` on object rows; every re-minted titre inside the implicated band (gate 2); ≥1 multi-window object with varying titre (gate 4, expected — the canary that proves the integration end-to-end) |
| `canary_exp_bg_mint` | 8000–8023 (24) | `titre_draw_mode:"background"` echo; ≥1 lot object (E≈2, P(0)≈0.13 — zero-lot fails and reports: the mint override is the suspect) |
| `canary_exp_fx_wide` | 8000–8023 (24) | `lot_extent_mode:"declared"` + `lot_extent_windows (12,24)` echoes (hard); **conditional**: on any minted lot, witness `extent_mode`, `extent_windows∈(12,24)`, cap bookkeeping, `extent_met` only where earned — a zero-lot canary does **not** fail at shipped mint (P(0)≈0.78; the wave cells carry the object gate, ~10/hull) |
| `canary_exp_ship` | 8000–8007 (8) | shipped-config witness on the campaign image: `common_source` block echoes the ship dict; `titre_draw_mode` resolves `two_mode` (absent → default); handler/diner objects present |
| `canary_exp_off` | 8000–8003 (4) | zero-witness: no object rows, no lot events, stream check vs prior `off` |

Canary = 108 cells. On green: STOP, report the canary readout. The
user gates every wave after. Wave order after a go: (1) exp all 11
arms; (2) cls + spr factorial core (`ship`, `mint`, `redraw_mint`,
`bg_mint`, `ind_bg`, `ind`, `off`, `bg`); (3) cls + spr remainder
(`redraw`, `fx_wide`, `fx_narrow`).

## 9. AWS wiring (frozen, nothing submitted by this PR)

`queue: picard-campaign-queue`; `image_tag: noro-food-shapes01`;
worker `tools/noro_diag/growth_chain_census.py`; resources 1 vCPU /
4096 MB / shm 512; `s3_prefix: campaign/noro_food_shapes_01/`;
`epochs: 288`; submission only through `scripts/campaign submit
noro/food_shapes_01` (jobdef rendered from
`deploy/aws/campaign_jobdef.json`, literal `--container-overrides`
argv). The campaign LEDGER records the image digest + jobdef revision
at submit time — never a bare tag.

## 10. Report immediately if

- An arm in §3.2 cannot be expressed in the shipped config schema —
  **none today** (all 11 arms are pure `common_source` overrides;
  verified against `engines/transmission_core.py` at `36ce23c8`).
- A sibling default-ON mechanism merges between freeze and submit —
  voids the §3.4 bit-identity bridges; re-declare before submitting.
- Canary shows a re-minted titre outside the resolved band, an
  `extent_met` outside `declared`, a `mint` cell at shipped mint
  rates, or a non-titre-realized divergence between `ship` and `bg`.
- `off` is not bit-identical to prior `off` cells — that is an engine
  drift flag on the shared stream, above any margin question.
- The `mint` census shows the measured 2/1,620 channel absence was an
  under-count of a different defect (e.g. objects mint but never
  serve) — changes what the mint axis is measuring.

## 11. Readout plan

Primary: `tools/noro_diag/outbreak_anchor_readout.py` (D1/D2 tables —
posting marginals vs `off` floor, posted-pax-AR medians).
Conversion: `tools/noro_diag/early_event_scan.py` +
`early_event_report.py` (D3 — censused shared-dose excursions →
posting, per channel). Burst: burst48 excursion-vs-rest on posted and
excursion sets (D4). Shape/dose: `tools/noro_diag/entrain_01_dose_audit.py`
+ `entrain_01_dose_audit_analysis.py` (delivered-dose Hill position,
minted-lot census, channel-presence fractions — the #988 reads
re-run on these zips). Integrity: witness-field echoes, re-mint band
audit, extent bookkeeping, and the three bit-identity bridges from
§7.4 gate 5 (same-seed zip compares vs `dbbd5395` cells; ship-fetched
from the ENTRAIN-01 S3 prefix). Posting-conditional reads pool within
an arm per §7.5.

Deliverable readout doc: `docs/norovirus/noro_food_shapes_01_readout.md`
+ campaign LEDGER findings section + open-ledger status update; each
margin reported as measured/inferred/hypothesis.

## 12. Exclusions (explicit non-goals)

No engine code changes; no image builds; no array submissions; no
mega hull; no `extra_lot_probability`, handler/diner-mint, or
redraw×background cells (pruned, §3.3); no fitting to the 0.04 AR
edge, the 0.4–0.9% posting band, or any `ind` signature; no absolute
dose figures in the readout while the dose ledger is withdrawn —
Hill positions and ratios only.
