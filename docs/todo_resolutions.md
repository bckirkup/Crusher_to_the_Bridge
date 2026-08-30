# TODO Resolutions for Crusher-to-the-Bridge Within-Host Infection Dynamics Spec v1.0

**Source:** `/workspace/formal_spec_v1.md` (5 TODOs in Appendix C)  
**Canonical SHA:** `d557f39f1692f72ff26b67b4074a5ae68e03b4c2`  
**Date:** 2026-08-30

---

## TODO-1: Cumulative Exposure Auto-Decay (§3.6)

### (a) Current Behavior Summary

**`cumulative_exposure`** is a `dict[str, float]` on each `KorkinAgent`, initialized to `{}` at agent creation (`infection_dynamics_bridge.py:394`).

| Operation | Location | Behavior |
|---|---|---|
| **Accumulate** | `transmission_core.py:1520–1524` | Each epoch, `effective_dose` is added: `cumulative_dose = agent.cumulative_exposure.get(pathogen_id, 0.0) + effective_dose` |
| **Reset on establishment** | `transmission_core.py:1539` | Set to `0.0` when infection establishes |
| **Reset on recovery** | *nowhere* | **Never cleared.** The recovery path (`orchestrator_epoch.py:496–497`) transitions `inf["status"]` to `RECOVERED` but does not touch `cumulative_exposure`. |
| **Decay** | *nowhere* | **Never decayed.** No exponential decay, no time-based windowing, no auto-reset. |
| **Read during establishment** | `transmission_core.py:1525–1527` | The *per-epoch* effective dose (not cumulative) feeds the dose-response hazard. Cumulative dose is passed to `_establish()` as `acquired_particles` only. |

The test suite confirms this exactly:
- `test_dose_accumulation.py:177` asserts the value accumulates across epochs.
- `test_dose_accumulation.py:181` asserts it resets to 0.0 on establishment.
- `test_dose_accumulation.py:189` asserts re-infection after manual recovery uses a fresh cumulative value — but only because the test *manually* sets `infection_status = RECOVERED`, which causes the agent to re-enter the susceptible pool and receive a new dose. No code resets the stale cumulative value itself.

**Consequence:** If an agent receives sub-infectious doses over many epochs, then goes unexposed for a long period, the stale cumulative dose persists indefinitely. If the agent later receives a new dose and establishes, the `acquired_particles` will include arbitrarily old inoculum — biologically implausible for mucosal pathogens where non-replicating particles are cleared within hours to days.

### (b) Recommended Resolution

**Add an optional auto-decay rate parameter, `cumulative_exposure_decay_rate_per_day` (default 0.0 = no decay).** This is distinct from the pre-establishment `inoculum_clearance_rate_per_day` already specified in §3.2 — and in fact the same parameter can serve both purposes. The §3.2 exponential clearance already implements exactly this decay: `C(t+1) = [C(t) + D_eff(t)] · exp(-λ · dt)`. No additional mechanism is needed beyond what §3.2 specifies; the TODO reduces to mandating the reset on recovery.

Concretely:

1. **SPEC-CLEAR-01** (already in §3.6): Reset `cumulative_exposure[pathogen_id]` to `0.0` when the infection transitions to `RECOVERED`. This is a one-line addition in the recovery path of `orchestrator_epoch.py` (after line 497).
2. The `inoculum_clearance_rate_per_day` parameter from §3.2 handles the auto-decay during periods of no exposure. When this rate is `> 0`, cumulative exposure decays exponentially every epoch regardless of whether new dose arrives — solving the stale-dose problem.
3. No separate "no-dose window" timer is needed. Exponential decay is both simpler and more biologically defensible than a hard timeout.

### (c) Backward Compatibility Impact

- **Zero risk for default = 0.0**: With `cumulative_exposure_decay_rate_per_day = 0.0` and `inoculum_clearance_rate_per_day = 0.0`, behavior is identical to SHA d557f39.
- The recovery reset (SPEC-CLEAR-01) is a bug fix, not a new feature. It changes behavior only for agents who: (i) accumulate sub-infectious dose, (ii) recover from a *different* pathogen or via immunity, (iii) and are later re-exposed. This scenario is rare in current 7–14 day voyages.
- 0 tests break: no existing test checks that stale cumulative exposure persists after recovery.

