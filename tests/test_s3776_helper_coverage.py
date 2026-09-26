"""Targeted coverage for helpers extracted during the S3776 split.

The Sonar new-code gate counts moved-but-previously-uncovered lines as new
code; these tests pin the extracted helpers' behavior so the refactors stay
covered without depending on external binaries.
"""

from __future__ import annotations

import xml.etree.ElementTree as ET

import pytest

from tools.ship_blueprint_import import validate as bp_validate
from tools.ship_blueprint_import.svg_io import (
    _overlay_polygon_from_elem,
    _parse_path_d,
    _polygon_points_from_elem,
    _shape_id,
)


class TestParsePathD:
    def test_absolute_move_line(self) -> None:
        assert _parse_path_d("M 10 20 L 30 40") == [(10.0, 20.0), (30.0, 40.0)]

    def test_relative_commands(self) -> None:
        assert _parse_path_d("m 10 20 l 5 5 h 5 v -5") == [
            (10.0, 20.0),
            (15.0, 25.0),
            (20.0, 25.0),
            (20.0, 20.0),
        ]

    def test_horizontal_vertical_absolute(self) -> None:
        assert _parse_path_d("M0 0 H10 V10") == [(0.0, 0.0), (10.0, 0.0), (10.0, 10.0)]

    def test_implicit_line_after_move(self) -> None:
        assert _parse_path_d("M 0 0 5 5 10 0") == [
            (0.0, 0.0),
            (5.0, 5.0),
            (10.0, 0.0),
        ]

    def test_close_path_returns_to_start(self) -> None:
        pts = _parse_path_d("M0 0 L10 0 L10 10 Z")
        assert pts[-1] == (0.0, 0.0)

    def test_close_path_no_duplicate_when_already_at_start(self) -> None:
        pts = _parse_path_d("M0 0 L10 0 L0 0 Z")
        assert pts[-1] == (0.0, 0.0)
        assert pts.count((0.0, 0.0)) == 2

    @pytest.mark.parametrize(
        ("cmd", "args"),
        [
            ("C", "1 1 2 2 3 4"),
            ("c", "1 1 2 2 3 4"),
            ("S", "2 2 3 4"),
            ("s", "2 2 3 4"),
            ("Q", "1 1 3 4"),
            ("q", "1 1 3 4"),
            ("T", "3 4"),
            ("t", "3 4"),
            ("A", "1 1 0 0 1 3 4"),
            ("a", "1 1 0 0 1 3 4"),
        ],
    )
    def test_curves_keep_only_end_point(self, cmd: str, args: str) -> None:
        pts = _parse_path_d(f"M0 0 {cmd} {args}")
        assert pts[0] == (0.0, 0.0)
        assert pts[-1] == (3.0, 4.0)

    def test_truncated_path_raises(self) -> None:
        with pytest.raises(ValueError, match="unexpected end"):
            _parse_path_d("M 5")

    def test_number_after_close_raises(self) -> None:
        with pytest.raises(ValueError, match="close-path"):
            _parse_path_d("M0 0 Z 5")


class TestPolygonPointsFromElem:
    def test_rect(self) -> None:
        elem = ET.fromstring('<rect x="1" y="2" width="3" height="4"/>')
        pts = _polygon_points_from_elem(elem)
        assert pts == [(1.0, 2.0), (4.0, 2.0), (4.0, 6.0), (1.0, 6.0), (1.0, 2.0)]

    def test_polygon(self) -> None:
        elem = ET.fromstring('<polygon points="0,0 4,0 4,4"/>')
        assert _polygon_points_from_elem(elem) == [(0.0, 0.0), (4.0, 0.0), (4.0, 4.0)]

    def test_polygon_too_few_points(self) -> None:
        elem = ET.fromstring('<polygon points="0,0 4,0"/>')
        with pytest.raises(ValueError, match="at least 3"):
            _polygon_points_from_elem(elem)

    def test_path_missing_d(self) -> None:
        elem = ET.fromstring("<path/>")
        with pytest.raises(ValueError, match="missing d"):
            _polygon_points_from_elem(elem)

    def test_unsupported_shape(self) -> None:
        elem = ET.fromstring("<ellipse/>")
        with pytest.raises(ValueError, match="unsupported SVG shape"):
            _polygon_points_from_elem(elem)


