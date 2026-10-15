# NORO-MINT-RATE-01 — Frozen evaluation design

**Status: frozen — declared before any cell ran.** Rung ladder, arm
set, admissibility criteria, integrity gates, canary spec and readout
plan below are the contract. Any post-readout change goes in a ledger
entry that names what changed and why; it does not retro-edit this
file.

**Branch:** off `origin/main` at `9039e234` (merge of #998, the
NORO-FOOD-SHAPES-01 final readout). Nothing between `45b2bf18` (the
SHAPES-01 eval image) and this head touches `engines/`, `data/` or any
default-ON mechanism — the §3.4 bridge condition holds at freeze and
is re-checked at submit.

## 0. The question

Channel presence — the provisioned-lot voyage gate
`lot_object_probability` — is the measured operative margin on the
object grammar (SHAPES-01, §1): at the powered gate U(0.02, 0.15) the
`mint` family posts at `ind` level on every hull and carries the full
signature (excursion conversion ≥`ind`, posted bursts above rest, D2
0.0411 on exp), while the shipped gate U(0.001, 0.02) posts in the D1
band on exp but mints so rarely (~6 voyages/1,000) that nothing else
is resolvable. **This campaign locates the gate value where D1 lands
in-band and measures whether the signature survives at that rate** —
the bracket between the vacuous shipped bottom and the over-posting
powered top. One axis only: cadence and extent are measured nulls and
ship their defaults; `two_mode` stays shipped-on.

## 1. Settled inputs (measured context, do not re-derive)

All numbers from the merged SHAPES-01 readouts at `45b2bf18`
([noro_food_shapes_01_readout.md](noro_food_shapes_01_readout.md),
[noro_food_shapes_01_wave1_readout.md](noro_food_shapes_01_wave1_readout.md)),
n=1,000 seeds/arm/hull:

- **D1** (posting marginal vs in-campaign `off`, band 0.4–0.9 pp):
  exp `ship` +0.60 (in band, thin), `mint` +7.60, `bg_mint` +7.20,
  `ind` +7.20 (over); cls `ship` +0.20 under, `mint` +4.90 over,
  `ind` +4.80 over; spr `ship` +0.10 under, `mint` +3.00 over,
  `ind` +2.60 over. `off` floors: exp 1.0%, cls 0.0%, spr 0.1%.
- **D2** (posted pax-AR pooled med): exp `mint` 0.0411 — the only arm
  over the 0.04 edge, `ind` 0.0380 under; cls `mint` 0.0389 tops the
  object arms and `ind` itself sits at 0.0352; spr `ind` tops the
  table at 0.0310 vs `mint` 0.0243. **`ind` misses the 0.04 edge on
  both big hulls** — the absolute edge is exp-calibrated and does not
  carry across hulls.
- **D3** (excursion→posting conversion vs `ind`): mint family at/above
  `ind` everywhere — exp 92.7% vs 77.7% (1.19×), cls 51.0% vs 50.0%
  (1.02×), spr 28.0% vs 26.3% (1.07×); thin arms collapse to
  0.10–0.20× on cls/spr.
- **D4** (burst48): posted mint cells carry the burst on every hull
  (0.708/0.454/0.326 vs rest ~0.41/0.29/0.27); the
  excursion-vs-rest half of D4 is unreadable on spr — gone on `ind`
  itself (0.257 vs 0.271).
- **Mint census, verbatim** (`provisioned_lot` objects / voyages
  minting, per 1,000 cells): exp `ship` 6 cells/7 objects, `mint`
  82/93, `bg_mint` 82/93; cls `ship` 6/7, `mint` 84/96, `bg_mint`
  84/96; spr identical to cls (the seed-paired mint stream is
  hull-invariant by construction).
- **P(post | ≥1 lot-minted voyage), powered measures**: exp ≈0.93
  ((86 posted − 10 floor)/82 minted), cls ≈0.58 (49/84, floor 0),
  spr ≈0.36 ((31−1)/84). Thin-arm point estimates (ship: ~1.0 / ~0.33
  / ~0.2 on n=6 minted) are consistent under noise but thin-flagged.