### (d) Spec Replacement Text

Replace the TODO at §3.6 (line 191 of the spec) with:

> **Resolution:** No separate auto-decay timer is needed. The `inoculum_clearance_rate_per_day` parameter (§3.2) already provides continuous exponential decay of the cumulative dose pool during all epochs, including periods of no new dose. When `inoculum_clearance_rate_per_day > 0`, the retained inoculum decays to negligible levels within $$\sim 5 / \lambda_{\text{clear}}$$ days without any new exposure. When `inoculum_clearance_rate_per_day = 0.0` (default, current behavior), no decay occurs — but SPEC-CLEAR-01 still mandates resetting cumulative exposure to zero on recovery, preventing stale dose from persisting across infection cycles. This combination is sufficient: biologically, an agent who recovers has either eliminated the pathogen (clearance) or mounted an immune response (protection ≥ 1.0, which blocks further dose accumulation via §4.2 step 3). No third mechanism is required.

---

## TODO-2: Fixed Recovery Day vs. Drawn Distribution (§5.5)

### (a) Current Behavior Summary

**`recovery_day`** is a **fixed integer** read from the pathogen profile. It is never drawn from a distribution.

| Aspect | Detail | Source |
|---|---|---|
| **Profile field** | `"recovery_day": int` | `active_profiles.json`: norwalk_gi = 3, sars_cov2_resp = 7 |
| **Read location** | `prof.get("recovery_day", 3)` | `orchestrator_epoch.py:483` |
| **Chronic extension** | `agent.get_chronic_recovery_day(pid, base)` adds integer `recovery_day_extension` from chronic diseases | `infection_dynamics_bridge.py:1066–1073` |
| **Total course** | `clearance_day = onset_day + recovery_day` (days) | `orchestrator_epoch.py:487` |
| **Strain clock** | Each co-resident strain clears at `clearance_day` independently | `infection_dynamics_bridge.py:727` |
| **Distribution** | None — fixed scalar, no draw, no variance | — |

The interaction with `incubation_period` is additive and independent: `clearance_day = onset_day + recovery_day`. The incubation period IS drawn from a distribution (lognormal or gamma), but recovery is fixed. The total infection course therefore has variance only through incubation, not through recovery duration.

**Who reads `recovery_day`:**
- `orchestrator_epoch.py:482–487` (the main progression loop)
- `infection_dynamics_bridge.py:711,727` (strain clearance in `advance_resident_strains`)
- `infection_dynamics_bridge.py:1066–1073` (chronic disease extension)
- 16 test files (53 total references across tests)

### (b) Recommended Resolution

**Replace fixed `recovery_day` with an optional drawn duration, using the same distribution infrastructure as incubation.** Specifically:

1. Add an optional `recovery` block to the pathogen profile, mirroring the `incubation` block:
   ```jsonc
   "recovery": {
     "distribution": "lognormal",   // or "gamma"; default "fixed"
     "median_days": 3,              // required; replaces scalar recovery_day
     "dispersion": 1.3,             // GSD for lognormal, CV for gamma; default 1.0 (= fixed)
     "min_days": 1,                 // default: 1
     "max_days": 14                 // default: 30
   }
   ```
2. When `"distribution": "fixed"` (or `recovery` block absent), behavior is identical to today: `recovery_day = median_days` (or the legacy scalar `recovery_day`).
3. When a distribution is specified, draw once per infection (like incubation) and cache as `infection["recovery_days"]`.
4. Chronic disease extension applies additively after the draw.
5. The drawn value replaces `recovery_day` in the clearance calculation: `clearance_day = onset_day + drawn_recovery`.

**Why:** The literature strongly supports heterogeneous infectious periods — Milbrath et al. 2013 reports norovirus shedding durations ranging from 1–22 days, and Teunis et al. 2015 shows lognormal shedding duration fits. A fixed recovery day produces artificially sharp epidemic troughs and underestimates tail shedding from supershedders.

### (c) Backward Compatibility Impact

