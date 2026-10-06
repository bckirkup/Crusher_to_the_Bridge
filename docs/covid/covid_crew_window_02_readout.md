# CREW-WINDOW-02 fractional/activity-scoped crew duty — CHANNEL-LANDED on the fractional axis (FRAC_25, ZONE_NARROW @Θ7.9e6)

> **Status:** Findings (2026-10-06). Campaign measured at `2df542ff`
> (image `picard-campaign@sha256:2b481866` / tag `covid-crew-window-02`,
> jobdef `picard-covid-crew-window-02`, queue `picard-analysis-queue`,
> S3 prefix `campaign/covid_crew_window_02/`). Spec and readout under
> `campaigns/covid/crew_window_02/`, design
> `picard_framework/runs/covid_crew_window_02_design.json` (frozen
> pre-run, verdict grammar carried verbatim from CW-01).

CW-01 measured only the corners of the crew-duty axis (verdict
CLIFF-STRUCTURE) because the DP hull instantiates only
`passenger_general` + `crew_general`. CW-02 opened the interior: two
new confinement-order modifiers — `exempt_work_zones` (postable-zone
lists NARROW 11/34, WIDE 19/34) and `exempt_fraction` (sticky
exact-count draws 261/523/784 of 1,045 crew) — carried by five new
SOP-017 protocol variants.

240/240 cells, 0 child failures across 12 20-child arrays. Canary
(ZONE_WIDE @7.9e6, 20 seeds) read out and reported before the full
array submitted.

## Result (takeoff-conditional medians, n≈19 takeoff seeds per row)

| θ | arm | during med | before med | Δbefore | crew share | realized exempt | min deliveries | verdict |
|---|---|---:|---:|---:|---:|---:|---:|---|
| 1e6 | D0_declared | 601.0 | 37.5 | 0.0 / 0.0 | 1.000 | 0.984 | 127935 | BASELINE |
| 1e6 | FRAC_25 | 195.0 | 37.5 | 0.0 / 0.0 | 1.000 | 0.245 | 165567 | IN-BAND-INCOMPLETE |
| 1e6 | FRAC_50 | 315.0 | 37.5 | 0.0 / 0.0 | 1.000 | 0.494 | 152991 | IN-BAND-INCOMPLETE |
| 1e6 | FRAC_75 | 485.0 | 37.5 | 0.0 / 0.0 | 1.000 | 0.737 | 140463 | UNDER-ATTENUATED |
| 1e6 | ZONE_NARROW | 238.0 | 37.5 | 0.0 / 0.0 | 1.000 | 0.312 | 161505 | IN-BAND-INCOMPLETE |
| 1e6 | ZONE_WIDE | 377.0 | 37.5 | 0.0 / 0.0 | 1.000 | 0.548 | 149343 | UNDER-ATTENUATED |
| 7.9e6 | D0_declared | 739.0 | 126.0 | 0.0 / 0.0 | 0.992 | 0.964 | 127935 | BASELINE |
| 7.9e6 | FRAC_25 | **301.0** | 126.0 | 0.0 / 0.0 | 0.973 | 0.242 | 165567 | **CHANNEL-LANDED** |
| 7.9e6 | FRAC_50 | 487.0 | 126.0 | 0.0 / 0.0 | 0.986 | 0.482 | 152991 | UNDER-ATTENUATED |
| 7.9e6 | FRAC_75 | 632.0 | 126.0 | 0.0 / 0.0 | 0.989 | 0.722 | 140463 | UNDER-ATTENUATED |
| 7.9e6 | ZONE_NARROW | **336.0** | 126.0 | 0.0 / 0.0 | 0.978 | 0.307 | 161631 | **CHANNEL-LANDED** |
| 7.9e6 | ZONE_WIDE | 504.0 | 126.0 | 0.0 / 0.0 | 0.986 | 0.540 | 149343 | UNDER-ATTENUATED |

