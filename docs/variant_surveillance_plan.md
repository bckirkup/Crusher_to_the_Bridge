# Variant Surveillance Implementation Plan — CTB Paper 3

Work plan for `docs/variant_surveillance_spec.md` ("Cruise Ships as
Phylogenomic Observatories"). Written against the code as it stands at the
merge of #276. Nothing here is implemented yet; this document is the plan and
the list of places where the spec has to change to survive contact with the
simulator.

Companion planning docs: `docs/sentinel_surveillance_spec.md` (paper 2, whose
§5 deferred exactly this work), `docs/multi_pathogen_model_changes_spec.md`.

## 0. Summary of the substantive findings

Six things the spec does not account for. Each is expanded below.

1. **CTB transmission has no parent.** `TransmissionCore.execute_transmission`
   pools dose per `(agent, pathogen)` across six pathways and then draws
   infection once; the emitted `TransmissionEvent` carries
   `source_agent_id=None` (`engines/transmission_core.py:501`). "The strain the
   parent transmitted" does not exist as a quantity today. Phase 1's real work
   is a **strain-resolved dose ledger** plus strain composition in the
   environmental pools — not the `StrainState` dataclass.
2. **Cross-immunity has nowhere to read from.** An agent has a boolean
   `immune`, a per-pathogen `susceptibility_multiplier`, and per-pathogen
   `infections[pid]["status"]` — no record of *which* genotype it recovered
   from. §1.4 needs an immune history written at the per-pathogen recovery seam
   (`orchestrator_epoch.py:340`), and a genotype for the ~20% baseline immunes
   created at `immune_ratio` (`infection_dynamics_bridge.py:864`), who by
   construction never had an infection event.
3. **Within-voyage de novo phenotype evolution is not detectable at the spec's
   own rates,** and the paper's headline result (§7.3a) has to be re-aimed.
   Norovirus at `0.02 × 0.05 = 1e-3` phenotype-affecting mutations per
   transmission over a few hundred transmissions expects ~0.2–0.5 phenotype
   events *per voyage*, most of them neutral in effect size. What a 7-day
   closed cohort can actually show is **typing of introduced diversity**:
   multiple introductions, genotype competition, founder bottlenecks, and drift
   of neutral labels. De novo phenotype emergence is a Trek arm (Psi-2000 at
   `0.10 × 0.50` is 100× norovirus) and an explicit high-rate sensitivity arm.
   Campaigns must therefore seed **multi-genotype embarkation**, which the spec
   does not currently ask for.
4. **The genotype fields already exist and are asserted `None`.** The sentinel
   layer plumbed `genotype: str | None` through `observations.py`,
   `port_health.py`, `port_ledger.py`, `wastewater_ops.py`, and
   `export_line_list.py` with tests that pin the null
   (`tests/test_sentinel_data_contracts.py:339`,
   `tests/test_sentinel_export_line_list.py:133`). Phase 2 is filling a wired
   socket, and those two tests change meaning deliberately — behind the
   strain-state flag, default off, so every existing run stays bit-identical.
5. **§2.2 wastewater deconvolution belongs on the amplicon/long-read channel,
   not the metagenomic one.** `wastewater_assays.py` already establishes that
   compositional metagenomics is blind at cruise prevalence (0.064 expected
   pathogen reads at 0.26% prevalence in a 250k library). A Freyja-style
   lineage mixture over ~0 reads is noise. Strain deconvolution is a *nested*
   Dirichlet-multinomial inside the reads the `amplicon`/`long_read` modes
   allocate after the qPCR gate.
6. **§3's Federation ports are a data file, not code.** Port surveillance
   capability is already a regional JSON library with a schema
   (`picard_framework/analysis/sentinel/data/port_surveillance_<region>.json`,
   `schemas/port_surveillance.schema.json`, four regions). Federation ports are
   a fifth region; Starfleet itineraries are `voyage_config.json` under the
   existing `enterprise_constitution_tos` / `enterprise_galaxy_tng` platforms.
   No new port model, per `sentinel_surveillance_spec.md` §1.1.

## 1. What GutModelBacteriocins actually contributes

GutIBM is C++17/MPI/CUDA against CTB's Python, so this is **design reuse, not
code reuse**. Four things are worth copying:

| GutIBM artifact | What to take |
|---|---|
| `src/fixes/fix_mutation.{h,cpp}` | The typed mutation *menu* (duplication / recombination / receptor / super-killer / compensatory) instead of one undifferentiated "point mutation", and — directly usable — its immunity-escape draw: a fraction of escape mutants (`immunity_escape_prob`) with escape sampled from a range (`escape_affinity_lo..hi`), rather than a single scalar. CTB's `immune_escape` should be drawn the same way. |
| `src/genome/lineage_tracker.{h,cpp}` | The observable set: an event log (`BIRTH/DEATH/MUTATION/HGT/WASHOUT`) plus **periodic population snapshots** carrying `lineage_counts`, `num_lineages`, `dominant_fraction`, with `resident_retention(window)` and `dominant_lineage()` derived from them. This is exactly the drift/bottleneck result set the paper's §7.5 needs, and the snapshot-not-log design is what keeps a 8,500-run campaign's artifacts finite. |
| `src/genome/plasmid.cpp` + `src/fixes/fix_conjugation.cpp` | The v2 recombination template: donor/recipient pairing, a per-event record, and co-residence of two genetic elements in one host. CTB's co-infection prerequisite (spec §1.2) is the same structure — two lineages resident in one agent, recombination drawn per co-infected epoch. |
| Toxin lumping / dysbiosis guard | The performance discipline: lump strains below a frequency floor and cap live lineages, or strain-indexed pools grow without bound. |

One unit mismatch to state in Methods: GutIBM mutates **per cell division**
(1e-5..1e-8 per division); the spec mutates **per transmission**
(0.005..0.10). Those are not comparable numbers, and the spec's rates are
per-transmission-bottleneck substitution probabilities, which is the right
choice for CTB's epoch scale. Any later within-host generation model has to
convert explicitly.

## 2. Phase 1 — heritable strain state (PRs 1–5)

Everything is gated by `variant_surveillance.enabled` (default `false`) in
`crusher_labs/config.yaml`; with the flag off, no RNG draw changes, so golden
tests and the campaign manifests stay bit-identical.

**PR 1 — `StrainState` and the strain registry.**
New `engines/strain_state.py`: frozen `StrainState` dataclass with the spec
§1.1 fields, plus a per-run `StrainRegistry` owning id allocation, the founder
set, and the census. Per-pathogen strain parameters (§1.3) go into the existing
pathogen profiles (`data/pathogens/*.json`) as an optional `strain_evolution`
block, validated by `schemas/pathogen_profiles.schema.json` and
`tools/sanity_checker.py` (rates in [0,1], genotype list non-empty,
multiplier bounds positive). No simulator wiring. Tests: schema + registry
invariants, and the sanity checker rejecting out-of-range rates.

**PR 2 — strain-resolved dose ledger.**
The load-bearing PR. `agent_pathogen_doses[agent][pathogen]` becomes
`{(pathogen, strain_id): dose}` inside `execute_transmission`, each of the six
pathway helpers attributing its dose to the shedding source's strain
(`_pathway_direct_contact`, `_pathway_droplet`, `_pathway_hvac_airborne`,
`_pathway_fomite`, `_pathway_food_contamination`, `_pathway_environmental`).
The dose-response draw still runs on the **summed** dose, so infection
probability is unchanged; on success the parent strain is drawn multinomially
over the strain-weighted contributions, and `TransmissionEvent.source_agent_id`
/ `source_strain_id` are populated where the contributing pathway knows the
shedder. `transmissibility_multiplier` multiplies that strain's contribution at
emission, not the recipient's dose-response — otherwise a mixed exposure gets
the wrong marginal. Tests: dose conservation (Σ strain doses == legacy pooled
dose to float tolerance), parent-draw frequencies matching contribution shares,
and flag-off byte-identity of a 24-epoch run.

**PR 3 — mutation at transmission.**
`Agent.infect_with_pathogen` takes an optional `parent_strain`, and mutation is
drawn in one place: Bernoulli(`mutation_rate`), then
Bernoulli(`phenotype_mutation_fraction`), then a typed effect on one of
transmissibility / shedding / incubation / immune_escape with GutIBM-style
range draws. `n_mutations` and `generation` increment; `parent_strain_id` is
recorded. Recombination stays out (v2). Tests: graded sensitivity — a few
mutation rates produce a few different mean `n_mutations` and lineage counts —
plus bounds (multipliers finite and positive, `immune_escape` in [0,1],
`generation` monotone along a chain).

**PR 4 — strain composition in environmental pools.**
`zone_pathogen_mass` / `multi_pathogen_mass` / surface pools / food pools /
`env_contamination` reservoirs carry a strain mixture rather than a scalar,
with decay applied proportionally and a frequency floor (`min_strain_fraction`,
GutIBM's lumping) collapsing the tail into an `unresolved` bin so state stays
bounded. Extinct strains are garbage-collected from the registry once no agent
and no pool references them. Tests: mass conservation per pathogen across the
mixture, floor behaviour, and a memory/step-time ceiling check on a
2,000-agent run.

**PR 5 — immune history and cross-immunity.**
`agent.immune_history: list[ImmuneRecord]` appended at the per-pathogen
recovery seam (`orchestrator_epoch.py:340`) carrying pathogen, genotype,
epoch, and the strain's `immune_escape`. Baseline immunes drawn at
`immune_ratio` get a genotype sampled from a configured
`prior_genotype_distribution` so §1.4's matrix has an argument for them.
Protection at exposure is
`base_protection[prior_genotype][challenge_genotype] * (1 - immune_escape)`,
folded into the existing `susceptibility_multiplier` path rather than a new
branch in the dose-response. Cross-immunity matrices live in the pathogen
profile (`cross_immunity`), row-validated by the sanity checker. Tests:
same-genotype rechallenge is strongly protected, cross-genotype weakly, escape
mutants recover susceptibility monotonically in `immune_escape`.

## 3. Phase 2 — observation models (PRs 6–9)

**PR 6 — clinical specimen sequencing.**
Extend `crusher_labs/modalities/long_read_sequencing.py` and
`targeted_pcr.py` so a typed call is produced from the strain state under the
§2.1 gate: amplicon target, Ct threshold (reuse the existing Ct/LOD machinery
rather than a second one), per-base accuracy → probability of a miscalled
genotype, turnaround from `instrument_turnaround.json`, cost into
`data/config/resource_costs.json`. Accuracy below 100% must be able to produce
a *wrong* genotype, not merely a failed call; that is what makes the detection
speed result honest.

**PR 7 — wastewater strain deconvolution.**
In `picard_framework/analysis/sentinel/wastewater_assays.py`, the
`amplicon`/`long_read` modes gain a nested Dirichlet-multinomial over strain
proportions within the pathogen reads, true proportions weighted by each
shedder's `get_pathogen_shedding` and smeared by the holding-tank lag already
modelled in `wastewater_ops.py`. `metagenomic` stays blind by construction and
is the negative control. Tests: recovery of known mixtures at high depth,
degradation to non-informative at cruise-realistic depth, and dominance
ordering preserved.

**PR 8 — surface sampling strain recovery.**
Surface swabs report the strain mixture of the depositing agents from PR 4's
pools, with recovery probability by surface type and time since deposition.
Small PR; depends entirely on PR 4.

**PR 9 — genotype fields go live end-to-end.**
Fills the `genotype` sockets in `sentinel/observations.py`, `port_health.py`,
`port_ledger.py`, `export_line_list.py`, and the campaign bundle; bumps
`schemas/sentinel_observations.schema.json`; adds the per-epoch strain census
(lineage counts, `num_lineages`, `dominant_fraction`) to the telemetry writer,
with the full lineage event log behind a separate flag because a 8,500-run
campaign cannot carry per-event logs (see the GutIBM ECR/S3 retention
lesson — artifacts, not compute, are what overruns). The two tests that pin
`genotype is None` are rewritten as flag-conditional contracts.

## 4. Phase 3 — ports, economics, campaigns (PRs 10–13)

**PR 10 — Federation port region.** A fifth
`port_surveillance_federation.json` matching the existing schema, plus the
`voyage_config.json` itineraries for the two Enterprise platforms per §3. Note
that the spec's Risa population (50,000) and DS9 (3,000) are *port* populations
that only enter the hazard prior; nothing else in CTB consumes them.

**PR 11 — surveillance cost model.** The §4 scenarios as Presidio fleet
configs over `crusher_labs/cost_ledger.py` and `resource_costs.json`, with
onboard/ashore split and the OIS treatment already used for interventions. The
"variants detected" column of §4 is an *output*, not an input, and must be
deleted from the config or it becomes a circular assumption.

**PR 12 — campaign manifests.** Five designs under
`picard_framework/runs/mega_cruise_campaign/` reusing `campaign_runner.py` /
`tier_iterators.py` / expand_design, with multi-genotype embarkation and a
mutation-rate sensitivity tier added per finding 3. 8,500 runs is under half
the existing mega-campaign, so the AWS Batch Fargate Spot path
(`.agents/skills/aws-batch-campaign`) needs no change beyond a job definition.

**PR 13 — phylodynamic observables and figures.** Detection-speed curves
(ship vs ashore), lineage diversity trajectories, retention/bottleneck
statistics ported from `lineage_tracker`'s definitions, and the investment
frontier, in `picard_framework/analysis/figures.py`.

## 5. Validation plan

Following `sentinel_surveillance_spec.md` §6, since reviewers will ask the same
questions:

1. **Neutral-label recovery** — with all phenotype effects off, the observed
   genotype frequencies must be an unbiased read of the true mixture at high
   sequencing depth.
2. **Null** — one founder strain, mutation off: no spurious diversity, no
   spurious variant detections. Reports the false-positive detection rate.
3. **Bottleneck** — a single index case must show founder-effect diversity
   collapse; this is a claim of the paper, so it needs its own check.
4. **Confounding** — two genotypes seeded at embarkation with equal
   phenotypes; the analysis must not report a transmissibility difference.
   This is the check that finding 3 makes essential.
5. **Miscall robustness** — detection-speed conclusions re-run at the §2.1
   accuracies and at 100%, reporting the bias rather than hiding it.
6. **Power** — the minimum detectable transmissibility difference given voyage
   length, cohort size, and sequencing depth, reported as a curve. If the
   answer is "a 7-day voyage cannot see a 10% difference", that is a result.

## 6. Open questions for the author

1. Is Paper 3's headline meant to be *de novo* within-voyage evolution, or
   detection and typing of introduced diversity? Finding 3 says the second;
   §7.3a reads like the first.
2. Should Phase 1 make `transmissibility_multiplier` act at emission (per this
   plan) or on the recipient's dose-response? Emission is the defensible
   choice under mixed exposure but it changes the meaning of the parameter
   relative to the spec's "dose_adj modifier".
3. Co-infection by two strains of the *same* pathogen is currently impossible
   (`infections` is keyed by pathogen id and `is_infected_with` short-circuits
   re-exposure). Recombination v2 requires changing that key. Confirm it stays
   out of scope for Paper 3.
4. Sequencing costs (§2.1) — are those per-sample list prices or fully loaded
   with labour? `resource_costs.json` distinguishes the two.
