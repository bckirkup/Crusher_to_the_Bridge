"""Validate the file-based norovirus ledger entry convention."""

from __future__ import annotations

import re
from datetime import date
from pathlib import Path

LEDGER_DIR = Path("docs/norovirus/ledger")
MAIN_LEDGER = Path("docs/norovirus/norovirus_open_ledger.md")
ID_RE = re.compile(r"^[A-Z][A-Z0-9]*(-[A-Z0-9]+)*$")
HEADER_RE = re.compile(r"^\*\*(Date|Commit|Status):\*\*\s*(.+)$")
NUMBERED_ITEM_RE = re.compile(r"^(\d+)\. \*\*")
FROZEN_LAST_ITEM = 58  # 58 is grandfathered from the concurrently-open AERO-CABIN-06 PR.
VALID_STATUSES = {"open", "measured", "closed"}


def test_ledger_entry_files_have_valid_headers() -> None:
    entries = sorted(path for path in LEDGER_DIR.glob("*.md") if path.name != "README.md")
    assert entries

    for path in entries:
        assert ID_RE.fullmatch(path.stem)
        lines = path.read_text(encoding="utf-8").splitlines()
        assert lines[0] == f"# {path.stem}"
        assert len(lines) >= 4

        fields = {
            match.group(1): match.group(2)
            for line in lines[1:4]
            if (match := HEADER_RE.fullmatch(line))
        }
        assert list(fields) == ["Date", "Commit", "Status"]
        assert fields.get("Date", "").strip()
        assert fields.get("Commit", "").strip()
        status = fields.get("Status", "").strip()
        assert status in VALID_STATUSES
        date.fromisoformat(fields["Date"].strip())


def test_main_ledger_numbered_items_remain_frozen() -> None:
    numbered_items = [
        int(match.group(1))
        for line in MAIN_LEDGER.read_text(encoding="utf-8").splitlines()
        if (match := NUMBERED_ITEM_RE.match(line))
    ]
    assert numbered_items
    assert max(numbered_items) <= FROZEN_LAST_ITEM
