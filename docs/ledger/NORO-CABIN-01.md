# NORO-CABIN-01
**Date:** 2026-09-26
**Commit:** b49a3ec2b0df4a94a9a2ab0c618838d292c5cf8d
**Pathogens:** norwalk_gi
**Status:** measured
**Measured at:** b49a3ec2b0df4a94a9a2ab0c618838d292c5cf8d

(The mechanism is pathogen-agnostic; the instrument arm was measured on
the classic_cruise_1900 voyage with norwalk_gi + influenza_a boarding.)

Confined cabin-mate pairs now exchange fomite dose through **their own
stateroom's pool**. Before this change the fomite chain was dead-coded at
both ends under confinement: `_shedder_surface_deposits` skipped confined
shedders, so a quarantined index never loaded the fittings it actually
touches, and `_fomite_pickup_request_for_area` /
`_fomite_pickup_requests_by_class` returned zero/None for every confined
target — which also dead-ended emesis-patch floor pickup, since patch
delivery flows through the same request. The literature channel for
confined-mate noro (shared-bathroom/own-fittings fomite) was therefore a
structural null *twice over*: pool-scoped wrong for the pair AND blanket
gated.

Channel map for a confined cabin-mate pair, measured at this change's
parent (`fdca3020`):

| channel | pre-change state | per-pair delivery |
|---|---|---|
| direct contact (hand-to-hand / shared-room) | compartment-scoped | live |
| emesis aerosol | compartment-scoped | live |
| flush aerosol (`_dose_flush_cabin`, venue = compartment key) | compartment-scoped | live path; see below |
| HVAC-downstream (emesis-conditioned entrainment) | compartment air unit | live |
| fomite pool + emesis patch | dead-coded under confinement | **this change** |

Mechanics (`transmission.cabin_confined_fomite`, default `"own_cabin"`;
`"off"` kept as the labelled bit-identical baseline for paired-seed
attribution, restoring the pre-change blanket gate):

- A confined agent deposits to and picks up from the pool at its current
  compartment key — by construction the pair's own stateroom
  (`{zone}::cabin{min(member ids)}`, which
  `_update_prev_occupancy` snapshots so trailing pickup resolves there).
  Corridor, sanitary and every other zone pool stay gated for confined
  agents exactly as before.
- Deposit and pickup requests scale by the deterministic
  `_cabin_presence_share` (1 − `confined_absence_hours_per_day`/awake
  hours for confined awake epochs, 1.0 otherwise — the CABIN-OCC-01
  partition, no draws).
- Every new draw lands on a dedicated stream,
  `self._cabin_fomite_rng`, spawned once from the shared generator's
  SeedSequence at init (spawn consumes no bit-generator draws). The
  shared stream sees the identical draw sequence in both arms until the
  first *realised* dose difference — i.e. `off` is bit-identical to the
  pre-change baseline, and `own_cabin` adds only dose-triggered draws
  (the delivered-dose susceptibility draw itself). No constant in this
  change was chosen to hit a target; the gate adds no new parameters —
  existence of the channel is Grade B (documented confined-mate
  transmission via shared bathroom/fittings), magnitudes are measured by
  the instrument below.

Instrument: `CabinPairChallengeLedger` +
`tools/noro_diag/cabin_pair_challenge_probe.py`, classic_cruise_1900,
288 epochs, paired seeds 8105/8106. Fomite trailing-exposure records now
carry `"unit"` (the pickup-unit key) alongside `"zone"` (parent) so pair
attribution distinguishes a stateroom pickup from a corridor one; the
probe gained `--cabin-confined-fomite off` for the baseline arm.

**Readout** (norwalk_gi rows only; `confined` = row target shared the
stateroom under confinement for ≥1 epoch):

| arm | seed | noro dose-rows | confined noro targets | confined noro attack |
|---|---|---|---|---|
| `own_cabin` | 8105 | 3 | 2 | 0 |
| `own_cabin` | 8106 | 1 | 1 | 0 |
| `off` | 8105 | 300 | 262 | 0 |
| `off` | 8106 | 1 | 1 | 0 |

Confined-pair noro channel dose, summed over confined targets:

| arm | contact | emesis | flush | hvac | fomite |
|---|---|---|---|---|---|
| `own_cabin` 8105 | 0.0502 | 0.2079 | 0 | 0 | 998.8936 |
| `own_cabin` 8106 | 0.0013 | 0 | 0 | 0 | 0 |
| `off` 8105 | 0.0004 | 0 | 0 | 0.3927 | 8368.4644 |
| `off` 8106 | 0 | 0 | 0 | 0 | 0.0689 |

- The `own_cabin` fomite dose on pair [1581,1586] (998.8 over 258
  confined epochs) is the new mechanism: confined index loading its own
  fittings, confined mate picking up there. The `off` arm's one fomite
  row (8368.5 on the same pair) is *pre-confinement* pickup — free-window
  compartment pickup existed before; only the confined window was gated.
- `hvac` on `off`-arm noro rows is emesis-conditioned aerosol entrained
  through HVAC to the compartment air unit — unchanged by this change.
- `flush` produced zero noro rows on both arms: the path is live
  (`_emit_flush` → `_dose_flush_cabin` keys the record's `target_zone` to
  the compartment), but no stool event with stool titre landed on a
  noro-carrying pair's unit in these realisations. Not dead-coded;
  unexercised at n≈3–133 noro-carrying pairs.
- Per-pair λ (susceptibility × Σdose) stays sub-copy: confined noro
  implied SAR ~1e-9–4e-4 per row on both arms. Even the dominant fomite
  delivery (≈1e3 dose-units over a confined window) yields λ ≈ 1.6e-8 —
  the per-pair absorbed hazard misses the literature confined-mate floor
  (Wikswo 2011 15.4%, Chimonas 2008 24.1%) by ~5 orders of magnitude.
  That is a dose-*scale* gap, not channel geometry: every named channel
  now reaches the pair key; what they carry is set upstream (open-ledger
  item 00 — the dose scale governs the box).

**Held-out check: confined-window noro mate attack = 0/266 pooled
confined targets across both arms — below the 5–30% trigger band and
reported in-session.** With λ ~1e-4 max per pair, ~263 expected-zero
conversions are consistent arithmetic, not a blocked channel: all four
non-air channels deliver to the pair key. Any-pathogen confined mate
attack (mostly the influenza co-boarding) reads 32.5%/30.1% on and
31.7%/28.7% off — inside the 18–81% Pluciński envelope as before.

Paired-seed caveat, recorded per the attribution discipline: the two arms
diverged at realisation level — noro touched 3 pair-cabins on `own_cabin`
8105 vs 133 on `off` 8105 (and `off` 8106 fizzled symmetrically at 1).
Shared-stream draws are bit-aligned until the first dose difference
(flu pairs also gain confined fomite delivery, so the first divergence
predates any noro conversion); a ship-wide infection-count delta on 5/2
noro boarders is therefore *not* attributable to this change at one seed
pair. What is attributable at the pair level: confined fomite dose exists
under `own_cabin` and is structurally absent under `off`.
