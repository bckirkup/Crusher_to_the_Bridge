"""Frozen, pre-results protocol text for ``CONTAM-FLEET-WORKUP-PROTOCOL-01``.

Data only. ``tools/contam_fleet_workup_design.py`` adds the pin, the setting
grid and the repetition counts and writes the result as ``protocol.json``.
Nothing here is a measurement.
"""

from __future__ import annotations

from typing import Any

_AGGREGATE_ONLY = (
    "One value per hull x lane x setting. No per-zone, per-path, per-deck or "
    "per-opening value, no zone or path identifier, no ranking of hulls, "
    "zones or paths, and no localized source or release of any kind."
)

PROTOCOL: dict[str, Any] = {
    "stage": "pre-results design freeze; no field solved, no solver timed",
    "numerical_reference": {
        "ledger": "CONTAM-PHASE3-BASELINE-01",
        "measured_at": "5c8f05cc6f0d0e3e962ab4ff6e14c9941781976e",
        "scope": "two hulls; historical to this design, not a fleet result",
    },
    "lanes": {
        "native_prescribed": {
            "construction": "engines.py_contam_bridge.ContamTransportEngine "
                            "from spatial_layout.json and air_flow_paths.json",
            "weather_input": "none; ambient exchange is a declared fixed rate",
        },
        "contamx_commissioned_export": {
            "construction": "tools.contam_prj_bridge.export_prj_with_path_map("
                            "hobbyist=True, overrides=<per-hull overrides>, "
                            "ahs_terminal_mode='commissioned'), then "
                            "engines.contamx_runner.run_contamx and SIM import",
            "weather_input": "relative_wind_speed_m_s and "
                             "relative_wind_direction_deg in the overrides",
            "effective_input_harmonization": (
                "Each positive-duty group's outdoor-air fraction declared in "
                "air_flow_paths.json is supplied to the export through the "
                "existing overrides oa_fraction map and to the import through "
                "the existing per-terminal declared_oa_fraction entry field, "
                "so all lanes use the fraction the native lane reads. No "
                "engine or exporter code is changed."
            ),
        },
        "contamx_commissioned_export_as_committed": {
            "construction": "same export with the committed overrides "
                            "unchanged; baseline setting only",
            "purpose": "shows what the harmonization changes; never pooled "
                       "with the comparative arms",
        },
        "contamx_authored_bundle": {
            "construction": "committed contam/platform.prj and path_map.json "
                            "solved as authored; baseline setting only",
            "purpose": "as-authored reference; never pooled with the "
                       "comparative arms",
        },
    },
    "baseline": {
        "relative_wind_speed_m_s": 1.0,
        "relative_wind_direction_deg": 0.0,
        "wind_source": "exporter default; an assumed engineering level, not "
                       "an onboard or meteorological measurement",
        "sealed_life_support_hulls": "authored calm (0 m/s) is their baseline",
        "ventilation": "ach, hvac_duty and oa_fraction as committed in "
                       "air_flow_paths.json at the input pin",
        "filter_efficiency": 0.3,
        "envelope_leak_mode": "boundary_sink",
        "source_of_levels": "all non-baseline levels are engineering test "
                            "levels chosen before any result; none is an "
                            "onboard measurement",
    },
    "setting_application": {
        "one_variable_at_a_time": True,
        "declared_interactions": [
            "wind_speed_10_heading_90", "wind_speed_10_heading_180",
        ],
        "interaction_reason": "heading is expected to be near-inert at the "
                              "1 m/s baseline speed, so heading is also "
                              "tested at the highest speed level",
        "relative_wind_speed": "overrides relative_wind_speed_m_s; heading "
                               "stays at baseline",
        "relative_wind_direction": "overrides relative_wind_direction_deg, "
                                   "degrees from ahead, in [0, 360)",
        "supply_group_hvac_duty": "hvac_duty of every group with positive "
                                  "duty multiplied by the factor; duty-0 "
                                  "groups unchanged",
        "supply_group_ach": "ach of every group with positive duty multiplied "
                            "by the factor. Both solvers use ach x duty as a "
                            "product on these groups, so this row must equal "
                            "supply_duty_x1p5; a difference is a finding",
        "recirculating_supply_group_oa_fraction": (
            "oa_fraction of every positive-duty group declared below 1.0 "
            "multiplied by the factor, in all three places named under "
            "effective_input_harmonization"
        ),
        "recirculating_supply_group_recirculated_fraction": (
            "(1 - oa_fraction) of the same groups multiplied by the factor, "
            "i.e. oa' = 1 - factor x (1 - oa); stays below 1.0"
        ),
        "not_varied": "night_setback, filters, openings, hatches, leakage, "
                      "zone isolation, equipment outage or any casualty state",
    },
    "status_vocabulary": {
        "planned": {
            "planned_execute": "the cell is run and timed",
            "structural_nonresponse": "the lane has no input for the "
                                      "parameter; the baseline value is "
                                      "carried by reference and nothing is "
                                      "run or timed",
            "not_applicable": "the parameter does not exist on this hull",
        },
        "observed": {
            "ok": "solved and imported; values are numbers, zero included",
            "unchanged": "ok, and every metric equals the lane baseline "
                         "within the declared tolerance",
            "field_not_reached": "the setting did not change the realized "
                                 "input fields; values are withheld",
            "failed": "export, solve or import raised; reason recorded",
            "timeout": "solver exceeded the timeout; reason recorded",
            "unimplemented": "the runner has no implementation of the cell",
            "structural_nonresponse": "as planned",
            "not_applicable": "as planned",
        },
        "rule": "A metric is a number only when observed status is ok or "
                "unchanged; otherwise it is empty, never 0.",
        "unchanged_tolerance": "relative 1e-9 or absolute 1e-9 in the "
                               "metric's unit, whichever is larger",
    },
    "contrast_types": {
        "matched_perturbation": "the same input change reaches both lanes",
        "one_sided_structural": "only the ContamX lane has the input; the "
                                "contrast is ContamX-at-level against "
                                "ContamX-at-baseline, with the native lane "
                                "constant by construction. It is not solver "
                                "agreement or disagreement.",
    },
    "metrics": {
        "constraint": _AGGREGATE_ONLY,
        "per_row": {
            "supply_total_m3h": "sum of AHS supply terminal flow",
            "return_total_m3h": "sum of AHS return terminal flow",
            "outdoor_air_total_m3h": "sum of AHS outdoor-air intake",
            "exhaust_total_m3h": "sum of AHS and exhaust-only branch exhaust",
            "ambient_inward_total_m3h": "sum of inward flow over all ambient "
                                        "boundary paths",
            "ambient_outward_total_m3h": "sum of outward flow over the same",
            "interzone_gross_m3h": "sum of absolute zone-to-zone flow",
            "hull_balance_residual_m3h": "inward minus outward over the whole "
                                         "hull boundary",
            "whole_hull_air_change_1_per_h": "outdoor-air inflow over total "
                                             "zone volume",
            "max_abs_zone_balance_residual_m3h": "largest absolute zone mass "
                                                 "balance residual; value "
                                                 "only, zone not reported",
            "pressure_abs_dp_median_pa": "median absolute path pressure drop; "
                                         "ContamX lanes only",
            "pressure_abs_dp_p95_pa": "95th percentile of the same",
            "pressure_abs_dp_max_pa": "maximum of the same; value only",
            "pressure_rows_unsolved": "count of paths without a solved "
                                      "pressure",
            "uniform_tracer_material_time_h": "whole-hull material-time of an "
                                              "inert tracer initialized at "
                                              "the same concentration in "
                                              "every zone, 12 h horizon, no "
                                              "decay, no filter credit "
                                              "beyond the lane's own",
            "uniform_tracer_closure_error": "absolute mass-closure error of "
                                            "the same run",
        },
        "pressure_native": "not defined: the native lane prescribes flow and "
                           "solves no pressure; recorded as not_applicable",
        "structural_invariants": [
            "zone count and total zone volume equal across lanes",
            "AHS group count equals hvac_zones count",
            "path-map entry count equals the exported path count",
            "every flow finite; every sum reproducible from its parts",
        ],
        "comparison": "per hull and setting: ContamX minus native, and the "
                      "ratio where the native value is nonzero; and each "
                      "setting minus its own lane baseline",
    },
    "field_realization_check": {
        "when": "smoke stage, before any timing, on every executed row of "
                "the canary hulls and once per setting family on every hull",
        "weather": "the Ws/Wd values in the exported weather record equal "
                   "the level; the count of wind-flagged paths is recorded",
        "operational": "the summed commissioned terminal flow in the export "
                       "and the summed native supply flow both change by the "
                       "declared factor within 1e-9 relative; the realized "
                       "outdoor-air share equals the declared share",
        "failure": "the row is field_not_reached and the stage stops; the "
                   "design is superseded rather than patched",
    },
    "runtime": {
        "phases": {
            "native_construct": "uncached construction of the native engine "
                                "from the two input documents",
            "contamx_export": "PRJ and path-map generation",
            "contamx_solve": "ContamX subprocess, wall time of the call",
            "contamx_import": "SIM read and ContamX transport engine "
                              "construction",
            "downstream": "the identical aggregate-metric computation, "
                          "applied to either engine",
            "end_to_end": "from input documents in memory to metrics",
        },
        "non_equivalence": "native_construct and contamx_export+solve+import "
                           "are different operations. They are reported side "
                           "by side and as an end-to-end total, never as a "
                           "like-for-like speed ratio of one step.",
        "clocks": {
            "wall": "time.perf_counter_ns",
            "cpu_parent": "time.process_time_ns of the Python process",
            "cpu_child": "resource.getrusage(RUSAGE_CHILDREN) user+system "
                         "delta around the solver call",
            "rule": "wall and CPU are separate columns and are never summed",
        },
        "cold_definition": "fresh Python interpreter per cell execution, "
                           "inputs read from disk, new temporary directory, "
                           "no reuse of a baseline field, PRJ or SIM",
        "cached_definition": "same interpreter, engine already constructed; "
                             "only the downstream phase is repeated. "
                             "Reported in its own table and never compared "
                             "with a cold phase.",
        "order": "hulls in sorted order; within a hull the settings in "
                 "matrix order; within a setting the lanes alternate first "
                 "position by repeat index (even: native first)",
        "threads": "OMP_NUM_THREADS=OPENBLAS_NUM_THREADS=MKL_NUM_THREADS=1; "
                   "one cell at a time; no concurrent cells on the host",
        "summaries": "median, minimum, maximum, interquartile range and "
                     "median absolute deviation over the measured repeats; "
                     "warm-up repeats are stored and excluded",
        "repeats_are_not_seeds": "the fields are deterministic; repeats "
                                 "measure timing noise only and support no "
                                 "statistical claim about the physics",
        "timeout": "a timed-out solve is recorded as timeout with elapsed "
                   "equal to the limit flagged censored; it is excluded "
                   "from medians and counted",
        "fingerprint": [
            "runner git commit and dirty flag", "input pin",
            "ContamX executable SHA-256, size and reported version",
            "python version and implementation", "uv.lock SHA-256",
            "numpy and scipy versions", "OS, kernel, machine",
            "CPU model, logical and physical core count",
            "total memory", "thread environment variables",
            "container image digest if any", "UTC start and end",
        ],
    },
    "edison_payload": {
        "status": "contract only; nothing is sent in this stage",
        "files": {
            "input_manifest.json": "this design's manifest, unchanged",
            "run_matrix.csv": "this design's matrix, unchanged",
            "coverage.csv": "this design's roster, unchanged",
            "protocol.json": "this document, unchanged",
            "results_long.csv": "one row per row_id x metric",
            "timing_raw.csv": "one row per row_id x repeat x phase",
            "timing_summary.csv": "robust summaries per row_id x phase",
            "coverage_observed.csv": "expected against observed status per "
                                     "row_id, with failure reason",
            "environment.json": "the runtime fingerprint",
            "external_files.json": "path, size and SHA-256 of every file "
                                   "used that is not in the repository",
            "SHA256SUMS": "SHA-256 of every file above",
        },
        "identity_fields": {
            "input_commit": "commit whose tree supplies the hull inputs",
            "design_commit": "commit that contains this design",
            "runner_commit": "commit of the code that executed the cells",
            "rule": "the three are recorded separately. The manifest hashes "
                    "inputs at input_commit only, so no file contains its "
                    "own hash or the hash of the commit that adds it.",
        },
        "results_long_columns": {
            "row_id": "hull|lane|setting_id, key into run_matrix.csv",
            "hull": "platform directory name",
            "lane": "see lanes",
            "setting_id": "see settings",
            "metric": "name from metrics.per_row",
            "unit": "unit of the value",
            "value": "number, or empty when status is not ok/unchanged",
            "observed_status": "see status_vocabulary.observed",
            "reason": "free text for any non-ok status",
            "platform_git_tree": "tree id of the hull inputs",
            "runner_commit": "see identity_fields",
        },
        "timing_raw_columns": {
            "row_id": "key into run_matrix.csv",
            "repeat_index": "0-based within kind",
            "repeat_kind": "warmup | measured | cached",
            "phase": "see runtime.phases",
            "wall_ns": "integer nanoseconds",
            "cpu_parent_ns": "integer nanoseconds",
            "cpu_child_ns": "integer nanoseconds; empty when no subprocess",
            "censored": "1 when the phase hit the timeout",
            "observed_status": "see status_vocabulary.observed",
        },
        "offline_checks": [
            "sha256sum -c SHA256SUMS",
            "run_matrix.csv and input_manifest.json byte-equal to this "
            "design's files",
            "every row_id of run_matrix.csv appears exactly once in "
            "coverage_observed.csv",
            "git ls-tree at input_commit reproduces every git_blob_sha1 and "
            "platform_git_tree in the manifest",
            "tools/contam_fleet_workup_design.py --verify-only at the "
            "design commit",
        ],
        "separation": "A passing input-tree check says the inputs are the "
                      "committed ones. It says nothing about whether a solve "
                      "ran, converged or was correct; that is "
                      "coverage_observed.csv.",
        "content_limit": _AGGREGATE_ONLY,
    },
    "stages": {
        "this_stage": "design freeze",
        "next_stage": "smoke and canary: build the runner, pass the field "
                      "realization check, run only the canary hulls, read "
                      "out, stop",
        "stop_boundary": "no hull outside the canary set is run until the "
                         "canary readout is reviewed and the fleet run is "
                         "approved",
        "canary_rule": "the two CONTAM-PHASE3-BASELINE-01 hulls, the hulls "
                       "with the fewest and the most zones (ties by name), "
                       "and the first sealed life-support hull by name",
    },
    "open_items": [
        "No execution harness exists for this matrix. "
        "tools/contam_fleet_compare.py exports without hobbyist weather or "
        "overrides and writes source-specific outputs; it is not used.",
        "The aggregate-metric reducer does not exist; "
        "tools/diag/contam_pressure_balance_diagnostic.analyze_field "
        "returns per-path data that must be reduced before anything is "
        "written.",
        "The ContamX executable is not in the repository. Its SHA-256 must "
        "be recorded by the execution stage; the two-hull reference used "
        "d14dc8020bd5e9f95962af52f46b7ce85e2899b63306309d6590cec652274b2b.",
        "Timing host is not chosen. Timings from different hosts are not "
        "pooled.",
        "Whether the uniform inert tracer metric is kept is decided at the "
        "canary readout from closure only, before fleet values exist.",
        "Wind levels are test levels. No onboard or route wind record is "
        "in the repository to replace them.",
    ],
    "exclusions": "No biological agent, infection, dose or occupant model; "
                  "no point or localized release; no source or compartment "
                  "identification; no path map; no failure, outage or "
                  "casualty arm; no ranking.",
}
