# Review — Edison's SARS-CoV-2 and influenza sourcing bundles

**Status:** Received and reviewed. **Nothing adopted.** No profile constant, no
engine constant changed by this review.
**Received:** `covid_parameter_sourcing_bundle.md`,
`influenza_parameter_sourcing_bundle.md` (both dated 2026-09-02, canonical SHA
a684d1c6).
**Companions:** [`../covid/covid_parameter_provenance_audit.md`](../covid/covid_parameter_provenance_audit.md)
(PR #366), [`edison_norovirus_influenza_bundle_review.md`](edison_norovirus_influenza_bundle_review.md),
[`consensus_tranche_5.md`](consensus_tranche_5.md).

Read the COVID bundle first: it contains the single most useful thing either
party has produced on that arm. Then read §3, because the influenza bundle
contradicts Edison's own earlier influenza bundle on the two values that decide
whether the arm can be loaded at all.

---

## 1. COVID: the bundle supplies the anchor #366 said was missing

#366's finding was structural: in the establishment law the dose and the
susceptibility scale enter only as a product, so Diamond Princess can pin
`(emission × route × transfer)/β` and nothing decomposes it. Fixing β from an
independent source **in the same units as the emission term** is the only way to
make the emission scale a measured quantity rather than a free composite. The
bundle supplies exactly that, from human data:

**Killingley et al. 2022 (*Nat Med*), human challenge:** 10 TCID50 intranasal →
18/36 infected (53 %). Under an exponential law that solves to k = 0.0755 per
TCID50 and **ID50 ≈ 9.2 TCID50** — checked, and consistent with the bundle's
"~10". This is a *human* SARS-CoV-2 dose-response, which is what the shipped
α = 0.18 / β = 58 has never had.

**Watanabe attribution withdrawn, independently.** #366 found that `formal_spec_v2`
and `pathogen_notes.md` disagree about whether the shipped α/β has a source at
all, and that the cited paper is a SARS-CoV-1 adaptation. The bundle goes
further and states the specific reason it cannot be the source: Watanabe 2010
fitted **murine** SARS-CoV-1 data to an **exponential** model (k = 4.1 × 10²
PFU) and explicitly reported that beta-Poisson gave no significant improvement,
so a beta-Poisson α/β pair cannot have come from it. Two parties reaching the
withdrawal by different routes is the strongest provenance result on this arm so
far.

### Arithmetic checked

- Shipped N50: `58 × (2^(1/0.18) − 1)` = **2 671** model units. Matches the
  bundle's 2 670. (Our establishment law is beta-frailty — `1 − ₁F₁(α; α+β; −D)`
  — not the classic approximation; at these parameters the two agree to within
  1.4 %, so the N50 comparison holds. See [`edison_v3_spec_review.md`](edison_v3_spec_review.md).)
- Zhang & Wang k = 6.4 × 10⁴ – 9.8 × 10⁵ RNA copies → ID50 = k·ln 2 =
  4.4 × 10⁴ – 6.8 × 10⁵ copies, i.e. **17–254× less sensitive** than shipped.
  Matches the bundle.
- One slip: the bundle converts Killingley's 10 TCID50 to "10³–10⁵ RNA copies"
  using a stated 10²–10³ copies/TCID50 factor. That product is 10³–10⁴, not
  10³–10⁵.

### The finding the bundle does not draw

Its two dose anchors disagree with each other, and the disagreement is the
interval. Killingley (human challenge, corrected) gives ID50 ≈ 10³–10⁴ copies;
Zhang & Wang (fitted to epidemiological data) gives 4.4 × 10⁴–6.8 × 10⁵. The
shipped 2 671 sits just *below* the challenge range and 1–2 orders below the
epidemiological one. So the honest statement for #30 is not "adopt Killingley",
it is: **β's sourced interval spans ~10³ to ~7 × 10⁵ copies, set by the
disagreement between a challenge study and an epidemiological fit, and the
emission term must be re-derived against Lane 2023 / Coleman 2021 with β swept
across that whole span.** Adopting either endpoint alone would hand back as a
"source" the very freedom #366 identified.

### Accepted as correcting us, with one caveat

