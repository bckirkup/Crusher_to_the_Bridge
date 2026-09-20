# Tranche 44 — the fomite transfer *product*: what is commensurable with literature, and what is not

**Read first.** This tranche exists because `NORO-DOSE-BLOCK-01` reported a
whole-voyage "surface→hand loss" that moved by more than a decade between the
8105/8106 pair (2.17 log10) and the 20-seed block (median 0.840 log10, range
7e-7 … 2.673 log10). The first question is therefore not "what does the
literature say", it is **which layer of the implemented chain a published
transfer measurement is even a measurement of**. The answer is that the
whole-voyage ratio is not one, and that the model's per-touch factors are.

Nothing here changes a constant. No number below was retrieved in order to
move the model onto an anchor; the arithmetic in §4 is run in the direction
model → literature, and where the model sits outside the retrieved evidence
that is recorded as a finding, not repaired.

**Register rows fed.** Amends the `SURFACE_TO_HAND_LOGNORMAL` row of
[`../parameter_provenance_register.md`](../parameter_provenance_register.md)
(§3.4) and **opens four rows that do not exist there at all**:
`HAND_TO_MOUTH_NORMAL`, `MOUTH_CONTACT_FRACTION_RANGE`,
`SURFACE_CONTACT_FRACTION_RANGE` and `HAND_AREA_CM2_RANGE`. All four are
carried in `engines/transmission_core.py` under the comment "from the authored
fomite rederivation specification", with no citation and no register row —
i.e. one of the two literature-comparable transfer efficiencies in the chain
(hand→mouth) has been untraced since the fomite rederivation landed. That is
finding **F44-1**.

**Retrieval.** Consensus MCP, full-text chunks on, four differently-phrased
queries (§5). Each number below records where in the paper it was read.

---

## 1. The implemented chain, factor by factor

`_fomite_pickup_request_for_area` and `_hand_to_mouth_dose`
(`engines/transmission_core.py`) implement, per susceptible per epoch:

```
request = contacts_surface(zone, epoch)
        * used_fraction_surface * hand_area_m2 / high_touch_area_m2(zone)
        * eff_surface_to_hand
        * surface_mass                      # then min(surface_mass, ·)
dose    = contacts_mouth(epoch)
        * used_fraction_mouth * eff_hand_to_mouth
        * hand_load                         # then min(hand_load, ·)
```

Six factors, of which only two are transfer efficiencies:

| Layer | Quantity | Commensurable with a published transfer measurement? |
|---|---|---|
| A | `eff_surface_to_hand` = lognormal(-2.1, 1.4), clipped at 1 | **yes** — donor-surface → finger/hand per contact |
| B | `eff_hand_to_mouth` = normal(0.339, 0.132), clipped to [0,1] | **yes** — finger → lip per contact |
| C | A × B, per touch-and-mouth pair | **yes**, against composed two-step assays |
| D | `used_fraction_*`, `hand_area_m2`, `high_touch_area_m2` | **only as geometry**: measured FSA distributions exist; the areal *denominator* (`HIGH_TOUCH_AREA_M2`) is a declared assumption with no measurement |
| E | contact frequencies | behaviour, sourced elsewhere (Wilson/Jin/Ackerley rows) — not transfer |
| F | `min(surface_mass, ·)` and `_delivery_scale` saturation | **no counterpart in any assay** — a conservation artifact of a shared pool |

## 2. Why the whole-voyage ratio is not layer C

`NORO-DOSE-BLOCK-01`'s transfer terms are
`log10(Σ surface_mass_offered / Σ mass_delivered_to_hands)` summed over
per-epoch deliver calls. Three properties make that ratio non-commensurable
with anything in §3:

1. **The denominator double-counts.** A zone pool that persists for k epochs is
   *offered* k times, so Σoffered is not a mass of virus, it is a mass-epoch.
2. **It is bounded above by conservation, not by transfer.** Σrequested/Σoffered
   over the 22 committed cells spans 0.0021 (seed 8002) to 2.13 (seed 8000);
   where it exceeds 1, layer F truncates it, and the "loss" recorded is
   `log10(1.000) ≈ 0`. Seed 8000's near-zero loss is exactly this: requested
   4.77e5 GEC against 2.24e5 GEC offered.
