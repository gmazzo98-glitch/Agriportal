"""
Agricultural Intelligence Portal — shared visual language.
Dual-mode stylesheet: adapts automatically to light AND dark themes.

DESIGN BRIEF  (unchanged from V1)
──────────────────────────────────
This is a serious modelling tool used by analysts and operators. The visual
language must be:
  · Data-first: high contrast, generous numeric type, clean tabular alignment.
  · Trustworthy: restrained palette, no decorative gradients, no rounded fluff.
  · Agricultural in tone: warm neutrals (paper/clay/linen), botanical green
    accent — not cold financial blue, not synthetic SaaS purple.
  · Quiet: chrome stays out of the way; the data is the protagonist.

DARK MODE
─────────
Both modes share the same warm, agricultural character:
  Light: linen-white surfaces, near-black ink, botanical sage green.
  Dark:  deep forest-floor surfaces, warm off-white ink, same green
         shifted brighter to maintain contrast on dark backgrounds.

Detection strategy:
  1. @media (prefers-color-scheme: dark)  — OS-level dark mode (CSS only)
  2. [data-theme="dark"] on <html>        — Streamlit's in-app manual toggle,
                                            detected by the JS component injected
                                            in inject_styles() below.
  Both layers set the same CSS variable overrides, so either path works.

VARIABLE ALIASES
────────────────
Home.py uses its own variable naming convention (--ink-1, --accent, --font,
etc.). Rather than editing that file, _styles.py defines aliases so that
all pages pick up dark-mode automatically with zero changes to their HTML.
"""

import streamlit as st


# ── Token reference (light mode canonical values) ──────────────────────────
TOKENS = {
    "ink":       "#161a16",
    "ink_2":     "#4a524a",
    "ink_3":     "#7a807a",
    "bg":        "#f4f1ea",
    "surface":   "#ffffff",
    "surface_2": "#fbf9f4",
    "rule":      "#d9d4c5",
    "rule_soft": "#e8e3d4",
    "sage":      "#2f5d3a",
    "sage_hi":   "#3e7448",
    "sage_tint": "#e6ede4",
    "clay":      "#b85c38",
    "amber":     "#c08a2e",
    "azure":     "#2c5a78",
    "font_sans": "'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif",
    "font_mono": "'JetBrains Mono', ui-monospace, SFMono-Regular, Menlo, monospace",
}
# Backward-compat alias
TOKENS["paper"] = TOKENS["bg"]


# ── JS dark-mode detector ────────────────────────────────────────────────────
# Injected via st.components.v1.html() (0px height, invisible).
# Reads the computed background-colour of .stApp in the parent frame and sets
# data-theme="dark"|"light" on <html>, enabling the [data-theme="dark"] CSS
# selectors below. Runs once on load, then re-checks every 800ms so it catches
# live toggles without a page refresh.
_DARK_DETECTOR_HTML = """
<script>
(function () {
  function apply() {
    try {
      var el = window.parent.document.querySelector('.stApp');
      if (!el) return;
      var bg = window.parent.getComputedStyle(el).backgroundColor;
      var m  = bg.match(/\\d+/g);
      if (!m || m.length < 3) return;
      var lum = (parseInt(m[0]) * 299 + parseInt(m[1]) * 587 + parseInt(m[2]) * 114) / 1000;
      window.parent.document.documentElement.setAttribute('data-theme', lum < 145 ? 'dark' : 'light');
    } catch (_) {}
  }
  apply();
  setInterval(apply, 800);
})();
</script>
"""


