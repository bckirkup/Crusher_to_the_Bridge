# Paper 1 pre-freeze contract review

21 November 2026 · Read-only review for Benjamin Kirkup

Distribution A (26-140): Approved for public release; distribution is unlimited.

## Decision

**I endorse the scientific program and the proposed reference configuration as the basis for evaluation. I recommend a bounded contract revision before declaring the freeze.** The revised contract should make the intended populations and outputs executable, preserve legitimate scenario contrasts, and use the bridge to establish interpretability rather than require a favorable scientific result. No new biological mechanism is needed to address these review findings.

The repository has implemented the practical prerequisites efficiently: a dedicated historical vessel, a regenerable platform recipe with commissioned transport attributes, an explicit baseline block, source-located configuration checks and the six outcome families needed for the paper. The four-hull program, temporal reconstruction, scale experiment and protective-response example remain the right combination. The principal corrections below make that program easier to execute and interpret.

This is a review recommendation. I have neither declared the freeze nor authorized or launched a campaign.

## What I would retain

- The four cruise archetypes, with the dedicated Explorer vessel alongside the large-ship archetype for the historical reconstruction.
- A named immutable source reference and image digest for each campaign, while leaving independent project development free to continue outside the reference.
- The continuous contamination calculation as the baseline, preserving the older discrete calculation as a specifically labeled comparison if used.
- The distinction between clinical illness, reported illness, reporting-threshold events and first-role chronology.
- The 7-, 12- and 21-day joint-evaluation scenarios; the historical reconstruction has its own observation-window definition.
- The staged sequence: a bounded bridge and temporal pilot, followed by informative contrasts and precision-driven expansion.
- Preservation of the old campaigns as version-specific development evidence, with fresh measurements supporting claims about the new reference.

## Required contract corrections

### 1. State and verify actual role populations, not only total agents

The contract lists total populations and the Explorer platform declares 3,245 passengers/1,183 crew. The checker builds its runs from a template using the generic YAML agent classes, which take precedence over the binary passenger fraction. It verifies initialization, not actual role counts. The manifest path inspected does not itself translate a platform's nominal role declaration into exact agent-class counts.

I independently applied the class-allocation arithmetic from the engine to the template fractions; this is a static arithmetic check, not an initialized model run:

| Platform | Total agents | Role counts implied by template classes, passenger / crew | Nominal platform declaration |
|---|---:|---:|---:|
| Expedition | 450 | 316 / 134 | 300 / 150 |
| Classic | 1,910 | 1,338 / 572 | 1,350 / 560 |
| Spirit | 3,000 | 2,100 / 900 | 2,100 / 900 |
| Mega | 7,000 | 4,900 / 2,100 | 5,000 / 2,000 |
| Explorer | 4,428 | 3,102 / 1,326 | 3,245 / 1,183 |

**Action:** record the intended role counts for each reference scenario and assert them on the actual initialized agents and in each outcome payload. Preserve the historical archetype allocations as a labeled baseline if desired. The Explorer reconstruction should use exact investigation counts through the existing exact-class-count facility, with the within-role class allocation declared. Its historical-archetype comparison should explicitly say which population differences are retained and which are controlled.

This makes the passenger/crew evaluation scientifically precise and gives the later composition experiment a clean starting point.

### 2. Make the effective mechanism state consistent on Explorer

The frozen block requests the exposure cap on. In the implementation, activation also requires the platform identifier to be in the rhythm/event catalog. The four archetypes are present; Explorer is absent. The effective cap therefore differs between the historical vessel and the archetype even with the same requested block. Five-hull parse/initialization checks miss this because the resolved-state probes are performed only on Expedition.

**Action:** resolve this before freezing Explorer's same-mechanism comparison. Prefer an explicitly reviewed eligibility correction matching the intended cruise-platform scope, with per-hull effective-state assertions and no accidental import of another ship's activity schedule. Alternatively, reserve and label Explorer as a deferred exception; its comparison then waits for the corrected reference. A nominal platform-class label alone is not a fix.

This is a bounded implementation/configuration issue, not evidence about the magnitude of the cap's epidemiological effect. It should be handled before full reference freezing rather than discovered during a large campaign.

### 3. Make the six-family output promise explicit in the worker contract

The endpoint machinery exists, but it is not all collected by an ordinary compact campaign:

- Clinical-onset collection needs an explicit Sentinel line-list request.
- First-role threshold is derived from role-specific cumulative reports, with passenger-first, crew-first, same-epoch ties, neither and missing states defined.
- Environmental assay records are retained in full telemetry, whereas ordinary compact records and generic summaries omit the necessary assay payload.

**Action:** declare a core compact outcome record plus a prospectively selected environmental/full-telemetry panel, or add output-only compact harvesting for every promised family. Preserve swab location, time, recovered amount/density units and detection/censoring information. Keep the holding-tank wastewater measurement distinct from the separate sequencing channel. Include onset/reporting coverage and role denominators in the extraction fixtures before the bridge design is executed.

