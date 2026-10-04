# ANCHOR-DERIVE-01 — derivation of the `covid.T1` clause targets under CAREGIVER-V1

> **Status:** Findings (2026-10-04). Derivation of record at `04d6ef18`.
> No cell ran and no constant changed: this is a derivation, not a
> measurement. Every figure quoted is attributed to the ledger entry and
> `main` SHA it was measured at; the targets themselves are traced to the
> named record publications behind `covid.T1`.

This doc answers the two questions THETA-REFIT-01 left open: (1) where
the clause's two targets — the 197 count and the 0.173 before-split
share — come from in the record, traced to their origin in the repo and
to the underlying Diamond Princess record; and (2) whether either
target is mechanism-dependent — whether the record figures implicitly
assume a transmission structure that CAREGIVER-V1 changes, or are
measured-direct observations any correct model must reproduce
regardless of mechanism.

## 1. The clause

Verbatim, as scored by the v10 design and carried unchanged through
v11–v15 and the THETA-REFIT-01 chain
(`picard_framework/runs/covid_theta_screen_v10_design.json`, criterion
at line 116; takeoff floor `takeoff_recorded_onsets: 10` at line 96):

> Among takeoff seeds (`recorded_onsets >= 10`), the q05–q95 interval of
> `recorded_onsets` contains **197** AND the takeoff-seed median
> `before_share` is within **0.10** of **0.173** — `before_share =
> onsets_before_split_day / recorded_onsets`, `0.173 = 34/197` onsets
> before day 17 = 6 February 2020. Scored only when the row has >= 5
> takeoff seeds.

The clause scores the model's dated-onset histogram against two cuts of
the record's dated-onset histogram: its total, and its split at the
quarantine order.

## 2. Where the targets come from

### 2.1 The 197 — count leg

Repo origin: `covid.T1` in `data/observation/covid_fit_targets.json`
(lines 14–31): `recorded_onsets: 197`, `recorded_onsets_range:
[197, 199]`, evidence grade A, source

> MHLW/NIID Diamond Princess epidemic curve (200223_epi_curveENG) and
> the NIID field briefing of 19 February 2020: onset dates among
> confirmed cases with a recorded onset.

What the figure *is*: the **dated-onset subset of confirmed cases** —
onset dates among confirmed cases with a recorded onset. The anchor's
own note fixes the denominator (fit spec §8,
`docs/proposals/covid_trajectory_fit_spec.md` lines 189–193): the
published curve covers 197–199 of the cases; further symptomatic cases
had their onset imputed from a ~3-day report lag and are *not* in this
denominator. The same §8 makes `covid.T1` the primary anchor precisely
because onset is test-independent — `covid.T3` (positives) moves with
test volume, so a wrong campaign replica would be absorbed into
biology; T1 cannot be.

Record context: by the briefing's ~20 Feb horizon the record carries
619–634 confirmed cases of 3,711 aboard; the published epi curve dates
the onset of 197–199 of them. (Population 3,711 = 2,666 + 1,045:
`data/scenarios/covid_hull_scenarios.json` provenance, Tsuboi 2020,
grade A.) The count leg therefore asks: conditional on ignition, does
the model's distribution of *confirmed cases with a dated onset*
straddle 197?

### 2.2 The 0.173 — timing leg

Same anchor block: `onsets_before_day: 34`,
`onsets_on_or_after_day: 163`, `split_day_index: 17`,
`split_calendar_date: "2020-02-06"` → `34/197 = 0.1726 ≈ 0.173`.

The split day is a calendar cut at the ship's regime change. The
record's timeline, all grade-A provenance in
`covid_hull_scenarios.json`:

- day 0 = 2020-01-20, departure Yokohama (`day_zero`); index onset 19
  Jan = day −1, declared by SEED-ONSET-01 (Yamagishi 2020,
  Eurosurveillance); index disembarks Hong Kong 25 Jan = day 5
  (`departure_day: 5.0`, same source).
- No RT-PCR aboard before 3 Feb = day 14
  (`molecular_ascertainment.start_day`: quarantine officers boarded
  3 Feb, collected specimens 3–4 Feb, first 31 results reported 5 Feb;
  NIID briefing 19 Feb; Mizumoto 2020 Table 1 — no reported tests
  before 5 Feb).
- MHLW cabin-quarantine order 5 Feb = day 16, passengers confined
  5–19 Feb while crew continued service duties (`SOP-017` window days
  16–30; `confinement_enforced: true` — Yamagishi + NIID briefing).
- The split at day 17 = 6 Feb is thus the first full day under the
  quarantine order: the share of dated onsets that had already
  presented before the ship changed regime.

Both legs are cuts of one histogram — "how many dated onsets" and
"what fraction of them predate the intervention".

## 3. Is either target mechanism-dependent?

### 3.1 The record quantity encodes no transmission structure

