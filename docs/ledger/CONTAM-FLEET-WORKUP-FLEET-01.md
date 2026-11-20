# CONTAM-FLEET-WORKUP-FLEET-01
**Date:** 2026-11-20
**Commit:** d5d50d3a7bc30d50231e6f27b5083925f26c9c23
**Pathogens:** all
**Status:** measured
**Measured at:** 56b1a990f64edae1f95eb32588d0017a34db6d0f

**Completes [CONTAM-FLEET-WORKUP-PROTOCOL-01](CONTAM-FLEET-WORKUP-PROTOCOL-01.md)
under the criteria of [CONTAM-FLEET-WORKUP-CANARY-01](CONTAM-FLEET-WORKUP-CANARY-01.md),
unchanged.** No pathogen, occupant or stochastic outcome is involved; no
seeds apply.

**Result.** The remaining 73 hulls ran on AWS Batch in eight serial jobs
after an untimed all-73 gate job. With the corrected canary (run 2) the 77
hulls cover all 2,156 matrix rows once: 1,591 executed and ok, 525
`structural_nonresponse`, 40 `not_applicable`; 9,546 timed cold cells (6,810
ContamX solves), 7,955 cached repeats, no timeout; 20,649 in-job gate checks,
0 failed. Baseline, ContamX over native across hulls: supply total 1 to
1.012; whole-hull air change 0.9998 to 1.008; effective outdoor-air fraction
exactly 1; gross interzone flow 0.012 to 4.51; tracer material time 0.53 to
1.52. The two as-shipped ContamX baselines agree with each other on every
hull and differ from the harmonized one in outdoor-air inputs on 68 hulls.
Full readout: `campaigns/contam/fleet_workup_fleet_01/READOUT.md`.

**Package.** `contam_fleet_workup_77_package_02.tar.gz`, SHA-256
`3bc0e40f4d7a03082bbb6caf01ff76257163d7da8daee672f55a80c406f9684d`, whole-hull
aggregates only, with a standard-library verifier (51 of 51 checks on a
clean unpack). It supersedes package 01 (`77366e25…`), which overstated
run-time input hashing: the canary job hashed its own 27 pinned files, each
fleet job all 392. Data tables are identical in both. Prepared only; not transferred anywhere outside the private
campaign prefix.

**Where.** Campaign `contam/fleet_workup_fleet_01`; running record in its
`LEDGER.md`. Packager `tools/diag/contam_fleet_workup_package.py`, verifier
`tools/diag/contam_fleet_workup_verify.py`.

**Limits.** Two models are compared numerically; neither is validated
against a ship. The downstream block shares one mass-balance model across
lanes. Run times are per cohort and host, never pooled.
