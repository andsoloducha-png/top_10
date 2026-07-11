from __future__ import annotations

from datetime import time


REQUIRED_COLUMNS = ["begin", "end", "item", "description"]

PROCESS_START = time(6, 0)
PROCESS_END = time(22, 30)

JAM_WASTELINE_START = 301.010
JAM_WASTELINE_END = 317.030

CHUTE_FULL_MIN = 200.0
CHUTE_FULL_MAX = 300.0

CHART_COLORS = [
    "#fb923c",
    "#60a5fa",
    "#a78bfa",
    "#84cc16",
    "#ef4444",
    "#22c55e",
    "#06b6d4",
    "#e879f9",
    "#f59e0b",
    "#94a3b8",
]
