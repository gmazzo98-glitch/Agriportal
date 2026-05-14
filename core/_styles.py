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
