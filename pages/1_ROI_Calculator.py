import streamlit as st
import plotly.graph_objects as go
import pandas as pd
import sys
import os
import copy
import io
from datetime import date
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import cm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.platypus import PageBreak
from reportlab.lib.utils import ImageReader
import plotly.io as pio

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from core.roi_calculate import calculate
from core.greenhouse_calculate import calculate_greenhouse
from core.greenhouse_data_tables import GREENHOUSE_CROPS, POLYTUNNEL_CROPS, FISH_SPECIES, CROP_NUTRIENT_DEMAND, COUPLING_PARAMS
from core.aquaponics_calculate import calculate_aquaponics, calculate_fish, COUNTRY_AMBIENT_TEMP
from core.data_tables import COUNTRIES, CROPS, LIGHTS
from core.climate import fetch_climate_profile, compute_natural_dli_fraction
from core._styles import inject_styles
from core.auth import require_login, current_user
from core.farm_context import render_farm_context_sidebar, load_farm, clear_farm, MODALITY_RADIO
import json
from supabase import create_client, Client

@st.cache_resource
def get_supabase() -> Client:
    return create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])

supabase = get_supabase()

st.set_page_config(page_title="ROI Calculator", page_icon="📊", layout="wide")
inject_styles()
require_login()

def _render_farm_selector_sidebar():
    """
    Persistent farm selector rendered at the top of the sidebar on every modality.
    Sets st.session_state["active_farm"] and triggers st.rerun() on load.
    Returns the active farm dict or None.
    """
    
# ═══════════════════════════════════════════════════════════════
# UNIFIED PDF ENGINE
# ═══════════════════════════════════════════════════════════════
# ─────────────────────────────────────────────────────────────────────────────
# UNIFIED PDF ENGINE — all modalities
# Design system: ink-on-paper, sage accent, JetBrains Mono numerics
# ─────────────────────────────────────────────────────────────────────────────

def _build_feasibility_pdf(result_dict: dict, inputs_dict: dict, modality: str,
                            farm_name: str = "") -> bytes:
    """
    Single entry point for all modalities:
      modality = "vf" | "gh" | "pt" | "aqd" | "aqc"
    """
    import io, hashlib
    from datetime import date as _date
    from reportlab.platypus import (
        BaseDocTemplate, PageTemplate, Frame, Paragraph, Spacer,
        Table, TableStyle, HRFlowable, PageBreak, KeepTogether,
        Image as RLImage,
    )
    from reportlab.lib.pagesizes import A4
    from reportlab.lib import colors
    from reportlab.lib.units import mm, cm
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.lib.enums import TA_LEFT, TA_RIGHT, TA_CENTER
    from reportlab.graphics.shapes import Drawing, Rect, Line
    from reportlab.graphics import renderPDF

    # ── Design tokens ──────────────────────────────────────────────────────────
    INK       = colors.HexColor("#161a16")
    INK_2     = colors.HexColor("#4a524a")
    INK_3     = colors.HexColor("#7a807a")
    INK_4     = colors.HexColor("#aeb2a8")
    PAPER     = colors.HexColor("#ffffff")
    LINEN     = colors.HexColor("#f4f1ea")
    LINEN_2   = colors.HexColor("#fbf9f4")
    RULE      = colors.HexColor("#d6d2c4")
    RULE_SOFT = colors.HexColor("#ece8db")
    SAGE      = colors.HexColor("#2f5d3a")
    SAGE_HI   = colors.HexColor("#3e7448")
    SAGE_TINT = colors.HexColor("#e6ede4")
    CLAY      = colors.HexColor("#b85c38")
    AMBER_C   = colors.HexColor("#c08a2e")
    AZURE     = colors.HexColor("#2c5a78")

    # TODO: register Inter / JetBrains Mono from agricultural_portal/assets/fonts/
    # For now fall back to Helvetica / Courier
    SANS  = "Helvetica"
    SANS_B= "Helvetica-Bold"
    MONO  = "Courier"
    MONO_B= "Courier-Bold"

    PAGE_W, PAGE_H = A4
    L_BAND = 8 * mm          # left sage band width
    LM = 22 * mm             # left margin (inside band)
    RM = 18 * mm
    TM = 16 * mm
    BM = 20 * mm
    BODY_W = PAGE_W - LM - RM

    # ── Document ID ────────────────────────────────────────────────────────────
    MOD_CODE = {"vf":"VF","gh":"GH","pt":"PT","aqd":"AQD","aqc":"AQC"}.get(modality,"XX")
    today_str = _date.today().strftime("%Y%m%d")
    _hash_src = (farm_name + today_str).encode()
    _nnn = int(hashlib.md5(_hash_src).hexdigest(), 16) % 1000
    DOC_ID = f"DOC {MOD_CODE}-{today_str}-{_nnn:03d}"
    report_date = _date.today().strftime("%d %B %Y")

    # ── Modality labels ────────────────────────────────────────────────────────
    MOD_LABELS = {
        "vf":  "Vertical Farm",
        "gh":  "High-Tech Greenhouse",
        "pt":  "Polytunnel",
        "aqd": "Decoupled Aquaponics",
        "aqc": "Coupled Aquaponics",
    }
    MOD_LABEL = MOD_LABELS.get(modality, modality.upper())
    IS_AQ = modality in ("aqd", "aqc")

    # ── Result dict normalisation ─────────────────────────────────────────────
    if IS_AQ:
        _pr = result_dict["plant"]
        _fr = result_dict["fish"]
        _combined_rev   = result_dict.get("combined_revenue", 0)
        _combined_ebitda= result_dict.get("combined_ebitda",  0)
        _combined_capex = result_dict.get("combined_capex",
                          _pr.get("total_capex",0) + _fr.get("total_fish_capex",0))
        _combined_margin= result_dict.get("combined_ebitda_margin",
                          _combined_ebitda / _combined_rev if _combined_rev else 0)
        _combined_dscr  = result_dict.get("combined_dscr",
                          _pr.get("dscr", result_dict.get("dscr")))
        _r = _pr   # plant side for most single-side metrics
    else:
        _pr = result_dict
        _fr = None
        _combined_rev    = _pr.get("annual_revenue", 0)
        _combined_ebitda = _pr.get("ebitda", 0)
        _combined_capex  = _pr.get("total_capex", 0)
        _combined_margin = _pr.get("ebitda_margin", 0)
        _combined_dscr   = _pr.get("dscr")
        _r = _pr

    _rev    = _pr.get("annual_revenue", 0)
    _ebitda = _pr.get("ebitda", 0)
    _capex  = _pr.get("total_capex", 0)
    _costs  = _pr.get("total_annual_costs", 0)
    _kg     = _pr.get("total_annual_kg", 0)
    _price  = _pr.get("effective_price", 0)
    _energy = _pr.get("annual_energy_cost", 0)
    _energy_pct = _energy / _rev * 100 if _rev > 0 else 0
    _payback = _pr.get("payback_years")
    _npv     = _pr.get("npv", 0)
    _dcf     = _pr.get("dcf_cashflows", [])
    _loss_r  = inputs_dict.get("loss_rate", 5) / 100
    _denom   = _price * (1 - _loss_r) * _pr.get("cycles_per_year", 1) * _pr.get("effective_grow_area", 1)
    _be_price  = _costs / _kg if _kg > 0 else None
    _be_yield  = _costs / _denom if _denom > 0 else None
    _price_hdroom = (_price - _be_price) / _price * 100 if _be_price and _price else None
    _equity  = _combined_capex * (1 - inputs_dict.get("ltv", 0) / 100)
    _debt    = _combined_capex * inputs_dict.get("ltv", 0) / 100
    _ds      = _pr.get("annual_debt_service", 0)

    if _energy_pct < 30:
        _viab, _viab_color = "VIABLE", SAGE
    elif _energy_pct < 60:
        _viab, _viab_color = "MARGINAL", AMBER_C
    else:
        _viab, _viab_color = "NOT VIABLE", CLAY

    # ── Paragraph style helper ─────────────────────────────────────────────────
    def ps(name, size, font=SANS, color=INK, align=TA_LEFT,
           sb=0, sa=3, leading_mult=1.4):
        return ParagraphStyle(name, fontName=font, fontSize=size,
                              textColor=color, alignment=align,
                              spaceBefore=sb, spaceAfter=sa,
                              leading=size * leading_mult)

    S_EYEBROW  = ps("Eyebrow", 7.5, MONO_B, INK_3, sa=2)
    S_TITLE    = ps("Title",   26,  SANS_B, INK,   sa=3, leading_mult=1.05)
    S_SUBLINE  = ps("Sub",     10,  SANS,   INK_2, sa=8)
    S_SECT_LBL = ps("SectLbl",  9,  SANS_B, INK,   sa=2)
    S_BODY     = ps("Body",     9.5, SANS,  INK,   sa=4)
    S_BODY2    = ps("Body2",    9,   SANS,  INK_2, sa=3)
    S_CAPTION  = ps("Cap",      8.5, SANS,  INK_3, sa=3)
    S_CAPTION_I= ps("CapI",     8.5, SANS,  INK_3, sa=3)
    S_KPI_VAL  = ps("KpiV",    22,  MONO_B, INK,   align=TA_LEFT, sa=0)
    S_KPI_VAL_S= ps("KpiVS",   22,  MONO_B, SAGE,  align=TA_LEFT, sa=0)
    S_KPI_VAL_C= ps("KpiVC",   22,  MONO_B, CLAY,  align=TA_LEFT, sa=0)
    S_KPI_LBL  = ps("KpiL",     7.5, MONO_B, INK_2, align=TA_LEFT, sa=1)
    S_KPI_SUB  = ps("KpiSub",   8,   SANS,  INK_3, align=TA_LEFT, sa=0)
    S_TBLHDR   = ps("TblH",     7.5, SANS_B, INK_2, align=TA_LEFT, sa=0)
    S_TBLHDR_R = ps("TblHR",    7.5, SANS_B, INK_2, align=TA_RIGHT, sa=0)
    S_TBLBODY  = ps("TblB",     9.5, SANS,   INK,   align=TA_LEFT, sa=0)
    S_TBLNUM   = ps("TblN",     9.5, MONO,   INK,   align=TA_RIGHT, sa=0)
    S_TBLNUM_S = ps("TblNS",    9.5, MONO_B, SAGE,  align=TA_RIGHT, sa=0)
    S_TBLNUM_C = ps("TblNC",    9.5, MONO_B, CLAY,  align=TA_RIGHT, sa=0)
    S_TBLNUM_3 = ps("TblN3",    8.5, MONO,   INK_3, align=TA_RIGHT, sa=0)
    S_TBLNOTE  = ps("TblNt",    8.5, SANS,   INK_2, align=TA_LEFT, sa=0)
    S_METH_LBL = ps("MethL",    7.5, MONO_B, SAGE,  sa=2)
    S_METH_BOD = ps("MethB",    9,   SANS,   INK_2, sa=3, leading_mult=1.55)
    S_CONFIG_K = ps("CfgK",     9,   SANS,   INK_2, sa=0)
    S_CONFIG_V = ps("CfgV",     9.5, MONO,   INK,   align=TA_RIGHT, sa=0)
    S_FOOTER   = ps("Ftr",      7,   SANS,   INK_3, align=TA_CENTER, sa=0)

    def _num(v, prefix="$", suffix="", decimals=0, color="ink"):
        fmt = f"{prefix}{abs(v):,.{decimals}f}{suffix}"
        if v < 0: fmt = f"-{fmt}"
        if color == "sage": return Paragraph(fmt, S_KPI_VAL_S)
        if color == "clay": return Paragraph(fmt, S_KPI_VAL_C)
        return Paragraph(fmt, S_KPI_VAL)

    def _tnum(v, prefix="$", suffix="", decimals=0):
        s = f"{prefix}{abs(v):,.{decimals}f}{suffix}"
        if v < 0: s = f"-{s}"
        style = S_TBLNUM_C if v < 0 else S_TBLNUM
        return Paragraph(s, style)

    def _dash(): return Paragraph("—", S_TBLNUM_3)

    # ── Running chrome ─────────────────────────────────────────────────────────
    _total_pages = [4]  # mutable so onPage can reference

    def _running_chrome(canvas, doc):
        canvas.saveState()
        pw, ph = A4

        # Left vertical band (sage top 30%, linen rest)
        band_top_h = ph * 0.30
        canvas.setFillColor(SAGE)
        canvas.rect(0, ph - band_top_h, L_BAND, band_top_h, fill=1, stroke=0)
        canvas.setFillColor(LINEN)
        canvas.rect(0, 0, L_BAND, ph - band_top_h, fill=1, stroke=0)

        # Rotated label in linen portion
        canvas.saveState()
        canvas.setFont(MONO, 6.5)
        canvas.setFillColor(INK_3)
        canvas.translate(L_BAND * 0.5, ph * 0.45)
        canvas.rotate(90)
        canvas.drawCentredString(0, 0, "CEA FEASIBILITY  ·  VOL. II")
        canvas.restoreState()

        # Header rule
        canvas.setStrokeColor(RULE)
        canvas.setLineWidth(0.5)
        canvas.line(LM, ph - TM + 2*mm, pw - RM, ph - TM + 2*mm)

        # Header text
        canvas.setFont(MONO, 7)
        canvas.setFillColor(INK_3)
        canvas.drawString(LM, ph - TM + 4*mm, "AGRIPORTAL  ·  AGRICULTURAL INTELLIGENCE")
        canvas.drawRightString(pw - RM, ph - TM + 4*mm, DOC_ID)

        # Footer rule
        canvas.setStrokeColor(RULE)
        canvas.line(LM, BM - 3*mm, pw - RM, BM - 3*mm)

        # Footer text
        pg_num = doc.page
        canvas.setFont(SANS_B, 7)
        canvas.setFillColor(INK_3)
        canvas.drawString(LM, BM - 7*mm, f"AGRIPORTAL V2  ·  {DOC_ID}")
        canvas.setFont(SANS, 7)
        canvas.drawCentredString(pw / 2, BM - 7*mm, "Indicative model output — not investment advice.")
        canvas.drawRightString(pw - RM, BM - 7*mm, f"PAGE {pg_num:02d} OF 04")

        canvas.restoreState()

    # ── Chart theming ──────────────────────────────────────────────────────────
    def _theme_for_pdf(fig):
        fig.update_layout(
            font=dict(family="Helvetica, sans-serif", color="#161a16", size=10),
            paper_bgcolor="#fbf9f4",
            plot_bgcolor="#fbf9f4",
            margin=dict(l=48, r=16, t=8, b=38),
            title=None,
            showlegend=False,
            xaxis=dict(
                showgrid=False, zeroline=False, showline=True,
                linecolor="#161a16", linewidth=1,
                tickfont=dict(family="Courier", color="#7a807a", size=9),
            ),
            yaxis=dict(
                showgrid=True, gridcolor="#ece8db", gridwidth=0.8,
                zeroline=True, zerolinecolor="#161a16", zerolinewidth=1,
                tickfont=dict(family="Courier", color="#7a807a", size=9),
            ),
        )
        return fig

    def _chart_img(fig, w_mm=174, h_mm=62):
        _theme_for_pdf(fig)
        png = fig.to_image(format="png", width=1600, height=560, scale=2)
        return RLImage(io.BytesIO(png), width=w_mm*mm, height=h_mm*mm)

    # ── Table style helpers ────────────────────────────────────────────────────
    def _fin_table(data, col_w, ebitda_row=None):
        """Financial statement table with LINEN_2 header, RULE_SOFT row rules."""
        t = Table(data, colWidths=col_w, repeatRows=1)
        ts = [
            ("FONTNAME",     (0,0),(-1,0),  SANS_B),
            ("FONTSIZE",     (0,0),(-1,0),  7.5),
            ("BACKGROUND",   (0,0),(-1,0),  LINEN_2),
            ("TEXTCOLOR",    (0,0),(-1,0),  INK_2),
            ("LINEBELOW",    (0,0),(-1,0),  0.5, INK_3),
            ("TOPPADDING",   (0,0),(-1,-1), 3),
            ("BOTTOMPADDING",(0,0),(-1,-1), 3),
            ("LEFTPADDING",  (0,0),(-1,-1), 4),
            ("RIGHTPADDING", (0,0),(-1,-1), 4),
            ("VALIGN",       (0,0),(-1,-1), "MIDDLE"),
        ]
        for i in range(1, len(data)):
            ts.append(("LINEBELOW", (0,i),(-1,i), 0.3, RULE_SOFT))
        if ebitda_row is not None:
            er = ebitda_row
            ts += [
                ("LINEABOVE",    (0,er),(-1,er), 0.5, INK),
                ("LINEBELOW",    (0,er),(-1,er), 0.5, INK),
                ("BACKGROUND",   (0,er),(-1,er), LINEN),
                ("FONTNAME",     (0,er),(0,er),  SANS_B),
            ]
        t.setStyle(TableStyle(ts))
        return t

    def _config_table(rows, col_w):
        """Definition-list style config table."""
        t = Table(rows, colWidths=col_w)
        ts = [
            ("TOPPADDING",   (0,0),(-1,-1), 2.5),
            ("BOTTOMPADDING",(0,0),(-1,-1), 2.5),
            ("LEFTPADDING",  (0,0),(-1,-1), 0),
            ("RIGHTPADDING", (0,0),(-1,-1), 0),
            ("LINEBELOW",    (0,0),(-1,-1), 0.4, RULE_SOFT),
            ("VALIGN",       (0,0),(-1,-1), "MIDDLE"),
        ]
        t.setStyle(TableStyle(ts))
        return t

    # ── Section header row ─────────────────────────────────────────────────────
    def _sect_hdr(numeral, title, hint=""):
        num_p  = Paragraph(f'<font color="#2f5d3a"><b>{numeral}</b></font>', ps("SN",11,MONO,INK_3))
        lbl_p  = Paragraph(f"<b>{title.upper()}</b>",
                           ps("SL",11,SANS_B,INK,sa=0))
        hint_p = Paragraph(hint, ps("SH",7.5,MONO,INK_3,align=TA_RIGHT,sa=0))
        row = Table([[num_p, lbl_p, hint_p]],
                    colWidths=[10*mm, BODY_W - 10*mm - 50*mm, 50*mm])
        row.setStyle(TableStyle([
            ("VALIGN",(0,0),(-1,-1),"BOTTOM"),
            ("LEFTPADDING",(0,0),(-1,-1),0),
            ("RIGHTPADDING",(0,0),(-1,-1),0),
            ("BOTTOMPADDING",(0,0),(-1,-1),2),
            ("TOPPADDING",(0,0),(-1,-1),0),
            ("LINEBELOW",(0,0),(-1,0),0.5,INK),
        ]))
        return [row, Spacer(1, 4*mm)]

    # ── Chart head row ─────────────────────────────────────────────────────────
    def _chart_hdr(num, title, hint=""):
        num_p  = Paragraph(f'<font color="#2f5d3a"><b>{num}</b></font>',
                           ps("CHN",8.5,MONO_B,INK_3,sa=0))
        ttl_p  = Paragraph(f"<b>{title.upper()}</b>",
                           ps("CHT",9,SANS_B,INK,sa=0))
        hnt_p  = Paragraph(hint, ps("CHH",7.5,MONO,INK_3,align=TA_RIGHT,sa=0))
        row = Table([[num_p, ttl_p, hnt_p]],
                    colWidths=[8*mm, BODY_W - 8*mm - 52*mm, 52*mm])
        row.setStyle(TableStyle([
            ("VALIGN",(0,0),(-1,-1),"BOTTOM"),
            ("LEFTPADDING",(0,0),(-1,-1),0),
            ("RIGHTPADDING",(0,0),(-1,-1),0),
            ("BOTTOMPADDING",(0,0),(-1,-1),2),
            ("TOPPADDING",(0,0),(-1,-1),0),
            ("LINEBELOW",(0,0),(-1,0),0.3,RULE),
        ]))
        return [row, Spacer(1, 2*mm)]

    # ── Sub-heading ────────────────────────────────────────────────────────────
    def _sub_hdr(text):
        return Paragraph(
            f'<font color="#2f5d3a">▮</font>  <b>{text}</b>',
            ps("SBH",10,SANS_B,INK,sb=6,sa=3))

    # ── Methodology callout ────────────────────────────────────────────────────
    def _meth_box(label, *paras):
        inner_rows = [[Paragraph(label, S_METH_LBL)]]
        for p in paras:
            inner_rows.append([Paragraph(p, S_METH_BOD)])
        inner = Table(inner_rows, colWidths=[BODY_W - 12*mm])
        inner.setStyle(TableStyle([
            ("LEFTPADDING",(0,0),(-1,-1),4),
            ("RIGHTPADDING",(0,0),(-1,-1),4),
            ("TOPPADDING",(0,0),(-1,-1),2),
            ("BOTTOMPADDING",(0,0),(-1,-1),2),
        ]))
        outer = Table([[inner]], colWidths=[BODY_W])
        outer.setStyle(TableStyle([
            ("BOX",         (0,0),(-1,-1), 0.5, RULE),
            ("BACKGROUND",  (0,0),(-1,-1), LINEN_2),
            ("LINEAFTER",   (0,0),(0,-1),  2.0, SAGE),
            ("LEFTPADDING", (0,0),(-1,-1), 6),
            ("RIGHTPADDING",(0,0),(-1,-1), 4),
            ("TOPPADDING",  (0,0),(-1,-1), 4),
            ("BOTTOMPADDING",(0,0),(-1,-1),4),
        ]))
        return outer

    # ══════════════════════════════════════════════════════════════════════════
    # PAGE 1 BUILDER
    # ══════════════════════════════════════════════════════════════════════════
    def _page1():
        els = []

        # Eyebrow
        els.append(Paragraph(
            f"CEA FEASIBILITY ASSESSMENT  ·  {MOD_LABEL.upper()}", S_EYEBROW))
        els.append(Spacer(1, 2*mm))

        # Title
        crop_name  = inputs_dict.get("crop", "—")
        if IS_AQ:
            fish_name  = _fr.get("species", inputs_dict.get("fish_species","—"))
            title_html = (f"<b>{crop_name}</b>"
                          f' <font color="#2f5d3a"><i> × </i></font>'
                          f"<b>{fish_name}</b>")
        else:
            title_html = f"<b>{crop_name}</b>"
        els.append(Paragraph(title_html,
                              ps("MainTitle",26,SANS_B,INK,sa=4,leading_mult=1.05)))

        # Subline
        _fp = inputs_dict.get("footprint", 0)
        _lvl = inputs_dict.get("levels","")
        _auto= inputs_dict.get("automation","—")
        sub_parts = [inputs_dict.get("country","—"),
                     f"{int(_fp):,} m² plant area"]
        if IS_AQ:
            _tv = _fr.get("tank_volume_m3", inputs_dict.get("tank_volume_m3","—"))
            sub_parts.append(f"{_tv} m³ fish tank")
        sub_parts += [f"{_auto} automation", report_date]
        els.append(Paragraph("   ·   ".join(str(s) for s in sub_parts),
                              ps("SubL",10,SANS,INK_2,sa=6)))

        # Viability strip
        _dscr_str = f"{_combined_dscr:.2f}×" if _combined_dscr else "—"
        if _viab == "VIABLE":
            _viab_body = (
                f"Plant energy intensity is <b>{_energy_pct:.1f}%</b> of "
                + ("combined revenue" if IS_AQ else "revenue")
                + " — well below the 30% caution threshold"
                + (" for decoupled aquaponics." if IS_AQ else ".")
                + (f" Combined system shows {'positive' if _combined_ebitda > 0 else 'negative'} EBITDA."
                   if IS_AQ else "")
            )
        elif _viab == "MARGINAL":
            _viab_body = (
                f"Energy intensity of <b>{_energy_pct:.1f}%</b> of revenue exceeds the 30% caution "
                "threshold. System is marginally viable; energy cost risk is elevated."
            )
        else:
            _viab_body = (
                f"Energy intensity of <b>{_energy_pct:.1f}%</b> of revenue is above the 60% "
                "non-viability ceiling. At current electricity prices this system is structurally unviable."
            )
        if _combined_dscr and _combined_dscr < 1.0:
            _viab_body += f" DSCR of {_combined_dscr:.2f}× indicates insufficient debt coverage."

        _viab_col_hex = {SAGE:"#2f5d3a", AMBER_C:"#c08a2e", CLAY:"#b85c38"}[_viab_color]
        stamp_col = ps("Stamp1",7,MONO_B,INK_3,align=TA_CENTER,sa=1)
        stamp_val = ps("Stamp2",14,MONO_B,INK,align=TA_CENTER,sa=0)
        _stamp = Table([
            [Paragraph("ENERGY RATIO", stamp_col)],
            [Paragraph(f"{_energy_pct:.1f}%", stamp_val)],
        ], colWidths=[24*mm])
        _stamp.setStyle(TableStyle([
            ("TOPPADDING",(0,0),(-1,-1),2),
            ("BOTTOMPADDING",(0,0),(-1,-1),2),
            ("LEFTPADDING",(0,0),(-1,-1),4),
        ]))
        _viab_left = Table([
            [Paragraph(
                f'<font color="{_viab_col_hex}">●</font>  '
                f'<b><font color="{_viab_col_hex}">{_viab}</font></b>  '
                f'<font color="#7a807a">STRUCTURAL VIABILITY SIGNAL</font>',
                ps("VB1",7.5,MONO_B,INK_3,sa=3))],
            [Paragraph(_viab_body, ps("VB2",8.5,SANS,INK_2,sa=0,leading_mult=1.5))],
        ], colWidths=[BODY_W - 32*mm])
        _viab_left.setStyle(TableStyle([("LEFTPADDING",(0,0),(-1,-1),0),
                                         ("TOPPADDING",(0,0),(-1,-1),1),
                                         ("BOTTOMPADDING",(0,0),(-1,-1),1)]))
        viab_outer = Table([[_viab_left, _stamp]],
                           colWidths=[BODY_W - 32*mm, 32*mm])
        viab_outer.setStyle(TableStyle([
            ("BOX",           (0,0),(-1,-1), 0.5, RULE),
            ("BACKGROUND",    (0,0),(-1,-1), LINEN_2),
            ("VALIGN",        (0,0),(-1,-1), "MIDDLE"),
            ("TOPPADDING",    (0,0),(-1,-1), 5),
            ("BOTTOMPADDING", (0,0),(-1,-1), 5),
            ("LEFTPADDING",   (0,0),(0,-1),  5),
            ("LINEAFTER",     (0,0),(0,-1),  0.4, RULE),
            ("LEFTPADDING",   (1,0),(1,-1),  6),
        ]))
        els.append(viab_outer)
        els.append(Spacer(1, 4*mm))

        # KPI grid
        def _kpi_cell(label, value_para, sub="", primary=False, negative=False):
            bg = SAGE_TINT if primary else LINEN_2
            top_rule_color = SAGE if primary else None
            inner = [[Paragraph(label.upper(), S_KPI_LBL)],
                     [value_para]]
            if sub:
                inner.append([Paragraph(sub, S_KPI_SUB)])
            t = Table(inner, colWidths=[BODY_W / 3 - 1*mm])
            ts_inner = [
                ("LEFTPADDING",  (0,0),(-1,-1), 5),
                ("RIGHTPADDING", (0,0),(-1,-1), 5),
                ("TOPPADDING",   (0,0),(-1,-1), 3),
                ("BOTTOMPADDING",(0,0),(-1,-1), 3),
                ("BACKGROUND",   (0,0),(-1,-1), bg),
            ]
            if top_rule_color:
                ts_inner.append(("LINEABOVE",(0,0),(-1,0), 2.0, SAGE))
            t.setStyle(TableStyle(ts_inner))
            return t

        if IS_AQ:
            _fish_rev  = _fr.get("annual_fish_revenue", 0)
            _plant_rev = _pr.get("annual_revenue", 0)
            _fish_pct  = _fish_rev / _combined_rev * 100 if _combined_rev else 0
            dscr_val = Paragraph(f"{_combined_dscr:.2f}<font size='11'>×</font>" if _combined_dscr else "N/A",
                                  S_KPI_VAL_C if (_combined_dscr and _combined_dscr < 1.0) else S_KPI_VAL)
            kpi_row1 = [
                _kpi_cell("Combined Revenue",
                          Paragraph(f"${_combined_rev/1e3:.0f}<font size='11'>K</font>", S_KPI_VAL_S),
                          sub=f"Plant ${_plant_rev/1e3:.0f}K  ·  Fish ${_fish_rev/1e3:.0f}K", primary=True),
                _kpi_cell("Combined EBITDA",
                          Paragraph(f"${_combined_ebitda/1e3:.0f}<font size='11'>K</font>",
                                    S_KPI_VAL_S if _combined_ebitda >= 0 else S_KPI_VAL_C),
                          sub=f"Margin {_combined_margin*100:.1f}%"),
                _kpi_cell("Combined CAPEX",
                          Paragraph(f"${_combined_capex/1e3:.0f}<font size='11'>K</font>", S_KPI_VAL),
                          sub="Plant + fish + shared"),
            ]
            _pb_str = f"{_payback:.1f}" if _payback else "N/A"
            _pb_sub = f"Not reached < 10y" if not _payback else "yrs to equity return"
            kpi_row2 = [
                _kpi_cell("Plant Payback",
                          Paragraph(_pb_str if not _payback else f"{_pb_str}<font size='11'>yr</font>",
                                    S_KPI_VAL_C if not _payback else S_KPI_VAL),
                          sub=_pb_sub),
                _kpi_cell("Combined DSCR", dscr_val,
                          sub="Coverage below 1.0×" if (_combined_dscr and _combined_dscr < 1.0)
                              else "Debt coverage ratio"),
                _kpi_cell("Fish Share of Revenue",
                          Paragraph(f"{_fish_pct:.0f}<font size='11'>%</font>",
                                    S_KPI_VAL if _fish_pct > 20 else S_KPI_VAL_C),
                          sub=f"{_fr.get('annual_kg_fish',0):,.0f} kg @ ${_fr.get('effective_fish_price',0):.2f}/kg"),
            ]
        else:
            dscr_v = _combined_dscr
            kpi_row1 = [
                _kpi_cell("Annual Revenue",
                          Paragraph(f"${_combined_rev/1e3:.0f}<font size='11'>K</font>", S_KPI_VAL_S),
                          primary=True),
                _kpi_cell("Annual EBITDA",
                          Paragraph(f"${_combined_ebitda/1e3:.0f}<font size='11'>K</font>",
                                    S_KPI_VAL_S if _combined_ebitda >= 0 else S_KPI_VAL_C),
                          sub=f"Margin {_combined_margin*100:.1f}%"),
                _kpi_cell("Total CAPEX",
                          Paragraph(f"${_combined_capex/1e3:.0f}<font size='11'>K</font>", S_KPI_VAL)),
            ]
            kpi_row2 = [
                _kpi_cell("Payback Period",
                          Paragraph(f"{_payback:.1f}<font size='11'>yr</font>" if _payback else "N/A",
                                    S_KPI_VAL_C if not _payback else S_KPI_VAL)),
                _kpi_cell("DSCR",
                          Paragraph(f"{dscr_v:.2f}<font size='11'>×</font>" if dscr_v else "N/A",
                                    S_KPI_VAL_C if (dscr_v and dscr_v < 1.0) else S_KPI_VAL),
                          sub="Debt coverage ratio"),
                _kpi_cell("NPV @ Year 10",
                          Paragraph(f"${_npv/1e3:.0f}<font size='11'>K</font>",
                                    S_KPI_VAL_S if _npv >= 0 else S_KPI_VAL_C)),
            ]

        def _kpi_row(cells):
            t = Table([cells], colWidths=[BODY_W/3]*3)
            t.setStyle(TableStyle([
                ("BOX",        (0,0),(-1,-1), 0.5, RULE),
                ("INNERGRID",  (0,0),(-1,-1), 0.5, RULE),
                ("VALIGN",     (0,0),(-1,-1), "TOP"),
                ("TOPPADDING", (0,0),(-1,-1), 0),
                ("BOTTOMPADDING",(0,0),(-1,-1),0),
                ("LEFTPADDING",(0,0),(-1,-1), 0),
                ("RIGHTPADDING",(0,0),(-1,-1),0),
            ]))
            return t

        kpi_grid = Table([[_kpi_row(kpi_row1)], [_kpi_row(kpi_row2)]], colWidths=[BODY_W])
        kpi_grid.setStyle(TableStyle([
            ("TOPPADDING",(0,0),(-1,-1),0),("BOTTOMPADDING",(0,0),(-1,-1),0),
            ("LEFTPADDING",(0,0),(-1,-1),0),("RIGHTPADDING",(0,0),(-1,-1),0),
        ]))
        els.append(kpi_grid)
        els.append(Spacer(1, 5*mm))

        # EBITDA Bridge chart
        els += _chart_hdr("01", "Combined EBITDA Bridge" if IS_AQ else "EBITDA Bridge",
                          "USD  ·  ANNUAL  ·  STACKED")
        if IS_AQ:
            _nutr = result_dict.get("nutrient_offset_saving", 0)
            _bl  = ["Plant Rev","Fish Rev","Plant Costs","Fish Costs","Nutrient ↔","EBITDA"]
            _bv  = [_pr["annual_revenue"], _fr["annual_fish_revenue"],
                    -_pr["total_annual_costs"], -_fr["total_fish_costs"],
                    _nutr, _combined_ebitda]
        else:
            _bl = ["Revenue","Variable","Water","Energy","Labour","Rent","Maint.","EBITDA"]
            _bv = [_rev, -_pr.get("annual_variable_cost",0), -_pr.get("annual_water_cost",0),
                   -_energy, -_pr.get("annual_labour_cost",0),
                   -_pr.get("annual_rent",0), -_pr.get("annual_maintenance",0), _ebitda]
        _bc = []
        for i, v in enumerate(_bv):
            if i == 0: _bc.append("#2f5d3a")
            elif IS_AQ and i == 1: _bc.append("#3e7448")
            elif i == len(_bv)-1: _bc.append("#2f5d3a" if v >= 0 else "#b85c38")
            else: _bc.append("rgba(184,92,56,0.78)" if v < 0 else "rgba(47,93,58,0.78)")

        import plotly.graph_objects as go
        fig_bridge = go.Figure(go.Bar(
            x=_bl, y=_bv, marker_color=_bc,
            text=[f"${v/1e3:+.0f}K" for v in _bv], textposition="outside",
        ))
        fig_bridge.update_layout(
            yaxis=dict(tickprefix="$", tickformat=",.0f"),
            xaxis=dict(showgrid=False),
        )
        _chart_box = Table([[_chart_img(fig_bridge, w_mm=BODY_W/mm, h_mm=68)]],
                           colWidths=[BODY_W])
        _chart_box.setStyle(TableStyle([
            ("BOX",(0,0),(-1,-1),0.5,RULE),
            ("BACKGROUND",(0,0),(-1,-1),LINEN_2),
            ("TOPPADDING",(0,0),(-1,-1),2),
            ("BOTTOMPADDING",(0,0),(-1,-1),2),
            ("LEFTPADDING",(0,0),(-1,-1),2),
            ("RIGHTPADDING",(0,0),(-1,-1),2),
        ]))
        els.append(_chart_box)

        _bridge_caption = (
            "Bars show annual contributions to EBITDA. "
            + ("Green bars are revenue sources; clay bars are cost categories. "
               if not IS_AQ else
               "Plant and fish revenues are shown separately; "
               "costs are combined by category. ")
            + f"Combined EBITDA: ${_combined_ebitda/1e3:.0f}K ({_combined_margin*100:.1f}% margin)."
        )
        els.append(Paragraph(_bridge_caption, S_CAPTION_I))
        return els

    # ══════════════════════════════════════════════════════════════════════════
    # PAGE 2 BUILDER
    # ══════════════════════════════════════════════════════════════════════════
    def _page2():
        els = []
        els += _sect_hdr("II", "Cost Structure & Profit / Loss", "Annual basis  ·  USD")

        # Plant P&L
        els.append(_sub_hdr("Plant Side — Annual P&L"))
        _total_c = _pr.get("total_annual_costs", 0) or 1
        _pr_rev  = _pr.get("annual_revenue", 0) or 1
        def _pct(v, denom): return f"{v/denom*100:.1f}%" if denom else "—"
        pl_rows = [
            [Paragraph("ITEM", S_TBLHDR),
             Paragraph("$ / YEAR", S_TBLHDR_R),
             Paragraph("% OF COSTS", S_TBLHDR_R),
             Paragraph("% OF REV", S_TBLHDR_R)],
        ]
        _pl_items = [
            ("Revenue",    _pr.get("annual_revenue",0),      "—",                   "100%"),
            ("Energy",     _pr.get("annual_energy_cost",0),  _pct(_energy,_total_c), _pct(_energy,_pr_rev)),
            ("Labour",     _pr.get("annual_labour_cost",0),  _pct(_pr.get("annual_labour_cost",0),_total_c), "—"),
            ("Variable",   _pr.get("annual_variable_cost",0),_pct(_pr.get("annual_variable_cost",0),_total_c),"—"),
            ("Water",      _pr.get("annual_water_cost",0),   _pct(_pr.get("annual_water_cost",0),_total_c),"—"),
            ("Maintenance",_pr.get("annual_maintenance",0),  _pct(_pr.get("annual_maintenance",0),_total_c),"—"),
            ("Rent",       _pr.get("annual_rent",0),         _pct(_pr.get("annual_rent",0),_total_c),"—"),
        ]
        for item, val, pct_c, pct_r in _pl_items:
            is_zero = val == 0
            _s = S_TBLNUM_3 if is_zero else S_TBLNUM
            pl_rows.append([
                Paragraph(item, S_TBLNUM_3 if is_zero else S_TBLBODY),
                Paragraph(f"${val:,.0f}", _s),
                Paragraph(pct_c, _s),
                Paragraph(pct_r, _s),
            ])
        # EBITDA row
        _ebi_s = S_TBLNUM_S if _ebitda >= 0 else S_TBLNUM_C
        pl_rows.append([
            Paragraph("EBITDA", ps("EBL",9.5,SANS_B,INK,sa=0)),
            Paragraph(f"${_ebitda:,.0f}", _ebi_s),
            Paragraph("—", S_TBLNUM_3),
            Paragraph(f"{_pr.get('ebitda_margin',0)*100:.1f}%",
                      ps("EBM",9.5,MONO_B,SAGE if _ebitda>=0 else CLAY,align=TA_RIGHT,sa=0)),
        ])
        cw = [BODY_W*0.42, BODY_W*0.20, BODY_W*0.19, BODY_W*0.19]
        els.append(_fin_table(pl_rows, cw, ebitda_row=len(pl_rows)-1))

        # Fish P&L (AQ only)
        if IS_AQ and _fr:
            els.append(Spacer(1, 4*mm))
            els.append(_sub_hdr("Fish Side — Annual P&L"))
            _fr_rev = _fr.get("annual_fish_revenue", 0)
            _fe     = _fr.get("fish_ebitda", 0)
            fish_items = [
                ("Revenue",    _fr_rev,                                 f"{_fr.get('annual_kg_fish',0):,.0f} kg @ ${_fr.get('effective_fish_price',0):.2f}/kg"),
                ("Feed",       _fr.get("annual_feed_cost",0),           f"FCR {_fr.get('fcr',1.5):.1f}"),
                ("Fingerlings",_fr.get("annual_fingerling_cost",0),     "—"),
                ("Energy",     _fr.get("annual_fish_energy_cost",0),    f"ΔT={_fr.get('delta_t',0):.0f}°C heating + aeration"),
                ("Water/other",_fr.get("annual_water_cost",0),          "—"),
                ("Labour",     _fr.get("annual_fish_labour_cost",0),    "—"),
                ("Maintenance",_fr.get("annual_fish_maintenance",0),    "—"),
            ]
            fish_rows = [
                [Paragraph("ITEM", S_TBLHDR),
                 Paragraph("$ / YEAR", S_TBLHDR_R),
                 Paragraph("NOTES", S_TBLHDR)],
            ]
            for item, val, note in fish_items:
                fish_rows.append([
                    Paragraph(item, S_TBLBODY),
                    Paragraph(f"${val:,.0f}", S_TBLNUM),
                    Paragraph(note, S_TBLNOTE),
                ])
            _fe_s = S_TBLNUM_S if _fe >= 0 else S_TBLNUM_C
            fish_rows.append([
                Paragraph("Fish EBITDA", ps("FEL",9.5,SANS_B,INK,sa=0)),
                Paragraph(f"${_fe:,.0f}", _fe_s),
                Paragraph("—", S_TBLNOTE),
            ])
            cw2 = [BODY_W*0.38, BODY_W*0.20, BODY_W*0.42]
            els.append(_fin_table(fish_rows, cw2, ebitda_row=len(fish_rows)-1))

        els.append(Spacer(1, 5*mm))
        _meth_p1 = (
            "Revenue and costs are modelled on an annual basis in USD. "
            "Energy pricing is taken from the country-specific benchmark table "
            "(kWh cost adjusted for food-index). Labour uses national hourly rates. "
            "EBITDA excludes depreciation, interest, and tax — it is an operating metric."
        )
        if IS_AQ:
            _meth_p2 = (
                "In decoupled mode, plant and fish sub-systems are financially independent. "
                "Nutrient offset (shown in the EBITDA bridge) represents fertiliser cost savings "
                "from fish effluent recirculated to the plant side."
            )
        else:
            _meth_p2 = (
                "Plant-side costs include a packaging cost per kg sold, "
                "a post-harvest loss rate applied to gross yield, "
                "and an energy component that scales with grow-light electricity demand."
            )
        els.append(_meth_box("READING THIS SECTION", _meth_p1, _meth_p2))
        return els

    # ══════════════════════════════════════════════════════════════════════════
    # PAGE 3 BUILDER
    # ══════════════════════════════════════════════════════════════════════════
    def _page3():
        import plotly.graph_objects as go
        els = []
        els += _sect_hdr("III", "Investment Returns",
                         "10-year DCF  ·  Plant side" if IS_AQ else "10-year DCF")

        els += _chart_hdr("02", "Cumulative NPV — 10-year DCF",
                          "USD  ·  DISCOUNTED  ·  CUMULATIVE")

        # DCF chart
        _end_npv = _dcf[-1]["cumulative_npv"] if _dcf else 0
        _line_col = "#2f5d3a" if _end_npv >= 0 else "#b85c38"
        _fill_col = "rgba(47,93,58,0.12)" if _end_npv >= 0 else "rgba(184,92,56,0.12)"

        fig_dcf = go.Figure()
        fig_dcf.add_trace(go.Scatter(
            x=["Y0"] + [f"Y{d['year']}" for d in _dcf],
            y=[-_equity] + [d["cumulative_npv"] for d in _dcf],
            mode="lines+markers",
            line=dict(color=_line_col, width=2),
            marker=dict(size=5, color=_line_col),
            fill="tozeroy", fillcolor=_fill_col,
        ))
        fig_dcf.add_hline(y=0, line_dash="solid", line_color="#161a16", line_width=0.8)
        _last_val = _end_npv
        _last_yr  = f"Y{len(_dcf)}"
        fig_dcf.add_annotation(
            x=_last_yr, y=_last_val,
            text=f"  ${_last_val/1e3:.0f}K @ {_last_yr}",
            showarrow=False, font=dict(family="Courier", size=9, color=_line_col),
            xanchor="left",
        )
        fig_dcf.update_layout(
            xaxis=dict(title=None),
            yaxis=dict(tickprefix="$", tickformat=",.0f"),
        )

        _dcf_chart_box = Table([[_chart_img(fig_dcf, w_mm=BODY_W/mm, h_mm=68)]],
                               colWidths=[BODY_W])
        _dcf_chart_box.setStyle(TableStyle([
            ("BOX",(0,0),(-1,-1),0.5,RULE),
            ("BACKGROUND",(0,0),(-1,-1),LINEN_2),
            ("TOPPADDING",(0,0),(-1,-1),2),
            ("BOTTOMPADDING",(0,0),(-1,-1),2),
            ("LEFTPADDING",(0,0),(-1,-1),2),
            ("RIGHTPADDING",(0,0),(-1,-1),2),
        ]))
        els.append(_dcf_chart_box)
        els.append(Spacer(1, 2*mm))

        # DCF detail table with trajectory bars
        els.append(_sub_hdr("DCF Detail — Plant Side" if IS_AQ else "DCF Detail"))
        _max_abs = max((abs(d["cumulative_npv"]) for d in _dcf), default=1)
        BAR_W = 36*mm
        BAR_H = 4*mm

        dcf_rows = [
            [Paragraph("YEAR",   S_TBLHDR),
             Paragraph("FCFE ($)",           S_TBLHDR_R),
             Paragraph("PV ($)",             S_TBLHDR_R),
             Paragraph("CUMULATIVE NPV ($)", S_TBLHDR_R),
             Paragraph("TRAJECTORY",         S_TBLHDR)],
        ]
        for d in _dcf:
            _cum = d["cumulative_npv"]
            _ratio = abs(_cum) / _max_abs
            bar = Drawing(BAR_W, BAR_H)
            bar.add(Rect(0, 0, BAR_W, BAR_H, fillColor=LINEN, strokeColor=None))
            bar.add(Line(BAR_W/2, 0, BAR_W/2, BAR_H,
                        strokeColor=INK_3, strokeWidth=0.5))
            fill_w = _ratio * (BAR_W / 2)
            bar_color = colors.HexColor("#2f5d3a") if _cum >= 0 else colors.HexColor("#b85c38")
            bar_color_t = colors.HexColor("#2f5d3a66") if _cum >= 0 else colors.HexColor("#b85c3866")
            if _cum >= 0:
                bar.add(Rect(BAR_W/2, 0.5, fill_w, BAR_H-1,
                            fillColor=bar_color_t, strokeColor=None))
            else:
                bar.add(Rect(BAR_W/2 - fill_w, 0.5, fill_w, BAR_H-1,
                            fillColor=bar_color_t, strokeColor=None))
            _cum_s = S_TBLNUM_C if _cum < 0 else S_TBLNUM
            dcf_rows.append([
                Paragraph(f"Y {d['year']}", S_TBLBODY),
                Paragraph(f"${d['fcfe']:,.0f}",   S_TBLNUM_C if d["fcfe"] < 0 else S_TBLNUM),
                Paragraph(f"${d['pv']:,.0f}",     S_TBLNUM_C if d["pv"]   < 0 else S_TBLNUM),
                Paragraph(f"${_cum:,.0f}",        _cum_s),
                bar,
            ])
        cw3 = [10*mm, BODY_W*0.18, BODY_W*0.18, BODY_W*0.22, BAR_W]
        t_dcf = Table(dcf_rows, colWidths=cw3, repeatRows=1)
        ts_dcf = [
            ("FONTNAME",     (0,0),(-1,0), SANS_B),
            ("FONTSIZE",     (0,0),(-1,0), 7.5),
            ("BACKGROUND",   (0,0),(-1,0), LINEN_2),
            ("TEXTCOLOR",    (0,0),(-1,0), INK_2),
            ("LINEBELOW",    (0,0),(-1,0), 0.5, INK_3),
            ("TOPPADDING",   (0,0),(-1,-1),3),
            ("BOTTOMPADDING",(0,0),(-1,-1),3),
            ("LEFTPADDING",  (0,0),(-1,-1),4),
            ("RIGHTPADDING", (0,0),(-1,-1),4),
            ("VALIGN",       (0,0),(-1,-1),"MIDDLE"),
        ]
        for i in range(1, len(dcf_rows)):
            ts_dcf.append(("LINEBELOW",(0,i),(-1,i),0.3,RULE_SOFT))
        t_dcf.setStyle(TableStyle(ts_dcf))
        els.append(t_dcf)
        els.append(Spacer(1, 2*mm))

        _disc_rate = inputs_dict.get("discount_rate", 8)
        _caption = (
            f"Discounted at {_disc_rate:.1f}% (cost of equity). "
            f"Year-0 entry: equity outlay of "
            f"-${_equity:,.0f} (CAPEX × (1 − LTV)). "
            "FCFE held constant across years for this model run. "
            + ("Negative trajectory indicates the plant side does not service its equity outlay "
               "within the 10-year horizon under current inputs."
               if _end_npv < 0 else
               "Positive trajectory indicates the project recovers its equity investment.")
        )
        els.append(Paragraph(_caption, S_CAPTION_I))
        return els

    # ══════════════════════════════════════════════════════════════════════════
    # PAGE 4 BUILDER
    # ══════════════════════════════════════════════════════════════════════════
    def _page4():
        els = []
        els += _sect_hdr("IV", "System Configuration",
                         f"As modelled  ·  {report_date}")

        def _row(key, val, bold_val=False):
            v_style = ps("CV",9.5,MONO_B if bold_val else MONO,INK,align=TA_RIGHT,sa=0)
            return [Paragraph(key, S_CONFIG_K), Paragraph(str(val), v_style)]

        def _grp_hdr(label):
            return [Paragraph(label.upper(), ps("GH",7.5,SANS_B,INK,sa=0)),
                    Paragraph("", S_CONFIG_K)]

        CW = BODY_W / 2 - 3*mm

        # Left column groups
        _fp = inputs_dict.get("footprint", 0)
        _lvl = inputs_dict.get("levels", 1)
        _ega = _pr.get("effective_grow_area", _fp)
        left_rows = (
            [_grp_hdr("System & Site")] +
            [_row("Country",         inputs_dict.get("country","—")),
             _row("Modality",        MOD_LABEL),
             _row("Footprint",       f"{int(_fp):,} m²"),
             _row("Levels",          str(int(_lvl)) if _lvl else "1"),
             _row("Effective grow",  f"{_ega:,.0f} m²"),
             _row("Net grow factor", f"{inputs_dict.get('net_grow_factor',85):.0f}%"),
             _row("Automation",      inputs_dict.get("automation","—")),
             _row("Lights tier",     inputs_dict.get("lights_tier","—")) if "lights_tier" in inputs_dict
                                    else _row("Structure", _r.get("structure_type","—")),
            ] +
            [_grp_hdr("Crop & Revenue")] +
            [_row("Crop",            inputs_dict.get("crop","—")),
             _row("Price scenario",  inputs_dict.get("price_scenario","—")),
             _row("Selling price",   f"${_price:.2f} / kg"),
             _row("Cycles / yr",     str(_pr.get("cycles_per_year","—"))),
             _row("Annual output",   f"{_kg:,.0f} kg"),
             _row("Break-even price",f"${_be_price:.2f} / kg" if _be_price else "N/A"),
             _row("Revenue / m²",    f"${_rev/(_fp or 1):,.0f} / yr"),
            ]
        )
        if IS_AQ and _fr:
            left_rows += (
                [_grp_hdr("Fish System")] +
                [_row("Species",     _fr.get("species","—")),
                 _row("Tank volume", f"{_fr.get('tank_volume_m3','—')} m³"),
                 _row("Scale",       _fr.get("system_scale","—")),
                 _row("Fish / yr",   f"{_fr.get('annual_kg_fish',0):,.0f} kg"),
                 _row("Cycles / yr", str(_fr.get("cycles_per_year","—"))),
                 _row("Price",       f"${_fr.get('effective_fish_price',0):.2f} / kg"),
                ]
            )

        # Right column groups
        right_rows = (
            [_grp_hdr("Financial Structure")] +
            [_row("LTV",             f"{inputs_dict.get('ltv',0):.0f}%"),
             _row("Interest rate",   f"{inputs_dict.get('interest_rate',0):.1f}%"),
             _row("Loan term",       f"{inputs_dict.get('loan_term_years',0)} yrs"),
             _row("Discount rate",   f"{inputs_dict.get('discount_rate',0):.1f}%"),
             _row("Depreciation",    f"{inputs_dict.get('depreciation_years',0)} yrs"),
             _row("Tax rate",        f"{inputs_dict.get('tax_rate',0):.1f}%"),
             _row("Equity",          f"${_equity:,.0f}"),
             _row("Debt",            f"${_debt:,.0f}"),
             _row("Annual debt svc", f"${_ds:,.0f}" if _ds else "N/A"),
             _row("DSCR",            f"{_combined_dscr:.2f}×" if _combined_dscr else "N/A"),
            ] +
            [_grp_hdr("CAPEX Composition")] +
            _capex_right_rows()
        )

        def _fmt_table(rows):
            t = Table(rows, colWidths=[CW*0.60, CW*0.40])
            ts = [
                ("TOPPADDING",   (0,0),(-1,-1), 2.5),
                ("BOTTOMPADDING",(0,0),(-1,-1), 2.5),
                ("LEFTPADDING",  (0,0),(-1,-1), 0),
                ("RIGHTPADDING", (0,0),(-1,-1), 0),
                ("VALIGN",       (0,0),(-1,-1), "MIDDLE"),
                ("LINEBELOW",    (0,0),(-1,-1), 0.35, RULE_SOFT),
            ]
            # Group headers get a bottom rule
            for i, row in enumerate(rows):
                if isinstance(row[0], Paragraph):
                    txt = row[0].text if hasattr(row[0],'text') else ""
            t.setStyle(TableStyle(ts))
            return t

        left_t  = _fmt_table(left_rows)
        right_t = _fmt_table(right_rows)
        two_col = Table([[left_t, Spacer(6*mm,1), right_t]],
                        colWidths=[CW, 6*mm, CW])
        two_col.setStyle(TableStyle([
            ("VALIGN",(0,0),(-1,-1),"TOP"),
            ("TOPPADDING",(0,0),(-1,-1),0),
            ("BOTTOMPADDING",(0,0),(-1,-1),0),
            ("LEFTPADDING",(0,0),(-1,-1),0),
            ("RIGHTPADDING",(0,0),(-1,-1),0),
        ]))
        els.append(two_col)
        els.append(Spacer(1, 5*mm))

        # Methodology callout
        _meth1 = (
            "All values generated by the Agricultural Intelligence Portal model. "
            "Crop yield benchmarks from the internal crop database "
            "(kg/m²/cycle per crop, scaled by net grow factor and loss rate). "
            "Energy costs use country-specific kWh prices. "
            "Labour uses national hourly rates. CAPEX from component cost functions "
            "scaled to grow area and automation level."
        )
        if IS_AQ:
            _meth2 = (
                "In decoupled aquaponics, plant and fish systems are financially independent. "
                "Fish EBITDA is shown separately; combined figures aggregate both sub-systems. "
                "Nutrient offset is credited to plant variable costs at 10–20% of fertiliser budget."
            )
        else:
            _meth2 = (
                f"This is a {MOD_LABEL} model. "
                "Energy demand scales with grow-light DLI requirement and HVAC load. "
                "For greenhouse / polytunnel, natural DLI fraction reduces supplemental lighting cost."
            )
        _meth3 = (
            "NPV is computed on plant equity FCFE discounted at the specified equity cost rate. "
            "Fish side (AQ) is reported at EBITDA level only — full fish DCF available on request. "
            "Results are indicative. Not investment advice."
        )
        els.append(_meth_box("METHODOLOGY  ·  SCOPE  ·  LIMITATIONS",
                             _meth1, _meth2, _meth3))
        return els

    def _capex_right_rows():
        rows = []
        if IS_AQ:
            _pc = _pr.get("total_capex", 0)
            _fc = _fr.get("total_fish_capex", 0)
            _ic = result_dict.get("integration_capex", 0)
            _tc = _combined_capex
            items = [
                ("Plant CAPEX",  _pc),
                ("Fish CAPEX",   _fc),
                ("Integration",  _ic),
            ]
            for k, v in items:
                rows.append(_row_fn(k, f"${v:,.0f}"))
            rows.append(_row_fn("Total CAPEX", f"${_tc:,.0f}", bold=True))
        else:
            _tc = _pr.get("total_capex", 0) or 1
            # VF components
            if "led_capex" in _pr:
                items = [
                    ("LED Lighting",   _pr.get("led_capex",0)),
                    ("HVAC",           _pr.get("hvac_capex",0)),
                    ("Racking",        _pr.get("racks_capex",0)),
                    ("Building",       _pr.get("building_capex",0)),
                    ("Automation",     _pr.get("automation_capex",0)),
                    ("Electrical",     _pr.get("electrical_capex",0)),
                    ("Water/Irrig.",   _pr.get("water_capex",0)),
                    ("Installation",   _pr.get("installation_capex",0)),
                ]
            else:
                items = [
                    ("Structure",      _pr.get("structure_capex",0)),
                    ("Climate",        _pr.get("climate_capex",0)),
                    ("Irrigation",     _pr.get("irrigation_capex",0)),
                    ("Lighting",       _pr.get("lighting_capex",0)),
                    ("Automation",     _pr.get("automation_capex",0)),
                    ("Real Estate",    _pr.get("real_estate_capex",0)),
                ]
            for k, v in items:
                if v > 0:
                    rows.append(_row_fn(k, f"${v:,.0f}"))
            rows.append(_row_fn("Total CAPEX", f"${_tc:,.0f}", bold=True))
        return rows

    def _row_fn(key, val, bold=False):
        v_s = ps("RV",9.5,MONO_B if bold else MONO,INK,align=TA_RIGHT,sa=0)
        k_s = ps("RK",9,SANS_B if bold else SANS,INK if bold else INK_2,sa=0)
        return [Paragraph(key, k_s), Paragraph(val, v_s)]

    # ══════════════════════════════════════════════════════════════════════════
    # ASSEMBLE DOCUMENT
    # ══════════════════════════════════════════════════════════════════════════
    buf = io.BytesIO()
    doc = BaseDocTemplate(
        buf, pagesize=A4,
        leftMargin=LM, rightMargin=RM,
        topMargin=TM + 8*mm, bottomMargin=BM + 8*mm,
    )
    frame = Frame(LM, BM + 8*mm, BODY_W, PAGE_H - TM - BM - 16*mm, id="body")
    doc.addPageTemplates([PageTemplate(id="report", frames=[frame],
                                       onPage=_running_chrome)])
    story = []
    story += _page1()
    story.append(PageBreak())
    story += _page2()
    story.append(PageBreak())
    story += _page3()
    story.append(PageBreak())
    story += _page4()
    doc.build(story)
    return buf.getvalue()



