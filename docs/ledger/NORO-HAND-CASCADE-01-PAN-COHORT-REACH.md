# NORO-HAND-CASCADE-01-PAN-COHORT-REACH
**Date:** 2026-11-15
**Commit:** 1ffda34a
**Pathogens:** norwalk_gi
**Status:** measured
**Measured at:** 1d1a60a0

Posted-cell provisioned-lot pan cohorts were measured on `fl_exp_12d_sens_p06_paxv`, `carriers_ordered`, seeds 8073/8038/8046/8047/8077 under `PYTHONHASHSEED=1`. The probe ran at `1d1a60a0` before PR #1229 merged; `git diff 1d1a60a0..1ffda34a` for `engines/transmission_core.py`, `picard_framework/simulation/ship_simulation.py`, `engines/infection_dynamics_bridge.py`, `data/pathogens`, and `data/platforms/expedition_cruise_450` is empty, so the numbers are current for this mechanism.

Method: `tools/noro_diag/pan_cohort_reach_probe.py` is read-only. It wraps `TransmissionCore._cs_object_emit_pans` inside the full-payload `growth_chain_census` instrumentation to capture provisioned-lot `cohort_ids`, `taker_ids`, and window takers, then joins never-takers to acquired-source `pickup` rows, donor-CS `hand_contact` rows, and non-`common_source_food` acquisitions. Contact dose is counted once per `(agent, epoch)` because `growth_chain_census` emits one contact row per donor with the same total dose. Buckets are `before_cs`, `cs_span_pre_q`, `cs_span_post_q`, and `after_cs`, with first quarantine from the voyage timeseries.

Measured: across 121 provisioned-lot service windows, there were 1,064 unique cohort agents, 825 ever-takers, and 239 never-takers. Service-window person-events were 5,095 cohort / 1,497 taker / 3,598 non-taker. Of the 239 never-takers, 196 (82.0%) had at least one acquired-source exposure candidate after their first cohort epoch, but only 8 (3.3%) had a secondary acquisition; all 8 were `fomite`, with 7 after the CS span and 1 in `cs_span_post_q`. Earliest exposure buckets for exposed never-takers were `cs_span_pre_q` 113, `cs_span_post_q` 9, and `after_cs` 74. Acquired-source dose reaching never-takers was dominated after the span: pickup dose 292,584.8 GEC after vs 41.8 pre-Q and 2,559.5 in-span post-Q; contact dose 366.3 after vs 0.9 pre-Q and 216.7 in-span post-Q.

Per-seed never-takers: 8073 = 16 cohort never-takers / 14 exposed / 0 secondary; 8038 = 17 / 12 / 1; 8046 = 31 / 26 / 1; 8047 = 72 / 54 / 1; 8077 = 103 / 90 / 5.

Inferred: the pan serving cap bounds direct servings but not acquired-source reach; most non-takers are reachable by secondary mass, yet conversion to secondary infection is rare and late. Hypothesis: the missing posted-outbreak tail is not that unexposed diners remain unreachable; it is that secondary dose arrives mostly after the pan span/quarantine and converts poorly, so the lever is earlier/higher conversion in the first ~20-40 epochs rather than merely more exposure reach. This is consistent with the non-cruise meal-AGE literature read that large non-foodborne symptomatic tails are uncommon in single-meal settings unless transmission persists over successive days.

Next decision: test early post-burst secondary conversion levers (earlier presymptomatic shedding/deposition amplitude, faster quarantine onset/compliance, or food-service secondary routes) before any per-contact CE geometry work.
