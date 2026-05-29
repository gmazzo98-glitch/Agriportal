"""
Agricultural Intelligence Portal — shared visual language.

DESIGN BRIEF
------------
This is a serious modelling tool used by analysts and operators. The visual
language must be:

  - Data-first: high contrast, generous numeric type, clean tabular alignment.
  - Trustworthy: restrained palette, no decorative gradients, no rounded fluff.
  - Agricultural in tone: warm neutrals (paper / clay / linen), botanical green
    accent — not cold financial blue, not synthetic SaaS purple.
  - Quiet: chrome stays out of the way; the data is the protagonist.

PALETTE
-------
  ink           #161a16   primary text, near-black with a hint of green
  ink-2         #4a524a   secondary text
  ink-3         #7a807a   muted captions
  paper         #f4f1ea   warm off-white page background (linen)
  surface       #ffffff   card / panel — pure white for max contrast
  surface-2     #fbf9f4   secondary card (slightly warmer)
  rule          #d9d4c5   hairline borders (warm tan)
  rule-soft     #e8e3d4
  sage          #2f5d3a   primary accent — botanical, deep
  sage-hi       #3e7448   hover
  sage-tint     #e6ede4   selected / active background wash
  clay          #b85c38   destructive
  amber         #c08a2e   warning
  azure         #2c5a78   info / secondary

TYPE
----
  Inter (Google Font, free) for everything. JetBrains Mono for numerics.
  These are loaded via @import in the CSS so the page does not depend on
  the user having them installed.

USAGE
-----
    from core._styles import inject_styles, section_heading, kpi_card

    inject_styles()                       # call once after st.set_page_config
    section_heading("Inputs", "01")
    kpi_card("Payback", "4.2", "years")
"""

import streamlit as st


TOKENS = {
    "ink":        "#161a16",
    "ink_2":      "#4a524a",
    "ink_3":      "#7a807a",
    "paper":      "#f4f1ea",
    "surface":    "#ffffff",
    "surface_2":  "#fbf9f4",
    "rule":       "#d9d4c5",
    "rule_soft":  "#e8e3d4",
    "sage":       "#2f5d3a",
    "sage_hi":    "#3e7448",
    "sage_tint":  "#e6ede4",
    "clay":       "#b85c38",
    "amber":      "#c08a2e",
    "azure":      "#2c5a78",
    "mod_vf":     "#3b3b52",
    "mod_gh":     "#2f5d3a",
    "mod_aqd":    "#2c5a78",
    "mod_aqc":    "#1f4d39",
    "font_sans":  "'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif",
    "font_mono":  "'JetBrains Mono', ui-monospace, SFMono-Regular, Menlo, monospace",
}


