# Paper-1 simulation plan — execution assessment

> **Status:** Assessment for Edison. Evaluates the proposed course of action for the
> first norovirus model-development paper against repository state at `fdae828b`
> (2026-11-20). Claims marked *measured* carry the revision or ledger entry that
> measured them; claims marked *inferred* or *hypothesis* are labelled. No new
> simulations were run for this document.

Responding document: Edison's recommended next simulations (four-hull joint
evaluation, temporal reconstruction, scale/geometry separation, one
protective-response demonstration, embedded uncertainty panel), with the stated
funding priority of items 1 and 2 and the ordering bridge → pilot → ensemble.

## Verdict

**The course of action is fundable as proposed, and the proposed ordering is the
right one.** Every item is executable on the current machinery. The single
largest new artifact is the dedicated Explorer vessel representation for item 2.
The plan's one premise that needs sharpening is that "the substantial baseline
and sensitivity work already completed" preserves *structure*, not numbers: the
last four-hull-scale measurement predates roughly seven weeks of mechanism
repair, and the open ledger's dose-figure stamp still stands on anchor outputs.
The paired bridge Edison proposes first is therefore not only a continuity check
— it is the measurement of whether the model at the frozen reference still
produces the quiet/outbreak mixture the paper's central claim needs. Treating
the bridge as an explicit go/no-go gate makes the whole sequence safe.

## What the plan assumes, checked against the ledger

**The four-hull ladder exists and is the right set.** The standard grid is
`expedition_cruise_450` (450), `classic_cruise_1900` (1,910),
`spirit_cruise_3000` (3,000), `mega_cruise_5000` (7,000 emitted complement),
used most recently by NORO-GENO-02's 4 × 3 × 4 × 3 × 20-seed mass surface
(measured at `4f5e7fbe`, 2,880/2,880 runs).

**The last joint four-hull evaluation predates the repair train.** Since
`4f5e7fbe` (2026-09-29) the tree landed, among others: (the solver screens
measured per-hull posting on selected seed strata later — `6742f1a4`,
`455f9ff7`, `c6c3c25f`, October–November — but they are seed-selected
screens, not the joint outcome evaluation item 1 calls for) CONTAM sanitary-direction,
galley/door/ducted/exhaust-sink link repairs (each withdrawing the
downstream-map dose figures that rested on them), ambient openings and
weather-deck sinks on the cruise hulls, room-air removal, the FOOD-SUPPLY-01
receipt/lot layer, the continuous hand-flow solver, spirit cabin relief, and
duct exclusions. Every withdrawn figure stands at its own `Measured at` SHA —
that is what the ledger is for — but none of them are figures of the current
model. The bridge Edison proposes is the correct instrument: labelled-baseline
arms reproducing a prior draw give a bit-identity check, and the paired strata
tell which results need fresh measurement rather than assuming it.

**The open anchor question is the quiet/outbreak mixture itself.** The last
anchor-scored run at scale (admissible-region gate v2, `admissible_region_37_v2`,
2026-09-07) returned **0 of 256 Sobol' points admissible**; the binding gap was
the absent symptom-conditioned spreading-efficiency term, with the quietest
box point still posting at ~6× A9's ceiling. That term is now implemented
(`SYMP-EFF-01`: hand recontamination drawn from stool-event rate, diarrhoeal
and non-diarrhoeal arms sourced separately) — but its effect on the
quiet/outbreak mixture at the current engine **has never been measured at
scale**. This is *inferred* risk, not a measured defect: the quiet-region
re-measurement is precisely what item 1 does. It is also the reason the bridge
should be read before ensemble cells are committed.

**The dose constant is settled; the anchor figures are not.**
`environmental_faecal_release_log10_g_per_epoch` = 7.57 [7.14, 8.86] was
re-derived as the chain-composed hand-route release per ill host-day
(`NORO-DOSE-REFIT-01`, `4a619493`). The ledger's stamp — every *other* dose
figure void pending refit — remains: attack rates, route shares, ladder tables
and per-host dose tables measured pre-refit are historical. This is an
argument *for* Edison's item 1, not against it.

