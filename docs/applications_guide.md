# Applications guide: study design, digital twin, prevention science, and retrospective investigation

> **Status:** Living — a map from four research/operational questions to the
> machinery that already exists in-tree. Every entry point named here exists;
> where the underlying capability is partial, that is stated. Follow the same
> status discipline as everywhere in `docs/`: when the tree and this document
> disagree, the tree wins.

The simulation is an agent-based model of a passenger vessel with a separable
**observation layer**: the engine produces ground truth (every infection, its
route, its dose, its timing), and Crusher Labs / Sentinel / the Stackelberg
layer produce *what an observer would actually see* — assays with declared
sensitivity, specificity, turnaround time, detection limits, censoring flags,
and an ascertainment funnel from infection → illness → report → test →
confirmation. That pairing is the reason one platform can serve four different
uses: for each, the question is asked of *both* streams, and the gap between
them is often the answer.

```text
ground truth (engine state)          observation record (instruments)
──────────────────────────           ────────────────────────────────
infections, doses, routes,           air sniffer, surface swab,
onsets, shedding, strains     ──►    wastewater grid + holding tank,
                                     per-agent assays, wearable scores,
                                     syndromic sick calls, line lists
                                     — each with sens/spec, LOD,
                                     TAT queue, cost, ascertainment
```

Entry points for everything below: `orchestrator.py` and
`picard_framework`/`ShipSimulation` ([OPERATORS_MANUAL_SHIP.md](OPERATORS_MANUAL_SHIP.md)),
campaign machinery (`campaigns/`, `scripts/campaign`,
`picard_framework/runs/mega_cruise_campaign/`, `deploy/aws/`), and the analysis
packages (`picard_framework/analysis/`).

---

## 1. Designing observational studies for model parametrization

The core move: **generate a synthetic cohort with known parameters, observe it
through a candidate study design, and measure whether the intended analysis
recovers the parameter** — before committing to a field protocol. Power,
sensitivity, and sampling strategy each map to machinery that already exists.

### 1.1 Power: how much data does the question need?

Two complementary instruments:

- **Analytic ceiling.** `picard_framework/analysis/sentinel/design_power.py`
  numerically differentiates the sentinel forward model and computes the
  independent-Poisson Fisher information — an optimistic bound on what any
  estimator could deliver — then a second engine simulates Poisson onsets and
  refits the reference posterior. It reports posterior sd, 90% widths, and the
  minimum detectable hazard ratio (MDHR) per design:

  ```bash
  python3 -m picard_framework.analysis.sentinel.run_design_power \
    --preset caribbean --engine both --out tmp_design_power_out
  ```

  Measured lessons recorded in [sentinel/sentinel_design_power.md](sentinel/sentinel_design_power.md):
  precision scales as `1/sqrt(ship-weeks)`; calls per ship-week are nearly flat
  because extra calls dilute the same passengers over more ports; the governing
  quantity is voyage-calls per port. The same logic transfers to onboard
  questions: exposure per measured cell, not nominal sample size, is what buys
  precision.

- **Empirical power.** For ABM-level questions there is no closed form, so the
  repo's practice is: pick a design cell, run it over seeds, measure the CI
  width of the estimand, raise the seed count until the CI does what the
  question requires. Precedents and their budgets:

  | Study need | In-repo precedent | Budget |
  |---|---|---|
  | Test a rare-event rate against a sub-percent anchor | `lowposting_region_37` — posting floor 3.19% (95% CI 2.35–4.24), no interval reaching A9's 0.42–0.56% | 16 points × 1,440 voyages |
  | Detect a policy effect on a binary outcome | `dutyexcl_matched_37` — crew duty-exclusion arm, McNemar exact p = 0.20 | 12 points × 1,440 paired seeds |
  | Resolve a mechanism crossing | `flush_sweep_v1` stages — emission linear in parameter, resolvability bracketed inside (1e-9, 1e-7) | 600–1,200 paired runs per arm |
  | Detect an arm effect on a conditional metric | `covid_quarantine_attribution_v2` — crew exemption −74% on the frozen criterion | 6 arms × 2 Θ × 20 paired seeds (240 cells) |

  Helpers for exactly this bookkeeping live in `tools/diag/readout_common.py`
  (Wilson centered intervals, `rate_summary`, `rate_ci_str`), with matched-seed
  pairing via common random numbers — the same seed set runs under every arm so
  arm-to-arm differences are attributable to the mechanism, not the draw.

