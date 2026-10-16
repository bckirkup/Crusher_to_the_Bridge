"""
test_ship_blueprint_import.py – Naval GA → platform importer (offline)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Golden-value + config-sensitivity coverage for
``tools.ship_blueprint_import`` without live LLM calls.
"""

from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
TEMPLATE_DIGEST = (
    REPO_ROOT
    / "tools"
    / "ship_blueprint_import"
    / "templates"
    / "toy_destroyer_digest.json"
)
FIXTURES = REPO_ROOT / "tests" / "fixtures" / "blueprint_import"


@pytest.fixture
def roots(tmp_path: Path) -> tuple[str, ...]:
    return (str(tmp_path), str(REPO_ROOT))


def _make_page_png(path: Path, width: int = 400, height: int = 200) -> None:
    from PIL import Image

    img = Image.new("RGB", (width, height), color=(20, 40, 80))
    path.parent.mkdir(parents=True, exist_ok=True)
    img.save(path)


def _seed_workdir(workdir: Path, *, width: int = 400, height: int = 200) -> None:
    pages = workdir / "pages"
    pages.mkdir(parents=True, exist_ok=True)
    _make_page_png(pages / "page_01.png", width=width, height=height)
    manifest = {
        "schema_version": "1.0",
        "input_kind": "images",
        "dpi": 150,
        "sources": [],
        "source_sha256": {},
        "pages": [
            {
                "page": 1,
                "file": "pages/page_01.png",
                "width": width,
                "height": height,
                "dpi": 150,
            }
        ],
    }
    (workdir / "pages_manifest.json").write_text(
        json.dumps(manifest, indent=2) + "\n", encoding="utf-8"
    )
    shutil.copy(TEMPLATE_DIGEST, workdir / "ship_digest.json")


class TestSvgIo:
    def test_round_trip_named_paths(self) -> None:
        from tools.ship_blueprint_import.svg_io import (
            OverlayPolygon,
            read_overlay_svg,
            write_overlay_svg,
        )

        polys = [
            OverlayPolygon(
                zone_id="Bridge",
                points=[(10, 10), (90, 10), (90, 40), (10, 40), (10, 10)],
            ),
            OverlayPolygon(
                zone_id="Berthing",
                points=[(10, 50), (100, 50), (100, 120), (10, 120)],
            ),
        ]
        svg = write_overlay_svg(polys, width=200, height=150)
        parsed = read_overlay_svg(svg)
        ids = {p.zone_id for p in parsed}
        assert ids == {"Bridge", "Berthing"}
        bridge = next(p for p in parsed if p.zone_id == "Bridge")
        assert bridge.area_px() > 0

    def test_rejects_unnamed_paths(self) -> None:
        from tools.ship_blueprint_import.svg_io import read_overlay_svg

        svg = """<svg xmlns="http://www.w3.org/2000/svg" width="10" height="10">
          <path d="M 0 0 L 10 0 L 10 10 Z"/>
        </svg>"""
        with pytest.raises(ValueError, match="unnamed"):
            read_overlay_svg(svg)

    def test_blank_template_parses(self) -> None:
        from tools.ship_blueprint_import.svg_io import read_overlay_svg

        text = (
            REPO_ROOT
            / "tools"
            / "ship_blueprint_import"
            / "templates"
            / "blank_overlay.svg"
        ).read_text(encoding="utf-8")
        polys = read_overlay_svg(text)
        assert {p.zone_id for p in polys} >= {"Bridge", "Berthing", "Engine_Room"}


class TestShipDigestModel:
    def test_template_validates(self) -> None:
        from tools.ship_blueprint_import.models import ShipDigest

        data = json.loads(TEMPLATE_DIGEST.read_text(encoding="utf-8"))
        digest = ShipDigest.model_validate(data)
        assert digest.platform_id == "toy_destroyer"
        assert len(digest.zones) == 6
        assert any(z.type == "Room" for z in digest.zones)

    def test_schema_file_exists(self) -> None:
        schema = REPO_ROOT / "schemas" / "ship_digest.schema.json"
        assert schema.is_file()
        data = json.loads(schema.read_text(encoding="utf-8"))
        assert data["$id"] == "ship_digest.schema.json"

    def test_schema_validates_template(self) -> None:
        jsonschema = pytest.importorskip("jsonschema")
        schema = json.loads(
            (REPO_ROOT / "schemas" / "ship_digest.schema.json").read_text(
                encoding="utf-8"
            )
        )
        data = json.loads(TEMPLATE_DIGEST.read_text(encoding="utf-8"))
        jsonschema.Draft202012Validator(schema).validate(data)


