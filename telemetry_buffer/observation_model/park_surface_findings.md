# The Park et al. out-of-sample check: a split verdict

Harness: `telemetry_buffer/observation_model/park_surface_check.py`
Output: `telemetry_buffer/observation_model/park_surface_check_out.txt`

This is the first quantity this model has been compared against that it was
never fitted to, before or after the fomite correction. The result is neither
a pass nor a failure. The absolute contamination levels land inside the
observed ranges; the cabin-to-public gradient misses by a factor of 25–75 and
cannot be rescued by any occupancy assumption. Both halves are reported here
because both are informative, and the second one is the more useful.

## The comparison

Park GW et al. (2015, *Appl Environ Microbiol* 81:5987) swabbed a cruise ship
during a passenger gastroenteritis outbreak — same setting, same pathogen,
same physical quantity as the corrected `surface_pools`. 17 of 92 samples
positive, macrofoam swabs over 645–700 cm² at 1.2–36% recovery.

The prediction is a steady-state surface loading computed from the implemented
constants, reported across a range of shedder-hours per zone rather than at
one arbitrary occupancy, because occupancy is not something the check should
be allowed to choose freely.

| Zone | Scenario | copies / 645 cm² swab | Park observed | |
|---|---|---:|---|---|
| Cabin | sick passenger, confined | 1,434 | 80 – 31,217 | in range |
| Cabin | sick passenger, unconfined | 522 | 80 – 31,217 | in range |
| Public | 10 shedder-hours/day | 59 | 16 – 113 | in range |
| Public | 60 shedder-hours/day | 357 | 16 – 113 | 3× high |
| Public | 200 shedder-hours/day | 1,190 | 16 – 113 | 10× high |

## What passed, and how much credit it deserves

The absolute levels are right. A chain assembled entirely from independent
measurements — AuYeung's hand areas, Julian's transfer efficiencies, Rusin's
hand-to-mouth efficiency, Wilson's contact frequencies, Liu's hand load, and
a declared high-touch area — lands inside a range measured on a different
ship by different people for a different purpose, across both zone classes,
spanning about 1.5 orders of magnitude. Nothing was adjusted to make that
happen. For a model whose previous fomite route delivered 0.13 particles over
an entire voyage, that is a real result.

It deserves less credit than it first appears, and the reason should be stated
rather than left for someone else to notice. Shedder-hours per zone is a free
input to this calculation, and the public-space prediction slides from 59 to
1,190 copies/swab across a plausible range of it. So the honest claim is that
the emission scale is correct to within the tolerance of the check *at
plausible occupancy*, not that the model predicted the level. The check
constrains the chain to about a factor of 10; it does not pin it.

## What failed, and why it cannot be fixed by tuning

The gradient is the part of this check that occupancy cannot move, and it is
the part that fails.

Predicted cabin/public ratio: **4.0×**. Observed: **roughly 100–300×**.

The gradient is a ratio of deposition rates over high-touch areas, so the
shedder hand load, the transfer efficiencies and the emission scale all cancel
out of it. What survives is `(2 contacts/h ÷ 1.5 m²)` for a cabin against
`(6 contacts/h ÷ 6 m²)` for a public zone — a structural factor of 1.33 — times
the ratio of shedder-hours the two zones accumulate. Reaching 100× would
require a cabin to see **75× more shedder-hours than a public lounge**. A cabin
holds one or two people; a public zone during an outbreak is visited by dozens
of shedders. The real ratio runs the other way. So the gradient is not
reachable by hand-to-surface transfer at any occupancy, under any of the Grade
C declarations in §3 or §4 of the re-derivation, and no adjustment to those
declarations would change that.

That is the useful part of the result, because it is diagnostic rather than
merely negative.

## What the failure says

Park's sick-cabin swabs (up to 31,217 copies, against 113 at the top of the
public range) are not the signature of contaminated hands touching a door
handle. They are the signature of **direct emesis and faecal deposition in a
small bathroom** — a projectile vomiting event distributes on the order of
10⁷–10⁸ particles over a few square metres in seconds, and a cabin bathroom is
the one place in the ship where that happens and is not immediately cleaned.

The model has no such mechanism. Every route it has delivers pathogen through
hands, air, or food, at rates that are continuous in time and proportional to
shedding. A vomiting event is none of those: it is discrete, enormous, and
spatially concentrated in exactly the zone class where a sick passenger is
confined.

This is the same defect the A5 diagnosis found, seen from the other side. A5
asked why role structure cannot appear and found that the routes carrying it
deliver nothing. Park asks why sick cabins are not hotter than lounges and
finds that the model has no way to make them so. Both point at the absence of
concentrated, localised deposition.

## What this does and does not license

It does not license adding an emesis term tuned to reproduce 31,217
copies/swab, or to reproduce the passenger:crew ratio of 2.9. If an emesis
mechanism is built it needs the same standard as this chain: emitted volume,
particle concentration, spatial distribution and cleaning response, each with
a source, and then checked against Park rather than fitted to it.

It also does not license treating the absolute-level agreement as validation.
One check at factor-of-10 resolution, with occupancy free, is weak evidence
that the emission scale is not wildly wrong. It is not evidence that the model
is right, and it says nothing at all about attack rates, illness fraction, or
any of A1–A5.

The one thing it does establish is that the corrected fomite chain is now in
the right numerical territory to be worth testing, which the previous one — at
0.13 particles per voyage — was not.

## Note on an earlier number

An initial version of this check, run from a short transient rather than a
steady state and with a different occupancy, reported 20.5 copies/swab for
cabins and 15.4 for public spaces at a 1.33× gradient. Those figures are
superseded by the steady-state calculation above. The 1.33× in that run was
the structural factor alone, with the shedder-hour ratio at unity by
construction; the conclusion that the gradient fails is unchanged, and the
absolute levels in that run were transient rather than wrong.
