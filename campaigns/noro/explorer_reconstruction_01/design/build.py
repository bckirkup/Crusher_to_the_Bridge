#!/usr/bin/env python3
"""Build the generated files of noro_explorer_reconstruction_01.

Three inputs, none of them transcribed here:

* the Paper-1 frozen ``config_overrides`` block, read out of the freeze
  design contract (the JSON after ``<!-- paper1-frozen-config-block -->``);
* the Explorer of the Seas daily onset table and its finals, parsed out of
  ``docs/norovirus/mega_voyage_source_evidence.md``;
* the platform complement, read from the committed ``spatial_layout.json``,
  and the shipped agent classes, read from ``crusher_labs/config.yaml``.

Outputs, all beside this directory: ``manifest.json`` (tiers carrying the
block verbatim), ``campaign.json`` (the ``scripts/campaign`` spec) and
``empirical_target.json`` (the comparison table with its denominators).

``--check`` rebuilds in memory and fails when a committed file differs, so
a drifted contract block or an edited evidence table is caught before any
cell runs.
"""
from __future__ import annotations

import argparse
import copy
import json
import re
import sys
from pathlib import Path
from typing import Any

import yaml

REPO = Path(__file__).resolve().parents[4]
CAMPAIGN_DIR = Path(__file__).resolve().parents[1]
CAMPAIGN_REL = "campaigns/noro/explorer_reconstruction_01"
CAMPAIGN_NAME = "noro_explorer_reconstruction_01"

CONTRACT_REL = "docs/norovirus/paper1_freeze_design_contract_2026_11_20.md"
EVIDENCE_REL = "docs/norovirus/mega_voyage_source_evidence.md"
EVIDENCE_SNAPSHOT = "74a6eff3ec45734b377acb07afe287ca6298f02f"
BLOCK_MARKER = "<!-- paper1-frozen-config-block -->"

PATHOGEN_ID = "norwalk_gi"
EPOCHS = 192
VOYAGE_DAYS = 8
SEEDS = list(range(8105, 8205))
CANARY_SEEDS = 20

PLATFORMS = {
    "exp": {"platform": "explorer_seas_06", "label": "Explorer of the Seas"},
    "meg": {"platform": "mega_cruise_5000", "label": "mega archetype"},
}
# Explorer runs the investigation complement; the archetype runs as shipped.
COMPLEMENTS = {"exp": "explorer_investigation", "meg": "archetype_shipped"}
# The mega archetype's emitted complement (assessment, four-hull ladder).
MEGA_NUM_AGENTS = 7000

# The declared introduction. ``count``/``role``/``epoch`` are the record
# (five passenger surveys recorded illness before boarding); ``onset_day``
# and ``infection_age_days`` are declared assumptions, because the record
# gives no onset date for the five: onset one day before embarkation
# (inside the VSP 4.1.1.2 three-day lookback), acquired one profile-median
# incubation (1.2 d, norwalk_gi ``incubation.median_days``) before that.
# Neither value is swept or fitted.
INTRODUCTIONS: dict[str, dict[str, Any]] = {
    "declared_five": {
        "explicit_seeds": [
            {
                "pathogen": PATHOGEN_ID,
                "count": 5,
                "role": "passenger",
                "epoch": 0,
                "onset_day": -1.0,
                "infection_age_days": 2.2,
            },
        ],
    },
    # Labelled baseline: the engine's own boarding draw and nothing else.
    "background_only": {"explicit_seeds": []},
}

# Verbatim from the NORO-GENO-02 manifest (contract section 2.5).
PATHOGEN_CONFIGS = {
    "norovirus": {
        "bundle": "active_profiles",
        "pathogen_id": PATHOGEN_ID,
        "overrides": {"remove": ["sars_cov2_resp"]},
    },
}
SURVEILLANCE_CONFIGS = {
    "syndromic_comp65": {
        "diagnostic_cascade": {"enabled": False},
        "fred_behavior": {
            "quarantine_compliance": 0.65,
            "compliance_by_class": {
                "crew": 0.65,
                "passenger_elderly": 0.54,
                "passenger_young": 0.34,
            },
        },
    },
}

