# Common-dose refit campaign design v1

**Status:** frozen design assessment — **design-blocked by the siting probe**; no campaign cell has run.
**Date:** 2026-11-27
**Pathogen:** `norwalk_gi`
**Scope:** design and local degeneracy siting only. No AWS submission, canary, fitting, refit execution, parameter change, mechanism change, or engine change occurred.

## 1. Required campaign and settled inputs

Outstanding item 3 asks for one common dose-response across
`expedition_cruise_450`, `classic_cruise_1900`, `spirit_cruise_3000`, and
`mega_cruise_5000`, with no hull-specific pathogen biology. The replacement for
withdrawn C1 must be sited where its axis resolves and must hold the
surveillance response fixed while dose moves.

Settled inputs adopted without re-derivation:

- `environmental_faecal_release_log10_g_per_epoch` / legacy `dose_adjustment`
  is a `-log10` gram-stool-equivalent exponent; larger values release less
  continuous material.
- C1's 12.0–14.0 ladder was degenerate and is withdrawn.
- `NORO-DOSE-REFIT-01` derives central value 7.57 and fitting box
  `[7.14, 8.86]` for the continuous channel.
- Emesis mass and the hand chain are absolutely declared. The refit must not
  silently rescale those channels.
- A8/A9 are fleet-scale mixture anchors under item 6 and cannot be legitimate
  verdicts for a single-configuration iid cell.

## 2. Candidate swept quantity and ladder

The only candidate axis considered was:

```text
pathogen_overrides.norwalk_gi.dose_adjustment
```

with the frozen five-rung ladder:

```text
7.14, 7.57, 8.00, 8.43, 8.86
```

The endpoints are the `NORO-DOSE-REFIT-01` box endpoints; 7.57 is its central
value. The axis is already logarithmic, so interpolation would be arithmetic
in `adj`, never in grams.

The probe lattice fixed everything else at the modern campaign coordinate:
`reportable` boarding, `syndromic_comp65`, hourly natural-history clock,
dwell-weighted sanitary visits, flush aerosol fraction 0.0, cabin flush
emission, cabin-compartment air, airflow pool transport, shipped alpha/beta
(`0.111`, `32.81`), and no `susceptibility_scale` override. The probe used
`expedition_cruise_450` at complement 450, 48 epochs, seeds 8105–8106, five
rungs: ten voyages. Its committed manifest is
`picard_framework/runs/mega_cruise_campaign/noro_common_dose_refit_probe_v1_manifest.json`.

## 3. Probe result: the axis does not resolve

The probe zips were flattened with `deploy/aws/aggregate_results.py` into
`docs/norovirus/common_dose_refit_probe_v1_summary.csv` and checked with:

```bash
python3 -m picard_framework.analysis.sweep_degeneracy \
  docs/norovirus/common_dose_refit_probe_v1_summary.csv \
  --axis parameters.dose_adjustment \
  --outputs derived.infection_attack_rate_passenger \
           derived.infection_attack_rate_crew \
           derived.ever_ill_attack_rate_passenger \
           derived.reported_case_attack_rate_passenger \
           derived.peak_prevalence \
  --group parameters.platform_id \
  --group parameters.surveillance \
  --replicate parameters.seed
```

Verbatim output is committed as
`docs/norovirus/common_dose_refit_probe_v1_degeneracy.txt`:

```text
- rows: 10
- rungs: 5
- resolved fraction: 0.200

## Collapsed rungs

- 7.14, 7.57, 8.0, 8.43, 8.86
```

The 0.200 fraction is one indistinguishable group of five rungs, not partial
resolution. At seed 8105 every rung records passenger infection/ever-ill
attack rate 0.0032, crew infection 0.0, reported passenger rate 0.0, and peak
prevalence 1. At seed 8106 every rung records passenger infection 0.0095,
ever-ill 0.0, crew infection 0.0, reported passenger rate 0.0, and peak
prevalence 3. The seed differences are realisation differences; the dose axis
moves nothing.

The measurement is registered as `docs/ledger/NORO-DOSE-REFIT-PROBE-01.md`; probe rows were produced with engine source clean at `3fe48d8b1916e1c06cdc92cc2d9c757574f9c53b` (the `-dirty` label reflects the then-uncommitted probe files). This is not treated as a short-horizon accident to engineer around, because
the active mechanism explains the bit collapse:

- the probe/default contact mode is `per_partner_contact`; direct-contact dose
  is composed through the donor's measured hand reservoir in
  `TransmissionCore._per_partner_contact_dose`, not proportional to the
  continuous shedding value;
- hand replenishment reads the measured stool-linked hand target, emesis uses
  the absolutely declared Kirby/plume source term, and food contamination
  deposits from hand load;
- norovirus continuous droplet emission is off by construction under the
  emesis-conditioned arm;
- the remaining uses of `get_pathogen_shedding` are eligibility/strain-mix
  weights or wastewater observation, not a dose magnitude that reaches a
  challenged host on this campaign coordinate.