**"One declared reference version" is itself a work item.** The engine moves
several times a week. The frozen block pattern exists (NORO-GENO-02 carried a
verbatim frozen `dose_adjustments`/`config_overrides` block on every cell). A
Paper-1 reference needs: a named commit, a frozen config block pinning every
mode whose default has flipped or may flip (sanitary visit mode, flush aerosol
fraction, cabin air mode, pathogen pool transport, droplet field split, room
air removal, near-field air — per the default-ON refinement rule every artifact
must pin the mode it measured), a declared limitations list citing the
ledger's open items, and a moratorium on mechanism work during evaluation.
None of this is machinery; it is a freeze decision plus a design file.

## Item-by-item execution needs

### 1. Joint four-hull evaluation — executable, one campaign dir missing

Every outcome Edison lists is already emitted or derivable from emitted data:

| Outcome | Source in run output |
|---|---|
| Routine + reported burden, role splits | `rep_pax_n`/`rep_crew_n`, `cumulative_reported_cases_*`, census |
| Reaching the reporting threshold | `vsp_trigger_epoch` (either-channel since `VSP-EITHER-CHANNEL-01`) |
| Outbreak-size distribution, tails | seed ensemble of the above; ≥1,000 seeds/cell for tail frequencies (measured precedent: NORO-OUTBREAK cells, lowposting 1,440-seed re-run) |
| First role to threshold | per-epoch `cumulative_reported_cases_{passenger,crew}` vs the 0.03 wire |
| Daily onset and reporting curves | `run.sentinel_line_list` — per-person `onset_epoch`, `report_epoch`, `crew`, channel (`SentinelLedger`, built for `compact` retention). Caveat: `report_epoch` is the strongest-channel detection clamped to onset (`max(channel_epoch, onset)`), not the operational report counter — the reporting curve comparable to an infirmary log comes from the per-epoch `cumulative_reported_cases_*` series, the line list supplies onsets and detection channels. Second caveat: the series is seeded at embarkation by `preboarding_reportable_ids` (VSP 4.1.1.2 reportable AGE declarations bypass the sick-call ladder), so bucket zero carries pre-boarding reports — the Explorer comparison actually wants this (five passengers reported pre-boarding illness) but the readout must label it, not read it as onboard sick-call |
| Environmental observables | `observation.surface_swab_source: surface_pool_density` + `wastewater_assay_mode: holding_tank` are shipped defaults (`environmental_observation_v1`) |

**Missing:** a joint-evaluation campaign (`campaigns/noro/<name>/` — design +
`build.py` + `cell.py` harvesting all six families in one run + readout), the
paired bridge strata (quiet / near-threshold / outbreak cells spanning all four
hulls), and the freeze described above. Bridge seed counts are per-stratum:
~20 seeds prove contract cleanliness and resolve loud cells, but a quiet
stratum at a ~0.5% event rate returns only a bound (zero postings in 20 seeds
bounds the rate at ≲14%), so quiet cells carry more seeds or are reported as
bounds, with the tail-resolution cells at the ≥1,000-seed scale above. The
voyage settings Edison says to retain are 168 / 288 / 504 epochs (7 / 12 / 21
days at 24 epochs/day).

### 2. Explorer temporal reconstruction — empirical target already extracted; one platform to build

The comparison data are in-tree (`mega_voyage_source_evidence.md`, measured
input snapshot `74a6eff3`): the Feb 26 – Mar 5, 2006 itinerary with daily
onsets transcribed — passenger peak Feb 28, crew peak Mar 2 (the two-day lag
Edison wants tested) — investigation finals 252/3,245 passengers, 20/1,183
crew; posting figures 243/3,245 and 19/1,184 reserved for cross-posting
comparisons. Introduction is documented: five passengers reported pre-boarding
illness, CDC judged person-to-person propagation from pre-boarding cases, no
common dining location among ill crew — declared introduction block, nothing
fitted.

**Missing:**

- **`data/platforms/explorer_*`** — the dedicated vessel (Voyager-class;
  3,245 passengers / ~1,184 crew). Needs `spatial_layout.json`,
  `air_flow_paths.json`, `voyage_config.json`, contam bundle, manifests. The
  platform dir pattern and the `adding-new-platform` /
  `importing-naval-blueprint` paths cover this; it is the largest single
  artifact in the whole plan.
- **A third voyage length**: 8 days ≈ 192 epochs — outside the retained
  168/288/504 set, needed only inside this study.