The dated-onset histogram was produced by: real infections → real
symptomatic courses → the real testing campaign (no RT-PCR aboard
before 3 Feb, then mass screening) → onset dating by interview/report.
Each bin is a count at a date. Whatever transmission occurred aboard —
droplet, aerosol, fomite, attendant-carried discovery, and *any
caregiver-mediated transmission that really happened* — is already
inside the histogram. The record does not decompose by route, and it
does not need to: a model under any mechanism mix is asked to
reproduce the same two cuts. There is no route-conditional version of
197 to re-derive, because 197 is not a statement about routes.

### 3.2 The model-side channel is commensurate by construction

The comparison was made like-for-like before CAREGIVER-V1 existed.
`crusher_labs/modalities/syndromic.py` lines 919–927 describe the
channel verbatim:

> The Diamond Princess onset curve (NIID field briefing, 19 Feb 2020)
> is onset dates among confirmed cases with a recorded onset: 197 of
> 619 cases by 20 Feb. … A host enters this channel only once it is
> laboratory-confirmed and presenting a syndrome-eligible severity;
> the day recorded is the day it first presented.

`_onset_observation` (same file, ~966–1004) gates on exactly that:
`_lab_confirmed` + `illness == "SYMPTOMATIC"` + `_onset_eligible`
severity. The profile declares no `onset_recording` channel, so every
confirmed symptomatic onset is dated — matching the record's
"confirmed case with a recorded onset". The scenario's ascertainment
gate (`start_day` 14) mirrors the real testing timeline: a January
onset enters the recorded curve only if a specimen taken from 3 Feb
tests positive, which is the record's own selection. Scoring-side,
`picard_framework/covid_theta_fit.py` computes `recorded_onsets` as the
sum over that curve and `before_share` at `split_day 17`. Model
quantity and record quantity are the same construction.

### 3.3 What CAREGIVER-V1 changes — and what it cannot change

The mechanism adds two things (docs/caregiver_v1_spec.md): **R2
tending**, a transmission path — elevated co-presence of a designated
family responder in the ill host's cabin over declared tending hours —
and a **discovery stamp**: `caregiver_report_due_epoch` routes a
presenting host into `sick_call_ids` + `true_positive_ids` through the
attendant channel, bypassing the host's own sick-call hazard
(syndromic.py ~505–513). Both land *inside* the same recorded-onsets
channel: tending produces infections that later present and are dated;
the stamp accelerates a presenting host into lab confirmation, and
confirmation is what admits an onset to the dated curve.

That discovery path is not a model artifact — the real ship had
attendants and companions carrying passengers to medical; that is why
the record holds dated onsets for cases that never self-presented at
sick call. So CAREGIVER-V1 changes the model's *prediction* of the two
cuts (more pre-quarantine infections via tending; more onsets reaching
the confirmed-and-dated subset via attendant-carried discovery); it
cannot change what the cuts *are*. A re-derivation of 197 or 0.173
"under CAREGIVER-V1" is incoherent: the record already contains the
real outbreak's caregiver component.

### 3.4 The scorer's conventions are not record quantities

Everything else in the clause is a frozen scorer convention, not a
record figure: the q05–q95 band, the ±0.10 share tolerance, the
`>= 10` takeoff gate, and the >= 5-takeoff-seed scoring floor are all
fixed in the design files (v7/v8 lineage, verbatim through the refit).
None encodes a mechanism; none changes under CAREGIVER-V1.

The one mechanism-adjacent element is the takeoff conditioning itself:
under a channel-lifting mechanism more seeds clear `>= 10` trivially,
so the gate's meaning drifts. But conditioning cannot rescue the
clause — every measured row on the refit surface already sits at 19/20
takeoff, so the conditioning is met at essentially every seed, and the
legs still fail. Tightening the gate would only discard seeds; it
cannot manufacture a θ where both legs hold, because the disjoint
half-planes are already measured on the takeoff subset.

### 3.5 The measured surface confirms the split is on/off-aligned

If 197/0.173 were the wrong target for a caregiver-bearing outbreak,
the pass/fail split would not be expected to line up with the
mechanism's on/off state on the same observables. It does:

- **CAREGIVER-ATTR-01** (`b932d0e9`,
  `docs/covid/covid_caregiver_off_v1_readout.md`): `caregiver.mode:
  off` on the identical observation stack and hull clause-passes —
  takeoff 11/20, q05 10, band ∋ 197, `before_share` 0.200 inside the
  ±0.10 window.
- **THETA-REFIT-01** (`78f52a58` / `8f49652f` / `8f926382`,
  `docs/ledger/THETA-REFIT-01.md` + addendum): all 15 shipped-default
  rows on [1e6, 1e9] fail >= 1 leg; the admissible half-planes are
  disjoint (θ_c ∈ (1e6, 1.4e6) count-leg crossing; θ_t ∈ (5.62e6,
  7.9e6) timing-leg crossing) — WINDOW-EMPTY-ORDERED, certified.

The target is reachable by the same measurement stack on the same
hull; the residual lives in what the mechanism adds.

## 4. Verdict: (b) — certificate of mechanism-independence