- **Zero risk for `"distribution": "fixed"` (default)**: Legacy profiles with scalar `recovery_day` are automatically interpreted as `recovery.median_days` with fixed distribution. No behavior change.
- Chronic disease `recovery_day_extension` applies after the draw, so the extension interface is unchanged.
- **16 test files** reference `recovery_day`. Tests that pass a literal `"recovery_day": N` continue to work because the fixed-distribution path preserves the integer. Tests that assert exact timing will still pass at default settings.
- **Schema migration**: Add `recovery` as optional; keep `recovery_day` as a deprecated alias. A migration validator emits a deprecation warning if `recovery_day` is present without a `recovery` block.

### (d) Spec Replacement Text

Replace the TODO at §5.5 (line 510 of the spec) with:

> **Resolution:** Replace the fixed `recovery_day` with an optional drawn duration distribution. The pathogen profile gains an optional `recovery` block with the same structure as the `incubation` block (distribution family, median_days, dispersion, min/max truncation). When absent or when `distribution = "fixed"`, `recovery_day` = `median_days` (scalar, current behavior). When a distribution is specified, the recovery duration is drawn once per infection, cached as `infection["recovery_days"]`, and used in place of the fixed value. Chronic disease extensions apply additively after the draw. The legacy `recovery_day` integer field is retained as a deprecated alias for `recovery.median_days` with implicit `distribution = "fixed"`. Default shipped profiles use `distribution = "fixed"` at v1.0 to preserve deterministic reproducibility; switching to a lognormal or gamma draw is a configuration change, not a code change. **Evidence:** Lognormal fits to norovirus shedding duration (Milbrath et al. 2013), SARS-CoV-2 infectious period heterogeneity (Cevik et al. 2021). **Evidence grade: A (meta-analysis/prospective cohort).**

---

## TODO-3: Route-Specific Shedding Curves (§6.7)

### (a) Current Behavior Summary

Shedding is currently a **single scalar** per agent per pathogen per epoch, computed by `get_pathogen_shedding()` (`infection_dynamics_bridge.py:863–902`). The function:

1. Selects either `shedding_curve_log10` (symptomatic) or `asymptomatic_shedding_log10` based on illness status.
2. Indexes by days-since-onset to get a log10 value.
3. Applies `dose_adjustment`, host multiplier, and strain multiplier.
4. Scales by `clock.amount_per_epoch()`.
5. Returns a **single float** — the total emission.

Route-specific weighting is handled **downstream** in `transmission_core.py:1698–1716` by `_apply_route_weights()`, which multiplies each pathway's dose by a pathogen-specific weight from `transmission_route_weights`:

| Pathogen | direct_contact | droplet | hvac_airborne | fomite | food |
|---|---|---|---|---|---|
| `norwalk_gi` | 0.35 | 0.10 | 0.05 | 0.30 | 0.20 |
| `sars_cov2_resp` | 0.25 | 0.30 | 0.30 | 0.10 | 0.00 |

The route weights apply to the **receiver's dose**, not to the **emitter's shedding**. This means all routes see the same temporal shedding curve shape — the only difference is a constant scaling factor per route.

**No pathogen currently has separate respiratory vs. fecal shedding curves.** The `shedding_curve_log10` arrays in both shipped profiles are single curves representing total-body emission.

**Callers of `get_pathogen_shedding()`** (31 references across 10 files): All expect a single float return. The wastewater module (`ship_simulation.py:148`), mass deposition (`orchestrator_epoch.py:578`), transmission core (`transmission_core.py:2645`), and strain shares all consume a scalar.

### (b) Recommended Resolution

**Do not add route-specific shedding curves at v1.0. Keep the current architecture with a note for future extension.**

