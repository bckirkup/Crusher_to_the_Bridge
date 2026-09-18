# AERO-NEAR-02
**Date:** 2026-09-18
**Commit:** 9c1ed81
**Pathogens:** all
**Status:** open

## Defect

The former continuous near-field route used a retained-fraction and assumed
unit-volume parameterisation. It could not identify the near/far exchange, and
the model had no per-meal seating unit for buffet or crew-mess diners.

## Declaration

The shipped declaration is `transmission.near_field_air.mode: two_box`, with
interzonal airflow β = 204 m³/h and neighbouring-table ratio ρ = 0.43.
β is a declared swept axis from 24–1,140 m³/h, not a fitted campaign constant.
The far-field pool and its mass are unchanged. Buffet and crew-mess diners are
dealt into random tables at every meal epoch, with cabin bookings kept
together, on-duty service staff excluded, and the default table size applied.
Fixed MDR and specialty seating is unchanged.

β is Keil et al. 2017 (DOI 10.1080/15459624.2017.1334903), Grade B,
Origin: Abstract + Results. ρ is the 0.40–0.47 analogous-setting envelope in
Li et al. 2021, Table 3, Grade B, Origin: T3. Background air-speed and
near-field extent context are recorded in `docs/near_field_air_spec.md` §11.
Serving-line queue exposure and cruise-dining-table β remain open omissions.

The COVID change detector moved from `(81, 42, 217, 88, 11)` to
`(64, 8, 217, 67, 36)` on CPython 3.11 and to
`(51, 8, 217, 51, 32)` on local CPython 3.12. These moves are attributed to
the default β near-field dose and the additional RNG consumption from
per-meal buffet/crew-mess table dealing. The CPython 3.11 reading was read
from the CI job (fast tier, 3.11) on this branch.
