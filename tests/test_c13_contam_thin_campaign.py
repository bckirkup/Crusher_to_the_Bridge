"""Offline tests for C13 Contam thin matched campaign wiring."""
from __future__ import annotations

import importlib.util
import json
import zipfile
from pathlib import Path
from typing import Any

import pytest

from picard_framework.runs.mega_cruise_campaign.campaign_runner import (
    OUTPUT_ROOT,
    generate_tier_runs,
    main,
    set_output_root,
)
from tools.contam_campaign_pair_compare import pair_rows

REPO_ROOT = Path(__file__).resolve().parent.parent
C12C_MANIFEST = (
    REPO_ROOT
    / "picard_framework"
    / "runs"
    / "mega_cruise_campaign"
    / "c12c_fine_calibration_manifest.json"
)
_BUILDER = REPO_ROOT / "scripts" / "build_c13_contam_thin_manifest.py"


def _load_builder() -> Any:
    spec = importlib.util.spec_from_file_location(
        "build_c13_contam_thin_manifest", _BUILDER,
    )
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _thin_manifest() -> dict[str, Any]:
    if not C12C_MANIFEST.is_file():
        pytest.skip(f"C12c manifest not staged: {C12C_MANIFEST}")
    builder = _load_builder()
    source = json.loads(C12C_MANIFEST.read_text(encoding="utf-8"))
    return builder.build_manifest(source)


def test_c13_thin_manifest_count_and_contamx_override() -> None:
    builder = _load_builder()
    manifest = _thin_manifest()
    runs = list(generate_tier_runs(manifest, builder.OUT_TIER))
    n_plat = len(manifest["tiers"][builder.OUT_TIER]["platforms"])
    expected = n_plat * len(builder.THIN_DOSES) * builder.THIN_SEED_COUNT
    assert len(runs) == expected == 80

    rid, spec = runs[0]
    assert rid.startswith("a2_norovirus_")
    assert "none_true" in rid
    hvac = (spec.get("config_overrides") or {}).get("hvac") or {}
    assert hvac.get("transport_engine") == "contamx"
    params = spec.get("campaign_parameters") or {}
    assert params.get("transport_engine") == "contamx"

    # Shared run_ids with C12c finecal native controls (pairing key).
    c12c = json.loads(C12C_MANIFEST.read_text(encoding="utf-8"))
    fine = list(generate_tier_runs(c12c, "a2_noro_finecal"))
    fine_ids = {r for r, _ in fine}
    assert {r for r, _ in runs}.issubset(fine_ids)


def test_set_output_root_and_cli_flag(tmp_path: Path) -> None:
    prior = OUTPUT_ROOT
    try:
        redirected = set_output_root(tmp_path / "c13_out")
        assert redirected == (tmp_path / "c13_out").resolve()
        from picard_framework.runs.mega_cruise_campaign import campaign_runner as cr

        assert cr.OUTPUT_ROOT == redirected
        assert cr.COMPLETED_LOG == redirected / "completed_runs.txt"
        assert cr.FAILED_LOG == redirected / "failed_runs.txt"
    finally:
        set_output_root(prior)

    # Manifest must live under repo or --output-dir (path confinement).
    if not C12C_MANIFEST.is_file():
        pytest.skip(f"C12c manifest not staged: {C12C_MANIFEST}")
    out = tmp_path / "cli_c13"
    out.mkdir(parents=True, exist_ok=True)
    manifest_path = out / "c13_contam_thin_manifest.json"
    manifest_path.write_text(
        json.dumps(_thin_manifest(), indent=2),
        encoding="utf-8",
    )
    try:
        rc = main([
            "--manifest", str(manifest_path),
            "--output-dir", str(out),
            "--dry-run",
        ])
        assert rc == 0
        from picard_framework.runs.mega_cruise_campaign import campaign_runner as cr

        assert cr.OUTPUT_ROOT == out.resolve()
    finally:
        set_output_root(prior)


def test_c13b_airborne_small_manifest_count_and_ids() -> None:
    builder_path = REPO_ROOT / "scripts" / "build_c13b_contam_airborne_small_manifest.py"
    c12 = (
        REPO_ROOT
        / "picard_framework"
        / "runs"
        / "mega_cruise_campaign"
        / "c12_recalibration_manifest.json"
    )
    if not c12.is_file():
        pytest.skip(f"C12 recal manifest not staged: {c12}")
    spec = importlib.util.spec_from_file_location(
        "build_c13b_contam_airborne_small_manifest", builder_path,
    )
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    source = json.loads(c12.read_text(encoding="utf-8"))
    manifest = mod.build_manifest(source)
    all_ids: set[str] = set()
    for tier_id in manifest["tiers"]:
        runs = list(generate_tier_runs(manifest, tier_id))
        assert runs
        hvac = (runs[0][1].get("config_overrides") or {}).get("hvac") or {}
        assert hvac.get("transport_engine") == "contamx"
        all_ids.update(r for r, _ in runs)
    assert len(all_ids) == 120
    # Shared run_ids with C12 recal native controls.
    c12_ids: set[str] = set()
    for meta in mod.SLICE.values():
        c12_ids.update(
            r for r, _ in generate_tier_runs(source, meta["source_tier"])
        )
    assert all_ids.issubset(c12_ids)


def test_pair_compare_joins_on_run_id(tmp_path: Path) -> None:
    native = tmp_path / "native"
    contam = tmp_path / "contam"
    native.mkdir()
    contam.mkdir()

    def _write_zip(
        directory: Path,
        run_id: str,
        *,
        attack_rate: float,
        transport: str,
        dose: float = 10.4,
    ) -> None:
        summary = {
            "run_id": run_id,
            "parameters": {
                "run_id": run_id,
                "platform_id": "expedition_cruise_450",
                "pathogen": "norovirus",
                "dose_adjustment": dose,
                "seed": 900,
                "surveillance": "none_true",
                "transport_engine": transport,
                "num_agents": 450,
                "num_epochs": 168,
            },
            "derived": {
                "attack_rate": attack_rate,
                "peak_prevalence": attack_rate * 0.5,
                "outbreak_occurred": attack_rate > 0.05,
            },
            "summary": {},
            "cost_accounting": {},
        }
        zpath = directory / f"{run_id}.zip"
        with zipfile.ZipFile(zpath, "w") as zf:
            zf.writestr("summary.json", json.dumps(summary))

    rid = "a2_norovirus_expedition_cruise_450_dose10p4_a075_imm0_none_true_s900"
    _write_zip(native, rid, attack_rate=0.20, transport="native")
    _write_zip(contam, rid, attack_rate=0.25, transport="contamx")
    _write_zip(
        native,
        "orphan_native",
        attack_rate=0.1,
        transport="native",
    )

    rows, aggregate = pair_rows(native, contam)
    assert aggregate["n_paired"] == 1
    assert aggregate["n_native_only"] == 1
    assert aggregate["n_contam_only"] == 0
    assert rows[0]["run_id"] == rid
    assert rows[0]["delta_attack_rate"] == pytest.approx(0.05)
    assert aggregate["delta_attack_rate_mean"] == pytest.approx(0.05)
