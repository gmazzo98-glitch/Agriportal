"""
core/_charts.py — unified Plotly theming for the Agricultural Intelligence Portal.

WHY THIS EXISTS
───────────────
Charts across the app were each styled inline with two problems:

  1. Hardcoded white backgrounds:  plot_bgcolor="#ffffff", paper_bgcolor="#ffffff"
     → a glaring white box on the dark page in dark mode.

  2. A neon / synthetic-SaaS palette:  #00e5a0 #ff4d4d #4fc3f7 #ba68c8 #ffc13d …
     → clashes with the warm linen/sage brand; harsh in both light and dark.
     (Meanwhile a few charts used the brand sage/clay, so it was inconsistent
      chart-to-chart too.)

THE FIX  (one call per figure)
──────────────────────────────
    from core._charts import style_fig
    ...
    fig = go.Figure(...)
    ...                       # build traces exactly as before — no logic change
    style_fig(fig)            # ← add this one line, just before st.plotly_chart
    st.plotly_chart(fig, use_container_width=True)

style_fig():
  · sets paper_bgcolor / plot_bgcolor to TRANSPARENT, so the chart inherits the
    themed surface behind it (the [data-testid="stPlotlyChart"] card in
    _styles.py is already theme-aware). One palette, both modes.
  · themes grid, zero-line, axis & legend fonts with neutral, theme-safe values
    (axis text is additionally re-coloured to var(--ink) by the CSS layer).
  · applies the brand COLORWAY so traces without an explicit colour pick brand
    hues automatically.
  · REMAPS the old neon literals → brand equivalents, so existing inline
    marker_color / marker_colors / line.color assignments are cleaned up with
    no per-chart edits.

COLOUR PHILOSOPHY
─────────────────
Mid-saturation, mid-luminance, earthy hues. Each reads acceptably on BOTH a
near-white linen surface and a deep forest-floor dark surface — the cardinal
rule that the old neon palette broke (neon is too light/saturated for light
backgrounds, too hot for dark ones).
"""

from __future__ import annotations


# ═══════════════════════════════════════════════════════════════════════════
#  PALETTES
# ═══════════════════════════════════════════════════════════════════════════

# Categorical — for pies, multi-series bars, country/crop comparisons.
# Eight harmonised earthy hues, ordered for maximum adjacent contrast.
CATEGORICAL = [
    "#4f8a5b",  # sage green     (primary)
    "#c0573a",  # terracotta     (clay)
    "#cf9b3f",  # wheat / amber
    "#3f7d9c",  # slate azure
    "#8d6a9f",  # muted plum
    "#3f9c8f",  # teal
    "#b07d5b",  # clay-tan
    "#6f9a52",  # olive
]

# Semantic — money flows, deltas, sensitivity.
POSITIVE = "#4f8a5b"   # gains, revenue, NPV-positive   (sage)
NEGATIVE = "#c0573a"   # costs, losses, NPV-negative     (terracotta)
NEUTRAL  = "#3f7d9c"   # totals, subtotals, baseline     (slate azure)
ACCENT   = "#cf9b3f"   # highlight / forecast            (amber)

# Sequential — single-hue ramps (light→dark) for graduated bars / heat.
SEQ_SAGE  = ["#dCe7dd", "#a9c6ae", "#7aa882", "#4f8a5b", "#356b40", "#234b2c"]
SEQ_AZURE = ["#d7e3ea", "#a7c3d2", "#6f9cb3", "#3f7d9c", "#2c5a78", "#1d3f55"]

# Theme-neutral chrome — chosen to read on white linen AND dark forest.
_GRID      = "rgba(127,127,120,0.16)"   # faint gridlines
_ZEROLINE  = "rgba(127,127,120,0.34)"   # slightly stronger zero / baseline
_AXIS_FONT = "#8a8f86"                   # CSS re-colours axis text to var(--ink)
_FONT      = "#8a8f86"


# ═══════════════════════════════════════════════════════════════════════════
#  NEON → BRAND REMAP
#  Every hardcoded synthetic colour found in the page sources, mapped to its
#  brand equivalent. Handles hex (#rrggbb) and rgba()/rgb() with preserved alpha.
# ═══════════════════════════════════════════════════════════════════════════

# hex (lowercased, no alpha) → brand hex
_HEX_MAP = {
    "#00e5a0": POSITIVE,   # neon mint     → sage
    "#ff4d4d": NEGATIVE,   # hot red       → terracotta
    "#ffc13d": "#cf9b3f",  # bright amber  → wheat
    "#ffa726": "#c98a3a",  # orange        → deep amber
    "#4fc3f7": "#3f7d9c",  # cyan          → slate azure
    "#29b6f6": "#5a93b0",  # light blue    → azure (light)
    "#0288d1": "#2c5a78",  # blue          → azure (deep)
    "#01579b": "#1d3f55",  # navy          → azure (darkest)
    "#80d8ff": "#7fb0c8",  # pale cyan     → azure (pale)
    "#26c6da": "#3f9c8f",  # turquoise     → teal
    "#ba68c8": "#8d6a9f",  # purple        → muted plum
    "#ab47bc": "#8d6a9f",  # deep purple   → muted plum
    "# ef9a9a".replace(" ", ""): "#c2776f",  # pink rose → dusty rose
    "#ef9a9a": "#c2776f",
    "#66bb6a": "#6f9a52",  # light green   → olive
    "#8d6e63": "#8a6f5e",  # brown         → warm brown
    "#f1c40f": "#cf9b3f",  # sun yellow    → wheat
    "#3498db": "#3f7d9c",  # flat blue     → slate azure
    "#2ecc71": "#4f8a5b",  # flat green    → sage
}