def _css() -> str:
    t = TOKENS
    return f"""
    <style id="agriportal-styles">
      @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500;600&display=swap');

      :root {{
        --ink: {t['ink']}; --ink-2: {t['ink_2']}; --ink-3: {t['ink_3']};
        --paper: {t['paper']}; --surface: {t['surface']}; --surface-2: {t['surface_2']};
        --rule: {t['rule']}; --rule-soft: {t['rule_soft']};
        --sage: {t['sage']}; --sage-hi: {t['sage_hi']}; --sage-tint: {t['sage_tint']};
        --clay: {t['clay']}; --amber: {t['amber']}; --azure: {t['azure']};
        --font-sans: {t['font_sans']}; --font-mono: {t['font_mono']};
      }}

      /* ── Shell ────────────────────────────────────────────────────────── */
      html, body, .stApp {{
        background: var(--paper);
        color: var(--ink);
        font-family: var(--font-sans);
        -webkit-font-smoothing: antialiased;
      }}
      .block-container {{ padding-top: 1.4rem; padding-bottom: 3rem; max-width: 1380px; }}
      header[data-testid="stHeader"] {{ background: transparent; }}
      #MainMenu, footer {{ visibility: hidden; }}

      /* All text inherits ink colour by default — readable everywhere. */
      .stApp, .stApp p, .stApp span, .stApp label, .stApp div {{ color: var(--ink); }}

      /* ── Typography ───────────────────────────────────────────────────── */
      .stMarkdown h1 {{ font-size: 28px; font-weight: 700; letter-spacing: -0.02em; margin: 0 0 .4rem; color: var(--ink); }}
      .stMarkdown h2 {{ font-size: 20px; font-weight: 700; letter-spacing: -0.01em; margin: 1.4rem 0 .5rem; color: var(--ink); }}
      .stMarkdown h3 {{ font-size: 15px; font-weight: 700; margin: 1.1rem 0 .4rem; color: var(--ink); }}
      .stMarkdown h4 {{ font-size: 13px; font-weight: 600; margin: .9rem 0 .3rem; color: var(--ink-2); text-transform: uppercase; letter-spacing: 0.08em; }}
      .stMarkdown p, .stMarkdown li {{ font-size: 14px; line-height: 1.55; color: var(--ink); }}

      [data-testid="stCaptionContainer"], .stCaption {{
        color: var(--ink-3) !important; font-size: 12px;
      }}

      /* ── Sidebar — distinct dark surface, the "control panel" ────────── */
      [data-testid="stSidebar"] {{
        background: #1e221e !important;
        border-right: 1px solid #2a2f2a;
      }}
      [data-testid="stSidebar"] *, [data-testid="stSidebar"] p,
      [data-testid="stSidebar"] span, [data-testid="stSidebar"] label,
      [data-testid="stSidebar"] div, [data-testid="stSidebar"] li {{
        color: #e8e6df;
      }}
      [data-testid="stSidebar"] h1, [data-testid="stSidebar"] h2,
      [data-testid="stSidebar"] h3, [data-testid="stSidebar"] h4 {{
        color: #ffffff !important;
      }}
      [data-testid="stSidebar"] [data-testid="stMarkdownContainer"] strong {{
        color: #ffffff;
      }}
      [data-testid="stSidebar"] [data-testid="stCaptionContainer"] {{
        color: #9ba39a !important;
      }}
      [data-testid="stSidebar"] hr {{ border-color: #2a2f2a; }}
      /* Sidebar widget labels */
      [data-testid="stSidebar"] [data-testid="stWidgetLabel"] p,
      [data-testid="stSidebar"] [data-testid="stWidgetLabel"] {{
        color: #c2c8be !important; font-size: 12px; font-weight: 500;
      }}
      /* Sidebar inputs — dark fields */
      [data-testid="stSidebar"] input,
      [data-testid="stSidebar"] textarea,
      [data-testid="stSidebar"] [data-baseweb="select"] > div {{
        background: #2a2f2a !important;
        color: #ffffff !important;
        border: 1px solid #3a4039 !important;
      }}
      [data-testid="stSidebar"] [data-baseweb="select"] > div * {{ color: #ffffff !important; }}
      [data-testid="stSidebar"] input:focus,
      [data-testid="stSidebar"] [data-baseweb="select"]:focus-within > div {{
        border-color: var(--sage-hi) !important;
      }}

      /* ── Buttons (main canvas) ───────────────────────────────────────── */
      .stButton > button, .stDownloadButton > button, .stFormSubmitButton > button {{
        background: var(--surface);
        color: var(--ink);
        border: 1px solid var(--ink);
        border-radius: 2px;
        padding: 8px 14px;
        font-family: var(--font-sans);
        font-size: 13px;
        font-weight: 600;
        letter-spacing: 0.01em;
        box-shadow: none;
        transition: all .12s ease;
      }}
      .stButton > button p, .stButton > button div, .stButton > button span,
      .stDownloadButton > button p, .stDownloadButton > button div, .stDownloadButton > button span,
      .stFormSubmitButton > button p, .stFormSubmitButton > button div, .stFormSubmitButton > button span {{
        color: var(--ink); margin: 0;
      }}
      .stButton > button:hover, .stDownloadButton > button:hover, .stFormSubmitButton > button:hover {{
        background: var(--ink); color: var(--surface);
      }}
      .stButton > button:hover p, .stButton > button:hover div, .stButton > button:hover span,
      .stDownloadButton > button:hover p, .stDownloadButton > button:hover div, .stDownloadButton > button:hover span,
      .stFormSubmitButton > button:hover p, .stFormSubmitButton > button:hover div, .stFormSubmitButton > button:hover span {{
        color: var(--surface);
      }}
      .stButton > button[kind="primary"], .stFormSubmitButton > button[kind="primary"] {{
        background: var(--sage); color: #ffffff; border-color: var(--sage);
      }}
      .stButton > button[kind="primary"] p, .stButton > button[kind="primary"] div, .stButton > button[kind="primary"] span,
      .stFormSubmitButton > button[kind="primary"] p, .stFormSubmitButton > button[kind="primary"] div, .stFormSubmitButton > button[kind="primary"] span {{
        color: #ffffff;
      }}
      .stButton > button[kind="primary"]:hover, .stFormSubmitButton > button[kind="primary"]:hover {{
        background: var(--sage-hi); border-color: var(--sage-hi);
      }}
      .stButton > button:disabled {{
        background: var(--surface-2); color: var(--ink-3); border-color: var(--rule);
      }}
      .stButton > button:disabled p, .stButton > button:disabled span, .stButton > button:disabled div {{
        color: var(--ink-3);
      }}

      /* ── Sidebar buttons — light on dark ─────────────────────────────── */
      [data-testid="stSidebar"] .stButton > button {{
        background: #2a2f2a; color: #e8e6df; border: 1px solid #3a4039;
      }}
      [data-testid="stSidebar"] .stButton > button p,
      [data-testid="stSidebar"] .stButton > button span,
      [data-testid="stSidebar"] .stButton > button div {{ color: #e8e6df; }}
      [data-testid="stSidebar"] .stButton > button:hover {{
        background: var(--sage); border-color: var(--sage); color: #ffffff;
      }}
      [data-testid="stSidebar"] .stButton > button:hover p,
      [data-testid="stSidebar"] .stButton > button:hover span,
      [data-testid="stSidebar"] .stButton > button:hover div {{ color: #ffffff; }}

      /* ── Page links ──────────────────────────────────────────────────── */
      a[data-testid="stPageLink-NavLink"] {{
        background: var(--surface); border: 1px solid var(--ink);
        border-radius: 2px; padding: 8px 14px; transition: all .12s;
      }}
      a[data-testid="stPageLink-NavLink"] p {{
        color: var(--ink); font-weight: 600; font-size: 13px; margin: 0;
      }}
      a[data-testid="stPageLink-NavLink"]:hover {{ background: var(--ink); }}
      a[data-testid="stPageLink-NavLink"]:hover p {{ color: var(--surface); }}

      /* ── Inputs (main canvas) ────────────────────────────────────────── */
      .stTextInput input, .stNumberInput input, .stDateInput input,
      .stTextArea textarea {{
        background: var(--surface); color: var(--ink);
        border: 1px solid var(--rule); border-radius: 2px;
        font-family: var(--font-sans); font-size: 13px;
        padding: 8px 10px; box-shadow: none;
      }}
      .stTextInput input:focus, .stNumberInput input:focus,
      .stDateInput input:focus, .stTextArea textarea:focus {{
        border-color: var(--sage); outline: none;
        box-shadow: 0 0 0 2px var(--sage-tint);
      }}
      [data-testid="stWidgetLabel"] p,
      .stTextInput label, .stNumberInput label, .stSelectbox label,
      .stMultiSelect label, .stSlider label, .stRadio label,
      .stCheckbox label, .stDateInput label, .stTextArea label {{
        color: var(--ink-2); font-size: 12px; font-weight: 600;
        text-transform: none; letter-spacing: 0;
      }}

      /* Selectbox / multiselect */
      .stSelectbox div[data-baseweb="select"] > div,
      .stMultiSelect div[data-baseweb="select"] > div {{
        background: var(--surface); border: 1px solid var(--rule);
        border-radius: 2px; min-height: 38px;
      }}
      .stSelectbox div[data-baseweb="select"] > div *,
      .stMultiSelect div[data-baseweb="select"] > div * {{
        color: var(--ink); font-size: 13px;
      }}
      .stSelectbox div[data-baseweb="select"]:focus-within > div,
      .stMultiSelect div[data-baseweb="select"]:focus-within > div {{
        border-color: var(--sage); box-shadow: 0 0 0 2px var(--sage-tint);
      }}

      /* Slider — sage track + thumb */
      .stSlider [data-baseweb="slider"] [role="slider"] {{
        background: var(--sage); border: 2px solid var(--sage);
        box-shadow: 0 0 0 2px var(--surface), 0 0 0 3px var(--sage);
      }}
      .stSlider [data-baseweb="slider"] > div > div > div {{ background: var(--sage); }}
      .stSlider [data-testid="stTickBar"] {{ color: var(--ink-3); font-family: var(--font-mono); font-size: 11px; }}

      /* Radio + checkbox */
      .stRadio [data-baseweb="radio"] [data-checked="true"],
      .stCheckbox [data-baseweb="checkbox"] [data-checked="true"] {{
        background: var(--sage); border-color: var(--sage);
      }}

      /* ── Tabs ────────────────────────────────────────────────────────── */
      .stTabs [data-baseweb="tab-list"] {{
        gap: 0; border-bottom: 1px solid var(--rule); background: transparent;
      }}
      .stTabs [data-baseweb="tab"] {{
        background: transparent; color: var(--ink-2);
        font-family: var(--font-sans); font-size: 13px; font-weight: 600;
        padding: 10px 16px; border: none;
        border-bottom: 2px solid transparent; margin-bottom: -1px;
        border-radius: 0;
      }}
      .stTabs [data-baseweb="tab"]:hover {{ color: var(--ink); }}
      .stTabs [aria-selected="true"] {{
        color: var(--sage); border-bottom-color: var(--sage);
      }}
      .stTabs [data-baseweb="tab-highlight"] {{ display: none; }}

      /* ── Expanders ───────────────────────────────────────────────────── */
      [data-testid="stExpander"] {{
        background: var(--surface); border: 1px solid var(--rule);
        border-radius: 2px; box-shadow: none;
      }}
      [data-testid="stExpander"] summary, [data-testid="stExpander"] summary p {{
        font-weight: 600; font-size: 13px; color: var(--ink);
      }}
      [data-testid="stExpander"] summary:hover, [data-testid="stExpander"] summary:hover p {{
        color: var(--sage);
      }}

      /* ── Metrics — the showpiece. Big, mono, tabular numerics. ──────── */
      [data-testid="stMetric"] {{
        background: var(--surface); border: 1px solid var(--rule);
        border-radius: 2px; padding: 14px 16px;
      }}
      [data-testid="stMetricLabel"], [data-testid="stMetricLabel"] p {{
        color: var(--ink-2); font-size: 11px; font-weight: 600;
        text-transform: uppercase; letter-spacing: 0.08em;
      }}
      [data-testid="stMetricValue"] {{
        color: var(--ink); font-family: var(--font-mono);
        font-variant-numeric: tabular-nums;
        font-weight: 600; font-size: 26px; letter-spacing: -0.01em;
      }}
      [data-testid="stMetricDelta"] {{
        font-family: var(--font-mono); font-size: 12px; font-weight: 500;
      }}

      /* ── Alerts — solid pastel fills, dark text ─────────────────────── */
      [data-testid="stAlert"] {{ border-radius: 2px; font-size: 13px; padding: 10px 14px; }}
      [data-testid="stAlert"][kind="success"] {{ background: var(--sage-tint); border: 1px solid var(--sage); color: var(--ink); }}
      [data-testid="stAlert"][kind="info"]    {{ background: #e6edf2; border: 1px solid var(--azure); color: var(--ink); }}
      [data-testid="stAlert"][kind="warning"] {{ background: #f5ecd6; border: 1px solid var(--amber); color: var(--ink); }}
      [data-testid="stAlert"][kind="error"]   {{ background: #f3dfd2; border: 1px solid var(--clay); color: var(--ink); }}
      [data-testid="stAlert"] *, [data-testid="stAlert"] p {{ color: var(--ink) !important; }}

      /* ── Tables / dataframes ────────────────────────────────────────── */
      [data-testid="stDataFrame"], [data-testid="stTable"] {{
        border: 1px solid var(--rule); border-radius: 2px; overflow: hidden;
      }}
      [data-testid="stTable"] table {{ font-family: var(--font-sans); font-size: 13px; }}
      [data-testid="stTable"] thead tr th {{
        background: var(--surface-2); color: var(--ink-2);
        font-weight: 600; font-size: 11px;
        text-transform: uppercase; letter-spacing: 0.06em;
        border-bottom: 1px solid var(--rule);
        text-align: left; padding: 8px 12px;
      }}
      [data-testid="stTable"] tbody tr td {{
        background: var(--surface); color: var(--ink);
        border-bottom: 1px solid var(--rule-soft);
        padding: 8px 12px; font-variant-numeric: tabular-nums;
      }}

      /* ── Plotly chart frame ─────────────────────────────────────────── */
      [data-testid="stPlotlyChart"] {{
        background: var(--surface); border: 1px solid var(--rule);
        border-radius: 2px; padding: 4px;
      }}
      /* Force Plotly iframe content to white background so transparent
         plot/paper_bgcolor resolves correctly. */
      [data-testid="stPlotlyChart"] iframe {{
        background: #ffffff !important;
      }}
      /* Plotly SVG text — axis labels, tick text, legend — must be dark. */
      [data-testid="stPlotlyChart"] .gtitle,
      [data-testid="stPlotlyChart"] .g-xtitle text,
      [data-testid="stPlotlyChart"] .g-ytitle text,
      [data-testid="stPlotlyChart"] .xtick text,
      [data-testid="stPlotlyChart"] .ytick text,
      [data-testid="stPlotlyChart"] .legend text,
      [data-testid="stPlotlyChart"] .legendtext {{
        fill: #161a16 !important;
        color: #161a16 !important;
      }}

      /* ── Divider ────────────────────────────────────────────────────── */
      [data-testid="stDivider"], hr {{
        border: none; border-top: 1px solid var(--rule); margin: 1.2rem 0;
      }}

      /* ── Progress ───────────────────────────────────────────────────── */
      .stProgress > div > div > div > div {{ background: var(--sage); }}

      /* ── Code ───────────────────────────────────────────────────────── */
      code, pre {{
        font-family: var(--font-mono); font-size: 12px;
        background: var(--surface-2); border: 1px solid var(--rule);
        border-radius: 2px; color: var(--ink);
      }}

      /* ── Helpers ────────────────────────────────────────────────────── */
      .ap-num {{ font-family: var(--font-mono); font-variant-numeric: tabular-nums; }}
    </style>
    """