class TestOverlayPolygonFromElem:
    def test_reserved_zone_id_skipped(self) -> None:
        elem = ET.fromstring('<rect x="0" y="0" width="1" height="1"/>')
        assert _overlay_polygon_from_elem(elem, "_page_bounds", None) is None

    def test_degenerate_shape_skipped(self) -> None:
        elem = ET.fromstring("<ellipse/>")
        assert _overlay_polygon_from_elem(elem, "ZoneA", 0) is None

    def test_valid_polygon(self) -> None:
        elem = ET.fromstring('<polygon points="0,0 4,0 4,4"/>')
        poly = _overlay_polygon_from_elem(elem, "ZoneA", 2)
        assert poly is not None
        assert poly.zone_id == "ZoneA"
        assert poly.page == 2
        assert len(poly.points) == 3


class TestShapeId:
    def test_id_attribute(self) -> None:
        elem = ET.fromstring('<path id="My Zone"/>')
        assert _shape_id(elem) == "My_Zone"

    def test_title_fallback(self) -> None:
        elem = ET.fromstring("<path><title>Engine Room</title></path>")
        assert _shape_id(elem) == "Engine_Room"

    def test_no_id(self) -> None:
        elem = ET.fromstring("<path/>")
        assert _shape_id(elem) is None


class _FakeProc:
    def __init__(self, returncode: int, stdout: str = "", stderr: str = "") -> None:
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = stderr