This is a data-contract correction; it uses existing scientific machinery rather than adding an unrelated model feature to obtain observations.

### 4. Separate bridge completion from the scientific outcome

The present gate requires quiet-designated strata to remain quiet, outbreak-designated strata to post and near-threshold-designated strata to lie between them on every hull. Nonposting or a reversal can automatically void the freeze and return to mechanism work.

**Action:** make technical completion and scientific interpretation separate decisions. A clean bridge establishes that intended inputs were used, outcomes can be extracted, independent attempts are accounted for and paired comparisons are meaningful. Its observed event rates then guide the next informative study or additional precision. A zero-event large-hull stratum is a measured result, not automatically an implementation fault.

Keep the substantive scientific standards for model utility and external comparison. This separation is not permission to claim adequate performance from an unfavorable result. Require a predeclared scientific continuation decision, but allow more than one valid continuation: temporal reconstruction, population/geometry comparison, targeted uncertainty evaluation, precision expansion or a justified defect correction. This retains all four hulls and lets the work earn its conclusions.

### 5. Freeze an invariant baseline and allow declared experimental differences

The contract says every cell carries the baseline block verbatim and changing any pinned value is prohibited, while the planned work includes supply-structure, uncertainty and response arms that intentionally change settings.

**Action:** distinguish an invariant baseline from prospectively declared arm differences. Every arm should retain the baseline reference, declare its changed paths, materialize the complete effective nested objects required by the shallow merge, and record the resolved effective configuration. Validate it after the runner has applied every axis, because later generated overrides can replace tier values. A difference in an approved experiment is not an undeclared default change. An unplanned biological change restarts the reference/version decision.

This preserves both reproducibility and the scientific comparisons the first paper needs.

### 6. Qualify and tighten the configuration checker

The checker is a useful improvement over parsing alone. Its 57 declared checks include **50 resolved-state probe entries and seven configuration-plus-source-string checks, covering 70 scalar JSON leaves in total**. The latter include transport selection, observation switches and escalation. Four declared units are grouped dictionaries; several projections inspect only one field. The reported “zero differences from default” therefore applies to the tested representation, not a complete runtime behavioral comparison.

One bounded error-path correction is needed: any exception during an alternate-value initialization is classified as a live pin. Using the actual extracted helper with mocked dependencies, an unrelated missing-file error returned `live (flip rejected: FileNotFoundError)`. No model code was imported or initialized in this test.

**Action:** unexpected initialization errors fail the check; deliberately expected validation failures are recorded separately with their specific reason. Report initialization evidence and configuration-only evidence as separate categories. Rerun the checker on the final named source and retain its output. The bridge supplies the later runtime evidence, including effective transport selection and resolved baseline state. Full grouped cleaning/source settings should be checked, while conditionally inactive controls such as discrete ordering under the continuous pathway are labeled as conditional rather than independently influential.

## Decisions I would affirm without reopening mechanism development

**Sanitary visits and flush aerosol.** Keep the shipped `none`/zero choices for the baseline. They define a clear reference; a sourced alternative can be declared as a later comparison. There is no need to choose a new value to obtain a preferred outcome.

**Escalation.** Preserve the campaign's 2% suspected, 3% confirmed and 5% lockdown thresholds, with the effective definitions and response consequences recorded. The YAML-versus-runner distinction is already identified and can now be made explicit in the complete scenario.

**Usual recognition.** Keep the named syndrome-based strategy as the baseline, including its class-dependent compliance configuration. Record it alongside the frozen block and make the response demonstration's specific changes explicit. Include the configurable reported-case counter thresholds, role filters, confinement actions and recognition/reporting settings: the hard-coded either-channel aggregation does not freeze those upstream choices.

**Provisioned source.** Keep the generic registry source and station-lot formulation as the declared reference. Resolve and save their actual source values and boarding choices in the complete scenario record. Diagnostic selected-seed strata and population-weighted voyage inference remain different analyses.

## Work-package decisions and proportionality

### Bridge size and statistical meaning

The literal seed table implies 4 hulls × 3 durations × (20 + 100 + 300) = **5,040 trajectories at one reference**, before tail-resolution work; duplicating that grid across old and new references would give 10,080. This is larger than the intended modest bridge.

Use a small complete four-hull bridge first, then the temporal pilot and a joint-outcome pilot to allocate replication. Keep all planned voyage durations in the scientific evaluation, but purchase precision where it improves the claim. Zero events in 300 yields an exact 95% one-sided upper event-probability bound near 0.994%; its convention and sampling frame should be stated. A thousand voyages is not automatically a thousand posted outbreaks: conditional tail precision follows the number of eligible events and their weights.

The next-stage design should state endpoint-specific precision, batch/analysis rules and source-stratum inclusion probabilities. Previously selected seeds remain diagnostic evidence; independently sampled evaluation seeds and justified source weights support population estimates.

