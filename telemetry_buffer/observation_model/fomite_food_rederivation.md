# Re-deriving the fomite and food dose chain from measured quantities

Status: specification. No parameter here is chosen against the A5 passenger:crew
ratio, against any VSP attack-rate target, or against any other anchor. Every
number is either a published measurement, an arithmetic consequence of one, or
explicitly labelled as a declared modelling choice with its sensitivity stated.

## 0. Summary of what is wrong

Four separate defects, of which only the second was in the A5 diagnosis (§9d).

1. **The pickup denominator is the wrong surface.** Pool mass is divided by
   `zone_volume / DECK_HEIGHT_M`, the zone's *deck footprint* — 400 m² for a
   1000 m³ lounge. Norovirus does not lie on the carpet waiting to be touched;
   it is on handrails, door handles, buffet tongs, lift buttons and tap levers.
   The QMRA literature divides by the **fomite surface area**, which for the
   touched objects in a zone is order 1–10 m², not 400 m².

2. **The transfer chain is one lumped constant where the literature has three
   measured steps.** `FOMITE_TRANSFER_FRACTION = 0.01` and
   `FOMITE_PICKUP_PROBABILITY = 0.10` stand in for: how often a hand touches a
   shared surface, what fraction of the pool that touch lifts, and — entirely
   missing — how often and how efficiently a hand then reaches the mouth.

3. **There is no hand compartment.** Surface mass is credited directly as
   ingested dose. This is not merely an accounting simplification: the hand is
   where role structure lives. Hand hygiene, glove use, eating, and the
   duration a contaminated hand persists between washing all act on a
   reservoir the model does not have.

4. **The route discount is applied twice.** `_pathway_fomite` deposits
   `shedding × 1e-4`, and `_apply_route_weights` then multiplies the delivered
   dose by the fomite route weight 0.30. The 1e-4 and the 0.30 are doing the
   same job. Whatever the emission fraction should be, it should be applied
   once.

## 1. What `dose_adjustment` actually is

The shedding curve is `log10` copies **per gram of stool**: its peak of 11.0
is the standard reported norovirus stool concentration (10⁹–10¹¹ copies/g).
`get_pathogen_shedding` returns `10^(curve − dose_adjustment)` as an absolute
amount per epoch. Dimensional analysis therefore fixes the meaning of the
offset exactly:

```
10^(curve − adj) copies/epoch = (10^curve copies/g) × (10^−adj g/epoch)
```

`dose_adjustment` is `−log10` of **grams of stool released to the environment
per epoch**. It is not a calibration constant, an efficiency, or an abstract
scale. At the current default of 4.0 it asserts 0.1 mg of stool per shedder
per hour; the campaign ladder of 1.0–5.5 spans 100 mg down to 3 µg per hour.

This is worth stating plainly because it converts our one fitted parameter
from an uninterpretable number into a physical quantity that can be checked
against a measurement it was never fitted to — see §6.

The field should be renamed to say so. Renaming is behaviour-preserving and
does not rebaseline anything.

## 2. The measured transfer chain

These are the parameters standard fomite QMRA uses, and they are all
measurements rather than assumptions. The compact statement of the chain is
Wilson et al. (2021), eq. 2.4–2.7, whose Table 2 is the source of the
distributions below.

| Quantity | Value | Source | Grade |
|---|---|---|---|
| Total surface area, one hand | Uniform(445, 535) cm² | AuYeung et al. 2008 | B |
| Fraction of hand used per surface contact, `S_h` | Uniform(0.008, 0.25) | AuYeung et al. 2008 | B |
| Fraction of hand used per mouth contact, `S_m` | Uniform(0.008, 0.012) | AuYeung et al. 2008 | B |
| Surface→hand transfer efficiency | lognormal(µ=−2.1, σ=1.4) on [0,1]; median 0.12 | Julian et al. 2010 | B |
| Hand→surface transfer efficiency | same distribution | Julian et al. 2010 | B |
| Hand→mouth transfer efficiency | Normal(0.339, 0.132) on [0,1] | Rusin et al. 2002 | B |

