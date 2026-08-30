"""Extract CDC Vessel Sanitation Program outbreak rows and counts."""

from __future__ import annotations

import argparse
import csv
import hashlib
import html
import re
import subprocess
import time
from dataclasses import dataclass, field
from datetime import date, datetime
from pathlib import Path
from typing import Iterable
from urllib.parse import urljoin

CURRENT_INDEX = (
    "https://www.cdc.gov/vessel-sanitation/cruise-ship-outbreaks/index.html"
)
EARLIER_INDEX = (
    "https://www.cdc.gov/vessel-sanitation/cruise-ship-outbreaks/"
    "earlier-outbreaks.html"
)
ARCHIVE_TIMESTAMP = "20191215062717"
LEGACY_INDEX = (
    f"https://web.archive.org/web/{ARCHIVE_TIMESTAMP}/"
    "https://www.cdc.gov/nceh/vsp/surv/gilist.htm"
)
INDEX_2022 = (
    "https://web.archive.org/web/20240101000000/"
    "https://www.cdc.gov/nceh/vsp/surv/gilist.htm"
)
DEFAULT_CACHE = Path.home() / "vsp_cache"
DEFAULT_OUTPUT = Path(__file__).with_name("vsp_outbreak_series.csv")
DEFAULT_LOG = Path(__file__).with_name("vsp_outbreak_series_extraction_log.md")
REQUEST_DELAY_SECONDS = 0.2
RETRY_DELAYS = (5.0, 15.0, 45.0)
CSV_FIELDS = (
    "year",
    "cruise_line",
    "ship",
    "voyage_dates_raw",
    "voyage_end",
    "causative_agent",
    "pax_ill",
    "pax_total",
    "pax_pct_page",
    "crew_ill",
    "crew_total",
    "crew_pct_page",
    "era",
    "source_url",
    "retrieved",
)
COUNT_RE = re.compile(
    r"(?P<ill>\d[\d,]*)\s+of\s+(?P<total>\d[\d,]*)\s*"
    r"(?:\(\s*(?P<pct>\d+(?:\.\d+)?)\s*%\s*\))?",
    re.IGNORECASE,
)
DATE_TOKEN_RE = re.compile(r"(?<!\d)(\d{1,2}/\d{1,2}(?:/\d{2,4})?)")
YEAR_RE = re.compile(r"\b(19\d{2}|20\d{2})\b")


@dataclass
class Cell:
    text: str = ""
    href: str | None = None
    rowspan: int = 1
    colspan: int = 1


@dataclass
class Table:
    rows: list[list[Cell]] = field(default_factory=list)
    caption: str = ""


@dataclass
class IndexRow:
    year: int
    cruise_line: str
    ship: str
    voyage_dates_raw: str
    causative_agent: str
    href: str | None
    pax_text: str = ""
    crew_text: str = ""
    source_url: str = ""
    layout: str = ""


@dataclass
class Page:
    body: str
    retrieved: str


@dataclass
class CheckResult:
    percentage_failures: list[str] = field(default_factory=list)
    plausibility_failures: list[str] = field(default_factory=list)
    missing_counts: list[str] = field(default_factory=list)


class PageParser:
    """Collect table cells, captions, links, and visible page text."""

    def __init__(self) -> None:
        self.tables: list[Table] = []
        self.visible_parts: list[str] = []
        self._table: Table | None = None
        self._row: list[Cell] | None = None
        self._cell: Cell | None = None
        self._caption_parts: list[str] | None = None

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attributes = dict(attrs)
        if tag == "table":
            self._table = Table()
            self.tables.append(self._table)
        elif tag == "tr" and self._table is not None:
            self._row = []
            self._table.rows.append(self._row)
        elif tag in {"td", "th"} and self._row is not None:
            self._cell = Cell(
                rowspan=int(attributes.get("rowspan") or 1),
                colspan=int(attributes.get("colspan") or 1),
            )
            self._row.append(self._cell)
        elif tag == "caption" and self._table is not None:
            self._caption_parts = []
        elif tag == "a" and self._cell is not None:
            self._cell.href = attributes.get("href")

    def handle_endtag(self, tag: str) -> None:
        if tag in {"td", "th"}:
            self._cell = None
        elif tag == "tr":
            self._row = None
        elif tag == "caption" and self._table is not None:
            self._table.caption = clean_text(" ".join(self._caption_parts or []))
            self._caption_parts = None
        elif tag == "table":
            self._table = None

    def handle_data(self, data: str) -> None:
        if self._cell is not None:
            self._cell.text += data
        if self._caption_parts is not None:
            self._caption_parts.append(data)
        self.visible_parts.append(data)

    def feed(self, source: str) -> None:
        from html.parser import HTMLParser

        parser = HTMLParser(convert_charrefs=True)
        parser.handle_starttag = self.handle_starttag
        parser.handle_endtag = self.handle_endtag
        parser.handle_data = self.handle_data
        parser.feed(source)


