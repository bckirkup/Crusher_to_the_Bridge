"""Per-tier cartesian products used by generate_tier_runs."""
from __future__ import annotations

from itertools import product
from typing import Any, Iterator


def _pathogen_bundle(ctx: Any, pathogen: str) -> tuple[str, Any, dict[str, Any]]:
    return ctx.get_pathogen_config(ctx.manifest, pathogen)


def _comp_behavior(comp: Any) -> tuple[dict[str, Any] | None, str]:
    if comp is None:
        return None, ""
    return (
        {"fred_behavior": {"quarantine_compliance": float(comp)}},
        f"_comp{int(float(comp) * 100)}",
    )


def _latency_from_level(level: Any) -> tuple[dict[str, int], int]:
    if isinstance(level, dict):
        lat = {
            "alert_delay_hours": int(level.get("alert", 0)),
            "suspected_delay_hours": int(level.get("suspected", 0)),
            "confirmed_delay_hours": int(level.get("confirmed", 0)),
            "lockdown_delay_hours": int(level.get("lockdown", 0)),
        }
        return lat, int(level.get("confirmed", 0))
    delay_tag = int(level)
    return (
        {
            "alert_delay_hours": min(delay_tag, 6),
            "suspected_delay_hours": delay_tag,
            "confirmed_delay_hours": delay_tag,
            "lockdown_delay_hours": max(delay_tag, 24),
        },
        delay_tag,
    )


def _lockdown_tag(lockdown_ar: Any) -> tuple[float | None, str]:
    lockdown_val = None if lockdown_ar in (None, "never") else float(lockdown_ar)
    tag = "never" if lockdown_val is None else f"{int(round(float(lockdown_ar) * 100))}"
    return lockdown_val, tag


def _path_overrides(
    base: dict[str, Any] | None,
    pathogen_id: str,
    dose: Any,
    n_init: Any,
) -> dict[str, Any]:
    path_over = dict(base or {})
    patch: dict[str, Any] = {}
    if dose is not None:
        patch["dose_adjustment"] = float(dose)
    if n_init is not None:
        patch["initial_infected"] = int(n_init)
    if not patch:
        return path_over
    path_over[pathogen_id] = {**(path_over.get(pathogen_id) or {}), **patch}
    return path_over


def _calibration_rid(
    ctx: Any,
    *,
    pathogen: str,
    plat: str,
    dose: Any,
    n_init: Any,
    alpha: Any,
    cmode: Any,
    sweep_epochs: bool,
    n_epochs: int,
    imm_tag: str,
    sname: str,
    seed: int,
) -> str:
    parts = [ctx.short, pathogen, plat]
    if dose is not None:
        parts.append(ctx.dose_tag(dose))
    if n_init is not None:
        parts.append(f"init{int(n_init)}")
    if alpha is not None:
        parts.append(ctx.alpha_tag(alpha))
    if cmode is not None:
        parts.append(ctx.contact_mode_tag(cmode))
    if sweep_epochs:
        parts.append(f"ep{int(n_epochs)}")
    if imm_tag:
        parts.append(imm_tag.lstrip("_"))
    parts.append(sname)
    parts.append(f"s{seed}")
    return "_".join(parts)

def _iter_t1_runs(ctx: Any) -> Iterator[tuple[str, dict[str, Any]]]:
    hvac = {"hvac": ctx.tier["hvac"]} if ctx.tier.get("hvac") else None
    # v4 uses surveillance_strategies; legacy manifests use a single
    # ``surveillance`` string (default "none"). Keep old run ids when
    # there is no strategy sweep so existing dry-run counts stay stable.
    strategies = list(ctx.tier.get("surveillance_strategies") or [])
    if not strategies:
        strategies = [ctx.tier.get("surveillance", "none")]
    multi_surv = "surveillance_strategies" in ctx.tier
    for pathogen, sname, seed in product(
        ctx.tier["pathogens"], strategies, ctx.tier["seeds"],
    ):
        bundle, _pid, overrides = _pathogen_bundle(ctx, pathogen)
        rid = (
            f"{ctx.short}_{pathogen}_{sname}_s{seed}"
            if multi_surv
            else f"{ctx.short}_{pathogen}_s{seed}"
        )
        yield ctx.yield_run(
            rid,
            bundle=bundle,
            pathogen_overrides=overrides,
            config_overrides=ctx.merge_cfg(hvac, ctx.surv_cfgs.get(sname)),
            seed=seed,
            pathogen=pathogen,
            surveillance=sname,
        )