Therefore the declared `[7.14, 8.86]` continuous-release box cannot presently
be sited to resolve the infection/readout axis. Under the session instruction,
this is a **design-blocked finding**, not a licence to move another constant,
widen the box, or substitute an alpha/beta arm. An alpha/beta arm is also not
seed-pairable under `RNG-FRAILTY-STREAM-01`.

## 4. Surveillance and adj stratification that remain required

The blocked design still fixes the response arm exactly as required:
`syndromic_comp65` on every rung, with no response-off or second surveillance
axis. Holding response fixed means identical detection, isolation,
confinement, quarantine-compliance, sick-call, and escalation parameters while
only the dose coordinate moves. This avoids C1's confounded 6–80x infection-
attack-rate contrast between response arms.

Every future readout must remain stratified by:

```text
hull class x dose-adjustment rung x seed
```

No readout may marginalize across `adj`. Paired-seed contrasts are legitimate
for `dose_adjustment` in principle because it consumes no random numbers and
does not re-parameterize a sampler; they are meaningless here because the axis
is collapsed.

## 5. Anchor scope if a future axis becomes readable

If a future design supplies a dose axis that actually reaches challenge dose,
a single-configuration cell can legitimately score only:

- **A1**, ever-ill passenger attack rate, conditional band 0.10–0.22;
- **A2**, ill/infected ratio, band 0.59–0.81;
- **A4**, reported passenger attack rate against the hull-class-specific
  pre-era VSP IQR;
- **A5**, passenger:crew reported-rate ratio, band 2.5–4.5.

It cannot legitimately score:

- **A3**, which is construction-only diagnostic output with no verdict;
- **A8/A9**, because item 6 makes them fleet-scale mixture anchors. They may
  be emitted as labelled diagnostics but must not enter admissibility or dose
  selection from single-configuration iid cells.

## 6. Frozen admissibility criteria, retained but not entered

These criteria are frozen for any successor design and were not entered here:

1. a scoring cell is valid only when all declared seeds complete with the
   declared hull, rung, surveillance arm, boarding rung, pathogen profile,
   complement, epoch count, and immutable engine image digest;
2. no mixed reporting/report-free cell is valid;
3. at least 20 of 100 seeds must take off (`peak_prevalence >= 10`) before a
   conditional attack-rate median can be interpreted;
4. a hull x rung cell is anchor-admissible only when A1, A2, A4, and A5 all
   pass under `score_anchors.py`'s frozen aggregation;
5. a rung is campaign-admissible only when the same rung is admissible on all
   four hulls;
6. disjoint passing rungs are reported as disjoint regions, never interpolated
   through a failing rung;
7. if no rung passes, the result is no admissible common dose in the declared
   box; neither the box nor another constant is moved as a rescue;
8. bit-collapsed rungs cannot contribute independent evidence and must be
   reported before interpretation.

## 7. Run counts and cost of the now-blocked lattice

Had the axis resolved, the minimum campaign lattice would have been:

| Hull class | Complement | Epochs | Seeds/rung | Rungs | Voyages |
|---|---:|---:|---:|---:|---:|
| expedition | 450 | 288 | 100 | 5 | 500 |
| classic | 1,910 | 288 | 100 | 5 | 500 |
| spirit | 3,000 | 288 | 100 | 5 | 500 |
| mega | 7,000 | 288 | 100 | 5 | 500 |
| **total** | — | — | — | — | **2,000** |

Planning estimate, one vCPU per voyage: expedition 10, classic 75, spirit 100,
and mega 150 vCPU-hours per 100-seed hull x rung cell, or about 1,675
vCPU-hours for all 20 cells. This is only a design bound; the canary runtime
would replace it. Since the axis is blocked, no production manifest or cost is
committed and this lattice must not be submitted.

## 8. Preflight gate for a successor, not this blocked design

A later execution session may enter the campaign-preflight sequence only after
a successor design supplies a resolving axis and its own probe evidence:

1. local smoke proving the override reaches the engine and the output contract
   is unchanged;
2. `--dry-run` count exactly matching the frozen lattice;
3. immutable image digest plus exact job-definition revision, never a bare
   mutable tag;
4. exact manifest artifact and content hash recorded;
5. canary of at least 20 seeds at one cell;
6. stop and report canary runtime, artifact contract, failures, and revised
   cost before any array decision.

None of those steps was executed beyond local probe/smoke work in this design
session.

## 9. Single open decision

The common-dose refit cannot proceed as a `dose_adjustment` ladder on the
current mechanism coordinate. The next decision is which ledger-level repair
owns the disconnect: either explicitly withdraw the continuous-release axis as
a transmission-dose control, or design a separately provenance-frozen,
RNG-safe recipient-dose axis whose physical meaning and dose-bearing consumers
are demonstrated before any refit campaign is designed.