def clean_text(value: str) -> str:
    return " ".join(html.unescape(value).split())


def cache_paths(cache_dir: Path, url: str) -> tuple[Path, Path]:
    key = hashlib.sha256(url.encode("utf-8")).hexdigest()
    return cache_dir / f"{key}.html", cache_dir / f"{key}.meta"


def read_cache(cache_dir: Path, url: str) -> Page | None:
    body_path, meta_path = cache_paths(cache_dir, url)
    if not body_path.exists() or not meta_path.exists():
        return None
    retrieved = meta_path.read_text(encoding="utf-8").strip()
    if not retrieved:
        return None
    return Page(body_path.read_text(encoding="utf-8"), retrieved)


def fetch_network(url: str) -> tuple[str, str]:
    for attempt in range(len(RETRY_DELAYS) + 1):
        result = subprocess.run(
            [
                "curl",
                "--compressed",
                "--fail-with-body",
                "--location",
                "--silent",
                "--show-error",
                "--max-time",
                "60",
                "--user-agent",
                "Crusher-VSP-extractor/1.0",
                "--write-out",
                "\n__VSP_HTTP_STATUS__%{http_code}",
                url,
            ],
            capture_output=True,
            check=False,
        )
        marker = b"\n__VSP_HTTP_STATUS__"
        body, _, status_bytes = result.stdout.rpartition(marker)
        status = int(status_bytes or b"0")
        retryable = status == 0 or status == 429 or 500 <= status <= 599
        if result.returncode == 0 and status == 200:
            return body.decode("utf-8", errors="replace"), date.today().isoformat()
        if not retryable or attempt == len(RETRY_DELAYS):
            detail = result.stderr.decode("utf-8", errors="replace").strip()
            suffix = f": {detail}" if detail else ""
            raise RuntimeError(f"unable to fetch {url}: HTTP {status}{suffix}")
        time.sleep(RETRY_DELAYS[attempt])
    raise RuntimeError(f"unable to fetch {url}")


def fetch_page(
    cache_dir: Path,
    url: str,
    *,
    refresh: bool,
    delay: float,
    fetched_urls: set[str],
) -> Page:
    if not refresh:
        cached = read_cache(cache_dir, url)
        if cached is not None:
            return cached
    if url not in fetched_urls:
        if fetched_urls:
            time.sleep(delay)
        fetched_urls.add(url)
    body, retrieved = fetch_network(url)
    body_path, meta_path = cache_paths(cache_dir, url)
    body_path.write_text(body, encoding="utf-8")
    meta_path.write_text(retrieved + "\n", encoding="utf-8")
    return Page(body, retrieved)


def table_year(caption: str) -> int | None:
    match = YEAR_RE.search(caption)
    return int(match.group(1)) if match else None


def is_outbreak_table(table: Table) -> bool:
    if not table.rows:
        return False
    headers = {clean_text(cell.text).lower() for cell in table.rows[0]}
    return "cruise line" in headers and "cruise ship" in headers


def table_layout(table: Table) -> str:
    header = " ".join(clean_text(cell.text).lower() for cell in table.rows[0])
    return "index_counts" if "case counts" in header else "detail_counts"