- `asymptomatic_shedding_log10`'s 1.5 log10 offset is **not supported** —
  measured URT loads are similar between symptomatic and asymptomatic
  individuals in the first week. Ours, unsourced, and the bundle is right.
- `shedding_variance_log10 = 1.2` against Schijven's between-individual SD of
  1.3–1.7 log10: inside-adjacent, "slightly low but defensible" is fair.
- Severity: three candidate vectors with *different denominators* (Wu's 1 %
  asymptomatic is a testing artefact; Buitrago-García's 31 % is screened;
  Tabata's 51 % is Diamond Princess). The bundle picks the screened denominator,
  which is right. **Caveat: the Diamond Princess row is barred as a source**, on
  the same ground tranche 3 barred Emery 2020 — it is our training set, and
  taking a severity vector from it would train the observation model on the
  target it is scored against. Keep it as the check.

### Rejected as stated

`illness_probability` η = 0.4 / γ = 0.12 "produce ~57 % illness at the profile's
N50". The field is `P(ill) = 1 − (1 + η·dose)^(−γ)`; at dose = 2 671 that is
1 − (1 + 1 068)^(−0.12) = **0.56**, so the number checks — but it is a
dose-conditional value at one dose, not an asymptomatic fraction, and it cannot
be compared to Buitrago-García's population proportion without integrating over
the realised dose distribution. The bundle's own framing ("within the
screened-cohort range") invites exactly that comparison. Grade C stands.

---

## 2. Influenza: the bundle is good evidence attached to two wrong conversions

Accepted, and useful:

- **Carrat et al. 2008:** symptomatic fraction pooled **66.9 % (95 % CI
  58.3–74.5)**, and **dose-independent** (p = 0.12) within the challenge range;
  33 % asymptomatic; fever ~3 d, total symptoms 5–7 d. This is Grade A human
  challenge synthesis and it is what the arm's clinical block should be built on.
- **Yan et al. 2018 (EMIT):** GM 3.8 × 10⁴ RNA copies per 30 min in fine
  aerosol, and no correlation with nasal swab load. Consistent with what we
  recorded in #374; it remains the measurement the COVID arm lacks.
- **Kormuth 2018:** <0.5 log10 airborne loss across 20–98 % RH **in respiratory
  mucus**, against minutes-scale half-lives in saline. If the arm is activated,
  `airborne_half_life_hours` must be entered as an interval whose width is
  *matrix*, not RH.

### Correction 1 — `surface_decay_per_day = 0.94` is not a 15 h half-life

The bundle states 0.94 "implies ~0.47 log10/day → half-life ~15 h". A per-day
fractional loss of 0.94 leaves 0.06, i.e. **1.22 log10/day**, a **5.9 h
half-life**. 0.47 log10/day would be f = 0.66.

The conclusion changes with the arithmetic. At 5.9 h the shipped value is
**slower** than *both* cited measurements (Greatorex 1.5 h; Bean ~4.8 h), not
"between" them — so it is defensible against Bean and 4× slow against
Greatorex, which is a different statement from the one the bundle makes. Same
class of error as the norovirus surface-decay conversion in
[`consensus_tranche_5.md`](consensus_tranche_5.md) §1: the log10-rate ↔
fractional-loss conversion is where this field keeps going wrong, in both
directions and for both parties.

### Correction 2 — Edison's two influenza bundles disagree, and the machine-readable one is the invalid one

| Quantity | `influenza_parameters_bundle.json` (reviewed in #374) | `influenza_parameter_sourcing_bundle.md` (this review) |
|---|---|---|
| `surface_decay_per_day` | **4.8**, noted as "~4.8 log10/day", range [2.0, 16.0] | shipped **0.94**, "defensible as a fleetwide mean" |
| Memoli 2015 intranasal ID50 | α = 0.407, β = 201 → **902 TCID50** (our arithmetic on their parameters) | "**~10⁴–10⁵ TCID50**" |
| Aerosol vs intranasal ratio | not stated | "~100-fold" |

The first row is the load-bearing one: a JSON formatted for loading carries 4.8
into a field the engine clamps at 1.0 (`decay = min(1.0, decay)`), which silently
means *total* daily loss of the surface reservoir. The prose bundle, two weeks
later, reports the shipped 0.94 as defensible and never mentions the 4.8. Task
#44 stands unchanged and is now better motivated: **the JSON must not be loaded
as shipped.**

The second row propagates into a claim I made to the record and must correct.
In #374 I reported that Memoli's fit "solves to an ID50 of 902 TCID50 against
Alford's aerosol 0.6–3, so the aerosol portal is 300–1 500× more efficient". The
902 is arithmetically right *for the α/β Edison supplied* — `201 × (2^(1/0.407)
− 1) = 902.3`, checked again here — but this bundle attributes 10⁴–10⁵ TCID50 to
the same study, which is 1–2 orders higher and would make the ratio 3 × 10³ to
1.7 × 10⁵. The bundle's own "~100-fold" summary is inconsistent with both. So:

- **Withdrawn:** the specific figure "300–1 500× more efficient per TCID50".
- **Stands:** the qualitative result, which is what the route-weight argument
  rested on — per-portal infection efficiency differs by **at least two and
  possibly five orders of magnitude**, so route discrimination is a measurable
  physical quantity and cannot be a set of shares summing to one (task #25).
- **Needs the primary text**, not a bundle: Memoli 2015's reported ID50 and its
  units. The same lesson as tranche 4's Kirby/Ge episode — two summaries of one
  paper disagreed and only the Results settled it.

### Correction 3 — one row is wrong about our tree, and the field it names has a mechanism problem

The bundle lists influenza `illness_probability` as "inherited from norovirus?".
It is not: the shipped profile carries η = 0.67, γ = 0.1, where norovirus carries
0.508 / 0.095. The 0.67 evidently reflects Carrat's 66.9 % — which is the
problem, in two ways:

1. **η is not a probability.** `P(ill) = 1 − (1 + η·dose)^(−γ)`. At influenza's
   own N50 (exponential k = 0.18 → ln 2/k = 3.85 model units) that is
   1 − (1 + 2.58)^(−0.1) = **0.12**, not 0.67. Putting a symptomatic *fraction*
   into η does not produce that fraction.
2. **The form contradicts the source.** Carrat's central finding is that illness
   given infection is **dose-independent** in influenza (p = 0.12), unlike
   norovirus. A monotone-increasing dose-conditional Hill function is therefore
   the wrong mechanism for this arm, not a mis-set parameter. Sourcing 0.67 into
   η would look like provenance and encode a dose effect the evidence rejects.

This is the third instance of the same failure mode in this bundle pair — a real
measurement mapped onto a field whose semantics differ — after the two surface
conversions above and Grove→`contact_transfer_fraction` in #374.

---

## 3. What this review changes

Nothing in the tree. Tasks:

1. **#30 gains its anchor and its interval:** re-derive the SARS-CoV-2 emission
   term against Lane 2023 / Coleman 2021 with β swept over 10³–7 × 10⁵ copies,
   the span between Killingley and Zhang & Wang — not fixed at either.
2. **#31 gains a barred source:** the Diamond Princess severity vector (Tabata)
   is the check, not the input; use the screened-cohort denominator.
3. **#31 also gains a correction:** drop the 1.5 log10 asymptomatic shedding
   offset when that block is rebuilt; measured URT loads do not support it.
4. **#44 is confirmed and narrowed:** Edison's influenza JSON must not be loaded
   as shipped (`surface_decay_per_day: 4.8` clamps to total loss). The shipped
   0.94 is a 5.9 h half-life, defensible against Bean and 4× slow against
   Greatorex.
5. **New:** the influenza `illness_probability` mechanism must become
   dose-independent before the arm is activated, per Carrat. Sourcing the value
   without changing the form would be worse than leaving it blank.
6. **New:** obtain Memoli et al. 2015's reported ID50 and units from the primary
   text; two Edison bundles disagree by 1–2 orders on the same study, and the
   figure I published in #374 depends on which is right.
7. **Withdrawn from the record:** "aerosol portal 300–1 500× more efficient per
   TCID50" (#374). The order-of-magnitude conclusion survives; the multiplier
   does not.
