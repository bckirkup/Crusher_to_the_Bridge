# PRESENT-SHARE-01
**Date:** 2026-10-01
**Commit:** #NNN
**Pathogens:** all
**Status:** measured
**Measured at:** a3c76061

The declared presentation probability — `symptomatic_fraction` on the
fixed-share profiles, the `illness_probability` Hill pair on the
dose-conditional ones — is a **share of courses**, and the schema states it
is "drawn once past incubation". The engine spent it as a **per-day
hazard**: `_advance_one_infection` re-rolled `draw_symptom_onset` at every
`crossed_day_boundary` while a course sat `NOT_ILL`, i.e. once per day of
natural history until shedding clearance (~15 draws on a 15-day shedding
curve). A share of 0.31 never-presenting becomes (1−0.31)^15 ≈ 10⁻⁸ —
effectively every infection presented within ~1.4 days of the incubation
crossing.

## Evidence

- Decomposed from `COVID-GM-RESCORE-01`'s H2 miss
  (`docs/ledger/COVID-GM-RESCORE-01.md`, measured `591d21b1`): the day-20
  screen found 2/112 positives unflagged on a hull whose profile share
  says ~31% never present. Expected from the residual mechanism alone:
  still-infected acquisitions on days ≥17 × tail assay sensitivity ≈ 2 —
  the presymptomatic tail, nothing else. The model did produce silent
  courses (~61% never-symptomatic on seed 20200205 under the flag-off
  read): it was the *presentation channel* that voided them, not the
  severity draw and not the specimen instrument.
- Profile exposure: `sars_cov2_resp` sf 0.69 and `influenza_a` sf 0.669
  (both fixed shares, Grade B) void entirely under the hazard —
  P(never present) ≈ 0. The `illness_probability` Hill arms
  (norwalk_gi, Edison roster, TNG/TOS) carry the same defect attenuated:
  high-dose hosts present on the first draw anyway, so the redraw mostly
  inflates the fitted low-dose tail — but their η/γ pair is also a
  measured share (Korkin challenge), not a per-day hazard.

## Change

`presentation_draw_mode` on the pathogen profile:
`once_per_course` (**shipped default** — the declared semantics; the draw
fires exactly once at the epoch crossing the host's own drawn incubation,
a failed draw stamps the course never-presenting via
`inf["presentation_drawn"]`) and `daily_hazard` (the labelled pre-change
baseline — bit-identical draw pattern and stream, no new stamp).
`will_present` forced courses are unaffected either way: the flag path
short-circuits inside `draw_symptom_onset` and consumed no stream before.
Validated in `tests/test_sim_clock.py` (one draw across 4 natural-history
days at 1h/6h/1-day epoch grains; `daily_hazard` restores the per-day
roll) and live-verified on the GM detector cell below.

## Repins (each attributed, AGENTS convention)

- `tests/test_illness_duration.py` inertness fingerprint + RNG cursor —
  moved by the mechanism itself: ~15 fewer shared-stream draws per
  infection reposition the cursor, and failed draws now keep the
  asymptomatic stamp so trajectory rows differ. The arm's own invariant
  (no stamp, no extra draw) is unaffected.
- `tests/test_covid_hull_change_detector.py` GM cell (Θ 1e10, seed
  20200333): `(2, 1, 217, 3, 0)` → `(2, 2, 217, 4, 1)` on CPython 3.12.
  `campaign_asymptomatic_positives` 0 → 1 is the intended direction on
  the pin that reads it. The `daily_hazard` flag-off cell reproduces
  `(2, 1, 217, 3, 0)` exactly on the same tree — the move is fully
  attributed to the share semantics. The 3.11 entry carries the same
  tuple pending its CI read, as prior near-extinct repins did.
- DP detector cell (same Θ/seed, slow tier): repinned in-file with the
  3.12 local read.

## Consequences (measured/inferred)

- Measured: every seeded golden that recorded a symptomatic trajectory
  post-incubation is re-rolled under the new stream; only the two
  detector families above pinned one.
- Inferred: the DP recorded-channel surplus (~10–18× vs the record's
  0.173 pre-quarantine share) plausibly sat in this defect — every
  infection presenting saturates recording. Re-score arrays ride the
  merged image; nothing here re-fits Θ or touches an anchor.
- Inferred: norwalk arms keep the Hill draw once per course — their
  measured P(ill|dose) curve is now spent as fitted rather than inflated
  by re-rolls; low-dose-tail composition moves, headline attack mostly
  does not (high-dose hosts presented on draw one before).

## Non-goals

No constant changed; `symptomatic_fraction`, `illness_probability`, the
severity and shedding blocks are untouched. No anchor re-scored in this
change — the GM/DP/noro re-reads are scheduled on the merged image.
