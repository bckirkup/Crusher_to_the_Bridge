# Activating the influenza arm: what it needs, in what order, and what it must not borrow

> **Status:** Proposed. **Nothing here is implemented.** No profile is added to
> `data/pathogens/active_profiles.json`, no constant, engine constant, schema,
> grade, interval or adoption state changes in this document, and no value is
> adopted. It is the sequencing document for a change not yet made.

**Ruling it implements.** Influenza should become an active arm, and before the
genotype structure people will eventually want, it has to be shown capable of
reproducing the *pattern* of past cruise-ship influenza outbreaks.

**Its evidence base** is [`../literature/consensus_tranche_20_shipboard_influenza_anchors.md`](../literature/consensus_tranche_20_shipboard_influenza_anchors.md),
which assembles the shipboard anchor set. **Its authoritative parameter state**
is register §3.3. Read both; this document repeats neither.

---

## 1. What "active" means mechanically, and why it is not a copy

`influenza_a` exists in `data/pathogens/edison_10pathogen_profiles.json` and is
absent from `active_profiles.json`, so no run loads it. Activation is not the
one-line move of pasting it across, for four reasons that are properties of the
*profile*, independent of any literature question:

1. **It carries a faecal-release constant.** `dose_adjustment: 1.5` is now
   spelled `environmental_faecal_release_log10_g_per_epoch` and means −log10 of
   the **grams of stool** released to the environment per epoch. On a
   respiratory arm that key has no referent at all, and it multiplies into
   dose. It must be removed or replaced by the respiratory equivalent, not
   carried across because the schema tolerates it.
2. **Its route numbers are shares, and the engine reads multipliers.**
   `transmission_route_weights` (0.2 / 0.35 / 0.3 / 0.15) sums to 1.0, i.e. it
   was authored as a mixture. The engine reads that key as the deprecated alias
   of `route_efficiency_multipliers`, which are **independent per-route dose
   multipliers, not shares**. Renaming the key without re-deriving the numbers
   would silently reinterpret a mixture as five efficiencies.
3. **It has no observation model.** The norovirus arm's `observation_model`
   (`system: VSP_AGE`) and `severity_model` are how simulated infections become
   *counted* cases. Influenza has neither, so an activated arm would emit
   infections against anchors that are all reported illness (tranche 20 §2).
   This is the substantive work, and §3 is about it.
4. **Its susceptibility scalar is not what the other arms carry.** Both active
   profiles have `base_susceptibility: 1.0`; influenza has **0.65**. It would
   be the only arm where a prior-immunity assumption is folded into a
   susceptibility constant — register §3.3 already grades it **F, and it is
   prior immunity**.

Minor, and not a blocker: `recovery_day: 5` truncates a 15-day
`shedding_curve_log10` with no `shedding_duration_days` to separate infectious
period from illness duration. Unlike the norovirus case, the loss is small — the
curve peaks at day 3, so ~99.7% of the linear-scale integral is inside the
window — but the two clocks should still be separated at activation rather than
coinciding by luck.

## 2. The anchor decision, which comes before every parameter

Tranche 20 §2 measures, on one voyage, 8.9% NAT-confirmed infection against
0.7% presenting to the infirmary. The literature's much-quoted "3.8% to 37%"
range is that ladder read as one quantity.

So the first decision is not a value. It is: **which rung is the influenza
arm's likelihood?** The recommendation is the two rungs that are measured
rather than reconstructed:

| Rung | Anchors | Role |
|---|---|---|
| **Laboratory-confirmed infection**, passengers | Ward 2010: 8.9% (3.9% pdm09 + 5.0% H3N2 + 0.1% both), n = 1,970 | primary — the only rung tied to the state the model actually simulates |
| **MAARI**, passengers and crew separately | Millman 2015: 3.7% / 3.1% (Ship A, n = 2,595 / 1,057) and 6.2% / 4.7% (Ship B, n = 2,987 / 1,157) | primary — the rung a ship's own data produces, and the only one with a passenger/crew contrast |
| Self-reported ILI/ARI post-voyage | Brotherton 37% of 836 respondents; Miller 17% of 1,284 | **validation only** — questionnaire recall, respondent denominators, non-influenza ARI included |
| Case counts without a denominator | Fernandes 104 cases | **excluded as a rate** (blocked read, tranche 20 §4) |

Two constraints on that set, both from the fleet ruling in
[`fleet_emergence_decision.md`](fleet_emergence_decision.md):

- These rates are the **likelihood**. No influenza parameter may be sourced by
  which value reproduces 3.7% or 8.9%.