with st.sidebar:
        st.markdown("### 🌱 Active Farm")
        try:
            _resp = supabase.table("farms").select(
                "id, name, modality, country, crop, footprint, levels, lights_tier, hvac, "
                "automation, price_scenario, price_override, packaging_cost, loss_rate, "
                "net_grow_factor, walkways_factor, water_price, rent_monthly, real_estate_capex, "
                "harvest_mode, depreciation_years, tax_rate, ltv, interest_rate, loan_term_years, "
                "lat, lon, crop_mix_json, ambient_temp_annual, mean_annual_dli, crop_source, discount_rate"
            ).order("created_at", desc=True).execute()
            _farms_list = _resp.data or []
        except Exception:
            _farms_list = []

        _active = st.session_state.get("active_farm")
        _active_name = _active["name"] if _active else None

        if _active:
            _mod_badge = {
                "vertical_farm": "🏭",
                "greenhouse": "🌿",
                "polytunnel": "🌿",
                "aquaponics_decoupled": "🐟",
                "aquaponics_coupled": "♻️",
            }.get(_active.get("modality", ""), "🌱")
            st.success(f"{_mod_badge} **{_active['name']}**")
            if _active.get("country"):
                st.caption(f"📍 {_active['country']}")
        else:
            st.info("No farm loaded. Select or create one below.")

        _farm_names = ["— select —"] + [f["name"] for f in _farms_list]
        _sel = st.selectbox(
            "Load farm",
            options=_farm_names,
            index=_farm_names.index(_active_name) if _active_name in _farm_names else 0,
            key="global_farm_selector",
        )

        if _sel != "— select —":
            _farm = next((f for f in _farms_list if f["name"] == _sel), None)
            if _farm and (not _active or _active.get("name") != _sel):
                if st.button("⬇️ Load", use_container_width=True, key="global_farm_load_btn"):
                    st.session_state["active_farm"]        = _farm
                    st.session_state["_pending_farm_load"] = _farm
                    st.session_state["gh_country"]         = _farm.get("country", "Germany")
                    st.session_state["gh_footprint"]       = int(_farm.get("footprint") or 5000)
                    st.session_state["gh_automation"]      = _farm.get("automation", "Medium")
                    _sl_gh_src = ("Polytunnel" if (_farm.get("crop_source") or "greenhouse").lower() == "polytunnel" else "Greenhouse")
                    st.session_state["gh_crop_source"]     = _sl_gh_src
                    _sl_gh_dict = POLYTUNNEL_CROPS if _sl_gh_src == "Polytunnel" else GREENHOUSE_CROPS
                    _sl_gh_crop = _farm.get("crop", "")
                    st.session_state["gh_crop"]            = _sl_gh_crop if _sl_gh_crop in _sl_gh_dict else list(_sl_gh_dict.keys())[0]
                    st.session_state["aq_country"]         = _farm.get("country", "Germany")
                    st.session_state["aq_plant_crop"]      = _farm.get("crop", "Lettuce (Butterhead)")
                    if _farm.get("lat") and _farm.get("lon"):
                        st.session_state["shared_lat"] = _farm["lat"]
                        st.session_state["shared_lng"] = _farm["lon"]
                        st.session_state["fim_lat"]    = _farm["lat"]
                        st.session_state["fim_lng"]    = _farm["lon"]
                    _mod = _farm.get("modality", "vertical_farm")
                    _mod_map = {
                        "vertical_farm":        "🏭 Indoor Vertical Farm",
                        "greenhouse":           "🌿 High-Tech Greenhouse",
                        "polytunnel":           "🌿 High-Tech Greenhouse",
                        "aquaponics_decoupled": "🐟 Decoupled Aquaponics",
                        "aquaponics_coupled":   "♻️ Coupled Aquaponics",
                    }
                    st.session_state["_pending_modality"] = _mod_map.get(_mod, "🏭 Indoor Vertical Farm")
                    st.rerun()

        if _active:
            if st.button("✖ Clear farm", use_container_width=True, key="global_farm_clear_btn"):
                st.session_state.pop("active_farm", None)
                st.rerun()

        st.divider()
        return st.session_state.get("active_farm")

if "show_save_farm_form" not in st.session_state:
    st.session_state["show_save_farm_form"] = False

# Sidebar widget default values — overwritten when a farm is loaded
_SIDEBAR_DEFAULTS = {
    "roi_country":           "Germany",
    "roi_crop":              "Lettuce (Butterhead)",
    "roi_footprint":         1000,
    "roi_levels":            5,
    "roi_lights_tier":       "Basic",
    "roi_hvac":              "Standard",
    "roi_automation":        "Medium",
    "roi_price_scenario":    "base",
    "roi_harvest_mode":      "Single",
    "roi_price_override":    0.0,
    "roi_packaging_cost":    0.15,
    "roi_loss_rate":         5.0,
    "roi_net_grow_factor":   85.0,
    "roi_walkways_factor":   15.0,
    "roi_water_price":       2.0,
    "roi_rent_monthly":      0.0,
    "roi_real_estate_capex": 0.0,
    "roi_depreciation_years": 10,
    "roi_tax_rate":          25.0,
    "roi_ltv":               60.0,
    "roi_interest_rate":     5.5,
    "roi_loan_term_years":   10,
}
for k, v in _SIDEBAR_DEFAULTS.items():
    if k not in st.session_state:
        st.session_state[k] = v