**Rationale:**
1. The current `transmission_route_weights` architecture already provides route-specific dose scaling. For single-tropism pathogens (all 12 shipped profiles), this is functionally equivalent to route-specific shedding curves with identical temporal shapes.
2. Route-specific shedding curves would only matter for pathogens where the *temporal shape* of shedding differs between routes (e.g., a pathogen that sheds fecally for 14 days but only aerosolizes during the acute 3-day window). None of the 12 shipped pathogens have literature supporting such divergent kinetics.
3. The engineering cost is high: `get_pathogen_shedding()` is called in 10 files (31 call sites), all expecting a scalar. Changing it to return a dict would break 31 callers and ~15 tests.
4. Norovirus vomitus aerosolization, the most compelling dual-route case, is episodic and better modeled as a stochastic emission event than as a separate shedding curve.

**Future extension path (v2.0):** If a pathogen requires route-specific temporal curves, the recommended design is:
- Add an optional `shedding_curves_by_route` dict to the profile (keyed by transmission route → curve array).
- `get_pathogen_shedding()` gains an optional `route: str` parameter; when omitted, returns the aggregate (sum over routes).
- `transmission_route_weights` become redundant when route-specific curves are present.

### (c) Backward Compatibility Impact

No changes at v1.0 — this is a decision to defer, not to implement. Zero tests affected.

### (d) Spec Replacement Text

Replace the TODO at §6.7 (line 588 of the spec) with:

> **Resolution (v1.0):** Route-specific shedding curves are deferred. The current architecture — a single shedding curve per pathogen scaled by per-route `transmission_route_weights` on the receiver side — is sufficient for all 12 shipped pathogen profiles, none of which have literature evidence for route-divergent shedding kinetics. The `transmission_route_weights` mechanism already provides route-specific dose proportioning with a constant per-route scaling factor. Route-specific shedding curves would only add value for pathogens where the *temporal shape* of emission differs materially by route (e.g., fecal shedding lasting 14 days while respiratory shedding peaks and resolves in 3 days). When such a pathogen is added, the extension point is an optional `shedding_curves_by_route: dict[str, list[float]]` on the profile, with `get_pathogen_shedding()` gaining an optional `route` parameter. The 31 existing callers continue to receive the aggregate scalar when `route` is omitted.

---

## TODO-4: Tissue Tropism Scope (§8.4)

### (a) Current Behavior Summary

**No tissue tropism, anatomical compartment, or organ-specific modeling exists anywhere in the codebase.**

| Search term | Python files | JSON/YAML | Schema files |
|---|---|---|---|
| `tropism` | 0 hits | 0 hits | 0 hits |
| `anatomical` | 0 hits | 0 hits | 0 hits |
| `tissue` | 10 hits | 0 hits | 0 hits |
| `compartment` | ~50 hits | 0 hits | 0 hits |

The `tissue` hits are all `wound_soft_tissue` — a clinical syndrome label, not an anatomical compartment. The `compartment` hits are all spatial/architectural (ship zones, deck compartments, SEIQR compartmental model references).

**No pathogen profile** (active 2, edison 10, enterprise TOS/TNG 4) contains any `tropism`, `portal`, `tissue`, or `compartment` field.

**No schema** defines tropism-related properties. The `pathogen_profiles.schema.json` has no tropism section.

Infection is modeled as a **scalar per-pathogen state on a whole-agent**. The `microflora_disruption` system tracks disruption magnitude by kingdom but does not partition infection into anatomical sites.

### (b) Recommended Resolution

**Tissue tropism should remain purely optional with no shipped pathogens requiring it at v1.0. No code changes needed.**

**Rationale:**
1. **Norovirus** (the primary use case suggested in the TODO): Its dual fecal-oral + vomitus-aerosol transmission is already handled by `transmission_route_weights` (`fomite: 0.30, food: 0.20, direct_contact: 0.35, droplet: 0.10, hvac: 0.05`). The vomitus-aerosol component is a brief episodic event, not sustained respiratory tropism. Tissue tropism would be over-engineering for this pathogen.
2. **SARS-CoV-2**: Purely respiratory. No dual tropism needed.
3. **Edison 10 pathogens**: All are either single-system enteric (norovirus GII.4, *Vibrio*, *Campylobacter*, *C. diff*) or single-system respiratory (SARS-CoV-2, influenza A, measles, *Legionella*, Andes hantavirus) or systemic via direct contact (Ebola). None have epidemiologically relevant dual tropism in the cruise context.
4. The literature evidence grade for tissue tropism is **D (modeling/expert consensus)** — no empirical data supports its necessity for the currently modeled pathogen set.
5. The §8.3 extension schema (optional `tissue_tropism` block with per-portal dose-response and shedding curves) is a clean future extension point that requires no current code changes.

