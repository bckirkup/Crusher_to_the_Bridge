# Shore-side transmission model

The shore layer is deterministic, pure NumPy post-processing. It is not a
second agent-based model and it does not alter the ship simulation.

## Ship interface

One `PortCallImportation` record supplies a port ID, pathogen ID, epoch length,
infectious disembarkations by epoch and opaque strain labels, plus the shipboard
detection epoch. An empty strain map is legal and produces zero cases. This is
the only coupling to the ship.

## Dynamics and counterfactual

Each strain is propagated through the same linear discrete renewal process:
the caller supplies `R_shore` and a lognormal shore generation interval, then
the canonical `renewal_incidence` recursion is applied. The model has no
susceptible depletion, so it is intended for cases small relative to the port
population. It reports an attack fraction and flags a depletion regime when
cumulative cases exceed 5% of that population. `R_shore >= 1` is reported as a
finite-horizon unbounded-growth regime. The central named scenario is
deliberately supercritical (`R_shore = 1.6`), so its `unbounded_growth` flag is
expected rather than a misconfiguration; on a sufficiently long horizon its
`depletion_regime` flag is expected as well. Results are interpretable only
while cumulative cases remain small relative to the port population.

The port detection epoch is derived from the existing port surveillance
capability and the canonical incubation projection from the active pathogen
profile. Active profile identifiers and the surveillance catalog's
public-health labels are not guaranteed to match, so the detection module
resolves the catalog label against the canonical profile name; that is a
translation, not a new surveillance parameter. Callers may instead provide an
explicit surveillance label when they have authoritative vocabulary mapping.
An unresolved non-empty catalog vocabulary raises an error: silently treating
that mismatch as no ascertainment would leave the port arm uncurtailed and
inflate the apparent benefit of shipboard detection. A label that does resolve
but is not covered by the programme is different and legitimately returns no
port detection. Ascertainment is syndromic coverage times expected onsets; the
profile's syndromic delay and, when applicable, laboratory turnaround are
converted to epochs. Detection is measured on the uncontrolled trajectory,
which is exact before detection because both counterfactual arms are identical
there.

The two arms differ only in importation curtailment: after shipboard detection
or port detection, respectively, imports are multiplied by the required
caller-supplied residual fraction. Benefit is port-arm cases minus ship-arm
cases; it is not clamped if negative.

`benefit_surface` reports the benefit over the cartesian product of the
`R_shore` grid and an importation multiplier grid. Because `R_shore` is
unanchored, the summary also reports how much of the answer that axis moves: a
coefficient of variation across the `R_shore` grid at fixed multiplier,
averaged over multipliers, for `benefit_fraction` and for the absolute arm
totals. Both are normalised by their own mean, since a raw standard deviation
of a dimensionless fraction is not comparable with one of case counts. On a
3x3 illustrative surface the relative benefit varies with a CV of 0.066 across
`R_shore` while the arm totals vary with a CV of 0.560, a ratio of 0.118.

`benefit_fraction` lies in `[0, 1]` whenever the ship detects no later than the
port. When the port detects first the benefit is negative and reported as
such, and the fraction (benefit divided by the smaller port-arm total) can fall
below -1; it is a ratio of two arms rather than a bounded score, and it is not
clamped.

## Anchoring and scope

Incubation is anchored to `active_profiles.json` through
`incubation_delay_for_profile`, and reporting delay is anchored to the bundled
`port_surveillance_<region>.json` capabilities. The opt-in
`NORWALK_GI_SHORE_SCENARIO` records the supplied norovirus generation interval:
the median and log spread cite Harris et al. 2014, while its eight-day
truncation is explicitly recorded as a modelling choice rather than attributed
to that paper. The scenario's `R_shore` range is now cited to Steele et al.
2020 and Gaythorpe et al. 2018, while 1.6 is explicitly flagged as an
author-selected judgement above the NORS median Re for a high-mixing port
catchment, not as a measured estimate; the previously outstanding community
transmission citation item is therefore closed for the range, while the
central value remains an author judgement. The environmental-dominated
`NORWALK_GI_ENVIRONMENTAL_SHORE_SCENARIO` records Heijne et al. 2009's 3.6-day
mean gamma-fit generation time as an approximation to the lognormal median
field; it is a sensitivity case, not a replacement or default. Residual
importation and detection case thresholds remain policy/scenario assumptions,
with semantics for every grid point recorded in machine-readable provenance.
The scenario module is not a default: `ShoreRenewalParameters`, the
counterfactual, and `benefit_surface` retain required caller-supplied values
and no value flows into those dynamics unless a caller opts into a named
scenario.

The model propagates the strain labels exported by the ship and makes no claim
about shore-side evolution. All strains share one shore parameter set;
per-strain, per-pathogen, and port-size-specific evolution is a later seam.
This package does not implement surface sampling, a Federation or port
network, or an economics layer.
