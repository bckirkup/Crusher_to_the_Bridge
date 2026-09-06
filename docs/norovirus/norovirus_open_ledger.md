# Norovirus fit: open ledger

> **Status:** Living

**Live status updated for R4.** What is currently withdrawn,
what each anchor last measured and *when*, and what is outstanding.

`docs/norovirus/norovirus_model_history.md` is the permanent record of defects and
corrections. This file is the volatile counterpart: it goes stale by design and
must be updated whenever a model change lands. If the head commit below is not
the current head, treat every number here as unverified.

Read this before quoting any dose figure or anchor result.

---

## 1. Currently withdrawn

**Every dose figure in this repository is void.**
`environmental_faecal_release_log10_g_per_epoch` (the old `dose_adjustment`,
still accepted as a legacy alias) was last fitted against a contact layer that no
longer exists: #351 rebuilt the fomite chain, #352 added emesis, and #353
raised the direct-contact kernel about 10x and the shared-surface touch rates
4-10x. A dose fitted before those is not transferable, and no refit has been
run since.

Also withdrawn and not yet replaced:

**Leisure-venue assignment and exterior-zone AHU membership changed.** The
`Free`-zone leisure draw is now capacity-weighted over passenger-accessible
venues instead of uniform over every `Free` zone, and exterior zones — open-air,
semi-open and open-aft decks — are no longer members of recirculating AHU
networks on any cruise platform. Both change zone occupancy and zone-to-zone
airborne coupling, so any attack-rate, route-share or dose measurement taken
before this commit is not transferable across it. No constant, grade or interval
changes here.

- **The v4 campaign** and every campaign before it. Each was invalidated by a
  defect found after it ran (§12 of the history).
- **The C1 reported-case bracket (2,880 runs, 2026-09-05).** Withdrawn as a
  bracket, not as runs. Its nine `dose_adjustment` rungs 12.0-14.0 produced
  bit-identical output at every seed across all 47 recorded outputs — resolved
  fraction 1/9 — so the ladder sat entirely inside the region where the
  environmental-release term has already gone to zero, and no dose interval,
  empty or non-empty, may be quoted from it. Measured in
  [`c1_reported_case_bracket_result.md`](c1_reported_case_bracket_result.md).
  Its syndromic arm is separately unscored: the runs recorded no sick-call
  hazard, and the scorer will not assume one.
- **Any host-level attack rate taken from a co-seeded bundle run, for any one
  pathogen.** Every agent-level infection and illness field is a projection
  across all of a host's lineages
  (`natural_history.project_legacy_illness`), and the summary counters, the
  reported-case ladder and the VSP threshold all read that projection, so a run
  of `active_profiles` — which seeds norovirus, influenza A and SARS-CoV-2 with
  one index case each — reports the union and attributes it to nothing. Measured
  at the Morris box centre over seeds 500-502: attack rate 0.4348 co-seeded
  against 0.0052 with norovirus alone, `vsp_posted` 1.0 against 0.0, peak epoch
  166 against 8. The influenza arm was activated at `f95677c` (2026-09-04),
  after the 2026-09-01 Morris pass, so the contamination is post-dated to that
  measurement rather than an explanation of it; it is nonetheless why the #36
  re-run isolates the screened pathogen (`--co-seeded isolated`, the default in
  `bounded_screen.py`). A composite run is a legitimate scenario, but it is a
  different scenario, and its ranking may not be compared with an isolated one.
- **The #36 Morris ranking (350 runs, 2026-09-05), as a statement about the
  current model.** Withdrawn on its initial condition, not on its arithmetic.
  Every one of its design points started from one fiat norovirus index case;
  #54/#440 landed the day after those runs and moved arrival into each
  pathogen's profile as a boarding prevalence draw (`norwalk_gi`: 3.25% of
  passengers, 1.85% of crew), which the initiation engine now owns outright.
  The regime is different, not merely re-plumbed: at the same box centre, same
  hull, agents, horizon and seed, the boarding arm reports a passenger
  infection attack rate of **0.0759 against ≈0.005** under one index case, and
  a peak at epoch 61 rather than 8. The screen's own §3 reading — that five of
  six factors sat below the floor because the isolated epidemic was near
  extinction — is exactly what a ~15× denser arrival changes, so the ranking
  may not be carried into #37 as a restriction on which factors it searches.
  The measurement stands as a measurement of the retired condition; a
  replacement pass needs its own floor, because the floor was taken under the
  same retired condition.
- **Every food-route dose and route share measured on the hourly grid before
  the pool fractions were unit-declared (Edison DIM-01).** `FOOD_INGESTION_FRACTION`
  0.05 and `ENV_DELIVERY_FRACTION` 0.01 were applied once per *epoch* with no
  clock conversion, so on the shipped 1 h grid a food pool was eaten down at
  24 days' worth of ingestion per day — about 14× the daily-grid delivery
  over 24 physical hours. They are now `FOOD_INGESTION_FRACTION_PER_DAY`
  (compounding, `decay_per_epoch`) and `ENV_DELIVERY_FRACTION_PER_DAY`
  (dividing, `amount_per_epoch`); the two deposition shares are shares of an
  already per-epoch emission and were not converted. No value changed. This
  sits under #37's empty region and the "every voyage posts" rate measured
  after it (food was 93-99.9% of delivered dose in the last route
  measurement), so neither may be read as a property of the model until
  re-run. Which of the six factors' magnitudes it moves is not yet measured.
- **Any claim that the model reproduces VSP attack rates.** Withdrawn at #346
  and not re-established. Expedition's earlier agreement was a cancellation of
  an inflated infection rate against a deflated illness ratio.
- **Route shares.** The often-quoted "droplet carries 94-96% of establishing
  dose" dates from the post-#338 measurement and remains withdrawn: it predates
  #351/#352/#353, all three of which change route magnitudes directly. The
  current measurement is
  [`route_weight_measurement_findings.md`](../../telemetry_buffer/observation_model/route_weight_measurement_findings.md),
  taken at `e8b2b95`, which finds droplet no longer dominant and reports mass
  share and establishment share as distinct objects. It adopts nothing and
  changes no constant.
- **The passenger/crew ratio.** Same reason.