### 1.2 Sensitivity and identifiability: which parameters can this study even see?

Before spending observations, establish which parameters are resolvable from
the proposed observables at the proposed size:

- **Morris elementary-effects screen** —
  `telemetry_buffer/observation_model/bounded_screen.py`, specified in
  [proposals/bounded_sensitivity_and_admissible_region_spec.md](proposals/bounded_sensitivity_and_admissible_region_spec.md).
  Each factor enters as a sourced interval with a declared transform; the
  screen ranks μ* against a **noise floor measured first** (20 seeds at the box
  centre). A factor below the floor is reported *indistinguishable from
  stochastic noise at this design size* — deliberately not "insensitive":
  "insensitive" would license freezing the parameter; the noise-floor verdict
  does not. σ flags interactions, so
  one-at-a-time designs that would mislead are caught up front. See
  [norovirus/bounded_screen_isolated_36.md](norovirus/bounded_screen_isolated_36.md)
  for what a real screen report looks like.

- **Admissible region** —
  `telemetry_buffer/observation_model/admissible_region.py`. Sample the
  parameter box (Sobol'), and a point is admissible iff *every* anchor interval
  is covered simultaneously. For study design this answers the sharpest
  identifiability question: does *any* parameter combination produce the
  quantities the study would observe? An empty region is a finding, not a
  residual — [norovirus/admissible_region_37_v2.md](norovirus/admissible_region_37_v2.md)
  reports the full ten-factor box empty with the posting anchor A9 failing
  high ≥6× everywhere — an observation-model/posting-mechanism tension rather
  than a dose-magnitude one (the verdict is pre-refit; see
  [norovirus/high_touch_area_handoff_2026_09_22.md](norovirus/high_touch_area_handoff_2026_09_22.md)).

- **Mechanism-ablation assays** — the small-design version of the same
  question. `covid_sensitivity_assay_v1` (240 cells) measured every
  transmission-layer arm inert on the frozen conditional metric — i.e., that
  design could not separate those mechanisms on that metric at that size.
  `tools/` carries the assay/probe drivers; the pattern is one arm per
  mechanism, a frozen criterion declared before any cell runs, paired seeds.

- **Design-matrix identifiability (fleet studies)** —
  `picard_framework/analysis/sentinel/separability.py` checks whether the port
  and calendar-week effects an itinerary would confound are actually
  separable, returning identified rank, VIF-like inflation, and exposure-weighted
  SEs per port:

  ```bash
  python3 -m picard_framework.analysis.sentinel.separability \
    --all-presets --write-visits --out separability_run
  ```

  Its measured verdict is the canonical study-design lesson: itinerary overlap
  costs ~20–30% contrast variance, but a week where the whole fleet calls at
  one port makes that port literally identical to that week's effect
  (degenerate design, rank 12/17). The fix is within-week spreading.

- **End-to-end recovery.** `analysis/stan/` fits Bayesian models to campaign
  outputs (`synthetic_recovery_*.stan`, `norovirus_*.stan`, `sentinel_*.stan`),
  and the `synthetic_recovery_v1` / `sentinel_synthetic_recovery_v1` campaigns
  (1,200 / 3,360 runs — [synthetic_recovery_and_vsp_degradation.md](synthetic_recovery_and_vsp_degradation.md))
  exist precisely to check whether the inference pipeline recovers *known*
  inputs. `tests/test_sentinel_fleet_validation.py` runs posterior-recovery
  fits as CI. If an estimator cannot recover truth from synthetic data, it will
  not recover it in the field.

### 1.3 Sampling strategy: which observations, where, how often

The observation layer is declared, so a sampling strategy is a *configuration*,
and alternatives are compared as paired-seed arms:

- **Instrument menu** (`crusher_labs/observation_core.py`, parameterized per
  pathogen in `data/config/clinical_instrument_params.json`; full tables in
  [instrument_parameterization_v2.md](instrument_parameterization_v2.md)):
  continuous `air_sniffer`, `surface_swab` (per-swab copy LOD, Park 2015, with
  `censored_below_lod` flagging), `wastewater_qpcr` on the blackwater holding
  tank plus a zone wastewater grid, per-agent clinical assays (RDT / multiplex
  panel / qPCR / culture — each with stage-dependent sensitivity, specificity,
  TAT, cost), and wearable anomaly scoring. Sampling **cadence** is a per-modality
  config key; `instrument_turnaround` queues results so a study's delivery
  latency is part of the design, not an afterthought.

- **Ascertainment funnel** — `tools/noro_diag/observation_channel_funnel.py`
  and the anchor layer measure infected → ever-ill → reported → tested →
  confirmed. A study's effective sample is the bottom of that funnel, not the
  population: 51% of postings in the measured cell were crew-only, and reported
  capture fractions are themselves parameterized (the NORO-CHANNEL-02 ledger
  entry records a reluctance factor found double-counted and since removed).
  When sizing a study, simulate the funnel first to get the *yielded* sample
  size.

- **Swept strategies as campaign dimensions** — the mega campaign's `t3`
  tier (10 pathogens × 4 surveillance strategies × 30 seeds), the
  `sentinel_ww_ops_scan_v1` manifest (9,000 runs adding per-cell
  `wastewater_surveillance` overrides — assay modes and cadences swept like any
  other factor), and the `t8` wearables tier are sampling-strategy studies
  expressed as manifests.

- **Adaptive/sequential designs** — `--order informative` and `--stop-rule`
  on the campaign runner order runs by expected informativeness and stop a
  shard when a pre-declared trend is already supported (skill
  `informative-shard-ordering`) — the machinery for group-sequential study
  designs.

- **Escalation design** — `diagnostic_cascade` (Tier 0–3) and long-read
  escalation let you test multi-stage protocols: cheap screen first, confirm
  the positives. The entry fusion rule (`infection_score` gating) is itself a
  declared study-design choice.

### 1.4 Recipe

1. Declare the estimand and the criterion *before any cell runs* — the repo's
   gate (skill `campaign-preflight`) requires frozen admissibility criteria in
   the design file.
2. Choose observables; translate the study into `config_overrides` on
   instruments, cadences, and assay parameters.
3. Screen (Morris/noise floor or a small ablation assay): is the parameter
   resolvable at all from these observables?
4. Size: pilot seeds → measure CI width → scale to the needed precision
   (empirically, or via the Fisher ceiling where a forward model exists).
5. Run the array — `scripts/campaign submit` for `campaigns/` specs, the
   mega-cruise runner + `deploy/aws/` submit scripts for manifest campaigns,
   canary first — apply the intended analysis to the *simulated observables
   only*, and score recovery.
6. Record the verdict in the campaign `LEDGER.md` with commit SHA — see the
   discipline notes in §5.

---

## 2. Building an effective digital twin for operations

A twin here is a **bundle, not a binary**: platform declaration + pathogen
bundle + run spec + instrument suite + response policies + cost model. The
pieces exist for twelve catalogued hulls (cruise classes, naval, expedition —
`data/platforms/`) plus machinery to stand up a new hull.

### 2.1 Compose the twin

| Layer | What it declares | Where |
|---|---|---|
| Vessel | Spatial layout, zones, cabin/stateroom structure, HVAC/airflow network (exact CONTAM linear operator), agent classes, schedules (`rhythm` event catalogs transcribed from real daily programs), sanitary plumbing | `data/platforms/<id>/`, `engines/transmission_core.py`, `engines/rhythm_layer.py`, `tools/ship_blueprint_import/` (GA drawings → platform JSON; skill `importing-naval-blueprint`) |
| Pathogen(s) | Route multipliers, dose-response, shedding curves, emission shares, susceptibility fractions | `data/pathogens/` bundles (`active_profiles`, `norwalk_only`, ...) |
| Voyage | Itinerary (sea/port/embarkation days), disembark fractions, port labels, medical response knobs, dining weights | `data/platforms/<id>/voyage_config.json` ([ship_operations_spec.md](ship_operations_spec.md), [medical_response_spec.md](medical_response_spec.md)) |
| Observation | Instruments, cadences, TAT, cascades, wearable deployments | `crusher_labs/config.yaml`, `data/config/clinical_instrument_params.json`, `instrument_turnaround.json`, `data/config/wearable_deployments/` |
| Response | SOP library, escalation thresholds, decision latency, compliance classes, crew duty exclusion | `data/config/protocols.json`, `crusher_labs/config.yaml` ([tiered_escalation_spec.md](tiered_escalation_spec.md)) |
| Costs | USD, labor, materials, OIS weights | `data/config/resource_costs.json`, [pricing_notes.md](pricing_notes.md) |
| Run | Seed, epochs, agent counts, overrides | `schemas/picard_run_spec.schema.json`, `picard_framework/runs/*.json` |

### 2.2 Make it trustworthy enough to operate on

The repo treats "is this twin believable" as an explicit, auditable contract:

- **Provenance.** Every epidemiological constant carries a source and an
  evidence grade (M measured / B analogous / I inherited / A adapted / C assumed
  / P placeholder / F free / X construction / S scored) at its definition;
  [parameter_provenance_register.md](parameter_provenance_register.md) is the
  authoritative index, and the sourcing protocol
  ([sourcing_protocol.md](sourcing_protocol.md)) is the process of record for
  updating it. An operator can ask "what is this number's provenance" and get
  an answer, not a shrug.
- **Validation.** `tools/sanity_checker.py --from-config` (contract checks),
  schema validation on every JSON in `data/`, ~6,400 tests including golden
  orchestrator, and posterior-recovery fits in CI (`test_sentinel_fleet_validation`).
- **Calibration discipline.** Parameters enter as sourced *intervals*; anchors
  (the observed record the twin must reproduce — §4) are *scoring* targets,
  and the hard rule is: never fit a physical constant to an anchor the model is
  scored against (AGENTS.md). Feasibility is checked by the admissible-region
  machinery — does any point in the sourced box reproduce the record?
- **Honest uncertainty.** The open ledgers
  ([norovirus/norovirus_open_ledger.md](norovirus/norovirus_open_ledger.md),
  [covid/covid_open_ledger.md](covid/covid_open_ledger.md)) record *what is
  currently withdrawn* — measurements voided by later model changes — and
  `docs/ledger/` carries one file per defect/measurement with commit SHAs.
  For operations, a twin that publishes which of its numbers are void is more
  useful than one that quietly doesn't.
- **Labelled baselines.** Nearly every mechanism ships with a paired `off`
  baseline (`near_field_air.mode: off`, `zone_pool` cabin air, `none` HVAC
  transport, `rhythm.enabled: false`, ...). Operational claims are made as
  contrasts against the labelled baseline on paired seeds, never as absolute
  stories.

### 2.3 Operate it

- **Interactive/programmatic:** `ShipSimulation(spec).step()` for embedding;
  `orchestrator.py` for CLI; `python -m api` exposes the twin over REST
  (`POST /v1/runs`, job lifecycle — [api_service.md](api_service.md)) so
  external systems can submit voyages; `streamlit run dashboard.py` (LCARS) for
  an operator-facing command deck over the telemetry buffers.
- **Decision loop:** with the `social` block on, each epoch runs information
  diffusion → population actions (symptom-hiding, reporting, quarantine
  refusal via `ThresholdBeliefPolicy`) → command/medical decisions
  (`authorize_sop_subset`, `activate_sop`, `order_verification_test`) → SOP
  physics — so the twin models *who decides what, when, on which belief*, with
  configurable decision latency and bimodal compliance. Utility features export
  to JSON and action envelopes import back ([OPERATORS_MANUAL_GAME_THEORY.md](OPERATORS_MANUAL_GAME_THEORY.md)),
  which is the seam for closing the loop with an external optimizer.
- **Fleet scale:** `presidio_runner.py` runs the meta-simulation across cruises
  with an experience store (`presidio/data/`) — the twin as a fleet asset that
  accumulates operational history.
- **Degradation realism:** the emerging ship-function layer
  ([proposals/ship_function_capacity_spec.md](proposals/ship_function_capacity_spec.md),
  sources in [ship_functions/parameter_sources.md](ship_functions/parameter_sources.md);
  `engines/ppe_fatigue.py` landed §7) asks what crew illness does to ship
  *functions* — galley, engineering watch — which is the operational question a
  plain attack-rate model cannot answer.
- **Forecasting under intervention:** because mechanisms have labelled
  baselines and seeds are paired, "what does tomorrow look like if we trigger
  SOP-X vs not" is a same-history counterfactual, not a guess.

---

## 3. Exploring new concepts in preventive medicine and public health

The platform's comparative advantage for concept work is that intervention
ideas arrive as **config/policy arms over a believable population, ship, and
observation stack** — so a concept is judged on measured effect and cost, with
the comparison machinery (paired seeds, frozen criteria) already built.

In-tree concept explorations that show the pattern:

- **Ships as distributed sensors for port epidemics** — the Sentinel layer
  ([sentinel/sentinel_surveillance_spec.md](sentinel/sentinel_surveillance_spec.md),
  implemented partially under `analysis/sentinel/` + `analysis/shore/`)
  inverts the usual frame: instead of protecting the ship, a fleet's onboard
  observations are pooled to infer introduction hazard at ports of call
  (`port_health.py`, `shore/importation.py`). Design power, separability, and
  MDHR machinery (§1) were built for this. This is a genuinely novel public
  health concept — voluntary fleet sensing as early-warning infrastructure.

- **Pre-embarkation screening economics** — the boundary decision model
  ([preboarding_wearable_decision_model_spec.md](preboarding_wearable_decision_model_spec.md);
  Phase 1 in `analysis/boundary/`): should wearable data sharing 24–72 h before
  boarding be encouraged, and what is its ROI? Distinct question from
  mid-voyage surveillance (C14 showed wearables add little once transmission is
  onboard) — prevention at the boundary vs detection mid-voyage. Companion:
  the insurance-incentivized wearable manuscript in `docs/reports/`.

- **Wastewater and environmental surveillance concepts** — holding-tank
  CSTR assay, zone grid, ops-scan sweeps over assay modes and cadences
  (`sentinel_ww_ops_scan_v1`), surface-swab LOD/censoring realism. Questions
  like "does wastewater buy days of early warning, and at what assay design?"

- **Intervention policy design space** — the SOP layer
  ([tiered_escalation_spec.md](tiered_escalation_spec.md)): escalation
  thresholds, decision latency, activation delays, bimodal compliance
  (compliant/reluctant/defiant), crew duty exclusion, confinement geometry —
  each is a policy parameter that can be swept (campaign tiers `t11`, `t15`,
  `t16` already do). NPI/pharmaceutical hooks live in
  `engines/non_pharmaceutical_interventions.py` /
  `pharmaceutical_interventions.py`; HVAC/ventilation levers are swept in `t2`.

- **Diagnostic-strategy design** — Tier 0–3 cascades, multiplex panels,
  TAT trade-offs, long-read escalation: new *testing* concepts evaluated as
  protocol configs, with cost in USD/labor/materials/OIS, not just detection
  latency.

- **Behavioral public health** — belief diffusion and population policies
  (`decision_engine/`): symptom-hiding, trust, rumor dynamics interacting with
  interventions; Stackelberg game structure between operator, authority, and
  population. Compliance is modeled, not assumed — a concept like "preemptive
  quarantine" is measured against realistic refusal.

- **Genomic/variant surveillance** — strain state and mutation engines
  (`engines/strain_*.py`) with phylodynamic observables
  (`analysis/phylodynamics/`, [paper3/](paper3/)): can sampling schemes detect
  introductions/variants, and what does genomic ascertainment add?

- **Economics as a first-class readout** — `analysis/economics/`
  (willingness-to-pay, surveillance economics; *the dollar valuations are
  declared unanchored placeholders*) plus the cost ledger (USD + labor +
  materials + OIS). A prevention concept is evaluated on burden, not just
  efficacy — e.g. `dutyexcl_matched_37` measured a regulation's effect at
  McNemar p = 0.20, i.e., near-neutral at full compliance.

The pattern for a *new* concept: implement the intervention as a mechanism or
policy arm → declare frozen criteria → canary → paired-seed A/B against the
labelled baseline → readout → verdict in the ledger. `COVID-RINGCAP-V1`,
`SOP-VSP-CREW-01`, the flush-aerosolisation staged brackets, and the
preboarding assessment arm ([norovirus/preboarding_assessment.md](norovirus/preboarding_assessment.md))
are the worked examples.

---

## 4. Retrospective outbreak investigation

The forensic use: **replay a documented outbreak inside the twin and ask which
mechanisms and parameter sets are consistent with what was actually observed —
and where consistency fails, localize *why*.**

### 4.1 The observed record becomes anchors

A real outbreak record enters as **anchor intervals** — quantities the model
must reproduce — declared with era and hull-class denominators before any
scoring (`telemetry_buffer/observation_model/anchor_measurement_spec.md`,
`score_anchors.py`, `vsp_class_era_scoring.py`). The norovirus set: Wikswo
cohort attack rate (A1), asymptomatic ratio (A2, itself a *prediction* of the
dose-response functional form), VSP posted attack rate per hull class × era
(A4), passenger/crew ratio (A5), unconditional AGE incidence (A8), posting
probability (A9), voyage-length gradients (A10, proposed). For COVID the
record is the Diamond Princess trajectory, with a fixed train/held-out split:
DP trains, **Greg Mortimer is held out** — textbook discipline for a
retrospective fit ([covid/](covid/) thread; see its README before quoting
numbers, several are withdrawn).

### 4.2 Consistency: the admissible region as a forensic instrument

"Could this model have produced this outbreak?" is answered by the admissible
region (§1.2): sample the sourced parameter box, and a point is admissible iff
every anchor is covered simultaneously. Two in-tree verdicts show the range of
conclusions this yields:

- **Empty region → missing/misspecified mechanism.** The norovirus #37 gate
  (256 Sobol' points × 180 seeds, ten factors) is empty: A9 (posting
  probability) fails high ≥6× everywhere. Pairwise anchor incompatibility is
  the diagnostic — it points at *which* part of the mechanism or observation
  model is wrong, not just that something is.
- **Non-empty band with a failing conditional clause.** The COVID Θ screens
  (v7–v14, thousands of cells on AWS Batch) found an admissible Θ band
  ({1.78e11 … 5.62e11} under capped reach at v13, sliding to {1.33e11 …
  4.22e11} at v14 on the repaired hand line), while the conditional clause
  failed at every interior admissible Θ across the v11–v13 and rebase screens
  — localizing the deficit to conditional outbreak size, which the hunt then
  localized further to onset-dating/channel over-inclusion
  ([covid/covid_channel_anchor_handoff_2026_09_25.md](covid/covid_channel_anchor_handoff_2026_09_25.md)).
  The investigation output is a *mechanism-level diagnosis*, not a fitted knob.

### 4.3 Attribution: which mechanisms were load-bearing

Once a replay is admissible (or the deficit localized), paired-seed
**channel-ablation** answers "what carried it?":

- **Route attribution** — dominant-route shares per establishment
  ([norovirus/route_attribution_headcount_scaling.md](norovirus/route_attribution_headcount_scaling.md),
  [norovirus/droplet_deletion_route_v1.md](norovirus/droplet_deletion_route_v1.md):
  deleting the continuous droplet share cut secondaries/import 31–49× and
  zeroed droplet attribution; `tools/noro_diag/route_attribution_readout.py`,
  `tools/covid_route_attribution.py`).
- **Quarantine/leak attribution** — `covid_quarantine_attribution_v2`: on the
  frozen criterion, crew confinement exemption (−74%) and pool transport (−66%)
  carried the Diamond Princess leak; near-field did not. That is a
  counterfactual answer to "what should have been done differently?"
- **Introduction attribution** — takeoff attribution
  (`tools/covid_takeoff_attribution.py`) and `lambda_cross`
  (`tools/covid_lambda_cross_smoke.py`) trace which boarding introductions
  founded the observed outbreak and how hazard-rate shifts move takeoff.
- **Ascertainment correction** — the funnel (§1.3) translates between the
  record's cases and true infections; a retrospective claim about "attack rate"
  must say which rung of infected/ill/reported it means. The anchor spec exists
  because early aggregate ratios mixed populations (passenger rate over a
  whole-ship denominator) — the same trap a real investigation faces when
  denominators differ.

### 4.4 Inference machinery and validation

- The Stan layer (`analysis/stan/`) fits outbreak probability and
  trajectory|outbreak to campaign outputs — the statistical layer for
  posterior claims about latent quantities. `synthetic_recovery_*` models
  exist to prove the machinery recovers truth *before* trusting it on real
  records.
- `sentinel/export_line_list.py` produces simulated line lists — the direct
  comparator to a real outbreak's case line list.
- `phylodynamics/` observables let genomic-era records (variant counts,
  diversity curves) enter as anchors.

### 4.5 Recipe

1. Fix the observed record: counts, timing, denominators, ascertainment
   channel — *which rung of the funnel the record sits on*.
2. Translate record → anchor intervals; freeze scoring criteria and the
   train/held-out split.
3. Screen the sourced box for admissibility (Morris → Sobol' region).
4. If non-empty: ablation arms on paired seeds attribute load-bearing
   channels; posterior fits quantify latent quantities.
5. If empty: pairwise anchor conflicts localize the missing/misspecified
   mechanism — that localization *is* the investigative result.
6. Validate on the held-out outbreak before claiming; record verdicts with
   commit SHAs.

---

## 5. Cross-cutting disciplines (apply to all four)

| Discipline | What it means here |
|---|---|
| Parameters are intervals with provenance | Every constant is a sourced range with an evidence grade ([parameter_provenance_register.md](parameter_provenance_register.md)); sweeps explore the box, nothing is "tuned to fit" — and never fit a constant to an anchor the model is scored against |
| Paired seeds / common random numbers | Any comparative claim runs the same seeds across arms; the attribution instrument is ablation on identical stochastic histories (skill `stochastic-attribution`) |
| Frozen criteria | Admissibility/verdict criteria are declared in the design file before cells run (skill `campaign-preflight`); seed geometry is validated and a canary precedes the array |
| Campaign machinery | `campaigns/<pathogen>/<name>/campaign.json` + `scripts/campaign` (list/describe/run/submit/readout) for `campaigns/` specs; manifest campaigns run through `picard_framework/runs/mega_cruise_campaign/` + `deploy/aws/` submit scripts; AWS Batch executes arrays |
| Ledger culture | Verdicts are recorded with commit SHAs in `docs/ledger/` and open ledgers; measurements voided by later changes are withdrawn explicitly — every number above carries that caveat |

## Which tool for which question — quick index

| Question | Start here |
|---|---|
| How many voyages/ships/seeds to detect effect size X? | `analysis/sentinel/design_power.py` (ceiling) → empirical seed scaling via `tools/diag/readout_common.py` |
| Can design D identify parameters P at all? | `bounded_screen.py`, `admissible_region.py`, `analysis/sentinel/separability.py`, a small ablation assay |
| Which instrument/cadence/placement buys information? | `crusher_labs/observation_core.py` + `clinical_instrument_params.json`; `sentinel_ww_ops_scan_v1` as precedent |
| Will my estimator recover truth? | `analysis/stan/` + `synthetic_recovery_v1` campaigns + `test_sentinel_fleet_validation` |
| Stand up a twin of vessel V | `data/platforms/` (12 catalogued) or `tools/ship_blueprint_import/`; `schemas/picard_run_spec.schema.json` |
| Integrate the twin with an ops system | `python -m api` ([api_service.md](api_service.md)); utility export/import ([OPERATORS_MANUAL_GAME_THEORY.md](OPERATORS_MANUAL_GAME_THEORY.md)) |
| Evaluate a prevention concept | SOP/policy arms ([tiered_escalation_spec.md](tiered_escalation_spec.md)), `analysis/boundary/`, `analysis/sentinel/`, `analysis/economics/` |
| Replay/documented-outbreak forensics | Anchors (`anchor_measurement_spec.md`), `admissible_region.py`, route/quarantine/takeoff attribution tools, Stan fits |
