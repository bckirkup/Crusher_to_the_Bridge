# NORO-GENO-02 — design (frozen before any cell runs)

**Status:** frozen — the mass-surface grid, admissibility, and the
readouts below are the contract the arrays run against; nothing here
may be revised after the first array child lands.

Question: the NORO-GENO-01 canary (ledger `docs/ledger/NORO-GENO-01.md`,
measured `2713e566`) proved the class-conditioned secretor gate resolves
mechanically and moved in the declared direction (B 1/6 vs A 0/3 aboard
non-secretor acquisitions), but the ~4.5× share ratio was unresolvable
at 3-vs-6 aboard events. This stage puts mass behind that readout:
identical arms run across the block axes that can move emesis-ignition
draws — hull class, voyage length, boarding prevalence — so the gate
reads wherever aboard mass exists. Shares, class secretor rels
(0.10 / 0.45), and `transmissibility_multiplier` 1.0 stay **declared,
not fitted** — hull, epochs, and prevalence are scenario dials, not
fitted constants, and no other transmission parameter moves to gain
mass. Postings per 1,000 is reported, never selected on.

Ruling: `docs/proposals/pathogen_class_structure_decision.md`.
Declaration: `docs/ledger/NORO-GENO-01.md`.
Share intervals: `docs/literature/consensus_tranche_49_genotype_class_shares.md`.

## Settled measurement: `dose_adjustment` is inert on this block

The original stage plan named `dose_adjustment` as the mass lever.
Sweep measured on the frozen block (cell A, seeds 8105–8124, image
`noro-geno-02-sweep-2713e566`, jobdef `picard-campaign:52`, array
`2ab5af15-806b-4a35-9db9-9d82207a817b`, S3
`campaign/noro_geno_02_sweep/`, 80/80 SUCCEEDED):

| dose_adjustment | ever_infected | aboard acquisitions | non-secretor aboard |
|---|---|---|---|
| 4.0 (canary, prior) | 151 | 3 (s8115/8123/8124) | 0 |
| 3.0 | 151 | 3 (same seeds) | 0 |
| 2.0 | 151 | 3 (same seeds) | 0 |
| 1.0 | 151 | 3 (same seeds) | 0 |
| 0.0 | 151 | 3 (same seeds) | 0 |

The override resolved at every point (`resolved_pathogen_profiles.json`
carries each swept value); four orders of magnitude of environmental
release produced zero marginal aboard events. Mechanism: the dial scales
only `get_pathogen_shedding` (`10^(curve − adj)`), whose consumers are
the post-724-collapsed deposit/pickup chain; aboard acquisitions on
this block ignite through emesis, which never reads the constant.
Corroborates NORO-DOSE-REFIT-01's "inert on shipped modes". Consequence:
aboard mass must come from levers that multiply emesis-ignition draws —
voyage length, boarding prevalence, hull — so `dose_adjustment` is
pinned at the canary's 4.0 on every cell below (proven-inert constant,
kept for run-id parity with the canary) and is not a swept axis.

A second dial died in preflight: `boarding_prevalence_points` only
reach the engine on the `shipped` rung (`rate_mode:
screening_prevalence`, explicit prevalence block). The canary's
`reportable` rung is `rate_mode: renewal` — prevalence is derived from
the fixed renewal block (39/1000py incidence × 28d detectable →
~0.0039 both roles) and declared points are dropped as "coordinates
the draw never read" while still producing `bp`-tagged replicate cells.
Verified two ways: code path
(`MECHANISM_RUNGS` / `_drop_inapplicable` in `boarding_axis.py`) and a
local smoke — a lo-point cell on `reportable` resolved
`initiation.prevalence` to 0.003936/0.003936, identical to the batch
canary; the same point on `shipped` resolved 0.025/0.007. The
import-pressure axis below therefore encodes prevalence as
rung×point conditions and splits `reportable` and `shipped` into
separate tiers so no dead replicate cells are generated.

## Mass-surface grid (frozen)

Axes, all scenario dials; nothing fitted:

- **Hulls:** `expedition_cruise_450` (450 agents),
  `classic_cruise_1900` (1910), `spirit_cruise_3000` (3000),
  `mega_cruise_5000` (7000 = emitted complement).
- **Voyage length:** 168 / 288 / 504 epochs (7 / 12 / 21 d).
- **Import pressure (rung × prevalence point):** `reportable`
  (**canary parity** — renewal-derived ~0.39% both roles, no declared
  points), `shipped` @ lo `{passenger 0.025, crew 0.007}`,
  `shipped` @ mid `{0.0325, 0.0185}` (licensed interval mid, also the
  unswept default), `shipped` @ hi `{0.04, 0.03}`. `shipped@mid` is
  the mechanism-controlled comparator against `reportable`; the lo→hi
  gradient on `shipped` is the measured NORO-IMPORT-01 mass lever.
- **Arms:** mono-GII.4 / mono-non-GII.4 / mixture — seed-paired
  everywhere, so every grid cell is a complete gate datapoint.
- **Seeds:** 8105–8124 (20), `variant_surveillance.enabled: true`,
  nominal mutation.

24 tiers per arm — per hull × voyage-length pair, one `rep` tier
(`reportable`, no prevalence key → 20 seeds) and one `ship` tier
(`shipped` × 3 points → 60 cells): **960 cells per arm, 2880 total.**

Frozen block, unchanged on every cell (verbatim from the canary):
surveillance `syndromic_comp65`, rung `reportable`,
`dose_adjustments [4.0]`, `config_overrides`
(`sanitary_visit_mode dwell_weighted`, `flush_aerosol_fraction 0.0`,
`flush_cabin_emission true`, `cabin_air_mode cabin_compartment`,
`hvac.pathogen_pool_transport airflow`, `variant_surveillance.enabled
true`).