class TestIngest:
    def test_ingest_image_folder(self, tmp_path: Path, roots: tuple[str, ...]) -> None:
        from tools.ship_blueprint_import.ingest import ingest

        src = tmp_path / "src_images"
        src.mkdir()
        _make_page_png(src / "deck_a.png", width=120, height=80)
        _make_page_png(src / "deck_b.png", width=120, height=80)
        workdir = tmp_path / "work"
        manifest = ingest(
            input_path=str(src),
            workdir=str(workdir),
            dpi=72.0,
            allowed_roots=roots,
        )
        assert len(manifest["pages"]) == 2
        assert (workdir / "pages" / "page_01.png").is_file()
        assert (workdir / "pages_manifest.json").is_file()


class TestMockDigestAndSynthesize:
    def test_mock_digest_writes_draft_svg(
        self, tmp_path: Path, roots: tuple[str, ...]
    ) -> None:
        from tools.ship_blueprint_import.digest import digest_workdir
        from tools.ship_blueprint_import.svg_io import read_overlay_svg

        workdir = tmp_path / "wd"
        _seed_workdir(workdir)
        # Remove pre-copied digest so mock fixture is used
        (workdir / "ship_digest.json").unlink()
        digest = digest_workdir(
            workdir=str(workdir),
            provider_name="mock",
            allowed_roots=roots,
        )
        assert digest.platform_id == "toy_destroyer"
        draft = workdir / "overlays" / "page_01_draft.svg"
        assert draft.is_file()
        polys = read_overlay_svg(draft.read_text(encoding="utf-8"))
        assert "Berthing" in {p.zone_id for p in polys}

    def test_synthesize_golden_zone_count(
        self, tmp_path: Path, roots: tuple[str, ...]
    ) -> None:
        from tools.ship_blueprint_import.digest import draft_svgs_from_digest
        from tools.ship_blueprint_import.models import ShipDigest
        from tools.ship_blueprint_import.synthesize import synthesize

        workdir = tmp_path / "wd"
        _seed_workdir(workdir)
        digest = ShipDigest.model_validate(
            json.loads((workdir / "ship_digest.json").read_text(encoding="utf-8"))
        )
        manifest = json.loads(
            (workdir / "pages_manifest.json").read_text(encoding="utf-8")
        )
        overlays = workdir / "overlays"
        draft_svgs_from_digest(
            digest, manifest, str(overlays), allowed_roots=roots, suffix="approved"
        )

        out = tmp_path / "platforms" / "toy_destroyer"
        result = synthesize(
            workdir=str(workdir),
            output_dir=str(out),
            platform_id="toy_destroyer",
            allowed_roots=roots,
            require_approved=True,
        )
        assert result["zone_count"] == 6
        spatial = json.loads((out / "spatial_layout.json").read_text(encoding="utf-8"))
        airflow = json.loads((out / "air_flow_paths.json").read_text(encoding="utf-8"))
        assert spatial["platform"] == "toy_destroyer"
        assert spatial["graywater_zones"] == ["Engine_Room"]
        assert len(spatial["zones"]) == 6
        assert all(z["volume_m3"] > 0 for z in spatial["zones"])
        assert all("display" in z and "x" in z["display"] for z in spatial["zones"])
        assert {z["id"] for z in spatial["zones"]} >= {
            "Bridge",
            "Berthing",
            "Engine_Room",
        }
        berthing = next(z for z in spatial["zones"] if z["id"] == "Berthing")
        assert berthing["type"] == "Room"
        assert berthing["volume_m3"] == pytest.approx(150.0, rel=0.01)
        assert airflow["platform"] == "toy_destroyer"
        assert len(airflow["hvac_zones"]) == 3
        room_sets = [set(h["rooms"]) for h in airflow["hvac_zones"]]
        assert {"Berthing", "Engine_Room"} in room_sets
        assert len(airflow["cross_zone_links"]) == 2
        assert (out / "import_provenance.json").is_file()

    def test_synthesize_fails_without_berthing(
        self, tmp_path: Path, roots: tuple[str, ...]
    ) -> None:
        from tools.ship_blueprint_import.digest import draft_svgs_from_digest
        from tools.ship_blueprint_import.models import ShipDigest
        from tools.ship_blueprint_import.synthesize import synthesize

        workdir = tmp_path / "wd"
        _seed_workdir(workdir)
        data = json.loads((workdir / "ship_digest.json").read_text(encoding="utf-8"))
        data["zones"] = [
            z for z in data["zones"] if z["type"] != "Room" and "Berth" not in z["id"]
        ]
        data["hvac_hints"] = []
        (workdir / "ship_digest.json").write_text(
            json.dumps(data, indent=2) + "\n", encoding="utf-8"
        )
        digest = ShipDigest.model_validate(data)
        manifest = json.loads(
            (workdir / "pages_manifest.json").read_text(encoding="utf-8")
        )
        draft_svgs_from_digest(
            digest,
            manifest,
            str(workdir / "overlays"),
            allowed_roots=roots,
            suffix="approved",
        )
        with pytest.raises(RuntimeError, match="berthing"):
            synthesize(
                workdir=str(workdir),
                output_dir=str(tmp_path / "out"),
                allowed_roots=roots,
                require_approved=True,
            )

    def test_ceiling_height_sensitivity(
        self, tmp_path: Path, roots: tuple[str, ...]
    ) -> None:
        """Config sensitivity: changing ceiling_height_m changes volumes."""
        from tools.ship_blueprint_import.digest import draft_svgs_from_digest
        from tools.ship_blueprint_import.models import ShipDigest
        from tools.ship_blueprint_import.synthesize import synthesize

        def _run(ceiling: float, out_name: str) -> float:
            workdir = tmp_path / f"wd_{out_name}"
            _seed_workdir(workdir)
            data = json.loads((workdir / "ship_digest.json").read_text(encoding="utf-8"))
            # Force geometry-driven volume (clear estimates)
            for z in data["zones"]:
                z.pop("volume_m3_est", None)
            data["ceiling_height_m"] = ceiling
            (workdir / "ship_digest.json").write_text(
                json.dumps(data, indent=2) + "\n", encoding="utf-8"
            )
            digest = ShipDigest.model_validate(data)
            manifest = json.loads(
                (workdir / "pages_manifest.json").read_text(encoding="utf-8")
            )
            draft_svgs_from_digest(
                digest,
                manifest,
                str(workdir / "overlays"),
                allowed_roots=roots,
                suffix="approved",
            )
            out = tmp_path / out_name
            synthesize(
                workdir=str(workdir),
                output_dir=str(out),
                allowed_roots=roots,
                require_approved=True,
                copy_graphics=False,
            )
            spatial = json.loads((out / "spatial_layout.json").read_text(encoding="utf-8"))
            return sum(z["volume_m3"] for z in spatial["zones"])

        v_low = _run(2.0, "plat_low")
        v_high = _run(4.0, "plat_high")
        assert v_high > v_low * 1.5


