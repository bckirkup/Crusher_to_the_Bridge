"""SVG overlay read/write for GIMP / Krita / Inkscape round-trips.

Convention: each zone is a closed ``<path id="ZoneId" …>`` (or ``<polygon>``)
in the same pixel coordinate space as the corresponding page PNG.
"""

from __future__ import annotations

import math
import re
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from typing import Iterable

_SVG_NS = "http://www.w3.org/2000/svg"
_NS = {"svg": _SVG_NS}
_PATH_CMD = re.compile(
    r"([MmLlHhVvCcSsQqTtAaZz])|([+-]?(?:\d+\.?\d*|\.\d+)(?:[eE][+-]?\d+)?)"
)


@dataclass(frozen=True)
class OverlayPolygon:
    zone_id: str
    points: list[tuple[float, float]]  # pixel coords
    page: int | None = None

    def centroid(self) -> tuple[float, float]:
        if not self.points:
            return (0.0, 0.0)
        xs = [p[0] for p in self.points]
        ys = [p[1] for p in self.points]
        return (sum(xs) / len(xs), sum(ys) / len(ys))

    def area_px(self) -> float:
        return abs(shoelace_area(self.points))


def shoelace_area(points: Iterable[tuple[float, float]]) -> float:
    pts = list(points)
    if len(pts) < 3:
        return 0.0
    if pts[0] != pts[-1]:
        pts = pts + [pts[0]]
    area = 0.0
    for i in range(len(pts) - 1):
        x1, y1 = pts[i]
        x2, y2 = pts[i + 1]
        area += x1 * y2 - x2 * y1
    return area / 2.0


def _local_tag(tag: str) -> str:
    if "}" in tag:
        return tag.rsplit("}", 1)[-1]
    return tag


def _parse_path_d(d: str) -> list[tuple[float, float]]:
    """Parse a subset of SVG path data into absolute polyline points."""
    tokens: list[str] = []
    for match in _PATH_CMD.finditer(d.replace(",", " ")):
        tokens.append(match.group(0))

    points: list[tuple[float, float]] = []
    cmd = "M"
    i = 0
    cx, cy = 0.0, 0.0
    start = (0.0, 0.0)

    def _num() -> float:
        nonlocal i
        if i >= len(tokens):
            raise ValueError("unexpected end of path data")
        val = float(tokens[i])
        i += 1
        return val

    while i < len(tokens):
        tok = tokens[i]
        if re.fullmatch(r"[MmLlHhVvCcSsQqTtAaZz]", tok):
            cmd = tok
            i += 1
            if cmd in ("Z", "z"):
                if points and points[-1] != start:
                    points.append(start)
                continue
        else:
            # Implicit repetition of previous command
            if cmd in ("M", "m"):
                cmd = "L" if cmd == "M" else "l"
            elif cmd in ("Z", "z"):
                raise ValueError(f"unexpected number after close-path: {tok}")

        if cmd == "M":
            cx, cy = _num(), _num()
            start = (cx, cy)
            points.append((cx, cy))
            cmd = "L"
        elif cmd == "m":
            cx, cy = cx + _num(), cy + _num()
            start = (cx, cy)
            points.append((cx, cy))
            cmd = "l"
        elif cmd == "L":
            cx, cy = _num(), _num()
            points.append((cx, cy))
        elif cmd == "l":
            cx, cy = cx + _num(), cy + _num()
            points.append((cx, cy))
        elif cmd == "H":
            cx = _num()
            points.append((cx, cy))
        elif cmd == "h":
            cx += _num()
            points.append((cx, cy))
        elif cmd == "V":
            cy = _num()
            points.append((cx, cy))
        elif cmd == "v":
            cy += _num()
            points.append((cx, cy))
        elif cmd in ("C", "c"):
            # Cubic: take end point only for coarse zone polygons
            for _ in range(4):
                _num()
            if cmd == "C":
                cx, cy = _num(), _num()
            else:
                cx, cy = cx + _num(), cy + _num()
            points.append((cx, cy))
        elif cmd in ("Q", "q"):
            for _ in range(2):
                _num()
            if cmd == "Q":
                cx, cy = _num(), _num()
            else:
                cx, cy = cx + _num(), cy + _num()
            points.append((cx, cy))
        elif cmd in ("S", "s", "T", "t"):
            if cmd in ("S", "s"):
                for _ in range(2):
                    _num()
            if cmd in ("S", "T"):
                cx, cy = _num(), _num()
            else:
                cx, cy = cx + _num(), cy + _num()
            points.append((cx, cy))
        elif cmd in ("A", "a"):
            for _ in range(5):
                _num()
            if cmd == "A":
                cx, cy = _num(), _num()
            else:
                cx, cy = cx + _num(), cy + _num()
            points.append((cx, cy))
        else:
            raise ValueError(f"unsupported SVG path command: {cmd}")

    return points


def _polygon_points_from_elem(elem: ET.Element) -> list[tuple[float, float]]:
    tag = _local_tag(elem.tag)
    if tag == "path":
        d = elem.attrib.get("d", "").strip()
        if not d:
            raise ValueError("path element missing d attribute")
        return _parse_path_d(d)
    if tag == "polygon":
        raw = elem.attrib.get("points", "").strip()
        if not raw:
            raise ValueError("polygon element missing points attribute")
        nums = [float(x) for x in re.split(r"[\s,]+", raw) if x]
        if len(nums) % 2 != 0 or len(nums) < 6:
            raise ValueError("polygon needs at least 3 coordinate pairs")
        return [(nums[i], nums[i + 1]) for i in range(0, len(nums), 2)]
    if tag == "rect":
        x = float(elem.attrib.get("x", 0))
        y = float(elem.attrib.get("y", 0))
        w = float(elem.attrib.get("width", 0))
        h = float(elem.attrib.get("height", 0))
        return [(x, y), (x + w, y), (x + w, y + h), (x, y + h), (x, y)]
    raise ValueError(f"unsupported SVG shape: {tag}")