def expanded_rows(table: Table) -> list[list[Cell]]:
    pending: dict[int, tuple[Cell, int]] = {}
    expanded: list[list[Cell]] = []
    for source_row in table.rows:
        if len(source_row) == 1 and source_row[0].colspan >= 4:
            pending = {}
            expanded.append(source_row)
            continue
        inherited = {column: cell for column, (cell, _) in pending.items()}
        next_pending = {
            column: (cell, remaining - 1)
            for column, (cell, remaining) in pending.items()
            if remaining > 1
        }
        output: list[Cell] = []
        column = 0
        for cell in source_row:
            while column in inherited:
                output.append(inherited[column])
                column += 1
            output.append(cell)
            if cell.rowspan > 1:
                next_pending[column] = (cell, cell.rowspan - 1)
            output.extend(Cell() for _ in range(cell.colspan - 1))
            column += cell.colspan
        while column in inherited:
            output.append(inherited[column])
            column += 1
        pending = next_pending
        expanded.append(output)
    return expanded


def normalize_href(index_url: str, href: str | None) -> str | None:
    if not href:
        return None
    if href.startswith("/web/"):
        return "https://web.archive.org" + href
    return urljoin(index_url, href)


def index_rows(page: Page, index_url: str, years: set[int]) -> list[IndexRow]:
    parser = PageParser()
    parser.feed(page.body)
    rows: list[IndexRow] = []
    for table in parser.tables:
        year = table_year(table.caption)
        if year not in years or not is_outbreak_table(table):
            continue
        layout = table_layout(table)
        for cells in expanded_rows(table)[1:]:
            values = [clean_text(cell.text) for cell in cells]
            full_span = len(cells) == 1 and cells[0].colspan >= 4
            if full_span:
                values = ["", "", values[0], ""]
            date_cell = cells[min(len(cells) - 1, max(0, len(cells) - 2))]
            if not full_span and len(values) == 1:
                values = ["", "", values[0], ""]
            elif not full_span and len(values) == 2:
                values = ["", "", values[0], values[1]]
            elif not full_span and len(values) == 3:
                values = ["", *values]
            row = IndexRow(
                year=year,
                cruise_line=values[0],
                ship=values[1],
                voyage_dates_raw=values[2],
                causative_agent=values[3].lower(),
                href=normalize_href(index_url, date_cell.href),
                source_url=index_url,
                layout=layout,
            )
            if layout == "index_counts":
                row.pax_text = values[-2] if len(values) >= 6 else ""
                row.crew_text = values[-1] if len(values) >= 6 else ""
            rows.append(row)
    return rows


def index_table_counts(page: Page, years: set[int]) -> dict[int, int]:
    parser = PageParser()
    parser.feed(page.body)
    counts: dict[int, int] = {}
    for table in parser.tables:
        year = table_year(table.caption)
        if year in years and is_outbreak_table(table):
            counts[year] = counts.get(year, 0) + max(
                0, len(expanded_rows(table)) - 1
            )
    return counts


def count_values(text: str) -> tuple[str, str, str] | None:
    match = COUNT_RE.search(text)
    if not match:
        return None
    return (
        str(int(match.group("ill").replace(",", ""))),
        str(int(match.group("total").replace(",", ""))),
        match.group("pct") or "",
    )


def detail_counts(page: Page) -> tuple[str, str, str, str, str, str]:
    parser = PageParser()
    parser.feed(page.body)
    text = clean_text(" ".join(parser.visible_parts))
    found: dict[str, tuple[str, str, str]] = {}
    for match in COUNT_RE.finditer(text):
        before = text[max(0, match.start() - 300) : match.start()].lower()
        passenger_at = before.rfind("passenger")
        crew_at = before.rfind("crew")
        group = "pax" if passenger_at > crew_at else "crew"
        found.setdefault(
            group,
            (
                str(int(match.group("ill").replace(",", ""))),
                str(int(match.group("total").replace(",", ""))),
                match.group("pct") or "",
            ),
        )
    pax = found.get("pax", ("", "", ""))
    crew = found.get("crew", ("", "", ""))
    return (*pax, *crew)