def _mutated_platform(
    tmp_path: Path,
    roots: tuple[str, ...],
    name: str,
    mutate,
) -> tuple[dict, dict, Path]:
    """Seed the toy workdir, mutate its digest, synthesize, load output."""
    from tools.ship_blueprint_import.digest import draft_svgs_from_digest
    from tools.ship_blueprint_import.models import ShipDigest
    from tools.ship_blueprint_import.synthesize import synthesize

    workdir = tmp_path / f"wd_{name}"
    _seed_workdir(workdir)
    data = json.loads((workdir / "ship_digest.json").read_text(encoding="utf-8"))
    mutate(data)
    (workdir / "ship_digest.json").write_text(
        json.dumps(data, indent=2) + "\n", encoding="utf-8"
    )
    digest = ShipDigest.model_validate(data)
    manifest = json.loads(
        (workdir / "pages_manifest.json").read_text(encoding="utf-8")
    )
    draft_svgs_from_digest(
        digest,
        manifest,
        str(workdir / "overlays"),
        allowed_roots=roots,
        suffix="approved",
    )
    out = tmp_path / name
    synthesize(
        workdir=str(workdir),
        output_dir=str(out),
        platform_id=f"toy_{name}",
        allowed_roots=roots,
        require_approved=True,
        copy_graphics=False,
    )
    spatial = json.loads((out / "spatial_layout.json").read_text(encoding="utf-8"))
    airflow = json.loads((out / "air_flow_paths.json").read_text(encoding="utf-8"))
    return spatial, airflow, out


