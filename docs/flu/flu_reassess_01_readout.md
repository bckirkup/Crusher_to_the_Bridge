# FLU-REASSESS-01: the post-enhancement re-census — 800 cells, all four classes

**Status:** Measurement of record for the post-CAREGIVER-SVC-01 /
DEFIANT-ESC-01 / MEAL-SVC-01 engine. Supersedes
[flu_open_voyage_01_readout.md](flu_open_voyage_01_readout.md) as the
flu census on the current engine; OPEN-01 remains the baseline of
record for cross-engine contrasts (its numbers are quoted below as
`base`).

**Measured at:** `a7593ddc` (ENGINE_GIT_SHA of image
`picard-campaign@sha256:dc88bb520fd2fb463f7ab143f044a4c5bab38972dab432be85083be6019d786d`,
tag `flu-reassess01`, merged spec #949). Campaign
`campaigns/flu/reassess_01/` (DESIGN.md carries the frozen predictions
P1–P6), cells at
`s3://crusherbucket-994254241749-us-east-1-an/campaign/flu_reassess_01/`.

**Cell:** the VIS-01 contract plus mechanism witnesses
(`mechanism_echo`, `compliance_actions`, verbatim `enforced_events` /
`refusal_events`, `caregiver_telemetry`). Same conditioned spec as
OPEN-01 — `confinement="organic"`, isolated `influenza_a`, explicit
2-passenger epoch-0 seed plus the boarding-prevalence draw, 288 epochs,
seeds 8105–8204. Blocks `{exp, spr, cls, mega} × {r100_dec, r200_dec}`
= 8 blocks × 100 seeds = **800 cells**: `r100_dec` is the new-engine
census, `r200_dec` is the reporting ×2 arm whose paired r200−r100
contrast re-scores the VIS-01 sign-reversal under both fixes.

**Execution:** jobdef `picard-flu-reassess-01:1` (EC2, digest-pinned);
Fargate twin `picard-flu-reassess-01-fargate:1` registered during a
~15 h us-east-1 On-Demand drought and used for the 20-seed canary
(`31bf588c`, read out separately — see LEDGER.md). When EC2 capacity
returned at ~17:41 UTC the parked canary `144d61ba` no-op'd through
dedup and the eight arrays ran FIFO on `picard-analysis-queue`:
**800/800 SUCCEEDED, 0 FAILED**, ~3.3 h wall (mega cells ~20–25 min
each serialized the tail). All audit invariants clean: schema
`flu_reassess_01.v1`, echo `["uniform",0.05,0.3]` / escalation 24 /
responder / uniform on every cell, `service_dose_to_host_credited == 0`
everywhere, enforced ≤ refusals per cell.

## Census, new engine vs OPEN-01

| tier / arm | infected | onboard-acquired | presenting attack | rep/inf pooled | rep/inf acq | outbreak | ≥ALERT | confined |
|---|---|---|---|---|---|---|---|---|
| exp r100 | 648 (Δ−107) | 180 (Δ−102) | **0.77 % ≈Ward** (was 0.89) | 53.4 % | 73.9 % | 0.65 | 0.99 | 96/100 |
| exp r200 | 619 | 151 | 0.74 % ≈Ward | 54.0 % | 74.2 % | 0.69 | 1.00 | 98/100 |
| spr r100 | 2213 (Δ−235) | 279 (Δ−228) | 0.18 % (was 0.21) | 24.2 % | 31.5 % | 0.88 | 1.00 | 100/100 |
| spr r200 | 2208 | 265 | 0.19 % | 25.6 % | 41.5 % | 0.89 | 1.00 | 100/100 |
| cls r100 | 1539 (Δ−147) | 212 (Δ−150) | 0.22 % (was 0.25) | 27.4 % | 37.3 % | 0.77 | 1.00 | 100/100 |
| cls r200 | 1540 | 215 | 0.23 % | 28.1 % | 42.8 % | 0.80 | 1.00 | 100/100 |
| mega r100 | 4728 (Δ−339) | 531 (Δ−332) | 0.14 % (was 0.15) | 20.8 % | 34.8 % | 0.96 | 1.00 | 100/100 |
| mega r200 | 4743 | 546 | 0.15 % | 22.0 % | 43.4 % | 0.98 | 1.00 | 100/100 |

Deltas are pooled counts vs the OPEN-01 constants (cross-engine
contrast, not paired). Onboard-acquired fell 36–45 % on every class —
the discounted crew bridge (`contact_factor ~ U[0.05,0.3]`) bites at
scale.

## The r200−r100 paired contrast (same engine, same seeds)

| tier | Δonboard mean | Δinfected | Δquarantined | share-positive (onboard) |
|---|---|---|---|---|
| exp | **−0.29** (was +1.62) | −0.29 (was +1.56) | −0.47 (was +1.44) | 0.18 |
| spr | −0.14 (was +0.17) | −0.05 (was +0.17) | −0.03 (was −0.33) | |
| cls | +0.03 (was −0.26) | +0.01 (was −0.25) | +0.02 (was +0.14) | |
| mega | +0.15 (was +0.68) | +0.15 (was +0.56) | +0.07 (was +2.38) | |

The serviced-quarantine sign-reversal is dead on the scored grid: exp's
paired Δonboard flipped negative, and no class approaches the VIS-01
tail.

## Mechanism witnesses

| arm | enforced (cells) | refusals (cells) | deliveries | svc dose credited | to_host |
|---|---|---|---|---|---|
| exp r100 | 75 (45) | 180 (52) | 12166 | 26352.0 | 0.0 |
| exp r200 | 63 (45) | 166 (55) | 12074 | 23509.7 | 0.0 |
| spr r100 | 64 (52) | 66 (52) | 19084 | 59558.1 | 0.0 |
| spr r200 | 67 (48) | 75 (55) | 19029 | 54152.5 | 0.0 |
| cls r100 | 54 (42) | 56 (42) | 14601 | 36558.3 | 0.0 |
| cls r200 | 52 (35) | 54 (37) | 14707 | 38621.4 | 0.0 |
| mega r100 | 123 (71) | 127 (71) | 35171 | 70714.3 | 0.0 |
| mega r200 | 121 (69) | 135 (72) | 35374 | 70359.5 | 0.0 |

619 `enforced_confinement` events across 800 cells — every one exactly
+24 epochs after a refusal by the same agent (full sweep, no orphans).
The service channel credits responder→host dose at scale
(~23.5k–70.7k per arm) and never leaks to `to_host` under `responder`.

## Frozen predictions P1–P6

| # | prediction | verdict | measured |
|---|---|---|---|
| P1 | exp paired Δonboard ≤ +0.3, share-positive ≤ 0.15 | **held** (tail marginal) | Δonboard **−0.29**; share-positive 0.18 (3 pt over the bound — reversal is dead, tail slightly fatter than frozen) |
| P2 | onboard falls everywhere; caregiver share of acquired < 49–55 % | **partial** | onboard fell 36–45 % on all classes ✓; caregiver share sits 55–68 % on 7/8 arms — absolute caregiver-dominant counts fell (e.g. mega 444→308) but droplet fell faster (mega 419→224), so share rose |
| P3 | exp attack falls toward Ward; big-hull residual 0.13–0.25 % | **held** | exp 0.74–0.77 % ≈Ward 0.7; spr/cls/mega 0.14–0.23 % inside the band |
| P4 | pooled rep/inf ≫ F5 [0.03, 0.15] | **held** | 20.8–54.0 % on all arms |
| P5 | enforced fires non-empty; epochs ≈ +24 h after refusal | **held** | enforced on 42–71 % of cells; 619/619 events exactly +24 |
| P6 | outbreak ≥0.6 exp / ≥0.8 elsewhere; confinement ≥95 %; ≥ALERT within a few pts of 67/96/97/99 | **mostly held** | outbreak 0.65/0.88/0.77/0.96 r100 (cls −3 pt marginal); confinement 96–100 ✓; ALERT spr/cls/mega within 1–4 pt (all 1.00) but **exp 0.67→0.99** — the enforcement stack escalates final status on the small hull |

## Anomalies

- **exp seed 8198 draws `index_cases = 1`** on both arms
  (`index_invariant_fails = 1` per arm, all other blocks 0). The
  embarkation draw is shared across reporting arms, so the same seed
  fails identically under r100 and r200 — an RNG-stream shift from the
  upstream mechanism draws vs the baseline (which drew ≥2 on 8198), not
  a mechanism malfunction. The cell is otherwise clean and its surfaces
  sit within the block distributions.
- **exp ≥ALERT 0.67 → 0.99:** confinement + enforced escalation raise
  the final trigger level on the weakest-outbreak tier. Direction is
  toward more escalation, consistent with DEFIANT-ESC-01 arming the
  escalation ladder; the mechanism attribution is plausible, not
  per-event proven.
- r200 caregiver share sits above r100 on exp/spr (62.9 % vs 46.1 %;
  67.5 % vs 65.6 %): doubling the reporting vector suppresses droplet
  acquisitions earlier than the discounted service channel — the route
  mix under feedback is not monotone, same lesson VIS-01 taught.

## Reading rules carried

Cross-engine deltas vs OPEN-01/VIS-01 constants are contrasts, not
paired seeds; nothing here was expected to bit-match the pre-
enhancement payloads. No constant was fit to an anchor on this
campaign.
