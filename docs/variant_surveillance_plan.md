# Variant Surveillance Implementation Plan — CTB Paper 3

Work plan for `docs/variant_surveillance_spec.md` ("Cruise Ships as
Phylogenomic Observatories"). Written against the code as it stands at the
merge of #276. Nothing here is implemented yet; this document is the plan and
the list of places where the spec has to change to survive contact with the
simulator.

Companion planning docs: `docs/sentinel_surveillance_spec.md` (paper 2, whose
§5 deferred exactly this work), `docs/multi_pathogen_model_changes_spec.md`.

**Integration branch.** All Paper 3 work lands on the long-lived
`paper3-variant-surveillance` branch, not `main`, so that `main` stays usable
for unrelated work while this capability is built (decision 6). Every PR in
§§3–5 targets that branch; it is rebased on `main` periodically and merged once
the capability is coherent. Practical consequence for the PR sequence: the
flag-off byte-identity tests matter more than usual, because they are the only
thing that will make the eventual merge to `main` reviewable.

## 0. Author decisions (2026-08-20)

Six rulings from the spec's author, folded into the plan below:

1. **Co-infection is in scope** as a deliberate design change, not deferred to
   v2. That promotes recombination into Paper 3 and reshapes Phase 1: see §3
   and PRs 3b–3c.
2. **Both evolutionary regimes get explored** — de novo emergence *and* typing
   of introduced diversity. The question the paper asks is how much ship
   surveillance can learn and on what timescale, so mutational supply becomes a
   swept axis rather than a fixed rate, and "nothing evolves in 7 days" is a
   reportable answer. See §1 finding 3 and PR 12.
3. **`transmissibility_multiplier` acts at emission.**
4. **Costs must support a two-community benefit split** — shore versus afloat —
   so the economics can ask whether ports would rationally pay into shipboard
   capability, including **in kind via labour** rather than cash. See §5 PR 11.
5. **The shore-side model gets built,** not stubbed or cited away, since
   decision 4's question cannot be answered without it. See PR 11b.
6. **Development happens on a long-lived branch,** `paper3-variant-surveillance`
   (see above), to keep `main` free for other work.

The spec is a starting point, not gospel; where this plan contradicts it, this
plan is the current intent.

## 1. Summary of the substantive findings

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
   own rates,** so mutational supply becomes a swept axis (decision 2).
   Norovirus at `0.02 × 0.05 = 1e-3` phenotype-affecting mutations per
   transmission over a few hundred transmissions expects ~0.2–0.5 phenotype
   events *per voyage*, most of them small in effect size. Two consequences:
   (a) the *introduced diversity* regime — multiple introductions, genotype
   competition, founder bottlenecks, neutral drift — needs **multi-genotype
   embarkation**, which the spec does not ask for; (b) the *de novo* regime
   needs a mutational supply the spec's per-transmission-only model cannot
   reach, because supply is then capped by the number of transmissions in a
   7-day voyage. So mutation gets a second, optional source: per-infected-
   agent-epoch within-host draws (PR 3), which is also the honest reading of
   GutIBM's per-division rates. The deliverable is a **time-to-detect versus
   mutational-supply curve** across both regimes, with Psi-2000 (`0.10 × 0.50`,
   100× norovirus) as the upper anchor.
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

## 2. What GutModelBacteriocins actually contributes

GutIBM is C++17/MPI/CUDA against CTB's Python, so this is **design reuse, not
code reuse**. Four things are worth copying:

| GutIBM artifact | What to take |
|---|---|
| `src/fixes/fix_mutation.{h,cpp}` | The typed mutation *menu* (duplication / recombination / receptor / super-killer / compensatory) instead of one undifferentiated "point mutation", and — directly usable — its immunity-escape draw: a fraction of escape mutants (`immunity_escape_prob`) with escape sampled from a range (`escape_affinity_lo..hi`), rather than a single scalar. CTB's `immune_escape` should be drawn the same way. |
| `src/genome/lineage_tracker.{h,cpp}` | The observable set: an event log (`BIRTH/DEATH/MUTATION/HGT/WASHOUT`) plus **periodic population snapshots** carrying `lineage_counts`, `num_lineages`, `dominant_fraction`, with `resident_retention(window)` and `dominant_lineage()` derived from them. This is exactly the drift/bottleneck result set the paper's §7.5 needs, and the snapshot-not-log design is what keeps a 8,500-run campaign's artifacts finite. |
| `src/genome/plasmid.cpp` + `src/fixes/fix_conjugation.cpp` | The recombination template, now in scope (decision 1): donor/recipient pairing, a per-event record, and co-residence of two genetic elements in one host. CTB's co-infection change is the same structure — two lineages resident in one agent, recombination drawn per co-infected epoch. |
| Toxin lumping / dysbiosis guard | The performance discipline: lump strains below a frequency floor and cap live lineages, or strain-indexed pools grow without bound. |

One unit mismatch to state in Methods: GutIBM mutates **per cell division**
(1e-5..1e-8 per division); the spec mutates **per transmission**
(0.005..0.10). Those are not comparable numbers — the spec's rates are
per-transmission-bottleneck substitution probabilities. Since decision 2 puts a
within-host source in scope (PR 3), the conversion has to be explicit in the
config: `within_host_mutation_rate` is per infected-agent-epoch, and any claim
relating it to a per-division rate needs a stated replication assumption rather
than a silent identification.

## 3. Phase 1 — heritable strain state (PRs 1–5, 3b–3c)

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
emission per decision 3, not the recipient's dose-response — otherwise a mixed
exposure gets the wrong marginal. Tests: dose conservation (Σ strain doses == legacy pooled
dose to float tolerance), parent-draw frequencies matching contribution shares,
and flag-off byte-identity of a 24-epoch run.

*As built* (`engines/strain_dose_ledger.py` + `TransmissionCore`): the ledger is a
shadow of the pooled dose rather than a replacement for it, so pooled dose,
route weighting, susceptibility scaling and the dose-response draw are the
original code path and the flag-off run makes no extra RNG draw. Three details
the spec left open. (a) Emission-side transmissibility is applied as the
emission-weighted mean multiplier (`EmissionMix.emission_factor`), which is
exactly per-strain emission scaling because every pathway kernel is linear in
emitted mass. (b) The lagged pathways — surfaces and food pools — carry their
own strain composition (`ReservoirComposition`, decayed with the pool it
shadows), so a pickup is attributed to what is still on the surface rather than
to whoever happens to be shedding now; environmental reservoirs get a founder
strain per pathogen, with a strain but no source agent. (c) Seeded and
pre-existing infections predate any strain, so the first time one is used as a
source it is minted a founder with a genotype drawn from
`prior_genotype_distribution` — which is where the introduced-diversity regime's
diversity comes from, one lineage per index case.

**PR 3 — mutation.**
`Agent.infect_with_pathogen` takes an optional `parent_strain`, and mutation is
drawn in one place: Bernoulli(`mutation_rate`), then
Bernoulli(`phenotype_mutation_fraction`), then a typed effect on one of
transmissibility / shedding / incubation / immune_escape with GutIBM-style
range draws. `n_mutations` and `generation` increment; `parent_strain_id` is
recorded. Per decision 2 the same operator is also reachable from an optional
**within-host** source — `within_host_mutation_rate` per infected-agent-epoch,
default 0 so the transmission-only model stays the baseline — which is what
lets the de novo regime have any mutational supply at all in a 7-day voyage.
`generation` stays a *transmission* generation count; within-host mutations
increment `n_mutations` only, so the phylogeny keeps its meaning. Tests: graded
sensitivity — a few rates produce a few different mean `n_mutations` and
lineage counts, from each source independently — plus bounds (multipliers
finite and positive, `immune_escape` in [0,1], `generation` monotone along a
transmission chain and unchanged by within-host draws).

*As built* (`engines/strain_mutation.py` + `TransmissionCore`): a mutation mints
a new lineage, and a transmission *without* one keeps the parent's strain id, so
a strain label means one genome rather than one infection — otherwise every
infection would be its own lineage and both the census and `generation` would
lose their meaning. Neutral mutations (the `1 - phenotype_mutation_fraction`
majority) still mint a lineage: they are visible to sequencing and invisible to
epidemiology, which is exactly the signal the typing arm reads. Phenotype
effects are multiplicative on transmissibility/shedding and additive on
incubation/immune escape, one axis per mutation, and multipliers are clamped to
[0.05, 20] because compounding an unbounded random walk over a long chain
eventually produces a strain that either cannot transmit or dominates by
numerical accident. The within-host source runs once per infected agent-epoch at
the top of `execute_transmission`, and does not mint founders for untracked
infections — founders still appear only when an agent first sheds, so enabling
the within-host source cannot change *who* is a founder, only what its
descendants look like.

**PR 3d — phenotype consumption.**
Of the four axes a mutation can move, PR 3 left only
`transmissibility_multiplier` consumed (at emission, PR 2), so a mutant was
epidemiologically distinguishable through one axis and any de novo result
understated variant impact. PR 3d wires the other three.

*As built.* Shedding and incubation travel *with the infection*: an acquired
strain's `Phenotype` is cached onto the infection record
(`strain_shedding_multiplier`, `strain_incubation_modifier`), so the shedding
curve and the epoch's illness draw read heritable effects without either call
site holding a `StrainRegistry`. Strain shedding multiplies the host's own
`shedding_variance_log10` draw rather than replacing it — host variation and
strain variation are different things and the typing arm needs to be able to
confuse them. Incubation shifts the symptom-onset gate, whose baseline is now
`symptom_onset_day` on the pathogen profile (default 1.0, the legacy value).
Immune escape is read at dose-response time instead, because protection depends
on both the challenge strain's genotype and what the host's immunity was raised
against: `_challenge_protection` takes the dose-share-weighted mean of
`effective_protection` over the strains actually challenging the agent, so a
heterologous or escape mutant breaches an immunity a homologous strain would
not, and dose that no strain claims stays in the denominator with zero
protection. Absolute immunity survives wherever the pathogen declares no
`cross_immunity` or the flag is off, which is what keeps legacy runs identical.

*Known limit, worth a decision.* Negative `incubation_modifier` draws are
currently inert for every shipped pathogen: progression is evaluated from day 1
post infection onward, and the baseline onset is day 1, so "faster" has nowhere
to go. The `symptom_onset_day` seam makes the negative half live for any
pathogen given a later baseline (SARS-CoV-2 at ~5 days being the obvious
candidate), but setting one changes main-line presentation timing — hence
detection timing, hence every headline result — so it is left unset here rather
than folded into a phenotype PR.

*Resolved by PR 7b.* A point onset day was the wrong instrument: incubation is
now a per-infection draw from a per-pathogen distribution conditioned on dose
and host biology, which subsumes `symptom_onset_day` and retires the seam.

**PR 3b — co-infection and within-host competition (decision 1).**
The blocking design change. `agent.infections` is keyed by pathogen id and
`execute_transmission` skips any agent already infected
(`transmission_core.py:467`), so a second strain of the same pathogen can never
establish and recombination has no substrate. Change: `infections[pid]` gains a
`strains: dict[strain_id, StrainInfection]` map carrying each strain's own
`time_infected`, `acquired_particles`, and `shedding_multiplier`; re-exposure of
an infected agent is evaluated against a `superinfection_susceptibility` factor
(homotypic interference, per pathogen) instead of being skipped; shedding is the
competition-weighted sum over resident strains; recovery is per strain, and the
pathogen-level status stays `INFECTED` until the last strain clears so every
existing consumer of `infections[pid]["status"]` keeps working.
`is_infected_with` keeps its current meaning; a new `resident_strains(pid)` is
the strain-aware accessor. Tests: superinfection frequency responds
monotonically to the interference factor; single-strain runs stay identical to
PR 2 behaviour; pathogen-level status and legacy fields unchanged under
co-infection; shedding conserved against the sum of per-strain curves.

*As built.* `infections[pid]["strains"]` holds a `StrainInfection` per resident
lineage, each with its own day post infection and establishing inoculum, so a
strain acquired on day four starts at the head of its own shedding curve inside
a four-day-old infection and clears on its own schedule. Competition is
implemented as partition rather than addition: resident lineages divide the
host's shedding capacity in proportion to establishing inoculum × heritable
shedding multiplier, so two strains in one host never out-shed the same host
carrying one, and a fitter or larger-inoculum lineage takes over the mixture.
Those same shares split the host's emitted mass in the dose ledger and in the
lagged surface/food reservoirs, which is what makes an onward transmission
attributable to one of the lineages a co-infected host carries. Pathogen-level
fields keep describing the *primary* lineage (illness onset belongs to the
infection, not to whatever superinfects it later); if the primary clears first,
the longest-resident survivor inherits them, and the infection stays `INFECTED`
until the last lineage goes. Within-host mutation now replaces one resident with
its descendant, clock and inoculum intact, instead of overwriting the mixture.

Two judgement calls worth knowing about. First, the gate is
`p_superinfection = p(dose) × (1 − cross-immunity protection) ×
superinfection_susceptibility`: the susceptibility factor is the
*non*-genotype-specific niche interference, because genotype-specific
interference already arrives through `cross_immunity`, which reads the resident
strain as the host's prior exposure — so a homologous challenge is rejected by
immunity while a heterologous one is only discounted. Second, this PR also
un-blocks something PR 3d shipped inert: `_get_susceptible` filtered immune
agents out before any dose was computed, so an escape mutant could never reach
the immunity it was built to escape. Immune agents are now challengeable
whenever the pathogen declares `cross_immunity`, and a breakthrough moves the
host out of the immune compartment. Both widenings are gated on strain tracking,
so a flag-off run keeps skipping infected and immune agents exactly as before.

**PR 3c — recombination (promoted from v2 by decision 1).**
With co-residence available, recombination is drawn per co-infected
agent-epoch: two resident strains produce a child inheriting each phenotype
axis from one parent (uniform crossover over the four axes plus `genotype`),
with `parent_strain_id` extended to a parent *pair* and a `recombinant: bool`
flag on `StrainState`. This is `fix_conjugation`'s donor/recipient event record
with both parents inside one host. Tests: recombinants only in co-infected
hosts; each child axis traces to one of its two parents; rate sensitivity; a
recombination-off run matching PR 3b exactly. Recombination also changes what
sequencing can reconstruct — an amplicon over one locus cannot see a crossover
elsewhere in the genome — so PR 6 must record which loci each assay covers.

*Implemented.* One Bernoulli per co-infected host-epoch at the pathogen's
`recombination_rate`, drawn after within-host mutation so a lineage that mutated
this epoch is what recombines. On a hit two distinct residents are drawn: the
first is the *recipient*, whose slot the recombinant takes over — inheriting its
day post infection, inoculum, and infection epoch — and the second is the
*donor*, which stays resident. So one event never widens a host's mixture;
only superinfection does. Crossover is uniform and per axis rather than
single-point, because CTB has no locus order to put a crossover coordinate on:
the four phenotype axes and `genotype` are each drawn 50/50 from one parent.
`generation` and `n_mutations` take the more derived parent's value, since
recombination passes no transmission generation and adds no substitution, and
the mosaic is at least as far from the founder as its more travelled parent.
Ancestry is recorded recipient-first, so `lineage_root` follows the lineage the
recombinant physically replaced. Note for the campaign arms: the *population*
does diversify faster than PR 3b even though single events do not, because a
recombinant is a new lineage that can later superinfect a host already carrying
both of its parents — three-way resident mixtures are reachable only this way.

**PR 4 — strain composition in environmental pools.**
`zone_pathogen_mass` / `multi_pathogen_mass` / surface pools / food pools /
`env_contamination` reservoirs carry a strain mixture rather than a scalar,
with decay applied proportionally and a frequency floor (`min_strain_fraction`,
GutIBM's lumping) collapsing the tail into an `unresolved` bin so state stays
bounded. Extinct strains are garbage-collected from the registry once no agent
and no pool references them. Tests: mass conservation per pathogen across the
mixture, floor behaviour, and a memory/step-time ceiling check on a
2,000-agent run.

*Implemented.* Every lagged pool the engine doses from — zone aerosol (read by
the HVAC pathway from `zone_pathogen_mass` / `multi_pathogen_mass`), surfaces,
food, and the `env_contamination` reservoirs — now carries a
`{(strain, depositor): mass}` composition that ages with the same factor as the
scalar pool it shadows, so a pickup is attributed to what is *in* the pool
rather than to whoever happens to be shedding at pickup time. Aerosol
composition is read before this epoch's shedding is added, which is what makes a
downstream HVAC dose inherit the air already standing in the target zone;
upstream shedders remain the fallback for air the composition does not yet
cover. A zone-scoped environmental reservoir is minted a founder lineage at its
own standing mass the first time it is read (a spa biofilm or spore load has a
lineage no host deposited), and under strain tracking a shedding occupant now
adds `ENV_HOST_DEPOSITION_FRACTION` of its emission to both the reservoir and
its composition, so the two describe the same pool. With tracking off no
composition exists and no host input is added, so the scalar reservoir is the
legacy reservoir exactly.

Two semantics worth stating because they change what a pool assay can claim.
First, the frequency floor conserves mass exactly rather than truncating: below
`min_strain_fraction` a contributor's *depositor* is forgotten first (the lineage
survives, its provenance does not), and a lineage still below the floor moves to
an `unresolved` pseudo-strain. That bin is deliberately never registered, so a
dose drawn from it yields *no* parent strain — the acquiring host is minted its
own founder — and it contributes nothing to cross-immunity recognition while
staying in the denominator at zero protection. This is the modelling statement
that a pool assay cannot call a variant below its limit of detection: the mass
is real, the lineage is not attributable. That floor is a property of the
*state representation* (it bounds a pool at roughly one entry per resolvable
lineage regardless of host count); the depth of a particular assay is a design
choice and stays in PR 6, so the two must not be conflated. Second, the largest
lineage is always kept even when every share is sub-floor, so a flat mixture
never collapses a pool to pure `unresolved`.

Registry collection runs once per epoch: a lineage is live if an infection
carries it (any resident of a co-infection, not only the primary) or if a pool
still holds more than `POOL_EXTINCTION_MASS` of it, and the ancestry of anything
live is retained — both parents of a recombinant included — because
`lineage_root` and the tree an assay reconstructs are the point of the exercise.
Ids are monotone, so a collected id is never reused. The environmental founders
are also held, one per pathogen, since they are reused whenever a reservoir is
re-seeded.

**PR 5 — immune history and cross-immunity. (implemented)**
`agent.immune_history: list[ImmuneRecord]` is appended at the per-pathogen
recovery seam, one record per *lineage* as it clears rather than one per
infection: a co-infected host resolves two exposures and comes out with memory
of both genotypes, which is exactly what makes sequencing a mixed infection
worth doing. Each record carries pathogen, genotype, strain id, the epoch it
cleared, and the strain's `immune_escape`, and is a **self-contained snapshot**
rather than a pointer into the registry — PR 4's collection forgets a lineage
once no host and no pool carries it, while the immunity it raised has to outlive
it. That also removes a latent failure: the old single prior read the recovered
infection's `strain_id` straight out of the registry, which a collection could
already have dropped.

Protection at exposure is
`max_over_priors(base_protection[prior][challenge]) * (1 - immune_escape)`,
dose-share weighted over the challenging strains as before. The maximum, not a
sum: repeated exposure to related genotypes does not stack past what the closest
match already gives, and a host that has met the challenge genotype itself is
protected as if its heterologous exposures had not happened. Priors come from
three places — the immune history, the lineages still resident (an ongoing
infection interferes before it clears), and, for an agent immune at embarkation,
one genotype drawn from `prior_genotype_distribution` and now also written to
the history as an `embarkation` record at epoch 0, since that immunity predates
the run. Unattributed and sub-floor `unresolved` dose still carries no genotype
to recognise and stays in the denominator at zero protection.

Cross-immunity matrices live in the pathogen profile (`cross_immunity`) and are
row-validated by the sanity checker, which now also warns on the two shapes that
are mistakes rather than models: a declared genotype with no row (silently making
every host that resolved it fully susceptible) and a row protecting better
against some other genotype than against itself.

With variant surveillance off nothing is recorded and immunity stays absolute,
so the legacy compartment is unchanged. Tests in `tests/test_immune_history.py`:
homologous rechallenge beats heterologous, escape grades protection down
monotonically to zero, a two-genotype history is scored on the best match,
repeat exposure does not stack, protection survives the lineage being collected,
and history length tracks resolved exposures rather than epochs.

## 4. Phase 2 — observation models (PRs 6–9)

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

*Delivered.* Two things the implementation settled that the sketch left open.
Reads are **conserved, not renormalized**: a lineage below the reporting floor,
and PR 4's untracked `unresolved` pool mass, stay counted as
`lineage_unresolved_reads`, so a row states how much of its library it actually
typed (`resolved_lineage_fraction`) rather than reporting a composition summing
to one. And the failure mode is graded by two separate dials — `min_pathogen_reads`
(a library too shallow to separate anything) versus `min_lineage_reads` /
`min_lineage_fraction` (a minority lineage present but unreportable) — because
the paper's claim about sufficient depth depends on which of the two bites.

**PR 7b — incubation as a distribution (supersedes the `symptom_onset_day`
decision).** Parameters and provenance live in
[`ctb_incubation_spec.md`](ctb_incubation_spec.md); this section records only
what the implementation does with them. `engines/incubation.py` draws one
lognormal or gamma incubation period per infection, conditioned on the
establishing inoculum (`dose_log10_shortening` above `dose_reference_log10`,
clamped below by a per-pathogen `dose_floor`) and truncated to the pathogen's
plausible window; the draw is persisted on the infection record, and
`incubation_modifier` shifts the drawn value, which is what finally makes the
negative half of that phenotype axis live. A profile with no `incubation` block
keeps the legacy fixed-onset path exactly, so pathogens are migrated one at a
time.

Three deliberate departures from the sketch. The profile states `median_days`
and `dispersion` rather than the spec's `mu`/`sigma`, because a reviewer reads a
median in days and a geometric standard deviation, and the lognormal parameters
are recoverable from them exactly. `host_factors` exist in the schema but are
*absent* from every shipped profile: the spec's own reading is that frailty
moves severity strongly and incubation at most weakly, so host conditioning is a
sensitivity arm rather than a main-line default — a test asserts both the
absence and that switching the axis on still moves onset. And
`dose_reference_log10` is each profile's own beta-Poisson `N50` in model units,
not the spec's literature figure in RT-PCR units or TCID50: taking the
literature unit literally put every simulated host three or more log10 above the
reference, pinned the dose factor at the floor, and moved main-line onset enough
to flip both golden trigger fixtures from `BASELINE` to `CONFIRMED` — a constant
acceleration masquerading as dose conditioning. Referenced to `N50` the goldens
are unchanged, a typical host presents at the literature median, and both
directions of the dose effect stay reachable; a regression test asserts the
reference is not saturating. What remains uncalibrated is the *magnitude* of the
shift at a given simulated dose, so its direction can be claimed and its size
cannot.

What PR 7b left inconsistent across the repository — three incubation
representations, a sentinel delay catalog that is not derived from the profiles,
13 profiles still on the fixed-onset fallback, and a calibration axis the dose
term now interacts with — is audited and sequenced in
[`incubation_reconciliation_plan.md`](incubation_reconciliation_plan.md),
together with the re-fit and `main`-exposure calls.

Still unimplemented from the spec, each its own scoped work: the frailty score
and its severity coupling, wearable-baseline coupling and pre-symptomatic
anomaly lead time, long-shedder behaviour, gamma-fitted variant lineages
(Alpha/Delta), and the remaining pathogen rows beyond norovirus and SARS-CoV-2.

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

## 5. Phase 3 — ports, economics, campaigns (PRs 10–13)

**PR 10 — Federation port region.** A fifth
`port_surveillance_federation.json` matching the existing schema, plus the
`voyage_config.json` itineraries for the two Enterprise platforms per §3. Note
that the spec's Risa population (50,000) and DS9 (3,000) are *port* populations
that only enter the hazard prior; nothing else in CTB consumes them.

**PR 11 — surveillance cost model and the two-community benefit split
(decision 4).** The §4 scenarios as Presidio fleet configs over
`crusher_labs/cost_ledger.py` and `resource_costs.json`, with the OIS treatment
already used for interventions. The "variants detected" column of §4 is an
*output*, not an input, and must be deleted from the config or it becomes a
circular assumption.

Beyond that, the ledger has to answer *who benefits*, which needs two things it
does not have:

- **In-kind contribution as a first-class cost line.** A port paying in labour
  (seconded technician hours, shared bioinformatics staff, reagent supply) is
  not a cash transfer, so `cost_ledger` gains a contribution record with a
  payer (`ship_operator` / `port_authority` / `public_health_agency`), a medium
  (`cash` / `labour_hours` / `consumables`), and an explicit conversion rate to
  monetary equivalent so sensitivity to that rate is reportable. Net cost *per
  payer*, not one total, is the output.
- **Shore-side benefit is not simulable in CTB today, and must not be
  invented.** CTB simulates the ship; ports enter only as a hazard prior and a
  capability profile (`port_health.py`, `port_ledger.py`). There is no shore
  transmission model, so "cases averted ashore" cannot come out of the ABM.
  The defensible construction is a downstream analytic layer: the ABM yields
  *earlier detection* and *fewer infectious disembarkations* per scenario, and
  a shore model (PR 11b) converts those into shore cases averted. The paper
  then reports the shore:afloat benefit ratio, and a port's
  willingness-to-pay threshold as the point where its share of benefit exceeds
  its share of cost.

**PR 11b — shore-side transmission model (decision 5).** New
`picard_framework/analysis/shore/`, deliberately *not* a second agent-based
model: a compartmental/renewal layer for the port community, seeded by CTB
output and small enough to run inside a campaign's post-processing.

- **Interface from the ship.** Per port call, the ABM already knows who
  disembarks and in what infection state; the shore model consumes an
  importation vector (infectious disembarkations by epoch, with their strain
  labels from Phase 1) plus the detection timestamp from Phase 2. That interface
  is the only coupling, which keeps the shore model swappable and testable in
  isolation.
- **Dynamics.** A renewal process (or SEIR, if age structure earns its keep) on
  the port population with its own `R_shore`, generation-interval
  distribution, and a reporting delay drawn from the port's existing
  surveillance capability in `port_surveillance_<region>.json` — so the ports
  already parameterised for Paper 2 carry over rather than being re-specified.
- **Counterfactual.** Benefit is the difference between two shore trajectories:
  importation timed by *shipboard* detection versus by the port's own detection
  latency. That difference, not an absolute case count, is what the economics
  needs, and it is far less sensitive to `R_shore` than either arm alone — worth
  showing explicitly.
- **Honesty about scope.** Strain-resolved shore spread is only as good as the
  importation labels; the model must not claim shore-side *evolution*. It
  propagates what the ship exported.
- **Tests.** Zero importations → zero shore cases; monotone benefit in detection
  lead time; `R_shore < 1` produces bounded outbreaks and the total scales
  linearly in importations (the check that the renewal implementation is
  right); and a sensitivity sweep over `R_shore` and the importation multiplier
  reported as a surface rather than a point.

**PR 12 — campaign manifests.** Five designs under
`picard_framework/runs/mega_cruise_campaign/` reusing `campaign_runner.py` /
`tier_iterators.py` / `expand_design.py`. Per decision 2 mutational supply is
swept in both regimes rather than fixed: a *diversity* arm (multi-genotype
embarkation, 1–4 founders, nominal per-pathogen rates) and an *emergence* arm
(single founder, per-transmission and within-host rates swept over ~2 decades
around nominal), crossed with voyage length so the answer is a timescale rather
than a single number. Co-infection interference and recombination rate get one
sensitivity tier each. The spec's 8,500 runs is under half the existing
mega-campaign, so the AWS Batch Fargate Spot path
(`.agents/skills/aws-batch-campaign`) needs no change beyond a job definition —
but the added axes push the count up, so it gets re-counted with
`count_manifest_cartesian.py` before submitting.

**PR 13 — phylodynamic observables and figures.** Detection-speed curves
(ship vs ashore), lineage diversity trajectories, retention/bottleneck
statistics ported from `lineage_tracker`'s definitions, and the investment
frontier, in `picard_framework/analysis/figures.py`.

## 6. Validation plan

Following `sentinel_surveillance_spec.md` §6, since reviewers will ask the same
questions. Items 1–4 are regime-independent; 5 is new with co-infection:

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
5. **Co-infection neutrality** — with recombination off and interference at the
   neutral value, co-infection must not change pathogen-level incidence or
   shedding totals. It is a new pathway into the transmission model, and this
   is the check that it did not quietly change the epidemiology.
6. **Miscall robustness** — detection-speed conclusions re-run at the §2.1
   accuracies and at 100%, reporting the bias rather than hiding it.
7. **Power** — the minimum detectable transmissibility difference given voyage
   length, cohort size, and sequencing depth, reported as a curve. If the
   answer is "a 7-day voyage cannot see a 10% difference", that is a result,
   and per decision 2 it is one of the results the paper is for.

## 7. Open questions for the author

The author's six rulings are in §0. What is still open:

1. What should `superinfection_susceptibility` default to? It sets how often
   co-infection — and therefore recombination — happens at all, so norovirus
   co-infection frequency in closed outbreaks is the citation to hunt for.
2. Sequencing costs (§2.1) — per-sample list prices or fully loaded with
   labour? `resource_costs.json` distinguishes the two, and decision 4's
   labour-medium contributions make the distinction load-bearing rather than
   cosmetic.
3. What sets `R_shore` and the port generation interval in PR 11b? The
   structure is ours to build, but those two numbers decide the shore:afloat
   ratio, so they need a literature anchor per pathogen (norovirus community
   transmission in particular) rather than a value chosen to make the ports'
   case.
4. Should the shore model track the port's *resident* population only, or also
   onward transmission to other travellers? The second closes a loop back to
   the fleet and is the more interesting claim, but it is a bigger model.