def _add_head(data: dict) -> None:
    data["zones"].append(
        {
            "id": "Head_Main",
            "type": "Sanitary",
            "deck": "main_deck",
            "page": 1,
            "traffic": "low",
            "serves": ["Mess_Hall", "Galley"],
            "polygon_norm": [
                [0.02, 0.02],
                [0.10, 0.02],
                [0.10, 0.16],
                [0.02, 0.16],
            ],
        }
    )


class TestSanitaryAndComplement:
    def test_sanitary_wiring_contract(
        self, tmp_path: Path, roots: tuple[str, ...]
    ) -> None:
        """Authored heads get the shared-head wiring the invariants test pins."""
        spatial, airflow, _ = _mutated_platform(
            tmp_path, roots, "heady", _add_head
        )
        head = next(z for z in spatial["zones"] if z["id"] == "Head_Main")
        assert head["type"] == "Sanitary"
        assert head["base_ach"] == pytest.approx(19.15, abs=0.1)
        assert head["ceiling_height_m"] == pytest.approx(2.3)
        assert head["volume_m3"] == pytest.approx(
            head["floor_area_m2"] * 2.3, rel=1e-3
        )
        assert head["max_occupancy"] == max(
            1, round(head["floor_area_m2"] / 2.7)
        )
        # Exhaust-only one-room branch per head.
        head_groups = [
            g for g in airflow["hvac_zones"] if g["id"] == "AHU_HD_Head_Main"
        ]
        assert len(head_groups) == 1
        group = head_groups[0]
        assert group["rooms"] == ["Head_Main"]
        assert group["ach"] == pytest.approx(19.15, abs=0.1)
        assert group["oa_fraction"] == 1.0
        assert group["hvac_duty"] == 0.0
        # The head sits in no other group and sources nothing.
        assert sum(
            "Head_Main" in g["rooms"] for g in airflow["hvac_zones"]
        ) == 1
        makeup = [
            link
            for link in airflow["cross_zone_links"]
            if link["to"] == "AHU_HD_Head_Main"
        ]
        assert len(makeup) == 1
        assert makeup[0]["path"] == "Sanitary_Makeup"
        assert makeup[0]["is_hvac_ducted"] is False
        assert makeup[0]["from"] == "zone_main"
        assert all(
            not link["from"].startswith("AHU_HD_")
            for link in airflow["cross_zone_links"]
        )
        # One-way rule: no adjacency edge touches the head.
        assert all(
            "Head_Main" not in (e["from"], e["to"])
            for e in airflow["adjacency"]
        )
        assert "Head_Main" not in spatial["graywater_zones"]

    def test_complement_declares_and_writes_manifest(
        self, tmp_path: Path, roots: tuple[str, ...]
    ) -> None:
        def _mut(data: dict) -> None:
            data["complement"] = {
                "passengers": 15,
                "crew": 20,
                "source": "toy manifest",
                "manifest": [
                    {
                        "class_id": "officers",
                        "role_group": "crew",
                        "count": 4,
                        "berth_zone": "Berthing",
                        "duty_zone": "Bridge",
                    },
                    {
                        "class_id": "deck_crew",
                        "role_group": "crew",
                        "count": 16,
                        "berth_zone": "Berthing",
                        "duty_zone": "Engine_Room",
                    },
                    {
                        "class_id": "scientists",
                        "role_group": "passenger",
                        "count": 15,
                        "berth_zone": "Mess_Hall",
                        "duty_zone": "Mess_Hall",
                    },
                ],
            }

        spatial, _, out = _mutated_platform(
            tmp_path, roots, "manned", _mut
        )
        assert spatial["nominal_complement"] == {
            "passengers": 15,
            "crew": 20,
        }
        manifest = json.loads(
            (out / "crew_manifest.json").read_text(encoding="utf-8")
        )
        assert manifest["consistency"] == {
            "declared_total": 35,
            "manifest_total": 35,
            "matches": True,
        }
        blocks = {b["class_id"]: b for b in manifest["manifest"]}
        assert blocks["officers"]["berth_zone"] == "Berthing"
        assert blocks["scientists"]["role_group"] == "passenger"

    def test_all_crew_complement_stays_manifest_only(
        self, tmp_path: Path, roots: tuple[str, ...]
    ) -> None:
        """An all-crew hull does not declare nominal_complement — the
        declaration is run-scored and refuses non-positive counts."""
        def _mut(data: dict) -> None:
            data["complement"] = {
                "passengers": 0,
                "crew": 99,
                "source": "wartime fit",
                "manifest": [
                    {
                        "class_id": "seamen",
                        "role_group": "crew",
                        "count": 99,
                        "berth_zone": "Berthing",
                        "duty_zone": "Bridge",
                    }
                ],
            }

        spatial, _, out = _mutated_platform(
            tmp_path, roots, "allcrew", _mut
        )
        assert "nominal_complement" not in spatial
        manifest = json.loads(
            (out / "crew_manifest.json").read_text(encoding="utf-8")
        )
        assert manifest["consistency"]["manifest_total"] == 99

    def test_plan_bbox_maps_display_into_span(
        self, tmp_path: Path, roots: tuple[str, ...]
    ) -> None:
        """A deck plan_bbox re-maps that deck's zones into the hull span.

        The box [0.35, 0.05, 0.70, 0.90] is declared to cover the hull
        band x∈[10,40] m, y∈[1,5] m — e.g. a superstructure block on a
        multi-view sheet. Zones inside it land proportionally inside the
        span; zones outside it map beyond the span (they lie off the
        drawn block), and other decks keep the legacy full-page map.
        """

        def _mut(data: dict) -> None:
            for deck in data["decks"]:
                if deck["id"] == "main_deck":
                    deck["plan_bbox_norm"] = [0.35, 0.05, 0.70, 0.90]
                    deck["hull_x_span_m"] = [10.0, 40.0]
                    deck["hull_y_span_m"] = [1.0, 5.0]

        spatial, _, _ = _mutated_platform(tmp_path, roots, "bbox", _mut)
        by_id = {z["id"]: z for z in spatial["zones"]}
        # SVG paths close with a duplicate first vertex, so the vertex-mean
        # centroids sit slightly left/below the rect centre: Mess_Hall's
        # effective norm centroid is (0.50, 0.37) -> rel (0.43, 0.38).
        mess = by_id["Mess_Hall"]["display"]
        assert mess["x"] == pytest.approx(22.9, abs=0.5)
        assert mess["y"] == pytest.approx(2.5, abs=0.3)
        # Galley sits inside the box in x (rel ~0.51).
        galley = by_id["Galley"]["display"]
        assert galley["x"] == pytest.approx(25.4, abs=0.5)
        # Bridge (effective centroid x ~0.80 > 0.70) lands beyond the
        # declared span — and nowhere near the legacy full-page ~80 m.
        bridge = by_id["Bridge"]["display"]
        assert 40.0 < bridge["x"] < 82.0
        # lower_deck has no bbox: Berthing keeps the legacy whole-page map.
        berth = by_id["Berthing"]["display"]
        assert berth["x"] == pytest.approx(20.0, abs=0.5)
        assert berth["y"] == pytest.approx(5.2, abs=0.3)