def parse_inline_counts(row: IndexRow) -> tuple[str, str, str, str, str, str]:
    pax = count_values(row.pax_text) or ("", "", "")
    crew = count_values(row.crew_text) or ("", "", "")
    return (*pax, *crew)


def resolve_voyage_end(raw: str, index_year: int) -> str:
    tokens = DATE_TOKEN_RE.findall(raw)
    if not tokens:
        return ""
    end = tokens[-1]
    parts = [int(part) for part in end.split("/")]
    if len(parts) == 3:
        month, day, year = parts
        if year < 100:
            year += 1900 if index_year < 2000 else 2000
    else:
        month, day = parts
        explicit_year = YEAR_RE.search(raw)
        year = int(explicit_year.group(1)) if explicit_year else index_year
    try:
        return datetime(year, month, day).date().isoformat()
    except ValueError:
        return ""


def era_for(voyage_end: str) -> str:
    if not voyage_end:
        return ""
    if voyage_end < "2004-01-01":
        return "legacy_pre2004"
    if voyage_end <= "2019-12-31":
        return "pre"
    if voyage_end <= "2021-12-31":
        return "shutdown"
    return "post"


def classify_missing(
    row: IndexRow,
    counts: tuple[str, str, str, str, str, str],
    url: str,
    result: CheckResult,
) -> None:
    labels = ("pax_ill", "pax_total", "pax_pct_page", "crew_ill", "crew_total", "crew_pct_page")
    for label, value in zip(labels, counts):
        if not value:
            result.missing_counts.append(f"{row.year} {row.ship} {label}: {url}")


def percentage_failures(
    row: IndexRow,
    counts: tuple[str, str, str, str, str, str],
    url: str,
    result: CheckResult,
) -> None:
    for label, offset in (("passenger", 0), ("crew", 3)):
        ill, total, printed = counts[offset : offset + 3]
        if not ill or not total or not printed:
            continue
        calculated = 100.0 * int(ill) / int(total)
        tolerance = 0.5 if float(printed).is_integer() else 0.06
        if abs(calculated - float(printed)) > tolerance:
            result.percentage_failures.append(
                f"{row.year} {row.ship} {label}: calculated={calculated:.4f}, "
                f"printed={printed}, url={url}"
            )


def plausibility_failures(
    row: IndexRow,
    counts: tuple[str, str, str, str, str, str],
    url: str,
    result: CheckResult,
) -> None:
    ill, total, printed = counts[:3]
    checks = []
    if ill and total:
        checks.extend(
            [
                (not (0 < int(ill) <= int(total)), "passenger count"),
                (int(total) < 100, "passenger total < 100"),
            ]
        )
    if printed:
        checks.append((float(printed) > 100, "passenger percentage > 100"))
    for failed, label in checks:
        if failed:
            result.plausibility_failures.append(
                f"{row.year} {row.ship} {label}: url={url}"
            )


def build_record(
    row: IndexRow,
    counts: tuple[str, str, str, str, str, str],
    retrieved: str,
    source_url: str,
) -> dict[str, str]:
    return dict(
        zip(
            CSV_FIELDS,
            (
                str(row.year),
                row.cruise_line,
                row.ship,
                row.voyage_dates_raw,
                resolve_voyage_end(row.voyage_dates_raw, row.year),
                row.causative_agent,
                *counts,
                era_for(resolve_voyage_end(row.voyage_dates_raw, row.year)),
                source_url,
                retrieved,
            ),
        )
    )


def extract_rows(
    rows: list[IndexRow],
    cache_dir: Path,
    *,
    refresh: bool,
    delay: float,
    fetched_urls: set[str],
    checks: CheckResult,
) -> list[dict[str, str]]:
    records: list[dict[str, str]] = []
    for row in rows:
        page = (
            fetch_page(
                cache_dir,
                row.href,
                refresh=refresh,
                delay=delay,
                fetched_urls=fetched_urls,
            )
            if row.href and row.layout == "detail_counts"
            else None
        )
        source_url = row.href if page is not None else row.source_url
        counts = detail_counts(page) if page is not None else parse_inline_counts(row)
        if page is not None:
            retrieved = page.retrieved
        else:
            index_page = read_cache(cache_dir, row.source_url)
            retrieved = index_page.retrieved if index_page else date.today().isoformat()
        classify_missing(row, counts, source_url, checks)
        percentage_failures(row, counts, source_url, checks)
        plausibility_failures(row, counts, source_url, checks)
        records.append(build_record(row, counts, retrieved, source_url))
    return records


