import streamlit as st
import plotly.graph_objects as go
import pandas as pd
import sys
import os
import json
from datetime import date, timedelta, datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from core.data_tables import COUNTRIES, CROPS, LIGHTS
from core._charts import style_fig
from core._tables import severity_cell
from core.greenhouse_data_tables import GREENHOUSE_CROPS, POLYTUNNEL_CROPS, FISH_SPECIES
from core._styles import inject_styles
from core.farm_context import render_farm_context_sidebar
from core.weather import (
    fetch_forecast, get_crop_alerts, compute_weekly_hvac_cost,
    fetch_current_conditions,
)
from supabase import create_client, Client

st.set_page_config(page_title="Harvest Tracker", page_icon="🌿", layout="wide")
inject_styles()
from core.auth import require_login # Keep page_icon emoji, but remove from title

# ── Sidebar Dropdown & Radio Readability Fix ──────────────────────────────
st.markdown("""
<style>
  /* Selectboxes and Multiselects inside sidebar expanders */
  [data-testid="stSidebar"] [data-testid="stExpander"] [data-baseweb="select"] > div {
    background-color: var(--surface) !important;
    border-color: var(--rule) !important;
  }
  [data-testid="stSidebar"] [data-testid="stExpander"] [data-baseweb="select"] * {
    color: var(--ink) !important;
    fill: var(--ink) !important;
  }
  /* Radio Button Visibility Fix */
  [data-testid="stRadio"] [data-baseweb="radio"] div:first-child {
    border-color: var(--ink-2) !important;
    background-color: var(--surface-2) !important;
  }
  [data-testid="stRadio"] [data-checked="true"] div:first-child {
    background-color: var(--surface) !important;
    border-color: var(--sage) !important;
  }
  [data-testid="stRadio"] [data-checked="true"] div:first-child div {
    background-color: var(--sage) !important;
  }
</style>
""", unsafe_allow_html=True)

require_login()
st.title("Harvest Tracker")

@st.cache_resource
def get_supabase() -> Client:
    return create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])

supabase = get_supabase()

# ── Expense categories ────────────────────────────────────────────────────────
EXPENSE_CATEGORIES = [
    ("⚡", "Energy"),
    ("🌱", "Seeds"),
    ("🪨", "Substrate"),
    ("💧", "Nutrients"),
    ("📦", "Packaging"),
    ("👷", "Labour"),
    ("🔧", "Maintenance"),
    ("🏠", "Rent"),
    ("📌", "Other"),
]

SALES_CHANNELS = ["Direct", "Wholesale", "Restaurant", "Market", "Online", "Other"]

# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    render_farm_context_sidebar()

# ── Tabs ──────────────────────────────────────────────────────────────────────
# ── Space Planner navigation bridge ──────────────────────────────────────────
# If arriving from Space Planner with ?rack=X&cycle_id=Y, store in session state
_qp = st.query_params
if "rack" in _qp:
    st.session_state["highlight_rack"]    = _qp["rack"]
    st.session_state["highlight_cycle"]   = _qp.get("cycle_id", "")
    # Clear query params so refresh doesn't re-trigger
    st.query_params.clear()

tab0, tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "🌱 Active Cycles",
    "📊 Farm Comparison",
    "🌿 Log Cycle",
    "🧾 Log Expense",
    "📊 Dashboard",
    "📈 Forecast & Financials",
])

