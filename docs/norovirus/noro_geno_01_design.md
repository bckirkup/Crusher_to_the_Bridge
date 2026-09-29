# NORO-GENO-01 — design (frozen before any cell runs)

**Status:** frozen — admissibility and cell layout below are the contract the
canary and any follow-on arrays run against; nothing here may be revised after
the first child lands.

Question: does the declared two-class structure (GII.4 pandemic lineages vs
non-GII.4 [GII.2, GII.17]) resolve mechanically inside one frozen voyage —
i.e., do founders draw from the pinned prior, does the class-conditioned
secretor-negative gate bite in the declared direction, and does per-class
acquisition attribution land in the run output? Shares, the class secretor
split, and `transmissibility_multiplier` are **declared, not fitted** — the
VSP anchor is genotype-blind and nothing here selects on it.

Ruling: `docs/proposals/pathogen_class_structure_decision.md`.
Declaration: `docs/ledger/NORO-GENO-01.md`.
Share intervals: `docs/literature/consensus_tranche_49_genotype_class_shares.md`.

## Cells

The frozen cell is `fl_spr_12d` of
`picard_framework/runs/mega_cruise_campaign/noro_rebase_01_canary_manifest.json`
copied verbatim into one manifest per cell — platform `spirit_cruise_3000`,
`dose_adjustments: [4.0]`, `surveillance_strategies: ["syndromic_comp65"]`,
`epoch_durations: [288]`, `boarding_mechanism_rungs: ["reportable"]`,
`num_agents: 3000`, the `config_overrides` block unchanged, seeds **8105–8124**
(paired with the NORO-REBASE-01 baseline canary so arm-vs-arm is seed-matched).

| manifest | tier | genotype prior | cell |
|---|---|---|---|
| `noro_geno_01_mono_gii4_manifest.json` | `geno_mono_gii4` | `{"GII.4": 1.0}` | A — GII.4 class alone |
| `noro_geno_01_mono_nongii4_manifest.json` | `geno_mono_nongii4` | `{"GII.17": 0.375, "GII.2": 0.625}` | B — non-GII.4 class alone, declared pre-era within-class split renormalized (the class is the measured unit) |
| `noro_geno_01_mixture_manifest.json` | `geno_mixture` | shipped era-`pre` map (`GII.4` 0.6 / `GII.17` 0.15 / `GII.2` 0.25) | C — declared mixture |

Override mechanics: `pathogen_configs.norovirus.overrides.norwalk_gi.
strain_evolution.prior_genotype_distribution` deep-patches the resolved
profile and wins over `prior_genotype_distribution_by_era`; `genotype_classes`
deep-merges untouched (A and B pin the prior only — the declared class
structure, class secretor rels 0.10 / 0.45, and `transmissibility_multiplier`
1.0 are identical across all three cells).

All cells carry `variant_surveillance.enabled: true` at shipped nominal
mutation rates — required for the strain registry (acquisition `strain_id`,
per-epoch `strain_census`) and kept uniform across cells so RNG consumption is
identical. The mutation window is not widened.

## Readouts (declared up front)

- Total acquisitions + attack rate per cell (aboard-acquired, split from
  boarding imports in `summary.json` → `strain_attribution`).
- Per-class acquisition attribution on cell C (`classes_acquired_aboard`,
  `classes_ever_infected`; `lineage_census.json` strain→genotype map for
  decoding).
- **Non-secretor acquisition share per cell** — the gate's discriminating
  readout (`non_secretor_share_acquired_aboard`; B should carry ~4.5× the
  non-secretor share of A under the declared 0.45 vs 0.10 rel).
- Postings per 1,000 (`cumulative_reported_cases` / num_agents) — **report,
  never select**.
- Per-epoch `strain_census` genotype presence (`lineage_census.json`
  snapshots).

## Instruments and witnesses

- `resolved_pathogen_profiles.json` — the pinned prior and intact
  `genotype_classes` must appear in the resolved profile block (the smoke
  gate asserts exactly this).
- `lineage_census.json` — truth channel: every strain with genotype +
  founders + per-epoch snapshots.
- `summary.json` → `strain_attribution.<pathogen_id>` — harness-side
  post-run agent walk: ever_infected / imported / acquired_aboard,
  non-secretor counts and shares per bucket, per-class and per-genotype
  agent attributions, population non-secretor share.
- `timeseries.json` — epidemic curve + postings marginal.

## Report immediately

- The override fails to resolve in the result zip's resolved profile block.
- Per-class attribution is absent from outputs (instrument the observer
  BEFORE the array — cells store only observer aggregates).
- Cell A shows a higher non-secretor acquisition share than B (gate folded
  backwards).
- A mono cell returns zero acquisitions on all 20 seeds.

## Campaign gate

Canary = cell A at all 20 seeds (jobs 1–20); then stop and report. The
remaining 40 runs (B and C) wait for the user's go. Verdict after the full
3-cell read flips `NORO-GENO-01` `open` → `measured`.
