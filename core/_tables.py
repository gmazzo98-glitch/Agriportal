"""
core/_tables.py — brand-coherent highlight tints for st.dataframe Stylers.

WHY
───
Several tables highlight rows with a pandas Styler, using the same neon palette
the charts did:
    background-color: rgba(0,229,160,0.25); color:#00e5a0     (mint)
    background-color: rgba(255,77,77,0.25); color:#ff4d4d     (hot red)
    background-color: rgba(255,193,61,0.25); color:#ffc13d    (amber)
These are injected from Python (so CSS can't reach them) and they neither match
the warm brand nor stay legible in dark mode.

The grid CHROME (header, gridlines, cell text) is painted by Streamlit's native
dataframe and already follows the active light/dark theme — so it needs no help.
Only the highlight tints do.

THE TINTS
─────────
Each tint is a LOW-ALPHA background wash + a MID-LUMINANCE brand text colour.
Low alpha means the wash reads correctly over either a white-linen cell or a
dark cell; mid-luminance text stays legible on both. One string, both themes.

USAGE — drop-in replacements
────────────────────────────
Replace the inline rgba strings in the existing highlight_* closures, e.g.

    # before
    return [""]*(len(row)-1) + ["background-color: rgba(255,77,77,0.25); color:#ff4d4d"]
    # after
    from core._tables import HIGH, MED, LOW, MATCH
    return [""]*(len(row)-1) + [HIGH]      # >60%  severe
    ...                         [MED]       # 40-60% caution
    ...                         [LOW]       # <40%  healthy
    ...                         [MATCH]     # subtle row match (no text colour)

Or call the ready-made helpers:
    from core._tables import severity_cell, match_row
    return [""]*(len(row)-1) + [severity_cell(val, hi=60, mid=40)]
    return match_row(row, condition=row["Predicted Industry"] != "Unknown / Other")
"""

from __future__ import annotations

# ── Cell tint strings (background wash + legible mid-tone text) ─────────────
# Severity scale — sage (good) → wheat (caution) → terracotta (severe).
LOW   = "background-color: rgba(79,138,91,0.18);  color:#4f8a5b; font-weight:600"   # healthy
MED   = "background-color: rgba(181,138,50,0.20);  color:#9a7322; font-weight:600"   # caution
HIGH  = "background-color: rgba(192,87,58,0.22);  color:#c0573a; font-weight:600"   # severe

# Subtle whole-row match — background wash only, text left to the theme ink.
MATCH = "background-color: rgba(79,138,91,0.12)"

# Neutral emphasis (totals / selected) — slate azure.
NEUTRAL = "background-color: rgba(63,125,156,0.20); color:#6f9cb3; font-weight:600"


def severity_cell(value, *, hi: float = 60.0, mid: float = 40.0,
                  reverse: bool = False) -> str:
    """
    Return a tint string for a single numeric cell on a 3-band severity scale.
    value above `hi`  → HIGH (terracotta);  above `mid` → MED (wheat);
    else → LOW (sage).  Set reverse=True when higher is BETTER (flips the scale).
    Accepts numbers or strings like "57.3%" / "N/A".
    """
    try:
        v = float(str(value).replace("%", "").strip())
    except (ValueError, TypeError):
        return ""
    bands = (LOW, MED, HIGH) if not reverse else (HIGH, MED, LOW)
    if v > hi:
        return bands[2]
    if v > mid:
        return bands[1]
    return bands[0]


def match_row(row, *, condition: bool) -> list[str]:
    """Subtle full-row match tint when `condition` is True, else no styling."""
    return [MATCH] * len(row) if condition else [""] * len(row)
