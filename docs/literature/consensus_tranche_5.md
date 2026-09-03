# Consensus tranche 5 — the two surface constants that gate the admissible-region search

**Status:** Evidence assembled and interpreted. One screen interval recut
(`bounded_screen.py`); **no pathogen-profile constant and no engine constant
changed.**
**Scope:** tasks #41 (`surface_decay_per_day` screen interval) and #42
(`surface_deposition_fraction` / hand→surface transfer).
**Method:** Consensus MCP searches on the measured quantity and medium, read
against the code paths that consume each field.

Both items entered the queue from Edison's norovirus bundle (see
[`edison_norovirus_influenza_bundle_review.md`](edison_norovirus_influenza_bundle_review.md)).
Both come back changed: one interval is far wider than either party proposed,
and the other task turns out to have been aimed at a field that does not do what
its name says.

---

## 1. `surface_decay_per_day`: the interval is an order of magnitude wide, and the fast end is unverified

### What the field is

`TransmissionCore._surface_survival` reads the profile value and passes it to
`SimClock.decay_per_epoch`, so it is a **per-day fractional loss of viable
surface-reservoir mass**, matching the schema (`number [0,1]`,
"Daily fraction of viable surface-reservoir mass lost"). Shipped norovirus
value: **0.25**, i.e. 0.125 log10/day, a 57.8 h half-life. Engine default
constant: 0.50. Screen interval before this tranche: **[0.10, 0.60]**.

Conversion used throughout: `f = 1 − 10^(−k)` for a decimal-log decay rate `k`
in log10/day.

### The measurements

No human-norovirus dry-surface *infectivity* decay measurement exists — human
norovirus is not culturable, so every infectivity number below is a surrogate
(MNV-1 or FCV), Grade B at best. Studies that state a rate or a rate-equivalent:

