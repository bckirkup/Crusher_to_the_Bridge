# Sentinel Surveillance Spec v2 — Cruise Ships as Port-of-Call Sentinels

Revision of the proposed `sentinel_software_spec.md`. Scope: infer pathogen
introduction hazard at ports of call from ship-side observations (clinical line
list, wastewater metagenomics, later genomics), pooling across the **fleet**.

Companion of the boundary analysis package (`docs/preboarding_wearable_decision_model_spec.md`):
boundary asks *should this passenger board*, sentinel asks *where did the
pathogen come from*. Both are ancillary inference layers over the same ABM.

## 1. What changed from the proposed spec, and why

The proposal is directionally right and the identifiability list is the right
list. Eight substantive changes:

### 1.1 Do not build a second itinerary model

The repo already has a voyage/port layer: `engines/voyage_itinerary.py` with
`schemas/voyage_config.schema.json` and per-platform
`data/platforms/<id>/voyage_config.json`. It already carries day types
(`sea_day`/`port_day`/`embarkation`/`disembarkation`), a `port` label,
`disembark_fraction` (= the proposal's `shore_excursion_rate`),
disembark/reembark windows, a per-agent `ashore` flag consumed by
`engines/transmission_core.py`, and — critically — a
`shore_infection_probability` field documented as *"config-only in v1; never
introduces pathogens"*.

So the sentinel `Voyage`/`PortCall` dataclasses become a **read-only view over
`voyage_config`**, not a parallel model. Fields the sentinel layer genuinely
needs and that `voyage_config` lacks are added to the existing schema as
optional keys: `port_id` (IATA/UN-LOCODE), `region`, `calendar_date`,
`crew_shore_leave_fraction`. One itinerary truth, one validator, one schema
test.

The view keeps the **home port**: embarkation and disembarkation are port calls,
not scaffolding around the itinerary. Every agent stands on that pier at least
once, the simulated ledger records ashore hours there, and the premise of the
scenario is a pathogen carried aboard at the home port — so dropping those days
made campaign bundles fail validation with *"hours_ashore references unknown
port 'miami'"*. Consequences: `PortCall.is_home_port` marks them, a port can be
called more than once (home port twice, or a repositioning itinerary repeating a
port), so ashore hours are checked against the **sum** of the visits
(`Voyage.port_calls_for`); the embarkation window contributes hours before
boarding closes and the disembarkation window hours after walk-off; and
separability metrics such as `min_inter_port_hours` only count calls that
actually put people ashore, so a default embarkation day with everyone already
onboard neither carries a hazard nor changes a separability claim.
`port_calls_from_config(..., include_home_port=False)` remains for callers that
want the excursion-only view.

### 1.2 Phase 2 comes before Phase 1's validation, and it is small

The proposal defers coupled simulation to "future", but the validation plan's
first item (synthetic voyages with known port hazards) *requires* a generator.
Phase 2 is therefore promoted, and it is not new machinery: it is activating
the `shore_infection_probability` stub inside the existing
`step_mid_cruise_introductions` seam (`orchestrator_epoch.py`), drawing over
agents already flagged `ashore`. Behind `voyage.shore_exposure.enabled`
(default false) so every current run and golden test stays bit-identical.

### 1.3 The wastewater channel does not match the instrument CTB has

The proposal models `concentration: genome copies/L`. CTB's wastewater
modality is GRUMB-style **compositional metagenomics**: a
`WastewaterSequencingGrid` over greywater collection zones
(`orchestrator_init.py`), Dirichlet-multinomial read draws over a
multi-kingdom relative-abundance vector, CLR-space anomaly scores
(`crusher_labs/modalities/sequencing.py`). There is no qPCR concentration
observable in the simulator.

Revised: the sample record carries `pathogen_reads`, `total_reads`,
`clr_anomaly_score`, and the collection point, with
`concentration_copies_per_l` kept optional for *external* qPCR datasets. The
likelihood is beta-binomial on pathogen reads out of total reads; a normal on
log-concentration understates uncertainty at the low read depths that actually
occur.

**Addendum (assay modes).** The revision above was right about the instrument
and wrong about the range. Compositional metagenomics is blind at the shedder
prevalences a cruise reaches: with an informative ceiling of `1e-4` of the
library, 0.26% prevalence expects 0.064 pathogen reads in a 250 000-read
library. `wastewater_surveillance.assay_mode` therefore selects the laboratory
(`picard_framework/analysis/sentinel/wastewater_assays.py`):

- `metagenomic` — the model described above, unchanged, and the **default** so
  no pre-existing cell changes meaning. Kept as the arm that demonstrates the
  blindness.
- `qpcr` — a simulated standard curve, so the concentration observable is no
  longer external-only. Reports a Ct above the LOD and *only the bound* below
  it; the fit puts a censored normal on pooled log10 concentration with its own
  link parameters, never sharing the read channel's calibration.
- `amplicon` / `long_read` — the same qPCR detection gate followed by a
  targeted library; their read fraction saturates, so they type rather than
  quantify, and long read additionally carries instrument turnaround.

A normal on log-concentration is the right likelihood *for qPCR* precisely
because a Ct is a log-scale measurement with roughly constant error, and the
non-detects that the low-read-depth objection was really about are handled as
censored rather than as measurements. The two channels stay separate: reads to
the beta-binomial, concentrations to the censored normal. Neither carries a port
label, for the reason below.

Second and more important: a ship's greywater is a **closed, integrating
system** with a residence-time lag. Its signal is dominated by onboard
shedding prevalence, so it does not carry an independent port label — it is a
second, aggregate observation of *onset timing*. Treated as an independent
hazard channel it double-counts the clinical line list. It enters the model as
an additional observation of the same latent incidence curve.

The generator side of that channel is `sentinel/wastewater_ops.py` (§8): the
holding tank is an explicit first-order lag on aboard shedder prevalence, so a
run's samples carry the same residence smearing the fit deconvolves.

### 1.4 The Stan sketch estimates shares, not hazards

As sketched, the likelihood runs over `N_cases` only. A rate needs a
denominator: the person-hours ashore of everyone who did *not* become a case.
Without it the model identifies attribution *shares* among observed cases,
which is not the paper's claim ("introduction rate per exposed person-day").

Revised likelihood: counts per `(voyage × port-call × stratum)` cell, Poisson
(or binomial) with `offset = log(person-hours ashore)`, secondaries handled by
a discrete-time self-exciting term. Per-case attribution posteriors then fall
out as generated quantities.

### 1.5 `R_onboard` must be a parameter with a prior, not data

Passing a point estimate as `data` fixes the secondary share and lets the port
hazards absorb every mismatch; the port credible intervals come out far too
narrow. CTB already produces a *posterior* for onboard transmission (hurdle
`norovirus_outbreak.stan` + `norovirus_trajectory.stan`, summarized by
`picard_framework/analysis/stan/posterior_summaries.py`). Pass its mean/sd as
prior hyperparameters and sample `R_onboard`.

Secondaries are then a discrete renewal term rather than the sketch's
whole-case mixture (which is not implementable as "forward-backward" over an
unordered case set):

```text
E[incidence(t)] = imported(t) + R_onboard * Σ_{s<t} w(t-s) * incidence(s)
imported(t)     = Σ_p λ_p * H_p * ∫ f_inc(t - u) dU_p(u)
```

with `w` the generation-interval pmf and `f_inc` the incubation pdf.

Two type errors in the sketch while we are here: `exposure_duration` must be
`matrix[N_cases, N_ports]` (person-specific hours ashore per port is the only
thing separating a hazard from a shared per-port fixed effect), and `N_ships`
is declared but unused — there is no ship level in the sketched model.

### 1.6 Right-censoring is missing and it biases the headline result

A passenger infected at the *last* port frequently has onset after
disembarkation and never enters the ship line list. Every voyage truncates the
incubation convolution at `T_end`, so without the survival term
`P(onset ≤ T_end | infection epoch)` the model systematically concludes that
early ports are the dangerous ones. This is the largest single threat to the
paper's claim and it is cheap to fix (one `_lcdf` term per cell).

### 1.7 Crew shore leave is modeled; crew are not a control

The proposal's control #7 is "crew with no shore leave". Crew do take shore
leave; CTB currently hard-codes crew never ashore in
`apply_ashore_and_embarkation`, which is a simulator simplification, not a
fact about ships.

Resolved: **model `crew_shore_leave_fraction` explicitly** (decision, 2026-08-14).
It is cheap, and it converts crew from a shaky control into the strongest
identification source in the design — the same person exposed to the same port
every week is a repeat-measures design, and it is the only within-person
contrast available. Crew-as-onboard-baseline is dropped; the crew contribution
is now a *stratum* (`crew_ashore` / `crew_aboard`) with its own exposure
offset, not a reference level.

Consequence for PR 3: `apply_ashore_and_embarkation` gains crew handling behind
the same `voyage.shore_exposure.enabled` gate, with
`crew_shore_leave_fraction` defaulting to 0.0 so existing runs are unchanged.

### 1.8 Pathogen inclusion criterion, stated up front

Sea-day and incubation-window controls only separate ports when the incubation
IQR is shorter than the shortest inter-port interval. Norovirus (12–48 h)
qualifies; measles does not. Rather than discovering this in review, the spec
requires: report port-level attribution only when
`IQR(incubation) < min(inter-port interval)`, otherwise attribute to a
**port-window set**. Norovirus is the v1 pathogen — it also matches the
existing calibration and the VSP threshold response.

### 1.9 Layout, to repo convention

- tests live in `/tests/test_sentinel_*.py`, never inside the package
  (86 files, all flat — cf. `tests/test_boundary_*.py`)
- Stan models and fit entrypoints live in `picard_framework/analysis/stan/`
  next to `_data.py`/`posterior_summaries.py`, not in a package-local `stan/`
- CLI is `__main__.py` + `run_sentinel.py` with a `--smoke` fixture mode, so CI
  passes without cmdstan (an optional `[analysis]` extra), exactly as
  `boundary.run_decision_model --smoke` does
- 13 modules is too many for phase 1; several would be one function. Merged
  below.

## 2. Revised package layout

```text
picard_framework/analysis/sentinel/
├── __init__.py
├── __main__.py                # → run_sentinel.main()
├── itinerary.py               # view over voyage_config + port metadata
├── incubation.py              # incubation/generation pmfs + delay deconvolution
├── exposure.py                # exposure offsets + reporting/care-seeking/testing offsets
├── observations.py            # line list + wastewater record loading/validation
├── wastewater_signal.py       # compositional (beta-binomial) signal → latent incidence
├── attribution.py             # cell builder, Stan data assembly, posterior → estimates
├── export_line_list.py        # ABM run dir → sentinel line list (see PR2)
├── figures.py
├── report.py
├── run_sentinel.py
├── data/
│   ├── incubation_distributions.json
│   ├── port_priors.json
│   └── example_itinerary.json
└── fixtures/
    ├── synthetic_voyage.json
    └── attribution_posterior.json      # CI smoke, no cmdstan needed

picard_framework/analysis/stan/
├── sentinel_attribution.stan           # port-date hazard + renewal secondaries
├── sentinel_fleet.stan                 # + ship/visit hierarchy
├── _sentinel_data.py
└── fit_sentinel_attribution.py

schemas/sentinel_observations.schema.json
tests/test_sentinel_data_contracts.py
tests/test_sentinel_incubation.py
tests/test_sentinel_attribution.py
tests/test_sentinel_synthetic_recovery.py
```

Dropped from phase 1: `back_calculation.py` (folded into `incubation.py`),
`observation_model.py` (folded into `exposure.py`), `source_attribution.py` +
`fleet_inference.py` (one `attribution.py` with a hierarchy switch — fleet is
an extra grouping level, not a second code path), `genomic_linkage.py`
(deferred, §5).

## 3. Data models

Dataclasses, `from __future__ import annotations`, no pydantic in the analysis
packages (matches `boundary/`).

```python
@dataclass(frozen=True)
class PortCall:
    port_id: str                 # UN-LOCODE, e.g. "MXCZM"
    port_name: str
    region: str                  # WHO region / CDC quarantine station
    voyage_day: int              # keys into voyage_config itinerary
    arrival_epoch: int
    departure_epoch: int
    calendar_date: date | None            # None for synthetic voyages
    pax_ashore_fraction: float            # = voyage_config disembark_fraction
    crew_ashore_fraction: float           # crew shore leave; default 0.0, §1.7
    mean_hours_ashore: float              # from disembark/reembark windows
    is_home_port: bool                    # embarkation / disembarkation day

@dataclass(frozen=True)
class Voyage:
    voyage_id: str
    ship_id: str
    platform_class: str          # expedition | classic | spirit | mega
    embarkation_date: date | None
    n_passengers: int
    n_crew: int
    port_calls: tuple[PortCall, ...]
    total_epochs: int
    epoch_duration_hours: float
    observation_end_epoch: int   # censoring boundary — §1.6

@dataclass(frozen=True)
class ClinicalCase:
    person_id: str
    onset_epoch: int
    crew: bool
    pathogen: str | None
    genotype: str | None                  # phase 3
    hours_ashore: Mapping[str, float]     # port_id → hours (0.0 = stayed aboard)
    reported_via: str                     # sick_call | screening | cascade | wearable

@dataclass(frozen=True)
class WastewaterSample:
    sample_epoch: int
    collection_point: str        # greywater zone
    pathogen: str
    pathogen_reads: int          # sequencing modes; 0 for qPCR rows
    total_reads: int
    clr_anomaly_score: float
    concentration_copies_per_l: float | None = None   # qPCR / external qPCR
    assay_mode: str = "metagenomic"                   # see §1.3 addendum
    ct_value: float | None = None                     # detected qPCR only
    detected: bool | None = None                      # False = censored at LOD
    lod_copies_per_l: float | None = None             # the censoring bound
    turnaround_hours: float | None = None             # long read
    genotype: str | None = None                       # long read

@dataclass(frozen=True)
class ExposureCell:
    """Likelihood unit: one voyage × port-call × stratum."""
    voyage_id: str
    ship_id: str
    port_id: str
    port_visit_key: str          # port_id + calendar week — the public-health unit
    stratum: str                 # pax_ashore | pax_aboard | crew_ashore | crew_aboard
    n_persons: int
    person_hours_ashore: float   # Poisson offset; 0 for aboard strata
    cases: int
    censor_epochs_remaining: int

@dataclass(frozen=True)
class PortHazardEstimate:
    port_id: str
    port_visit_key: str | None   # None = pooled across visits
    pathogen: str
    hazard_mean: float           # infections per exposed person-hour ashore
    hazard_q05: float
    hazard_q95: float
    n_attributed_cases: float
    evidence_loglik: Mapping[str, float]   # per-channel contribution, §1.3
    censoring_corrected: bool
```

`evidence_loglik` replaces the proposal's `evidence_sources: list[str]`: with
three partially-redundant channels, reviewers will ask how much of the
attribution the wastewater actually carried, and a list of strings cannot
answer that.

## 4. Identifiability, restated honestly

Ranked by how much each actually buys, with the failure mode named:

| Source | Buys | Fails when |
|---|---|---|
| Person-level hours ashore vs stayed-aboard, same voyage | Most of the signal; within-voyage contrast removes voyage-level confounding | Ashore/aboard choice correlates with age/behavior → adjust in `exposure.py` offsets |
| Crew repeat exposure to the same port | Repeat-measures separation of port from voyage; the only within-person contrast | Crew shore leave is non-random (rank, duty rotation) → stratify by department |
| Itinerary crossover across ships | Separates port from itinerary position | Fleet must actually differ in port order; a single repeated Caribbean loop buys nothing |
| Incubation timing | Port resolution | `IQR(incubation) ≥ min(inter-port interval)` (§1.8) |
| Sea-day onsets | Bounds the onboard/secondary share | Long-incubation pathogens |
| Wastewater timing | Sharpens the latent incidence curve | Not an independent hazard channel (§1.3) |
| Genomic clusters | Would be decisive | No strain state in the ABM today (§5) |

Explicit non-identifiability to state in the paper: a port visited by every
ship on the same calendar day, by every passenger, is not separable from a
fleet-wide time effect. `sentinel_fleet.stan` must include the fleet-time
effect so that this shows up as a wide interval instead of a confident wrong
number.

## 5. Genomics is deferred, and why

`genomic_linkage.py` needs within-pathogen strain identity. The ABM tracks
multiple pathogens (`agent.infections[pid]`) but has no genotype/lineage state
— nothing to link. Phase 3 = minimal heritable strain label on infection
(parent strain + mutation draw at transmission), then linkage. Sequencing a
strain label is a real change to `infection_dynamics_bridge.py` and should not
ride along in an inference PR.

## 6. Validation plan

Reuses the existing synthetic-recovery machinery
(`picard_framework/analysis/stan/synthetic_recovery_*.stan`,
`analysis/synthetic_recovery_postprocess.py`).

1. **Recovery** — generate voyages with known `λ_p` via the Phase 2 generator;
   posterior covers truth at nominal rate across a hazard grid.
2. **Null** — flat hazards across all ports must *not* yield significant port
   effects. False-positive rate reported. Reviewers ask this first.
3. **Confounded** — all true signal onboard (single index case, `λ_p = 0`);
   the model must not attribute it to ports. Reviewers ask this second.
4. **Censoring** — same true hazards with a voyage truncated one day after the
   last port; the last-port estimate must not collapse (guards §1.6).
5. **Mis-specification** — fit with the wrong incubation distribution and with
   the wastewater channel off; report the bias magnitude rather than hiding it.
6. **Retrospective — voyage-level, not individual-level.** The proposal assumed
   deidentified MIDRS line-level data with shore-excursion status. CDC states
   that MIDRS AGE counts *"do not represent the number of active AGE cases at
   any given port of call or at disembarkation"*
   ([Federal Register, 2025-11-21](https://www.federalregister.gov/documents/2025/11/21/2025-20580/proposed-data-collection-submitted-for-public-comment-and-recommendations)).
   Port-call attribution is therefore **outside** what MIDRS can support, at
   any level of access — this is a data-content limit, not an access
   negotiation. The voyage-level fallback is promoted to *the* retrospective
   design:

   - **Numerator**: MIDRS/VSP voyage-level AGE case counts and outbreak reports.
   - **Denominator/exposure**: port-visit history reconstructed from external
     itinerary sources — published cruise line schedules and AIS-derived port
     calls — joined to each voyage by ship and date. Feasibility of that join
     (coverage, ship-name matching, per-visit dwell time) is an open question
     and the first task of that PR, not an assumption.
   - **Ashore fraction**: not observed. It enters as a prior with a
     platform/region-conditional distribution, and the sensitivity of the port
     hazard to that prior is reported, since it scales the offset directly.

   The identification burden therefore shifts entirely onto **itinerary
   crossover** (§4) plus the censoring correction (§1.6): with no individual
   shore-excursion status there is no within-voyage ashore/aboard contrast, so
   the ranked #1 evidence source in §4 is unavailable retrospectively. Expect
   wide intervals and report them; the retrospective validates *ranking and
   sign*, and the synthetic suites (1–5) carry the calibration claims.

   Any commercial-data fusion beyond schedules/AIS (e.g. excursion booking
   volumes as an ashore-fraction proxy) is speculative and stays out of the
   spec until a source is actually in hand.
7. **Prospective pilot** — 3–5 ships, repeated itinerary, wastewater sampling,
   voluntary symptom reporting. This is the only design that recovers
   individual shore-excursion status, which after (6) makes it the *primary*
   route to an individual-level hazard rather than a nice-to-have. Note the §4
   warning: a single shared loop is the worst case for crossover
   identification; stagger port order across the pilot ships deliberately, and
   record shore-excursion status and crew shore leave per person.

Test design follows `.agents/skills/ci-test-design`: graded sensitivity
(raising the true hazard at one port raises its posterior mean, monotonically
over ≥3 levels) and bounds/invariants (hazards positive and finite,
attribution shares sum to 1, censoring correction never decreases a late-port
estimate), with at most two labeled golden values as change detectors.

## 7. Implementation plan

PR-sized, each independently reviewable and green on its own. Estimates are in
Devin sessions.

| PR | Content | Est. |
|---|---|---|
| 1 | Spec (this doc) + `voyage_config.schema.json` optional port metadata (`port_id`, `region`, `calendar_date`, `crew_shore_leave_fraction`) + `schemas/sentinel_observations.schema.json` + `sentinel/itinerary.py` view + fixtures + `tests/test_sentinel_data_contracts.py` | 0.5 |
| 2 | **Foundation.** `export_line_list.py`: per-person onset/exposure line list out of an ABM run dir. Today `orchestrator_record.record_epoch` emits aggregates and drops per-agent blobs in `compact` retention, so no per-person onset epoch survives — every later PR and both synthetic-recovery claims stand on this one. Land it before anything downstream is designed against a guessed schema. | 1 |
| 3 | ✅ Phase 2 port exposure: `shore_infection_probability` applied as a per-epoch-ashore hazard in `step_shore_introductions`, crew shore leave in `apply_ashore_and_embarkation` (§1.7), both gated on `voyage.shore_exposure.enabled` (default off, `crew_shore_leave_fraction` default 0.0); introductions recorded as `truth_introductions` for recovery scoring; golden-run invariance test when off | 1 |
| 4 | ✅ `incubation.py` (lognormal/discrete delay pmfs on the epoch grid, forward convolution, strictly-lagged renewal, `observed_onset_fraction` censoring term, censoring-aware Richardson–Lucy back-calculation) + `exposure.py` (per-port × stratum cells, ashore denominators from the ledger or reconstructed from the schedule, ascertainment, log offsets, incubation-weighted port attribution) + `data/incubation_distributions.json`. `observations.py` needed no change — PR 1 already parses cases, hours ashore, and `exposure_totals`. Pure numpy, no Stan. | 1 |
| 5 | `sentinel_attribution.stan` + `_sentinel_data.py` + `fit_sentinel_attribution.py`: single-ship Poisson-offset hazards with renewal secondaries and sampled `R_onboard`; fixture posterior for CI | 1.5 |
| 6 | `sentinel_fleet.stan`: port-visit × ship hierarchy, fleet-time effect, crew repeat exposure; synthetic recovery + null + confounded + censoring suites | 1.5 |
| 7 | `wastewater_signal.py` beta-binomial channel wired into the latent curve; per-channel `evidence_loglik` | 1 |
| 8 | ✅ `run_sentinel.py` CLI + `artifacts.py` fit-directory loader + `figures.py` + `report.py` + `--smoke` in `ci.yml` | 0.5 |
| 9 | (Phase 3, separate track) strain label in the ABM, then `genomic_linkage.py` | 2 |
| 10 | (Retrospective track, gated on §6) voyage-level model: MIDRS/VSP counts × AIS/schedule port-visit reconstruction, ashore-fraction prior + sensitivity. First task is the ship/date join feasibility check. | 1.5 |

Order matters: 3 before 5–6, because recovery/null/confounded validation needs
the generator. 7 is deliberately after 6 so the wastewater channel's marginal
value is measurable against a working clinical-only baseline — which is itself
a result worth reporting.

Out of scope: no change to transmission physics, HVAC, the diagnostic cascade,
or SOP escalation. The sentinel layer never calls `ShipSimulation`; it reads
run outputs (as `boundary/` does), with the exceptions of PR 3 and PR 11, which
touch the simulator behind default-off flags.

## 8. Shipboard wastewater sampling operations

PR 7 gave the fit a wastewater channel; nothing generated samples for it, so its
value was untestable. `picard_framework/analysis/sentinel/wastewater_ops.py` is
the generator, behind `wastewater_surveillance.enabled` (default **false**, so
every existing run stays bit-identical — the draws also use a separate RNG
stream so enabling the channel cannot perturb the epidemic it observes).

| Setting | Meaning |
|---|---|
| `sampling_interval_epochs` | Epochs between bottles; gates emission only |
| `holding_tank_residence_hours` | Mean residence `tau` of a first-order tank lag, `w = exp(-epoch_hours / tau)`; `0` is a direct line tap |
| `collection_points` | Greywater taps; zones split into contiguous blocks, one row each per sampled epoch |
| `sequencing_depth` | `total_reads` per row |
| `pathogen_shedding_to_reads_scale`, `background_read_fraction` | Place shedder prevalence on the read-fraction scale metagenomics reports |
| `assay_mode` | `qpcr` \| `amplicon` \| `metagenomic` (default) \| `long_read` — what the laboratory reports off the tank (§1.3 addendum) |
| `qpcr`, `amplicon`, `long_read` | Optional per-mode calibration blocks (standard curve, LOD, extraction recovery, depth, turnaround) |
| `pathogen` / `pathogen_id` | Delay-catalog key written on samples / ABM profile counted as shedding |

The tank advances every epoch whether or not a sample is drawn, because the
smearing is physical rather than an artifact of observation. Rows match
`WastewaterSample` (§3) and reach the fit via the sentinel line list;
`concentration_copies_per_l` and `clr_anomaly_score` stay optional — the
simulator has no qPCR observable (§1.3).

Multiple taps in one epoch are **correlated replicates**, not independent
likelihood terms: `pool_wastewater` collapses an epoch's rows into one trial
with a capped effective depth, so spatial coverage sharpens an epoch instead of
multiplying the evidence. `fit_sentinel_fleet` therefore takes
`--wastewater-residence-hours` and `--wastewater-max-effective-reads`, so a cell
can be fit under the residence time it was actually sampled with.

The operating envelope this opens up is scanned by `sentinel_ww_ops_scan_v1`
(4230 runs) — see `docs/sentinel_wastewater_ops_scan.md`.

| PR | Content | Est. |
|---|---|---|
| 11 | ✅ `wastewater_ops.py` generator + `wastewater_surveillance` config + `sentinel_ww_ops_scan_v1` design/manifest + residence/effective-read fit controls | 1 |