def _iter_t2_runs(ctx: Any) -> Iterator[tuple[str, dict[str, Any]]]:
    oa_fractions = ctx.tier.get("oa_fractions") or {"oa20": 0.20}
    for pathogen, (fname, fval), (oaname, oaval), (dname, dval), seed in product(
        ctx.tier["pathogens"],
        ctx.tier["filter_efficiencies"].items(),
        oa_fractions.items(),
        ctx.tier["decay_rates"].items(),
        ctx.tier["seeds"],
    ):
        bundle, _pid, overrides = _pathogen_bundle(ctx, pathogen)
        yield ctx.yield_run(
            f"{ctx.short}_{pathogen}_{fname}_{oaname}_{dname}_s{seed}",
            bundle=bundle,
            pathogen_overrides=overrides,
            config_overrides={"hvac": {
                "filter_efficiency": fval,
                "natural_decay_rate": dval,
                "oa_fraction": oaval,
            }},
            seed=seed,
            pathogen=pathogen,
            filter=fname,
            oa=oaname,
            decay=dname,
        )

def _iter_t3_runs(ctx: Any) -> Iterator[tuple[str, dict[str, Any]]]:
    hvac = {"hvac": ctx.tier["hvac"]} if ctx.tier.get("hvac") else None
    for pathogen, sname, seed in product(
        ctx.tier["pathogens"],
        ctx.tier["surveillance_strategies"],
        ctx.tier["seeds"],
    ):
        bundle, _pid, overrides = _pathogen_bundle(ctx, pathogen)
        yield ctx.yield_run(
            f"{ctx.short}_{pathogen}_{sname}_s{seed}",
            bundle=bundle,
            pathogen_overrides=overrides,
            config_overrides=ctx.merge_cfg(hvac, ctx.surv_cfgs.get(sname)),
            seed=seed,
            pathogen=pathogen,
            surveillance=sname,
        )

def _iter_t4_runs(ctx: Any) -> Iterator[tuple[str, dict[str, Any]]]:
    for pathogen, (fname, fval), (dname, dval), sname, seed in product(
        ctx.tier["pathogens"],
        ctx.tier["filter_efficiencies"].items(),
        ctx.tier["decay_rates"].items(),
        ctx.tier["surveillance_strategies"],
        ctx.tier["seeds"],
    ):
        bundle, _pid, overrides = _pathogen_bundle(ctx, pathogen)
        yield ctx.yield_run(
            f"{ctx.short}_{pathogen}_{fname}_{dname}_{sname}_s{seed}",
            bundle=bundle,
            pathogen_overrides=overrides,
            config_overrides=ctx.merge_cfg(
                {"hvac": {
                    "filter_efficiency": fval,
                    "natural_decay_rate": dval,
                }},
                ctx.surv_cfgs.get(sname),
            ),
            seed=seed,
            pathogen=pathogen,
            filter=fname,
            decay=dname,
            surveillance=sname,
        )

def _iter_t5_runs(ctx: Any) -> Iterator[tuple[str, dict[str, Any]]]:
    for combo, sname, seed in product(
        ctx.tier["combos"],
        ctx.tier["surveillance_strategies"],
        ctx.tier["seeds"],
    ):
        bundle, overrides = ctx.combo_overrides(ctx.manifest, combo)
        yield ctx.yield_run(
            f"{ctx.short}_{combo.replace('+', '_')}_{sname}_s{seed}",
            bundle=bundle,
            pathogen_overrides=overrides,
            config_overrides=ctx.surv_cfgs.get(sname),
            seed=seed,
            combo=combo,
            surveillance=sname,
        )