- **Hull compression ≈1.6–2× per step** on every absolute margin
  (`ind` posting 8.2→4.8→2.7%, conversion 77.7→50.0→26.3%) — rung
  expectations are per-hull, never a single band projection.
- Cadence (`lot_state_redraw: "per_window"`) and extent
  (`lot_extent_mode: "declared"`) are **measured nulls** on every
  D-metric (`mint − redraw_mint` Δposted +0.00 pp). They ship their
  defaults (`per_object`, `emergent`) and are not crossed here.
- `titre_draw_mode: "two_mode"` is shipped default-ON (implicated
  band logU(1.5e2, 5e3) on every provisioned_lot mint). It stays on
  every arm; the titre margin is settled (material on the v1 path,
  modest on the object path) and is not re-crossed.
- Dose ledger withdrawn: positions-on-curve and ratios only, **no
  absolute dose figures** anywhere in this campaign's readout.

## 2. Shipped machinery under the axis (measured code paths)

The mint mechanism at `engines/transmission_core.py` @ `9039e234`:

- **Voyage gate**: `_cs_plan_objects` (≈:12538) — one Bernoulli on the
  per-voyage drawn `lot_object_probability` per armed pathogen. The
  rate is drawn once per voyage in `_cs_draw_voyage_rates` (≈:3491)
  off the dedicated `_cs_rng` stream (`_COMMON_SOURCE_STREAM_KEY`),
  spec resolved by `_cs_spec_range` — a scalar spec or a `[lo, hi]`
  interval are both legal overrides (`_cs_draw` ≈:3551; `lo == hi`
  returns the value and **consumes no stream element** — a declared
  stream-layout note, §3.4).
- **Multiplicity tail**: conditional on the gate, K = 1 + extra, each
  extra object an independent Bernoulli on the per-voyage drawn
  `extra_lot_probability` ~ U(0.02, 0.25) — a geometric tail
  (`P(K ≥ k+1 | K ≥ k) = e`). E[K | ≥1] = E[1/(1−e)] =
  ln(0.98/0.75)/0.23 ≈ **1.163**. `extra_lot` therefore enters
  E[objects] only as a constant multiplier; the scored margin is
  *voyage-level channel presence*, so the tail stays shipped on every
  arm (the SHAPES-01 §3.3 pruning — object density is second-order —
  is carried here).
- **Posture decoupling**: the lot gate is `lot_factor`-free under the
  shipped config — `lot_posture_coupling` defaults `false` (≈:3408),
  so `food_safety_posture` scales only handler/diner span seeding,
  never the lot gate. E[presence] per rung is posture-free and
  platform-independent — confirmed measured: cls and spr realized
  identical mint sets on the shared seed list.
- **Object content**: a realized object mints one contamination state
  — item line, start window, servings, titre (implicated band under
  `two_mode`), take-share, strain — once, shared by every pan it emits
  (`_cs_realize_lot_object` ≈:12585). A minted object drawn to a
  zone/(day) cell with no service never enters the witness — realized
  objects only are counted.
- **Posting is voyage-presence-driven, not object-count-driven**:
  minted voyages posted ~93% on exp regardless of whether the voyage
  held 1 or 2 objects — the measured P(post | minted) is the
  rate-to-posting transfer this campaign brackets.

## 3. Frozen grid

### 3.1 Hulls

| hull | platform | agents | seeds |
|------|----------|-------:|-------|
| exp  | `expedition_cruise_450` | 450  | 8000–8999 |
| cls  | `classic_cruise_1900`   | 1910 | 8105–9104 |
| spr  | `spirit_cruise_3000`    | 3000 | 8105–9104 |

**mega excluded** — objects are never armed there (same rationale as
SHAPES-01 §3.1).

### 3.2 Rung table (the axis, 9 arms)

Every arm is a `transmission.common_source` override dict on the
FOOD-01/FOOD-02 transmission block; everything not listed is shipped
(`two_mode`, `emergent`, `per_object`, `extra_lot_probability`
U(0.02, 0.25), posture coupling off). Scalar rungs set
`lot_object_probability` to a **point value** — the per-voyage gate is
exactly p, so E[presence] is exact rather than interval-midpoint
(justified in §4: the margin is linear in E[p]; interval dispersion
adds no information to this question).

