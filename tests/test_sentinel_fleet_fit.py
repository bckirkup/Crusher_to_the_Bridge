"""The fleet fit path: manifest -> assembled fleet -> pooled hazard files.

Contract tests on the runner, not the estimator (that is
``test_sentinel_fleet_validation``): that manifest entries resolve against the
manifest rather than the caller's directory, that a mismatched
itinerary/observation pair is refused instead of silently pooled, and that the
output files carry the port/visit/week keys a reader needs to interpret them.

Everything here runs from paths inside the repository because
``picard_framework.analysis._io`` confines reads and writes to the process CWD
(Sonar S8707); a manifest under ``/tmp`` is refused by design, so the scratch
directory is a repo subdirectory rather than ``tmp_path``.
"""

from __future__ import annotations

import csv
import json
import os
import shutil
import sys
from typing import Any, Iterator

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from picard_framework.analysis.sentinel.fleet import (
    FLEET_HAZARD_COLUMNS,
    VISIT_HAZARD_COLUMNS,
)
from picard_framework.analysis.stan._sentinel_fleet_data import (
    build_sentinel_fleet_data,
)
from picard_framework.analysis.stan.fit_sentinel_fleet import (
    SamplerOptions,
    fit_sentinel_fleet,
    load_fleet_manifest,
    load_fleet_voyages,
    main,
    stan_model_path,
    write_fleet_outputs,
)
from tests.test_sentinel_attribution import GENERATION, INCUBATION

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(REPO, "picard_framework", "analysis", "sentinel", "data")
FLEET_MANIFEST = os.path.join(DATA, "example_fleet.json")


def write_manifest(directory: str, payload: Any, name: str = "fleet.json") -> str:
    path = os.path.join(directory, name)
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(payload, fh)
    return path


@pytest.fixture
def scratch() -> Iterator[str]:
    """A scratch directory under the repo: analysis I/O refuses paths outside CWD."""
    base = os.path.join(REPO, "out_test_fleet_fit")
    shutil.rmtree(base, ignore_errors=True)
    os.makedirs(base)
    try:
        yield base
    finally:
        shutil.rmtree(base, ignore_errors=True)


@pytest.fixture
def out_dir(scratch: str) -> str:
    return scratch


def test_committed_manifest_resolves_to_files_that_exist() -> None:
    pairs = load_fleet_manifest(FLEET_MANIFEST)
    assert len(pairs) == 3
    for itinerary, observations in pairs:
        assert os.path.isabs(itinerary)
        assert os.path.isfile(itinerary)
        assert os.path.isabs(observations)
        assert os.path.isfile(observations)


def test_relative_entries_resolve_against_the_manifest_directory(
    scratch: str,
) -> None:
    """A manifest one directory deep names its voyages relative to itself.

    Resolving against the caller's directory instead would make the same manifest
    mean different fleets depending on where it was run from.
    """
    nested = os.path.join(scratch, "nested")
    os.makedirs(nested)
    relative_data = os.path.relpath(DATA, nested)
    path = write_manifest(
        nested,
        {
            "voyages": [
                {
                    "itinerary": os.path.join(relative_data, "example_itinerary.json"),
                    "observations": os.path.join(
                        relative_data, "example_observations.json",
                    ),
                },
            ],
        },
    )
    (itinerary, observations), = load_fleet_manifest(path)
    assert os.path.realpath(itinerary) == os.path.join(DATA, "example_itinerary.json")
    assert os.path.realpath(observations) == os.path.join(
        DATA, "example_observations.json",
    )


def test_absolute_manifest_entries_are_left_alone(scratch: str) -> None:
    itinerary = os.path.join(DATA, "example_itinerary.json")
    observations = os.path.join(DATA, "example_observations.json")
    path = write_manifest(
        scratch,
        {"voyages": [{"itinerary": itinerary, "observations": observations}]},
    )
    assert load_fleet_manifest(path) == [(itinerary, observations)]


@pytest.mark.parametrize(
    ("payload", "message"),
    [
        ([], "must be an object"),
        ({}, "lists no voyages"),
        ({"voyages": []}, "lists no voyages"),
        ({"voyages": ["a.json"]}, "is not an object"),
        ({"voyages": [{"observations": "o.json"}]}, "has no itinerary"),
        ({"voyages": [{"itinerary": "i.json"}]}, "has no observations"),
        ({"voyages": [{"itinerary": "", "observations": "o.json"}]}, "has no itinerary"),
    ],
)
def test_malformed_manifests_are_refused(
    scratch: str, payload: Any, message: str,
) -> None:
    path = write_manifest(scratch, payload)
    with pytest.raises(ValueError, match=message):
        load_fleet_manifest(path)