The fraction of a surface pool that one touch removes is
`S_h × A_hand / A_fomite × TE_sh` — the same form the code already has, with
the deck footprint replaced by the touched-surface area and the lumped 0.01
replaced by a measured transfer efficiency.

Note that `S_m × A_hand ≈ 0.01 × 490 ≈ 4.9 cm²` is the mouth-contact area,
about 2.5× the existing `FOMITE_CONTACT_AREA_M2 = 2 cm²`, which is in the
right ballpark and was never the main error. The denominator was.

## 3. Contact frequencies

### Hand to mouth

Wilson et al. (2021), 199 adults observed 30 min each across airport, bar,
church, classroom, food court, museum, library and a sporting event —
public venues, which is the setting we need:

| Macro-activity | n | Mouth contacts/h, mean ± SD | Median |
|---|---:|---:|---:|
| Non-eating | 180 | 2.9 ± 2.5 | 2.0 |
| Eating | 19 | 7.7 ± 4.1 | 6.0 |

Grade B. This replaces the Nicas & Best (2008) ten-subject figure that most
QMRA still uses.

**The eating/non-eating split is the single most useful number in this
document, and it is not a knob.** Hand-to-mouth contact is 2.7× higher while
eating, and dining is precisely where the ship's role structure is expressed:
passengers eat in passenger dining rooms and at buffets, crew eat in the crew
mess, galley staff work in the galley. A dose pathway that is 2.7× stronger
during meals will express role structure that the current well-mixed aerosol
pathway cannot, and it will do so for a reason measured in 2001 by people who
had never heard of this model.

### Hand to surface

Weaker evidence, and it must be said so. Zhang, Li & Huang (2018) recorded
>120,000 touches over 60 h in a graduate-student office: about **5 touches per
minute per person**, but **98.8% of touched surfaces were private** (own
phone, own desk, own body). The shared-surface subset is small — though public
surfaces were touched by 68% of occupants, which is exactly the mixing
structure that matters. Oh et al. (2021), 30 Korean adults over 2 h, report
contact density highest for occasionally-shared items and lowest for public-use
items.

I take **shared-surface contacts = 6/h in public zones, 2/h in cabins**, i.e.
about 2% of total touches, and record it as **Grade C, declared**. It is the
one quantity here the literature does not hand us for a cruise ship, and it
goes into the sensitivity sweep rather than being asserted.

## 4. High-touch surface area per zone

Also Grade C and also declared. The QMRA studies use per-object areas (a door
handle, a desk) because they model one object; we need an aggregate per zone.
I take high-touch area as a function of zone type rather than of volume, since
handrails and tongs do not scale with the cubic metres of a lounge:

| Zone type | High-touch area | Basis |
|---|---:|---|
| Cabin | 1.5 m² | door handle, tap, flush lever, remote, rails |
| Dining / buffet | 8 m² | tongs, trays, rails, chair backs, tables |
| Public / lounge / corridor | 6 m² | rails, lift buttons, door plates |
| Galley / service | 10 m² | work surfaces, handles, utensils |
| Crew mess / berthing | 4 m² | shared, smaller footprint |

These are order-of-magnitude declarations, defensible to within a factor of
about 3, and they enter as a swept parameter. What matters is that they are
1–10 m² rather than the 400 m² the code currently uses: the defect being
fixed is two orders of magnitude, and the residual uncertainty is a factor
of 3.

## 5. The hand compartment

Each agent gains a per-pathogen hand load. Per epoch:

```
pickup   = N_touch · (S_h·A_hand / A_fomite) · TE_sh · pool
hand    += pickup                            (pool -= pickup)
dose     = N_mouth · S_m·A_hand · TE_hm · hand / A_hand
hand    -= dose
hand    *= exp(-k_hand · Δt)                 (inactivation on skin)
hand    *= (1 - hygiene_efficacy)            (on a hand-hygiene event)
```

Deposition runs the same chain in reverse: a shedder's hands carry faecal
contamination, and `TE_hs` moves it onto the shared surface. This replaces
`SURFACE_DEPOSITION_FRACTION = 1e-4` with a mechanism, and removes defect 4
by making the route weight the only place the fomite share is applied.