_DATE_COLUMNS = (
    "Feb 26", "Feb 27", "Feb 28", "Mar 1", "Mar 2", "Mar 3", "Mar 4",
    "Mar 5",
)


def frozen_block() -> dict[str, Any]:
    """The contract's frozen ``config_overrides`` block, parsed."""
    text = (REPO / CONTRACT_REL).read_text(encoding="utf-8")
    match = re.search(
        re.escape(BLOCK_MARKER) + r"\s*```json\n(.*?)\n```", text, re.DOTALL,
    )
    if match is None:
        raise SystemExit(f"no frozen block after {BLOCK_MARKER}")
    return json.loads(match.group(1))


def _table_row(text: str, label: str) -> list[int]:
    match = re.search(
        r"^\|\s*" + re.escape(label) + r"\s*\|(.+)\|\s*$", text, re.MULTILINE,
    )
    if match is None:
        raise SystemExit(f"no {label!r} row in {EVIDENCE_REL}")
    return [int(cell.strip()) for cell in match.group(1).split("|")]


def _fraction(text: str, pattern: str) -> tuple[int, int]:
    match = re.search(pattern, text)
    if match is None:
        raise SystemExit(f"{pattern!r} not found in {EVIDENCE_REL}")
    return (
        int(match.group(1).replace(",", "")),
        int(match.group(2).replace(",", "")),
    )


def _peak_day(counts: list[int]) -> int:
    return counts.index(max(counts))


def empirical_target() -> dict[str, Any]:
    """The comparison table, parsed from the evidence readout."""
    text = (REPO / EVIDENCE_REL).read_text(encoding="utf-8")
    header = _table_row_header(text)
    if header != list(_DATE_COLUMNS):
        raise SystemExit(f"onset table columns moved: {header}")
    onsets = {}
    for role, label in (("passenger", "Passengers"), ("crew", "Crew")):
        row = _table_row(text, label)
        daily, total = row[:-1], row[-1]
        if len(daily) != VOYAGE_DAYS or sum(daily) != total:
            raise SystemExit(f"{label} onset row does not sum to its total")
        onsets[role] = {"daily": daily, "total": total}
    inv_pax = _fraction(text, r"gives (\d+)/([\d,]+) passengers and \d+/")
    inv_crew = _fraction(text, r"gives \d+/[\d,]+ passengers and (\d+)/([\d,]+) crew")
    post_pax = _fraction(text, r"posting gives (\d+)/([\d,]+) and \d+/")
    post_crew = _fraction(text, r"posting gives \d+/[\d,]+ and (\d+)/([\d,]+)")
    for role, (cases, _denominator) in (
        ("passenger", inv_pax), ("crew", inv_crew),
    ):
        if onsets[role]["total"] != cases:
            raise SystemExit(f"{role} onset total != investigation final")
    peaks = {role: _peak_day(onsets[role]["daily"]) for role in onsets}
    return {
        "source": EVIDENCE_REL,
        "source_snapshot": EVIDENCE_SNAPSHOT,
        "source_location": (
            "CDC trip report Appendix C (labeled bars), pp. 1 and 7, as "
            "transcribed in the evidence readout; not re-transcribed here"
        ),
        "voyage": "Explorer of the Seas, Feb 26 - Mar 5 2006",
        "day_labels": list(_DATE_COLUMNS),
        "onsets_by_day": {
            role: onsets[role]["daily"] for role in onsets
        },
        "investigation_finals": {
            "passenger": {"cases": inv_pax[0], "denominator": inv_pax[1]},
            "crew": {"cases": inv_crew[0], "denominator": inv_crew[1]},
            "use": "with the onset curve",
        },
        "posting_figures": {
            "passenger": {"cases": post_pax[0], "denominator": post_pax[1]},
            "crew": {"cases": post_crew[0], "denominator": post_crew[1]},
            "use": "cross-posting comparisons only",
        },
        "peak_day_index": peaks,
        "peak_day_label": {
            role: _DATE_COLUMNS[day] for role, day in peaks.items()
        },
        "crew_minus_passenger_peak_lag_days": peaks["crew"] - peaks["passenger"],
        "preboarding_ill_passenger_surveys": 5,
    }