def _iter_t6_runs(ctx: Any) -> Iterator[tuple[str, dict[str, Any]]]:
    immunities = ctx.tier.get("pre_immunity_fractions", [None])
    for pathogen, n_init, imm_frac, seed in product(
        ctx.tier["pathogens"],
        ctx.tier["initial_infected"],
        immunities,
        ctx.tier["seeds"],
    ):
        bundle, pathogen_id, overrides = ctx.get_pathogen_config(ctx.manifest, pathogen)
        path_over = dict(overrides or {})
        path_over[pathogen_id] = {
            **(path_over.get(pathogen_id) or {}),
            "initial_infected": int(n_init),
        }
        cfg_over, imm_tag = ctx.immunity_override(imm_frac)
        yield ctx.yield_run(
            f"{ctx.short}_{pathogen}_init{n_init}{imm_tag}_s{seed}",
            bundle=bundle,
            pathogen_overrides=path_over,
            config_overrides=cfg_over,
            seed=seed,
            pathogen=pathogen,
            n_init=int(n_init),
            immunity=imm_frac,
        )

def _iter_t7_runs(ctx: Any) -> Iterator[tuple[str, dict[str, Any]]]:
    immunities = ctx.tier.get("pre_immunity_fractions", [None])
    for pathogen, sname, comp, imm_frac, seed in product(
        ctx.tier["pathogens"],
        ctx.tier["surveillance_strategies"],
        ctx.tier["compliance_levels"],
        immunities,
        ctx.tier["seeds"],
    ):
        bundle, _pid, overrides = _pathogen_bundle(ctx, pathogen)
        imm_over, imm_tag = ctx.immunity_override(imm_frac)
        yield ctx.yield_run(
            f"{ctx.short}_{pathogen}_{sname}_comp{int(comp * 100)}{imm_tag}_s{seed}",
            bundle=bundle,
            pathogen_overrides=overrides,
            config_overrides=ctx.merge_cfg(
                ctx.merge_cfg(
                    ctx.surv_cfgs.get(sname),
                    {"fred_behavior": {"quarantine_compliance": float(comp)}},
                ),
                imm_over,
            ),
            seed=seed,
            pathogen=pathogen,
            surveillance=sname,
            compliance=float(comp),
            immunity=imm_frac,
        )

def _iter_t8_runs(ctx: Any) -> Iterator[tuple[str, dict[str, Any]]]:
    for pathogen, wname, sname, seed in product(
        ctx.tier["pathogens"],
        ctx.tier["wearable_configs"],
        ctx.tier["surveillance_strategies"],
        ctx.tier["seeds"],
    ):
        bundle, _pid, overrides = _pathogen_bundle(ctx, pathogen)
        yield ctx.yield_run(
            f"{ctx.short}_{pathogen}_{wname}_{sname}_s{seed}",
            bundle=bundle,
            pathogen_overrides=overrides,
            config_overrides=ctx.merge_cfg(
                ctx.surv_cfgs.get(sname),
                {"wearable_monitoring": {"deployment_profile": wname}},
            ),
            seed=seed,
            pathogen=pathogen,
            wearables=wname,
            surveillance=sname,
        )

def _iter_t9_runs(ctx: Any) -> Iterator[tuple[str, dict[str, Any]]]:
    for pathogen, sname, seed in product(
        ctx.tier["pathogens"],
        ctx.tier["surveillance_strategies"],
        ctx.tier["seeds"],
    ):
        bundle, _pid, overrides = _pathogen_bundle(ctx, pathogen)
        yield ctx.yield_run(
            f"{ctx.short}_{pathogen}_{sname}_s{seed}",
            bundle=bundle,
            pathogen_overrides=overrides,
            config_overrides=ctx.surv_cfgs.get(sname),
            seed=seed,
            pathogen=pathogen,
            surveillance=sname,
        )

