# Paper-1 WP2 joint four-hull evaluation — frozen design

Status: frozen design, authored and gated. No census, canary or cell has
run. Every Batch stage waits for the declared WP1 freeze
(`docs/norovirus/paper1_freeze_design_contract_2026_11_20.md`, a proposal
under review). This design incorporates the four corrections from Edison's
pre-freeze contract review that apply to the campaign (as relayed in the
WP2 session; the review text is not in this repository).

## Question

Does the frozen reference run cleanly on all four hulls and three voyage
lengths, with every outcome family extractable, and how do posting rates
order across diagnostic strata? The bridge gate is **technical completion
only**. The ordering is a measured diagnostic that selects a predeclared
continuation. No outcome voids the freeze. This is not an anchor fit.

## Baseline and arms

- **Baseline (invariant):** the contract's section 2 block, parsed from the
  contract by `design/build.py` and stored once as
  `manifest.joint_eval.baseline_block`.
- **Arms:** every tier is an arm. It declares the leaf paths on which it
  differs from the baseline (`joint_eval.changed_paths`) and carries the
  **complete effective nested objects**, because `merge_config_overrides`
  is one level deep. Census, bridge and pilot arms declare exactly one
  change, `ship_graph.agent_classes` (the hull's role split, below); every
  other key of their `config_overrides` is the block verbatim.
- **Checks:** the builder refuses a tier whose effective config differs
  from the baseline anywhere undeclared. `cell.py` repeats that, then,
  after the runner has applied every axis and the engine has initialised,
  checks that the runner changed no declared leaf (and records the paths it
  added) and that every leaf equals the engine-resolved `sim.cfg`. The
  resolved effective config is written to every archive. A failed check
  exits non-zero and writes no archive.
- **Reproduction arm** (the contract's labelled baseline that reproduces a
  prior draw): `supply_solver_screen_01` tier
  `fl_exp_12d_sens_p06_paxv_station_lots_continuous` on its own 16 seeds.
  Its declared differences from the baseline are the 12 `changed_paths` in
  the manifest plus five tier axes (`pathogen_overrides`,
  `boarding_prevalence_points`, `boarding_mechanism_rungs`,
  `never_symptomatic_fractions`, `sensitivity_profile`). Voyage
  fingerprints (engine commit and tier id excluded) are compared seed by seed with
  fingerprints computed from that campaign's archive at the gated stage.
- **Held fixed outside the block** (contract section 2.5): dose 7.57,
  `syndromic_comp65`, bundle `active_profiles` / `norwalk_gi` minus
  `sars_cov2_resp`, clock `hours`, `PYTHONHASHSEED=1` (pinned by `cell.py`
  and `entry.py`; see "Hash seed" below).

### Role split (the one declared arm difference)

The owner decided on 2026-11-20 that the reference runs each platform's
declared `nominal_complement`, not the split the shipped class template
happens to place. One block cannot hold four mixes, so the block is
unchanged and each tier declares `ship_graph.agent_classes` as its
difference (`build.py`, `class_mix`; contract section 2.5 records the
decision).

`class_mix` keeps the shipped class list and its within-role proportions,
gives each class a whole number of agents (largest remainder) and writes
each fraction as that count over the complement. Only `fraction` changes.

| Hull | Agents | Intended passenger / crew (= declared nominal) | Shipped template placed |
|---|---|---|---|
| `expedition_cruise_450` | 450 | 300 / 150 | 316 / 134 |
| `classic_cruise_1900` | 1,910 | 1,350 / 560 | 1,338 / 572 |
| `spirit_cruise_3000` | 3,000 | 2,100 / 900 | 2,100 / 900 |
| `mega_cruise_5000` | 7,000 | 5,000 / 2,000 | 4,900 / 2,100 |

Intended counts are recorded per tier (`joint_eval.intended_roles`) and
asserted by `cell.py` on the initialised agents and on the complements in
the outcome payload. The 3% rule divides by them. The reproduction arm
re-runs a prior draw with the class list it ran with, so it intends the
template split (316 / 134).

## Strata: diagnostic labels from a seed census

Quiet, near-threshold and outbreak are **diagnostic labels**, not verdict
classes. A label says what a seed boarded, measured under the baseline
block. The block is identical in every stratum; no stratum knob exists.

**Census** (Batch stage, gated on the declared freeze). Sampling frame: per
hull, 20,000 consecutive seeds, one voyage draw each under the baseline
block. 1 epoch, 100 agents, worker `tools/noro_diag/supply_seed_scan.py`
arm `station_lots` (adds no key). Ranges: exp 2,000,000–2,019,999; cls
2,100,000–2,119,999; spr 2,200,000–2,219,999; meg 2,300,000–2,319,999.

**Source strata:** contaminated (`provisioned_source[norwalk_gi].n_contaminated > 0`)
and uncontaminated. Burden = sum over provisioned-lot objects of
`lot_servings * lot_titre_gec_per_g * 150 g`.

**Selection rule** (code: `build.py --select`; boarding state only, no
posting or attack-rate outcome enters it):

| Seeds | Per hull | Rule | Status |
|---|---|---|---|
| diagnostic quiet | 20 | first 20 uncontaminated, ascending seed | purposive; no population weight |
| diagnostic outbreak | 20 | contaminated, highest burden; ties to the lower seed | purposive; no population weight |
| diagnostic near | 20 | contaminated, lowest burden, disjoint from outbreak | purposive; no population weight |
| evaluation | 20 per source stratum | lowest `sha256("noro_paper1_joint_eval_01:<seed>")` within the stratum | equal-probability sample; inclusion probability `n_s / N_s`, source weight `W_s = N_s / N` |

Census-selected diagnostic seeds are diagnostic evidence. Only the
independently sampled evaluation seeds, with their source weights, carry
population estimates. Inclusion probabilities and weights are written to
`design/seed_selection.json` with the seed lists.

Shortfall: a stratum the fixed census cannot fill is run at its achieved
count and reported. The census is not extended and no seed is hand-picked.

## Cells

| Stage | What | Tiers | Runs |
|---|---|---|---|
| A | census | 4 | 800 children (80,000 one-epoch seeds) |
| A | reproduction arm | 1 | 16 |
| B | small complete bridge: 4 hulls x 168/288/504 x 3 diagnostic strata x 20 paired seeds | 36 | 720 |
| B | joint-outcome pilot: 4 hulls x 288 epochs x 2 source strata x 20 evaluation seeds | 8 | 160 |

Stage A is 816 array children, the `scripts/campaign describe` count at
authoring. Stage B (880 trajectories) is emitted by `build.py` once
`seed_selection.json` exists. Explorer and 192 epochs are WP3 only.

The contract's larger counts (100 near-threshold, 300 quiet, >= 1,000 tail)
are replication targets. They are allocated after the pilots (below), not
run as a 5,040-trajectory grid.

Diagnostic seeds are paired across the three lengths within hull and
stratum. They are not paired across hulls.

## Output contract (`cell.py`, one run per cell)

`OUTPUT_CONTRACT` in the worker is the authoritative text; every archive
carries it and a `families` block with `present` or `missing` per family.

| Family | Request | Source |
|---|---|---|
| 1 burden by role | none | final `cumulative_reported_cases_*`, ever-ill, ever-infected, complements |
| 2 threshold timing | none | `derived.vsp_trigger_epoch` |
| 3 size distribution | none | seed ensemble of 1 and 2, in the readout |
| 4 first role to 0.03 | none | per-epoch role cumulative reports over the role complement |
| 5 daily curves | **explicit** `run.sentinel_line_list` (the runner arms it only for shore-exposure or variant runs) | onsets from the line list; reporting curve from the cumulative series |
| 6 environment | **output-only harvest** through `ShipSimulation.epoch_observer` | `work.swab_results`, `work.wastewater_ht_result` |

- **First role classes:** `passenger_first`, `crew_first`, `same_epoch`,
  `neither` (no role reached 3%), `missing` (no usable role series or
  complement; never folded into `neither`).
- **Reporting curve day 0** includes pre-boarding AGE declarations and is
  labelled. The declarations are counted by role from the initialised
  engine (`preboarding_declared_*`); the series' first row
  (`epoch0_cumulative_reported_*`) is reported beside them because it also
  holds any sick-call report made during epoch 0.
- **Swabs:** every swab is counted per epoch; each swab with recovered
  copies keeps a row with zone, epoch, surface class, density (copies per
  cm2), recovered copies and LOD (copies per swab), `detected` and
  `censored_below_lod`. Units are stated in the archive.
- **Wastewater:** the holding-tank qPCR assay only, one row per assay with
  concentration, LOD and LOQ (copies per litre), `detected`,
  `quantifiable`, `censored_below_lod`. The wastewater sequencing channel
  is a different instrument and is named as not harvested.

## Bridge gate: technical completion

| Criterion | Rule |
|---|---|
| intended inputs used | every archive: voyage length equals the tier's epochs; `PYTHONHASHSEED` recorded as 1; arm differences equal the declaration; effective config resolved with no mismatch; effective hash equals the tier's; intended role counts on agents and in the payload; one engine commit per tier |
| outcomes extractable | every archive: all six families `present` |
| independent attempts accounted | seeds read are exactly the tier's seeds, each once; a failed child is listed with its reason, retried at most once on the same seed, never replaced |
| paired comparisons meaningful | the three lengths hold the same seed set per hull and stratum and all are read; the reproduction arm is compared on every one of its seeds |

Complete or incomplete. A quiet stratum that posts, or a large hull with
zero events, does not make the bridge incomplete.

## Ordering diagnostic and continuation

Posting = `derived.vsp_trigger_epoch` is not null. Intervals are
Clopper-Pearson two-sided 95%. Bands (declared, not fitted, not tuned to
any anchor): quiet <= 0.02; outbreak >= 0.50; near strictly between the
quiet and outbreak rates and within 0.10–0.90.

- A hull x length is **in** when all three strata are in band and ordered;
  **out** when an interval excludes its band; otherwise **undetermined**.
- A hull is in if all three lengths are in, out if any is out, otherwise
  undetermined.

Continuation, evaluated only on a technically complete bridge, first match:

| Continuation | When |
|---|---|
| justified defect fix | the reproduction arm does not reproduce. Needs a named defect with paired-seed evidence before any fix; an outcome alone never opens it |
| reconstruction | every hull is out |
| population-geometry | some hulls are out and others are not (includes a zero-event large hull) |
| uncertainty | no hull is out and at least one is undetermined |
| precision | every hull is in; allocate replication from the pilots |

## Precision, pilots and batches

- **Zero-event convention:** for 0 events in n, the exact (Clopper-Pearson)
  one-sided 95% upper bound `1 - 0.05^(1/n)`: 0/300 gives 0.994%, 0/20
  gives 13.9%. Always stated with its sampling frame (hull, length, source
  stratum, census seed range).
- **Bridge precision (n = 20):** half-width about ±0.23 at a rate of 0.5.
  The bridge resolves ordering, not rates.
- **Endpoint targets for replication:** posting probability half-width
  <= 0.10 per hull x length; quiet bound <= 1% one-sided (300 zero-event
  evaluation seeds in the uncontaminated stratum); first-role split
  half-width <= 0.10 among posted voyages; size-tail frequencies from
  >= 1,000 seeds per cell; curves and environment are descriptive (median
  and IQR of timing) with no target.
- **Joint-outcome pilot:** population posting probability per hull is the
  source-weighted estimate `sum_s W_s p_s` over evaluation seeds.
  Replication is split across source strata by Neyman allocation,
  `n_s ∝ W_s sqrt(p_s (1 - p_s))`; a stratum with `p_s = 0` is sized by the
  quiet-bound target instead.
- **Temporal pilot** (no extra runs): if every 504-epoch run's role-report
  series is bit-identical over its first 168 and 288 epochs to the same
  seed's shorter runs, replication runs 504 epochs only and truncates;
  otherwise each length is replicated.
- **Batches:** the bridge, the pilot and each replication block are
  fixed-size batches declared before submission. A batch is analysed once,
  when every child is accounted for. No interim look changes a batch size,
  and earlier batches are not re-analysed under new rules.

## Reported, never selected on

Reported attack rates, first-role split, swab and holding-tank detection
counts and timing, engine commits seen.

## Hash seed: contract versus actual

The freeze contract (section 2.5) says `PYTHONHASHSEED=1` is set in the job
definition environment. It is not: neither the shared job definition
template nor the campaign image sets it (checked on main, 2026-11-20;
reported by the WP3 review). For WP1b's contract revision: the pin lives in
the workers, not the job definition.

In this campaign `cell.py` re-executes itself under `PYTHONHASHSEED=1` when
run as a script (the same approach as
`campaigns/noro/explorer_reconstruction_01/cell.py`) and records the value
in every archive; the readout counts an archive as an intended input only
if it is `1`. The census worker (`supply_seed_scan.py`) has no pin of its
own and gets it from `entry.py`, which sets it for the subprocess; a direct
invocation of the census worker must set it explicitly.

## Limitations

- Compact history retention drops swab and holding-tank results from the
  epoch record; family 6 is read through the read-only observer hook.
  `cell.py --verify-draws` measures that the hook and the line list leave
  the voyage bit-identical.
- The role split is a declared arm difference, not part of the block; a
  cell elsewhere that carries the block alone runs the template split.
- The census draws its 100 agents from the same re-weighted class list,
  but at 100 agents the declared role counts cannot be placed and the
  census worker does not assert a role split. Role counts are asserted
  only on `cell.py` runs.
- The census runs at 100 agents; agent-count neutrality of the provisioned
  plan was measured once in `supply_seed_scan_01` (seed 8114, an earlier
  engine) and must be re-witnessed in the census canary.
- Whether burden rank separates the diagnostic strata under the baseline
  block is unmeasured; the bridge measures it.
- The pilot covers 288 epochs only; population estimates at 168 and 504
  rest on the temporal pilot or on replication.

## Preflight gate (not run this session)

Declared freeze -> census canary and array -> `build.py --select` and
rebuild -> image digest pin and manifest upload -> canary of 20 seeds at
one bridge cell, then stop and report -> user decides on the array.
