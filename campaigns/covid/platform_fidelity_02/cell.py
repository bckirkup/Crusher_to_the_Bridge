#!/usr/bin/env python3
"""PLATFORM-FIDELITY-02 cell worker: run one (theta, arm_id, seed) cell.

The larger-seed Diamond Princess follow-up on the corrected
function-matched union ``exempt_work_zones``
(``data/config/protocols_covid_pf_dp_01b.json``; pre-registration
``docs/covid/covid_platform_fidelity_02_prereg.md``). Identical machinery
to the PLATFORM-FIDELITY-01b worker: the design declares the arms; the
``platform_id`` arm key rewrites ``catalog.platform_id`` in
``prepare_cell_run_spec``, and the design's ``base_overrides`` (the boxed
crew-mess block on DP) is composed after the arm's own overrides. Both the
proxy and dedicated arms are submitted over the full 200-seed series; the
first 20 dedicated seeds double as the in-image replication row against the
01b cells.

Every payload carries the ``platform_fidelity`` echo block: the resolved
platform_id, the protocols path, SHA-256 hashes of every input file the
cell consumed (run spec, design, scenario record, protocols file, platform
spatial layout + air-flow paths, pathogen bundle, agent profile bundle when
declared), and the set of protocol ids the protocol engine actually
activated during the voyage — with the ``close_zones`` firing flag that
makes a cell a FAILED COMPARISON.

``--num-epochs`` caps the voyage for local smoke validation only; Batch runs
always take the design's full declared voyage.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
from pathlib import Path
from typing import Any

_REPO_ROOT = Path(__file__).resolve().parents[3]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from picard_framework.catalog.registry import CatalogRegistry  # noqa: E402
from picard_framework.covid_boarding_screen import (  # noqa: E402
    QuarantineAttributionLedger,
    apply_arm_overrides,
    cell_payload,
    enumerate_cells,
    load_design,
    prepare_cell_run_spec,
)
from picard_framework.covid_theta_fit import (  # noqa: E402
    load_covid_profile,
    run_fit_spec,
)

_SCENARIO_RECORD = "data/scenarios/covid_hull_scenarios.json"


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _sha256_json(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, default=str).encode("utf-8"),
    ).hexdigest()


class _FiredProtocolLedger:
    """Collect the protocol ids the engine activated, and close_zones firings.

    Attached as a second epoch observer alongside the quarantine
    attribution ledger: ``work.active_mods`` at end-of-step is the
    protocol engine's per-protocol active list, so the fired set is read
    off the same object the engine itself produced — no re-derivation.
    """

    def __init__(self) -> None:
        self.protocol_ids: set[str] = set()
        self.close_zones_ids: set[str] = set()

    def observe(self, sim: Any, work: Any) -> None:
        active = getattr(work, "active_mods", None) or ()
        for entry in active:
            pid = entry.get("protocol_id")
            if not pid:
                continue
            pid = str(pid)
            self.protocol_ids.add(pid)
            modifiers = entry.get("modifiers") or {}
            if modifiers.get("close_zones"):
                self.close_zones_ids.add(pid)

    def as_dict(self) -> dict[str, Any]:
        return {
            "fired_protocol_ids": sorted(self.protocol_ids),
            "close_zones_fired": sorted(self.close_zones_ids),
            "close_zones_fired_flag": bool(self.close_zones_ids),
        }


def _scenario_declared_platform(repo_root: Path, scenario_id: str) -> str | None:
    """The proxy platform the frozen scenario record declares."""
    path = repo_root / _SCENARIO_RECORD
    raw = json.loads(path.read_text(encoding="utf-8"))
    for record in raw.get("scenarios", []):
        if record.get("scenario_id") == scenario_id:
            return record.get("platform_id")
    return None


def _input_hashes(
    repo_root: Path,
    design_path: Path,
    raw: dict[str, Any],
    cell: Any,
) -> dict[str, str]:
    """SHA-256 of every input file the cell consumed, plus the resolved spec."""
    hashes: dict[str, str] = {
        "run_spec_canonical_sha256": _sha256_json(raw),
        "design_sha256": _sha256_file(design_path),
        "scenario_record_sha256": _sha256_file(repo_root / _SCENARIO_RECORD),
    }
    protocols = raw.get("catalog", {}).get("protocols_path")
    if protocols:
        protocols_path = Path(protocols)
        if not protocols_path.is_absolute():
            protocols_path = repo_root / protocols_path
        hashes["protocols_sha256"] = _sha256_file(protocols_path)
    registry = CatalogRegistry.from_repo(str(repo_root))
    platform_id = raw.get("catalog", {}).get("platform_id")
    if platform_id:
        entry = registry.resolve_platform(str(platform_id))
        hashes["platform_spatial_layout_sha256"] = _sha256_file(
            Path(entry.spatial_layout),
        )
        hashes["platform_air_flow_sha256"] = _sha256_file(
            Path(entry.air_flow_paths),
        )
    bundle_id = raw.get("catalog", {}).get("pathogen_bundle_id")
    if bundle_id:
        hashes["pathogen_bundle_sha256"] = _sha256_file(
            Path(registry.resolve_pathogen_bundle(str(bundle_id))),
        )
    agent_bundle = (raw.get("social") or {}).get("agent_profile_bundle")
    if agent_bundle:
        agent_path = Path(str(agent_bundle))
        if not agent_path.is_absolute():
            agent_path = repo_root / agent_path
        hashes["agent_profile_bundle_sha256"] = _sha256_file(agent_path)
    return hashes


def _platform_fidelity_block(
    repo_root: Path,
    design_path: Path,
    design: Any,
    raw: dict[str, Any],
    cell: Any,
    fired: _FiredProtocolLedger,
) -> dict[str, Any]:
    """The prereg's per-cell echo: resolved hull, frozen inputs, fired SOPs."""
    catalog = raw.get("catalog", {})
    return {
        "resolved_platform_id": catalog.get("platform_id"),
        "scenario_declared_platform_id": _scenario_declared_platform(
            repo_root, cell.scenario_id,
        ),
        "protocols_path": catalog.get("protocols_path"),
        "input_hashes": _input_hashes(repo_root, design_path, raw, cell),
        **fired.as_dict(),
    }


