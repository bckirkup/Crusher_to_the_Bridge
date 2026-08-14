"""Allow ``python3 -m picard_framework.analysis.sentinel``."""

from __future__ import annotations

from picard_framework.analysis.sentinel.export_line_list import main

if __name__ == "__main__":
    raise SystemExit(main())
