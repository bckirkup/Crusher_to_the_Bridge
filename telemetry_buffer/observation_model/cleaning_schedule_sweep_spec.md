# Per-zone-class cleaning schedule: sourced bounds and the sweep

Status: specification. Authored before the harness, so the grid is fixed by
what the literature bounds and not by which cell helps.

## Why a sweep and not a constant

PR #355 implemented routine housekeeping as a discrete pass over the share of
high-touch objects it reaches, using one coverage and one frequency for every
zone on the ship:

```python
ROUTINE_CLEANING_COVERAGE = 0.37        # Carling et al. 2009, Grade A
ROUTINE_CLEANING_LOG10_REDUCTION = 1.29 # Grade B
ROUTINE_CLEANING_EVENTS_PER_DAY = 1.0   # Grade B
```

That left an open item: real ships do not clean a cabin and a buffet rail on the
same schedule, and the gradient the model has to reproduce is precisely a
cabin-versus-public one. The question was whether a measured per-zone-class
schedule exists to replace the uniform pair. It does not — see §4 — so the
schedule is **swept inside sourced bounds and reported as an envelope**, and no
cell of the sweep is promoted to a default.

**One thing to notice before reading further.** Carling's 37% is Grade A, but
read what it measured: 8,344 objects in **273 public restrooms on 56 cruise
ships**. It is a *public-zone* measurement that the engine currently applies to
cabins as well. The uniform schedule is therefore not the conservative choice
it looks like; extending a public-restroom audit to a cabin is already an
unsourced step. The sweep does not add freedom to the model, it exposes freedom
the uniform constant was hiding.

## 1. Swept quantity

Per zone class `z` in `{cabin, dining, public, galley, crew_mess}` (the classes
`HIGH_TOUCH_AREA_M2` and `SURFACE_CONTACTS_PER_HOUR` already partition on):

- `coverage[z]` — fraction of high-touch objects a pass reaches.
- `events_per_day[z]` — passes per day.

`ROUTINE_CLEANING_LOG10_REDUCTION` (1.29) is **not** swept. It is a per-pass
efficacy of a wipe on a hard surface, measured on the objects actually wiped,
and nothing about which room the object is in changes it. Sweeping it would be
sweeping the same quantity twice, since coverage already carries the "was this
object cleaned at all" question.

## 2. Sourced bounds

Every bound below is a measured value from a named setting. Where a bound comes
from a model rather than a measurement, it says so.

### 2.1 Frequency, `events_per_day`

| zone class | range | low bound source | high bound source |
|---|---|---|---|
| `cabin` | 0.33 – 1.0 | Boone et al. 2025, *Hygiene* 5(2):22 — American household restrooms, fomite sampling at 1/2/3/7-day intervals; contamination and risk minimised at a **three-day (twice-weekly)** cycle, i.e. 0.33/day. QMRA on the same data estimates >98% norovirus risk reduction at that cycle (Gerba 2025, *Open Forum Infect Dis*, P-253: 91.5%). Private-accommodation analogue for a cabin. Grade C for a ship. | One pass/day, the denominator of Carling's "cleaned on a daily basis". Grade B. |
| `public` | 1.0 – 12.0 | One pass/day, as above. Grade B. | Zhang et al. 2024, *PLOS Comput Biol* 20:e1012561 — airport public surfaces, **every 2 h** (12/day) reduces norovirus infection risk by up to 83%. Built on 21.3 h of video across nine functional areas, 25,925 measured touches. The touch data are measurement; the 2 h interval is that paper's modelled optimum, not observed practice. Grade C. |
| `dining`, `galley`, `crew_mess` | 1.0 – 6.0 | One pass/day. Grade B. | Ge et al. 2020, *Am J Infect Control* 48(9):1095 — **measured practice**, routine disinfection 3×/day in general isolation wards and 6×/day in isolation ICUs. A supervised institutional food or care regime is the closest measured schedule to a galley's. Grade C for a ship. |

Two frequency figures were found and deliberately not used as bounds:

- Zhuang et al. 2023, *Buildings* 13:2582 — **twice per hour** (48/day) public
  surface disinfection, same airport touch dataset as Zhang 2024. Reported as
  an intervention scenario, not an optimum or an observed practice; 48/day is
  outside anything an operating ship would staff, and including it would widen
  the envelope with a number no one claims is real.
- Odoyo et al. 2021, *IJERPH* 18:6810 — five times a day for high-touch
  surfaces in Kenyan hospitals. This is the authors' *recommendation* given the
  contamination they found, not a measured schedule, and it sits inside the
  1.0–6.0 range already taken from Ge 2020.

### 2.2 Coverage, `coverage`