| arm | `lot_object_probability` | E[minted voyages]/1,000 | E[objects]/1,000 (×1.163) | role |
|-----|--------------------------|------------------------:|--------------------------:|------|
| `off` | — (`mode: "off"`) | 0 | 0 | mechanism-absence floor; bit-identical to every prior `off` |
| `ind` | — (v1 `lot_event_probability` U(0.02,0.15)) | — (v1 events) | — | the signature denominator per hull |
| `ship` | U(0.001, 0.02) — shipped | 10.5 | 12.2 | bracket bottom anchor; SHAPES-01 `ship` bridge |
| `p005` | **0.005** | 5.0 | 5.8 | rung — below-band probe, exp low edge |
| `p008` | **0.008** | 8.0 | 9.3 | rung — exp/cls band candidate |
| `p012` | **0.012** | 12.0 | 14.0 | rung — cls/spr band candidate |
| `p017` | **0.017** | 17.0 | 19.8 | rung — spr band centre |
| `p024` | **0.024** | 24.0 | 27.9 | rung — spr band top |
| `mint` | U(0.02, 0.15) — powered | 85.0 | 98.9 | bracket top anchor; powered signature carrier; SHAPES-01 `mint` bridge |

Scalar rungs are declared arm configuration, not physical constants —
same class as SHAPES-01's (0.02,0.15) override; no
provenance-register rows are added (the register carries shipped
constants; arm-local sweep points cite this design).

### 3.3 Per-rung margin expectations (from the measured anchors)

Expected posting marginal (pp, marginal = E[presence] ×
P(post|minted) × 100, P per hull from §1):

| arm | exp (P≈0.93) | cls (P≈0.58) | spr (P≈0.36) |
|-----|--------------|--------------|--------------|
| `ship` | ~0.98 (measured +0.60 at realized 0.6% presence) | ~0.61 (measured +0.20) | ~0.38 (measured +0.10) |
| `p005` | 0.47 — in band (low edge) | 0.29 — under | 0.18 — under |
| `p008` | 0.74 — in band | 0.46 — in band | 0.29 — under |
| `p012` | 1.12 — over | 0.70 — in band | 0.43 — in band (low edge) |
| `p017` | 1.58 — over | 0.99 — over (edge) | 0.61 — in band |
| `p024` | 2.23 — over | 1.39 — over | 0.86 — in band (top edge) |
| `mint` | ~7.9 — over (measured +7.60) | ~4.9 — over (measured +4.90) | ~3.1 — over (measured +3.00) |

Reads declared before cells: **the D1-in-band window is per-hull** —
≈[0.004, 0.010] on exp, ≈[0.007, 0.015] on cls, ≈[0.011, 0.025] on
spr at the measured P's. No single gate lands in-band on all three
hulls; `p012` is the closest (in on cls and spr, just over on exp).
That is the expected finding, not a defect — hull compression is
measured. The thin-arm P estimates widen these windows on the low
side (if ship's ~0.33 on cls is the true low-rate P rather than 0.58,
the cls band shifts right toward `p017`/`p024`); the ladder brackets
that uncertainty either way.

### 3.4 Seeds, pairing and the stream-layout declaration

Seed lists verbatim from SCORE-01/ENTRAIN-01/SHAPES-01 — exp
8000–8999, cls/spr 8105–9104, **1,000 seeds per cell**. 9 arms ×
3 hulls = **27,000 voyages** + canary (§8). Same-seed pairing across
arms is exact per hull.

**Stream layout, declared.** A scalar `lot_object_probability`
consumes zero uniforms in `_cs_draw_voyage_rates` (the `lo == hi`
early return), so the five scalar rungs share one stream layout
(gate uniform at the same position per seed) while the interval arms
`ship`/`mint` — and SHAPES-01's interval cells — draw the gate one
position later. Consequences, declared:

