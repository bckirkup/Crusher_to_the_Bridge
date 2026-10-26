"""Accessors for the frozen campaign-reducer contract documents.

The JSON files under ``contracts/`` are the single schema authority
(``docs/campaign_reduction/SURVEY_AND_DEVIN_SPEC.md`` section 1). They are
read by the offline ``plan``/``validate`` operations and must never be
patched: a contract that looks wrong is reported, not edited.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

CONTRACTS_DIR = Path(__file__).resolve().parent / "contracts"

CANONICAL_INTERFACE = "CANONICAL_INTERFACE.json"
CAMPAIGN_COVERAGE = "CAMPAIGN_COVERAGE.json"
REQUEST_SCHEMA = "REQUEST.schema.json"
BOOTSTRAP_REQUEST_SCHEMA = "BOOTSTRAP_REQUEST.schema.json"
QUERY_SCHEMA = "QUERY.schema.json"

# ``analysis validate --request-kind <kind>`` selects which frozen schema the
# --request document is checked against. ``query`` means the document is a
# QUERY.json bounded query, not an execution envelope.
REQUEST_KIND_SCHEMAS = {
    "execution": REQUEST_SCHEMA,
    "bootstrap": BOOTSTRAP_REQUEST_SCHEMA,
    "query": QUERY_SCHEMA,
}

# CANONICAL_INTERFACE.json exit_codes. Argparse already exits 2 on bad argv,
# which reads consistently with "invalid contract".
EXIT_COMPLETE = 0
EXIT_INVALID_CONTRACT = 2
EXIT_ACCESS_OR_RESOURCE_BLOCKED = 3
EXIT_ADMISSION_REQUIRED_OR_EXCEEDED = 4
EXIT_BUDGET_STOPPED_CHECKPOINTED = 5
EXIT_SOURCE_CHANGED = 6
EXIT_SCHEMA_OR_CORRUPTION_QUARANTINE = 7
EXIT_PARTIAL_COVERAGE = 8
EXIT_RETURN_PATH_BLOCKED = 9

# Operations registered in the analysis namespace but not implemented by
# ticket D0 exit with this status; admission is the input that cannot be
# produced yet, so they share the ADMISSION_REQUIRED_OR_EXCEEDED code.
NOT_IMPLEMENTED_EXIT = EXIT_ADMISSION_REQUIRED_OR_EXCEEDED


def load(name: str) -> Any:
    """Parse a contract document by file name."""
    return json.loads((CONTRACTS_DIR / name).read_text(encoding="utf-8"))


def sha256(name: str) -> str:
    """Content hash of a contract document as shipped on disk."""
    return hashlib.sha256((CONTRACTS_DIR / name).read_bytes()).hexdigest()
