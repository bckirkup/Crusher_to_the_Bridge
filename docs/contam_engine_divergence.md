# CONTAM vs native transport — divergence measurement

> **Status:** Measured analysis (2026-10-16, at `1ac4da8a`); mechanism
> corrected 2026-10-16 — ledger
> [`ledger/CONTAM-COMMISSION-01.md`](ledger/CONTAM-COMMISSION-01.md).
> Original ledger:
> [`ledger/CONTAM-DIVERGENCE-01.md`](ledger/CONTAM-DIVERGENCE-01.md). Index:
> [README.md](README.md).
>
> **Correction (2026-10-16):** §2's mechanism is falsified. Flagged
> simple-AHS terminals **do** enforce `Fahs × schedule` — measured on the
> native Linux ContamX 3.4.0.3 build now in `third_party/contamx/`. The
> "878 m³/h through MedBay" figure was the July-era 44-path fixture `.sim`
> read through the September 69-path `path_map.json`; re-solving the July
> `.prj` reproduces the fixture exactly — no shunt. The real authoring
> defects: uniform `ach·ΣV/n` terminal Fahs (ignoring per-room `V·duty`)
> plus the hobbyist duty schedule re-multiplying an already duty-weighted
> field. §1's retained-mass divergence and §3's HD-sink finding stand.
> The commissioned construction §7 prescribes is implemented as
> `ahs_terminal_mode="commissioned"` with measured solve-back inside
> 0.2% of declared on destroyer + expedition — see §9.

The repository carries two transport engines over the *same* mass-balance
propagator (`engines/py_contam_bridge.py` exact linear operator):

- **Path B (native):** `ContamTransportEngine` — prescribed star HVAC
  (`ach · V_branch · duty` apportioned by room volume share) plus declared
  cross-zone links and flat passive adjacency rates.
- **Path A (ContamX):** `ContamXTransportEngine` — real `.prj` → ContamX
  `.sim` pressure-solved airflow field, AHS legs bridged onto the same zone
  mass balance.

Only the **airflow field** differs; the deposition/removal machinery is
identical, so "deposition divergence" is purely which paths carry how much
air. ~~ContamX is a Windows binary and cannot run on Linux CI~~ — the
NIST ContamX 3.4.0.3 Linux-64 build now sits in (gitignored)
`third_party/contamx/`, so real solves run on this box; this document
collects what is measurable in-repo and what it implies.

## 1. Destroyer ground truth (real `.sim` fixture)

`tests/fixtures/contam/destroyer_baseline.sim` through the production
engines, identical 1e6-unit injection into Bridge, η = 0.5, decay = 0,
12 epochs:

| Metric | native | ContamX |
|---|---|---|
| Airborne mass retained after 12 h | 423,148 (42%) | 980,352 (98%) |
| Per-epoch concentration divergence (L1) | — | ≈ 9% of injected mass |
| Per-zone outflow-rate ratio range | — | 0.75×–30× |

Native removes airborne mass ~**2.3× faster** — the remembered "2×" is
still present, direction native-high, and now attributable.

## 2. What creates it — AHS terminal authoring (corrected 2026-10-16)

The `.prj` terminal legs of each AHS are **element-free paths** (`e# = 0`)
carrying a `Fahs` value equal to a per-room supply share. The original
account claimed `Fahs` is a non-enforced design annotation and that
ContamX's pressure solve "shunted 878 m³/h through MedBay alone" — **both
claims are falsified** (see the header correction): flagged simple-AHS
terminals enforce `Fahs × schedule`, and the 878 figure was a stale
`path_map.json` readout of the 44-path fixture `.sim`.

The real authoring defects the commissioned mode fixes:

- **Uniform split.** Terminal `Fahs` was `ach·ΣV_rooms / n_rooms` —
  ignoring the per-room `V·duty` weighting the declared field uses. On
  destroyer ahs2 that wrote 300/300/300 m³/h for
  MedBay/Mess_Hall/Galley vs declared 180/480/240: the branch total is
  right, the distribution wrong — a room-level misallocation, not a
  solver artefact.
- **Schedule double-count.** Hobbyist mode pins terminals to the `DutyW`
  week schedule (×0.5), halving the already duty-weighted declared field.