class TestValidateViaCli:
    def test_missing_data_and_schema_failure(
        self, tmp_path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        platform = tmp_path / "platform"
        schemas = tmp_path / "schemas"
        platform.mkdir()
        schemas.mkdir()
        (platform / "a.json").write_text("{}")
        (schemas / "a.schema.json").write_text("{}")

        calls: list[list[str]] = []

        def fake_run(cmd, capture_output=False, text=False):  # noqa: ARG001
            calls.append(cmd)
            return _FakeProc(1, stdout="schema mismatch")

        monkeypatch.setattr(bp_validate.subprocess, "run", fake_run)

        errors = bp_validate._validate_via_cli(
            [("a.json", "a.schema.json"), ("missing.json", "missing.schema.json")],
            str(platform),
            str(schemas),
        )
        assert errors == ["a.json: schema mismatch", "missing missing.json"]
        assert len(calls) == 1

    def test_success(self, tmp_path, monkeypatch: pytest.MonkeyPatch) -> None:
        platform = tmp_path / "platform"
        schemas = tmp_path / "schemas"
        platform.mkdir()
        schemas.mkdir()
        (platform / "a.json").write_text("{}")
        (schemas / "a.schema.json").write_text("{}")

        monkeypatch.setattr(
            bp_validate.subprocess, "run", lambda *a, **k: _FakeProc(0)
        )
        assert (
            bp_validate._validate_via_cli(
                [("a.json", "a.schema.json")], str(platform), str(schemas)
            )
            == []
        )


class TestRunContamBootstrap:
    def test_success(self, monkeypatch: pytest.MonkeyPatch) -> None:
        import tools.ship_blueprint_import.author_contam as ac

        monkeypatch.setattr(
            ac,
            "author_contam",
            lambda **kw: {
                "prj_path": "/p/platform.prj",
                "openings_count": 3,
                "offline_gate": {"ok": True},
            },
        )
        ok, msg, gate = bp_validate._run_contam_bootstrap("/p", (), None)
        assert ok is True
        assert "offline_gate=PASS" in msg
        assert gate is None

    def test_gate_failure(self, monkeypatch: pytest.MonkeyPatch) -> None:
        import tools.ship_blueprint_import.author_contam as ac

        monkeypatch.setattr(
            ac,
            "author_contam",
            lambda **kw: {
                "prj_path": "/p/platform.prj",
                "openings_count": 0,
                "offline_gate": {"ok": False},
            },
        )
        ok, msg, gate = bp_validate._run_contam_bootstrap("/p", (), None)
        assert ok is False
        assert "offline_gate=FAIL" in msg
        assert gate == {"ok": False}

    def test_exception(self, monkeypatch: pytest.MonkeyPatch) -> None:
        import tools.ship_blueprint_import.author_contam as ac

        def boom(**kw):  # noqa: ARG001
            raise RuntimeError("no contam")

        monkeypatch.setattr(ac, "author_contam", boom)
        ok, msg, gate = bp_validate._run_contam_bootstrap("/p", (), None)
        assert ok is False
        assert "author_contam FAILED" in msg
        assert gate is None


class TestRunContamGate:
    def test_missing_prj(self, tmp_path) -> None:
        ok, result = bp_validate._run_contam_gate(str(tmp_path), ())
        assert ok is False
        assert "missing contam/platform.prj" in str(result)

    def test_gate_result(self, tmp_path, monkeypatch: pytest.MonkeyPatch) -> None:
        import tools.ship_blueprint_import.author_contam as ac

        prj_dir = tmp_path / "contam"
        prj_dir.mkdir()
        (prj_dir / "platform.prj").write_text("dummy")
        monkeypatch.setattr(
            ac, "validate_prj_offline", lambda prj, allowed_roots: {"ok": True}
        )
        ok, result = bp_validate._run_contam_gate(str(tmp_path), ())
        assert ok is True
        assert result == {"ok": True}


class TestValidatePlatformContamBranches:
    def test_bootstrap_and_gate_invoked(
        self, tmp_path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(bp_validate, "validate_against_schemas", lambda *a, **k: [])
        monkeypatch.setattr(
            bp_validate, "run_sanity_checker", lambda *a, **k: (True, "sane")
        )
        monkeypatch.setattr(
            bp_validate,
            "_run_contam_bootstrap",
            lambda *a: (True, "bootstrap msg", None),
        )
        monkeypatch.setattr(
            bp_validate, "_run_contam_gate", lambda *a: (True, {"ok": True})
        )

        out = bp_validate.validate_platform(
            str(tmp_path),
            allowed_roots=(),
            contam_bootstrap=True,
            contam_gate=True,
        )
        assert out["ok"] is True
        assert out["contam_bootstrap"] == "bootstrap msg"
        assert out["contam_gate"] == {"ok": True}


class TestDisruptionSite:
    @staticmethod
    def _assay(profiles: dict) -> object:
        from crusher_labs.observation_core import ClinicalMicrobiology

        return ClinicalMicrobiology(pathogen_profiles=profiles)

    def _infections(self, *pids: str) -> dict:
        return {pid: {"status": "INFECTED"} for pid in pids}

    def test_syndrome_gastrointestinal(self) -> None:
        assay = self._assay(
            {"noro": {"clinical_presentation": {"syndromes": ["gastrointestinal"]}}}
        )
        assert assay._disruption_site(self._infections("noro")) == "gastrointestinal"

    def test_syndrome_respiratory(self) -> None:
        assay = self._assay(
            {"fluX": {"clinical_presentation": {"syndromes": ["respiratory"]}}}
        )
        assert assay._disruption_site(self._infections("fluX")) == "respiratory"

    def test_sample_type_fallbacks(self) -> None:
        stool = self._assay(
            {"p1": {"clinical_presentation": {"sample_types": ["stool"]}}}
        )
        assert stool._disruption_site(self._infections("p1")) == "gastrointestinal"
        swab = self._assay(
            {"p2": {"clinical_presentation": {"sample_types": ["np_swab"]}}}
        )
        assert swab._disruption_site(self._infections("p2")) == "respiratory"
        spec = self._assay(
            {"p3": {"clinical_presentation": {"sample_types": ["respiratory_specimen"]}}}
        )
        assert spec._disruption_site(self._infections("p3")) == "respiratory"

    def test_disruption_type_fallback(self) -> None:
        assay = self._assay(
            {"p1": {"microflora_disruption": {"disruption_type": "gastro_shift"}}}
        )
        assert assay._disruption_site(self._infections("p1")) == "gastrointestinal"
        assay2 = self._assay(
            {"p2": {"microflora_disruption": {"disruption_type": "resp_flora"}}}
        )
        assert assay2._disruption_site(self._infections("p2")) == "respiratory"

    def test_legacy_fallback_substrings(self) -> None:
        assay = self._assay({})
        assert assay._disruption_site(self._infections("enteric_virus")) == (
            "gastrointestinal"
        )
        assert assay._disruption_site(self._infections("cov_variant")) == "respiratory"
        assert assay._disruption_site(self._infections("unknown_pid")) == "skin"

    def test_inactive_infection_falls_to_legacy(self) -> None:
        assay = self._assay(
            {"noro": {"clinical_presentation": {"syndromes": ["gastrointestinal"]}}}
        )
        assert assay._disruption_site({"noro": {"status": "RECOVERED"}}) == "skin"