### (c) Backward Compatibility Impact

No changes — this is a decision to confirm the status quo. Zero code, zero tests, zero schema modifications.

### (d) Spec Replacement Text

Replace the TODO at §8.4 (line 749 of the spec) with:

> **Resolution (v1.0):** No shipped pathogen requires explicit tissue tropism modeling. Norovirus dual-route transmission (fecal-oral + vomitus aerosol) is adequately captured by `transmission_route_weights` without anatomical compartments; the aerosol component is an episodic event, not sustained respiratory tropism. SARS-CoV-2 is single-system respiratory. All 10 Edison extended profiles are either single-system enteric, single-system respiratory, or systemic. The `tissue_tropism` block (§8.3) remains as a documented optional extension schema for future pathogens where tissue-dependent transmission or clinical course is epidemiologically relevant (e.g., a pathogen with materially different shedding kinetics from respiratory vs. GI sites). No code, schema, or configuration changes are required at v1.0. **Evidence grade for deferral: D (expert consensus)** — no published ABM of shipboard transmission has required tissue compartmentalization.

---

## TODO-5: Deprecate Agent-Level Infection Fields (§12.2)

### (a) Current Behavior Summary

The agent has **two parallel state representations**:

| Level | Fields | Source of truth? |
|---|---|---|
| **Per-pathogen** (`infections` dict) | `status`, `illness`, `time_infected`, `acquired_particles`, `shedding_multiplier`, `infection_epoch`, `strain_id`, `strains`, etc. | ✅ Yes — written by `_establish()` and `_advance_agent_pathogen_infections()` |
| **Agent-level** (scalar) | `infection_status`, `illness_status`, `time_infected`, `acquired_particles`, `shedding_multiplier` | ❌ No — shadow/projection of per-pathogen state |

**The projection mechanism** is `_project_legacy_illness()` (`orchestrator_epoch.py:500–530`), which rewrites agent-level fields from per-pathogen records every epoch:
- `infection_status` = `INFECTED` if any pathogen is active, else `RECOVERED` if was infected
- `illness_status` = `SYMPTOMATIC` if any active pathogen is symptomatic
- `time_infected` = max of active pathogen time_infected values
- Called at `orchestrator_epoch.py:554`, once per agent per epoch

**Consumers of agent-level fields:**

| Consumer category | Files | References | What it reads |
|---|---|---|---|
| **Production code (direct)** | 5 files | ~30 refs | `infection_status`, `illness_status`, `time_infected` |
| **Properties** (`is_infected`, `is_symptomatic`, `is_recovered`) | 3 properties | Used in ~25 prod refs | Delegate to `infection_status`/`illness_status` |
| **Telemetry** (`to_schema_dict()`) | 1 file | 1 call | `infection_status`, `is_symptomatic`, `is_recovered` |
| **Observation** (`agent_is_infected()`) | 2 files | ~12 refs | Reads from `to_schema_dict()` output |
| **Legacy engine** (`current_shedding`) | 1 property | `_default` pathway | `is_infected`, `time_infected` |
| **Orchestrator init** | 1 file | 2 refs | `infection_status` for seed selection |
| **Tests** | 18 files | ~70 refs | `infection_status`, `illness_status` (write + assert) |

**Key insight:** The agent-level fields are **already computed projections**, not an independent state machine. The `_project_legacy_illness()` function was specifically written to fix the dual-state-machine bug where agent-level fields latched `SYMPTOMATIC` incorrectly. The docstring explicitly says: "The agent-level fields are a summary channel, not a second state machine."

**Can they be computed from per-pathogen state?** Yes — `_project_legacy_illness()` already does exactly this. The `is_infected`, `is_symptomatic`, `is_recovered` properties read from `infection_status`/`illness_status`, which are set by the projection.

### (b) Recommended Resolution

**Keep agent-level fields as computed projections (status quo), but formally document them as read-only derived values. Do NOT deprecate or remove them.**

