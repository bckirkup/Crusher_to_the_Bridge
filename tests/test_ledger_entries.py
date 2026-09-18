"""Validate the repository-wide ledger entry file convention."""

from __future__ import annotations

import json
import re
from datetime import date
from pathlib import Path

LEDGER_DIR = Path("docs/ledger")
MAIN_LEDGER = Path("docs/norovirus/norovirus_open_ledger.md")
PROFILE_SOURCE = Path("data/pathogens/active_profiles.json")
ID_RE = re.compile(r"^[A-Z][A-Z0-9]*(-[A-Z0-9]+)*$")
SHA_RE = re.compile(r"^(?:#\d+|[0-9a-f]{7,40})$")
HEADER_RE = re.compile(r"^\*\*(Date|Commit|Pathogens|Status|Measured at):\*\*\s*(.+)$")
NUMBERED_ITEM_RE = re.compile(r"^(\d+)\. \*\*")
FROZEN_LAST_ITEM = 58
VALID_STATUSES = {"open", "measured", "closed"}


def _profile_ids() -> set[str]:
    payload = json.loads(PROFILE_SOURCE.read_text(encoding="utf-8"))
    return {profile["pathogen_id"] for profile in payload["pathogens"]}


def test_ledger_entry_files_have_valid_headers() -> None:
    entries = sorted(path for path in LEDGER_DIR.glob("*.md") if path.name != "README.md")
    assert entries
    profile_ids = _profile_ids()

    for path in entries:
        assert ID_RE.fullmatch(path.stem)
        lines = path.read_text(encoding="utf-8").splitlines()
        assert lines[0] == f"# {path.stem}"
        assert len(lines) >= 5

        fields = []
        values = {}
        for line in lines[1:]:
            match = HEADER_RE.fullmatch(line)
            if match is None:
                break
            fields.append(match.group(1))
            values[match.group(1)] = match.group(2).strip()

        assert fields[:4] == ["Date", "Commit", "Pathogens", "Status"]
        assert fields[4:] in ([], ["Measured at"])
        date.fromisoformat(values["Date"])
        assert SHA_RE.fullmatch(values["Commit"])
        pathogens = values["Pathogens"]
        pathogen_ids = {item.strip() for item in pathogens.split(",")}
        assert pathogens == "all" or pathogen_ids <= profile_ids
        assert values["Pathogens"]
        assert values["Status"] in VALID_STATUSES
        if "Measured at" in values:
            assert re.fullmatch(r"[0-9a-f]{7,40}", values["Measured at"])


def test_main_ledger_numbered_items_remain_frozen() -> None:
    numbered_items = [
        int(match.group(1))
        for line in MAIN_LEDGER.read_text(encoding="utf-8").splitlines()
        if (match := NUMBERED_ITEM_RE.match(line))
    ]
    assert numbered_items
    assert max(numbered_items) <= FROZEN_LAST_ITEM