# ─────────────────────────────────────────────────────────────────────────────
# TAB 0 — Active Cycles (NEW)
# ─────────────────────────────────────────────────────────────────────────────
with tab0:
    _ac_farm = st.session_state.get("active_farm")
    if not _ac_farm:
        st.info("No active farm selected. Load a farm from Home to see active cycles.")
        st.page_link("Home.py", label="🏠 Go to Home →")
    else:
        # ── Weather widget ────────────────────────────────────────────────────
        _ac_lat = _ac_farm.get("lat")
        _ac_lon = _ac_farm.get("lon")
        _ac_modality = (_ac_farm.get("modality") or
                        _ac_farm.get("agriculture_type") or "vertical_farm")
        _ac_primary_crop = _ac_farm.get("crop", "Lettuce (Butterhead)")
        _ac_country_data = COUNTRIES.get(_ac_farm.get("country", "Germany"), {})
        _ac_kwh_price = float(_ac_country_data.get("kwh", 0.25))
        _ac_footprint = float(_ac_farm.get("footprint") or
                              _ac_farm.get("plant_footprint") or 1000)
        _ac_target_temp = 22.0  # default indoor target

        if _ac_lat and _ac_lon:
            with st.spinner("Fetching weather forecast..."):
                _fc = fetch_forecast(_ac_lat, _ac_lon)
            if _fc and _fc.get("dates"):
                # ── 7-day forecast strip ──────────────────────────────────
                st.markdown("### 🌤 7-Day Forecast")
                _wc = st.columns(7)
                _weather_icons = {
                    (True,  True):  "⛈",
                    (True,  False): "🌧",
                    (False, True):  "⛅",
                    (False, False): "☀️",
                }
                for _wi, _wd in enumerate(_fc["dates"][:7]):
                    with _wc[_wi]:
                        _wt_max  = _fc["temp_max"][_wi]  if _wi < len(_fc["temp_max"])  else None
                        _wt_min  = _fc["temp_min"][_wi]  if _wi < len(_fc["temp_min"])  else None
                        _wp      = _fc["precipitation"][_wi] if _wi < len(_fc["precipitation"]) else 0
                        _wcl     = _fc["cloud_cover"][_wi]   if _wi < len(_fc["cloud_cover"])   else 0
                        _wicon   = _weather_icons.get((_wp > 2, _wcl > 60), "☀️")
                        _day_lbl = datetime.strptime(_wd, "%Y-%m-%d").strftime("%a %d")
                        st.markdown(
                            f'<div style="text-align:center;background:#ffffff;'
                            f'border:1px solid #d9d4c5;border-radius:3px;padding:8px 4px;'
                            f'font-size:12px;">'
                            f'<div style="font-weight:700;color:#161a16;">{_day_lbl}</div>'
                            f'<div style="font-size:20px;margin:4px 0;">{_wicon}</div>'
                            f'<div style="color:#b85c38;font-weight:600;">'
                            f'{_wt_max:.0f}°</div>'
                            f'<div style="color:#2c5a78;">'
                            f'{_wt_min:.0f}°</div>'
                            + (f'<div style="color:#4a524a;font-size:10px;">{_wp:.0f}mm</div>'
                               if _wp and _wp > 0.5 else '') +
                            f'</div>',
                            unsafe_allow_html=True,
                        )

                # ── HVAC cost projection ──────────────────────────────────
                _hvac = compute_weekly_hvac_cost(
                    _fc, _ac_target_temp, _ac_footprint, _ac_kwh_price
                )
                if _hvac["total_kwh"] > 0:
                    st.markdown("")
                    _hc1, _hc2, _hc3 = st.columns(3)

                    # ── Flip tile helper ──────────────────────────────────
                    def _flip_tile(col, key, icon, label, value, formula_lines):
                        """Render a metric tile that flips to show formula on click."""
                        _fk = f"flip_hvac_{key}"
                        if _fk not in st.session_state:
                            st.session_state[_fk] = False
                        with col:
                            if not st.session_state[_fk]:
                                st.markdown(
                                    f'<div style="background:#ffffff;border:1px solid #d9d4c5;'
                                    f'border-radius:3px;padding:12px 14px;text-align:center;">'
                                    f'<div style="font-size:11px;color:#7a807a;font-weight:600;'
                                    f'text-transform:uppercase;letter-spacing:0.05em;margin-bottom:4px;">'
                                    f'{icon} {label}</div>'
                                    f'<div style="font-size:22px;font-weight:700;color:#161a16;">'
                                    f'{value}</div></div>',
                                    unsafe_allow_html=True,
                                )
                            else:
                                st.markdown(
                                    f'<div style="background:#f4f1ea;border:1px solid #c5c0b4;'
                                    f'border-radius:3px;padding:10px 12px;">'
                                    + "".join([
                                        f'<div style="font-size:11px;color:#161a16;'
                                        f'font-family:monospace;margin-bottom:3px;">'
                                        f'{line}</div>'
                                        for line in formula_lines
                                    ])
                                    + "</div>",
                                    unsafe_allow_html=True,
                                )
                            if st.button(
                                "✕ Close" if st.session_state[_fk] else "ℹ️ How?",
                                key=f"btn_hvac_{key}",
                                use_container_width=True,
                            ):
                                st.session_state[_fk] = not st.session_state[_fk]
                                st.rerun()

                    _flip_tile(
                        _hc1, "heat",
                        "🔥", "Weekly Heating",
                        f"{_hvac['heating_kwh']:,.0f} kWh",
                        [
                            "ΔT = target_temp − outdoor_mean (°C)",
                            "load = ΔT × 10 W/m²/°C × footprint",
                            "kWh/day = load × 24h ÷ 0.85 efficiency",
                            "Sum over 7-day forecast days.",
                            "→ Assumptions §15, ASHRAE Fund. Ch.18",
                        ],
                    )
                    _flip_tile(
                        _hc2, "cool",
                        "❄️", "Weekly Cooling",
                        f"{_hvac['cooling_kwh']:,.0f} kWh",
                        [
                            "Same formula as heating but",
                            "ΔT = outdoor_mean − target_temp (°C).",
                            "Applies on days outdoor > target.",
                            "Same 0.85 efficiency factor applied.",
                            "→ Assumptions §15, ASHRAE Fund. Ch.18",
                        ],
                    )
                    _flip_tile(
                        _hc3, "cost",
                        "⚡", "Est. HVAC Cost",
                        f"${_hvac['total_cost']:,.2f}",
                        [
                            "cost = total_kWh × electricity $/kWh",
                            f"= {_hvac['total_kwh']:,.0f} kWh × ${_ac_kwh_price:.3f}/kWh",
                            "Price from farm country (Eurostat/IEA).",
                            "Upper bound — excludes solar gains.",
                            "→ Assumptions §15, §17.6",
                        ],
                    )

                # ── Crop alerts ───────────────────────────────────────────
                _alerts = get_crop_alerts(_fc, _ac_primary_crop, _ac_modality) # Keep emojis in alert messages
                if _alerts:
                    st.markdown("### Crop Alerts")
                    for _al in _alerts:
                        _lvl = _al["level"]
                        if _lvl == "critical":
                            st.error(f"🔴 **{_al['date']}** — {_al['message']}")
                        elif _lvl == "warning":
                            st.warning(f"🟡 **{_al['date']}** — {_al['message']}")
                        else:
                            st.info(f"🔵 **{_al['date']}** — {_al['message']}")
            else:
                st.caption("⚠️ Weather forecast unavailable — check farm coordinates.")
        else:
            st.info("Add coordinates to your farm profile to enable weather forecasts.")

        st.divider()
        
        # ── Active cycles ─────────────────────────────────────────────────────
        st.markdown("### Active Crop Cycles")
        try:
            _open_resp = (
                supabase.table("harvest_logs")
                .select("*")
                .eq("farm_id", _ac_farm["id"])
                .in_("status", ["seeding", "growing", "ready"])
                .order("seeding_date", desc=False)
                .execute()
            )
            _open_cycles = _open_resp.data or []
        except Exception as _e:
            _open_cycles = []
            st.caption(f"Could not load active cycles: {_e}")

        if not _open_cycles:
            st.info(
                "No active cycles. Open a new cycle in the **Log Cycle** tab "
                "by saving without a harvest date."
            )
        else:
            # Clear Space Planner navigation highlight after one render
            _ht_highlight_rack  = st.session_state.pop("highlight_rack", None)
            _ht_highlight_cycle = st.session_state.pop("highlight_cycle", None)
            for _oc in _open_cycles:
                _ocid     = _oc["id"]
                _oc_crop  = _oc.get("crop", "Unknown")
                _oc_zone  = _oc.get("zone") or "—"
                _oc_seed  = _oc.get("seeding_date")
                _oc_exp   = _oc.get("expected_harvest_date")
                _oc_status = _oc.get("status", "growing")
                _oc_area  = _oc.get("area_m2") or "—"

                # Days elapsed
                _days_elapsed = None
                if _oc_seed:
                    try:
                        _seed_dt = datetime.strptime(_oc_seed, "%Y-%m-%d").date()
                        _days_elapsed = (date.today() - _seed_dt).days
                    except Exception:
                        pass

                # Days to expected harvest
                _days_to_harvest = None
                if _oc_exp:
                    try:
                        _exp_dt = datetime.strptime(_oc_exp, "%Y-%m-%d").date()
                        _days_to_harvest = (_exp_dt - date.today()).days
                    except Exception:
                        pass

                _status_colours = {
                    "seeding": ("#e6ede4", "#2f5d3a"),
                    "growing": ("#e6edf2", "#2c5a78"),
                    "ready":   ("#f5ecd6", "#c08a2e"),
                    "failed":  ("#f3dfd2", "#b85c38"),
                }
                _s_bg, _s_fg = _status_colours.get(_oc_status, ("#f4f1ea", "#161a16"))

                # Fish cycle detection
                _is_fish_cycle = _oc_crop in FISH_SPECIES
                _cycle_icon    = "🐟" if _is_fish_cycle else "🌿"
                _zone_label    = "Tank" if _is_fish_cycle else "Zone"

                with st.expander( # Keep emojis in expander title
                    f"{_cycle_icon} {_oc_crop} — {_zone_label}: {_oc_zone} — "
                    + (f"Day {_days_elapsed}" if _days_elapsed is not None else "")
                    + (f" — 🟡 {'Harvest' if not _is_fish_cycle else 'Ready'} in {_days_to_harvest}d"
                       if _days_to_harvest is not None and 0 <= _days_to_harvest <= 5
                       else ""),
                    expanded=(
                        (_days_to_harvest is not None and 0 <= _days_to_harvest <= 3)
                        or str(_ocid) == (_ht_highlight_cycle or "")
                        or (_oc_zone and _oc_zone == (_ht_highlight_rack or ""))
                    ),
                ):
                    _oc1, _oc2, _oc3 = st.columns(3)
                    with _oc1:
                        st.markdown(
                            f'<span style="background:{_s_bg};color:{_s_fg};'
                            f'font-size:11px;font-weight:700;padding:2px 8px;'
                            f'border-radius:2px;">{_oc_status.upper()}</span>',
                            unsafe_allow_html=True,
                        )
                        if _is_fish_cycle:
                            st.markdown(f"**Species:** {_oc_crop}")
                            st.markdown(f"**Tank:** {_oc_zone}")
                            _fish_spec = FISH_SPECIES.get(_oc_crop, {})
                            if _fish_spec:
                                st.caption(
                                    f"Grow cycle: {_fish_spec.get('grow_cycle_days','?')}d · "
                                    f"Harvest weight: {_fish_spec.get('harvest_weight_kg','?')} kg/fish"
                                )
                            if _oc_area and str(_oc_area) != "—":
                                st.markdown(f"**Tank vol:** {_oc_area} m³")
                        else:
                            st.markdown(f"**Crop:** {_oc_crop}")
                            st.markdown(f"**Zone:** {_oc_zone}")
                            st.markdown(f"**Area:** {_oc_area} m²")
                    with _oc2:
                        _seed_label = "Stocked" if _is_fish_cycle else "Seeded"
                        st.markdown(f"**{_seed_label}:** {_oc_seed or '—'}")
                        st.markdown(f"**Expected harvest:** {_oc_exp or '—'}")
                        if _days_elapsed is not None:
                            st.markdown(f"**Days elapsed:** {_days_elapsed}")
                        if _days_to_harvest is not None:
                            _dt_label = (
                                "🔴 Overdue" if _days_to_harvest < 0
                                else ("🟡 Ready soon" if _days_to_harvest <= 3
                                      else f"In {_days_to_harvest} days")
                            )
                            st.markdown(f"**Days to harvest:** {_dt_label}")
                        if not _is_fish_cycle:
                            try:
                                _rla_resp = supabase.table("rack_layer_assignments").select(
                                    "rack_name, layer_index, area_m2"
                                ).eq("cycle_id", _ocid).execute()
                                _rla_rows = _rla_resp.data or []
                                if _rla_rows:
                                    _rla_by_rack = {}
                                    for _rla in _rla_rows:
                                        _rla_by_rack.setdefault(_rla["rack_name"], []).append(_rla["layer_index"])
                                    st.markdown("**📍 Layout assignments:**")
                                    for _rack_nm, _layers in _rla_by_rack.items():
                                        _layer_str = ", ".join(f"L{l+1}" for l in sorted(_layers))
                                        st.caption(f"↳ {_rack_nm} — {_layer_str}")
                            except Exception:
                                pass
                        else:
                            st.markdown(f"**📍 Tank:** {_oc_zone}")
                    with _oc3:
                        # Observation log
                        _obs_raw  = _oc.get("observations") or []
                        _obs_list = _obs_raw if isinstance(_obs_raw, list) else []
                        if _obs_list:
                            st.markdown("**Observations:**")
                            for _ob in _obs_list[-3:]:
                                st.caption(f"_{_ob.get('date','?')}_: {_ob.get('text','')}")

                    # Actions
                    _act1, _act2, _act3, _act4, _act5, _act6 = st.columns(6)

                    # Add observation
                    with _act1:
                        if st.button("📝 Note", key=f"obs_{_ocid}", # Keep emoji in button
                                     use_container_width=True,
                                     help="Add an observation to this cycle"):
                            st.session_state[f"obs_open_{_ocid}"] = True

                    # View on Map (Space Planner)
                    with _act6:
                        if st.button("📍 Map", key=f"map_{_ocid}", # Keep emoji in button
                                     use_container_width=True,
                                     help="Open this rack in the Space Planner"):
                            st.session_state["highlight_rack"]  = _oc_zone
                            st.session_state["highlight_cycle"] = str(_ocid)
                            st.switch_page("pages/5_Space_Planner.py")

                    # Update status
                    with _act2:
                        _new_status = st.selectbox(
                            "Status",
                            ["seeding", "growing", "ready"],
                            index=["seeding","growing","ready"].index(_oc_status)
                            if _oc_status in ["seeding","growing","ready"] else 1,
                            key=f"status_sel_{_ocid}",
                            label_visibility="collapsed",
                        )
                        if _new_status != _oc_status:
                            if st.button("Update", key=f"upd_status_{_ocid}",
                                         use_container_width=True):
                                try:
                                    supabase.table("harvest_logs").update(
                                        {"status": _new_status}
                                    ).eq("id", _ocid).execute()
                                    st.success("Status updated.")
                                    st.rerun()
                                except Exception as _ue:
                                    st.error(str(_ue))

                    # Close cycle with harvest
                    with _act3:
                        if st.button("✅ Close / Harvest", key=f"close_{_ocid}", # Keep emoji in button
                                     use_container_width=True,
                                     type="primary"):
                            st.session_state[f"close_open_{_ocid}"] = True

                    # Edit cycle
                    with _act4:
                        if st.button("✏️ Edit", key=f"edit_{_ocid}", # Keep emoji in button
                                     use_container_width=True,
                                     help="Edit cycle details, rack, or layer assignments"):
                            st.session_state[f"edit_open_{_ocid}"] = True

                    # Mark failed
                    with _act5:
                        if st.button("❌ Failed", key=f"fail_{_ocid}", # Keep emoji in button
                                     use_container_width=True):
                            st.session_state[f"fail_open_{_ocid}"] = True

                    # Observation form
                    if st.session_state.get(f"obs_open_{_ocid}"):
                        with st.form(f"obs_form_{_ocid}"):
                            st.markdown("**Add observation**")
                            _ob_text = st.text_area("Observation",
                                placeholder="e.g. Yellowing on lower leaves, aphid presence zone B",
                                height=80)
                            _ob_s, _ob_c = st.columns(2)
                            _ob_save   = _ob_s.form_submit_button("💾 Save", use_container_width=True)
                            _ob_cancel = _ob_c.form_submit_button("✖ Cancel", use_container_width=True)
                        if _ob_save and _ob_text.strip():
                            _updated_obs = _obs_list + [
                                {"date": str(date.today()), "text": _ob_text.strip()}
                            ]
                            try:
                                supabase.table("harvest_logs").update(
                                    {"observations": _updated_obs}
                                ).eq("id", _ocid).execute()
                                st.session_state.pop(f"obs_open_{_ocid}", None)
                                st.success("Observation saved.")
                                st.rerun()
                            except Exception as _oe:
                                st.error(str(_oe))
                        if _ob_cancel:
                            st.session_state.pop(f"obs_open_{_ocid}", None)
                            st.rerun()

                    # Close cycle form
                    if st.session_state.get(f"close_open_{_ocid}"):
                        with st.form(f"close_form_{_ocid}"):
                            st.markdown("**Close cycle — record harvest**")
                            _cl1, _cl2 = st.columns(2)
                            with _cl1:
                                _cl_date  = st.date_input("Harvest date", value=date.today())
                                _cl_kg    = st.number_input("kg Harvested",
                                    min_value=0.1, step=0.5, format="%.2f")
                            with _cl2:
                                _cl_price = st.number_input("Sale price ($/kg)",
                                    min_value=0.0, step=0.01, format="%.3f")
                                _cl_chan  = st.selectbox("Sales channel",
                                    ["— Not sold yet —"] + SALES_CHANNELS)
                                _cl_waste = st.number_input("Rejection % at sale",
                                    min_value=0.0, max_value=100.0, step=0.5)
                            _cl_notes = st.text_area("Notes (optional)", height=60)
                            _cls, _clc = st.columns(2)
                            _cl_save   = _cls.form_submit_button("✅ Close Cycle",
                                use_container_width=True, type="primary")
                            _cl_cancel = _clc.form_submit_button("✖ Cancel",
                                use_container_width=True)
                        if _cl_save:
                            # Compute cycle score
                            _score = None
                            if (_oc_seed and _oc.get("area_m2") and
                                    _oc.get("area_m2") > 0 and _cl_kg > 0):
                                _mod = _ac_modality
                                if _mod == "vertical_farm" and _oc_crop in CROPS:
                                    _model_yield = CROPS[_oc_crop].get("yield", 0)
                                    _actual_yield = _cl_kg / float(_oc["area_m2"])
                                    _score = round(
                                        (_actual_yield / _model_yield * 100)
                                        if _model_yield > 0 else None, 1
                                    )
                            try:
                                supabase.table("harvest_logs").update({
                                    "status":              "harvested",
                                    "date":                str(_cl_date),
                                    "kg_harvested":        _cl_kg,
                                    "sale_price_per_kg":   _cl_price if _cl_price > 0 else None,
                                    "sales_channel":       _cl_chan
                                        if _cl_chan != "— Not sold yet —" else None,
                                    "waste_pct":           _cl_waste if _cl_waste > 0 else None,
                                    "notes":               _cl_notes or None,
                                    "cycle_end_date":      str(_cl_date),
                                }).eq("id", _ocid).execute()
                                st.session_state.pop(f"close_open_{_ocid}", None)
                                _score_msg = (
                                    f" Yield score: {_score}% of model."
                                    if _score is not None else ""
                                )
                                st.success(
                                    f"✅ Cycle closed — {_cl_kg:.1f} kg harvested."
                                    + _score_msg
                                )
                                st.rerun()
                            except Exception as _ce:
                                st.error(str(_ce))
                        if _cl_cancel:
                            st.session_state.pop(f"close_open_{_ocid}", None)
                            st.rerun()

                    # Edit cycle form (two-step: rack select → layer assign + conflict check)
                    if st.session_state.get(f"edit_open_{_ocid}"):
                        # ── Fetch layout objects ──────────────────────────────
                        _ed_layout_racks = []
                        _ed_layout_tanks = []
                        try:
                            _ed_lr = supabase.table("farm_layouts").select(
                                "layout_json"
                            ).eq("farm_id", _ac_farm["id"]).eq("is_active", True).limit(1).execute()
                            if _ed_lr.data:
                                _ed_lj = _ed_lr.data[0].get("layout_json") or {}
                                if isinstance(_ed_lj, str):
                                    import json as _json2
                                    _ed_lj = _json2.loads(_ed_lj)
                                _ed_layout_racks = [o for o in (_ed_lj.get("objects") or []) if o.get("type") == "rack"]
                                _ed_layout_tanks = [o for o in (_ed_lj.get("objects") or []) if o.get("type") == "tank"]
                        except Exception:
                            _ed_layout_racks = []
                            _ed_layout_tanks = []

                        # ── Fetch existing layer assignments (plant cycles only) ──
                        _ed_existing_layers = []
                        _ed_existing_rack   = None
                        if not _is_fish_cycle:
                            try:
                                _ed_rla = supabase.table("rack_layer_assignments").select(
                                    "id, rack_name, layer_index, area_m2"
                                ).eq("cycle_id", _ocid).execute()
                                _ed_existing_layers = _ed_rla.data or []
                                if _ed_existing_layers:
                                    _ed_existing_rack = _ed_existing_layers[0]["rack_name"]
                            except Exception:
                                _ed_existing_layers = []

                        st.markdown(f"**✏️ Edit {'fish' if _is_fish_cycle else 'plant'} cycle**")
                        _edf1, _edf2 = st.columns(2)

                        # ── Left col: core fields ─────────────────────────────
                        with _edf1:
                            _ed_farm_mod = (_ac_farm.get("modality") or _ac_farm.get("agriculture_type") or "vertical_farm")
                            _is_ed_aq    = "aquaponics" in _ed_farm_mod

                            if _is_fish_cycle:
                                _ed_crop_opts = list(FISH_SPECIES.keys())
                            elif _ed_farm_mod == "vertical_farm":
                                _ed_crop_opts = list(CROPS.keys())
                            elif _ed_farm_mod == "polytunnel" or (_is_ed_aq and _ac_farm.get("crop_source") == "polytunnel"):
                                _ed_crop_opts = list(POLYTUNNEL_CROPS.keys())
                            else:
                                _ed_crop_opts = list(GREENHOUSE_CROPS.keys())
                            if _oc_crop and _oc_crop not in _ed_crop_opts:
                                _ed_crop_opts = [_oc_crop] + _ed_crop_opts
                            _ed_crop_idx = _ed_crop_opts.index(_oc_crop) if _oc_crop in _ed_crop_opts else 0
                            _ed_crop     = st.selectbox(
                                "Fish Species" if _is_fish_cycle else "Crop",
                                _ed_crop_opts, index=_ed_crop_idx, key=f"ed_crop_{_ocid}"
                            )

                            _ed_seed_label = "Stocking date" if _is_fish_cycle else "Seeding date"
                            _ed_seed_val   = (datetime.strptime(_oc_seed, "%Y-%m-%d").date() if _oc_seed else date.today())
                            _ed_seed       = st.date_input(_ed_seed_label, value=_ed_seed_val, key=f"ed_seed_{_ocid}")

                            # Auto-compute expected harvest
                            _ed_crop_days = (
                                FISH_SPECIES.get(_ed_crop, {}).get("grow_cycle_days")
                                or CROPS.get(_ed_crop, {}).get("cycle")
                                or GREENHOUSE_CROPS.get(_ed_crop, {}).get("cycle")
                                or POLYTUNNEL_CROPS.get(_ed_crop, {}).get("cycle")
                            )
                            _ed_exp_default = (
                                datetime.strptime(_oc_exp, "%Y-%m-%d").date() if _oc_exp
                                else (_ed_seed + timedelta(days=int(_ed_crop_days)) if _ed_crop_days else None)
                            )
                            _ed_exp = st.date_input("Expected harvest", value=_ed_exp_default, key=f"ed_exp_{_ocid}")
                            if _ed_crop_days and not _oc_exp:
                                st.caption(f"📅 Auto-set from {_ed_crop_days}-day model cycle.")

                        # ── Right col: zone/tank/rack selector ────────────────
                        with _edf2:
                            _ed_area_label = "Tank volume (m³)" if _is_fish_cycle else "Area (m²)"
                            _ed_area = st.number_input(
                                _ed_area_label, min_value=0.0, step=0.1,
                                value=float(_oc_area) if str(_oc_area).replace(".", "", 1).isdigit() else 0.0,
                                key=f"ed_area_{_ocid}"
                            )

                            _ed_sel_rack_obj = None
                            if _is_fish_cycle:
                                # Tank selector
                                if _ed_layout_tanks:
                                    _ed_tank_options = ["— Free text —"] + [
                                        f"{t['name']} (~{t.get('w',0)*t.get('h',0)*t.get('depth',1):.1f} m³)"
                                        for t in _ed_layout_tanks
                                    ]
                                    _ed_tank_default = next(
                                        (i + 1 for i, t in enumerate(_ed_layout_tanks) if t["name"] == _oc_zone), 0
                                    )
                                    _ed_tank_sel = st.selectbox("Fish Tank", _ed_tank_options,
                                        index=_ed_tank_default, key=f"ed_tank_{_ocid}")
                                    if _ed_tank_sel == "— Free text —":
                                        _ed_zone = st.text_input("Tank name (free text)",
                                            value=_oc_zone or "", key=f"ed_tank_ft_{_ocid}")
                                    else:
                                        _ed_zone = _ed_tank_sel.split(" (~")[0]
                                else:
                                    _ed_zone = st.text_input("Tank name", value=_oc_zone or "", key=f"ed_zone_fish_{_ocid}")
                            elif _ed_layout_racks:
                                # Rack selector
                                _ed_rack_options = ["— Free text —"] + [
                                    f"{r['name']} ({r.get('rackType','standard').upper()}, {r.get('layers',5)}L)"
                                    for r in _ed_layout_racks
                                ]
                                _ed_rack_default = next(
                                    (i + 1 for i, r in enumerate(_ed_layout_racks)
                                     if r["name"] == (_ed_existing_rack or _oc_zone)), 0
                                )
                                _ed_rack_sel = st.selectbox("Rack", _ed_rack_options,
                                    index=_ed_rack_default, key=f"ed_rack_{_ocid}")
                                if _ed_rack_sel == "— Free text —":
                                    _ed_zone = st.text_input("Zone (free text)",
                                        value=_oc_zone or "", key=f"ed_zone_ft_{_ocid}")
                                else:
                                    _ed_zone = _ed_rack_sel.split(" (")[0]
                                    _ed_sel_rack_obj = next(
                                        (r for r in _ed_layout_racks if r["name"] == _ed_zone), None
                                    )
                            else:
                                _ed_zone = st.text_input("Zone (free text)",
                                    value=_oc_zone or "", key=f"ed_zone_{_ocid}")

                        # ── Layer assignment — PLANT CYCLES ONLY ─────────────
                        _ed_layer_selections = []
                        if not _is_fish_cycle and _ed_sel_rack_obj:
                            _ed_n_layers  = int(_ed_sel_rack_obj.get("layers") or 1)
                            _ed_area_per  = float(_ed_sel_rack_obj.get("w", 0)) * float(_ed_sel_rack_obj.get("h", 0))
                            _assigned_layer_idxs = {a["layer_index"] for a in _ed_existing_layers
                                                    if a.get("rack_name") == _ed_zone}
                            # Conflict detection
                            _ed_conflicts = {}
                            try:
                                _ed_all_rla = supabase.table("rack_layer_assignments").select(
                                    "cycle_id, layer_index"
                                ).eq("farm_id", _ac_farm["id"]).eq("rack_name", _ed_zone).execute()
                                for _rla_row in (_ed_all_rla.data or []):
                                    if _rla_row["cycle_id"] != _ocid:
                                        _li = _rla_row["layer_index"]
                                        _ed_conflicts[_li] = _ed_conflicts.get(_li, 0) + 1
                            except Exception:
                                pass
                            if _ed_conflicts:
                                _conflict_summary = ", ".join(f"L{l+1}" for l in sorted(_ed_conflicts))
                                st.warning(f"⚠️ Layer conflicts on {_ed_zone}: {_conflict_summary} already assigned to another cycle.")
                            st.markdown(f"**Layer assignment** — {_ed_zone} · {_ed_n_layers} layers")
                            _ed_la_cols = st.columns(min(_ed_n_layers, 8))
                            for _ed_li in range(_ed_n_layers):
                                with _ed_la_cols[_ed_li % min(_ed_n_layers, 8)]:
                                    _ed_checked = st.checkbox(
                                        f"L{_ed_li+1}{' ⚠️' if _ed_li in _ed_conflicts else ''}",
                                        value=(_ed_li in _assigned_layer_idxs if _assigned_layer_idxs else True),
                                        key=f"ed_layer_{_ocid}_{_ed_li}",
                                    )
                                    _ed_layer_selections.append({"layer": _ed_li, "selected": _ed_checked})
                            _ed_sel_layers = [a["layer"] for a in _ed_layer_selections if a["selected"]]
                            if _ed_sel_layers and _ed_area_per > 0:
                                st.caption(f"✅ {len(_ed_sel_layers)} layer(s) — ~{_ed_area_per * len(_ed_sel_layers):.1f} m² canopy")

                        # ── Save / Cancel ─────────────────────────────────────
                        _edsave_col, _edcanc_col = st.columns(2)
                        _ed_save_btn = _edsave_col.button("💾 Save changes",
                            key=f"ed_save_{_ocid}", use_container_width=True, type="primary")
                        _ed_canc_btn = _edcanc_col.button("✖ Cancel",
                            key=f"ed_canc_{_ocid}", use_container_width=True)

                        if _ed_save_btn:
                            try:
                                _ed_update = {
                                    "crop":                  _ed_crop,
                                    "zone":                  _ed_zone or None,
                                    "seeding_date":          str(_ed_seed),
                                    "expected_harvest_date": str(_ed_exp) if _ed_exp else None,
                                    "area_m2":               _ed_area if _ed_area > 0 else None,
                                }
                                supabase.table("harvest_logs").update(_ed_update).eq("id", _ocid).execute()
                                # Layer assignments: only for plant cycles
                                if not _is_fish_cycle:
                                    supabase.table("rack_layer_assignments").delete().eq("cycle_id", _ocid).execute()
                                    if _ed_sel_rack_obj and _ed_layer_selections:
                                        _ed_area_per_s = float(_ed_sel_rack_obj.get("w", 0)) * float(_ed_sel_rack_obj.get("h", 0))
                                        _ed_rows = [
                                            {"farm_id": _ac_farm["id"], "cycle_id": _ocid,
                                             "rack_name": _ed_zone, "layer_index": _li,
                                             "area_m2": round(_ed_area_per_s, 2) if _ed_area_per_s > 0 else None}
                                            for _li in [a["layer"] for a in _ed_layer_selections if a["selected"]]
                                        ]
                                        if _ed_rows:
                                            supabase.table("rack_layer_assignments").insert(_ed_rows).execute()
                                st.session_state.pop(f"edit_open_{_ocid}", None)
                                st.success("✅ Cycle updated.")
                                st.rerun()
                            except Exception as _ee:
                                st.error(str(_ee))

                        if _ed_canc_btn:
                            st.session_state.pop(f"edit_open_{_ocid}", None)
                            st.rerun()

                    # Failed form
                    if st.session_state.get(f"fail_open_{_ocid}"):
                        with st.form(f"fail_form_{_ocid}"):
                            st.markdown("**Mark cycle as failed**")
                            _fr_reason = st.text_area(
                                "Failure reason",
                                placeholder="e.g. Disease outbreak, equipment failure, frost damage",
                                height=80,
                            )
                            _fs, _fc2 = st.columns(2)
                            _fr_save   = _fs.form_submit_button("✅ Confirm", use_container_width=True)
                            _fr_cancel = _fc2.form_submit_button("✖ Cancel", use_container_width=True)
                        if _fr_save:
                            try:
                                supabase.table("harvest_logs").update({
                                    "status":         "failed",
                                    "failure_reason": _fr_reason or None,
                                }).eq("id", _ocid).execute()
                                st.session_state.pop(f"fail_open_{_ocid}", None)
                                st.warning("Cycle marked as failed.")
                                st.rerun()
                            except Exception as _fe:
                                st.error(str(_fe))
                        if _fr_cancel:
                            st.session_state.pop(f"fail_open_{_ocid}", None)
                            st.rerun()

        # ── Harvest Prediction Calendar ───────────────────────────────────────
        _today = date.today()
        _cal_cycles = [
            c for c in _open_cycles
            if c.get("expected_harvest_date")
            and _today <= date.fromisoformat(c["expected_harvest_date"]) <= _today + timedelta(days=13)
        ]

        st.divider()
        st.markdown("### Upcoming Harvests — Next 14 Days")
        if not _cal_cycles:
            st.info("No harvests expected in the next 14 days.")
        else:
            _days = [_today + timedelta(days=i) for i in range(14)]
            _cols = st.columns(14)
            _crop_colours = {}
            _palette = ["🟢","🔵","🟠","🟣","🔴","🟡","🟤"]
            for _idx, _day in enumerate(_days):
                _due = [c for c in _cal_cycles if date.fromisoformat(c["expected_harvest_date"]) == _day]
                with _cols[_idx]:
                    st.markdown(f"<div style='text-align:center;font-size:11px;font-weight:600'>{_day.strftime('%a')}<br>{_day.strftime('%d/%m')}</div>", unsafe_allow_html=True)
                    if _due:
                        for _dc in _due:
                            _cr = _dc.get("crop","?")
                            if _cr not in _crop_colours:
                                _crop_colours[_cr] = _palette[len(_crop_colours) % len(_palette)]
                            st.markdown(f"<div style='text-align:center;font-size:11px'>{_crop_colours[_cr]}<br>{_cr[:6]}</div>", unsafe_allow_html=True)
                    else:
                        st.markdown("<div style='text-align:center;color:#aaa;font-size:16px'>·</div>", unsafe_allow_html=True)

            with st.expander("📋 Harvest schedule detail"):
                _cal_rows = []
                for _dc in sorted(_cal_cycles, key=lambda x: x["expected_harvest_date"]):
                    _cal_rows.append({
                        "Expected Date": _dc.get("expected_harvest_date","—"),
                        "Crop":          _dc.get("crop","—"),
                        "Zone / Rack":   _dc.get("zone") or "—",
                        "Area (m²)":     _dc.get("area_m2","—"),
                        "Status":        _dc.get("status","—"),
                    })
                st.dataframe(pd.DataFrame(_cal_rows), use_container_width=True, hide_index=True)

        st.divider()
        st.markdown("### Recently Closed Cycles")
        try:
            _closed_resp = (
                supabase.table("harvest_logs")
                .select("id, date, crop, zone, kg_harvested, seeding_date, status, area_m2")
                .eq("farm_id", _ac_farm["id"])
                .eq("status", "harvested")
                .order("date", desc=True)
                .limit(8)
                .execute()
            )
            _closed = _closed_resp.data or []
        except Exception:
            _closed = []

        if _closed:
            _cl_df = pd.DataFrame(_closed)[[
                "date", "crop", "zone", "kg_harvested",
                "seeding_date", "area_m2"
            ]].rename(columns={
                "date": "Harvest Date", "crop": "Crop",
                "zone": "Zone", "kg_harvested": "kg",
                "seeding_date": "Seeded", "area_m2": "Area (m²)",
            })
            st.dataframe(_cl_df, use_container_width=True, hide_index=True)
        else:
            st.caption("No completed cycles yet.")