- The set is **five ships**, two of which share an itinerary shape, one of
  which yields no rate. Its identifiable content is one or two composites, not
  a per-outbreak fit. Any activation that needs more free quantities than that
  is not testable on this anchor.

And one that is specific to this arm: **the influenza fleet count cannot be a
likelihood at all.** Tranche 20 §3.3 — seasonal-influenza reporting to CDC is
*voluntary*, and the maritime threshold is 1.38 ILI cases per 1,000
traveler-days, a different functional form from VSP's passenger-fraction rule.
Where norovirus's fleet aggregate is blocked on a missing denominator (#13),
influenza's is additionally self-selected in the numerator. The fleet-as-sensor
use case therefore cannot be built on the influenza posting record.

## 3. The three things activation must supply

### 3.1 An observation model, whose capture fraction is *not* norovirus's

The norovirus arm's infirmary capture (anchor A3) is **0.60 ± 0.05**. Ward's
two rungs imply **≈0.08** for influenza on the same kind of hull. Reusing A3
would overstate influenza's visibility by roughly 7×, and would do it
invisibly, because the arm would still be producing plausible-looking infection
counts.

An influenza `observation_model` therefore needs, at minimum: its own
severity-graded case eligibility (MAARI, not AGE), its own reporting
probability, and the traveler-day threshold rule as its posting condition
rather than VSP's. Two further multipliers are measured and belong in it rather
than in the transmission model:

- **MAARI is not influenza.** Of tested MAARI cases, 22–57% were confirmed
  (tranche 20 §3.6) — the syndromic rung over-counts influenza 2–5×, and the
  multiplier differed between two ships three weeks apart.
- **Serology undercounts.** 31% of SHIVERS seroconversions were NAI-only, so an
  HAI-defined infection endpoint misses about a third.

### 3.2 Prior immunity, as a scenario input, per subtype and age

`base_susceptibility: 0.65` cannot survive activation as a constant, and the
reason is measurement, not taste:

- On Ward's single voyage, pandemic H1N1 had **RR 17.4 (10.5–29.1)** in children
  aged 3–6 and **zero cases** in passengers over 65, while H3N2 was **flat
  across every age band**. One scalar cannot hold both.
- Vaccination does not behave like a susceptibility reduction in any shipboard
  record: Millman's crew were 90% and 95.5% vaccinated, and 93.9% and 100% of
  crew cases were vaccinated; Brotherton found no significant protection;
  Ortiz 2023 found HAI ≥40 does not separate infected from uninfected
  (p = 0.126).

So prior immunity is a **per-season, per-subtype, age-structured scenario
input** — the same status the ship model gives an itinerary. It is also the
single most dangerous quantity on this arm: it is the one knob that can absorb
any discrepancy with §2's rates while looking like an assumption. It must be
declared and swept, never fitted.

### 3.3 An emission path that is not a fraction of a nasal curve

`surface_deposition_fraction: 1e-3` is the deprecated spelling of
`airborne_emission_fraction`, which feeds the **airborne** zone reservoir. Yan
2017/2018 (EMIT) measured absolute emission — GM 3.8e4 copies/30 min fine
aerosol, 1.2e4 coarse — and found it **uncorrelated with nasopharyngeal swab
load**. A fraction of a nasal-swab-indexed shedding curve is therefore the one
form the evidence excludes.

This is exactly the defect R4 resolved for norovirus, by redefining the field
rather than re-sourcing the number: norovirus became emesis-conditioned with an
interval. The influenza analogue is an **absolute per-host aerosol emission
rate** in Yan's own units. Not proposed here; recorded as the shape the repair
has to take.

## 4. What does *not* block activation

Two items that would otherwise sit in the critical path can be closed as
declared approximations, on evidence:

- **Surface decay.** `surface_decay_log10_per_day = 1.221849` is a **5.9 h
  half-life**, which sits at the slow edge of Qian's measured 4.5–5.9 h
  respiratory-matrix range and well inside its 2.4–8.6 h credible interval. The
  five available studies bracket roughly [0.27, 4.8] log10/day (Thompson's
  175 h to Greatorex's 1.5 h) and the spread is **matrix, not strain**
  (Perry: p = 0.45). That is a declared interval containing the shipped point,
  not a null — and the test is empirical: sweep the field across the bracket and
  see whether any scored observable moves.
- **The biphasic form** proposed in [`surface_decay_biphasic_spec.md`](surface_decay_biphasic_spec.md)
  can be closed as **refused on evidence rather than for want of sourcing**:
  Rockey 2024 finds a wet/dry split in saliva but **none in airway surface
  liquid**, the matrix a ship deposit resembles, and French 2023's phase
  ordering reverses between conditions. Refusing it deletes three proposed
  degrees of freedom, which on a five-ship anchor is worth more than a better
  point estimate would be.

Also not a blocker, and deliberately deferred: **`dose_response.k`**. It stays
as register §3.3 has it — 0.18 exponential, Grade C, with the cited aerosol and
intranasal evidence disagreeing by one to two orders and the route-efficiency
ratio absent. `k` and emission enter as a product, so this is the same
identifiability constraint as register §4 items 4 and 6 and must move with
them. An activated arm should run with `k` **swept across its sourced
disagreement**, and must not have it fitted to §2's rates.

## 5. Subtypes: where influenza is *easier* than norovirus, and where it is harder

The pathogen-class ruling in [`pathogen_class_structure_decision.md`](pathogen_class_structure_decision.md)
refused genotype-indexed norovirus structure because the anchor carries **zero**
genotypes, making shares unidentifiable. Influenza inverts one half of that and
worsens the other:

- **Easier — the shares are externally measured.** Subtype composition is
  published per season and per region (WHO FluNet, CDC FluView), so the class
  mixture is a *declared external input* with real provenance, not a
  placeholder. The bundle's uniform `H1N1: 0.5, H3N2: 0.5` is a placeholder and
  must be replaced by, or indexed to, the season being represented. And unlike
  norovirus, the shipboard anchors are typed: Ward reports 78 pdm09 against 100
  H3N2 on one voyage, Millman three co-circulating viruses on Ship A and
  influenza B alone on Ship B.
- **Easier — the class difference is measured, not assumed.** Ward's age-specific
  RRs (§3.2) are a direct measurement of subtype-differential susceptibility in
  one population. That is the influenza counterpart of the secretor odds ratios
  that justified the norovirus GII.4 / non-GII.4 split.
- **Harder — importation is plural.** Both Millman ships and Ward's voyage
  carried **two or three co-circulating viruses**, with onsets before departure.
  The one-founder-per-voyage simplification the norovirus decision leaned on is
  contradicted by the observed norm here, so the founder draw has to admit
  multiple simultaneous importations at embarkation.
- **Harder — influenza B is a third class, not a subtype of A.** Ship B's
  outbreak was influenza B alone, and Brotherton's was A and B together. An arm
  with only H1N1 and H3N2 cannot represent two of the five anchor voyages.

Recommendation: activate with **one pooled influenza A arm** and no phenotype
differences (they are all 1.0 today in any case), because §2 supports one or two
identifiable composites. Add classes only when the season's declared external
shares are wired in — and add influenza B as a class before adding a third
influenza A subtype, since the anchor set demands B and does not demand more A.

## 6. Sequence

| # | Step | Depends on |
|---|---|---|
| A1 | Declare the anchor rungs and their denominators (§2), as a register anchor block — likelihood, not prior | tranche 20 |
| A2 | Strip the faecal-release key, re-derive route numbers as multipliers under the current key, separate the two clocks (§1) | — |
| A3 | Author the influenza `observation_model` + `severity_model`, with its own capture fraction and the traveler-day posting rule (§3.1) | A1 |
| A4 | Demote `base_susceptibility` to a declared per-season, per-subtype, age-structured scenario input (§3.2) | A1 |
| A5 | Add to `active_profiles.json` with `k` and prior immunity **swept**, not fitted; report whether the sweep's envelope contains §2's rates | A2, A3, A4 |
| A6 | Only if A5's envelope fails: repair the emission path (§3.3) before touching anything else, since a fraction-of-nasal-curve emission is the one form the evidence excludes | A5 |
| A7 | Deferred: influenza B as a class; then external seasonal subtype shares; then per-class phenotype offsets | A5 |

A5 is the test the ruling asked for, and it is a test the arm can fail. The
honest failure mode to watch for is §3.1's: an arm that produces the right
*reported* rates through a capture fraction borrowed from gastroenteritis, at
the wrong infection prevalence.

## 7. What this document does not do

It adopts no value, changes no grade, activates no profile, authorises no fit,
and does not re-grade any register row. It does not treat any shipboard rate as
a prior. It does not propose fitting `k`, `base_susceptibility`, route
efficiencies, or a capture fraction to the anchors in §2. It does not claim the
influenza arm can reproduce those anchors — that claim is A5's to earn.
