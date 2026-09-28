# FLU-DELIVERY-01
**Date:** 2026-09-27
**Commit:** 201835b2
**Pathogens:** influenza_a
**Status:** measured
**Measured at:** 201835b2

## k unit correction (sourced, not fitted)

`dose_response.k` for `influenza_a` moved `0.18 → 0.0006` per emitted copy —
the arithmetic midpoint of the converted sourced bound `2e-4..1e-3` per copy
(`docs/literature/non_scored_arms_audit.md` §2.2: Alford 1966 ID50 0.6–3 TCID50
→ k 0.23–1.16 per TCID50, ÷ the Van Wesenbeeck 2015 ≥1e3 copies/TCID50
conversion floor). Grade B basis; the aerosol-vs-intranasal citation spread
behind the interval stays open for the literature-audit session — the register
row says so explicitly.

Two coupled live fields moved with it: `dose_reference_log10 0.59 → 3.06`
(anchors dose-dependent incubation shortening at the corrected N50 ≈ 1155
copies; `engines/incubation.py` reads it) and `flu_confined_dose_probe`'s
`SATURATION_99_COPIES` became `_saturation_99(profile)` so the probe tracks
whatever k ships. Edison bundle keeps `k = 0.18` as the labelled baseline
comparator — untouched.

## Stage-resolved confined delivery (measured)

Instrument: `tools/flu_delivery_stages_probe.py` — pure-observation wrappers on
`_deposit_agent_emission`, `_droplet_unit_doses`, `_droplet_target_dose`,
`_apply_hvac_downstream_doses`, `partition_block_air` and
`set_pathogen_zone_mass`, plus the `ChallengeRecorder` for post-efficiency
dose. RNG untouched. Cells: `classic_cruise_1900`, declared SOP-017
confinement, seeds 8105/8106, corrected k — i.e. run on the 201835b2 working
tree with this PR's profile diff applied. Slot definition identical to
FLU-DOSE-01 (infected index + confined pair + mate uninfected at confinement).

At corrected k the slot population is 34 (28 + 6) vs 707 at shipped k — the
extensive-margin correction is itself part of the result: far fewer cabins
ever see an index.

Pooled chain (both seeds; per-copy factors in parentheses, all measured):

| stage | 8105 | 8106 | declared basis |
|---|---|---|---|
| member emission into cabin compartment | 8.63e8 | 3.56e8 | — |
| → post-confinement emitted | 9.66e6 (×0.050) | 1.38e6 (×0.05 on droplet-rows) | `confinement_emission_factor` 0.05 |
| → HVAC deposit branch | 3.28e7 (×0.038) | 1.35e7 (×0.038) | dep_frac 0.76 × cef 0.05 |
| → droplet aerosol (pool+plume) | 4.83e5 (×0.05) | 6.9e4 (×0.05) | `DROPLET_AEROSOL_FRACTION` 0.05; partition 0.175 pool / 0.825 plume |
| HVAC: mass presented to a doseable target | 2.49e4 (×7.6e-4) | 1.15e4 (×8.5e-4) | t½ 1.5 h decay + block-partition dilution + shedder-cabin exclusion (see below) |
| pool inhaled_pre → pool dose | 1082 → 8.28 (×7.7e-3) | 185 → 1.15 | residence 0.166 × tf 0.05 × presence ≈ declared factors exactly |
| delivered droplet (pool + mate addback + plume) | 9770 | 1057 | addback 33–42% · plume 57–67% |
| delivered HVAC | 3.7 | 0.5 | ~0.04% of delivered |
| **capture delivered/emitted** | **1.13e-5** | **2.97e-6** | pooled 8.9e-6 |

Every measured factor matches its declared constant — no stage discards more
than its constants imply. The earlier ~1e-6–1e-7 capture figure was inferred
from shipped-k doses that were truncated by early conversion; measured on an
open window it is ~1e-5–3e-6.

One asymmetry surfaced (measured, not a defect on the evidence): the HVAC arm
keeps `dep_frac × cef = 0.038` of member emission with no mate restoration,
while the droplet arm restores confinement-withheld emission to mates via the
addback. It costs ~0.04% of delivered dose — immaterial to the verdict; filed
as an open item only.

## Verdict

At `k = 6e-4` per copy the expected confined cabinmate SAR is **13.4%**
(mean per-slot `1−e^(−hazard)`, 4.6 expected secondaries over 34 slots);
observed confined attack is **7/34 = 20.6%** (6/28, 1/6) — inside the 15–25%
floor band. (That band is withdrawn: it was the norovirus Wikswo/Chimonas
pair reused generically — the corrected band is the declared-k expected-SAR
interval, `docs/confined_attack_floor_spec.md`, CABIN-FLOOR-03.) Expected
sits ~1.1× under the floor's lower edge, within Poisson
scatter of the observed count. The per-slot distribution is heavy-tailed:
median SAR ~3%, q90 ~50% — the mean is carried by long-overlap shedding
windows.

The paired defects therefore cancel at the floor for sourced reasons: the
under-delivery (~9e-6 capture) is real but is fully explained by declared
constants (confinement withholding ×0.05, droplet aerosol ef ×0.05,
partition/dilution, residence × presence), and the dose *window* — not a
constant — was the term that re-opened once k was corrected. No remaining
stage behaves unphysically; nothing here is a tuning target.

Open items for the literature/anchor sessions, not this PR: the aerosol-vs-
intranasal citation spread inside the k interval; the droplet route's use of
`DROPLET_AEROSOL_FRACTION = 0.05` rather than the profile's
`airborne_emission_fraction = 0.76` (pre-existing open item at
`_droplet_emission_fraction`); the HVAC/droplet confinement asymmetry above;
a distributional check on confined SAR's heavy tail before the anchor spec.

## Baseline gate

`tools/flu_confined_dose_probe.py` re-run on shipped k **before** any profile
change reproduced FLU-DOSE-01 exactly: 547 + 160 slots, medians 2.68 / 2.14
copies, observed 344/547 + 58/160 = 402/707 = **56.9%** pooled confined
attack.
