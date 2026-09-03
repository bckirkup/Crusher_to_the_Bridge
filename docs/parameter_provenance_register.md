# Parameter provenance register: every quantity, its class, and what blocks its adoption

Status: **register, 2026-09-02. This is the central record.** It is the document
to read before changing any epidemiological constant in any arm, and the document
to update in the same change.

It exists because the answer to "how many parameters are sourced now" was, until
today, only recoverable by reading five tranche documents in publication order
and applying two corrections issued mid-series. That is not a state a
defensibility claim can rest on.

## 0. What this replaces, and what it does not

| Document | Relationship |
|---|---|
| [`norovirus/norovirus_open_ledger.md`](norovirus/norovirus_open_ledger.md) | **Still authoritative** for what is *withdrawn*. Every dose figure is void pending refit; that record stays there. This register does not restate it |
| [`covid/covid_parameter_provenance_audit.md`](covid/covid_parameter_provenance_audit.md) | Absorbed as the SARS-CoV-2 rows of §3. Its §2–§5 arguments are not restated here |
| [`norovirus/norovirus_parameter_freedom_audit.md`](norovirus/norovirus_parameter_freedom_audit.md) | Absorbed as §5. Its measurements (the inert dose knob, the 15 observation-model numbers) stand |
| [`literature/`](literature/) tranches 1–5 and the Edison reviews | The evidence behind the Evidence column. Contextual: this register is the index into them, and where the two disagree, the tranche document holds the citation and this one holds the status |
| `formal_spec_v2.md` Appendix A | Superseded as a provenance record. Its source column was the baseline this register was built against |

## 1. Two axes, because one was hiding half the problem

Provenance class alone was the wrong instrument. Nine quantities in §3 have a
citation and *still cannot be adopted*, because the field they would go into
cannot express what the paper measured. Classifying those as "sourced" would be
the most dangerous entry in the table: it would look like provenance and encode
something the evidence rejects.

**Axis 1 — provenance class.**

| Class | Meaning |
|---|---|
| **M** measured | Direct measurement in the target setting, quantity and units check |
| **B** analogous | Direct measurement in an analogous setting (surrogate virus, different material, different host) |
| **I** inherited | Carried from the upstream Korkin Java model or another pathogen, with no measurement behind the transfer |
| **A** adapted | Derived from a measurement of something else by an unquantified adjustment |
| **C** assumed | No source; a plausible number |
| **P** placeholder | No source and not intended as one |
| **F** free | Available for fitting, by construction |
| **X** construction | Not a measurable quantity — a unit, a convention, a truncation bound |
| **S** scored output | Not an input. Listed only where a value has been mistaken for one |

**Axis 2 — adoption state.** The column that matters operationally.

| State | Meaning |
|---|---|
| **✓ adoptable** | Evidence exists, the field can express it, nothing blocks the change but the work |
| **⊘ field** | Evidence exists; the field's units or shape cannot represent it. Needs a schema or engine change first |
| **⊘ mech** | Evidence exists; the mechanism the field drives is the wrong mechanism. Needs a model change first |
| **⊘ joint** | Evidence exists but the quantity is not separately identifiable — it must be adopted together with another, or swept |
| **∅ null** | Searched, and no measurement of this quantity exists. Must be declared or bounded by argument, not sourced |
| **— in tree** | Already carries a citation in the tree |

## 2. Where the count actually stands

Against the #366/#369 baseline (SARS-CoV-2 8 sourced of 25, norovirus 6 of 35,
influenza 2 of ~25):

| | Count |
|---|---|
| Quantities that had no usable literature basis and now have one recorded | **24** |
| — of those, adoptable as they stand | 9 |
| — blocked by a field or mechanism defect (⊘) | **7** |
| — adopted in the tree | **2** (the FUT2 pair, Wave 1) |
| — provenance recovered but mis-genogrouped | 2 |
| — refuted, or shown to be unmeasurable (∅) | 4 |
| Profile scalars carrying a citation **in the tree** | still 8 / 6 / 2 |

