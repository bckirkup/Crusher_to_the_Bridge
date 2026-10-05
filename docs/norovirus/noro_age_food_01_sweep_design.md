# NORO-AGE-FOOD-01 sweep design — passenger age composition × food channel

> **Status:** frozen — grid, arms, pairings, and reporting split are
> frozen before any array submits. No criterion in this file may be
> altered after a surface exists.

First crossed demographic × food-channel campaign on the post-HOST-AGE,
post-FOOD-COMMON-SOURCE engine. Until now every norovirus fleet cell
sailed the shipped generic passenger mix — the uniform-band default
bundle under the shipped class fractions — so the just-landed age-graded
machinery (HOST-AGE-02 presentation factor, HOST-AGE-03 severity
partition, both default-ON) has only ever seen one population.

The campaign asks how passenger age structure and the common-source food
channel **jointly** move the scored outputs: incidence (acquisitions
per voyage), posting rate (VSP ≥3% share per 1,000 voyages), and attack
rate (infection AR by role, plus the reported-case channel), on the
expedition hull family and at a few mega-hull cells.

This is a measurement campaign: **there is no selection criterion.**
No cell is admissible or inadmissible by outcome; every arm was declared
here before the first run, and the findings are the per-cell readouts
and the pairings named below — never a point estimate fitted to an
anchor.

## Axes and semantics

### Axis A — age composition (3 arms)