| zone class | range | source |
|---|---|---|
| `public` | 0.292 – 0.454 | Carling et al. 2009, *Clin Infect Dis* 49:1312 — 37% of 8,344 high-touch objects cleaned daily, 95% CI 29.2–45.4%, in 273 public restrooms on 56 cruise ships. **Grade A: this quantity, this setting.** The CI is the sweep range; the point estimate stays the default. |
| `cabin` | 0.336 – 0.600 | McKinley et al. 2022, *Am J Infect Control* 50(11):1216 — direct observation of 3,602 surfaces over 62 room cleanings in VA acute and long-term care: **33.6% of all environmental surfaces and 60.0% of high-touch surfaces** cleaned during a daily pass. An occupied single-occupancy room cleaned daily by housekeeping staff is the cabin analogue. Grade B. Meyer et al. 2020 (*AJIC* 48:S45, UV-marker audit, 1,235 surfaces) independently reports 63% appropriately cleaned, consistent with the upper end. |
| `dining`, `galley`, `crew_mess` | 0.292 – 0.600 | Union of the two above. No measurement exists for a food-service space; the range spans the two measured institutional settings rather than picking one. Grade C. |

Note the direction of the cabin range: the hospital analogue is *higher* than
Carling's shipboard public restrooms at both ends of the high-touch figure. If
a per-zone-class schedule is turned on, cabins get cleaned better than public
restrooms, not worse. That is the opposite of what would help the Park
gradient, which is a good sign the bounds were not chosen for their effect.

## 3. The grid

Cartesian product of the per-class ranges evaluated at their endpoints and
their midpoint, three points per axis:

```
coverage[z]       in {lo, (lo+hi)/2, hi}   from the table in 2.2
events_per_day[z] in {lo, geometric mid, hi} from the table in 2.1
```

The frequency midpoint is **geometric**, because the quantity that enters the
periodic steady state is the inter-pass interval `T = 24/n` and the effect of a
pass is roughly log-linear in `T` over this range; an arithmetic midpoint of
0.33 and 1.0 would sit at 0.67/day, which is a 36 h interval, and would
misrepresent the middle of the range as closer to daily than it is.

Reported for each cell: the Park cabin/public gradient, the per-zone-class
routine-cleaning multiplier on the time-averaged pool, and the absolute
cabin and public copies/swab against Park's observed ranges.

The headline output is the **envelope** — the min and max gradient over the
whole sourced box — and whether any cell reaches Park's 100–300×.

## 4. The null result, recorded

Searched via Consensus (~220M papers) with queries naming the measured
quantity and setting: cleaning frequency per day by area type; hotel
housekeeping public areas versus guest rooms; disinfection frequency public
restrooms and transit surfaces; measured cleaning schedules in accommodation.

**No study measures a cleaning frequency schedule differentiated by zone class
in an accommodation or passenger-vessel setting.** What exists is:

- *Coverage* measurements, many, all in hospitals or (Carling) shipboard public
  restrooms — how much of a room gets cleaned in one pass. §2.2 uses these.
- *Frequency* figures that are either modelled optima (Zhang 2024, Boone 2025)
  or single-setting observed practice in a hospital (Ge 2020). §2.1 uses these
  as bounds and labels which is which.
- *Within-room* differentials rather than between-zone ones: McKinley 2022
  finds bathroom surfaces cleaned more often than bedroom surfaces (OR 3.23)
  and Bernstein 2015 finds bathroom ATP drops below threshold after a daily
  pass while surfaces around the bed do not. Real, measured, and at a finer
  grain than the model's zone classes — it cannot be spent on a cabin-versus-
  public schedule.

Two findings from the same search that bear on the mechanism rather than the
schedule, and should not be lost:

- **Lei et al. 2017**, *BMC Infect Dis* 17:85 (MRSA, ODE model): daily whole-room
  cleaning at **100% efficiency** still reduces transmission to a susceptible
  occupant by only 54%, because surfaces recontaminate rapidly between passes.
  Below ~3 wipes/hour, targeting high-touch surfaces beats broad coverage;
  above it, coverage proportional to touch frequency wins. This is an
  independent statement of exactly what PR #355 measured: in a zone where
  pickup and redeposition are fast, a daily pass cannot hold the pool down.
  A model, not a measurement — but it is a model of the same mechanism,
  built by other people, agreeing.
- **Park et al. 2019**, *Int J Contemp Hosp Manag* 31(4):1793 — ATP readings and
  counted high-touch surfaces are both **higher in hotel guestrooms than in
  hotel public areas**. Independent support for the model's cabin/public
  contamination gradient having the sign it has, in a hospitality setting, from
  a study with no connection to norovirus or to this model.

## 5. Rules for reading the sweep

1. **No cell becomes a default.** The shipped configuration keeps the uniform
   Carling pair. A per-zone-class schedule is a configuration a run may set,
   with the sourced box as its admissible region, and the sweep reports what
   the choice is worth.
2. **The envelope is the result.** If no cell in the box reaches Park's
   gradient, the schedule is not the missing mechanism and PR #355's finding
   stands strengthened. That is a result, and it is reported as one.
3. **The gradient must not select the cell.** Reading the best-fitting cell
   back into the model is fitting a physical schedule to Park, which
   `.agents/skills/model-parameter-provenance/SKILL.md` forbids, and it would
   destroy Park's status as an out-of-sample check.
4. If a future source measures a real per-zone-class schedule, it replaces the
   corresponding range and the sweep narrows. The bounds are provisional; the
   prohibition in (3) is not.