# ─────────────────────────────────────────────────────────────────────────────
# TAB 1 — Farm Comparison
# ─────────────────────────────────────────────────────────────────────────────
with tab1:
    st.subheader("Farm Comparison")
    st.caption(
        "Side-by-side comparison of all saved farm profiles. "
        "Figures are from the last saved model snapshot — re-run the ROI Calculator "
        "and save to update them."
    )

    try:
        _cmp_resp = supabase.table("farms").select(
            "id, name, modality, country, crop, footprint, automation, "
            "crop_mix_json, model_snapshot, model_updated_at, created_at"
        ).order("created_at", desc=True).execute()
        _cmp_farms = _cmp_resp.data or []
    except Exception as _e:
        st.error(f"Could not load farms: {_e}")
        _cmp_farms = []

    _active_farm = st.session_state.get("active_farm")

    if not _cmp_farms:
        st.info("No farm profiles yet. Create one in the ROI Calculator.")
    else:
        # ── Parse model snapshots ─────────────────────────────────────────────
        _MOD_BADGE = {
            "vertical_farm":        ("🏭", "#3b3b52", "#ffffff"),
            "greenhouse":           ("🌿", "#2f5d3a", "#ffffff"),
            "polytunnel":           ("🌿", "#2f5d3a", "#ffffff"),
            "aquaponics_decoupled": ("🐟", "#2c5a78", "#ffffff"),
            "aquaponics_coupled":   ("♻️", "#1f4d39", "#ffffff"),
        }

        _rows = []
        for _f in _cmp_farms:
            _snap = None # Keep emojis in _MOD_BADGE dictionary
            _snap_raw = _f.get("model_snapshot")
            if _snap_raw:
                try:
                    _snap = json.loads(_snap_raw) if isinstance(_snap_raw, str) else _snap_raw
                except Exception:
                    _snap = None

            # For aquaponics, model_snapshot may have nested plant/fish structure
            if _snap and "plant" in _snap:
                _snap_plant = _snap.get("plant", {})
                _revenue   = _snap_plant.get("annual_revenue") or _snap.get("combined_revenue")
                _ebitda    = _snap_plant.get("ebitda") or _snap.get("combined_ebitda")
                _capex     = _snap_plant.get("total_capex") or _snap.get("combined_capex")
                _margin    = _snap_plant.get("ebitda_margin")
                _payback   = _snap_plant.get("payback_years")
                _energy_pct = (
                    _snap_plant.get("annual_energy_cost", 0) / _revenue * 100
                    if _revenue and _revenue > 0 else None
                )
            elif _snap:
                _revenue   = _snap.get("annual_revenue")
                _ebitda    = _snap.get("ebitda")
                _capex     = _snap.get("total_capex")
                _margin    = _snap.get("ebitda_margin")
                _payback   = _snap.get("payback_years")
                _energy_pct = (
                    _snap.get("annual_energy_cost", 0) / _revenue * 100
                    if _revenue and _revenue > 0 else None
                )
            else:
                _revenue = _ebitda = _capex = _margin = _payback = _energy_pct = None

            # Crop summary
            _mix_raw = _f.get("crop_mix_json")
            _crop_str = _f.get("crop", "—")
            if _mix_raw:
                try:
                    _mix = json.loads(_mix_raw) if isinstance(_mix_raw, str) else _mix_raw
                    if isinstance(_mix, list) and len(_mix) > 1:
                        _crop_str = " / ".join(
                            f"{r['crop'].split(' ')[0]} {r['pct']}%"
                            for r in _mix[:3]
                        )
                except Exception:
                    pass

            _rows.append({
                "id":        _f["id"],
                "name":      _f["name"],
                "modality":  _f.get("modality", "vertical_farm"),
                "country":   _f.get("country", "—"),
                "crop":      _crop_str,
                "footprint": int(_f.get("footprint") or 0),
                "automation": _f.get("automation", "—"),
                "revenue":   _revenue,
                "ebitda":    _ebitda,
                "margin":    _margin,
                "capex":     _capex,
                "payback":   _payback,
                "energy_pct": _energy_pct,
                "updated":   (_f.get("model_updated_at") or "")[:10] or "—",
                "is_active": bool(_active_farm and _active_farm.get("id") == _f["id"]),
            })

        # ── Metric selector ───────────────────────────────────────────────────
        _metric_opts = {
            "EBITDA ($)":          "ebitda",
            "Annual Revenue ($)":  "revenue",
            "EBITDA Margin (%)":   "margin",
            "Total CAPEX ($)":     "capex",
            "Payback (yrs)":       "payback",
            "Energy % Revenue":    "energy_pct",
        }
        _sel_metric_label = st.selectbox(
            "Compare by",
            list(_metric_opts.keys()),
            key="cmp_metric_sel",
        )
        _sel_metric = _metric_opts[_sel_metric_label]

        # ── Sort by selected metric ───────────────────────────────────────────
        _asc = _sel_metric in ("payback", "energy_pct", "capex")
        _rows_sorted = sorted(
            _rows,
            key=lambda r: (r[_sel_metric] is None, r[_sel_metric] if r[_sel_metric] is not None else 0),
            reverse=not _asc,
        )

        # ── Bar chart ─────────────────────────────────────────────────────────
        _chart_names  = [r["name"] for r in _rows_sorted if r[_sel_metric] is not None]
        _chart_values = [r[_sel_metric] for r in _rows_sorted if r[_sel_metric] is not None]
        _chart_modalities = [r["modality"] for r in _rows_sorted if r[_sel_metric] is not None]

        _MODALITY_COLOURS_MAP = {
            "vertical_farm":        "#3b3b52",
            "greenhouse":           "#2f5d3a",
            "polytunnel":           "#2f5d3a",
            "aquaponics_decoupled": "#2c5a78",
            "aquaponics_coupled":   "#1f4d39",
        }
        _bar_colours = [_MODALITY_COLOURS_MAP.get(m, "#4a524a") for m in _chart_modalities]

        # Format values for display
        def _fmt_metric(val, metric_key):
            if val is None:
                return "—"
            if metric_key in ("ebitda", "revenue", "capex"):
                return f"${val:,.0f}"
            if metric_key == "margin":
                return f"{val*100:.1f}%"
            if metric_key == "payback":
                return f"{val:.1f} yrs"
            if metric_key == "energy_pct":
                return f"{val:.1f}%"
            return str(round(val, 2))

        if _chart_names:
            _display_values = [
                val * 100 if _sel_metric == "margin" else val
                for val in _chart_values
            ]
            _fig_cmp = go.Figure(go.Bar(
                x=_chart_names,
                y=_display_values,
                marker_color=_bar_colours,
                text=[_fmt_metric(v, _sel_metric) for v in _chart_values],
                textposition="outside",
                textfont=dict(size=11, color="#161a16"),
            ))
            _fig_cmp.update_layout(
                plot_bgcolor="#ffffff",
                paper_bgcolor="#ffffff",
                font_color="#161a16",
                margin=dict(t=20, b=40, l=10, r=10),
                height=320,
                showlegend=False,
                yaxis=dict(showgrid=True, gridcolor="#e8e3d4", zeroline=True,
                           zerolinecolor="#d9d4c5"),
                xaxis=dict(showgrid=False),
            )
            style_fig(_fig_cmp)
            st.plotly_chart(_fig_cmp, use_container_width=True)
        else:
            st.info("No model snapshots yet — run the ROI Calculator for each farm and save.")

        # ── Comparison table ──────────────────────────────────────────────────
        st.divider()
        st.markdown("**All farms**")

        for _row in _rows_sorted:
            _icon, _bg, _fg = _MOD_BADGE.get(_row["modality"], ("🌱", "#4a524a", "#ffffff"))
            _is_active_str = " ✅" if _row["is_active"] else ""
            with st.expander( # Keep emojis in expander title
                f"{_icon} {_row['name']}{_is_active_str} — "
                f"{_row['country']} — {_row['footprint']:,} m²",
                expanded=_row["is_active"],
            ):
                _tc1, _tc2, _tc3 = st.columns(3)
                with _tc1:
                    st.markdown(
                        f'<span style="background:{_bg};color:{_fg};font-size:11px;'
                        f'font-weight:700;padding:2px 8px;border-radius:2px;">' # Keep emoji in badge
                        f'{_icon} {_row["modality"].replace("_"," ").title()}</span>',
                        unsafe_allow_html=True,
                    )
                    st.markdown(f"**Crop:** {_row['crop']}")
                    st.markdown(f"**Automation:** {_row['automation']}")
                    st.markdown(f"**Footprint:** {_row['footprint']:,} m²")
                with _tc2:
                    st.markdown(f"**Revenue:** {_fmt_metric(_row['revenue'], 'revenue')}")
                    st.markdown(f"**EBITDA:** {_fmt_metric(_row['ebitda'], 'ebitda')}")
                    st.markdown(f"**EBITDA Margin:** {_fmt_metric(_row['margin'], 'margin')}")
                with _tc3:
                    st.markdown(f"**CAPEX:** {_fmt_metric(_row['capex'], 'capex')}")
                    st.markdown(f"**Payback:** {_fmt_metric(_row['payback'], 'payback')}")
                    st.markdown(f"**Energy % Rev:** {_fmt_metric(_row['energy_pct'], 'energy_pct')}")
                    st.markdown(f"**Model updated:** {_row['updated']}")

                st.markdown("")
                _act1, _act2, _act3 = st.columns(3)
                with _act1:
                    if st.button(
                        "✅ Activate this farm", # Keep emoji in button
                        key=f"cmp_activate_{_row['id']}",
                        use_container_width=True,
                        type="primary" if not _row["is_active"] else "secondary",
                    ):
                        try:
                            _full = supabase.table("farms").select("*").eq(
                                "id", _row["id"]
                            ).single().execute()
                            _fd = _full.data
                        except Exception:
                            _fd = next((f for f in _cmp_farms if f["id"] == _row["id"]), {})
                        st.session_state["active_farm"]        = _fd
                        st.session_state["_pending_farm_load"] = _fd
                        if _fd.get("lat") and _fd.get("lon"):
                            st.session_state["shared_lat"] = _fd["lat"]
                            st.session_state["shared_lng"] = _fd["lon"]
                        from core.farm_context import MODALITY_RADIO
                        st.session_state["_pending_modality"] = MODALITY_RADIO.get(
                            _fd.get("modality", "vertical_farm"),
                            "🏭 Indoor Vertical Farm",
                        )
                        st.success(f"✅ {_fd.get('name')} activated.")
                        st.rerun()
                with _act2:
                    if st.button(
                        "📊 Open in Calculator", # Keep emoji in button
                        key=f"cmp_calc_{_row['id']}",
                        use_container_width=True,
                    ):
                        try:
                            _full = supabase.table("farms").select("*").eq(
                                "id", _row["id"]
                            ).single().execute()
                            _fd = _full.data
                        except Exception:
                            _fd = next((f for f in _cmp_farms if f["id"] == _row["id"]), {})
                        st.session_state["active_farm"]        = _fd
                        st.session_state["_pending_farm_load"] = _fd
                        from core.farm_context import MODALITY_RADIO
                        st.session_state["_pending_modality"] = MODALITY_RADIO.get(
                            _fd.get("modality", "vertical_farm"),
                            "🏭 Indoor Vertical Farm",
                        )
                        st.switch_page("pages/1_ROI_Calculator.py")
                with _act3:
                    if st.button(
                        "🏗 Plan Layout", # Keep emoji in button
                        key=f"plan_layout_{_row['id']}",
                        use_container_width=True,
                    ):
                        try:
                            _full = supabase.table("farms").select("*").eq(
                                "id", _row["id"]
                            ).single().execute()
                            _fd = _full.data
                        except Exception:
                            _fd = next((f for f in _cmp_farms if f["id"] == _row["id"]), {})
                        st.session_state["active_farm"]        = _fd
                        st.session_state["_pending_farm_load"] = _fd
                        st.switch_page("pages/5_Space_Planner.py")