Consequence (still true, revised attribution): a room whose terminal is
*under-authored* — not solver-starved — drops toward its adjacency floor.
Measured floors vs native outflow rates:

| Platform | adjacency-only floor | native `k` | implied dwell factor |
|---|---|---|---|
| expedition_cruise_450 | 0.01–0.15 /h | 3–14 /h | 30–600× longer |
| classic_cruise_1900 | 0.02–0.14 /h | 5–10 /h | 30–600× longer |

## 3. Head-deck sinks

> **Shipped baseline (CONTAM-BIDIR-01):** numbers below were measured
> while native treated every `cross_zone_links` entry as one-way
> (`hvac.passive_link_mode: oneway`). The shipped default
> `bidirectional` emits both senses on passive links, matching the
> ContamX orifice; per-link `direction` pins a declared sense.
>
> **Shipped baseline (CONTAM-DUTY0-01):** the sink behaviour measured
> below is `hvac.duty0_terminal_mode: sealed`. The shipped default
> `extract` gives every duty-0 `oa_fraction: 1.0` branch return/exhaust
> legs at `ach · V_room` — heads now drain overboard natively, matching
> the commissioned export and the SIM behaviour below.

Every platform declares `HD_*` sanitary zones (`ach 19.2`,
`oa_fraction 1.0`, `hvac_duty 0.0` — exhaust-only branches). Under native
they are **permanent sinks**: `Sanitary_Makeup` cross-zone links push mass
in and no path takes it out. Measured native behaviour after 12 h:

| Platform | retained after 12 h | where |
|---|---|---|
| expedition_cruise_450 | 1.74% | 100% in 13 `HD_*` zones |
| classic_cruise_1900 | 0.33% | 100% in 17 `HD_*` zones |
| mega_cruise_5000 | — | 60 `HD_*` sinks by construction |

The destroyer SIM shows the real behaviour: heads vent overboard through
dedicated exhaust AHUs (`HD_MAIN_M`→ambient, makeup drawn from adjacent
service spaces). The native trap is a **field artefact**, small but real.

## 4. As-designed vs uncommissioned — the framing that decides everything

The two twins do not bracket "designed vs as-built"; they bracket
**design intent vs never-commissioned build**:

- **Native star ≈ the commissioned field.** The sourced ACH values
  (design-standard per-branch air changes) describe the distribution a
  ship's test-and-balance (TAB) exists to enforce — every terminal gets
  design flow.
- **ContamX solve on this PRJ ≈ the unbalanced field.** No balancing
  elements exist in the network, so the solve produces the distribution an
  *uncommissioned* ship would get — one terminal hogging each AHU.
- **The as-built ship is a third point neither twin contains:**
  commissioned to design, degraded by however much the TAB has drifted in
  service. That point is only reachable by sampling real vessels — it
  cannot be resolved inside the modeling stack.

Privileging the solved field over the sourced ACHs is therefore
privileging an *unbalanced-network artefact*, not a measurement of the
ship.

## 5. Bracketed-surrogate permissible-region test