- **The comparison archetype named**: Explorer bins to **mega_cruise_5000**
  under the repository's passenger-complement rule (3,245 > the 3,240.37
  boundary). Running mega alongside answers Edison's vessel-specificity
  question — with one caveat: mega differs from Explorer in geometry *and*
  complements (~5,000/2,000 vs 3,245/1,184), so a stock-mega contrast
  measures the bundle, not geometry alone; separating the two is what item
  3's population/composition contrasts are for, and the reconstruction
  readout should not attribute the whole delta to vessel fidelity.
- **Fruit-cluster verification**: the cluster is traced to AIDAdiva/AIDAluna
  September–October 2019 (spirit-class; `mega_voyage_source_evidence.md`). The
  repo does not yet record whether Rispens et al. publish per-day onset curves
  sufficient for a second temporal reconstruction — a cheap literature check
  should gate that expansion, which is exactly the condition Edison placed on
  it.

### 3. Population / composition / spatial separation — two legs cheap, one leg needs build

- **Total population** and **passenger–crew composition** are config-level
  contrasts (population draw, `config_overrides.ship_graph.agent_classes` —
  all seven classes declared summing to 1.0; `agent_class_fractions` is the
  stamped *output*, not the input key). Paired-seed designs are the existing
  pattern.
- **Spatial and dining organization** is not a config dial on existing
  platforms: it needs synthetic platform variants (re-zoned dining/venue
  structure). Proportionate to build only for contrasts the cheap legs show to
  be informative — Edison's own sequencing says this.
- The **implemented supply-side census** Edison references is
  `SUPPLY-STRUCTURE-01` Stage A (`supply_structure` rungs: `independent`,
  `line_shared`, `venue_group_shared`, `fleet_shared`; `venue_menu` masks;
  `lot_scale`): implemented and smoke-tested in PR #1319, **never run at
  campaign scale** — it is the inexpensive first analysis he describes, and its
  design is already frozen.

### 4. Protective-response demonstration — all machinery exists

- Earlier recognition: diagnostic cascade tiers and syndromic surveillance are
  shipped; `variant_surveillance.enabled` and cascade configs are arm-level.
- Isolation response: `crew_duty_exclusion` (`engines/crew_duty_exclusion.py`)
  implements the VSP §4.4.1.1.1 rule — food employees held 48 h symptom-free,
  other crew 24 h — declared, `enabled: false` by default. Two wiring facts
  shape the arm design: its trigger reads `ever_reported_ids`, which
  syndromic sick-call reports populate but cascade detections do **not**, so
  an earlier-recognition-via-cascade arm does not fire exclusion earlier
  unless the trigger is widened or the pairing keys on syndromic
  identification; and admits are added to `quarantined_ids` without a
  `quarantine_order_epoch` write, so isolation person-days come from the
  per-epoch `quarantined` series, not the order-epoch map. SOP-008
  symptom-triggered removal exists at ALERT.
- Outcome set: illness and role burden (census + reported), recognition-to-action
  time (report/trigger epochs vs action epochs), isolation person-days
  (per-epoch quarantined counts), operational disruption (OIS in
  `cost_accounting`), reported-vs-true illness (both emitted). An arm +
  readout design only; no engine work expected beyond a possible trigger
  wiring decision above.

### 5. Uncertainty panel — machinery exists, screen must re-run

The parameter provenance register and Morris bounded-screen machinery exist,
but every screen result on file is pre-refit **and** was produced on an
interval box since invalidated (per §1 of the open ledger). The panel Edison
wants is a fresh focused screen on the frozen reference — introduction,
natural history, recognition/reporting, dominant environmental/contact
representation — cheap relative to the ensemble.

## Sequenced execution plan

| WP | Work | Depends on |
|---|---|---|
| WP0 | `explorer_*` platform build (new recipe in `scripts/cruise_platform_recipes.py` + generated `data/platforms/<id>/`), sanity + schema + data-contract validation, one 192-epoch smoke | —; lands **before** the freeze so the named reference SHA contains the pilot vessel (Benjamin, 2026-11-20) |
| WP1 | Freeze decision: named commit + frozen config block + declared-limitations list; moratorium during evaluation | Edison review of the design contract (his pre-freeze lane); WP0 merged |
| WP2 | Joint-eval campaign authored (`campaigns/noro/<name>/`); paired bridge canary over the strata; readout as go/no-go | WP1 |
| WP3 | Temporal-reconstruction campaign (mega archetype alongside, paired seeds, 8-day = 192-epoch voyage) | WP0 + WP1 |
| WP4 | SUPPLY-STRUCTURE-01 Stage A census at scale + population/composition contrasts | WP1 |
| WP5 | Response-demonstration arm + readout | WP2 readout (pick recognition/isolation pairing on measured behaviour) |
| WP6 | Focused Morris re-run on frozen reference | WP1 |
| WP7 | Ensemble expansion + replication where intervals/tails require | WP2 readout |

