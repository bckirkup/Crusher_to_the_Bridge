# NORO-HAND-PRACTICE-01
**Date:** 2026-10-01
**Commit:** #804
**Pathogens:** norwalk_gi, sars_cov2_resp
**Status:** open

Repair campaign for the `NORO-HAND-RESERVOIR-01` verdict `still_starved`
(PR #802): under `wash_reuptake`, occupancy on the frozen cells measured
3.35% vs Liu's 25.4% (R = 0.132, below the defect-band floor 0.2), the
event/routine ordering stayed unflipped, and the witness decomposition
showed **the deficit is retention, not delivery** — 80% of pickup mass
lands on non-challengeable hands and 87% of shedding rows underflow at
end-epoch because every stool event ends in a deterministic wash while
nothing reloads the hand between visits. Per the declared map that
outcome is a scope change — *a routine source needs a new emission term* —
and this entry declares it, with the wash itself rebuilt as a stochastic
practice per tranche 51 (`docs/literature/consensus_tranche_51_hand_practice.md`):
**the bathroom visit is a coin-flip wash with a per-act efficacy family
and a drying tail, and routine activity ticks reload the hand between
visits.**

## Design declarations (frozen before building)

### (i) Wash compliance — a toilet visit ends in a wash only sometimes

Each stool event remains a bathroom visit; the wash on it is gated by a
persistent per-host `wash_compliance` drawn U(0.35, 0.75) — observed
post-restroom wash fractions 51.1% basic (Lawson 2019) and 63% any-wash
(Drankiewicz 2003), interval covering both. This is the mechanism Liu's
post-bathroom column (12.4% ≥ LOD) actually implies: a deterministic wash
suppresses post-visit positivity toward zero; a compliance-gated wash
leaves a contaminated-but-unwashed residue, and the residual survives on
the roughly half of visits nobody washes after. Declared: no per-event
correlation between contaminate and comply draws (no data).

### (ii) Routine washes — non-bathroom hygiene exists

Measured total hand-hygiene frequency is ~5–10/day (Machida 2020 median
5, IQR 3–8; Machida 2021 mean 10.2; Głąbska 2020 3–10 pre-pandemic); the
stool-event stream already accounts for 1.0–5.63/day. The residual —
per-host `routine_washes_per_day` U(2, 8), Poisson within each epoch —
runs as routine washes anywhere in the epoch, each with the same per-act
efficacy draw and wet-window mark. Grade C declared residual; it is the
suppression term that keeps routine loads below the pre-PRACTICE-01
steady state even when ticks are active.

### (iii) Per-act efficacy — a soap/water mixture, not one distribution

Each wash act (bathroom or routine) independently draws soap use at
share 0.4 (Drankiewicz), then efficacy from the sourced family: soap
N(2.03, 0.5) clip[0.5, 3.5] vs water-only N(1.55, 0.6) clip[0.2, 3.0]
log10 (Hilton 2025 meta-analysis, virus arms; the declared spreads are
deliberately wider than the meta-analytic CIs — a CI over a summary mean
is not a per-act spread). The authored `HAND_HYGIENE_EFFICACY_LOG10`
stays untouched: it still serves the `wash_reuptake`/`spike_decay`
baselines and the `hand_hygiene_rate_per_hour` profile lever. Standing
liability recorded: Hilton's field-study LRVs are 0.45–0.55 — lab
efficacy overstates the distracted 8 s rinse; a future arm could bound
that gap.

### (iv) Drying — a wet window, not a permanent wet hand

The shipped `HAND_TO_SURFACE_LOGNORMAL` is documented at its own
definition as a *wet-contact* parameterisation (Tuladhar immediate 13%,
Bidawid 13%) — today every contact behaves as if the hand were wet.
Under this repair each wash act marks a residual-moisture window of
U(20, 90) s (Patrick 1997: moisture controls translocation; no duration
series retrieved, declared Grade C). The epoch-level deposit multiplier
is the wet-share blend
`wet_share·1 + (1 − wet_share)·dry`, with `dry` ~ U(0.005, 0.08)
(Tuladhar 13%→0.1% ≈ 0.008; Sharps 59%→<1% ≈ 0.017; Patrick's wet:dry
translocation ratios 47–486× bracket the reciprocal). Applied to every
donor-hand deposit path — `_shedder_surface_deposits`, `_food_deposits`,
and hand→hand contact — because Patrick's measured translocation is a
deposit in each case. Pickup (surface→hand) unchanged: the shipped
pickup distribution was measured off dried donor surfaces already, and a
wet *recipient* hand's uptake gain is plausible but unretrieved —
declared out of scope. Susceptible pickup wetness likewise unmodelled
(susceptible hands carry no per-pathogen practice state).

### (v) Routine re-loading — the missing emission term

Between bathroom visits a shedding host reloads its own hands through
ordinary activity: a per-host episode stream `self_contacts_per_day`
U(2, 8), Poisson within each epoch; each episode adds
`propensity × logU(50, 6300)` GEC (Pickering 2011 per-activity
increments, tranche 40 §4) capped at the visit ceiling `target`.
Ram 2011 reads within-person hand titres as 2–3.5 log10 swings over
hours — bursts then decay, not a plateau — so the stream runs at the
daily scale of the activities that plausibly re-inoculate, and a
per-hour drizzle at Pickering increments over-supplies by construction.
The propensity coupling is a declared structural choice: a host that
does not contaminate at the toilet also seeds its own surroundings
less, and the coupling is what produces Liu's never-positive tail
without a separate clean-subject flag. Tick rate Grade C declared;
increment Grade C (indicator CFU on a different population). Both
bounds, neither fitted.

### (vi) Ordering inside the epoch is declared, not resolved

At epoch granularity the physical order of event/tick/wash placement
inside the hour is unidentifiable; the arm processes decay → stool event
(contaminate, then compliance-gated wash) → routine washes → self-contact
ticks, and the census reads the post-state. Event rows therefore carry
the wash residual of that visit; routine rows carry the tick equilibrium.

### (vii) Continuous arm (profiles without `stool_events_per_day`)

SARS-CoV-2's relax-to-target arm gains the routine-wash stream and wet
windows only — no stool events, no self-contact ticks (no fecal source
term exists for it; continuous shedding is the emission). Net effect: its
hand reservoir sits below the ceiling between washes for the first time.

### (viii) Engine gating — `hygiene_cycle` becomes the default

`transmission.hand_reservoir_mode`: **`hygiene_cycle`** (default — this
repair) / **`wash_reuptake`** (labelled baseline, the RESERVOIR-01 arm,
bit-identical on matched seeds) / **`spike_decay`** (labelled baseline,
the shipped pre-RESERVOIR mechanism). Per the standing convention the
new mechanism ships default-ON and the old arms stay as named baselines.
`_apply_hand_hygiene` (profile lever `hand_hygiene_rate_per_hour`,
default 0.0) is unchanged and orthogonal. RNG consumption is confined to
the new arm — baselines draw nothing extra.

## Constants bound

| Constant | Value | Source / grade |
|---|---|---|
| `HAND_WASH_COMPLIANCE_RANGE` | U(0.35, 0.75) | Lawson 2019 51.1% / Drankiewicz 2003 63%. B, Ab |
| `HAND_WASH_SOAP_SHARE` | 0.4 | Drankiewicz 2003 38% soap. B, Ab |
| `HAND_WASH_EFFICACY_SOAP_LOG10` | N(2.03, 0.5) clip[0.5,3.5] | Hilton 2025 virus S+W LRV 2.03 [1.45,2.62]. B, R/T2 |
| `HAND_WASH_EFFICACY_WATER_LOG10` | N(1.55, 0.6) clip[0.2,3.0] | Hilton 2025 virus water-only LRV 1.55 [0.74,2.35]. B, R/T2 |
| `ROUTINE_WASHES_PER_DAY_RANGE` | U(2, 8) | Machida 2020/2021, Głąbska 2020 totals minus stool stream. C, Ab |
| `SELF_CONTACT_TICKS_PER_DAY_RANGE` | U(2, 8) | Declared (Ram 2011 swings; daily episode scale). C |
| `SELF_CONTACT_INCREMENT_GEC_RANGE` | logU(50, 6300) × propensity | Pickering 2011 per-activity increments. C, T |
| `HAND_WET_SECONDS_RANGE` | U(20, 90) | Patrick 1997 moisture window; duration undeclared. C, Ab |
| `HAND_DRY_TRANSFER_MULTIPLIER_RANGE` | U(0.005, 0.08) | Tuladhar 0.008 / Sharps <0.017 / Patrick reciprocal. B, Ab |

## Match criteria (frozen before the census runs)

Same four criteria as NORO-HAND-RESERVOIR-01 on the same frozen cells
(`fl_spr_12d` seeds 8105–8164, `classic_cruise_1900` seeds 8000–8019,
288 epochs, `tools/noro_diag/hand_occupancy*`):

- **Occupancy** vs Liu 0.254: R ∈ [0.2, 5.0] clears the defect band;
  R ∈ [1/3, 3] earns `restored`.
- **Ordering** — median post-visit event-row load < median non-event row
  load: **required**.
- **Never-positive share** ∈ (0.05, 0.80) vs Liu 0.33.
- **Positive-mean** log10 ∈ [2.30, 5.45] vs Liu [3.30, 4.45].

Reported alongside, ungated: the shedder share of delivered pickup mass
(the RESERVOIR-01 delivery witness) and the wet-window share of
deposit-direction transfers (the drying witness this arm adds).

Verdict map: `mechanism_restored` = all four pass with ordering flipped
and R ∈ [1/3, 3]; `partial` = inside the defect band but ordering
un-flipped or a secondary window missed; `still_starved` = R < 0.2;
`over_supplied` = R > 5 — reported, not re-tuned.

## Validation gate

pytest slice over touched paths + `pre-commit` + `sonar_guard` +
`tools/sanity_checker.py --from-config`; the frozen-cell re-census runs on
AWS Batch at the merged SHA (same `picard-hand-occupancy` instrument and
S3 `campaign/noro_hand_reservoir_01/` dump prefix family) and the
measured verdict is appended here.

## Measured verdict: `still_starved` (census at merged `d0466064`)

Frozen-cell re-census on the built arm (`picard-hand-occupancy:5`,
digest-pinned at the merge SHA; 42 cells: spirit 22/22, classic 18/20
void 8011+8015; S3 `campaign/noro_hand_practice_01/`): occupancy
2.82% vs Liu's 25.4% → **R = 0.111** (was 0.132 under `wash_reuptake`);
ordering `event_higher`, un-flipped; never-positive 0.564 and
positive-mean 2.586 log10 inside their windows. The emission term
fires on every cell and still starves: the additive propensity-scaled
ticks are erased by the multiplicative wash + inactivation strip, and
the ordering cannot flip while the routine source rides the same Beta
carriage trait as the events. Drying witness active: mean deposit
factor 0.046, window open on 4.7% of rows. Full decomposition appended
to `docs/ledger/NORO-HAND-RESERVOIR-01.md`; readout at
`docs/norovirus/noro_hand_practice_01/hand_occupancy_cells.json`.