def _css() -> str:
    return """
<style id="agriportal-styles">
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500;600&display=swap');

/* ═══════════════════════════════════════════════════════════════════════════
   COLOUR TOKENS
   ─────────────────────────────────────────────────────────────────────────
   :root   = light mode (default)
   @media (prefers-color-scheme: dark)  } both set identical overrides so
   [data-theme="dark"]                  } either detection path works
   ═══════════════════════════════════════════════════════════════════════════ */

:root {
  color-scheme: light dark;

  /* ── Core palette ─────────────────────────────────────── */
  --ink:        #161a16;
  --ink-2:      #4a524a;
  --ink-3:      #7a807a;
  --bg:         #f4f1ea;
  --surface:    #ffffff;
  --surface-2:  #fbf9f4;
  --rule:       #d9d4c5;
  --rule-soft:  #e8e3d4;
  --sage:       #2f5d3a;
  --sage-hi:    #3e7448;
  --sage-tint:  #e6ede4;
  --clay:       #b85c38;
  --amber:      #c08a2e;
  --azure:      #2c5a78;

  /* ── Alert tints (separate so they can flip in dark mode) */
  --tint-info:    #e6edf2;
  --tint-warn:    #f5ecd6;
  --tint-error:   #f3dfd2;
  --tint-success: #e6ede4;

  /* ── Typography ───────────────────────────────────────── */
  --font-sans: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
  --font-mono: 'JetBrains Mono', ui-monospace, SFMono-Regular, Menlo, monospace;

  /* ── Aliases for Home.py inline CSS compatibility ─────── */
  --ink-1:        var(--ink);
  --paper:        var(--bg);
  --accent:       var(--sage);
  --accent-d:     var(--sage-hi);
  --accent-soft:  var(--sage-tint);
  --warn:         var(--clay);
  --font:         var(--font-sans);
}

/* ── Dark mode — OS / system level ──────────────────────────────────────── */
@media (prefers-color-scheme: dark) {
  :root {
    --ink:        #e8e4db;
    --ink-2:      #9ba394;
    --ink-3:      #5e6659;
    --bg:         #191b19;
    --surface:    #212321;
    --surface-2:  #262826;
    --rule:       #2e342e;
    --rule-soft:  #272b27;
    --sage:       #52a066;
    --sage-hi:    #62b076;
    --sage-tint:  #182a1c;
    --clay:       #d4724e;
    --amber:      #d4a845;
    --azure:      #4a88b8;
    --tint-info:    #182230;
    --tint-warn:    #281e0e;
    --tint-error:   #281510;
    --tint-success: #182a1c;
  }
}

/* ── Dark mode — Streamlit in-app toggle (set by JS detector) ────────────── */
[data-theme="dark"] {
  --ink:        #e8e4db;
  --ink-2:      #9ba394;
  --ink-3:      #5e6659;
  --bg:         #191b19;
  --surface:    #212321;
  --surface-2:  #262826;
  --rule:       #2e342e;
  --rule-soft:  #272b27;
  --sage:       #52a066;
  --sage-hi:    #62b076;
  --sage-tint:  #182a1c;
  --clay:       #d4724e;
  --amber:      #d4a845;
  --azure:      #4a88b8;
  --tint-info:    #182230;
  --tint-warn:    #281e0e;
  --tint-error:   #281510;
  --tint-success: #182a1c;
}

/* ═══════════════════════════════════════════════════════════════════════════
   SHELL
   ═══════════════════════════════════════════════════════════════════════════ */

html, body, .stApp {
  background:              var(--bg) !important;
  color:                   var(--ink);
  font-family:             var(--font-sans);
  -webkit-font-smoothing:  antialiased;
}
.block-container {
  padding-top:    1.4rem;
  padding-bottom: 3rem;
  max-width:      1380px;
}
header[data-testid="stHeader"] { background: transparent !important; }
#MainMenu, footer               { visibility: hidden; }

/* Prevent Streamlit's own theme bleeds */
.stApp > div,
[data-testid="stAppViewContainer"],
[data-testid="stMain"],
[data-testid="stBottom"] {
  background: transparent !important;
}

/* ── Global text colour inheritance ─────────────────────────────────────── */
.stApp p, .stApp span, .stApp label, .stApp div { color: var(--ink); }

/* ═══════════════════════════════════════════════════════════════════════════
   TYPOGRAPHY
   ═══════════════════════════════════════════════════════════════════════════ */

.stMarkdown h1 {
  font-size: 28px; font-weight: 700; letter-spacing: -0.02em;
  margin: 0 0 .4rem; color: var(--ink);
}
.stMarkdown h2 {
  font-size: 20px; font-weight: 700; letter-spacing: -0.01em;
  margin: 1.4rem 0 .5rem; color: var(--ink);
}
.stMarkdown h3 {
  font-size: 15px; font-weight: 700;
  margin: 1.1rem 0 .4rem; color: var(--ink);
}
.stMarkdown h4 {
  font-size: 13px; font-weight: 600; margin: .9rem 0 .3rem;
  color: var(--ink-2); text-transform: uppercase; letter-spacing: 0.08em;
}
.stMarkdown p, .stMarkdown li {
  font-size: 14px; line-height: 1.55; color: var(--ink);
}
[data-testid="stCaptionContainer"], .stCaption {
  color: var(--ink-3) !important; font-size: 12px;
}

/* ═══════════════════════════════════════════════════════════════════════════
   SIDEBAR
   ─────────────────────────────────────────────────────────────────────────
   Always dark — a deliberate "control panel" aesthetic.
   Slightly darker in dark mode to keep it distinct from the main canvas.
   ═══════════════════════════════════════════════════════════════════════════ */

[data-testid="stSidebar"] {
  background:   #1a1e1a !important;
  border-right: 1px solid #252a25 !important;
}
[data-testid="stSidebar"] *,
[data-testid="stSidebar"] p,
[data-testid="stSidebar"] span,
[data-testid="stSidebar"] label,
[data-testid="stSidebar"] div,
[data-testid="stSidebar"] li    { color: #d6d2c8; }
[data-testid="stSidebar"] h1,
[data-testid="stSidebar"] h2,
[data-testid="stSidebar"] h3,
[data-testid="stSidebar"] h4    { color: #f0ece4 !important; }
[data-testid="stSidebar"] [data-testid="stMarkdownContainer"] strong { color: #f0ece4; }
[data-testid="stSidebar"] [data-testid="stCaptionContainer"] { color: #7a8070 !important; }
[data-testid="stSidebar"] hr    { border-color: #252a25; }
[data-testid="stSidebar"] [data-testid="stWidgetLabel"] p,
[data-testid="stSidebar"] [data-testid="stWidgetLabel"] {
  color: #9ba390 !important; font-size: 12px; font-weight: 500;
}
/* Sidebar inputs */
[data-testid="stSidebar"] input,
[data-testid="stSidebar"] textarea,
[data-testid="stSidebar"] [data-baseweb="select"] > div {
  background: #252a25 !important;
  color:      #f0ece4 !important;
  border:     1px solid #363c36 !important;
}
[data-testid="stSidebar"] [data-baseweb="select"] > div * { color: #f0ece4 !important; }
[data-testid="stSidebar"] input:focus,
[data-testid="stSidebar"] [data-baseweb="select"]:focus-within > div {
  border-color: var(--sage) !important;
}
/* Sidebar buttons */
[data-testid="stSidebar"] .stButton > button {
  background: #252a25; color: #d6d2c8; border: 1px solid #363c36;
}
[data-testid="stSidebar"] .stButton > button p,
[data-testid="stSidebar"] .stButton > button span,
[data-testid="stSidebar"] .stButton > button div { color: #d6d2c8 !important; }
[data-testid="stSidebar"] .stButton > button:hover:not(:disabled) {
  background: var(--sage); border-color: var(--sage); color: #ffffff;
}
[data-testid="stSidebar"] .stButton > button:hover:not(:disabled) p,
[data-testid="stSidebar"] .stButton > button:hover:not(:disabled) span,
[data-testid="stSidebar"] .stButton > button:hover:not(:disabled) div { color: #ffffff !important; }
/* Sidebar primary buttons */
[data-testid="stSidebar"] .stButton > button[kind="primary"] {
  background: var(--sage); color: #ffffff; border-color: var(--sage);
}
[data-testid="stSidebar"] .stButton > button[kind="primary"] p,
[data-testid="stSidebar"] .stButton > button[kind="primary"] span,
[data-testid="stSidebar"] .stButton > button[kind="primary"] div { color: #ffffff !important; }
[data-testid="stSidebar"] .stButton > button[kind="primary"]:hover:not(:disabled) {
  background: var(--sage-hi); border-color: var(--sage-hi);
}

/* ═══════════════════════════════════════════════════════════════════════════
   BUTTONS — main canvas
   ═══════════════════════════════════════════════════════════════════════════ */

.stButton > button,
.stDownloadButton > button,
.stFormSubmitButton > button {
  background:    var(--surface);
  color:         var(--ink);
  border:        1.5px solid var(--rule);
  border-radius: 3px;
  padding:       8px 14px;
  font-family:   var(--font-sans);
  font-size:     13px;
  font-weight:   600;
  letter-spacing: 0.01em;
  box-shadow:    none;
  transition:    background .12s ease, color .12s ease, border-color .12s ease;
}
.stButton > button p, .stButton > button div, .stButton > button span,
.stDownloadButton > button p, .stDownloadButton > button div, .stDownloadButton > button span,
.stFormSubmitButton > button p, .stFormSubmitButton > button div, .stFormSubmitButton > button span {
  color: var(--ink) !important; margin: 0;
}
/* Hover — invert for crisp contrast in both light and dark */
.stButton > button:hover:not(:disabled),
.stDownloadButton > button:hover:not(:disabled),
.stFormSubmitButton > button:hover:not(:disabled) {
  background:   var(--ink);
  color:        var(--surface);
  border-color: var(--ink);
}
.stButton > button:hover:not(:disabled) p,
.stButton > button:hover:not(:disabled) div,
.stButton > button:hover:not(:disabled) span,
.stDownloadButton > button:hover:not(:disabled) p,
.stDownloadButton > button:hover:not(:disabled) div,
.stDownloadButton > button:hover:not(:disabled) span,
.stFormSubmitButton > button:hover:not(:disabled) p,
.stFormSubmitButton > button:hover:not(:disabled) div,
.stFormSubmitButton > button:hover:not(:disabled) span { color: var(--surface) !important; }

/* Primary */
.stButton > button[kind="primary"],
.stFormSubmitButton > button[kind="primary"] {
  background: var(--sage); color: #ffffff; border-color: var(--sage);
}
.stButton > button[kind="primary"] p,
.stButton > button[kind="primary"] div,
.stButton > button[kind="primary"] span,
.stFormSubmitButton > button[kind="primary"] p,
.stFormSubmitButton > button[kind="primary"] div,
.stFormSubmitButton > button[kind="primary"] span { color: #ffffff !important; }
.stButton > button[kind="primary"]:hover:not(:disabled),
.stFormSubmitButton > button[kind="primary"]:hover:not(:disabled) {
  background: var(--sage-hi); border-color: var(--sage-hi); color: #ffffff;
}
.stButton > button[kind="primary"]:hover:not(:disabled) p,
.stButton > button[kind="primary"]:hover:not(:disabled) span,
.stButton > button[kind="primary"]:hover:not(:disabled) div,
.stFormSubmitButton > button[kind="primary"]:hover:not(:disabled) p,
.stFormSubmitButton > button[kind="primary"]:hover:not(:disabled) span,
.stFormSubmitButton > button[kind="primary"]:hover:not(:disabled) div { color: #ffffff !important; }

/* Disabled */
.stButton > button:disabled,
.stDownloadButton > button:disabled,
.stFormSubmitButton > button:disabled {
  background:   var(--surface-2) !important;
  color:        var(--ink-3)     !important;
  border-color: var(--rule)      !important;
  opacity: 0.75;
}
.stButton > button:disabled p, .stButton > button:disabled span, .stButton > button:disabled div,
.stDownloadButton > button:disabled p, .stDownloadButton > button:disabled span, .stDownloadButton > button:disabled div,
.stFormSubmitButton > button:disabled p, .stFormSubmitButton > button:disabled span, .stFormSubmitButton > button:disabled div {
  color: var(--ink-3) !important;
}

/* ═══════════════════════════════════════════════════════════════════════════
   PAGE LINKS
   ═══════════════════════════════════════════════════════════════════════════ */

a[data-testid="stPageLink-NavLink"] {
  background:    var(--surface);
  border:        1.5px solid var(--rule);
  border-radius: 3px;
  padding:       8px 14px;
  transition:    background .12s, border-color .12s;
}
a[data-testid="stPageLink-NavLink"] p {
  color: var(--ink); font-weight: 600; font-size: 13px; margin: 0;
}
a[data-testid="stPageLink-NavLink"]:hover {
  background: var(--ink); border-color: var(--ink);
}
a[data-testid="stPageLink-NavLink"]:hover p { color: var(--surface); }

/* ═══════════════════════════════════════════════════════════════════════════
   INPUTS — text, number, date, textarea
   ═══════════════════════════════════════════════════════════════════════════ */

.stTextInput input,
.stNumberInput input,
.stDateInput input,
.stTextArea textarea {
  background:    var(--surface);
  color:         var(--ink);
  border:        1px solid var(--rule);
  border-radius: 3px;
  font-family:   var(--font-sans);
  font-size:     13px;
  padding:       8px 10px;
  box-shadow:    none;
}
.stTextInput input:focus,
.stNumberInput input:focus,
.stDateInput input:focus,
.stTextArea textarea:focus {
  border-color: var(--sage);
  outline:      none;
  box-shadow:   0 0 0 2px var(--sage-tint);
}
/* Placeholder text */
.stTextInput input::placeholder,
.stNumberInput input::placeholder,
.stTextArea textarea::placeholder { color: var(--ink-3); }

/* Widget labels */
[data-testid="stWidgetLabel"] p,
.stTextInput label, .stNumberInput label, .stSelectbox label,
.stMultiSelect label, .stSlider label, .stRadio label,
.stCheckbox label, .stDateInput label, .stTextArea label {
  color: var(--ink-2); font-size: 12px; font-weight: 600;
}

/* Number input stepper buttons */
.stNumberInput button {
  background:   var(--surface-2) !important;
  color:        var(--ink)       !important;
  border-color: var(--rule)      !important;
}
.stNumberInput button:hover { background: var(--rule-soft) !important; }
.stNumberInput button svg   { fill: var(--ink) !important; }

/* ═══════════════════════════════════════════════════════════════════════════
   SELECTBOX / MULTISELECT
   ═══════════════════════════════════════════════════════════════════════════ */

.stSelectbox   div[data-baseweb="select"] > div,
.stMultiSelect div[data-baseweb="select"] > div {
  background:    var(--surface);
  border:        1px solid var(--rule);
  border-radius: 3px;
  min-height:    38px;
}
.stSelectbox   div[data-baseweb="select"] > div *,
.stMultiSelect div[data-baseweb="select"] > div * { color: var(--ink); font-size: 13px; }
.stSelectbox   div[data-baseweb="select"]:focus-within > div,
.stMultiSelect div[data-baseweb="select"]:focus-within > div {
  border-color: var(--sage);
  box-shadow:   0 0 0 2px var(--sage-tint);
}
/* Dropdown caret icon */
.stSelectbox svg { fill: var(--ink-2) !important; }

/* Dropdown menu portal */
[data-baseweb="popover"],
[data-baseweb="menu"]    { background: var(--surface) !important; }
[data-baseweb="menu"] ul { background: var(--surface) !important; }
[data-baseweb="menu"] li {
  background: var(--surface) !important;
  color:      var(--ink)     !important;
}
[data-baseweb="menu"] li:hover,
[data-baseweb="menu"] li[aria-selected="true"] { background: var(--sage-tint) !important; }
[data-baseweb="menu"] li * { color: var(--ink) !important; }

/* Multiselect tags */
[data-baseweb="tag"] {
  background:   var(--sage-tint) !important;
  border-color: var(--sage)      !important;
}
[data-baseweb="tag"] span  { color: var(--sage)    !important; }
[data-baseweb="tag"] [role="button"] svg { fill: var(--sage) !important; }

/* ═══════════════════════════════════════════════════════════════════════════
   SLIDER
   ═══════════════════════════════════════════════════════════════════════════ */

.stSlider [data-baseweb="slider"] > div > div:first-child {
  background: var(--rule) !important;
}
.stSlider [data-baseweb="slider"] > div > div > div { background: var(--sage); }
.stSlider [data-baseweb="slider"] [role="slider"] {
  background: var(--sage);
  border:     2px solid var(--sage);
  box-shadow: 0 0 0 2px var(--surface), 0 0 0 3px var(--sage);
}
.stSlider [data-testid="stTickBar"] {
  color:       var(--ink-3);
  font-family: var(--font-mono);
  font-size:   11px;
}

/* ═══════════════════════════════════════════════════════════════════════════
   RADIO + CHECKBOX
   ═══════════════════════════════════════════════════════════════════════════ */

.stRadio    [data-baseweb="radio"]    div,
.stCheckbox [data-baseweb="checkbox"] div {
  border-color: var(--rule);
  background:   var(--surface);
}
.stRadio    [data-baseweb="radio"]    [data-checked="true"],
.stCheckbox [data-baseweb="checkbox"] [data-checked="true"] {
  background:   var(--sage);
  border-color: var(--sage);
}
.stRadio    label,
.stCheckbox label { color: var(--ink) !important; }

/* ═══════════════════════════════════════════════════════════════════════════
   TOGGLE
   ═══════════════════════════════════════════════════════════════════════════ */

[data-testid="stToggle"] label { color: var(--ink); }
/* Off state track */
[data-baseweb="toggle"] > div { background: var(--rule) !important; }
/* On state track */
[data-testid="stToggle"] [aria-checked="true"] > div { background: var(--sage) !important; }

/* ═══════════════════════════════════════════════════════════════════════════
   TABS
   ═══════════════════════════════════════════════════════════════════════════ */

.stTabs [data-baseweb="tab-list"] {
  gap:           0;
  border-bottom: 1px solid var(--rule);
  background:    transparent;
}
.stTabs [data-baseweb="tab"] {
  background:     transparent;
  color:          var(--ink-2);
  font-family:    var(--font-sans);
  font-size:      13px;
  font-weight:    600;
  padding:        10px 16px;
  border:         none;
  border-bottom:  2px solid transparent;
  margin-bottom:  -1px;
  border-radius:  0;
  transition:     color .12s;
}
.stTabs [data-baseweb="tab"]:hover { color: var(--ink); }
.stTabs [aria-selected="true"]     { color: var(--sage) !important; border-bottom-color: var(--sage); }
.stTabs [aria-selected="true"] p   { color: var(--sage) !important; }
.stTabs [data-baseweb="tab-highlight"]  { display: none; }
.stTabs [data-baseweb="tab-panel"]      { background: transparent; }

/* ═══════════════════════════════════════════════════════════════════════════
   EXPANDERS
   ═══════════════════════════════════════════════════════════════════════════ */

[data-testid="stExpander"] {
  background:    var(--surface);
  border:        1px solid var(--rule);
  border-radius: 3px;
  box-shadow:    none;
}
[data-testid="stExpander"] details { background: transparent; }
[data-testid="stExpander"] summary,
[data-testid="stExpander"] summary p {
  font-weight: 600; font-size: 13px; color: var(--ink);
}
[data-testid="stExpander"] summary svg { fill: var(--ink-2); }
[data-testid="stExpander"] summary:hover,
[data-testid="stExpander"] summary:hover p { color: var(--sage); }

/* ═══════════════════════════════════════════════════════════════════════════
   METRICS
   ═══════════════════════════════════════════════════════════════════════════ */

[data-testid="stMetric"] {
  background:    var(--surface);
  border:        1px solid var(--rule);
  border-radius: 3px;
  padding:       14px 16px;
}
[data-testid="stMetricLabel"],
[data-testid="stMetricLabel"] p {
  color:           var(--ink-2);
  font-size:       11px;
  font-weight:     600;
  text-transform:  uppercase;
  letter-spacing:  0.08em;
}
[data-testid="stMetricValue"] {
  color:                   var(--ink);
  font-family:             var(--font-mono);
  font-variant-numeric:    tabular-nums;
  font-weight:             600;
  font-size:               26px;
  letter-spacing:          -0.01em;
}
[data-testid="stMetricDelta"] {
  font-family: var(--font-mono);
  font-size:   12px;
  font-weight: 500;
}

/* ═══════════════════════════════════════════════════════════════════════════
   ALERTS
   ═══════════════════════════════════════════════════════════════════════════ */

[data-testid="stAlert"] {
  border-radius: 3px;
  font-size:     13px;
  padding:       10px 14px;
}
[data-testid="stAlert"][kind="success"] {
  background: var(--tint-success); border: 1px solid var(--sage);
}
[data-testid="stAlert"][kind="info"] {
  background: var(--tint-info);    border: 1px solid var(--azure);
}
[data-testid="stAlert"][kind="warning"] {
  background: var(--tint-warn);    border: 1px solid var(--amber);
}
[data-testid="stAlert"][kind="error"] {
  background: var(--tint-error);   border: 1px solid var(--clay);
}
[data-testid="stAlert"] *,
[data-testid="stAlert"] p { color: var(--ink) !important; }

/* ═══════════════════════════════════════════════════════════════════════════
   TABLES / DATAFRAMES
   ═══════════════════════════════════════════════════════════════════════════ */

[data-testid="stDataFrame"],
[data-testid="stTable"]    { border: 1px solid var(--rule); border-radius: 3px; overflow: hidden; }
[data-testid="stTable"] table { font-family: var(--font-sans); font-size: 13px; }
[data-testid="stTable"] thead tr th {
  background:     var(--surface-2);
  color:          var(--ink-2);
  font-weight:    600;
  font-size:      11px;
  text-transform: uppercase;
  letter-spacing: 0.06em;
  border-bottom:  1px solid var(--rule);
  text-align:     left;
  padding:        8px 12px;
}
[data-testid="stTable"] tbody tr td {
  background:           var(--surface);
  color:                var(--ink);
  border-bottom:        1px solid var(--rule-soft);
  padding:              8px 12px;
  font-variant-numeric: tabular-nums;
}
/* Glide data editor (newer dataframe component) */
[data-testid="stDataFrameGlideDataEditor"] { background: var(--surface) !important; }

/* ═══════════════════════════════════════════════════════════════════════════
   PLOTLY CHART FRAME
   ═══════════════════════════════════════════════════════════════════════════ */

[data-testid="stPlotlyChart"] {
  background:    var(--surface);
  border:        1px solid var(--rule);
  border-radius: 3px;
  padding:       4px;
}
[data-testid="stPlotlyChart"] iframe { background: transparent !important; }
/* SVG axis labels, ticks, legend text */
[data-testid="stPlotlyChart"] .gtitle,
[data-testid="stPlotlyChart"] .g-xtitle  text,
[data-testid="stPlotlyChart"] .g-ytitle  text,
[data-testid="stPlotlyChart"] .xtick     text,
[data-testid="stPlotlyChart"] .ytick     text,
[data-testid="stPlotlyChart"] .legend    text,
[data-testid="stPlotlyChart"] .legendtext { fill: var(--ink) !important; color: var(--ink) !important; }

/* ═══════════════════════════════════════════════════════════════════════════
   MISC COMPONENTS
   ═══════════════════════════════════════════════════════════════════════════ */

/* Divider */
[data-testid="stDivider"], hr {
  border: none; border-top: 1px solid var(--rule); margin: 1.2rem 0;
}

/* Progress bar */
.stProgress > div > div              { background: var(--rule)  !important; }
.stProgress > div > div > div > div  { background: var(--sage)  !important; }

/* Code / pre */
code, pre {
  font-family:   var(--font-mono);
  font-size:     12px;
  background:    var(--surface-2);
  border:        1px solid var(--rule);
  border-radius: 3px;
  color:         var(--ink);
}

/* File uploader */
[data-testid="stFileUploaderDropzone"] {
  background:    var(--surface-2);
  border:        1.5px dashed var(--rule);
  border-radius: 3px;
}
[data-testid="stFileUploaderDropzone"] * { color: var(--ink-2); }

/* Toast */
[data-testid="stToast"] {
  background: var(--surface) !important;
  border:     1px solid var(--rule) !important;
}
[data-testid="stToast"] p { color: var(--ink) !important; }

/* Modal / dialog */
[data-baseweb="modal"]   { background: var(--surface) !important; }
[data-baseweb="modal"] * { color: var(--ink); }

/* ── Utility helpers ─────────────────────────────────────────────────────── */
.ap-num { font-family: var(--font-mono); font-variant-numeric: tabular-nums; }

</style>
"""


