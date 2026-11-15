# CONTAM-BDQ-LAMINAR-01
**Date:** 2026-11-15
**Commit:** c8dbb22fe14d58bcc864e2993c0c358c1cebb67d
**Pathogens:** all
**Status:** open
**Measured at:** 5f693f81ff2298fb73afe44ba8d6899e926ced33

Edison's paired diagnostic (2026-11-15) was verified against the exporter: every declared one-way passive `pressure_opening` cross-zone link was emitted as NIST TN 1887r1 `plr_bdq` (Contam element icon/type 24) with the first parameter, the laminar flow coefficient `lam`, set to zero. With the official NIST ContamX 3.4.0.3 binary that made the opening solve zero forward flow even under forward pressure.

The fix implements the documented TN 1887r1 §8.3.3 laminar-transition calculation for commissioned exports only: reference air viscosity `1.81625e-5 kg/(m·s)`, transition Reynolds number 30, discharge coefficient 0.6, transition mass flow `F_trans = mu Re A / D`, transition pressure from the turbulent powerlaw coefficient, and `Ck = mu F_trans / (rho dP_trans)`. Design-mode emission is unchanged so committed Contam bundles remain byte-stable; the native transport lane is unaffected because it uses declared flows.

Verification at the measured SHA: structural tests pin the commissioned `plr_bdq` parameter order `(lam, Cp, xp, Cn, xn)`, positive `lam`, and the documented `C**1.5` laminar-coefficient scaling for `n=0.5`. The live two-zone ContamX control solved forward pressure to 99.836 m3/h through a 120 m3/h design opening, reverse pressure to -0.0 m3/h, and equal pressure to 0.0 m3/h. Hull-level commissioned checks restored sanitary make-up forward flow where pressure allows: `destroyer_baseline` 7/7 forward with 478.085 m3/h aggregate, and `expedition_cruise_450` 20/53 forward with 1372.394 m3/h aggregate (the remaining Expedition paths stay shut under adverse pressure). `tools/contam_commissioned_check.py` now reports passive one-way forward/reverse counts and fails on reverse flow.

Scope is future commissioned exports only. Frozen Phase 1/2 caches, committed readouts, existing ledgers, and hull declarations are untouched; no recorded measurement is invalidated, so no open-ledger notes were added.