- **Nested mint sets (integrity gate §7.4-3)**: across the scalar
  ladder the gate compares the *same* uniform per seed — a voyage
  minting at `p005` mints at every higher scalar rung; minted sets
  must be perfectly nested p005 ⊆ p008 ⊆ p012 ⊆ p017 ⊆ p024 per seed
  per hull. Non-nesting says the draw sequence changed.
- Scalar arms are **not** mint-decision-paired with `ship`/`mint` and
  pair with them only at the voyage-outcome level (same seed, same
  coordinates) — their handler/diner rate draws shift one position vs
  the interval arms, so non-lot witness interiors differ at shared
  seeds. Declared, not a defect.
- `ship`, `mint`, `ind`, `off` carry **verbatim SHAPES-01 arm dicts**
  and identical seeds: at an eval image with no mechanism delta vs
  `45b2bf18` they are expected **bit-identical** to the SHAPES-01
  cells — the minted-set census (6/82/84 per arm) reproduces
  verbatim. Condition re-checked at submit (holds at freeze — only
  docs/tools merges since `45b2bf18`); if a sibling default-ON
  mechanism lands, the bridge claim degrades to the minted-voyage
  parity check and is re-declared in the LEDGER at submit.

### 3.5 What was pruned, and why each arm earns its cells

- **`bg`/`ind_bg`/`bg_mint`** — the titre margin is measured
  (material on v1, modest on objects); `two_mode` is the shipped
  physics on every arm. Not re-crossed.
- **`redraw`/`redraw_mint`/`fx_*`** — cadence and extent are measured
  nulls; shipped defaults stand.
- **`extra_lot_probability` ladder** — enters E[objects] only as the
  ×1.163 multiplicity factor (§2); voyage presence is the margin.
- **handler/diner mint arms** — channel absence was measured on the
  provisioned_lot channel only.
- **midpoint-of-shipped rung (~0.0105)** — the shipped interval's
  midpoint sits inside the ladder's coverage (p008/p012 bracket it)
  and `ship` itself anchors the bottom.
- **mega** — objects never armed.

Each surviving arm is either a rung on the named axis, a measured
bracket endpoint re-run as the in-campaign anchor, or a baseline the
gates divide against (`off` floor, `ind` signature denominator).

### 3.6 Fixed coordinates

Identical to FOOD-01/02, AGE-FOOD-01, SCORE-01, ENTRAIN-01 and
SHAPES-01: `boarding_mechanism_rungs: ["shipped"]`;
`boarding_prevalence_points: [{passenger: 0.0325, crew: 0.0185}]`;
`never_symptomatic_fractions: [0.29]`; `epoch_durations: [288]`;
`dose_adjustments: [7.57]`; `surveillance_strategies:
["syndromic_comp65"]`; `pathogen_id: "norwalk_gi"` (bundle
`active_profiles`, removes `sars_cov2_resp`); `embarkation_date
"2026-01-10"`; `natural_history_clock "hours"`; the shipped 7-entry
class mix declared verbatim so `agent_class_fractions` stamps into run
parameters (resolved config identical to the undeclared mix, voyages
bit-identical). Emit-complement wires unchanged: exp ≥10/≥5, cls
≥41/≥18, spr ≥63/≥27.

## 4. The E[objects] curve — stated, not guessed

From the shipped draw mechanics (§2), for gate value/interval-
midpoint `p` on any hull:

```
E[minted voyages / 1,000] = 1,000 · p            (posture-free gate)
E[objects / 1,000]        = 1,000 · p · 1.163    (geometric tail, e ~ U(0.02,0.25))
E[posting marginal pp]    = 100 · p · P(post | ≥1 lot minted)   per hull
```

The relation is **linear in the gate midpoint**: p is drawn
independently of everything downstream (the object's realized state —
titre, servings, take-share — does not see p), so interval dispersion
adds variance structure but no information to the margin — the reason
the rungs are scalar points. `extra_lot_probability` contributes only
the ×1.163 object multiplicity. The campaign's discriminating output
is the realized posting-vs-presence slope per hull — i.e. whether
P(post|minted) is rate-independent (linearity holds → the band window
is where the table says) or rate-dependent (posted share rises with
rate → over-posting is a selection effect of powered gates, and the
in-band point shifts).