### Explorer reconstruction

The dedicated platform is a substantial advance and should stay in the reference. The independently checked recipe reproduces the committed spatial layout exactly. It reproduces the airflow layout apart from five positive commissioned exchange fields, as expected; all three platform JSON schemas validate. The reported code/initialization smoke adds practical usability evidence; the reconstruction will evaluate scientific agreement.

Before the historical campaign, fix its date-to-epoch mapping and correct role allocation. February 26–March 5 spans eight calendar dates but seven elapsed days. A 192-hour simulation can be a declared inclusive-day approximation, but it must not silently add a full day of exposure or replace exact embarkation/disembarkation timing. If original times remain unavailable, declare the convention and use an appropriately bounded timing sensitivity. Preserve the 252/20 onset counts with the investigation denominators, separately from 243/19 posting counts and the posting crew denominator.

The platform's published passenger layout, documented estimated volumes, service-space placement and ventilation grouping are a proportionate basis for a vessel-specific model. A final check should ensure a frozen baseline can disable response actions consistently on both historical and archetype hulls, and any active response refers to valid vessel zone IDs. The scientific comparison can then ask directly how much the dedicated representation matters.

### Historical evidence and future claims

The execution assessment's blanket suggestion that almost every old quantitative result is void should be replaced by a version- and mechanism-specific disposition. The explicit dose-refit amendment predates the November focal experiments; specific earlier withdrawals remain specific. The new bridge measures transfer to the new reference. It does not restore, erase or rerun historical outputs by declaration.

### Moratorium scope

Protect the named evaluation reference and effective configuration. Unrelated work can continue on other repository revisions. New telemetry that changes an archive's metadata is not itself new biology; scientific-output neutrality and valid version tracking are the relevant checks. Meaningful unplanned norovirus changes create a new reference and an explicit disposition of already-run cells.

## Recommended next handoff

1. Correct the six contract items above, keeping the settled scientific program intact.
2. Produce a complete example run specification for each reference hull and the historical vessel, with role counts, pathogen/source/boarding choices, strategy, reported-case counters and requested outputs. Check the final generated cells after all runner axes, not only the tier block before generation.
3. Rerun the improved initialization checker at the final named source; retain exact source/image identities and its output.
4. Declare the reference in a separate record, then submit the bounded bridge design for its prospective scientific review.
5. Use the resulting evidence to prioritize the temporal and joint-outcome studies, followed by scale, response and focused uncertainty work.

I support moving forward through that sequence. This review does not require a new broad audit, a new supply-chain model or a new parameter fit.

## Evidence and verification

Exact current source identity, proposal/merge identity and source line locators are in the separate provenance and component evidence registers. Three independent reviews cover configuration semantics, evaluation design and the Explorer platform. Coordinator checks include candidate-to-current source-change scope, static role-allocation arithmetic, checker exception classification with mocks, bridge-size arithmetic and review reconciliation. I independently replayed the pure Explorer generation, schema, allocation and eligibility checks and verified all saved source-file hashes were unchanged. Repository model code, initialization, epoch stepping, campaign workers and cloud jobs were not executed by this review.

The detailed component reports and full saved BibTeX accompany the review. The conventional repository reference is: Crusher_to_the_Bridge contributors, *Paper 1 freeze design contract and associated implementation*, accessed November 21, 2026, https://github.com/bckirkup/Crusher_to_the_Bridge. Exact revision and file locators are retained with the technical evidence.

## Source-linked component reviews

- **Configuration:** [CONFIG_REVIEW.md](CONFIG_REVIEW.md), seven findings and 59 exact source excerpts in [CONFIG_EVIDENCE.json](CONFIG_EVIDENCE.json); full pin inventory and independent arithmetic in [CONFIG_STATIC_CHECKS.json](CONFIG_STATIC_CHECKS.json).
- **Evaluation design:** [DESIGN_REVIEW.md](DESIGN_REVIEW.md), nine findings and 49 exact source spans in [DESIGN_EVIDENCE.json](DESIGN_EVIDENCE.json), including endpoint collection, precision and arm semantics.
- **Historical vessel:** [EXPLORER_REVIEW.md](EXPLORER_REVIEW.md) and twelve evidence records in [EXPLORER_EVIDENCE.json](EXPLORER_EVIDENCE.json), with original CDC endpoints and the bounded replay in [EXPLORER_REPLAY.py](EXPLORER_REPLAY.py).

Review pin: `73ad8724929217a1a90b8f0a2f6533562df81b91` (merged PR 1355), compared with proposal head `f8ef4844bcc5bc45db045d7ff654da76263f9f21`. The contract and checker match the reviewed merge. The candidate-to-review difference contains documentation and this checker, not a norovirus mechanism change. Each campaign still needs its final reference and effective input specification recorded.
