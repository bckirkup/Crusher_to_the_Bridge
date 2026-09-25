# NORO-COINCIDENCE-CELL-01
**Date:** 2026-09-25
**Commit:** cf6a3769
**Pathogens:** norwalk_gi
**Status:** measured
**Measured at:** 995746e4

A re-run of the frozen `NORO-TOUCH-SHARE-01` coincidence canary at a **cell
chosen so that most seeds carry at least one fomite-credited host**, the
deficiency that kept the `-01`/`-02` verdicts indeterminate: at the
`classic_cruise_1900` cell only ~5 of the deposit-aligned seeds carried any
fomite-credited host at n = 20, so the frozen coincidence rule had almost no
paired mass to act on. §§0–3 freeze the cell-selection screen, the chosen
cell, the pass threshold and the readout **before** the paired runs; §4 is
filled only from the measured block.

Every dose quantity here is a paired ratio, share or event count against a
withdrawn baseline (`../norovirus/norovirus_open_ledger.md` §1). **Absolute
whole-voyage dose is not a pass/fail criterion anywhere in this entry and
every absolute dose figure is withdrawn.**

## 0. Settled inputs (quoted, not re-derived)

- **`NORO-GATE-FLOOR-01`** (merged, #677, measured `37dc215`): the 1-GEC
  pickup gate `SURFACE_PICKUP_MIN_GEC` and the 1e-12 residue floor stay,
  unchanged. Its frozen canary — seeds 8000–8019, `classic_cruise_1900`,
  `--bundle norwalk_only`, 288 epochs, arm A = `per_surface + areal +
  shipped`, arm D = `per_surface + declared + shipped` with the #666 table —
  read out **10/20 deposit-aligned**, median Jaccard 1.000, focus-class gain
  `> 0.10` on 12/20 seeds → **indeterminate at n = 20**. Of the 10 aligned
  seeds 5 credited no fomite host at all.
- **`NORO-GATE-FLOOR-02`** (merged, #679, null result): **no seed diverges
  on a deposit**; every A-vs-D divergence at that cell is the declared
  table's own reallocation opening the pickup gate in one arm; deposits
  draw no RNG (inferred). Gate repairs are exhausted — none is proposed or
  built here.
- **Frozen coincidence rule** (`NORO-TOUCH-SHARE-01` §4, verbatim in
  `NORO-GATE-FLOOR-01` §4.1): the declared table **changes coincidence** if
  over 20 seeds (a) median credited-host-set Jaccard `< 0.90` **and** (b) in
  `≥ 15` seeds the `public.button_or_dispenser` share of the public zone
  class's delivered mass exceeds its areal-arm share by `> 0.10` absolute;
  **inert** if `H_A == H_D` on all 20 seeds; otherwise **indeterminate**.
  The rule is not changed here.
- **§4.2 event-alignment witness and interpretation rule** (frozen):
  `aligned` = equal `surface_deposit_calls`, equal deposited GEC
  (`rel ≤ 1e-9`) and equal `hand_to_mouth_calls` over the voyage; a
  coincidence verdict is interpretable only on aligned seeds, and a low
  aligned fraction is reported as indeterminate at n = 20. `-02` measured
  that this witness **counts the treatment effect as misalignment**; it is
  reported as a column, while the verdict rests on the frozen rule.
- **`NORO-FOMITE-DISAGG-01`** (measured `622f99f`, re-measured `37dc215`):
  `pooled == per_surface + areal + shipped` to `rel ≤ 1e-9`, event counts
  exact. It is re-checked at the chosen cell; a failure on any seed is a
  stop-and-report, not a model difference.
- **Driver and readouts:** `tools/noro_diag/per_host_dose_challenge.py`
  (`--platform`, `--bundle norwalk_only`, `--pathogen-id norwalk_gi`,
  `--epochs`, `--fomite-representation per_surface`,
  `--fomite-touch-share areal|declared`, `--fomite-touch-share-table
  data/config/fomite_touch_share_declared.json`),
  `tools/noro_diag/touch_share_coincidence_readout.py`,
  `tools/noro_diag/fomite_disagg_identity_readout.py`, and the `-02`
  lockstep instrumentation
  `tools/noro_diag/touch_share_lockstep_probe.py`.
- **Operator decisions:** the declared touch-share table stays
  pathogen-agnostic; `pooled` stays the default; no AWS block this
  session; no constant changes; `HIGH_TOUCH_AREA_M2` untouched;
  `per_surface`/`declared` stay non-default.

## 1. Cell-selection screen (declared before any paired run)

**Purpose.** The chosen cell's pass threshold is that **most seeds carry at
least one fomite-credited host** — the deficiency at the `-01` cell. The
screen measures exactly the quantity it selects on: seeds with
`len(fomite_delivered_by_host) ≥ 1` in the areal arm.

**Candidates**, `data/platforms/`, ordered by the cost of a 60-run paired
block (20 seeds × {areal, declared, pooled} at the frozen voyage) on this
2-vCPU VM, given the ~4 h wall budget authorized for the paired block:

| candidate | declared complement | status in screen |
|---|---|---|
| `expedition_cruise_450` | 450 | screened |
| `messy_cruise_500` | none declared | **excluded a priori**: `declared_total` refuses it — a run cannot state a complement its hull does not berth |
| `spirit_cruise_3000` | 3000 | screened |
| `mega_cruise_5000` | 7000 | **excluded a priori by budget**: larger population than spirit (which already projects near the ~4 h limit at its declared voyage); a 60-run block cannot fit ~4 h wall |

`classic_cruise_1900` is not a candidate: it is the `-01` cell whose
interpretable n this entry exists to fix.

**Screen protocol.** Single arm (`per_surface + areal + shipped`),
`norwalk_only`, seeds drawn from the canary set 8000–8019, a few seeds per
candidate; per seed, count fomite-credited hosts
(`len(fomite_delivered_by_host)`). A candidate **predicts ≥ 15/20** when at
least 3/4 of its screened seeds carry ≥ 1 fomite-credited host; a screen
that starts ≤ 1/4 rejects the candidate. The first candidate in cost order
that predicts ≥ 15/20 is selected; its screened areal-arm cells are reused
in the paired block. The epoch count is part of the cell: the platform's
declared voyage (`voyage_config.total_epochs` — 168 on every hull in
`data/platforms/`) is screened first; the `-01` cell's 288 epochs were a
voyage extension on classic, and at spirit that extension would push the
60-run block past the ~4 h budget. If the declared-voyage screen leaves
the prediction marginal (the screened viable fraction within ~1 seed of
the 3/4 bar), the next epoch count up that still fits the budget is
screened on the same seeds and the cell takes the larger count that
clears the bar.

**Pass threshold (frozen).** ≥ 15/20 seeds with `len(fomite_delivered_by_host)
≥ 1` in the areal arm of the paired block.

### 1.1 Screen measurements (measured at this branch's run commit)

`expedition_cruise_450`, 288 epochs, areal arm — 4 seeds: **1/4 carried a
fomite-credited host** (8000: 0, outbreak extinct — 1 import, no
depositions above noise; 8001: 0, `Boarded norwalk_gi -> 0 hosts` — no
index case at all; 8002: 25 hosts, 114 credited, 3.96 GEC deposited; 8003:
0, extinct — 1e-253 GEC dust). Screen: **rejected** — norwalk on this hull
is bimodal toward extinction, which cannot put a fomite host on most seeds.

Driver defect found on seed 8001 and fixed on this branch:
`fomite_representation_seen`/`fomite_touch_share_seen` were only stamped
inside the `deposit` wrapper, so a seed with zero surface deposits ran to
completion and then aborted on the override-dropped guard, silently
dropping the seed from any readout. The stamps moved to the per-epoch
`_execute_pathogen_pathways` wrapper; behaviour on seeds that deposit is
unchanged (the witnesses record the same resolved arm strings).

`spirit_cruise_3000`, 288 epochs, areal arm — 4 seeds: **4/4 carried a
fomite-credited host** (8000: 647, 8001: 662, 8002: 394, 8003: 278; ~10.6
min/seed wall under 2-way contention). Screen at the extended voyage:
**passes ≥ 3/4 with a wide margin**.

`spirit_cruise_3000`, 168 epochs (declared voyage), areal arm — 8 seeds
(8000–8007): **7/8 carried a fomite-credited host** (8000: 83, 8001: 0 —
extinct, 2 index cases boarded, 15 deposit calls, no deliveries; 8002: 386,
8003: 1, 8004: 176, 8005: 366, 8006: 587, 8007: 205; ~6.4 min/seed wall
under contention). Screen: **predicts ≥ 15/20** (87.5% viable). These 8
cells are arm A's first eight and live in `arm_per_surface_areal/`.

`spirit_cruise_3000`, 192 epochs (epoch-axis fallback), areal arm — 4 seeds
(8000–8003): credited-host sets **identical to the 168-epoch runs on all 4**
(83, 0, 386, 1). Two measured consequences: (i) the first 168 epochs are
literally the same simulation — boarding draws and trajectories match,
voyage length only extends the tail; (ii) the fomite-credited host set does
not grow between epochs 168 and 192 on any screened seed — slow outbreaks
either have their fomite phase inside the declared voyage or need >192
epochs to reach it (seed 8001's extinct-at-168 trajectory reaches 662 hosts
at 288). The 192-epoch cell is therefore the same cell for viability at
~14% more cost — **rejected on cost, not on coverage**.

## 2. The frozen cell

**Cell: `spirit_cruise_3000` × `--bundle norwalk_only` × 168 epochs** (the
platform's declared `voyage_config.total_epochs`).

- **Why this cell** (selection, not dose): the cheapest surviving candidate.
  `expedition_cruise_450` was rejected by its own screen (1/4 seeds);
  `messy_cruise_500` cannot host the declared arm; `mega_cruise_5000`
  breaks the ~4 h block budget; `classic_cruise_1900` is the `-01` cell.
  Spirit's areal screen passed 4/4 at 288 epochs and re-confirmed at the
  declared voyage below.
- **Epoch count**: 168, the declared voyage on every hull — not a budget
  fit and not a match to `-01`'s 288-epoch extension on classic.
- **Projected cost**: measured ~6.4 min/seed at 168 epochs under 2-way
  contention on this 2-vCPU VM. The 60-run block reuses the 8 screened
  areal cells (seeds 8000–8007), leaving 52 runs ≈ 2.8 h wall, inside the
  authorized ~4 h.
- **Pass threshold (re-stated, frozen)**: ≥ 15/20 seeds with
  `len(fomite_delivered_by_host) ≥ 1` in arm A.

## 3. Paired canary and readout (frozen)

**Block.** Seeds 8000–8019 (20 paired), `--bundle norwalk_only`,
`norwalk_gi`, arms `A = per_surface + areal + shipped`,
`D = per_surface + declared + shipped` (table
`data/config/fomite_touch_share_declared.json`), plus `P = pooled` for the
DISAGG-01 identity re-check. Local only. Dumps land under
`docs/norovirus/noro_coincidence_cell_01/arm_{per_surface_areal,
per_surface_declared,pooled}/`. If the block is projected to exceed ~4 h
wall, the cell moves to fewer epochs and the move is stated here before
the run.

**Readout** (`touch_share_coincidence_readout.py` on A vs D;
`fomite_disagg_identity_readout.py` on A vs P), all quantities paired or
relative only:

1. seeds with `len(fomite_delivered_by_host) ≥ 1`, per arm, against the
   §1 pass threshold;
2. credited-host-set Jaccard per seed and its median;
3. per-(zone class, item class) `hosts_credited` deltas D − A;
4. the §4.2 event-alignment column (fraction of seeds deposit-aligned);
5. cap shares: `capped_calls / calls` per class in arm D — **any class
   > 10% is a report-immediately stop**;
6. the frozen coincidence verdict: fires / does not fire / still
   indeterminate, with the reason.

**Stop conditions (frozen).**

| condition | action |
|---|---|
| no candidate cell predicts ≥ 15/20 | stop, report |
| areal arm not bit-identical to pooled on any seed (`rel ≤ 1e-9`, event counts exact) | stop, report — implementation defect |
| any declared class > 10% capped calls in arm D | report immediately |
| the paired block projects over ~4 h wall | move the cell to fewer epochs and state the move, or stop and report |

## 4. Measured

Block run at `995746e4` (post-#681 main, including the §1.1 driver fix):
60 runs = seeds 8000–8019 × arms {areal, declared, pooled}, ~2 h 40 m wall
(~6.4 CPU-h) on the 2-vCPU VM, inside the ~4 h budget. Dumps under
`../norovirus/noro_coincidence_cell_01/arm_*/`, readout JSONs under
`../norovirus/noro_coincidence_cell_01/readouts/`. Every figure below is
measured on those dumps; nothing is inferred.

### 4.1 Stop conditions — all clear

- **Pass threshold**: 18/20 seeds carry ≥ 1 fomite-credited host in the
  areal arm (≥ 15 required) — **met**. Only 8001 and 8018 are extinct
  (0 hosts, both arms). Declared arm: also 18/20.
- **DISAGG-01 identity**: areal == pooled to `rel ≤ 1e-9`, event counts
  exact, on all 20 seeds (worst deviation 2.9e-15, host-level). **Holds.**
- **Cap shares**: worst `capped_calls/calls` = 0.52%
  (`crew_mess.button_or_dispenser`, seed 8005, declared arm). No class
  anywhere near the 10% stop.
- **Wall clock**: 2 h 40 m ≪ ~4 h.

### 4.2 Credited-host sets and Jaccard

| seed | n_A | n_D | Jaccard | aligned | seed | n_A | n_D | Jaccard | aligned |
|---|---|---|---|---|---|---|---|---|---|
| 8000 | 83 | 83 | 1.000 | yes | 8010 | 475 | 475 | 1.000 | yes |
| 8001 | 0 | 0 | 1.000 | yes | 8011 | 637 | 212 | 0.314 | no |
| 8002 | 386 | 386 | 1.000 | yes | 8012 | 2 | 2 | 1.000 | yes |
| 8003 | 1 | 1 | 1.000 | yes | 8013 | 1102 | 1102 | 1.000 | yes |
| 8004 | 176 | 176 | 1.000 | yes | 8014 | 795 | 951 | 0.834 | no |
| 8005 | 366 | 430 | 0.625 | no | 8015 | 66 | 66 | 1.000 | no |
| 8006 | 587 | 593 | 0.990 | no | 8016 | 87 | 91 | 0.935 | no |
| 8007 | 205 | 205 | 1.000 | yes | 8017 | 717 | 259 | 0.359 | no |
| 8008 | 655 | 655 | 1.000 | yes | 8018 | 0 | 0 | 1.000 | yes |
| 8009 | 135 | 135 | 1.000 | yes | 8019 | 139 | 173 | 0.164 | no |

- **Median Jaccard: 1.000** [0.164, 1.000]. Identical host sets on 12/20
  seeds.
- **Event alignment (§4.2 witness): 12/20 aligned** — the same 12 seeds
  whose credited sets are identical. On every diverged seed the deposit
  stream also diverged (deposit calls differ, e.g. 8011: 65 vs 59;
  8014: 114 vs 88), consistent with `-02`'s mechanism: the declared
  reallocation tips pickups across the 1-GEC gate and the treatment
  effect then propagates into the event stream.

### 4.3 Per-class `hosts_credited` deltas (D − A, summed over 20 seeds)

| zone class | per-item delta | classes |
|---|---|---|
| public | −715 (`button_or_dispenser`), −587 (`door_lever`, `grab_rail_m`) | 3 |
| dining | −192 (all 4 item classes) | 4 |
| galley | +140 (all 5 item classes) | 5 |
| crew_mess | +43 (all 4 item classes) | 4 |
| cabin | +4 (all 10 item classes) | 10 |

The declared table reallocates delivered mass **out of** the public and
dining zones into galley/crew-mess/cabin — the opposite sign of the
`public.button_or_dispenser` focus-class gain on the same seeds: within
the public class the declared table concentrates the remaining mass on
the button/dispenser item (share gain), while shrinking the class's
total credited-host count.

### 4.4 Verdict

**Still indeterminate**, on the frozen rule:

- (a) median credited-host Jaccard = 1.000 — the `< 0.90` bar fails;
- (b) `public.button_or_dispenser` share gain `> 0.10` on **12/20**
  seeds (gains 0.386–0.868) — the `≥ 15` bar fails;
- not **inert**: `H_A ≠ H_D` on 8/20 seeds (Jaccard down to 0.164).

**Reason.** The deficiency this entry was written to fix is fixed —
18/20 seeds now carry fomite mass, where the `-01` cell gave ~5
interpretable seeds — but the declared reallocation expresses only on a
seed-level subset: on 10 of the 18 viable seeds it never tips a pickup
across the 1-GEC gate, so the arms are bit-identical there (aligned,
Jaccard = 1). On the 8 viable seeds where it does express, the effect
is large (Jaccard 0.164–0.990, focus-share gain 0.39–0.87, credited-set
membership moves in both directions). The frozen rule's joint bar —
median Jaccard < 0.90 **and** ≥ 15 expressing seeds — needs expression
on ≳ 3/4 of seeds; measured expression is ~44% of viable seeds (8/18),
~60% of the 20-seed window under the focus-share witness (12/20). At
n = 20 a bimodal ~half-seed expression rate cannot fire the rule, and
the cell itself is no longer the limiting factor.

The event-alignment witness counts the treatment effect as
misalignment on all 8 expressing seeds (the `-02` caveat); the aligned
fraction is 12/20 and would be ~2/3 even in the best case, so the
indeterminacy is now structural to the rule's bar, not to host
coverage.
