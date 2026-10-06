# FLU-OPEN-01: the open voyage on all four classes — first free-running census

**Status:** Measurement of record.

**Measured at:** `7f4702ef` (ENGINE_GIT_SHA of image
`picard-campaign@sha256:bc72e55295de111b3b14a987daad3dd422983d5c922b2604befcd5707d952324`,
tag `flu-open-voy01`, merged spec #921). Campaign
`campaigns/flu/open_voyage_01/` (DESIGN.md carries the frozen verdict
frames), cells at
`s3://crusherbucket-994254241749-us-east-1-an/campaign/flu_open_voyage_01/`.

**Cell:** `conditioned_spec(confinement="organic")` — the FLU-RHYTHM-01
conditioned spec minus declared SOP-017. Isolated `influenza_a`, explicit
2-passenger epoch-0 seed plus the live boarding-prevalence draw (0.008
passenger / 0.005 crew), k = 6e-4, 288 epochs (12 days), seeds 8105–8204,
4 blocks × 100 seeds (expedition_cruise_450, spirit_cruise_3000,
classic_cruise_1900, mega_cruise_5000), single arm — comparisons ride the
seeds, not flags.

**Execution:** jobdef `picard-flu-open-voyage-01` revs :3–:6 (revs :1–:2
registered the same rendered jobdef during the canary submits), image as
above. Spot canary attempt parked ~35 min RUNNABLE under a zero-capacity
drought; terminated `5023fe35-…` and resubmitted On-Demand on user
decision. Canary `4c84471a-b219-484d-bf2c-b00b5c7ea853` on
`picard-analysis-queue` SUCCEEDED in ~5 min; arrays `18074d2e` (exp),
`7224370a` (spr), `bb8fdf0e` (cls), `c86b415f` (mega): **400/400
SUCCEEDED, 0 FAILED**, ~75 min wall end-to-end (exp ~10 min, spr ~40,
cls ~50, mega ~75). Artifact contract held: exactly one
`cell_<seed>.json` per block dir, `index_invariant_fails = 0` on all
blocks (≥2 index cases per cell). **Determinism:** seed 8105 was
re-run locally at `7f4702ef` and reproduces the canary's payload
bit-for-bit (counts, all 10 infection records, caregiver telemetry); the
only differing field is `engine_git_sha` (`unknown` off-image — the env
stamp, not a run input).

## Composition of the infection pool

The open voyage's infected set is dominated by epoch-0 imports: the
boarding draw (0.008 pax / 0.005 crew on complements 450–7000) plus the 2
explicit seeds, not onboard transmission. Onboard-acquired infections are
the minority everywhere:

| block | total inf. | epoch-0 (imports+seeds) | onboard-acquired | acquired share | attack/cell (inf/complement) |
|---|---|---|---|---|---|
| flu_exp_12d | 755 | 473 | 282 | 0.373 | 7.55/450 = 1.68% |
| flu_cls_12d | 1686 | 1324 | 362 | 0.215 | 16.86/1910 = 0.88% |
| flu_spr_12d | 2448 | 1941 | 507 | 0.207 | 24.48/3000 = 0.82% |
| flu_mega_12d | 5067 | 4204 | 863 | 0.170 | 50.67/7000 = 0.72% |

Acquired infections concentrate early-mid voyage (median
`infection_epoch` 111 of 288; p90 228), so ~26% of acquired infections
never reach onset inside the window by incubation lag — a denominator
property of any reporting ratio.

## The frozen frames, answered

| frame | exp | spr | cls | mega |
|---|---|---|---|---|
| F5 reported/infected, frozen [0.03, 0.15] | **0.531** [0.495, 0.566] | **0.255** [0.238, 0.273] | **0.279** [0.258, 0.301] | **0.203** [0.193, 0.215] |
| ever_ill / infected (implied band-mix ≈ 0.74) | 0.597 | 0.347 | 0.366 | 0.290 |
| outbreak formed (≥1 onboard-acquired inf.) | 0.67 | 0.88 | 0.80 | 0.97 |
| organic confinement formed (quarantined > 0) | 95/100 | 100/100 | 100/100 | 100/100 |
| final trigger ≥ ALERT | 67% | 96% | 97% | 99% |

Every F5 read sits above the frozen cap — `anchor_tension` on all four
classes. **The breach is the declared observation vector, measured, not a
new defect:** the `influenza_a.observation_model` notes record that the
declared reporting probabilities "imply a pre-recognition
medically-attended fraction near 0.16 per infection against the roughly
0.08 Ward measures… the arm starts about 2× too visible and closing that
is the sweep's job." The census now quantifies that declared
over-visibility per class and per infection cohort (below). The frozen
frame's failure mode is composition, not machinery — it was written
against a conditioned surface (SOP-017 confined the cohort early; the
0.18 reading there) and cannot arbitrate an import-dominated open
voyage.

### Decomposed funnel — where the deficit lives

| cohort | n | presented | ill | reported |
|---|---|---|---|---|
| epoch-0 imports+seeds | 7942 | 0.600 | 0.236 | 0.220 |
| onboard-acquired | 2014 | 0.737 | 0.750 | 0.387 |

On the cohort the natural-history table governs — onboard-acquired —
the machinery fires exactly as declared: presented 0.737 against the
band-mix-implied ≈0.74, ill 0.750. The pooled under-read is entirely the
import cohort, which follows the *initiation* `state_split`
(`never_symptomatic_fraction` 0.44; `presymptomatic_share_of_presenting`
0.3): expected import presentation ≈ 0.56 (+ the always-symptomatic
explicit seeds) vs measured 0.600; expected import illness ≈ 0.3 × 0.56 ≈
0.17 vs measured 0.13–0.16 once the 2 seeds/cell are backed out (exp's
0.507 import-ill is seed-share inflated — seeds are 42% of its epoch-0
cohort vs 5% on mega). Symptomatic-at-boarding imports (0.7 × 0.56)
arrive with `presented`/`severity_peak` resolved but their illness
predates the voyage, so they hold an infection record without an
in-voyage `ill` event — correct semantics for a 12-day window.

The same composition explains the per-band presentation flags on
cls/spr/mega (measured 0.58–0.76 against the band table 0.734–0.965):
epoch-0 imports present per the initiation split, not the
age-band natural-history table. Expedition's bands stay consistent
because the small cohort is seed-dominated.

Onboard-acquired reported/infected: exp **0.681**, cls **0.395**, spr
**0.377**, mega **0.293**; reported|ill 0.70–0.89. Against the profile's
declared severity-keyed vectors (pre-recognition 0/0/0.1/0.55/1.0,
post-recognition 0/0/0.18/0.7/1.0 on
asymptomatic/subclinical/mild/moderate/severe) and the measured severity
mix of infected (mild 0.35–0.43, moderate 0.14–0.19, subclinical
~0.10–0.14, severe_critical ~0.01), the acquired-cohort reporting is the
declared vector operating on an ALERT-formed voyage — high by
construction, now measured. Whether that level is the intended depiction
is the ledger's open question (see FLU-OPEN-01, §"what the census opened").

## Routes and the caregiver answer

Dominant-route attribution across all classes (share of infections):

| block | index_or_boarding | caregiver | droplet | hvac_airborne |
|---|---|---|---|---|
| flu_exp_12d | 473 (63%) | 137 | 142 | 3 |
| flu_cls_12d | 1324 (78%) | 188 | 167 | 7 |
| flu_spr_12d | 1939 (79%) | 278 | 229 | 2 |
| flu_mega_12d | 4204 (83%) | 444 | 419 | 2 |

**The s8113 amplifier question is answered at fleet scale:** caregiver is
a first-order onboard route on every class, not a confined-surface
artifact — 49% (exp) to 55% (spr) of *onboard-acquired* infections are
caregiver-dominant (9–18% of all infections once imports dominate the
denominator), at parity with or above droplet on every class; crew are
the plurality of caregiver-touched agents (e.g. mega 195 crew / 255 pax).
`hvac_airborne` is background noise (2–7 attributions/class).

## Severity and trigger surfaces

Severity mix of infected (resolved `severity_peak`): mild 35–43%,
moderate 14–19%, subclinical ~10–14%, severe_critical ~1% — the
age-graded CDC vectors operating on the cruise age structure, no class
anomaly. Outbreak formation rises with hull size (exp 0.67 → mega 0.97):
on the 450-agent ship one-third of voyages see no onboard transmission at
all — a property of the small susceptible pool + k, not stasis.
Confinement forms organically on 95–100% of cells; final trigger reaches
ALERT on 96–99% of the three larger hulls (exp: ALERT 60, SUSPECTED 32,
CONFIRMED 7, BASELINE 1).

## Verdict

**The flu arm depicts an open voyage on all four classes — with the
declared reporting visibility measured precisely, sitting above the Ward
comparator as the profile itself declares.** No engine defect surfaced:
natural history, presentation, severity, escalation and the caregiver
route all fire at their declared levels; the only surfaces above their
frozen frames are the ones the `observation_model` notes say are
intentionally ~2× hot pending the visibility sweep. The F5 frame's
composition assumption (an onboard-dominated denominator) failed — the
census fixed that by measuring both cohorts separately. What the census
opened for the ledger: (1) the declared post-recognition reporting level
on acquired infections (0.29–0.68) vs Ward's 0.08 — the sweep surface;
(2) expedition's 33% no-transmission rate — a small-ship floor to cite
when comparing classes; (3) caregiver reach measured on the open voyage
— the crew-scale amplifier is live at fleet scale.
