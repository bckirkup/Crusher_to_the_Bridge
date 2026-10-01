# Consensus tranche 52 — hand carriage: protected sites and own-environment re-loading

Evidence retrieved 2026-10-01 for NORO-HAND-CARRIAGE-01, the second
repair pass on the hand reservoir after the PRACTICE-01 census verdict
(`still_starved`, R = 0.111). Questions: where on the hand does carriage
survive a wash, and what does routine re-loading actually touch.

## 1. Subungual and crease sites — the wash-resistant compartment

**Lin et al. 2003**, *J Food Prot* 66(12):2296–2301,
DOI 10.4315/0362-028x-66.12.2296 — "Comparison of hand washing
efficiencies in removing fecal coliforms and feline calicivirus (FCV,
a norovirus surrogate) from hands". The subungual region — beneath the
nail — **harbors the most microorganisms and is the most difficult
area of the hand to clean**. FCV persisted beneath both natural and
artificial nails through every hand-washing method except soap +
nailbrush; fingernail region recovery exceeded palm/finger sites by
orders. Also read: washing *without* thorough drying can transfer more
virus than it removes in the same act (transfer to a touched surface
from wet hands ~2 log10 higher than dry).

**Walaszek et al. 2018**, *J Hosp Infect*, DOI
10.1016/j.jhin.2018.06.023 — bacterial colonization beneath fingernails
persists after alcohol-based hand disinfection; subungual material is
sheltered even under healthcare-grade rubs.

→ Mechanism basis (Grade B) for `hand_protected_load_by_pathogen`: a
compartment that wash efficacy cannot reach is measured, not invented.
Magnitude bounded by Liu 2013's own post-bathroom arm (12.4% of rinses
still ≥ 2.30 log10 after visit + wash) — `HAND_PROTECTED_SEQUESTER_GEC_RANGE`.

## 2. Recontamination opportunity rate — why the source cannot stay a 2–8/day tick

**Alonso et al. 2013**, *Clin Infect Dis* 57(9):1333, DOI
10.1093/cid/cis961 — cohort touch diary/instrumented study: subjects
touched common environmental surfaces ~**3.3 times/hour** and their own
mouth/nose ~**3.6 times/hour** — ~7 recontamination opportunities per
waking hour versus a wash frequency of order 0.1–0.5/hour. Even after
the routine source is confined to the host's own contaminated
fittings, a 2–8/day tick rate is the conservative floor; it is kept
but now multiplies a real standing pool.

**Zhao et al. 2025**, *Environ Sci Technol*, DOI
10.1021/acs.est.5c03147 — own-home surface→hand recirculation measured
in situ: residents' own rooms are the dominant within-person
re-inoculation reservoir, supporting the own-environment pool (own
cabin compartment / home zone) rather than deck-wide shared pools as
the routine source.

→ `hand_self_pool_by_pathogen` credited by `_credit_own_environment_pool`,
decaying at the profile's `_surface_survival` rate; ticks draw a
measured `SURFACE_TO_HAND_LOGNORMAL` fraction of the standing pool —
no new uptake constant.

## 3. What was NOT retrieved

- No dedicated under-nail viral *survival/inactivation* series —
  `HAND_PROTECTED_INACTIVATION_PER_HOUR_RANGE` stays declared Grade C,
  an order below the fingertip-pad rate.
- No shipboard hand-occupancy series — Liu 2013's 25.4% occupancy
  anchor remains the only measured baseline; the model's own pool is a
  structural analogue of Zhao's own-home finding, not a fitted term.
