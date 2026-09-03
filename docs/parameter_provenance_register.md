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
| [`literature/`](literature/) tranches 1–7 and the Edison reviews | The evidence behind the Evidence column. Contextual: this register is the index into them, and where the two disagree, the tranche document holds the citation and this one holds the status |
| `formal_spec_v2.md` Appendix A | Superseded as a provenance record. Its source column was the baseline this register was built against |

## 1. Two axes, because one was hiding half the problem

Provenance class alone was the wrong instrument. Six quantities in §3 have a
citation and *still cannot be adopted*, because the field they would go into
cannot express what the paper measured. The count was seven after tranche 7
measured two quantities the model could not express: norovirus shedding
duration, which had no field at all, and the shedding curve's peak magnitude,
which is mis-genogrouped and not separately identifiable. Tranche 8 removes
the first blocker: `shedding_duration_days` exists, the shedding clock is
separate from the illness clock, and the measured interval is adopted at 15
days (#46). Classifying the remaining blocked quantities as "sourced" would be
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
| Quantities that had no usable literature basis and now have one recorded | **28** |
| — of those, adoptable as they stand | 10 |
| — blocked by a field or mechanism defect (⊘) | **6** |
| — adopted in the tree | **2** (the FUT2 pair, Wave 1) |
| — provenance recovered but mis-genogrouped | **1** (η/γ; the dose-response pair left this row in tranche 6, declared as the GI.1 arm and swept over the GII interval it lies inside) |
| — refuted, or shown to be unmeasurable (∅) | 5 |
| Profile scalars carrying a citation **in the tree** | still 8 / 6 / 2 |

The last row is the honest headline, and it has moved once. Wave 1 adopted the
FUT2 pair — `secretor_negative_fraction` 0.20 with
`secretor_negative_relative_susceptibility` 0.20 — by replacing the mechanism
that blocked them, and resolved the naming defect on the two renamed fields
(`route_efficiency_multipliers`, `airborne_emission_fraction`) without sourcing
either. Wave 2 then adopted the identified emesis total and moved surface decay
into its sourced unit, and the other in-tree changes from the sourcing campaign
remain three screening intervals (`surface_decay_log10_per_day`, the recut
interval in sourced units, [0.067, 0.79]; `hand_to_surface_drying_multiplier`,
[0.008, 1.0] at a neutral shipped value;
`secretor_negative_relative_susceptibility`, [0.05, 0.50] → [0.04, 0.83],
tranche 6). The remaining gap
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
| `dose_response.alpha` / `beta` | 0.111 / 32.81 | I → **M (form and value)** | The shipped pair is the **disaggregated GI.1 challenge arm** of Teunis 2008, traced by Edison's bundle. Mapped onto α at fixed β = 32.81, the human GII evidence gives **α ∈ [0.072, 0.161]**: Rouphael 2022 GII.2 challenge ID50 5.1e5 → 0.072; Guix 2020 GII outbreak illness ID50 2,934 → 0.154, a *lower* bound on infection α; Ramesh 2020 gnotobiotic-pig GII.4 → 0.149–0.161, Grade C corroboration ([tranche 6](literature/consensus_tranche_6.md) §2) | ✓ **declared and swept** — 0.111 lies inside that interval and within 3% of its geometric centre (0.108), so it is declared as the GI.1 arm rather than refitted; α is queued into the screen box over [0.072, 0.161] with β held fixed, because family + aggregation assumption + dose unit are one categorical choice. **No profile value changes** | #21 note |
| `illness_probability.eta` / `gamma` | 0.508 / 0.095 | I → **M** | Teunis 2008, same table. The genogroup contrast **cannot be quantified** for this pair either: Teunis 2020's per-copy genogroup figures are aggregate-unit, not disaggregated qPCR-copy ([tranche 6](literature/consensus_tranche_6.md) §3), and Guix's illness ID50 bounds the infection∘illness composite, not η/γ alone | ⊘ mech — same genogroup mismatch, and no GII-specific η/γ measurement exists to replace it | |
| `secretor_negative_fraction` | 0.20 | B | FUT2 se428 nonsense-homozygote prevalence, European/North American populations ~20% (population genetics, not this setting) | ✓ **adopted** (#21) — demographic input, deliberately outside the screen box | #21 done |
| `secretor_negative_relative_susceptibility` | 0.20 | B | **Genotype-specific**: Kambhampati 2015 pooled secretor:non-secretor odds ratios 9.9 (3.9–24.8) for GII.4 and 2.2 (1.2–4.2) for GII non-4, implying non-secretor relative susceptibility **0.10 (0.04–0.26)** and **0.45 (0.24–0.83)**; the declared genotype mixture GII.4/GII.17/GII.2 straddles both rows ([tranche 6](literature/consensus_tranche_6.md) §4) | ✓ **adopted** (#21); screened over **[0.04, 0.83]**, widened from [0.05, 0.50] — the width is **genotype composition**, not measurement error, and the adopted 0.20 sits inside it and is not refuted. Implies a removed-equivalent fraction of 0.20 × 0.80 = **0.16**, the #367 ceiling | #21 done |
| `innate_nonsusceptible_fraction` | withdrawn from `norwalk_gi`; deprecated alias | — | The removed-fraction mechanism is refuted for GII and is no longer the norovirus mechanism. Alias retained (rr = 0.0) so the other bundles in `data/pathogens/` keep loading | — superseded | #21 done |
| **Divergence: campaign vs shipped profile** | campaigns write `innate_nonsusceptible_fraction` | — | `picard_framework/runs/mega_cruise_campaign/campaign_runner.py:988` still writes `innate_nonsusceptible_fraction` into its per-run overrides, so **every campaign run models sterile immunity in a removed fraction** while `data/pathogens/active_profiles.json` models FUT2 partial susceptibility. Behaviour deliberately left unchanged: the campaign *sweeps* the removed fraction, and converting the swept axis to a relative susceptibility is a design decision, not a rename | recorded, unresolved | |
| `shedding_variance_log10` | 1.0 | C | Teunis 2014, 102 subjects, peaks 10⁵–10⁹/g | ✓ | |
| `recovery_day` | 3 | I → **M as an illness duration** | Atmar 2008 measures both in the same 16 subjects: symptomatic illness **1–2 days**, faecal RT-PCR shedding **median 28 days** (13–56). Two independent sources on illness duration (tranche 3 §5) put 3 days inside the illness range | ✓ **implemented as an illness duration only.** The second job moved to `shedding_duration_days` in tranche 8: `illness_clearance_day = onset_day + recovery_day` now ends the *illness* (and the emesis schedule with it), while the infection and its shedding run to the shedding clock. The value is unchanged | #46 done |
| `shedding_duration_days` | **15** | **B** as an interval | Cheng 2021 (77 children, GII): rise days 2–9, decline after day 9, most shedding ceased by **day 15**. Atmar 2008 (GI.1 challenge): median **28 days** (13–56). Kirby 2014 (GI.1 and GII.2 challenge, stools to day 35): both genogroups shed **up to 3 weeks past symptom resolution**. Shipped value **15**, the authored curve's own length and Cheng's cessation day; interval **[12, 30]** ([tranche 7](literature/consensus_tranche_7.md) §3, §6). Not fitted to any scored anchor | ✓ **implemented** (tranche 8). The field is optional and absent means the shedding period equals `recovery_day`, so the COVID arm is unchanged; the norovirus host now reaches all 15 authored curve indices and emits **100.0%** of both authored integrals, against 30.9% symptomatic / 75.0% asymptomatic before. Unblocks #45 | #46 done |
| Curve selection by *current* illness status | symptomatic vs asymptomatic curve re-chosen every epoch | — | — | ✓ **defect, fixed in tranche 8.** Once illness can clear while shedding continues, selecting the curve from `illness == SYMPTOMATIC` silently moved a convalescent host onto the *asymptomatic* curve mid-course. All three selection sites (`get_pathogen_shedding`, `get_pathogen_hand_target`, `strain_shedding_shares`) now select on whether the host ever presented, so the tail read is the tail of the curve the host started on | #46 done |
| `shedding_curve_log10` peak magnitude | 11.0 log10 copies/g | I → **M, and mis-genogrouped** | 11.0 is Atmar 2008's GI.1 median peak (95×10⁹ = 10^10.98) to two decimals. Kirby 2014 measures GII.2 titres ≈**2 logs below** GI.1 in the same challenge design ([tranche 7](literature/consensus_tranche_7.md) §3) | ⊘ **joint** — unlike the dose axis, this discrepancy is directional and large, but emission scale and dose-response enter as a **product** (#366), so a −2 log emission correction cannot be adopted alone. Declared, not applied | #47 |
| `immunocompromised_fraction` (config) | 0.05 | **A → B as an era-aware interval** | Harpaz 2016 (NHIS, 2.7% of US adults, 2013), Martinson 2024 (6.6% in 2021, 7.4% in 2022), Lopez-Gigosos 2020 (24 of 1,196 travel-clinic travellers, **2.0%**) → **[0.02, 0.074]**; the width is population and era, not uncertainty ([tranche 7](literature/consensus_tranche_7.md) §5) | ✓ adoptable as an era-aware interval, not a point. Not yet adopted | #45 |
| `immunocompromised_multiplier` (config) | 2.0 | **F → ∅ refuted as a quantity** | No source measures the relative risk of *acquiring* norovirus while immunocompromised; Green 2014 states the persistence mechanisms are unknown. What is measured is duration and infectiousness: van Beek 2017 (2,182 SOT recipients, 4.6% infected, 22.8% chronic, median **218 days**, 32–1,164), Davis 2020 (20 chronic paediatric cases 37 to >418 days, **infectious** virus shed continuously, HIE-confirmed), Chaimongkol 2024 (chronic shedding **10⁴–10¹¹** copies/g) | ∅ **withdrawn on the record** — an assumption sitting on the one quantity the literature does not measure. Wave 1 made it bite harder by composing multiplicatively instead of overwriting. Tranche 8 supplies the shedding-duration field, so #45 is now unblocked to move the evidence onto duration; the 7-log magnitude is a swept axis, never a point | #45 |
| `surface_decay_log10_per_day` | key added, **no profile sets it**; the active profiles still ship the deprecated `surface_decay_per_day` = 0.25 | C → **B in sourced units** | Five surrogate studies → **[0.067, 0.79] log10/day**, Grade B, which is the unit every source measures in; the former [0.14, 0.84] was that same interval converted through f = 1 − 10⁻ᵏ. Shipped 0.25 fractional ↔ −log10(0.75) = **0.125 log10/day**, which lies **inside [0.067, 0.79] near its slow end** (tranche 5 §1) | ✓ interval **adopted in the screen box in sourced units** (#41); conversion now happens in exactly one place, `TransmissionCore._surface_survival`. **Divergence recorded:** shipped profiles ride the deprecated alias, so behaviour is bit-identical and the sourced key is unexercised until a profile adopts it | #41 done |
| `airborne_emission_fraction` | 1e-4 (renamed from `surface_deposition_fraction`, value unchanged) | **C** unsourced-assumed | No study reports emission to a room reservoir as a fraction of shedding. The field feeds the **airborne** zone reservoir, which is now what it is called; the surface pools are fed by the emesis and faecal-release paths | — not blocked: the ⊘ field defect is **resolved** (#42) and nothing about the field now prevents adoption; it simply has no source | #42 done |
| `airborne_half_life_hours` | 1.1 | **I, cross-pathogen** | No measurement of airborne norovirus decay exists. The value is van Doremalen's SARS-CoV-2 figure | ∅ null — declare or bound by deposition physics | #39 |
| `route_efficiency_multipliers` (6) | 0.35/0.1/0.05/0.3/0.2/0.0 (renamed from `transmission_route_weights`, values unchanged) | C | None. Independent per-route multipliers, not shares — the schema now says so | ⊘ **joint** — the field defect is resolved (#25); these multipliers are not separately identifiable from Edison's pre-establishment clearance layer, which parameterises the same object, so no per-route efficiency can be adopted into one of the two alone | #25 |
| `environmental_faecal_release_log10_g_per_epoch` | 4.0 (`dose_adjustment`) | F → **measured inert** | Ge 2023 measures *total shed genome copies*, which retires the key rather than sourcing it | ⊘ field | #38 |
| `emesis_total_shed_gec_range` (engine) | (1e5, 1e8), log-uniform, drawn **once per symptomatic illness** | **B**, surrogate genotype | Kirby 2016 Table 3, per-subject **cumulative** emesis shed: GII.2 Snow Mountain 1.8e7 GEC (SEM 1.8e7), GI.1 2.3e8, per-subject values spanning ≈1e5–1e8. No GII.4 emesis measurement exists (tranche 4 §3). The interval reproduces the measurement rather than being fitted: the arithmetic mean of a log-uniform on [1e5, 1e8] is (1e8 − 1e5)/ln(1e3) = **1.45e7**, within 1.25× of the measured 1.8e7 | ✓ **adopted** (#38); screened over [3.6e7, 3.1e8] on the high endpoint (GII.2 mean + 1 SEM → largest per-subject cumulative mean in the paper) | #38 done |
| **Degrees-of-freedom reduction (emesis)** | three inputs → **one** | — | The former titre × volume × episode-count parameterisation carried **three** free inputs for a quantity the source identifies **once**, and it was not merely mis-valued: the measured GII.2 titre mean (1.6e5 GEC/mL) times the measured mean total volume (845 mL) is 1.35e8, **7.5× above** the same paper's measured per-subject cumulative 1.8e7, because the titre mean is taken over positive samples on a heavy right tail. Setting all three independently therefore overstated emission by an order of magnitude *while looking like provenance on each*. Adopting the cumulative total removes two degrees of freedom outright | ✓ recorded and implemented | #38 done |
| Emesis titre (engine) | **withdrawn and deleted**; 3.9e4 no longer appears in the engine, and the withdrawn figure is recorded here and in the ledger | B, **from the abstract** | Kirby 2016 Table 3: GII.2 = 1.6e5. The abstract pools a 2-subject GII.1 pilot the Results exclude. No profile key resolves to a titre any more; the emesis record carries titre as a **derived** diagnostic (`episode_load / volume_ml`), so the abstract-versus-Results defect cannot return through a config | — superseded by the cumulative total | #38 done |
| Emesis volume (engine) | 50–800 mL/episode, still drawn | B | Tung-Thompson 2015, Booth & Frost 2019. It no longer multiplies a titre: with the total identified, volume is only the physical deposit volume, used for the deposition record and any concentration-based check | ✓ role narrowed | #38 done |
| Emesis episode count (engine) | **1–7** (was 1–3) | **B**, measured | Kirby Tables 2–3: 1–7 events per subject, mode 1. With the total identified, the count only **partitions and times** that same total; it no longer scales emission, which is what makes correcting the range safe | ✓ **adopted** (#38) | #38 done |
| `contact_transfer_fraction` (engine) | **1.0, by omission** — neither active profile sets it | C | The ~0.25 contact-model anchor is recorded in `norovirus/norovirus_model_history.md` §10 and is itself thinly sourced. Contact is now sampled at POLYMOD rates and transferred at unit efficiency. **Measured to clear no noise floor anywhere** in the screen | ✓ low priority | #22 |
| `SURFACE_TO_HAND_LOGNORMAL` (engine) | median 0.122 | B | Corroborated: close to measured **wet** finger↔steel transfer (Bidawid 13%, Tuladhar 13%, Dallner 9.2%). Pickup direction only; drying is a weak lever here (2–11% Sharps 2012; 2.0 ± 2.0% off steel, Tuladhar 2013) | — in tree, corroborated | |
| `HAND_TO_SURFACE_LOGNORMAL` (engine) | median 0.122, **identical numbers**, split out by direction | B | Deposit direction, a different measured quantity. Defensible as a **wet-contact** parameterisation against Tuladhar's immediate 13% and Bidawid's 13% | — in tree, corroborated for wet contact only | #42 |
| `hand_to_surface_drying_multiplier` | key added, **1.0 (neutral) by default, no profile sets it** | **B** as an interval | The drying lever is ~100× on the deposit direction and only ~5× on pickup: hand→surface falls 13% → 0.1% after 10 min drying (Tuladhar 2013) and 59% → <1% (Sharps 2012). Interval **[0.008, 1.0]**, log10 — 0.008 is Tuladhar's dried/immediate ratio (0.1%/13% = 0.0077), 1.0 is fully wet | ✓ interval **adopted in the screen box**; the value is *not* adopted, because **which drying state applies to a hand continuously recontaminated by its own shedding is not measured**. It enters as a swept axis, at neutral, changing no shipped arithmetic | #42 |
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

## 4. The six blocked, and the change each needs

This is the actionable core of the register. In every case the paper exists and
the field cannot take it, so the next move is a model change, not a search.

Two items left this list in Wave 2 and are recorded in their §3.1 rows instead.
The norovirus half of the surface-decay defect is resolved: the field is now
`surface_decay_log10_per_day`, the unit every source measures in, and the
conversion happens in one place (#41 done) — the influenza half survives as item
3 below. And the drying-state axis **now exists**, as
`hand_to_surface_drying_multiplier` over [0.008, 1.0], shipping neutral and
swept; what remains there is that no value is adopted, which is a missing source
rather than a missing mechanism (#42).

Norovirus dose-response left this list in tranche 6: the shipped α/β is declared
as the disaggregated GI.1 arm and swept over the human GII interval it lies
inside (§3.1), so no model change is owed. Its conditional-illness partner η/γ
remains blocked, and its blocker is now carried in its §3.1 row rather than as an
item here, because the genogroup contrast cannot be quantified for it at all.

1. **Route efficiency, both active arms** — the naming and schema defect is
   resolved (they are declared independent per-route multipliers, not shares, and
   the six numbers were left exactly as shipped). What remains blocked is that
   they duplicate the object Edison's clearance layer parameterises, so the two
   are not separately identifiable: influenza supplies the measured version of the
   same quantity (per-portal efficiency, ≥2 orders) and it cannot be adopted into
   two parameterisations at once (#25).
2. **Influenza `illness_probability`** — the value is a population fraction and
   the field is a dose-conditional Hill form whose monotonicity Carrat's
   dose-independence rejects. Sourcing 0.67 into η would encode a dose effect the
   evidence denies (#44).
3. **Influenza `surface_decay_per_day`** — the influenza bundle still carries a
   scalar fractional daily loss, which cannot express humidity-, matrix- and
   drying-dependent non-exponential survival, and its own value converts to a
   half-life slower than both its citations. The norovirus half of this item is
   resolved (see above); influenza has to move to the same sourced unit before
   any of the bundle is loaded (#44).
4. **SARS-CoV-2 emission × β** — not separately identifiable: dose and
   susceptibility enter the beta-frailty law strictly as a product. Must be
   adopted jointly against a copies-denominated measurement, with β swept over
   the Killingley-to-Zhang & Wang span (#30).
5. **The observation model's ~15 numbers** — jointly constrained by a single
   empirical aggregate which *is* anchor A3, so A3 cannot also be a test of them
   (#23, #27).
6. **Norovirus shedding-curve peak magnitude** — 11.0 log10 copies/g is Atmar's
   GI.1 median peak to two decimals, and Kirby measures GII.2 about two logs
   below GI.1 in the same challenge design. Unlike the dose axis, where the GII
   interval contained the shipped GI.1 value, this discrepancy is directional and
   large — and it is the same blocker as item 4 in a different arm: emission
   scale and dose-response enter as a product, so a −2 log emission correction
   applied alone would be absorbed into a quantity we have not identified.
   Declared, not applied, and it has to be adopted jointly with the dose axis if
   at all (#47).

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