**Rationale:**
1. **94+ downstream references** across production and test code read these fields. Removing them would be a large, disruptive refactor with no functional benefit.
2. The `_project_legacy_illness()` mechanism already works correctly and runs every epoch.
3. The `is_infected`, `is_symptomatic`, `is_recovered` properties provide a clean API that downstream modules (observation, telemetry, confinement) need — they should not have to iterate `infections` themselves.
4. The `_default` pathway in `transmission_core.py:2641–2643` and `current_shedding` property still need the agent-level fields for single-pathogen backward compatibility.
5. The real risk is not the fields' existence but **direct writes** to them outside `_project_legacy_illness()` and `_establish()`. These should be audited and eliminated.

**Recommended actions:**
1. **Document** agent-level `infection_status`, `illness_status`, `time_infected`, `acquired_particles`, and `shedding_multiplier` as **read-only projections** in the spec. Add a `@property` or naming convention to signal this.
2. **Audit and remove** direct writes to these fields outside `_project_legacy_illness()`, `_establish()`, and `orchestrator_init.py` (seed infection). Currently, `infection_dynamics_bridge.py:1426,1474,1513,1558` (legacy fallback paths) also write them — these writes should be guarded by a `_project_legacy_illness()` call rather than inlined.
3. **Add a deprecation warning** on direct assignment (via `__setattr__` guard or code review policy) to prevent new code from writing to agent-level fields.
4. **No removal timeline** — the fields stay as derived properties indefinitely.

### (c) Backward Compatibility Impact

- **Zero breaking changes**: Fields remain accessible; values remain identical (already computed by projection).
- **18 test files** write to `infection_status`/`illness_status` for test setup. These writes are valid in test fixtures (setting up initial state). They would need updating only if the fields became truly read-only properties, which is not recommended.
- **5 production files** are affected by the audit/cleanup, but the cleanup is behavioral (consolidating writes), not API-breaking.

### (d) Spec Replacement Text

Replace the TODO at §12.2 (line 989 of the spec) with:

> **Resolution:** Keep agent-level infection fields (`infection_status`, `illness_status`, `time_infected`, `acquired_particles`, `shedding_multiplier`) as **read-only computed projections**, not deprecated. The per-pathogen `infections` dict remains the single source of truth; `_project_legacy_illness()` (called once per agent per epoch at `orchestrator_epoch.py:554`) rewrites the agent-level fields from the per-pathogen records. The `is_infected`, `is_symptomatic`, and `is_recovered` properties are thin wrappers over these projected fields and remain the recommended API for downstream consumers (observation, telemetry, confinement, VSP thresholds). **New code MUST NOT write directly to agent-level infection fields** outside `_project_legacy_illness()`, `_establish()`, and seed-infection initialization. Existing direct writes in the legacy fallback paths (`infection_dynamics_bridge.py:1426–1559`) are to be consolidated behind the projection in a future cleanup PR. No removal timeline is set; the fields persist as derived values indefinitely, since 94+ references across 23 files (5 production, 18 test) depend on them.

---

## Summary Table

| TODO | Resolution | Code Changes Required | Tests Affected | Risk |
|---|---|---|---|---|
| **TODO-1** (cumulative_exposure decay) | §3.2 inoculum_clearance_rate handles decay; add recovery reset (SPEC-CLEAR-01) | 1 line in `orchestrator_epoch.py` | 0 | Negligible |
| **TODO-2** (recovery distribution) | Add optional `recovery` block; default `"fixed"` preserves current behavior | New `sample_recovery()` function; modify `orchestrator_epoch.py:482–487` | 0 at defaults; 16 files if distribution enabled | Low (opt-in) |
| **TODO-3** (route-specific shedding) | Defer to v2.0; current `transmission_route_weights` sufficient | 0 | 0 | None |
| **TODO-4** (tissue tropism scope) | No shipped pathogen needs it; schema extension stays optional | 0 | 0 | None |
| **TODO-5** (agent-level fields) | Keep as read-only projections; document, don't deprecate | Documentation + write-audit (no API change) | 0 | None |
