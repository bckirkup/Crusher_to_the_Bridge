# NORO-TOUCH-SHARE-02
**Date:** 2026-09-24
**Commit:** 56eaa0e
**Pathogens:** norwalk_gi
**Status:** declared

A two-seed epoch-lockstep probe of the `per_surface + areal` (A) versus
`per_surface + declared` (D) fomite arms measured in `NORO-TOUCH-SHARE-01`,
answering one question: **at the first epoch where the two arms' RNG
streams differ, what caused the divergence?** §§0–3 are frozen before either
seed runs; §4 is filled only from the probe output; §5 states what is
inferred and what remains hypothesis. Every mass or dose-like quantity
quoted here is a paired, relative witness read from two arms of the same
seed — never a dose result (`../norovirus/norovirus_open_ledger.md` §1).
Nothing is adopted: `pooled` stays the default; the declared table and its
grades are untouched; no constant moves.

## 0. Settled inputs (quoted, not re-derived)

- **`NORO-TOUCH-SHARE-01`** (#666/#667, measured `3a54ad3`, seeds
  8000–8019, 288 epochs, `classic_cruise_1900`, `norwalk_gi`): A is
  bit-identical to #664 (`NORO-FOMITE-DISAGG-01`). The §4 rule fired
  `changes_coincidence` (median Jaccard 0.787), but deposit event streams
  stayed aligned on only 3/20 seeds (Jaccard ≈ 1.0 there); median
  `hand_to_mouth_calls` 4934.5 (A) → 11836.5 (D) with fewer deposits
  (26.5 → 24.5). Its §5.6 hypothesis — the D-arm divergence is real
  reallocation dynamics, not an RNG-stream disruption — is what is tested.
  Seed 8001 is one of the three aligned seeds; seed 8000 diverged.
- **`NORO-FOMITE-DISAGG-01`** §6.1 (measured `622f99f`): the archetype. A
  `<= 0` / empty / cap gate evaluated on a floating-point residue
  (|mass| ~ 1e-13 GEC) is taken differently by two algebraically equivalent
  arms, changing the *count* of downstream RNG draws and so the whole
  stream. Its fix — the exact-empty pattern (`if scale < 1.0:
  delivered_total = surface_mass`, per-class analogue in
  `_deliver_fomite_requests_by_class`) — is already on the default path.
  Its method — step two arms epoch by epoch under one process and compare
  RNG state after each epoch — is reused here.
- **Instrument seam:** `tools/noro_diag/per_host_dose_challenge.py`
  (`build_spec`, the read-only `instrumented()` wrappers). The declared
  table is the JSON shipped in #666.

## 1. Question and frozen classification rule

For each seed s ∈ {8001, 8000}, arms A and D are stepped in lockstep from
the same `ShipSimulation` seed for 288 epochs. After every epoch the root
`Generator` bit-state and the ordered per-epoch draw sequence (method,
argument shape, calling engine context) are compared.

**First divergence epoch** e* = the first epoch whose draw sequence (or,
if sequences are equal, whose bit-state) differs. Before e* both arms
must have identical cumulative event-stream counts (deposit calls,
per-class pickup requests, deliveries, `hand_to_mouth_calls`, challenge
resolutions); an inequality before e* is itself a finding (§1 class c).

The **first differing draw** d* is the first index in epoch e* at which
the two sequences differ (a differing method, a differing call context, or
one arm having a draw the other does not). Its cause is classified as
exactly one of:

- **(a) expected.** d* is issued from a fomite pickup / deposition /
  hand-to-mouth event whose *occurrence or argument* depends on a
  delivered, held or surface mass that legitimately differs between arms
  because D reallocates mass among item classes. Evidence required: the
  event, zone, item class, and the two masses — both with
  |mass| ≥ 1e-12 GEC, or one exactly 0.0 and the other ≥ 1e-12 GEC with
  the zero traceable to a class the declared table assigns share 0 or to a
  class whose mass was fully consumed (an exact zero, not a residue).
- **(b) archetype.** d* is issued (or omitted) because a `<= 0` / empty /
  cap gate — `surface_mass <= 0` (zone skip), `delivered <= 0.0`,
  `hand_load <= 0.0`, `_delivery_scale` cap, per-class empty — was taken
  differently on a quantity that in at least one arm is a floating-point
  residue: 0 < |value| < **1e-12 GEC** (frozen threshold; analogous
  quantities such as hand load use the same threshold in GEC). Evidence
  required: the gate and the two values.
- **(c) other.** Anything else; the mechanism is stated in §4.

**Verdict rule (frozen).** The archetype is ruled out for this pair iff
both seeds classify (a). Any (b) is an implementation defect and is
reported immediately; it is fixed in this session only if the fix is the
§6.1 exact-empty pattern, in which case it is labelled a default-path
change and the probe is re-run. Any (c) is reported immediately.

**Ordering witness (frozen).** Per seed, the probe records the epoch and
draw index of the first D-arm per-class pickup whose delivered mass
differs from A's by more than 1e-9 relative (both ≥ 1e-12 GEC). If d*
precedes that pickup, the share table changes something upstream of
pickup and this is reported immediately regardless of class.

## 2. Instrument (read-only)

`tools/noro_diag/touch_share_lockstep_probe.py`:

- Two `ShipSimulation`s per seed built from
  `per_host_dose_challenge.build_spec` (A: `per_surface`, `areal`,
  `shipped`; D: `per_surface`, `declared`, `shipped`, the #666 table).
- Each arm's root `rng` is replaced, before `initialize()`, by a tracing
  proxy that forwards every call unchanged to the real
  `numpy.random.Generator` and appends `(context, method, arg-shape)` to
  the arm's current-epoch trace. It consumes no randomness and changes no
  return value.
- Engine context is supplied by wrapping (not replacing) the same
  `TransmissionCore` methods `per_host_dose_challenge.instrumented()`
  already wraps, plus `_fomite_pickup_by_class`, `_deliver_one_pickup`,
  `_consume_surface_mass(_by_class)` and `_resolve_pathogen_challenge`;
  wrappers set the active context, count the event, record masses, and
  call the original with the original arguments.
- At the start of every epoch each arm's per-zone surface pool mass and,
  for the per-surface arm, per-(zone, class) mass are snapshotted
  (read-only from `TransmissionCore` state). Both arms are stepped one
  epoch, then compared; the comparison never feeds back into either arm.
- Cumulative `hand_to_mouth_calls` (all three call sites: pooled/per-class
  pickup, emesis patch, hand contact) are recorded per epoch for both arms
  for all 288 epochs, so the -01 "doubling with fewer deposits" observation
  can be placed before or after e*.
- Output is deterministic JSON; CLI-derived output paths go through the
  `_safe_path` pattern (Sonar S8707).
- `tests/test_touch_share_lockstep_probe.py` proves that the pooled default
  is bit-identical (root RNG state, surface pools, hand loads) with the
  instrument attached versus detached.

## 3. Non-goals

Larger seed blocks; AWS; changing the declared table or its grades; adding
event alignment to the -01 §4 rule (successor's job — see §5.3); adopting
`per_surface` or `declared`; whole-voyage dose interpretation; cleaning
policy; `derived` area basis.

## 4. Measured

*(filled only from the probe output; empty while `Status: declared`)*

## 5. Inferred / hypothesis / next decision

*(filled after §4)*