def _match_cell(
    design: object, theta: float, arm_id: str, seed: int,
) -> object:
    """The single design cell at (theta, arm_id, seed), or die."""
    matches = [
        cell for cell in enumerate_cells(design)
        if cell.arm_id == arm_id and cell.seed == seed
        and math.isclose(cell.theta, theta, rel_tol=1e-12)
    ]
    if len(matches) != 1:
        raise SystemExit(
            f"{len(matches)} cells match theta={theta} arm={arm_id} "
            f"seed={seed}; expected exactly 1",
        )
    return matches[0]


def _load_design_with_base(design_rel: str) -> tuple[Any, dict[str, Any], Path]:
    """The design, its raw JSON (for base_overrides/protocols_path), and path."""
    design_path = (_REPO_ROOT / design_rel).resolve()
    raw_design = json.loads(design_path.read_text(encoding="utf-8"))
    return load_design(str(design_path)), raw_design, design_path


def run_pf_cell(
    design: object,
    cell: object,
    *,
    raw_design: dict[str, Any],
    design_path: Path,
    num_epochs: int | None = None,
) -> dict[str, Any]:
    """Run one cell: arm overrides (platform swap) + declared base + frozen SOPs."""
    raw = prepare_cell_run_spec(
        design, cell, num_epochs=num_epochs, repo_root=str(_REPO_ROOT),
    )
    base = dict(raw_design.get("base_overrides") or {})
    if base:
        apply_arm_overrides(
            raw, base,
            profile=load_covid_profile(str(_REPO_ROOT)),
            theta=cell.theta,
        )
    protocols_path = raw_design.get("protocols_path")
    if protocols_path:
        raw.setdefault("catalog", {})["protocols_path"] = protocols_path
    ledger = QuarantineAttributionLedger()
    fired = _FiredProtocolLedger()

    def _observe(sim: Any, work: Any) -> None:
        ledger.observe(sim, work)
        fired.observe(sim, work)

    sim = run_fit_spec(
        raw, repo_root=str(_REPO_ROOT), epoch_observer=_observe,
    )
    payload = cell_payload(design, cell, sim, ledger, raw)
    payload["platform_fidelity"] = _platform_fidelity_block(
        _REPO_ROOT, design_path, design, raw, cell, fired,
    )
    return payload


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--design", required=True,
                        help="repo-relative boarding-screen design JSON")
    parser.add_argument("--theta", required=True, type=float)
    parser.add_argument("--arm", required=True, help="design arm_id")
    parser.add_argument("--seed", required=True, type=int)
    parser.add_argument("--out", required=True,
                        help="directory the cell artifact is written to")
    parser.add_argument("--num-epochs", type=int, default=None,
                        help="smoke cap on voyage epochs (local only)")
    args = parser.parse_args(argv)

    design, raw_design, design_path = _load_design_with_base(args.design)
    cell = _match_cell(design, args.theta, args.arm, args.seed)
    import functools
    runner = functools.partial(
        run_pf_cell,
        raw_design=raw_design,
        design_path=design_path,
        num_epochs=args.num_epochs,
    )
    payload = {
        "design_id": design.design_id,
        "sanitary_visit_mode": design.sanitary_visit_mode,
        "cell": cell.as_dict(),
        **runner(design, cell),
    }

    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)
    artifact = out_dir / f"cell_{args.seed}.json"
    artifact.write_text(
        json.dumps(payload, indent=2) + "\n", encoding="utf-8",
    )
    print(f"WROTE {artifact}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
