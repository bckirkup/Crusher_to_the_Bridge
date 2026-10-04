# NORO-ONSET-CURVE-01 — acquisition/onset clustering instrument

Status: measured — 2026-10-04, readout `noro_onset_curve_01_readout.md`, ledger `docs/ledger/NORO-ONSET-CURVE-01.md`. Instrument `tools/noro_diag/onset_curve_readout.py` on existing campaign zips; no campaign, no engine change in v1.

## Question

Are voyage outbreaks *propagated* (exponential, dispersed case times) or
*point-source-like* (cases clustered nearly simultaneously)? Real posted
norovirus outbreaks present the point-source signature: a burst of onsets inside
~one incubation window (24–48 h) followed by a declining tail, distinct from a
smooth exponential ramp even when cumulative counts look alike. OUTBREAK-01/02/03/04
progression tables show the opposite shape — onset med ~0, "peak" at epoch
~270–286 of 288 (accumulation at voyage end, never a crest). This instrument
measures the *distribution* that verdict rests on.

## Input

- Hot campaign zips (not yet lifecycle-archived): `campaign/noro_outbreak_02/`,
  `noro_outbreak_03/`, `noro_outbreak_04/`, `noro_mega_01/`.
- Member `growth_census.json.gz`: per-host `epoch_acquired` (present on every
  infected host), `symptomatic_epochs`, `confined_epochs`, `vomiting_axis`,
  `dominant_pathway`, `gen`. Member `summary.json`: voyage aggregates
  (`cumulative_reported_cases*`, complements, `derived.*` epochs).
- Decode path: zip member is DEFLATE inside the zip → gzip stream inside;
  two-stage decompress (`zlib -15` then `wbits=31`), ranged member reads via
  `tools/noro_diag/outbreak_anchor_readout._s3_member_blob`.

## Metrics (per voyage)

From `epoch_acquired` over infected hosts (acquisition-time distribution —
the upstream signature of common-source dosing):

- `burst_24`, `burst_48`: max fraction of acquisitions inside any rolling
  W-epoch window (point-source signature → near 1.0).
- `peak_window_center`: epoch at the centre of the densest 48-epoch window,
  reported relative to voyage midpoint and to `num_epochs` (end-bias test).
- Acquisition-histogram concentration (share of acquisitions in the densest
  decile of the voyage span).
- Same metrics restricted to symptomatic hosts (`symptomatic_epochs > 0`) —
  the *visible* epidemic's timing shape.
- Implied onset curve: acquisition histogram convolved with the declared
  incubation law → implied symptom-onset histogram (inferred; see emit gap).

## Cell-level aggregates

- Median [IQR] of `burst_24`/`burst_48` per cell; share of voyages with
  `burst_48 > 0.5` ("spiky" share).
- Median `peak_window_center / num_epochs` per cell (> ~0.9 = end-smeared;
  0.3–0.6 = mid-voyage burst, the real-posting shape).
- Cross-cut by `took_off` and by posted/unposted (does posting correlate with
  clustered acquisition?).

## Emit gap (flagged for next image)

`epoch_acquired` is serialized; **per-case symptom-onset epoch is not**
(`symptomatic_epochs` is a count). The implied-onset convolution stands in for
v1. One-line census addition for a future image: `epoch_symptomatic_onset`
(and optionally `epoch_reported`) per host — then the observable-side curve
(what VSP sees) is measured directly.

## Comparator

Real-side expectation is qualitative (point-source noro curves in the
literature: onset cluster inside 1–2 incubation periods, occasional secondary
shoulder) — inferred, not a committed anchor. The discriminating read is
model-internal: if acquisitions disperse across the voyage, no common-source
mechanism is active at observable rates; if a cluster exists, something
already produces synchronized dosing.

## Deliverable

`tools/noro_diag/onset_curve_readout.py` + committed readout table
(`docs/norovirus/noro_onset_curve_01_readout.md`): per-cell burst metrics,
spiky share, peak-window location, symptomatic-cohort curves. Runs locally
against ranged GETs; no fleet, no image build.