## 5. Scored criteria — frozen before any cell runs

### 5.1 Admissibility (the D-criteria, adapted to the SHAPES-01 measurement)

- **D1 — posting marginal**: each arm's posting marginal vs the
  in-campaign `off` floor, per hull, Wilson 95% on the arm rate;
  reference band 0.4–0.9 pp lifted posting. A rung is *in-band* on a
  hull when its marginal lands in the band there — verdicts are
  per-hull (SHAPES-01 measured the band as exp-calibrated; `ind`
  itself overshoots it on every hull).
- **D2 — posted-AR signature**: pooled posted-pax-AR median per rung
  per hull, **recorded against the in-campaign `ind` median on the
  same hull** — the verdict reads mint-vs-`ind`, not mint-vs-0.04
  alone, because `ind` itself misses the 0.04 edge on cls (0.0352)
  and spr (0.0310). The 0.04 edge is still printed per hull for
  reference; on exp the edge is also a live criterion (SHAPES-01: only
  `mint` cleared it, 0.0411). Signature-survives verdict on a hull:
  the pooled in-band rungs' posted-AR median ≥ the in-campaign `ind`
  median on that hull.
- **D3 — excursion→posting conversion**: object-arm conversion vs
  in-campaign `ind` per hull; the read is the ratio — powered on
  `mint`/`ind`, thin on the scalar rungs, and pooled across a hull's
  in-band rungs for the in-band signature read.
- **D4 — burst48 discriminator**: excursion vs rest separation where
  readable (exp, cls — declared unreadable on spr, measured gone on
  `ind` itself: 0.257 vs 0.271); posted cells must not collapse to
  the rest rate (on spr that is the only D4 half that can read).

A rung is admissible when its cells pass the integrity gates (§5.4)
and its read is reportable under the vacuity rule (§5.5); the
campaign's question is answered when the per-hull in-band rung set and
the pooled in-band signature are both read.

### 5.2 Margin map

| margin | powered contrast | thin/pooled contrast | read |
|--------|------------------|----------------------|------|
| mint rate ↔ posting | each rung's marginal vs `off`, per hull | — | D1 — the ladder IS the margin |
| signature at rate | `mint` vs `ind` | pooled in-band rungs vs `ind` | D2/D3/D4 at in-band rate |
| presence census | every object arm vs §4 curve | — | gate realized? (§5.4-4) |
| nested mint sets | scalar rungs pairwise per seed | — | stream layout (§5.4-3) |
| anchors vs SHAPES-01 | `ship`/`mint`/`ind`/`off` vs `45b2bf18` cells | — | engine drift + bracket re-measure |

### 5.3 Must-not-move invariants

- `off` cells: zero object/event witness rows, zero cs postings —
  bit-identical to prior `off` (stream check).
- `ind` cells: zero `object_id` witness rows (v1 events only);
  object-mode arms mint `object_id` rows iff armed.
- Non-cs routes (contact/droplet/fomite/HVAC dose, non-cs postings):
  paired-seed equal across all arms — divergence is a defect.
- Median (non-excursion) AR vs `off`: flat — the gate must not raise
  the background.
- Anchor arms vs SHAPES-01 cells at unchanged engine: bit-identical
  (condition §3.4).

### 5.4 Integrity gates (frozen)

1. **Witness echo**: run parameters echo `parameters.transmission.
   common_source` verbatim per arm — scalar rungs echo the scalar
   value exactly (`"lot_object_probability": 0.012`, not an
   interval), `ship`/`mint` echo the frozen intervals.