The last row is the honest headline, and it has moved once. Wave 1 adopted the
FUT2 pair — `secretor_negative_fraction` 0.20 with
`secretor_negative_relative_susceptibility` 0.20 — by replacing the mechanism
that blocked them, and resolved the naming defect on the two renamed fields
(`route_efficiency_multipliers`, `airborne_emission_fraction`) without sourcing
either. The other in-tree change from the sourcing campaign remains one screening
interval (`surface_decay_per_day`, [0.10, 0.60] → [0.14, 0.84]). The remaining gap
is deliberate — adoption is queued behind the mechanism fixes in §4 — but it must
not be reported as progress on sourcing when it is progress on evidence.

## 3. The register

Shipped values verified against `data/pathogens/active_profiles.json` and
`data/pathogens/edison_10pathogen_profiles.json` on 2026-09-02.

### 3.1 Norovirus (`norwalk_gi`) — active

| Quantity | Shipped | Class | Evidence / interval | State | Task |
|---|---|---|---|---|---|
| `incubation` (3 fields) | — | M | Lee 2013, **GII** | — in tree | |
| `presymptomatic_shedding_days` | 0.5 | M | Atmar 2008 | — in tree | |
| `dose_response.alpha` / `beta` | 0.111 / 32.81 | I → **M (form and value)** | Teunis 2008 disaggregated GI.1, traced by Edison's bundle | ⊘ mech — **GI.1 inoculum, GII arm** | #21 note |
| `illness_probability.eta` / `gamma` | 0.508 / 0.095 | I → **M** | Teunis 2008, same table | ⊘ mech — same genogroup mismatch | |
| `secretor_negative_fraction` | 0.20 | B | FUT2 se428 nonsense-homozygote prevalence, European/North American populations ~20% (population genetics, not this setting) | ✓ **adopted** (#21) — demographic input, deliberately outside the screen box | #21 done |
| `secretor_negative_relative_susceptibility` | 0.20 | B | Teunis 2020 GII rows, 0.015 / 0.076 = 0.197; Rouphael GII.2 challenge (4 of 8 Se− ill at top dose) bounds the high end | ✓ **adopted** (#21); screened over [0.05, 0.50]. Implies a removed-equivalent fraction of 0.20 × 0.80 = **0.16**, the #367 ceiling | #21 done |
| `innate_nonsusceptible_fraction` | withdrawn from `norwalk_gi`; deprecated alias | — | The removed-fraction mechanism is refuted for GII and is no longer the norovirus mechanism. Alias retained (rr = 0.0) so the other bundles in `data/pathogens/` keep loading | — superseded | #21 done |
| **Divergence: campaign vs shipped profile** | campaigns write `innate_nonsusceptible_fraction` | — | `picard_framework/runs/mega_cruise_campaign/campaign_runner.py:988` still writes `innate_nonsusceptible_fraction` into its per-run overrides, so **every campaign run models sterile immunity in a removed fraction** while `data/pathogens/active_profiles.json` models FUT2 partial susceptibility. Behaviour deliberately left unchanged: the campaign *sweeps* the removed fraction, and converting the swept axis to a relative susceptibility is a design decision, not a rename | recorded, unresolved | |
| `shedding_variance_log10` | 1.0 | C | Teunis 2014, 102 subjects, peaks 10⁵–10⁹/g | ✓ | |
| `recovery_day` | 3 | I | Two independent sources on illness duration (tranche 3 §5) | ✓ | |
| `surface_decay_per_day` | 0.25 | C | Five surrogate studies → **[0.14, 0.84]** fractional loss/day, Grade B. Shipped value is *inside* it, near the slow end | ✓ interval **adopted in the screen box**; the profile value is untouched | #41 done |
| `airborne_emission_fraction` | 1e-4 (renamed from `surface_deposition_fraction`, value unchanged) | **C** unsourced-assumed | No study reports emission to a room reservoir as a fraction of shedding. The field feeds the **airborne** zone reservoir, which is now what it is called; the surface pools are fed by the emesis and faecal-release paths | — not blocked: the ⊘ field defect is **resolved** (#42) and nothing about the field now prevents adoption; it simply has no source | #42 done |
| `airborne_half_life_hours` | 1.1 | **I, cross-pathogen** | No measurement of airborne norovirus decay exists. The value is van Doremalen's SARS-CoV-2 figure | ∅ null — declare or bound by deposition physics | #39 |
| `route_efficiency_multipliers` (6) | 0.35/0.1/0.05/0.3/0.2/0.0 (renamed from `transmission_route_weights`, values unchanged) | C | None. Independent per-route multipliers, not shares — the schema now says so | ⊘ **joint** — the field defect is resolved (#25); these multipliers are not separately identifiable from Edison's pre-establishment clearance layer, which parameterises the same object, so no per-route efficiency can be adopted into one of the two alone | #25 |
| `environmental_faecal_release_log10_g_per_epoch` | 4.0 (`dose_adjustment`) | F → **measured inert** | Ge 2023 measures *total shed genome copies*, which retires the key rather than sourcing it | ⊘ field | #38 |
| Emesis titre (engine) | 3.9e4 GEC/mL | B, **from the abstract** | Kirby 2016 Table 3: GII.2 = 1.6e5. The abstract pools a 2-subject pilot the Results exclude | ✓ | #38 |
| Emesis volume (engine) | 50–800 mL/episode | B | Tung-Thompson 2015, Booth & Frost 2019. The defect is the *per-subject total* it implies — ≈200–600 mL against Kirby's measured 658.7 (GI) / 845.0 (GII.2) | ✓ | #38 |
| Emesis episode count (engine) | 1–3 | C, inferred | Kirby Results: 1–7 episodes | ✓ | #38 |
| `contact_transfer_fraction` (engine) | **1.0, by omission** — neither active profile sets it | C | The ~0.25 contact-model anchor is recorded in `norovirus/norovirus_model_history.md` §10 and is itself thinly sourced. Contact is now sampled at POLYMOD rates and transferred at unit efficiency. **Measured to clear no noise floor anywhere** in the screen | ✓ low priority | #22 |
| `SURFACE_TO_HAND_LOGNORMAL` (engine) | median 0.122 | B | Corroborated: close to measured **wet** finger↔steel transfer (Bidawid 13%, Tuladhar 13%, Dallner 9.2%) | — in tree, corroborated | |
| Cabin-localization fraction `f` | swept | C, declared | No measurement exists (Wikswo 2009 is the nearest and does not measure it). Park 2015's cabin swabs bear on it | ∅ null | #12 |
| Observation model (~15 numbers) | — | C / F | One empirical aggregate constrains them jointly, and that aggregate is anchor A3 | ⊘ **A3 is not a test** | #23, #27 |

### 3.2 SARS-CoV-2 (`sars_cov2_resp`) — active, not scoreable

| Quantity | Shipped | Class | Evidence / interval | State | Task |
|---|---|---|---|---|---|
| `incubation` (3 fields) | lognormal, 5.8 d, GSD 1.57 | M | Wei 2021, ancestral | — in tree (wrong for Omicron) | |
| `presymptomatic_shedding_days` | 2.0 | M | He 2020 | — in tree | |
| `airborne_half_life_hours` | 1.1 | M | van Doremalen 2020 | — in tree | |
| `surface_decay_per_day` | 0.95 | C → **M** | = 5.55 h half-life against van Doremalen's 5.6 h | — in tree (#366) | |
| `recovery_day` | 7 | C → **B** | #366 §3 | — in tree | |
| `shedding_curve_log10` (shape) | peak at index 4 | C → **B** | #366 §3 | — in tree | |
| `shedding_curve_log10` (magnitude) | peak 10⁹ | C, **mis-dimensioned** | Lane 2023 ~80 copies/min breathing; Coleman 2021 63–5,821 copies/activity; Alsved 2023 4–127 TCID50/s singing. Shipped term is a nasal concentration used as a rate, 2–4 orders high | ⊘ joint with β | #30 |
| `dose_response.alpha` / `beta` | 0.18 / 58.0 | C (attribution withdrawn twice, independently) | Killingley 2022 human challenge → ID50 ≈ 9.2 TCID50 ≈ 10³–10⁴ copies; Zhang & Wang 2020 → 4.4e4–6.8e5 copies. **The two disagree by 1–2 orders; that disagreement is the interval** | ⊘ joint — sweep 10³–7e5, adopt neither endpoint | #30 |
| `asymptomatic_shedding_log10` | peak 10⁷·⁵ | C | **Refuted**: measured URT loads are similar between symptomatic and asymptomatic in week 1. The 1.5-log10 offset has no basis | ✓ remove the offset | #31 |
| `shedding_variance_log10` | 1.2 | C | Schijven 2020: between-person SD 1.3–1.7 log10 | ✓ | #31 |
| Severity / asymptomatic fraction | absent | — | Buitrago-García 2020 (~31% screened), Sah 2021 (35.1%). **Tabata/Diamond Princess is barred — it is the training set** | ✓ with the screened denominator | #31 |
| PCR sensitivity vs time since exposure | absent | — | Tranche 3 §3 | ✓ — required by the observation layer | #33 |
| `illness_probability.eta` / `gamma` | 0.4 / 0.12 | C | Unattributed near-neighbours of norovirus's Korkin values. Yields 0.56 at the profile N50 — a dose-conditional value, not a population fraction | ⊘ field | #31 |
| `route_efficiency_multipliers` (6) | 0.25/0.3/0.3/0.1/0/0.05 (renamed, values unchanged) | C | None | ⊘ **joint** — field defect resolved (#25); not separately identifiable from the clearance layer, as norovirus | #25 |
| `airborne_emission_fraction` | 5e-5 (renamed, value unchanged) | **C** unsourced-assumed | Norovirus's 1e-4, halved, with no stated reason | — not blocked: field defect **resolved** (#42); unsourced, not blocked | #42 done |
| Secretor / innate nonsusceptibility | absent (key removed from neither — never set) | C, **defensible** | No known innate-resistance locus; correct by argument for a naive 2020 population | declared | |
| `base_susceptibility` | 1.0 | X | The unit modifiers act against | construction | |
| `immunocompromised_fraction` (shared, `config.yaml`) | 0.05 | C | Self-reported immunosuppression in US adults: 2.7% (Harpaz 2016, JAMA, DOI 10.1001/jama.2016.16477), 6.6% in 2021 (Martinson 2024, JAMA, DOI 10.1001/jama.2023.28019), 7.4% in 2022 (Li 2024, OFID, DOI 10.1093/ofid/ofae415). Nearest measurement in our setting: 24 of 1,196 international travellers = 2.0% (Lopez-Gigosos 2020, AJTMH, DOI 10.4269/ajtmh.19-0702). Interval ≈ **[0.02, 0.074]**, Grade B — the width is population and era, not uncertainty, so it wants an era-aware interval like the NPI sets | evidence recorded, **not adopted**: adoptable as an interval; shipped value unchanged in this change | |
| `immunocompromised_multiplier` (shared, `config.yaml`) | 2.0 | C | No study measures immunocompromised *acquisition* risk for norovirus; Green 2014 (DOI 10.1111/1469-0691.12761) states the persistence mechanisms are unknown. What is measured is **duration**: van Beek 2017 (DOI 10.1016/j.cmi.2016.12.010), 2,182 solid-organ recipients, 4.6% infected, 22.8% of those chronic, median shedding 218 days (range 32–1,164); Bok 2016 (DOI 10.1093/ofid/ofw169), persistent infection ≥6 months in 8 of 18 genotyped | ⊘ **mech** — evidence recorded, **not adopted**; see the note below | |

**The immunocompromised evidence measures duration, not susceptibility.**
Against a 7–14 day voyage a 218-day median shedding duration makes the relevant
immunocompromised host one who **boards already shedding**. That is an
importation channel, quantifiable as prevalence × chronic fraction, not a
susceptibility multiplier — which is why `immunocompromised_multiplier` is
recorded as ⊘ mech rather than bounded. It is a live lever now precisely because
of the composition fix in Wave 1: `immunocompromised_multiplier` is applied
multiplicatively (`*=`) rather than by assignment, so it composes with base
susceptibility and secretor status instead of overwriting them.

### 3.3 Influenza A (`influenza_a`) — **not active**, in `edison_10pathogen_profiles.json`

Not in `active_profiles.json`. Nothing here is loaded by a run today, and §4.4
must be resolved before it is.

| Quantity | Shipped | Class | Evidence / interval | State | Task |
|---|---|---|---|---|---|
| Incubation | — | M | Lessler 2009, median 1.4 d | — in tree | |
| `presymptomatic_shedding_days` | 1.0 | M | Ip 2017, ~1 d | — in tree | |
| `illness_probability.eta` / `gamma` | 0.67 / 0.1 | C | Carrat 2008: **66.9% symptomatic (CI 58.3–74.5), and dose-INdependent (p=0.12)**. The field is `1 − (1 + η·dose)^−γ`, monotone in dose, and yields 0.12 at this arm's own N50 | ⊘ mech — the *form* contradicts the source | #44 |
| `dose_response.k` | 0.18 (exponential) | C | Alford 1966 **aerosol** ID50 0.6–3 TCID50; Memoli 2015 **intranasal** — and Edison's two bundles disagree on it by 1–2 orders (α/β → 902 TCID50 vs a quoted 10⁴–10⁵) | ⊘ joint + unresolved citation | #44 |
| Route efficiency (aerosol vs intranasal) | absent | — | The ratio is a **measurable physical quantity spanning at least two orders**. Multiplier withdrawn pending Memoli's primary text; the order-of-magnitude conclusion stands | ⊘ field — needs #25 first | #25 |
| Emission | — | C | Yan 2017/2018 (EMIT): GM 3.8e4 copies/30 min fine aerosol, 1.2e4 coarse, culturable in 39% of fine. **Uncorrelated with NP swab load** — direct proof that a nasal-indexed curve cannot be an emission rate | ✓ once the shedding path takes a rate | #30 pattern |
| `surface_decay_per_day` | 0.94 | C | = 1.22 log10/day = **5.9 h half-life** (not the 0.47 / ~15 h stated). Slower than *both* Greatorex 2011 (1.5 h) and Bean 1982 (4.8 h) | ⊘ field — a constant fractional loss cannot carry an RH/matrix-dependent curve | #44 |
| Same key in Edison's *proposed* bundle (not in `data/`) | **4.8**, range [2.0, 16.0] | P | Schema max is 1 (`schemas/pathogen_profiles.schema.json`); the engine clamps with `min(1.0, decay)` (`engines/sim_clock.py`), so 4.8 would silently become *total* daily loss. The in-tree bundle value is 0.94 | **must not be loaded** | #44 |
| `airborne_half_life_hours` | 1.5 | C | Kormuth 2018: <0.5 log10 loss across 20–98% RH **in respiratory mucus** vs minutes in saline. Interval width is *matrix*, not RH | ✓ as an interval | |
| `base_susceptibility` | 0.65 | **F, and it is prior immunity** | Not a constant: a per-season, per-route seroprevalence/vaccination input. This is the one place a flu arm could quietly overfit | reclassify as a scenario input | |
| `surface_deposition_fraction` | 1e-3 | I | 10× the norovirus value, no stated reason. The bundle still uses the deprecated key name; the engine reads it through the alias | ∅ null; ⊘ field resolved in the active bundle only (#42) | #42 |

## 4. The seven blocked, and the change each needs

This is the actionable core of the register. In every case the paper exists and
the field cannot take it, so the next move is a model change, not a search.

1. **Norovirus dose-response and conditional illness** — provenance recovered
   (Teunis 2008) but tied to a GI.1 oral inoculum while the arm is GII by
   declaration, name and incubation. Either re-source both for GII or state
   plainly that a GI.1 dose axis is scored against GII.4 observations.
2. **Route efficiency, both active arms** — the naming and schema defect is
   resolved (they are declared independent per-route multipliers, not shares, and
   the six numbers were left exactly as shipped). What remains blocked is that
   they duplicate the object Edison's clearance layer parameterises, so the two
   are not separately identifiable: influenza supplies the measured version of the
   same quantity (per-portal efficiency, ≥2 orders) and it cannot be adopted into
   two parameterisations at once (#25).
3. **Influenza `illness_probability`** — the value is a population fraction and
   the field is a dose-conditional Hill form whose monotonicity Carrat's
   dose-independence rejects. Sourcing 0.67 into η would encode a dose effect the
   evidence denies (#44).
4. **Influenza and norovirus `surface_decay_per_day`** — a scalar fractional
   daily loss cannot express humidity-, matrix- and drying-dependent
   non-exponential survival. The norovirus interval is an order of magnitude wide
   *in rate* for this reason, and the influenza bundle's own value converts to a
   half-life slower than both its citations.
5. **SARS-CoV-2 emission × β** — not separately identifiable: dose and
   susceptibility enter the beta-frailty law strictly as a product. Must be
   adopted jointly against a copies-denominated measurement, with β swept over
   the Killingley-to-Zhang & Wang span (#30).
6. **The observation model's ~15 numbers** — jointly constrained by a single
   empirical aggregate which *is* anchor A3, so A3 cannot also be a test of them
   (#23, #27).
7. **The drying-state axis, which does not exist.** Finger↔surface transfer falls
   from 13% to 0.1% with ten minutes of drying — a factor-of-100 lever that no
   interval in the box represents, because the model has no wet/dry state. The
   largest single unrepresented uncertainty found in tranche 5.

## 5. Degrees of freedom, by provenance

Named quantities still free to move, after identifiability collapses some of
them:

| Arm | Free quantities | Notes |
|---|---|---|
| Norovirus | 6 route efficiency multipliers, cabin-localization `f`, `airborne_emission_fraction`, one reporting-probability scale | The reporting scale is the only one constrained by an anchor, and that anchor is A3. The former single dose knob is **measured inert** above release 8 — the fomite pool dominates so completely that a 14-log10 change is byte-identical |
| SARS-CoV-2 | 1 identifiable composite `(emission × route × transfer)/β`, 6 route efficiency multipliers, a 5-state severity vector, the testing-campaign replica, `airborne_emission_fraction` | The composite is *one* degree of freedom wearing four parameters' clothing. Fitting it while the background is unsourced would absorb their error, which is the failure the whole audit road exists to avoid |
| Influenza | `base_susceptibility` (prior immunity), plus everything in §3.3 | Not active. The susceptibility term must come from seroprevalence or vaccination coverage for the specific season and route, or the arm has a free knob on its most consequential input |

Two of these were *removed* by measurement rather than by sourcing, which is
worth recording as the register's own precedent: the norovirus dose knob (inert),
and `contact_transfer_fraction` (clears no noise floor anywhere across its whole
sourced interval — correct it, but do not prioritise it).

## 6. Rules this register is held to

Unchanged from `.agents/skills/model-parameter-provenance/SKILL.md`, restated
because this table is where they would first be broken:

- No value in this register may be selected because it improves a scored target.
  Intervals are literature spans, not favourable ends.
- A citation is not adoption. The Evidence column may be full while the State
  column says ⊘; that is the normal case, not an oversight.
- Genome persistence is not infectious-virus persistence, and an RNA-denominated
  pool decayed at an RNA rate preserves non-infectious material as dose. Both
  conversions must be stated wherever they are used.
- A source calibrated on a held-out target is barred, however attractive: Emery
  2020 and Tabata's Diamond Princess severity vector are both excluded on this
  ground.
- Recording a null (∅) is a result. Four quantities in §3 are known to be
  unmeasurable as specified; they are to be declared, not searched again.

## 7. Keeping it current

Update this register in the same change as any constant, interval, mechanism or
schema change that moves a row. When a tranche document and this register
disagree, the tranche holds the citation and this holds the status — fix the
status here. When the tree and this register disagree, the tree wins: correct the
register and say so in the change.
