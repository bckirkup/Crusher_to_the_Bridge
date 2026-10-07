# LEDGER — covid_crew_berth_01

Campaign mechanics for the CREW-BERTH-01 design
(`docs/covid/covid_crew_berth_01_design.md`,
`picard_framework/runs/covid_crew_berth_01_design.json`).

## 1. Spec

| Field | Value |
|---|---|
| Queue | `picard-analysis-queue` (Fargate `picard-analysis-fargate-queue` per aws_batch drought playbook) |
| Jobdef | `picard-covid-crew-berth-01` (+ `-fargate` if needed) |
| Image tag | `covid-crew-berth-01` |
| S3 prefix | `s3://crusherbucket-994254241749-us-east-1-an/campaign/covid_crew_berth_01/` |
| Resources | 1 vCPU / 2048 MB |

## 2. Blocks

`{theta, arm_id}` cells resolved inside the design JSON's enumeration —
`entry.py` translates (block args, seed) into the cell worker argv.

| Block | Arm | SOP | Seeds |
|---|---|---|---|
| `shipped_baseline` | shipped corner | SOP-017 | 20200205–20200224 (20) |
| `mess_boxed_base` | base corner | SOP-017-MESSBOX | 20200205–20200224 (20) |
| `berth_cohort` | re-deal only | SOP-017-BERTHCOH | 20 |
| `berth_rezone` | re-deal + D4 block | SOP-017-BERTHRZ | 20 |
| `work_pods` | 2-pod shifts | SOP-017-PODSHFT | 20 |
| `combined` | rezone + pods (CANARY) | SOP-017-BERTHPODS | 20 |

Total: 120 cells. Submission order: `combined` canary first — the family
ceiling falsifies cheapest; the ladder only runs on the owner's go-ahead.

## 3. Runs

| Date | Block | Seeds | Cells | Job | SHA | Digest | Wall | Result |
|---|---|---|---|---|---|---|---|---|
| 2026-10-07 | declared | — | 0 | — | a1961d17 | — | — | design frozen pre-run |

## 4. Notes

- `readout.py` audits the berthing/cohort witness echoes (modes, params,
  applied/restored epochs, re-deal tallies, `mixed_status_cabins == 0`)
  on top of the carried CW-02/MEAL-SVC-02 invariants, and pairs
  `mess_boxed_base` seed-for-seed against the CREW-MESS-01
  `sect_mess_boxed` canary cells as the DRIFT witness.
- Verdict grammar binds on `combined`; weaker arms read with the same
  machinery for the decomposition.
- `tools/covid_berth_attribution.py` reruns on the canary seeds after
  the readout lands (mechanism attribution check).