def _iter_t10_runs(ctx: Any) -> Iterator[tuple[str, dict[str, Any]]]:
    strategies = list(ctx.tier.get("surveillance_strategies") or [])
    multi_surv = bool(strategies)
    if not strategies:
        strategies = [None]
    for pathogen, n_agents, sname, seed in product(
        ctx.tier["pathogens"],
        ctx.tier["population_sizes"],
        strategies,
        ctx.tier["seeds"],
    ):
        bundle, _pid, overrides = _pathogen_bundle(ctx, pathogen)
        rid = (
            f"{ctx.short}_{pathogen}_{sname}_n{n_agents}_s{seed}"
            if multi_surv
            else f"{ctx.short}_{pathogen}_n{n_agents}_s{seed}"
        )
        yield ctx.yield_run(
            rid,
            bundle=bundle,
            pathogen_overrides=overrides,
            config_overrides=ctx.surv_cfgs.get(sname) if sname is not None else None,
            seed=seed,
            num_agents=int(n_agents),
            pathogen=pathogen,
            surveillance=sname,
        )

def _iter_t11_latency(ctx: Any) -> Iterator[tuple[str, dict[str, Any]]]:
    comps = ctx.tier.get("compliance_levels", [None])
    for pathogen, level, sname, comp, seed in product(
        ctx.tier["pathogens"],
        ctx.tier["decision_latency_levels"],
        ctx.tier["surveillance_strategies"],
        comps,
        ctx.tier["seeds"],
    ):
        bundle, _pid, overrides = _pathogen_bundle(ctx, pathogen)
        lat, delay_tag = _latency_from_level(level)
        behavior, comp_tag = _comp_behavior(comp)
        yield ctx.yield_run(
            f"{ctx.short}_{pathogen}_{sname}_lat{delay_tag}{comp_tag}_s{seed}",
            bundle=bundle,
            pathogen_overrides=overrides,
            config_overrides=ctx.merge_cfg(
                ctx.merge_cfg(
                    ctx.surv_cfgs.get(sname),
                    {"escalation": {"decision_latency": lat}},
                ),
                behavior,
            ),
            seed=seed,
            pathogen=pathogen,
            surveillance=sname,
            decision_latency_epochs=delay_tag,
            compliance=float(comp) if comp is not None else None,
        )


def _iter_t11_legacy(ctx: Any) -> Iterator[tuple[str, dict[str, Any]]]:
    comps = ctx.tier.get("compliance_levels", [None])
    for pathogen, delay, sname, comp, seed in product(
        ctx.tier["pathogens"],
        ctx.tier["surveillance_delay_epochs"],
        ctx.tier["surveillance_strategies"],
        comps,
        ctx.tier["seeds"],
    ):
        bundle, _pid, overrides = _pathogen_bundle(ctx, pathogen)
        behavior, comp_tag = _comp_behavior(comp)
        delay_over = {
            "syndromic": {"activation_delay_hours": int(delay)},
            "diagnostic_cascade": {"activation_delay_hours": int(delay)},
        }
        yield ctx.yield_run(
            f"{ctx.short}_{pathogen}_{sname}_delay{int(delay)}{comp_tag}_s{seed}",
            bundle=bundle,
            pathogen_overrides=overrides,
            config_overrides=ctx.merge_cfg(
                ctx.merge_cfg(ctx.surv_cfgs.get(sname), delay_over),
                behavior,
            ),
            seed=seed,
            pathogen=pathogen,
            surveillance=sname,
            surveillance_delay_epochs=int(delay),
            compliance=float(comp) if comp is not None else None,
        )


def _iter_t11_runs(ctx: Any) -> Iterator[tuple[str, dict[str, Any]]]:
    if "decision_latency_levels" in ctx.tier:
        yield from _iter_t11_latency(ctx)
        return
    yield from _iter_t11_legacy(ctx)

def _iter_t12_runs(ctx: Any) -> Iterator[tuple[str, dict[str, Any]]]:
    for pathogen, scp, sname, seed in product(
        ctx.tier["pathogens"],
        ctx.tier["sick_call_probabilities"],
        ctx.tier["surveillance_strategies"],
        ctx.tier["seeds"],
    ):
        bundle, _pid, overrides = _pathogen_bundle(ctx, pathogen)
        yield ctx.yield_run(
            (
                f"{ctx.short}_{pathogen}_{sname}"
                f"_scp{int(round(float(scp) * 100))}_s{seed}"
            ),
            bundle=bundle,
            pathogen_overrides=overrides,
            config_overrides=ctx.merge_cfg(
                ctx.surv_cfgs.get(sname),
                {"syndromic": {"sick_call_probability": float(scp)}},
            ),
            seed=seed,
            pathogen=pathogen,
            surveillance=sname,
            sick_call_probability=float(scp),
        )