def test_a_missing_voyage_file_is_not_silently_dropped(scratch: str) -> None:
    path = write_manifest(
        scratch,
        {
            "voyages": [
                {
                    "itinerary": os.path.join(DATA, "example_itinerary.json"),
                    "observations": os.path.join(DATA, "no_such_observations.json"),
                },
            ],
        },
    )
    pairs = load_fleet_manifest(path)
    with pytest.raises((FileNotFoundError, OSError, ValueError)):
        load_fleet_voyages(pairs)


def test_observations_that_contradict_the_itinerary_are_refused(scratch: str) -> None:
    """A case ashore at a port the ship never called at must abort the fleet.

    Pooling it would credit a hazard to a visit that is not in the design, and
    the whole point of the denominator is that every case sits over exposure the
    itinerary actually contains.
    """
    with open(os.path.join(DATA, "example_observations.json"), encoding="utf-8") as fh:
        bundle = json.load(fh)
    bundle["clinical_cases"][0]["hours_ashore"] = {"JMMBJ": 6.0}
    observations = os.path.join(scratch, "bad_observations.json")
    with open(observations, "w", encoding="utf-8") as fh:
        json.dump(bundle, fh)

    path = write_manifest(
        scratch,
        {
            "voyages": [
                {
                    "itinerary": os.path.join(DATA, "example_itinerary.json"),
                    "observations": observations,
                },
            ],
        },
    )
    pairs = load_fleet_manifest(path)
    with pytest.raises(ValueError, match="do not match the itinerary"):
        load_fleet_voyages(pairs)


def test_a_bundle_may_be_paired_with_any_itinerary_shape(scratch: str) -> None:
    """The runner takes voyage identity *from the bundle*, so ids cannot mismatch.

    Recorded deliberately: pairing week 2's observations with week 1's itinerary
    file is accepted, because the itinerary contributes only the port/day shape
    and the bundle names the voyage. The date that drives fleet-time pooling
    therefore comes from the itinerary, so a manifest that points a bundle at the
    wrong itinerary file will pool it into the wrong week and nothing here will
    catch it. The manifest is the trusted input.
    """
    path = write_manifest(
        scratch,
        {
            "voyages": [
                {
                    "itinerary": os.path.join(DATA, "example_itinerary.json"),
                    "observations": os.path.join(
                        DATA, "example_observations_week2.json",
                    ),
                },
            ],
        },
    )
    voyages, _ = load_fleet_voyages(load_fleet_manifest(path))
    assert voyages[0].voyage.voyage_id == "VOY-2026-01-17-ENDEAVOR"


def test_ascertainment_scales_the_assembled_fleet() -> None:
    """Under-ascertainment must reach the design, or hazards absorb it."""
    pairs = load_fleet_manifest(FLEET_MANIFEST)
    full, pathogen = load_fleet_voyages(pairs)
    partial, _ = load_fleet_voyages(pairs, reporting=0.5)
    assert pathogen
    assert [v.design.ascertainment for v in full] == [1.0] * len(full)
    assert [v.design.ascertainment for v in partial] == [0.5] * len(partial)