def _table_row_header(text: str) -> list[str]:
    match = re.search(
        r"^\|\s*Illness onsets by date\s*\|(.+)\|\s*Total\s*\|\s*$",
        text, re.MULTILINE,
    )
    if match is None:
        raise SystemExit(f"no onset table header in {EVIDENCE_REL}")
    return [cell.strip() for cell in match.group(1).split("|")]


def _complement(platform: str) -> dict[str, int]:
    layout = json.loads(
        (REPO / "data/platforms" / platform / "spatial_layout.json")
        .read_text(encoding="utf-8"),
    )
    nominal = layout["nominal_complement"]
    return {
        "passenger": int(nominal["passengers"]),
        "crew": int(nominal["crew"]),
    }


def _shipped_classes() -> list[dict[str, Any]]:
    config = yaml.safe_load(
        (REPO / "crusher_labs/config.yaml").read_text(encoding="utf-8"),
    )
    return config["ship_graph"]["agent_classes"]


def _by_role(classes: list[dict[str, Any]], counts: dict[str, int]) -> dict[str, int]:
    out = {"passenger": 0, "crew": 0}
    for cls in classes:
        out[cls["role_group"]] += counts[cls["class_id"]]
    return out


def exact_complement_block(platform: str) -> dict[str, Any]:
    """Shipped agent classes with head counts realizing the hull's complement.

    The engine splits ``num_agents`` by the shipped class fractions (70/30),
    which puts 3,102 passengers and 1,326 crew on a 4,428-agent hull. A
    class ``count`` is the engine's own grammar for a replayed population;
    each role's declared berths are divided among its classes in the shipped
    within-role proportions (largest remainder), every other class field
    verbatim.
    """
    shipped = _shipped_classes()
    berths = _complement(platform)
    total = sum(berths.values())
    counts: dict[str, int] = {}
    for role, role_total in berths.items():
        classes = [c for c in shipped if c["role_group"] == role]
        weight = sum(c["fraction"] for c in classes)
        exact = {
            c["class_id"]: role_total * c["fraction"] / weight for c in classes
        }
        counts.update({cid: int(value) for cid, value in exact.items()})
        short = role_total - sum(int(value) for value in exact.values())
        by_remainder = sorted(
            exact, key=lambda cid: (int(exact[cid]) - exact[cid], cid),
        )
        for cid in by_remainder[:short]:
            counts[cid] += 1
    return {
        "allocation": (
            "exact head counts: platform nominal_complement per role, "
            "divided among the role's classes in the shipped proportions"
        ),
        "intended": berths,
        "class_counts": counts,
        "agent_classes": [
            {
                **cls,
                "count": counts[cls["class_id"]],
                "fraction": counts[cls["class_id"]] / total,
            }
            for cls in shipped
        ],
    }


def shipped_complement_block(num_agents: int) -> dict[str, Any]:
    """What the shipped class fractions allocate, declared for assertion.

    Mirrors the engine's rule (``_allocate_class_counts``): each class takes
    ``int(total * fraction)`` and the remainder goes to the first class. No
    ``agent_classes`` override is composed; the archetype runs as shipped.
    """
    shipped = _shipped_classes()
    counts = {
        cls["class_id"]: int(num_agents * cls["fraction"]) for cls in shipped
    }
    counts[shipped[0]["class_id"]] += num_agents - sum(counts.values())
    return {
        "allocation": "shipped class fractions, no override",
        "intended": _by_role(shipped, counts),
        "class_counts": counts,
        "agent_classes": None,
    }


def tier_name(hull: str, introduction: str) -> str:
    return f"fl_{hull}_8d_recon_{introduction}"


