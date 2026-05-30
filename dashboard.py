"""
dashboard.py – Streamlit entry point (``streamlit run dashboard.py``).

Implementation lives in the ``dashboard/`` package. This file exists so
``streamlit run`` has a single script target; use ``import dashboard`` for
programmatic access (package, not this file).
"""
from __future__ import annotations

from dashboard import main

if __name__ == "__main__":
    main()