# ── Consume pending farm load (written by load handlers, applied before any widget renders)
if "_pending_farm_load" in st.session_state:
    _pf = st.session_state.pop("_pending_farm_load")

    # ── Parse crop mix once ───────────────────────────────────────────────────
    _pf_mix_raw = _pf.get("crop_mix_json")
    _pf_parsed_mix = None
    if _pf_mix_raw:
        try:
            _parsed_attempt = json.loads(_pf_mix_raw) if isinstance(_pf_mix_raw, str) else _pf_mix_raw
            if isinstance(_parsed_attempt, list) and _parsed_attempt:
                _pf_parsed_mix = _parsed_attempt
        except Exception:
            pass
    _pf_crop_fallback = _pf.get("crop", "Lettuce (Butterhead)")

    # ── Pop ALL widget-owned keys before writing so Streamlit treats them as
    #    freshly instantiated and respects the new values. ────────────────────
    _all_widget_keys = [
        # VF
        "roi_country", "roi_crop", "roi_footprint", "roi_levels",
        "roi_lights_tier", "roi_hvac", "roi_automation", "roi_price_scenario",
        "roi_harvest_mode", "roi_price_override", "roi_packaging_cost",
        "roi_loss_rate", "roi_net_grow_factor", "roi_walkways_factor",
        "roi_water_price", "roi_rent_monthly", "roi_real_estate_capex",
        "roi_depreciation_years", "roi_tax_rate", "roi_ltv",
        "roi_interest_rate", "roi_loan_term_years", "roi_multi_crop",
        # GH
        "gh_country", "gh_crop", "gh_footprint", "gh_crop_source",
        "gh_automation", "gh_price_scenario", "gh_harvest_mode",
        "gh_price_override", "gh_packaging_cost", "gh_loss_rate",
        "gh_net_grow_factor", "gh_walkways_factor", "gh_water_price",
        "gh_rent_monthly", "gh_real_estate_capex", "gh_depreciation_years",
        "gh_tax_rate", "gh_ltv", "gh_interest_rate", "gh_loan_term_years",
        "gh_discount_rate", "gh_multi_crop",
        # AQ
        "aq_country", "aq_plant_crop", "aq_plant_crop_source",
        "aq_plant_footprint", "aq_automation", "aq_price_scenario",
        "aq_harvest_mode", "aq_packaging_cost", "aq_loss_rate",
        "aq_net_grow_factor", "aq_walkways_factor", "aq_water_price",
        "aq_rent_monthly", "aq_real_estate_capex", "aq_depreciation_years",
        "aq_tax_rate", "aq_ltv", "aq_interest_rate", "aq_loan_term_years",
        "aq_discount_rate", "aq_multi_crop",
    ]
    for _k in _all_widget_keys:
        st.session_state.pop(_k, None)
    # Dynamic crop mix row keys (up to 6 rows, all three modality prefixes)
    for _i in range(6):
        for _pfx in ("roi", "gh", "aq"):
            st.session_state.pop(f"{_pfx}_mix_crop_{_i}", None)
            st.session_state.pop(f"{_pfx}_mix_pct_{_i}", None)

    # ── VF keys ───────────────────────────────────────────────────────────────
    st.session_state["roi_country"]            = _pf.get("country", "Germany")
    st.session_state["roi_crop"]               = _pf_crop_fallback
    st.session_state["roi_footprint"]          = int(_pf.get("footprint") or 1000)
    st.session_state["roi_levels"]             = int(_pf.get("levels") or 5)
    st.session_state["roi_lights_tier"]        = _pf.get("lights_tier", "Basic")
    st.session_state["roi_hvac"]               = _pf.get("hvac", "Standard")
    st.session_state["roi_automation"]         = _pf.get("automation", "Medium")
    st.session_state["roi_price_scenario"]     = _pf.get("price_scenario", "base")
    st.session_state["roi_harvest_mode"]       = _pf.get("harvest_mode", "Single")
    st.session_state["roi_price_override"]     = float(_pf.get("price_override") or 0.0)
    st.session_state["roi_packaging_cost"]     = float(_pf.get("packaging_cost") or 0.15)
    st.session_state["roi_loss_rate"]          = float(_pf.get("loss_rate") or 5.0)
    st.session_state["roi_net_grow_factor"]    = float(_pf.get("net_grow_factor") or 85.0)
    st.session_state["roi_walkways_factor"]    = float(_pf.get("walkways_factor") or 15.0)
    st.session_state["roi_water_price"]        = float(_pf.get("water_price") or 2.0)
    st.session_state["roi_rent_monthly"]       = float(_pf.get("rent_monthly") or 0.0)
    st.session_state["roi_real_estate_capex"]  = float(_pf.get("real_estate_capex") or 0.0)
    st.session_state["roi_depreciation_years"] = int(_pf.get("depreciation_years") or 10)
    st.session_state["roi_tax_rate"]           = float(_pf.get("tax_rate") or 25.0)
    st.session_state["roi_ltv"]                = float(_pf.get("ltv") or 60.0)
    st.session_state["roi_interest_rate"]      = float(_pf.get("interest_rate") or 5.5)
    st.session_state["roi_loan_term_years"]    = int(_pf.get("loan_term_years") or 10)
    # Filter mix to only crops valid in the VF CROPS dict
    _vf_valid_fallback = (_pf_crop_fallback if _pf_crop_fallback in CROPS
                          else list(CROPS.keys())[0])
    _vf_filtered_mix = ([row for row in _pf_parsed_mix if row.get("crop") in CROPS]
                        if _pf_parsed_mix else [])
    if _vf_filtered_mix:
        st.session_state["roi_multi_crop"] = True
        st.session_state["roi_crop_mix"]   = _vf_filtered_mix
        for _i, _row in enumerate(_vf_filtered_mix):
            st.session_state[f"roi_mix_crop_{_i}"] = _row.get("crop", _vf_valid_fallback)
            st.session_state[f"roi_mix_pct_{_i}"]  = int(_row.get("pct", 100))
    else:
        st.session_state["roi_multi_crop"] = False
        st.session_state["roi_crop_mix"]   = [{"crop": _vf_valid_fallback, "pct": 100}]

    # ── GH keys ───────────────────────────────────────────────────────────────
    _gh_crop_source_raw = (_pf.get("crop_source") or "greenhouse").lower()
    _gh_crop_source_val = "Polytunnel" if _gh_crop_source_raw == "polytunnel" else "Greenhouse"
    _gh_valid_dict      = POLYTUNNEL_CROPS if _gh_crop_source_val == "Polytunnel" else GREENHOUSE_CROPS
    _gh_crop_fallback   = _pf.get("crop", "Tomato (Beef)")
    _gh_valid_fallback  = _gh_crop_fallback if _gh_crop_fallback in _gh_valid_dict else list(_gh_valid_dict.keys())[0]
    st.session_state["gh_country"]            = _pf.get("country", "Germany")
    st.session_state["gh_crop"]               = _gh_valid_fallback
    st.session_state["gh_footprint"]          = int(_pf.get("footprint") or 1000)
    st.session_state["gh_crop_source"]        = _gh_crop_source_val
    st.session_state["gh_automation"]         = _pf.get("automation", "Medium")
    st.session_state["gh_price_scenario"]     = _pf.get("price_scenario", "base")
    st.session_state["gh_harvest_mode"]       = _pf.get("harvest_mode", "Single")
    st.session_state["gh_price_override"]     = float(_pf.get("price_override") or 0.0)
    st.session_state["gh_packaging_cost"]     = float(_pf.get("packaging_cost") or 0.15)
    st.session_state["gh_loss_rate"]          = float(_pf.get("loss_rate") or 5.0)
    st.session_state["gh_net_grow_factor"]    = float(_pf.get("net_grow_factor") or 85.0)
    st.session_state["gh_walkways_factor"]    = float(_pf.get("walkways_factor") or 15.0)
    st.session_state["gh_water_price"]        = float(_pf.get("water_price") or 2.0)
    st.session_state["gh_rent_monthly"]       = float(_pf.get("rent_monthly") or 0.0)
    st.session_state["gh_real_estate_capex"]  = float(_pf.get("real_estate_capex") or 0.0)
    st.session_state["gh_depreciation_years"] = int(_pf.get("depreciation_years") or 10)
    st.session_state["gh_tax_rate"]           = float(_pf.get("tax_rate") or 25.0)
    st.session_state["gh_ltv"]                = float(_pf.get("ltv") or 60.0)
    st.session_state["gh_interest_rate"]      = float(_pf.get("interest_rate") or 5.5)
    st.session_state["gh_loan_term_years"]    = int(_pf.get("loan_term_years") or 10)
    st.session_state["gh_discount_rate"]      = float(_pf.get("discount_rate") or 8.0)
    # Filter mix to only crops valid in the GH crop source dict
    _gh_filtered_mix = ([row for row in _pf_parsed_mix if row.get("crop") in _gh_valid_dict]
                        if _pf_parsed_mix else [])
    if _gh_filtered_mix:
        st.session_state["gh_multi_crop"] = True
        st.session_state["gh_crop_mix"]   = _gh_filtered_mix
        for _i, _row in enumerate(_gh_filtered_mix):
            st.session_state[f"gh_mix_crop_{_i}"] = _row.get("crop", _gh_valid_fallback)
            st.session_state[f"gh_mix_pct_{_i}"]  = int(_row.get("pct", 100))
    else:
        st.session_state["gh_multi_crop"] = False
        st.session_state["gh_crop_mix"]   = [{"crop": _gh_valid_fallback, "pct": 100}]

    # ── AQ keys ───────────────────────────────────────────────────────────────
    _aq_crop_fallback = _pf.get("crop", "Lettuce (Romaine)")
    st.session_state["aq_country"]            = _pf.get("country", "Germany")
    st.session_state["aq_plant_crop"]         = _aq_crop_fallback
    st.session_state["aq_plant_crop_source"]  = (
        "Polytunnel" if (_pf.get("crop_source") or "greenhouse").lower() == "polytunnel"
        else "Greenhouse"
    )
    st.session_state["aq_plant_footprint"]    = int(_pf.get("footprint") or 1000)
    st.session_state["aq_automation"]         = _pf.get("automation", "Medium")
    st.session_state["aq_price_scenario"]     = _pf.get("price_scenario", "base")
    st.session_state["aq_harvest_mode"]       = _pf.get("harvest_mode", "Single")
    st.session_state["aq_packaging_cost"]     = float(_pf.get("packaging_cost") or 0.15)
    st.session_state["aq_loss_rate"]          = float(_pf.get("loss_rate") or 5.0)
    st.session_state["aq_net_grow_factor"]    = float(_pf.get("net_grow_factor") or 90.0)
    st.session_state["aq_walkways_factor"]    = float(_pf.get("walkways_factor") or 10.0)
    st.session_state["aq_water_price"]        = float(_pf.get("water_price") or 2.0)
    st.session_state["aq_rent_monthly"]       = float(_pf.get("rent_monthly") or 0.0)
    st.session_state["aq_real_estate_capex"]  = float(_pf.get("real_estate_capex") or 0.0)
    st.session_state["aq_depreciation_years"] = int(_pf.get("depreciation_years") or 15)
    st.session_state["aq_tax_rate"]           = float(_pf.get("tax_rate") or 25.0)
    st.session_state["aq_ltv"]                = float(_pf.get("ltv") or 60.0)
    st.session_state["aq_interest_rate"]      = float(_pf.get("interest_rate") or 5.5)
    st.session_state["aq_loan_term_years"]    = int(_pf.get("loan_term_years") or 15)
    st.session_state["aq_discount_rate"]      = float(_pf.get("discount_rate") or 8.0)
    # AQ fish/tank params — stored in metadata jsonb if present
    _pf_meta = _pf.get("metadata") or {}
    if isinstance(_pf_meta, str):
        try:
            _pf_meta = json.loads(_pf_meta)
        except Exception:
            _pf_meta = {}
    if _pf_meta.get("species"):
        st.session_state["aq_species"]       = _pf_meta["species"]
    if _pf_meta.get("tank_volume_m3"):
        st.session_state["aq_tank_volume_m3"] = float(_pf_meta["tank_volume_m3"])
    if _pf_meta.get("target_temp_c"):
        st.session_state["aq_target_temp_c"]  = float(_pf_meta["target_temp_c"])
    # Filter mix to only crops valid in the AQ plant crop source dict
    _aq_crop_source_for_filter = (_pf.get("crop_source") or "greenhouse").lower()
    _aq_valid_dict = POLYTUNNEL_CROPS if _aq_crop_source_for_filter == "polytunnel" else GREENHOUSE_CROPS
    _aq_valid_fallback = (list(_aq_valid_dict.keys())[0]
                          if _aq_crop_fallback not in _aq_valid_dict else _aq_crop_fallback)
    _aq_filtered_mix = ([row for row in _pf_parsed_mix if row.get("crop") in _aq_valid_dict]
                        if _pf_parsed_mix else [])
    if _aq_filtered_mix:
        st.session_state["aq_multi_crop"] = True
        st.session_state["aq_crop_mix"]   = _aq_filtered_mix
        for _i, _row in enumerate(_aq_filtered_mix):
            st.session_state[f"aq_mix_crop_{_i}"] = _row.get("crop", _aq_valid_fallback)
            st.session_state[f"aq_mix_pct_{_i}"]  = int(_row.get("pct", 100))
    else:
        st.session_state["aq_multi_crop"] = False
        st.session_state["aq_crop_mix"]   = [{"crop": _aq_valid_fallback, "pct": 100}]

def _run_multicrop_generic(base_inputs: dict, crop_mix: list,
                            calc_fn, crop_data_dict: dict,
                            dli_key: str = "dli") -> dict:
    """
    Generic multi-crop aggregation engine used by all modalities.
    calc_fn:        the calculation function (calculate or calculate_greenhouse)
    crop_data_dict: the crop dictionary to read DLI from (CROPS, GREENHOUSE_CROPS, etc.)
    dli_key:        field name for DLI in the crop dict (default "dli")
    """
    import copy as _copy
    total_pct = sum(row["pct"] for row in crop_mix)
    if total_pct == 0:
        return calc_fn(base_inputs)

    # Per-crop sub-area runs
    crop_results = []
    for row in crop_mix:
        frac    = row["pct"] / total_pct
        sub_inp = _copy.deepcopy(base_inputs)
        sub_inp["crop"]      = row["crop"]
        sub_inp["footprint"] = base_inputs["footprint"] * frac
        crop_results.append((frac, row["crop"], calc_fn(sub_inp)))

    # Aggregate revenue and operating costs
    annual_revenue       = sum(cr["annual_revenue"]       for _, _, cr in crop_results)
    annual_variable_cost = sum(cr["annual_variable_cost"] for _, _, cr in crop_results)
    annual_water_cost    = sum(cr["annual_water_cost"]    for _, _, cr in crop_results)
    annual_labour_cost   = sum(cr["annual_labour_cost"]   for _, _, cr in crop_results)
    annual_rent          = crop_results[0][2]["annual_rent"]

    # Single energy calculation using area-weighted DLI
    _ref_crop    = max(crop_mix, key=lambda r: crop_data_dict[r["crop"]][dli_key])["crop"]
    weighted_dli = sum(crop_data_dict[cn][dli_key] * f for f, cn, _ in crop_results)
    _orig        = crop_data_dict[_ref_crop]
    _patched     = _copy.deepcopy(_orig)
    _patched[dli_key] = weighted_dli
    crop_data_dict[_ref_crop] = _patched
    _energy_inp  = _copy.deepcopy(base_inputs)
    _energy_inp["crop"] = _ref_crop
    try:
        _energy_r = calc_fn(_energy_inp)
    finally:
        crop_data_dict[_ref_crop] = _orig
    annual_energy_cost = _energy_r["annual_energy_cost"]
    total_annual_kwh   = _energy_r.get("total_annual_kwh") or _energy_r.get("annual_kwh", 0)

    # Single CAPEX calculation using highest-DLI crop
    _capex_inp = _copy.deepcopy(base_inputs)
    _capex_inp["crop"] = _ref_crop
    _capex_r = calc_fn(_capex_inp)
    total_capex        = _capex_r["total_capex"]
    annual_maintenance = _capex_r["annual_maintenance"]

    # EBITDA and financial layer
    total_annual_costs = (annual_energy_cost + annual_variable_cost +
                          annual_water_cost + annual_labour_cost +
                          annual_rent + annual_maintenance)
    ebitda        = annual_revenue - total_annual_costs
    ebitda_margin = ebitda / annual_revenue if annual_revenue > 0 else 0.0

    annual_depreciation = _capex_r["annual_depreciation"]
    annual_debt_service = _capex_r["annual_debt_service"]
    dscr            = ebitda / annual_debt_service if annual_debt_service > 0 else None
    equity_invested = total_capex * (1 - base_inputs["ltv"] / 100)
    annual_fcfe     = (ebitda - annual_debt_service
                       - annual_depreciation * (base_inputs["tax_rate"] / 100))
    payback_years   = (equity_invested / annual_fcfe
                       if annual_fcfe > 0 and equity_invested > 0 else None)

    _disc = base_inputs.get("discount_rate", 8.0) / 100
    dcf_cashflows  = []
    cumulative_npv = -equity_invested
    for yr in range(1, 11):
        pv = annual_fcfe / ((1 + _disc) ** yr)
        cumulative_npv += pv
        dcf_cashflows.append({"year": yr, "fcfe": annual_fcfe,
                               "pv": pv, "cumulative_npv": cumulative_npv})

    combined = dict(_capex_r)
    combined.update({
        "annual_revenue":       annual_revenue,
        "annual_energy_cost":   annual_energy_cost,
        "annual_variable_cost": annual_variable_cost,
        "annual_water_cost":    annual_water_cost,
        "annual_labour_cost":   annual_labour_cost,
        "annual_maintenance":   annual_maintenance,
        "annual_rent":          annual_rent,
        "total_annual_costs":   total_annual_costs,
        "ebitda":               ebitda,
        "ebitda_margin":        ebitda_margin,
        "total_capex":          total_capex,
        "total_annual_kwh":     total_annual_kwh,
        "annual_kwh":           total_annual_kwh,
        "annual_depreciation":  annual_depreciation,
        "annual_debt_service":  annual_debt_service,
        "dscr":                 dscr,
        "payback_years":        payback_years,
        "dcf_cashflows":        dcf_cashflows,
        "npv":                  cumulative_npv,
        "total_annual_kg":      sum(cr["total_annual_kg"] for _, _, cr in crop_results),
        "_is_multicrop":        True,
        "_crop_results": [
            {
                "crop":                 cn,
                "pct":                  f * 100,
                "annual_revenue":       cr["annual_revenue"],
                "annual_variable_cost": cr["annual_variable_cost"],
                "annual_labour_cost":   cr["annual_labour_cost"],
                "annual_water_cost":    cr["annual_water_cost"],
                "ebitda":               cr["ebitda"],
                "total_annual_kg":      cr["total_annual_kg"],
                "effective_price":      cr["effective_price"],
            }
            for f, cn, cr in crop_results
        ],
    })
    return combined

# Apply pending modality switch (set by load handlers, applied before radio renders)
if "_pending_modality" in st.session_state:
    st.session_state["cea_modality"] = st.session_state.pop("_pending_modality")

# ── Persistent farm context (top of sidebar, all modalities) ────────────
_active_farm_global = render_farm_context_sidebar(supabase=supabase)

# ── Setup gate — no farm loaded ──────────────────────────────────────────
if not _active_farm_global:
    st.title("📊 CEA Feasibility Calculator")
    st.info(
        "**No farm profile loaded.**\n\n"
        "Select an existing farm profile in the sidebar to run the analysis, "
        "or configure the parameters below and use **Save as Farm Profile** to create one.\n\n"
        "👈 Use the sidebar to load or create a farm."
    )
    st.markdown("---")
    st.caption(
        "First time? Pick a modality, fill in the parameters below, run the calculation, "
        "then click 💾 Save as Farm Profile at the bottom of the results."
    )

modality = st.radio(
    "Select farming modality",
    options=[
        "🏭 Indoor Vertical Farm",
        "🌿 High-Tech Greenhouse",
        "🐟 Decoupled Aquaponics",
        "♻️ Coupled Aquaponics",
    ],
    horizontal=True,
    key="cea_modality",
)