# ─────────────────────────────────────────────────────────────────────────────
# TAB 2 — Log Cycle (open or close a crop cycle)
# ─────────────────────────────────────────────────────────────────────────────
with tab2:
    st.subheader("🌿 Log Crop Cycle")
    active_farm = st.session_state.get("active_farm")

    if not active_farm:
        st.warning("Please select an active farm in the Farm Profiles tab first.")
    else:
        st.caption(f"Logging for: **{active_farm['name']}** — {active_farm.get('crop','—')} / {active_farm.get('country','—')}")

        _lc_mode = st.radio(
            "Entry type",
            ["🌱 Open new cycle (seeding)", "✅ Log completed harvest"],
            horizontal=True,
            key="lc_mode_radio",
        )
        st.markdown("---")

        # Pre-compute cycle days so variables are always in scope at submit time
        _lc_crop_days = None
        _exp_harvest  = None

        # ── Cycle type and species/crop selector (outside form so it controls form layout) ──
        _farm_modality_pre = (active_farm.get('modality') or
                              active_farm.get('agriculture_type') or 'vertical_farm')
        _is_aquaponics_pre = 'aquaponics' in _farm_modality_pre

        if _is_aquaponics_pre:
            _aq_cycle_type = st.radio(
                "Cycle type",
                ["🐟 Fish cycle", "🌿 Plant cycle"], # Keep emojis in radio options
                horizontal=True,
                key=f"lc_aq_type_{active_farm['id']}",
            )
            if _aq_cycle_type == "🐟 Fish cycle":
                _lc_h_crop = st.selectbox(
                    "Fish Species",
                    list(FISH_SPECIES.keys()),
                    key=f"lc_fish_{active_farm['id']}",
                )
                _lc_is_fish = True
            else:
                _lc_h_crop = st.selectbox(
                    "Plant Crop",
                    list(GREENHOUSE_CROPS.keys()),
                    key=f"lc_plant_{active_farm['id']}",
                )
                _lc_is_fish = False
            st.session_state[f"_lc_crop_{active_farm['id']}"] = _lc_h_crop
            st.session_state[f"_lc_fish_{active_farm['id']}"] = _lc_is_fish
            st.markdown("---")

        with st.form(f"harvest_form_{active_farm['id']}"):
            st.markdown("**Core harvest data**")
            hf_col1, hf_col2 = st.columns(2)
            with hf_col1:
                if _lc_mode == "✅ Log completed harvest":
                    h_date = st.date_input("Harvest Date", value=date.today())
                else:
                    h_date = None
                    st.caption("No harvest date — cycle will remain open until closed in Active Cycles.")
                _farm_modality = active_farm.get('modality') or active_farm.get('agriculture_type') or 'vertical_farm'
                _farm_crop_source = active_farm.get('crop_source', 'greenhouse')
                _is_aquaponics = 'aquaponics' in _farm_modality
                if _farm_modality == 'vertical_farm':
                    _crop_options = list(CROPS.keys())
                    # If farm has a crop mix, surface those crops at the top of the list
                    _mix_raw = active_farm.get('crop_mix_json')
                    _farm_mix = []
                    if _mix_raw:
                        try:
                            _farm_mix = json.loads(_mix_raw) if isinstance(_mix_raw, str) else _mix_raw
                        except Exception:
                            _farm_mix = []
                    if _farm_mix:
                        _mix_crops = [row["crop"] for row in _farm_mix if row["crop"] in _crop_options]
                        _crop_options = _mix_crops + [c for c in _crop_options if c not in _mix_crops]
                    _crop_default = active_farm.get('crop', _crop_options[0])
                    _crop_idx = _crop_options.index(_crop_default) if _crop_default in _crop_options else 0
                elif _is_aquaponics:
                    pass
                elif _farm_crop_source == 'polytunnel':
                    _crop_options = list(POLYTUNNEL_CROPS.keys())
                    _crop_default = active_farm.get('crop', list(POLYTUNNEL_CROPS.keys())[0])
                    _crop_idx = _crop_options.index(_crop_default) if _crop_default in _crop_options else 0
                else:
                    _crop_options = list(GREENHOUSE_CROPS.keys())
                    _crop_default = active_farm.get('crop', list(GREENHOUSE_CROPS.keys())[0])
                    _crop_idx = _crop_options.index(_crop_default) if _crop_default in _crop_options else 0
                
                if _is_aquaponics:
                    _log_is_fish = st.session_state.get(f"_lc_fish_{active_farm['id']}", False)
                    h_crop = st.session_state.get(f"_lc_crop_{active_farm['id']}", "")
                else:
                    _crop_opts_clean = [o for o in _crop_options if not o.startswith("──")]
                    _crop_default_clean = _crop_default if _crop_default in _crop_opts_clean else _crop_opts_clean[0]
                    _crop_idx_clean = _crop_opts_clean.index(_crop_default_clean)
                    h_crop = st.selectbox(
                        "Species / Crop",
                        _crop_opts_clean,
                        index=_crop_idx_clean,
                        key=f"lc_crop_{active_farm['id']}_{_farm_modality}",
                    )
                    _log_is_fish = False
                # Load rack layout for this farm
                _ht_layout_racks = []
                _ht_layout_tanks = []
                try:
                    _ht_lr = supabase.table("farm_layouts").select(
                        "layout_json"
                    ).eq("farm_id", active_farm["id"]).eq("is_active", True).limit(1).execute()
                    if _ht_lr.data:
                        _ht_lj = _ht_lr.data[0].get("layout_json") or {}
                        if isinstance(_ht_lj, str):
                            import json as _json
                            _ht_lj = _json.loads(_ht_lj)
                        _ht_layout_racks = [
                            o for o in (_ht_lj.get("objects") or [])
                            if o.get("type") == "rack"
                        ]
                        _ht_layout_tanks = [
                            o for o in (_ht_lj.get("objects") or [])
                            if o.get("type") == "tank"
                        ]
                except Exception:
                    _ht_layout_racks = []
                    _ht_layout_tanks = []

                if _log_is_fish:
                    # Fish cycle — show tank selector
                    if _ht_layout_tanks:
                        _tank_options = ["— Free text —"] + [
                            f"{t['name']} (~{t.get('w',0)*t.get('h',0)*t.get('depth',1):.1f} m³)"
                            for t in _ht_layout_tanks
                        ]
                        _tank_sel = st.selectbox("Fish Tank", _tank_options,
                            key="ht_tank_sel",
                            help="Select a tank from your saved layout")
                        if _tank_sel == "— Free text —":
                            h_zone = st.text_input("Tank name (free text)", placeholder="e.g. TANK_1")
                            _ht_selected_rack = None
                        else:
                            h_zone = _tank_sel.split(" (~")[0]
                            _ht_selected_rack = None
                    else:
                        h_zone = st.text_input("Tank name", placeholder="e.g. TANK_1")
                        _ht_selected_rack = None
                elif _ht_layout_racks:
                    _rack_options = ["— Free text zone —"] + [
                        f"{r['name']} ({r.get('rackType','standard').upper()}, {r.get('layers',5)}L)"
                        for r in _ht_layout_racks
                    ]
                    _rack_sel = st.selectbox(
                        "Zone / Rack",
                        _rack_options,
                        key="ht_rack_sel",
                        help="Select a rack from your saved layout, or use free text",
                    )
                    if _rack_sel == "— Free text zone —":
                        h_zone = st.text_input("Zone (free text)", placeholder="e.g. Room A, Row 3")
                        _ht_selected_rack = None
                    else:
                        h_zone = _rack_sel.split(" (")[0]
                        _ht_selected_rack = next(
                            (r for r in _ht_layout_racks if r["name"] == h_zone), None
                        )
                else:
                    h_zone = st.text_input("Zone / Room (optional)", placeholder="e.g. RACK_1, Room A")
                    _ht_selected_rack = None
                h_kg         = st.number_input("kg Harvested", min_value=0.0, step=0.5, format="%.2f")
            with hf_col2:
                h_sale_price = st.number_input(
                    "Actual sale price ($/kg)", min_value=0.0, step=0.01, format="%.3f",
                    help="Leave 0 if not yet sold or unknown",
                )
                h_channel    = st.selectbox("Sales channel", ["— Not sold yet —"] + SALES_CHANNELS)
                h_rejection  = st.number_input(
                    "Rejection / waste at sale (%)", min_value=0.0, max_value=100.0, step=0.5,
                    help="% of harvested kg rejected or wasted at point of sale",
                )
                h_notes      = st.text_area("Notes (optional)")

            st.markdown("**Cycle details**")
            _lc_col1, _lc_col2 = st.columns(2)
            with _lc_col1:
                _seed_date_label = (
                    "Stocking date *" if (_log_is_fish and _lc_mode == "🌱 Open new cycle (seeding)")
                    else ("Seeding / transplant date *" if _lc_mode == "🌱 Open new cycle (seeding)"
                          else "Seeding / transplant date (optional)")
                )
                h_cycle_start = st.date_input(
                    _seed_date_label,
                    value=date.today() if _lc_mode == "🌱 Open new cycle (seeding)" else None,
                    help="When was stocking / seeding for this batch?",
                )
                if _log_is_fish:
                    h_area = st.number_input(
                        "Tank volume (m³)",
                        min_value=0.0, step=1.0, format="%.1f",
                        help="Total tank volume for this fish batch.",
                    )
                else:
                    # Compute already-allocated m² from open cycles
                    _farm_footprint = float(
                        active_farm.get("footprint") or
                        active_farm.get("plant_footprint") or 0
                    )
                    try:
                        _alloc_resp = (
                            supabase.table("harvest_logs")
                            .select("area_m2")
                            .eq("farm_id", active_farm["id"])
                            .in_("status", ["seeding", "growing", "ready"])
                            .execute()
                        )
                        _alloc_data = _alloc_resp.data or []
                        _allocated_m2 = sum(
                            float(r["area_m2"]) for r in _alloc_data
                            if r.get("area_m2")
                        )
                    except Exception:
                        _allocated_m2 = 0.0
                    _available_m2 = max(0.0, _farm_footprint - _allocated_m2)

                    h_area = st.number_input(
                        "Area planted (m²)",
                        min_value=0.0,
                        max_value=float(_farm_footprint) if _farm_footprint > 0 else None,
                        step=10.0,
                        format="%.1f",
                        help="How many m² does this cycle cover?",
                    )
                    if _farm_footprint > 0:
                        _avail_colour = (
                            "#2f5d3a" if _available_m2 > _farm_footprint * 0.3
                            else ("#c08a2e" if _available_m2 > 0 else "#b85c38")
                        )
                        st.markdown(
                            f'<div style="font-size:11px;margin-top:-8px;">'
                            f'Farm total: <b>{_farm_footprint:,.0f} m²</b> &nbsp;·&nbsp; '
                            f'In active cycles: <b>{_allocated_m2:,.0f} m²</b> &nbsp;·&nbsp; '
                            f'<span style="color:{_avail_colour};font-weight:700;">'
                            f'Available: {_available_m2:,.0f} m²</span></div>',
                            unsafe_allow_html=True,
                        )
            with _lc_col2:
                if _lc_mode == "🌱 Open new cycle (seeding)":
                    _lc_crop_days = None
                    if _log_is_fish:
                        _lc_crop_days = FISH_SPECIES.get(h_crop, {}).get("grow_cycle_days")
                    else:
                        _farm_mod = (active_farm.get("modality") or
                                     active_farm.get("agriculture_type") or "vertical_farm")
                        if _farm_mod == "vertical_farm" and h_crop in CROPS:
                            _lc_crop_days = CROPS[h_crop].get("cycle")
                        elif _farm_mod in ("greenhouse",) and h_crop in GREENHOUSE_CROPS:
                            _lc_crop_days = GREENHOUSE_CROPS[h_crop].get("cycle")
                        elif _farm_mod in ("polytunnel",) and h_crop in POLYTUNNEL_CROPS:
                            _lc_crop_days = POLYTUNNEL_CROPS[h_crop].get("cycle")
                        if not _lc_crop_days:
                            _lc_crop_days = (
                                CROPS.get(h_crop, {}).get("cycle")
                                or GREENHOUSE_CROPS.get(h_crop, {}).get("cycle")
                                or POLYTUNNEL_CROPS.get(h_crop, {}).get("cycle")
                            )
                    if _lc_crop_days and h_cycle_start:
                        _exp_harvest = h_cycle_start + timedelta(days=int(_lc_crop_days))
                        _cycle_label = "grow cycle" if _log_is_fish else "model cycle"
                        st.markdown(f"**Expected harvest:** {_exp_harvest}  \n"
                                    f"*(based on {_lc_crop_days}-day {_cycle_label})*")
                        if _log_is_fish:
                            _fs = FISH_SPECIES.get(h_crop, {})
                            st.caption(
                                f"🐟 Harvest weight: {_fs.get('harvest_weight_kg','?')} kg/fish · "
                                f"FCR: {_fs.get('feed_conversion_ratio','?')} · "
                                f"Density: {_fs.get('stocking_density','?')} kg/m³"
                            )
                    else:
                        st.caption("No cycle length found — harvest date left blank.")
                else:
                    # Harvest mode — no expected harvest date needed
                    if h_cycle_start and h_date and h_cycle_start > h_date:
                        st.warning("⚠️ Seeding date is after harvest date.")

            # ── Layer assignment (if a rack was selected) ──────────────
            _ht_layer_assignments = []
            if "_ht_selected_rack" in dir() and _ht_selected_rack:
                _n_layers = int(_ht_selected_rack.get("layers") or 1)
                _rack_type = _ht_selected_rack.get("rackType", "standard")
                st.markdown(f"**Layer assignment** — {h_zone} · {_n_layers} layers · {_rack_type.upper()}")
                if _rack_type == "tower":
                    st.caption("Tower rack — assign crop to whole tower (all nodes).")
                    _ht_layer_assignments = [{"layer": i, "selected": True} for i in range(_n_layers)]
                else:
                    _la_cols = st.columns(min(_n_layers, 6))
                    for _li in range(_n_layers):
                        with _la_cols[_li % min(_n_layers, 6)]:
                            _la_check = st.checkbox(
                                f"L{_li+1}",
                                value=True,
                                key=f"ht_layer_{_li}",
                                help=f"Layer {_li+1} of {h_zone}",
                            )
                            _ht_layer_assignments.append({"layer": _li, "selected": _la_check})
                _selected_layers = [a["layer"] for a in _ht_layer_assignments if a["selected"]]
                _area_per_layer = float(_ht_selected_rack.get("w", 0)) * float(_ht_selected_rack.get("h", 0))
                if _selected_layers and _area_per_layer > 0:
                    _total_assigned = _area_per_layer * len(_selected_layers)
                    st.caption(
                        f"✅ {len(_selected_layers)} layer(s) selected — "
                        f"~{_total_assigned:.1f} m² canopy area "
                        f"({_area_per_layer:.1f} m² × {len(_selected_layers)} layers)"
                    )

            _submit_label = (
                "🌱 Open Cycle" if _lc_mode == "🌱 Open new cycle (seeding)"
                else "✅ Log Harvest"
            )
            submitted = st.form_submit_button(_submit_label, use_container_width=True)

        if submitted:
            _is_open_cycle = (_lc_mode == "🌱 Open new cycle (seeding)")
            if not _is_open_cycle and h_kg <= 0:
                st.error("Please enter a kg amount greater than 0.")
            else:
                try:
                    _insert_data = {
                        "farm_id":          active_farm["id"],
                        "crop":             h_crop,
                        "zone":             h_zone or None,
                        "seeding_date":     str(h_cycle_start) if h_cycle_start else None,
                        "cycle_start_date": str(h_cycle_start) if h_cycle_start else None,
                        "area_m2":          h_area if h_area > 0 else None,
                        "notes":            h_notes or None,
                        "observations":     [],
                    }
                    if _is_open_cycle:
                        # date column is NOT NULL — use seeding date as placeholder.
                        # It will be overwritten with the actual harvest date when
                        # the cycle is closed via the Active Cycles tab.
                        _insert_data["status"] = "seeding"
                        _insert_data["date"]   = str(h_cycle_start) if h_cycle_start else str(date.today())
                        if _exp_harvest:
                            _insert_data["expected_harvest_date"] = str(_exp_harvest)
                        elif h_cycle_start and _lc_crop_days:
                            _insert_data["expected_harvest_date"] = str(
                                h_cycle_start + timedelta(days=int(_lc_crop_days))
                            )
                    else:
                        _insert_data.update({
                            "status":            "harvested",
                            "date":              str(h_date),
                            "cycle_end_date":    str(h_date),
                            "kg_harvested":      h_kg,
                            "sale_price_per_kg": h_sale_price if h_sale_price > 0 else None,
                            "sales_channel":     h_channel if h_channel != "— Not sold yet —" else None,
                            "waste_pct":         h_rejection if h_rejection > 0 else None,
                        })
                    _ins_resp = supabase.table("harvest_logs").insert(_insert_data).execute()
                    _new_cycle_id = _ins_resp.data[0]["id"] if _ins_resp.data else None

                    # Write rack layer assignments if layers were selected
                    if _new_cycle_id and "_ht_selected_rack" in dir() and _ht_selected_rack:
                        _sel_layers = [
                            a["layer"] for a in _ht_layer_assignments if a.get("selected") # Keep emoji in success message
                        ]
                        if _sel_layers:
                            _rack_area = float(_ht_selected_rack.get("w", 0)) * float(_ht_selected_rack.get("h", 0))
                            _assignment_rows = [
                                {
                                    "cycle_id":    _new_cycle_id,
                                    "farm_id":     active_farm["id"],
                                    "rack_name":   h_zone,
                                    "layer_index": _li,
                                    "area_m2":     _rack_area if _rack_area > 0 else None,
                                }
                                for _li in _sel_layers
                            ]
                            supabase.table("rack_layer_assignments").insert(_assignment_rows).execute()

                    if _is_open_cycle:
                        _layer_msg = ""
                        if "_ht_selected_rack" in dir() and _ht_selected_rack:
                            _n_sel = len([a for a in _ht_layer_assignments if a.get("selected")])
                            if _n_sel:
                                _layer_msg = f" Assigned to {_n_sel} layer(s) of {h_zone}."
                        st.success( # Keep emoji in success message
                            f"✅ Cycle opened: {h_crop} seeded on {h_cycle_start}.{_layer_msg} "
                            f"Track it in the **Active Cycles** tab."
                        )
                    else:
                        st.success(
                            f"✅ Harvest logged: {h_kg:.2f} kg of {h_crop} on {h_date}."
                        )
                except Exception as e:
                    st.error(str(e))

        st.divider()
        st.markdown("**Recent harvest entries**")
        try:
            recent_resp = (
                supabase.table("harvest_logs")
                .select("*")
                .eq("farm_id", active_farm["id"])
                .order("date", desc=True)
                .limit(20)
                .execute()
            )
            recent = recent_resp.data or []
        except Exception as e:
            st.error(f"Could not load recent entries: {e}")
            recent = []

        if not recent:
            st.info("No harvest entries yet for this farm.")
        else:
            for entry in recent:
                eid  = entry["id"]
                ekey = f"harvest_{eid}"
                with st.expander(
                    f"🌿 {entry.get('date','?')} — {entry.get('crop','?')} — "
                    f"{entry.get('kg_harvested','?')} kg"
                    + (f" @ ${entry['sale_price_per_kg']:.2f}/kg" if entry.get('sale_price_per_kg') else ""),
                    expanded=False,
                ):
                    if st.session_state.get(f"{ekey}_editing"):
                        with st.form(f"edit_harvest_{eid}"):
                            ec1, ec2 = st.columns(2)
                            with ec1:
                                ed_date  = st.date_input("Date",
                                    value=pd.to_datetime(entry["date"]).date())
                                ed_crop  = st.selectbox("Crop", list(CROPS.keys()),
                                    index=list(CROPS.keys()).index(entry["crop"]) if entry.get("crop") in CROPS else 0)
                                ed_zone  = st.text_input("Zone", value=entry.get("zone") or "")
                                ed_kg    = st.number_input("kg Harvested",
                                    value=float(entry.get("kg_harvested") or 0),
                                    min_value=0.0, step=0.5, format="%.2f")
                            with ec2:
                                ed_price = st.number_input("Sale price ($/kg)",
                                    value=float(entry.get("sale_price_per_kg") or 0),
                                    min_value=0.0, step=0.01, format="%.3f")
                                ed_chan  = st.selectbox("Sales channel",
                                    ["— Not sold yet —"] + SALES_CHANNELS,
                                    index=(["— Not sold yet —"] + SALES_CHANNELS).index(
                                        entry["sales_channel"]) if entry.get("sales_channel") in SALES_CHANNELS else 0)
                                ed_rej   = st.number_input("Rejection %",
                                    value=float(entry.get("rejection_rate_pct") or 0),
                                    min_value=0.0, max_value=100.0, step=0.5)
                                ed_notes = st.text_area("Notes", value=entry.get("notes") or "")
                            ed_cyc_start = st.date_input("Cycle start date",
                                value=pd.to_datetime(entry["cycle_start_date"]).date() if entry.get("cycle_start_date") else None)
                            if ed_cyc_start and ed_cyc_start > ed_date:
                                st.warning("⚠️ Cycle start is after harvest date.")
                            sv1, sv2 = st.columns(2)
                            save_edit   = sv1.form_submit_button("✅ Save changes", use_container_width=True)
                            cancel_edit = sv2.form_submit_button("✖ Cancel", use_container_width=True)

                        if save_edit:
                            try:
                                supabase.table("harvest_logs").update({
                                    "date":               str(ed_date),
                                    "crop":               ed_crop,
                                    "zone":               ed_zone or None,
                                    "kg_harvested":       ed_kg,
                                    "sale_price_per_kg":  ed_price if ed_price > 0 else None,
                                    "sales_channel":      ed_chan if ed_chan != "— Not sold yet —" else None,
                                    "rejection_rate_pct": ed_rej if ed_rej > 0 else None,
                                    "cycle_start_date":   str(ed_cyc_start) if ed_cyc_start else None,
                                    "cycle_end_date":     str(ed_date),
                                    "notes":              ed_notes or None,
                                }).eq("id", eid).execute()
                                st.session_state[f"{ekey}_editing"] = False
                                st.success("✅ Harvest entry updated.")
                                st.rerun()
                            except Exception as e:
                                st.error(f"Could not update: {e}")
                        if cancel_edit:
                            st.session_state[f"{ekey}_editing"] = False
                            st.rerun()
                    else:
                        vc1, vc2 = st.columns(2)
                        with vc1:
                            st.markdown(f"**Date:** {entry.get('date','—')}")
                            st.markdown(f"**Crop:** {entry.get('crop','—')}")
                            st.markdown(f"**Zone:** {entry.get('zone') or '—'}")
                            st.markdown(f"**kg Harvested:** {entry.get('kg_harvested','—')}")
                            st.markdown(f"**Cycle start:** {entry.get('cycle_start_date') or '—'}")
                        with vc2:
                            st.markdown(f"**Sale price:** {'$'+str(entry['sale_price_per_kg'])+'/kg' if entry.get('sale_price_per_kg') else '—'}")
                            st.markdown(f"**Channel:** {entry.get('sales_channel') or '—'}")
                            st.markdown(f"**Rejection %:** {entry.get('rejection_rate_pct') or '—'}")
                            st.markdown(f"**Notes:** {entry.get('notes') or '—'}")
                        act1, act2 = st.columns(2)
                        with act1:
                            if st.button("✏️ Edit", key=f"edit_h_{eid}", use_container_width=True):
                                st.session_state[f"{ekey}_editing"] = True
                                st.rerun()
                        with act2:
                            if not st.session_state.get(f"{ekey}_confirm_delete"):
                                if st.button("🗑️ Delete", key=f"del_h_{eid}", use_container_width=True):
                                    st.session_state[f"{ekey}_confirm_delete"] = True
                                    st.rerun()
                            else:
                                st.warning("Delete this harvest entry?")
                                dc1, dc2 = st.columns(2)
                                with dc1:
                                    if st.button("✅ Yes, delete", key=f"del_h_yes_{eid}", use_container_width=True):
                                        try:
                                            supabase.table("harvest_logs").delete().eq("id", eid).execute()
                                            st.session_state.pop(f"{ekey}_confirm_delete", None)
                                            st.success("Harvest entry deleted.")
                                            st.rerun()
                                        except Exception as e:
                                            st.error(f"Could not delete: {e}")
                                with dc2:
                                    if st.button("✖ Cancel", key=f"del_h_no_{eid}", use_container_width=True):
                                        st.session_state[f"{ekey}_confirm_delete"] = False
                                        st.rerun()