# ── JS dark-mode detector injected via components ────────────────────────────
# Must live outside _css() because st.markdown() strips <script> tags.
_DARK_DETECTOR_HTML = """
<script>
(function () {
  function apply() {
    try {
      var el = window.parent.document.querySelector('.stApp');
      if (!el) return;
      var bg = window.parent.getComputedStyle(el).backgroundColor;
      var m  = bg.match(/\\d+/g);
      if (!m || m.length < 3) return;
      var lum = (parseInt(m[0]) * 299 + parseInt(m[1]) * 587 + parseInt(m[2]) * 114) / 1000;
      window.parent.document.documentElement.setAttribute(
        'data-theme', lum < 145 ? 'dark' : 'light'
      );
    } catch (_) {}
  }
  apply();
  setInterval(apply, 800);
})();
</script>
"""


# ═══════════════════════════════════════════════════════════════════════════════
# PUBLIC API
# ═══════════════════════════════════════════════════════════════════════════════

def inject_styles() -> None:
    """
    Call once per page, after st.set_page_config().

    Injects:
      1. The CSS design system (via st.markdown — Streamlit places it in <head>).
      2. A tiny JS component that detects Streamlit's dark-mode toggle and sets
         data-theme="dark"|"light" on <html>, activating the [data-theme] CSS
         overrides. Falls back gracefully if components are unavailable.
    """
    st.markdown(_css(), unsafe_allow_html=True)
    try:
        import streamlit.components.v1 as _components
        _components.html(_DARK_DETECTOR_HTML, height=0, scrolling=False)
    except Exception:
        pass  # OS prefers-color-scheme still covers system-level dark mode