The hand pool is what makes role structure expressible, and it is the reason
this is worth doing properly rather than by rescaling a constant.

## 5a. Numeric closure of §5

Decay and hygiene, from the same Wilson et al. (2021) Table 2:

| Quantity | Value | Source | Grade |
|---|---|---|---|
| Inactivation on hands, `k_hand` | Uniform(0.61, 1.7) h⁻¹ | Wilson 2021 Tab. 2 | B |
| Inactivation on fomites | Uniform(0.0048, 0.013) h⁻¹ | Wilson 2021 Tab. 2 | B |
| Hand-hygiene efficacy | Normal(1.06, 0.54) log₁₀ reduction, on [0, 1.89] | Wilson 2021 Tab. 2 | B |

Two things follow that are worth noting rather than burying.

**Hands are a fast compartment and surfaces are a slow one.** `k_hand` gives a
half-life of 25–70 minutes, against 53–144 hours on a fomite. The hand is a
conveyor, not a reservoir; the surface is the reservoir. Any implementation
that treats them with a common decay constant is wrong by four orders of
magnitude.

**The existing surface decay is already right.** `norwalk_gi` carries
`surface_decay_per_day: 0.25`, i.e. 0.0104 h⁻¹, which sits in the middle of the
literature interval above. That constant was not part of the defect and should
not be touched.

### Shedder hand load

The spec's "reverse chain" needs a source term, and there is a direct
measurement of it. Liu et al. (2013) collected 159 hand rinses during a Norwalk
virus human challenge study — the same virus our dose-response is fitted to.
Hands of infected symptomatic subjects carried a mean of **3.86 log₁₀ genomic
copies per hand**. Kambhampati et al. separately found hand load correlated
with the host's own stool titre (r = 0.9 in 9 of 10 paired samples), which
licenses scaling that anchor by the host's own position on the shedding curve
rather than holding it fixed:

```
hand_target(host) = 10^3.86 · 10^(curve[t] − curve_peak) · host_shedding_multiplier
```

with `curve_peak = 11.0`. Replenishment is continuous toward that target, so
under the §5a decay the steady state is `R = hand_target · k_hand`. This avoids
inventing a toileting schedule to reproduce Liu's 25.4% sample positivity.

**Be explicit about what this costs.** Anchoring the hand compartment to a
measurement removes it from the fitted emission scale: `dose_adjustment` will
no longer govern the fomite route, only droplet, direct contact and HVAC. That
is a change in the structure of the fit, and it means fomite magnitude becomes
measured rather than fitted. I think that is strictly better — it is one fewer
thing the ladder can absorb — but it is a design decision, not a derivation,
and every dose figure quoted after this change means something different from
every dose figure quoted before it.

It also costs us Liu as an out-of-sample check, since a measurement used to set
a parameter cannot then test it. §6 is therefore rewritten around a different
measurement.

## 6. The out-of-sample check

Park et al. (2015, *Appl Environ Microbiol* 81:5987) swabbed surfaces on a
**cruise ship** during a passenger gastroenteritis outbreak, using macrofoam
swabs over areas up to 645–700 cm² at 1.2–36% recovery:

| Location | Norovirus GII, RNA copies per swab |
|---|---|
| Cabins of sick passengers | 80 – 31,217 |
| Public spaces | 16 – 113 |

17 of 92 samples positive. Correcting for recovery widens the true surface
loading to roughly 2×10² – 3×10⁶ copies per swabbed area, and the recovery
range alone is a factor of 30, so this check has about a 1.5 log₁₀ tolerance.

Two things make it the right check and not merely an available one. It is the
same setting, the same pathogen and the same physical quantity the corrected
`surface_pools` now represents; and nothing in the model has ever been fitted
to it, before or after this change.