| Source | Medium and condition | Reported | k (log10/day) | f = 1 − 10⁻ᵏ |
|---|---|---|---|---|
| Fallahi & Mattison 2011, *J Food Prot* ([10.4315/0362-028x.jfp-11-081](https://doi.org/10.4315/0362-028x.jfp-11-081)) | MNV, stainless-steel disks, room temp | ~1 log10 infectivity loss in 15 d | **0.067** | **0.14** |
| Mormann et al. 2015, *J Food Prot* ([10.4315/0362-028x.jfp-14-165](https://doi.org/10.4315/0362-028x.jfp-14-165)) | MNV/FCV, stainless steel and plastic, room temp | infectious virus detected to 7 d; intact capsids 3–4 log over 70 d | 0.043–0.057 (capsid) | 0.09–0.12 |
| Kim, An-Na et al. 2014, *Food Environ Virol* ([10.1007/s12560-014-9154-4](https://doi.org/10.1007/s12560-014-9154-4)) | MNV, stainless steel, 28 d | 2.28 log10 PFU reduction; **D_R = 91.76 h** | **0.262** | **0.45** |
| Leblanc et al. 2019, *Food Microbiol* ([10.1016/j.fm.2019.103257](https://doi.org/10.1016/j.fm.2019.103257)) | MNV-1, stainless steel, 21 °C | >4 log viability loss in 14 d | ≥0.286 | ≥0.48 |
| Leblanc et al. 2019, same | MNV-1, stainless steel, 4 °C / −20 °C | no comparable loss | ≈0 | ≈0 |
| Kim, S. et al. 2012, *Environ Sci Technol* ([10.1021/es3032105](https://doi.org/10.1021/es3032105)) | MNV, stainless steel and coated wood, 15–40 °C, 30/50/70 % RH, 30 d | material-, temperature- and RH-dependent; **Weibull fitted better than linear** | Edison quotes 0.31 (30 % RH) and 0.79 (50 % RH) — see below | 0.51–0.84 |
| Konkol et al. 2026, *J Hosp Infect* ([10.1016/j.jhin.2026.05.042](https://doi.org/10.1016/j.jhin.2026.05.042)) | MNV, bathroom surfaces (steel, glass, tile, plastic) | stable 14 d; 21 d on terry cloth | slow | — |
| Lamhoujeb et al. 2009, *Food Environ Virol* ([10.1007/s12560-009-9010-0](https://doi.org/10.1007/s12560-009-9010-0)) | **Human** NoV, steel and PVC, 7/20 °C, low/high RH | putative infectivity persists days–weeks, RH- and temperature-dependent | not stated as a rate | — |
| Colas de la Noue et al. 2014, *Appl Environ Microbiol* ([10.1128/aem.01871-14](https://doi.org/10.1128/aem.01871-14)) | MNV, absolute humidity gradient, 9/25 °C | low **and** saturated AH preserve infectivity better than intermediate — non-monotone in RH | — | — |

### Two corrections to the queued task

**(a) Edison's [0.49, 0.84] is the top ~40 % of the literature, not its span.**
The recommendation rests on one study's fastest two cells. Four other
stainless-steel MNV studies land between 0.09 and 0.48, and the slowest
(Fallahi) is 12× slower in rate than the fastest cell Edison quotes. The
shipped 0.25 is *inside* the literature, near the slow end — not "2–6× off" it.

**(b) The citation and the numbers do not line up, and the numbers are
unverified.** Edison attributes "D10 = 1.26 d (50 % RH) / 3.20 d (30 % RH)" to
Kim et al. **2014**. Kim 2014 is a food-contact-surface survival study with no
RH arm; its abstract reports a single stainless-steel **D_R of 91.76 h**, which
is 0.262 log10/day — **3× slower** than the 0.79 attributed to it. The RH design
(30/50/70 %) belongs to Kim et al. **2012**, whose abstract states that Weibull
fits beat linear ones and reports no rate constants. So the pair 0.31/0.79 is
either from Kim 2012's tables (plausible, unverifiable from the abstract) or a
conflation of two papers. **Not adoptable as stated**; recorded here as the
fast-end candidate with its provenance in doubt.

### One semantic trap, worth stating because it would look like sourcing

Every study that measured both reports **genome loss far slower than infectivity
loss** — Fallahi's genome copies barely decline while infectivity falls 1 log;
Mormann's capsids survive 70 d. Our surface pool is denominated in genome copies
and its dose is converted through a copies-based dose-response, so decaying the
pool at the **RNA** rate (0.04–0.06 log10/day, f ≈ 0.09–0.12) would be
dimensionally consistent and epidemiologically wrong: it would preserve
non-infectious material as if it were dose. The infectivity rate is the right
one, and that choice is an interpretation, not a measurement.

### What was changed

`bounded_screen.py`, norovirus factor `surface_decay_per_day`: **[0.10, 0.60] →
[0.14, 0.84]**, Grade B, comment carrying the low- and high-end sources. The
interval is the *span of the surrogate literature on non-porous surfaces at
indoor temperature*, low end Fallahi 2011, high end the Kim fast cell flagged
above. It is deliberately wider than either the old screen or Edison's
proposal, because the width is real: it is material, temperature, RH and assay,
and Colas de la Noue shows the RH dependence is not even monotone.

Consequences recorded rather than acted on:

- The 4 °C arm implies f ≈ 0 for refrigerated surfaces. Cruise-ship galley cold
  rooms exist; the screen does not resolve zone temperature, so the interval is
  authored for occupied indoor spaces and the cold case is out of scope.
- The screen sweeps `f` **linearly** and this tranche did not change that. The
  underlying quantity is a rate spanning 1.07 decades, so a rate-space
  (log-uniform) sweep would cover the slow end better; the factor was already
  flagged non-monotone on whole-ship attack rate in
  [`../norovirus/bounded_screen_results.md`](../norovirus/bounded_screen_results.md)
  §4. Queued rather than done, so the representation change is not entangled
  with the interval change.
- The Morris ranking was produced on the old box. Recutting an interval changes
  the elementary effects of *every* factor, so the ranking must be re-run before
  #37, not patched.

---

## 2. `surface_deposition_fraction`: task #42 was aimed at the wrong field

### The code fact, established before any evidence was applied

There are three distinct `1e-4` constants and one profile key, and they do not
mean the same thing:

| Quantity | Location | What it multiplies | Reservoir it feeds |
|---|---|---|---|
| `surface_deposition_fraction` (profile key) | read in `orchestrator_epoch.py` as `prof.get("surface_deposition_fraction", 1e-4)` | shedding × confinement emission factor | `engine.get_pathogen_zone_mass(pid)` — the **zone/airborne** pool that is decayed by `airborne_half_life_hours` in the same loop |
| `SURFACE_DEPOSITION_FRACTION = 1e-4` | `engines/infection_dynamics_bridge.py` | `agent.current_shedding` | `_zone_pathogen_mass` — the **legacy** path |
| `ENV_HOST_DEPOSITION_FRACTION = 1e-4` | env source path | host shedding | zone-scoped environmental reservoir |
| hand→surface deposit | `engines/transmission_core.py` | agent hand load | `_deposit_surface_mass` — the **modern fomite surface pool** |

The modern fomite pool is *not* filled by the profile key. It is filled by
emesis (`pool_gain`) and by hand→surface back-transfer, and drained by
`surface_decay_per_day` and cleaning. So "source `surface_deposition_fraction`
from Grove's hand→surface 0.6 %" mapped a *fomite-chain* measurement onto a key
whose value lands in the *airborne* pool, one decay law removed from any
surface. The task as written would have made the arm worse while looking like
provenance.

Its inherited comment does not describe a measurement either: "ViralParticle.java:
particles survive 86400 steps = 1 day" is a *survival duration*, offered as the
justification for a *deposition fraction*. Two different quantities, and the
COVID profile's 5e-5 is documented in the audit as that same number divided by
two.

### The evidence, applied to the field that actually deposits on surfaces

Hand→surface transfer, measured, norovirus or a calicivirus surrogate on
non-porous surfaces:

| Source | System | Hand → surface | Surface → hand |
|---|---|---|---|
| Tuladhar et al. 2013, *Int J Food Microbiol* ([10.1016/j.ijfoodmicro.2013.09.018](https://doi.org/10.1016/j.ijfoodmicro.2013.09.018)) | MNV-1 infectivity, finger pad ↔ stainless steel | **13 ± 16 %** immediate; **0.1 ± 0.2 %** after 10 min drying | 2.0 ± 2.0 % (steel), 4.0 ± 5.0 % (Trespa), 40 min dry |
| Sharps et al. 2012, *J Food Prot* ([10.4315/0362-028x.jfp-12-052](https://doi.org/10.4315/0362-028x.jfp-12-052)) | Human NoV GII, gloved fingertip → steel | **58–60 %** wet; **<1 %** dry | 1–50 % wet, 2–11 % dry (via fomite) |
| Bidawid et al. 2004, *J Food Prot* ([10.4315/0362-028x-67.1.103](https://doi.org/10.4315/0362-028x-67.1.103)) | FCV infectivity, fingerpad ↔ steel disk | **13 ± 3.6 %** | 7 ± 1.9 % |
| Dallner et al. 2021, *Viruses* ([10.3390/v13071352](https://doi.org/10.3390/v13071352)) | MNV-1, contaminated hand → steel | **9.19 %** | — |
| Anderson et al. 2021, *Appl Environ Microbiol* ([10.1128/aem.01215-21](https://doi.org/10.1128/aem.01215-21)) | MS2/Phi6, 360 events, 20 volunteers, steel/plastic/wood | pooled mean 0.26 (MS2), 0.17 (Phi6); direction significant for MS2 (surface→finger > finger→surface) | same study |
| Julian et al. 2010, *J Appl Microbiol* ([10.1111/j.1365-2672.2010.04814.x](https://doi.org/10.1111/j.1365-2672.2010.04814.x)) | MS2/φX174/fr, 656 events, glass | pooled 0.23 ± 0.22, both directions | same study |
| Lopez et al. 2013, *Appl Environ Microbiol* ([10.1128/aem.01030-13](https://doi.org/10.1128/aem.01030-13)) | fomite → finger, 9 surfaces, RH arms | — | non-porous up to 57 % (low RH) / 79.5 % (high RH); porous <13 % |
| Walker et al. 2022, *Viruses* ([10.3390/v14051048](https://doi.org/10.3390/v14051048)) | aerosol-deposited saliva, surface → artificial finger | — | <10 % below 40 % RH, rising to ~50 % above it |

Three findings follow, and each contradicts something we or Edison had assumed.

**(a) The 40× directional asymmetry is not a property of the literature.** Grove
is quoted as 24 % surface→hand against 0.6 % hand→surface. Bidawid measures the
asymmetry the *other* way on the same materials (13 % hand→steel against 7 %
steel→hand), Sharps measures hand→surface at 58–60 %, and Anderson — the largest
bidirectional data set — finds direction significant but worth a factor well
under two. What actually spans orders of magnitude is **wet versus dry**:
Tuladhar's own finger→steel figure falls from 13 % to 0.1 % with ten minutes of
drying, and Sharps' from 59 % to <1 %. Grove's 0.6 % is consistent with a dried
donor; adopting it as *the* hand→surface fraction would encode drying state as
if it were direction.

**(b) Grove 2015 could not be verified at source.** Two targeted Consensus
searches on its measured quantity, its stated design (n = 150 transfers, 80
participants) and its author did not return it. That is a null on verification,
not a claim the paper does not exist — and **that null is now retired**: Grove 2015 was the first
result of a query in [tranche 12](consensus_tranche_12_contact_transfer.md) and its
numbers (24 % surface → hand, 0.6 % hand → surface, ≥ 9 replicates) are
confirmed there — but the pair 24 % / 0.6 % is currently
Grade C-by-provenance in our hands regardless of the grade Edison assigned it,
and the verifiable literature above covers the same quantity.

**(c) The model's existing choice survives, for a reason nobody had stated.**
`SURFACE_TO_HAND_LOGNORMAL = (−2.1, 1.4)` (median 0.122) is used for *both*
directions — pickup and hand→surface deposit. Against Bidawid's 13 % and
Tuladhar's immediate 13 %, a 12 % median for hand→surface is close to the
measured wet value; against Tuladhar's dried 0.1 % it is 100× high. So the
reuse of one distribution in both directions is defensible as a *wet-contact*
parameterisation and is the honest interval, whereas Edison's 0.006 point value
would have been 20× low relative to the same measurement it cites for the other
direction. Reversing the recommendation.

### What this makes of task #42

Not "source `surface_deposition_fraction` from 0.6 %". Split into:

1. **Rename or retire the profile key.** It deposits into the airborne pool
   under a name that says surface. Either the name follows the reservoir or the
   write follows the name; both are behaviour changes and neither is a sourcing
   change, so this is a mechanism task with a before/after run attached.
2. **Bound the hand→surface fraction as an interval, not a point:** [0.001,
   0.60] across the wet/dry span, with [0.09, 0.13] as the wet-contact core
   (Tuladhar immediate, Bidawid, Dallner) — which is where the shipped
   distribution already sits. Grade B (surrogate, non-porous, food-contact).
3. **The binding uncertainty is drying state, not transfer efficiency**, and the
   model has no drying-state axis on the surface pool. That is the finding worth
   carrying to #37: a factor-of-100 lever exists that no interval in our box
   currently represents.

---

## 3. Recorded nulls

- No human-norovirus dry-surface infectivity decay rate exists (surrogate-only,
  confirming tranche 1's null on the airborne side for a different medium).
- No measurement of hand→surface transfer under *cruise-ship* soiling,
  humidity or touch pressure. Every value above is a food-contact or
  laboratory assay.
- ~~Grove et al. 2015 not located by Consensus in two targeted searches (§2b).~~
  **Retired:** tranche 12 retrieved it as a first result and confirmed its
  numbers; see §2b.
- No study reports deposition as a *fraction of total shedding*, which is what
  the profile key's units claim to be. The quantity the code asks for may not be
  a measurable one.
