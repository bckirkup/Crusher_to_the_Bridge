# CONTAM-EXPOSURE-TAGGING-01
**Date:** 2026-11-16
**Commit:** 20680d0f
**Pathogens:** all
**Status:** measured
**Measured at:** 20680d0f

## Scope

Owner rulings (Benjamin, 2026-11-16, verbatim): "The Greg Mortimer is for
Antarctic cruises. the bars are enclosed. I have pictures with the HVAC. The
exterior promenades on diamond princess are open to the sea." Correction,
same day, verbatim: "PromGalleria is NOT weather. ... The open-to-sea
promenade he was remembering is `OceanFront` ... which ALREADY has
`exposure: "weather"` ... do not touch it." Indoor-reading confirmation,
same day, verbatim: "These are specifically indoor spaces".

This entry applies only D7(b) `exposure` declarations. It adds no
`ambient_openings`, changes no `flow_rate_m3h`, no `envelope_leak.area_m2`,
and no exporter constant. Base `origin/main`
`605f9841932251b134683ba651f6cfa2d49ec41f`.

## Changes

- `greg_mortimer`: `BarsDeck5`, `BarsDeck8`, `ObsDeck7`, `ObsDeck8` declare
  `exposure: "enclosed"` (Antarctic-cruise bars/observation spaces, HVAC
  pictures in hand). No openings.
- `diamond_princess`: `PromGalleria` declares `exposure: "enclosed"` — the
  indoor duty-free shopping galleria on Deck 7, AHU_Public_Mid-served. The
  open-to-sea `OceanFront` promenade is untouched. No openings.
- `classic_cruise_1900` `Promenade`, `spirit_cruise_3000` `Promenade`, and
  `mega_cruise_5000` `Royal_Promenade` declare `exposure: "enclosed"` under
  the owner's indoor-reading confirmation. No openings.

## Hull-audit before/after

`tools/hull_audit.py` JSON for the five touched hulls is identical before and
after (`classic_cruise_1900`, `diamond_princess`, `greg_mortimer`,
`mega_cruise_5000`, `spirit_cruise_3000`): every tagged zone is AHU-grouped,
so the CLI's ungrouped census and metrics do not reclassify it. The
authored-exposure inventory (`tools.hull_audit._is_exterior`) moves only for
the four Greg Mortimer bars:

| Hull | Before | After | Move |
|---|---:|---:|---|
| `classic_cruise_1900` | 1 | 1 | none; `Promenade` was already non-exterior, now explicitly enclosed |
| `diamond_princess` | 8 | 8 | none; `PromGalleria` was already non-exterior, now explicitly enclosed |
| `greg_mortimer` | 9 | 5 | `BarsDeck5`, `BarsDeck8`, `ObsDeck7`, `ObsDeck8` leave |
| `mega_cruise_5000` | 5 | 5 | none; `Royal_Promenade` was already non-exterior, now explicitly enclosed |
| `spirit_cruise_3000` | 3 | 3 | none; `Promenade` was already non-exterior, now explicitly enclosed |

No other zone moved on any touched hull.

## Bundles

The exposure field is not read by the native bridge or the ContamW exporter.
Base export reproduced first: regenerating the five commissioned bundles
before the edits produced no `contam/` diff. After the tags, the same
regeneration again produced no `contam/` diff (`git diff --exit-code --
'data/platforms/*/contam'` clean), so no bundle was regenerated or committed.

## Residuals

- `exposure: "enclosed"` is an authored declaration read by
  `tools/hull_audit.py`; it does not itself change transport. The four Greg
  bars leave the lexical exterior inventory; the other four spaces were
  already inside the classifier's indoor reading and are now explicit.
- `OceanFront` remains the Diamond Princess open-to-sea weather opening from
  CONTAM-AMBIENT-WEATHER-CRUISE-01; classic/spirit/mega balcony and weather
  openings are unchanged.