**Both targets are measured-direct observations of the actual
outbreak.** Neither the 197 count nor the 0.173 share assumes a
transmission structure; both are cuts of the real dated-onset
histogram, which already contains whatever caregiver-mediated
transmission truly occurred. The model-side channel is commensurate by
construction and CAREGIVER-V1 feeds the same channel, so the
comparison stays like-for-like under the mechanism. No re-derived
clause target exists to state.

Consequence: the clause **legitimately fails** under shipped defaults,
and the suspect moves to the mechanism's pre-quarantine delivery
strength — exactly as the parent prompt anticipated. The witness
columns sharpen it (`covid_theta_refit_*_v1_readout.md`):

- Pooled `aboard_window` caregiver acquisitions run **105–248** across
  all measured rows, monotone in Θ (105 at the 1e6 floor; 141–248
  across the 3.16e6→1e9 lattice; 116–138 in the bracket), while
  `during_quarantine` caregiver is **0 on every row**. The window is
  the index's days-0–4 aboard (events before `index_departure_epoch`,
  `picard_framework/covid_boarding_screen.py` ~1773–1821). The whole
  credited caregiver delivery lands inside the first five days.
- The during-quarantine zero is structural, not incidental: under
  SOP-017 every passenger is confined from day 16, a confined
  responder cannot be drawn, and the R2 pool is family-only
  (`docs/caregiver_v1_spec.md` §3/§5); R3 service continues but its
  respiratory credit is negligible in the tally.
- Normalized (approximate, stated as arithmetic on the pooled
  witness): ~105–248 acquisitions ÷ ~19 takeoff seeds ≈ **5–13
  caregiver-attributed acquisitions per takeoff seed inside days
  0–4** — against a record whose *entire* pre-6-Feb dated mass is 34
  onsets. A ~10-per-seed five-day caregiver floor is large against
  that. "Over-strong pre-quarantine delivery" is now the named
  hypothesis.

## 5. Proposed bounded follow-up — CG-FLOOR-01 (not run)

The conclusion demands a bounded probe of *delivery strength*, which
the non-goals bar running here. Proposed design, declared for the next
session:

- **Cells:** the two measured leg-crossing rows — Θ1e6 (count passes,
  timing fails) and Θ7.9e6 (timing passes, count fails) — × 20 seeds,
  seed-paired against shipped defaults.
- **Arm:** the frozen R2 factor box's low corner —
  `tending_copresence_multiplier` 1.5, `tending_hours` 2.0 — the
  bottom of the declared intervals (register §3.11; all Grade C
  declarations bounded above by the Kordsmeyer aOR 3.27 reproduction
  check). No new constants; a designation-without-dose arm would be a
  *new* declaration and is out of scope for the corner probe.
- **Read:** seed-paired Δrecorded_onsets / Δbefore_share, the pooled
  `aboard_window` caregiver tally, and a new witness — caregiver-route
  share of dated onsets per takeoff seed (attributes the dated curve's
  route composition; currently the payloads carry route tallies on
  acquisitions, not on dated onsets).
- **Verdict grammar, frozen:** DELIVERY-BOUNDED — the legs converge
  inside the declared box (the disjoint half-planes are factor-driven;
  next stage is a factor re-sourcing task) — or DELIVERY-STRUCTURAL —
  the legs stay disjoint at the declared floor (the defect is the
  mechanism's designation/discovery shape itself, not its constants).

## Sources

- `data/observation/covid_fit_targets.json` `covid.T1` (lines 14–31) —
  anchor values, grade, denominator note.
- `docs/proposals/covid_trajectory_fit_spec.md` §3.1 (line 60), §8
  (lines 186–196) — anchor table; onset-curve incompleteness and the
  recorded-onset denominator rule.
- `data/scenarios/covid_hull_scenarios.json` provenance array —
  population (Tsuboi 2020), day_zero/duration (Yamagishi 2020 +
  Tsuboi), index onset/departure (Yamagishi; SEED-ONSET-01), SOP-017
  window + confinement (NIID briefing + Yamagishi + Tsuboi),
  ascertainment day 14 (NIID briefing + Mizumoto 2020 Table 1).
- `picard_framework/runs/covid_theta_screen_v10_design.json` lines 96,
  116 — the frozen criterion and takeoff floor.
- `crusher_labs/modalities/syndromic.py` ~505–513, 919–927, ~966–1004 —
  attendant-channel stamp; channel construction comment;
  `_onset_observation` gates.
- `picard_framework/covid_theta_fit.py` ~306–356, 455–473 — scoring-side
  observables and `split_day 17`.
- `picard_framework/covid_boarding_screen.py` ~1773–1821 — aboard-window
  definition (events before `index_departure_epoch`).
- `docs/caregiver_v1_spec.md` §3/§5 — R2 tending grammar; confined
  responder cannot be drawn; factor table.
- `docs/ledger/THETA-REFIT-01.md` + addendum;
  `docs/covid/covid_theta_refit{,_floor,_bracket}_v1_readout.md` — the
  measured leg map and caregiver witness columns.
- `docs/ledger/CAREGIVER-ATTR-01.md`;
  `docs/covid/covid_caregiver_off_v1_readout.md` — the CG_OFF clause
  pass.