class TestProviders:
    def test_get_provider_names(self) -> None:
        from tools.ship_blueprint_import.providers import get_provider

        assert get_provider("mock").name == "mock"
        assert get_provider("gemini").name == "gemini"
        assert get_provider("openai_compat").name == "openai_compat"
        assert get_provider("anthropic").name == "anthropic"
        with pytest.raises(ValueError):
            get_provider("nope")

    def test_extract_json_object_fenced(self) -> None:
        from tools.ship_blueprint_import.providers import extract_json_object

        text = '```json\n{"platform_id": "x", "zones": []}\n```'
        # zones empty will fail ShipDigest later; extractor should still parse
        data = extract_json_object(text)
        assert data["platform_id"] == "x"

    def test_extract_json_object_embedded_and_nested(self) -> None:
        from tools.ship_blueprint_import.providers import extract_json_object

        text = 'prefix {"platform_id": "y", "meta": {"a": 1}} trailing'
        data = extract_json_object(text)
        assert data["platform_id"] == "y"
        assert data["meta"]["a"] == 1


class TestValidate:
    def test_validate_synthesized_platform(
        self, tmp_path: Path, roots: tuple[str, ...]
    ) -> None:
        from tools.ship_blueprint_import.digest import draft_svgs_from_digest
        from tools.ship_blueprint_import.models import ShipDigest
        from tools.ship_blueprint_import.synthesize import synthesize
        from tools.ship_blueprint_import.validate import validate_platform

        workdir = tmp_path / "wd"
        _seed_workdir(workdir)
        digest = ShipDigest.model_validate(
            json.loads((workdir / "ship_digest.json").read_text(encoding="utf-8"))
        )
        manifest = json.loads(
            (workdir / "pages_manifest.json").read_text(encoding="utf-8")
        )
        draft_svgs_from_digest(
            digest,
            manifest,
            str(workdir / "overlays"),
            allowed_roots=roots,
            suffix="approved",
        )
        # sanity_checker only reads paths under the repo root
        out = REPO_ROOT / "work" / "blueprints" / "_pytest_toy_destroyer"
        if out.exists():
            shutil.rmtree(out)
        try:
            synthesize(
                workdir=str(workdir),
                output_dir=str(out),
                allowed_roots=(str(REPO_ROOT), str(tmp_path)),
                require_approved=True,
            )
            result = validate_platform(
                str(out), allowed_roots=(str(REPO_ROOT),)
            )
            assert result["schema_errors"] == [], result["schema_errors"]
            assert result["sanity_ok"], result["sanity_report"]
            assert result["ok"]
        finally:
            if out.exists():
                shutil.rmtree(out)


