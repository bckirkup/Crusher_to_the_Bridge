# NORO-TOUCH-PATCH-01
**Date:** 2026-11-23
**Commit:** 8a698da7
**Pathogens:** norwalk_gi
**Status:** measured (canary, 20 of 22 cells)

TOUCH-PATCH canary per `docs/norovirus/fomite_touch_patch_spec.md`
(PR #1401), implementation PR #1403. NORO-POOL-PICKUP-01 measured that
ordinary fomite encounters *request* ~0 (0–4k GEC delivered per cold
cell) under every solver arm — the deficit was upstream of delivery,
in encounter/request structure. This arm restructures the request
itself: `fomite_representation: item_instances` puts deposited mass
on the discrete items each touch samples, and pickups sample one
reachable instance per touch at that instance's areal density.

## Frozen decision criteria (campaigns/noro/noro_touch_patch_01/LEDGER.md)

- Hot-cell floor: min Σhazard among D0′ take-off cells = 1.1 (seed
  8105; D0′ hot cells 8000: 31.0, 8006: 146.0, 8105: 1.1).
- Previously-cold canary cells: 18 of 20 (8000, 8006 took off under
  the baseline; 8105/8106 held for the full-campaign decision).
- **Ignites :=** ≥9 of 18 previously-cold cells reach Σhazard ≥ 1.1.

## Result — canary, seeds 8000–8019 (Measured at: 8a698da7)

Batch array `ff4673b5-20f0-4196-b177-945580d8cf4a`, jobdef
`picard-noro-touch-patch-01:3`, image
`sha256:946ef435cb8e70516d53ed00c3612af51df4f58c98b1d2efc65b434bc4cd8217`,
288 epochs. All 20 artifacts passed the frozen audit (len-288 ledgers,
four reconciliations ≤1e-9, Σinstance_mass == surface_pools drift 0.0,
`fomite_representation_resolved: item_instances`, solver resolved
discrete vs configured continuous).

- **The mechanism fired.** Instance witness per cell: 0.1–6.6M touches
  sampling items, 8k–1.5M contaminated touches, 3k–58k coincident
  deliveries (distinct susceptibles on one contaminated instance —
  the co-location count the spec wanted), 51–2850 contaminated
  instances.
- **Requests rose.** Discrete requests on cold cells: 0.1k–1.1M GEC
  (vs ~0–4k baseline delivered ceiling). Non-patch delivered mass
  reached hands on 16 of 18 cold cells — up to 12.4k GEC (8014).
- **Take-off did not cross the gate:** 2/18 cold cells ≥1.1 Σhazard
  (8008: 2.27, 8018: 1.39) — below the required 9.
- **The waterfall moved downstream.** Mouth dose stayed ~1–4% of
  delivered mass on every cell (e.g. 8018: 2.25M delivered → 26.3k
  mouth; 8014: 23.8k → 301) — the hand reservoir still sheds
  ~96–99% of delivered mass to wash/decay before swallowing, and
  hazard converts at mouth dose, not delivered.

## Verdict under the frozen rules

**Requests rose but take-off does not** — spec §6 second arm: item
encounters deliver ordinary-fomite mass to hands, but the
hand-reservoir → mouth → challenge stage still strands it. The
binding stage has moved downstream of delivery entirely; report the
waterfall, change nothing else.

Caveats (recorded, not attributed): both crossing cells are
patch-dominated (8008: 1.7k of 299k delivered non-patch; 8018: 3.8k
of 2.25M) so their hazard is largely food-burst driven; ordinary-
instance delivery contributes mass but did not produce new hot cells.
Two cold cells (8004, 8011) sampled zero/one instance touches at all —
their voyage realized almost no ordinary-fomite contact structure.

## Consequence

D2′′ question for the next proposal: the mouth/hand-reservoir
conversion (~4% delivered → mouth, ~99% shed to wash/decay) is now
the measured binding stage. Candidate levers live there (mouth-touch
frequency, hand-reservoir retention, swallow efficiency) — or the
challenge floor itself. D1′ (carrier donor eligibility) and D3′
(rhythm A/B) remain parked.