# ─────────────────────────────────────────────────────────────────────────────
# TAB 3 — Log Expense
# ─────────────────────────────────────────────────────────────────────────────
with tab3:
    st.subheader("Log Expense")
    active_farm = st.session_state.get("active_farm")

    if not active_farm:
        st.warning("Please select an active farm in the Farm Profiles tab first.")
    else:
        st.caption(f"Logging expenses for: **{active_farm['name']}**")

        if st.session_state.pop("ex_reset", False):
            for _k in ["ex_amount", "ex_supplier", "ex_notes"]:
                if _k in st.session_state:
                    del st.session_state[_k]

        # ── Supplier memory ───────────────────────────────────────────────────
        _meta = active_farm.get("metadata") or {}
        if isinstance(_meta, str):
            try:
                _meta = json.loads(_meta)
            except Exception:
                _meta = {}
        _supplier_map = _meta.get("supplier_category_map", {})

        # ── Expense entry form ────────────────────────────────────────────────
        st.markdown("### New Expense Entry")

        ex_col1, ex_col2 = st.columns([1, 2])
        with ex_col1:
            ex_date   = st.date_input("Date", value=date.today(), key="ex_date")
            ex_amount = st.number_input("Amount ($)", min_value=0.0, step=0.01,
                                        format="%.2f", key="ex_amount")

        with ex_col2:
            ex_supplier = st.text_input(
                "Supplier / source (optional)",
                key="ex_supplier",
                help="e.g. GreenPower GmbH, AgroSeeds Italia. Used to auto-suggest category next time.",
            )
            # Auto-suggest category from supplier memory
            _suggested_cat = None
            if ex_supplier and ex_supplier in _supplier_map:
                _suggested_cat = _supplier_map[ex_supplier]
                st.caption(f"💡 Last used category for **{ex_supplier}**: **{_suggested_cat}**")

            ex_notes = st.text_area("Notes (optional)", key="ex_notes", height=68)

        # Category button grid
        st.markdown("**Select category:**")
        if "ex_category" not in st.session_state:
            st.session_state["ex_category"] = _suggested_cat or "Other"

        btn_cols = st.columns(3)
        for i, (icon, cat) in enumerate(EXPENSE_CATEGORIES):
            col = btn_cols[i % 3]
            is_selected = st.session_state["ex_category"] == cat
            label = f"{icon} **{cat}**" if is_selected else f"{icon} {cat}" # Keep emoji in button
            btn_style = "primary" if is_selected else "secondary"
            if col.button(label, key=f"cat_btn_{cat}", use_container_width=True, type=btn_style):
                st.session_state["ex_category"] = cat
                st.rerun()

        selected_category = st.session_state["ex_category"]
        st.caption(f"Selected: **{selected_category}**")

        # Cycle assignment
        st.markdown("**Cycle assignment (optional)**")
        st.caption(
            "Leave blank to use automatic assignment (expense date determines cycle). "
            "Override only if this expense belongs to a different cycle."
        )

        # Fetch all cycles (open + closed) for this farm for expense linking
        try:
            cycles_resp = (
                supabase.table("harvest_logs")
                .select("id, date, crop, seeding_date, cycle_start_date, status")
                .eq("farm_id", active_farm["id"])
                .order("seeding_date", desc=True, nullsfirst=False)
                .limit(30)
                .execute()
            )
            cycles_data = cycles_resp.data or []
        except Exception:
            cycles_data = []

        cycle_options = ["— Auto-assign by date —"]
        cycle_id_map  = {}
        for c in cycles_data:
            _c_status = c.get("status", "harvested")
            _c_seed   = c.get("seeding_date") or c.get("cycle_start_date", "?")
            _c_icon   = "🌱" if _c_status in ("seeding","growing","ready") else "✅" # Keep emoji in label
            label = f"{_c_icon} {c.get('crop','?')} — {_c_seed} ({_c_status})"
            cycle_options.append(label)
            cycle_id_map[label] = c["id"]

        ex_cycle_label = st.selectbox("Assign to harvest cycle", cycle_options, key="ex_cycle_select")
        ex_cycle_id    = cycle_id_map.get(ex_cycle_label)

        st.divider()
        st.subheader("📅 Upcoming Harvests — Next 14 Days")
        # Keep emojis in calendar display
        _today_date = date.today()
        _14_days_from_now = _today_date + timedelta(days=14)
        _upcoming = []
        for _oc in _open_cycles:
            if _oc.get("status") in ["seeding", "growing"]:
                _exp_date_str = _oc.get("expected_harvest_date")
                if _exp_date_str:
                    try:
                        _exp_d = datetime.strptime(_exp_date_str, "%Y-%m-%d").date()
                        if _today_date <= _exp_d <= _14_days_from_now:
                            _upcoming.append(_oc)
                    except Exception:
                        pass
        
        if not _upcoming:
            st.info("No harvests expected in the next 14 days.")
        else:
            _cal_cols = st.columns(14)
            for i in range(14):
                _curr_date = _today_date + timedelta(days=i)
                _curr_date_str = _curr_date.strftime("%Y-%m-%d")
                with _cal_cols[i]:
                    st.markdown(
                        f"<div style='text-align:center;font-size:11px;font-weight:600;color:#7a807a;line-height:1.2;'>"
                        f"{_curr_date.strftime('%a')}<br>{_curr_date.strftime('%d/%m')}</div>",
                        unsafe_allow_html=True
                    )
                    _day_cycles = [c for c in _upcoming if c.get("expected_harvest_date") == _curr_date_str]
                    for _dc in _day_cycles:
                        _cname = _dc.get("crop", "Unknown")
                        _abbr = _cname[:8] + "." if len(_cname) > 8 else _cname
                        st.markdown(
                            f"<div style='text-align:center;font-size:10px;margin-top:4px;background:#e6ede4;color:#2f5d3a;padding:2px;border-radius:3px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;' title='{_cname}'>🟢 {_abbr}</div>",
                            unsafe_allow_html=True
                        )
            
            st.markdown("<br>", unsafe_allow_html=True)
            with st.expander("View harvest schedule detail"):
                _detail_data = []
                for _dc in _upcoming:
                    _crop = _dc.get("crop", "Unknown")
                    _area = _dc.get("area_m2") or 0
                    
                    _expected_kg = 0.0
                    if _area:
                        if _ac_modality == "vertical_farm" and _crop in CROPS:
                            _expected_kg = float(_area) * CROPS[_crop].get("yield", 0)
                        elif _ac_modality == "polytunnel" and _crop in POLYTUNNEL_CROPS:
                            _expected_kg = float(_area) * POLYTUNNEL_CROPS[_crop].get("yield", 0)
                        elif _crop in GREENHOUSE_CROPS:
                            _expected_kg = float(_area) * GREENHOUSE_CROPS[_crop].get("yield", 0)
                            
                    _detail_data.append({
                        "Expected Date": _dc.get("expected_harvest_date"),
                        "Rack": _dc.get("zone") or "—",
                        "Crop": _crop,
                        "Area (m²)": _area if _area else "—",
                        "Expected kg": round(_expected_kg, 1) if _expected_kg else "—"
                    })
                
                st.dataframe(pd.DataFrame(_detail_data), use_container_width=True, hide_index=True)

        st.divider()

        if st.button("💾 Save Expense", use_container_width=True, type="primary"):
            if ex_amount <= 0:
                st.error("Please enter an amount greater than 0.")
            else:
                try:
                    supabase.table("expense_logs").insert({
                        "farm_id":          active_farm["id"],
                        "date":             str(ex_date),
                        "amount":           ex_amount,
                        "category":         selected_category,
                        "supplier":         ex_supplier or None,
                        "notes":            ex_notes or None,
                        "harvest_log_id":   ex_cycle_id,
                    }).execute()

                    # Update supplier memory in farm metadata
                    if ex_supplier:
                        _supplier_map[ex_supplier] = selected_category
                        _meta["supplier_category_map"] = _supplier_map
                        supabase.table("farms").update(
                            {"metadata": json.dumps(_meta)}
                        ).eq("id", active_farm["id"]).execute()
                        # Update session state active farm metadata
                        _af = dict(active_farm)
                        _af["metadata"] = _meta
                        st.session_state["active_farm"] = _af

                    st.success(f"✅ Expense saved: **${ex_amount:.2f}** — {selected_category} on {ex_date}.")
                    st.session_state["ex_reset"] = True # Keep emoji in success message
                    st.rerun()
                except Exception as e:
                    st.error(f"Could not save expense: {e}")

        # ── Recent expenses ───────────────────────────────────────────────────
        st.divider()
        st.markdown("**Recent expense entries**")
        try:
            exp_resp = (
                supabase.table("expense_logs")
                .select("*")
                .eq("farm_id", active_farm["id"])
                .order("date", desc=True)
                .limit(30)
                .execute()
            )
            exp_data = exp_resp.data or []
        except Exception as e:
            st.error(f"Could not load expenses: {e}")
            exp_data = []

        if not exp_data:
            st.info("No expense entries yet.")
        else:
            for exp in exp_data:
                xid  = exp["id"]
                xkey = f"expense_{xid}"
                icon = next((i for i, c in EXPENSE_CATEGORIES if c == exp.get("category")), "📌")
                with st.expander(
                    f"{icon} {exp.get('date','?')} — {exp.get('category','?')} — "
                    f"${exp.get('amount',0):.2f}"
                    + (f" ({exp['supplier']})" if exp.get("supplier") else ""),
                    expanded=False,
                ):
                    if st.session_state.get(f"{xkey}_editing"):
                        # Fetch harvest cycles for re-assignment
                        try:
                            xedit_cycles_resp = (
                                supabase.table("harvest_logs")
                                .select("id, date, crop, cycle_start_date")
                                .eq("farm_id", active_farm["id"])
                                .order("date", desc=True)
                                .limit(30)
                                .execute()
                            )
                            xedit_cycles = xedit_cycles_resp.data or []
                        except Exception:
                            xedit_cycles = []

                        xedit_cycle_options = ["— Auto-assign by date —"]
                        xedit_cycle_id_map  = {}
                        for xc in xedit_cycles:
                            _lbl = (
                                f"{xc.get('crop','?')} — "
                                f"{xc.get('cycle_start_date') or xc.get('date','?')}"
                                f" (harvest {xc.get('date','?')})"
                            )
                            xedit_cycle_options.append(_lbl)
                            xedit_cycle_id_map[_lbl] = xc["id"]

                        # Find current assignment label if any
                        current_harvest_log_id = exp.get("harvest_log_id")
                        current_cycle_idx = 0
                        if current_harvest_log_id:
                            for _i, (_lbl, _id) in enumerate(xedit_cycle_id_map.items()):
                                if _id == current_harvest_log_id:
                                    current_cycle_idx = _i + 1  # +1 for the auto-assign option
                                    break

                        with st.form(f"edit_expense_{xid}"):
                            xc1, xc2 = st.columns(2)
                            with xc1:
                                xd_date     = st.date_input("Date",
                                    value=pd.to_datetime(exp["date"]).date())
                                xd_amount   = st.number_input("Amount ($)",
                                    value=float(exp.get("amount") or 0),
                                    min_value=0.0, step=0.01, format="%.2f")
                                xd_supplier = st.text_input("Supplier",
                                    value=exp.get("supplier") or "")
                            with xc2:
                                xd_notes = st.text_area("Notes",
                                    value=exp.get("notes") or "")
                                xd_cat   = st.selectbox("Category",
                                    [c for _, c in EXPENSE_CATEGORIES],
                                    index=[c for _, c in EXPENSE_CATEGORIES].index(
                                        exp["category"]) if exp.get("category") in [c for _, c in EXPENSE_CATEGORIES] else 0)

                            xd_cycle_label = st.selectbox(
                                "Assign to harvest cycle",
                                options=xedit_cycle_options,
                                index=current_cycle_idx,
                                help="Change which harvest cycle this expense is linked to, or leave as auto-assign.",
                            )
                            xd_cycle_id = xedit_cycle_id_map.get(xd_cycle_label)

                            xs1, xs2     = st.columns(2)
                            save_xedit   = xs1.form_submit_button("✅ Save changes", use_container_width=True)
                            cancel_xedit = xs2.form_submit_button("✖ Cancel", use_container_width=True)

                        if save_xedit:
                            try:
                                supabase.table("expense_logs").update({
                                    "date":           str(xd_date),
                                    "amount":         xd_amount,
                                    "category":       xd_cat,
                                    "supplier":       xd_supplier or None,
                                    "notes":          xd_notes or None,
                                    "harvest_log_id": xd_cycle_id,
                                }).eq("id", xid).execute()
                                st.session_state[f"{xkey}_editing"] = False
                                st.success("✅ Expense updated.")
                                st.rerun()
                            except Exception as e:
                                st.error(f"Could not update: {e}")
                        if cancel_xedit:
                            st.session_state[f"{xkey}_editing"] = False
                            st.rerun()
                    else:
                        xv1, xv2 = st.columns(2)
                        with xv1:
                            st.markdown(f"**Date:** {exp.get('date','—')}")
                            st.markdown(f"**Amount:** ${exp.get('amount',0):.2f}")
                            st.markdown(f"**Category:** {icon} {exp.get('category','—')}")
                        with xv2:
                            st.markdown(f"**Supplier:** {exp.get('supplier') or '—'}")
                            st.markdown(f"**Notes:** {exp.get('notes') or '—'}")
                        xa1, xa2 = st.columns(2)
                        with xa1:
                            if st.button("✏️ Edit", key=f"edit_x_{xid}", use_container_width=True):
                                st.session_state[f"{xkey}_editing"] = True
                                st.rerun()
                        with xa2:
                            if not st.session_state.get(f"{xkey}_confirm_delete"):
                                if st.button("🗑️ Delete", key=f"del_x_{xid}", use_container_width=True):
                                    st.session_state[f"{xkey}_confirm_delete"] = True
                                    st.rerun()
                            else:
                                st.warning("Delete this expense entry?")
                                xdc1, xdc2 = st.columns(2)
                                with xdc1:
                                    if st.button("✅ Yes, delete", key=f"del_x_yes_{xid}", use_container_width=True):
                                        try:
                                            supabase.table("expense_logs").delete().eq("id", xid).execute()
                                            st.session_state.pop(f"{xkey}_confirm_delete", None)
                                            st.success("Expense deleted.")
                                            st.rerun()
                                        except Exception as e:
                                            st.error(f"Could not delete: {e}")
                                with xdc2:
                                    if st.button("✖ Cancel", key=f"del_x_no_{xid}", use_container_width=True):
                                        st.session_state[f"{xkey}_confirm_delete"] = False
                                        st.rerun()

        # ── Energy meter readings ─────────────────────────────────────────────
        st.divider()
        st.markdown("### Log Energy Meter Reading")
        st.caption(
            "Optional but powerful — weekly meter readings give much more granular "
            "energy tracking than monthly invoices. Readings are used in the Forecast tab "
            "to compute actual energy cost per kWh."
        )

        with st.form("meter_form"):
            mc1, mc2 = st.columns(2)
            with mc1:
                m_date    = st.date_input("Reading date", value=date.today())
                m_reading = st.number_input("Meter reading (kWh)", min_value=0.0, step=1.0, format="%.1f")
            with mc2:
                m_notes   = st.text_area("Notes (optional)", height=68)
            meter_submitted = st.form_submit_button("Log Meter Reading", use_container_width=True)

        if meter_submitted:
            if m_reading <= 0:
                st.error("Please enter a reading greater than 0.")
            else:
                try:
                    supabase.table("energy_meter_logs").insert({
                        "farm_id":     active_farm["id"],
                        "date":        str(m_date),
                        "reading_kwh": m_reading,
                        "notes":       m_notes or None,
                    }).execute()
                    st.success(f"✅ Meter reading logged: {m_reading:.1f} kWh on {m_date}.")
                except Exception as e:
                    st.error(f"Could not save meter reading: {e}")

        # Recent meter readings
        try:
            meter_resp = (
                supabase.table("energy_meter_logs")
                .select("*")
                .eq("farm_id", active_farm["id"])
                .order("date", desc=True)
                .limit(10)
                .execute()
            )
            meter_data = meter_resp.data or []
            if meter_data:
                mdf = pd.DataFrame(meter_data)[["date","reading_kwh","notes"]]
                mdf.columns = ["Date","Reading (kWh)","Notes"]
                st.dataframe(mdf, use_container_width=True, hide_index=True)
        except Exception:
            pass

