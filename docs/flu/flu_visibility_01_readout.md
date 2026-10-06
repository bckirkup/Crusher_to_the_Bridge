# FLU-VIS-01: the visibility sweep — the reporting layer saturates; the big-hull gap is incidence

**Status:** Measurement of record.

**Measured at:** `ca775a0b` (ENGINE_GIT_SHA on all 2401 cells; image
`picard-campaign@sha256:1c0aa1d570f0fe905b936db9e08b3509369997d5a74999913a3decf95a2a17d3`,
tag `flu-vis01`, merged spec #928). Campaign
`campaigns/flu/visibility_01/` (DESIGN.md carries the frozen verdict
frames), cells at
`s3://crusherbucket-994254241749-us-east-1-an/campaign/flu_visibility_01/`.
Baseline of record: FLU-OPEN-01 (`7f4702ef`, CW-02 delta audited and
canary-verified flu-inert).

**Grid:** report_scale ∈ {0.25, 0.5, 2.0} (multiply-then-clip at 1.0 on
both recognition vectors) × eligibility ∈ {declared `[0,0,0.85,1,1]`,
strict-mild `[0,0,0,1,1]`} = 6 arms × 4 classes × seeds 8105–8204 =
**2400 cells** on the FLU-OPEN-01 open-voyage spec. The shipped corner
(r100 × dec) is the OPEN-01 cells — declared reuse, verified twice (spec
smoke and the canary below), never re-run.

**Execution:** jobdef `picard-flu-visibility-01` revs :2–:25, queue
`picard-analysis-queue` On-Demand. Baseline-identity canary
`b346d49d-33b6-4d7c-81ba-d12d39f81052` on `flu_exp_12d_r100_dec`
SUCCEEDED and its seed-8105 payload is **bit-identical to OPEN-01's
`cell_8105.json`** on every count field, infections and complement →
reuse held; the four `r100_dec` contingency blocks stayed unsubmitted
per DESIGN §3. 24 arrays: **2400/2400 SUCCEEDED, 0 FAILED** (~5.7 h wall
on a CE shared with a sibling covid session; mega serialized the tail).
Audit invariants, all clean on the full payload set: ≥2 index infections
per cell (`index_invariant_fails = 0`); every cell's `arm.resolved`
severity model equals its declared patch (0/2401 mismatches — arm echo,
not argv); schema `flu_visibility_01.v1` everywhere; **1200 strict-arm
cells carry exactly 0 dated mild onsets** — the eligibility corner fired.

## The answer in one table

Presenting attack (`ever_reported / complement`, mean per cell) vs
Ward's ~0.7 % (bracket [0.4 %, 1.0 %]):

| arm | exp | spr | cls | mega |
|-----|-----|-----|-----|------|
| r100_dec (baseline) | 0.89 % | 0.21 % | 0.25 % | 0.15 % |
| r025_dec | 0.85 % | 0.21 % | 0.23 % | 0.14 % |
| r025_str | 0.85 % | 0.21 % | 0.22 % | 0.13 % |
| r050_dec | 0.88 % | 0.22 % | 0.23 % | 0.14 % |
| r050_str | 0.86 % | 0.21 % | 0.23 % | 0.14 % |
| r200_dec | 1.07 % | 0.22 % | 0.25 % | 0.16 % |
| r200_str | 1.04 % | 0.21 % | 0.25 % | 0.15 % |

**Expedition brackets Ward on every arm and overshoots at r200; the
three big hulls never reach Ward's band at ANY declared corner.** An 8×
span of the reporting vectors — including r200, where moderate and
severe saturate at the 1.0 clip ceiling — moves presenting attack ≤0.02
pp on spr/cls/mega. The reporting pipeline on those hulls is already
saturated: it reports nearly everything the severity mix lets it reach.
**The binding constraint is incidence, not visibility.** Ward's 0.7 %
needs ~49 presenting cases on a 7000-complement mega; measured reported
is ~10/cell (0.15 %), and even the ceiling-saturated arm lifts
reported/infected only to 0.223 pooled (0.398 acquired). Closing the
mega gap by visibility alone would need rep/inf ≈ 0.45 on the current
~50-infection pool — outside the declared space — or ~4–5× the
infection count. Expedition sits at Ward because its voyage attack is
~2× the others' (1.68 % vs 0.72–0.88 % of complement infected): same
reporting machinery, more cases to report.

## Frozen frames, read

### 2/3 — Reported/infected, pooled and acquired cohort

| arm | exp pooled | spr pooled | cls pooled | mega pooled | mega acquired |
|-----|-----------|-----------|-----------|------------|---------------|
| r100_dec | 0.531 | 0.255 | 0.279 | 0.203 | 0.293 |
| r025_dec | 0.497 | 0.245 | 0.256 | 0.190 | 0.238 |
| r025_str | 0.492 | 0.242 | 0.252 | 0.188 | 0.227 |
| r050_dec | 0.513 | 0.257 | 0.265 | 0.197 | 0.278 |
| r050_str | 0.500 | 0.252 | 0.259 | 0.193 | 0.254 |
| r200_dec | 0.530 | 0.271 | 0.283 | 0.223 | 0.398 |
| r200_str | 0.541 | 0.257 | 0.272 | 0.205 | 0.317 |

Two measured facts about the declared space:

- **Even the coldest corner can't reach the F5 frame.** r025×str
  pooled rep/inf reads 0.188–0.492 — still ≥ ~1.7× above the [0.03,
  0.15] cap on every class. The frame is unreachable anywhere in the
  swept grid; the reporting floor on this voyage is ~0.19–0.25 pooled.
- The axis moves the right direction and roughly proportionally on the
  acquired cohort where it binds hardest (mega acquired 0.227 → 0.398
  from r025_str to r200_dec); on exp it saturates (~0.60–0.65 across
  all arms — post-recognition moderate/severe already at ceiling).

### 4 — Reporting feedback into transmission (paired-seed deltas vs baseline)

Hypothesis was: scale-down → fewer reports → less confinement → weakly
more onboard acquisition; r200 → the reverse.

| tier | arm | Δonboard mean/med | Δinfected mean/med | Δreported mean/med | Δquarantined mean/med |
|------|-----|-------------------|--------------------|--------------------|------------------------|
| exp | r025_dec | +0.15 / 0 | +0.15 / 0 | −0.18 / 0 | −0.21 / 0 |
| exp | r200_dec | +1.62 / 0 | +1.56 / 0 | +0.82 / 0 | +1.44 / 0 |
| spr | r025_dec | +1.19 / 0 | +1.07 / 0 | +0.00 / 0 | +1.24 / 0 |
| spr | r200_dec | +0.17 / 0 | +0.17 / 0 | +0.42 / 0 | −0.33 / 0 |
| cls | r025_dec | −0.04 / 0 | −0.05 / 0 | −0.40 / 0 | −0.03 / 0 |
| cls | r200_dec | −0.26 / 0 | −0.25 / 0 | +0.00 / 0 | +0.14 / 0 |
| mega | r025_dec | −0.56 / 0 | −0.48 / 0 | −0.78 / −0.5 | −0.01 / 0 |
| mega | r200_dec | +0.68 / 0 | +0.56 / 0 | +1.12 / +1 | +2.38 / +1 |

Measured: **visibility is transmission-relevant, but the sign is not the
naive one.** All medians are 0 — the effect is tail-driven rare-event
dynamics, not a uniform shift. Scale-down adds onboard acquisition on
the small/mid hulls (exp +0.15, spr +1.1–1.3 mean) as predicted
(fewer reports → fewer quarantines → more transmitters loose). But
r200 on exp **adds** infections (+1.56 mean, +156 total infections vs
baseline's 755) while quadrupling quarantine (+1.44 mean) — more
reporting produced *more* onboard spread on the small hull, opposite
the predicted direction. Attributed below: it is a real mechanism —
the serviced-quarantine crew bridge — not RNG-stream re-realization.

#### Attribution of the exp r200 sign-reversal

Attributed at `ca775a0b` by paired local probe re-runs (per-agent
confinement/cabin-mate/infection records) on the largest driver seed
(8188, +49) plus a cross-check across all 100 paired exp seeds:

- **RNG stream intact**: import cohorts are identical between arms
  (same six agent IDs at `first_infection_epoch` 0). The divergence
  opens only after reporting outcomes differ the state — it is
  state-mediated through the arm's own causal pathway, not raw stream
  corruption. (The earlier "divergent import" appearance was a
  recording artifact: `infection_epoch` shows the *last* episode;
  the arm's shifted IDs were reinfected imports at `episode` 2+.)
- **Cabin-mate co-confinement refuted**: only 2 of 59 arm onboard
  infections occurred while quarantined. The CONFIRMED-time
  cabin-mate sweep is not the channel.
- **The channel is the serviced-quarantine crew bridge**: more
  reported cases → confined cohort ×5 at voyage end (77 vs 15)
  → steward service deliveries into cabins ×2.6 (440 vs 167)
  → crew caregiver-route infections ×1.6 (14 vs 9) plus 6 crew
  droplet acquisitions → exempt crew keep circulating and seed a
  late passenger droplet wave (epochs ~205–283, 38 vs 2 — nearly
  all never-confined when infected). Confinement removed free
  transmitters, but cabin service bypasses the confinement boundary
  and bridges the outbreak into the still-free pool.
- **Cross-seed support**: Pearson r = 0.81 between Δinfected and
  Δquarantined across the 100 paired exp seeds, in both directions
  (the largest −Δquarantined cell, s8142 at −42, is also the largest
  −Δinfected at −24).
- **Why exp only**: on the 450-agent hull the confined cohort reaches
  ~17 % of complement against a small free pool; on the 1900–5000
  hulls the same bridge exists but dilutes into a far larger free
  surface (spr r200 Δ flat at +0.17, consistent with dilution).

Interpretation: on the small hull, quarantine's benefit is partly
self-defeating through the service channel — physically coherent
(quarantined passengers still receive cabin service; Diamond Princess
crews kept delivering), and reporting-driven, not stochastic. What
remains hypothesis-level: the same decomposition is not yet probed on
the other driver seeds (8112/8184/8162), though the 100-seed
correlation supports the same shape.

### 5 — Recognition timing (`escalation_log`, first epoch at ALERT)

| tier | baseline (final ≥ ALERT) | arm ever-ALERT medians by arm |
|------|--------------------------|-------------------------------|
| exp | 67 % | 97–100 % ever-ALERT; first-ALERT median 40.5 (r025) → 30.5 (r200) |
| spr | 96 % | 100 % ever-ALERT; median 5 → 4 |
| cls | 97 % | 100 % ever-ALERT; median 11 → 9 |
| mega | 99 % | 100 % ever-ALERT; median 0 (import prevalence triggers immediately) |

Arm-vs-baseline final-trigger rates (recomputed on arm cells for
comparability): exp 63–66 %, spr 95–99 %, cls 96–97 %, mega 97–100 % —
flat vs baseline on every class; **the reporting level does not change
whether a voyage ends at ALERT**. What it changes is when: first-ALERT
timing is class-dominated (mega 0 ≈ instantaneous from import
prevalence; exp ~40 ≈ slow-burn accumulation) and the reporting scale
only nudges it on the small hull (−10 epochs r025→r200). Baseline rows
have no `escalation_log` (OPEN-01 payloads predate it) — their ALERT
figures are final-trigger, noted as such; the exp baseline row in the
arm table is the n=1 canary cell.

### 6 — Eligibility witness + what the strict corner bought

Strict arms: **0 dated mild onsets in 1200 cells** (declared arms:
175–425 per class-block) — `_onset_eligible` gating fired as designed.
Effect on everything else ≈ nil: presenting attack moves ≤0.01 pp
between dec and str at fixed scale on every class; reported counts drop
~5–15 per class-block. Measured conclusion: at the declared reporting
vectors (mild pre 0.10 / post 0.18), mild-eligible cases contribute
little to the report pool anyway, so **"mild self-treats" is a
second-order axis on this voyage** — it cannot manufacture the missing
Ward gap either. The corner is real (witness fires), it is just
second-order here.

### 7 — Route mix

Dominant-route attribution stable across arms, as predicted (routes
precede the observation funnel): caregiver ≈ 36–56 % of
onboard-acquired infections everywhere, droplet ≈ 44–50 %,
hvac_airborne ≤ ~1 %. One visible tail: exp r200 droplet attributions
rise (271 vs ~175 at other arms) alongside the +Δinfected cells — now
attributed (§4): the late service-bridge wave lands on the droplet
route among the never-confined pool, not a route-mechanism shift.

## Verdict

**No declared reporting corner reaches Ward's presenting attack on
spr/cls/mega; the sweep measured that the gap is incidence, not
visibility.** What the reporting layer actually does on this voyage,
measured per class: it saturates early (r200 gains ≈ nothing over r050
on the big hulls), it feeds back into transmission with a tail-driven,
sign-ambiguous response (small hulls acquire more under BOTH extreme
corners), its final escalation outcome is invariant, and its strict-mild
corner is a live-but-second-order axis. The residual big-hull gap —
model ~0.13–0.25 % vs Ward ~0.7 % — is now cleanly attributable to the
incidence side of the cell (importation intensity, onboard acquisition,
exposure window): on measured numbers, presenting attack tracks
`infected/complement` far more than `reported/infected`, and Ward sits
off the model's presenting-attack distribution on the big hulls rather
than inside any reachable reporting corner. Whether Ward's 0.7 % is a
fleet-level expectation or a realized outbreak voyage is the comparator
question the ledger inherits; the model's answer under shipped
incidence is "off-distribution on the big hulls, centered at Ward on
expedition." The exp r200 sign-reversal is separately attributed (§4)
to the serviced-quarantine crew bridge, so it does not count as an
incidence-side defect.
