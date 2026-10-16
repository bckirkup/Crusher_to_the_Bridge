# NORO-MINT-RATE-01 — wave readout

Status: MEASURED (waves 1–2, 27,000 cells) | campaign:
`campaigns/noro/mint_rate_01/` | design of record:
`docs/norovirus/noro_mint_rate_01_sweep_design.md` (frozen pre-run)

Question: the `lot_object_probability` voyage gate is the operative
margin on the common-source object grammar. Where along the gate does
the D1 posting marginal land in the 0.4–0.9 pp band per hull, and does
the D2/D3/D4 signature survive at that rate?

Bridge status: bit-identity vs SHAPES-01 is unmeasurable (ledger F0 —
same image diverges by host; PR #1022 flipped the absent-default after
the campaign image). All cross-campaign reads are statistical. In-wave
reads remain valid: every arm in a wave shares that wave's fleet-day
float path as its `off`.

Evidence labels per margin: **measured** (this campaign's cells),
**inferred** (statistical bridge / pooled), **hypothesis** (declared
pre-run, unverified beyond this readout).

## Coverage

| hull | cells scanned | arms | scan errors |
|------|--------------:|-----:|------------:|
| exp | 9,000 | 9 | 0 |
| cls | 9,000 | 9 | 0 |
| spr | 9,000 | 9 | 0 |

Scan: `tools/noro_diag/food_shapes_01_scan.py` streaming member reads,
partitioned as a 27-child Fargate array
(`picard-noro-scan-readout`, image `noro-mint-rate01` @ `49e1993b`),
rows landed to `campaign/noro_mint_rate_01/_scan_rows/`. Report:
`food_shapes_01_report.py --arm-set mint_rate`.

## D1 — posting marginal vs in-campaign `off` (band +0.4–0.9 pp)

### exp (measured)

off floor 0.70% posted (7/1,000). `ship` +0.50 and `p005` +0.90 in
band; `p008`–`p024` +1.10/+1.20/+1.50/+1.80 over; `mint` +8.00,
`ind` +7.30. **In-band window ≈ gate [0.005, 0.0105]** — the design's
predicted [0.004, 0.010] (hypothesis, confirmed). Posting marginal ≈
minted-voyage count on every rung (measured): the voyage posts
essentially iff it minted ≥1 provisioned_lot.

### cls (measured)

off floor 0.30% posted (3/1,000). `p005`–`p017` in band:
+0.60/+0.60/+0.70/+0.80; `p024` +1.30 over; `mint` +4.90, `ind`
+5.60. `ship` +0.10 under the band floor. **In-band window ≈ gate
[0.005, ~0.020]** — wider than the design's predicted [0.007, 0.015],
shifted a touch lower (p005 in-band at +0.60; ship, presence ≈0.0105,
lands *under* at +0.10 — its U-drawn mints concentrate the low end on
cls, and P(post|minted) ≈ 0.5–0.6 halves the yield vs exp's 0.93).

### spr (measured)

off floor 0.00% posted (0/1,000). `p008`–`p024` in band:
+0.50/+0.60/+0.70/+0.70; `ship` +0.20 and `p005` +0.30 under;
`mint` +3.20, `ind` +2.70 over. **In-band window ≈ gate
[0.008, 0.024]** — shifted high vs the design's predicted
[0.005, 0.012]: spr's P(post|minted) ≈0.37 is the lowest of the
three hulls, so it takes more mints per posting — the whole
ladder shifts up the gate.

## Signature at rate (D2 posted-AR / D3 conversion / D4 burst48)

The verdicts diverge by hull — the campaign's designed read.

### exp (measured)

- D2: pooled in-band rungs (ship+p005, 28 posted) postAR med **0.0301 <
  in-campaign `ind` 0.0380 → signature does NOT survive at in-band
  rate**. (0.04 edge also missed: only `p024`/`mint` ≥0.0411.)
- D3: excursion→posting conversion ≥`ind` at every rung (0.88–1.27×).
- D4: posted b48 0.66–0.78 vs rest 0.409 at every rung — survives.

### cls (measured)

- D2: pooled in-band rungs (p005–p017, 39 posted) postAR med **0.0516 ≥
  `ind` 0.0359 → signature SURVIVES at in-band rate** — the mirror of
  exp. Per-rung medians 0.0508–0.0524, all above `ind`.
- D3: excursion→posting conversion 26.1% pooled in-band vs `ind`
  57.1% (**0.46× → does NOT hold at ind level**). Per-rung 24–33% vs
  ind 57%; `mint` 51% (0.89× ind).
- D4: posted b48 0.40–0.50 vs rest 0.287 at every in-band rung —
  survives (the gate selects bursty voyages even where the excursion
  set itself sits at rest level, 0.29 vs 0.287).

### spr (measured)

- D2: pooled in-band rungs (p008–p024, 25 posted) postAR med
  **0.0319 ≥ `ind` 0.0310 → signature SURVIVES at in-band rate**
  — barely: the +0.0009 edge is within pooled noise (per-rung
  medians 0.0167–0.0438 straddle `ind`; the pooling draws the
  median up through p017/p024).
- D3: excursion→posting conversion 14.5% pooled in-band
  (25/172) vs `ind` 27.8% (**0.52× → does NOT hold at ind
  level**); `mint` 27.4% (0.99× ind).
- D4: posted b48 0.303–0.504 vs rest 0.271–0.272 at every
  in-band rung — survives on the posted-not-collapsed-to-rest
  read (design §5.1's weaker spr form).

## Mint presence vs declared gate (integrity §5.4-4)

| hull | ship | p005 | p008 | p012 | p017 | p024 | mint |
|------|-----:|-----:|-----:|-----:|-----:|-----:|-----:|
| exp minted | 6 | 9 | 11 | 13 | 17 | 20 | 82 |
| cls minted | 6 | 9 | 12 | 14 | 18 | 21 | 84 |
| spr minted | 6 | 9 | 12 | 14 | 18 | 21 | 84 |
| E[p] | 10.5 | 5 | 8 | 12 | 17 | 24 | 85 |

All within binomial noise of the gate (measured, all three hulls).
Nested mint sets across the scalar rungs: **0 violations on exp,
cls, and spr** (p005⊆p008⊆p012⊆p017⊆p024 per seed — the
stream-layout gate §5.4-3). **cls and spr minted counts are
bit-identical per arm** (same seed indices 8105–9104 → the
seed-paired mint draw is a discrete RNG gate, float-path
independent — F0 confirmed as a cross-hull identity, not just
within-host). `mint` minted 82 (exp) / 84 (cls, spr) — 82 on exp
= SHAPES-01's 82 exactly.

## P(post | ≥1 lot object) — the rate-independence read

| hull | arm | minted | posted | P(post\|minted) | anchored |
|------|-----|-------:|-------:|----------------:|---------:|
| exp | in-band pool | 15 | 14 | 0.93 | 0.93 |
| exp | mint | 82 | 81 | 0.99 | — |
| cls | in-band pool | 53 | 31 | **0.585** | 0.58 |
| cls | mint | 84 | 51 | 0.61 | — |
| spr | in-band pool | 65 | 24 | **0.369** | 0.36 |
| spr | mint | 84 | 31 | 0.37 | — |

At in-band rate, P(post|minted) lands on the SHAPES-01-anchored
per-hull value on all three hulls (measured): the posting
probability is a property of the hull+mechanism, not of the gate rate —
the linear-marginal mechanism (marginal ≈ minted × P1) holds on
every hull.

## Integrity

- Echo verbatim on every cell, all hulls: 9,000/9,000 per hull, 0
  mismatches (scalar rungs echo the point value; `lot_mint_model`
  absent — pre-#1022 manifests).
- Titres: every object + pan draw in [1.5e2, 5e3] on all three
  hulls (spr draws 154.9–4,986.7); every object exactly one titre
  (0 varying, all constant); zero zero-serve objects.
- `off` zero-witness on all hulls (0 objects, 0 events, dose 0).
- `ind` v1-only on all hulls (0 object rows; 471/478 pans on
  cls/spr).
- Non-cs route share / median AR drift vs `off`: see per-hull tables
  (must-not-move section of the tool output).

## Vacuity

Rungs with <20 realized minted voyages read census+marginal only
(design §5.5): exp ship/p005–p017 thin (6–17 minted); cls and spr
ship–p017 thin (6–18 minted; only p024 21 and mint 84 are not).
The thin-flagged D2/D3/D4 reads above pool the
in-band set, which is the declared protocol.

## Verdict

Per-hull in-band brackets, all measured: **exp [0.005, 0.0105],
cls [0.005, ~0.020], spr [0.008, 0.024]** — the operative gate
moves up as the hull's P(post|minted) falls (0.93 / 0.58 / 0.37).

Signature at rate splits by hull — the campaign's designed
discriminating read:

| criterion | exp | cls | spr |
|-----------|-----|-----|-----|
| D2 postAR ≥ ind | FAIL (0.030<0.038) | PASS (0.052≥0.036) | PASS (0.032≥0.031, thin) |
| D3 conv ≥ ind | PASS (≥0.88×) | FAIL (0.46×) | FAIL (0.52×) |
| D4 b48 | PASS | PASS | PASS (weak form) |

No hull satisfies D2+D3+D4 jointly at in-band rate: exp fails D2;
cls and spr fail D3. The measured signature is that the mint-rate
mechanism carries the posting marginal AND the posted-AR edge on
the two large hulls but cannot reproduce ind's excursion→posting
conversion there — on cls/spr only ~half of excursions post, vs
ind's ~28–57%. What the mechanism does reproduce on every hull:
the minted-set discrete draws (bit-stable, nested, gate-tracked),
the linear marginal (minted × per-hull P1), posted-b48 separation,
and the P(post|minted) hull constants.