class TestCliSmoke:
    def test_cli_help(self) -> None:
        from tools.ship_blueprint_import.cli import build_parser

        parser = build_parser()
        args = parser.parse_args(
            ["digest", "--workdir", "work/blueprints/x", "--provider", "mock"]
        )
        assert args.command == "digest"
        assert args.provider == "mock"

    def test_cli_author_contam_parser(self) -> None:
        from tools.ship_blueprint_import.cli import build_parser

        parser = build_parser()
        args = parser.parse_args(
            [
                "author_contam",
                "--platform-dir",
                "data/platforms/toy_destroyer",
                "--workdir",
                "work/blueprints/x",
            ]
        )
        assert args.command == "author_contam"
        assert args.platform_dir.endswith("toy_destroyer")


class TestAuthorContam:
    def _synth_platform(
        self, tmp_path: Path, roots: tuple[str, ...], name: str
    ) -> tuple[Path, Path]:
        from tools.ship_blueprint_import.digest import draft_svgs_from_digest
        from tools.ship_blueprint_import.models import ShipDigest
        from tools.ship_blueprint_import.synthesize import synthesize

        workdir = tmp_path / f"wd_{name}"
        _seed_workdir(workdir)
        digest = ShipDigest.model_validate(
            json.loads((workdir / "ship_digest.json").read_text(encoding="utf-8"))
        )
        manifest = json.loads(
            (workdir / "pages_manifest.json").read_text(encoding="utf-8")
        )
        draft_svgs_from_digest(
            digest,
            manifest,
            str(workdir / "overlays"),
            allowed_roots=roots,
            suffix="approved",
        )
        out = REPO_ROOT / "work" / "blueprints" / name
        if out.exists():
            shutil.rmtree(out)
        synthesize(
            workdir=str(workdir),
            output_dir=str(out),
            allowed_roots=(str(REPO_ROOT), str(tmp_path)),
            require_approved=True,
            copy_graphics=False,
        )
        return out, workdir

    def test_author_contam_emits_prj_and_openings(
        self, tmp_path: Path, roots: tuple[str, ...]
    ) -> None:
        from tools.ship_blueprint_import.author_contam import author_contam

        out, workdir = self._synth_platform(
            tmp_path, roots, "_pytest_contam_toy"
        )
        try:
            result = author_contam(
                platform_dir=str(out),
                workdir=str(workdir),
                allowed_roots=(str(REPO_ROOT), str(tmp_path)),
                hobbyist=True,
                run_offline_gate=True,
            )
            assert Path(result["prj_path"]).is_file()
            assert Path(result["path_map"]).is_file()
            openings = json.loads(
                Path(result["openings_draft"]).read_text(encoding="utf-8")
            )
            assert openings["openings"], "expected opening checklist entries"
            assert any(o["type"] for o in openings["openings"])
            # Opening hint area from toy digest should appear
            hatch = next(
                (
                    o
                    for o in openings["openings"]
                    if {o["from"], o["to"]} == {"Berthing", "Engine_Room"}
                ),
                None,
            )
            assert hatch is not None
            assert hatch["area_m2"] == pytest.approx(0.36, rel=0.01)
            handoff = Path(result["handoff"]).read_text(encoding="utf-8")
            assert "Target B" in handoff or "handwork" in handoff.lower()
            overrides = json.loads(
                (out / "contam" / "hobbyist_overrides.json").read_text(encoding="utf-8")
            )
            assert overrides.get("skip_duct_spines") is True
            assert overrides.get("duct_hvac_ids") == []
            gate = result["offline_gate"]
            assert gate, gate
            assert gate["ok"], gate
            assert gate["zone_count"] >= 6
            assert gate["path_map_entries"] >= 1
            # Zones gained Contam geometry
            spatial = json.loads((out / "spatial_layout.json").read_text(encoding="utf-8"))
            assert all("elevation_m" in z for z in spatial["zones"])
            assert all("floor_area_m2" in z for z in spatial["zones"])
            prj = Path(result["prj_path"]).read_text(encoding="utf-8")
            assert "plr_orfc" in prj or "orfc" in prj.lower()
        finally:
            if out.exists():
                shutil.rmtree(out)

    def test_skip_duct_spines_config_sensitivity(self) -> None:
        """Changing skip_duct_spines changes hobbyist override payload."""
        from tools.ship_blueprint_import.author_contam import (
            build_naval_hobbyist_overrides,
        )
        from tools.ship_blueprint_import.models import ContamHints, ShipDigest

        spatial = {
            "platform": "x",
            "deck_dimensions": {"length_m": 100, "beam_m": 12},
            "zones": [
                {"id": "Bridge", "type": "Free", "deck": "main", "display": {"x": 80, "y": 6}},
                {"id": "Berthing", "type": "Room", "deck": "lower", "display": {"x": 20, "y": 6}},
            ],
        }
        airflow = {"hvac_zones": [{"id": "zone_main", "rooms": ["Bridge", "Berthing"], "ach": 6}]}
        base = ShipDigest.model_validate(
            {
                "platform_id": "x",
                "zones": [
                    {
                        "id": "Bridge",
                        "type": "Free",
                        "deck": "main",
                        "page": 1,
                        "polygon_norm": [[0, 0], [1, 0], [1, 1]],
                    },
                    {
                        "id": "Berthing",
                        "type": "Room",
                        "deck": "lower",
                        "page": 1,
                        "polygon_norm": [[0, 0], [1, 0], [1, 1]],
                    },
                ],
                "contam_hints": {"skip_duct_spines": True, "duct_hvac_ids": ["zone_main"]},
            }
        )
        o_skip = build_naval_hobbyist_overrides(
            platform_id="x", spatial=spatial, airflow=airflow, digest=base
        )
        base.contam_hints = ContamHints(skip_duct_spines=False, duct_hvac_ids=["zone_main"])
        o_ducts = build_naval_hobbyist_overrides(
            platform_id="x", spatial=spatial, airflow=airflow, digest=base
        )
        assert o_skip["skip_duct_spines"] is True
        assert o_skip["duct_hvac_ids"] == []
        assert o_ducts["skip_duct_spines"] is False
        assert o_ducts["duct_hvac_ids"] == ["zone_main"]