def section_heading(
    title: str,
    num:   str | None = None,
    hint:  str | None = None,
) -> None:
    """Renders a labelled section divider with optional running number and hint."""
    num_html  = (
        f'<span style="font-family:var(--font-mono);color:var(--ink-3);'
        f'font-weight:500;margin-right:10px;">{num}</span>'
        if num else ''
    )
    hint_html = (
        f'<div style="font-family:var(--font-mono);font-size:11px;color:var(--ink-3);'
        f'text-transform:uppercase;letter-spacing:0.1em;">{hint}</div>'
        if hint else '<div></div>'
    )
    st.markdown(
        f"""
        <div style="display:flex;align-items:baseline;justify-content:space-between;
                    margin:1.6rem 0 0.6rem 0;padding-bottom:0.5rem;
                    border-bottom:1px solid var(--rule);">
          <div style="font-size:13px;font-weight:700;text-transform:uppercase;
                      letter-spacing:0.14em;color:var(--ink);">
            {num_html}{title}
          </div>
          {hint_html}
        </div>
        """,
        unsafe_allow_html=True,
    )


def kpi_card(
    label:  str,
    value:  str,
    unit:   str  = "",
    accent: bool = False,
) -> None:
    """Renders a standalone KPI tile using design-system tokens."""
    top_border = "border-top:3px solid var(--sage);" if accent else ""
    st.markdown(
        f"""
        <div style="background:var(--surface);border:1px solid var(--rule);
                    border-radius:3px;padding:14px 16px;{top_border}">
          <div style="font-family:var(--font-mono);font-size:11px;font-weight:600;
                      text-transform:uppercase;letter-spacing:0.08em;
                      color:var(--ink-2);margin-bottom:6px;">{label}</div>
          <div style="font-family:var(--font-mono);font-size:26px;font-weight:600;
                      letter-spacing:-0.01em;color:var(--ink);line-height:1.1;">
            {value}
            <span style="font-size:13px;color:var(--ink-3);font-weight:400;
                         margin-left:4px;">{unit}</span>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