if modality == "🏭 Indoor Vertical Farm":

    # ── Sidebar ───────────────────────────────────────────────────────────────────
    with st.sidebar:
        st.header("Farm Parameters")
    
        # ── Farm parameters ───────────────────────────────────────────────────────
        country_list = list(COUNTRIES.keys())
        _c_default   = st.session_state["roi_country"]
        country = st.selectbox("Country", country_list,
                               index=country_list.index(_c_default) if _c_default in country_list else 0,
                               key="roi_country")
    
        # ── Multi-crop toggle ─────────────────────────────────────────────────
        multi_crop_mode = st.toggle("Multi-crop mode",
                                     value=st.session_state.get("roi_multi_crop", False),
                                     key="roi_multi_crop")

        if not multi_crop_mode:
            crop_list   = list(CROPS.keys())
            _cr_default = st.session_state["roi_crop"]
            crop = st.selectbox("Crop", crop_list,
                                index=crop_list.index(_cr_default) if _cr_default in crop_list else 0,
                                key="roi_crop")
        else:
            crop = list(CROPS.keys())[0]  # placeholder — unused in multi-crop mode
            st.markdown("**Crop allocation** (must sum to 100%)")
            if "roi_crop_mix" not in st.session_state:
                st.session_state["roi_crop_mix"] = [{"crop": "Lettuce (Butterhead)", "pct": 100}]
            _mix = st.session_state["roi_crop_mix"]
            _crop_list_all = list(CROPS.keys())
            _to_remove = None
            for _ci, _row in enumerate(_mix):
                _rc1, _rc2, _rc3 = st.columns([4, 2, 1])
                with _rc1:
                    _mix[_ci]["crop"] = st.selectbox(
                        f"Crop {_ci+1}", _crop_list_all,
                        index=_crop_list_all.index(_row["crop"]) if _row["crop"] in _crop_list_all else 0,
                        key=f"roi_mix_crop_{_ci}")
                with _rc2:
                    _mix[_ci]["pct"] = st.number_input(
                        "%", min_value=1, max_value=100, value=int(_row["pct"]),
                        step=1, key=f"roi_mix_pct_{_ci}")
                with _rc3:
                    if len(_mix) > 1 and st.button("✕", key=f"roi_mix_del_{_ci}"):
                        _to_remove = _ci
            if _to_remove is not None:
                _mix.pop(_to_remove)
                st.session_state["roi_crop_mix"] = _mix
                st.rerun()
            _total_pct = sum(r["pct"] for r in _mix)
            st.caption(f"Total allocated: **{_total_pct}%**")
            if _total_pct != 100:
                st.warning(f"⚠️ Must sum to 100%. Currently {_total_pct}%.")
            if len(_mix) < 6:
                if st.button("➕ Add crop", key="roi_mix_add"):
                    _mix.append({"crop": _crop_list_all[0], "pct": 1})
                    st.session_state["roi_crop_mix"] = _mix
                    st.rerun()
            st.session_state["roi_crop_mix"] = _mix
    
        st.divider()
        footprint = st.number_input("Footprint (m²)", value=st.session_state["roi_footprint"],
                                    step=100, min_value=50, key="roi_footprint")
        levels    = st.number_input("Levels", value=st.session_state["roi_levels"],
                                    min_value=1, max_value=20, step=1, key="roi_levels")
    
        st.divider()
        lights_list    = list(LIGHTS.keys())
        _lt_default    = st.session_state["roi_lights_tier"]
        lights_tier    = st.selectbox("Lights", lights_list,
                                      index=lights_list.index(_lt_default) if _lt_default in lights_list else 1,
                                      key="roi_lights_tier")
    
        hvac_list   = ["Excellent conditions", "Standard", "High HVAC"]
        _hv_default = st.session_state["roi_hvac"]
        hvac        = st.selectbox("HVAC", hvac_list,
                                   index=hvac_list.index(_hv_default) if _hv_default in hvac_list else 1,
                                   key="roi_hvac")
    
        auto_list   = ["None", "Low", "Medium", "High"]
        _au_default = st.session_state["roi_automation"]
        automation  = st.selectbox("Automation", auto_list,
                                   index=auto_list.index(_au_default) if _au_default in auto_list else 2,
                                   key="roi_automation")
    
        ps_list     = ["base", "low", "high"]
        _ps_default = st.session_state["roi_price_scenario"]
        price_scenario = st.selectbox("Price Scenario", ps_list,
                                      index=ps_list.index(_ps_default) if _ps_default in ps_list else 0,
                                      key="roi_price_scenario")
    
        # Harvest mode — only enable multi-harvest if crop supports it
        crop_data = CROPS[crop]
        if crop_data["days_between"] > 0:
            hm_list     = ["Single", "2 Harvests", "3 Harvests"]
            _hm_default = st.session_state["roi_harvest_mode"]
            harvest_mode = st.selectbox("Harvest Mode", hm_list,
                                        index=hm_list.index(_hm_default) if _hm_default in hm_list else 0,
                                        key="roi_harvest_mode")
        else:
            st.selectbox("Harvest Mode", ["Single"], disabled=True,
                         help="This crop only supports single harvest.")
            harvest_mode = "Single"
            st.session_state["roi_harvest_mode"] = "Single"
    
        st.divider()
        st.subheader("Advanced")
        price_override    = st.number_input("Price Override ($/kg, 0=auto)",
                                            value=st.session_state["roi_price_override"],
                                            step=0.1, min_value=0.0, key="roi_price_override")
        packaging_cost    = st.number_input("Packaging ($/kg)",
                                            value=st.session_state["roi_packaging_cost"],
                                            step=0.01, min_value=0.0, key="roi_packaging_cost")
        loss_rate         = st.number_input("Loss Rate (%)",
                                            value=st.session_state["roi_loss_rate"],
                                            step=0.5, min_value=0.0, max_value=100.0, key="roi_loss_rate")
        net_grow_factor   = st.number_input("Net Grow Factor (%)",
                                            value=st.session_state["roi_net_grow_factor"],
                                            step=1.0, min_value=1.0, max_value=100.0, key="roi_net_grow_factor")
        walkways_factor   = st.number_input("Walkways Factor (%)",
                                            value=st.session_state["roi_walkways_factor"],
                                            step=1.0, min_value=0.0, max_value=50.0, key="roi_walkways_factor")
        water_price       = st.number_input("Water Price ($/m³)",
                                            value=st.session_state["roi_water_price"],
                                            step=0.1, min_value=0.0, key="roi_water_price")
        rent_monthly      = st.number_input("Monthly Rent ($)",
                                            value=st.session_state["roi_rent_monthly"],
                                            step=100.0, min_value=0.0, key="roi_rent_monthly")
        real_estate_capex = st.number_input("Real Estate CAPEX ($)",
                                            value=st.session_state["roi_real_estate_capex"],
                                            step=10000.0, min_value=0.0, key="roi_real_estate_capex")
    
        st.divider()
        st.subheader("Financial Structure")
        depreciation_years  = st.number_input("Depreciation (years)",
                                              value=st.session_state["roi_depreciation_years"],
                                              step=1, min_value=1, key="roi_depreciation_years")
        tax_rate_input      = st.number_input("Tax Rate (%)",
                                              value=st.session_state["roi_tax_rate"],
                                              step=1.0, min_value=0.0, max_value=100.0, key="roi_tax_rate")
        ltv_input           = st.number_input("LTV (%)",
                                              value=st.session_state["roi_ltv"],
                                              step=5.0, min_value=0.0, max_value=100.0, key="roi_ltv")
        interest_rate_input = st.number_input("Interest Rate (%)",
                                              value=st.session_state["roi_interest_rate"],
                                              step=0.1, min_value=0.0, key="roi_interest_rate")
        loan_term_years     = st.number_input("Loan Term (years)",
                                              value=st.session_state["roi_loan_term_years"],
                                              step=1, min_value=1, key="roi_loan_term_years")
    
    # ── Run calculation ───────────────────────────────────────────────────────────
    inputs = {
        "country":           country,
        "crop":              crop,
        "footprint":         footprint,
        "levels":            levels,
        "lights_tier":       lights_tier,
        "hvac":              hvac,
        "automation":        automation,
        "price_scenario":    price_scenario,
        "price_override":    price_override,
        "packaging_cost":    packaging_cost,
        "loss_rate":         loss_rate,
        "net_grow_factor":   net_grow_factor,
        "walkways_factor":   walkways_factor,
        "water_price":       water_price,
        "rent_monthly":      rent_monthly,
        "real_estate_capex": real_estate_capex,
        "harvest_mode":      harvest_mode,
        "depreciation_years": depreciation_years,
        "tax_rate":          tax_rate_input,
        "ltv":               ltv_input,
        "interest_rate":     interest_rate_input,
        "loan_term_years":   loan_term_years,
        "discount_rate":     8.0,
    }
    
    def run_multicrop(base_inputs: dict, crop_mix: list) -> dict:
        import core.data_tables as _dt
        return _run_multicrop_generic(base_inputs, crop_mix, calculate, _dt.CROPS)

    # Guard: ensure all dict lookups are valid before calculation.
    # Fields can be None if a non-VF farm was loaded and session state bled over.
    from core.data_tables import LIGHTS as _LIGHTS_CHECK, HVAC_FACTORS as _HVAC_CHECK
    if not inputs.get("lights_tier") or inputs["lights_tier"] not in _LIGHTS_CHECK:
        inputs["lights_tier"] = "Basic"
    if not inputs.get("hvac") or inputs["hvac"] not in _HVAC_CHECK:
        inputs["hvac"] = "Standard"
    if not inputs.get("crop") or inputs["crop"] not in CROPS:
        inputs["crop"] = list(CROPS.keys())[0]
    if not inputs.get("country") or inputs["country"] not in COUNTRIES:
        inputs["country"] = "Germany"

    _multi_crop_mode = st.session_state.get("roi_multi_crop", False)
    _crop_mix        = st.session_state.get("roi_crop_mix", [])

    # Sanitise locally — only keep crops valid in VF CROPS dict
    # Do NOT write back to session state here (widget already rendered)
    _crop_mix  = [row for row in _crop_mix if row.get("crop") in CROPS]
    if not _crop_mix:
        _multi_crop_mode = False

    _mix_total       = sum(row["pct"] for row in _crop_mix)
    _mix_valid       = _multi_crop_mode and len(_crop_mix) > 0 and _mix_total == 100

    if _multi_crop_mode and not _mix_valid:
        st.warning("⚠️ Fix crop allocation (must sum to 100%) before results are shown.")
        st.stop()

    if _mix_valid:
        r = run_multicrop(inputs, _crop_mix)
    else:
        r = calculate(inputs)

    # ── Climate profile display ───────────────────────────────────────────────
    _active_farm_data = st.session_state.get("active_farm")
    if _active_farm_data and _active_farm_data.get("mean_annual_dli"):
        _loc_dli  = _active_farm_data["mean_annual_dli"]
        _loc_temp = _active_farm_data["ambient_temp_annual"]
        _crop_dli = CROPS[crop]["dli"]
        _nat_frac = compute_natural_dli_fraction(_loc_dli, _crop_dli)
        st.caption(
            f"🌤️ **Climate profile active** — "
            f"Mean annual DLI: {_loc_dli:.1f} mol/m²/day · "
            f"Ambient temperature: {_loc_temp:.1f}°C · "
            f"Natural DLI coverage for {crop}: {_nat_frac*100:.0f}% "
            f"({'supplemental lighting required' if _nat_frac < 1.0 else 'no supplemental lighting required'})"
        )
    
    # ── PDF Report Generator ─────────────────────────────────────────────────
    def generate_pdf_report(inputs: dict, r: dict) -> bytes:
        _fn = st.session_state.get("active_farm", {}).get("name", "")
        return _build_feasibility_pdf(r, inputs, "vf", farm_name=_fn)

    # ── Key metrics ───────────────────────────────────────────────────────────────
    # ── PDF Download Button ───────────────────────────────────────────────────
    pdf_col1, pdf_col2 = st.columns([5, 1])
    with pdf_col2:
        if st.button("📄 Download PDF Report", use_container_width=True):
            with st.spinner("Generating PDF..."):
                pdf_bytes = generate_pdf_report(inputs, r)
                filename = f"CEA_Report_{inputs['crop'].replace(' ', '_').replace('/', '')}_{inputs['country']}_{date.today().strftime('%Y%m%d')}.pdf"
                st.download_button(
                    label="⬇️ Save PDF",
                    data=pdf_bytes,
                    file_name=filename,
                    mime="application/pdf",
                    use_container_width=True,
                )
    st.divider()
    
    st.subheader("Key Metrics")
    
    # Break-even yield: minimum kg/m²/cycle needed to cover all costs
    # Back-solved from: revenue = total_costs
    # breakeven_yield = total_costs / (price * (1-loss) * cycles * ega)
    _loss = inputs.get("loss_rate", 5) / 100
    _denominator = r["effective_price"] * (1 - _loss) * r["cycles_per_year"] * r["effective_grow_area"]
    breakeven_yield = r["total_annual_costs"] / _denominator if _denominator > 0 else None
    projected_yield = CROPS[crop]["yield"]
    
    if breakeven_yield is not None:
        yield_gap_pct = (projected_yield - breakeven_yield) / breakeven_yield * 100
        yield_gap_str = f"{yield_gap_pct:+.1f}%"
    else:
        yield_gap_str = "N/A"
    
    m1, m2, m3, m4, m5, m6, m7 = st.columns(7)
    m1.metric("Annual Revenue",   f"${r['annual_revenue']:,.0f}")
    m2.metric("EBITDA",           f"${r['ebitda']:,.0f}")
    m3.metric("EBITDA Margin",    f"{r['ebitda_margin']*100:.1f}%")
    m4.metric("Total CAPEX",      f"${r['total_capex']:,.0f}")
    m5.metric("Payback",          f"{r['payback_years']:.1f} yrs" if r["payback_years"] else "N/A")
    m6.metric("DSCR",             f"{r['dscr']:.2f}" if r["dscr"] else "N/A")
    m7.metric(
        "Break-even Yield",
        f"{breakeven_yield:.2f} kg/m²/cycle" if breakeven_yield else "N/A",
        delta=yield_gap_str if breakeven_yield else None,
        delta_color="normal",
        help="Minimum yield needed to cover all costs. Delta = projected crop yield vs this threshold."
    )
    
    # ── Multi-crop breakdown ──────────────────────────────────────────────────
    if r.get("_is_multicrop"):
        st.divider()
        st.subheader("Per-Crop Breakdown")
        _mc_rows = []
        for _mc in r["_crop_results"]:
            _mc_rows.append({
                "Crop":           _mc["crop"],
                "Area %":         f"{_mc['pct']:.0f}%",
                "Annual kg":      f"{_mc['total_annual_kg']:,.0f}",
                "Price ($/kg)":   f"${_mc['effective_price']:.2f}",
                "Revenue":        f"${_mc['annual_revenue']:,.0f}",
                "Variable Cost":  f"${_mc['annual_variable_cost']:,.0f}",
                "Labour":         f"${_mc['annual_labour_cost']:,.0f}",
                "EBITDA contrib": f"${_mc['ebitda']:,.0f}",
            })
        st.dataframe(pd.DataFrame(_mc_rows), use_container_width=True, hide_index=True)
        st.caption(
            "Energy cost and CAPEX are shared farm infrastructure — "
            "computed once on the full farm area and shown in the combined metrics above."
        )
        st.divider()

    # ── DSCR warning ─────────────────────────────────────────────────────────────
    if r.get("dscr") is not None and r["dscr"] < 1.0:
        st.warning(
            f"⚠️ **Debt service coverage is low (DSCR = {r['dscr']:.2f}x).** "
            f"Annual debt repayment (${r['annual_debt_service']:,.0f}) exceeds EBITDA (${r['ebitda']:,.0f}). "
            f"Consider reducing LTV, extending the loan term, increasing farm scale, or selecting a higher-margin crop."
        )

    # ── Save as Farm Profile ──────────────────────────────────────────────────
    st.divider()
    save_col1, save_col2 = st.columns([5, 1])
    with save_col2:
        if st.button("💾 Save as Farm Profile", use_container_width=True):
            st.session_state["show_save_farm_form"] = True
    
    if st.session_state["show_save_farm_form"]:
        with st.container(border=True):
            _vf_active  = st.session_state.get("active_farm")
            _save_lat = st.session_state.get("shared_lat")
            _save_lon = st.session_state.get("shared_lng")
            _climate_data = {}
            if _save_lat and _save_lon:
                with st.spinner("🌤️ Fetching climate profile for this location…"):
                    try:
                        from core.climate import fetch_climate_profile
                        _climate_data = fetch_climate_profile(_save_lat, _save_lon)
                    except Exception:
                        _climate_data = {}
            _vf_payload = {
                "country":           inputs["country"],
                "crop":              (_crop_mix[0]["crop"] if _mix_valid and _crop_mix else inputs["crop"]),
                "footprint":         inputs["footprint"],
                "levels":            inputs["levels"],
                "lights_tier":       inputs["lights_tier"],
                "hvac":              inputs["hvac"],
                "automation":        inputs["automation"],
                "price_scenario":    inputs["price_scenario"],
                "price_override":    inputs["price_override"],
                "packaging_cost":    inputs["packaging_cost"],
                "loss_rate":         inputs["loss_rate"],
                "net_grow_factor":   inputs["net_grow_factor"],
                "walkways_factor":   inputs["walkways_factor"],
                "water_price":       inputs["water_price"],
                "rent_monthly":      inputs["rent_monthly"],
                "real_estate_capex": inputs["real_estate_capex"],
                "harvest_mode":      inputs["harvest_mode"],
                "depreciation_years": inputs["depreciation_years"],
                "tax_rate":          inputs["tax_rate"],
                "ltv":               inputs["ltv"],
                "interest_rate":     inputs["interest_rate"],
                "loan_term_years":   inputs["loan_term_years"],
                "lat":               st.session_state.get("shared_lat"),
                "lon":               st.session_state.get("shared_lng"),
                "ambient_temp_annual": _climate_data.get("ambient_temp_annual"),
                "mean_annual_dli":     _climate_data.get("mean_annual_dli"),
                "agriculture_type":  "vertical_farm",
                "modality":          "vertical_farm",
                "metadata":          {},
                "model_snapshot":    json.dumps(r),
                "model_updated_at":  date.today().isoformat(),
                "crop_mix_json":     json.dumps(_crop_mix) if _mix_valid else None,
                "notes":             None,
            }
            if _vf_active:
                st.markdown(f"**Update** existing farm **{_vf_active['name']}**, or save as a new profile.")
                _vu1, _vu2, _vu3 = st.columns([2, 2, 1])
                with _vu1:
                    if st.button("✅ Update existing farm", use_container_width=True, key="vf_update_btn"):
                        try:
                            supabase.table("farms").update(_vf_payload).eq("id", _vf_active["id"]).execute()
                            st.session_state["active_farm"] = {**_vf_active, **_vf_payload}
                            st.success(f"✅ Farm **{_vf_active['name']}** updated.")
                            if _climate_data.get("mean_annual_dli"):
                                st.caption(f"🌤️ Climate profile saved — Mean DLI: {_climate_data['mean_annual_dli']:.1f} mol/m²/day · Ambient temp: {_climate_data['ambient_temp_annual']:.1f}°C")
                            st.session_state["show_save_farm_form"] = False
                            st.rerun()
                        except Exception as e:
                            st.error(f"Update failed: {e}")
                with _vu2:
                    farm_profile_name = st.text_input("New farm name", key="farm_profile_name_input", placeholder="Enter name for new profile")
                    if st.button("➕ Save as new farm", use_container_width=True, key="vf_saveas_btn"):
                        if not farm_profile_name.strip():
                            st.error("Please enter a name for the new farm profile.")
                        else:
                            try:
                                supabase.table("farms").insert({**_vf_payload, "name": farm_profile_name.strip(), "owner_id": current_user()}).execute()
                                st.success(f"✅ New farm profile '{farm_profile_name.strip()}' saved.")
                                if _climate_data.get("mean_annual_dli"):
                                    st.caption(f"🌤️ Climate profile saved — Mean DLI: {_climate_data['mean_annual_dli']:.1f} mol/m²/day · Ambient temp: {_climate_data['ambient_temp_annual']:.1f}°C")
                                st.session_state["show_save_farm_form"] = False
                                st.rerun()
                            except Exception as e:
                                st.error(f"Could not save: {e}")
                with _vu3:
                    if st.button("✖ Cancel", use_container_width=True, key="vf_cancel_save"):
                        st.session_state["show_save_farm_form"] = False
                        st.rerun()
            else:
                st.markdown("**Save current configuration as a Farm Profile**")
                st.caption("Saves all parameters so you can track harvests in the Harvest Tracker.")
                farm_profile_name = st.text_input("Farm name", key="farm_profile_name_input")
                _vn1, _vn2 = st.columns([3, 1])
                with _vn1:
                    if st.button("✅ Confirm Save", use_container_width=True, key="vf_confirm_save"):
                        if not farm_profile_name.strip():
                            st.error("Please enter a farm name.")
                        else:
                            try:
                                supabase.table("farms").insert({**_vf_payload, "name": farm_profile_name.strip(), "owner_id": current_user()}).execute()
                                st.success(f"Farm profile '{farm_profile_name.strip()}' saved.")
                                if _climate_data.get("mean_annual_dli"):
                                    st.caption(f"🌤️ Climate profile saved — Mean DLI: {_climate_data['mean_annual_dli']:.1f} mol/m²/day · Ambient temp: {_climate_data['ambient_temp_annual']:.1f}°C")
                                st.session_state["show_save_farm_form"] = False
                                st.rerun()
                            except Exception as e:
                                st.error(f"Could not save farm profile: {e}")
                with _vn2:
                    if st.button("✖ Cancel", use_container_width=True, key="vf_cancel_new"):
                        st.session_state["show_save_farm_form"] = False
                        st.rerun()
    
    st.divider()
    
    # ── EBITDA Bridge ─────────────────────────────────────────────────────────
    st.subheader("EBITDA Bridge")
    bridge_labels = ["Revenue", "Variable", "Water", "Energy", "Labour", "Rent", "Maintenance", "EBITDA"]
    bridge_values = [
        r["annual_revenue"],
        -r["annual_variable_cost"],
        -r["annual_water_cost"],
        -r["annual_energy_cost"],
        -r["annual_labour_cost"],
        -r["annual_rent"],
        -r["annual_maintenance"],
        r["ebitda"],
    ]
    bar_colors = []
    for i, v in enumerate(bridge_values):
        if i == 0:
            bar_colors.append("rgba(0,229,160,0.85)")
        elif i == len(bridge_values) - 1:
            bar_colors.append("rgba(0,229,160,0.85)" if v >= 0 else "rgba(255,77,77,0.85)")
        else:
            bar_colors.append("rgba(255,77,77,0.6)")
    
    fig_bridge = go.Figure(go.Bar(
        x=bridge_labels,
        y=bridge_values,
        marker_color=bar_colors,
        text=[f"${abs(v):,.0f}" for v in bridge_values],
        textposition="outside",
    ))
    fig_bridge.update_layout(
        plot_bgcolor="#ffffff", paper_bgcolor="#ffffff",
        font_color="#161a16", showlegend=False,
        yaxis=dict(showgrid=False),
        xaxis=dict(showgrid=False),
        height=380, margin=dict(t=30, b=20),
    )
    st.plotly_chart(fig_bridge, use_container_width=True)
    
    st.divider()
    
    # ── Cost breakdown + CAPEX breakdown ─────────────────────────────────────────
    col_cost, col_capex = st.columns(2)
    
    with col_cost:
        st.subheader("Annual Cost Breakdown")
        cost_labels = ["Energy", "Labour", "Variable", "Water", "Maintenance", "Rent"]
        cost_values = [
            r["annual_energy_cost"], r["annual_labour_cost"],
            r["annual_variable_cost"], r["annual_water_cost"],
            r["annual_maintenance"], r["annual_rent"],
        ]
        fig_cost = go.Figure(go.Pie(
            labels=cost_labels,
            values=cost_values,
            hole=0.45,
            marker_colors=["#ff4d4d", "#ffc13d", "#00e5a0", "#4fc3f7", "#ba68c8", "#ef9a9a"],
        ))
        fig_cost.update_layout(
            plot_bgcolor="#ffffff", paper_bgcolor="#ffffff",
            font_color="#161a16", height=320, margin=dict(t=10, b=10),
        )
        st.plotly_chart(fig_cost, use_container_width=True)
    
    with col_capex:
        st.subheader("CAPEX Breakdown")
        capex_labels = ["LED", "HVAC", "Racks", "Building", "Automation",
                        "Robotics", "Electrical", "Water", "Installation"]
        capex_values = [
            r["led_capex"], r["hvac_capex"], r["racks_capex"], r["building_capex"],
            r["automation_capex"], r["robotics_capex"], r["electrical_capex"],
            r["water_capex"], r["installation_capex"],
        ]
        fig_capex = go.Figure(go.Pie(
            labels=capex_labels,
            values=capex_values,
            hole=0.45,
            marker_colors=["#00e5a0", "#26c6da", "#66bb6a", "#ffa726", "#ab47bc",
                           "#ef5350", "#42a5f5", "#26a69a", "#8d6e63"],
        ))
        fig_capex.update_layout(
            plot_bgcolor="#ffffff", paper_bgcolor="#ffffff",
            font_color="#161a16", height=320, margin=dict(t=10, b=10),
        )
        st.plotly_chart(fig_capex, use_container_width=True)
    
    st.divider()
    
    # ── DCF chart ─────────────────────────────────────────────────────────────────
    st.subheader("Cumulative NPV — 10-year DCF")
    dcf_years      = [d["year"] for d in r["dcf_cashflows"]]
    dcf_cumulative = [d["cumulative_npv"] for d in r["dcf_cashflows"]]
    
    fig_dcf = go.Figure()
    fig_dcf.add_trace(go.Scatter(
        x=dcf_years,
        y=dcf_cumulative,
        mode="lines+markers",
        line=dict(color="#00e5a0", width=2),
        fill="tozeroy",
        fillcolor="rgba(0,229,160,0.1)",
    ))
    fig_dcf.add_hline(y=0, line_dash="dash", line_color="rgba(255,255,255,0.3)")
    fig_dcf.update_layout(
        plot_bgcolor="#ffffff", paper_bgcolor="#ffffff",
        font_color="#161a16", height=300,
        xaxis=dict(title="Year", showgrid=False),
        yaxis=dict(title="Cumulative NPV ($)", showgrid=False),
        margin=dict(t=10, b=10),
    )
    st.plotly_chart(fig_dcf, use_container_width=True)
    
    st.divider()
    
    # ── Full results table ────────────────────────────────────────────────────────
    st.subheader("Full Results")
    
    summary_data = {
        "Metric": [
            "Effective Grow Area (m²)", "Gross Area (m²)",
            "Cycles / Year", "Effective Cycle Days", "Harvest Mode",
            "Total Annual kg", "Price ($/kg)",
            "Annual Revenue", "Energy Cost", "Variable Cost",
            "Water Cost", "Labour Cost", "Maintenance", "Rent",
            "Total Annual Costs", "EBITDA", "EBITDA Margin",
            "Total CAPEX", "Payback (years)",
            "Annual Labour Hours", "Net Income", "NPV (10yr)",
        ],
        "Value": [
            f"{r['effective_grow_area']:,.0f}",
            f"{r['gross_area']:,.0f}",
            r["cycles_per_year"],
            r["effective_cycle_days"],
            r["harvest_mode"],
            f"{r['total_annual_kg']:,.0f}",
            f"${r['effective_price']:.2f}",
            f"${r['annual_revenue']:,.0f}",
            f"${r['annual_energy_cost']:,.0f}",
            f"${r['annual_variable_cost']:,.0f}",
            f"${r['annual_water_cost']:,.0f}",
            f"${r['annual_labour_cost']:,.0f}",
            f"${r['annual_maintenance']:,.0f}",
            f"${r['annual_rent']:,.0f}",
            f"${r['total_annual_costs']:,.0f}",
            f"${r['ebitda']:,.0f}",
            f"{r['ebitda_margin']*100:.1f}%",
            f"${r['total_capex']:,.0f}",
            f"{r['payback_years']:.1f}" if r["payback_years"] else "N/A",
            f"{r['annual_labour_hours']:,.1f}",
            f"${r['net_income']:,.0f}",
            f"${r['npv']:,.0f}",
        ],
    }
    
    st.dataframe(pd.DataFrame(summary_data), use_container_width=True, hide_index=True)
    
    # ═════════════════════════════════════════════════════════════════════════════
    # COUNTRY & CROP COMPARISON
    # ═════════════════════════════════════════════════════════════════════════════
    st.divider()
    st.subheader("🌍 Viability Comparison")
    st.caption("All calculations use the current sidebar inputs. Only the dimension being compared changes.")
    
    comp_tab1, comp_tab2 = st.tabs(["Compare Countries", "Compare Crops"])
    
    # ── TAB 1: Country Comparison ─────────────────────────────────────────────────
    with comp_tab1:
        country_metric = st.selectbox(
            "Rank by",
            ["EBITDA", "Energy % of Revenue", "Payback (years)", "EBITDA Margin (%)"],
            key="country_metric_select",
        )
    
        country_results = []
        for c_name in COUNTRIES.keys():
            c_inputs = copy.deepcopy(inputs)
            c_inputs["country"] = c_name
            try:
                c_r = calculate(c_inputs)
                energy_pct = c_r["annual_energy_cost"] / c_r["annual_revenue"] * 100 if c_r["annual_revenue"] > 0 else 999
                country_results.append({
                    "Country":              c_name,
                    "EBITDA":               c_r["ebitda"],
                    "Energy % of Revenue":  energy_pct,
                    "Payback (years)":      c_r["payback_years"] if c_r["payback_years"] else 999,
                    "EBITDA Margin (%)":    c_r["ebitda_margin"] * 100,
                    "revenue":              c_r["annual_revenue"],
                    "energy_cost":          c_r["annual_energy_cost"],
                })
            except Exception:
                continue
    
        if country_results:
            df_countries = pd.DataFrame(country_results)
    
            # Sort: for EBITDA and margin, descending (higher is better).
            # For energy % and payback, ascending (lower is better).
            ascending = country_metric in ("Energy % of Revenue", "Payback (years)")
            df_countries = df_countries.sort_values(country_metric, ascending=ascending).reset_index(drop=True)
    
            def country_bar_color(row, metric):
                if metric == "EBITDA":
                    return "rgba(0,229,160,0.75)" if row["EBITDA"] >= 0 else "rgba(255,77,77,0.75)"
                elif metric == "Energy % of Revenue":
                    return "rgba(0,229,160,0.75)" if row["Energy % of Revenue"] < 40 else "rgba(255,77,77,0.75)"
                elif metric == "Payback (years)":
                    # Payback under 10 years = green, over = red, 999 = no payback = red
                    return "rgba(0,229,160,0.75)" if 0 < row["Payback (years)"] < 10 else "rgba(255,77,77,0.75)"
                elif metric == "EBITDA Margin (%)":
                    return "rgba(0,229,160,0.75)" if row["EBITDA Margin (%)"] >= 0 else "rgba(255,77,77,0.75)"
                return "rgba(105,105,105,0.75)"
    
            bar_colors_country = [
                country_bar_color(row, country_metric)
                for _, row in df_countries.iterrows()
            ]
    
            fig_countries = go.Figure(go.Bar(
                x=df_countries[country_metric],
                y=df_countries["Country"],
                orientation="h",
                marker_color=bar_colors_country,
                text=df_countries[country_metric].apply(
                    lambda v: f"${v:,.0f}" if country_metric == "EBITDA"
                    else (f"{v:.1f}%" if "%" in country_metric
                    else (f"{v:.1f} yrs" if v < 900 else "N/A"))
                ),
                textposition="outside",
            ))
    
            # Add viability threshold line for energy % chart
            if country_metric == "Energy % of Revenue":
                fig_countries.add_vline(
                    x=40,
                    line_dash="dash",
                    line_color="rgba(255,193,61,0.6)",
                    annotation_text="40% threshold",
                    annotation_position="top",
                    annotation_font_color="#ffc13d",
                )
    
            fig_countries.update_layout(
                plot_bgcolor="#ffffff",
                paper_bgcolor="#ffffff",
                font_color="#161a16",
                height=max(500, len(df_countries) * 22),
                margin=dict(l=10, r=100, t=20, b=20),
                xaxis=dict(showgrid=False, zeroline=False),
                yaxis=dict(showgrid=False, autorange="reversed"),
            )
            st.plotly_chart(fig_countries, use_container_width=True)
    
            # Summary note
            viable = (df_countries["Energy % of Revenue"] < 40).sum()
            st.caption(f"**{viable} of {len(df_countries)} countries** show energy below 40% of revenue for this crop and setup. Green = below threshold, Red = above threshold.")
    
    # ── TAB 2: Crop Comparison ────────────────────────────────────────────────────
    with comp_tab2:
        crop_col1, crop_col2 = st.columns(2)
        with crop_col1:
            crop_metric = st.selectbox(
                "Rank by",
                ["EBITDA", "EBITDA Margin (%)", "Energy % of Revenue", "Payback (years)"],
                key="crop_metric_select",
            )
        with crop_col2:
            # Category filter
            CROP_CATEGORIES = {
                "All crops": None,
                "Leafy greens & lettuce": ["Lettuce", "Leaf ", "Lollo", "Batavia", "Frisee",
                                            "Escarole", "Baby Lettuce", "Spinach", "Baby Spinach",
                                            "Kale", "Baby Kale", "Mizuna", "Arugula", "Tatsoi",
                                            "Pak Choi", "Shanghai", "Mustard", "Mibuna", "Choi Sum",
                                            "Komatsuna", "Swiss Chard", "Purslane", "Sorrel",
                                            "Watercress", "Upland Cress", "Claytonia", "Turnip Greens",
                                            "Broccoli", "Brussels", "Radicchio", "Chicory",
                                            "Endive", "Fennel"],
                "Herbs": ["Basil", "Mint", "Parsley", "Cilantro", "Chives", "Dill", "Oregano",
                          "Thyme", "Sage", "Rosemary", "Lemongrass", "Stevia", "Shiso",
                          "Wasabi", "Celery", "Chinese Celery", "Garlic Chives", "Spring Onions"],
                "Microgreens": ["Microgreens", "Pea Shoots"],
                "Fruiting & other": ["Strawberr", "Tomato", "Pepper", "Chili", "Eggplant",
                                      "Cucumber", "Dwarf Bean", "Okra", "Edible Flower",
                                      "Carrot", "Radish", "Beet", "Micro-Turnip"],
                "Mushrooms": ["Mushroom"],
            }
            selected_category = st.selectbox("Filter by category", list(CROP_CATEGORIES.keys()), key="crop_category_select")
    
        # Apply category filter
        filter_keywords = CROP_CATEGORIES[selected_category]
        if filter_keywords:
            filtered_crops = [c for c in CROPS.keys() if any(kw in c for kw in filter_keywords)]
        else:
            filtered_crops = list(CROPS.keys())
    
        crop_results = []
        for cr_name in filtered_crops:
            cr_inputs = copy.deepcopy(inputs)
            cr_inputs["crop"] = cr_name
            cr_inputs["harvest_mode"] = "Single"   # normalise to single for fair comparison
            cr_inputs["price_override"] = 0        # use each crop's own price
            try:
                cr_r = calculate(cr_inputs)
                energy_pct = cr_r["annual_energy_cost"] / cr_r["annual_revenue"] * 100 if cr_r["annual_revenue"] > 0 else 999
                crop_results.append({
                    "Crop":                 cr_name,
                    "EBITDA":               cr_r["ebitda"],
                    "EBITDA Margin (%)":    cr_r["ebitda_margin"] * 100,
                    "Energy % of Revenue":  energy_pct,
                    "Payback (years)":      cr_r["payback_years"] if cr_r["payback_years"] else 999,
                })
            except Exception:
                continue
    
        if crop_results:
            df_crops = pd.DataFrame(crop_results)
    
            ascending_crop = crop_metric in ("Energy % of Revenue", "Payback (years)")
            df_crops = df_crops.sort_values(crop_metric, ascending=ascending_crop).reset_index(drop=True)
    
            def crop_bar_color(row, metric):
                if metric == "EBITDA":
                    return "rgba(0,229,160,0.75)" if row["EBITDA"] >= 0 else "rgba(255,77,77,0.75)"
                elif metric == "Energy % of Revenue":
                    return "rgba(0,229,160,0.75)" if row["Energy % of Revenue"] < 40 else "rgba(255,77,77,0.75)"
                elif metric == "Payback (years)":
                    return "rgba(0,229,160,0.75)" if 0 < row["Payback (years)"] < 10 else "rgba(255,77,77,0.75)"
                elif metric == "EBITDA Margin (%)":
                    return "rgba(0,229,160,0.75)" if row["EBITDA Margin (%)"] >= 0 else "rgba(255,77,77,0.75)"
                return "rgba(105,105,105,0.75)"
    
            bar_colors_crop = [
                crop_bar_color(row, crop_metric)
                for _, row in df_crops.iterrows()
            ]
    
            fig_crops = go.Figure(go.Bar(
                x=df_crops[crop_metric],
                y=df_crops["Crop"],
                orientation="h",
                marker_color=bar_colors_crop,
                text=df_crops[crop_metric].apply(
                    lambda v: f"${v:,.0f}" if crop_metric == "EBITDA"
                    else (f"{v:.1f}%" if "%" in crop_metric
                    else (f"{v:.1f} yrs" if v < 900 else "N/A"))
                ),
                textposition="outside",
            ))
    
            if crop_metric == "Energy % of Revenue":
                fig_crops.add_vline(
                    x=40,
                    line_dash="dash",
                    line_color="rgba(255,193,61,0.6)",
                    annotation_text="40% threshold",
                    annotation_position="top",
                    annotation_font_color="#ffc13d",
                )
    
            fig_crops.update_layout(
                plot_bgcolor="#ffffff",
                paper_bgcolor="#ffffff",
                font_color="#161a16",
                height=max(500, len(df_crops) * 22),
                margin=dict(l=10, r=100, t=20, b=20),
                xaxis=dict(showgrid=False, zeroline=False),
                yaxis=dict(showgrid=False, autorange="reversed"),
            )
            st.plotly_chart(fig_crops, use_container_width=True)
    
            viable_crops = (df_crops["Energy % of Revenue"] < 40).sum()
            st.caption(f"**{viable_crops} of {len(df_crops)} crops** show energy below 40% of revenue for this country and setup. Normalised to Single harvest for fair comparison.")
    
    # ═════════════════════════════════════════════════════════════════════════════
    # SENSITIVITY ANALYSIS
    # ═════════════════════════════════════════════════════════════════════════════
    st.divider()
    st.subheader("🔬 Sensitivity Analysis")
    
    # ── Helper: run calculate() with a temporarily modified country entry ─────────
    def run_with_country_override(base_inputs: dict, kwh_mult: float = 1.0, labour_mult: float = 1.0) -> dict:
        """
        Runs calculate() with energy and/or labour prices modified by a multiplier.
        Uses a deep copy of the country entry so the global COUNTRIES dict is never mutated.
        """
        from core.data_tables import COUNTRIES
        import core.data_tables as dt
    
        country_name = base_inputs["country"]
        original = COUNTRIES[country_name]
    
        modified = copy.deepcopy(original)
        modified["kwh"]    = original["kwh"]    * kwh_mult
        modified["labour"] = original["labour"] * labour_mult
    
        # Temporarily patch the global dict
        dt.COUNTRIES[country_name] = modified
        try:
            result = calculate(base_inputs)
        finally:
            # Always restore — even if calculate() raises an exception
            dt.COUNTRIES[country_name] = original
    
        return result
    
    # ── Helper: run calculate() with yield or price multiplier ───────────────────
    def run_with_multipliers(
        base_inputs: dict,
        kwh_mult: float = 1.0,
        labour_mult: float = 1.0,
        yield_mult: float = 1.0,
        price_mult: float = 1.0,
    ) -> dict:
        """
        Runs calculate() with energy/labour via country override,
        and yield/price via modified inputs dict.
        """
        modified_inputs = copy.deepcopy(base_inputs)
    
        # Yield override: scale the crop's yield by setting price_override and
        # a yield multiplier. Since calculate() reads yield from CROPS directly,
        # we use price_override for price and a crop patch for yield.
        import core.data_tables as dt
        from core.data_tables import CROPS as _CROPS_LOCAL
        from core.data_tables import COUNTRIES as _COUNTRIES_LOCAL
    
        crop_name = base_inputs["crop"]
        original_crop = _CROPS_LOCAL[crop_name]
    
        modified_crop = copy.deepcopy(original_crop)
        modified_crop["yield"]    = original_crop["yield"]    * yield_mult
        modified_crop["yield_h2"] = original_crop["yield_h2"]  # fractions stay the same
        modified_crop["yield_h3"] = original_crop["yield_h3"]
    
        # Price override: if user already set a price_override, scale that;
        # otherwise compute base effective price and scale it
        if base_inputs.get("price_override", 0) > 0:
            modified_inputs["price_override"] = base_inputs["price_override"] * price_mult
        else:
            country = _COUNTRIES_LOCAL[base_inputs["country"]]
            base_price = original_crop[f"price_{base_inputs['price_scenario']}"] * country["food_index"]
            modified_inputs["price_override"] = base_price * price_mult
    
        country_name = base_inputs["country"]
        original_country = _COUNTRIES_LOCAL[country_name]
        modified_country = copy.deepcopy(original_country)
        modified_country["kwh"]    = original_country["kwh"]    * kwh_mult
        modified_country["labour"] = original_country["labour"] * labour_mult
    
        dt.CROPS[crop_name]              = modified_crop
        dt.COUNTRIES[country_name]       = modified_country
        try:
            if _mix_valid:
                result = run_multicrop(modified_inputs, _crop_mix)
            else:
                result = calculate(modified_inputs)
        finally:
            dt.CROPS[crop_name]        = original_crop
            dt.COUNTRIES[country_name] = original_country
    
        return result
    
    # ─────────────────────────────────────────────────────────────────────────────
    # COMPONENT 1 — TORNADO CHART
    # ─────────────────────────────────────────────────────────────────────────────
    st.markdown("#### Tornado Chart — EBITDA Sensitivity")
    st.caption("Each bar shows how EBITDA changes when one variable is stressed while all others stay at base values.")
    
    base_ebitda = r["ebitda"]
    
    # Define variables: (label, kwh_mult_pess, kwh_mult_opt, labour_mult_pess, labour_mult_opt, yield_mult_pess, yield_mult_opt, price_mult_pess, price_mult_opt)
    tornado_vars = [
        {
            "label":        "Energy Price",
            "pess":         run_with_multipliers(inputs, kwh_mult=1.50)["ebitda"],
            "opt":          run_with_multipliers(inputs, kwh_mult=0.70)["ebitda"],
            "pess_label":   "Energy price +50% (stress: energy crisis scenario)",
            "opt_label":    "Energy price −30% (upside: efficiency gains / cheaper tariff)",
            "rationale":    "Asymmetric: energy spikes are the dominant CEA risk in Europe. +50% reflects 2021–2022 style shock; −30% reflects realistic downside from long-term contracts or solar integration.",
        },
        {
            "label":        "Selling Price",
            "pess":         run_with_multipliers(inputs, price_mult=0.80)["ebitda"],
            "opt":          run_with_multipliers(inputs, price_mult=1.20)["ebitda"],
            "pess_label":   "Selling price −20% (stress: market price pressure)",
            "opt_label":    "Selling price +20% (upside: premium positioning or scarcity)",
            "rationale":    "Symmetric ±20%. Reflects realistic wholesale price volatility for premium fresh produce in European markets.",
        },
        {
            "label":        "Yield",
            "pess":         run_with_multipliers(inputs, yield_mult=0.80)["ebitda"],
            "opt":          run_with_multipliers(inputs, yield_mult=1.20)["ebitda"],
            "pess_label":   "Yield −20% (stress: underperformance vs crop profile)",
            "opt_label":    "Yield +20% (upside: optimised cultivar or growing conditions)",
            "rationale":    "Symmetric ±20%. Crop profile yields are benchmarks; actual yields vary with cultivar selection, growing protocol, and operator experience.",
        },
        {
            "label":        "Labour Cost",
            "pess":         run_with_multipliers(inputs, labour_mult=1.30)["ebitda"],
            "opt":          run_with_multipliers(inputs, labour_mult=0.80)["ebitda"],
            "pess_label":   "Labour cost +30% (stress: wage inflation or high turnover)",
            "opt_label":    "Labour cost −20% (upside: automation or lower-cost market)",
            "rationale":    "Asymmetric: labour costs in CEA tend to rise over time. +30% reflects structural wage inflation or higher-than-modelled staff requirements; −20% reflects partial automation gains.",
        },
    ]
    
    # Compute deltas from base and sort by total swing (widest bar on top)
    for tv in tornado_vars:
        tv["delta_pess"] = tv["pess"] - base_ebitda
        tv["delta_opt"]  = tv["opt"]  - base_ebitda
        tv["swing"]      = abs(tv["delta_opt"] - tv["delta_pess"])
    
    tornado_vars.sort(key=lambda x: x["swing"], reverse=True)
    
    fig_tornado = go.Figure()
    
    for tv in tornado_vars:
        # Pessimistic bar (always negative impact or less positive)
        fig_tornado.add_trace(go.Bar(
            name="Pessimistic",
            y=[tv["label"]],
            x=[tv["delta_pess"]],
            orientation="h",
            marker_color="rgba(255,77,77,0.75)",
            showlegend=(tv == tornado_vars[0]),
            text=f"${tv['delta_pess']:,.0f}",
            textposition="outside",
            customdata=[[tv["pess_label"], tv["rationale"]]],
            hovertemplate=(
                "<b>%{y}</b><br>"
                "EBITDA delta: %{x:$,.0f}<br>"
                "<i>%{customdata[0]}</i><br>"
                "<br><b>Rationale:</b> %{customdata[1]}<extra></extra>"
            ),
        ))
        # Optimistic bar
        fig_tornado.add_trace(go.Bar(
            name="Optimistic",
            y=[tv["label"]],
            x=[tv["delta_opt"]],
            orientation="h",
            marker_color="rgba(0,229,160,0.75)",
            showlegend=(tv == tornado_vars[0]),
            text=f"${tv['delta_opt']:,.0f}",
            textposition="outside",
            customdata=[[tv["opt_label"], tv["rationale"]]],
            hovertemplate=(
                "<b>%{y}</b><br>"
                "EBITDA delta: %{x:$,.0f}<br>"
                "<i>%{customdata[0]}</i><br>"
                "<br><b>Rationale:</b> %{customdata[1]}<extra></extra>"
            ),
        ))
    
    fig_tornado.add_vline(x=0, line_dash="dash", line_color="rgba(255,255,255,0.4)")
    fig_tornado.update_layout(
        barmode="overlay",
        plot_bgcolor="#ffffff",
        paper_bgcolor="#ffffff",
        font_color="#161a16",
        height=320,
        margin=dict(l=10, r=80, t=20, b=20),
        xaxis=dict(title="EBITDA delta from base ($)", showgrid=False, zeroline=False),
        yaxis=dict(showgrid=False),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    )
    st.plotly_chart(fig_tornado, use_container_width=True)
    
    # ─────────────────────────────────────────────────────────────────────────────
    # COMPONENT 2 — SCENARIO COMPARISON
    # ─────────────────────────────────────────────────────────────────────────────
    st.divider()
    st.markdown("#### Scenario Comparison")
    st.caption("Define up to 4 named scenarios by adjusting multipliers. The Base Case always shows the current sidebar inputs.")
    
    if "scenarios" not in st.session_state:
        try:
            resp = supabase.table("scenarios").select("*").is_("farm_id", "null").order("created_at", desc=False).execute()
            loaded = []
            for row in resp.data:
                try:
                    result = json.loads(row["outputs_json"]) if row.get("outputs_json") else {}
                    loaded.append({
                        "name":         row["name"],
                        "energy_mult":  row["energy_factor"],
                        "yield_mult":   row["yield_factor"],
                        "price_mult":   row["price_factor"],
                        "labour_mult":  row["labour_factor"],
                        "is_actual":    row["is_actual"],
                        "result":       result,
                        "supabase_id":  row["id"],
                    })
                except Exception:
                    continue
            st.session_state["scenarios"] = loaded
        except Exception:
            st.session_state["scenarios"] = []
    
    # ── Scenario builder ──────────────────────────────────────────────────────────
    with st.expander("➕ Define a new scenario", expanded=len(st.session_state["scenarios"]) == 0):
        sc_name = st.text_input("Scenario name", value="Scenario 1", key="sc_name_input")
    
        sc_col1, sc_col2 = st.columns(2)
        with sc_col1:
            sc_energy   = st.slider("Energy price multiplier",  min_value=0.3, max_value=3.0, value=1.0, step=0.05, key="sc_energy")
            sc_yield    = st.slider("Yield multiplier",         min_value=0.3, max_value=2.0, value=1.0, step=0.05, key="sc_yield")
        with sc_col2:
            sc_price    = st.slider("Selling price multiplier", min_value=0.3, max_value=2.0, value=1.0, step=0.05, key="sc_price")
            sc_labour   = st.slider("Labour cost multiplier",   min_value=0.3, max_value=3.0, value=1.0, step=0.05, key="sc_labour")
    
        if st.button("💾 Save Scenario", use_container_width=True):
            if len(st.session_state["scenarios"]) >= 4:
                st.warning("Maximum 4 scenarios reached. Delete one before adding another.")
            else:
                sc_result = run_with_multipliers(
                    inputs,
                    kwh_mult=sc_energy,
                    labour_mult=sc_labour,
                    yield_mult=sc_yield,
                    price_mult=sc_price,
                )
                new_scenario = {
                    "name":        sc_name,
                    "energy_mult": sc_energy,
                    "yield_mult":  sc_yield,
                    "price_mult":  sc_price,
                    "labour_mult": sc_labour,
                    "result":      sc_result,
                    "is_actual":   False,
                    "supabase_id": None,
                }
                try:
                    sb_resp = supabase.table("scenarios").insert({
                        "name":          sc_name,
                        "energy_factor": sc_energy,
                        "yield_factor":  sc_yield,
                        "price_factor":  sc_price,
                        "labour_factor": sc_labour,
                        "capex_factor":  1.0,
                        "is_actual":     False,
                        "farm_id":       None,
                        "outputs_json":  json.dumps(sc_result),
                    }).execute()
                    if sb_resp.data:
                        new_scenario["supabase_id"] = sb_resp.data[0]["id"]
                    st.success(f"Scenario '{sc_name}' saved.")
                except Exception as e:
                    st.error(f"Saved locally but could not write to database: {e}")
                    st.success(f"Scenario '{sc_name}' saved locally.")
                st.session_state["scenarios"].append(new_scenario)
    
        if st.session_state["scenarios"]:
            if st.button("🗑️ Clear all scenarios", use_container_width=True):
                try:
                    supabase.table("scenarios").delete().is_("farm_id", "null").execute()
                except Exception as e:
                    st.error(f"Could not delete from database: {e}")
                st.session_state["scenarios"] = []
                st.rerun()
    
    # ── Comparison display ────────────────────────────────────────────────────────
    if st.session_state["scenarios"]:
    
        # Per-scenario delete buttons
        for idx, sc in enumerate(st.session_state["scenarios"]):
            del_col1, del_col2 = st.columns([8, 1])
            with del_col1:
                st.caption(f"**{sc['name']}** — energy ×{sc['energy_mult']} / yield ×{sc['yield_mult']} / price ×{sc['price_mult']} / labour ×{sc['labour_mult']}")
            with del_col2:
                if st.button("🗑️", key=f"del_sc_{idx}"):
                    if sc.get("supabase_id"):
                        try:
                            supabase.table("scenarios").delete().eq("id", sc["supabase_id"]).execute()
                        except Exception as e:
                            st.error(f"Could not delete from database: {e}")
                    st.session_state["scenarios"].pop(idx)
                    st.rerun()
    
        scenario_names   = ["Base Case"] + [s["name"] for s in st.session_state["scenarios"]]
        scenario_results = [r] + [s["result"] for s in st.session_state["scenarios"]]
    
        # Grouped bar chart
        metrics_to_plot = {
            "EBITDA":       [res["ebitda"]             for res in scenario_results],
            "Revenue":      [res["annual_revenue"]      for res in scenario_results],
            "Energy Cost":  [res["annual_energy_cost"]  for res in scenario_results],
            "Labour Cost":  [res["annual_labour_cost"]  for res in scenario_results],
        }
    
        bar_colors_chart = ["#00e5a0", "#ffc13d", "#4fc3f7", "#ba68c8", "#ef9a9a"]
    
        fig_compare = go.Figure()
        for i, (metric_name, values) in enumerate(metrics_to_plot.items()):
            fig_compare.add_trace(go.Bar(
                name=metric_name,
                x=scenario_names,
                y=values,
                marker_color=bar_colors_chart[i],
                text=[f"${v:,.0f}" for v in values],
                textposition="outside",
            ))
    
        fig_compare.update_layout(
            barmode="group",
            plot_bgcolor="#ffffff",
            paper_bgcolor="#ffffff",
            font_color="#161a16",
            height=420,
            margin=dict(t=30, b=20),
            xaxis=dict(showgrid=False),
            yaxis=dict(showgrid=False, title="$"),
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        )
        st.plotly_chart(fig_compare, use_container_width=True)
    
        # Summary table
        def energy_pct(res):
            if res["annual_revenue"] > 0:
                return f"{res['annual_energy_cost'] / res['annual_revenue'] * 100:.1f}%"
            return "N/A"
    
        def fmt_payback(res):
            return f"{res['payback_years']:.1f}" if res["payback_years"] else "N/A"
    
        table_rows = []
        for name, res in zip(scenario_names, scenario_results):
            table_rows.append({
                "Scenario":           name,
                "Revenue":            f"${res['annual_revenue']:,.0f}",
                "Energy Cost":        f"${res['annual_energy_cost']:,.0f}",
                "Labour Cost":        f"${res['annual_labour_cost']:,.0f}",
                "EBITDA":             f"${res['ebitda']:,.0f}",
                "EBITDA Margin":      f"{res['ebitda_margin']*100:.1f}%",
                "Payback (yrs)":      fmt_payback(res),
                "Energy % of Revenue": energy_pct(res),
            })
    
        scenario_df = pd.DataFrame(table_rows)
    
        def highlight_energy_pct(row):
            val_str = row["Energy % of Revenue"]
            if val_str == "N/A":
                return [""] * len(row)
            try:
                val = float(val_str.replace("%", ""))
            except ValueError:
                return [""] * len(row)
            if val > 60:
                return [""] * (len(row) - 1) + ["background-color: rgba(255,77,77,0.25); color: #ff4d4d"]
            elif val > 40:
                return [""] * (len(row) - 1) + ["background-color: rgba(255,193,61,0.25); color: #ffc13d"]
            else:
                return [""] * (len(row) - 1) + ["background-color: rgba(0,229,160,0.15); color: #00e5a0"]
    
        st.dataframe(
            scenario_df.style.apply(highlight_energy_pct, axis=1),
            use_container_width=True,
            hide_index=True,
        )
    
    else:
        st.info("No scenarios saved yet. Use the form above to define and save your first scenario.")

