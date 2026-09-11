# Tranche 39 — nobody weighs the faeces on a hand, and the indicator arithmetic that stands in for it puts the shipped convention at the bottom of its band

**Register rows fed / supersession.** Feeds the open ledger's §4 item 22(f) —
the hand route's implicit release bridge — and the register row for
`HAND_LOAD_LOG10_GEC` / `HAND_LOAD_REFERENCE_PEAK_LOG10`
(`engines/infection_dynamics_bridge.py`). It **supersedes nothing**,
**withdraws no measurement**, **moves no constant and adopts none**. Nothing
here narrows the hand bridge, and no value below may be read into the engine
without its own design and approval.

**Status:** Evidence assembled and interpreted. Nothing implemented.

**Scope.** The quantity item 22(d) left open: *what mass of faecal material is
on a contaminated hand?* The engine answers it implicitly. It pins a shedding
host's hand at Liu 2013's **3.86 log10 genome equivalents per hand** and
rescales it by `curve[idx] − 11.0`, so a peak-shedding host's hand carries
`10^(3.86 − 11.0)` = **10⁻⁷·¹⁴ g of stool-equivalent**, a Class X convention
that the constant's own comment declares and that no study has measured.

**Result in one line.** The direct quantity is a **∅ null** — no study weighs
faecal material on a hand, and no study measures stool titre and hand load in
the same subject (tranche 26's nulls stand). What exists is an **indicator
bridge**: faecal-indicator counts per hand divided by indicator counts per
gram of stool. Composed over the retrieved sources it puts a *routine*
contaminated hand at roughly **10⁻⁶·⁹ to 10⁻⁴·¹ g of stool per hand** in
heavily contaminated household settings — so the shipped 10⁻⁷·¹⁴ sits **at or
just below the bottom edge** of a band derived with no reference to any anchor.
The direction matters for what item 22 may be read to claim, and is stated in
§5 with the reasons it is a bound and not a replacement.

---

## 1. E0 triage — what could settle this, and in what units

| Candidate route | Unit it would deliver | Commensurable with the engine? |
|---|---|---|
| Gravimetric faecal residue on hands | g/hand | Directly — this is the bridge |
| Norovirus genome copies per hand in an infected host | gc/hand | Directly — this is what Liu measures |
| Faecal indicator (E. coli) per hand ÷ indicator per gram stool | g-equivalent/hand | Only through two surrogate conversions (§4) |
| Transfer-efficiency studies (surface↔hand, hand↔food) | dimensionless fraction | No — they move a load, they do not set one |
| Hand-hygiene efficacy | log10 reduction | No — removal, not deposition |

The last two rows were already closed as non-answers in tranche 26 and are not
re-queried here.

## 2. The direct quantity — ∅ null, and the closest published thing is a model

No retrieval returned a gravimetric measurement of faecal material on a hand.
The closest published quantity is **derived**, not measured:

| Study | What it reports | Setting | Origin | Grade |
|---|---|---|---|---|
| Mattioli et al. 2015, *Environ Sci Technol*, [10.1021/es505555f](https://doi.org/10.1021/es505555f) | Monte-Carlo **mass of faeces ingested per day**: **0.93 mg/day** by hand-to-mouth vs **0.098 mg/day** from stored drinking water | Children <5, Bagamoyo, Tanzania; hand-rinse and stored-water indicator data from >1,200 households | Sec (read from Cantrell 2022's Introduction; the indicator→mass conversion factor the model used is `?nr`) | C for this repo |

It is the right *class* of quantity — indicator counts converted to a mass of
stool — and it is the precedent for §4's arithmetic. It is not usable as the
engine's hand load: it is an integrated daily ingested dose over many contacts
by a small child, not a load per hand, and its conversion factor was not
retrieved.

## 3. The two halves of the indicator bridge, as retrieved

**Numerator — faecal indicator per hand.**

| Study | Quantity, as reported | Setting | Origin |
|---|---|---|---|
| Mattioli et al. 2015, *Am J Trop Med Hyg*, [10.4269/ajtmh.14-0778](https://doi.org/10.4269/ajtmh.14-0778) | E. coli **2.2 (SD 1.0)** and **2.1 (SD 1.0) log10 CFU per two hands** (rainy / dry); enterococci 2.6 | Mothers, Bagamoyo, Tanzania; 63% seated immediately before sampling | R (Results table) |
| Wang et al. 2017, *Am J Trop Med Hyg*, [10.4269/ajtmh.16-0408](https://doi.org/10.4269/ajtmh.16-0408) | Hand-rinse E. coli **2.25 to 1.55 × 10⁵ CFU per pair of hands**, N = 287 | Children <5, Accra, Ghana (SaniPath) | R (Discussion, "result not shown") |
| Deblais et al. 2025, *Front Public Health*, [10.3389/fpubh.2024.1484808](https://doi.org/10.3389/fpubh.2024.1484808) | E. coli **> 2 log10 CFU per pair of hands**, detected in > 53% of hand rinses | Infants, siblings, mothers; rural eastern Ethiopia (EXCAM) | R |
| Cantrell et al. 2022, *ACS Environ Au*, [10.1101/2022.07.11.22277510](https://doi.org/10.1101/2022.07.11.22277510) | Mean E. coli **prevalence** on hands 40% overall; **49%** in low/lower-middle-income, **6% [1–12%]** in upper-middle/high-income countries. Hand **rinsing recovers more** than swabs or imprints | 80 studies, 31,305 observations | R |
| Oie et al. 2021 (tranche recorded earlier) | **39,499 ± 77,768 CFU per glove** after defecation without a bidet; **4,147 ± 11,427** with | 32 nursing students, Japan; outer glove of a double-gloved hand | Ab |

**Denominator — indicator per gram of stool.**

| Study | Quantity, as reported | Setting | Origin |
|---|---|---|---|
| McOrist et al. 2005, *Can J Microbiol*, [10.1139/w05-021](https://doi.org/10.1139/w05-021) | Total E. coli **undetectable to 8.75 log10 CFU/g faeces**, 41 healthy adults, 4 samples over 12 weeks | Healthy adults, Australia | Ab |
| Islam et al. 2019, *Front Microbiol*, [10.3389/fmicb.2019.00640](https://doi.org/10.3389/fmicb.2019.00640) | Total E. coli **6.86 ± 1.56 log10 CFU/g wet stool** (n = 100), MacConkey drop-plate | Healthy infants, rural Bangladesh | R |

## 4. The composition, and why it is a bound

Taking Mattioli's mothers (10^2.2 CFU per two hands, i.e. 10^1.9 per hand)
against a 10⁶–10^8.75 CFU/g denominator:

```
g stool per hand  =  10^1.9 CFU/hand  /  10^(6.0 … 8.75) CFU/g
                  =  10^-4.1  …  10^-6.85
```

Against Wang's upper observation (1.55 × 10⁵ CFU/pair) the same arithmetic
returns 10⁻³·⁹ to 10⁻¹·¹ g/hand — the upper end being ~80 mg of stool on one
hand, which is not credible and is the clearest sign that the numerator is not
a conserved faecal tracer.

Five reasons this is an envelope and not a measurement, each of which would
have to be answered before any of it reaches a constant:

1. **Two stacked surrogates.** E. coli for norovirus, and culturable CFU for
   genome copies. Neither conversion is measured in the same subjects.
2. **E. coli is not conserved outside the gut.** It grows in some matrices and
   dies on dry skin; norovirus does neither in the same way. The ratio
   numerator/denominator is therefore not a mass fraction.
3. **The denominator is left-censored.** McOrist's adults run from
   *undetectable* to 8.75 log10 CFU/g; a host at the low end makes the implied
   mass per hand arbitrarily large for the same hand count.
4. **The setting is wrong for a cruise ship.** Every numerator above is a
   low/lower-middle-income household. Cantrell's own stratification puts E.
   coli prevalence on hands at 6% [1–12%] in upper-middle/high-income
   settings, so in the analogous population the measurement is mostly
   non-detects and bounds rather than locates the load.
5. **Recovery efficiency is unmeasured.** Hand rinsing recovers more than
   swabbing (Cantrell), but the fraction recovered is not known, so every
   numerator is a lower bound on what was on the hand.

**The event arm is unconvertible.** Oie 2021 is the only retrieved measurement
taken at a defecation *event* — the structure the engine actually uses, since
`_replenish_hand` re-attains the target at a stool event and decays between
them (SYMP-EFF-01). Its unit is total culturable microbes per glove, and the
matching per-gram denominator for that medium and that count is **`?nr`**: two
phrasings returned E. coli-specific and 16S community data only. Dividing
39,499 CFU/glove by an *E. coli* per-gram figure would be a unit error, and is
not done here. Read as an ordering only, it says a post-defecation hand
carries 2–3 logs more culturable organisms than the routine hands in the
numerator table — which is what one would expect, and which is why §4's band
should not be read as a peak-event load.

## 5. What this does and does not say about the A9 floor

The shipped bridge is **10⁻⁷·¹⁴ g/hand**. The routine-hand band derived above
is 10⁻⁶·⁹ … 10⁻⁴·¹, and the event-level ordering sits above that again. So the
convention is **at or below the bottom edge** of an independently derived
envelope: whatever else is wrong with it, it is not obviously *too high*.

Item 22 established that the residual posting floor at `adj` ≥ 10 runs through
the hand chain and that its normaliser is unsourced. This tranche does not
license the further inference that the floor exists *because the constant is
too large*. If anything, an independently sourced replacement drawn from this
envelope would raise the hand load and raise the floor. That is recorded here
as a consequence of the arithmetic, not as a reason to keep the present value,
and it is exactly why the bridge may not be sourced by which value moves A9 —
the anchor and the envelope point in opposite directions, and following the
anchor would mean discarding the only independent evidence retrieved.

## 6. Nulls, retrieval states, and what would close the row

| Row | State | Basis |
|---|---|---|
| Gravimetric faecal mass on a hand | **∅ null** | Three phrasings across this tranche and tranche 26; the literature measures organisms per hand, never mass |
| Stool titre and hand load in the same subjects | ~~**∅ null**~~ → **retrieved, partial** | **Overturned by [tranche 40](consensus_tranche_40_hand_event_amplitude.md) §2**: Liu 2013's Table 3, read from the PMC full text, pairs each subject's *maximum* stool titre (7.4–8.3 log10/g) with that subject's *mean positive* hand load. The pairing is max-versus-mean rather than simultaneous, so it bounds rather than measures — but it is not absent, and this row was a retrieval failure, not a null |
| crAssphage or other marker per hand, normalised | **∅ null** | Tranche 38 — the marker is a water literature |
| Total culturable organisms per gram of human faeces (Oie's denominator) | **`?nr`** | Two phrasings returned E. coli-specific and 16S data only |
| Mattioli 2015 ES&T indicator→mass conversion factor | **`?nr`** | Headline result read from a citing paper; the paper's own Methods not retrieved |
| Norovirus genome copies per hand in a naturally infected GII host | **∅ null** | Tranche 26, unchanged; Liu's GI.1 challenge subjects remain the only measurement |

Note on (i): tranche 40 found the full text of the paper this tranche read
only in abstract, and it answers part of (i) — see the row above, and §2 of
that tranche for the consequence, which is that the within-study pairing puts
the bridge at `−3.5 … −4.4 log10 g/hand`, at the **top** of the envelope this
tranche derived rather than below it.

What would close it, in order of strength: (i) a hand-rinse study reporting
norovirus genome copies per hand *and* stool titre in the same subjects,
*simultaneously*;
(ii) a gravimetric or dye-tracer study of faecal residue transferred to the
hand at defecation; (iii) Oie's per-gram denominator, which would turn the one
event-level numerator into a usable event-level bridge. None of the three was
found.