3. **It mixes layers A, D, E and F**, whose spans are respectively ~2, ~1.5 and
   ~1.5 decades wide, so its seed-to-seed movement carries no information about
   any one of them.

The 2.17 → 0.840 log10 move that opened this item is therefore a change in
*which regime the cells sat in*, not evidence that the hull's transfer
efficiencies moved. Deciding whether the transfer chain is defensible requires
layers A, B and C, measured per contact.

## 3. What the literature measures

### 3.1 Layer B — finger → lip, per contact

* **Rusin et al. 2002**, *Journal of Applied Microbiology*, DOI
  10.1046/j.1365-2672.2002.01734.x. Fingertips inoculated with a pooled
  culture, held to the lip area: **PRD-1 phage 33.90 %**, S. rubidea 33.97 %,
  M. luteus 40.99 % (**Abstract, Methods-and-results**; `Ab` — the SD is not in
  the retrieved text). The model's mean 0.339 is Rusin's *phage* figure to
  three decimals; the shipped SD 0.132 has **no retrieved origin** (F44-1).
* **Abney et al. 2022**, *Journal of Applied Microbiology*, DOI
  10.1111/jam.15758. MS2 coliphage, finger → lip, by inoculum matrix:
  **PBS 52.53 ± 4.48 %**, TSB **23.15 ± 24.27 %**, intermediate for FBS and
  ASTM soil load; matrix effect significant (p = 0.0135) (**Table 3 and
  Abstract**; `R` — full-text chunk). Their own Discussion states Rusin 2002
  is *"the sole reference for self-inoculation transfer efficiency rates to
  calculate dose for QMRA"* (`R`), which is why B has two sources and not ten.
* Both are surrogates (phage), both are *lip* not *ingestion*, and neither is
  norovirus. **Grade B is the ceiling.**

### 3.2 Layer A — donor surface → hand, per contact

Already sourced in the register (§3.4): norovirus and norovirus surrogates on
non-porous donors by infectivity **2.0–24 %** (Tuladhar 2013 MNV-1 steel
2.0 ± 2.0 %; Bidawid 2004 FCV 7 ± 1.9 %; Grove 2015 MNV-1 spigot → bare hand
24 %), human NoV by genome copies **2–11 % dry / 1–50 % wet** (Sharps 2012),
widened over analogous viruses and humidity **~0.5–80 %** (Lopez 2013, Ansari
1988, Behzadinasab 2021). This tranche adds two items that bear on *how* those
percentages must be read:

* **Rusin 2002** (same paper as §3.1): whole-hand transfer from **non-porous**
  household fomites in normal use — phone receiver **38.47–65.80 %**, faucet
  **27.59–40.03 %**, porous fomites **< 0.01 %** (**Abstract**; `Ab`). This is
  an order of magnitude above the norovirus-specific band and is the *upper*
  envelope of layer A: bacteria/phage, whole-hand, wet inoculum.
* **Walker et al. 2022**, *Viruses*, DOI 10.3390/v14051048. Artificial
  finger-pad, aerosol-deposited saliva, standardized 15 N / 1 s touch:
  transfer **< 10 % at RH < 40 %**, rising with RH (**Abstract**; `R`). Their
  contact-area treatment is the point of interest here: the artificial finger
  contacts a proportion **A ~ Normal(0.1865, 0.0224)** of the 1250 mm² coupon,
  and the *observed* transfer efficiency is only recoverable after dividing
  out A (their Eqs 5-7, **Methods**; `R`). So a published "transfer
  efficiency" is a *per-contact-patch* quantity, and composing it with a
  separate areal-dilution factor — which is what layer D does — is the
  intended use, not a double count.

### 3.3 Layer D — the geometry factors

* **AuYeung et al. 2008**, *Environmental Research*, DOI
  10.1016/j.envres.2008.07.010. Fraction of total hand
  surface area per hand-to-object contact, children, outdoor: median FSAs
  **0.13–0.27** across object classes, time-weighted **0.12–0.24**, and
  **0.31 captures 80-100 %** of each child's contacts (**Abstract**; `Ab`).
  Model `SURFACE_CONTACT_FRACTION_RANGE` = uniform(0.008, 0.25): mean 0.129
  lands on AuYeung's lower median, the upper bound on the upper median — but
  the **lower bound 0.008 is below anything measured**, and the population is
  children outdoors, not adults on a ship. Grade B as an interval, shape X.