- **Admissibility (frozen):** a grid cell is *powered* for the gate
  readout iff its per-arm aboard acquisitions across 20 seeds ≥40
  (≥2/seed mean). Cells under the bar are reported, not discarded —
  the surface itself maps where mass is achievable.
- **Selection rule (frozen):** the headline gate ratio is read on the
  powered cells, pooled by hull × voyage-length at each prevalence
  point; no cell is cherry-picked past the admissibility bar.
- **Failure rule (frozen):** if no grid cell powers up, report that
  immediately — do not relax another lever.

## Expected gate signature (binomial check, declared up front)

Under the declared class rels and non-secretor population share
f = 0.19, the challenged-population non-secretor fraction is
f·rel / (1 − f + f·rel):

- cell A (rel 0.10): 0.19·0.10 / (0.81 + 0.019) = 0.0229 → **≈2.3%**
- cell B (rel 0.45): 0.19·0.45 / (0.81 + 0.0855) = 0.0955 → **≈9.5%**

≈4.2× ratio. Resolution needs ≥40 aboard acquisitions per arm across
the 20 seeds — the per-cell admissibility criterion above.

## Cells

Three manifests, one per arm; each holds the same 24 tiers
(`fl_{exp,cls,spr,mega}_{7d,12d,21d}_{rep,ship}_geno02_<arm>`):

| manifest | genotype prior | cell |
|---|---|---|
| `noro_geno_02_mono_gii4_manifest.json` | `{"GII.4": 1.0}` | A — GII.4 class alone |
| `noro_geno_02_mono_nongii4_manifest.json` | `{"GII.17": 0.375, "GII.2": 0.625}` | B — non-GII.4 class alone, declared pre-era within-class split renormalized |
| `noro_geno_02_mixture_manifest.json` | shipped era-`pre` map (`GII.4` 0.6 / `GII.17` 0.15 / `GII.2` 0.25) | C — declared mixture |

Override mechanics unchanged from NORO-GENO-01:
`pathogen_configs.norovirus.overrides.norwalk_gi.strain_evolution.
prior_genotype_distribution` deep-patches the resolved profile;
`genotype_classes` deep-merges untouched (class structure, class
secretor rels 0.10 / 0.45, `transmissibility_multiplier` 1.0 identical
across all three arms). `variant_surveillance.enabled: true` at nominal
mutation on all cells. Run ids are shared across arms; the S3 prefix
(`campaign/noro_geno_02_{gii4,nongii4,mixture}/`) and manifest carry
arm identity.

## Readouts (declared up front)

- Aboard acquisitions per arm per cell
  (`strain_attribution.acquired_aboard`).
- **Aboard non-secretor share per arm with binomial CIs** — the
  discriminating readout (`non_secretor_acquired_aboard` /
  `acquired_aboard`; B should carry ~4× the share of A under the
  declared 0.45 vs 0.10 rel), read per powered cell and pooled by
  hull × voyage-length × prevalence.
- Per-class + per-genotype attribution on the mixture arm
  (`classes_ever_infected`, `classes_acquired_aboard`,
  `genotypes_ever_carried`; `lineage_census.json` strain→genotype map).
- Attack rate (`attack_rate_ever_infected`,
  `attack_rate_acquired_aboard`) — the mass surface itself.
- Imports per cell (establishment × prevalence × hull, the
  NORO-IMPORT-01 gradient under the genotype arms).
- Postings per 1,000 (`cumulative_reported_cases` / num_agents) —
  **report, never select**.

## Instruments and witnesses

Same as NORO-GENO-01, plus the new axes: `resolved_pathogen_profiles.json`
carries the pinned prior, intact `genotype_classes` (under
`strain_evolution`), and resolved `dose_adjustment` 4.0; on `ship`
tiers `initiation.prevalence` must equal the declared point (witnessed
0.025/0.007 on the lo-point smoke — on `rep` tiers the block records
the renewal-derived ~0.0039 and the declared-point witness does not
apply); `campaign_parameters` carries `boarding_mechanism_rung`,
`num_agents`, `num_epochs` per cell; `lineage_census.json` the truth
channel; `summary.json → strain_attribution.<pathogen_id>` the
per-agent attribution; `timeseries.json` the curve + postings marginal.

## Report immediately

- No grid cell reaches the ≥40 aboard/20-seed admissibility bar.
- The prior override fails to resolve; on `ship` tiers
  `initiation.prevalence` differs from the declared point; on `rep`
  tiers the rung resolves to anything but `reportable`; agent count or
  epoch axis fails to resolve in the result zip's resolved blocks.
- Per-class attribution is absent from outputs.
- Cell B's aboard non-secretor share lands below cell A's on the
  powered cells (gate folded backwards).
- A mono arm shows founders of the wrong class (any `GII.2`/`GII.17`
  on A, any `GII.4` on B in `lineage_census` / `genotypes_ever_carried`).

## Campaign gate

Preflight: one canary child on the new grid (spr × 504 ep × shipped@hi,
cell A — the largest expected-mass fast cell) inspected for axis
resolution + attribution + output contract before the arrays submit;
ETA reported at submission. The three 960-child arrays submit on the
user's go; verdict after the full read flips `NORO-GENO-02` `open` →
`measured` in a new ledger entry carrying the measured gate ratio on
powered cells (or the honest "unresolvable at this mass") and the
Batch job ids.

## Non-goals

Sweeping `transmissibility_multiplier` (the follow-on stage); any
dose-ledger/refit work; emesis near-field; VSP scoring; GI.1.