2. **Titre band**: every `two_mode` titre draw on every minted
   `provisioned_lot` inside [1.5e2, 5e3]; every object `per_object`
   (exactly one titre per `object_id`) — no redraw/declared rows
   anywhere (those arms don't exist here).
3. **Nested mint sets**: across the scalar ladder per seed per hull,
   minted voyage sets are nested in gate order (§3.4); a voyage
   minting at a lower rung but not a higher one is a stream-layout
   defect.
4. **Presence census tracks the gate**: realized minted-voyage
   fraction per rung lands within binomial tolerance of E[presence]
   (§3.2); realized objects track p × 1.163. A rung minting at
   shipped or powered-anchor rates says the override didn't reach the
   engine.
5. **Bit-identity bridges**: `off` vs any prior `off`; `ship`/`mint`/
   `ind` vs the SHAPES-01 cells at `45b2bf18` on the same seed list —
   bit-identical under the §3.4 condition, minted-voyage parity and
   downstream-only diffs otherwise.
6. **Zero-lot bookkeeping on thin rungs**: a zero-mint rung cell is
   within expectation at low p (P(0 minted) per 1,000 ≈ (1−p)^1000 —
   printed per rung in the readout) and is not a failure; the failure
   is a rung whose *aggregate* presence contradicts its gate.

### 5.5 Vacuity rule

Declared before cells: rungs with **<20 realized minted-lot voyages
per hull** report the presence census and the voyage-level posting
marginal only — their per-rung conversion/AR/burst reads are
thin-flagged and never quoted as verdicts. Powered signature reads
come from `mint`/`ind` and from the **in-band posted pool** — posted
cells pooled across a hull's in-band rungs (same mechanism, same
channel; the in-band rate does not change what a posted object is).
Expected thin set per §3.2: `p005` (E≈5), `p008` (E≈8), `ship`
(E≈10.5 — measured 6), `p012` (E≈12); `p017`/`p024` are powered
enough for per-rung census reads (E≈17–24 minted).

## 6. What would make the campaign FAIL-informative

Declared before cells:

- **No rung lands D1-in-band on a hull** — posting marginal tracks
  floor + powered-anchor level with nothing between → presence and
  posting are decoupled at voyage level → the axis is wrong; the next
  margin is per-object posting probability, not the gate.
- **Rung lands in-band but the pooled signature collapses** — in-band
  postings read at thin-arm level (posted-AR ≪ `ind`, no burst
  separation, conversion ≪ `ind`) → the powered-mint signature was a
  high-presence selection artifact, not a channel property → next
  axis is per-object virulence/dose shape.
- **P(post|minted) measured strongly rate-dependent** — the §4
  linearity check fails (e.g. low rungs convert minted voyages ≈0)
  → the posting–presence map is not the measured slope → re-bracket
  before any readout verdict.
- **Anchor arms do not reproduce the SHAPES-01 census** — `mint`
  minted-set parity fails at an unchanged engine → engine drift on
  the shared stream, above any margin question.

## 7. Canary and stop order

Local smoke first (on the eval image, `fl_exp_12d_scr_p012` index 0):
3-member zip contract (summary.json, growth_census.json.gz,
rss_samples.json) + run-parameter echo of the scalar override
(`"lot_object_probability": 0.012`) + object-mode echo. Then canary —
**all on exp, then STOP and report**:

| block | seeds | cells | hard gates |
|-------|-------|------:|------------|
| `canary_exp_mint` | 8000–8047 | 48 | ≥1 `provisioned_lot` (E≈4.1 objects at midpoint 0.085; P(0)≈0.014 — a zero-lot canary fails, declared); interval echo `[0.02,0.15]`; every object titre inside the implicated band; `per_object` single titre per `object_id` |
| `canary_exp_p024` | 8000–8023 | 24 | scalar echo `0.024` verbatim; conditional: any minted object's titre in band (E≈0.7 objects, P(0)≈0.50 — zero-lot does NOT fail, declared; the wave cells carry the census gate) |
| `canary_exp_p005` | 8000–8023 | 24 | scalar echo `0.005` verbatim; conditional object check (E≈0.14, P(0)≈0.87 — declared non-failing) |
| `canary_exp_ind` | 8000–8007 | 8 | independent-modes echo; v1 rows `object_id: null`; no object mint |
| `canary_exp_ship` | 8000–8007 | 8 | shipped block echo (object modes + `[0.001,0.02]`); `titre_draw_mode` resolves `two_mode` (absent → default); handler/diner objects present |
| `canary_exp_off` | 8000–8003 | 4 | zero-witness: no objects, no events, `dose_credited` 0.0; bit-identical to prior `off` |