def _add_systems(data: dict, **overrides) -> None:
    data["systems"] = {
        "era": "usn_ww2",
        "vent_markers": [
            {
                "id": "Cowl_Mess",
                "page": 1,
                "position_norm": [0.4, 0.4],
                "deck": "main_deck",
                "kind": "cowl",
                "facing": "fore",
                "serves_zone": "Mess_Hall",
                "evidence": "sheet_read",
            },
            {
                "id": "Funnel",
                "page": 1,
                "position_norm": [0.6, 0.6],
                "deck": "lower_deck",
                "kind": "funnel",
                "facing": "up",
                "serves_zone": "Engine_Room",
                "evidence": "sheet_read",
            },
        ],
        "tanks": [],
    }
    data["systems"].update(overrides)


class TestSystemsInference:
    def test_era_modes_enrich_groups_and_write_notes(
        self, tmp_path: Path, roots: tuple[str, ...]
    ) -> None:
        spatial, airflow, out = _mutated_platform(
            tmp_path, roots, "sys", _add_systems
        )
        groups = {g["id"]: g for g in airflow["hvac_zones"]}
        # Marker modes beat era rules on a mixed branch: Mess_Hall's sheet-read
        # supply cowl gives zone_main nat_supply; Engine_Room's sheet-read
        # funnel keeps the machinery space mechanical (mech_supply_exhaust).
        assert groups["zone_main"]["vent_mode"] == "nat_supply"
        assert groups["zone_main"]["evidence"] == "sheet_read"
        assert groups["zone_lower"]["vent_mode"] == "mech_supply_exhaust"
        assert groups["zone_lower"]["evidence"] == "sheet_read"
        # Hints declare no oa_fraction → era mode prior applies.
        assert groups["zone_main"]["oa_fraction"] == 1.0
        assert groups["zone_lower"]["oa_fraction"] == 0.4
        # Notes artifacts exist with evidence grades.
        notes = json.loads((out / "systems_notes.json").read_text())
        assert notes["era"] == "usn_ww2"
        marker_dirs = {m["id"]: m["direction"] for m in notes["vent_markers"]}
        assert marker_dirs == {"Cowl_Mess": "supply", "Funnel": "exhaust"}
        # Zone modes refine marker kind: the funnel keeps Engineering mechanical.
        assert notes["zone_modes"]["Engine_Room"]["mode"] == "mech_supply_exhaust"
        assert (out / "systems_notes.md").is_file()
        # Zone modes separate sheet reads from era rules.
        assert notes["zone_modes"]["Mess_Hall"]["evidence"] == "sheet_read"
        assert notes["zone_modes"]["MedBay"]["evidence"] == "era_rule"

    def test_declared_hint_oa_wins_over_era(
        self, tmp_path: Path, roots: tuple[str, ...]
    ) -> None:
        def _mut(data: dict) -> None:
            _add_systems(data)
            data["hvac_hints"][1]["oa_fraction"] = 0.9

        _, airflow, _ = _mutated_platform(tmp_path, roots, "sysoa", _mut)
        groups = {g["id"]: g for g in airflow["hvac_zones"]}
        assert groups["zone_main"]["oa_fraction"] == 0.9
        assert groups["zone_upper"]["oa_fraction"] == 1.0  # Bridge Free→nat_supply

    def test_sewage_tank_joins_graywater(
        self, tmp_path: Path, roots: tuple[str, ...]
    ) -> None:
        def _mut(data: dict) -> None:
            _add_systems(
                data,
                tanks=[
                    {
                        "label": "SEWAGE HOLDING",
                        "page": 1,
                        "position_norm": [0.6, 0.6],
                        "deck": "lower_deck",
                    }
                ],
            )

        spatial, _, out = _mutated_platform(tmp_path, roots, "syspl", _mut)
        notes = json.loads((out / "systems_notes.json").read_text())
        assert notes["tanks"][0]["kind"] == "sewage"
        added = notes["tanks"][0]["nearest_zone"]
        assert added in spatial["graywater_zones"]
        assert notes["plumbing_drains"]

    def test_hangar_door_is_natural_opening(
        self, tmp_path: Path, roots: tuple[str, ...]
    ) -> None:
        """Carrier hangar-side roller doors read as natural ventilation."""

        def _mut(data: dict) -> None:
            _add_systems(
                data,
                vent_markers=[
                    {
                        "id": "Hangar_Door_P",
                        "page": 1,
                        "position_norm": [0.4, 0.4],
                        "deck": "main_deck",
                        "kind": "hangar_door",
                        "facing": "unknown",
                        "serves_zone": "Mess_Hall",
                        "evidence": "sheet_read",
                    }
                ],
            )

        _, airflow, out = _mutated_platform(tmp_path, roots, "syshd", _mut)
        groups = {g["id"]: g for g in airflow["hvac_zones"]}
        assert groups["zone_main"]["vent_mode"] == "nat_supply"
        assert groups["zone_main"]["evidence"] == "sheet_read"
        notes = json.loads((out / "systems_notes.json").read_text())
        assert notes["vent_markers"][0]["direction"] == "supply"

    def test_no_systems_no_notes(
        self, tmp_path: Path, roots: tuple[str, ...]
    ) -> None:
        _, airflow, out = _mutated_platform(
            tmp_path, roots, "sysnone", lambda d: None
        )
        assert not (out / "systems_notes.json").exists()
        assert all(
            "vent_mode" not in g for g in airflow["hvac_zones"]
        )