Record-informed band [150, 350] (context only); record crew share
0.29. Reach echoes audited before the median read.

## What was measured

- **The fractional axis lands the band.** FRAC_25 (75% of crew
  confined at order activation) → during median 301 @7.9e6; ZONE_NARROW
  (only essential-posted crew working) → 334. Both with the before
  phase seed-paired unmoved (Δ0.0 vs in-design D0). The CW-01 cliff was
  the class vocabulary, not the channel: the channel has an interior.
- **Crew share moves only marginally** — 0.973/0.978 vs D0's 0.992
  (record 0.29). Confining crew attenuates the during-window mass but
  the residual infections stay crew-on-crew: confined crew still eat
  via R3 steward cabin delivery (`service_deliveries` 128k–166k/cell,
  no starvation), and steward contact + cabin adjacency keep the route
  open. CHANNEL-LANDED on the grammar's letter (share moved), nowhere
  near the record's share.
- **Monotone in the confinement dose, as designed:** during medians
  rise with realized exempt share at both thetas (7.9e6: 0.242→301,
  0.307→336, 0.482→487, 0.540→504, 0.722→632, 0.964→739). A ~0.25–0.31
  working share brackets the band's interior; ~0.5+ sits above it.
- **At Θ1e6 the band lands but the share never moves** (1.000 on every
  row) — IN-BAND-INCOMPLETE on FRAC_25/FRAC_50/ZONE_NARROW. The
  passenger contribution at low theta is already negligible; confining
  crew cannot shift attribution that was never there.
- **Realized shares track declarations.** FRAC drawn counts exactly
  261/523/784 on every cell (dedicated RNG stream, recorded per order);
  ZONE realized 0.31/0.54 vs posted-conditioned lottery 0.32/0.56
  (realized denominates all 1,045 crew; ~84% carry postings) — no
  material departure. Working crew are inside the essential list on
  every ZONE cell.
- **CW-01 drift witness clean:** in-design D0 pairs seed-for-seed
  against CW-01 D0 at median paired delta **0.0** on both thetas — the
  replay is bit-stable at the merged SHA.

## Frozen-invariant departures (reported, not amended)

`realized_exempt_share ≈1` on D0 flagged 4 cells: 0.68–0.87 on seeds
20200208 (@7.9e6: 0.678; @1e6: 0.863), 20200205 (0.849), 20200221
(0.870). Attribution: on the big before-phase seeds (e.g. 20200208,
2,252 before infections) symptomatic crew are already confined through
the isolation path when the order fires — D0 exempts crew from the
order's confinement gate, not from symptomatic isolation. The gate
itself provably reached (D0 cells carry no gate echo; CW-01 pairing
Δ0.0). The frozen "≈1" expectation did not account for isolation-path
confinement on big seeds; left as flagged rather than edited post-hoc.

**OPEN ITEM (unruled):** whether `≈1` was ever physical on big
before-phase seeds — the isolation path confines symptomatic crew
independently of the order gate on every arm, so a D0 realized share
<1 is expected physics, not a gate failure. Awaiting owner decision:
amend the frozen expectation (≈1 except where isolation has already
confined) or keep it as a strict witness.

## Campaign mechanics

- Design frozen before any cell ran; verdict grammar verbatim from
  CW-01 (CHANNEL-LANDED / UNDER-ATTENUATED / OVER-ATTENUATED / UNMOVED;
  IN-BAND-INCOMPLETE when in-band without the share clause).
- Readout-tool defects found and fixed during the campaign (landed
  with this readout): falsy-zero `.get(...) or -1` on
  `settled_share=0.0` and `confined_crew_count=0` produced spurious
  audit flags; `_CW1_PREFIX` default lacked the `s3://` bucket scheme.
- Ops detail (image digest, jobdef revisions, array job ids, canary
  record): `campaigns/covid/crew_window_02/LEDGER.md`.