Edison's rare-event arithmetic is right and the stratified-allocation machinery
it argues for is the existing tier/block pattern. The 0.005 illustrative event
probability should itself be treated as unmeasured on the current engine — the
bridge returns the actual event rate per stratum.

## Corrections and flags for Edison

- **"Retained voyage settings"** are 7/12/21 days; Explorer is a third length
  (8 days), only inside item 2 — noted so the frozen grid does not silently
  acquire a fourth axis.
- **Name the archetype**: the alongside comparison for Explorer is
  `mega_cruise_5000` by complement binning, stated so "existing large-ship
  archetype" is not ambiguous at build time.
- **The complement denominators differ across sources** (crew 1,183 vs 1,184;
  final counts 252/3,245 investigation vs 243/3,245 posting). The repository
  convention is investigation figures for the curve, posting figures for
  cross-posting comparisons — adopt it in the reconstruction spec.
- **The fruit cluster's expansion is correctly conditional**; the per-day
  onset detail has not been confirmed in the source. Run the literature check
  before scoping a second dedicated hull.
- **First-role-to-threshold is a model-side outcome**: the public posting
  series carries final counts, not which role crossed first, and the pooled
  classic/spirit denominators do not separate them; the empirical comparator
  for role timing is thin — the Explorer onset curves by role (and one
  investigation noting crew illness preceding passengers across successive
  voyages, Crisp et al.) are it.
- **"Baseline and sensitivity work already completed"** preserves designs,
  seeds, strata and comparators — not numbers. Almost every quantitative
  statement the paper would reuse is stamped void or predates the repair
  train; the bridge is what turns that prior work back into evidence.
- **A4/A8/A9 as previously mapped are partially design-limited or
  definitional**, not purely parametric (the 23× conditional/unconditional
  separation is computed in-run; the crew posting channel is repaired). The
  refreshed evaluation should score them as the ledger now defines them, not
  as the September gate did.

## Return path (how results reach Edison)

No new infrastructure is needed or proposed:

- **Committed readouts** under `docs/norovirus/` — the established "for
  Edison" surface (`cross_hull_outbreak_evidence.md`,
  `mega_voyage_source_evidence.md`), readable through Edison's GitHub PAT.
- **Bounded campaign artifacts** via `campaign_collect.yml` +
  `github-crusher-collector` covering `campaign/*` (each dispatch waits on the
  `aws-campaign` approval), with a bounded manifest in the
  `contam_edison_return_01` shape.
- **Push ingest** via `edison-client` `store_file_content` where a file should
  land directly; the token (`EDISON_PLATFORM_API_KEY`, repo Actions secret)
  has a short TTL and must be checked live before a return leg.
- **Check artifacts, not engines**: aggregates, hash-verifiable cell indexes,
  and small spot-recompute helpers — Edison verifies computations, it does
  not run them.

## Decision for Edison

1. **Freeze point**: propose the evaluation design contract (WP0+WP1 design
   files) for his pre-freeze review, with head at freeze time as the named
   reference; his blocker findings gate the freeze as before.
2. **Bridge gating**: confirm the paired bridge is read as a go/no-go before
   ensemble cells are committed — this is his ordering made explicit.
3. **Temporal pilot first**: agree with his recommendation; the platform
   build itself now lands **before** the freeze so the reference SHA carries
   the pilot vessel — the reconstruction campaign then runs on the same
   named commit as everything else.
4. **Response demonstration**: name the decision pair at design time —
   candidate is earlier recognition (cascade/surveillance arm) + crew duty
   exclusion vs usual recognition, all four hulls, paired seeds — unless he
   prefers a different already-implemented decision.
5. **Fruit cluster**: a second temporal reconstruction is gated on confirming
   per-day onset curves in the source; the check is cheap and runs first.
