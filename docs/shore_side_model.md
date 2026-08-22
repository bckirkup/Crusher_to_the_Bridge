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
finite-horizon unbounded-growth regime.

The port detection epoch is derived from the existing port surveillance
capability and the canonical incubation projection from the active pathogen
profile. Active profile identifiers and the surveillance catalog's
public-health labels are not guaranteed to match, so the detection module
resolves the catalog label against the canonical profile name; that is a
translation, not a new surveillance parameter. Ascertainment is syndromic coverage times expected onsets; the
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
`port_surveillance_<region>.json` capabilities. `R_shore`, the shore
generation interval, residual importation fraction, and detection case
threshold are required caller-supplied scenario fields. `R_shore` and the
generation interval must be swept; they have no defaults. The outstanding
author item is the norovirus community-transmission citation. No citation or
literature value is invented here.

The model propagates the strain labels exported by the ship and makes no claim
about shore-side evolution. All strains share one shore parameter set;
per-strain, per-pathogen, and port-size-specific evolution is a later seam.
This package does not implement surface sampling, a Federation or port
network, or an economics layer.