Question posed by the prior endorsement ("the engine difference did not
eliminate the permissible region"): does a single emission rescale restore
the anchor vector under substitution?

**Method** (`tools/_contam_bracket_surrogate.py`): per AHS, divert fraction
`s` of each non-terminal room's return/supply legs onto the branch terminal
room (`s ∈ {0.5, 1.0}`; `s = 1` = the destroyer-SIM regime), terminal picked
as smallest or largest room per system, `HD_*` vented at PRJ-declared
exhaust rates. 24 h integrated-concentration integrals on four injection
classes per platform; dose aggregated into occupied zone classes (cabins,
dining, public venues, service, medical).

**Result — the endorsement fails on all three platforms:**

| Platform | occupied-class dose ratio range (cx/native) | retained 24 h (s=1) | residual anisotropy |
|---|---|---|---|
| expedition_cruise_450 | 0.18×–630× | 1–89% (native ~0.3–1.7%) | up to 95× |
| classic_cruise_1900 | 0.18×–2150× | up to 90% (native ~0.3%) | up to ~95× |
| spirit_cruise_3000 | 0.04×–2320× | up to 97% (native 0.7–17%) | up to ~275× |

- Required scalar rescale `r*` swings **0.25×–2000×+** by injection site —
  no global emission constant spans it.
- At `s = 0.5` (half the observed severity): still 1.4–95× anisotropy on
  multi-class anchors.
- **The sign is unknowable per venue.** Spirit's `LidoBuffet` injection
  gives dining-class dose **143.9×** under the smallest-terminal corner but
  **0.04×** under the largest-terminal corner — a ~3600× same-venue swing
  purely from which room the solver picks.
- Caveat on the largest ratios: they are partly low-denominator (native
  barely delivers dose to those classes). The defensible headline is the
  qualitative one: unknowable-sign, order-of-magnitude re-weighting per
  venue.
- What survives: only single-class-dominated anchors, and only partially —
  a dining-only event keeps dining dose near-scalable (1.0–20×) while its
  bystander classes still move 6–47×.

A uniform ~2× is absorbable by scalar refit; spatial re-weighting pulls
local-dose anchors and spread anchors in opposite directions — the
simultaneous-fit constraint is what dies, not just the region's position.

## 6. Per-anchor directions under substitution (inferred)

- **Local-exposure anchors (flu confined-slot, cabin exposure): up.**
  Cabins are exactly the zone class the solver starves.
- **Covid takeoff seeds:** already saturate (~96% vs 19–26% record);
  under ContamX current constants over-deliver *more* → refit pulls
  air-weighted emission constants **down**.
- **Total attack-rate anchors:** genuinely ambiguous — local dose ↑ vs
  shipwide mixing ↓ compete.
- **Norovirus:** ~null; zero continuous airborne emission by construction —
  this channel does not exist for it.
- **HD-trap inflation:** small but real — native permanently parks
  ~1.7%/0.3% of injected mass in head-deck zones; the vented field removes
  that artefact.

## 7. What ContamX is still good for — the defensible construction

- HD_* exhaust circuits (vents overboard — the correction native declares
  flatly wrong).
- Inter-zone orifice/leakage flows solved in one pressure field (measured
  ±50% vs native's flat 8–15 m³/h — same order, modest).
- Transient/pressure-driven flows native cannot do at all.

The defensible hybrid: **hold AHS terminals at design flow** and let
ContamX solve only the leakage/exhaust network — ContamX corrects what
native declares flatly rather than re-solving what native already gets
from sourced values. Under that construction the divergence collapses to
the HD-vent fix plus adjacency corrections — small, roughly scalar, and the
permissible-region endorsement plausibly survives.

**Implemented 2026-10-16** as `ahs_terminal_mode="commissioned"` — the
`Fahs` on a flagged simple-AHS terminal *is* ContamX's constant-flow
terminal (no bespoke fan model needed). Measured proof and the harness:
§9 and `tools/contam_commissioned_check.py`.

## 8. Open measurements

- The C13b paired zips (native vs ContamX on expedition/classic, seeds
  900–909, both flu and covid) were gitignored locals and never reached
  S3 — see ledger entry for the scan evidence. Even if recovered they
  quantify the *unbalanced* solve, not the commissioned field — they bound
  the artefact, not the truth.
- ~~Which room each AHS shunts to is solver-decided~~ — falsified:
  terminals enforce `Fahs × sched`; the bracket readout was a stale-map
  artefact. The commissioned `.prj` emission mode exists (§9).
- The decisive physical measurement is whether a real ship's TAB holds
  design flow — i.e., real-ship airflow sampling.

## 9. Hull → solver commissioning (2026-10-16, CONTAM-COMMISSION-01)

`ahs_terminal_mode="commissioned"` writes each terminal's `Fahs` as the
per-room declared `ach · V_room · duty` on a constant schedule
(exhaust-only `hvac_duty ≤ 0` branches: supply 0, return `ach · V`),
recording `declared_flow_m3h` per terminal in `path_map`.
`tools/contam_commissioned_check.py` exports, solves with ContamX 3.4.0.3
and compares per terminal. Measured on both reference hulls — every
terminal inside 0.2% of declared (residual is the `.sim` mean-density
conversion): destroyer 18 legs at ratio 1.002; expedition 92 legs at
1.001; all `HD_*` supplies exactly 0 with returns at the declared exhaust
rate. Non-FATAL on both.
