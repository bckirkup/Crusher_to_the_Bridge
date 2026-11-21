# FLU-CONTAM-SOLVER-01
**Date:** 2026-11-21
**Commit:** #1382
**Pathogens:** influenza_a
**Status:** measured
**Measured at:** 77235441

Paired `ContamXTransportEngine` (`contamx`) vs. `ContamTransportEngine` (`native`) organic `influenza_a` (`active_profiles`, 288 epochs, seeds `8105`–`8124`, 20 paired seeds per hull) across 6 commissioned current cruise ship hulls on AWS Batch (`picard-flu-contam-solver-01:1`, ECR digest `sha256:23c5e8286e25bbcb911772e05145d7f43781667c65da9760ff57b3751c0136f2`, 240/240 verified cells; historic naval vessels excluded; `mega_cruise_5000` held).

- **Ensemble outbreak comparison (measured):** No statistically detected directional shift on any hull (exploratory Wilcoxon signed-rank p = 0.148–1.000) or pooled across 120 pairs (mean paired diff +0.32 onboard acquisitions, W = 1120.0, p = 0.9048; median paired difference 0.0 on 5/6 hulls and +1.0 on `diamond_princess`, where arm medians are 29.5 vs. 29.5). Non-significance alone does not establish a formal equivalence bound.
- **HVAC-airborne regimes (measured):** `diamond_princess` (741/888 native vs. 744/932 ContamX `hvac_airborne`-dominant) and `greg_mortimer` (62/100 vs. 56/87) exhibit active HVAC-airborne transmission with large symmetric per-seed swings that cancel across seeds; `expedition_cruise_450`, `classic_cruise_1900`, `spirit_cruise_3000`, and `explorer_seas_06` are droplet/caregiver-driven (1 total `hvac_airborne`-dominant infection per arm across 80 pairs).
- **Worker-measured compute (measured):** 12.64 h native vs. 13.04 h ContamX summed per-cell wall (1.032×); 12.74 vs. 13.13 vCPU-h summed CPU (1.031×); `contamx3` child CPU totaled 2.49 s across all 120 ContamX runs (0.005%); peak RSS 359 vs. 385 MB on `explorer_seas_06`.
- **Full provenance, tables, and Edison bundle:** `campaigns/flu/contam_solver_01/LEDGER.md` and `campaigns/flu/contam_solver_01/readout_6hull/`.