elif modality == "🌿 High-Tech Greenhouse":

    st.markdown("### 🌿 High-Tech Greenhouse & Polytunnel Calculator")

    # ── Session state defaults ────────────────────────────────────────────────
    _GH_DEFAULTS = {
        "gh_country":           "Germany",
        "gh_crop_source":       "Greenhouse",
        "gh_crop":              "Tomato (Beef)",
        "gh_footprint":         1000,
        "gh_automation":        "Medium",
        "gh_price_scenario":    "base",
        "gh_harvest_mode":      "Single",
        "gh_price_override":    0.0,
        "gh_packaging_cost":    0.15,
        "gh_loss_rate":         5.0,
        "gh_net_grow_factor":   90.0,
        "gh_walkways_factor":   10.0,
        "gh_water_price":       2.0,
        "gh_rent_monthly":      0.0,
        "gh_real_estate_capex": 0.0,
        "gh_depreciation_years": 15,
        "gh_tax_rate":          25.0,
        "gh_ltv":               60.0,
        "gh_interest_rate":     5.5,
        "gh_loan_term_years":   15,
        "gh_discount_rate":     8.0,
        "gh_multi_crop":        False,
        "gh_crop_mix":          [{"crop": "Tomato (Beef)", "pct": 100}],
    }
    for _k, _v in _GH_DEFAULTS.items():
        if _k not in st.session_state:
            st.session_state[_k] = _v

    if "gh_show_save_form" not in st.session_state:
        st.session_state["gh_show_save_form"] = False

    # ── Sidebar ───────────────────────────────────────────────────────────────
    with st.sidebar:
        st.header("Greenhouse Parameters")

        st.divider()

        # ── Farm parameters ───────────────────────────────────────────────────
        gh_country_list = list(COUNTRIES.keys())
        gh_country = st.selectbox("Country", gh_country_list,
                                  index=gh_country_list.index(st.session_state["gh_country"]) if st.session_state["gh_country"] in gh_country_list else 0,
                                  key="gh_country")

        gh_crop_source = st.radio("Crop source", ["Greenhouse", "Polytunnel"],
                                  index=0 if st.session_state["gh_crop_source"] == "Greenhouse" else 1,
                                  horizontal=True, key="gh_crop_source")

        if gh_crop_source == "Greenhouse":
            gh_crop_list = list(GREENHOUSE_CROPS.keys())
        else:
            gh_crop_list = list(POLYTUNNEL_CROPS.keys())

        # ── Multi-crop toggle ─────────────────────────────────────────────────
        gh_multi_crop_mode = st.toggle("Multi-crop mode", value=False, key="gh_multi_crop")

        if not gh_multi_crop_mode:
            _gh_crop_default = st.session_state["gh_crop"]
            gh_crop = st.selectbox("Crop", gh_crop_list,
                                   index=gh_crop_list.index(_gh_crop_default) if _gh_crop_default in gh_crop_list else 0,
                                   key="gh_crop")
        else:
            gh_crop = gh_crop_list[0]  # placeholder — unused in multi-crop mode
            st.markdown("**Crop allocation** (must sum to 100%)")
            if "gh_crop_mix" not in st.session_state:
                st.session_state["gh_crop_mix"] = [{"crop": gh_crop_list[0], "pct": 100}]
            _gh_mix = st.session_state["gh_crop_mix"]
            # Validate all mix crops exist in current crop list
            _gh_mix = [row for row in _gh_mix if row["crop"] in gh_crop_list]
            if not _gh_mix:
                _gh_mix = [{"crop": gh_crop_list[0], "pct": 100}]
            _gh_to_remove = None
            for _gci, _grow in enumerate(_gh_mix):
                _gc1, _gc2, _gc3 = st.columns([4, 2, 1])
                with _gc1:
                    _gh_mix[_gci]["crop"] = st.selectbox(
                        f"Crop {_gci+1}", gh_crop_list,
                        index=gh_crop_list.index(_grow["crop"]) if _grow["crop"] in gh_crop_list else 0,
                        key=f"gh_mix_crop_{_gci}")
                with _gc2:
                    _gh_mix[_gci]["pct"] = st.number_input(
                        "%", min_value=1, max_value=100, value=int(_grow["pct"]),
                        step=1, key=f"gh_mix_pct_{_gci}")
                with _gc3:
                    if len(_gh_mix) > 1 and st.button("✕", key=f"gh_mix_del_{_gci}"):
                        _gh_to_remove = _gci
            if _gh_to_remove is not None:
                _gh_mix.pop(_gh_to_remove)
                st.session_state["gh_crop_mix"] = _gh_mix
                st.rerun()
            _gh_total_pct = sum(r["pct"] for r in _gh_mix)
            st.caption(f"Total allocated: **{_gh_total_pct}%**")
            if _gh_total_pct != 100:
                st.warning(f"⚠️ Must sum to 100%. Currently {_gh_total_pct}%.")
            if len(_gh_mix) < 6:
                if st.button("➕ Add crop", key="gh_mix_add"):
                    _gh_mix.append({"crop": gh_crop_list[0], "pct": 1})
                    st.session_state["gh_crop_mix"] = _gh_mix
                    st.rerun()
            st.session_state["gh_crop_mix"] = _gh_mix

        st.divider()
        gh_footprint = st.number_input("Footprint (m²)", value=st.session_state["gh_footprint"],
                                       step=100, min_value=50, key="gh_footprint")

        st.divider()
        gh_automation = st.selectbox("Automation", ["None", "Low", "Medium", "High"],
                                     index=["None", "Low", "Medium", "High"].index(st.session_state["gh_automation"]),
                                     key="gh_automation")

        ps_list_gh = ["base", "low", "high"]
        gh_price_scenario = st.selectbox("Price Scenario", ps_list_gh,
                                         index=ps_list_gh.index(st.session_state["gh_price_scenario"]),
                                         key="gh_price_scenario")

        if gh_crop_source == "Greenhouse":
            gh_crop_data = GREENHOUSE_CROPS[gh_crop]
        else:
            gh_crop_data = POLYTUNNEL_CROPS[gh_crop]

        if gh_crop_data["days_between"] > 0:
            hm_list_gh = ["Single", "2 Harvests", "3 Harvests"]
            _gh_hm_default = st.session_state["gh_harvest_mode"]
            gh_harvest_mode = st.selectbox("Harvest Mode", hm_list_gh,
                                           index=hm_list_gh.index(_gh_hm_default) if _gh_hm_default in hm_list_gh else 0,
                                           key="gh_harvest_mode")
        else:
            st.selectbox("Harvest Mode", ["Single"], disabled=True,
                         help="This crop only supports single harvest.")
            gh_harvest_mode = "Single"
            st.session_state["gh_harvest_mode"] = "Single"

        st.divider()
        st.subheader("Advanced")
        gh_price_override    = st.number_input("Price Override ($/kg, 0=auto)",
                                               value=st.session_state["gh_price_override"],
                                               step=0.1, min_value=0.0, key="gh_price_override")
        gh_packaging_cost    = st.number_input("Packaging ($/kg)",
                                               value=st.session_state["gh_packaging_cost"],
                                               step=0.01, min_value=0.0, key="gh_packaging_cost")
        gh_loss_rate         = st.number_input("Loss Rate (%)",
                                               value=st.session_state["gh_loss_rate"],
                                               step=0.5, min_value=0.0, max_value=100.0, key="gh_loss_rate")
        gh_net_grow_factor   = st.number_input("Net Grow Factor (%)",
                                               value=st.session_state["gh_net_grow_factor"],
                                               step=1.0, min_value=1.0, max_value=100.0, key="gh_net_grow_factor")
        gh_walkways_factor   = st.number_input("Walkways Factor (%)",
                                               value=st.session_state["gh_walkways_factor"],
                                               step=1.0, min_value=0.0, max_value=50.0, key="gh_walkways_factor")
        gh_water_price       = st.number_input("Water Price ($/m³)",
                                               value=st.session_state["gh_water_price"],
                                               step=0.1, min_value=0.0, key="gh_water_price")
        gh_rent_monthly      = st.number_input("Monthly Rent ($)",
                                               value=st.session_state["gh_rent_monthly"],
                                               step=100.0, min_value=0.0, key="gh_rent_monthly")
        gh_real_estate_capex = st.number_input("Real Estate CAPEX ($)",
                                               value=st.session_state["gh_real_estate_capex"],
                                               step=10000.0, min_value=0.0, key="gh_real_estate_capex")

        st.divider()
        st.subheader("Financial Structure")
        gh_depreciation_years = st.number_input("Depreciation (years)",
                                                value=st.session_state["gh_depreciation_years"],
                                                step=1, min_value=1, key="gh_depreciation_years")
        gh_tax_rate           = st.number_input("Tax Rate (%)",
                                                value=st.session_state["gh_tax_rate"],
                                                step=1.0, min_value=0.0, max_value=100.0, key="gh_tax_rate")
        gh_ltv                = st.number_input("LTV (%)",
                                                value=st.session_state["gh_ltv"],
                                                step=5.0, min_value=0.0, max_value=100.0, key="gh_ltv")
        gh_interest_rate      = st.number_input("Interest Rate (%)",
                                                value=st.session_state["gh_interest_rate"],
                                                step=0.1, min_value=0.0, key="gh_interest_rate")
        gh_loan_term_years    = st.number_input("Loan Term (years)",
                                                value=st.session_state["gh_loan_term_years"],
                                                step=1, min_value=1, key="gh_loan_term_years")
        gh_discount_rate      = st.number_input("Discount Rate (%)",
                                                value=st.session_state["gh_discount_rate"],
                                                step=0.5, min_value=0.0, key="gh_discount_rate")

    # ── Run calculation ───────────────────────────────────────────────────────
    gh_inputs = {
        "country":            gh_country,
        "crop":               gh_crop,
        "crop_source":        gh_crop_source.lower(),
        "footprint":          gh_footprint,
        "automation":         gh_automation,
        "price_scenario":     gh_price_scenario,
        "price_override":     gh_price_override,
        "packaging_cost":     gh_packaging_cost,
        "loss_rate":          gh_loss_rate,
        "net_grow_factor":    gh_net_grow_factor,
        "walkways_factor":    gh_walkways_factor,
        "water_price":        gh_water_price,
        "rent_monthly":       gh_rent_monthly,
        "real_estate_capex":  gh_real_estate_capex,
        "harvest_mode":       gh_harvest_mode,
        "depreciation_years": gh_depreciation_years,
        "tax_rate":           gh_tax_rate,
        "ltv":                gh_ltv,
        "interest_rate":      gh_interest_rate,
        "loan_term_years":    gh_loan_term_years,
        "discount_rate":      gh_discount_rate,
        "ambient_temp_annual":    st.session_state.get("active_farm", {}).get("ambient_temp_annual"),
        "mean_annual_dli":        st.session_state.get("active_farm", {}).get("mean_annual_dli"),
    }

    _gh_multi_crop_mode = st.session_state.get("gh_multi_crop", False)
    _gh_crop_mix        = st.session_state.get("gh_crop_mix", [])
    _gh_mix_total       = sum(row["pct"] for row in _gh_crop_mix)
    _gh_mix_valid       = _gh_multi_crop_mode and len(_gh_crop_mix) > 0 and _gh_mix_total == 100

    if _gh_multi_crop_mode and not _gh_mix_valid:
        st.warning("⚠️ Fix greenhouse crop allocation (must sum to 100%) before results are shown.")
        st.stop()

    _gh_crop_data_dict = GREENHOUSE_CROPS if gh_crop_source == "Greenhouse" else POLYTUNNEL_CROPS

    if _gh_mix_valid:
        gh_r = _run_multicrop_generic(gh_inputs, _gh_crop_mix,
                                       calculate_greenhouse, _gh_crop_data_dict)
    else:
        gh_r = calculate_greenhouse(gh_inputs)

    # ── Climate profile display ─────────────────────────────────────────────────
    _gh_active2 = st.session_state.get("active_farm")
    if _gh_active2 and _gh_active2.get("mean_annual_dli"):
        _gh_loc_dli2  = _gh_active2["mean_annual_dli"]
        _gh_loc_temp2 = _gh_active2["ambient_temp_annual"]
        _gh_crop_dli2 = gh_crop_data["dli"]
        _gh_nat_frac2 = compute_natural_dli_fraction(_gh_loc_dli2, _gh_crop_dli2)
        st.caption(
            f"🌤️ **Climate profile active** — "
            f"Mean annual DLI: {_gh_loc_dli2:.1f} mol/m²/day · "
            f"Ambient temperature: {_gh_loc_temp2:.1f}°C · "
            f"Natural DLI coverage for {gh_crop}: {_gh_nat_frac2*100:.0f}% "
            f"({'supplemental lighting required' if _gh_nat_frac2 < 1.0 else 'no supplemental lighting required'})"
        )

    # ── Key metrics ───────────────────────────────────────────────────────────
    # ── PDF Report ────────────────────────────────────────────────────────────
    def generate_gh_pdf_report(gh_inputs: dict, gh_r: dict) -> bytes:
        _fn = st.session_state.get("active_farm", {}).get("name", "")
        _mc = "pt" if gh_inputs.get("crop_source","").lower() == "polytunnel" else "gh"
        return _build_feasibility_pdf(gh_r, gh_inputs, _mc, farm_name=_fn)

    gh_pdf_col1, gh_pdf_col2 = st.columns([5, 1])
    with gh_pdf_col2:
        if st.button("📄 Download PDF Report", key="gh_pdf_btn", use_container_width=True):
            with st.spinner("Generating PDF..."):
                gh_pdf_bytes = generate_gh_pdf_report(gh_inputs, gh_r)
                gh_filename = f"GH_Report_{gh_inputs['crop'].replace(' ','_').replace('/','').replace('(','').replace(')','_')}_{gh_inputs['country']}_{date.today().strftime('%Y%m%d')}.pdf"
                st.download_button(label="⬇️ Save PDF", data=gh_pdf_bytes,
                                   file_name=gh_filename, mime="application/pdf",
                                   use_container_width=True, key="gh_pdf_dl")
    st.divider()

    st.subheader("Key Metrics")

    gh_energy_pct = (gh_r["annual_energy_cost"] / gh_r["annual_revenue"] * 100
                     if gh_r["annual_revenue"] > 0 else 0)
    _gh_loss  = gh_inputs["loss_rate"] / 100
    _gh_denom = (gh_r["effective_price"] * (1 - _gh_loss)
                 * gh_r["cycles_per_year"] * gh_r["effective_grow_area"])
    gh_be_yield = gh_r["total_annual_costs"] / _gh_denom if _gh_denom > 0 else None
    _gh_projected_yield = gh_crop_data["yield"]
    if gh_be_yield is not None:
        _gh_yield_gap = (_gh_projected_yield - gh_be_yield) / gh_be_yield * 100
        _gh_yield_gap_str = f"{_gh_yield_gap:+.1f}%"
    else:
        _gh_yield_gap_str = "N/A"

    gm1, gm2, gm3, gm4, gm5, gm6, gm7 = st.columns(7)
    gm1.metric("Annual Revenue",   f"${gh_r['annual_revenue']:,.0f}")
    gm2.metric("EBITDA",           f"${gh_r['ebitda']:,.0f}")
    gm3.metric("EBITDA Margin",    f"{gh_r['ebitda_margin']*100:.1f}%")
    gm4.metric("Total CAPEX",      f"${gh_r['total_capex']:,.0f}")
    gm5.metric("Payback",          f"{gh_r['payback_years']:.1f} yrs" if gh_r["payback_years"] else "N/A")
    gm6.metric("DSCR",             f"{gh_r['dscr']:.2f}" if gh_r["dscr"] else "N/A")
    gm7.metric(
        "Break-even Yield",
        f"{gh_be_yield:.2f} kg/m²/cycle" if gh_be_yield else "N/A",
        delta=_gh_yield_gap_str if gh_be_yield else None,
        delta_color="normal",
        help="Minimum yield needed to cover all costs. Delta = projected crop yield vs this threshold."
    )

    if gh_r["supplemental_dli"] > 0:
        st.caption(
            f"💡 Supplemental DLI: {gh_r['supplemental_dli']:.1f} mol/m²/day "
            f"({(1 - gh_crop_data['natural_dli_fraction'])*100:.0f}% artificial) — "
            f"{gh_r['lighting_kwh_m2_year']:.1f} kWh/m²/year for lighting"
        )
    else:
        st.caption("☀️ Natural light only — no supplemental lighting required.")

    if gh_r["dscr"] is not None and gh_r["dscr"] < 1.0:
        st.warning(
            f"⚠️ **Debt service coverage is low (DSCR = {gh_r['dscr']:.2f}x).** "
            f"Annual debt repayment (${gh_r['annual_debt_service']:,.0f}) exceeds EBITDA (${gh_r['ebitda']:,.0f}). "
            f"Consider reducing LTV, extending the loan term, increasing farm scale, or selecting a higher-margin crop."
        )

    # ── Multi-crop breakdown ──────────────────────────────────────────────────
    if gh_r.get("_is_multicrop"):
        st.divider()
        st.subheader("Per-Crop Breakdown")
        _gh_mc_rows = []
        for _mc in gh_r["_crop_results"]:
            _gh_mc_rows.append({
                "Crop":           _mc["crop"],
                "Area %":         f"{_mc['pct']:.0f}%",
                "Annual kg":      f"{_mc['total_annual_kg']:,.0f}",
                "Price ($/kg)":   f"${_mc['effective_price']:.2f}",
                "Revenue":        f"${_mc['annual_revenue']:,.0f}",
                "Variable Cost":  f"${_mc['annual_variable_cost']:,.0f}",
                "Labour":         f"${_mc['annual_labour_cost']:,.0f}",
                "EBITDA contrib": f"${_mc['ebitda']:,.0f}",
            })
        st.dataframe(pd.DataFrame(_gh_mc_rows), use_container_width=True, hide_index=True)
        st.caption(
            "Energy cost and CAPEX are shared farm infrastructure — "
            "computed once on the full farm area and shown in the combined metrics above."
        )
        st.divider()
    # ── Save as Farm Profile ──────────────────────────────────────────────────
    st.divider()
    gh_save_col1, gh_save_col2 = st.columns([5, 1])
    with gh_save_col2:
        if st.button("💾 Save as Farm Profile", key="gh_save_btn", use_container_width=True):
            st.session_state["gh_show_save_form"] = True

    if st.session_state["gh_show_save_form"]:
        with st.container(border=True):
            _gh_active   = st.session_state.get("active_farm")
            _save_lat = st.session_state.get("shared_lat")
            _save_lon = st.session_state.get("shared_lng")
            _climate_data = {}
            if _save_lat and _save_lon:
                with st.spinner("🌤️ Fetching climate profile for this location…"):
                    try:
                        from core.climate import fetch_climate_profile
                        _climate_data = fetch_climate_profile(_save_lat, _save_lon)
                    except Exception:
                        _climate_data = {}
            _gh_modality = "polytunnel" if gh_crop_source == "Polytunnel" else "greenhouse"
            _gh_payload  = {
                "country":           gh_inputs["country"],
                "crop":              (_gh_crop_mix[0]["crop"] if _gh_mix_valid and _gh_crop_mix else gh_inputs["crop"]),
                "footprint":         gh_inputs["footprint"],
                "automation":        gh_inputs["automation"],
                "price_scenario":    gh_inputs["price_scenario"],
                "price_override":    gh_inputs["price_override"],
                "packaging_cost":    gh_inputs["packaging_cost"],
                "loss_rate":         gh_inputs["loss_rate"],
                "net_grow_factor":   gh_inputs["net_grow_factor"],
                "walkways_factor":   gh_inputs["walkways_factor"],
                "water_price":       gh_inputs["water_price"],
                "rent_monthly":      gh_inputs["rent_monthly"],
                "real_estate_capex": gh_inputs["real_estate_capex"],
                "harvest_mode":      gh_inputs["harvest_mode"],
                "depreciation_years": gh_inputs["depreciation_years"],
                "tax_rate":          gh_inputs["tax_rate"],
                "ltv":               gh_inputs["ltv"],
                "interest_rate":     gh_inputs["interest_rate"],
                "loan_term_years":   gh_inputs["loan_term_years"],
                "lat":               st.session_state.get("shared_lat"),
                "lon":               st.session_state.get("shared_lng"),
                "ambient_temp_annual": _climate_data.get("ambient_temp_annual"),
                "mean_annual_dli":     _climate_data.get("mean_annual_dli"),
                "agriculture_type":  _gh_modality,
                "modality":          _gh_modality,
                "crop_source":       gh_inputs["crop_source"],
                "discount_rate":     gh_inputs["discount_rate"],
                "metadata":          {},
                "model_snapshot":    json.dumps(gh_r),
                "model_updated_at":  date.today().isoformat(),
                "crop_mix_json":     json.dumps(_gh_crop_mix) if _gh_mix_valid else None,
                "notes":             None,
            }
            if _gh_active:
                st.markdown(f"**Update** existing farm **{_gh_active['name']}**, or save as a new profile.")
                _gu1, _gu2, _gu3 = st.columns([2, 2, 1])
                with _gu1:
                    if st.button("✅ Update existing farm", use_container_width=True, key="gh_update_btn"):
                        try:
                            supabase.table("farms").update(_gh_payload).eq("id", _gh_active["id"]).execute()
                            st.session_state["active_farm"] = {**_gh_active, **_gh_payload}
                            st.success(f"✅ Farm **{_gh_active['name']}** updated.")
                            if _climate_data.get("mean_annual_dli"):
                                st.caption(f"🌤️ Climate profile saved — Mean DLI: {_climate_data['mean_annual_dli']:.1f} mol/m²/day · Ambient temp: {_climate_data['ambient_temp_annual']:.1f}°C")
                            st.session_state["gh_show_save_form"] = False
                            st.rerun()
                        except Exception as e:
                            st.error(f"Update failed: {e}")
                with _gu2:
                    gh_farm_name = st.text_input("New farm name", key="gh_farm_name_input", placeholder="Enter name for new profile")
                    if st.button("➕ Save as new farm", use_container_width=True, key="gh_saveas_btn"):
                        if not gh_farm_name.strip():
                            st.error("Please enter a name for the new farm profile.")
                        else:
                            try:
                                supabase.table("farms").insert({**_gh_payload, "name": gh_farm_name.strip(), "owner_id": current_user()}).execute()
                                st.success(f"✅ New farm profile '{gh_farm_name.strip()}' saved.")
                                if _climate_data.get("mean_annual_dli"):
                                    st.caption(f"🌤️ Climate profile saved — Mean DLI: {_climate_data['mean_annual_dli']:.1f} mol/m²/day · Ambient temp: {_climate_data['ambient_temp_annual']:.1f}°C")
                                st.session_state["gh_show_save_form"] = False
                                st.rerun()
                            except Exception as e:
                                st.error(f"Could not save: {e}")
                with _gu3:
                    if st.button("✖ Cancel", use_container_width=True, key="gh_cancel_save"):
                        st.session_state["gh_show_save_form"] = False
                        st.rerun()
            else:
                st.markdown("**Save current configuration as a Farm Profile**")
                st.caption("Saves all parameters so you can track harvests in the Harvest Tracker.")
                gh_farm_name = st.text_input("Farm name", key="gh_farm_name_input")
                _gn1, _gn2 = st.columns([3, 1])
                with _gn1:
                    if st.button("✅ Confirm Save", key="gh_confirm_save", use_container_width=True):
                        if not gh_farm_name.strip():
                            st.error("Please enter a farm name.")
                        else:
                            try:
                                supabase.table("farms").insert({**_gh_payload, "name": gh_farm_name.strip(), "owner_id": current_user()}).execute()
                                st.success(f"Farm profile '{gh_farm_name.strip()}' saved.")
                                if _climate_data.get("mean_annual_dli"):
                                    st.caption(f"🌤️ Climate profile saved — Mean DLI: {_climate_data['mean_annual_dli']:.1f} mol/m²/day · Ambient temp: {_climate_data['ambient_temp_annual']:.1f}°C")
                                st.session_state["gh_show_save_form"] = False
                                st.rerun()
                            except Exception as e:
                                st.error(f"Could not save farm profile: {e}")
                with _gn2:
                    if st.button("✖ Cancel", key="gh_cancel_new", use_container_width=True):
                        st.session_state["gh_show_save_form"] = False
                        st.rerun()

    st.divider()

    # ── EBITDA Bridge ─────────────────────────────────────────────────────────
    st.subheader("EBITDA Bridge")
    gh_bridge_labels = ["Revenue", "Variable", "Water", "Energy", "Labour", "Rent", "Maintenance", "EBITDA"]
    gh_bridge_values = [
        gh_r["annual_revenue"], -gh_r["annual_variable_cost"], -gh_r["annual_water_cost"],
        -gh_r["annual_energy_cost"], -gh_r["annual_labour_cost"],
        -gh_r["annual_rent"], -gh_r["annual_maintenance"], gh_r["ebitda"],
    ]
    gh_bar_colors = []
    for _i, _v in enumerate(gh_bridge_values):
        if _i == 0:
            gh_bar_colors.append("rgba(0,229,160,0.85)")
        elif _i == len(gh_bridge_values) - 1:
            gh_bar_colors.append("rgba(0,229,160,0.85)" if _v >= 0 else "rgba(255,77,77,0.85)")
        else:
            gh_bar_colors.append("rgba(255,77,77,0.6)")
    gh_fig_bridge = go.Figure(go.Bar(
        x=gh_bridge_labels, y=gh_bridge_values,
        marker_color=gh_bar_colors,
        text=[f"${abs(_v):,.0f}" for _v in gh_bridge_values],
        textposition="outside",
    ))
    gh_fig_bridge.update_layout(
        plot_bgcolor="#ffffff", paper_bgcolor="#ffffff",
        font_color="#161a16", showlegend=False,
        yaxis=dict(showgrid=False), xaxis=dict(showgrid=False),
        height=380, margin=dict(t=30, b=20),
    )
    st.plotly_chart(gh_fig_bridge, use_container_width=True)

    st.divider()

    # ── Cost + CAPEX donuts ───────────────────────────────────────────────────
    gh_col_cost, gh_col_capex = st.columns(2)
    with gh_col_cost:
        st.subheader("Annual Cost Breakdown")
        gh_fig_cost = go.Figure(go.Pie(
            labels=["Energy", "Labour", "Variable", "Water", "Maintenance", "Rent"],
            values=[gh_r["annual_energy_cost"], gh_r["annual_labour_cost"],
                    gh_r["annual_variable_cost"], gh_r["annual_water_cost"],
                    gh_r["annual_maintenance"], gh_r["annual_rent"]],
            hole=0.45,
            marker_colors=["#ff4d4d", "#ffc13d", "#00e5a0", "#4fc3f7", "#ba68c8", "#ef9a9a"],
        ))
        gh_fig_cost.update_layout(
            plot_bgcolor="#ffffff", paper_bgcolor="#ffffff",
            font_color="#161a16", height=320, margin=dict(t=10, b=10),
        )
        st.plotly_chart(gh_fig_cost, use_container_width=True)
    with gh_col_capex:
        st.subheader("CAPEX Breakdown")
        gh_fig_capex = go.Figure(go.Pie(
            labels=["Structure", "Climate", "Irrigation", "Lighting", "Automation", "Real Estate"],
            values=[gh_r["structure_capex"], gh_r["climate_capex"], gh_r["irrigation_capex"],
                    gh_r["lighting_capex"], gh_r["automation_capex"], gh_r["real_estate_capex"]],
            hole=0.45,
            marker_colors=["#00e5a0", "#26c6da", "#66bb6a", "#ffa726", "#ab47bc", "#8d6e63"],
        ))
        gh_fig_capex.update_layout(
            plot_bgcolor="#ffffff", paper_bgcolor="#ffffff",
            font_color="#161a16", height=320, margin=dict(t=10, b=10),
        )
        st.plotly_chart(gh_fig_capex, use_container_width=True)

    st.divider()

    # ── DCF chart ─────────────────────────────────────────────────────────────
    st.subheader("Cumulative NPV — 10-year DCF")
    gh_fig_dcf = go.Figure()
    gh_fig_dcf.add_trace(go.Scatter(
        x=[d["year"] for d in gh_r["dcf_cashflows"]],
        y=[d["cumulative_npv"] for d in gh_r["dcf_cashflows"]],
        mode="lines+markers", line=dict(color="#00e5a0", width=2),
        fill="tozeroy", fillcolor="rgba(0,229,160,0.1)",
    ))
    gh_fig_dcf.add_hline(y=0, line_dash="dash", line_color="rgba(255,255,255,0.3)")
    gh_fig_dcf.update_layout(
        plot_bgcolor="#ffffff", paper_bgcolor="#ffffff",
        font_color="#161a16", height=300,
        xaxis=dict(title="Year", showgrid=False),
        yaxis=dict(title="Cumulative NPV ($)", showgrid=False),
        margin=dict(t=10, b=10),
    )
    st.plotly_chart(gh_fig_dcf, use_container_width=True)

    st.divider()

    # ── Full results table ────────────────────────────────────────────────────
    st.subheader("Full Results")
    st.dataframe(pd.DataFrame({
        "Metric": [
            "Effective Grow Area (m²)", "Gross Area (m²)", "Structure Type",
            "Cycles / Year", "Harvest Mode", "Total Annual kg", "Price ($/kg)",
            "Annual Revenue", "Energy Cost", "Variable Cost", "Water Cost",
            "Labour Cost", "Maintenance", "Rent", "Total Annual Costs",
            "EBITDA", "EBITDA Margin", "Total CAPEX", "Payback (years)",
            "Annual Labour Hours", "Annual kWh", "Net Income", "NPV (10yr)",
        ],
        "Value": [
            f"{gh_r['effective_grow_area']:,.0f}",
            f"{gh_r['gross_area']:,.0f}",
            gh_r["structure_type"],
            gh_r["cycles_per_year"],
            gh_r["harvest_mode"],
            f"{gh_r['total_annual_kg']:,.0f}",
            f"${gh_r['effective_price']:.2f}",
            f"${gh_r['annual_revenue']:,.0f}",
            f"${gh_r['annual_energy_cost']:,.0f}",
            f"${gh_r['annual_variable_cost']:,.0f}",
            f"${gh_r['annual_water_cost']:,.0f}",
            f"${gh_r['annual_labour_cost']:,.0f}",
            f"${gh_r['annual_maintenance']:,.0f}",
            f"${gh_r['annual_rent']:,.0f}",
            f"${gh_r['total_annual_costs']:,.0f}",
            f"${gh_r['ebitda']:,.0f}",
            f"{gh_r['ebitda_margin']*100:.1f}%",
            f"${gh_r['total_capex']:,.0f}",
            f"{gh_r['payback_years']:.1f}" if gh_r["payback_years"] else "N/A",
            f"{gh_r['annual_labour_hours']:,.0f}",
            f"{gh_r['annual_kwh']:,.0f}",
            f"${gh_r['net_income']:,.0f}",
            f"${gh_r['npv']:,.0f}",
        ],
    }), use_container_width=True, hide_index=True)

    # ═══════════════════════════════════════════════════════════════════════════
    # COUNTRY & CROP COMPARISON
    # ═══════════════════════════════════════════════════════════════════════════
    st.divider()
    st.subheader("🌍 Viability Comparison")
    st.caption("All calculations use the current sidebar inputs. Only the dimension being compared changes.")

    gh_comp_tab1, gh_comp_tab2 = st.tabs(["Compare Countries", "Compare Crops"])

    with gh_comp_tab1:
        gh_country_metric = st.selectbox(
            "Rank by",
            ["EBITDA", "Energy % of Revenue", "Payback (years)", "EBITDA Margin (%)"],
            key="gh_country_metric_select",
        )
        gh_country_results = []
        for _cn in COUNTRIES.keys():
            _ci = dict(gh_inputs); _ci["country"] = _cn
            try:
                _cr = calculate_greenhouse(_ci)
                _ep = _cr["annual_energy_cost"]/_cr["annual_revenue"]*100 if _cr["annual_revenue"]>0 else 999
                gh_country_results.append({
                    "Country": _cn, "EBITDA": _cr["ebitda"],
                    "Energy % of Revenue": _ep,
                    "Payback (years)": _cr["payback_years"] if _cr["payback_years"] else 999,
                    "EBITDA Margin (%)": _cr["ebitda_margin"]*100,
                })
            except Exception:
                continue
        if gh_country_results:
            _gh_df_c = pd.DataFrame(gh_country_results)
            _gh_asc  = gh_country_metric in ("Energy % of Revenue","Payback (years)")
            _gh_df_c = _gh_df_c.sort_values(gh_country_metric, ascending=_gh_asc).reset_index(drop=True)
            def _gh_cbar(row, m):
                if m=="EBITDA": return "rgba(0,229,160,0.75)" if row["EBITDA"]>=0 else "rgba(255,77,77,0.75)"
                if m=="Energy % of Revenue": return "rgba(0,229,160,0.75)" if row["Energy % of Revenue"]<40 else "rgba(255,77,77,0.75)"
                if m=="Payback (years)": return "rgba(0,229,160,0.75)" if 0<row["Payback (years)"]<10 else "rgba(255,77,77,0.75)"
                return "rgba(0,229,160,0.75)" if row["EBITDA Margin (%)"]>=0 else "rgba(255,77,77,0.75)"
            _gh_bc = [_gh_cbar(r, gh_country_metric) for _,r in _gh_df_c.iterrows()]
            _gh_fig_c = go.Figure(go.Bar(
                x=_gh_df_c[gh_country_metric], y=_gh_df_c["Country"], orientation="h",
                marker_color=_gh_bc,
                text=_gh_df_c[gh_country_metric].apply(
                    lambda v: f"${v:,.0f}" if gh_country_metric=="EBITDA"
                    else (f"{v:.1f}%" if "%" in gh_country_metric
                    else (f"{v:.1f} yrs" if v<900 else "N/A"))),
                textposition="outside"))
            if gh_country_metric=="Energy % of Revenue":
                _gh_fig_c.add_vline(x=40, line_dash="dash", line_color="rgba(255,193,61,0.6)",
                                    annotation_text="40% threshold", annotation_font_color="#ffc13d")
            _gh_fig_c.update_layout(
                plot_bgcolor="#ffffff", paper_bgcolor="#ffffff",
                font_color="#161a16", height=max(500,len(_gh_df_c)*22),
                margin=dict(l=10,r=100,t=20,b=20),
                xaxis=dict(showgrid=False,zeroline=False),
                yaxis=dict(showgrid=False,autorange="reversed"))
            st.plotly_chart(_gh_fig_c, use_container_width=True)
            _gh_viable_c = (_gh_df_c["Energy % of Revenue"]<40).sum()
            st.caption(f"**{_gh_viable_c} of {len(_gh_df_c)} countries** show energy below 40% of revenue for this crop and setup.")

    with gh_comp_tab2:
        _gh_crop_pool = list(GREENHOUSE_CROPS.keys()) if gh_crop_source=="Greenhouse" else list(POLYTUNNEL_CROPS.keys())
        gh_crop_metric = st.selectbox(
            "Rank by",
            ["EBITDA","EBITDA Margin (%)","Energy % of Revenue","Payback (years)"],
            key="gh_crop_metric_select",
        )
        gh_crop_results = []
        for _crn in _gh_crop_pool:
            _cri = dict(gh_inputs); _cri["crop"] = _crn; _cri["harvest_mode"] = "Single"; _cri["price_override"] = 0
            try:
                _crr = calculate_greenhouse(_cri)
                _ep2 = _crr["annual_energy_cost"]/_crr["annual_revenue"]*100 if _crr["annual_revenue"]>0 else 999
                gh_crop_results.append({
                    "Crop": _crn, "EBITDA": _crr["ebitda"],
                    "EBITDA Margin (%)": _crr["ebitda_margin"]*100,
                    "Energy % of Revenue": _ep2,
                    "Payback (years)": _crr["payback_years"] if _crr["payback_years"] else 999,
                })
            except Exception:
                continue
        if gh_crop_results:
            _gh_df_cr = pd.DataFrame(gh_crop_results)
            _gh_asc2  = gh_crop_metric in ("Energy % of Revenue","Payback (years)")
            _gh_df_cr = _gh_df_cr.sort_values(gh_crop_metric, ascending=_gh_asc2).reset_index(drop=True)
            def _gh_crbar(row, m):
                if m=="EBITDA": return "rgba(0,229,160,0.75)" if row["EBITDA"]>=0 else "rgba(255,77,77,0.75)"
                if m=="Energy % of Revenue": return "rgba(0,229,160,0.75)" if row["Energy % of Revenue"]<40 else "rgba(255,77,77,0.75)"
                if m=="Payback (years)": return "rgba(0,229,160,0.75)" if 0<row["Payback (years)"]<10 else "rgba(255,77,77,0.75)"
                return "rgba(0,229,160,0.75)" if row["EBITDA Margin (%)"]>=0 else "rgba(255,77,77,0.75)"
            _gh_brc = [_gh_crbar(r, gh_crop_metric) for _,r in _gh_df_cr.iterrows()]
            _gh_fig_cr = go.Figure(go.Bar(
                x=_gh_df_cr[gh_crop_metric], y=_gh_df_cr["Crop"], orientation="h",
                marker_color=_gh_brc,
                text=_gh_df_cr[gh_crop_metric].apply(
                    lambda v: f"${v:,.0f}" if gh_crop_metric=="EBITDA"
                    else (f"{v:.1f}%" if "%" in gh_crop_metric
                    else (f"{v:.1f} yrs" if v<900 else "N/A"))),
                textposition="outside"))
            if gh_crop_metric=="Energy % of Revenue":
                _gh_fig_cr.add_vline(x=40, line_dash="dash", line_color="rgba(255,193,61,0.6)",
                                     annotation_text="40% threshold", annotation_font_color="#ffc13d")
            _gh_fig_cr.update_layout(
                plot_bgcolor="#ffffff", paper_bgcolor="#ffffff",
                font_color="#161a16", height=max(400,len(_gh_df_cr)*22),
                margin=dict(l=10,r=100,t=20,b=20),
                xaxis=dict(showgrid=False,zeroline=False),
                yaxis=dict(showgrid=False,autorange="reversed"))
            st.plotly_chart(_gh_fig_cr, use_container_width=True)
            _gh_viable_cr = (_gh_df_cr["Energy % of Revenue"]<40).sum()
            st.caption(f"**{_gh_viable_cr} of {len(_gh_df_cr)} crops** show energy below 40% of revenue. Normalised to Single harvest.")

    # ═══════════════════════════════════════════════════════════════════════════
    # SENSITIVITY ANALYSIS
    # ═══════════════════════════════════════════════════════════════════════════
    st.divider()
    st.subheader("🔬 Sensitivity Analysis")

    def _gh_run_mult(base, kwh_m=1.0, lab_m=1.0, yld_m=1.0, prc_m=1.0):
        import core.greenhouse_data_tables as _ghdt
        import copy as _copy
        _cn = base["country"]
        from core.data_tables import COUNTRIES as _CTRS
        import core.data_tables as _cdt
        _orig_c = _CTRS[_cn]
        _mod_c  = _copy.deepcopy(_orig_c)
        _mod_c["kwh"]    = _orig_c["kwh"]    * kwh_m
        _mod_c["labour"] = _orig_c["labour"] * lab_m
        _mod_i = _copy.deepcopy(base)
        if prc_m != 1.0 or yld_m != 1.0:
            _src = base.get("crop_source","greenhouse")
            _cd  = _ghdt.POLYTUNNEL_CROPS if _src=="polytunnel" else _ghdt.GREENHOUSE_CROPS
            _orig_crop = _cd[base["crop"]]
            _mod_crop  = _copy.deepcopy(_orig_crop)
            _mod_crop["yield"]    = _orig_crop["yield"]    * yld_m
            _mod_crop["yield_h2"] = _orig_crop["yield_h2"] * yld_m
            _mod_crop["yield_h3"] = _orig_crop["yield_h3"] * yld_m
            if base.get("price_override",0)>0:
                _mod_i["price_override"] = base["price_override"] * prc_m
            else:
                _base_price = _orig_crop[f"price_{base['price_scenario']}"]
                _mod_i["price_override"] = _base_price * prc_m
            _cd[base["crop"]] = _mod_crop
        _cdt.COUNTRIES[_cn] = _mod_c
        try:
            if _gh_mix_valid:
                _res = _run_multicrop_generic(_mod_i, _gh_crop_mix,
                                              calculate_greenhouse, _gh_crop_data_dict)
            else:
                _res = calculate_greenhouse(_mod_i)
        finally:
            _cdt.COUNTRIES[_cn] = _orig_c
            _src2 = base.get("crop_source","greenhouse")
            _cd2  = _ghdt.POLYTUNNEL_CROPS if _src2=="polytunnel" else _ghdt.GREENHOUSE_CROPS
            if prc_m != 1.0 or yld_m != 1.0:
                _cd2[base["crop"]] = _orig_crop
        return _res

    st.markdown("#### Tornado Chart — EBITDA Sensitivity")
    st.caption("Each bar shows how EBITDA changes when one variable is stressed while all others stay at base values.")

    _gh_base_ebitda = gh_r["ebitda"]
    _gh_tvars = [
        {"label":"Energy Price",  "pess":_gh_run_mult(gh_inputs,kwh_m=1.50)["ebitda"], "opt":_gh_run_mult(gh_inputs,kwh_m=0.70)["ebitda"],
         "pess_label":"Energy price +50%","opt_label":"Energy price −30%","rationale":"Energy cost volatility is a primary greenhouse risk."},
        {"label":"Selling Price", "pess":_gh_run_mult(gh_inputs,prc_m=0.80)["ebitda"], "opt":_gh_run_mult(gh_inputs,prc_m=1.20)["ebitda"],
         "pess_label":"Selling price −20%","opt_label":"Selling price +20%","rationale":"Wholesale price volatility for fresh produce."},
        {"label":"Yield",         "pess":_gh_run_mult(gh_inputs,yld_m=0.80)["ebitda"], "opt":_gh_run_mult(gh_inputs,yld_m=1.20)["ebitda"],
         "pess_label":"Yield −20%","opt_label":"Yield +20%","rationale":"Actual yields vary with cultivar and growing conditions."},
        {"label":"Labour Cost",   "pess":_gh_run_mult(gh_inputs,lab_m=1.30)["ebitda"], "opt":_gh_run_mult(gh_inputs,lab_m=0.80)["ebitda"],
         "pess_label":"Labour cost +30%","opt_label":"Labour cost −20%","rationale":"Structural wage inflation vs automation gains."},
    ]
    for _tv in _gh_tvars:
        _tv["delta_pess"] = _tv["pess"] - _gh_base_ebitda
        _tv["delta_opt"]  = _tv["opt"]  - _gh_base_ebitda
        _tv["swing"]      = abs(_tv["delta_opt"] - _tv["delta_pess"])
    _gh_tvars.sort(key=lambda x: x["swing"], reverse=True)

    _gh_fig_torn = go.Figure()
    for _tv in _gh_tvars:
        _gh_fig_torn.add_trace(go.Bar(
            name="Pessimistic", y=[_tv["label"]], x=[_tv["delta_pess"]], orientation="h",
            marker_color="rgba(255,77,77,0.75)", showlegend=(_tv==_gh_tvars[0]),
            text=f"${_tv['delta_pess']:,.0f}", textposition="outside",
            customdata=[[_tv["pess_label"],_tv["rationale"]]],
            hovertemplate="<b>%{y}</b><br>EBITDA delta: %{x:$,.0f}<br><i>%{customdata[0]}</i><extra></extra>"))
        _gh_fig_torn.add_trace(go.Bar(
            name="Optimistic", y=[_tv["label"]], x=[_tv["delta_opt"]], orientation="h",
            marker_color="rgba(0,229,160,0.75)", showlegend=(_tv==_gh_tvars[0]),
            text=f"${_tv['delta_opt']:,.0f}", textposition="outside",
            customdata=[[_tv["opt_label"],_tv["rationale"]]],
            hovertemplate="<b>%{y}</b><br>EBITDA delta: %{x:$,.0f}<br><i>%{customdata[0]}</i><extra></extra>"))
    _gh_fig_torn.add_vline(x=0, line_dash="dash", line_color="rgba(255,255,255,0.4)")
    _gh_fig_torn.update_layout(
        barmode="overlay", plot_bgcolor="#ffffff", paper_bgcolor="#ffffff",
        font_color="#161a16", height=320, margin=dict(l=10,r=80,t=20,b=20),
        xaxis=dict(title="EBITDA delta from base ($)",showgrid=False,zeroline=False),
        yaxis=dict(showgrid=False),
        legend=dict(orientation="h",yanchor="bottom",y=1.02,xanchor="right",x=1))
    st.plotly_chart(_gh_fig_torn, use_container_width=True)

    st.divider()
    st.markdown("#### Scenario Comparison")
    st.caption("Define up to 4 named scenarios by adjusting multipliers. The Base Case always shows the current sidebar inputs.")

    if "gh_scenarios" not in st.session_state:
        st.session_state["gh_scenarios"] = []

    with st.expander("➕ Define a new scenario", expanded=len(st.session_state["gh_scenarios"])==0):
        _gh_sc_name = st.text_input("Scenario name", value="Scenario 1", key="gh_sc_name")
        _gh_sc1, _gh_sc2 = st.columns(2)
        with _gh_sc1:
            _gh_sc_energy = st.slider("Energy price multiplier",  0.3, 3.0, 1.0, 0.05, key="gh_sc_energy")
            _gh_sc_yield  = st.slider("Yield multiplier",         0.3, 2.0, 1.0, 0.05, key="gh_sc_yield")
        with _gh_sc2:
            _gh_sc_price  = st.slider("Selling price multiplier", 0.3, 2.0, 1.0, 0.05, key="gh_sc_price")
            _gh_sc_labour = st.slider("Labour cost multiplier",   0.3, 3.0, 1.0, 0.05, key="gh_sc_labour")

        if st.button("💾 Save Scenario", key="gh_save_sc", use_container_width=True):
            if len(st.session_state["gh_scenarios"]) >= 4:
                st.warning("Maximum 4 scenarios reached.")
            else:
                _gh_sc_res = _gh_run_mult(gh_inputs, kwh_m=_gh_sc_energy, lab_m=_gh_sc_labour,
                                          yld_m=_gh_sc_yield, prc_m=_gh_sc_price)
                st.session_state["gh_scenarios"].append({
                    "name": _gh_sc_name, "energy_mult": _gh_sc_energy, "yield_mult": _gh_sc_yield,
                    "price_mult": _gh_sc_price, "labour_mult": _gh_sc_labour, "result": _gh_sc_res})
                st.success(f"Scenario '{_gh_sc_name}' saved.")

        if st.session_state["gh_scenarios"]:
            if st.button("🗑️ Clear all scenarios", key="gh_clear_sc", use_container_width=True):
                st.session_state["gh_scenarios"] = []
                st.rerun()

    if st.session_state["gh_scenarios"]:
        for _idx, _sc in enumerate(st.session_state["gh_scenarios"]):
            _dc1, _dc2 = st.columns([8,1])
            with _dc1:
                st.caption(f"**{_sc['name']}** — energy ×{_sc['energy_mult']} / yield ×{_sc['yield_mult']} / price ×{_sc['price_mult']} / labour ×{_sc['labour_mult']}")
            with _dc2:
                if st.button("🗑️", key=f"gh_del_sc_{_idx}"):
                    st.session_state["gh_scenarios"].pop(_idx)
                    st.rerun()

        _gh_sc_names   = ["Base Case"] + [s["name"] for s in st.session_state["gh_scenarios"]]
        _gh_sc_results = [gh_r] + [s["result"] for s in st.session_state["gh_scenarios"]]

        _gh_fig_comp = go.Figure()
        _gh_comp_metrics = {
            "EBITDA":      [res["ebitda"]            for res in _gh_sc_results],
            "Revenue":     [res["annual_revenue"]     for res in _gh_sc_results],
            "Energy Cost": [res["annual_energy_cost"] for res in _gh_sc_results],
            "Labour Cost": [res["annual_labour_cost"] for res in _gh_sc_results],
        }
        for _i, (_mn, _mv) in enumerate(_gh_comp_metrics.items()):
            _gh_fig_comp.add_trace(go.Bar(name=_mn, x=_gh_sc_names, y=_mv,
                marker_color=["#00e5a0","#ffc13d","#4fc3f7","#ba68c8"][_i],
                text=[f"${v:,.0f}" for v in _mv], textposition="outside"))
        _gh_fig_comp.update_layout(
            barmode="group", plot_bgcolor="#ffffff", paper_bgcolor="#ffffff",
            font_color="#161a16", height=420, margin=dict(t=30,b=20),
            xaxis=dict(showgrid=False), yaxis=dict(showgrid=False,title="$"),
            legend=dict(orientation="h",yanchor="bottom",y=1.02,xanchor="right",x=1))
        st.plotly_chart(_gh_fig_comp, use_container_width=True)

        _gh_sc_rows = []
        for _sn, _sr in zip(_gh_sc_names, _gh_sc_results):
            _ep3 = f"{_sr['annual_energy_cost']/_sr['annual_revenue']*100:.1f}%" if _sr["annual_revenue"]>0 else "N/A"
            _gh_sc_rows.append({
                "Scenario": _sn,
                "Revenue":  f"${_sr['annual_revenue']:,.0f}",
                "Energy Cost": f"${_sr['annual_energy_cost']:,.0f}",
                "Labour Cost": f"${_sr['annual_labour_cost']:,.0f}",
                "EBITDA":   f"${_sr['ebitda']:,.0f}",
                "EBITDA Margin": f"{_sr['ebitda_margin']*100:.1f}%",
                "Payback (yrs)": f"{_sr['payback_years']:.1f}" if _sr["payback_years"] else "N/A",
                "Energy % of Revenue": _ep3,
            })
        _gh_sc_df = pd.DataFrame(_gh_sc_rows)

        def _gh_highlight_ep(row):
            v_str = row["Energy % of Revenue"]
            if v_str=="N/A": return [""]*len(row)
            try: v=float(v_str.replace("%",""))
            except: return [""]*len(row)
            if v>60:   return [""]*( len(row)-1)+["background-color:rgba(255,77,77,0.25);color:#ff4d4d"]
            elif v>40: return [""]*( len(row)-1)+["background-color:rgba(255,193,61,0.25);color:#ffc13d"]
            else:      return [""]*( len(row)-1)+["background-color:rgba(0,229,160,0.15);color:#00e5a0"]

        st.dataframe(_gh_sc_df.style.apply(_gh_highlight_ep,axis=1),
                     use_container_width=True, hide_index=True)
    else:
        st.info("No scenarios saved yet. Use the form above to define and save your first scenario.")


