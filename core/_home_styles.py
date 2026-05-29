"""
core/_home_styles.py
────────────────────
Page-specific styles for Home.py (farm finder, context panel, onboarding).

These rules contain ZERO hardcoded palette values — every colour comes from
the CSS custom properties defined in _styles.py.  That means dark-mode
(both OS-level and Streamlit's manual toggle) is handled entirely in one
place without touching this file.

USAGE in Home.py
────────────────
1. Remove (or comment out) the giant st.markdown("<style>…</style>") block
   that currently lives in Home.py.
2. Add this import alongside the existing _styles import:
       from core._home_styles import inject_home_styles
3. Call it once, right after inject_styles():
       inject_styles()
       inject_home_styles()

The existing st.markdown topbar / finder / panel HTML strings need no changes
because they already reference var(--accent), var(--ink-1), etc., which are
now live aliases defined in _styles.py.
"""

import streamlit as st


def _css() -> str:
    return """
<style id="agriportal-home-styles">

/* ═══════════════════════════════════════════════════════════════════════════
   TOP BAR
   ═══════════════════════════════════════════════════════════════════════════ */

.topbar {
  display:         flex;
  align-items:     center;
  justify-content: space-between;
  padding:         8px 0 14px 0;
  border-bottom:   1px solid var(--rule);
  margin-bottom:   22px;
}
.topbar .brand {
  display:     flex;
  align-items: center;
  gap:         10px;
  font-size:   14px;
  font-weight: 600;
  color:       var(--ink);
  letter-spacing: -0.005em;
}
.topbar .brand .mark {
  width:         22px;
  height:        22px;
  border-radius: 4px;
  background:    var(--accent);
  display:       inline-flex;
  align-items:   center;
  justify-content: center;
  color:         #fff;
  font-size:     12px;
  font-weight:   700;
}
.topbar .brand .sub {
  color:        var(--ink-3);
  font-weight:  400;
  font-size:    13px;
  margin-left:  8px;
  padding-left: 10px;
  border-left:  1px solid var(--rule);
}
.topbar .session-pill {
  display:     inline-flex;
  align-items: center;
  gap:         8px;
  font-size:   12px;
  color:       var(--ink-2);
  background:  var(--surface);
  border:      1px solid var(--rule);
  padding:     5px 10px;
  border-radius: 999px;
}
.topbar .session-pill .dot {
  width:         6px;
  height:        6px;
  border-radius: 50%;
  background:    var(--accent);
}
.topbar .session-pill.empty .dot { background: var(--ink-3); }
.topbar .session-pill .farm { color: var(--ink); font-weight: 600; }

/* ═══════════════════════════════════════════════════════════════════════════
   PAGE HEADING
   ═══════════════════════════════════════════════════════════════════════════ */

.pg-head            { margin-bottom: 18px; }
.pg-head h1         { font-size: 26px; font-weight: 600; letter-spacing: -0.015em; margin: 0 0 4px 0; color: var(--ink); }
.pg-head p          { font-size: 14px; color: var(--ink-2); margin: 0; }

/* ═══════════════════════════════════════════════════════════════════════════
   FINDER LIST
   ═══════════════════════════════════════════════════════════════════════════ */

.finder-head {
  display:         flex;
  align-items:     baseline;
  justify-content: space-between;
  margin-bottom:   8px;
}
.finder-head .h {
  font-size:      11px;
  font-weight:    600;
  letter-spacing: 0.12em;
  text-transform: uppercase;
  color:          var(--ink-3);
}
.finder-head .count { font-size: 11px; color: var(--ink-3); font-variant-numeric: tabular-nums; }

.finder-list {
  background:    var(--surface);
  border:        1px solid var(--rule);
  border-radius: 6px;
  overflow:      hidden;
}
.finder-row {
  display:               grid;
  grid-template-columns: 28px 1fr auto;
  align-items:           center;
  gap:                   12px;
  padding:               12px 14px;
  border-bottom:         1px solid var(--rule-soft);
  cursor:                pointer;
  transition:            background .12s ease;
  position:              relative;
}
.finder-row:last-child { border-bottom: none; }
.finder-row:hover      { background: var(--surface-2); }
.finder-row.selected   { background: var(--accent-soft); }
.finder-row.selected::before {
  content:  "";
  position: absolute; left: 0; top: 0; bottom: 0;
  width:    3px;
  background: var(--accent);
}
.finder-row .mono {
  font-size:            10px;
  font-weight:          700;
  letter-spacing:       0.04em;
  color:                var(--ink-2);
  background:           var(--rule-soft);
  border-radius:        3px;
  padding:              3px 0;
  text-align:           center;
  font-variant-numeric: tabular-nums;
}
.finder-row.selected .mono { background: var(--accent); color: #fff; }
.finder-row .name {
  font-size:     14px;
  font-weight:   500;
  color:         var(--ink);
  line-height:   1.25;
  min-width:     0;
  overflow:      hidden;
  text-overflow: ellipsis;
  white-space:   nowrap;
}
.finder-row .name .country { color: var(--ink-3); font-weight: 400; font-size: 12px; margin-left: 6px; }
.finder-row .footprint     { font-size: 12px; color: var(--ink-2); font-variant-numeric: tabular-nums; white-space: nowrap; }

.finder-empty {
  background:    var(--surface);
  border:        1px solid var(--rule);
  border-radius: 6px;
  padding:       22px 18px;
  text-align:    center;
  font-size:     13px;
  color:         var(--ink-2);
}

/* ── Clickable finder rows (Streamlit buttons styled as list rows) ───────── */
.finder-buttons {
  background:    var(--surface);
  border:        1px solid var(--rule);
  border-radius: 6px;
  overflow:      hidden;
}
.finder-buttons .row-btn .stButton > button,
.finder-buttons .row-btn.selected-row .stButton > button {
  height:         auto     !important;
  min-height:     48px     !important;
  padding:        12px 14px !important;
  border:         none     !important;
  border-bottom:  1px solid var(--rule-soft) !important;
  border-radius:  0        !important;
  background:     var(--surface) !important;
  text-align:     left     !important;
  justify-content: flex-start !important;
  font-size:      13px     !important;
  font-weight:    500      !important;
}
.finder-buttons .row-btn .stButton > button p,
.finder-buttons .row-btn .stButton > button div,
.finder-buttons .row-btn .stButton > button span {
  text-align:  left    !important;
  font-size:   13px    !important;
  font-weight: 500     !important;
  color:       var(--ink) !important;
  white-space: normal  !important;
  word-break:  break-word !important;
}
.finder-buttons .row-btn .stButton > button:hover:not(:disabled) {
  background: var(--surface-2) !important;
  border-color: var(--rule-soft) !important;
  color: var(--ink) !important;
}
.finder-buttons .row-btn .stButton > button:hover:not(:disabled) p,
.finder-buttons .row-btn .stButton > button:hover:not(:disabled) div,
.finder-buttons .row-btn .stButton > button:hover:not(:disabled) span {
  color: var(--ink) !important;
}
.finder-buttons .row-btn.selected-row .stButton > button {
  background:  var(--accent-soft) !important;
  box-shadow:  inset 3px 0 0 0 var(--accent) !important;
}
.finder-buttons .row-btn.selected-row .stButton > button p,
.finder-buttons .row-btn.selected-row .stButton > button div,
.finder-buttons .row-btn.selected-row .stButton > button span {
  color:       var(--ink) !important;
  font-weight: 600        !important;
}

/* ═══════════════════════════════════════════════════════════════════════════
   RIGHT PANEL
   ═══════════════════════════════════════════════════════════════════════════ */

.panel {
  background:    var(--surface);
  border:        1px solid var(--rule);
  border-radius: 6px;
  padding:       24px 26px;
}
.panel-head {
  display:         flex;
  align-items:     flex-start;
  justify-content: space-between;
  gap:             16px;
  padding-bottom:  18px;
  border-bottom:   1px solid var(--rule);
  margin-bottom:   20px;
}
.panel-head .farm-name {
  font-size:      22px;
  font-weight:    600;
  letter-spacing: -0.01em;
  color:          var(--ink);
  margin:         0 0 6px 0;
}
.panel-head .farm-meta { font-size: 13px; color: var(--ink-2); line-height: 1.5; }
.panel-head .farm-meta .mod  { color: var(--accent); font-weight: 600; }
.panel-head .farm-meta .dot  {
  display:       inline-block;
  width:         3px; height: 3px;
  background:    var(--ink-3);
  border-radius: 50%;
  margin:        0 8px;
  vertical-align: middle;
}

/* ── Activity timeline ──────────────────────────────────────────────────── */
.activity             { margin-bottom: 22px; }
.activity .h {
  font-size:      11px; font-weight: 600; letter-spacing: 0.12em;
  text-transform: uppercase; color: var(--ink-3); margin-bottom: 12px;
}
.activity .timeline {
  display:               grid;
  grid-template-columns: repeat(3, 1fr);
  gap:                   14px;
}
.activity .stat {
  padding:       12px 14px;
  background:    var(--bg);
  border:        1px solid var(--rule-soft);
  border-radius: 5px;
}
.activity .stat .lbl {
  font-size:      11px; color: var(--ink-3);
  text-transform: uppercase; letter-spacing: 0.08em; margin-bottom: 6px;
}
.activity .stat .val {
  font-size:            16px; font-weight: 600; color: var(--ink);
  line-height:          1.2;  font-variant-numeric: tabular-nums;
}
.activity .stat .val.muted { color: var(--ink-3); font-weight: 500; }
.activity .stat .sub       { font-size: 11px; color: var(--ink-3); margin-top: 2px; }

/* ── Destination cards ──────────────────────────────────────────────────── */
.destinations .h {
  font-size: 11px; font-weight: 600; letter-spacing: 0.12em;
  text-transform: uppercase; color: var(--ink-3); margin-bottom: 12px;
}
.dest-card {
  background:    var(--surface);
  border:        1px solid var(--rule);
  border-radius: 6px;
  padding:       16px 18px;
  margin-bottom: 10px;
  transition:    border-color .15s ease, background .15s ease;
}
.dest-card:hover {
  border-color: var(--accent);
  background:   var(--surface-2);
}
.dest-card .lead  { font-size: 14px; font-weight: 600; color: var(--ink); margin-bottom: 4px; letter-spacing: -0.005em; }
.dest-card .desc  { font-size: 13px; color: var(--ink-2); margin-bottom: 10px; line-height: 1.45; }

/* ── Empty panel ────────────────────────────────────────────────────────── */
.panel-empty .h2  { font-size: 18px; font-weight: 600; color: var(--ink); margin: 0 0 6px 0; }
.panel-empty .sub { font-size: 14px; color: var(--ink-2); margin-bottom: 22px; line-height: 1.5; }
.panel-empty .what-row {
  display:    flex; gap: 14px;
  padding:    14px 0;
  border-top: 1px solid var(--rule-soft);
}
.panel-empty .what-row:last-child  { border-bottom: 1px solid var(--rule-soft); }
.panel-empty .what-row .num        { font-size: 13px; color: var(--ink-3); font-weight: 600; font-variant-numeric: tabular-nums; min-width: 28px; padding-top: 1px; }
.panel-empty .what-row .body       { flex: 1; }
.panel-empty .what-row .body strong { font-size: 14px; color: var(--ink); font-weight: 600; display: block; margin-bottom: 2px; }
.panel-empty .what-row .body span  { font-size: 13px; color: var(--ink-2); line-height: 1.5; }

/* ═══════════════════════════════════════════════════════════════════════════
   ONBOARDING (first-time, no farms)
   ═══════════════════════════════════════════════════════════════════════════ */

.onboard {
  background:    var(--surface);
  border:        1px solid var(--rule);
  border-radius: 8px;
  padding:       56px 48px;
  text-align:    center;
}
.onboard .glyph {
  width:           56px; height: 56px;
  border-radius:   50%;
  background:      var(--accent-soft);
  color:           var(--accent);
  display:         inline-flex;
  align-items:     center;
  justify-content: center;
  font-size:       24px;
  margin-bottom:   18px;
}
.onboard h2 { font-size: 22px; font-weight: 600; color: var(--ink);   margin: 0 0 8px 0; }
.onboard p  { font-size: 14px; color: var(--ink-2); margin: 0 auto 22px auto; max-width: 480px; line-height: 1.55; }

/* ═══════════════════════════════════════════════════════════════════════════
   ROSTER SUMMARY
   ═══════════════════════════════════════════════════════════════════════════ */

.roster-summary {
  margin-top:    14px;
  background:    var(--surface);
  border:        1px solid var(--rule);
  border-radius: 6px;
  padding:       14px 16px;
}
.roster-summary .rs-h {
  font-size: 11px; font-weight: 600; letter-spacing: 0.12em;
  text-transform: uppercase; color: var(--ink-3); margin-bottom: 10px;
}
.roster-summary .rs-stats {
  display:               grid;
  grid-template-columns: 1fr 1fr;
  gap:                   10px;
  margin-bottom:         12px;
}
.roster-summary .rs-stat .lbl {
  font-size: 11px; color: var(--ink-3);
  text-transform: uppercase; letter-spacing: 0.06em; margin-bottom: 2px;
}
.roster-summary .rs-stat .val { font-size: 15px; font-weight: 600; color: var(--ink); font-variant-numeric: tabular-nums; }
.roster-summary .rs-chips {
  display:      flex; flex-wrap: wrap; gap: 6px;
  padding-top:  10px;
  border-top:   1px solid var(--rule-soft);
}
.roster-summary .chip {
  font-size:     11px;
  color:         var(--ink-2);
  background:    var(--bg);
  border:        1px solid var(--rule);
  padding:       3px 8px;
  border-radius: 999px;
}
.roster-summary .chip b { color: var(--accent); font-weight: 700; margin-right: 4px; }

/* ═══════════════════════════════════════════════════════════════════════════
   FARM SETUP WIZARD — progress & modality cards
   ═══════════════════════════════════════════════════════════════════════════ */

/* The progress bar and step label are rendered via st.markdown inline HTML
   in _render_farm_setup(). Those strings already use hardcoded hex values.
   The two lines below re-target the progress segment colours so they use
   tokens even when the hex is left in the markup. */
.farm-setup-progress-active   { background: var(--accent)  !important; }
.farm-setup-progress-inactive { background: var(--rule)    !important; }

/* ═══════════════════════════════════════════════════════════════════════════
   DANGER BUTTON WRAPPER
   ─────────────────────────────────────────────────────────────────────────
   Usage: wrap a st.button in st.markdown('<div class="danger-btn">') ...
   ('danger-btn' class is referenced in existing Home.py HTML)
   ═══════════════════════════════════════════════════════════════════════════ */

.danger-btn .stButton > button {
  border-color: var(--rule) !important;
  color:        var(--ink-3) !important;
  background:   var(--surface) !important;
}
.danger-btn .stButton > button p,
.danger-btn .stButton > button div,
.danger-btn .stButton > button span { color: var(--ink-3) !important; }
.danger-btn .stButton > button:hover:not(:disabled) {
  border-color: var(--warn) !important;
  color:        var(--warn) !important;
  background:   var(--surface) !important;
}
.danger-btn .stButton > button:hover:not(:disabled) p,
.danger-btn .stButton > button:hover:not(:disabled) div,
.danger-btn .stButton > button:hover:not(:disabled) span { color: var(--warn) !important; }

/* ═══════════════════════════════════════════════════════════════════════════
   PAGE LINK — primary variant
   ═══════════════════════════════════════════════════════════════════════════ */

.primary-link a[data-testid="stPageLink-NavLink"] {
  background:   var(--accent)   !important;
  border-color: var(--accent)   !important;
}
.primary-link a[data-testid="stPageLink-NavLink"] p { color: #fff !important; }
.primary-link a[data-testid="stPageLink-NavLink"]:hover {
  background:   var(--accent-d) !important;
  border-color: var(--accent-d) !important;
}
.primary-link a[data-testid="stPageLink-NavLink"]:hover p { color: #fff !important; }

/* ═══════════════════════════════════════════════════════════════════════════
   SEARCH INPUT — hide label, custom chrome
   ═══════════════════════════════════════════════════════════════════════════ */

div[data-testid="stTextInput"] label              { display: none !important; }
div[data-testid="stHorizontalBlock"]              { align-items: stretch !important; }

</style>
"""


def inject_home_styles() -> None:
    """
    Inject Home.py-specific page styles.
    Call right after inject_styles() in Home.py.
    """
    st.markdown(_css(), unsafe_allow_html=True)