def test_fleet_outputs_carry_the_keys_needed_to_read_them(out_dir: str) -> None:
    """Port, visit, and week rows are written with their identifiers intact."""
    voyages, pathogen = load_fleet_voyages(load_fleet_manifest(FLEET_MANIFEST))
    data, meta = build_sentinel_fleet_data(voyages, INCUBATION, GENERATION)

    # A deterministic stand-in posterior: this test is about the writer, and a
    # real fit is exercised by the smoke test below.
    posterior: dict[str, list[float]] = {}
    for i in range(1, len(meta["ports"]) + 1):
        posterior[f"lambda_port[{i}]"] = [1.0e-4 * i, 2.0e-4 * i, 3.0e-4 * i]
        posterior[f"imported_cases[{i}]"] = [1.0, 2.0, 3.0]
        posterior[f"attribution_share[{i}]"] = [0.2, 0.3, 0.4]
    for i in range(1, int(data["NV"]) + 1):
        posterior[f"lambda_visit[{i}]"] = [1.0e-4, 2.0e-4, 4.0e-4]
        posterior[f"imported_cases_visit[{i}]"] = [1.0, 2.0, 3.0]
    for i in range(1, int(data["W"]) + 1):
        posterior[f"fleet_time[{i}]"] = [-0.2, 0.0, 0.3]
    for i in range(1, int(data["S"]) + 1):
        posterior[f"lambda_aboard[{i}]"] = [1.0e-6, 2.0e-6, 3.0e-6]
        posterior[f"R_onboard[{i}]"] = [0.3, 0.5, 0.7]
    posterior["aboard_cases"] = [1.0, 2.0, 3.0]
    posterior["secondary_cases"] = [0.5, 1.0, 1.5]
    posterior["import_share"] = [0.5, 0.6, 0.7]
    posterior["crew_hazard_ratio"] = [0.9, 1.0, 1.1]
    posterior["repeat_hazard_ratio"] = [0.8, 1.0, 1.2]
    posterior["loglik_clinical"] = [-60.0, -61.0, -62.0]

    summary = write_fleet_outputs(out_dir, posterior, meta, pathogen)
    assert summary["n_ports"] == len(meta["ports"])
    assert summary["n_visits"] == int(data["NV"])
    assert summary["n_weeks"] == int(data["W"])

    with open(os.path.join(out_dir, "fleet_port_hazards.csv"), encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh))
    assert list(rows[0]) == list(FLEET_HAZARD_COLUMNS)
    assert [r["port_id"] for r in rows] == meta["ports"]
    assert all(r["pathogen"] == pathogen for r in rows)

    with open(os.path.join(out_dir, "visit_hazards.csv"), encoding="utf-8") as fh:
        visit_rows = list(csv.DictReader(fh))
    assert list(visit_rows[0]) == list(VISIT_HAZARD_COLUMNS)
    assert [r["visit_key"] for r in visit_rows] == [
        v["visit_key"] for v in meta["visits"]
    ]
    assert {r["port_id"] for r in visit_rows} == set(meta["ports"])

    with open(os.path.join(out_dir, "fleet_time.csv"), encoding="utf-8") as fh:
        week_rows = list(csv.DictReader(fh))
    assert [r["week"] for r in week_rows] == meta["weeks"]

    with open(os.path.join(out_dir, "onboard_summary.json"), encoding="utf-8") as fh:
        onboard = json.load(fh)
    assert [s["ship_id"] for s in onboard["ships"]] == meta["ships"]
    assert 0.0 <= onboard["import_share_mean"] <= 1.0

    with open(os.path.join(out_dir, "crew_exposure.json"), encoding="utf-8") as fh:
        crew = json.load(fh)
    assert crew["crew_hazard_ratio_mean"] > 0.0
    assert crew["repeat_hazard_ratio_mean"] > 0.0


def test_a_posterior_missing_a_column_fails_loudly(out_dir: str) -> None:
    """Half-written summaries are worse than none: the reader cannot tell."""
    voyages, pathogen = load_fleet_voyages(load_fleet_manifest(FLEET_MANIFEST))
    _, meta = build_sentinel_fleet_data(voyages, INCUBATION, GENERATION)
    with pytest.raises(KeyError, match="lambda_port"):
        write_fleet_outputs(out_dir, {"import_share": [0.5]}, meta, pathogen)


def test_smoke_fit_writes_every_output_for_the_example_fleet(out_dir: str) -> None:
    """End to end on the committed three-voyage manifest, no CmdStan required."""
    status = fit_sentinel_fleet(
        FLEET_MANIFEST,
        out_dir,
        smoke=True,
        sampler=SamplerOptions(show_progress=False),
    )
    assert status["status"] == "smoke"
    assert status["engine"] == "numpy_rw_mh"
    for name in (
        "fleet_port_hazards.csv",
        "visit_hazards.csv",
        "fleet_time.csv",
        "onboard_summary.json",
        "crew_exposure.json",
        "stan_data_meta.json",
        "fit_status.json",
    ):
        assert os.path.getsize(os.path.join(out_dir, name)) > 0, name

    meta = status["meta"]
    # The manifest pools two ships in one week and the same ship a week later:
    # three voyages and ports that recur across them. Visits span three
    # calendar weeks because the home-port calls sit on the voyage boundaries.
    assert len(meta["voyages"]) == 3
    assert len(meta["ships"]) == 2
    assert len(meta["weeks"]) == 3
    assert status["summary"]["n_visits"] > len(meta["ports"])
    assert all(v > 0.0 for v in status["summary"]["hazard_mean"].values())


def test_cli_exit_code_and_engine_choice(out_dir: str) -> None:
    assert (
        main([FLEET_MANIFEST, "--out", out_dir, "--smoke", "--no-show-progress"]) == 0
    )
    with open(os.path.join(out_dir, "fit_status.json"), encoding="utf-8") as fh:
        assert json.load(fh)["status"] == "smoke"


def test_stan_source_carries_the_terms_the_runner_reads() -> None:
    """The runner names parameters by string; a renamed block must fail here."""
    with open(stan_model_path(), encoding="utf-8") as fh:
        source = fh.read()
    for symbol in (
        "fleet_time",
        "crew_repeat",
        "lambda_port",
        "lambda_visit",
        "R_onboard",
        "import_share",
        "repeat_hazard_ratio",
        "loglik_clinical",
    ):
        assert symbol in source, symbol