elif modality in ("🐟 Decoupled Aquaponics", "♻️ Coupled Aquaponics"):

    _aq_mode  = "decoupled" if modality == "🐟 Decoupled Aquaponics" else "coupled"
    _aq_label = modality

    st.markdown(f"### {_aq_label}")

    # ── Session state defaults ────────────────────────────────────────────────
    _AQ_DEFAULTS = {
        "aq_country":               "Germany",
        "aq_plant_crop_source":     "Greenhouse",
        "aq_plant_crop":            "Lettuce (Romaine)",
        "aq_plant_footprint":       1000,
        "aq_automation":            "Medium",
        "aq_price_scenario":        "base",
        "aq_harvest_mode":          "Single",
        "aq_packaging_cost":        0.15,
        "aq_loss_rate":             5.0,
        "aq_net_grow_factor":       90.0,
        "aq_walkways_factor":       10.0,
        "aq_water_price":           2.0,
        "aq_rent_monthly":          0.0,
        "aq_real_estate_capex":     0.0,
        "aq_depreciation_years":    15,
        "aq_tax_rate":              25.0,
        "aq_ltv":                   60.0,
        "aq_interest_rate":         5.5,
        "aq_loan_term_years":       15,
        "aq_discount_rate":         8.0,
        "aq_species":               "Tilapia (Nile)",
        "aq_tank_volume_m3":        50.0,
        "aq_fish_price_scenario":   "base",
        "aq_target_temp_c":         26.0,
        "aq_fish_depreciation_years": 10,
        "aq_coupled_efficiency":    0.88,
        "aq_multi_crop":            False,
        "aq_crop_mix":              [{"crop": "Lettuce (Romaine)", "pct": 100}],
    }
    for _k, _v in _AQ_DEFAULTS.items():
        if _k not in st.session_state:
            st.session_state[_k] = _v
    if "aq_show_save_form" not in st.session_state:
        st.session_state["aq_show_save_form"] = False

    # ── Sidebar ───────────────────────────────────────────────────────────────
    with st.sidebar:
        st.header("Aquaponics Parameters")

        # Plant parameters
        st.subheader("🌿 Plant Side")
        aq_country_list = list(COUNTRIES.keys())
        aq_country = st.selectbox("Country", aq_country_list,
            index=aq_country_list.index(st.session_state["aq_country"]) if st.session_state["aq_country"] in aq_country_list else 0,
            key="aq_country")

        aq_plant_crop_source = st.radio("Crop source", ["Greenhouse", "Polytunnel"],
            index=0 if st.session_state["aq_plant_crop_source"] == "Greenhouse" else 1,
            horizontal=True, key="aq_plant_crop_source")

        if _aq_mode == "coupled":
            _aq_allowed_crops = [c for c, v in CROP_NUTRIENT_DEMAND.items()
                                 if v.get("aquaponics_suitability") in ("high", "medium")]
            _aq_crop_list = [c for c in (GREENHOUSE_CROPS if aq_plant_crop_source == "Greenhouse"
                              else POLYTUNNEL_CROPS) if c in _aq_allowed_crops]
            if not _aq_crop_list:
                _aq_crop_list = list(GREENHOUSE_CROPS.keys())
            st.caption("♻️ Coupled mode: only aquaponics-compatible crops shown.")
        else:
            _aq_crop_list = list(GREENHOUSE_CROPS.keys() if aq_plant_crop_source == "Greenhouse"
                                 else POLYTUNNEL_CROPS.keys())

        # ── Multi-crop toggle ─────────────────────────────────────────────────
        aq_multi_crop_mode = st.toggle("Multi-crop mode (plant side)", value=False,
                                        key="aq_multi_crop")

        if not aq_multi_crop_mode:
            _aq_crop_def  = st.session_state["aq_plant_crop"]
            aq_plant_crop = st.selectbox("Plant crop", _aq_crop_list,
                index=_aq_crop_list.index(_aq_crop_def) if _aq_crop_def in _aq_crop_list else 0,
                key="aq_plant_crop")
        else:
            aq_plant_crop = _aq_crop_list[0]  # placeholder
            st.markdown("**Plant crop allocation** (must sum to 100%)")
            if "aq_crop_mix" not in st.session_state:
                st.session_state["aq_crop_mix"] = [{"crop": _aq_crop_list[0], "pct": 100}]
            _aq_mix = st.session_state["aq_crop_mix"]
            _aq_mix = [row for row in _aq_mix if row["crop"] in _aq_crop_list]
            if not _aq_mix:
                _aq_mix = [{"crop": _aq_crop_list[0], "pct": 100}]
            _aq_to_remove = None
            for _aci, _arow in enumerate(_aq_mix):
                _ac1, _ac2, _ac3 = st.columns([4, 2, 1])
                with _ac1:
                    _aq_mix[_aci]["crop"] = st.selectbox(
                        f"Crop {_aci+1}", _aq_crop_list,
                        index=_aq_crop_list.index(_arow["crop"]) if _arow["crop"] in _aq_crop_list else 0,
                        key=f"aq_mix_crop_{_aci}")
                with _ac2:
                    _aq_mix[_aci]["pct"] = st.number_input(
                        "%", min_value=1, max_value=100, value=int(_arow["pct"]),
                        step=1, key=f"aq_mix_pct_{_aci}")
                with _ac3:
                    if len(_aq_mix) > 1 and st.button("✕", key=f"aq_mix_del_{_aci}"):
                        _aq_to_remove = _aci
            if _aq_to_remove is not None:
                _aq_mix.pop(_aq_to_remove)
                st.session_state["aq_crop_mix"] = _aq_mix
                st.rerun()
            _aq_total_pct = sum(r["pct"] for r in _aq_mix)
            st.caption(f"Total allocated: **{_aq_total_pct}%**")
            if _aq_total_pct != 100:
                st.warning(f"⚠️ Must sum to 100%. Currently {_aq_total_pct}%.")
            if len(_aq_mix) < 6:
                if st.button("➕ Add crop", key="aq_mix_add"):
                    _aq_mix.append({"crop": _aq_crop_list[0], "pct": 1})
                    st.session_state["aq_crop_mix"] = _aq_mix
                    st.rerun()
            st.session_state["aq_crop_mix"] = _aq_mix

        aq_plant_footprint = st.number_input("Plant footprint (m²)",
            value=st.session_state["aq_plant_footprint"], step=100, min_value=50,
            key="aq_plant_footprint")

        _aq_cd = GREENHOUSE_CROPS.get(aq_plant_crop, POLYTUNNEL_CROPS.get(aq_plant_crop, {}))
        if _aq_cd.get("days_between", 0) > 0:
            _aq_hm_list = ["Single", "2 Harvests", "3 Harvests"]
            _aq_hm_def  = st.session_state["aq_harvest_mode"]
            aq_harvest_mode = st.selectbox("Harvest Mode", _aq_hm_list,
                index=_aq_hm_list.index(_aq_hm_def) if _aq_hm_def in _aq_hm_list else 0,
                key="aq_harvest_mode")
        else:
            st.selectbox("Harvest Mode", ["Single"], disabled=True)
            aq_harvest_mode = "Single"
            st.session_state["aq_harvest_mode"] = "Single"

        st.divider()

        # Fish parameters
        st.subheader("🐟 Fish Side")
        _aq_species_list = list(FISH_SPECIES.keys())
        aq_species = st.selectbox("Fish species", _aq_species_list,
            index=_aq_species_list.index(st.session_state["aq_species"]) if st.session_state["aq_species"] in _aq_species_list else 0,
            key="aq_species")

        if aq_species == "Atlantic Salmon":
            if _aq_mode == "coupled":
                st.error("🚫 Salmon incompatible with coupled aquaponics (cold water ≤14°C vs shared loop).")
            else:
                st.warning("⚠️ Salmon needs cold water (8–14°C). High heating costs in temperate climates.")

        aq_tank_volume = st.number_input("Tank volume (m³)",
            value=st.session_state["aq_tank_volume_m3"], step=10.0, min_value=5.0,
            key="aq_tank_volume_m3")

        aq_system_scale = "Commercial-scale (>100m³)" if aq_tank_volume >= 100 else "Small-scale (<100m³)"
        st.session_state["aq_system_scale"] = aq_system_scale
        st.caption(
            f"⚙️ System scale: **{aq_system_scale}** (auto-selected based on tank volume). "
            f"{'Commercial scale applies lower CAPEX rates per m³ due to economies of scale.' if aq_tank_volume >= 100 else 'Small-scale applies higher CAPEX rates per m³. Cross the 100 m³ threshold to unlock commercial rates.'}"
        )

        aq_target_temp = st.number_input("Fish target temp (°C)",
            value=st.session_state["aq_target_temp_c"], step=1.0, min_value=4.0, max_value=35.0,
            key="aq_target_temp_c",
            help=f"Ambient in {aq_country}: {COUNTRY_AMBIENT_TEMP.get(aq_country, 15.0):.1f}°C")

        _aq_fps_list = ["base", "low", "high"]
        aq_fish_price_scenario = st.selectbox("Fish price scenario", _aq_fps_list,
            index=_aq_fps_list.index(st.session_state["aq_fish_price_scenario"]),
            key="aq_fish_price_scenario")

        st.divider()

        # Shared parameters
        st.subheader("⚙️ Shared")
        aq_automation = st.selectbox("Automation", ["None","Low","Medium","High"],
            index=["None","Low","Medium","High"].index(st.session_state["aq_automation"]),
            key="aq_automation")
        aq_price_scenario = st.selectbox("Plant price scenario", ["base","low","high"],
            index=["base","low","high"].index(st.session_state["aq_price_scenario"]),
            key="aq_price_scenario")

        if _aq_mode == "coupled":
            aq_coupled_efficiency = st.slider("Coupled yield efficiency",
                0.70, 1.00, float(st.session_state["aq_coupled_efficiency"]), 0.01,
                key="aq_coupled_efficiency",
                help="Yield reduction vs greenhouse due to pH/EC compromise. Default 0.88.")
        else:
            aq_coupled_efficiency = 0.88

        st.divider()
        st.subheader("Advanced")
        aq_packaging_cost    = st.number_input("Packaging ($/kg)", value=st.session_state["aq_packaging_cost"], step=0.01, min_value=0.0, key="aq_packaging_cost")
        aq_loss_rate         = st.number_input("Plant loss rate (%)", value=st.session_state["aq_loss_rate"], step=0.5, min_value=0.0, max_value=100.0, key="aq_loss_rate")
        aq_net_grow_factor   = st.number_input("Net grow factor (%)", value=st.session_state["aq_net_grow_factor"], step=1.0, min_value=1.0, max_value=100.0, key="aq_net_grow_factor")
        aq_walkways_factor   = st.number_input("Walkways factor (%)", value=st.session_state["aq_walkways_factor"], step=1.0, min_value=0.0, max_value=50.0, key="aq_walkways_factor")
        aq_water_price       = st.number_input("Water price ($/m³)", value=st.session_state["aq_water_price"], step=0.1, min_value=0.0, key="aq_water_price")
        aq_rent_monthly      = st.number_input("Monthly rent ($)", value=st.session_state["aq_rent_monthly"], step=100.0, min_value=0.0, key="aq_rent_monthly")
        aq_real_estate_capex = st.number_input("Real estate CAPEX ($)", value=st.session_state["aq_real_estate_capex"], step=10000.0, min_value=0.0, key="aq_real_estate_capex")

        st.divider()
        st.subheader("Financial Structure")
        aq_dep_years  = st.number_input("Plant depreciation (yrs)", value=st.session_state["aq_depreciation_years"], step=1, min_value=1, key="aq_depreciation_years")
        aq_fish_dep   = st.number_input("Fish depreciation (yrs)", value=st.session_state["aq_fish_depreciation_years"], step=1, min_value=1, key="aq_fish_depreciation_years")
        aq_tax_rate   = st.number_input("Tax rate (%)", value=st.session_state["aq_tax_rate"], step=1.0, min_value=0.0, max_value=100.0, key="aq_tax_rate")
        aq_ltv        = st.number_input("LTV (%)", value=st.session_state["aq_ltv"], step=5.0, min_value=0.0, max_value=100.0, key="aq_ltv")
        aq_interest   = st.number_input("Interest rate (%)", value=st.session_state["aq_interest_rate"], step=0.1, min_value=0.0, key="aq_interest_rate")
        aq_loan_term  = st.number_input("Loan term (yrs)", value=st.session_state["aq_loan_term_years"], step=1, min_value=1, key="aq_loan_term_years")
        aq_discount   = st.number_input("Discount rate (%)", value=st.session_state["aq_discount_rate"], step=0.5, min_value=0.0, key="aq_discount_rate")

    # ── RUN CALCULATION ───────────────────────────────────────────────────────
    if _aq_mode == "coupled" and aq_species == "Atlantic Salmon":
        st.error("🚫 Cannot run: Atlantic Salmon is incompatible with coupled aquaponics. "
                 "Select a different species or switch to Decoupled mode.")
        st.stop()

    aq_inputs = {
        "aquaponics_mode":          _aq_mode,
        "country":                  aq_country,
        "plant_crop":               aq_plant_crop,
        "plant_crop_source":        aq_plant_crop_source.lower(),
        "plant_footprint":          aq_plant_footprint,
        "automation":               aq_automation,
        "price_scenario":           aq_price_scenario,
        "plant_price_override":     0.0,
        "packaging_cost":           aq_packaging_cost,
        "loss_rate":                aq_loss_rate,
        "net_grow_factor":          aq_net_grow_factor,
        "walkways_factor":          aq_walkways_factor,
        "water_price":              aq_water_price,
        "rent_monthly":             aq_rent_monthly,
        "real_estate_capex":        aq_real_estate_capex,
        "harvest_mode":             aq_harvest_mode,
        "depreciation_years":       aq_dep_years,
        "tax_rate":                 aq_tax_rate,
        "ltv":                      aq_ltv,
        "interest_rate":            aq_interest,
        "loan_term_years":          aq_loan_term,
        "discount_rate":            aq_discount,
        "ambient_temp_annual":    st.session_state.get("active_farm", {}).get("ambient_temp_annual"),
        "mean_annual_dli":        st.session_state.get("active_farm", {}).get("mean_annual_dli"),
        "species":                  aq_species,
        "tank_volume_m3":           aq_tank_volume,
        "system_scale":             aq_system_scale,
        "fish_price_scenario":      aq_fish_price_scenario,
        "price_override_fish":      0.0,
        "target_temp_c":            aq_target_temp,
        "fish_depreciation_years":  aq_fish_dep,
        "coupled_efficiency_factor": aq_coupled_efficiency,
    }

    _aq_multi_crop_mode = st.session_state.get("aq_multi_crop", False)
    _aq_crop_mix        = st.session_state.get("aq_crop_mix", [])
    _aq_mix_total       = sum(row["pct"] for row in _aq_crop_mix)
    _aq_mix_valid       = _aq_multi_crop_mode and len(_aq_crop_mix) > 0 and _aq_mix_total == 100

    if _aq_multi_crop_mode and not _aq_mix_valid:
        st.warning("⚠️ Fix plant crop allocation (must sum to 100%) before results are shown.")
        st.stop()

    if _aq_mix_valid:
        # Run plant side as multi-crop, fish side as single species
        _aq_plant_dict = POLYTUNNEL_CROPS if aq_inputs.get("plant_crop_source") == "polytunnel" else GREENHOUSE_CROPS
        # Build plant-only inputs for multi-crop engine
        _aq_plant_base = {
            "country":            aq_inputs["country"],
            "crop":               _aq_crop_mix[0]["crop"],
            "crop_source":        aq_inputs.get("plant_crop_source", "greenhouse"),
            "footprint":          aq_inputs["plant_footprint"],
            "automation":         aq_inputs["automation"],
            "price_scenario":     aq_inputs["price_scenario"],
            "plant_price_override": 0.0,
            "packaging_cost":     aq_inputs["packaging_cost"],
            "loss_rate":          aq_inputs["loss_rate"],
            "net_grow_factor":    aq_inputs["net_grow_factor"],
            "walkways_factor":    aq_inputs["walkways_factor"],
            "water_price":        aq_inputs["water_price"],
            "rent_monthly":       aq_inputs["rent_monthly"],
            "real_estate_capex":  aq_inputs["real_estate_capex"],
            "harvest_mode":       aq_inputs["harvest_mode"],
            "depreciation_years": aq_inputs["depreciation_years"],
            "tax_rate":           aq_inputs["tax_rate"],
            "ltv":                aq_inputs["ltv"],
            "interest_rate":      aq_inputs["interest_rate"],
            "loan_term_years":    aq_inputs["loan_term_years"],
            "discount_rate":      aq_inputs["discount_rate"],
            "ambient_temp_annual": aq_inputs.get("ambient_temp_annual"),
            "mean_annual_dli":    aq_inputs.get("mean_annual_dli"),
        }
        _aq_plant_r = _run_multicrop_generic(
            _aq_plant_base, _aq_crop_mix, calculate_greenhouse, _aq_plant_dict)
        # Run fish side normally via calculate_aquaponics, extract fish result
        _aq_single_r = calculate_aquaponics(aq_inputs)
        _fr_multi     = _aq_single_r["fish"]
        # Combine
        aq_r = dict(_aq_single_r)
        aq_r["plant"]             = _aq_plant_r
        aq_r["combined_revenue"]  = _aq_plant_r["annual_revenue"]  + _fr_multi["annual_fish_revenue"]
        aq_r["combined_ebitda"]   = _aq_plant_r["ebitda"]          + _fr_multi["fish_ebitda"]
        aq_r["combined_capex"]    = _aq_plant_r["total_capex"]      + _fr_multi["total_fish_capex"] + aq_r["integration_capex"]
        aq_r["combined_ebitda_margin"] = (aq_r["combined_ebitda"] / aq_r["combined_revenue"]
                                           if aq_r["combined_revenue"] > 0 else 0.0)
        aq_r["_is_multicrop"]     = True
        aq_r["_crop_results"]     = _aq_plant_r.get("_crop_results", [])
    else:
        aq_r = calculate_aquaponics(aq_inputs)

    _pr  = aq_r["plant"]
    _fr  = aq_r["fish"]

    # ── WARNINGS ──────────────────────────────────────────────────────────────
    # ── Climate profile display ─────────────────────────────────────────────────
    _aq_farm_active = st.session_state.get("active_farm")
    if _aq_farm_active and _aq_farm_active.get("ambient_temp_annual"):
        st.caption(
            f"🌤️ **Climate profile active** — "
            f"Ambient temperature: {_aq_farm_active['ambient_temp_annual']:.1f}°C "
            f"(used for fish heating calculation)"
            + (f" · Mean annual DLI: {_aq_farm_active['mean_annual_dli']:.1f} mol/m²/day"
               if _aq_farm_active.get("mean_annual_dli") else "")
        )

    if aq_r.get("salmon_warning"):
        st.warning(aq_r["salmon_warning"])
    if aq_r.get("ratio_warning"):
        st.warning(aq_r["ratio_warning"])
    if _aq_mode == "decoupled" and aq_r["nutrient_offset_saving"] > 0:
        st.success(
            f"🌿 Nutrient offset saving: **${aq_r['nutrient_offset_saving']:,.0f}/year** — "
            f"{aq_r['annual_n_output_g']/1000:.1f} kg N/yr from fish effluent "
            f"({COUPLING_PARAMS['decoupled_nutrient_offset_fraction']['base']*100:.0f}% offset applied)"
        )

    # ── Multi-crop plant breakdown ────────────────────────────────────────────
    if aq_r.get("_is_multicrop") and aq_r.get("_crop_results"):
        st.divider()
        st.subheader("Per-Crop Plant Breakdown")
        _aq_mc_rows = []
        for _mc in aq_r["_crop_results"]:
            _aq_mc_rows.append({
                "Crop":           _mc["crop"],
                "Area %":         f"{_mc['pct']:.0f}%",
                "Annual kg":      f"{_mc['total_annual_kg']:,.0f}",
                "Price ($/kg)":   f"${_mc['effective_price']:.2f}",
                "Revenue":        f"${_mc['annual_revenue']:,.0f}",
                "Variable Cost":  f"${_mc['annual_variable_cost']:,.0f}",
                "Labour":         f"${_mc['annual_labour_cost']:,.0f}",
                "EBITDA contrib": f"${_mc['ebitda']:,.0f}",
            })
        st.dataframe(pd.DataFrame(_aq_mc_rows), use_container_width=True, hide_index=True)
        st.caption("Fish side is always single-species. Plant energy and CAPEX shared across the mix.")
        st.divider()
    # ── PDF BUTTON ────────────────────────────────────────────────────────────
    def generate_aq_pdf_report(aq_inputs: dict, aq_r: dict) -> bytes:
        _fn  = st.session_state.get("active_farm", {}).get("name", "")
        _mc  = "aqc" if aq_inputs.get("mode","").lower() in ("coupled","aqc") else "aqd"
        return _build_feasibility_pdf(aq_r, aq_inputs, _mc, farm_name=_fn)

    aq_pdf_col1, aq_pdf_col2 = st.columns([5, 1])
    with aq_pdf_col2:
        if st.button("📄 Download PDF Report", key="aq_pdf_btn", use_container_width=True):
            with st.spinner("Generating PDF..."):
                _aq_pdf_bytes = generate_aq_pdf_report(aq_inputs, aq_r)
                _aq_filename = (
                    f"AQ_Report_{aq_inputs.get('plant_crop','').replace(' ','_').replace('/','').replace('(','').replace(')','')}"
                    f"_{aq_inputs.get('species','').replace(' ','_')}"
                    f"_{aq_inputs.get('country','')}_{date.today().strftime('%Y%m%d')}.pdf"
                )
                st.download_button(label="⬇️ Save PDF", data=_aq_pdf_bytes,
                                   file_name=_aq_filename, mime="application/pdf",
                                   use_container_width=True, key="aq_pdf_dl")
    st.divider()

    # ── COMBINED KEY METRICS ──────────────────────────────────────────────────
    st.subheader("Combined System Metrics")
    # Break-even yield for plant side
    _aq_loss_r   = aq_inputs["loss_rate"] / 100
    _aq_be_denom = (_pr["effective_price"] * (1 - _aq_loss_r) *
                    _pr["cycles_per_year"] * _pr["effective_grow_area"])
    _aq_be_yield = _pr["total_annual_costs"] / _aq_be_denom if _aq_be_denom > 0 else None
    _aq_plant_dict_early = POLYTUNNEL_CROPS if aq_inputs.get("plant_crop_source","greenhouse")=="polytunnel" else GREENHOUSE_CROPS
    _aq_proj_yield = _aq_plant_dict_early.get(aq_plant_crop, {}).get("yield", 0) if not _aq_mix_valid else 0
    _aq_yield_gap_str = (f"{(_aq_proj_yield - _aq_be_yield) / _aq_be_yield * 100:+.1f}%"
                         if _aq_be_yield and _aq_proj_yield else "N/A")
    # DSCR combined
    _aq_combined_ds = _pr.get("annual_debt_service", 0) + _fr.get("annual_debt_service", 0)
    _aq_combined_dscr = aq_r["combined_ebitda"] / _aq_combined_ds if _aq_combined_ds > 0 else None
    am1, am2, am3, am4, am5, am6, am7 = st.columns(7)
    am1.metric("Combined Revenue",  f"${aq_r['combined_revenue']:,.0f}")
    am2.metric("Combined EBITDA",   f"${aq_r['combined_ebitda']:,.0f}")
    am3.metric("EBITDA Margin",     f"{aq_r['combined_ebitda_margin']*100:.1f}%")
    am4.metric("Combined CAPEX",    f"${aq_r['combined_capex']:,.0f}")
    am5.metric("Plant Revenue",     f"${_pr['annual_revenue']:,.0f}")
    am6.metric("Fish Revenue",      f"${_fr['annual_fish_revenue']:,.0f}")
    am7.metric("Plant Break-even",
               f"{_aq_be_yield:.2f} kg/m²/cycle" if _aq_be_yield else "N/A",
               delta=_aq_yield_gap_str if _aq_be_yield and not _aq_mix_valid else None,
               delta_color="normal",
               help="Minimum plant yield to cover all plant costs.")
    if _aq_combined_dscr is not None and _aq_combined_dscr < 1.0:
        st.warning(
            f"⚠️ **Combined debt service coverage is low (DSCR = {_aq_combined_dscr:.2f}x).** "
            f"Total annual debt repayment exceeds combined EBITDA. "
            f"Consider reducing LTV or extending loan terms."
        )

    st.divider()

    # ── SIDE-BY-SIDE P&L ──────────────────────────────────────────────────────
    st.subheader("Plant vs Fish P&L")
    _aq_pc, _aq_fc = st.columns(2)

    with _aq_pc:
        st.markdown(f"**🌿 Plant — {aq_plant_crop}**")
        if _aq_mode == "decoupled":
            st.caption(f"Nutrient saving included: ${aq_r['nutrient_offset_saving']:,.0f}/yr")
        else:
            st.caption(f"Coupled efficiency: {aq_coupled_efficiency:.0%} of greenhouse yield")
        st.dataframe(pd.DataFrame({
            "Item": ["Revenue","Energy","Variable","Water","Labour","Maintenance","Rent","EBITDA","EBITDA Margin"],
            "$/year": [f"${_pr['annual_revenue']:,.0f}", f"${_pr['annual_energy_cost']:,.0f}",
                       f"${_pr['annual_variable_cost']:,.0f}", f"${_pr['annual_water_cost']:,.0f}",
                       f"${_pr['annual_labour_cost']:,.0f}", f"${_pr['annual_maintenance']:,.0f}",
                       f"${_pr['annual_rent']:,.0f}", f"${_pr['ebitda']:,.0f}",
                       f"{_pr['ebitda_margin']*100:.1f}%"],
        }), use_container_width=True, hide_index=True)

    with _aq_fc:
        st.markdown(f"**🐟 Fish — {aq_species}**")
        st.caption(f"{_fr['annual_kg_fish']:,.0f} kg/yr · {_fr['cycles_per_year']} cycle(s) · ΔT={_fr['delta_t']:.0f}°C")
        st.dataframe(pd.DataFrame({
            "Item": ["Revenue","Feed","Fingerlings","Energy","Water","Labour","Maintenance","EBITDA","EBITDA Margin"],
            "$/year": [f"${_fr['annual_fish_revenue']:,.0f}", f"${_fr['annual_feed_cost']:,.0f}",
                       f"${_fr['annual_fingerling_cost']:,.0f}", f"${_fr['annual_fish_energy_cost']:,.0f}",
                       f"${_fr['annual_water_cost']:,.0f}", f"${_fr['annual_fish_labour_cost']:,.0f}",
                       f"${_fr['annual_fish_maintenance']:,.0f}", f"${_fr['fish_ebitda']:,.0f}",
                       f"{_fr['fish_ebitda_margin']*100:.1f}%"],
        }), use_container_width=True, hide_index=True)

    st.divider()

    # ── COMBINED EBITDA BRIDGE ────────────────────────────────────────────────
    st.subheader("Combined EBITDA Bridge")
    _aq_bl = ["Plant Revenue","Fish Revenue","Plant Costs","Fish Costs","Nutrient Saving","Combined EBITDA"]
    _aq_bv = [_pr["annual_revenue"], _fr["annual_fish_revenue"],
               -_pr["total_annual_costs"], -_fr["total_fish_costs"],
               aq_r["nutrient_offset_saving"], aq_r["combined_ebitda"]]
    _aq_bc = ["rgba(0,229,160,0.85)","rgba(0,229,160,0.85)","rgba(255,77,77,0.6)","rgba(255,77,77,0.6)",
               "rgba(79,195,247,0.85)",
               "rgba(0,229,160,0.85)" if aq_r["combined_ebitda"] >= 0 else "rgba(255,77,77,0.85)"]
    _aq_fig_b = go.Figure(go.Bar(x=_aq_bl, y=_aq_bv, marker_color=_aq_bc,
        text=[f"${abs(v):,.0f}" for v in _aq_bv], textposition="outside"))
    _aq_fig_b.update_layout(plot_bgcolor="#ffffff", paper_bgcolor="#ffffff",
        font_color="#161a16", showlegend=False, height=380, margin=dict(t=30,b=20),
        yaxis=dict(showgrid=False), xaxis=dict(showgrid=False))
    st.plotly_chart(_aq_fig_b, use_container_width=True)

    st.divider()

    # ── CAPEX ─────────────────────────────────────────────────────────────────
    st.subheader("CAPEX Breakdown")
    _aq_cc1, _aq_cc2 = st.columns(2)
    with _aq_cc1:
        st.markdown(f"**🌿 Plant CAPEX — ${_pr['total_capex']:,.0f}**")
        _pcf = go.Figure(go.Pie(
            labels=["Structure","Climate","Irrigation","Lighting","Automation","Real Estate"],
            values=[_pr["structure_capex"],_pr["climate_capex"],_pr["irrigation_capex"],
                    _pr["lighting_capex"],_pr["automation_capex"],_pr["real_estate_capex"]],
            hole=0.45, marker_colors=["#00e5a0","#26c6da","#66bb6a","#ffa726","#ab47bc","#8d6e63"]))
        _pcf.update_layout(plot_bgcolor="#ffffff",paper_bgcolor="#ffffff",
                           font_color="#161a16",height=300,margin=dict(t=10,b=10))
        st.plotly_chart(_pcf, use_container_width=True)
    with _aq_cc2:
        st.markdown(f"**🐟 Fish CAPEX — ${_fr['total_fish_capex']:,.0f} + Integration ${aq_r['integration_capex']:,.0f}**")
        _fcf = go.Figure(go.Pie(
            labels=["Tanks","Filtration","Aeration","Monitoring","Plumbing"],
            values=[_fr["tank_capex"],_fr["filtration_capex"],_fr["aeration_capex"],
                    _fr["monitoring_capex"],_fr["plumbing_capex"]],
            hole=0.45, marker_colors=["#4fc3f7","#29b6f6","#0288d1","#01579b","#80d8ff"]))
        _fcf.update_layout(plot_bgcolor="#ffffff",paper_bgcolor="#ffffff",
                           font_color="#161a16",height=300,margin=dict(t=10,b=10))
        st.plotly_chart(_fcf, use_container_width=True)

    st.divider()

    # ── Annual cost breakdown (plant side) ───────────────────────────────────
    st.subheader("Plant Annual Cost Breakdown")
    _aq_cost_fig = go.Figure(go.Pie(
        labels=["Energy", "Variable", "Water", "Labour", "Maintenance", "Rent"],
        values=[_pr["annual_energy_cost"], _pr["annual_variable_cost"],
                _pr["annual_water_cost"], _pr["annual_labour_cost"],
                _pr["annual_maintenance"], _pr["annual_rent"]],
        hole=0.45,
        marker_colors=["#ff4d4d", "#ffc13d", "#00e5a0", "#4fc3f7", "#ba68c8", "#ef9a9a"]))
    _aq_cost_fig.update_layout(
        plot_bgcolor="#ffffff", paper_bgcolor="#ffffff",
        font_color="#161a16", height=320, margin=dict(t=10, b=10))
    st.plotly_chart(_aq_cost_fig, use_container_width=True)

    st.divider()

    # ── DCF ───────────────────────────────────────────────────────────────────
    st.subheader("Cumulative NPV — 10-year DCF")
    _dcf_col1, _dcf_col2 = st.columns(2)

    with _dcf_col1:
        st.markdown("**🌿 Plant Side**")
        _pdcf = go.Figure()
        _pdcf.add_trace(go.Scatter(
            x=[d["year"] for d in _pr["dcf_cashflows"]],
            y=[d["cumulative_npv"] for d in _pr["dcf_cashflows"]],
            mode="lines+markers", line=dict(color="#00e5a0", width=2),
            fill="tozeroy", fillcolor="rgba(0,229,160,0.1)"))
        _pdcf.add_hline(y=0, line_dash="dash", line_color="rgba(255,255,255,0.3)")
        _pdcf.update_layout(plot_bgcolor="#ffffff", paper_bgcolor="#ffffff",
            font_color="#161a16", height=280,
            xaxis=dict(title="Year", showgrid=False),
            yaxis=dict(title="Cumulative NPV ($)", showgrid=False),
            margin=dict(t=10, b=10))
        st.plotly_chart(_pdcf, use_container_width=True)

    with _dcf_col2:
        st.markdown("**🐟 Fish Side**")
        _fdcf = go.Figure()
        _fdcf.add_trace(go.Scatter(
            x=[d["year"] for d in _fr["dcf_cashflows"]],
            y=[d["cumulative_npv"] for d in _fr["dcf_cashflows"]],
            mode="lines+markers", line=dict(color="#4fc3f7", width=2),
            fill="tozeroy", fillcolor="rgba(79,195,247,0.1)"))
        _fdcf.add_hline(y=0, line_dash="dash", line_color="rgba(255,255,255,0.3)")
        _fdcf.update_layout(plot_bgcolor="#ffffff", paper_bgcolor="#ffffff",
            font_color="#161a16", height=280,
            xaxis=dict(title="Year", showgrid=False),
            yaxis=dict(title="Cumulative NPV ($)", showgrid=False),
            margin=dict(t=10, b=10))
        st.plotly_chart(_fdcf, use_container_width=True)

    st.divider()

    # ── FULL RESULTS ──────────────────────────────────────────────────────────
    st.subheader("Full Results")
    _frt1, _frt2 = st.tabs(["🌿 Plant Detail", "🐟 Fish Detail"])
    with _frt1:
        st.dataframe(pd.DataFrame({
            "Metric": ["Effective Grow Area (m²)","Gross Area (m²)","Structure Type",
                       "Cycles/Year","Harvest Mode","Annual kg","Price ($/kg)",
                       "Revenue","Energy","Variable","Water","Labour","Maintenance","Rent",
                       "Total Costs","EBITDA","EBITDA Margin","Plant CAPEX","Annual kWh"],
            "Value": [f"{_pr['effective_grow_area']:,.0f}", f"{_pr['gross_area']:,.0f}",
                      _pr["structure_type"], _pr["cycles_per_year"], _pr["harvest_mode"],
                      f"{_pr['total_annual_kg']:,.0f}", f"${_pr['effective_price']:.2f}",
                      f"${_pr['annual_revenue']:,.0f}", f"${_pr['annual_energy_cost']:,.0f}",
                      f"${_pr['annual_variable_cost']:,.0f}", f"${_pr['annual_water_cost']:,.0f}",
                      f"${_pr['annual_labour_cost']:,.0f}", f"${_pr['annual_maintenance']:,.0f}",
                      f"${_pr['annual_rent']:,.0f}", f"${_pr['total_annual_costs']:,.0f}",
                      f"${_pr['ebitda']:,.0f}", f"{_pr['ebitda_margin']*100:.1f}%",
                      f"${_pr['total_capex']:,.0f}", f"{_pr['annual_kwh']:,.0f}"],
        }), use_container_width=True, hide_index=True)
    with _frt2:
        st.dataframe(pd.DataFrame({
            "Metric": ["Species","Tank Volume (m³)","System Scale","Harvest Biomass (kg)",
                       "Cycles/Year","Annual kg Fish","Price ($/kg)",
                       "Revenue","Feed","Fingerlings","Energy","Water","Labour","Maintenance",
                       "Total Costs","EBITDA","EBITDA Margin","Fish CAPEX",
                       "Annual kWh","Heating kWh","Ambient Temp (°C)","Target Temp (°C)",
                       "Annual N Output (kg)"],
            "Value": [_fr["species"], f"{_fr['tank_volume_m3']:.0f}", _fr["system_scale"],
                      f"{_fr['harvest_biomass_kg']:,.0f}", _fr["cycles_per_year"],
                      f"{_fr['annual_kg_fish']:,.0f}", f"${_fr['effective_fish_price']:.2f}",
                      f"${_fr['annual_fish_revenue']:,.0f}", f"${_fr['annual_feed_cost']:,.0f}",
                      f"${_fr['annual_fingerling_cost']:,.0f}", f"${_fr['annual_fish_energy_cost']:,.0f}",
                      f"${_fr['annual_water_cost']:,.0f}", f"${_fr['annual_fish_labour_cost']:,.0f}",
                      f"${_fr['annual_fish_maintenance']:,.0f}", f"${_fr['total_fish_costs']:,.0f}",
                      f"${_fr['fish_ebitda']:,.0f}", f"{_fr['fish_ebitda_margin']*100:.1f}%",
                      f"${_fr['total_fish_capex']:,.0f}", f"{_fr['annual_fish_kwh']:,.0f}",
                      f"{_fr['heating_kwh']:,.0f}", f"{_fr['ambient_temp_c']:.1f}",
                      f"{_fr['target_temp_c']:.1f}", f"{_fr['annual_n_output_g']/1000:.1f}"],
        }), use_container_width=True, hide_index=True)

    st.divider()

    # ═══════════════════════════════════════════════════════════════════════════
    # VIABILITY COMPARISON (plant side)
    # ═══════════════════════════════════════════════════════════════════════════
    st.subheader("🌍 Plant Side Viability Comparison")
    st.caption("Plant side only — uses current plant inputs. Only the dimension being compared changes.")

    _aq_comp_tab1, _aq_comp_tab2 = st.tabs(["Compare Countries", "Compare Crops"])

    with _aq_comp_tab1:
        _aq_country_metric = st.selectbox("Rank by",
            ["EBITDA", "Energy % of Revenue", "Payback (years)", "EBITDA Margin (%)"],
            key="aq_country_metric")
        _aq_country_results = []
        for _cn in COUNTRIES.keys():
            _ci = dict(aq_inputs)
            _ci["country"] = _cn
            _ci["plant_crop"] = aq_plant_crop
            try:
                _cr = calculate_greenhouse({
                    "country": _cn, "crop": aq_inputs["plant_crop"],
                    "crop_source": aq_inputs.get("plant_crop_source","greenhouse"),
                    "footprint": aq_inputs["plant_footprint"],
                    "automation": aq_inputs["automation"],
                    "price_scenario": aq_inputs["price_scenario"],
                    "plant_price_override": 0.0, "price_override": 0.0,
                    "packaging_cost": aq_inputs["packaging_cost"],
                    "loss_rate": aq_inputs["loss_rate"],
                    "net_grow_factor": aq_inputs["net_grow_factor"],
                    "walkways_factor": aq_inputs["walkways_factor"],
                    "water_price": aq_inputs["water_price"],
                    "rent_monthly": aq_inputs["rent_monthly"],
                    "real_estate_capex": aq_inputs["real_estate_capex"],
                    "harvest_mode": aq_inputs["harvest_mode"],
                    "depreciation_years": aq_inputs["depreciation_years"],
                    "tax_rate": aq_inputs["tax_rate"], "ltv": aq_inputs["ltv"],
                    "interest_rate": aq_inputs["interest_rate"],
                    "loan_term_years": aq_inputs["loan_term_years"],
                    "discount_rate": aq_inputs["discount_rate"],
                })
                _ep = _cr["annual_energy_cost"]/_cr["annual_revenue"]*100 if _cr["annual_revenue"]>0 else 999
                _aq_country_results.append({
                    "Country": _cn, "EBITDA": _cr["ebitda"],
                    "Energy % of Revenue": _ep,
                    "Payback (years)": _cr["payback_years"] if _cr["payback_years"] else 999,
                    "EBITDA Margin (%)": _cr["ebitda_margin"]*100,
                })
            except Exception:
                continue
        if _aq_country_results:
            _aq_df_c = pd.DataFrame(_aq_country_results)
            _aq_asc  = _aq_country_metric in ("Energy % of Revenue","Payback (years)")
            _aq_df_c = _aq_df_c.sort_values(_aq_country_metric, ascending=_aq_asc).reset_index(drop=True)
            _aq_fig_c = go.Figure(go.Bar(
                x=_aq_df_c[_aq_country_metric], y=_aq_df_c["Country"], orientation="h",
                marker_color=["rgba(0,229,160,0.75)" if (
                    (_aq_country_metric=="EBITDA" and v>=0) or
                    (_aq_country_metric=="Energy % of Revenue" and v<40) or
                    (_aq_country_metric=="Payback (years)" and 0<v<10) or
                    (_aq_country_metric=="EBITDA Margin (%)" and v>=0)
                ) else "rgba(255,77,77,0.75)" for v in _aq_df_c[_aq_country_metric]],
                text=_aq_df_c[_aq_country_metric].apply(
                    lambda v: f"${v:,.0f}" if _aq_country_metric=="EBITDA"
                    else (f"{v:.1f}%" if "%" in _aq_country_metric
                    else (f"{v:.1f} yrs" if v<900 else "N/A"))),
                textposition="outside"))
            if _aq_country_metric == "Energy % of Revenue":
                _aq_fig_c.add_vline(x=40, line_dash="dash", line_color="rgba(255,193,61,0.6)",
                                    annotation_text="40% threshold", annotation_font_color="#ffc13d")
            _aq_fig_c.update_layout(
                plot_bgcolor="#ffffff", paper_bgcolor="#ffffff",
                font_color="#161a16", height=max(500, len(_aq_df_c)*22),
                margin=dict(l=10,r=100,t=20,b=20),
                xaxis=dict(showgrid=False,zeroline=False),
                yaxis=dict(showgrid=False,autorange="reversed"))
            st.plotly_chart(_aq_fig_c, use_container_width=True)

    with _aq_comp_tab2:
        _aq_plant_dict_comp = POLYTUNNEL_CROPS if aq_inputs.get("plant_crop_source","greenhouse")=="polytunnel" else GREENHOUSE_CROPS
        _aq_crop_metric = st.selectbox("Rank by",
            ["EBITDA","EBITDA Margin (%)","Energy % of Revenue","Payback (years)"],
            key="aq_crop_metric")
        _aq_crop_results = []
        for _crn in _aq_plant_dict_comp.keys():
            try:
                _crr = calculate_greenhouse({
                    "country": aq_inputs["country"], "crop": _crn,
                    "crop_source": aq_inputs.get("plant_crop_source","greenhouse"),
                    "footprint": aq_inputs["plant_footprint"],
                    "automation": aq_inputs["automation"],
                    "price_scenario": aq_inputs["price_scenario"], "price_override": 0.0,
                    "packaging_cost": aq_inputs["packaging_cost"],
                    "loss_rate": aq_inputs["loss_rate"],
                    "net_grow_factor": aq_inputs["net_grow_factor"],
                    "walkways_factor": aq_inputs["walkways_factor"],
                    "water_price": aq_inputs["water_price"],
                    "rent_monthly": 0.0, "real_estate_capex": 0.0,
                    "harvest_mode": "Single",
                    "depreciation_years": aq_inputs["depreciation_years"],
                    "tax_rate": aq_inputs["tax_rate"], "ltv": aq_inputs["ltv"],
                    "interest_rate": aq_inputs["interest_rate"],
                    "loan_term_years": aq_inputs["loan_term_years"],
                    "discount_rate": aq_inputs["discount_rate"],
                })
                _ep2 = _crr["annual_energy_cost"]/_crr["annual_revenue"]*100 if _crr["annual_revenue"]>0 else 999
                _aq_crop_results.append({
                    "Crop": _crn, "EBITDA": _crr["ebitda"],
                    "EBITDA Margin (%)": _crr["ebitda_margin"]*100,
                    "Energy % of Revenue": _ep2,
                    "Payback (years)": _crr["payback_years"] if _crr["payback_years"] else 999,
                })
            except Exception:
                continue
        if _aq_crop_results:
            _aq_df_cr = pd.DataFrame(_aq_crop_results)
            _aq_asc2  = _aq_crop_metric in ("Energy % of Revenue","Payback (years)")
            _aq_df_cr = _aq_df_cr.sort_values(_aq_crop_metric, ascending=_aq_asc2).reset_index(drop=True)
            _aq_fig_cr = go.Figure(go.Bar(
                x=_aq_df_cr[_aq_crop_metric], y=_aq_df_cr["Crop"], orientation="h",
                marker_color=["rgba(0,229,160,0.75)" if (
                    (_aq_crop_metric=="EBITDA" and v>=0) or
                    (_aq_crop_metric=="Energy % of Revenue" and v<40) or
                    (_aq_crop_metric=="Payback (years)" and 0<v<10) or
                    (_aq_crop_metric=="EBITDA Margin (%)" and v>=0)
                ) else "rgba(255,77,77,0.75)" for v in _aq_df_cr[_aq_crop_metric]],
                text=_aq_df_cr[_aq_crop_metric].apply(
                    lambda v: f"${v:,.0f}" if _aq_crop_metric=="EBITDA"
                    else (f"{v:.1f}%" if "%" in _aq_crop_metric
                    else (f"{v:.1f} yrs" if v<900 else "N/A"))),
                textposition="outside"))
            _aq_fig_cr.update_layout(
                plot_bgcolor="#ffffff", paper_bgcolor="#ffffff",
                font_color="#161a16", height=max(400, len(_aq_df_cr)*22),
                margin=dict(l=10,r=100,t=20,b=20),
                xaxis=dict(showgrid=False,zeroline=False),
                yaxis=dict(showgrid=False,autorange="reversed"))
            st.plotly_chart(_aq_fig_cr, use_container_width=True)

    st.divider()

    # ═══════════════════════════════════════════════════════════════════════════
    # SENSITIVITY ANALYSIS (plant side)
    # ═══════════════════════════════════════════════════════════════════════════
    st.subheader("🔬 Plant Side Sensitivity Analysis")

    def _aq_run_mult(base_plant_inputs, kwh_m=1.0, lab_m=1.0, yld_m=1.0, prc_m=1.0):
        import core.greenhouse_data_tables as _ghdt
        import copy as _copy
        import core.data_tables as _cdt
        _cn = base_plant_inputs["country"]
        _orig_c = _cdt.COUNTRIES[_cn]
        _mod_c  = _copy.deepcopy(_orig_c)
        _mod_c["kwh"]    = _orig_c["kwh"]    * kwh_m
        _mod_c["labour"] = _orig_c["labour"] * lab_m
        _mod_i = _copy.deepcopy(base_plant_inputs)
        _src   = base_plant_inputs.get("crop_source","greenhouse")
        _cd    = _ghdt.POLYTUNNEL_CROPS if _src=="polytunnel" else _ghdt.GREENHOUSE_CROPS
        if prc_m != 1.0 or yld_m != 1.0:
            _orig_crop = _cd[base_plant_inputs["crop"]]
            _mod_crop  = _copy.deepcopy(_orig_crop)
            _mod_crop["yield"]    = _orig_crop["yield"]    * yld_m
            _mod_crop["yield_h2"] = _orig_crop["yield_h2"] * yld_m
            _mod_crop["yield_h3"] = _orig_crop["yield_h3"] * yld_m
            if base_plant_inputs.get("price_override",0)>0:
                _mod_i["price_override"] = base_plant_inputs["price_override"] * prc_m
            else:
                _base_price = _orig_crop[f"price_{base_plant_inputs['price_scenario']}"]
                _mod_i["price_override"] = _base_price * prc_m
            _cd[base_plant_inputs["crop"]] = _mod_crop
        _cdt.COUNTRIES[_cn] = _mod_c
        try:
            _res = calculate_greenhouse(_mod_i)
        finally:
            _cdt.COUNTRIES[_cn] = _orig_c
            if prc_m != 1.0 or yld_m != 1.0:
                _cd[base_plant_inputs["crop"]] = _orig_crop
        return _res

    # Build plant inputs dict for sensitivity
    _aq_plant_sens_inputs = {
        "country": aq_inputs["country"], "crop": aq_inputs["plant_crop"],
        "crop_source": aq_inputs.get("plant_crop_source","greenhouse"),
        "footprint": aq_inputs["plant_footprint"],
        "automation": aq_inputs["automation"],
        "price_scenario": aq_inputs["price_scenario"], "price_override": 0.0,
        "packaging_cost": aq_inputs["packaging_cost"],
        "loss_rate": aq_inputs["loss_rate"],
        "net_grow_factor": aq_inputs["net_grow_factor"],
        "walkways_factor": aq_inputs["walkways_factor"],
        "water_price": aq_inputs["water_price"],
        "rent_monthly": aq_inputs["rent_monthly"],
        "real_estate_capex": aq_inputs["real_estate_capex"],
        "harvest_mode": aq_inputs["harvest_mode"],
        "depreciation_years": aq_inputs["depreciation_years"],
        "tax_rate": aq_inputs["tax_rate"], "ltv": aq_inputs["ltv"],
        "interest_rate": aq_inputs["interest_rate"],
        "loan_term_years": aq_inputs["loan_term_years"],
        "discount_rate": aq_inputs["discount_rate"],
    }

    st.markdown("#### Tornado Chart — Plant EBITDA Sensitivity")
    st.caption("Each bar shows how plant EBITDA changes when one variable is stressed. Fish side held constant.")

    _aq_base_ebitda = _pr["ebitda"]
    _aq_tvars = [
        {"label":"Energy Price",  "pess":_aq_run_mult(_aq_plant_sens_inputs,kwh_m=1.50)["ebitda"], "opt":_aq_run_mult(_aq_plant_sens_inputs,kwh_m=0.70)["ebitda"],
         "pess_label":"Energy price +50%","opt_label":"Energy price −30%"},
        {"label":"Selling Price", "pess":_aq_run_mult(_aq_plant_sens_inputs,prc_m=0.80)["ebitda"], "opt":_aq_run_mult(_aq_plant_sens_inputs,prc_m=1.20)["ebitda"],
         "pess_label":"Selling price −20%","opt_label":"Selling price +20%"},
        {"label":"Yield",         "pess":_aq_run_mult(_aq_plant_sens_inputs,yld_m=0.80)["ebitda"], "opt":_aq_run_mult(_aq_plant_sens_inputs,yld_m=1.20)["ebitda"],
         "pess_label":"Yield −20%","opt_label":"Yield +20%"},
        {"label":"Labour Cost",   "pess":_aq_run_mult(_aq_plant_sens_inputs,lab_m=1.30)["ebitda"], "opt":_aq_run_mult(_aq_plant_sens_inputs,lab_m=0.80)["ebitda"],
         "pess_label":"Labour cost +30%","opt_label":"Labour cost −20%"},
    ]
    for _tv in _aq_tvars:
        _tv["delta_pess"] = _tv["pess"] - _aq_base_ebitda
        _tv["delta_opt"]  = _tv["opt"]  - _aq_base_ebitda
        _tv["swing"]      = abs(_tv["delta_opt"] - _tv["delta_pess"])
    _aq_tvars.sort(key=lambda x: x["swing"], reverse=True)

    _aq_fig_torn = go.Figure()
    for _tv in _aq_tvars:
        _aq_fig_torn.add_trace(go.Bar(
            name="Pessimistic", y=[_tv["label"]], x=[_tv["delta_pess"]], orientation="h",
            marker_color="rgba(255,77,77,0.75)", showlegend=(_tv==_aq_tvars[0]),
            text=f"${_tv['delta_pess']:,.0f}", textposition="outside"))
        _aq_fig_torn.add_trace(go.Bar(
            name="Optimistic", y=[_tv["label"]], x=[_tv["delta_opt"]], orientation="h",
            marker_color="rgba(0,229,160,0.75)", showlegend=(_tv==_aq_tvars[0]),
            text=f"${_tv['delta_opt']:,.0f}", textposition="outside"))
    _aq_fig_torn.add_vline(x=0, line_dash="dash", line_color="rgba(255,255,255,0.4)")
    _aq_fig_torn.update_layout(
        barmode="overlay", plot_bgcolor="#ffffff", paper_bgcolor="#ffffff",
        font_color="#161a16", height=320, margin=dict(l=10,r=80,t=20,b=20),
        xaxis=dict(title="Plant EBITDA delta ($)",showgrid=False,zeroline=False),
        yaxis=dict(showgrid=False),
        legend=dict(orientation="h",yanchor="bottom",y=1.02,xanchor="right",x=1))
    st.plotly_chart(_aq_fig_torn, use_container_width=True)

    st.divider()
    st.markdown("#### Scenario Comparison")
    st.caption("Stress the plant side. Fish side is always recalculated at base parameters.")

    if "aq_scenarios" not in st.session_state:
        st.session_state["aq_scenarios"] = []

    with st.expander("➕ Define a new scenario", expanded=len(st.session_state["aq_scenarios"])==0):
        _aq_sc_name   = st.text_input("Scenario name", value="Scenario 1", key="aq_sc_name")
        _aq_sc1, _aq_sc2 = st.columns(2)
        with _aq_sc1:
            _aq_sc_energy = st.slider("Energy price multiplier",  0.3, 3.0, 1.0, 0.05, key="aq_sc_energy")
            _aq_sc_yield  = st.slider("Yield multiplier",         0.3, 2.0, 1.0, 0.05, key="aq_sc_yield")
        with _aq_sc2:
            _aq_sc_price  = st.slider("Selling price multiplier", 0.3, 2.0, 1.0, 0.05, key="aq_sc_price")
            _aq_sc_labour = st.slider("Labour cost multiplier",   0.3, 3.0, 1.0, 0.05, key="aq_sc_labour")
        if st.button("💾 Save Scenario", key="aq_save_sc", use_container_width=True):
            if len(st.session_state["aq_scenarios"]) >= 4:
                st.warning("Maximum 4 scenarios reached.")
            else:
                _aq_sc_plant_r = _aq_run_mult(_aq_plant_sens_inputs,
                    kwh_m=_aq_sc_energy, lab_m=_aq_sc_labour,
                    yld_m=_aq_sc_yield, prc_m=_aq_sc_price)
                st.session_state["aq_scenarios"].append({
                    "name": _aq_sc_name, "energy_mult": _aq_sc_energy,
                    "yield_mult": _aq_sc_yield, "price_mult": _aq_sc_price,
                    "labour_mult": _aq_sc_labour, "plant_result": _aq_sc_plant_r})
                st.success(f"Scenario '{_aq_sc_name}' saved.")
        if st.session_state["aq_scenarios"]:
            if st.button("🗑️ Clear all scenarios", key="aq_clear_sc", use_container_width=True):
                st.session_state["aq_scenarios"] = []
                st.rerun()

    if st.session_state["aq_scenarios"]:
        for _idx2, _sc2 in enumerate(st.session_state["aq_scenarios"]):
            _dc1, _dc2 = st.columns([8,1])
            with _dc1:
                st.caption(f"**{_sc2['name']}** — energy ×{_sc2['energy_mult']} / yield ×{_sc2['yield_mult']} / price ×{_sc2['price_mult']} / labour ×{_sc2['labour_mult']}")
            with _dc2:
                if st.button("🗑️", key=f"aq_del_sc_{_idx2}"):
                    st.session_state["aq_scenarios"].pop(_idx2)
                    st.rerun()
        _aq_sc_names   = ["Base Case"] + [s["name"] for s in st.session_state["aq_scenarios"]]
        _aq_sc_presults = [_pr] + [s["plant_result"] for s in st.session_state["aq_scenarios"]]
        _aq_fig_comp = go.Figure()
        for _i3, (_mn3, _mv3) in enumerate({
            "Plant EBITDA":  [res["ebitda"]            for res in _aq_sc_presults],
            "Revenue":       [res["annual_revenue"]     for res in _aq_sc_presults],
            "Energy Cost":   [res["annual_energy_cost"] for res in _aq_sc_presults],
            "Labour Cost":   [res["annual_labour_cost"] for res in _aq_sc_presults],
        }.items()):
            _aq_fig_comp.add_trace(go.Bar(name=_mn3, x=_aq_sc_names, y=_mv3,
                marker_color=["#00e5a0","#ffc13d","#4fc3f7","#ba68c8"][_i3],
                text=[f"${v:,.0f}" for v in _mv3], textposition="outside"))
        _aq_fig_comp.update_layout(
            barmode="group", plot_bgcolor="#ffffff", paper_bgcolor="#ffffff",
            font_color="#161a16", height=420, margin=dict(t=30,b=20),
            xaxis=dict(showgrid=False), yaxis=dict(showgrid=False,title="$"),
            legend=dict(orientation="h",yanchor="bottom",y=1.02,xanchor="right",x=1))
        st.plotly_chart(_aq_fig_comp, use_container_width=True)

        _aq_sc_rows = []
        for _sn3, _sr3 in zip(_aq_sc_names, _aq_sc_presults):
            _ep4 = f"{_sr3['annual_energy_cost']/_sr3['annual_revenue']*100:.1f}%" if _sr3["annual_revenue"]>0 else "N/A"
            _aq_sc_rows.append({
                "Scenario": _sn3,
                "Revenue":  f"${_sr3['annual_revenue']:,.0f}",
                "Energy":   f"${_sr3['annual_energy_cost']:,.0f}",
                "Labour":   f"${_sr3['annual_labour_cost']:,.0f}",
                "Plant EBITDA": f"${_sr3['ebitda']:,.0f}",
                "Margin":   f"{_sr3['ebitda_margin']*100:.1f}%",
                "Energy % Rev": _ep4,
            })
        _aq_sc_df = pd.DataFrame(_aq_sc_rows)
        def _aq_highlight_ep(row):
            v_str = row["Energy % Rev"]
            if v_str=="N/A": return [""]*len(row)
            try: v=float(v_str.replace("%",""))
            except: return [""]*len(row)
            if v>60:   return [""]*( len(row)-1)+["background-color:rgba(255,77,77,0.25);color:#ff4d4d"]
            elif v>40: return [""]*( len(row)-1)+["background-color:rgba(255,193,61,0.25);color:#ffc13d"]
            else:      return [""]*( len(row)-1)+["background-color:rgba(0,229,160,0.15);color:#00e5a0"]
        st.dataframe(_aq_sc_df.style.apply(_aq_highlight_ep,axis=1),
                     use_container_width=True, hide_index=True)
    else:
        st.info("No scenarios saved yet. Define and save your first scenario above.")

    st.divider()

    # ── SAVE AS FARM PROFILE ──────────────────────────────────────────────────
    aq_save_col1, aq_save_col2 = st.columns([5, 1])
    with aq_save_col2:
        if st.button("💾 Save as Farm Profile", key="aq_save_btn", use_container_width=True):
            st.session_state["aq_show_save_form"] = True

    if st.session_state["aq_show_save_form"]:
        with st.container(border=True):
            _aq_active   = st.session_state.get("active_farm")
            _save_lat = st.session_state.get("shared_lat")
            _save_lon = st.session_state.get("shared_lng")
            _climate_data = {}
            if _save_lat and _save_lon:
                with st.spinner("🌤️ Fetching climate profile for this location…"):
                    try:
                        from core.climate import fetch_climate_profile
                        _climate_data = fetch_climate_profile(_save_lat, _save_lon)
                    except Exception:
                        _climate_data = {}
            _aq_modality = f"aquaponics_{_aq_mode}"
            _aq_meta     = json.dumps({
                "species":                 aq_species,
                "tank_volume_m3":          aq_tank_volume,
                "system_scale":            aq_system_scale,
                "target_temp_c":           aq_target_temp,
                "fish_depreciation_years": aq_fish_dep,
                "plant_crop_source":       aq_plant_crop_source.lower(),
            })
            _aq_snap = json.dumps({
                "plant": {k: v for k, v in _pr.items()},
                "fish":  {k: v for k, v in _fr.items()},
                "combined_revenue":  aq_r["combined_revenue"],
                "combined_ebitda":   aq_r["combined_ebitda"],
                "combined_capex":    aq_r["combined_capex"],
            })
            _aq_payload = {
                "country":           aq_country,
                "crop":              (_aq_crop_mix[0]["crop"] if _aq_mix_valid and _aq_crop_mix else aq_plant_crop),
                "crop_source":       aq_plant_crop_source.lower(),
                "footprint":         aq_plant_footprint,
                "automation":        aq_automation,
                "price_scenario":    aq_price_scenario,
                "price_override":    0.0,
                "packaging_cost":    aq_packaging_cost,
                "loss_rate":         aq_loss_rate,
                "net_grow_factor":   aq_net_grow_factor,
                "walkways_factor":   aq_walkways_factor,
                "water_price":       aq_water_price,
                "rent_monthly":      aq_rent_monthly,
                "real_estate_capex": aq_real_estate_capex,
                "harvest_mode":      aq_harvest_mode,
                "depreciation_years": aq_dep_years,
                "tax_rate":          aq_tax_rate,
                "ltv":               aq_ltv,
                "interest_rate":     aq_interest,
                "loan_term_years":   aq_loan_term,
                "lat":               st.session_state.get("shared_lat"),
                "lon":               st.session_state.get("shared_lng"),
                "ambient_temp_annual": _climate_data.get("ambient_temp_annual"),
                "mean_annual_dli":     _climate_data.get("mean_annual_dli"),
                "agriculture_type":  _aq_modality,
                "modality":          _aq_modality,
                "discount_rate":     aq_discount,
                "metadata":          _aq_meta,
                "model_snapshot":    _aq_snap,
                "model_updated_at":  date.today().isoformat(),
                "crop_mix_json":     json.dumps(_aq_crop_mix) if _aq_mix_valid else None,
                "notes":             None,
            }
            if _aq_active:
                st.markdown(f"**Update** existing farm **{_aq_active['name']}**, or save as a new profile.")
                _au1, _au2, _au3 = st.columns([2, 2, 1])
                with _au1:
                    if st.button("✅ Update existing farm", use_container_width=True, key="aq_update_btn"):
                        try:
                            supabase.table("farms").update(_aq_payload).eq("id", _aq_active["id"]).execute()
                            st.session_state["active_farm"] = {**_aq_active, **_aq_payload}
                            st.success(f"✅ Farm **{_aq_active['name']}** updated.")
                            if _climate_data.get("mean_annual_dli"):
                                st.caption(f"🌤️ Climate profile saved — Mean DLI: {_climate_data['mean_annual_dli']:.1f} mol/m²/day · Ambient temp: {_climate_data['ambient_temp_annual']:.1f}°C")
                            st.session_state["aq_show_save_form"] = False
                            st.rerun()
                        except Exception as e:
                            st.error(f"Update failed: {e}")
                with _au2:
                    aq_farm_name = st.text_input("New farm name", key="aq_farm_name_input", placeholder="Enter name for new profile")
                    if st.button("➕ Save as new farm", use_container_width=True, key="aq_saveas_btn"):
                        if not aq_farm_name.strip():
                            st.error("Please enter a name for the new farm profile.")
                        else:
                            try:
                                supabase.table("farms").insert({**_aq_payload, "name": aq_farm_name.strip(), "owner_id": current_user()}).execute()
                                st.success(f"✅ New farm profile '{aq_farm_name.strip()}' saved.")
                                if _climate_data.get("mean_annual_dli"):
                                    st.caption(f"🌤️ Climate profile saved — Mean DLI: {_climate_data['mean_annual_dli']:.1f} mol/m²/day · Ambient temp: {_climate_data['ambient_temp_annual']:.1f}°C")
                                st.session_state["aq_show_save_form"] = False
                                st.rerun()
                            except Exception as e:
                                st.error(f"Could not save: {e}")
                with _au3:
                    if st.button("✖ Cancel", use_container_width=True, key="aq_cancel_save"):
                        st.session_state["aq_show_save_form"] = False
                        st.rerun()
            else:
                st.markdown("**Save current aquaponics configuration as a Farm Profile**")
                st.caption("Saves all parameters so you can track harvests in the Harvest Tracker.")
                aq_farm_name = st.text_input("Farm name", key="aq_farm_name_input")
                _an1, _an2 = st.columns([3, 1])
                with _an1:
                    if st.button("✅ Confirm Save", key="aq_confirm_save", use_container_width=True):
                        if not aq_farm_name.strip():
                            st.error("Please enter a farm name.")
                        else:
                            try:
                                supabase.table("farms").insert({**_aq_payload, "name": aq_farm_name.strip(), "owner_id": current_user()}).execute()
                                st.success(f"Farm profile '{aq_farm_name.strip()}' saved.")
                                if _climate_data.get("mean_annual_dli"):
                                    st.caption(f"🌤️ Climate profile saved — Mean DLI: {_climate_data['mean_annual_dli']:.1f} mol/m²/day · Ambient temp: {_climate_data['ambient_temp_annual']:.1f}°C")
                                st.session_state["aq_show_save_form"] = False
                                st.rerun()
                            except Exception as e:
                                st.error(f"Could not save: {e}")
                with _an2:
                    if st.button("✖ Cancel", key="aq_cancel_new", use_container_width=True):
                        st.session_state["aq_show_save_form"] = False
                        st.rerun()