Armed per-tier through `config_overrides.social.agent_profile_bundle`
(repo-root-confined `load_agent_profile_bundle`) plus, on `fam`, a
`ship_graph.agent_classes` fraction override (the shipped family share
0.10 cannot carry a family-market child fraction — verified arithmetic
in the bundle's derivation block).

| arm | bundle | class mix | composite passengers |
|-----|--------|-----------|----------------------|
| `gen` | shipped `default_ship_population.json` | shipped fractions | ~5% under-18, ~14% ≥65 |
| `snr` | `data/scenarios/agent_profiles/senior_cruise_dp2020.json` — DP-derived (NIID briefing + Tsuboi 2020, the only measured cruise composition in-tree); all crew classes draw the DP crew composition | shipped fractions | ~60% ≥65, ~2% under-18 |
| `fam` | `data/scenarios/agent_profiles/family_cruise_u18.json` — family class reweighted to 56% under-18 across `0-4`/`5-17` (Grade C declared) | `passenger_family` 0.10→0.25, `passenger_general` 0.50→0.35 | ~20% under-18, ~14% ≥65 |

The age arms act on norovirus through exactly three channels — all
downstream of acquisition, so the age × incidence read measures the
indirect loop (presentation → emesis events → aboard spread), not a
susceptibility lever:

1. **Presentation** (`illness_probability.age_factor_by_age_band`,
   HOST-AGE-02): `child`/`0-4`/`5-17` → ×0.51, all other bands ×1.0 —
   ≥65 presentation is a measured NULL, deliberately not split.
2. **Severity partition** (`severity_model.base_probabilities_by_age_band`,
   HOST-AGE-03): `senior`/`65-74`/`75+` carry severe_critical 0.017925
   vs the reference 0.001 (Calderwood 2021 NORS LTCF, Grade C).
3. **Reporting compliance** (`syndromic_comp65` `compliance_by_class`):
   `passenger_young` 0.34 < `passenger_elderly` 0.54 < `crew` 0.65 —
   a family hull dampens reporting twice over.

### Axis B — food (6 arms on 2 sub-designs)

`transmission.common_source` block, per-tier `config_overrides`:

| arm | `mode` | `lot_event_probability` | `food_safety_posture` | `lot_posture_coupling` |
|-----|--------|------------------------|-----------------------|------------------------|
| `off` | **off** | — | — | — |
| `l1`  | on | [0.001, 0.0075] | 1.0 | false |
| `l2`  | on | [0.002, 0.015]  | 1.0 | false |
| `ship`| on | [0.02, 0.15]    | 1.0 | false |
| `p05` | on | [0.001, 0.0075] | **0.5** | **true** |
| `p20` | on | [0.001, 0.0075] | **2.0** | **true** |

`off` is the whole-mechanism labelled baseline: `_init_common_source`
spawns no `_cs_rng` stream and nothing draws — bit-identical to the
pre-mechanism engine on every channel, not merely "no events".

The posture arms are the VSP-moderated covariate shelved by FOOD-02:
`food_safety_posture` multiplies the handler/diner per-window rates, and
this campaign turns `lot_posture_coupling` on so the same ship-quality
scalar also scales the lot draw. **Flagged, deliberately:** FOOD-02's
design argued supplier-side lot contamination cannot depend on ship
galley practice and ran `lot_posture_coupling` false throughout. The
coupled arm here is the *labelled alternative* — it measures the
"sloppy ship is sloppy everywhere" covariate (a sloppy galley plausibly
also holds lots longer / handles more), and it is reported as a coupled
arm, not blended with the decoupled rungs. Posture rungs {0.5, 2.0} are
Grade C declared sweep coordinates around the 1.0 reference; the
measured input (VSP per-ship inspection scores, in-tree at
`telemetry_buffer/observation_model/vsp_inspection_series.csv`) has no
score→multiplier map in v1 — that map remains an open derivation, and
nothing here claims one.

## Grid and fixed coordinates

Fixed on every cell — identical to NORO-FOOD-01/02 and
NORO-OUTBREAK-02/03/04 so cells pair voyage-for-voyage: boarding rung
`shipped`, prevalence point bp32.5c18.5 (passenger 0.0325 / crew
0.0185 — the mid diagonal FOOD-01 measured flat), `nsf29`, 288 epochs
(12 d), `dose_adjustment` 7.57, surveillance `syndromic_comp65`, the
FOOD-02 transmission/hvac block unchanged, and escalation defaults
(0.05/0.02/0.03).

Seeds: exp 8000–8999; cls + spr 8105–9104 (the same voyage-for-voyage
pairing as FOOD-01/02); mega 8000–8287 (288 per cell).

| hull | cells | per cell | voyages |
|------|-------|----------|---------|
| expedition 450 | 18 = 3 ages × 4 lot + 3 ages × 2 posture | 1,000 | 18,000 |
| classic 1900   | 18 | 1,000 | 18,000 |
| spirit 3000    | 18 | 1,000 | 18,000 |
| mega 5000      | 6 = 3 ages × {l1, ship} | 288 | 1,728 |

60 tiers / 55,728 voyages. Tiers `fl_<hull>_12d_scr_<age>_<food>`;
manifest `picard_framework/runs/mega_cruise_campaign/noro_age_food_01_manifest.json`;
builder `campaigns/noro/age_food_01/design/build.py` (every arm and seed
declared there — regenerate, never hand-edit). Mega cells ride their own
campaign spec (`campaigns/noro/age_food_01_mega/`, 6144 MB — the
MEGA-IMPACT-01-proven container class); the rest submit under
`campaigns/noro/age_food_01/` at the FOOD-02 class (4096 MB).

## Free pairings (declared before first run)

- **gen column** pairs seed-for-seed against FOOD-01 (shipped rung) and
  FOOD-02 (l1/l2) cells — same seeds, but the engine delta is HOST-AGE
  landing between them, so the gen column doubles as the *measured
  consequence of the HOST-AGE mechanism on the generic mix*.
- **off column** gives the pre-food baseline on the *current* engine
  (the prior off cells ran pre-HOST-AGE; pairing there is loose, and
  this column is the clean current-engine reference).
- **snr/fam vs gen at the same rung** = the pure age-arm contrast.
- **p05/p20 vs l1 at the same age** = the posture covariate's direction
  and magnitude at the anchor-adjacent lot rung.

## Endpoints — reported, never selected on

Per cell, from `outbreak_anchor_readout.py` over the run zips
(campaign parameter stamps `common_source`, `agent_profile_bundle`,
`agent_class_fractions` are now written by `campaign_runner` itself —
the FOOD-02 jobdef monkey-patch is retired into the map):

- posting share per 1,000 voyages (VSP ≥3% rule)
- incidence: acquisitions per voyage
- attack rate: `infection_attack_rate_passenger` / `_crew`, plus
  `reported_case_rate_*` and `ever_ill_rate_*` (the infection → illness
  → report conversion)
- diagnostic (reported, never selected): common_source witness counters
  (events, takers, dose credited), emesis/onset curves, ill/inf share,
  genotype share of imports vs lot events

Reference anchors for framing only: posted share ~0.3–0.5% (VSP),
ill/inf ~0.18 hull-invariant (MEGA-IMPACT-01), excursion→posting
conversion ~43% (FOOD-01). **Nothing is fitted to these.**

## Audit invariants (a violation is a defect, not a failed arm)

- every `summary.json` carries `parameters.common_source`,
  `agent_profile_bundle` (absent only on `gen`), and
  `agent_class_fractions`;
- `off` cells show `common_source_events` = 0 on every voyage;
- crew class fractions and crew age composition are invariant across
  age arms (the arms move passengers only);
- `fam` arm totals: `passenger_family` ≈ 25% of agents and
  `passenger_general` ≈ 35% (berth shares held — all passenger classes
  berth in `PC_` zones).

## Gates and waves (the stop order)

1. **Local smoke** (done, this checkout): `fl_exp_12d_scr_fam_l1`
   index 0 voyage ran clean end-to-end — bundle resolved, class
   fractions stamped, `common_source` fired (4 events / 26 takers),
   contract files intact.
2. **Canary:** `canary_exp_snr_l1` (24 seeds 8000–8023) +
   `canary_exp_fam_l1` (8 seeds 8000–8007) submitted first; readout
   inspected (parameters stamped, contract intact, non-degenerate
   voyage). **Stop and report** — the user decides the fleet.
3. **Wave 1:** `fl_exp_*` + `fl_cls_*` blocks (36 cells, 36,000
   voyages) — land first.
4. **Wave 2:** `fl_spr_*` blocks (18 cells, 18,000 voyages) —
   independent submission; spirit is the ~4×-classic per-voyage cost
   and the wave to trim first if the budget says so.
5. **Wave 3:** `fl_meg_*` under `noro_age_food_01_mega` (6 cells × 288)
   — independent submission, its own image tag and jobdef.

Readouts report per wave as it lands (posting / incidence / AR tables
vs the gen and off columns), not only at fleet completion.

## Exclusions (settled, do not re-derive)

- No new epidemiological constants; no constant is chosen to move VSP,
  Park, attack-rate or incidence anchors. Bundle weights carry their
  own provenance blocks; the only measured inputs are the DP
  composition and the FOOD-02 lot rungs.
- No bp-diagonal expansion (FOOD-01 measured the excursion share flat
  across the diagonal), no `ren` rung, no 7-day tiers, no posture→lot
  decoupling arm re-run (the decoupled ladder is the lot rungs
  themselves), no engine or platform wiring changes.
- The `gen` column is re-run rather than copied from FOOD-02 because
  the engine moved (HOST-AGE); treating the pairing as exact is a
  known looseness and the design records it rather than hiding it.
