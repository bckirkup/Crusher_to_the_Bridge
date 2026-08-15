"""Allow ``python3 -m picard_framework.analysis.sentinel``.

The module entry point is the sentinel run CLI. The line-list export keeps its
own entry point (``-m picard_framework.analysis.sentinel.export_line_list``): it
is an ABM-output step, not part of fitting.
"""

from __future__ import annotations

from picard_framework.analysis.sentinel.run_sentinel import main

if __name__ == "__main__":
    raise SystemExit(main())