* **AuYeung et al. 2006** (ISEE P-626, DOI 10.1097/00001648-200611001-01259).
  Fraction of hand surface area **mouthed** per hand-to-mouth immersion,
  38 children videotaped: median per-contact FSA **0.11** (range of child
  medians 0.06–0.33), time-weighted median 0.14; most immersions were 2-3
  fingers, partial immersion (**Abstract**; `Ab`). Model
  `MOUTH_CONTACT_FRACTION_RANGE` = uniform(0.008, 0.012) — i.e. **~10× below
  the only retrieved measurement of this exact quantity**. It is consistent
  with an *adult fingertip* geometry (one fingertip 1.83 cm², the contact
  area used in every trial of Wilson et al. 2020, DOI 10.1098/rsif.2020.0121,
  **Methods**, `R`, over a 448 cm² hand = 0.41 %; 2-3 fingertips = 0.8-1.2 %, which is the
  shipped interval to two figures), so the gap is population + configuration
  (children immersing whole fingers vs adults touching with fingertips), not
  arithmetic. Direction of the residual: the model is **conservative** here.
  Finding **F44-2**: the shipped interval is an unstated adult-fingertip
  derivation, defensible but not measured, and `X` in shape.
* **Lee et al. 2007**, *Journal of Physiological Anthropology*, DOI
  10.2114/jpa2.26.475. Alginate-measured single-hand surface area, 65 Korean
  adults: males mean **448 cm² (371-540)**, females mean **392 cm²
  (297-482)**; hand = 2.4-2.5 % of BSA (**Abstract + Results**; `R`). Model
  `HAND_AREA_CM2_RANGE` = uniform(445, 535) is a **male-only upper band**: it
  excludes the entire female mean and most of the female range, and its lower
  bound sits at the male mean. Finding **F44-3** — a ~10-15 % high bias on a
  linear factor of the pickup numerator, in a passenger population that is not
  male-only.
* `HIGH_TOUCH_AREA_M2` (the areal denominator) remains a **declared
  assumption** — the in-code comment already says no whole-room high-touch
  area measurement was found, and nothing retrieved here supplies one. It is
  the largest single factor in layer D (cabin 1.5 m² vs galley 10 m²) and it
  is unmeasured; that, not the transfer efficiencies, is where the product's
  uncertainty lives. **∅ null, unchanged.**
* Rejected, per the register's standing policy on model-derived numbers:
  Wilson 2020/2021, Julian 2009, Canales 2004 supply *model* parameters and
  compartment conventions, not measurements of this hull's quantities. They
  are cited above only for conventions (fingertip area, the A-divisor).

## 4. Model vs literature, per layer

Closed form over the shipped constants (4e6 draws, `numpy` default_rng(0);
this is arithmetic on the constants, not a simulation result):

| Layer | Model | Literature | Verdict |
|---|---|---|---|
| A `eff_surface_to_hand` | median **0.122**, IQR 0.048-0.315, mean 0.243, **6.7 % of draws clip at 1.0** | NoV/surrogate non-porous by infectivity 0.020-0.24; wet/genomic to 0.50; analogues to 0.80; Rusin whole-hand non-porous 0.28-0.66 | **defensible**: median and IQR inside the norovirus-specific band; the clipped 6.7 % tail is above every norovirus figure and is licensed only by the analogue envelope |
| B `eff_hand_to_mouth` | median **0.339**, IQR 0.250-0.428 | Rusin PRD-1 0.339; Abney MS2 0.232-0.525 | **defensible**, and the point value is traceably Rusin's phage figure; the SD is untraced (F44-1) |
| C per-touch chain A×B | median **0.038**, IQR 0.014-0.102, mean 0.082 | composed: NoV-specific low 0.020 × 0.339 = **0.0068**; Grove 0.24 × 0.339 = **0.081**; Rusin non-porous 0.385-0.658 × 0.339 = **0.13-0.22** | **defensible**: the model's median sits between the norovirus-specific floor and the phage/bacteria ceiling, one decade above the former and one below the latter |
| D areal dilution `used × hand/area × A`, per touch | cabin median 4.2e-4 (mean 1.0e-3); dining 8.0e-5; public 1.1e-4; galley 6.4e-5; sanitary 1.3e-3 | **no commensurable measurement** — the denominator is declared | **∅ null**; two of its three factors (F44-2, F44-3) are additionally biased against measured FSA/HSA distributions |
| F cap / saturation | 22-cell witness: Σrequested/Σoffered 0.0021-2.13, one cell truncated at 1.000 | none | **model artifact**; must be reported separately, never inside a "transfer" figure |

