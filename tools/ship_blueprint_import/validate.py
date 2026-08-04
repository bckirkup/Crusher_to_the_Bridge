"""Stage 5: schema + sanity_checker validation for synthesized platforms."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from typing import Any

from simulation_utils.paths import resolve_child_path, validated_open

_REPO_ROOT = os.path.dirname(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
)


def _load_json(path: str, *, allowed_roots: tuple[str, ...]) -> dict[str, Any]:
    with validated_open(path, "r", allowed_roots=allowed_roots, encoding="utf-8") as fh:
        return json.load(fh)


def validate_against_schemas(
    platform_dir: str,
    *,
    allowed_roots: tuple[str, ...],
    schemas_dir: str | None = None,
) -> list[str]:
    """Return list of error strings (empty = ok). Uses jsonschema if present."""
    errors: list[str] = []
    schemas_dir = schemas_dir or os.path.join(_REPO_ROOT, "schemas")
    pairs = [
        ("spatial_layout.json", "spatial_layout.schema.json"),
        ("air_flow_paths.json", "air_flow_paths.schema.json"),
    ]
    try:
        import jsonschema
    except ImportError:
        for data_name, schema_name in pairs:
            data_path = resolve_child_path(platform_dir, data_name)
            schema_path = resolve_child_path(schemas_dir, schema_name)
            if not os.path.isfile(data_path):
                errors.append(f"missing {data_name}")
                continue
            cmd = [
                sys.executable,
                "-m",
                "check_jsonschema",
                "--schemafile",
                schema_path,
                data_path,
            ]
            proc = subprocess.run(cmd, capture_output=True, text=True)
            if proc.returncode != 0:
                errors.append(
                    f"{data_name}: {proc.stdout.strip() or proc.stderr.strip() or 'schema fail'}"
                )
        return errors

    for data_name, schema_name in pairs:
        data_path = resolve_child_path(platform_dir, data_name)
        schema_path = resolve_child_path(schemas_dir, schema_name)
        if not os.path.isfile(data_path):
            errors.append(f"missing {data_name}")
            continue
        data = _load_json(data_path, allowed_roots=allowed_roots)
        schema = _load_json(schema_path, allowed_roots=allowed_roots)
        validator = jsonschema.Draft202012Validator(schema)
        for err in sorted(validator.iter_errors(data), key=lambda e: list(e.path)):
            errors.append(f"{data_name}: {list(err.path)}: {err.message}")
    return errors


def run_sanity_checker(platform_dir: str) -> tuple[bool, str]:
    """Invoke tools.sanity_checker.run_checks for a platform directory."""
    from tools.sanity_checker import run_checks

    config_dir = os.path.join(_REPO_ROOT, "data", "config")
    pathogen_file = os.path.join(_REPO_ROOT, "data", "pathogens", "active_profiles.json")
    report = run_checks(config_dir, platform_dir, pathogen_file=pathogen_file)
    lines = []
    for f in report.findings:
        lines.append(f"[{f.severity.value}] {f.file} {f.rule}: {f.message}")
    return report.passed, "\n".join(lines)


def validate_platform(
    platform_dir: str,
    *,
    allowed_roots: tuple[str, ...],
    contam_bootstrap: bool = False,
    contam_gate: bool = False,
    workdir: str | None = None,
) -> dict[str, Any]:
    """Full validation gate; optionally author Contam starter / gate PRJ parse."""
    schema_errors = validate_against_schemas(
        platform_dir, allowed_roots=allowed_roots
    )
    sanity_ok, sanity_text = run_sanity_checker(platform_dir)
    contam_msg = None
    contam_gate_result: dict[str, Any] | str | None = None

    ok = (not schema_errors) and sanity_ok

    if contam_bootstrap and ok:
        from tools.ship_blueprint_import.author_contam import author_contam

        try:
            result = author_contam(
                platform_dir=platform_dir,
                workdir=workdir,
                allowed_roots=allowed_roots,
                hobbyist=True,
                run_offline_gate=True,
            )
            gate = result.get("offline_gate") or {}
            contam_msg = (
                f"author_contam ok: {result['prj_path']} "
                f"({result['openings_count']} openings); "
                f"offline_gate={'PASS' if gate.get('ok') else 'FAIL'}"
            )
            if not gate.get("ok", True):
                ok = False
                contam_gate_result = gate
        except Exception as exc:  # noqa: BLE001
            contam_msg = f"author_contam FAILED: {exc}"
            ok = False

    if contam_gate:
        from tools.ship_blueprint_import.author_contam import validate_prj_offline

        prj = os.path.join(platform_dir, "contam", "platform.prj")
        if not os.path.isfile(prj):
            contam_gate_result = "missing contam/platform.prj"
            ok = False
        else:
            gate = validate_prj_offline(prj, allowed_roots=allowed_roots)
            contam_gate_result = gate
            if not gate.get("ok"):
                ok = False

    return {
        "ok": ok,
        "schema_errors": schema_errors,
        "sanity_ok": sanity_ok,
        "sanity_report": sanity_text,
        "contam_bootstrap": contam_msg,
        "contam_gate": contam_gate_result,
    }