# rgb triples (as tuples) → brand hex, used to remap rgba()/rgb() while keeping alpha
_RGB_MAP = {
    (0, 229, 160):  POSITIVE,   # rgba(0,229,160,a)   neon mint  → sage
    (255, 77, 77):  NEGATIVE,   # rgba(255,77,77,a)   hot red    → terracotta
    (255, 193, 61): "#cf9b3f",  # rgba(255,193,61,a)  amber
}


def _hex_to_rgb(h: str) -> tuple[int, int, int]:
    h = h.lstrip("#")
    return (int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16))


def _remap_color(c):
    """Map a single colour value (hex or rgba/rgb string) to its brand match.
    Returns the original if no mapping applies, or the input unchanged for
    brand colours / non-strings."""
    if not isinstance(c, str):
        return c
    s = c.strip().lower()

    # hex
    if s.startswith("#") and s in _HEX_MAP:
        return _HEX_MAP[s]

    # rgb() / rgba()
    if s.startswith("rgb"):
        nums = s[s.find("(") + 1 : s.find(")")].split(",")
        try:
            r, g, b = (int(float(nums[0])), int(float(nums[1])), int(float(nums[2])))
        except (ValueError, IndexError):
            return c
        if (r, g, b) in _RGB_MAP:
            br, bg, bb = _hex_to_rgb(_RGB_MAP[(r, g, b)])
            if len(nums) >= 4:                       # preserve alpha
                return f"rgba({br},{bg},{bb},{nums[3].strip()})"
            return f"rgb({br},{bg},{bb})"
    return c


def _remap_any(value):
    """Remap a colour, a list of colours, or leave anything else untouched."""
    if isinstance(value, (list, tuple)):
        return [_remap_color(v) for v in value]
    return _remap_color(value)


# ═══════════════════════════════════════════════════════════════════════════
#  PUBLIC API
# ═══════════════════════════════════════════════════════════════════════════

def style_fig(fig, *, remap: bool = True, legend: bool | None = None):
    """
    Apply the unified brand theme to a Plotly figure IN PLACE (also returns it).

    Parameters
    ----------
    remap   : if True (default), rewrite any neon literals already assigned to
              traces into their brand equivalents. Set False if a chart was
              already authored with brand colours and you want them untouched.
    legend  : force legend on/off; None keeps whatever the figure declared.

    No data, traces, ordering, or values are modified — only colour & chrome.
    """
    # ── 1. Transparent canvas + neutral typography + brand colorway ─────────
    layout = dict(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        colorway=CATEGORICAL,
        font=dict(family="Inter, Helvetica, sans-serif", color=_FONT, size=12),
        margin=dict(l=8, r=8, t=28, b=8),
        hoverlabel=dict(
            bgcolor="rgba(33,35,33,0.94)",
            bordercolor="rgba(127,127,120,0.4)",
            font=dict(family="Inter, sans-serif", color="#f0ece4", size=12),
        ),
    )
    if legend is not None:
        layout["showlegend"] = legend
    fig.update_layout(**layout)

    # Legend chrome (if present)
    fig.update_layout(
        legend=dict(
            font=dict(color=_AXIS_FONT, size=11),
            bgcolor="rgba(0,0,0,0)",
            bordercolor="rgba(127,127,120,0.25)",
        )
    )

    # ── 2. Themed axes (grid / zero-line / ticks) ───────────────────────────
    axis = dict(
        gridcolor=_GRID,
        zerolinecolor=_ZEROLINE,
        linecolor=_GRID,
        tickfont=dict(color=_AXIS_FONT, size=11),
        title_font=dict(color=_AXIS_FONT, size=12),
    )
    fig.update_xaxes(**axis)
    fig.update_yaxes(**axis)

    # ── 3. Remap any neon literals already on the traces ────────────────────
    if remap:
        for tr in fig.data:
            mk = getattr(tr, "marker", None)
            if mk is not None:
                if getattr(mk, "color", None) is not None:
                    try: tr.marker.color = _remap_any(mk.color)
                    except Exception: pass
                if getattr(mk, "colors", None) is not None:      # pie
                    try: tr.marker.colors = _remap_any(mk.colors)
                    except Exception: pass
                if getattr(mk, "line", None) is not None and getattr(mk.line, "color", None) is not None:
                    try: tr.marker.line.color = _remap_any(mk.line.color)
                    except Exception: pass
            ln = getattr(tr, "line", None)
            if ln is not None and getattr(ln, "color", None) is not None:
                try: tr.line.color = _remap_any(ln.color)
                except Exception: pass

    return fig


def bridge_colors(values):
    """
    Semantic colours for a P&L / cash bridge bar series:
    positive deltas → sage, negative → terracotta. Pass the list of bar values,
    get back a parallel list of colours.
    """
    return [POSITIVE if v >= 0 else NEGATIVE for v in values]


def diverging_colors(values, *, hi=POSITIVE, lo=NEGATIVE):
    """Two-tone colours for tornado / sensitivity bars."""
    return [hi if v >= 0 else lo for v in values]