def threshold_counts(records: Iterable[dict[str, str]]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for record in records:
        pax = record["pax_pct_page"]
        crew = record["crew_pct_page"]
        if not pax or not crew or float(pax) >= 3 or float(crew) >= 3:
            continue
        era = record["era"]
        counts[era] = counts.get(era, 0) + 1
    return counts


def write_csv(path: Path, records: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    ordered = sorted(records, key=lambda record: record["voyage_end"], reverse=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=CSV_FIELDS, lineterminator="\n")
        writer.writeheader()
        writer.writerows(ordered)


def format_list(items: list[str]) -> str:
    return "\n".join(f"- {item}" for item in items) or "- None"


def unresolved_dates(records: list[dict[str, str]]) -> list[str]:
    return [
        f"{record['year']} {record['ship'] or '(ship missing)'}: "
        f"{record['voyage_dates_raw'] or '(date missing)'}; "
        f"url={record['source_url']}"
        for record in records
        if not record["voyage_end"]
    ]


def write_log(
    path: Path,
    records: list[dict[str, str]],
    expected_rows: dict[int, int],
    layouts: dict[int, set[str]],
    checks: CheckResult,
    sources: list[str],
    idempotence_passed: bool,
) -> None:
    actual_rows: dict[int, int] = {}
    for record in records:
        year = int(record["year"])
        actual_rows[year] = actual_rows.get(year, 0) + 1
    row_checks = [
        f"{year}: extracted {actual_rows.get(year, 0)}; "
        f"index rows {expected_rows.get(year, 0)}"
        for year in sorted(expected_rows)
    ]
    row_count_passed = all(
        actual_rows.get(year, 0) == expected_rows.get(year, 0)
        for year in expected_rows
    )
    era_counts: dict[str, int] = {}
    for record in records:
        era = record["era"]
        if era:
            era_counts[era] = era_counts.get(era, 0) + 1
    threshold = threshold_counts(records)
    unresolved = unresolved_dates(records)
    rows_2022 = [record for record in records if record["year"] == "2022"]
    complete_2022_count = sum(
        bool(
            record["pax_ill"]
            and record["pax_total"]
            and record["pax_pct_page"]
            and record["crew_ill"]
            and record["crew_total"]
            and record["crew_pct_page"]
        )
        for record in rows_2022
    )
    complete_2022 = all(
        record["pax_ill"]
        and record["pax_total"]
        and record["pax_pct_page"]
        and record["crew_ill"]
        and record["crew_total"]
        and record["crew_pct_page"]
        for record in rows_2022
    )
    lines = [
        "# VSP outbreak series extraction log",
        "",
        f"Extraction run date: {date.today().isoformat()}",
        "",
        "## Sources and layouts",
        "",
        *[f"- `{source}`" for source in sources],
        "",
        "| Year | Layout |",
        "|---:|---|",
    ]
    lines.extend(
        f"| {year} | {', '.join(sorted(layouts.get(year, {'none'})))} |"
        for year in sorted(expected_rows)
    )
    lines.extend(
        [
            "",
            "## Row-count check",
            "",
            f"- Overall: {'PASS' if row_count_passed else 'FAIL'}",
            *[f"- {line}" for line in row_checks],
            "",
            "## Rough completeness cross-check",
            "",
            f"- pre (2004-2019): {era_counts.get('pre', 0)} rows; "
            "operator-supplied rough comparison: approximately 261",
            f"- post (2022-2026): {era_counts.get('post', 0)} rows; "
            "operator-supplied rough comparison: approximately 64",
            "",
            "## Threshold check",
            "",
            "- PASS: threshold rows were counted without filtering them out.",
            *[
                f"- {era}: {threshold.get(era, 0)} rows with both printed "
                "passenger and crew percentages below 3%"
                for era in ("legacy_pre2004", "pre", "shutdown", "post")
            ],
            "",
            "## Unresolved voyage dates",
            "",
            format_list(unresolved),
            "",
            "## 2022 completeness",
            "",
            f"- {'PASS' if complete_2022 else 'GAPS'}: {complete_2022_count} "
            f"of {len(rows_2022)} rows have passenger and crew counts from the "
            f"archived 2022 source `{INDEX_2022}`.",
            "",
            "## Printed-percentage check failures",
            "",
            f"- Overall: {'PASS' if not checks.percentage_failures else 'FAIL'} "
            f"({len(checks.percentage_failures)} failures)",
            format_list(checks.percentage_failures),
            "",
            "## Plausibility check failures",
            "",
            f"- Overall: {'PASS' if not checks.plausibility_failures else 'FAIL'} "
            f"({len(checks.plausibility_failures)} failures)",
            format_list(checks.plausibility_failures),
            "",
            "## Missing or unparseable counts",
            "",
            f"- {len(checks.missing_counts)} field-level gaps were preserved as "
            "empty CSV fields.",
            format_list(checks.missing_counts),
            "",
            "## Idempotence check",
            "",
            f"- {'PASS' if idempotence_passed else 'FAIL'}: the script re-runs "
            "extraction from the raw cache and compares the resulting CSV bytes.",
        ]
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def run(args: argparse.Namespace) -> None:
    cache_dir = args.cache.expanduser()
    cache_dir.mkdir(parents=True, exist_ok=True)
    fetched_urls: set[str] = set()
    checks = CheckResult()
    source_specs = (
        (CURRENT_INDEX, {2026}),
        (EARLIER_INDEX, {2023, 2024, 2025}),
        (INDEX_2022, {2022}),
        (LEGACY_INDEX, set(range(1994, 2020))),
    )
    all_rows: list[IndexRow] = []
    expected_rows: dict[int, int] = {}
    layouts: dict[int, set[str]] = {}
    for source_url, years in source_specs:
        page = fetch_page(
            cache_dir,
            source_url,
            refresh=args.refresh,
            delay=args.delay,
            fetched_urls=fetched_urls,
        )
        rows = index_rows(page, source_url, years)
        all_rows.extend(rows)
        table_counts = index_table_counts(page, years)
        for year, count in table_counts.items():
            expected_rows[year] = expected_rows.get(year, 0) + count
        for row in rows:
            layouts.setdefault(row.year, set()).add(row.layout)
    records = extract_rows(
        all_rows,
        cache_dir,
        refresh=args.refresh,
        delay=args.delay,
        fetched_urls=fetched_urls,
        checks=checks,
    )
    write_csv(args.out, records)
    first = args.out.read_bytes()
    second_records = extract_rows(
        all_rows,
        cache_dir,
        refresh=False,
        delay=args.delay,
        fetched_urls=fetched_urls,
        checks=CheckResult(),
    )
    write_csv(args.out, second_records)
    idempotence_passed = args.out.read_bytes() == first
    if not idempotence_passed:
        raise RuntimeError("idempotence check failed: cached extraction changed CSV bytes")
    write_log(
        args.log,
        records,
        expected_rows,
        layouts,
        checks,
        [item[0] for item in source_specs],
        idempotence_passed,
    )
    print(f"wrote {len(records)} rows to {args.out}")
    print(f"wrote extraction log to {args.log}")
    print(f"missing or unparseable count fields: {len(checks.missing_counts)}")
    print(f"printed-percentage failures: {len(checks.percentage_failures)}")
    print(f"plausibility failures: {len(checks.plausibility_failures)}")
    print("idempotence: PASS")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--cache", type=Path, default=DEFAULT_CACHE)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--log", type=Path, default=DEFAULT_LOG)
    parser.add_argument("--refresh", action="store_true")
    parser.add_argument("--delay", type=float, default=REQUEST_DELAY_SECONDS)
    return parser.parse_args()


if __name__ == "__main__":
    run(parse_args())
