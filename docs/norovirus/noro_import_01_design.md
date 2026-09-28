# NORO-IMPORT-01 — design (frozen before any cell runs)

**Status:** frozen — admissibility and cell layout below are the contract the
canary and arrays run against; nothing here may be revised after the first
child lands.

Question: does any licensed point on the import axes produce establishment
(ignition → takeoff → posting), and which axis carries it? Sourced-admissible
region only; no fitting to anchors; every dose figure remains void pending the
open-ledger refit.

## Arms and axes

The norwalk_gi shipped profile is the full renewal arm (`rate_mode: renewal`,
`age_draw: stationary_detectable`, `illness_duration.draw:
empirical_survival`, `symptomatic_stream.enabled: true`, crew pre-boarding
clause on). The prevalence intervals in the register (pax [0.025, 0.040],
crew [0.007, 0.030], Grade B) are coordinates of the screening comparator;
the engine encodes them only under `rate_mode: screening_prevalence`, so the
map has two import families and Axis C bridges them.

- **Axis A — boarding prevalence** (screening family): pax/crew diagonal
  pairs `(0.025, 0.007)` lo / `(0.0325, 0.0185)` mid / `(0.040, 0.030)` hi —
  the two interval ends share a direction (more import), so the correlated
  diagonal spans the region; mid equals the shipped comparator.
  Mechanism: `boarding_mechanism_rungs: ["shipped"]` +
  `boarding_prevalence_points`. `_swept_block` writes the shipped block then
  the point — self-describing screening spec per cell.
- **Axis B — never_symptomatic**: `never_symptomatic_fractions`
  [0.22, 0.29, 0.36] (adult_challenge) on both families.
- **Axis C — symptomatic stream**: measured in two licensed forms of "off"
  because the code only permits the stream under renewal —
  `renewal_stationary` (renewal, stream off — the stream's isolated
  contribution) and `reportable` (the shipped default: renewal + stream +
  crew clause). The screening family above is the historical off-arm; the
  readout tables it separately so each interpretation of "off" is answered.
- **Axis D — dose_adjustment endpoints**: {7.14, 8.86} once each at the
  A-mid / B-mid / screening point (`fl_exp_12d_dose`) — confirms asserted
  inertness on shipped modes; then the axis collapses.
- **Flagged B (population-mismatched, not pooled)**: one
  `community_cohort` point 0.635 on the renewal/reportable arm
  (`fl_exp_12d_flag`) — bounds the regime's effect on the default stack.
- **Flagged α (what-if, never mixed into the licensed map)**: α = 0.15,
  β = 32.81 held, on one expedition-12d reportable cell
  (`fl_exp_12d_alpha`, `pathogen: norovirus_gii_alpha` — a second
  `pathogen_configs` entry deep-merging `dose_response.alpha`).

## Cells

| tier | platform | epochs | cells | seeds/cell | runs |
|---|---|---|---:|---:|---:|
| fl_exp_7d_scr / _ren | expedition_cruise_450 | 168 | 9 + 6 | 1000 | 15,000 |
| fl_exp_12d_scr / _ren | expedition_cruise_450 | 288 | 9 + 6 | 1000 | 15,000 |
| fl_exp_12d_flag | expedition_cruise_450 | 288 | 1 | 1000 | 1,000 |
| fl_exp_12d_dose | expedition_cruise_450 | 288 | 2 | 1000 | 2,000 |
| fl_exp_12d_alpha | expedition_cruise_450 | 288 | 1 | 1000 | 1,000 |
| fl_spr_12d_scr / _ren | spirit_cruise_3000 | 288 | 9 + 6 | 200 | 3,000 |
| fl_cls_12d_scr / _ren | classic_cruise_1900 | 288 | 9 + 6 | 200 | 3,000 |
| fl_mega_12d_scr / _ren | mega_cruise_5000 | 288 | 9 + 6 | 200 | 3,000 |

Total 43,000 voyages. Seeds: expedition 8000–8999, class 8105–8304 — the
RHYTHM-01 seed sets voyage-for-voyage, so the renewal mid cells (reportable
× nsf 0.29) are draw-identical replications of RHYTHM-01's cells and serve
as a built-in repeatability anchor. Same `config_overrides`
(transmission + hvac pins) and `syndromic_comp65` surveillance as
RHYTHM-01; dose_adjustment 7.57 fixed except the two Axis-D cells.

## Instruments and witnesses (frozen)

Driver: `tools/noro_diag/growth_chain_census.py`, extended so each run zip
carries the campaign-layout `summary.json` (`parameters` / `timeseries` /
`derived` / `summary` / `cost_accounting` — the same blocks a
campaign-produced zip scores under) plus `growth_census.json.gz` unchanged,
and a new `initiation` block in `summary.json`:

- the engine's `initiation_manifest` (per-pathogen `drawn_by_role`,
  `composition` per state incl. `symptomatic`, `preboarding_assessment`,
  `boarding_mode`, `prevalence`, `state_split`);
- the resolved `BoardingSpec` coordinates (`rate_mode`,
  `symptomatic_stream`, `symptomatic_passenger_prevalence` = p_sym,
  `symptomatic_crew_prevalence`, `passenger_prevalence`, `crew_prevalence`,
  `never_symptomatic_fraction`).

Per cell: n runs, ignition rate with 95% Wilson CI (emesis emit ≥1),
takeoff rate (`derived.peak_prevalence` ≥ 10), posting rate
(`derived.vsp_trigger_epoch` set), peak-prevalence distribution, growth
depth (concurrent-peak distribution from `timeseries`), and the placement
partition (emesis landing split from the census payload).

**Stream-consumption gate (before any renewal number is read):** every
renewal/stream-on cell must show `rate_mode: renewal`,
`symptomatic_stream: true`, resolved `symptomatic_*_prevalence` matching
the register derivation (p_sym ≈ 0.02746% under empirical_survival), and
fleet-pooled `composition.symptomatic` counts consistent with the binomial
expectation (mean ≈ p_sym × pool, reported with its binomial CI). A cell
whose stream drew zero symptomatic boarders is admissible only if the
expected count is ≪1 (small hulls); the proof is the resolved p_sym plus
the pooled counter, per the SMALLN-01 rule.

**Paired-seed discipline:** cells sharing a seed set are compared as
discordance counts (off-only / on-only / both / neither ignitions), not
independent rates.

## Report-immediately triggers

1. Any licensed point produces posting (first post-fix posting is
   scope-changing).
2. The renewal arm fails to exercise the symptomatic partition (resolved
   spec shows stream disabled, or pooled symptomatic count is inconsistent
   with the binomial expectation — a dead flag).
3. The α = 0.15 arm converts expedition takeoff (makes the GI.1→GII
   provenance decision load-bearing — escalate, do not fold into the map).

## Verdict rule

If no licensed point establishes: "mechanism-shaped in import/dose
structure" — the ledger names which boundary is binding (lowest import arm
that still ignites vs the prevalence ceiling reached). If a point
establishes, name the carrying axis.
