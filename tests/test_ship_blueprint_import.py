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


@pytest.fixture()
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