def _iter_t13_runs(ctx: Any) -> Iterator[tuple[str, dict[str, Any]]]:
    wname = ctx.tier.get("wearable_config", "crew_only")
    for pathogen, sens, sname, seed in product(
        ctx.tier["pathogens"],
        ctx.tier["wearable_sensitivities"],
        ctx.tier["surveillance_strategies"],
        ctx.tier["seeds"],
    ):
        bundle, _pid, overrides = _pathogen_bundle(ctx, pathogen)
        yield ctx.yield_run(
            (
                f"{ctx.short}_{pathogen}_{wname}_{sname}"
                f"_wsens{int(round(float(sens) * 100))}_s{seed}"
            ),
            bundle=bundle,
            pathogen_overrides=overrides,
            config_overrides=ctx.merge_cfg(
                ctx.surv_cfgs.get(sname),
                {
                    "wearable_monitoring": {
                        "deployment_profile": wname,
                        "detection_sensitivity_scale": float(sens),
                    },
                },
            ),
            seed=seed,
            pathogen=pathogen,
            wearables=wname,
            surveillance=sname,
            wearable_sensitivity=float(sens),
        )

def _iter_t14_runs(ctx: Any) -> Iterator[tuple[str, dict[str, Any]]]:
    sname = ctx.tier.get("surveillance", "syndromic")
    surv = ctx.surv_cfgs.get(sname)
    for pathogen, imm_frac, seed in product(
        ctx.tier["pathogens"],
        ctx.tier["pre_immunity_fractions"],
        ctx.tier["seeds"],
    ):
        bundle, _pid, overrides = _pathogen_bundle(ctx, pathogen)
        imm_over, imm_tag = ctx.immunity_override(imm_frac)
        yield ctx.yield_run(
            f"{ctx.short}_{pathogen}{imm_tag}_s{seed}",
            bundle=bundle,
            pathogen_overrides=overrides,
            config_overrides=ctx.merge_cfg(surv, imm_over),
            seed=seed,
            pathogen=pathogen,
            surveillance=sname,
            immunity=imm_frac,
        )

def _iter_t15_runs(ctx: Any) -> Iterator[tuple[str, dict[str, Any]]]:
    for pathogen, suspect_ar, lockdown_ar, seed in product(
        ctx.tier["pathogens"],
        ctx.tier["suspect_attack_rates"],
        ctx.tier["lockdown_attack_rates"],
        ctx.tier["seeds"],
    ):
        bundle, _pid, overrides = _pathogen_bundle(ctx, pathogen)
        lockdown_val, lockdown_tag = _lockdown_tag(lockdown_ar)
        yield ctx.yield_run(
            (
                f"{ctx.short}_{pathogen}"
                f"_sar{int(round(float(suspect_ar) * 100))}"
                f"_lar{lockdown_tag}_s{seed}"
            ),
            bundle=bundle,
            pathogen_overrides=overrides,
            config_overrides={
                "escalation": {
                    "suspect_attack_rate": float(suspect_ar),
                    "lockdown_attack_rate": lockdown_val,
                },
            },
            seed=seed,
            pathogen=pathogen,
            suspect_attack_rate=float(suspect_ar),
            lockdown_attack_rate="never" if lockdown_val is None else float(lockdown_ar),
        )

def _iter_t16_runs(ctx: Any) -> Iterator[tuple[str, dict[str, Any]]]:
    qcomp = float(ctx.tier.get("quarantine_compliance", 0.6))
    delay_values = ctx.tier.get(
        "reluctant_delay_hours",
        ctx.tier.get("reluctant_delay_epochs", []),
    )
    for pathogen, rfrac, rdelay, seed in product(
        ctx.tier["pathogens"],
        ctx.tier["reluctant_fractions"],
        delay_values,
        ctx.tier["seeds"],
    ):
        bundle, _pid, overrides = _pathogen_bundle(ctx, pathogen)
        yield ctx.yield_run(
            (
                f"{ctx.short}_{pathogen}"
                f"_rf{int(round(float(rfrac) * 100))}"
                f"_rd{int(rdelay)}_s{seed}"
            ),
            bundle=bundle,
            pathogen_overrides=overrides,
            config_overrides={
                "fred_behavior": {
                    "reluctant_fraction": float(rfrac),
                    "reluctant_delay_hours": int(rdelay),
                    "quarantine_compliance": qcomp,
                },
            },
            seed=seed,
            pathogen=pathogen,
            reluctant_fraction=float(rfrac),
            reluctant_delay_epochs=int(rdelay),
        )

