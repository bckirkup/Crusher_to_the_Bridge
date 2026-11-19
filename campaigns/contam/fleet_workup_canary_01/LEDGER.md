# contam/fleet_workup_canary_01 — ledger

Four-hull canary of the fleet native-vs-ContamX workup
([protocol](../../../docs/audits/2026-11-19_contam_fleet_workup_protocol/README.md)).
Non-biological, whole-hull aggregates and run times only. One Batch job, not
an array. The other 73 hulls are not run from here.

## Pins

| What | Value |
|------|-------|
| Input commit (hull files) | `d5d50d3a7bc30d50231e6f27b5083925f26c9c23` |
| Design commit | `fb6a0bd5b7109dff288dd7fbf5d4681805016db3` (PR #1333) |
| Frozen design copy | `design/frozen/`, byte-identical to the audit evidence; `SHA256SUMS` passes |
| Criteria | `design/canary_criteria.json` |
| ContamX | NIST 3.4.0.3 64 bit, executable SHA-256 `d14dc8020bd5e9f95962af52f46b7ce85e2899b63306309d6590cec652274b2b`, archive SHA-256 `3612798dff9a4f1ea4f0279c4c7b526b244b88875dea425fafd868f3570df4fa` |

ContamX provenance, checked 2026-11-19: the archive downloaded from
`https://www.nist.gov/document/contam-x-3403-linux-64bittargz` has the
archive hash above and contains the executable with the hash above, the same
executable the two-hull reference ledger used. NIST states the software is
public domain (17 U.S.C. 105) and may be redistributed freely. It is staged
only under the campaign's private S3 prefix; it is not committed and not
published.

## 2026-11-19 — smoke finding, before any timing

Measured locally (untimed configuration smoke, all four canary hulls,
harmonized commissioned export):

- Halving outdoor-air fraction changes the exported PRJ text and **no solved
  path flow** (max |ΔFlow0| = 0 exactly).
- ContamX reports Flow0 = 0 on every simple-AHS outdoor-air, exhaust and
  recirculation path. Terminals carry the flow.
- Wind reaches the solver: 1 → 10 m/s moves solved flows on the three
  weather-applicable hulls.

Inferred: in the ContamX lane, outdoor-air fraction is realized only in the
import-side recirculation synthesis, which is shared model code. The frozen
outdoor-air check ("exported AHS outdoor-air flow equals declared") would
have passed as a configuration echo.

Reported to Benjamin before any timed work. Ruling: *"Separate solved airflow
from downstream mixing, then benchmark both."*

## 2026-11-19 — prospective amendment (CONTAM-FLEET-WORKUP-CANARY-01)

Frozen in `design/canary_criteria.json` before any timed execution. The
matrix, hulls, row IDs, lanes, settings and repetitions are unchanged.

- Two labelled output blocks per row. `solved_airflow`: sums over the lane's
  own field; a quantity ContamX does not resolve is blank with a reason, not
  0. `downstream_mixing`: the shared mass-balance operator on that field,
  derived, not an independent ContamX result.
- The outdoor-air gate now reads realized effective mixing from the
  operator's legs in both lanes, and requires realized terminal flow to stay
  put.
- The weather gate requires the solved field to move at 10 m/s, not only the
  exported weather record.
- Two new tolerances (1e-3) for solved volumetric ratios, set before any such
  ratio was measured; all other tolerances are the protocol's 1e-9.
- `hull_balance_residual_m3h` is the sum of zone net inflow (boundary plus
  terminals), because the AHS ambient paths are unresolved.
- Added timing phases `input_read`, `field_reduce`, `process_total`.
- The in-job smoke adds 53 untimed solves, reported apart from the 318 timed.

Honest limit on "prospective": the criteria were written after the
outdoor-air finding above and one untimed destroyer mechanics check, and
before any canary metric table or timing existed. The first full local smoke
then passed every gate without a criteria edit.

## Local smoke (untimed), this commit's code

`python3 tools/diag/contam_fleet_workup_run.py --mode smoke` with the pinned
executable: 77 of 77 cells completed, every gate passed (993 checks, 0
failed). Margins: tracer closure ≤ 1.4e-14; operator sum-of-parts ≤ 2.3e-15
relative; outdoor-air rows move effective outdoor-air fraction by 0.075 to
0.425 with terminal flow change exactly 0; at 10 m/s some solved aggregate
moves by 0.93 to 1.16 relative on each weather-applicable hull. This is a
gate result, not a benchmark; no local timing is reported.

## 2026-11-19 — canary run and readout

- Image `picard-campaign:contam-fleet-workup-canary-01@sha256:92eaa848ab686f7149beb046293968ef2fab7e7ec9821a76ad733a154ae0a121`,
  built from root `Dockerfile` + `deploy/aws/Dockerfile.campaign` at
  `5f524b81`. The in-image smoke passed every gate before the push. The
  digest was pinned in `campaign.json` in the next commit (`campaign.json`
  is the only file that differs from the image).
- ContamX archive staged at
  `s3://crusherbucket-994254241749-us-east-1-an/campaign/contam_fleet_workup_canary_01/external/`;
  anonymous GET and LIST return 403.
- Job definition `picard-contam-fleet-workup-canary-01:2` (`:1` is the
  identical `--register-only` revision). One job, not an array:
  `3940f345-8c40-4dcb-842b-800d44178266`, 1 attempt, SUCCEEDED, about 10
  minutes on `c7a.8xlarge` `i-03338f7ba9911b6ae`.
- In-job gates: 993 checks, 0 failed. 462 timed cold cells, 318 timed
  solves, 385 cached repeats, no timeout.
- Raw artifact `canary/canary_raw.tar.gz`, SHA-256
  `0441e19ca3db1577d08bc7225188f251181f432b7fabccd53a66e97bde8bbfb9`,
  reduced offline into `readout/`; audit passed 14 of 14.
- Readout: [READOUT.md](READOUT.md).

**Stopped here.** No other job was submitted. Open decision: run the other
73 hulls or not.