def _shape_id(elem: ET.Element) -> str | None:
    for key in ("id", "inkscape:label", "{http://www.inkscape.org/namespaces/inkscape}label"):
        val = elem.attrib.get(key)
        if val and val.strip():
            return val.strip().replace(" ", "_")
    # GIMP path names sometimes land in <title>
    for child in elem:
        if _local_tag(child.tag) == "title" and (child.text or "").strip():
            return child.text.strip().replace(" ", "_")
    return None


def read_overlay_svg(svg_text: str, *, page: int | None = None) -> list[OverlayPolygon]:
    """Parse named zone polygons from an SVG document."""
    root = ET.fromstring(svg_text)
    polygons: list[OverlayPolygon] = []
    unnamed = 0
    for elem in root.iter():
        tag = _local_tag(elem.tag)
        if tag not in ("path", "polygon", "rect"):
            continue
        # Skip empty/group decorative paths without geometry attrs
        if tag == "path" and not elem.attrib.get("d"):
            continue
        zone_id = _shape_id(elem)
        if not zone_id:
            unnamed += 1
            continue
        if zone_id.startswith("_"):
            # Reserved decorative elements (e.g. _page_bounds)
            continue
        try:
            pts = _polygon_points_from_elem(elem)
        except ValueError:
            continue
        if len(pts) < 3:
            continue
        polygons.append(OverlayPolygon(zone_id=zone_id, points=pts, page=page))
    if unnamed:
        raise ValueError(
            f"SVG contains {unnamed} unnamed path/polygon/rect element(s); "
            "every zone shape must have an id (or inkscape:label / title) "
            "matching the ShipDigest zone id"
        )
    if not polygons:
        raise ValueError("SVG contains no named zone shapes")
    return polygons


def write_overlay_svg(
    polygons: list[OverlayPolygon],
    *,
    width: int,
    height: int,
    title: str = "Crusher naval blueprint overlay",
) -> str:
    """Serialize zone polygons to an SVG string in pixel coordinates."""
    root = ET.Element(
        "svg",
        {
            "xmlns": _SVG_NS,
            "width": str(width),
            "height": str(height),
            "viewBox": f"0 0 {width} {height}",
        },
    )
    title_el = ET.SubElement(root, "title")
    title_el.text = title
    desc = ET.SubElement(root, "desc")
    desc.text = (
        "Named paths are Crusher simulation zones. Edit in GIMP/Krita/Inkscape; "
        "keep path ids equal to zone ids. Export as page_NN_approved.svg."
    )
    # Transparent underlay hint rectangle
    ET.SubElement(
        root,
        "rect",
        {
            "id": "_page_bounds",
            "x": "0",
            "y": "0",
            "width": str(width),
            "height": str(height),
            "fill": "none",
            "stroke": "#888888",
            "stroke-width": "1",
            "stroke-dasharray": "4 4",
        },
    )
    colors = ["#e41a1c", "#377eb8", "#4daf4a", "#984ea3", "#ff7f00", "#a65628"]
    for idx, poly in enumerate(polygons):
        if poly.zone_id.startswith("_"):
            continue
        pts = list(poly.points)
        if len(pts) < 3:
            continue
        if pts[0] != pts[-1]:
            pts = pts + [pts[0]]
        d = "M " + " L ".join(f"{x:.2f} {y:.2f}" for x, y in pts) + " Z"
        color = colors[idx % len(colors)]
        ET.SubElement(
            root,
            "path",
            {
                "id": poly.zone_id,
                "d": d,
                "fill": color,
                "fill-opacity": "0.25",
                "stroke": color,
                "stroke-width": "2",
            },
        )
    return ET.tostring(root, encoding="unicode")


def norm_to_pixel(
    polygon_norm: list[list[float]],
    width: int,
    height: int,
) -> list[tuple[float, float]]:
    return [(float(x) * width, float(y) * height) for x, y in polygon_norm]


def pixel_to_norm(
    points: list[tuple[float, float]],
    width: int,
    height: int,
) -> list[list[float]]:
    w = max(width, 1)
    h = max(height, 1)
    return [[p[0] / w, p[1] / h] for p in points]


def polygons_touch(
    a: list[tuple[float, float]],
    b: list[tuple[float, float]],
    *,
    gap_px: float = 8.0,
) -> bool:
    """Cheap proximity test via expanded axis-aligned bounding boxes."""
    if len(a) < 2 or len(b) < 2:
        return False

    def _bbox(pts: list[tuple[float, float]]) -> tuple[float, float, float, float]:
        xs = [p[0] for p in pts]
        ys = [p[1] for p in pts]
        return min(xs), min(ys), max(xs), max(ys)

    ax0, ay0, ax1, ay1 = _bbox(a)
    bx0, by0, bx1, by1 = _bbox(b)
    return not (
        ax1 + gap_px < bx0
        or bx1 + gap_px < ax0
        or ay1 + gap_px < by0
        or by1 + gap_px < ay0
    )


def polygon_looks_closed(points: list[tuple[float, float]], *, tol: float = 1.0) -> bool:
    if len(points) < 3:
        return False
    return math.hypot(points[0][0] - points[-1][0], points[0][1] - points[-1][1]) <= tol
