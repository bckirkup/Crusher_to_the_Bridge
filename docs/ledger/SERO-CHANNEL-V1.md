# SERO-CHANNEL-V1
**Date:** 2026-09-26
**Commit:** 20086708
**Pathogens:** sars_cov2_resp
**Status:** declared

The observational-channel arm of the ~18x conditional-size hunt, declared
in `picard_framework/runs/covid_sero_channel_v1_design.json` before any
cell ran. SENS-ASSAY-V1 measured the gap unreachable inside the
transmission layer (~4.7x over-burn x ~3.5x dated-onset bookkeeping);
this screen replays the LAMBDA-CROSS-V1 theta axis {1.0 ... 0.001} x
4.22e10 under two onset-recording channels — declared (every confirmed
symptomatic onset dated) and period (onset dated only if the host had
presented on or before the epoch of its confirming specimen, times a
once-per-case recall draw at 0.56, record-derivable as 197/712 / ~0.49
symptomatic-at-specimen) — x the same 20 seeds, 360 cells. The new
anchor, covid.H5 (serology-informed true infections ~840, admissible
band [712, 960] after Hung et al. 2020), is held out forever and scored
per row on `infections_total`, conditional on takeoff — never fitted
against.

The channel is additive and default-off (`observation_model.onset_recording`
on the pathogen profile, reached through the existing `pathogen_overrides`
deep-merge): absent the block, no code path changes and no RNG stream is
touched — onset draws run on a dedicated stream derived from the parent
SeedSequence entropy, so molecular and parent draws are structurally
unperturbed and the declared arm is expected bit-identical to pre-change
main. Validation gate on the PR: paired declared-vs-main payload equality
at matched seed on the new image, spec-lands read-back of the period
block, unit tests for the gate/draw/stream isolation.

Canary (per the bounded-research rule): the period arm at theta x0.001
only, cells 340-359, 20 seeds. Nothing in this entry is a result; it
moves to measured when the canary is read out. If the gate lands dating
far from ~0.28 of confirmed the declared fallback is the recall draw
alone without the symptomatic-at-specimen gate — declared before the
array, never after.