def _calibration_epochs(ctx: Any) -> tuple[list[int], bool]:
    if ctx.epochs_override is not None:
        return [int(ctx.epochs_override)], False
    if "epoch_durations" in ctx.tier:
        return [int(e) for e in ctx.tier["epoch_durations"]], True
    return [int(ctx.default_epochs)], False


def _iter_calibration_runs(ctx: Any) -> Iterator[tuple[str, dict[str, Any]]]:
    pathogen = ctx.tier["pathogen"]
    bundle, pathogen_id, base_overrides = ctx.get_pathogen_config(ctx.manifest, pathogen)
    platforms = ctx.resolve_tier_platforms(
        ctx.tier,
        fallback_platform=ctx.manifest["platform"],
        platform_override=ctx.platform_override,
    )
    strategies = list(ctx.tier.get("surveillance_strategies") or []) or [
        ctx.tier.get("surveillance", "none"),
    ]
    epoch_list, sweep_epochs = _calibration_epochs(ctx)
    hvac = {"hvac": ctx.tier["hvac"]} if ctx.tier.get("hvac") else None
    for plat, dose, n_init, alpha, cmode, imm_frac, n_epochs, sname, seed in product(
        platforms,
        ctx.calibration_dose_values(ctx.tier),
        ctx.calibration_init_values(ctx.tier),
        ctx.density_exponent_values(ctx.tier),
        ctx.contact_mode_values(ctx.tier),
        ctx.tier.get("pre_immunity_fractions", [None]),
        epoch_list,
        strategies,
        ctx.tier["seeds"],
    ):
        imm_over, imm_tag = ctx.immunity_override(imm_frac)
        yield ctx.yield_run(
            _calibration_rid(
                ctx,
                pathogen=pathogen,
                plat=plat,
                dose=dose,
                n_init=n_init,
                alpha=alpha,
                cmode=cmode,
                sweep_epochs=sweep_epochs,
                n_epochs=n_epochs,
                imm_tag=imm_tag,
                sname=sname,
                seed=seed,
            ),
            bundle=bundle,
            pathogen_overrides=_path_overrides(
                base_overrides, pathogen_id, dose, n_init,
            ),
            config_overrides=ctx.merge_cfg(
                ctx.surv_cfgs.get(sname),
                imm_over,
                ctx.density_contact_override(alpha, contact_mode=cmode),
                hvac,
            ),
            seed=seed,
            num_agents=ctx.platform_num_agents(
                plat,
                num_agents_override=ctx.num_agents_override,
                tier=ctx.tier,
                default_agents=int(ctx.manifest.get("default_num_agents", 7000)),
            ),
            pathogen=pathogen,
            platform_id=plat,
            epochs=int(n_epochs),
            surveillance=sname,
            dose_adjustment=dose,
            n_init=n_init,
            immunity=imm_frac,
            density_exponent=alpha,
            contact_mode=cmode,
        )


_STANDARD_ITERS = {f"t{i}": globals()[f"_iter_t{i}_runs"] for i in range(1, 17)}
_CALIBRATION_SHORTS = frozenset(
    {"c1", "c2", "c3", "c4", "c5", "c6", "a2", "b1", "b2"},
)


def dispatch_standard_or_calibration(
    ctx: Any,
) -> Iterator[tuple[str, dict[str, Any]]] | None:
    """Return a t1–t16 or calibration iterator, else None for another family."""
    iterator = _STANDARD_ITERS.get(ctx.short)
    if iterator is not None:
        return iterator(ctx)
    if ctx.short in _CALIBRATION_SHORTS:
        return _iter_calibration_runs(ctx)
    return None
