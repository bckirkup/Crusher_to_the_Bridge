"""Stage 1: rasterize PDF / image folders into workdir pages."""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
from datetime import datetime, timezone
from typing import Any

from simulation_utils.paths import (
    prepare_output_directory,
    resolve_child_path,
    validated_open,
)

IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".tif", ".tiff", ".webp", ".bmp"}


def _file_sha256(path: str, *, allowed_roots: tuple[str, ...]) -> str:
    h = hashlib.sha256()
    with validated_open(path, "rb", allowed_roots=allowed_roots) as fh:
        while True:
            chunk = fh.read(1024 * 1024)
            if not chunk:
                break
            h.update(chunk)
    return h.hexdigest()


def _write_json(path: str, payload: dict[str, Any], *, allowed_roots: tuple[str, ...]) -> None:
    parent = os.path.dirname(path)
    prepare_output_directory(parent, allowed_roots=allowed_roots)
    with validated_open(path, "w", allowed_roots=allowed_roots, encoding="utf-8") as fh:
        json.dump(payload, fh, indent=2, ensure_ascii=False)
        fh.write("\n")


def _copy_source(src: str, dest_dir: str, *, allowed_roots: tuple[str, ...]) -> str:
    prepare_output_directory(dest_dir, allowed_roots=allowed_roots)
    base = os.path.basename(src)
    dest = resolve_child_path(dest_dir, base)
    shutil.copy2(src, dest)
    return dest


def _rasterize_pdf_pypdfium2(
    pdf_path: str,
    pages_dir: str,
    *,
    dpi: float,
    allowed_roots: tuple[str, ...],
) -> list[dict[str, Any]]:
    import pypdfium2 as pdfium  # type: ignore[import-untyped]

    scale = dpi / 72.0
    doc = pdfium.PdfDocument(pdf_path)
    pages: list[dict[str, Any]] = []
    prepare_output_directory(pages_dir, allowed_roots=allowed_roots)
    for i in range(len(doc)):
        page = doc[i]
        bitmap = page.render(scale=scale)
        pil = bitmap.to_pil()
        name = f"page_{i + 1:02d}.png"
        out = resolve_child_path(pages_dir, name)
        pil.save(out)
        pages.append(
            {
                "page": i + 1,
                "file": f"pages/{name}",
                "width": int(pil.size[0]),
                "height": int(pil.size[1]),
                "dpi": dpi,
            }
        )
    return pages


def _rasterize_pdf_pdftoppm(
    pdf_path: str,
    pages_dir: str,
    *,
    dpi: float,
    allowed_roots: tuple[str, ...],
) -> list[dict[str, Any]]:
    prepare_output_directory(pages_dir, allowed_roots=allowed_roots)
    prefix = os.path.join(pages_dir, "page")
    cmd = [
        "pdftoppm",
        "-png",
        "-r",
        str(int(dpi)),
        pdf_path,
        prefix,
    ]
    subprocess.run(cmd, check=True, capture_output=True)
    from PIL import Image

    pages: list[dict[str, Any]] = []
    # pdftoppm emits page-1.png, page-01.png, or page-001.png depending on count
    produced = sorted(
        f for f in os.listdir(pages_dir) if f.startswith("page") and f.endswith(".png")
    )
    for idx, fname in enumerate(produced, start=1):
        src = resolve_child_path(pages_dir, fname)
        dest_name = f"page_{idx:02d}.png"
        dest = resolve_child_path(pages_dir, dest_name)
        if src != dest:
            if os.path.exists(dest):
                os.remove(dest)
            os.rename(src, dest)
        with Image.open(dest) as im:
            w, h = im.size
        pages.append(
            {
                "page": idx,
                "file": f"pages/{dest_name}",
                "width": int(w),
                "height": int(h),
                "dpi": dpi,
            }
        )
    if not pages:
        raise RuntimeError("pdftoppm produced no page images")
    return pages


