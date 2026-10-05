# NORO-SYMPTOM-COURSE-01
**Date:** 2026-10-05
**Commit:** 50bc52ab
**Pathogens:** norwalk_gi
**Status:** declared

## Question

The infected -> symptomatic-course link measures 0.12–0.19 against the
declared 0.6 on every hull measured (CHANNEL-03 `d6c51c14`,
MEGA-IMPACT-01 `7e1b54bc`). The decomposition readout
(`docs/norovirus/noro_symptom_course_01_decomposition.md`, `50bc52ab`)
splits the loss: ~66% the onboard presentation draw, ~22% the import
side (presented courses whose window sits off the voyage), ~13%
ramp-clipping (inferred [4%, 30%]). The shipped Hill realizes 0.234
presentation on clip-free acquisitions — below both sourced
`never_symptomatic_fraction` regimes. Does the funnel's first link move
when the onboard draw is armed at the declared regime points?

## Design (frozen in `docs/norovirus/noro_symptom_course_01_design.md`)

`symptomatic_fraction` profile patch on norwalk_gi at the two register
regimes — challenge {0.64, 0.71, 0.78}, community {0.32, 0.365, 0.41},
never pooled — plus the shipped Hill as the labelled baseline
(CHANNEL-04 dumps as the seed-paired baseline). Six cells (cls + spr,
scr-mid/scr-hi/ren) x 20 seeds on the unchanged CHANNEL-03 funnel
harness under a fresh `campaign/noro_symptom_course_01/` prefix; a
canary-gated mega witness (a1 spec, regime midpoints, 20 seeds) carries
the census decomposition at scale.

## Admissibility (frozen)

Identity closure per dump; presented/infected monotone in declared sf;
import side flat on sf arms (the patch must not touch boarding); acq
volume within 30%; onboard_ill >= 0.5 x presented; any violation is a
report-immediately trigger, not a patch-and-rerun.