# ─────────────────────────────────────────────────────────────────────────────
# TAB 4 — Dashboard
# ─────────────────────────────────────────────────────────────────────────────
with tab4:
    st.subheader("Operational Dashboard")
    active_farm = st.session_state.get("active_farm")

    if not active_farm:
        st.warning("Please select an active farm in the Farm Profiles tab first.")
    else:
        # ── Load all data ─────────────────────────────────────────────────────
        try:
            hl_resp = supabase.table("harvest_logs").select("*").eq("farm_id", active_farm["id"]).order("date").execute()
            harvest_logs = hl_resp.data or []
        except Exception as e:
            st.error(f"Could not load harvest data: {e}")
            harvest_logs = []

        try:
            el_resp = supabase.table("expense_logs").select("*").eq("farm_id", active_farm["id"]).order("date").execute()
            expense_logs = el_resp.data or []
        except Exception as e:
            st.error(f"Could not load expense data: {e}")
            expense_logs = []

        if not harvest_logs and not expense_logs:
            st.info("Log some harvests and expenses first — then this dashboard will build your actual vs model P&L.")
        else:
            # ── Parse model snapshot ──────────────────────────────────────────
            snapshot_raw = active_farm.get("model_snapshot")
            model = None
            if snapshot_raw:
                try:
                    model = json.loads(snapshot_raw) if isinstance(snapshot_raw, str) else snapshot_raw
                except Exception:
                    model = None

            model_monthly = None
            if model:
                model_monthly = {
                    "revenue":     model.get("annual_revenue", 0) / 12,
                    "energy":      model.get("annual_energy_cost", 0) / 12,
                    "labour":      model.get("annual_labour_cost", 0) / 12,
                    "variable":    model.get("annual_variable_cost", 0) / 12,
                    "water":       model.get("annual_water_cost", 0) / 12,
                    "maintenance": model.get("annual_maintenance", 0) / 12,
                    "rent":        model.get("annual_rent", 0) / 12,
                    "total_costs": model.get("total_annual_costs", 0) / 12,
                    "ebitda":      model.get("ebitda", 0) / 12,
                }

            # ── Build monthly actuals ─────────────────────────────────────────
            df_h = pd.DataFrame(harvest_logs) if harvest_logs else pd.DataFrame()
            df_e = pd.DataFrame(expense_logs) if expense_logs else pd.DataFrame()

            if not df_h.empty:
                df_h["date"] = pd.to_datetime(df_h["date"])
                df_h["month"] = df_h["date"].dt.to_period("M")
                df_h["kg_harvested"] = pd.to_numeric(df_h["kg_harvested"], errors="coerce").fillna(0)
                df_h["sale_price_per_kg"] = pd.to_numeric(df_h["sale_price_per_kg"], errors="coerce").fillna(0)
                df_h["revenue"] = df_h["kg_harvested"] * df_h["sale_price_per_kg"]

            if not df_e.empty:
                df_e["date"] = pd.to_datetime(df_e["date"])
                df_e["month"] = df_e["date"].dt.to_period("M")
                df_e["amount"] = pd.to_numeric(df_e["amount"], errors="coerce").fillna(0)

            # Determine all months in range
            all_months = set()
            if not df_h.empty:
                all_months.update(df_h["month"].unique())
            if not df_e.empty:
                all_months.update(df_e["month"].unique())
            all_months = sorted(all_months)

            # Build monthly summary rows
            monthly_rows = []
            for m in all_months:
                row = {"Month": str(m)}

                # Revenue
                if not df_h.empty:
                    mh = df_h[df_h["month"] == m]
                    row["Actual kg"]       = mh["kg_harvested"].sum()
                    row["Actual Revenue"]  = mh["revenue"].sum()
                    row["Harvests"]        = len(mh)
                else:
                    row["Actual kg"]      = 0
                    row["Actual Revenue"] = 0
                    row["Harvests"]       = 0

                # Expenses by category
                cat_map = {c: 0.0 for _, c in EXPENSE_CATEGORIES}
                if not df_e.empty:
                    me = df_e[df_e["month"] == m]
                    for _, c in EXPENSE_CATEGORIES:
                        cat_map[c] = me[me["category"] == c]["amount"].sum()

                row["Energy"]      = cat_map["Energy"]
                row["Seeds"]       = cat_map["Seeds"]
                row["Substrate"]   = cat_map["Substrate"]
                row["Nutrients"]   = cat_map["Nutrients"]
                row["Packaging"]   = cat_map["Packaging"]
                row["Labour"]      = cat_map["Labour"]
                row["Maintenance"] = cat_map["Maintenance"]
                row["Rent"]        = cat_map["Rent"]
                row["Other"]       = cat_map["Other"]
                row["Total Costs"] = sum(cat_map.values())
                row["EBITDA"]      = row["Actual Revenue"] - row["Total Costs"]

                if model_monthly:
                    row["Model Revenue"]     = model_monthly["revenue"]
                    row["Model Costs"]       = model_monthly["total_costs"]
                    row["Model EBITDA"]      = model_monthly["ebitda"]
                    row["Revenue Variance"]  = row["Actual Revenue"] - model_monthly["revenue"]
                    row["EBITDA Variance"]   = row["EBITDA"] - model_monthly["ebitda"]

                monthly_rows.append(row)

            df_monthly = pd.DataFrame(monthly_rows)

            # ── Summary KPIs ──────────────────────────────────────────────────
            total_actual_revenue = df_monthly["Actual Revenue"].sum()
            total_actual_costs   = df_monthly["Total Costs"].sum()
            total_actual_ebitda  = total_actual_revenue - total_actual_costs
            total_actual_kg      = df_monthly["Actual kg"].sum()

            k1, k2, k3, k4 = st.columns(4)
            k1.metric("Total Revenue (actual)",    f"${total_actual_revenue:,.0f}")
            k2.metric("Total Costs (actual)",      f"${total_actual_costs:,.0f}")
            k3.metric("EBITDA (actual)",            f"${total_actual_ebitda:,.0f}")
            k4.metric("Total kg Harvested",         f"{total_actual_kg:,.1f} kg")

            if model_monthly and len(all_months) > 0:
                n_months = len(all_months)
                model_rev_total  = model_monthly["revenue"] * n_months
                model_cost_total = model_monthly["total_costs"] * n_months
                model_ebitda_tot = model_monthly["ebitda"] * n_months
                rev_var_pct  = (total_actual_revenue - model_rev_total) / model_rev_total * 100 if model_rev_total else 0
                cost_var_pct = (total_actual_costs   - model_cost_total) / model_cost_total * 100 if model_cost_total else 0
                ebitda_var_pct = (total_actual_ebitda - model_ebitda_tot) / abs(model_ebitda_tot) * 100 if model_ebitda_tot else 0

                k5, k6, k7 = st.columns(3)
                k5.metric("Revenue vs Model",
                    f"${total_actual_revenue:,.0f}",
                    delta=f"{rev_var_pct:+.1f}% vs model ${model_rev_total:,.0f}",
                    delta_color="normal")
                k6.metric("Costs vs Model",
                    f"${total_actual_costs:,.0f}",
                    delta=f"{cost_var_pct:+.1f}% vs model ${model_cost_total:,.0f}",
                    delta_color="inverse")
                k7.metric("EBITDA vs Model",
                    f"${total_actual_ebitda:,.0f}",
                    delta=f"{ebitda_var_pct:+.1f}% vs model ${model_ebitda_tot:,.0f}",
                    delta_color="normal")

            st.divider()

            # ── Monthly P&L chart ─────────────────────────────────────────────
            st.markdown("#### Monthly P&L — Actual vs Model")
            fig_pl = go.Figure()

            fig_pl.add_trace(go.Bar(
                name="Actual Revenue",
                x=df_monthly["Month"],
                y=df_monthly["Actual Revenue"],
                marker_color="rgba(0,229,160,0.8)",
            ))
            fig_pl.add_trace(go.Bar(
                name="Actual Costs",
                x=df_monthly["Month"],
                y=-df_monthly["Total Costs"],
                marker_color="rgba(255,77,77,0.7)",
            ))
            fig_pl.add_trace(go.Scatter(
                name="Actual EBITDA",
                x=df_monthly["Month"],
                y=df_monthly["EBITDA"],
                mode="lines+markers",
                line=dict(color="#ffc13d", width=2),
                marker=dict(size=7),
            ))
            if model_monthly:
                fig_pl.add_hline(
                    y=model_monthly["revenue"],
                    line_dash="dash", line_color="rgba(0,229,160,0.4)",
                    annotation_text="Model revenue/mo",
                    annotation_position="right",
                    annotation_font_color="rgba(0,229,160,0.6)",
                )
                fig_pl.add_hline(
                    y=model_monthly["ebitda"],
                    line_dash="dash", line_color="rgba(255,193,61,0.4)",
                    annotation_text="Model EBITDA/mo",
                    annotation_position="right",
                    annotation_font_color="rgba(255,193,61,0.6)",
                )

            fig_pl.update_layout(
                barmode="relative",
                plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
                font_color="#e8ecf0", height=380,
                xaxis=dict(showgrid=False),
                yaxis=dict(showgrid=False, title="$"),
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
                margin=dict(t=30, b=20),
            )
            style_fig(fig_pl)
            st.plotly_chart(fig_pl, use_container_width=True)

            # ── Cost breakdown chart ──────────────────────────────────────────
            st.divider()
            st.markdown("#### Cost Breakdown by Category")
            cost_cats = ["Energy","Seeds","Substrate","Nutrients","Packaging","Labour","Maintenance","Rent","Other"]
            cat_colors = ["#ff4d4d","#00e5a0","#8B5A2B","#4fc3f7","#ffa726","#ffc13d","#ab47bc","#26c6da","#969696"]

            fig_costs = go.Figure()
            for cat, color in zip(cost_cats, cat_colors):
                if cat in df_monthly.columns:
                    fig_costs.add_trace(go.Bar(
                        name=cat, x=df_monthly["Month"], y=df_monthly[cat],
                        marker_color=color,
                    ))
            fig_costs.update_layout(
                barmode="stack",
                plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
                font_color="#e8ecf0", height=320,
                xaxis=dict(showgrid=False),
                yaxis=dict(showgrid=False, title="$ Costs"),
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
                margin=dict(t=30, b=20),
            )
            style_fig(fig_costs)
            st.plotly_chart(fig_costs, use_container_width=True)

            # ── Deviation metrics ─────────────────────────────────────────────
            if model:
                st.divider()
                st.markdown("#### Key Deviations from Model")

                # Energy deviation
                actual_energy_total = df_monthly["Energy"].sum()
                model_energy_total  = (model.get("annual_energy_cost", 0) / 12) * len(all_months)
                energy_dev = (actual_energy_total - model_energy_total) / model_energy_total * 100 if model_energy_total else 0

                # Yield deviation
                if not df_h.empty and model:
                    model_cycles_per_year = model.get("cycles_per_year", 1)
                    model_ega             = model.get("effective_grow_area", 1)
                    model_yield_per_cycle = model.get("total_annual_kg", 0) / max(model_cycles_per_year, 1) / max(model_ega, 1)
                    actual_harvests       = df_h.copy()
                    actual_avg_kg_per_harvest = actual_harvests["kg_harvested"].mean() if not actual_harvests.empty else 0
                    actual_yield_per_m2  = actual_avg_kg_per_harvest / max(model_ega, 1)
                    yield_dev = (actual_yield_per_m2 - model_yield_per_cycle) / model_yield_per_cycle * 100 if model_yield_per_cycle else 0
                else:
                    yield_dev = 0

                # Revenue per kg deviation
                if not df_h.empty:
                    priced = df_h[df_h["sale_price_per_kg"].notna() & (df_h["sale_price_per_kg"] > 0)]
                    actual_avg_price = priced["sale_price_per_kg"].mean() if not priced.empty else 0
                    model_price      = model.get("effective_price", 0)
                    price_dev = (actual_avg_price - model_price) / model_price * 100 if model_price and actual_avg_price else 0
                else:
                    price_dev = 0

                d1, d2, d3 = st.columns(3)
                d1.metric( # Keep delta color
                    "Energy Cost vs Model",
                    f"${actual_energy_total:,.0f}",
                    delta=f"{energy_dev:+.1f}%",
                    delta_color="inverse",
                    help="Actual energy spend vs model prediction for this period. Red = over budget."
                )
                d2.metric( # Keep delta color
                    f"{actual_avg_kg_per_harvest:.1f} kg/harvest" if not df_h.empty else "N/A",
                    delta=f"{yield_dev:+.1f}% per m²/cycle" if not df_h.empty else None,
                    delta_color="normal",
                    help="Average kg per harvest vs model assumption per cycle."
                )
                d3.metric( # Keep delta color
                    f"${actual_avg_price:.2f}/kg" if not df_h.empty and actual_avg_price > 0 else "No sales logged",
                    delta=f"{price_dev:+.1f}% vs model ${model_price:.2f}/kg" if model_price and actual_avg_price else None,
                    delta_color="normal",
                    help="Average actual sale price vs model assumption."
                )

            # ── Harvest cycle table ───────────────────────────────────────────
            st.divider()
            st.markdown("#### Harvest Cycle Performance")
            if not df_h.empty:
                cycles_with_dates = df_h[df_h["cycle_start_date"].notna()].copy() if "cycle_start_date" in df_h.columns else pd.DataFrame()
                if not cycles_with_dates.empty:
                    cycles_with_dates["cycle_start_date"] = pd.to_datetime(cycles_with_dates["cycle_start_date"])
                    cycles_with_dates["cycle_length_days"] = (
                        cycles_with_dates["date"] - cycles_with_dates["cycle_start_date"]
                    ).dt.days

                    model_cycle_days = model.get("effective_cycle_days") if model else None

                    cycle_display = cycles_with_dates[[
                        "date","crop","zone","kg_harvested","sale_price_per_kg",
                        "rejection_rate_pct","cycle_start_date","cycle_length_days"
                    ]].copy()
                    cycle_display.columns = [
                        "Harvest Date","Crop","Zone","kg","$/kg","Rejection %",
                        "Cycle Start","Cycle Days"
                    ]
                    cycle_display["Revenue"] = cycle_display["kg"] * cycle_display["$/kg"].fillna(0)

                    if model_cycle_days:
                        cycle_display["vs Model (days)"] = cycle_display["Cycle Days"] - model_cycle_days

                    st.dataframe(cycle_display, use_container_width=True, hide_index=True)

                    if model_cycle_days:
                        avg_actual_days = cycles_with_dates["cycle_length_days"].mean()
                        st.caption(
                            f"Model assumes **{model_cycle_days} days/cycle**. "
                            f"Your actual average: **{avg_actual_days:.1f} days**. "
                            + ("✅ On track." if abs(avg_actual_days - model_cycle_days) <= 2
                               else f"⚠️ Running **{avg_actual_days - model_cycle_days:+.1f} days** vs model — "
                               + ("this reduces annual cycles." if avg_actual_days > model_cycle_days else "cycles are faster than modelled."))
                        )
                else:
                    st.caption("Add cycle start dates when logging harvests to see per-cycle performance.")

            # ── Monthly P&L table ─────────────────────────────────────────────
            st.divider()
            st.markdown("#### Monthly Detail Table")
            view_cols = ["Month","Actual Revenue","Total Costs","EBITDA","Actual kg","Harvests"]
            if model_monthly:
                view_cols += ["Model Revenue","Model Costs","Model EBITDA","Revenue Variance","EBITDA Variance"]

            display_monthly = df_monthly[[c for c in view_cols if c in df_monthly.columns]].copy()

            def highlight_variance(row):
                styles = [""] * len(row)
                if "EBITDA Variance" in row.index:
                    idx = list(row.index).index("EBITDA Variance")
                    styles[idx] = severity_cell(row["EBITDA Variance"], hi=0, mid=-1, reverse=True)
                return styles

            st.dataframe(
                display_monthly.style.apply(highlight_variance, axis=1).format({
                    c: "${:,.0f}" for c in display_monthly.columns if c not in ("Month","Actual kg","Harvests")
                }),
                use_container_width=True, hide_index=True,
            )

            # Export
            csv_dash = df_monthly.to_csv(index=False)
            st.download_button(
                "⬇️ Export monthly P&L",
                csv_dash,
                f"pl_{active_farm['name'].replace(' ','_')}.csv",
                "text/csv",
            )