def rasterize_pdf(
    pdf_path: str,
    pages_dir: str,
    *,
    dpi: float = 150.0,
    allowed_roots: tuple[str, ...],
) -> list[dict[str, Any]]:
    try:
        return _rasterize_pdf_pypdfium2(
            pdf_path, pages_dir, dpi=dpi, allowed_roots=allowed_roots
        )
    except ImportError:
        # Fall back to the pdftoppm executable when the optional library is absent.
        pass
    if shutil.which("pdftoppm"):
        return _rasterize_pdf_pdftoppm(
            pdf_path, pages_dir, dpi=dpi, allowed_roots=allowed_roots
        )
    raise RuntimeError(
        "PDF rasterization requires pypdfium2 (pip install pypdfium2) "
        "or the pdftoppm binary (poppler-utils)"
    )


def ingest_images(
    image_paths: list[str],
    pages_dir: str,
    *,
    dpi: float,
    allowed_roots: tuple[str, ...],
) -> list[dict[str, Any]]:
    from PIL import Image

    prepare_output_directory(pages_dir, allowed_roots=allowed_roots)
    pages: list[dict[str, Any]] = []
    for idx, src in enumerate(sorted(image_paths), start=1):
        name = f"page_{idx:02d}.png"
        dest = resolve_child_path(pages_dir, name)
        with Image.open(src) as im:
            rgb = im.convert("RGB")
            rgb.save(dest)
            w, h = rgb.size
        pages.append(
            {
                "page": idx,
                "file": f"pages/{name}",
                "width": int(w),
                "height": int(h),
                "dpi": dpi,
                "source_image": os.path.basename(src),
            }
        )
    return pages


def collect_input_images(input_path: str) -> tuple[str, list[str]]:
    """Return ('pdf'|'images', list of absolute paths)."""
    if os.path.isfile(input_path):
        ext = os.path.splitext(input_path)[1].lower()
        if ext == ".pdf":
            return "pdf", [input_path]
        if ext in IMAGE_EXTS:
            return "images", [input_path]
        raise ValueError(f"unsupported input file type: {ext}")
    if os.path.isdir(input_path):
        images = [
            os.path.join(input_path, name)
            for name in sorted(os.listdir(input_path))
            if os.path.splitext(name)[1].lower() in IMAGE_EXTS
        ]
        if not images:
            raise ValueError(f"no images found in directory: {input_path}")
        return "images", images
    raise FileNotFoundError(f"input not found: {input_path}")


def ingest(
    *,
    input_path: str,
    workdir: str,
    dpi: float = 150.0,
    allowed_roots: tuple[str, ...],
) -> dict[str, Any]:
    """Rasterize blueprint sources into ``workdir/pages`` + manifest."""
    kind, sources = collect_input_images(input_path)
    prepare_output_directory(workdir, allowed_roots=allowed_roots)
    source_dir = os.path.join(workdir, "source")
    pages_dir = os.path.join(workdir, "pages")
    overlays_dir = os.path.join(workdir, "overlays")
    prepare_output_directory(source_dir, allowed_roots=allowed_roots)
    prepare_output_directory(pages_dir, allowed_roots=allowed_roots)
    prepare_output_directory(overlays_dir, allowed_roots=allowed_roots)

    copied: list[str] = []
    source_hashes: dict[str, str] = {}
    for src in sources:
        dest = _copy_source(src, source_dir, allowed_roots=allowed_roots)
        copied.append(os.path.relpath(dest, workdir))
        source_hashes[os.path.basename(src)] = _file_sha256(
            dest, allowed_roots=allowed_roots
        )

    if kind == "pdf":
        pdf_local = os.path.join(source_dir, os.path.basename(sources[0]))
        pages = rasterize_pdf(
            pdf_local, pages_dir, dpi=dpi, allowed_roots=allowed_roots
        )
    else:
        local_images = [
            os.path.join(source_dir, os.path.basename(s)) for s in sources
        ]
        pages = ingest_images(
            local_images, pages_dir, dpi=dpi, allowed_roots=allowed_roots
        )

    manifest: dict[str, Any] = {
        "schema_version": "1.0",
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "input_kind": kind,
        "dpi": dpi,
        "sources": copied,
        "source_sha256": source_hashes,
        "pages": pages,
    }
    manifest_path = resolve_child_path(workdir, "pages_manifest.json")
    _write_json(manifest_path, manifest, allowed_roots=allowed_roots)
    return manifest
