# CONTAM-FLEET-WORKUP-FLEET-01 ledger

Stage: the 73 hulls the canary did not run, then the 77-hull offline package.
Settled inputs, not re-derived: design `fb6a0bd5b7109dff288dd7fbf5d4681805016db3`
(#1333), hull inputs `d5d50d3a7bc30d50231e6f27b5083925f26c9c23`, canary
criteria and corrected canary run 2 (#1335, job
`ac1b56e1-2080-40cc-be8f-b8473ceca793`, raw SHA-256
`b99690680cd30331d4af0ad9e3afba5543d4499668e19c42205cf272f5a7ac8b`). Canary
run 1 is not used anywhere in this stage.

## What changed in the machinery, and what did not

- New: `design/fleet_selection.json` (selection metadata: roster as frozen 77
  minus canary 4, eight alphabetical cohorts, expected counts, authored
  `platform.prj` SHA-256 for the 73 hulls copied from the frozen manifest).
- Runner: `--selection`, `--cohort`, modes `fleet` and `fleet_gate`. Reducer:
  hull list and expected counts from the selection.
- Unchanged: cell, gates, criteria, tolerances, matrix, row IDs, settings,
  repetitions, timer boundaries, repeat order, one thread, one cell at a time.
- Parity: reducing the committed canary records with the changed reducer
  reproduces all 18 committed readout files byte for byte.

## Preflight (nothing timed)

- All 392 pinned input files match the checkout at the build commit. Every
  fleet job (gate and cohorts) re-hashes all 392 in the image before and
  after. The canary job, run earlier under its own runner, hashed 27.
- Local untimed smoke, all 73 hulls: 1,514 of 1,514 cells, all gates passed.
- In-image untimed smoke, cohort 7: 189 cells, all gates passed.
- Image `picard-campaign:contam-fleet-workup-fleet-01@sha256:0a25129f30ec04c66c7c83d5e446c73889a81c188e4985d475aaf36791ae4f79`,
  built from `Dockerfile` + `deploy/aws/Dockerfile.campaign` at
  `56b1a990f64edae1f95eb32588d0017a34db6d0f`, base
  `python:3.11-slim@sha256:07d4824036af339fa1b6ef769cc99d9c10a141769538b52b3b597c84f7a7b535`.
  `campaign.json` (the digest pin) is the only campaign file newer than the image.
- Batch gate job `ebb91831-7b40-4346-82d5-9594d0de7c63`, job definition
  `picard-contam-fleet-workup-fleet-01:1`, not an array, 1 attempt,
  `c7a.4xlarge`, 23.9 min: 1,514 cells ok, 19,656 gate checks, 0 failed, no
  blocker, inputs unchanged. Raw `gate/fleet_gate_raw.tar.gz`, SHA-256
  `d801fdcda37304cd94c1f7b89d8cbb6e5ceb67890a6c3a8020289c41ec984fcb`.
  Solved block identical to the local smoke on every row; downstream values
  within 4.4e-15 relative (residuals within 1.9e-9 m³/h absolute).

## Timed run

Eight jobs, submitted singly (`scripts/campaign submit --canary --index N`),
each only after the previous one's artifact was fetched and its
`smoke_gates.json` read as passed with no `blocker.json`. No two overlapped.
Each submission registered an identical job definition revision (2 to 9).
Job IDs, hosts, attempts, wall time, gate counts and raw artifact hashes are
in `READOUT.md` and `readout/cohorts.csv`; `readout/jobs/` holds each job's
receipt and reduction audit (14 of 14 checks in every cohort).

- Cohort 4 (`9a1564dc-…`) and cohort 7 (`99b9d3f6-…`): first attempt ended
  with "Host EC2 … terminated" (Spot reclaim) after 5.1 and 7.3 min; Batch
  retried on a new host. Nothing of the first attempt survives; the artifact
  is written once, at the end. `reporting_attempt` equals `attempts` for
  every cohort.
- Hosts drawn: `c7i.8xlarge` (Xeon 8488C) for cohorts 0, 4, 5, 6;
  `c7a.4xlarge` (EPYC 9R14) for cohorts 1, 2, 3, 7. Timings are per cohort.
- One operator error, no effect on results: `collect_job.sh` was edited
  while the cohort 0 collector was running it, so that collector died with a
  shell syntax error after the job had already succeeded. The chain was
  restarted from a copy of the script, picked the same job up by its saved
  ID, and submitted nothing twice.

## Package (01, superseded; see the correction below)

- `contam_fleet_workup_77_package_01.tar.gz`, 4,573,577 bytes, SHA-256
  `77366e25c6b4c388516dc0c2650b6baf207ae1b9585f820c272d1226028c5964`; built with
  the packager and verifier at `c2a06e39`. Private copy:
  `s3://crusherbucket-994254241749-us-east-1-an/campaign/contam_fleet_workup_fleet_01/package/`
  (anonymous GET returns 403). Not sent anywhere else.
- Contents: 11 aggregate CSVs, the frozen design with its own checksums,
  criteria, selection, `EXPECTED.json`, `README.md`, `per_hull_readout.md`,
  `verify.py`, `SHA256SUMS`. No raw record, solver file, geometry or log.
  `readout/` in this directory holds the small files; the large tables live
  only in the archive.
- Clean-directory check: unpacked into an empty directory and run with the
  system Python, isolated mode, in a network namespace with no interfaces:
  48 of 48. External `.sha256` matches.
- Rejection checks on the unpacked package, each re-summed so the checksum
  alone would pass: missing row, duplicate row, blank replaced by 0, phase
  relabelled, timing sample moved to another cohort, cohort job ID swapped,
  extra raw file, dropped repeat. Each failed the check that names it. A
  flipped byte without re-summing fails the checksum.

## Correction: package 01 superseded by package 02

- Parent found that package 01's README, the readout and this ledger said
  every job hashed all 392 pinned inputs. Checked against the retained
  records: canary run 2's `environment.json` holds 27 entries before and 27
  after (4 hulls × 5 files + 7 shared); the gate job and each of the eight
  cohort jobs hold 392 and 392. In all ten records the path set equals the
  manifest set of that scope, every digest equals the manifest's, and before
  equals after. The claim was wrong for the canary cohort only; no
  measurement is affected.
- Package 02 adds `data/input_verification.csv` (per cohort: scope, counts,
  set digests before and after, taken from the retained record) and three
  verifier checks that recompute each scope's digest from
  `design/input_manifest.json`. A package that claims 392 for the canary is
  refused. README wording corrected there and in four other places found on
  re-reading against the code and data: `end_to_end` is its own clock and
  excludes `input_read` (it was described as a sum); `process_total` is the
  parent's launch-to-exit time; supply air change ×1.5 is the design's
  redundancy check on duty ×1.5; harmonization is of the outdoor-air
  fraction, as the protocol states; lane order alternates by repeat.
- The eleven data tables, design files and `per_hull_readout.md` are
  byte-identical between 01 and 02. Changed: `README.md`, `EXPECTED.json`
  (id, `supersedes`), `verify.py`, `SHA256SUMS`; added:
  `data/input_verification.csv`.
- `contam_fleet_workup_77_package_02.tar.gz`, 4,575,643 bytes, SHA-256
  `3bc0e40f4d7a03082bbb6caf01ff76257163d7da8daee672f55a80c406f9684d`; verifier 51 of 51
  on a clean offline unpack; rebuild reproduces the hash. Rejection checks
  run on it: flipped byte, missing row, duplicate row, blank replaced by 0,
  relabelled phase, canary claiming 392, a fleet count of 391, a dropped
  receipt row, a changed manifest digest. All refused.
- Package 01 stays in the private prefix untouched, and its checksum file is
  kept under `readout/superseded/`. No job was run for this correction.

## Regenerate

```
for i in 0..7:  aws s3 cp <prefix>/fleet/fleet_cohort$i_raw.tar.gz .   # check SHA-256 against READOUT.md
                tar -xzf … -C raw$i
                python3 tools/diag/contam_fleet_workup_reduce.py --raw raw$i --out red$i \
                    --selection campaigns/contam/fleet_workup_fleet_01/design/fleet_selection.json --cohort $i
                cp campaigns/contam/fleet_workup_fleet_01/readout/jobs/cohort$i.job.json red$i/job.json
python3 tools/diag/contam_fleet_workup_package.py build \
    --cohort canary_run2=campaigns/contam/fleet_workup_canary_01/readout \
    --cohort fleet_cohort0=red0 … --cohort fleet_cohort7=red7 \
    --out pkg/contam_fleet_workup_77_package_02 --archive pkg/contam_fleet_workup_77_package_02.tar.gz
```

The archive is byte-reproducible (sorted members, zero timestamps), so the
SHA-256 of package 02 is the check.

## Stopped here

No further job was submitted. Nothing was sent to Edison or published.
Open decision: whether and how to hand the package over.