Per-contact hand→mouth fraction of the whole hand load, `used_m × B`: median
**0.0033**, IQR 0.0024-0.0043 — this is the quantity the block's
`hand_to_mouth_dose / hand_load_seen` ratio (~0.010 per epoch, i.e. ~3 mouth
contacts) decomposes into, and it is **not** layer B; a reader comparing the
block's 1.96 log10 hand→mouth "loss" against Rusin's 33.9 % is comparing an
epoch-level depletion against a per-contact efficiency.

## 5. Retrieval record

| Query | Filters | Outcome |
|---|---|---|
| "fingertip to lip transfer efficiency percent virus bacteria hand-to-mouth 33.9%" | full-text chunks, 8 results | Rusin 2002 `Ab` (abstract only, no SD), Abney 2022 surfaced, Wilson 2020 `R`, Walker 2022 `R` |
| "finger to lip transfer efficiency MS2 coliphage percent inoculum matrix toilet seat" | full-text chunks, 5 results | Abney 2022 **`R`** — Table 3 and Experiment-results chunks |
| "fraction of total hand surface area involved in hand-to-mouth contact fingertip area percent exposure model" | full-text chunks, 6 results | AuYeung 2006 `Ab`, Wilson 2021 `R` (conventions only) |
| "fraction of hand surface area contacting surfaces per hand-to-surface contact adults fingertips palm exposure model distribution" | full-text chunks, 6 results | AuYeung 2008 `Ab`, Brouwer 1999 surfaced (powder, dermal loading — different endpoint), Canales 2004 rejected as model input |
| "adult hand surface area cm2 mean men women exposure factors dermal surface area of hands" | full-text chunks, 6 results | Lee 2007 **`R`**; no EPA Exposure Factors Handbook table retrieved (not indexed — `?nr`, not a null) |

Legend as elsewhere in this directory: `R` = read in retrieved full text,
`Ab` = abstract only after the attempts shown, `?nr` = not retrieved.

## 6. Findings

* **F44-1** `HAND_TO_MOUTH_NORMAL` has no register row and no cited source in
  the engine. Its mean is Rusin 2002's PRD-1 figure; its SD 0.132 is untraced.
  A layer that the register grades and bounds elsewhere in this chain has been
  shipping ungraded.
* **F44-2** `MOUTH_CONTACT_FRACTION_RANGE` (0.008-0.012) is ~10× below
  AuYeung 2006's measured per-contact mouthed FSA (median 0.11, children). It
  reconstructs exactly as an adult 2-3-fingertip geometry, so it is
  *derivable* but undocumented and unmeasured, and it makes the model
  conservative on the ingestion step.
* **F44-3** `HAND_AREA_CM2_RANGE` (445-535 cm²) is a male-only band against
  Lee 2007 (males 448, females 392 cm²), biasing a linear factor of pickup
  high by ~10-15 % for a mixed passenger population.
* **F44-4** The whole-voyage "transfer terms" reported by `NORO-DOSE-01` and
  `NORO-DOSE-BLOCK-01` are not transfer efficiencies and must not be compared
  to published ones; the comparable quantities are layers A, B and C, and on
  those the hull is defensible.
* **F44-5** The product's dominant unmeasured factor is the areal denominator
  `HIGH_TOUCH_AREA_M2`, not the transfer efficiencies. Any future attempt to
  make the fomite route agree with an outbreak anchor by moving A or B would
  be moving the two factors that *are* sourced, in order to compensate for the
  one that is not.
