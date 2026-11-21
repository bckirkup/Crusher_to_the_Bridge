# FLU-CONTAM-SOLVER-01
**Date:** 2026-11-21
**Commit:** #1382
**Pathogens:** influenza_a
**Status:** measured
**Measured at:** 77235441

Paired `ContamXTransportEngine` (`contamx`) vs. `ContamTransportEngine` (`native`) organic `influenza_a` (`active_profiles`, 288 epochs, seeds `8105`–`8124`, 20 paired seeds per hull) across all 7 commissioned current cruise ship hulls on AWS Batch (`picard-flu-contam-solver-01:1`, `:2`, `:3`, ECR digest `sha256:23c5e8286e25bbcb911772e05145d7f43781667c65da9760ff57b3751c0136f2`, 280/280 verified cells; historic naval vessels excluded).

- **Ensemble outbreak comparison (measured):** No statistically detected directional shift on any hull (exploratory Wilcoxon signed-rank p = 0.148–1.000) or pooled across 140 pairs (mean paired diff +0.26 onboard acquisitions, p = 0.8942; median paired difference 0.0 on 6/7 hulls and +1.0 on `diamond_princess`, where arm medians are 29.5 vs. 29.5; `mega_cruise_5000` mean 4.40 native vs. 4.30 ContamX, paired diff −0.10, p = 0.8726). Non-significance alone does not establish a formal equivalence bound.
- **HVAC-airborne regimes (measured):** `diamond_princess` (741/888 native vs. 744/932 ContamX `hvac_airborne`-dominant) and `greg_mortimer` (62/100 vs. 56/87) exhibit active HVAC-airborne transmission with large symmetric per-seed swings that cancel across seeds; `expedition_cruise_450`, `classic_cruise_1900`, `spirit_cruise_3000`, `explorer_seas_06`, and `mega_cruise_5000` are droplet/caregiver-driven (1 total `hvac_airborne`-dominant infection per arm across 100 pairs).
- **Worker-measured compute (measured):** 20.90 h native vs. 21.80 h ContamX summed per-cell wall (1.043×); 21.02 vs. 21.92 vCPU-h summed CPU (1.043×); `contamx3` child CPU totaled 3.64 s across all 140 ContamX runs (0.0046%); peak RSS 650 vs. 676 MB on `mega_cruise_5000` (1.061× wall/CPU).
- **Full provenance, tables, and Edison bundle:** `campaigns/flu/contam_solver_01/LEDGER.md` and `campaigns/flu/contam_solver_01/readout_7hull/`.