Canary = 116 cells. On green: STOP, report the canary readout. The
user gates every wave after. Wave order after a go: (1) exp, all 9
arms (9,000 cells — `fl_exp_12d_scr_mint` first as the probe array:
armed echo + powered object gate on the new campaign); (2) cls + spr,
all 9 arms (18,000 cells).

## 8. AWS wiring (frozen, nothing submitted by this PR)

`queue: picard-campaign-queue`; `image_tag: noro-mint-rate01`; worker
`tools/noro_diag/growth_chain_census.py`; resources 1 vCPU / 4096 MB /
shm 512; `s3_prefix: campaign/noro_mint_rate_01/`; `epochs: 288`;
submission only through `scripts/campaign submit noro/mint_rate_01`
(jobdef rendered from `deploy/aws/campaign_jobdef.json`, literal
`--container-overrides` argv). The campaign LEDGER records the image
digest + jobdef revision at submit time — never a bare tag.

## 9. Report immediately if

- The shipped `lot_object_probability` semantics differ from §2
  (e.g. per-object rather than per-voyage gating, posture coupling
  armed, or `extra_lot_probability` dominating the E[objects] curve)
  — changes rung spacing. *Checked at freeze @ `9039e234`: semantics
  as §2.*
- A sibling default-ON mechanism merges between freeze and submit —
  voids the §3.4 bit-identity bridges; re-declare before submitting.
- Canary shows a scalar echo mismatch (interval where a point was
  declared or vice versa), a `mint` canary at shipped-mint rates, or
  a titre outside the resolved band.
- `off` is not bit-identical to prior `off` cells — engine drift on
  the shared stream, above any margin question.
- The census shows minted objects that never serve at rates that
  change the presence→posting map (the "mints but never enters
  service" under-count) — changes what the gate measures.
- Non-nested mint sets appear across scalar rungs at shared seeds —
  the declared stream layout failed.

## 10. Readout plan

Primary census + tables: `tools/noro_diag/food_shapes_01_scan.py`
(one-pass streaming decode — summary + witness + mint/titre census +
integrity) and `tools/noro_diag/food_shapes_01_report.py`, extended
for the new arm set (arm table + echo expectations only — no new
witness fields are required; the scalar echo is the same
`parameters.transmission.common_source` field). Anchoring marginals:
`tools/noro_diag/outbreak_anchor_readout.py` (posting vs `off` floor,
posted-AR medians). Conversion: `tools/noro_diag/early_event_scan.py`
+ `early_event_report.py`. Burst: burst48 excursion-vs-rest on posted
and excursion sets. Dose position (positions/ratios only — the dose
ledger is withdrawn): `tools/noro_diag/entrain_01_dose_audit.py` +
`entrain_01_dose_audit_analysis.py`. Bridges:
`tools/noro_diag/food_shapes_01_bridge.py` — paired-seed compares vs
the SHAPES-01 prefixes at `45b2bf18`
(`s3://crusherbucket-994254241749-us-east-1-an/campaign/noro_food_shapes_01/`),
hull-parameterized. Posting-conditional reads pool within an arm per
§5.5, and across in-band rungs for the signature pool.

Deliverable readout doc:
`docs/norovirus/noro_mint_rate_01_readout.md` + campaign LEDGER
findings section + open-ledger status update; each margin reported as
measured/inferred/hypothesis.

## 11. Exclusions (explicit non-goals)

No engine code changes; no image builds; no array submissions; no
mega hull; no cadence/extent/titre-denominator arms (settled);
no `extra_lot_probability`, handler/diner-mint, or `ind`-gate cells
(pruned, §3.5); no provenance-register edits (rung values are arm
config); no fitting to the 0.4–0.9 posting band, the 0.04 AR edge, or
any `ind` signature — rungs are declared points on the measured axis;
no absolute dose figures in the readout while the dose ledger is
withdrawn — Hill positions and ratios only.