It also carries a **structural** prediction, which is the part that can
genuinely fail: cabins of the sick run 100–300× hotter than public spaces. The
corrected model either reproduces that gradient or it does not, and the
gradient does not depend on the emission scale, the recovery fraction, or any
Grade C declaration in §3 or §4 — it depends only on whether contamination is
being concentrated where shedders spend their time. The current model, which
divides everything by a 400 m² deck footprint, cannot produce it.

**This check must be run and reported whatever it says.** It is the first
opportunity this model has had to be wrong about something it was not fitted
to, and a model that cannot fail a test is not being tested.

## 7. On role asymmetry, and what this does not license

Kambhampati et al. (PMC9007178) sampled hands during 12 norovirus outbreaks in
12 long-term care facilities: **11 of 15 residents** had norovirus-positive
hands, at 2.4–7.9 log₁₀ copies, against **2 of 15 healthcare workers** at 3.4
and 4.9. Hand load correlated with the subject's own stool titre.

The mechanism is hand hygiene and functional dependence, not role as such.
Mapping it to a ship requires the analogy that crew are a trained, supervised,
hygiene-enforced population and passengers are not — which is plausible, is
consistent with the post-COVID crew/passenger divergence Benjamin's data show,
and is nonetheless an analogy. A role-dependent hand-hygiene rate is therefore
a legitimate modelled mechanism with a real citation behind its direction, but
its *magnitude* on a cruise ship is not measured, and it must be swept, not
fitted.

Explicitly not claimed:

- that this reproduces the observed 2.9 passenger:crew ratio;
- that the fomite route will become dominant, or should;
- that any of these constants may later be tuned against 2.9. If the
  corrected chain gives 1.4, the answer is 1.4, and the remaining gap is a
  finding about the model rather than a licence to adjust §3 or §4.

The uniform `immune_ratio` across a resident crew and a weekly-turnover
passenger cohort remains a separate unexamined assumption, and is a more
likely home for part of the residual than anything in this document.

## 8. Sources

- AuYeung W, Canales RA, Leckie JO (2008). The fraction of total hand surface
  area involved in young children's outdoor hand-to-object contacts.
  *Environ Res* 108(3):294–299.
- Julian TR, Canales RA, Leckie JO, Boehm AB (2009/2010). A model of exposure
  to rotavirus from nondietary ingestion iterated by simulated intermittent
  contacts. *Risk Anal* 29(5):617–632.
- Liu P, Chien Y-W, Papafragkou E, Hsiao H-M, Jaykus L-A, Moe C (2013).
  Laboratory evidence of Norwalk virus contamination on the hands of infected
  individuals. *Appl Environ Microbiol* 79(24):7875–7881. PMC3837815.
- Kambhampati AK et al. High hand contamination rates during norovirus
  outbreaks in long-term care facilities. PMC9007178.
- Park GW et al. (2015). Evaluation of a new environmental sampling protocol
  for detection of human norovirus on inanimate surfaces. *Appl Environ
  Microbiol* 81(17):5987–5992.
- Oh HS, Ryu M, Yang Y (2021). Characteristics of hand-to-environment contact
  during indoor activities in daily life among Korean adults using a
  video-based observation method. *Osong Public Health Res Perspect*
  12(3):187–195.
- Rusin P, Maxwell S, Gerba C (2002). Comparative surface-to-hand and
  fingertip-to-lip transfer efficiency of gram-positive bacteria,
  gram-negative bacteria, and phage. *J Appl Microbiol* 93(4):585–592.
- Wilson AM, Verhougstraete MP, Beamer PI, King M-F, Reynolds KA, Gerba CP
  (2021). Frequency of hand-to-head, -mouth, -eyes, and -nose contacts for
  adults and children during eating and non-eating macro-activities.
  *J Expo Sci Environ Epidemiol* 31(1):34–44. PMC7362609.
- Wilson AM, Weir MH, Bloomfield SF, Scott EA, Reynolds KA (2021). Comparing
  approaches for modelling indirect contact transmission of infectious
  diseases. *J R Soc Interface* 18(182):20210281. PMC8437226.
- Zhang N, Li Y, Huang H (2018). Surface touch and its network growth in a
  graduate student office. *Indoor Air* 28(6):963–972.