def build_manifest() -> dict[str, Any]:
    block = frozen_block()
    explorer = _complement(PLATFORMS["exp"]["platform"])
    num_agents = {
        "exp": explorer["passenger"] + explorer["crew"],
        "meg": MEGA_NUM_AGENTS,
    }
    tiers: dict[str, dict[str, Any]] = {}
    for hull, platform in PLATFORMS.items():
        for introduction in INTRODUCTIONS:
            tiers[tier_name(hull, introduction)] = {
                "platform": platform["platform"],
                "pathogen": "norovirus",
                "dose_adjustments": [7.57],
                "surveillance_strategies": ["syndromic_comp65"],
                "epoch_durations": [EPOCHS],
                "num_agents": num_agents[hull],
                "description": (
                    f"WP3 Explorer temporal reconstruction: {platform['label']} "
                    f"({platform['platform']}), {EPOCHS} epochs, introduction "
                    f"{introduction}, Paper-1 frozen block verbatim, "
                    "syndromic_comp65, dose 7.57."
                ),
                "config_overrides": copy.deepcopy(block),
                "introduction": introduction,
                "complement": COMPLEMENTS[hull],
                "seeds": list(SEEDS),
            }
    return {
        "campaign": CAMPAIGN_NAME,
        "description": (
            "Paper-1 WP3: Explorer of the Seas Feb 26 - Mar 5 2006 temporal "
            "reconstruction on explorer_seas_06 with the mega_cruise_5000 "
            "archetype alongside on paired seeds. Scores the frozen engine "
            "against the transcribed onset curves; fits nothing."
        ),
        "platform": PLATFORMS["exp"]["platform"],
        "default_epochs": EPOCHS,
        "default_num_agents": num_agents["exp"],
        "embarkation_date": "2006-02-26",
        "natural_history_clock": "hours",
        "frozen_block_source": CONTRACT_REL,
        "pathogen_configs": copy.deepcopy(PATHOGEN_CONFIGS),
        "surveillance_configs": copy.deepcopy(SURVEILLANCE_CONFIGS),
        "introduction_blocks": copy.deepcopy(INTRODUCTIONS),
        "complement_blocks": {
            "explorer_investigation": exact_complement_block(
                PLATFORMS["exp"]["platform"],
            ),
            "archetype_shipped": shipped_complement_block(MEGA_NUM_AGENTS),
        },
        "tiers": tiers,
    }


def build_campaign() -> dict[str, Any]:
    blocks = {
        f"{hull}_{introduction}": {
            "worker": f"{CAMPAIGN_REL}/cell.py",
            "tier": tier_name(hull, introduction),
            "seeds": list(SEEDS),
        }
        for hull in PLATFORMS
        for introduction in INTRODUCTIONS
    }
    return {
        "name": CAMPAIGN_NAME,
        "pathogen": "norovirus",
        "manifest": f"{CAMPAIGN_REL}/manifest.json",
        "pathogen_id": PATHOGEN_ID,
        "epochs": EPOCHS,
        "s3_prefix": f"campaign/{CAMPAIGN_NAME}/",
        "queue": "picard-campaign-queue",
        "image_tag": "noro-explorer-recon01",
        "resources": {"vcpu": "1", "memory": "8192", "shm": 512},
        "readout": f"{CAMPAIGN_REL}/readout.py",
        "canary": {"block": "exp_declared_five", "seeds": CANARY_SEEDS},
        "blocks": blocks,
    }


def outputs() -> dict[str, str]:
    """Generated file name -> serialized content."""
    return {
        "manifest.json": json.dumps(build_manifest(), indent=1) + "\n",
        "campaign.json": json.dumps(build_campaign(), indent=1) + "\n",
        "empirical_target.json": json.dumps(empirical_target(), indent=1) + "\n",
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--check", action="store_true",
        help="fail when a committed generated file differs from a rebuild",
    )
    args = parser.parse_args(argv)
    stale = []
    for name, content in outputs().items():
        path = CAMPAIGN_DIR / name
        if args.check:
            if not path.is_file() or path.read_text(encoding="utf-8") != content:
                stale.append(name)
            continue
        path.write_text(content, encoding="utf-8")
        print(f"wrote {path.relative_to(REPO)}")
    if stale:
        print(f"STALE: {', '.join(stale)}", file=sys.stderr)
        return 1
    if args.check:
        manifest = build_manifest()
        cells = sum(len(t["seeds"]) for t in manifest["tiers"].values())
        print(f"check ok: {len(manifest['tiers'])} tiers, {cells} cells")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
