# NORO-GATE-FLOOR-01
**Date:** 2026-09-24
**Commit:** 1264f60
**Pathogens:** all
**Status:** measured
**Measured at:** 37dc215

A **physical** minimum-pickup threshold for fomite surface pools
(`SURFACE_PICKUP_MIN_GEC`), distinct from and above the numerical residue
floor, plus the norwalk-only re-canary of `NORO-TOUCH-SHARE-01` that the
threshold makes interpretable. §§0–5 are frozen **before** any cell of the
Part-B block runs; §6 is filled only from the measured block.

Every dose quantity here is a paired ratio, share or event count against a
withdrawn baseline (`../norovirus/norovirus_open_ledger.md` §1). **Absolute
whole-voyage dose is not a pass/fail criterion anywhere in this entry and
every absolute dose figure is withdrawn.**

## 0. Settled inputs (quoted, not re-derived)

- **`NORO-TOUCH-SHARE-02`** (#672, main `1264f60`): the `-01` coincidence
  signal was **gate-count divergence**, not norovirus reallocation.
  `SURFACE_RESIDUE_FLOOR_GEC = 1e-12` is a *numerical* floor on every
  surface pool and per-surface unit total, all pathogens, both arms,
  pooled default. It stays, unchanged, beneath the constant added here.
- **Measured post-floor (seeds 8000/8001, `29bbd39`)**: `_pathway_fomite`
  still opened the zone gate on pools of 1e-9…1e-6 GEC and dispatched a
  pickup draw per occupant against sub-copy pools.
- **`NORO-TOUCH-SHARE-01`** (#666, measured `3a54ad3`): canary design
  (seeds 8000–8019, `classic_cruise_1900`, 288 epochs, areal vs declared)
  and its coincidence rule, reproduced verbatim in §4.1; readout tool
  `tools/noro_diag/touch_share_coincidence_readout.py`; driver
  `tools/noro_diag/per_host_dose_challenge.py`; lockstep instrumentation
  `tools/noro_diag/touch_share_lockstep_probe.py` (from `-02`).
- **`NORO-FOMITE-DISAGG-01`** (#664, measured `622f99f`): the identity
  `pooled == per_surface + areal + shipped`. It must still hold after
  Part A; §3 freezes the re-measurement.
- **Operator decision:** the declared touch-share table stays
  pathogen-agnostic (touch shares are human behaviour). It is **not**
  scoped to norovirus here.
- **`SWAB_LOD_COPIES_BY_SURFACE`** (`crusher_labs/observation_core.py`,
  10^3.5 / 10^4 copies per swab, Grade A/B) is an **observation**
  threshold. It is deliberately *not* used as the transmission gate; the
  two are independent and are argued separately in §1.2.
- **Untouched:** `HIGH_TOUCH_AREA_M2`,
  `SANITARY_HIGH_TOUCH_AREA_M2_PER_WC`, the 1e-12 residue floor, the
  declared share table, the engine default pathogen bundle. `pooled`,
  `areal` and `shipped` stay the defaults. No derived area basis, no
  cleaning-policy work, no fitting to VSP/Park/attack rate, no AWS block.

## 1. Part A — the constant (frozen)

### 1.1 Definition

`engines/fomite_surfaces.py`:

```python
SURFACE_PICKUP_MIN_GEC = 1.0

def pickup_gate_open(surface_mass: float) -> bool:
    return surface_mass >= SURFACE_PICKUP_MIN_GEC
```

`engines/transmission_core.py`: the four pickup gates that read
`surface_mass <= 0` — pooled/default `_pathway_fomite`, the per-surface
sanitary request path, the pooled sanitary request path and the legacy
pickup loop — now read `not pickup_gate_open(surface_mass)`. All four sit
above `_fomite_pickup_request`, `_fomite_pickup_requests_by_class` and
`_fomite_pickup_by_class`, so **a sub-copy pool consumes no pickup RNG**.

Applied identically in `pooled` and `per_surface`, every pathogen, every
arm. **This is a default-path change** and is labelled as such in the PR
and in every golden comment it moves.

### 1.2 Provenance row

| field | value |
|---|---|
| constant | `SURFACE_PICKUP_MIN_GEC` |
| value | 1 GEC — exact, not an interval; the quantum is one copy |
| what is measured | nothing environmental: this is the **quantisation of the mass unit the engine already carries** (genome equivalent copies are discrete; a pool holding less than one whole copy has no virion for a hand to pick up) |
| setting | every zone and per-surface unit, all pathogens, both representations, default path |
| grade | **C** — declared assumption |
| origin | `Tr` — transcribed from this repository's own mass-unit definition. **No journal source defines a fomite pickup threshold and none is claimed.** The observation-side swab LOD (10^3.5–10^4 copies/swab, Grade A/B) is a property of the assay, not of the hand, and is 3–4 orders larger; adopting it would silently delete real pickups, so it is rejected as the gate. |
| no-tuning | not selected to hit VSP, Park, an attack rate or the passenger/crew ratio; it is the smallest physically meaningful pool, fixed by the unit |

Grade C or better is available, so the report-immediately condition
("cannot be given a provenance row of grade C or better") is **not**
triggered.

### 1.3 Gated, not zeroed — and the mass-conservation consequence

**Decision: gated, not zeroed.** A pool below 1 GEC keeps its mass in the
reservoir; only the pickup gate closes. The mass continues to decay, is
still subject to cleaning and disinfection, and the gate **reopens** the
moment later deposition carries the total back to ≥ 1 GEC.

Consequence: this constant is **mass-conserving** — it removes no mass,
it only forbids a transfer that has no physical referent. The only term
that discards mass remains the 1e-12 numerical residue floor beneath it.
The alternative (zeroing sub-copy pools, as the residue floor does) was
rejected because it is lossy at a scale that is *not* numerical dust:
repeated sub-copy deposits that would legitimately accumulate to a whole
copy would each be destroyed, so a zeroing gate would suppress real
accumulation rather than only sub-copy pickup.

### 1.4 Goldens moved by Part A (all attributed, measured locally)

Base `1264f60`, fast tier `-m 'not slow' -n auto`: 5,883 passed with the
four movements below, each measured in a tree containing no other change,
and each passing at base.

| golden | move | attribution |
|---|---|---|
| `test_covid_hull_change_detector` `greg_mortimer_2020` (3.12) | `(0, 0, 217, 1, 0)` → `(4, 2, 217, 5, 2)` | sub-copy pickups and their hand-to-mouth draws no longer happen, the shared stream reorders, and the near-extinct cell re-ignites. CPython 3.11 reads the same tuple (CI job 107765635955, fast tier 3.11 shard 3, this branch), so both interpreters agree. |
| `test_index_departure` transmission-gating fixture | `aboard_events 1 → 0` | the fixture's zone pool is 0.44 GEC: its entire fomite route ran **below one genome copy**. Re-based on `_profile(8.0)` (≈3.58 GEC) so it still tests the route it names. |
| `test_index_departure` graded-departure sweep | `[10,10,7,0]` → `[10,7,10,0]` | same stream shift; the second scenario also now gets fresh susceptibles instead of hosts the first already exposed. |
| `test_route_attribution` | `sum(routes) == ever_infected − 3` fails (5 ever-infected, 3 route events) | the equality was only ever true when no host acquired a second pathogen: `cumulative_ever_infected` counts **distinct hosts**, route attribution counts **host-pathogen acquisitions**. Replaced by the invariant it stood in for (no fiat import is attributed to a route; every non-fiat infection carries one). |

No other golden or neutrality test moved. A move that could not be
attributed to Part A would be a report-immediately stop; none occurred.

## 2. Part B driver — norwalk-only bundle

`data/pathogens/norwalk_only.json`: a diagnostic-only bundle holding
`norwalk_gi` alone, selected with the **existing**
`per_host_dose_challenge.py --bundle` / `touch_share_lockstep_probe.py
--bundle` option. No driver code change and **no change to the engine
default bundle** (`asset_defaults.DEFAULT_PATHOGEN_BUNDLE_ID`) were
needed, so the report-immediately condition ("cannot run norwalk-only
without touching the engine default bundle") is **not** triggered.

## 3. Identity re-measurement (frozen)

`NORO-FOMITE-DISAGG-01` §2, re-run on the Part-A commit: paired seeds
8000–8019, 288 epochs, `classic_cruise_1900`, `norwalk_gi`, arms `pooled`
vs `per_surface + areal + shipped`, readout
`tools/noro_diag/fomite_disagg_identity_readout.py`, tolerances exactly as
frozen there (event counts exact; masses, credited dose and per-host
vectors `rel ≤ 1e-9`).

**Deviation declared here, before the run:** the block runs under
`--bundle norwalk_only` rather than the shipped default bundle, so the
identity arm is shared with the Part-B `A` arm (60 runs instead of 80 on
a 2-vCPU VM). The identity is an algebraic-neutrality claim about the
fomite route and is bundle-independent; norwalk is the only fomite-active
pathogen in the bundle. A failure on any seed is an implementation defect
and a **stop-and-report**, not a model difference.

## 4. Part B — coincidence readout (frozen)

**Cell.** `classic_cruise_1900`, **`--bundle norwalk_only`**,
`norwalk_gi`, 288 epochs, paired seeds 8000–8019 (20), arms
`A = per_surface + areal + shipped` and
`D = per_surface + declared + shipped` with the #666 table
(`data/config/fomite_touch_share_declared.json`). Local only; run on the
Part-A commit.

### 4.1 Coincidence rule (verbatim from `NORO-TOUCH-SHARE-01` §4)

Credited quantity: per host, fomite mass delivered to hands over the
voyage (`hosts[].fomite_delivered_by_class`, summed).

The declared table **changes coincidence** if, over the 20 seeds,
(a) median `jaccard` of the credited-host sets `< 0.90` **and** (b) in
`≥ 15` seeds the `public.button_or_dispenser` share of the *public zone
class's* delivered mass exceeds its areal-arm share by `> 0.10` absolute.
It is **inert** if `H_A == H_D` on all 20 seeds. Otherwise
**indeterminate at n = 20**. Predicted direction unchanged:
`button_or_dispenser` rises and `grab_rail_m` falls in `public`; dining
classes move little.

### 4.2 Event alignment (new column, frozen)

The `-01` readout's `aligned` witness is promoted to a **primary**
column, and the `-02` lockstep instrumentation supplies the epoch:

1. `aligned` (per seed): arms A and D have equal `surface_deposit_calls`
   **and** deposited GEC equal within `rel ≤ 1e-9` **and** equal
   `hand_to_mouth_calls` over the voyage
   (`tools/noro_diag/touch_share_coincidence_readout.py::_stream_alignment`).
   Reported as the **fraction of seeds whose deposit streams stay
   aligned**.
2. `first_divergence_epoch` (per seed): from
   `tools/noro_diag/touch_share_lockstep_probe.py --bundle norwalk_only`,
   run over the **first 96 epochs** of the same 20 seeds (a third of the
   voyage; the probe costs two runs per seed and the `-02` divergences
   appeared in the first tens of epochs). A seed still in lockstep at
   epoch 96 is recorded as `≥96`, **not** as "aligned to 288".
3. Alongside it, the probe's `first_divergence_draw` and the event
   witness at that epoch, so a divergence can be read as *deposit-stream*
   vs *pickup-gate* in origin.

**Interpretation rule, frozen:** a coincidence verdict under §4.1 is
**interpretable only on the seeds whose deposit streams stay aligned**.
On a seed that diverges, the arms are no longer paired and any host-set
or share difference is a stream artefact. The fraction aligned is
therefore reported with the verdict and, if it is low, the verdict is
recorded as *indeterminate at n = 20* whatever (a) and (b) say. The
`-01` block measured 3/20 aligned; the hypothesis this entry tests is
that the Part-A gate raises that fraction.

### 4.3 Per-class cap-share diagnostic (frozen)

Per (zone class, item class) and arm: delivered-mass share of the ship
total and of that zone class's total, distinct hosts credited, and
`capped_calls / calls`. **Any declared class with capped-call share
> 10% in arm D is a report-immediately stop condition**; its delivered
share then measures the conservation cap, not the touch share.

### 4.4 Reporting rule (frozen)

Paired and relative quantities only: host-set Jaccard, within-zone-class
shares, D/A ratios, event counts, alignment fractions and per-seed
differences. **No absolute whole-voyage dose is a criterion**, and none
is quoted as a result.

## 5. Stop conditions (frozen)

| condition | action |
|---|---|
| Part A breaks the §3 identity on any seed | stop, report — implementation defect |
| any golden moves that is not attributable to Part A | stop, report |
| any declared class > 10% capped calls in arm D | report immediately |
| the driver cannot run norwalk-only without touching the engine default bundle | report (not triggered, §2) |
| the threshold cannot be given a Grade C or better provenance row | stop after ledgering candidates (not triggered, §1.2) |
| `H_A == H_D` on all 20 seeds (inert) | design finding, stop |

## 6. Measured

Measured at `37dc215` (Part A merged, #674). Block: 20 paired seeds
8000–8019, `classic_cruise_1900`, `--bundle norwalk_only`, 288 epochs,
three arms (`pooled`, `per_surface+areal`, `per_surface+declared`) plus
the 96-epoch lockstep probe on all 20 seeds. Artifacts committed under
`../norovirus/noro_gate_floor_01/`.

### 6.1 Identity (§3) — holds

`fomite_disagg_identity_per_surface_areal.json`: **identity holds** on all
20 seeds. Every exact statistic (`surface_deposit_calls`,
`deliver_calls`, `hand_to_mouth_calls`, `hosts_credited_any_dose`,
`secondaries`, `imports`, `attack_rate`) is equal; the worst relative
deviation over all mass/dose statistics and the per-host vectors is
`1.5e-15` (seed 8001), i.e. float-summation order only, 6 orders inside
the frozen `1e-9`. Part A therefore does **not** break `DISAGG-01`.

Five seeds (8004, 8009, 8012, 8013, 8016) deliver no fomite mass at all
under `norwalk_only`, so the delivery witnesses never fire — **in
neither arm**. The readout originally scored a field absent in both arms
as a defect, which reported `DEFECT` with every compared value equal.
Fixed in `tools/noro_diag/fomite_disagg_identity_readout.py`: absence in
both arms is agreement (`seeds_absent_in_both_arms`), absence in exactly
one arm is a defect (`seeds_absent_in_one_arm`); three regression tests
pin the three cases.

**Runtime side-effect (diagnostic, not a criterion).** `per_surface` /
`pooled` wall-clock ratio is median **1.012** [0.965, 1.159] against the
spec envelope [1.5, 4.0] — below it, as `DISAGG-01` §7 already measured
(**1.126** [1.051, 1.211]). Only `> 4×` was ever a report condition, so
nothing is triggered. The two figures are not strictly comparable (that
block ran the shipped bundle, this one `norwalk_only`), but the drop is
in the direction Part A predicts: the per-surface arm no longer pays for
per-class pickup dispatch against sub-copy pools.

### 6.2 Event alignment (§4.2) — 10/20 at 288 epochs, 13/20 at 96

| quantity | `-01` (all pathogens) | here (norwalk only, Part-A gate) |
|---|---|---|
| deposit streams aligned, 288 epochs | 3/20 | **10/20** |
| still in lockstep at epoch 96 | — | **13/20** |

First-divergence epochs (lockstep probe, 96-epoch window):

| seed | first divergence | probe class | max \|mass\| at divergence (GEC) |
|---|---|---|---|
| 8000 | ≥96 | — | — |
| 8001 | 61 | expected | 0.965 |
| 8002 | ≥96 | — | — |
| 8003 | 36 | expected | 48.7 |
| 8004 | ≥96 | — | — |
| 8005 | 65 | expected | 1.36 |
| 8006 | ≥96 | — | — |
| 8007 | 89 | expected | 3.90 |
| 8008 | 45 | expected | 1.37e3 |
| 8009 | ≥96 | — | — |
| 8010 | ≥96 | — | — |
| 8011 | ≥96 | — | — |
| 8012 | ≥96 | — | — |
| 8013 | ≥96 | — | — |
| 8014 | 83 | expected | 1.03 |
| 8015 | ≥96 | — | — |
| 8016 | ≥96 | — | — |
| 8017 | 91 | expected | 1.04 |
| 8018 | ≥96 | — | — |
| 8019 | ≥96 | — | — |

All seven divergences inside the window are classified `expected` by the
`-02` probe — a `norwalk_gi` class-mass reallocation between the areal
and declared tables, on a pool the arms genuinely share. This is the
substantive change from `-02`, where the first divergence was a
gate-count artefact on sub-copy pools: **with the 1-GEC gate the arms no
longer part company over pools that cannot yield a pickup.** One residual
(seed 8001, epoch 61, 0.965 GEC in `Engine_Room`) diverges on a *deposit*
into a still-sub-copy pool, so a deposit-side counterpart of this gate is
the remaining sub-copy asymmetry — recorded, not fixed here.

Seeds 8015 and 8018 stay in lockstep to epoch 96 yet are misaligned over
288, so divergence is not confined to the first tens of epochs under
`norwalk_only` and the `≥96` rows must not be read as "aligned to 288".

### 6.3 Coincidence (§4.1) — rule does not fire; inert where paired

`touch_share_coincidence_per_surface_declared.json`, all 20 seeds:
median host-set Jaccard **1.000** (rule needs `< 0.90`) and the focus
class `public.button_or_dispenser` gains `> 0.10` share in **12/20**
seeds (rule needs `≥ 15`). Neither limb is satisfied → **indeterminate at
n = 20**, matching `-01`.

Under the frozen §4.2 interpretation rule the verdict is read only on the
10 deposit-aligned seeds, and there it is sharper:

| subset | seeds | median Jaccard | focus gain > 0.10 |
|---|---|---|---|
| deposit-aligned | 10 | **1.000** (all ten exactly 1.0) | 2/10 |
| diverged | 10 | 0.807 | 10/10 |

**On every seed where the arms are still paired, `H_A == H_D` exactly.**
The entire Jaccard signal and the entire focus-class gain live on the
seeds whose event streams had already parted — i.e. they are stream
artefacts, which is the `-02` conclusion re-confirmed on a norovirus-only
bundle against the physical gate. `secondaries_delta` is **0 on all 20
seeds**, both arms, so the declared table changes no outcome.

The two aligned seeds with a focus gain (8000: +0.512, 8002: +0.386) show
the declared table doing exactly what it was predicted to do *within* a
zone class — `button_or_dispenser` share up, `grab_rail_m` down — while
crediting the identical host set. Declared-vs-areal is therefore a
**re-allocation of mass among item classes, not of exposure among
hosts**, at this cell.

Caveat on power: of the 10 aligned seeds, 5 credit **no** fomite host at
all under `norwalk_only` (8004, 8009, 8012, 8013, 8016) and one credits
2. The interpretable n is **4–5 seeds**, not 10, so "inert" here is a
strong hint, not a measurement at n = 20. `identical_host_sets_all_seeds`
is `false`, so the §5 inert-design stop is **not** triggered.

### 6.4 Cap-share diagnostic (§4.3) — no stop

Maximum `capped_calls / calls` over every (zone class, item class) in
arm D: **0.93%**, against the 10% report-immediately limit. `cap_flags`
is empty. **Not triggered** — no declared class's delivered share is
measuring the conservation cap.

### 6.5 Stop conditions

None triggered. Identity holds (6.1); every moved golden is attributed
(§1.4); no class exceeds 10% capped calls (6.4); norwalk-only ran on the
existing `--bundle` option with the engine default bundle untouched (§2);
the constant carries a Grade C row (§1.2); host sets are not identical on
all 20 seeds, so the inert-design stop does not apply (6.3).

### 6.6 What this entry settles, and what it does not

- **Settled:** a sub-copy pool no longer opens the pickup gate anywhere
  on the default path; the pooled/per-surface identity survives it; the
  declared touch-share table is inert on host sets on every seed where
  the arms remain paired, and moves only within-zone-class item shares.
- **Not settled:** the coincidence rule of `-01` remains unfired at
  n = 20 because only ~5 aligned seeds carry fomite hosts at all under
  `norwalk_only`; a decision on the table needs either a cell with more
  fomite-active seeds or the deposit-side gate that would keep more
  seeds paired (6.2). Every absolute dose figure remains withdrawn.