**The removed-fraction non-secretor mechanism is withdrawn and replaced
(Wave 1, task #21).** `norwalk_gi` no longer carries
`innate_nonsusceptible_fraction`. It carries
`secretor_negative_fraction` 0.20 (FUT2 se428 nonsense-homozygote prevalence in
European/North American populations, Grade B) with
`secretor_negative_relative_susceptibility` 0.20 (Teunis 2020 GII rows,
0.015 / 0.076 = 0.197, Grade B), applied multiplicatively to the host's
susceptibility multiplier instead of assigning zero. The removed-equivalent
fraction this implies is 0.20 × (1 − 0.20) = **0.16**, the ceiling published in
#367, so the arm no longer asserts sterile immunity that Teunis 2020 and
Rouphael's 4-of-8 GII.2 challenge refute. `innate_nonsusceptible_fraction`
survives only as a deprecated alias (relative susceptibility 0.0) so the other
bundles in `data/pathogens/` keep their present behaviour. The history below is
retained because the sequence of reversals is the reason the mechanism changed.

**The mega-cruise campaign still runs the withdrawn mechanism.**
`picard_framework/runs/mega_cruise_campaign/campaign_runner.py:988` writes
`innate_nonsusceptible_fraction` into its per-run overrides, so every campaign
run rides the deprecated alias at relative susceptibility 0.0 — sterile immunity
— while `data/pathogens/active_profiles.json` runs partial susceptibility. The
behaviour is deliberately unchanged: the campaign sweeps the removed fraction,
and converting that swept axis into a relative susceptibility is a design
decision rather than a rename. Any campaign result must therefore be read as
having been produced under the withdrawn mechanism until that decision is
taken.

**The emesis titre × volume parameterisation is withdrawn and replaced by the
quantity Kirby identifies (Wave 2, task #38).** `EMESIS_TITRE_GEC_PER_ML` is no
longer an input: no profile key resolves to a titre, and the emesis record
carries titre only as a derived diagnostic (`episode_load / volume_ml`). The
emitted load now comes from `EMESIS_TOTAL_SHED_GEC_RANGE` = (1e5, 1e8) genome
copies, log-uniform, drawn **once per symptomatic illness** and partitioned
equally over the episodes drawn with it. Provenance: Kirby et al. 2016 Table 3,
per-subject **cumulative** emesis shed — GII.2 Snow Mountain 1.8e7 GEC
(SEM 1.8e7), GI.1 2.3e8, per-subject values spanning ≈1e5–1e8; Grade B on a
surrogate genotype, because no GII.4 emesis measurement exists (tranche 4 §3).
The endpoints are set by an arithmetic check and not by tuning: the arithmetic
mean of a log-uniform on [1e5, 1e8] is (1e8 − 1e5)/ln(1e3) = **1.45e7**, within
1.25× of the measured 1.8e7. The reason this is a reparameterisation rather than
a value swap is that the three former inputs are not independent — the measured
GII.2 titre mean 1.6e5 GEC/mL times the measured mean total volume 845 mL is
1.35e8, **7.5× above** the same paper's measured cumulative 1.8e7, because the
titre mean is taken over positive samples on a heavy right tail. Volume stays
drawn over 50–800 mL as the physical deposit volume only, and
`EMESIS_EPISODES_RANGE` is corrected to the measured (1, 7): with the total
identified, the episode count only partitions and times that same total.
**Every emesis-derived numeric expectation and every RNG-dependent emesis golden
is invalidated by this change**, since both the magnitude and the emesis draw
sequence move.

**Surface decay is now in the units it is sourced in, everywhere (Wave 2 task
#41, completed by R1/#59).** `surface_decay_log10_per_day` is the **only** key:
the deprecated fraction-valued alias `surface_decay_per_day` is deleted from the
engine, the schema and every profile, and a profile that still spells it that way
falls through to the default rather than being honoured. `norwalk_gi` carries
**0.124939 log10/day**. The conversion f = 1 − 10⁻ᵏ happens in exactly one
function, `transmission_core.surface_fraction_per_day`, instead of living in a
comment in `bounded_screen.py`. **No measurement recorded here is invalidated:**
0.124939 = −log10(1 − 0.25) reproduces the previous per-day fraction exactly, so
no shipped behaviour and no golden moved — this is a unit migration, not a
refit. The divergence #41 recorded is therefore closed rather than carried: the
sourced key is now the only key, and it is exercised by everything that runs.
The screen box is expressed unconverted, [0.067, 0.79] log10/day, and remains
adopted **for the screen box only** — the shipped 0.124939 is still an unsourced
value that happens to lie inside it near the slow end.

**Hand↔surface transfer is split by direction, and a drying axis is added at
neutral (Wave 2, task #42 item 3).** `SURFACE_TO_HAND_LOGNORMAL` keeps the pickup
direction; `HAND_TO_SURFACE_LOGNORMAL` — identical numbers — carries the deposit
direction, because they are two different measured quantities carrying very different
drying levers: ~100× on the deposit direction, where hand→surface falls
13% → 0.1% with 10 minutes of drying (Tuladhar 2013) and 59% → <1%
(Sharps 2012), against only ~5× on pickup, where surface→hand dries to
2–11% (Sharps) / 2.0 ± 2.0% on steel (Tuladhar). The shipped distribution is therefore a
**wet-contact** parameterisation, defensible against Tuladhar's and Bidawid's
immediate 13% and about 100× too high for a dried donor hand. The new
`hand_to_surface_drying_multiplier` multiplies the deposit side only, defaults to
1.0, is set by no profile and consumes no RNG, so it reproduces the shipped
arithmetic exactly; it is screened over [0.008, 1.0] (log10) because **which
drying state applies to a hand continuously recontaminated by its own shedding
is not measured**. That is why it enters as an axis and not as a value.

**The Morris ranking in
[`bounded_screen_results.md`](bounded_screen_results.md) is invalidated a second
time, and by this change.** The screen's seventh factor was
`innate_nonsusceptible_fraction` over [0.00, 0.16]; it is now
`secretor_negative_relative_susceptibility`, now over [0.04, 0.83] (widened in
tranche 6, below) — a different factor over a different interval, so every
elementary effect in that document is stale. The re-run on the recut `surface_decay_per_day` box was **killed part-way
and never completed**: only the 20-seed noise floor at the new box centre exists,
and there is no completed screen on either the recut box or the substituted
factor. Nothing may be ranked from that document until a screen is run on the
current box.

**That screen has now been run, isolated, and it is
[`bounded_screen_isolated_36.md`](bounded_screen_isolated_36.md) (#36,
2026-09-05).** 350 runs, 10 trajectories over the current six factors, 5 matched
seeds per point, `--co-seeded isolated`, against a 20-seed floor at the same
centre. It resolves **one** factor above that floor —
`environmental_faecal_release_log10_g_per_epoch`, monotone, ratio 1.6–2.0 on the
whole-ship and both passenger channels — and places the other five below it,
including every factor on the crew reported-case channel. `peak_epoch` carries no
ranking and `vsp_posted` cannot be thresholded from a centre that never posts. It
is a ranking and nothing else: no interval moves, no admissible region follows,
and #37 is a separate measurement. Two things it changes here: the resolved
factor is the box's only grade-D one, so the scored outputs are dominated over
this box by the quantity with the least right to its interval; and five
unresolved factors is a statement about the design, since at 450 agents with one
index case the isolated epidemic sits near extinction (centre attack rate ≈0.005)
and the seed budget, not the trajectory count, is what binds.

**The “≈3.7× GI-vs-GII infectivity per genome copy” comparison is withdrawn as a
unit error (tranche 6 §3).** It was published in tranche 3 and repeated when
Wave 3 was proposed. Reproducing Teunis et al. 2020's single-copy GII risk of
0.076 inside the shipped beta-Poisson family requires α = 2.85, which implies an
ID50 of ≈10 genome copies — five orders of magnitude below every challenge
measurement. Those fits model *aggregation* and report risk per aggregate, not
per disaggregated qPCR copy, so the two figures were never in the same unit and
no genogroup infectivity ratio can be read off them.

**The norovirus dose-response is no longer blocked by mechanism: it is declared
and swept (tranche 6 §2; register §3.1).** The shipped α = 0.111 / β = 32.81 is
the disaggregated GI.1 challenge arm of Teunis et al. 2008, and it is declared as
that rather than refitted. Mapped onto α at fixed β = 32.81, the human GII
evidence gives α ∈ [0.072, 0.161] — Rouphael 2022 GII.2 challenge ID50 5.1×10⁵
→ 0.072; Guix 2020 GII outbreak illness ID50 2,934 → 0.154, a lower bound on
infection α; Ramesh 2020 gnotobiotic-pig GII.4 → 0.149–0.161 as Grade C
corroboration — and 0.111 lies inside it, within 3% of its geometric centre
(0.108). No profile value changed, and β does not become an independent factor:
family, aggregation assumption and dose unit are one categorical choice (Liu et
al. 2026).

**#43's norovirus half is closed on the unit, and the ≈925 copies-per-aggregate
bridge is withdrawn (tranche 23).** The dose axis of the shipped row is
**administered genome copies (gEq/GEC)** — the unit both challenge inocula were
quantified in, and the unit in which Kirby, Teunis & Moe and Atmar's reply agree
that the two studies' no-aggregation models give similar estimates. On our side
the live per-agent confluent-hypergeometric beta-Poisson path has an N50 of
**16,644 copies** and the closed-form helper an approximate **16,871 copies**;
both give **P ≈ 0.047** at `D = 18`, so pairing "ID50 = 18" with this row stays
arithmetically impossible whatever unit the 18 is in.

The 925 figure was `16,643.78 / 18 = 924.65` — the N50 it was derived from — and
is **withdrawn as circular**. Its published replacement is **µ_c = 517**, the
aggregate-size parameter in Kirby's Figure 1 caption, which belongs to the
*pooled aggregation-corrected* fit (α = .024, β = .017) rather than to our
no-aggregation row — that row has no aggregation parameter, which is what "no
aggregation" means. **The ~100× aggregation fork is retracted, and the arithmetic
is why:** that pooled fit's exact N50 is 1.85 aggregates, and 1.85 × 517 = 954
copies, within 6% of Teunis's aggregated ID50 of 1,015 gEq. An aggregate-unit
axis re-expresses the same dose; it does not move it by two orders of magnitude.

What is **not** settled is Teunis's own wording, and it is contested in print
rather than merely unread: Kirby's letter reports the disaggregated HID50 as
**18.2 GEC, 95% CI 1.03–4,350 GEC**; Atmar's reply calls the 18 "genomic
equivalents ... determined using assumptions about differing amounts of virus
aggregation" and argues Teunis's own 0/9 at 324 gEq and 0/8 at 32.4 gEq make it
untenable; the collaborator bundle reads the Results sentence as 18 *single
virions* under a hypothetical fully disaggregated inoculum, and is cited as
**Sec** for that. Teunis 2008's body text and Table III are **?nr** — paywalled,
no body from Europe PMC, two chunk queries returned the abstract only — so the
row-structure claims rest on secondary analysis. Nothing above depends on the
wording. **#43 was still filed against a question our own review had already
posed**, and it is withdrawn rather than sent. Atmar's measured HID50 of
1,320–2,800 gEq remains an open **5.9–12.6×** gap below the live 16,644 under the
same no-aggregation framing, and **is now declared as a span on the dose axis**,
[1.32×10³, 1.69×10⁴] gEq, `logU`, **declared and not applied** so the #36 screen
and #37 admissible-region test expose it rather than absorb it. No dose figure
changed — every dose figure in this repository remains void pending refit.

**The proposal to close that 5.9–12.6× gap by retargeting α/β onto Atmar's
HID50 is rejected on genogroup, and the gap is reclassified as a
genogroup-declaration item rather than a residual error.** The narrative review
of the exchange adds three things the ledger did not have, and the third
disqualifies the refit. First, **Atmar 2014 fits a logistic model**, not a
beta-Poisson: its 1,320 gEq (secretor-positive blood group O/A) and 2,800 gEq
(all secretor-positive, blood group B/AB being wholly resistant in that study)
are logistic ID50s, with no infection observed below 324 gEq. Importing either
would change the dose-response *family* as well as its value, and β = 32.81
would keep no provenance at all once the Teunis fit it was lifted from is
abandoned — moving α while holding β is retaining half of a rejected fit.
**Corrected by tranche 23: the family is not what produces the gap.** Kirby's
Figure 1 caption reports an *exact beta-Poisson* refit of Atmar's own data with
no aggregation — the same family and assumption as our row — at α = .28,
β = .58, whose exact N50 recomputed in-repo is 4.16 dose units, ≈**1,660 gEq**
at Atmar's ≈400 gEq per RT-PCR unit (the caption does not state its unit; that
conversion is an inference, grade C). Family and value move together and the
~10× distance from 16,644 survives, so the refusal to retarget α/β rests on the
genogroup argument below and on the after-the-gate boundary, not on family.
Second, **the two figures are not interchangeable, and the tree picks 2,800**:
susceptibility here is gated on secretor status and **not** on ABO, so a
secretor-positive agent stands for Atmar's whole secretor-positive cohort across
blood groups, which is the 2,800 arm; the 1,320 arm conditions on O/A hosts this
model cannot separate, and adopting it without an ABO nonsusceptibility gate
would overstate susceptibility by exactly the resistant B/AB share. Third, and
decisively, **Atmar 2014 challenged GI.1 Norwalk while this arm is GII**: the
`norwalk_gi` id says GI, but the profile's name, its declared genotype mixture
GII.4/GII.17/GII.2 and its pooled-GII incubation row all say GII, and against
GII challenge evidence the shipped 16,644 is roughly **30× too sensitive**
(Rouphael 2022 GII.2 ID50 5.1e5), not 6–13× too insensitive. The two claims sit
on opposite sides of the shipped value and cannot both be about this arm, so the
6–13× figure is a GI-vs-GII comparison and not a demonstrated model error. What
this item now needs is the genogroup declaration, not a fit: declared GII, the
existing α ∈ [0.072, 0.161] interval stands and Atmar 2014 is out of scope;
declared GI.1, the target is 2,800 and α/β must be refitted **jointly** to
Atmar's data and graded as a logistic-to-beta-Poisson transfer. No value moved
and the withdrawal is unchanged.
[`proposals/pathogen_class_structure_decision.md`](../proposals/pathogen_class_structure_decision.md)
then settles how the ~2.6 logs of spread across these measurements is
*structured* — as GII.4-versus-non-GII.4 classes, with the shares declared from
external typing rather than fitted, since the VSP series carries no genotype in
any of its 428 postings — and adopts no dose value either.

**The exact and approximate dose-response forms are also an open implementation
item, not a repair in this change.** Production reaches
`_dose_response_hazard` at `engines/transmission_core.py:2082`, through the
persistent Beta draw in `_dose_response_susceptibility`; the closed helper
`_dose_response` at `engines/transmission_core.py:1649` is exercised only by
`tests/test_dose_pathway_invariants.py:473`. The tree therefore carries two
spellings of one mechanism — an exact per-agent frailty path in production and
an approximate population closed form covered by a test — matching the
duplicate-mechanism archetype in the provenance guidance. Neither function nor
the test is changed here.

**The secretor screen interval widens to [0.04, 0.83], which invalidates the
pending Morris design again (tranche 6 §4).** Kambhampati 2015's pooled
secretor:non-secretor odds ratios are genotype-specific — 9.9 (3.9–24.8) for
GII.4 and 2.2 (1.2–4.2) for GII non-4, implying non-secretor relative
susceptibility 0.10 (0.04–0.26) and 0.45 (0.24–0.83) — and the declared genotype
mixture GII.4/GII.17/GII.2 straddles both rows, so the width is genotype
composition rather than measurement error. The adopted 0.20 stays inside the
interval and is not refuted, and no profile value changed. The screen box moves,
so the screen re-run that was already outstanding is invalidated a further time;
task #36 carries it.

**`innate_nonsusceptible_fraction` (history): the sourced interval is 0.00 – 0.16, and
both the shipped 0.0 and Edison's 0.2 sit outside it.** This entry has been
rewritten twice; the sequence matters, because the second reversal was caused by
reading a paper more carefully than the profile.

- #367 withdrew the queued 0.0 → 0.2 correction, using the **GII** row of
  Teunis et al. 2020, *Epidemics* 32:100401 — Se+ 0.076 against Se− 0.015 per
  genomic copy, a ~5× reduction rather than an exclusion — corroborated by
  Rouphael et al. 2022 (*JID*, GII.2: 4 of 8 Se− ill at top dose) and Frenck et
  al. 2012 (*JID*, GII.4: 1 of 17 Se− ill against 13 of 23 Se+). Non-secretors
  are partially susceptible to GII, so a fully-removed fraction is the wrong
  mechanism and its ceiling is ≈0.16.
- #371 reversed that, on the grounds that the same paper's **GI** row is Se+
  0.28 against Se− **0.00007** (a factor of ~4,000), with Lindesmith et al.
  2003, *Nature Medicine* reporting the FUT2 null allele as fully penetrant in
  GI.1 challenge — no nonsecretor infected **at any dose**. That is correct for
  GI.1, and #371 asserted `norwalk_gi` is a GI.1 arm.
- **That assertion was false, and the profile says so.** `norwalk_gi` carries
  `name: "Norwalk Virus (Norovirus GII.4)"`; its `strain_evolution.genotypes`
  are `GII.4 / GII.17 / GII.2` at equal prior weight; and its incubation note
  states outright that the distribution is "GII rather than the GI the
  pathogen_id implies, because this profile's genotypes are GII.4/GII.17/GII.2."
  The arm simulates GII. **The GII interval therefore governs, #367's
  conclusion stands, and Edison's 0.2 is not defensible for this arm.**

**The chimera is real but runs the other way round.** What is mis-genogrouped is
the *dose-response*, not the susceptibility term: `alpha` 0.111 / `beta` 32.81
are inherited from `Person.java` and were, per
[`norovirus_model_history.md`](norovirus_model_history.md) §9c, fitted to
administered oral **Norwalk (GI.1)** inoculum — while name, genotypes,
incubation and validation targets are all GII. GI is 3.7× more infectious per
genome copy in Se+ hosts than GII (0.28 vs 0.076), so the arm is running a GI
infectivity curve against a GII strain set, and correcting it would move
infectivity and susceptibility in opposite directions, partially cancelling in
the aggregate attack rate. Prevalence is population-specific in any case (~20%
European-ancestry, 29% of the Lindesmith 2003 sample, 19% in the Rwandan cohort
of Munyemana et al. 2025), so a removed fraction — if the mechanism were right —
would remain an interval rather than a value. Evidence:
[`../literature/consensus_tranche_2.md`](../literature/consensus_tranche_2.md)
§1–§2 and
[`../literature/consensus_tranche_3.md`](../literature/consensus_tranche_3.md)
§1; derivation:
[`bounded_sensitivity_and_admissible_region_spec.md`](../proposals/bounded_sensitivity_and_admissible_region_spec.md)
§3.3. No profile JSON is changed by this entry.

**Withdrawn (2026-09-03): the claim that the chronic immunocompromised shedder
is the norovirus importation channel.** Stated in PR #383 and in the #45 notes.
The mechanism stands — a chronic host boards already shedding and never clears
on a 7–14 day voyage — but the prevalence was never computed. Tranche 10
computes it two ways, which disagree by 2.5 orders (1.4e-5 to 4.2e-3 of a
boarding population), and both ends sit one to three orders below the ordinary
asymptomatic adult channel at 2.5–4%. No chronic-shedder boarding point
prevalence is licensed; the importation channel is mostly immunocompetent.

## 2. Anchors

Targets, from `telemetry_buffer/observation_model/anchor_measurement_spec.md`:

| | quantity | target |
|---|---|---|
| A1 | ever-ill attack rate, passengers (Wikswo whole-ship cohort) | ~0.154 |
| A2 | ever-ill / infected | 0.68-0.81 (0.59-0.81 GII.4-weighted) |
| A3 | reported / ever-ill (infirmary capture) | 0.60 ± 0.05 |
| A4 | reported passenger attack rate | inside the hull-class IQR |
| A5 | passenger / crew reported attack rate | ~2.9-3.5 |

A5's two figures come from different sources and are both live: the anchor spec
says ~3.5 (7% vs 2%); the VSP 424-outbreak series gives ~2.9 (passenger
5.7-6.9% against crew 2.0-2.4%). Treat the target as a range, not a point.

**"Stable on both sides of the COVID break" was wrong, and is withdrawn.** It
was inferred from A5 rather than measured, and the per-outbreak series
contradicts it: across the break the median crew rate rises by 1.37x
(1.004-1.677, p=0.007) while the passenger median does not move detectably,
so the passenger/crew ratio falls by about a third (A7c = 0.668, 0.532-0.907).
A5 must therefore be quoted per era, not as one era-independent number, and any
fit that reproduces A5 pooled across both arms is reproducing an average of two
different ratios. Measured at `e167e32`; see A7 in
`telemetry_buffer/observation_model/anchor_measurement_spec.md`.

**Last measured values, and this is the part that matters: they are stale.**
All of the following were taken at `d557f39`, immediately after #346 and
*before* #348, #351, #352 and #353 landed. Every one of those changed
transmission. Do not quote these as current model behaviour; they are recorded
so the next measurement has something to compare against.

| | expedition | classic | measured at |
|---|---:|---:|---|
| infection attack rate | 0.407 | 0.465 | `d557f39`, 120 runs, dose 2.0 |
| ill / infected (A2) | 0.341 | 0.364 | `d557f39` |
| reported passenger AR (A4) | 3.48% | 3.89% | `d557f39` |
| A5, ever-ill ratio | 0.94-1.15 across hulls | | pre-#351 |
| A5, reported ratio | 0.85-0.97 across hulls | | pre-#351 |

Status at that measurement: **A4 failed on both hulls** (expedition below the
4.51% floor). **A2 missed by ~1.8x.** **A5 missed by ~3x, in a model that
returns roughly parity.** A1 and A3 were not jointly satisfiable with A2 under
homogeneous exposure — infection attack rate and ill/infected are welded to the
same dose, so they cannot be separated by refitting.

**The four hard-coded VSP class targets are withdrawn.** The triples
`score_anchors.py` carried (expedition 8.56%, 4.51-13.60%; classic 5.59%,
4.46-7.76%; spirit 5.64%, 4.44-7.90%; mega 5.61%, 3.40-7.45%) had no
derivation script and no source note, and do not reproduce from
`telemetry_buffer/observation_model/vsp_outbreak_series.csv` under capacity
bands or under any alternative band edge tried; the expedition class misses by
the widest margin. They are replaced by values recomputed from the series at
runtime, per hull class **and per era**, by
`telemetry_buffer/observation_model/vsp_class_era_scoring.py`, which
`score_anchors.py` now calls (`--vsp-era`, default `pre`). Derivation and
sources: `telemetry_buffer/observation_model/incidence_and_attack_rate_scoring_spec.md`.

VSP passenger attack-rate targets, for A4, as now derived (333 of 428 postings
carry a passenger denominator; the 87 `legacy_pre2004` rows carry none, and the
5 `shutdown` postings are never pooled into either arm):

Binned on **passenger** complements as of B3 (#29); the earlier cut of this
table binned passenger denominators against passenger-plus-crew totals and is
superseded:

| hull | era | n | q1 | median | q3 |
|---|---|---:|---:|---:|---:|
| expedition | pre | 21 | 4.00% | 5.32% | 10.45% |
| expedition | post | 12 | 3.22% | 7.42% | 13.74% |
| classic | pre | 95 | 4.15% | 5.52% | 7.82% |
| classic | post | 8 | — | — | — |
| spirit | pre | 130 | 4.18% | 5.26% | 7.24% |
| spirit | post | 43 | 3.72% | 4.95% | 6.95% |
| mega | pre | 16 | 3.55% | 6.00% | 7.49% |
| mega | post | 3 | — | — | — |

Against the floor of ten postings, the recut moves anchors in both directions:
**`mega_cruise_5000` gains a pre-2020 A4 anchor** (16 postings, where the
total-agent bins gave it four) and **`classic_cruise_1900` loses its post-2020
one** (8 postings, where they gave it 32). `score_anchors.py` reports a
withheld cell as `n/a (insufficient VSP postings)` rather than scoring it, so
no post-2020 classic result and no post-2020 mega result may be described as
passing or failing A4.

**A8/A9 are now implemented model-side, but the post-COVID arm has no
unconditional incidence observation at all.** The model-side channels are in
`telemetry_buffer/observation_model/score_anchors.py`; their MIDRS constants,
interval targets and fixed hull-to-GRT mapping are in
`telemetry_buffer/observation_model/midrs_incidence_targets.py`, sourced from
`telemetry_buffer/observation_model/midrs_observed_targets.md`. A8 aggregates
reported cases and travel-days over every run, including non-take-off runs. A9
applies the VSP 3% passenger-or-crew rule to eligible voyages and reports
ineligible runs separately. A truth-only arm emits an explicit no-reporting
sentinel rather than a false zero.

The only published MIDRS incidence analysis is MMWR Surveill Summ 2021;70(6),
covering 2006-2019; a search of CDC's VSP data pages, MMWR and the
peer-reviewed literature found nothing after it. So the post-2020
health-practice configuration changes exactly the channel we have no post-2020
observation for. A pre-arm A8 match plus a post-arm A4 match is the most that
can honestly be claimed until a post-2020 MIDRS analysis exists.

The MIDRS source record carries three conflicts that must remain attached to
the implementation. First, the MMWR Results prose labels 26.7 and 29.2 as
mega and super-mega **crew** rates, but Table 2 identifies those as passenger
rates; the crew values are 14.7 and 16.0, with the crew maximum 19.8 on
extra-large ships. Second, the reported "80.6% of the 252 ships were extra
large" is actually 30,039/37,258 voyage reports; the per-ship size distribution
is unpublished. Third, MMWR counts 156 investigated passenger outbreaks,
whereas `telemetry_buffer/observation_model/vsp_outbreak_series.csv` contains
208 posted outbreaks over the same period. A9 therefore reports an interval
spanning those definitions rather than silently mixing them.

**Resolved in B3 (#29): `HULL_CAPACITY` was a total-agent complement, not a
passenger complement.** The role split used by the model is authoritative in
`orchestrator_init.py::role_group_for_agent`: on the expedition reprobe
summary `..._dose12_..._s503`, `cumulative_ever_infected_passenger = 107` and
`infection_attack_rate_passenger = 0.338608`, giving
`round(107 / 0.338608) = 316`; the corresponding crew values are 40 and
0.298507, giving 134. Thus 316 passengers plus 134 crew equals the
`num_agents = 450` total. `HULL_CAPACITY["expedition_cruise_450"] = 450`
therefore denotes the total complement, not the passenger denominator.
`BAND_EDGES` in `telemetry_buffer/observation_model/vsp_class_era_scoring.py`
are geometric means of those total complements while binning observed
passenger counts (`pax_total`), so the A4 class bins inherited this offset.
**Repaired in B3 (#29):** each hull's `spatial_layout.json` now declares
`nominal_complement` as a passengers/crew split, `HULL_PASSENGER_CAPACITY`
reads the passenger half, and `BAND_EDGES` are geometric means of those
passenger complements (636 / 1,684 / 3,240). The A4 targets merged in #360 are
superseded by the recut table above. Still unrepaired: the hull-to-GRT
mapping behind A8/A9 picked representative ships for the classic and spirit
hulls against the same total-agent figures, so their GRT band is one band too
high pending two re-sourced representative ships. A8's passenger and crew denominators instead
come from the role-derived complements emitted in each run summary and do
not use `HULL_CAPACITY`, so A8/A9 are unaffected.

### The #37 feasibility gate: empty, and two of six anchors never became evidence

**Run, 2026-09-06:**
[`admissible_region_37.md`](admissible_region_37.md). 128 Sobol' points over the
full six-factor box, 5 matched seeds each, `mega_cruise_5000`, pre-2020,
norovirus isolated at the boarding channel. **0 of 128 points admissible**; the
best passes two of the five scoreable anchors, and every anchor pair passes
jointly zero times except A5+A4 (twice).

What binds, and this is what stops the result being read as structural
infeasibility:

- **A8 and A9 are unusable as currently mapped, not failed.** A4 is conditional
  on a posted outbreak and A8 is unconditional over all travel-days, on the same
  numerator: converted to A8's units at these runs' 5.19-day voyage, A4's target
  is 683-1,442 per 100,000 travel-days against A8's 16.9-29.2 — 23x apart, so no
  parameter value satisfies both in a cell of identically distributed voyages.
  A9's target likewise cannot be represented by 5 runs (it needs >=180 eligible
  voyages for one posting to land inside 0.00419-0.00558) and is reported
  design-limited rather than waived.
- **A1 against A2 is the one genuinely structural tension.** Both are inside the
  box's reach separately (8 and 2 passes) and never together: ill/infected is
  dose-dependent, so A2 reaches 0.59 only at an ever-ill attack rate of
  0.30-0.32, against A1's ceiling of 0.22; inside A1's band it tops out at 0.544,
  short of A2's floor by 1.08x. A5 sits the same way: over the 24 points where
  the ratio is in band, A1 never exceeds 0.073.
- **A1 against A4 binds in the observation model.** A4's reported band lies
  entirely below A1's ever-ill band, so both can hold only if reported/ever-ill
  is ~0.16-0.75 — roughly what A3 asserts. The shipped observation model's
  capture instead **rises with epidemic size and saturates at 1.0**, and A3 lands
  out of its 0.35-0.45 construction band at 123 of 128 points. That capture
  saturation is a defect of the observation model (§4.7), not grounds to widen
  either anchor.

No interval was widened, no endpoint selected, no anchor dropped and no constant
refitted after this gate ran. Unlike #36 this design is not near extinction: the
take-off fraction is 1.0 at all 128 points.

## 3. Out-of-sample checks

**Park et al. (2015)** — surface swabs during a shipboard outbreak; nothing was
ever fitted to it. Observed 80-31,217 copies/swab in sick passengers' cabins,
16-113 in public spaces, a gradient of roughly 100-300x.

| | #351 (hand chain) | #352 (+ emesis) | #353 (+ measured contact) | #355 (+ cleaning) |
|---|---:|---:|---:|---:|
| cabin, confined | 1,434 | 1,434 | 5,571 | 4,120 |
| public, 60 shedder-h/day | 356.9 | 356.9 | 384.9 | 368.0 |
| cabin/public gradient | 4.02x | 4.02x | 14.5x | 11.2x |
| shedder-hour asymmetry needed for 100x | 75x | 75x | 29.3x | 29.3x |

Levels sit inside the observed ranges across 1.5 orders of magnitude, from
independently sourced constants. The **gradient still fails**. A single emesis
episode reaches Park's level (1,047-31,400 copies/swab at Park's stated
recovery) but carries no intrinsic cabin/public gradient — the touchable-area
factor and the per-area concentration cancel exactly. The residual is *where*
people vomit, and reaching 100x needs 98.5-99.7% of episodes in the host's own
cabin. That fraction is unmeasured, is not a model parameter, and reading it off
Park's gradient would be fitting. Refused. Harness:
`telemetry_buffer/observation_model/park_surface_check.py`.

Routine cleaning (#355) moves the gradient the **wrong way**, from 14.5x to
11.2x, and the reason is instructive: a daily pass over 37% of objects competes
with continuous removal by hand pickup, so it multiplies the time-averaged pool
by 0.74 in a quiet cabin (loss 0.029/h) but only 0.96 in a busy public zone
(loss 0.33/h), where pickup already clears surfaces faster than housekeeping
can. Real ships clean cabins and public spaces on different schedules with
different products; the model does not, because nothing measured says how. The
gradient shortfall is therefore not a cleaning gap — it remains §4's sick-host
movement problem. Measured at the #355 head with
`ROUTINE_CLEANING_COVERAGE=0.37`, 1.29 log10/pass, one pass/day.

**The COVID discontinuity** is the better instrument, is now measured, and is
not yet scored. It is a *difference*, so errors common to both arms cancel —
which is what this effort needs, having spent its length finding errors that
cancel in levels. #355 supplies the NPI lever it needs (routine coverage and
per-event log10 are separately configurable, and outbreak response is a
distinct mechanism), but one schedule still applies to every zone class, so the
passenger-facing asymmetry cannot yet be expressed.

Two limits on the instrument, from
`telemetry_buffer/observation_model/post_covid_configuration_sources.md`. Every
A7 statistic is conditional on VSP posting, so an intervention that stops an
introduction from taking off is *invisible* to all of them — it prevents the
posting rather than shrinking it, and pre-boarding screening and denial of
boarding are exactly that kind. A7c is therefore a lower bound on NPI effect,
and a flat A7a is not evidence that NPIs did nothing. Second, the post-2020 arm
carries two changes with opposite signs: the NPI change, and a susceptibility
rise from two years of interrupted exposure (O'Reilly 2021, Lappe 2023, the
latter projecting >2-fold community incidence at full contact resumption).
Prior immunity must be set from those sources, or the NPI configuration
silently absorbs the immunity effect. Also note the industry's own hand-hygiene
push was alcohol-rub-centric, and alcohol rub is measurably weaker than soap
against norovirus (Tuladhar 2015), so it is expected to be near-null here.

The two caveats that blocked it are now handled by construction rather than by
correction, per `telemetry_buffer/observation_model/vsp_covid_discontinuity_design.md`: score only statistics
conditional on posting, so the missing voyage denominator never enters; and run
VSP's own posting rule over simulated voyages, so both arms are truncated
identically. The reporting-intensity confound is cancelled by taking the
passenger shift over the crew shift.

**The "~15-20% drop, p=0.032" figure is withdrawn.** It was read off
`docs/norovirus/vsp_covid_discontinuity.png`, whose per-outbreak table was never in the
repository. Rebuilt from CDC-hosted pages (`telemetry_buffer/observation_model/vsp_outbreak_series.csv`, 428
postings, `e167e32`), the passenger median moves 5.39% → 4.91%, a ratio of
0.912 (0.788-1.182, p=0.26) — no detectable level drop. The discontinuity is
real but it is not that: the crew median rises, the passenger/crew ratio falls
by a third (A7c = 0.668, p<0.001, and 0.736 with fleet composition held), and
what disappears from the passenger distribution is its upper tail — on ships
carrying 1000+ passengers, 11 of 226 pre-2020 postings exceeded 15% of
passengers ill and 0 of 48 post-2020 do, the maximum falling 25.2% → 13.5%.
About half the crew rise is composition, not behaviour: small expedition
vessels, several below VSP's own 100-passenger criterion, are posted post-2020.
Detecting an effect of this size needs hundreds of posted simulated voyages per
configuration; the design fixes 1,000.

## 4. Outstanding

Roughly in dependency order.

1. **Zone-differentiated cleaning schedules — swept, bounds sourced, no cell
   adopted.** #355 closed the "nothing cleans surfaces" gap — routine
   housekeeping is a discrete pass over the measured 37% of objects it reaches,
   and outbreak-response hypochlorite is a separate, stronger, SOP-triggered
   mechanism. A search found no measured cleaning-frequency schedule
   differentiated by zone class in an accommodation or passenger-vessel
   setting. The opt-in schedule is therefore swept inside the bounds documented
   in
   [`cleaning_schedule_sweep_spec.md`](../../telemetry_buffer/observation_model/cleaning_schedule_sweep_spec.md):
   cabin frequency 0.33–1.0/day, public 1.0–12.0/day, dining/galley/crew_mess
   1.0–6.0/day; cabin coverage 0.336–0.600, public 0.292–0.454, and
   dining/galley/crew_mess 0.292–0.600. No sweep cell may be adopted as a
   parameter value or default.

   Carling et al.'s Grade A 37% measurement is specifically from public
   restrooms on cruise ships, not cabins. Applying it to cabins is an
   unsourced extension, not evidence of a cabin schedule. The shipped model
   retains its uniform default; the schedule sweep exposes this uncertainty
   without fitting it to an anchor. Its hand-only gradient envelope is
   8.6635–18.5054x, against 11.1977x for the shipped default: that is a
   bound on schedule leverage (at most 1.6526x upward), not a test of Park
   reachability, because the hand-transfer channel was already shown
   unreachable at any occupancy. The Park comparison is instead made with
   the emesis-inclusive calculation, swept over the separate, unmeasured
   fraction of a host's emesis episodes occurring in its own cabin; at 0.99,
   78 of 81 schedule cells reach Park's 100–300x range, and at 1.00 all 81 do.
   That fraction is not a schedule parameter and no value is selected. It was
   spelled "cabin-localization fraction f" until #12 and is now
   `EMESIS_IN_OWN_CABIN_SWEEP`: it counts episode locations, not transmission
   events, so the register's `f ≤ 0.5`-scale ceiling never applied to it.
   Note that the premise has changed:
   crew rates did *not* hold still across the break, they rose (A7b), so a
   configuration that leaves the crew arm untouched now contradicts the data
   rather than matching it.
2. **Refit the common dose** against VSP class targets. The contact layer
   (#353) and cleaning (#355) are now in place, so this is next. One common
   dose-response across all four hull classes; no hull-specific pathogen
   biology, ever. The first attempt (C1, 2,880 runs) is withdrawn by §1: its
   ladder was degenerate, and a replacement must be sited where the axis
   resolves — checked with `picard_framework/analysis/sweep_degeneracy.py` on a
   short probe *before* submission — and must hold the surveillance response
   fixed while the dose moves, since the two arms differ 6-80x in infection
   attack rate at the same dose and seed.
3. **Re-measure route shares and the passenger/crew ratio** on the refitted
   model. Expect #353 to push A5 *further* from 2.9 — crew work the highest
   touch-rate zones and their berthing is already ~3x denser than passengers'.
   If it does, that is a finding about what is still missing.
4. **Score the v4-successor campaign** against VSP class targets, per era,
   and never on a withheld A4 cell (post-2020 classic, post-2020 mega).
5. **A8/A9 need a fleet-scale cell before they can score anything.** #37 showed
   the two anchors as mapped cannot be satisfied by a cell of replicate runs of
   one configuration at all: A4 is outbreak-conditional and A8 unconditional on
   the same numerator (23x apart in A8's units), and A9's target needs >=180
   eligible voyages to be attainable. Either the gate's cell becomes a fleet
   spanning outbreak and quiet voyages, or both anchors are withdrawn from the
   verdict until it does. Model-side aggregation and the sourced
   MIDRS target tables are implemented in
   `telemetry_buffer/observation_model/score_anchors.py` and
   `telemetry_buffer/observation_model/midrs_incidence_targets.py`. The
   post-arm observation remains unavailable, and A10 duration trajectories are
   still Proposed.
6. **The observation model's capture saturates at 1.0, and A3 says it should
   not.** Measured across #37's 128 points: reported/ever-ill rises with epidemic
   size and reaches 1.0 in exactly the region where A1 is in band, so A3 is out
   of its 0.35-0.45 construction band at 123 of 128 points and A4 inherits A1's
   value. This is the fifteen declared, unsourced observation numbers of B2/#27
   showing up as a scored consequence; it must be repaired in the observation
   model, and A4 re-read afterwards, before an A1/A4 incompatibility means
   anything about transmission.
7. **Cabin-level environmental compartments.** The finest mixing compartment is
   `Cabin_Corridor`: ~37 people in 800 m³ where reality is 2 people in ~40 m³
   (crew 3). `cabin_size` and `cabin_mate_ids` exist but only exempt a mate from
   confinement attenuation. Building this would raise crew rates — away from the
   anchor — so build it honestly and do not expect it to help. No cruise
   platform has four-berth cabins; crew are three.
8. **Aerosol portal efficiency.** #352 computes and records the emesis aerosol
   load but does not route it into the airborne reservoir. The direction is
   settled (norovirus establishes enterically; inhalation is delivery-to-gut via
   swallowing, so the respiratory clearance proxy is the wrong quantity) but the
   magnitude is not: the 10-30% figure is deposition in mouth/nose/trachea and
   is explicitly **not** an intestinal-delivery fraction.
9. **Sick-host movement and a bathroom destination.** The Park gradient needs
   it; see §3.
10. **AWS daughter session: CONTAM vs native accumulation comparison.** Deferred.
11. **Provenance queue, re-ordered by the bounded screen.** Measured in
    [`bounded_screen_results.md`](bounded_screen_results.md) §7.
    `innate_nonsusceptible_fraction` moves to the front on consequence: it is
    the top-ranked factor while carrying the mechanism §1 withdraws.
    `contact_transfer_fraction` drops down it — across its whole sourced
    interval it moves no scored output above the measured noise floor, so the
    shipped value is still wrong but it is not an exposure. **That screen row is
    withdrawn and the item is closed by retirement (#22):** the field stood in
    the same position of the same product as
    `route_efficiency_multipliers["direct_contact"]`, so the design ranged half
    of a product and its μ\* is not a sensitivity of contact transfer at all. The
    field is deleted from the engine, the schema and the box, and refused at
    load; the route keeps one owner
    ([`../literature/consensus_tranche_12_contact_transfer.md`](../literature/consensus_tranche_12_contact_transfer.md)
    §10). No other row in that screen is affected. Emesis titre
    becomes a first-order provenance target, which it was not before.
12. **`EMESIS_TITRE_GEC_PER_ML` = 3.9e4 is the wrong figure from the right
    paper, and its two companions are also off the measurement.** Traced in
    [`../literature/consensus_tranche_4.md`](../literature/consensus_tranche_4.md)
    §1c. 3.9 × 10⁴ is Kirby et al. 2016's **abstract** value for "GII viruses",
    which pools GII.2 Snow Mountain with a 2-subject GII.1 Hawaii pilot at
    5.0 × 10³ that the paper's own Results excludes from every genogroup
    comparison; Table 3 gives GII.2 as **1.6 × 10⁵ GEC/mL** and reports no
    significant GI/GII difference (p = 0.36 against the abstract's p = 0.02).
    For a GII.4/GII.17/GII.2 arm the applicable measured value is 4.1× what is
    shipped. Alongside it, `EMESIS_EPISODES_RANGE` = (1, 3) against a measured
    1–7 events (mode 1, 32% single), and per-episode volume 50–800 mL log-uniform
    implying ≈200–600 mL per subject against measured means of 658.7 mL (GI) and
    845.0 mL (GII.2). Compounded, the pathway sits about an order of magnitude
    below the measured per-subject cumulative shed — on the screen's
    second-ranked factor. Not repaired here: the measured object is a
    heavy-tailed distribution (Kirby's GI mean 8.0 × 10⁵ against Atmar 2008's
    median 4.1 × 10⁴ for the same genogroup, 20×), so the repair is a
    distribution plus a corrected episode count, not a swapped point value, and
    it must go through `model-parameter-provenance` with the goldens moved
    deliberately. **Repaired in Wave 2 as a reparameterisation, not a value
    swap** — see §1: the pathway is now driven by the measured per-subject
    cumulative shed, drawn log-uniform once per illness, with titre retired as
    an input and the episode count corrected to 1–7. Three inputs collapse to
    one, so the item is closed as a degrees-of-freedom reduction rather than as
    a re-valued titre.
13. **Resolved: the infectious period was incorrectly tied to illness duration,
    and two thirds of the authored shedding curve was never emitted.** Measured,
    not argued:
    `telemetry_buffer/observation_model/shedding_clock_check.py` drives the real
    progression seam. The tranche 7 baseline was a norovirus host reaching only
    curve indices
    **0–2 of the authored 15**, clearing on day 3–6 (median 4), with
    **30.9% symptomatic and 75.0% asymptomatic integral emitted** — equivalently,
    69.1% and 25.0% unreachable. After tranche 8, the host reaches indices
    **0–14**, clears on day 15–18 (median 16), and emits **100.0%** of both
    integrals. The COVID control is unchanged: indices **0–6**, last shedding
    day median **12** (range 8–22), and **99.8%** of both integrals.
    The repair separates `recovery_day` as illness duration from
    `shedding_duration_days` as infectious/shedding duration. Illness and its
    emesis records clear at onset + 3 days, while infection, hand load and
    faecal shedding remain active through onset + 15 days. Atmar 2008 measures
    both quantities in the same subjects: symptoms 1–2 days, faecal shedding
    median **28 days** (13–56); Kirby 2014 finds shedding up to three weeks past
    symptom resolution in both genogroups; Cheng 2021 sees GII shedding cease
    around day 15. The shipped value is **15**, screen interval **[12, 30]**,
    Grade B, not fitted to any scored anchor. The legacy
    no-per-pathogen-record path in `engines/infection_dynamics_bridge.py` still
    uses `ONSET_DAY + RECOVERY_DAY` as a one-clock fallback; that known
    limitation is unchanged. See
    [`../literature/consensus_tranche_7.md`](../literature/consensus_tranche_7.md).

14. **Resolved: immunocompromise acted on acquisition, the one quantity nothing
    measures, and not on duration, which is measured directly.** #45 deleted
    `immunocompromised_multiplier` = 2.0 from the tree — no source measures the
    relative risk of *acquiring* norovirus while immunocompromised, and Green
    2014 states the persistence mechanisms are unknown — and put the measured
    quantities where they were measured, as pathogen-profile keys on
    `norwalk_gi` only: `chronic_shedder_fraction` **0.228** (van Beek 2017,
    *Clin Microbiol Infect* 23(4):265 — 23 of 101 infected solid-organ
    recipients) and `chronic_shedding_duration_days` with median **218 days**,
    range **32–1,164** and a declared σ_log of **1.09**. The σ is a
    distributional assumption of ours, not van Beek's: treating the reported
    range as an approximate 90% interval, ln(1164/218) = 1.674 and
    ln(218/32) = 1.919, mean 1.797, ÷1.645 → 1.09. Davis 2020 confirms
    *infectious* virus (HIE) rather than RNA alone in 20 chronic paediatric
    cases (37 to >418 days), and van Beek 2017 (*J Infect Dis* 216(9):1132)
    supports at mean 352 days (76–716). The fraction is conditional on being
    both immunocompromised and infected; the duration is drawn once per host per
    profile at initialization on a derived RNG stream, truncated to
    [32, 1164], and preferred over the profile's `shedding_duration_days`
    through the infection record by the tranche 8 clearance seam, so a chronic
    host's illness still clears at onset + `recovery_day` while it keeps
    shedding past any voyage length. Deliberately **not** done here: no chronic
    *magnitude* multiplier (Chaimongkol 2024's 10⁴–10¹¹ copies/g is 7 logs wide
    and already spanned by the `shedding_variance_log10` per-host draw, with no
    point value to adopt), no severity multiplier (reported but unquantified),
    and no boarding-prevalence importation channel — that is the
    quantitatively interesting half, and no chronic-shedder point prevalence is
    licensed yet
    ([`../literature/consensus_tranche_7.md`](../literature/consensus_tranche_7.md)
    §6). **This move is downward on every arm**: 5% of hosts lose a 2×
    susceptibility multiplier, and the chronic duration only lengthens shedding
    in the small immunocompromised-and-infected subset.

## 5. Held fixed by assumption

Live Grade C liabilities. Any of these could move the reported rate; the system
is over-determined only *given* them. Full list in §10 of the history document.

- Route weights (contact 0.35, fomite 0.30, food 0.20, droplet 0.10, HVAC 0.05)
  — assumed, not traced to a source. **The largest single unsourced input.**
- `shedding_duration_days` = **15 days**, screened over **[12, 30]**, Grade B
  (Atmar 2008, Kirby 2014, Cheng 2021). The shipped value is a declared
  operational point, not fitted to a scored anchor; the field keeps the
  illness duration (`recovery_day`) separate from the infectious/shedding
  duration.
- `HIGH_TOUCH_AREA_M2` — per-room high-touch area in m² has never been measured
  by anybody. Permanent Grade C; the gap is the field's, not ours.
- Fraction of emesis episodes occurring in the host's own cabin — swept, never
  asserted.
- `EMESIS_AEROSOL_FRACTION_RANGE` (7.2e-7 – 2.67e-4, Tung-Thompson surrogate)
  **has now been checked** against a measured airborne concentration: Alsved et
  al. 2019, *CID* — 5–215 copies/m³ beside 26 hospital norovirus patients,
  positivity associated with vomiting in the previous 3 h. The check is
  `scripts/alsved_airborne_check.py` and it **decides nothing about the value**:
  the interval's ceiling reaches 5.0–6.7 copies/m³ in a 900–1200 m³ zone, at the
  measurement's floor, and the 6.4-decade interval constrains
  fraction × total shed ÷ volume jointly — inverting the comparison admits
  receiving volumes across five decades. So there is no over-emission to
  correct, and the fraction remains an interval with no point selected;
  choosing it to match the measurement would be fitting. See
  [`../literature/consensus_tranche_4.md`](../literature/consensus_tranche_4.md)
  §1d and
  [tranche 28](../literature/consensus_tranche_28_airborne_norovirus_out_of_sample.md).
- Confinement attenuation factor 0.05.
- `immunocompromised_fraction` = 0.05, defaulted in the multi-pathogen config
  block rather than in a profile, is now **bounded by measurement**:
  **[0.02, 0.074]**, Grade B (Lopez-Gigosos 2020's 2.0% of 1,196 travel-clinic
  travellers; NHIS 2.7% in 2013 rising to 7.4% in 2022), a width that is era and
  population rather than uncertainty. The shipped 0.05 is unchanged and lies
  inside the interval, the sources sit at the definition, and a value outside
  the interval draws an advisory sanity-checker warning. The companion key
  `immunocompromised_multiplier` = 2.0 is **withdrawn and deleted from the
  tree** (#45): a config still setting it is warned about rather than silently
  ignored, and the measured quantities enter as duration on the profile — see
  §4 item 13.
  Remaining Grade C liability: `chronic_shedding_duration_days.sigma_log` =
  1.09 is our declared lognormal shape over van Beek's measured median and
  range, not a measured dispersion. See
  [`../literature/consensus_tranche_7.md`](../literature/consensus_tranche_7.md)
  §4–§5.
- The **seeded index case's acquisition dose** is a construction constant, in
  two different values: the legacy engine path seeds `10^(9.0 − 4.0)` = 1e5
  from the symptomatic curve's day-1 entry, and the pathogen-aware boarding,
  mid-cruise and shore paths hard-code `1e4`. `acquired_particles` is the
  argument of `illness_probability`, so these numbers set the index case's
  probability of ever presenting — 0.643 and 0.555 at this profile's η/γ,
  against 0.577 at its own beta-Poisson N50 — and neither tracks
  `environmental_faecal_release_log10_g_per_epoch`, so under the campaign's
  dose sweep every transmission-acquired dose rescales and the index case's
  does not. Grade C, no source, no comment at the definition. See
  [`../proposals/initiation_engine_spec.md`](../proposals/initiation_engine_spec.md)
  §1 and §3, which replaces it with an explicit config value or with no dose
  at all. **Both values are now removed from the boarding and the seed
  paths**, which closes that liability where initiation owns the host: a
  boarded host carries dose 0.0 and an explicitly seeded one carries the dose
  its config states, or 0.0 when it states none, and whether the host presents
  is set by the boarding state axis or by the seed rather than by a
  construction dose read through `illness_probability`. The two constants
  survive only on the legacy paths a run without an `initiation` block still
  takes, which is every run shipped today.
- Secretor-status non-susceptibility. Not a held-fixed 20% ceiling: the profile
  the campaign runs ships 0.0, no attack-rate ceiling is observed (0.013–0.326
  across the override arms), and §1 withdraws 0.2 as the correction target. The
  live liability is that the mechanism is a removed fraction at all, where the
  evidence is partial susceptibility.
- `airborne_half_life_hours` = 1.1 is cited to van Doremalen et al. 2020, which
  measured **SARS-CoV-2**, and is the identical value carried by the COVID
  profile. A search for a norovirus airborne decay measurement returned a null
  result (see
  [`../literature/parameter_sourcing_bundle.md`](../literature/parameter_sourcing_bundle.md)
  §2.3), so this is a cross-pathogen borrow presented as a citation, not a
  sourced value. Treat as Grade C until it is declared or bounded by deposition
  physics.
- The shipped rate, **0.124939 log10/day** (spelled `surface_decay_per_day` =
  0.25 until R1 migrated it), has no source. It implies 0.125 log10/day,
  slower than the MNV-1-on-stainless-steel surrogate measurement (≥0.29
  log10/day, Leblanc et al. 2019), and the gap inflates the fomite reservoir.
  No human-norovirus dry-surface infectivity decay measurement exists; any
  adopted interval is Grade B at best and must state its medium.
- The decay interval is now carried in the units it is measured in,
  **[0.067, 0.79] log10/day** on `surface_decay_log10_per_day`, recut in
  `../literature/consensus_tranche_5.md` §1 from five surrogate studies; the
  earlier [0.14, 0.84] is the identical interval converted through
  f = 1 − 10⁻ᵏ (0.067 ↔ 0.143, 0.79 ↔ 0.838). It is an order of magnitude wide in rate, and the
  shipped 0.25 lies inside it near the slow end — Edison's proposed
  [0.49, 0.84] is the top of the literature, not its span, and the fast-end
  citation does not check against the paper it names. Every Morris result in
  `bounded_screen_results.md` was produced on the old [0.10, 0.60] box and
  must be re-run before the admissible-region search. The re-run was launched
  and then killed part-way; the factor substitution in §1 invalidates that
  document again, independently.
- The former `surface_deposition_fraction` / `airborne_emission_fraction`
  continuous-shedding definition is deleted from the active norovirus profiles:
  shedding is measured in copies/g of stool or vomitus while airborne virus is
  measured in copies/m³ of room air, never in the same subjects. Norovirus now
  declares `airborne_emission_mode = emesis_conditioned` and
  `emesis_aerosol_fraction_range = [7.2e-7, 2.67e-4]`; `TransmissionCore` draws
  log-uniformly per emesis event and drains that mass into the zone airborne
  reservoir once. Tung-Thompson 2015's table is in percent
  (7.2e-5%–2.67e-2%), so the declared fractions are the two-decades-smaller
  conversion. The deleted 1e-4 fell inside the interval only by coincidence
  across incompatible denominators, not corroboration.
- Uniform `immune_ratio` across a resident crew and a weekly-turnover passenger
  cohort — an assumption that bears directly on A5.
- Crew presenteeism and mandatory occupational reporting: absent in both
  directions.
- `OUTBREAK_CLEANING_COVERAGE` 0.58 — no shipboard measurement exists. Carried
  over from a 34%→53% supervision-and-feedback effect in two hospitals
  (Murphy 2011) applied to Carling's 37%. Sweep it; never assert it.
- Log10 additivity of the two-step outbreak procedure (detergent preclean then
  hypochlorite, 1.29 + 3.0 = 4.29). The field reports two-step efficacy that
  way; nobody measured the composition.
- Uniform routine cleaning remains the shipped default. One pass per day is the
  denominator of Carling's "cleaned on a daily basis", not a measured
  per-zone-class schedule. The optional per-zone-class schedule is swept inside
  sourced bounds; no sweep cell may be adopted as a parameter value.
- Newly deposited surface mass is split into cleaned and missed shares in
  proportion to coverage, i.e. shedders touch reached and missed objects alike.
  Untested; if soiling concentrates on the objects housekeeping skips, the
  missed reservoir is larger than modelled.

## 6. Maintaining this file

Update it in the same PR as any change that invalidates something here. The
failure mode this file exists to prevent is a future session reading a stale
dose figure from a doc and building on it in good faith — so a ledger that is
quietly out of date is worse than no ledger. Date-stamp every measurement with
the commit it was taken at.