# ─────────────────────────────────────────────────────────────────────────────
# TAB 5 — Forecast & Financials
# ─────────────────────────────────────────────────────────────────────────────
with tab5:
    st.subheader("Forecast & Financials")
    active_farm = st.session_state.get("active_farm")

    if not active_farm:
        st.warning("Please select an active farm in the Farm Profiles tab first.")
    else:
        # ── Load data ─────────────────────────────────────────────────────────
        try:
            hl_resp2 = supabase.table("harvest_logs").select("*").eq("farm_id", active_farm["id"]).order("date").execute()
            harvest_logs2 = hl_resp2.data or []
        except Exception:
            harvest_logs2 = []

        try:
            el_resp2 = supabase.table("expense_logs").select("*").eq("farm_id", active_farm["id"]).order("date").execute()
            expense_logs2 = el_resp2.data or []
        except Exception:
            expense_logs2 = []

        try:
            ml_resp = supabase.table("energy_meter_logs").select("*").eq("farm_id", active_farm["id"]).order("date").execute()
            meter_logs = ml_resp.data or []
        except Exception:
            meter_logs = []

        # ── Parse model snapshot ──────────────────────────────────────────────
        snapshot_raw2 = active_farm.get("model_snapshot")
        model2 = None
        if snapshot_raw2:
            try:
                model2 = json.loads(snapshot_raw2) if isinstance(snapshot_raw2, str) else snapshot_raw2
            except Exception:
                model2 = None

        if not model2:
            st.warning(
                "⚠️ No model snapshot found for this farm. "
                "A snapshot is the baseline financial model that your actuals will be compared against."
            )

            # Check whether the farm has enough parameters to generate a snapshot
            _has_params = all([
                active_farm.get("country"),
                active_farm.get("crop"),
                active_farm.get("footprint"),
                active_farm.get("levels"),
            ])

            if not _has_params:
                st.error(
                    "This farm profile was created from the map and has no financial parameters. "
                    "Go to the ROI Calculator, load this farm, fill in all parameters, "
                    "and click **Save as Farm Profile** to generate a baseline."
                )
            else:
                st.info(
                    "This farm has saved parameters. Click the button below to generate a "
                    "baseline model snapshot from them now — no need to go to the ROI Calculator."
                ) # Keep emoji in button
                if st.button("⚡ Generate Model Snapshot Now", type="primary", use_container_width=False):
                    from core.roi_calculate import calculate as _calc
                    _snap_inputs = {
                        "country":            active_farm.get("country", "Germany"),
                        "crop":               active_farm.get("crop", "Lettuce (Butterhead)"),
                        "footprint":          float(active_farm.get("footprint") or 1000),
                        "levels":             int(active_farm.get("levels") or 5),
                        "lights_tier":        active_farm.get("lights_tier") or "Basic",
                        "hvac":               active_farm.get("hvac") or "Standard",
                        "automation":         active_farm.get("automation") or "Medium",
                        "price_scenario":     active_farm.get("price_scenario") or "base",
                        "price_override":     float(active_farm.get("price_override") or 0),
                        "packaging_cost":     float(active_farm.get("packaging_cost") or 0.15),
                        "loss_rate":          float(active_farm.get("loss_rate") or 5),
                        "net_grow_factor":    float(active_farm.get("net_grow_factor") or 85),
                        "walkways_factor":    float(active_farm.get("walkways_factor") or 15),
                        "water_price":        float(active_farm.get("water_price") or 2),
                        "rent_monthly":       float(active_farm.get("rent_monthly") or 0),
                        "real_estate_capex":  float(active_farm.get("real_estate_capex") or 0),
                        "harvest_mode":       active_farm.get("harvest_mode") or "Single",
                        "depreciation_years": int(active_farm.get("depreciation_years") or 10),
                        "tax_rate":           float(active_farm.get("tax_rate") or 25),
                        "ltv":                float(active_farm.get("ltv") or 60),
                        "interest_rate":      float(active_farm.get("interest_rate") or 5.5),
                        "loan_term_years":    int(active_farm.get("loan_term_years") or 10),
                    }
                    try:
                        _snap_result = _calc(_snap_inputs)
                        _snap_json   = json.dumps(_snap_result)
                        _snap_time   = date.today().isoformat()
                        supabase.table("farms").update({
                            "model_snapshot":   _snap_json,
                            "model_updated_at": _snap_time,
                        }).eq("id", active_farm["id"]).execute()
                        # Update session state so the page refreshes with the new snapshot
                        _af2 = dict(active_farm)
                        _af2["model_snapshot"]   = _snap_json
                        _af2["model_updated_at"] = _snap_time
                        st.session_state["active_farm"] = _af2
                        st.success("✅ Model snapshot generated and saved. The forecast is now available.")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Could not generate snapshot: {e}")
        else:
            df_h2 = pd.DataFrame(harvest_logs2) if harvest_logs2 else pd.DataFrame()
            df_e2 = pd.DataFrame(expense_logs2) if expense_logs2 else pd.DataFrame()

            if not df_h2.empty:
                df_h2["date"] = pd.to_datetime(df_h2["date"], errors="coerce")
                df_h2["kg_harvested"] = pd.to_numeric(df_h2["kg_harvested"], errors="coerce").fillna(0)
                df_h2["sale_price_per_kg"] = pd.to_numeric(df_h2["sale_price_per_kg"], errors="coerce").fillna(0)
            if not df_e2.empty:
                df_e2["date"] = pd.to_datetime(df_e2["date"], errors="coerce")
                df_e2["amount"] = pd.to_numeric(df_e2["amount"], errors="coerce").fillna(0)

            # ── Confidence level ──────────────────────────────────────────────
            n_harvest_cycles = len(df_h2) if not df_h2.empty else 0
            n_months_data    = 0
            if not df_h2.empty or not df_e2.empty:
                all_dates = []
                if not df_h2.empty: all_dates += df_h2["date"].dropna().tolist()
                if not df_e2.empty: all_dates += df_e2["date"].dropna().tolist()
                if all_dates:
                    span = (max(all_dates) - min(all_dates)).days
                    n_months_data = max(1, round(span / 30))

            if n_harvest_cycles < 2 or n_months_data < 2:
                confidence = "🔴 Very Low"
                conf_color = "#ff4d4d"
                conf_note  = "Less than 2 harvest cycles or 2 months of data. Forecast is based on almost no real data — treat as illustrative only."
            elif n_months_data < 2:
                confidence = "🔴 Low"
                conf_color = "#ff4d4d"
                conf_note  = f"Based on {n_harvest_cycles} harvest(s) across {n_months_data} month(s). Projections have low reliability."
            elif n_months_data < 6:
                confidence = "🟡 Medium"
                conf_color = "#ffc13d"
                conf_note  = f"Based on {n_harvest_cycles} harvests across {n_months_data} months. Reasonable for directional planning, not investment decisions."
            else:
                confidence = "🟢 High"
                conf_color = "#00e5a0"
                conf_note  = f"Based on {n_harvest_cycles} harvests across {n_months_data} months. Sufficient data for reliable re-projection."

            st.markdown(
                f"""<div style="background:#1a1a2e;border-radius:8px;padding:12px 16px;margin-bottom:16px;">
                <span style="font-size:14px;font-weight:bold;color:{conf_color};">
                Forecast Confidence: {confidence}</span>
                <span style="font-size:12px;color:#8892a0;margin-left:12px;">{conf_note}</span>
                </div>""",
                unsafe_allow_html=True,
            )

            # ── Compute actual averages for re-projection ─────────────────────
            # Average yield per cycle per m² (vs model assumption)
            model_ega2          = model2.get("effective_grow_area", 1)
            model_cycles2       = model2.get("cycles_per_year", 1)
            model_yield_total   = model2.get("total_annual_kg", 0)
            model_yield_cycle   = model_yield_total / max(model_cycles2, 1)
            model_price2        = model2.get("effective_price", 0)
            model_energy_annual = model2.get("annual_energy_cost", 0)
            model_kwh_annual    = model2.get("total_annual_kwh", 0)
            model_kwh_price     = model2.get("annual_energy_cost", 0) / max(model_kwh_annual, 1)

            actual_avg_yield_per_cycle = None
            actual_avg_price2          = None
            actual_energy_kwh_price    = None
            actual_energy_monthly      = None

            if not df_h2.empty:
                actual_avg_yield_per_cycle = df_h2["kg_harvested"].mean()
                priced2 = df_h2[df_h2["sale_price_per_kg"].notna() & (df_h2["sale_price_per_kg"] > 0)]
                if not priced2.empty:
                    actual_avg_price2 = priced2["sale_price_per_kg"].mean()

            # ── Energy input — three-tier hierarchy ──────────────────────────
            # Tier 1: meter readings (most reliable — actual kWh measured)
            # Tier 2: manual monthly override entered by farmer
            # Tier 3: derived from expense logs with farmer-chosen mode
            # The first available tier wins.

            st.divider()
            st.markdown("#### ⚡ Energy Cost Input for Re-Projection")

            # Manual override — always shown, always takes priority over expense logs
            energy_override = st.number_input(
                "Manual monthly energy cost override ($/month)",
                min_value=0.0, step=10.0, value=0.0, format="%.2f",
                key="forecast_energy_override",
                help=(
                    "If you know your average monthly energy cost, enter it here. "
                    "This overrides the expense log derivation. Leave 0 to use expense logs or meter readings."
                ),
            )

            # Data completeness mode — only relevant when using expense logs
            energy_expenses_all = df_e2[df_e2["category"] == "Energy"].copy() if not df_e2.empty else pd.DataFrame()
            has_energy_expenses = not energy_expenses_all.empty

            # Render mode radio FIRST so its value is available for calculation below
            if has_energy_expenses and energy_override == 0 and len(meter_logs) < 2:
                energy_data_mode = st.radio(
                    "How complete is your energy expense data?",
                    options=[
                        "I enter expenses as they occur — data covers the full period",
                        "I am still catching up — some periods have missing entries",
                    ],
                    key="forecast_energy_mode",
                    help=(
                        "This affects how your logged expenses are extrapolated to a monthly average. "
                        "If you log every bill consistently, choose the first option — the total is divided "
                        "by the months spanned. If you've only entered some bills so far, choose the second — "
                        "the total is divided only by the months that contain entries."
                    ),
                )
            else:
                energy_data_mode = st.session_state.get(
                    "forecast_energy_mode",
                    "I enter expenses as they occur — data covers the full period"
                )

            # NOW compute energy figures using the already-rendered radio value
            _energy_source_label = None

            if len(meter_logs) >= 2:
                # Tier 1: meter readings
                ml_df = pd.DataFrame(meter_logs)
                ml_df["date"] = pd.to_datetime(ml_df["date"])
                ml_df = ml_df.sort_values("date")
                total_kwh_consumed = ml_df["reading_kwh"].iloc[-1] - ml_df["reading_kwh"].iloc[0]
                total_days         = (ml_df["date"].iloc[-1] - ml_df["date"].iloc[0]).days
                if total_days > 0 and total_kwh_consumed > 0:
                    energy_exp = energy_expenses_all["amount"].sum() if has_energy_expenses else 0
                    if energy_exp > 0:
                        actual_energy_kwh_price = energy_exp / total_kwh_consumed
                        actual_energy_monthly   = actual_energy_kwh_price * model_kwh_annual / 12
                        _energy_source_label    = (
                            f"📟 **Tier 1 — Meter readings:** {total_kwh_consumed:,.0f} kWh consumed "
                            f"over {total_days} days → implied ${actual_energy_kwh_price:.4f}/kWh "
                            f"→ **${actual_energy_monthly:,.0f}/month** projected"
                        )

            if actual_energy_kwh_price is None and energy_override > 0:
                # Tier 2: manual override
                actual_energy_monthly   = energy_override
                actual_energy_kwh_price = energy_override * 12 / max(model_kwh_annual, 1)
                _energy_source_label    = (
                    f"✏️ **Tier 2 — Manual override:** ${energy_override:,.2f}/month entered "
                    f"→ **${energy_override * 12:,.0f}/year** projected"
                )

            if actual_energy_kwh_price is None and has_energy_expenses:
                # Tier 3: expense logs — mode selected by radio above
                energy_expenses_all["date"] = pd.to_datetime(energy_expenses_all["date"])
                total_energy_spend = energy_expenses_all["amount"].sum()

                if "as they occur" in energy_data_mode:
                    e_span_days     = (energy_expenses_all["date"].max() - energy_expenses_all["date"].min()).days
                    n_energy_months = max(1, round(e_span_days / 30)) if e_span_days > 0 else 1
                    mode_label      = f"full span ({n_energy_months} month{'s' if n_energy_months != 1 else ''})"
                else:
                    months_with_entries = energy_expenses_all["date"].dt.to_period("M").nunique()
                    n_energy_months     = max(1, months_with_entries)
                    mode_label          = f"months with entries ({n_energy_months} month{'s' if n_energy_months != 1 else ''})"

                actual_energy_monthly   = total_energy_spend / n_energy_months
                actual_energy_kwh_price = actual_energy_monthly * 12 / max(model_kwh_annual, 1)
                _energy_source_label    = (
                    f"🧾 **Tier 3 — Expense logs:** ${total_energy_spend:,.2f} total ÷ {mode_label} "
                    f"= **${actual_energy_monthly:,.2f}/month** → **${actual_energy_monthly * 12:,.0f}/year** projected"
                )

            if _energy_source_label:
                st.info(_energy_source_label)
            elif energy_override == 0:
                st.caption(
                    "⚠️ No energy data found (no meter readings, no energy expenses logged, no override entered). "
                    "Re-projection will use the original model's energy assumption unchanged."
                )

            st.divider()

            # ── Build re-projection inputs ────────────────────────────────────
            from core.roi_calculate import calculate
            import core.data_tables as dt
            import copy as _copy

            # Reconstruct inputs from farm profile
            reproj_inputs = {
                "country":           active_farm.get("country", "Germany"),
                "crop":              active_farm.get("crop", "Lettuce (Butterhead)"),
                "footprint":         float(active_farm.get("footprint", 1000)),
                "levels":            int(active_farm.get("levels", 5)),
                "lights_tier":       active_farm.get("lights_tier", "Basic"),
                "hvac":              active_farm.get("hvac", "Standard"),
                "automation":        active_farm.get("automation", "Medium"),
                "price_scenario":    active_farm.get("price_scenario", "base"),
                "price_override":    float(active_farm.get("price_override") or 0),
                "packaging_cost":    float(active_farm.get("packaging_cost") or 0.15),
                "loss_rate":         float(active_farm.get("loss_rate") or 5),
                "net_grow_factor":   float(active_farm.get("net_grow_factor") or 85),
                "walkways_factor":   float(active_farm.get("walkways_factor") or 15),
                "water_price":       float(active_farm.get("water_price") or 2),
                "rent_monthly":      float(active_farm.get("rent_monthly") or 0),
                "real_estate_capex": float(active_farm.get("real_estate_capex") or 0),
                "harvest_mode":      active_farm.get("harvest_mode", "Single"),
                "depreciation_years": int(active_farm.get("depreciation_years") or 10),
                "tax_rate":          float(active_farm.get("tax_rate") or 25),
                "ltv":               float(active_farm.get("ltv") or 60),
                "interest_rate":     float(active_farm.get("interest_rate") or 5.5),
                "loan_term_years":   int(active_farm.get("loan_term_years") or 10),
            }

            # Apply actual price if available
            if actual_avg_price2:
                reproj_inputs["price_override"] = actual_avg_price2

            # Apply actual yield via crop patch
            crop_name2    = reproj_inputs["crop"]
            orig_crop2    = dt.CROPS.get(crop_name2, {})
            patched_crop2 = _copy.deepcopy(orig_crop2)
            if actual_avg_yield_per_cycle and model_ega2 > 0:
                patched_crop2["yield"] = actual_avg_yield_per_cycle / model_ega2

            # Apply actual energy price via country patch
            country_name2    = reproj_inputs["country"]
            orig_country2    = dt.COUNTRIES.get(country_name2, {})
            patched_country2 = _copy.deepcopy(orig_country2)
            if actual_energy_kwh_price and actual_energy_kwh_price > 0:
                patched_country2["kwh"] = actual_energy_kwh_price

            _farm_modality = active_farm.get("modality") or active_farm.get("agriculture_type") or "vertical_farm"

            if _farm_modality == "vertical_farm":
                # ── VF reprojection via calculate() ──────────────────────────
                try:
                    dt.CROPS[crop_name2]        = patched_crop2
                    dt.COUNTRIES[country_name2] = patched_country2
                    if not reproj_inputs.get("lights_tier") or reproj_inputs.get("lights_tier") not in LIGHTS:
                        reproj_result = None
                    else:
                        reproj_result = calculate(reproj_inputs)
                finally:
                    dt.CROPS[crop_name2]        = orig_crop2
                    dt.COUNTRIES[country_name2] = orig_country2

            elif _farm_modality in ("greenhouse", "polytunnel"):
                # ── GH reprojection via calculate_greenhouse() ───────────────
                from core.greenhouse_calculate import calculate_greenhouse
                from core.greenhouse_data_tables import GREENHOUSE_CROPS as _GH_CROPS, POLYTUNNEL_CROPS as _PT_CROPS
                import core.greenhouse_data_tables as _ghdt

                _gh_crop_source = active_farm.get("crop_source", "greenhouse").lower()
                _gh_crop_dict   = _PT_CROPS if _gh_crop_source == "polytunnel" else _GH_CROPS

                gh_reproj_inputs = {
                    "country":           active_farm.get("country", "Germany"),
                    "crop":              active_farm.get("crop", list(_GH_CROPS.keys())[0]),
                    "crop_source":       _gh_crop_source,
                    "footprint":         float(active_farm.get("footprint", 5000)),
                    "automation":        active_farm.get("automation", "Medium"),
                    "price_scenario":    active_farm.get("price_scenario", "base"),
                    "price_override":    float(active_farm.get("price_override") or 0),
                    "packaging_cost":    float(active_farm.get("packaging_cost") or 0.15),
                    "loss_rate":         float(active_farm.get("loss_rate") or 5),
                    "net_grow_factor":   float(active_farm.get("net_grow_factor") or 85),
                    "walkways_factor":   float(active_farm.get("walkways_factor") or 15),
                    "water_price":       float(active_farm.get("water_price") or 2),
                    "rent_monthly":      float(active_farm.get("rent_monthly") or 0),
                    "real_estate_capex": float(active_farm.get("real_estate_capex") or 0),
                    "harvest_mode":      active_farm.get("harvest_mode", "Single"),
                    "depreciation_years": int(active_farm.get("depreciation_years") or 10),
                    "tax_rate":          float(active_farm.get("tax_rate") or 25),
                    "ltv":               float(active_farm.get("ltv") or 60),
                    "interest_rate":     float(active_farm.get("interest_rate") or 5.5),
                    "loan_term_years":   int(active_farm.get("loan_term_years") or 10),
                    "discount_rate":     float(active_farm.get("discount_rate") or 8.0),
                    "mean_annual_dli":   active_farm.get("mean_annual_dli"),
                    "ambient_temp_annual": active_farm.get("ambient_temp_annual"),
                }

                # Apply actual price
                if actual_avg_price2:
                    gh_reproj_inputs["price_override"] = actual_avg_price2

                # Apply actual yield via GH crop patch
                _gh_crop_name   = gh_reproj_inputs["crop"]
                _gh_orig_crop   = _gh_crop_dict.get(_gh_crop_name, {})
                _gh_patched_crop = _copy.deepcopy(_gh_orig_crop)
                if actual_avg_yield_per_cycle and model_ega2 > 0:
                    _gh_patched_crop["yield"] = actual_avg_yield_per_cycle / model_ega2

                # Apply actual energy price via country patch
                _gh_orig_country    = dt.COUNTRIES.get(country_name2, {})
                _gh_patched_country = _copy.deepcopy(_gh_orig_country)
                if actual_energy_kwh_price and actual_energy_kwh_price > 0:
                    _gh_patched_country["kwh"] = actual_energy_kwh_price

                try:
                    _gh_crop_dict[_gh_crop_name]    = _gh_patched_crop
                    dt.COUNTRIES[country_name2]      = _gh_patched_country
                    reproj_result = calculate_greenhouse(gh_reproj_inputs)
                except Exception as _gh_err:
                    reproj_result = None
                    st.caption(f"⚠️ GH re-projection skipped: {_gh_err}")
                finally:
                    _gh_crop_dict[_gh_crop_name] = _gh_orig_crop
                    dt.COUNTRIES[country_name2]  = _gh_orig_country

            else:
                # ── Aquaponics reprojection via calculate_aquaponics() ────────
                # Plant side: patch crop yield and energy price with actuals.
                # Fish side: always stays fully modelled (no fish actuals logged).
                from core.aquaponics_calculate import calculate_aquaponics
                from core.greenhouse_data_tables import (
                    GREENHOUSE_CROPS as _AQ_GH_CROPS,
                    POLYTUNNEL_CROPS as _AQ_PT_CROPS,
                )

                # Parse AQ-specific params from farm metadata
                _aq_meta_raw = active_farm.get("metadata") or {}
                if isinstance(_aq_meta_raw, str):
                    try:
                        _aq_meta = json.loads(_aq_meta_raw)
                    except Exception:
                        _aq_meta = {}
                else:
                    _aq_meta = _aq_meta_raw

                _aq_mode        = "coupled" if "coupled" in (
                    active_farm.get("modality") or ""
                ) else "decoupled"
                _aq_crop_source = (active_farm.get("crop_source") or "greenhouse").lower()
                _aq_crop_dict   = (
                    _AQ_PT_CROPS if _aq_crop_source == "polytunnel" else _AQ_GH_CROPS
                )
                _aq_plant_crop  = active_farm.get("crop", list(_aq_crop_dict.keys())[0])
                if _aq_plant_crop not in _aq_crop_dict:
                    _aq_plant_crop = list(_aq_crop_dict.keys())[0]

                aq_reproj_inputs = {
                    "aquaponics_mode":       _aq_mode,
                    "country":               active_farm.get("country", "Germany"),
                    "plant_crop":            _aq_plant_crop,
                    "plant_crop_source":     _aq_crop_source,
                    "plant_footprint":       float(
                        active_farm.get("footprint") or
                        active_farm.get("plant_footprint") or 1000
                    ),
                    "automation":            active_farm.get("automation", "Medium"),
                    "price_scenario":        active_farm.get("price_scenario", "base"),
                    "plant_price_override":  float(
                        active_farm.get("price_override") or 0
                    ),
                    "packaging_cost":        float(
                        active_farm.get("packaging_cost") or 0.15
                    ),
                    "loss_rate":             float(
                        active_farm.get("loss_rate") or 5
                    ),
                    "net_grow_factor":       float(
                        active_farm.get("net_grow_factor") or 90
                    ),
                    "walkways_factor":       float(
                        active_farm.get("walkways_factor") or 10
                    ),
                    "water_price":           float(
                        active_farm.get("water_price") or 2
                    ),
                    "rent_monthly":          float(
                        active_farm.get("rent_monthly") or 0
                    ),
                    "real_estate_capex":     float(
                        active_farm.get("real_estate_capex") or 0
                    ),
                    "harvest_mode":          active_farm.get("harvest_mode", "Single"),
                    "depreciation_years":    int(
                        active_farm.get("depreciation_years") or 15
                    ),
                    "tax_rate":              float(
                        active_farm.get("tax_rate") or 25
                    ),
                    "ltv":                   float(active_farm.get("ltv") or 60),
                    "interest_rate":         float(
                        active_farm.get("interest_rate") or 5.5
                    ),
                    "loan_term_years":       int(
                        active_farm.get("loan_term_years") or 15
                    ),
                    "discount_rate":         float(
                        active_farm.get("discount_rate") or 8.0
                    ),
                    "mean_annual_dli":       active_farm.get("mean_annual_dli"),
                    "ambient_temp_annual":   active_farm.get("ambient_temp_annual"),
                    # Fish side — from metadata, falls back to safe defaults
                    "species":               _aq_meta.get("species", "Tilapia"),
                    "tank_volume_m3":        float(
                        _aq_meta.get("tank_volume_m3") or 50
                    ),
                    "system_scale":          (
                        "Commercial-scale (>100m³)"
                        if float(_aq_meta.get("tank_volume_m3") or 50) >= 100
                        else "Small-scale (<100m³)"
                    ),
                    "target_temp_c":         float(
                        _aq_meta.get("target_temp_c") or 28
                    ),
                    "fish_price":            float(
                        _aq_meta.get("fish_price") or 4.5
                    ),
                    "fish_depreciation_years": int(
                        _aq_meta.get("fish_depreciation_years") or 10
                    ),
                }

                # Apply actual plant sale price if available
                if actual_avg_price2:
                    aq_reproj_inputs["plant_price_override"] = actual_avg_price2

                # Patch plant crop yield with actuals (same pattern as GH)
                _aq_orig_crop    = _aq_crop_dict.get(_aq_plant_crop, {})
                _aq_patched_crop = _copy.deepcopy(_aq_orig_crop)
                if actual_avg_yield_per_cycle and model_ega2 > 0:
                    _aq_patched_crop["yield"] = (
                        actual_avg_yield_per_cycle / model_ega2
                    )

                # Patch energy price with actuals
                _aq_orig_country    = dt.COUNTRIES.get(country_name2, {})
                _aq_patched_country = _copy.deepcopy(_aq_orig_country)
                if actual_energy_kwh_price and actual_energy_kwh_price > 0:
                    _aq_patched_country["kwh"] = actual_energy_kwh_price

                try:
                    _aq_crop_dict[_aq_plant_crop]  = _aq_patched_crop
                    dt.COUNTRIES[country_name2]     = _aq_patched_country
                    _aq_reproj_full = calculate_aquaponics(aq_reproj_inputs)
                    # Flatten to the same keys the comparison table expects
                    # (plant side fields + combined revenue/ebitda/capex)
                    _aq_plant_r = _aq_reproj_full.get("plant", {})
                    reproj_result = {
                        **_aq_plant_r,
                        "annual_revenue":    _aq_reproj_full.get(
                            "combined_revenue",
                            _aq_plant_r.get("annual_revenue", 0),
                        ),
                        "ebitda":            _aq_reproj_full.get(
                            "combined_ebitda",
                            _aq_plant_r.get("ebitda", 0),
                        ),
                        "ebitda_margin":     _aq_reproj_full.get(
                            "combined_ebitda_margin",
                            _aq_plant_r.get("ebitda_margin", 0),
                        ),
                        "total_capex":       _aq_reproj_full.get(
                            "combined_capex",
                            _aq_plant_r.get("total_capex", 0),
                        ),
                    }
                except Exception as _aq_err:
                    reproj_result = None
                    st.caption(f"⚠️ AQ re-projection skipped: {_aq_err}")
                finally:
                    _aq_crop_dict[_aq_plant_crop] = _aq_orig_crop
                    dt.COUNTRIES[country_name2]    = _aq_orig_country

            # ── Side-by-side comparison ───────────────────────────────────────
            st.markdown(
                "<p style='font-size:11px;color:#444c5a;margin:4px 0 0 0;text-align:right;'>"
                "<a style='color:#444c5a;text-decoration:none;cursor:pointer;' "
                "onclick=\"document.getElementById('reproj_debug').style.display="
                "document.getElementById('reproj_debug').style.display==='none'?'block':'none'\">"
                "⚙ re-projection diagnostics</a></p>",
                unsafe_allow_html=True,
            )
            with st.expander("", expanded=False):
                # ── Snapshot inputs ───────────────────────────────────────────
                st.markdown("##### 📐 Model Snapshot — Key Assumptions")
                snap_rows = [
                    ("Annual Revenue",        f"${model2.get('annual_revenue',0):,.0f}"),
                    ("Annual Energy Cost",     f"${model2.get('annual_energy_cost',0):,.0f}"),
                    ("Total Annual kWh",       f"{model2.get('total_annual_kwh',0):,.0f}"),
                    ("Implied kWh Price",      f"${model_kwh_price:.4f}/kWh"),
                    ("Annual Labour Cost",     f"${model2.get('annual_labour_cost',0):,.0f}"),
                    ("Annual Labour Hours",    f"{model2.get('annual_labour_hours',0):,.1f} hrs"),
                    ("Effective Grow Area",    f"{model2.get('effective_grow_area',0):,.1f} m²"),
                    ("Cycles / Year",          f"{model2.get('cycles_per_year',0)}"),
                    ("Total Annual kg",        f"{model2.get('total_annual_kg',0):,.0f} kg"),
                    ("Effective Price",        f"${model2.get('effective_price',0):.3f}/kg"),
                    ("EBITDA",                 f"${model2.get('ebitda',0):,.0f}"),
                ]
                st.dataframe(
                    pd.DataFrame(snap_rows, columns=["Parameter", "Model Snapshot"]),
                    use_container_width=True, hide_index=True,
                )

                # ── What was substituted ──────────────────────────────────────
                st.markdown("##### 🔄 What the Re-Projection Substituted")
                sub_rows = []

                _model_yield_per_m2 = model2.get("total_annual_kg", 0) / max(model2.get("cycles_per_year", 1), 1) / max(model_ega2, 1)
                _reproj_yield_per_m2 = actual_avg_yield_per_cycle / model_ega2 if actual_avg_yield_per_cycle and model_ega2 > 0 else None

                sub_rows.append((
                    "Yield per m²/cycle",
                    f"{_model_yield_per_m2:.3f} kg/m²",
                    f"{_reproj_yield_per_m2:.3f} kg/m²" if _reproj_yield_per_m2 else "unchanged (no harvest data)",
                    f"{(_reproj_yield_per_m2 - _model_yield_per_m2) / _model_yield_per_m2 * 100:+.1f}%" if _reproj_yield_per_m2 else "—",
                ))
                sub_rows.append((
                    "Sale Price",
                    f"${model_price2:.3f}/kg",
                    f"${actual_avg_price2:.3f}/kg" if actual_avg_price2 else "unchanged (no sale prices logged)",
                    f"{(actual_avg_price2 - model_price2) / model_price2 * 100:+.1f}%" if actual_avg_price2 and model_price2 else "—",
                ))
                sub_rows.append((
                    "Energy kWh Price",
                    f"${model_kwh_price:.4f}/kWh",
                    f"${actual_energy_kwh_price:.4f}/kWh" if actual_energy_kwh_price else "unchanged (no energy data)",
                    f"{(actual_energy_kwh_price - model_kwh_price) / model_kwh_price * 100:+.1f}%" if actual_energy_kwh_price and model_kwh_price else "—",
                ))
                sub_rows.append((
                    "Labour rate",
                    "not substituted — driven by country table",
                    "not substituted — driven by country table",
                    "Labour cost changes only as a side-effect of yield change",
                ))
                st.dataframe(
                    pd.DataFrame(sub_rows, columns=["Variable", "Original", "Re-Projection", "Change"]),
                    use_container_width=True, hide_index=True,
                )

                # ── Re-projection outputs ─────────────────────────────────────
                st.markdown("##### 📊 Re-Projection Result vs Model")
                out_rows = [
                    ("Annual Revenue",      f"${model2.get('annual_revenue',0):,.0f}",      f"${(reproj_result or {}).get('annual_revenue',0):,.0f}"),
                    ("Annual Energy Cost",  f"${model2.get('annual_energy_cost',0):,.0f}",  f"${(reproj_result or {}).get('annual_energy_cost',0):,.0f}"),
                    ("Annual Labour Cost",  f"${model2.get('annual_labour_cost',0):,.0f}",  f"${(reproj_result or {}).get('annual_labour_cost',0):,.0f}"),
                    ("Annual Labour Hours", f"{model2.get('annual_labour_hours',0):,.1f}",  f"{(reproj_result or {}).get('annual_labour_hours',0):,.1f}"),
                    ("Total Annual Costs",  f"${model2.get('total_annual_costs',0):,.0f}",  f"${(reproj_result or {}).get('total_annual_costs',0):,.0f}"),
                    ("Total Annual kg",     f"{model2.get('total_annual_kg',0):,.0f}",      f"{(reproj_result or {}).get('total_annual_kg',0):,.0f}"),
                    ("Effective Price",     f"${model2.get('effective_price',0):.3f}/kg",   f"${(reproj_result or {}).get('effective_price',0):.3f}/kg"),
                    ("EBITDA",              f"${model2.get('ebitda',0):,.0f}",              f"${(reproj_result or {}).get('ebitda',0):,.0f}"),
                    ("NPV 10yr",            f"${model2.get('npv',0):,.0f}",                 f"${(reproj_result or {}).get('npv',0):,.0f}"),
                ]
                st.dataframe(
                    pd.DataFrame(out_rows, columns=["Metric", "Original Model", "Re-Projection"]),
                    use_container_width=True, hide_index=True,
                )

                # ── Labour explanation ────────────────────────────────────────
                st.markdown("##### 👷 Why Labour Changes in the Re-Projection")
                st.caption(
                    "Labour is not directly substituted from your expense logs. "
                    "It is recomputed by `calculate()` using the patched yield. "
                    "Post-harvest processing, packaging, and waste handling tasks "
                    "scale with `total_production_gross` and `total_annual_kg` — "
                    "both of which change when yield is patched. "
                    "If your actual yield is lower than the model, labour for those tasks "
                    "decreases proportionally. The labour **rate** ($/hr) stays at the "
                    "country table value and is never substituted from expense logs."
                )
                if not df_e2.empty:
                    labour_logged = df_e2[df_e2["category"] == "Labour"]["amount"].sum()
                    if labour_logged > 0 and n_months_data > 0:
                        labour_monthly_actual = labour_logged / n_months_data
                        labour_annual_actual  = labour_monthly_actual * 12
                        model_labour_annual   = model2.get("annual_labour_cost", 0)
                        reproj_labour_annual  = (reproj_result or {}).get("annual_labour_cost", 0)
                        st.caption(
                            f"Your logged labour expenses: **${labour_logged:,.2f}** total "
                            f"over {n_months_data} month(s) = **${labour_monthly_actual:,.2f}/month** "
                            f"= **${labour_annual_actual:,.0f}/year** annualised. "
                            f"Compare: model assumes **${model_labour_annual:,.0f}/year**, "
                            f"re-projection computes **${reproj_labour_annual:,.0f}/year** "
                            f"(difference is yield-driven, not from your expense logs)."
                        )
            st.markdown("#### Original Model vs Re-Projection")
            st.caption(
                "Re-projection substitutes your actual observed averages (yield, sale price, energy cost) "
                "into the model in place of the original assumptions. Everything else stays the same."
            )

            comp_metrics = [
                ("Annual Revenue",      "annual_revenue"),
                ("Annual Energy Cost",  "annual_energy_cost"),
                ("Annual Labour Cost",  "annual_labour_cost"),
                ("Total Annual Costs",  "total_annual_costs"),
                ("EBITDA",              "ebitda"),
                ("EBITDA Margin",       "ebitda_margin"),
                ("Total CAPEX",         "total_capex"),
                ("Payback (years)",     "payback_years"),
                ("NPV 10yr",            "npv"),
            ]

            comp_rows = []
            for label, key in comp_metrics:
                orig_val   = model2.get(key)
                reproj_val = (reproj_result or {}).get(key)
                if orig_val is None or reproj_val is None:
                    continue

                if key == "ebitda_margin":
                    orig_fmt   = f"{orig_val*100:.1f}%"
                    reproj_fmt = f"{reproj_val*100:.1f}%"
                    delta      = f"{(reproj_val - orig_val)*100:+.1f}pp"
                elif key == "payback_years":
                    orig_fmt   = f"{orig_val:.1f} yrs" if orig_val else "N/A"
                    reproj_fmt = f"{reproj_val:.1f} yrs" if reproj_val else "N/A"
                    delta      = f"{reproj_val - orig_val:+.1f} yrs" if orig_val and reproj_val else "—"
                else:
                    orig_fmt   = f"${orig_val:,.0f}"
                    reproj_fmt = f"${reproj_val:,.0f}"
                    pct_chg    = (reproj_val - orig_val) / abs(orig_val) * 100 if orig_val else 0
                    delta      = f"{pct_chg:+.1f}%"

                comp_rows.append({
                    "Metric":        label,
                    "Original Model": orig_fmt,
                    "Re-Projection": reproj_fmt,
                    "Change":        delta,
                })

            df_comp = pd.DataFrame(comp_rows)
            st.dataframe(df_comp, use_container_width=True, hide_index=True)

            # ── Key driver callout ────────────────────────────────────────────
            st.divider()
            st.markdown("#### Main Drivers of Change")

            drivers = []
            if actual_energy_kwh_price and model_kwh_price:
                e_chg = (actual_energy_kwh_price - model_kwh_price) / model_kwh_price * 100
                if abs(e_chg) > 2:
                    direction = "above" if e_chg > 0 else "below"
                    drivers.append(
                        f"⚡ **Energy cost** running **{abs(e_chg):.1f}% {direction} assumption** "
                        f"(actual: ${actual_energy_kwh_price:.3f}/kWh vs model: ${model_kwh_price:.3f}/kWh)"
                    )
            if actual_avg_price2 and model_price2:
                p_chg = (actual_avg_price2 - model_price2) / model_price2 * 100
                if abs(p_chg) > 2:
                    direction = "above" if p_chg > 0 else "below"
                    drivers.append(
                        f"💰 **Sale price** running **{abs(p_chg):.1f}% {direction} assumption** "
                        f"(actual: ${actual_avg_price2:.2f}/kg vs model: ${model_price2:.2f}/kg)"
                    )
            if actual_avg_yield_per_cycle and model_yield_cycle:
                y_chg = (actual_avg_yield_per_cycle - model_yield_cycle) / model_yield_cycle * 100
                if abs(y_chg) > 2:
                    direction = "above" if y_chg > 0 else "below"
                    drivers.append(
                        f"🌿 **Yield per cycle** running **{abs(y_chg):.1f}% {direction} assumption** "
                        f"(actual avg: {actual_avg_yield_per_cycle:.1f} kg/cycle vs model: {model_yield_cycle:.1f} kg/cycle)"
                    )

            if drivers:
                for d in drivers:
                    st.markdown(f"- {d}")
            else:
                st.success("✅ All key metrics are tracking close to model assumptions.")

            # ── DCF comparison chart ──────────────────────────────────────────
            st.divider()
            st.markdown("#### 10-Year NPV Trajectory — Original vs Re-Projection")

            orig_dcf   = model2.get("dcf_cashflows", [])
            reproj_dcf = (reproj_result or {}).get("dcf_cashflows", [])

            if orig_dcf and reproj_dcf:
                fig_dcf2 = go.Figure()
                fig_dcf2.add_trace(go.Scatter(
                    x=[d["year"] for d in orig_dcf],
                    y=[d["cumulative_npv"] for d in orig_dcf],
                    name="Original Model",
                    mode="lines+markers",
                    line=dict(color="rgba(0,229,160,0.6)", width=2, dash="dash"),
                    marker=dict(size=6),
                ))
                fig_dcf2.add_trace(go.Scatter(
                    x=[d["year"] for d in reproj_dcf],
                    y=[d["cumulative_npv"] for d in reproj_dcf],
                    name="Re-Projection",
                    mode="lines+markers",
                    line=dict(color="#ffc13d", width=2.5),
                    marker=dict(size=7),
                    fill="tozeroy",
                    fillcolor="rgba(255,193,61,0.06)",
                ))
                fig_dcf2.add_hline(y=0, line_dash="dot", line_color="rgba(255,255,255,0.2)")
                fig_dcf2.update_layout(
                    plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
                    font_color="#e8ecf0", height=360,
                    xaxis=dict(title="Year", showgrid=False, dtick=1),
                    yaxis=dict(title="Cumulative NPV ($)", showgrid=False),
                    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
                    margin=dict(t=20, b=20),
                )
                style_fig(fig_dcf2)
                st.plotly_chart(fig_dcf2, use_container_width=True)

                orig_npv   = orig_dcf[-1]["cumulative_npv"] if orig_dcf else 0
                reproj_npv = reproj_dcf[-1]["cumulative_npv"] if reproj_dcf else 0
                npv_delta  = reproj_npv - orig_npv
                st.caption(
                    f"Original model 10yr NPV: **${orig_npv:,.0f}** → "
                    f"Re-projection: **${reproj_npv:,.0f}** "
                    f"({'▲' if npv_delta >= 0 else '▼'} ${abs(npv_delta):,.0f})"
                )

            # ── Scenario overlay ──────────────────────────────────────────────
            st.divider()
            st.markdown("#### Scenario Overlay")
            st.caption(
                "Apply a saved scenario on top of the re-projection (not the original model). "
                "This answers: 'What if energy prices rise 20% from my current actual level?'"
            )

            # ── Cycle Gantt Chart ─────────────────────────────────────────────
            st.divider()
            with st.expander("📊 Rack Utilisation — Cycle Gantt"):
                try:
                    _gantt_resp = (
                        supabase.table("harvest_logs")
                        .select("id, crop, zone, status, seeding_date, expected_harvest_date, date")
                        .eq("farm_id", active_farm["id"])
                        .execute()
                    )
                    _gantt_cycles = _gantt_resp.data or []
                except Exception as _ge:
                    _gantt_cycles = []
                    st.caption(f"Could not load Gantt data: {_ge}")

                if not _gantt_cycles:
                    st.info("No cycle data yet.")
                else:
                    _today_g = date.today()
                    _x_start = _today_g - timedelta(weeks=4)
                    _x_end   = _today_g + timedelta(weeks=4)

                    _gantt_fig = go.Figure()
                    _status_colours = {
                        "seeding":   "#5C7CFA",
                        "growing":   "#2f9e44",
                        "ready":     "#f59f00",
                        "harvested": "#868e96",
                        "failed":    "#e03131",
                    }

                    for _gc in _gantt_cycles:
                        _gc_start_raw = _gc.get("seeding_date")
                        _gc_end_raw   = _gc.get("expected_harvest_date") or _gc.get("date")
                        if not _gc_start_raw or not _gc_end_raw:
                            continue
                        try:
                            _gc_start = date.fromisoformat(_gc_start_raw)
                            _gc_end   = date.fromisoformat(_gc_end_raw)
                        except ValueError:
                            continue
                        _gc_label  = str(_gc.get("zone") or "—") + " · " + str(_gc.get("crop") or "?")
                        _gc_status = _gc.get("status", "growing")
                        _gc_colour = _status_colours.get(_gc_status, "#868e96")
                        _gc_opacity = 1.0 if _gc_status in ("seeding","growing","ready") else 0.5

                        _gantt_fig.add_trace(go.Bar(
                            name=_gc_status,
                            x=[(_gc_end - _gc_start).days],
                            y=[_gc_label],
                            base=[_gc_start.isoformat()],
                            orientation="h",
                            marker=dict(color=_gc_colour, opacity=_gc_opacity),
                            hovertemplate=(
                                f"<b>{_gc_label}</b><br>"
                                f"Status: {_gc_status}<br>"
                                f"Start: {_gc_start}<br>"
                                f"End: {_gc_end}<extra></extra>"
                            ),
                            showlegend=False,
                        ))

                    # Today line
                    _today_ms = int(pd.Timestamp(_today_g).timestamp() * 1000)
                    _gantt_fig.add_vline(
                        x=_today_ms,
                        line_width=1.5, line_dash="dash", line_color="#e03131",
                        annotation_text="Today", annotation_position="top right",
                    )

                    _gantt_fig.update_layout(
                        barmode="overlay",
                        xaxis=dict(
                            type="date",
                            range=[_x_start.isoformat(), _x_end.isoformat()],
                            title="",
                        ),
                        yaxis=dict(title="", automargin=True),
                        height=max(200, 40 * len(_gantt_cycles) + 80),
                        margin=dict(l=10, r=10, t=30, b=10),
                        paper_bgcolor="rgba(0,0,0,0)",
                        plot_bgcolor="rgba(0,0,0,0)",
                        font=dict(color="#ccc"),
                    )
                    style_fig(_gantt_fig)
                    st.plotly_chart(_gantt_fig, use_container_width=True)
                    st.caption("Solid bars = open cycles · Faded bars = closed/failed · Dashed red line = today")

            try:
                sc_resp = supabase.table("scenarios").select("*").is_("farm_id", "null").order("created_at").execute()
                saved_scenarios = sc_resp.data or []
            except Exception:
                saved_scenarios = []

            if not saved_scenarios:
                st.caption("No saved scenarios yet. Create them in the ROI Calculator's Scenario Comparison section.")
            else:
                sc_names   = ["— No overlay —"] + [s["name"] for s in saved_scenarios]
                sc_choice  = st.selectbox("Apply scenario", sc_names, key="forecast_sc_select")
                if sc_choice != "— No overlay —":
                    chosen_sc = next((s for s in saved_scenarios if s["name"] == sc_choice), None)
                    if chosen_sc:
                        # Apply multipliers on top of re-projection inputs
                        ov_inputs    = _copy.deepcopy(reproj_inputs)
                        ov_crop      = _copy.deepcopy(patched_crop2)
                        ov_country   = _copy.deepcopy(patched_country2)
                        ov_crop["yield"]    *= float(chosen_sc.get("yield_factor", 1))
                        ov_country["kwh"]   *= float(chosen_sc.get("energy_factor", 1))
                        ov_country["labour"]*= float(chosen_sc.get("labour_factor", 1))
                        if ov_inputs.get("price_override", 0) > 0:
                            ov_inputs["price_override"] *= float(chosen_sc.get("price_factor", 1))

                        try:
                            dt.CROPS[crop_name2]        = ov_crop
                            dt.COUNTRIES[country_name2] = ov_country
                            ov_result = calculate(ov_inputs)
                        finally:
                            dt.CROPS[crop_name2]        = orig_crop2
                            dt.COUNTRIES[country_name2] = orig_country2

                        ov_col1, ov_col2, ov_col3, ov_col4 = st.columns(4)
                        ov_col1.metric("EBITDA (overlay)",
                            f"${ov_result['ebitda']:,.0f}",
                            delta=f"{ov_result['ebitda'] - ((reproj_result or {}).get('ebitda', 0)):+,.0f} vs re-projection")
                        ov_col2.metric("Revenue (overlay)",
                            f"${ov_result['annual_revenue']:,.0f}",
                            delta=f"{ov_result['annual_revenue'] - ((reproj_result or {}).get('annual_revenue', 0)):+,.0f}")
                        ov_col3.metric("Energy (overlay)",
                            f"${ov_result['annual_energy_cost']:,.0f}",
                            delta=f"{ov_result['annual_energy_cost'] - ((reproj_result or {}).get('annual_energy_cost', 0)):+,.0f}",
                            delta_color="inverse")
                        ov_col4.metric("NPV 10yr (overlay)",
                            f"${ov_result['npv']:,.0f}",
                            delta=f"{ov_result['npv'] - ((reproj_result or {}).get('npv', 0)):+,.0f}")