def inject_styles() -> None:
    st.markdown(_css(), unsafe_allow_html=True)


def inject_home_styles() -> None:
    st.markdown(
        """
        <style>
          :root {
            --bg:        #fafaf7;
            --surface:   #ffffff;
            --ink-1:     #1c1f1a;
            --ink-2:     #5a6258;
            --ink-3:     #8b9085;
            --rule:      #e6e4dc;
            --rule-soft: #f0eee6;
            --accent:    #3a6b40;
            --accent-d:  #2a5230;
            --accent-soft: #eaf0e9;
            --warn:      #a64545;
            --font:      -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
          }

          .block-container {
            padding-top: 1.2rem;
            padding-bottom: 3rem;
            max-width: 1400px;
          }
          header[data-testid="stHeader"] { background: transparent; }
          #MainMenu, footer { visibility: hidden; }

          html, body, [class*="css"], .stApp {
            font-family: var(--font);
            color: var(--ink-1);
            background-color: var(--bg);
          }

          * { -webkit-font-smoothing: antialiased; }

          /* ── Top bar ────────────────────────────────────────────────────── */
          .topbar {
            display: flex;
            align-items: center;
            justify-content: space-between;
            padding: 8px 0 14px 0;
            border-bottom: 1px solid var(--rule);
            margin-bottom: 22px;
          }
          .topbar .brand {
            display: flex; align-items: center; gap: 10px;
            font-size: 14px; font-weight: 600; color: var(--ink-1);
            letter-spacing: -0.005em;
          }
          .topbar .brand .mark {
            width: 22px; height: 22px;
            border-radius: 4px;
            background: var(--accent);
            display: inline-flex; align-items: center; justify-content: center;
            color: #fff; font-size: 12px; font-weight: 700;
          }
          .topbar .brand .sub {
            color: var(--ink-3); font-weight: 400; font-size: 13px;
            margin-left: 8px; padding-left: 10px; border-left: 1px solid var(--rule);
          }
          .topbar .session-pill {
            display: inline-flex; align-items: center; gap: 8px;
            font-size: 12px; color: var(--ink-2);
            background: var(--surface);
            border: 1px solid var(--rule);
            padding: 5px 10px;
            border-radius: 999px;
          }
          .topbar .session-pill .dot {
            width: 6px; height: 6px; border-radius: 50%;
            background: var(--accent);
          }
          .topbar .session-pill.empty .dot { background: var(--ink-3); }
          .topbar .session-pill .farm { color: var(--ink-1); font-weight: 600; }

          /* ── Page heading ─────────────────────────────────────────────── */
          .pg-head {
            margin-bottom: 18px;
          }
          .pg-head h1 {
            font-size: 26px;
            font-weight: 600;
            letter-spacing: -0.015em;
            margin: 0 0 4px 0;
            color: var(--ink-1);
          }
          .pg-head p {
            font-size: 14px;
            color: var(--ink-2);
            margin: 0;
          }

          /* ── Two-column workspace ─────────────────────────────────────── */
          /* Streamlit columns drive layout; we just style content inside. */

          /* Finder (left column) */
          .finder-head {
            display: flex; align-items: baseline; justify-content: space-between;
            margin-bottom: 8px;
          }
          .finder-head .h {
            font-size: 11px;
            font-weight: 600;
            letter-spacing: 0.12em;
            text-transform: uppercase;
            color: var(--ink-3);
          }
          .finder-head .count {
            font-size: 11px;
            color: var(--ink-3);
            font-variant-numeric: tabular-nums;
          }

          .finder-list {
            background: var(--surface);
            border: 1px solid var(--rule);
            border-radius: 6px;
            overflow: hidden;
          }
          .finder-row {
            display: grid;
            grid-template-columns: 28px 1fr auto;
            align-items: center;
            gap: 12px;
            padding: 12px 14px;
            border-bottom: 1px solid var(--rule-soft);
            cursor: pointer;
            transition: background .12s ease;
            position: relative;
          }
          .finder-row:last-child { border-bottom: none; }
          .finder-row:hover { background: #f7f6f1; }
          .finder-row.selected {
            background: var(--accent-soft);
          }
          .finder-row.selected::before {
            content: "";
            position: absolute; left: 0; top: 0; bottom: 0;
            width: 3px;
            background: var(--accent);
          }
          .finder-row .mono {
            font-size: 10px;
            font-weight: 700;
            letter-spacing: 0.04em;
            color: var(--ink-2);
            background: var(--rule-soft);
            border-radius: 3px;
            padding: 3px 0;
            text-align: center;
            font-variant-numeric: tabular-nums;
          }
          .finder-row.selected .mono {
            background: var(--accent);
            color: #fff;
          }
          .finder-row .name {
            font-size: 14px;
            font-weight: 500;
            color: var(--ink-1);
            line-height: 1.25;
            min-width: 0;
            overflow: hidden;
            text-overflow: ellipsis;
            white-space: nowrap;
          }
          .finder-row .name .country {
            color: var(--ink-3);
            font-weight: 400;
            font-size: 12px;
            margin-left: 6px;
          }
          .finder-row .footprint {
            font-size: 12px;
            color: var(--ink-2);
            font-variant-numeric: tabular-nums;
            white-space: nowrap;
          }

          .finder-empty {
            background: var(--surface);
            border: 1px solid var(--rule);
            border-radius: 6px;
            padding: 22px 18px;
            text-align: center;
            font-size: 13px;
            color: var(--ink-2);
          }

          /* Right panel */
          .panel {
            background: var(--surface);
            border: 1px solid var(--rule);
            border-radius: 6px;
            padding: 24px 26px;
          }
          .panel-head {
            display: flex; align-items: flex-start; justify-content: space-between;
            gap: 16px;
            padding-bottom: 18px;
            border-bottom: 1px solid var(--rule);
            margin-bottom: 20px;
          }
          .panel-head .farm-name {
            font-size: 22px;
            font-weight: 600;
            letter-spacing: -0.01em;
            color: var(--ink-1);
            margin: 0 0 6px 0;
          }
          .panel-head .farm-meta {
            font-size: 13px;
            color: var(--ink-2);
            line-height: 1.5;
          }
          .panel-head .farm-meta .mod {
            color: var(--accent);
            font-weight: 600;
          }
          .panel-head .farm-meta .dot {
            display: inline-block;
            width: 3px; height: 3px;
            background: var(--ink-3);
            border-radius: 50%;
            margin: 0 8px;
            vertical-align: middle;
          }

          /* Activity timeline */
          .activity {
            margin-bottom: 22px;
          }
          .activity .h {
            font-size: 11px;
            font-weight: 600;
            letter-spacing: 0.12em;
            text-transform: uppercase;
            color: var(--ink-3);
            margin-bottom: 12px;
          }
          .activity .timeline {
            display: grid;
            grid-template-columns: repeat(3, 1fr);
            gap: 14px;
          }
          .activity .stat {
            padding: 12px 14px;
            background: var(--bg);
            border: 1px solid var(--rule-soft);
            border-radius: 5px;
          }
          .activity .stat .lbl {
            font-size: 11px;
            color: var(--ink-3);
            text-transform: uppercase;
            letter-spacing: 0.08em;
            margin-bottom: 6px;
          }
          .activity .stat .val {
            font-size: 16px;
            font-weight: 600;
            color: var(--ink-1);
            line-height: 1.2;
            font-variant-numeric: tabular-nums;
          }
          .activity .stat .val.muted { color: var(--ink-3); font-weight: 500; }
          .activity .stat .sub {
            font-size: 11px;
            color: var(--ink-3);
            margin-top: 2px;
          }

          /* Next-step destination cards */
          .destinations .h {
            font-size: 11px;
            font-weight: 600;
            letter-spacing: 0.12em;
            text-transform: uppercase;
            color: var(--ink-3);
            margin-bottom: 12px;
          }
          .dest-card {
            background: var(--surface);
            border: 1px solid var(--rule);
            border-radius: 6px;
            padding: 16px 18px;
            margin-bottom: 10px;
            transition: all .15s ease;
          }
          .dest-card:hover {
            border-color: var(--accent);
            background: #fcfcfa;
          }
          .dest-card .lead {
            font-size: 14px;
            font-weight: 600;
            color: var(--ink-1);
            margin-bottom: 4px;
            letter-spacing: -0.005em;
          }
          .dest-card .desc {
            font-size: 13px;
            color: var(--ink-2);
            margin-bottom: 10px;
            line-height: 1.45;
          }

          /* Empty right panel */
          .panel-empty .h2 {
            font-size: 18px;
            font-weight: 600;
            color: var(--ink-1);
            margin: 0 0 6px 0;
          }
          .panel-empty .sub {
            font-size: 14px;
            color: var(--ink-2);
            margin-bottom: 22px;
            line-height: 1.5;
          }
          .panel-empty .what-row {
            display: flex; gap: 14px;
            padding: 14px 0;
            border-top: 1px solid var(--rule-soft);
          }
          .panel-empty .what-row:last-child { border-bottom: 1px solid var(--rule-soft); }
          .panel-empty .what-row .num {
            font-size: 13px;
            color: var(--ink-3);
            font-weight: 600;
            font-variant-numeric: tabular-nums;
            min-width: 28px;
            padding-top: 1px;
          }
          .panel-empty .what-row .body {
            flex: 1;
          }
          .panel-empty .what-row .body strong {
            font-size: 14px;
            color: var(--ink-1);
            font-weight: 600;
            display: block;
            margin-bottom: 2px;
          }
          .panel-empty .what-row .body span {
            font-size: 13px;
            color: var(--ink-2);
            line-height: 1.5;
          }

          /* First-time onboarding (no farms at all) */
          .onboard {
            background: var(--surface);
            border: 1px solid var(--rule);
            border-radius: 8px;
            padding: 56px 48px;
            text-align: center;
          }
          .onboard .glyph {
            width: 56px; height: 56px;
            border-radius: 50%;
            background: var(--accent-soft);
            color: var(--accent);
            display: inline-flex; align-items: center; justify-content: center;
            font-size: 24px;
            margin-bottom: 18px;
          }
          .onboard h2 {
            font-size: 22px;
            font-weight: 600;
            color: var(--ink-1);
            margin: 0 0 8px 0;
          }
          .onboard p {
            font-size: 14px;
            color: var(--ink-2);
            margin: 0 auto 22px auto;
            max-width: 480px;
            line-height: 1.55;
          }

          /* ── Buttons ──────────────────────────────────────────────────── */
          .stButton { width: 100% !important; }
          .stButton > button {
            width: 100% !important;
            min-height: 36px !important;
            height: 36px !important;
            font-family: var(--font) !important;
            font-size: 13px !important;
            font-weight: 500 !important;
            padding: 0 14px !important;
            border-radius: 5px !important;
            border: 1px solid var(--rule) !important;
            background-color: var(--surface) !important;
            color: var(--ink-1) !important;
            transition: all .15s ease !important;
            box-shadow: none !important;
          }
          .stButton > button p,
          .stButton > button div,
          .stButton > button span {
            color: var(--ink-1) !important;
            font-size: 13px !important;
            font-weight: 500 !important;
            margin: 0 !important;
          }
          .stButton > button:hover:not(:disabled) {
            border-color: var(--accent) !important;
            color: var(--accent) !important;
          }
          .stButton > button:hover:not(:disabled) p,
          .stButton > button:hover:not(:disabled) div,
          .stButton > button:hover:not(:disabled) span {
            color: var(--accent) !important;
          }
          .stButton > button:disabled,
          .stButton > button[disabled] {
            background-color: var(--bg) !important;
            opacity: 1 !important;
            cursor: default !important;
          }
          .stButton > button:disabled p,
          .stButton > button:disabled div,
          .stButton > button:disabled span {
            color: var(--ink-3) !important;
          }
          .stButton > button[kind="primary"] {
            background-color: var(--accent) !important;
            border-color: var(--accent) !important;
          }
          .stButton > button[kind="primary"] p,
          .stButton > button[kind="primary"] div,
          .stButton > button[kind="primary"] span {
            color: #fff !important;
          }
          .stButton > button[kind="primary"]:hover:not(:disabled) {
            background-color: var(--accent-d) !important;
            border-color: var(--accent-d) !important;
          }
          .stButton > button[kind="primary"]:hover:not(:disabled) p,
          .stButton > button[kind="primary"]:hover:not(:disabled) div,
          .stButton > button[kind="primary"]:hover:not(:disabled) span {
            color: #fff !important;
          }

          /* danger button (delete) */
          .danger-btn .stButton > button {
            border-color: var(--rule) !important;
          }
          .danger-btn .stButton > button p,
          .danger-btn .stButton > button div,
          .danger-btn .stButton > button span { color: var(--ink-3) !important; }
          .danger-btn .stButton > button:hover:not(:disabled) {
            border-color: var(--warn) !important;
            color: var(--warn) !important;
          }
          .danger-btn .stButton > button:hover:not(:disabled) p,
          .danger-btn .stButton > button:hover:not(:disabled) div,
          .danger-btn .stButton > button:hover:not(:disabled) span {
            color: var(--warn) !important;
          }

          /* page-link */
          a[data-testid="stPageLink-NavLink"] {
            background: var(--surface) !important;
            border: 1px solid var(--rule) !important;
            border-radius: 5px !important;
            padding: 8px 14px !important;
            transition: all .15s ease;
          }
          a[data-testid="stPageLink-NavLink"] * {
            color: var(--ink-1) !important;
            font-family: var(--font) !important;
            font-weight: 500 !important;
            font-size: 13px !important;
          }
          a[data-testid="stPageLink-NavLink"]:hover {
            border-color: var(--accent) !important;
          }
          a[data-testid="stPageLink-NavLink"]:hover * { color: var(--accent) !important; }

          .primary-link a[data-testid="stPageLink-NavLink"] {
            background: var(--accent) !important;
            border-color: var(--accent) !important;
          }
          .primary-link a[data-testid="stPageLink-NavLink"] * { color: #fff !important; }
          .primary-link a[data-testid="stPageLink-NavLink"]:hover {
            background: var(--accent-d) !important;
            border-color: var(--accent-d) !important;
          }
          .primary-link a[data-testid="stPageLink-NavLink"]:hover * { color: #fff !important; }

          /* search input */
          div[data-testid="stTextInput"] input {
            font-family: var(--font) !important;
            font-size: 13px !important;
            background: var(--surface) !important;
            border: 1px solid var(--rule) !important;
            border-radius: 5px !important;
            color: var(--ink-1) !important;
            padding: 8px 12px !important;
          }
          div[data-testid="stTextInput"] input:focus {
            border-color: var(--accent) !important;
            box-shadow: 0 0 0 2px var(--accent-soft) !important;
          }
          div[data-testid="stTextInput"] label { display: none !important; }

          div[data-testid="stHorizontalBlock"] { align-items: stretch !important; }

          /* ── Clickable finder rows (Streamlit buttons styled as rows) ──── */
          .finder-buttons {
            background: var(--surface);
            border: 1px solid var(--rule);
            border-radius: 6px;
            overflow: hidden;
          }
          .finder-buttons .row-btn .stButton > button,
          .finder-buttons .row-btn.selected-row .stButton > button {
            height: auto !important;
            min-height: 48px !important;
            padding: 12px 14px !important;
            border: none !important;
            border-bottom: 1px solid var(--rule-soft) !important;
            border-radius: 0 !important;
            background: var(--surface) !important;
            text-align: left !important;
            justify-content: flex-start !important;
            font-size: 13px !important;
            font-weight: 500 !important;
            color: var(--ink-1) !important;
          }
          .finder-buttons .row-btn .stButton > button p,
          .finder-buttons .row-btn .stButton > button div,
          .finder-buttons .row-btn .stButton > button span {
            text-align: left !important;
            font-size: 13px !important;
            font-weight: 500 !important;
            color: var(--ink-1) !important;
            white-space: normal !important;
            word-break: break-word !important;
          }
          .finder-buttons .row-btn .stButton > button:hover:not(:disabled) {
            background: #f7f6f1 !important;
            border-color: var(--rule-soft) !important;
          }
          .finder-buttons .row-btn .stButton > button:hover:not(:disabled) p,
          .finder-buttons .row-btn .stButton > button:hover:not(:disabled) div,
          .finder-buttons .row-btn .stButton > button:hover:not(:disabled) span {
            color: var(--ink-1) !important;
          }
          .finder-buttons .row-btn.selected-row .stButton > button {
            background: var(--accent-soft) !important;
            box-shadow: inset 3px 0 0 0 var(--accent) !important;
          }
          .finder-buttons .row-btn.selected-row .stButton > button p,
          .finder-buttons .row-btn.selected-row .stButton > button div,
          .finder-buttons .row-btn.selected-row .stButton > button span {
            color: var(--ink-1) !important;
            font-weight: 600 !important;
          }

          /* Roster summary */
          .roster-summary {
            margin-top: 14px;
            background: var(--surface);
            border: 1px solid var(--rule);
            border-radius: 6px;
            padding: 14px 16px;
          }
          .roster-summary .rs-h {
            font-size: 11px; font-weight: 600;
            letter-spacing: 0.12em; text-transform: uppercase;
            color: var(--ink-3); margin-bottom: 10px;
          }
          .roster-summary .rs-stats {
            display: grid; grid-template-columns: 1fr 1fr; gap: 10px;
            margin-bottom: 12px;
          }
          .roster-summary .rs-stat .lbl {
            font-size: 11px; color: var(--ink-3);
            text-transform: uppercase; letter-spacing: 0.06em;
            margin-bottom: 2px;
          }
          .roster-summary .rs-stat .val {
            font-size: 15px; font-weight: 600; color: var(--ink-1);
            font-variant-numeric: tabular-nums;
          }
          .roster-summary .rs-chips {
            display: flex; flex-wrap: wrap; gap: 6px;
            padding-top: 10px;
            border-top: 1px solid var(--rule-soft);
          }
          .roster-summary .chip {
            font-size: 11px;
            color: var(--ink-2);
            background: var(--bg);
            border: 1px solid var(--rule);
            padding: 3px 8px;
            border-radius: 999px;
          }
          .roster-summary .chip b {
            color: var(--accent);
            font-weight: 700;
            margin-right: 4px;
          }
        </style>
        """,
        unsafe_allow_html=True,
    )

def section_heading(title: str, num: str | None = None, hint: str | None = None) -> None:
    num_html = (
        f'<span style="font-family:var(--font-mono);color:var(--ink-3);'
        f'font-weight:500;margin-right:10px;">{num}</span>' if num else ''
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
