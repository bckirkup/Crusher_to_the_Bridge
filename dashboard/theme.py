"""LCARS theme constants and HTML helpers."""
from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    import plotly.graph_objects as go

# ── LCARS Styling ────────────────────────────────────────────────────────

# TNG-era LCARS palette
LCARS_GOLD = "#FF9900"
LCARS_AMBER = "#CC7700"
LCARS_BLUE = "#9999FF"
LCARS_PURPLE = "#CC99CC"
LCARS_PEACH = "#FFCC99"
LCARS_TAN = "#CC9966"
LCARS_RED = "#CC6666"
LCARS_GREEN = "#99CC99"
LCARS_BG = "#000000"
LCARS_PANEL = "#1A1A2E"

# Alert condition colours
ALERT_COLORS = {
    "BASELINE": LCARS_GREEN,
    "SUSPECTED": LCARS_GOLD,
    "CONFIRMED": LCARS_RED,
}
ALERT_LABELS = {
    "BASELINE": "CONDITION GREEN",
    "SUSPECTED": "YELLOW ALERT",
    "CONFIRMED": "RED ALERT",
}
STOPLIGHT_COLORS = {"GREEN": LCARS_GREEN, "AMBER": LCARS_GOLD, "RED": LCARS_RED}
_STOPLIGHT_SEVERITY = {"GREEN": 0, "AMBER": 1, "RED": 2}

# Plotly template overrides for LCARS look
LCARS_PLOTLY = {
    "template": "plotly_dark",
    "paper_bgcolor": "rgba(0,0,0,0)",
    "plot_bgcolor": "rgba(26,26,46,0.6)",
    "font": {"family": "Helvetica Neue, Arial, sans-serif", "color": LCARS_PEACH},
}


def apply_lcars_layout(fig: go.Figure, **overrides: Any) -> None:
    """Apply LCARS Plotly styling without duplicate layout keyword errors.

    Plotly 5.x/6.x rejects ``update_layout(**LCARS_PLOTLY, plot_bgcolor=...)``
    when the same key appears in both the spread dict and explicit kwargs.
    Passing one merged dict (positional) is safe across versions.
    """
    fig.update_layout({**LCARS_PLOTLY, **overrides})


LCARS_CSS = """
<style>
    /* LCARS background */
    .stApp {
        background-color: #000000;
    }
    /* Tab styling */
    .stTabs [data-baseweb="tab-list"] {
        gap: 2px;
    }
    .stTabs [data-baseweb="tab"] {
        background-color: #1A1A2E;
        color: #FFCC99;
        border-radius: 12px 12px 0 0;
        padding: 8px 20px;
        font-weight: bold;
    }
    .stTabs [aria-selected="true"] {
        background-color: #FF9900;
        color: #000000;
    }
    /* Metric styling */
    [data-testid="stMetricValue"] {
        color: #FF9900;
    }
    [data-testid="stMetricLabel"] {
        color: #FFCC99;
    }
    /* Subheader styling */
    .stMarkdown h2, .stMarkdown h3 {
        color: #FF9900;
        border-bottom: 2px solid #CC7700;
        padding-bottom: 4px;
    }
    /* Sidebar */
    [data-testid="stSidebar"] {
        background-color: #0D0D1A;
        border-right: 3px solid #FF9900;
    }
    /* Expander */
    .streamlit-expanderHeader {
        color: #FFCC99;
        background-color: #1A1A2E;
    }
    /* Divider */
    hr {
        border-color: #CC7700;
    }
</style>
"""


def _lcars_banner(text: str, color: str = LCARS_GOLD, bg: str = LCARS_PANEL) -> str:
    return (
        f"<div style='background:{bg}; border-left:6px solid {color}; "
        f"padding:10px 16px; border-radius:0 8px 8px 0; margin:6px 0; "
        f"font-size:14px; font-weight:bold; color:{color};'>"
        f"{text}</div>"
    )


def _lcars_alert_banner(status: str) -> str:
    color = ALERT_COLORS.get(status, "gray")
    label = ALERT_LABELS.get(status, status)
    return (
        f"<div style='background:linear-gradient(90deg, {color}22, {color}44); "
        f"border:2px solid {color}; border-radius:8px; padding:12px; "
        f"text-align:center; font-size:20px; font-weight:bold; "
        f"color:{color}; letter-spacing:3px; margin:8px 0;'>"
        f"{label}</div>"
    )


def _worst_stoplight(level: Any) -> str:
    if isinstance(level, dict):
        worst = "GREEN"
        for v in level.values():
            s = str(v)
            if _STOPLIGHT_SEVERITY.get(s, 0) > _STOPLIGHT_SEVERITY.get(worst, 0):
                worst = s
        return worst
    return str(level)
