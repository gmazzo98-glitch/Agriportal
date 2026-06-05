import streamlit as st
import streamlit.components.v1 as components
import json, os, sys
from datetime import date

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from supabase import create_client, Client
from core._styles import inject_styles
from core._charts import style_fig
from core.farm_context import render_farm_context_sidebar, get_active_farm
from core.sun import get_sun_position, get_daily_sun_path, get_monthly_sun_summary, get_sunrise_sunset
import plotly.graph_objects as go

st.set_page_config(layout="wide", page_title="CEA Space Planner", page_icon="🏗️")
inject_styles()
from core.auth import require_login
require_login()

@st.cache_resource
def get_supabase() -> Client:
    return create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])

supabase = get_supabase()

with st.sidebar:
    render_farm_context_sidebar(supabase=supabase)
    st.markdown("### 🏗️ Space Planner")
    st.caption("Design your farm layout in 2D and 3D. Save to link with financials and crop cycles.")
    st.page_link(
        "pages/3_Farm_Intelligence_Map.py",
        label="🗺️ View location in Intelligence Map",
        icon="🗺️",
    )

active_farm = get_active_farm()

if "cea_layout_json" not in st.session_state:
    st.session_state["cea_layout_json"] = ""

_preload_objects_js = "[]"
_layout_name_loaded = None
if active_farm and active_farm.get("id"):
    try:
        _lr = supabase.table("farm_layouts").select(
            "id, layout_json, name, updated_at"
        ).eq("farm_id", active_farm["id"]).eq("is_active", True).limit(1).execute()
        if _lr.data:
            _sl = _lr.data[0]
            _lj = _sl.get("layout_json")
            if isinstance(_lj, str):
                _lj = json.loads(_lj)
            if _lj and _lj.get("objects"):
                _preload_objects_js = json.dumps(_lj["objects"])
                _layout_name_loaded = _sl.get("name", "Active layout")
                st.sidebar.success(f"Layout: **{_layout_name_loaded}**  \nUpdated: {(_sl.get('updated_at') or '')[:10]}")
    except Exception:
        pass

_farm_js     = "null"
_supabase_js = "null"
if active_farm:
    _ms_raw = active_farm.get("model_snapshot")
    _model_snap = {}
    if _ms_raw:
        try:
            _model_snap = json.loads(_ms_raw) if isinstance(_ms_raw, str) else (_ms_raw or {})
        except Exception:
            _model_snap = {}
    # Look up country electricity rate for KPI panel
    _country_kwh = 0.20  # fallback
    try:
        from core.energy_labour import get_rates_for_country_name as _get_el_rates
        _el_lookup = _get_el_rates(active_farm.get("country", ""))
        _country_kwh = float(_el_lookup["energy"].get("industrial") or 0.20)
    except Exception:
        pass

    _farm_js = json.dumps({
        "id":             active_farm.get("id"),
        "name":           active_farm.get("name", "My Farm"),
        "modality":       active_farm.get("modality", "vertical_farm"),
        "footprint":      float(active_farm.get("footprint") or active_farm.get("plant_footprint") or 0),
        "levels":         int(active_farm.get("levels") or 1),
        "country":        active_farm.get("country", ""),
        "country_kwh":    _country_kwh,
        "metadata":       json.loads(active_farm.get("metadata", "{}")) if isinstance(active_farm.get("metadata"), str) else active_farm.get("metadata", {}),
        "price_override": float(active_farm.get("price_override") or 0),
        "net_grow_factor":float(active_farm.get("net_grow_factor") or 0.85),
        "loss_rate":      float(active_farm.get("loss_rate") or 5),
        "packaging_cost": float(active_farm.get("packaging_cost") or 0.3),
        "model_snapshot": _model_snap,
    })
    try:
        _supabase_js = json.dumps({
            "url": st.secrets["SUPABASE_URL"],
            "key": st.secrets["SUPABASE_KEY"],
        })
    except Exception:
        _supabase_js = "null"

    # Compute sun data for JS shadow engine
    try:
        from core.sun import get_sun_position, get_monthly_sun_summary
        from datetime import datetime as _dtnow_init
        _s_lat = float(active_farm.get("lat") or 0)
        _s_lon = float(active_farm.get("lon") or 0)
        if _s_lat and _s_lon:
            _now_sun   = get_sun_position(_s_lat, _s_lon, _dtnow_init.now())
            _monthly_s = get_monthly_sun_summary(_s_lat, _s_lon, year=date.today().year)
            _sun_js    = json.dumps({
                "lat":        _s_lat,
                "lon":        _s_lon,
                "azimuth":    _now_sun["azimuth"],
                "elevation":  _now_sun["elevation"],
                "is_daytime": _now_sun["is_daytime"],
                "monthly":    _monthly_s,
            })
        else:
            _sun_js = "null"
    except Exception:
        _sun_js = "null"
    try:
        _cm_raw = active_farm.get("crop_mix_json")
        _cm = json.loads(_cm_raw) if isinstance(_cm_raw, str) else (_cm_raw or [])
        _farm_crops = [r["crop"] for r in _cm if r.get("crop")] if _cm else []
        if not _farm_crops:
            _farm_crops = [active_farm.get("crop", "Lettuce (Butterhead)")]
        _modality = active_farm.get("modality", "vertical_farm")
        if _modality == "vertical_farm":
            from core.data_tables import CROPS as _ALL_CROPS
            _all_crops_js = json.dumps(sorted(_ALL_CROPS.keys()))
        elif _modality in ("greenhouse", "polytunnel", "aquaponics_decoupled", "aquaponics_coupled"):
            from core.greenhouse_data_tables import GREENHOUSE_CROPS as _GH_C, POLYTUNNEL_CROPS as _PT_C
            _crop_src = (active_farm.get("crop_source") or "greenhouse").lower()
            _dict = _PT_C if _crop_src == "polytunnel" else _GH_C
            _all_crops_js = json.dumps(sorted(_dict.keys()))
        else:
            _all_crops_js = json.dumps(_farm_crops)
        _farm_crops_js = json.dumps(_farm_crops)
    except Exception:
        _farm_crops_js = "null"
        _all_crops_js  = "null"
    try:
        from core.greenhouse_data_tables import FISH_SPECIES as _FISH
        _fish_js = json.dumps(_FISH)
    except Exception:
        _fish_js = "null"
else:
    _sun_js        = "null"
    _farm_crops_js = "null"
    _all_crops_js  = "null"
    _fish_js       = "null"

# ── Layout ↔ Financial model consistency engine ───────────────────────────────

def _compute_layout_metrics(objects: list) -> dict:
    """
    Derive key physical metrics from the layout objects[] array.
    Returns a dict of computed values for comparison against the financial model.
    """
    building_area   = 0.0
    canopy_area     = 0.0   # rack layers × rack footprint
    path_area       = 0.0
    tank_volume_m3  = 0.0
    max_rack_levels = 0
    rack_footprint  = 0.0   # ground footprint of racks only

    for o in objects:
        w = float(o.get("w") or 0)
        h = float(o.get("h") or 0)  # depth/length
        area = w * h

        otype = o.get("type", "")
        if otype == "building":
            building_area += area
        elif otype == "rack":
            layers    = int(o.get("layers") or 1)
            rack_type = o.get("rackType", "standard")
            rack_ht   = float(o.get("height") or 2.4)
            # Wall racks: grow area = wall length × rack height
            # Wall length = max(w, h) regardless of canvas orientation; thickness = min = 0.30m
            if rack_type == "wall":
                wall_len = max(w, float(o.get("h") or 0))
                canopy_area += wall_len * rack_ht
            else:
                canopy_area += area * layers
            rack_footprint += area
            max_rack_levels = max(max_rack_levels, layers)
        elif otype == "path":
            path_area += area
        elif otype == "tank":
            depth = float(o.get("height") or 1.5)
            tank_volume_m3 += area * depth

    # Derived ratios
    walkways_pct = (path_area / building_area * 100) if building_area > 0 else 0
    net_grow_pct = (rack_footprint / building_area * 100) if building_area > 0 else 0

    return {
        "building_area":    round(building_area, 1),
        "canopy_area":      round(canopy_area, 1),
        "rack_footprint":   round(rack_footprint, 1),
        "path_area":        round(path_area, 1),
        "tank_volume_m3":   round(tank_volume_m3, 1),
        "max_rack_levels":  max_rack_levels,
        "walkways_pct":     round(walkways_pct, 1),
        "net_grow_pct":     round(net_grow_pct, 1),
    }


def _run_consistency_check(layout_metrics: dict, farm: dict) -> list:
    """
    Compare layout geometry against the financial model parameters stored in the farm.
    Returns a list of conflict dicts: {field, layout_val, model_val, severity, suggestion}.
    severity: "critical" | "warning" | "info"
    """
    conflicts = []
    lm = layout_metrics

    # 1 — Building footprint vs farm footprint
    model_fp = float(farm.get("footprint") or farm.get("plant_footprint") or 0)
    if model_fp > 0 and lm["building_area"] > 0:
        diff_pct = abs(lm["building_area"] - model_fp) / model_fp * 100
        if diff_pct > 20:
            conflicts.append({
                "field":      "Building footprint",
                "layout_val": f"{lm['building_area']:,.0f} m²",
                "model_val":  f"{model_fp:,.0f} m²",
                "diff":       f"{diff_pct:.0f}% difference",
                "severity":   "critical",
                "suggestion": "Update the financial model footprint to match the actual building, "
                              "or resize the building in the layout.",
                "sync_key":   "footprint",
                "sync_val":   lm["building_area"],
            })
        elif diff_pct > 10:
            conflicts.append({
                "field":      "Building footprint",
                "layout_val": f"{lm['building_area']:,.0f} m²",
                "model_val":  f"{model_fp:,.0f} m²",
                "diff":       f"{diff_pct:.0f}% difference",
                "severity":   "warning",
                "suggestion": "Minor discrepancy — review before finalising.",
                "sync_key":   "footprint",
                "sync_val":   lm["building_area"],
            })

    # 2 — Rack levels vs financial model levels
    model_levels = int(farm.get("levels") or 0)
    if model_levels > 0 and lm["max_rack_levels"] > 0:
        if lm["max_rack_levels"] != model_levels:
            conflicts.append({
                "field":      "Rack levels",
                "layout_val": str(lm["max_rack_levels"]),
                "model_val":  str(model_levels),
                "diff":       f"{abs(lm['max_rack_levels'] - model_levels)} level difference",
                "severity":   "critical" if abs(lm["max_rack_levels"] - model_levels) > 1 else "warning",
                "suggestion": "The number of rack levels directly affects energy, labour, and yield. "
                              "Align layout and model.",
                "sync_key":   "levels",
                "sync_val":   lm["max_rack_levels"],
            })

    # 3 — Net grow factor (rack footprint as % of building)
    # 3 — Net grow factor (floor footprint fraction — standard racks only)
    model_ngf = float(farm.get("net_grow_factor") or 0)
    if model_ngf > 0 and lm["net_grow_pct"] > 0:
        diff_pp = abs(lm["net_grow_pct"] - model_ngf)
        if diff_pp > 10:
            conflicts.append({
                "field":      "Net grow factor (floor)",
                "layout_val": f"{lm['net_grow_pct']:.0f}%",
                "model_val":  f"{model_ngf:.0f}%",
                "diff":       f"{diff_pp:.0f}pp difference",
                "severity":   "warning",
                "suggestion": "The fraction of floor space occupied by racks differs from the model assumption. "
                              "Note: wall racks add canopy vertically and are not reflected in floor %. "
                              "See 'Effective canopy area' check below.",
                "sync_key":   "net_grow_factor",
                "sync_val":   lm["net_grow_pct"],
            })

    # 3b — Effective canopy area vs model EGA (catches wall rack contribution)
    _ms_raw = farm.get("model_snapshot")
    _ms = {}
    if _ms_raw:
        try:
            _ms = json.loads(_ms_raw) if isinstance(_ms_raw, str) else (_ms_raw or {})
        except Exception:
            _ms = {}
    _snap_data = _ms.get("plant", _ms) if _ms else {}
    model_ega = float(_snap_data.get("effective_grow_area") or 0)
    if model_ega > 0 and lm["canopy_area"] > 0:
        diff_pct = (lm["canopy_area"] - model_ega) / model_ega * 100
        abs_diff = abs(diff_pct)
        if abs_diff > 15:
            _direction = "larger" if diff_pct > 0 else "smaller"
            conflicts.append({
                "field":      "Effective canopy area",
                "layout_val": f"{lm['canopy_area']:,.0f} m²",
                "model_val":  f"{model_ega:,.0f} m² (saved model)",
                "diff":       f"{abs_diff:.0f}% {_direction} than model",
                "severity":   "critical" if abs_diff > 30 else "warning",
                "suggestion": (
                    f"Your drawn layout has {_direction} canopy than the saved ROI model assumed. "
                    "Wall racks, additional layers, or changed rack dimensions are the usual cause. "
                    "Re-run the ROI Calculator with the layout's canopy area to keep projections accurate."
                    if diff_pct > 0 else
                    f"Your drawn layout has less canopy than the saved ROI model assumed. "
                    "You may have fewer racks drawn than the model expects, or the model "
                    "uses a higher net grow factor. Check rack count and dimensions."
                ),
                "sync_key":   None,
                "sync_val":   None,
            })

    # 4 — Walkways factor (path area as % of building)
    model_wf = float(farm.get("walkways_factor") or 0)
    if model_wf > 0 and lm["walkways_pct"] > 0:
        diff_pp = abs(lm["walkways_pct"] - model_wf)
        if diff_pp > 8:
            conflicts.append({
                "field":      "Walkways factor",
                "layout_val": f"{lm['walkways_pct']:.0f}%",
                "model_val":  f"{model_wf:.0f}%",
                "diff":       f"{diff_pp:.0f}pp difference",
                "severity":   "info",
                "suggestion": "Path area differs from model assumption. "
                              "Accurate walkway modelling improves labour cost precision.",
                "sync_key":   "walkways_factor",
                "sync_val":   lm["walkways_pct"],
            })

    # 5 — Tank volume (aquaponics only)
    if "aquaponics" in (farm.get("modality") or ""):
        _meta = farm.get("metadata") or {}
        if isinstance(_meta, str):
            try:
                _meta = json.loads(_meta)
            except Exception:
                _meta = {}
        model_tv = float(_meta.get("tank_volume_m3") or 0)
        if model_tv > 0 and lm["tank_volume_m3"] > 0:
            diff_pct = abs(lm["tank_volume_m3"] - model_tv) / model_tv * 100
            if diff_pct > 25:
                conflicts.append({
                    "field":      "Fish tank volume",
                    "layout_val": f"{lm['tank_volume_m3']:.1f} m³",
                    "model_val":  f"{model_tv:.1f} m³",
                    "diff":       f"{diff_pct:.0f}% difference",
                    "severity":   "warning",
                    "suggestion": "Tank volume drives fish production capacity, aeration, and heating costs. "
                                  "Align tank dimensions in layout or update model.",
                    "sync_key":   None,  # metadata field — needs special handling
                    "sync_val":   lm["tank_volume_m3"],
                })

    return conflicts


def _render_consistency_panel(conflicts: list, farm: dict, layout_metrics: dict) -> None:
    """
    Render the consistency check results and sync buttons.
    """
    if not conflicts:
        st.success(
            "✅ Layout geometry is consistent with the financial model. "
            "No significant discrepancies found."
        )
        return

    # Summary
    n_crit = sum(1 for c in conflicts if c["severity"] == "critical")
    n_warn = sum(1 for c in conflicts if c["severity"] == "warning")
    n_info = sum(1 for c in conflicts if c["severity"] == "info")

    _summary_parts = []
    if n_crit: _summary_parts.append(f"**{n_crit} critical**")
    if n_warn: _summary_parts.append(f"**{n_warn} warnings**")
    if n_info: _summary_parts.append(f"**{n_info} notes**")

    if n_crit:
        st.error(
            f"⚠️ Layout ↔ Model conflicts: {', '.join(_summary_parts)}. "
            "Revenue and cost projections may be inaccurate until resolved."
        )
    else:
        st.warning(
            f"Layout ↔ Model discrepancies: {', '.join(_summary_parts)}. "
            "Review before using projections for decisions."
        )

    # Per-conflict rows
    for _cf in conflicts:
        _sev = _cf["severity"]
        _icon = "🔴" if _sev == "critical" else ("🟡" if _sev == "warning" else "🔵")
        with st.expander(
            f"{_icon} {_cf['field']}: layout {_cf['layout_val']} vs model {_cf['model_val']} ({_cf['diff']})",
            expanded=(_sev == "critical"),
        ):
            st.caption(_cf["suggestion"])
            _cc1, _cc2 = st.columns([3, 1])
            with _cc1:
                _tbl = (
                    "| | Layout | Financial Model |\n"
                    "|---|---|---|\n"
                    f"| **{_cf['field']}** | {_cf['layout_val']} | {_cf['model_val']} |"
                )
                st.markdown(_tbl)
            with _cc2:
                if _cf.get("sync_key") and _cf.get("sync_val") is not None:
                    if st.button(
                        f"⟵ Sync to model",
                        key=f"sync_{_cf['sync_key']}",
                        use_container_width=True,
                        help=f"Update farm.{_cf['sync_key']} = {_cf['sync_val']} in Supabase",
                    ):
                        try:
                            supabase.table("farms").update(
                                {_cf["sync_key"]: _cf["sync_val"]}
                            ).eq("id", farm["id"]).execute()
                            # Also update session state active_farm
                            if st.session_state.get("active_farm"):
                                st.session_state["active_farm"][_cf["sync_key"]] = _cf["sync_val"]
                            st.success(
                                f"✅ **{_cf['field']}** updated to {_cf['layout_val']} in the financial model."
                            )
                            st.page_link(
                                "pages/1_ROI_Calculator.py",
                                label="→ Go to ROI Calculator to recalculate",
                                icon="📊",
                            )
                            st.rerun()
                        except Exception as _se:
                            st.error(f"Sync failed: {_se}")
                else:
                    st.caption("Manual sync required — update via ROI Calculator.")

    # Layout summary
    with st.expander("📐 Full layout metrics"):
        _lmc1, _lmc2 = st.columns(2)
        with _lmc1:
            st.metric("Building area", f"{layout_metrics['building_area']:,.1f} m²")
            st.metric("Rack canopy area", f"{layout_metrics['canopy_area']:,.1f} m²",
                      help="Effective growing surface including vertical wall racks")
            st.metric("Path area", f"{layout_metrics['path_area']:,.1f} m²")
        with _lmc2:
            st.metric("Max rack levels", layout_metrics["max_rack_levels"])
            st.metric("Net grow factor (floor)", f"{layout_metrics['net_grow_pct']:.1f}%",
                      help="Rack floor footprint as % of building — standard racks only")
            st.metric("Canopy / Building", f"{layout_metrics['canopy_pct']:.1f}%",
                      help="Total canopy area (incl. wall rack vertical surface) as % of building footprint")
            st.metric("Walkways factor", f"{layout_metrics['walkways_pct']:.1f}%")
            if layout_metrics["tank_volume_m3"] > 0:
                st.metric("Tank volume", f"{layout_metrics['tank_volume_m3']:.1f} m³")


def garden_planner():
    html_code = r'''

<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500;600&display=swap" rel="stylesheet">
<style>
*{box-sizing:border-box;margin:0;padding:0;}
html,body{height:100%;background:#0f1310;color:#e8e4db;font-family:'Inter',-apple-system,sans-serif;-webkit-font-smoothing:antialiased;}
.mono{font-family:'JetBrains Mono',ui-monospace,monospace;}
:root{
  --s0:#0f1310;--s1:#191b19;--s2:#212321;--s3:#2a2d2a;
  --line:#2e342e;--line-soft:#23271f;
  --ink:#e8e4db;--ink2:#9ba394;--ink3:#5e6659;
  --accent:#52a066;--accent-d:#3e7d4f;--accent-soft:rgba(82,160,102,0.15);
  --accent-gold:#cf9b3f;--accent-gold-soft:rgba(207,155,63,0.15);
  --danger:#c0573a;--danger-soft:rgba(192,87,58,0.12);
  --azure:#3f7d9c;--azure-soft:rgba(63,125,156,0.15);
  --plum:#8d6a9f;
}
#ui-wrapper{height:100vh;display:flex;flex-direction:column;padding:8px;gap:6px;overflow:hidden;}
.toolbar{display:flex;justify-content:space-between;align-items:center;background:var(--s1);border:1px solid var(--line);border-radius:10px;padding:9px 14px;flex-shrink:0;gap:10px;}
.toolbar .t-left{display:flex;align-items:center;gap:10px;}
.toolbar .t-right{display:flex;gap:5px;flex-wrap:wrap;}
.mode-badge{font-family:'JetBrains Mono',monospace;font-size:9.5px;letter-spacing:.08em;color:var(--ink3);text-transform:uppercase;padding-left:12px;border-left:1px solid var(--line);}
.mode-status-val{color:var(--accent);}
.btn{font-family:inherit;font-size:11px;font-weight:600;letter-spacing:.05em;text-transform:uppercase;padding:7px 12px;border-radius:6px;cursor:pointer;border:1px solid var(--line);background:var(--s2);color:var(--ink2);transition:all .13s;white-space:nowrap;}
.btn:hover{border-color:var(--ink3);color:var(--ink);}
.btn.primary{background:var(--accent);border-color:var(--accent);color:var(--s0);}
.btn.primary:hover{background:var(--accent-d);}
.btn.on{border-color:var(--accent-gold);color:var(--accent-gold);background:var(--accent-gold-soft);}
.btn.danger-hover:hover{border-color:var(--danger);color:var(--danger);}
.btn.azure{background:var(--azure-soft);border-color:var(--azure);color:var(--azure);}
.btn.azure:hover{background:var(--azure);color:#fff;}
.kpi-strip{display:flex;flex-wrap:wrap;gap:0;background:var(--s1);border:1px solid var(--line);border-radius:10px;padding:8px 14px;flex-shrink:0;align-items:center;}
.kpi-item{display:flex;flex-direction:column;gap:2px;padding:0 12px 0 0;min-width:76px;}
.kpi-item+.kpi-item{border-left:1px solid var(--line-soft);padding-left:12px;}
.kpi-lbl{font-size:8.5px;font-weight:600;letter-spacing:.09em;text-transform:uppercase;color:var(--ink3);}
.kpi-val{font-family:'JetBrains Mono',monospace;font-size:14px;font-weight:600;}
.kpi-val.c-azure{color:var(--azure);} .kpi-val.c-gold{color:var(--accent-gold);} .kpi-val.c-green{color:var(--accent);} .kpi-val.c-plum{color:var(--plum);} .kpi-val.c-ink2{color:var(--ink2);}
.sun-strip{display:flex;align-items:center;gap:12px;flex-wrap:wrap;margin-left:auto;padding-left:12px;border-left:1px solid var(--line-soft);}
.sun-grp{display:flex;flex-direction:column;gap:3px;}
.sun-grp label{font-size:8.5px;font-weight:600;letter-spacing:.08em;text-transform:uppercase;color:var(--ink3);}
.sun-grp .sv{font-family:'JetBrains Mono',monospace;font-size:11px;color:var(--ink);font-weight:500;}
.track{height:3px;border-radius:999px;background:var(--line);position:relative;min-width:80px;cursor:pointer;}
.track-fill{position:absolute;left:0;top:0;bottom:0;border-radius:999px;background:var(--accent-gold);}
.track-knob{position:absolute;top:50%;width:10px;height:10px;border-radius:50%;background:var(--accent-gold);transform:translate(-50%,-50%);box-shadow:0 0 0 2px var(--s1);pointer-events:none;}
.snap-label{font-size:11px;color:var(--ink3);display:flex;align-items:center;gap:5px;cursor:pointer;white-space:nowrap;}
.snap-label input{accent-color:var(--accent);}
.tool-select{padding:6px 10px;background:var(--s2);color:var(--ink);border:1px solid var(--line);border-radius:6px;font-family:inherit;font-size:12px;cursor:pointer;}
.tool-select:focus{outline:none;border-color:var(--accent);}
#main-view{flex:1;display:flex;gap:8px;min-height:0;}
#canvas-container{flex:2;background:var(--s0);border-radius:10px;position:relative;border:1px solid var(--line);overflow:hidden;}
#canvas2d{display:block;width:100%;height:100%;}
.canvas-badge{position:absolute;left:10px;bottom:9px;font-family:'JetBrains Mono',monospace;font-size:8.5px;letter-spacing:.1em;text-transform:uppercase;color:var(--ink3);background:var(--s1);border:1px solid var(--line);padding:3px 8px;border-radius:4px;}
#inspector{flex:1;background:var(--s1);border-radius:10px;border:1px solid var(--line);padding:12px;display:flex;flex-direction:column;gap:10px;overflow-y:auto;min-width:210px;max-width:270px;}
::-webkit-scrollbar{width:4px;} ::-webkit-scrollbar-track{background:var(--s0);} ::-webkit-scrollbar-thumb{background:var(--line);border-radius:3px;}
.insp-title{font-size:9.5px;font-weight:700;letter-spacing:.1em;text-transform:uppercase;color:var(--ink3);}
.no-sel{color:var(--ink3);font-style:italic;font-size:12px;line-height:1.5;}
.field{display:flex;flex-direction:column;gap:4px;}
.field label,.field-lbl{font-size:9.5px;font-weight:600;letter-spacing:.06em;text-transform:uppercase;color:var(--ink3);}
.fi{background:var(--s2);border:1px solid var(--line);border-radius:5px;padding:6px 8px;font-size:12px;color:var(--ink);font-family:inherit;width:100%;}
.fi:focus{outline:none;border-color:var(--accent);}
.fi[readonly]{color:var(--azure);opacity:0.7;}
.row2{display:grid;grid-template-columns:1fr 1fr;gap:6px;}
.info-strip{font-size:10px;color:var(--azure);background:var(--azure-soft);border:1px solid var(--azure);border-radius:4px;padding:5px 8px;}
.kpi-card{background:var(--s0);border:1px solid var(--line-soft);border-radius:7px;padding:8px 9px;display:flex;flex-direction:column;gap:4px;}
.kpi-card-hdr{font-size:8px;font-weight:700;letter-spacing:.09em;text-transform:uppercase;color:var(--accent);margin-bottom:2px;}
.kpi-card-hdr.azure{color:var(--azure);}
.kpi-card-hdr.muted{color:var(--ink3);border-top:1px solid var(--line-soft);padding-top:5px;margin-top:1px;}
.kpi-row{display:flex;justify-content:space-between;font-size:10.5px;gap:6px;}
.kpi-row .kl{color:var(--ink3);} .kpi-row .kv{font-family:'JetBrains Mono',monospace;color:var(--ink);font-weight:500;}
.kpi-row .kv.acc{color:var(--accent);} .kpi-row .kv.gold{color:var(--accent-gold);} .kpi-row .kv.azure{color:var(--azure);} .kpi-row .kv.plum{color:var(--plum);} .kpi-row .kv.muted{color:var(--ink3);}
.rack-btns{display:flex;gap:4px;flex-wrap:wrap;}
.rack-btn{flex:1;padding:5px 3px;font-size:9.5px;font-weight:700;letter-spacing:.03em;text-transform:uppercase;border:1px solid var(--line);border-radius:4px;cursor:pointer;background:var(--s2);color:var(--ink3);transition:all .13s;}
.rack-btn:hover{color:var(--ink);border-color:var(--ink3);}
.rack-btn-active{background:var(--accent-soft);}
.warn-box{font-size:10px;color:var(--danger);padding:6px 8px;background:var(--danger-soft);border:1px solid var(--danger);border-radius:4px;}
.ops-panel{background:var(--s0);border:1px solid var(--line);border-radius:6px;padding:9px;font-size:11px;color:var(--ink2);}
.ops-panel-hdr{font-size:8.5px;font-weight:700;letter-spacing:.09em;text-transform:uppercase;color:var(--accent-gold);margin-bottom:5px;}
.ops-panel-hdr.azure{color:var(--azure);}
.ops-grid{display:grid;grid-template-columns:1fr 1fr;gap:3px;line-height:1.7;}
.ops-grid .ok{color:var(--ink3);}
.ops-no-data{color:var(--ink3);font-style:italic;font-size:11px;}
.mini-modal{background:var(--s0);border:1px solid var(--line);border-radius:6px;padding:10px;font-size:11px;color:var(--ink2);}
.mini-modal-hdr{font-weight:700;color:var(--accent);margin-bottom:7px;font-size:11.5px;}
.mini-modal-hdr.azure{color:var(--azure);}
.mini-modal label{display:block;color:var(--ink3);margin-bottom:2px;font-size:9.5px;font-weight:600;letter-spacing:.05em;text-transform:uppercase;}
.mini-modal input,.mini-modal select{width:100%;padding:5px 8px;background:var(--s2);border:1px solid var(--line);color:var(--ink);border-radius:4px;margin-bottom:5px;font-family:inherit;font-size:11px;}
.mini-modal input:focus,.mini-modal select:focus{outline:none;border-color:var(--accent);}
.modal-btns{display:flex;gap:5px;}
.modal-status{margin-top:4px;font-size:10px;}
.viewport-wrap{border:1px solid var(--line);border-radius:9px;overflow:hidden;position:relative;margin-top:auto;flex-shrink:0;height:260px;}
#container3d{width:100%;height:100%;}
.vp-badge{position:absolute;left:10px;top:8px;font-family:'JetBrains Mono',monospace;font-size:8.5px;letter-spacing:.1em;text-transform:uppercase;color:var(--ink2);background:rgba(0,0,0,0.4);padding:3px 7px;border-radius:4px;backdrop-filter:blur(4px);}
.vp-hint{position:absolute;right:10px;bottom:8px;font-size:10px;color:var(--ink3);background:rgba(0,0,0,0.3);padding:3px 8px;border-radius:4px;backdrop-filter:blur(4px);}
.delete-btn{font-family:inherit;font-size:10.5px;font-weight:600;letter-spacing:.05em;text-transform:uppercase;width:100%;padding:7px;border:1px solid var(--line);background:transparent;color:var(--ink3);border-radius:5px;cursor:pointer;margin-top:4px;transition:all .13s;}
.delete-btn:hover{background:var(--danger-soft);border-color:var(--danger);color:var(--danger);}
#custom-confirm-modal{position:fixed;top:50%;left:50%;transform:translate(-50%,-50%);background:var(--s1);border:1px solid var(--danger);border-radius:10px;z-index:1000;padding:20px;box-shadow:0 8px 32px rgba(0,0,0,0.7);text-align:center;min-width:260px;}
.confirm-msg{color:var(--ink);font-size:13px;margin-bottom:16px;}
.confirm-btns{display:flex;gap:8px;justify-content:center;}
input[type=range]{accent-color:var(--accent-gold);}
</style>

<div id="ui-wrapper">
<div class="toolbar">
  <div class="t-left">
    <button id="opsBtn" onclick="toggleOpsMode()" class="btn primary">COMMIT TO OPERATIONS</button>
    <span class="mode-badge">STATUS:&nbsp;<span id="mode-status" class="mode-status-val">ARCHITECT MODE (EDITABLE)</span></span>
  </div>
  <div class="t-right">
    <button onclick="saveToSupabase()" class="btn azure">Save to Cloud</button>
    <button id="shadowBtn" onclick="toggleShadows()" class="btn on">Shadows On</button>
    <button onclick="toggleFullscreen()" class="btn">Fullscreen</button>
    <button onclick="window.clearAll()" class="btn danger-hover">Reset</button>
  </div>
</div>

<div class="kpi-strip">
  <div class="kpi-item"><span class="kpi-lbl">Building Area</span><span class="kpi-val c-azure"><span id="m-build">0.0</span> m&#178;</span></div>
  <div class="kpi-item"><span class="kpi-lbl">Max Height</span><span class="kpi-val c-gold"><span id="m-height">0.0</span> m</span></div>
  <div class="kpi-item"><span class="kpi-lbl">Canopy Area</span><span class="kpi-val c-green"><span id="m-canopy">0.0</span> m&#178;</span></div>
  <div class="kpi-item"><span class="kpi-lbl">Efficiency</span><span class="kpi-val c-plum"><span id="m-eff">0</span>%</span></div>
  <div class="kpi-item"><span class="kpi-lbl">Est. Yield/yr</span><span class="kpi-val c-gold"><span id="m-yield">&#8212;</span></span></div>
  <div class="kpi-item"><span class="kpi-lbl">Racks</span><span class="kpi-val c-ink2"><span id="m-racks">0</span></span></div>
  <div class="sun-strip">
    <label class="snap-label"><input type="checkbox" id="snapToggle" checked> Snap 0.5m</label>
    <div class="sun-grp">
      <label>N&#8593; Rotation</label>
      <div style="display:flex;align-items:center;gap:5px;">
        <input type="range" id="northSlider" min="0" max="359" value="0" step="1" style="width:56px;" oninput="updateNorth(this.value)">
        <span id="northLabel" class="sv mono" style="font-size:10px;color:var(--accent-gold);min-width:26px;">0&#176;</span>
      </div>
    </div>
    <div class="sun-grp" style="min-width:150px;">
      <label id="sunHourLabelTop">Time of Day &middot; 12:00</label>
      <div style="display:flex;align-items:center;gap:6px;">
        <div class="track" id="sunTrackWrap" style="flex:1;">
          <div class="track-fill" id="sunTrackFill" style="width:43%;"></div>
          <div class="track-knob" id="sunTrackKnob" style="left:43%;"></div>
        </div>
        <input type="range" id="sunHourSlider" min="6" max="20" value="12" step="0.5" style="position:absolute;opacity:0;pointer-events:none;width:1px;" oninput="updateSunFromSlider()">
        <button id="sunPlayBtn" onclick="toggleSunAnimation()" class="btn" style="padding:4px 9px;font-size:11px;">&#9654; Play</button>
      </div>
    </div>
    <select id="toolSelect" onchange="handleToolChange()" class="tool-select">
      <option value="building">&#127963; Building</option>
      <option value="plot">&#128208; Property Plot</option>
      <option value="rack">&#128752; Std Rack (multi-layer)</option>
      <option value="wall_rack">&#128255; Wall Rack (vertical)</option>
      <option value="tower_rack">&#11835; Tower Rack (column)</option>
      <option value="single_shelf">&#9645; Single Shelf / Bench</option>
      <option value="tank">&#128031; Fish Tank</option>
      <option value="equip">&#9881; Equipment</option>
      <option value="path">&#128739; Pathway</option>
      <option value="measure">&#128207; Measure Tape</option>
      <option value="select">&#128433; Select / Move</option>
    </select>
  </div>
</div>

<div id="main-view">
  <div id="canvas-container">
    <canvas id="canvas2d"></canvas>
    <div class="canvas-badge">2D &middot; Top-down &middot; 1px = 0.033m</div>
  </div>
  <div id="inspector">
    <div class="insp-title">Inspector</div>
    <div id="no-selection" class="no-sel">Select an element to edit its properties.</div>
    <div id="editor-ui" style="display:none;flex-direction:column;gap:9px;">
      <div class="field"><label>Name</label><input type="text" id="objName" class="fi"></div>

      <div id="building-ui" style="display:none;flex-direction:column;gap:7px;">
        <div class="field"><label>Facility Category</label>
          <select id="buildType" onchange="toggleSpanUI()" class="fi">
            <option value="warehouse">Vertical Farm (Warehouse)</option>
            <option value="greenhouse">High-Tech Greenhouse</option>
            <option value="polytunnel">Polytunnel (Arched)</option>
          </select>
        </div>
        <div id="span-selector" style="display:none;">
          <div class="field"><label>Standard Span (Width)</label>
            <select id="standardSpan" class="fi">
              <option value="6.0">6.0m Small Span</option>
              <option value="8.0">8.0m Medium Span</option>
              <option value="9.6" selected>9.6m Professional Span</option>
              <option value="12.0">12.0m Wide Span</option>
            </select>
          </div>
        </div>
        <div id="dim-inputs">
          <div class="row2">
            <div class="field"><label id="w-label">Width (m)</label><input type="number" id="buildWidth" step="0.1" class="fi mono"></div>
            <div class="field"><label>Length (m)</label><input type="number" id="buildLength" step="0.1" class="fi mono"></div>
          </div>
          <div class="field" style="margin-top:5px;"><label>Max Height (m)</label><input type="number" id="buildHeight" step="0.5" class="fi mono"></div>
        </div>
        <div id="warn-msg" style="display:none;" class="warn-box">&#9888;&#65039; Racks are outside building bounds!</div>
      </div>

      <div id="rack-ui" style="display:none;flex-direction:column;gap:7px;">
        <div>
          <div class="field-lbl" style="margin-bottom:5px;">Rack Type</div>
          <div class="rack-btns" id="rack-type-btns">
            <button onclick="setRackSubtype('standard')" id="rtype-standard" class="rack-btn rack-btn-active">&#128752; Standard</button>
            <button onclick="setRackSubtype('wall')"     id="rtype-wall"     class="rack-btn">&#128255; Wall</button>
            <button onclick="setRackSubtype('tower')"    id="rtype-tower"    class="rack-btn">&#11835; Tower</button>
            <button onclick="setRackSubtype('bench')"    id="rtype-bench"    class="rack-btn">&#9645; Bench</button>
          </div>
        </div>
        <div id="rack-desc" style="font-size:10px;color:var(--ink3);padding:5px 7px;background:var(--s0);border-radius:4px;border:1px solid var(--line-soft);"></div>
        <div id="wall-thickness-strip" style="display:none;" class="info-strip"></div>
        <div class="row2">
          <div class="field" id="wrapper-rackWidth"><label id="lbl-rackWidth">Width (m)</label><input type="number" id="rackWidth" step="0.1" min="0.1" class="fi mono"></div>
          <div class="field" id="wrapper-rackLength"><label id="lbl-rackLength">Length (m)</label><input type="number" id="rackLength" step="0.1" min="0.1" class="fi mono"></div>
        </div>
        <div class="field"><label id="lbl-rackHeight">Height (m)</label><input type="number" id="rackHeight" step="0.1" min="0.1" class="fi mono"></div>
        <div id="rack-layer-controls">
          <div class="row2">
            <div class="field"><label>Layers</label><input type="number" id="objLayers" min="1" max="20" value="5" class="fi mono"></div>
            <div class="field" id="spacing-wrapper"><label>Spacing (m)</label><input type="number" id="layerSpacing" step="0.1" value="0.6" class="fi mono"></div>
          </div>
        </div>
        <!-- Tower rack controls (shows for tower only) -->
        <div id="rack-tower-controls" style="display:none;margin-bottom:8px;">
            <label style="font-size:11px;color:#888;display:block;">PLANTS PER TOWER</label>
            <input type="number" id="towerPlants" step="1" value="20" min="4" max="60" style="width:100%;padding:8px;background:#222;border:1px solid #444;color:#fff;margin-top:5px;">
            <label style="font-size:11px;color:#888;display:block;margin-top:8px;">TOWER SHAPE</label>
            <div style="display:flex;gap:4px;margin-top:5px;">
                <button id="tshape-round" onclick="setTowerShape('round')"
                    style="flex:1;padding:6px 4px;font-size:10px;font-weight:700;border:1px solid #52a066;border-radius:3px;cursor:pointer;background:rgba(82,160,102,0.15);color:#52a066;">
                    ● Round</button>
                <button id="tshape-rect" onclick="setTowerShape('rect')"
                    style="flex:1;padding:6px 4px;font-size:10px;font-weight:700;border:1px solid #444;border-radius:3px;cursor:pointer;background:#222;color:#888;">
                    ▬ Rect</button>
            </div>
        </div>
        <div id="rack-kpis" class="kpi-card">
          <div class="kpi-card-hdr">This Rack</div>
          <div class="kpi-row"><span class="kl">Canopy</span><span class="kv acc" id="kpi-canopy"></span></div>
          <div class="kpi-row"><span class="kl">Yield/cycle</span><span class="kv gold" id="kpi-yield-cycle"></span></div>
          <div class="kpi-row"><span class="kl">Yield/year</span><span class="kv gold" id="kpi-yield-year"></span></div>
          <div class="kpi-row"><span class="kl">Revenue/yr</span><span class="kv plum" id="kpi-revenue"></span></div>
          <div class="kpi-row"><span class="kl">Energy/yr</span><span class="kv" style="color:var(--accent-gold);" id="kpi-energy"></span></div>
          <div class="kpi-row"><span class="kl">Gross margin</span><span class="kv azure" id="kpi-margin"></span></div>
          <div class="kpi-card-hdr muted">vs Model (pro-rated)</div>
          <div class="kpi-row"><span class="kl">Model canopy</span><span class="kv muted" id="kpi-model-canopy"></span></div>
          <div class="kpi-row"><span class="kl">Model yield/yr</span><span class="kv muted" id="kpi-model-yield"></span></div>
          <div class="kpi-row"><span class="kl">Model revenue</span><span class="kv muted" id="kpi-model-rev"></span></div>
          <div class="kpi-row"><span class="kl">&#916; Revenue</span><span class="kv" id="kpi-delta-rev"></span></div>
        </div>
        <button onclick="duplicateSelected()" class="btn azure" style="width:100%;">&#10064; Duplicate (Ctrl+D)</button>
        <div id="aisle-warn" style="display:none;" class="warn-box">&#9888; Aisle &lt;0.8m &#8212; too narrow for trolley access</div>
      </div>

      <div id="tank-ui" style="display:none;flex-direction:column;gap:7px;">
        <div class="row2">
          <div class="field"><label>Width (m)</label><input type="number" id="tankWidth" step="0.1" class="fi mono"></div>
          <div class="field"><label>Length (m)</label><input type="number" id="tankLength" step="0.1" class="fi mono"></div>
        </div>
        <div class="field"><label>Tank Depth (m)</label><input type="number" id="tankDepth" step="0.1" class="fi mono"></div>
        <div id="tank-kpis" class="kpi-card">
          <div class="kpi-card-hdr azure">This Tank</div>
          <div class="kpi-row"><span class="kl">Volume</span><span class="kv azure" id="kpi-tank-vol"></span></div>
          <div class="kpi-row"><span class="kl">Yield/cycle</span><span class="kv gold" id="kpi-fish-cycle"></span></div>
          <div class="kpi-row"><span class="kl">Yield/year</span><span class="kv gold" id="kpi-fish-year"></span></div>
          <div class="kpi-row"><span class="kl">Revenue/yr</span><span class="kv plum" id="kpi-fish-rev"></span></div>
          <div class="kpi-row"><span class="kl">Gross margin</span><span class="kv azure" id="kpi-fish-margin"></span></div>
          <div class="kpi-card-hdr muted">vs Model (pro-rated)</div>
          <div class="kpi-row"><span class="kl">Model vol</span><span class="kv muted" id="kpi-model-tank-vol"></span></div>
          <div class="kpi-row"><span class="kl">Model yield/yr</span><span class="kv muted" id="kpi-model-fish-yield"></span></div>
          <div class="kpi-row"><span class="kl">Model revenue</span><span class="kv muted" id="kpi-model-fish-rev"></span></div>
          <div class="kpi-row"><span class="kl">&#916; Revenue</span><span class="kv" id="kpi-delta-fish-rev"></span></div>
        </div>
        <div style="font-size:10px;color:var(--azure);">Est. water weight: <span id="water-weight" class="mono">0</span> kg</div>
        <div id="fish-ops-panel" style="display:none;" class="ops-panel">
          <div class="ops-panel-hdr azure">&#128031; Live Fish Cycle</div>
          <div id="fish-ops-content" class="ops-grid"></div>
          <div id="fish-no-cycle" style="display:none;" class="ops-no-data">No active fish cycle in this tank.</div>
          <button id="fish-open-ht-btn" onclick="openFishInHarvestTracker()" style="display:none;margin-top:7px;width:100%;" class="btn azure">&#128640; Open in Harvest Tracker</button>
          <button id="fish-stock-btn" onclick="openStockTankModal()" style="display:none;margin-top:5px;width:100%;" class="btn">+ Stock Tank</button>
        </div>
        <div id="stock-tank-modal" style="display:none;" class="mini-modal">
          <div class="mini-modal-hdr azure">&#128031; Stock Tank</div>
          <label>Fish Species</label><select id="st-species" onchange="onSpeciesChange()" class="fi"></select>
          <div id="st-species-info" style="font-size:10px;color:var(--azure);margin-bottom:5px;"></div>
          <label>Stocking Date</label><input type="date" id="st-stock-date" class="fi">
          <label>Expected Harvest Date <span style="color:var(--ink3);">(auto-computed)</span></label><input type="date" id="st-harvest-date" class="fi">
          <label>Tank Volume (m&#179;) <span style="color:var(--ink3);">(auto from tank)</span></label><input type="number" id="st-volume" step="0.1" class="fi">
          <div class="modal-btns" style="margin-top:4px;">
            <button onclick="submitStockTank()" class="btn primary" style="flex:1;">Save</button>
            <button onclick="closeStockTankModal()" class="btn" style="flex:1;">Cancel</button>
          </div>
          <div id="st-status" class="modal-status"></div>
        </div>
      </div>

      <div id="equip-ui" style="display:none;flex-direction:column;gap:7px;">
        <div class="field"><label>Equipment Type</label>
          <select id="equipType" class="fi">
            <option value="hvac">HVAC Unit</option>
            <option value="biofilter">Biofilter System</option>
            <option value="pump">Pump Station</option>
          </select>
        </div>
        <div class="field"><label>Unit Height (m)</label><input type="number" id="equipHeight" step="0.1" value="2.0" class="fi mono"></div>
      </div>

      <div id="path-ui" style="display:none;">
        <div class="row2">
          <div class="field"><label>Path Width (m)</label><input type="number" id="pathWidth" step="0.1" class="fi mono"></div>
          <div class="field"><label>Path Length (m)</label><input type="number" id="pathLength" step="0.1" class="fi mono"></div>
        </div>
      </div>

      <div id="ops-cycle-panel" style="display:none;" class="ops-panel">
        <div class="ops-panel-hdr">&#9889; Live Cycle Data</div>
        <div id="ops-cycle-content" class="ops-grid"></div>
        <div id="ops-no-cycle" style="display:none;" class="ops-no-data">No active cycle on this unit.</div>
        <button id="ops-open-ht-btn" onclick="openInHarvestTracker()" style="display:none;margin-top:7px;width:100%;" class="btn azure">&#128640; Open in Harvest Tracker</button>
        <button id="ops-start-cycle-btn" onclick="openStartCycleModal()" style="display:none;margin-top:5px;width:100%;" class="btn">+ Start New Cycle</button>
      </div>

      <div id="start-cycle-modal" style="display:none;" class="mini-modal">
        <div class="mini-modal-hdr">&#127807; Start New Cycle</div>
        <label>Crop / Species</label><select id="sc-crop" class="fi"></select>
        <label>Seeding Date</label><input type="date" id="sc-seed-date" class="fi">
        <label>Expected Harvest Date</label><input type="date" id="sc-harvest-date" class="fi">
        <label id="sc-area-lbl">Area (m&#178;) <span style="color:var(--ink3);">(auto from unit)</span></label><input type="number" id="sc-area" step="0.1" class="fi">
        <div class="modal-btns" style="margin-top:4px;">
          <button onclick="submitStartCycle()" class="btn primary" style="flex:1;">Save</button>
          <button onclick="closeStartCycleModal()" class="btn" style="flex:1;">Cancel</button>
        </div>
        <div id="sc-status" class="modal-status"></div>
      </div>

      <button onclick="deleteSelected()" class="delete-btn">Delete Selected</button>
    </div>

    <!-- Farm Summary Panel — shown in Ops mode when nothing selected -->
    <div id="farm-summary-panel" style="display:none;flex-direction:column;gap:8px;">
      <div style="display:flex;justify-content:space-between;align-items:center;">
        <div class="insp-title">Farm Summary</div>
        <button onclick="closeFarmSummary()" class="btn" style="padding:3px 8px;font-size:10px;">✕</button>
      </div>
      <div id="farm-summary-content" style="display:flex;flex-direction:column;gap:5px;"></div>
    </div>

    <div class="viewport-wrap">
    <div class="viewport-wrap" id="viewport-wrap">
      <div id="container3d"></div>
      <div class="vp-badge">3D &middot; Forest Studio</div>
      <div class="vp-badge" id="vp-badge-label">3D &middot; Forest Studio</div>
      <div class="vp-hint">drag to orbit &middot; scroll to zoom</div>
      <button id="swap-view-btn" onclick="swapViews()" title="Swap 2D / 3D" style="
        position:absolute;top:8px;right:8px;z-index:10;
        padding:4px 9px;font-size:10px;font-weight:700;letter-spacing:.05em;
        background:rgba(15,19,16,0.75);border:1px solid var(--line);color:var(--ink2);
        border-radius:5px;cursor:pointer;backdrop-filter:blur(4px);transition:all .13s;
      ">⇄ SWAP</button>
    </div>
  </div>
</div>

<div id="custom-confirm-modal" style="display:none;">
  <div id="custom-confirm-msg" class="confirm-msg">Are you sure?</div>
  <div class="confirm-btns">
    <button id="custom-confirm-yes" class="btn danger-hover" style="flex:1;padding:8px 16px;">Yes</button>
    <button onclick="closeCustomConfirm()" class="btn" style="flex:1;padding:8px 16px;">Cancel</button>
  </div>
</div>

</div>

<script src="https://cdnjs.cloudflare.com/ajax/libs/three.js/r128/three.min.js"></script>
<script src="https://cdn.jsdelivr.net/npm/three@0.128.0/examples/js/controls/OrbitControls.js"></script>
<script>
// Sun track click handler
(function(){
  function initTrack(){
    const wrap=document.getElementById('sunTrackWrap');
    const slider=document.getElementById('sunHourSlider');
    const fill=document.getElementById('sunTrackFill');
    const knob=document.getElementById('sunTrackKnob');
    const lbl=document.getElementById('sunHourLabelTop');
    if(!wrap||!slider) return;
    function pct(v){ return ((v-6)/(20-6)*100).toFixed(1)+'%'; }
    function syncTrack(){
      const v=parseFloat(slider.value);
      fill.style.width=pct(v); knob.style.left=pct(v);
      const hh=Math.floor(v),mm=Math.round((v-hh)*60);
      if(lbl) lbl.textContent='Time of Day \u00b7 '+String(hh).padStart(2,'0')+':'+String(mm).padStart(2,'0');
    }
    slider.addEventListener('input', syncTrack);
    wrap.addEventListener('click', function(e){
      const r=wrap.getBoundingClientRect();
      const frac=Math.max(0,Math.min(1,(e.clientX-r.left)/r.width));
      slider.value=6+frac*14; syncTrack();
      if(typeof updateSunFromSlider==='function') updateSunFromSlider();
    });
    syncTrack();
  }
  if(document.readyState==='loading') document.addEventListener('DOMContentLoaded',initTrack);
  else initTrack();
})();
</script>


<script>
        let objects = [];
        let selection = null;
        let zoom = 30, offsetX = 400, offsetY = 375;
        let isDrawing = false, isDragging = false, isPanning = false, rectStart = null;
        let isResizing = false, resizeHandle = null, resizeStartMouse = null, resizeStartRect = null;
        let dragOffset = { x: 0, y: 0 };
        let spacePressed = false;
        let isOpsMode = false;
        let showShadows = true;
        let _liveCycles = [];       // populated by fetchAndApplyCycleData
        let _liveAssignments = [];  // rack_layer_assignments from Supabase

        const canvas = document.getElementById('canvas2d');
        const ctx = canvas.getContext('2d');

        // --- 3D ENGINE ---
        const cont3d = document.getElementById('container3d');
        const scene = new THREE.Scene();
        const camera = new THREE.PerspectiveCamera(50, cont3d.clientWidth/cont3d.clientHeight, 0.1, 2000);
        const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true });
renderer.shadowMap.enabled = true;
renderer.shadowMap.type = THREE.PCFSoftShadowMap;
        renderer.setSize(cont3d.clientWidth, cont3d.clientHeight);
        cont3d.appendChild(renderer.domElement);
        camera.position.set(15, 15, 15);
        const controls = new THREE.OrbitControls(camera, renderer.domElement);
        // --- 3D ENGINE RE-FIX ---
        scene.background = null;
        cont3d.style.background = "linear-gradient(180deg, #1d2119 0%, #0d0f0b 100%)";
        scene.fog = new THREE.Fog(0x14170f, 40, 110);
        const gridHelper = new THREE.GridHelper(500, 250, 0x3d4831, 0x29301f);
        gridHelper.position.y = 0.01;
        scene.add(gridHelper);
        const ground = new THREE.Mesh(new THREE.PlaneGeometry(500,500),
          new THREE.MeshStandardMaterial({color:0x141710,roughness:0.97,metalness:0}));
        ground.rotation.x = -Math.PI/2; ground.receiveShadow = true;
        scene.add(ground);
        scene.add(new THREE.HemisphereLight(0x3e4a33, 0x14160f, 0.85));
        scene.add(new THREE.AmbientLight(0xffffff, 0.18));
        const sun = new THREE.DirectionalLight(0xffffff, 1.15);
        sun.castShadow = true; sun.shadow.mapSize.set(2048,2048);
        Object.assign(sun.shadow.camera,{left:-60,right:60,top:60,bottom:-60,near:1,far:200});
        sun.shadow.bias=-0.0004; sun.shadow.radius=6;
        scene.add(sun);

        // Ensure camera can see the large grid (Far clipping plane at 2000)
        camera.far = 2000;
        camera.updateProjectionMatrix();
        const objectGroup = new THREE.Group();
        scene.add(objectGroup);

        function resizeCanvas() {
            if (canvas && canvas.parentElement) {
                canvas.width = canvas.parentElement.clientWidth;
                canvas.height = canvas.parentElement.clientHeight;
            }
            if (typeof cont3d !== 'undefined' && typeof camera !== 'undefined' && typeof renderer !== 'undefined') {
                if (cont3d.clientHeight > 0) {
                    camera.aspect = cont3d.clientWidth / cont3d.clientHeight;
                    camera.updateProjectionMatrix();
                    renderer.setSize(cont3d.clientWidth, cont3d.clientHeight);
                }
            }
            draw();
        }
        window.addEventListener('resize', resizeCanvas);

        function toggleFullscreen() {
            if (!document.fullscreenElement) {
                document.documentElement.requestFullscreen().catch(err => {
                    console.warn(`Fullscreen error: ${err.message}`);
                });
            } else {
                if (document.exitFullscreen) {
                    document.exitFullscreen();
                }
            }
        }

        function toWorld(sX, sY) { return { x: (sX - offsetX) / zoom, y: (sY - offsetY) / zoom }; }

        function toggleOpsMode() {
            isOpsMode = !isOpsMode;
            const btn = document.getElementById('opsBtn');
            const status = document.getElementById('mode-status');
            const toolSel = document.getElementById('toolSelect');

            if (isOpsMode) {
                btn.textContent = "MODIFY STRUCTURE";
                btn.style.background = "var(--accent-gold)"; btn.style.color = "var(--s0)";
                status.textContent = "OPERATIONS MODE (LIVE DATA)";
                status.style.color = "var(--accent-gold)";
                toolSel.value = "select";
                toolSel.disabled = true;

                fetchAndApplyCycleData();  // Load live cycle data
                // Show farm summary when entering ops mode with nothing selected
                setTimeout(() => {
                    if (!selection) openFarmSummary();
                }, 200);
            } else {
                btn.textContent = "COMMIT TO OPERATIONS";
                btn.style.background = "var(--accent)"; btn.style.color = "var(--s0)";
                status.textContent = "ARCHITECT MODE (EDITABLE)";
                status.style.color = "var(--accent)";
                toolSel.disabled = false;
                const sp = document.getElementById('farm-summary-panel');
                if (sp) sp.style.display = 'none';
                document.getElementById('no-selection').style.display = 'block';
            }
            draw();
        }

        // Fetch active cycles from Supabase and map to rack objects
        async function fetchAndApplyCycleData() {
            if (!SUPABASE_CONFIG || !FARM_DATA || !FARM_DATA.id) return;
            try {
                // Fetch active cycles
                const cycleResp = await fetch(
                    `${SUPABASE_CONFIG.url}/rest/v1/harvest_logs?farm_id=eq.${FARM_DATA.id}&status=in.(seeding,growing,ready,failed)&select=id,crop,zone,status,seeding_date,expected_harvest_date`,
                    { headers: { apikey: SUPABASE_CONFIG.key, Authorization: 'Bearer ' + SUPABASE_CONFIG.key } }
                );
                const cycles = cycleResp.ok ? await cycleResp.json() : [];
                _liveCycles = cycles;

                // Fetch rack-layer assignments for this farm
                const assignResp = await fetch(
                    `${SUPABASE_CONFIG.url}/rest/v1/rack_layer_assignments?farm_id=eq.${FARM_DATA.id}&select=cycle_id,rack_name,layer_index`,
                    { headers: { apikey: SUPABASE_CONFIG.key, Authorization: 'Bearer ' + SUPABASE_CONFIG.key } }
                );
                const assignments = assignResp.ok ? await assignResp.json() : [];
                _liveAssignments = assignments;

                // Build cycle_id → cycle object map
                const cycleMap = {};
                cycles.forEach(c => { cycleMap[c.id] = c; });

                // Build rack_name → { layerIndex → { status, crop } } map from assignments
                const rackLayerMap = {};
                assignments.forEach(a => {
                    const c = cycleMap[a.cycle_id];
                    if (!c) return;
                    if (!rackLayerMap[a.rack_name]) rackLayerMap[a.rack_name] = {};
                    const priority = {ready:4, growing:3, seeding:2, failed:1};
                    const existing = rackLayerMap[a.rack_name][a.layer_index];
                    if (!existing || (priority[c.status]||0) > (priority[existing?.status]||0)) {
                        rackLayerMap[a.rack_name][a.layer_index] = { status: c.status, crop: c.crop };
                    }
                });

                // Fallback: zone-based matching for cycles without layer assignments
                const zoneMap = {};
                cycles.forEach(c => {
                    if (c.zone && !assignments.find(a => a.cycle_id === c.id)) {
                        const priority = {ready:4, growing:3, seeding:2, failed:1};
                        const ex = zoneMap[c.zone];
                        if (!ex || (priority[c.status]||0) > (priority[ex.status]||0))
                            zoneMap[c.zone] = c;
                    }
                });

                // Apply to objects
                let totalAssigned = 0;
                objects.forEach(o => {
                    if (o.type === 'tank') {
                        const fallback = zoneMap[o.name] || zoneMap[String(o.id)];
                        // Only assign if the cycle crop is a recognised fish species
                        const isFish = fallback && FISH_DATA && FISH_DATA[fallback.crop];
                        if (isFish) {
                            o.cycleStatus = fallback.status;
                            o.crops = [fallback.crop];
                            totalAssigned++;
                        } else {
                            o.cycleStatus = '';
                            o.crops = [];
                        }
                    } else if (o.type === 'rack') {
                        const layerData = rackLayerMap[o.name] || {};
                        const fallback  = zoneMap[o.name] || zoneMap[String(o.id)];

                        // Per-layer status and crop
                        o.layerStatus = [];
                        o.crops = [];
                        for (let i = 0; i < (o.layers || 5); i++) {
                            const ld = layerData[i];
                            if (ld) {
                                o.layerStatus[i] = ld.status;
                                o.crops[i] = ld.crop;
                            } else if (fallback) {
                                o.layerStatus[i] = fallback.status;
                                o.crops[i] = fallback.crop;
                            } else {
                                o.layerStatus[i] = '';
                                o.crops[i] = 'None';
                            }
                        }
                        // Rack-level status = highest priority layer
                        const priority = {ready:4, growing:3, seeding:2, failed:1};
                        let best = '';
                        o.layerStatus.forEach(ls => {
                            if ((priority[ls]||0) > (priority[best]||0)) best = ls;
                        });
                        o.cycleStatus = best;
                        if (best) totalAssigned++;
                    }
                });

                const statusEl = document.getElementById('mode-status');
                if (statusEl) {
                    statusEl.style.color='var(--accent-gold)'; statusEl.textContent = `OPERATIONS MODE — ${cycles.length} active cycles, ${totalAssigned} units with data`;
                }
                    if (selection && selection.type === 'rack') updateRackKPIs();
                if (selection && selection.type === 'tank') updateTankKPIs();
                sync3D();
                draw();

                // Auto-select rack or tank if arriving from Harvest Tracker
                if (HIGHLIGHT_RACK) {
                    const target = objects.find(o =>
                        (o.type === 'rack' || o.type === 'tank') && o.name === HIGHLIGHT_RACK
                    );
                    if (target) {
                        selection = target;
                        offsetX = canvas.width  / 2 - (target.x + target.w / 2) * zoom;
                        offsetY = canvas.height / 2 - (target.y + target.h / 2) * zoom;
                        showInspector(true);
                        if (target.type === 'tank') showTankCyclePanel(target);
                        else showOpsCyclePanel(target);
                        draw();
                    }
                }
            } catch(e) {
                console.error('Cycle fetch error:', e);
            }
        }

        
        async function saveToSupabase() {
            if (!SUPABASE_CONFIG || !FARM_DATA || !FARM_DATA.id) {
                alert("No active farm loaded. Please load a farm profile first."); return;
            }
            if (!objects || objects.length === 0) {
                alert("Nothing to save — draw some objects first."); return;
            }
            const allBtns = document.querySelectorAll("button");
            let saveBtn = null;
            allBtns.forEach(b => { if (b.innerText.includes("SAVE TO CLOUD")) saveBtn = b; });
            if (saveBtn) { saveBtn.textContent = "Saving…"; saveBtn.disabled = true; saveBtn.style.opacity = "0.5"; }

            const payload = {
                objects:     objects,
                exported_at: new Date().toISOString(),
                stats: {
                    building_area: parseFloat(document.getElementById("m-build").innerText || "0"),
                    canopy_area:   parseFloat(document.getElementById("m-canopy").innerText || "0"),
                    efficiency:    parseInt(document.getElementById("m-eff").innerText || "0"),
                    max_height:    parseFloat(document.getElementById("m-height").innerText || "0"),
                }
            };
            const supaUrl = SUPABASE_CONFIG.url;
            const supaKey = SUPABASE_CONFIG.key;
            const farmId  = FARM_DATA.id;
            const today   = new Date().toISOString().split("T")[0];
            try {
                // Check for an existing active layout to update in place
                const checkResp = await fetch(
                    `${supaUrl}/rest/v1/farm_layouts?farm_id=eq.${farmId}&is_active=eq.true&select=id`,
                    { headers: { "apikey": supaKey, "Authorization": "Bearer " + supaKey } }
                );
                const existingRows = await checkResp.json();
                let newId;
                if (existingRows.length > 0) {
                    // Update existing active layout
                    const existingId = existingRows[0].id;
                    const patchResp = await fetch(
                        `${supaUrl}/rest/v1/farm_layouts?id=eq.${existingId}`,
                        {
                            method: "PATCH",
                            headers: { "Content-Type": "application/json", "apikey": supaKey, "Authorization": "Bearer " + supaKey, "Prefer": "return=representation" },
                            body: JSON.stringify({ layout_json: payload, updated_at: today }),
                        }
                    );
                    if (!patchResp.ok) throw new Error(await patchResp.text());
                    const patchRows = await patchResp.json();
                    newId = patchRows[0]?.id || existingId;
                } else {
                    // No active layout yet — insert a new one
                    const postResp = await fetch(
                        `${supaUrl}/rest/v1/farm_layouts`,
                        {
                            method: "POST",
                            headers: { "Content-Type": "application/json", "apikey": supaKey, "Authorization": "Bearer " + supaKey, "Prefer": "return=representation" },
                            body: JSON.stringify({ farm_id: farmId, layout_json: payload, name: FARM_DATA.name + " Layout", is_active: true, updated_at: today }),
                        }
                    );
                    if (!postResp.ok) throw new Error(await postResp.text());
                    const postRows = await postResp.json();
                    newId = postRows[0]?.id || "?";
                }
                if (saveBtn) {
                    saveBtn.textContent = "✅ Saved"; saveBtn.disabled = false;
                    saveBtn.style.opacity = "1"; saveBtn.style.boxShadow = "";
                    setTimeout(() => { saveBtn.textContent = "Save to Cloud"; }, 4000);
                }
            } catch(err) {
                console.error("Save error:", err);
                if (saveBtn) {
                    saveBtn.innerText = "❌ " + err.message.substring(0,50);
                    saveBtn.style.background = "#e74c3c"; saveBtn.disabled = false;
                    setTimeout(() => { saveBtn.textContent = "Save to Cloud"; saveBtn.style.opacity = "1"; }, 6000);
                }
            }
        }

        function toggleShadows() {
            showShadows = !showShadows;
            const btn = document.getElementById('shadowBtn');
            if (btn) {
                btn.textContent = showShadows ? "Shadows On" : "Shadows Off";
                btn.classList.toggle("on", showShadows);
            }
            draw();
        }

        // Mark unsaved changes with button glow
        let _syncTimer = null;
        function notifyParent() {
            clearTimeout(_syncTimer);
            _syncTimer = setTimeout(() => {
                document.querySelectorAll("button").forEach(b => {
                    if (b.innerText.includes("SAVE TO CLOUD"))
                        b.style.boxShadow = "0 0 0 2px var(--accent)";
                });
            }, 800);
        }

        let northDeg = 0;
        function updateNorth(val) {
            northDeg = parseInt(val);
            document.getElementById('northLabel').innerText = val + '°';
            draw();
        }

        function computeSunPosition(lat, lon, hourDecimal) {
            const now = new Date();
            const start = new Date(now.getFullYear(), 0, 0);
            const doy = Math.round((now - start) / 86400000);
            const B = (Math.PI / 180) * (360 / 365) * (doy - 81);
            const decl = (Math.PI / 180) * 23.45 * Math.sin(B);
            const latR = lat * Math.PI / 180;
            const eot = 9.87 * Math.sin(2*B) - 7.53 * Math.cos(B) - 1.5 * Math.sin(B);
            const solarTime = hourDecimal + eot / 60 + lon / 15;
            const hourAngle = (Math.PI / 180) * 15 * (solarTime - 12);
            const sinElev = Math.sin(latR)*Math.sin(decl) + Math.cos(latR)*Math.cos(decl)*Math.cos(hourAngle);
            const elevation = Math.asin(Math.max(-1, Math.min(1, sinElev))) * 180 / Math.PI;
            const cosElev = Math.cos(elevation * Math.PI / 180);
            let azimuth = 180;
            if (cosElev > 1e-6) {
                const cosAz = Math.max(-1, Math.min(1,
                    (Math.sin(decl) - Math.sin(latR)*sinElev) / (Math.cos(latR)*cosElev)
                ));
                const azRaw = Math.acos(cosAz) * 180 / Math.PI;
                azimuth = solarTime < 12 ? azRaw : 360 - azRaw;
            }
            return { elevation, azimuth };
        }

        function updateSunFromSlider() {
            const slider = document.getElementById('sunHourSlider');
            if (!slider) return;
            const hour = parseFloat(slider.value);
            const hh = Math.floor(hour), mm = Math.round((hour - hh) * 60);
            const lbl = document.getElementById('sunHourLabel');
            if (lbl) lbl.innerText = String(hh).padStart(2,'0') + ':' + String(mm).padStart(2,'0');
            const lat = (SUN_DATA && SUN_DATA.lat) ? SUN_DATA.lat : 51.5;
            const lon = (SUN_DATA && SUN_DATA.lon) ? SUN_DATA.lon : 0;
            const pos = computeSunPosition(lat, lon, hour);
            sunAzimuth   = pos.azimuth;
            sunElevation = pos.elevation;
            draw();
        }

        let _sunAnimInterval = null;
        function toggleSunAnimation() {
            const btn = document.getElementById('sunPlayBtn');
            if (_sunAnimInterval) {
                clearInterval(_sunAnimInterval);
                _sunAnimInterval = null;
                btn.textContent = '▶ Play';
            } else {
                btn.textContent = '⏸ Pause';
                _sunAnimInterval = setInterval(() => {
                    const slider = document.getElementById('sunHourSlider');
                    if (!slider) return;
                    let val = parseFloat(slider.value) + 0.5;
                    if (val > 20) val = 6;
                    slider.value = val;
                    updateSunFromSlider();
                    draw();
                }, 100);
            }
        }

        // ── Ops Cycle Panel ────────────────────────────────────────────────────
        let _currentOpsCycleId = null;

        function showOpsCyclePanel(obj) {
            const panel   = document.getElementById('ops-cycle-panel');
            const content = document.getElementById('ops-cycle-content');
            const noData  = document.getElementById('ops-no-cycle');
            const htBtn   = document.getElementById('ops-open-ht-btn');
            const scBtn   = document.getElementById('ops-start-cycle-btn');
            if (!panel) return;

            panel.style.display = 'block';
            _currentOpsCycleId = null;

            let objCycles = [];
            
            if (obj.type === 'rack') {
                const objAssignments = _liveAssignments.filter(a => a.rack_name === obj.name);
                const assignedCycleIds = [...new Set(objAssignments.map(a => a.cycle_id))];
                objCycles = _liveCycles.filter(c => assignedCycleIds.includes(c.id));
            }
            
            // Fallback: zone-name match
            if (objCycles.length === 0) {
                objCycles = _liveCycles.filter(c => c.zone === obj.name);
            }

            if (objCycles.length === 0) {
                content.innerHTML = '';
                noData.style.display = 'block';
                htBtn.style.display  = 'none';
                scBtn.style.display  = 'block';
                // Populate crop dropdown for new cycle
                _populateScCropSelect(obj);
                return;
            }

            noData.style.display = 'none';
            scBtn.style.display  = 'none';

            // Show most relevant cycle (highest priority status)
            const priority = {ready:4, growing:3, seeding:2, failed:1};
            objCycles.sort((a,b) => (priority[b.status]||0) - (priority[a.status]||0));
            const c = objCycles[0];
            _currentOpsCycleId = c.id;

            const statusColours = {seeding:'#3f7d9c', growing:'#52a066', ready:'#cf9b3f', failed:'#c0573a'};
            const col = statusColours[c.status] || '#aaa';
            const today = new Date();
            let daysLeft = '—';
            // Resolve harvest date: use stored value or compute from CROP_YIELDS cycle rate
            let harvestDateDisplay = c.expected_harvest_date || null;
            let harvestNote = '';
            if (!harvestDateDisplay && c.seeding_date && c.crop) {
                if (obj.type === 'tank' && FISH_DATA && FISH_DATA[c.crop]) {
                    const fishData = FISH_DATA[c.crop];
                    if (fishData && fishData.grow_cycle_days > 0) {
                        const cycleDays = fishData.grow_cycle_days;
                        const seedMs = new Date(c.seeding_date).getTime();
                        const estHarvest = new Date(seedMs + cycleDays * 86400000).toISOString().split('T')[0];
                        harvestDateDisplay = estHarvest;
                        harvestNote = ` <span style="color:#888;font-size:10px;">(est. ${cycleDays}d model)</span>`;
                    }
                } else if (CROP_YIELDS[c.crop]) {
                    const cropData = CROP_YIELDS[c.crop];
                    if (cropData && cropData.c > 0) {
                        const cycleDays = Math.round(365 / cropData.c);
                        const seedMs = new Date(c.seeding_date).getTime();
                        const estHarvest = new Date(seedMs + cycleDays * 86400000).toISOString().split('T')[0];
                        harvestDateDisplay = estHarvest;
                        harvestNote = ` <span style="color:#888;font-size:10px;">(est. ${cycleDays}d model)</span>`;
                    }
                }
            }
            if (harvestDateDisplay) {
                const diff = Math.round((new Date(harvestDateDisplay) - today) / 86400000);
                daysLeft = diff < 0 ? `<span style="color:#e74c3c;">Overdue ${Math.abs(diff)}d</span>`
                                    : diff <= 3 ? `<span style="color:#f1c40f;">In ${diff}d ⚡</span>`
                                    : `In ${diff}d`;
            }

            content.innerHTML = `
                <div style="display:grid;grid-template-columns:1fr 1fr;gap:4px;line-height:1.6;">
                    <span style="color:#888;">Status:</span><span style="color:${col};font-weight:700;">${c.status.toUpperCase()}</span>
                    <span style="color:#888;">Crop:</span><span>${c.crop || '—'}</span>
                    <span style="color:#888;">Seeded:</span><span>${c.seeding_date || '—'}</span>
                    <span style="color:#888;">Harvest:</span><span>${harvestDateDisplay || '—'}${harvestNote}</span>
                    <span style="color:#888;">Days left:</span><span>${daysLeft}</span>
                    ${objCycles.length > 1 ? `<span style="color:#888;">Cycles on ${obj.type}:</span><span>${objCycles.length}</span>` : ''}
                </div>`;

            htBtn.style.display = 'block';
        }

        function hideOpsCyclePanel() {
            const panel = document.getElementById('ops-cycle-panel');
            if (panel) panel.style.display = 'none';
            closeStartCycleModal();
        }

        let _currentFishCycleId = null;

        function showTankCyclePanel(tank) {
            const panel   = document.getElementById('fish-ops-panel');
            const content = document.getElementById('fish-ops-content');
            const noData  = document.getElementById('fish-no-cycle');
            const htBtn   = document.getElementById('fish-open-ht-btn');
            const stBtn   = document.getElementById('fish-stock-btn');
            if (!panel) return;

            panel.style.display = 'block';
            _currentFishCycleId = null;

            // Find fish cycles by zone matching tank name
            const fishCycles = _liveCycles.filter(c =>
                c.zone === tank.name &&
                FISH_DATA && FISH_DATA[c.crop]
            );

            if (fishCycles.length === 0) {
                content.innerHTML = '';
                noData.style.display = 'block';
                htBtn.style.display  = 'none';
                stBtn.style.display  = 'block';
                _populateStSpeciesSelect();
                return;
            }

            noData.style.display = 'none';
            stBtn.style.display  = 'none';

            const priority = {ready:4, growing:3, seeding:2, failed:1};
            fishCycles.sort((a,b) => (priority[b.status]||0) - (priority[a.status]||0));
            const c = fishCycles[0];
            _currentFishCycleId = c.id;

            const statusColours = {seeding:'#3f7d9c', growing:'#52a066', ready:'#cf9b3f', failed:'#c0573a'};
            const col = statusColours[c.status] || '#aaa';
            const today = new Date();

            // Resolve harvest date with fallback from FISH_DATA
            let harvestDisplay = c.expected_harvest_date || null;
            let harvestNote = '';
            if (!harvestDisplay && c.seeding_date && FISH_DATA && FISH_DATA[c.crop]) {
                const cycleDays = FISH_DATA[c.crop].grow_cycle_days;
                const est = new Date(new Date(c.seeding_date).getTime() + cycleDays * 86400000);
                harvestDisplay = est.toISOString().split('T')[0];
                harvestNote = ` <span style="color:#888;font-size:10px;">(est. ${cycleDays}d)</span>`;
            }

            let daysLeft = '—';
            if (harvestDisplay) {
                const diff = Math.round((new Date(harvestDisplay) - today) / 86400000);
                daysLeft = diff < 0 ? `<span style="color:#e74c3c;">Overdue ${Math.abs(diff)}d</span>`
                                    : diff <= 7 ? `<span style="color:#f1c40f;">In ${diff}d</span>`
                                    : `In ${diff}d`;
            }

            const spec = (FISH_DATA && FISH_DATA[c.crop]) || {};
            const tankVol = c.area_m2 ? `${parseFloat(c.area_m2).toFixed(1)} m³` : '—';

            content.innerHTML = `
                <div style="display:grid;grid-template-columns:1fr 1fr;gap:4px;line-height:1.6;">
                    <span style="color:#888;">Status:</span><span style="color:${col};font-weight:700;">${c.status.toUpperCase()}</span>
                    <span style="color:#888;">Species:</span><span>${c.crop || '—'}</span>
                    <span style="color:#888;">Stocked:</span><span>${c.seeding_date || '—'}</span>
                    <span style="color:#888;">Harvest:</span><span>${harvestDisplay || '—'}${harvestNote}</span>
                    <span style="color:#888;">Days left:</span><span>${daysLeft}</span>
                    <span style="color:#888;">Tank vol:</span><span>${tankVol}</span>
                    ${spec.harvest_weight_kg ? `<span style="color:#888;">Harvest wt:</span><span>${spec.harvest_weight_kg} kg/fish</span>` : ''}
                    ${fishCycles.length > 1 ? `<span style="color:#888;">Active batches:</span><span>${fishCycles.length}</span>` : ''}
                </div>`;

            htBtn.style.display = 'block';
        }

        function hideTankCyclePanel() {
            const panel = document.getElementById('fish-ops-panel');
            if (panel) panel.style.display = 'none';
            closeStockTankModal();
        }

        function openFishInHarvestTracker() {
            if (!_currentFishCycleId) return;
            const tank = selection ? selection.name : '';
            const base = window.top.location.href.split('?')[0].replace(/5_Space_Planner.*/, '2_Harvest_Tracker');
            window.top.location.href = base + '?rack=' + encodeURIComponent(tank) + '&cycle_id=' + _currentFishCycleId;
        }

        function _populateStSpeciesSelect() {
            const sel = document.getElementById('st-species');
            if (!sel || !FISH_DATA) return;
            sel.innerHTML = '';
            Object.keys(FISH_DATA).forEach(sp => {
                const opt = document.createElement('option');
                opt.value = sp; opt.textContent = sp;
                sel.appendChild(opt);
            });
            onSpeciesChange();
        }

        function onSpeciesChange() {
            const sp = document.getElementById('st-species')?.value;
            const infoEl = document.getElementById('st-species-info');
            const harvestEl = document.getElementById('st-harvest-date');
            const stockEl = document.getElementById('st-stock-date');
            if (!sp || !FISH_DATA || !FISH_DATA[sp]) return;
            const spec = FISH_DATA[sp];
            if (infoEl) infoEl.textContent =
                `Grow cycle: ${spec.grow_cycle_days}d · Harvest: ${spec.harvest_weight_kg} kg/fish · FCR: ${spec.feed_conversion_ratio}`;
            // Auto-compute harvest date from stocking date
            const stockDate = stockEl?.value;
            if (stockDate && harvestEl) {
                const est = new Date(new Date(stockDate).getTime() + spec.grow_cycle_days * 86400000);
                harvestEl.value = est.toISOString().split('T')[0];
            }
        }

        function openStockTankModal() {
            const modal = document.getElementById('stock-tank-modal');
            if (!modal) return;
            _populateStSpeciesSelect();
            const today = new Date().toISOString().split('T')[0];
            const stockEl = document.getElementById('st-stock-date');
            if (stockEl) { stockEl.value = today; stockEl.addEventListener('change', onSpeciesChange); }
            // Pre-fill tank volume from object dimensions
            if (selection && selection.type === 'tank') {
                const vol = (selection.w || 0) * (selection.h || 0) * (selection.depth || selection.height || 1);
                const volEl = document.getElementById('st-volume');
                if (volEl) volEl.value = vol.toFixed(1);
            }
            document.getElementById('st-status').textContent = '';
            onSpeciesChange();
            modal.style.display = 'block';
        }

        function closeStockTankModal() {
            const modal = document.getElementById('stock-tank-modal');
            if (modal) modal.style.display = 'none';
        }

        async function submitStockTank() {
            const statusEl = document.getElementById('st-status');
            if (!SUPABASE_CONFIG || !FARM_DATA || !FARM_DATA.id) {
                statusEl.textContent = '❌ No active farm.'; statusEl.style.color = 'var(--danger)'; return;
            }
            const species     = document.getElementById('st-species').value;
            const stockDate   = document.getElementById('st-stock-date').value;
            const harvestDate = document.getElementById('st-harvest-date').value || null;
            const volume      = parseFloat(document.getElementById('st-volume').value) || 0;
            const tankName    = selection ? selection.name : null;

            if (!species || !stockDate) {
                statusEl.textContent = '❌ Species and stocking date required.';
                statusEl.style.color = 'var(--danger)'; return;
            }

            statusEl.textContent = '⏳ Saving...'; statusEl.style.color = 'var(--ink2)';

            const payload = {
                farm_id:               FARM_DATA.id,
                crop:                  species,
                zone:                  tankName,
                status:                'seeding',
                seeding_date:          stockDate,
                expected_harvest_date: harvestDate || undefined,
                area_m2:               volume || undefined,
                date:                  stockDate,
            };

            try {
                const resp = await fetch(`${SUPABASE_CONFIG.url}/rest/v1/harvest_logs`, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'apikey': SUPABASE_CONFIG.key,
                        'Authorization': 'Bearer ' + SUPABASE_CONFIG.key,
                        'Prefer': 'return=representation',
                    },
                    body: JSON.stringify(payload),
                });
                if (!resp.ok) throw new Error(await resp.text());
                statusEl.textContent = '✅ Tank stocked!'; statusEl.style.color = 'var(--accent)';
                setTimeout(() => { closeStockTankModal(); fetchAndApplyCycleData(); }, 1200);
            } catch(err) {
                statusEl.textContent = '❌ ' + err.message.substring(0, 60);
                statusEl.style.color = 'var(--danger)';
            }
        }


        function openInHarvestTracker() {
            if (!_currentOpsCycleId || !SUPABASE_CONFIG) return;
            const rack = selection ? selection.name : '';
            // Navigate parent window to Harvest Tracker with query params
            const base = window.top.location.href.split('?')[0].replace(/5_Space_Planner.*/, '2_Harvest_Tracker');
            window.top.location.href = base + '?rack=' + encodeURIComponent(rack) + '&cycle_id=' + _currentOpsCycleId;
        }

        function _populateScCropSelect(obj) {
            const sel = document.getElementById('sc-crop');
            if (!sel) return;
            sel.innerHTML = '';
            let options = [];
            if (obj && obj.type === 'tank') {
                options = FISH_DATA ? Object.keys(FISH_DATA) : ['Tilapia (Nile)', 'Rainbow Trout'];
            } else {
                options = (FARM_CROPS && FARM_CROPS.length > 0) ? FARM_CROPS : Object.keys(CROP_YIELDS);
            }
            options.forEach(c => {
                const opt = document.createElement('option');
                opt.value = c; opt.textContent = c;
                sel.appendChild(opt);
            });
        }

        function openStartCycleModal() {
            const modal = document.getElementById('start-cycle-modal');
            if (!modal) return;
            _populateScCropSelect(selection);
            // Pre-fill area from rack/tank
            if (selection) {
                let area;
                if (selection.type === 'tank') {
                    area = selection.w * selection.h * (selection.height || 1.5);
                } else if (selection.rackType === 'wall') {
                    // Wall rack: grow area = wall length × rack height (not floor footprint × layers)
                    area = Math.max(selection.w, selection.h) * (selection.height || 2.4);
                } else {
                    area = selection.w * selection.h * (selection.layers || 1);
                }
                const areaEl = document.getElementById('sc-area');
                if (areaEl) {
                    areaEl.value = area.toFixed(1);
                    areaEl.previousElementSibling.innerHTML = selection.type === 'tank'
                        ? `Volume (m³) <span style="color:#555;">(auto from tank)</span>`
                        : selection.rackType === 'wall'
                            ? `Area (m²) <span style="color:#74c0fc;">(wall: length × height)</span>`
                            : `Area (m²) <span style="color:#555;">(auto from rack)</span>`;
                }
            }
            // Default dates
            const today = new Date().toISOString().split('T')[0];
            document.getElementById('sc-seed-date').value = today;
            document.getElementById('sc-status').textContent = '';
            modal.style.display = 'block';
        }

        function closeStartCycleModal() {
            const modal = document.getElementById('start-cycle-modal');
            if (modal) modal.style.display = 'none';
        }

        async function submitStartCycle() {
            const statusEl = document.getElementById('sc-status');
            if (!SUPABASE_CONFIG || !FARM_DATA || !FARM_DATA.id) {
                statusEl.textContent = '❌ No active farm.'; statusEl.style.color = 'var(--danger)'; return;
            }
            const crop        = document.getElementById('sc-crop').value;
            const seedDate    = document.getElementById('sc-seed-date').value;
            const harvestDateRaw = document.getElementById('sc-harvest-date').value || null;
            // Auto-compute from CROP_YIELDS if blank
            let harvestDate = harvestDateRaw;
            if (!harvestDate && crop && seedDate) {
                if (selection && selection.type === 'tank') {
                    const fishData = FISH_DATA && FISH_DATA[crop];
                    if (fishData && fishData.grow_cycle_days > 0) {
                        const seedMs = new Date(seedDate).getTime();
                        harvestDate = new Date(seedMs + fishData.grow_cycle_days * 86400000).toISOString().split('T')[0];
                    }
                } else {
                    const cropData = CROP_YIELDS[crop];
                    if (cropData && cropData.c > 0) {
                        const cycleDays = Math.round(365 / cropData.c);
                        const seedMs = new Date(seedDate).getTime();
                        harvestDate = new Date(seedMs + cycleDays * 86400000).toISOString().split('T')[0];
                    }
                }
            }
            const area        = parseFloat(document.getElementById('sc-area').value) || 0;
            const rackName    = selection ? selection.name : null;

            if (!crop || !seedDate) {
                statusEl.textContent = '❌ Crop and seeding date required.'; statusEl.style.color = 'var(--danger)'; return;
            }

            statusEl.textContent = '⏳ Saving...'; statusEl.style.color = 'var(--ink2)';

            const payload = {
                farm_id:                FARM_DATA.id,
                crop:                   crop,
                zone:                   rackName,
                status:                 'seeding',
                seeding_date:           seedDate,
                expected_harvest_date:  harvestDate || undefined,
                area_m2:                area || undefined,
            };

            try {
                const resp = await fetch(
                    `${SUPABASE_CONFIG.url}/rest/v1/harvest_logs`,
                    {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json',
                            'apikey': SUPABASE_CONFIG.key,
                            'Authorization': 'Bearer ' + SUPABASE_CONFIG.key,
                            'Prefer': 'return=representation',
                        },
                        body: JSON.stringify(payload),
                    }
                );
                if (!resp.ok) throw new Error(await resp.text());
                const rows = await resp.json();
                const newId = rows[0]?.id;
                statusEl.textContent = '✅ Cycle started!'; statusEl.style.color = 'var(--accent)';

                // If rack has layers, also insert rack_layer_assignments for all layers
                if (newId && rackName && selection && selection.layers > 0) {
                    const layerRows = [];
                    // Layer area: wall racks use wall_length × rack_height per layer; standard uses floor footprint
                    const _layerAreaM2 = (selection.rackType === 'wall')
                        ? parseFloat((Math.max(selection.w, selection.h) * (selection.height || 2.4)).toFixed(2))
                        : parseFloat((selection.w * selection.h).toFixed(2));
                    for (let i = 0; i < selection.layers; i++) {
                        layerRows.push({
                            farm_id:     FARM_DATA.id,
                            cycle_id:    newId,
                            rack_name:   rackName,
                            layer_index: i,
                            area_m2:     _layerAreaM2,
                        });
                    }
                    await fetch(
                        `${SUPABASE_CONFIG.url}/rest/v1/rack_layer_assignments`,
                        {
                            method: 'POST',
                            headers: {
                                'Content-Type': 'application/json',
                                'apikey': SUPABASE_CONFIG.key,
                                'Authorization': 'Bearer ' + SUPABASE_CONFIG.key,
                            },
                            body: JSON.stringify(layerRows),
                        }
                    );
                }

                setTimeout(() => {
                    closeStartCycleModal();
                    fetchAndApplyCycleData(); // refresh colours
                }, 1200);

            } catch(err) {
                statusEl.textContent = '❌ ' + err.message.substring(0, 60);
                statusEl.style.color = 'var(--danger)';
            }
        }

        function snapVal(v) {
            return document.getElementById('snapToggle')?.checked ? Math.round(v*2)/2 : v;
        }
        // ── Rack subtype system ─────────────────────────────────────────────
        const RACK_TYPES = {
            standard: {
                label: 'Standard Rack',
                desc:  'Multi-layer horizontal shelving. Standard CEA rack — grows from floor up.',
                color2d: '#40C057',
                colorStr: '0x40C057',
            },
            wall: {
                label: 'Wall Rack',
                desc:  'Mounted on building wall. Single-sided. Shallow depth (0.2–0.4m). High vertical density.',
                color2d: '#74c0fc',
                colorStr: '0x74c0fc',
            },
            tower: {
                label: 'Tower Rack',
                desc:  'Vertical NFT/aeroponic column. Very small footprint (~0.3x0.3m). Height = growing surface.',
                color2d: '#ffd43b',
                colorStr: '0xffd43b',
            },
            bench: {
                label: 'Single Bench / Table',
                desc:  'Single-level work bench or propagation table. Fixed height, one growing surface.',
                color2d: '#cc5de8',
                colorStr: '0xcc5de8',
            },
        };

        function setRackSubtype(subtype) {
            if (selection && selection.type === 'rack') {
                selection.rackType = subtype;
                // Apply defaults for this type
                if (subtype === 'tower') {
                    selection.layers  = parseInt(document.getElementById('towerPlants')?.value) || 20;
                    selection.spacing = 0.15;
                    selection.height  = selection.height || 2.0;
                } else if (subtype === 'wall') {
                    selection.layers        = 1;
                    selection.spacing       = 0.0;
                    selection.height        = selection.height || 2.4;
                    selection.wallThickness = 0.30;   // fixed — not user-editable
                    // Detect orientation: the SHORTER canvas dimension is the thickness.
                    // Portrait (h > w): thickness is w, wall runs along h (Y axis — N/S wall)
                    // Landscape (w >= h): thickness is h, wall runs along w (X axis — E/W wall)
                    if (selection.h > selection.w) {
                        selection.w = 0.30;  // lock X to thickness
                    } else {
                        selection.h = 0.30;  // lock Y to thickness
                    }
                } else if (subtype === 'bench') {
                    selection.layers  = 1;
                    selection.spacing = 0.0;
                    selection.height  = selection.height || 0.9;
                }
                sync3D(); draw(); updateRackKPIs();
            }
            // Update button styles
            ['standard','wall','tower','bench'].forEach(t => {
                const btn = document.getElementById('rtype-'+t);
                if (!btn) return;
                const isActive = t === subtype;
                btn.classList.toggle('rack-btn-active', isActive);
                btn.style.color = isActive ? RACK_TYPES[t].color2d : '';
                btn.style.borderColor = isActive ? RACK_TYPES[t].color2d : '';
            });
            // Show/hide subtype-specific controls
            document.getElementById('rack-layer-controls').style.display = ['standard'].includes(subtype) ? 'block' : 'none';
            document.getElementById('spacing-wrapper').style.display     = subtype === 'standard' ? 'block' : 'none';
            document.getElementById('rack-tower-controls').style.display = subtype === 'tower' ? 'block' : 'none';
            // Wall rack: relabel inputs based on orientation, show info strip
            const isWall = subtype === 'wall';
            const lblW = document.getElementById('lbl-rackWidth');
            const lblL = document.getElementById('lbl-rackLength');
            const lblH = document.getElementById('lbl-rackHeight');
            const wrapL = document.getElementById('wrapper-rackLength');
            const strip = document.getElementById('wall-thickness-strip');
            if (isWall && selection) {
                // Portrait: wall runs N/S (along Y), X = thickness
                // Landscape: wall runs E/W (along X), Y = thickness
                const portrait = selection.h > selection.w;
                if (lblW) lblW.innerText  = portrait ? 'THICKNESS (m) — fixed' : 'WALL LENGTH (m)';
                if (lblL) lblL.innerText  = portrait ? 'WALL LENGTH (m)' : 'THICKNESS (m) — fixed';
                // Dim the thickness axis, highlight the length axis
                const widthInput  = document.getElementById('rackWidth');
                const lengthInput = document.getElementById('rackLength');
                if (portrait) {
                    // w = thickness (locked, blue)
                    if (widthInput)  { widthInput.value  = '0.30'; widthInput.readOnly  = true;  widthInput.style.color  = '#74c0fc'; }
                    if (lengthInput) { lengthInput.readOnly = false; lengthInput.style.color = '#fff'; }
                    document.getElementById('wrapper-rackWidth') && (document.getElementById('wrapper-rackWidth').style.opacity = '0.4');
                    if (wrapL) wrapL.style.opacity = '1';
                } else {
                    // h = thickness (locked, blue)
                    if (lengthInput) { lengthInput.value = '0.30'; lengthInput.readOnly = true;  lengthInput.style.color = '#74c0fc'; }
                    if (widthInput)  { widthInput.readOnly = false; widthInput.style.color = '#fff'; }
                    if (wrapL) wrapL.style.opacity = '0.4';
                    document.getElementById('wrapper-rackWidth') && (document.getElementById('wrapper-rackWidth').style.opacity = '1');
                }
                if (lblH) lblH.innerText = 'RACK HEIGHT (m)';
                if (strip) {
                    strip.style.display = 'block';
                    const thickEl = document.getElementById('wall-thickness-val');
                    if (thickEl) thickEl.innerText = '0.30';
                    // Update orientation hint
                    strip.innerHTML = '&#128204; <strong>' + (portrait ? 'N/S wall (portrait)' : 'E/W wall (landscape)') + '</strong>'
                        + ' &nbsp;&middot;&nbsp; Thickness fixed 0.30 m &nbsp;&middot;&nbsp; Grow area = <strong>Wall length &times; Height</strong>';
                }
            } else {
                if (lblW) lblW.innerText  = 'WIDTH (m)';
                if (lblL) lblL.innerText  = 'LENGTH (m)';
                if (lblH) lblH.innerText  = 'HEIGHT (m)';
                if (wrapL) wrapL.style.opacity = '1';
                if (strip) strip.style.display = 'none';
                const widthInput  = document.getElementById('rackWidth');
                const lengthInput = document.getElementById('rackLength');
                if (widthInput)  { widthInput.readOnly  = false; widthInput.style.color  = '#fff'; }
                if (lengthInput) { lengthInput.readOnly = false; lengthInput.style.color = '#fff'; }
            }
            // Update description
            const descEl = document.getElementById('rack-desc');
            if (descEl) descEl.innerText = RACK_TYPES[subtype]?.desc || '';
        }
        window.setRackSubtype = setRackSubtype;
        function setTowerShape(shape) {
            if (selection && selection.type === 'rack' && selection.rackType === 'tower') {
                selection.towerShape = shape;
                sync3D(); draw();
            }
            const btnR = document.getElementById('tshape-round');
            const btnRec = document.getElementById('tshape-rect');
            if (!btnR || !btnRec) return;
            if (shape === 'rect') {
                btnRec.style.background = 'rgba(82,160,102,0.15)'; btnRec.style.color = '#52a066'; btnRec.style.borderColor = '#52a066';
                btnR.style.background = '#222'; btnR.style.color = '#888'; btnR.style.borderColor = '#444';
            } else {
                btnR.style.background = 'rgba(82,160,102,0.15)'; btnR.style.color = '#52a066'; btnR.style.borderColor = '#52a066';
                btnRec.style.background = '#222'; btnRec.style.color = '#888'; btnRec.style.borderColor = '#444';
            }
        }
        window.setTowerShape = setTowerShape;

        function duplicateSelected() {
            if (!selection) return;
            const copy = JSON.parse(JSON.stringify(selection));
            copy.id = Date.now(); copy.name = selection.name+'_2';
            copy.x = snapVal(selection.x+1.0); copy.y = snapVal(selection.y+1.0);
            objects.push(copy); selection = copy;
            updateStats(); sync3D(); draw(); notifyParent();
        }
        window.duplicateSelected = duplicateSelected;
        document.addEventListener('keydown', e => {
            if ((e.ctrlKey||e.metaKey) && e.key==='d') { e.preventDefault(); duplicateSelected(); }
            if ((e.key==='Delete'||e.key==='Backspace') &&
                document.activeElement.tagName!=='INPUT' &&
                document.activeElement.tagName!=='SELECT') { deleteSelected(); }
        });
        // Per-crop yield data (kg/m²/cycle, cycles/yr, price $/kg)
        // Values from portal data_tables — approximations for planning tool
        const CROP_YIELDS = {
            "default":                  {y:4.2,  c:13, p:3.20},
            "Lettuce (Butterhead)":     {y:4.5,  c:14, p:3.20},
            "Lettuce (Romaine)":        {y:4.2,  c:13, p:3.40},
            "Lettuce (Loose Leaf)":     {y:4.0,  c:13, p:3.10},
            "Baby Spinach":             {y:3.8,  c:12, p:4.20},
            "Rocket":                   {y:3.5,  c:11, p:4.80},
            "Basil":                    {y:3.0,  c:10, p:6.50},
            "Mint":                     {y:3.2,  c:10, p:6.00},
            "Kale":                     {y:4.0,  c:11, p:3.80},
            "Coriander":                {y:2.8,  c:10, p:5.20},
            "Parsley":                  {y:2.5,  c:9,  p:5.50},
            "Tomato (Cherry)":          {y:18.0, c:3,  p:3.80},
            "Tomato (Beefsteak)":       {y:22.0, c:2,  p:3.20},
            "Tomato (Beef)":            {y:22.0, c:2,  p:3.20},
            "Cucumber":                 {y:25.0, c:3,  p:2.80},
            "Strawberry":               {y:6.0,  c:2,  p:5.50},
            "Microgreens":              {y:2.0,  c:18, p:12.0},
            "Wheatgrass":               {y:1.8,  c:20, p:10.0},
        };

        function getCropData(cropName) {
            if (cropName === 'default' && FARM_CROPS && FARM_CROPS.length > 0) {
                return CROP_YIELDS[FARM_CROPS[0]] || CROP_YIELDS["default"];
            }
            return CROP_YIELDS[cropName] || CROP_YIELDS["default"];
        }

        function updateRackKPIs() {
            if (!selection || selection.type !== 'rack') return;
            const layers    = selection.layers || 1;
            const layerArea = selection.w * selection.h;
            // Wall racks: grow area = wall length × rack height
            // Wall length = the LONG axis (max of w/h); thickness = short axis (0.30m)
            const wallLen   = (selection.rackType === 'wall') ? Math.max(selection.w, selection.h) : 0;
            const canopy    = (selection.rackType === 'wall')
                ? wallLen * (selection.height || 2.4)
                : layerArea * layers;

            // ── Section 1: LIVE DATA from Harvest Tracker cycles ────────────
            // Find cycles assigned to this rack
            const rackAssignments = _liveAssignments.filter(a => a.rack_name === selection.name);
            const assignedCycleIds = [...new Set(rackAssignments.map(a => a.cycle_id))];
            const rackCycles = _liveCycles.filter(c =>
                assignedCycleIds.includes(c.id) || c.zone === selection.name
            );
            const activeCycles = rackCycles.filter(c => ['seeding','growing','ready'].includes(c.status));

            let liveCanopy = 0, liveYieldCycle = 0, liveYieldYear = 0, liveRevYear = 0;
            let hasLiveData = false;

            if (activeCycles.length > 0) {
                hasLiveData = true;
                // Deduplicate by layer: each physical layer counts once.
                // If two cycles cover the same layer on the same rack, take the
                // higher-priority one (ready > growing > seeding). This prevents
                // double-counting canopy when a rack has overlapping active cycles.
                const layerCycleMap = {}; // layer_index → cycle
                const priorityOf = { ready: 3, growing: 2, seeding: 1, failed: 0 };
                activeCycles.forEach(c => {
                    const assigns = _liveAssignments.filter(
                        a => a.cycle_id === c.id && a.rack_name === selection.name
                    );
                    if (assigns.length > 0) {
                        assigns.forEach(a => {
                            const existing = layerCycleMap[a.layer_index];
                            if (!existing || (priorityOf[c.status]||0) > (priorityOf[existing.status]||0)) {
                                layerCycleMap[a.layer_index] = c;
                            }
                        });
                    } else {
                        // Zone-based fallback: assign all layers if no layer assignments exist
                        for (let i = 0; i < (selection.layers || 1); i++) {
                            const existing = layerCycleMap[i];
                            if (!existing || (priorityOf[c.status]||0) > (priorityOf[existing.status]||0)) {
                                layerCycleMap[i] = c;
                            }
                        }
                    }
                });
                // Now aggregate from deduplicated layer map
                const cropAreaMap = {}; // crop → total area (for annualised yield)
                const effectiveLayerArea = canopy / Math.max(1, layers);
                Object.values(layerCycleMap).forEach(c => {
                    cropAreaMap[c.crop] = (cropAreaMap[c.crop] || 0) + effectiveLayerArea;
                });
                liveCanopy = Object.values(cropAreaMap).reduce((s, a) => s + a, 0);
                
                const pOvr = FARM_DATA ? parseFloat(FARM_DATA.price_override || 0) : 0;
                const nGr  = FARM_DATA ? parseFloat(FARM_DATA.net_grow_factor || 0.85) : 0.85;
                const lRt  = FARM_DATA ? parseFloat(FARM_DATA.loss_rate || 5) / 100 : 0.05;

                Object.entries(cropAreaMap).forEach(([cropName, area]) => {
                    const d = getCropData(cropName);
                    const effPrice    = pOvr > 0 ? pOvr : d.p;
                    const cycleYield  = area * d.y * nGr * (1 - lRt);
                    const annualYield = cycleYield * d.c;
                    liveYieldYear  += annualYield;
                    liveYieldCycle += cycleYield;
                    liveRevYear    += annualYield * effPrice;
                });
            }

            // ── Section 2: MODEL forecast ────────────────────────────────────
            const priceOverride = FARM_DATA ? parseFloat(FARM_DATA.price_override || 0) : 0;
            const netGrow       = FARM_DATA ? parseFloat(FARM_DATA.net_grow_factor || 0.85) : 0.85;
            const lossRate      = FARM_DATA ? parseFloat(FARM_DATA.loss_rate || 5) / 100 : 0.05;
            const packCost      = FARM_DATA ? parseFloat(FARM_DATA.packaging_cost || 0.3) : 0.3;

            let modelYield = 0, modelRev = 0, cyclesEst = 13;
            const crops = selection.crops || [];
            if (crops.length > 0 && crops.some(c => c && c !== 'None')) {
                let wY = 0, wP = 0, wC = 0, n = 0;
                crops.slice(0, layers).forEach(c => {
                    if (c && c !== 'None') { const d = getCropData(c); wY += d.y; wP += d.p; wC += d.c; n++; }
                });
                if (n > 0) {
                    const avgY = wY/n, avgP = wP/n, avgC = wC/n;
                    const effP = priceOverride > 0 ? priceOverride : avgP;
                    cyclesEst  = Math.round(avgC);
                    modelYield = canopy * avgY * netGrow * (1 - lossRate);
                    modelRev   = modelYield * effP - (modelYield * packCost);
                }
            } else {
                const d = getCropData('default');
                const effP = priceOverride > 0 ? priceOverride : d.p;
                cyclesEst  = Math.round(d.c);
                modelYield = canopy * d.y * netGrow * (1 - lossRate);
                modelRev   = modelYield * effP - (modelYield * packCost);
            }

            // ── Render ────────────────────────────────────────────────────────
            if (document.getElementById('kpi-canopy')) {
                if (hasLiveData) {
                    // Show live data in top section
                    document.getElementById('kpi-canopy').innerText      = liveCanopy.toFixed(1) + ' m² (live)';
                    document.getElementById('kpi-yield-cycle').innerText  = liveYieldCycle.toFixed(0) + ' kg';
                    document.getElementById('kpi-yield-year').innerText   = Math.round(liveYieldYear).toLocaleString() + ' kg/yr';
                    document.getElementById('kpi-revenue').innerText      = '$' + Math.round(liveRevYear).toLocaleString() + '/yr';
                } else {
                    // No cycles — show model forecast greyed
                    document.getElementById('kpi-canopy').innerText      = canopy.toFixed(1) + ' m²';
                    document.getElementById('kpi-yield-cycle').innerText  = (modelYield / Math.max(1, cyclesEst)).toFixed(0) + ' kg (est)';
                    document.getElementById('kpi-yield-year').innerText   = Math.round(modelYield).toLocaleString() + ' kg/yr (est)';
                    document.getElementById('kpi-revenue').innerText      = '$' + Math.round(modelRev).toLocaleString() + '/yr (est)';
                }

                // Energy estimate — uses actual country industrial electricity rate from energy_labour module
                const isVF        = !FARM_DATA || (FARM_DATA.modality === 'vertical_farm');
                const kwh_per_m2_yr = isVF ? (200 * 8760 / 1000) : (50 * 4380 / 1000);
                const _kwh_rate   = (FARM_DATA && FARM_DATA.country_kwh > 0) ? FARM_DATA.country_kwh : 0.20;
                const energyCost  = canopy * kwh_per_m2_yr * _kwh_rate;
                const revForMargin = hasLiveData ? liveRevYear : modelRev;
                const margin = revForMargin > 0 ? ((revForMargin - energyCost) / revForMargin * 100) : 0;
                document.getElementById('kpi-energy').innerText       = '$' + Math.round(energyCost).toLocaleString() + '/yr';
                document.getElementById('kpi-margin').innerText       = (margin > 0 ? '+' : '') + margin.toFixed(0) + '%';
                document.getElementById('kpi-margin').style.color     = margin > 30 ? 'var(--accent)' : margin > 0 ? 'var(--accent-gold)' : 'var(--danger)';
            }

            // ── VS MODEL comparison (pro-rated from model_snapshot) ───────────
            const snap     = FARM_DATA && FARM_DATA.model_snapshot;
            const snapPlant = snap && snap.plant ? snap.plant : snap;
            if (snapPlant && document.getElementById('kpi-model-canopy')) {
                const modelTotalArea = parseFloat(snapPlant.effective_grow_area || FARM_DATA.footprint || 0);
                const modelTotalRev  = parseFloat(snapPlant.annual_revenue    || 0);
                const modelTotalKg   = parseFloat(snapPlant.total_annual_kg   || 0);
                if (modelTotalArea > 0) {
                    const ratio      = canopy / modelTotalArea;
                    const mRev       = modelTotalRev * ratio;
                    const mKg        = modelTotalKg  * ratio;
                    const compareRev = hasLiveData ? liveRevYear : modelRev;
                    const deltaRev   = compareRev - mRev;
                    document.getElementById('kpi-model-canopy').innerText = modelTotalArea.toFixed(0) + ' m² total';
                    document.getElementById('kpi-model-yield').innerText  = Math.round(mKg).toLocaleString() + ' kg/yr';
                    document.getElementById('kpi-model-rev').innerText    = '$' + Math.round(mRev).toLocaleString() + '/yr';
                    document.getElementById('kpi-delta-rev').innerText    = (deltaRev >= 0 ? '+' : '') + '$' + Math.round(deltaRev).toLocaleString();
                    document.getElementById('kpi-delta-rev').style.color  = deltaRev >= 0 ? 'var(--accent)' : 'var(--danger)';
                } else {
                    ['kpi-model-canopy','kpi-model-yield','kpi-model-rev','kpi-delta-rev']
                        .forEach(id => { const el = document.getElementById(id); if(el) el.innerText = '—'; });
                }
            }

            // Aisle warning
            const peers = objects.filter(o => o.type === 'rack' && o.id !== selection.id);
            let minG = Infinity;
            peers.forEach(r => {
                const gx = Math.max(0, Math.max(selection.x, r.x) - Math.min(selection.x + selection.w, r.x + r.w));
                const gy = Math.max(0, Math.max(selection.y, r.y) - Math.min(selection.y + selection.h, r.y + r.h));
                const g  = Math.sqrt(gx*gx + gy*gy); if (g < minG && g < 5) minG = g;
            });
            const aw = document.getElementById('aisle-warn');
            if (aw) aw.style.display = (minG < 0.8 && minG > 0) ? 'block' : 'none';
        }

        function updateTankKPIs() {
            if (!selection || selection.type !== 'tank') return;
            const vol = selection.w * selection.h * (selection.height || 1.5);

            // ── Section 1: LIVE DATA from Harvest Tracker fish cycles ────────
            const tankCycles = _liveCycles.filter(c =>
                c.zone === selection.name && FISH_DATA && FISH_DATA[c.crop]
            );
            const activeFishCycles = tankCycles.filter(c => ['seeding','growing','ready'].includes(c.status));
            let hasLiveData = activeFishCycles.length > 0;
            let liveTankVol = 0, liveYieldCycle = 0, liveYieldYear = 0, liveRevYear = 0;

            if (hasLiveData) {
                activeFishCycles.forEach(c => {
                    const cVol  = parseFloat(c.area_m2) || vol;
                    liveTankVol += cVol;
                    const fData = FISH_DATA[c.crop];
                    if (fData) {
                        const stockDens  = fData.stocking_density  || 60;
                        const harvWt     = fData.harvest_weight_kg || 0.7;
                        const mortality  = (fData.mortality_rate   || 5) / 100;
                        const cycleDays  = fData.grow_cycle_days   || 210;
                        const price      = fData.price_base        || 4.10;
                        const fcr        = fData.feed_conversion_ratio || 1.5;
                        const feedPrice  = 1.20;
                        const fishPerBatch  = (cVol * stockDens) / harvWt;
                        const yieldPerCycle = fishPerBatch * (1 - mortality) * harvWt;
                        const cycles        = Math.max(Math.floor(365 / cycleDays), 1);
                        const annualYield   = yieldPerCycle * cycles;
                        const feedCost      = annualYield * fcr * feedPrice;
                        liveYieldCycle += yieldPerCycle;
                        liveYieldYear  += annualYield;
                        liveRevYear    += annualYield * price - feedCost;
                    }
                });
            }

            // ── Section 2: MODEL forecast (fallback or always shown in VS MODEL) ──
            let species = selection.species || null;
            if (!species && FARM_DATA && FARM_DATA.metadata && FARM_DATA.metadata.species)
                species = FARM_DATA.metadata.species;
            if (!species && FISH_DATA) species = Object.keys(FISH_DATA)[0];

            let modelYield = 0, modelRev = 0, cyclesEst = 1;
            const fData = species && FISH_DATA ? FISH_DATA[species] : null;
            if (fData) {
                const stockDens  = fData.stocking_density  || 60;
                const harvWt     = fData.harvest_weight_kg || 0.7;
                const mortality  = (fData.mortality_rate   || 5) / 100;
                const cycleDays  = fData.grow_cycle_days   || 210;
                const price      = fData.price_base        || 4.10;
                const fcr        = fData.feed_conversion_ratio || 1.5;
                const feedPrice  = 1.20;
                const fishPerBatch   = (vol * stockDens) / harvWt;
                const yieldPerCycle  = fishPerBatch * (1 - mortality) * harvWt;
                cyclesEst            = Math.max(Math.floor(365 / cycleDays), 1);
                modelYield           = yieldPerCycle * cyclesEst;
                const feedCost       = modelYield * fcr * feedPrice;
                modelRev             = modelYield * price - feedCost;
            }

            const margin = liveRevYear > 0 ? (liveRevYear / Math.max(liveRevYear + 100, 1) * 100)
                         : modelRev > 0 ? (modelRev / Math.max(modelRev + 100, 1) * 100) : 0;

            if (document.getElementById('kpi-tank-vol')) {
                if (hasLiveData) {
                    document.getElementById('kpi-tank-vol').innerText      = liveTankVol.toFixed(1) + ' m³ (live)';
                    document.getElementById('kpi-fish-cycle').innerText    = liveYieldCycle.toFixed(0) + ' kg';
                    document.getElementById('kpi-fish-year').innerText     = Math.round(liveYieldYear).toLocaleString() + ' kg/yr';
                    document.getElementById('kpi-fish-rev').innerText      = '$' + Math.round(liveRevYear).toLocaleString() + '/yr';
                } else {
                    document.getElementById('kpi-tank-vol').innerText      = vol.toFixed(1) + ' m³';
                    document.getElementById('kpi-fish-cycle').innerText    = (modelYield / Math.max(1, cyclesEst)).toFixed(0) + ' kg (est)';
                    document.getElementById('kpi-fish-year').innerText     = Math.round(modelYield).toLocaleString() + ' kg/yr (est)';
                    document.getElementById('kpi-fish-rev').innerText      = '$' + Math.round(modelRev).toLocaleString() + '/yr (est)';
                }
                const revForMargin = hasLiveData ? liveRevYear : modelRev;
                const feedCostEst  = modelYield * (fData ? fData.feed_conversion_ratio || 1.5 : 1.5) * 1.20;
                const m = revForMargin > 0 ? ((revForMargin - feedCostEst) / revForMargin * 100) : 0;
                document.getElementById('kpi-fish-margin').innerText    = (m > 0 ? '+' : '') + m.toFixed(0) + '%';
                document.getElementById('kpi-fish-margin').style.color  = m > 30 ? '#2ecc71' : m > 0 ? '#f1c40f' : '#e74c3c';
            }

            // ── VS MODEL comparison ──────────────────────────────────────────
            const snap     = FARM_DATA && FARM_DATA.model_snapshot;
            const snapFish = snap && snap.fish ? snap.fish : null;
            if (snapFish && document.getElementById('kpi-model-tank-vol')) {
                const modelTotalVol   = parseFloat((FARM_DATA.metadata && FARM_DATA.metadata.tank_volume_m3) || 0);
                const modelFishRev    = parseFloat(snapFish.annual_revenue  || 0);
                const modelFishYield  = parseFloat(snapFish.total_annual_kg || 0);
                if (modelTotalVol > 0) {
                    const ratio      = vol / modelTotalVol;
                    const mRev       = modelFishRev   * ratio;
                    const mKg        = modelFishYield * ratio;
                    const compareRev = hasLiveData ? liveRevYear : modelRev;
                    const deltaRev   = compareRev - mRev;
                    document.getElementById('kpi-model-tank-vol').innerText   = modelTotalVol.toFixed(0) + ' m³ total';
                    document.getElementById('kpi-model-fish-yield').innerText = Math.round(mKg).toLocaleString() + ' kg/yr';
                    document.getElementById('kpi-model-fish-rev').innerText   = '$' + Math.round(mRev).toLocaleString() + '/yr';
                    document.getElementById('kpi-delta-fish-rev').innerText   = (deltaRev >= 0 ? '+' : '') + '$' + Math.round(deltaRev).toLocaleString();
                    document.getElementById('kpi-delta-fish-rev').style.color = deltaRev >= 0 ? 'var(--accent)' : 'var(--danger)';
                } else {
                    ['kpi-model-tank-vol','kpi-model-fish-yield','kpi-model-fish-rev','kpi-delta-fish-rev']
                        .forEach(id => { const el = document.getElementById(id); if(el) el.innerText = '—'; });
                }
            }
        }

        function drawOverlays() {
            ctx.save();
            ctx.globalAlpha = 1.0;
            const sbX=14, sbY=canvas.height-22, spx=10*zoom;
            ctx.strokeStyle='#ccc'; ctx.lineWidth=1.5;
            ctx.beginPath();
            ctx.moveTo(sbX,sbY); ctx.lineTo(sbX+spx,sbY);
            ctx.moveTo(sbX,sbY-3); ctx.lineTo(sbX,sbY+3);
            ctx.moveTo(sbX+spx,sbY-3); ctx.lineTo(sbX+spx,sbY+3);
            ctx.stroke();
            ctx.fillStyle='#ccc'; ctx.font='bold 9px Inter'; ctx.textAlign='center';
            ctx.fillText('10 m', sbX+spx/2, sbY-5);
            if(window.lastWorld) {
                ctx.textAlign='right'; ctx.fillStyle='#555'; ctx.font='9px Inter';
                ctx.fillText('x:'+window.lastWorld.x.toFixed(1)+'m  y:'+window.lastWorld.y.toFixed(1)+'m', canvas.width-6, canvas.height-6);
            }
            const cx=canvas.width-36, cy=36, r=20;
            ctx.fillStyle='rgba(0,0,0,0.55)';
            ctx.beginPath(); ctx.arc(cx,cy,r+3,0,Math.PI*2); ctx.fill();
            ctx.strokeStyle='#333'; ctx.lineWidth=1;
            ctx.beginPath(); ctx.arc(cx,cy,r,0,Math.PI*2); ctx.stroke();
            ['N','E','S','W'].forEach((l,i)=>{
                const a=(northDeg+i*90-90)*Math.PI/180;
                ctx.fillStyle=l==='N'?'#f1c40f':'#555';
                ctx.font='bold 8px Inter'; ctx.textAlign='center';
                ctx.fillText(l, cx+(r-5)*Math.cos(a), cy+(r-5)*Math.sin(a)+3);
            });
            const nRad=(northDeg-90)*Math.PI/180;
            ctx.fillStyle='#f1c40f';
            ctx.beginPath();
            ctx.moveTo(cx+r*Math.cos(nRad), cy+r*Math.sin(nRad));
            ctx.lineTo(cx+5*Math.cos(nRad+2.3), cy+5*Math.sin(nRad+2.3));
            ctx.lineTo(cx,cy);
            ctx.lineTo(cx+5*Math.cos(nRad-2.3), cy+5*Math.sin(nRad-2.3));
            ctx.closePath(); ctx.fill();
            if(FARM_DATA&&FARM_DATA.footprint>0&&!objects.some(o=>o.type==='building')) {
                const side=Math.sqrt(FARM_DATA.footprint);
                ctx.strokeStyle='rgba(52,152,219,0.35)'; ctx.lineWidth=1.5;
                ctx.setLineDash([8,6]);
                ctx.strokeRect(offsetX, offsetY, side*zoom, side*zoom);
                ctx.setLineDash([]);
                ctx.fillStyle='rgba(52,152,219,0.45)'; ctx.font='10px Inter'; ctx.textAlign='left';
                ctx.fillText('Design boundary: '+FARM_DATA.footprint.toFixed(0)+'m²', offsetX+4, offsetY-4);
            }
            ctx.restore(); ctx.textAlign='left';
        }
        function drawCycleOverlay() {
            if(!isOpsMode) return;
            const sc={seeding:'rgba(52,152,219,0.55)',growing:'rgba(46,204,113,0.55)',ready:'rgba(241,196,15,0.65)',failed:'rgba(231,76,60,0.55)'};
            objects.forEach(o=>{
                if(o.type!=='rack' && o.type!=='tank') return;
                const rx=o.x*zoom+offsetX, ry=o.y*zoom+offsetY, rw=o.w*zoom, rh=o.h*zoom;
                const st=o.cycleStatus||'';
                ctx.save(); ctx.globalAlpha=1;
                ctx.fillStyle=sc[st]||'rgba(80,80,80,0.3)';
                ctx.fillRect(rx,ry,rw,rh);
                if(st){ctx.fillStyle='#fff';ctx.font='bold 9px Inter';ctx.fillText(st.toUpperCase(),rx+4,ry+rh-6);}
                ctx.restore();
            });
        }
        window.handleToolChange = () => {
            const tool = document.getElementById('toolSelect').value;
            selection = null; // Clear selection when switching tools
            if (tool !== 'select' && tool !== 'measure') {
                document.getElementById('no-selection').style.display = 'none';
                document.getElementById('editor-ui').style.display = 'flex';
                document.getElementById('building-ui').style.display = tool === 'building' ? 'block' : 'none';
                document.getElementById('rack-ui').style.display = ['rack','wall_rack','tower_rack','single_shelf'].includes(tool) ? 'block' : 'none';
                document.getElementById('tank-ui').style.display = tool === 'tank' ? 'block' : 'none';
                // Set subtype based on tool
                if (tool === 'wall_rack')    { setTimeout(()=>setRackSubtype('wall'),50); }
                else if (tool === 'tower_rack')  { setTimeout(()=>setRackSubtype('tower'),50); }
                else if (tool === 'single_shelf'){ setTimeout(()=>setRackSubtype('bench'),50); }
                else if (tool === 'rack')        { setTimeout(()=>setRackSubtype('standard'),50); }
                document.getElementById('equip-ui').style.display = tool === 'equip' ? 'block' : 'none';
                document.getElementById('path-ui').style.display = tool === 'path' ? 'block' : 'none';
                if(tool === 'building') window.toggleSpanUI(); 
            } else {
                showInspector(false);
            }
            draw();
        };

        window.onload = () => {
            resizeCanvas();

            // Restore Navigation Keys
            window.addEventListener('keydown', e => { if(e.code === 'Space') spacePressed = true; });
            window.addEventListener('keyup', e => { if(e.code === 'Space') { spacePressed = false; isPanning = false; } });

            canvas.addEventListener('mousedown', startAction);
            window.addEventListener('mousemove', moveAction);
            window.addEventListener('mouseup', endAction);
            canvas.addEventListener('wheel', handleZoom, {passive: false});
            // Parametric Inputs
            document.getElementById('objName').addEventListener('input', e => { if(selection){ selection.name = e.target.value; draw(); sync3D(); } });
            document.getElementById('buildWidth').addEventListener('input', e => { if(selection){ selection.w = parseFloat(e.target.value); checkSafety(); draw(); sync3D(); updateStats(); } });
            document.getElementById('buildLength').addEventListener('input', e => { if(selection){ selection.h = parseFloat(e.target.value); checkSafety(); draw(); sync3D(); updateStats(); } });
            document.getElementById('buildHeight').addEventListener('input', e => { if(selection){ selection.height = parseFloat(e.target.value); checkSafety(); sync3D(); updateStats(); } });
            document.getElementById('buildType').addEventListener('input', e => { if(selection){ selection.subType = e.target.value; checkSafety(); sync3D(); draw(); window.toggleSpanUI(); } }); // New listener for building type
            document.getElementById('standardSpan').addEventListener('input', e => { 
                if(selection && selection.type === 'building' && selection.subType === 'polytunnel'){
                    selection.w = parseFloat(e.target.value);
                    selection.height = selection.w / 2.1; // Update height based on new span
                    checkSafety(); sync3D(); draw(); updateStats();
                }
            });
            ['rackWidth', 'rackLength', 'rackHeight'].forEach(id => {
                document.getElementById(id).addEventListener('input', e => {
                    if(selection && selection.type === 'rack'){
                        const val = parseFloat(e.target.value);
                        // Wall rack: whichever axis is the thickness (short axis) is locked at 0.30m
                        if (selection.rackType === 'wall') {
                            const portrait = selection.h >= selection.w;
                            if ((id === 'rackWidth'  &&  portrait) ||
                                (id === 'rackLength' && !portrait)) {
                                e.target.value = '0.30';
                                if (portrait) selection.w = 0.30; else selection.h = 0.30;
                                selection.wallThickness = 0.30;
                                updateRackKPIs(); updateStats(); draw(); sync3D();
                                return;
                            }
                        }
                        if (id === 'rackWidth') selection.w = val;
                        if (id === 'rackLength') selection.h = val;
                        if (id === 'rackHeight') selection.height = val;
                        
                        if (id === 'rackHeight' && selection.rackType === 'standard') {
                             selection.spacing = selection.height / Math.max(1, selection.layers);
                             document.getElementById('layerSpacing').value = selection.spacing.toFixed(2);
                        }

                        autoAdjustCeiling(); updateRackKPIs(); updateStats(); draw(); sync3D();
                    }
                });
            });

            document.getElementById('objLayers').addEventListener('input', e => {
                if(selection){
                    selection.layers=parseInt(e.target.value);
                    if(!selection.crops) selection.crops=[];
                    if(!selection.layerStatus) selection.layerStatus=[];
                    if(selection.rackType === 'standard') {
                        selection.spacing = selection.height / Math.max(1, selection.layers);
                        document.getElementById('layerSpacing').value = selection.spacing.toFixed(2);
                    }
                    autoAdjustCeiling(); updateRackKPIs(); updateStats(); sync3D();
                }
            });

            document.getElementById('layerSpacing').addEventListener('input', e => {
                if(selection && selection.type === 'rack'){
                    selection.spacing = parseFloat(e.target.value);
                    if (selection.rackType === 'standard') {
                        selection.height = selection.spacing * selection.layers + 0.3;
                        document.getElementById('rackHeight').value = selection.height.toFixed(2);
                    }
                    autoAdjustCeiling();
                    sync3D();
                }
            });

            document.getElementById('towerPlants').addEventListener('input', e => {
                if(selection && selection.type === 'rack' && selection.rackType === 'tower'){
                    selection.layers = parseInt(e.target.value);
                    sync3D(); updateStats(); updateRackKPIs();
                }
            });
            document.getElementById('tankDepth').addEventListener('input', e => { 
                if(selection && selection.type === 'tank'){
                    selection.height = parseFloat(e.target.value);
                    sync3D(); updateStats();
                }
            });
            document.getElementById('tankWidth').addEventListener('input', e => { if(selection){ selection.w = parseFloat(e.target.value); draw(); sync3D(); updateStats(); } });
            document.getElementById('tankLength').addEventListener('input', e => { if(selection){ selection.h = parseFloat(e.target.value); draw(); sync3D(); updateStats(); } });
            document.getElementById('pathWidth').addEventListener('input', e => { if(selection){ selection.w = parseFloat(e.target.value); draw(); sync3D(); } });
            document.getElementById('pathLength').addEventListener('input', e => { if(selection){ selection.h = parseFloat(e.target.value); draw(); sync3D(); } });
            document.getElementById('equipType').addEventListener('change', e => { if(selection){ selection.subType = e.target.value; draw(); sync3D(); updateStats(); } });
            document.getElementById('equipHeight').addEventListener('input', e => { if(selection){ selection.height = parseFloat(e.target.value); checkSafety(); draw(); sync3D(); updateStats(); } });

            const confirmBtn = document.getElementById('custom-confirm-yes');
            if(confirmBtn) {
                confirmBtn.addEventListener('click', () => {
                    if (_confirmCallback) _confirmCallback();
                    closeCustomConfirm();
                });
            }

            animate();
            window.toggleSpanUI(); // Call on load to set initial state
            sync3D();
            draw();
        };

        let _confirmCallback = null;
        function customConfirm(msg, onYes) {
            const modal = document.getElementById('custom-confirm-modal');
            if(modal) {
                document.getElementById('custom-confirm-msg').innerHTML = msg;
                _confirmCallback = onYes;
                modal.style.display = 'block';
            }
        }
        function closeCustomConfirm() {
            const modal = document.getElementById('custom-confirm-modal');
            if(modal) modal.style.display = 'none';
            _confirmCallback = null;
        }

        function getResizeHandle(worldX, worldY, sel) {
            if (!sel || sel.type !== 'rack') return null;
            const t = 10 / zoom; // 10px hit area
            const x = sel.x, y = sel.y, w = sel.w, h = sel.h;
            
            const onLeft = Math.abs(worldX - x) <= t && worldY >= y - t && worldY <= y + h + t;
            const onRight = Math.abs(worldX - (x + w)) <= t && worldY >= y - t && worldY <= y + h + t;
            const onTop = Math.abs(worldY - y) <= t && worldX >= x - t && worldX <= x + w + t;
            const onBottom = Math.abs(worldY - (y + h)) <= t && worldX >= x - t && worldX <= x + w + t;

            if (onTop && onLeft) return 'nw';
            if (onTop && onRight) return 'ne';
            if (onBottom && onLeft) return 'sw';
            if (onBottom && onRight) return 'se';
            if (onTop) return 'n';
            if (onBottom) return 's';
            if (onLeft) return 'w';
            if (onRight) return 'e';

            return null;
        }

        function startAction(e) {
            const r = canvas.getBoundingClientRect();
            const world = toWorld(e.clientX - r.left, e.clientY - r.top);
            const tool = document.getElementById('toolSelect').value;
            window.lastMouse = { x: e.clientX, y: e.clientY };

            if (spacePressed || e.button === 1) { isPanning = true; return; }

            if (tool === 'select' || isOpsMode) {
                if (selection && !isOpsMode) {
                    const handle = getResizeHandle(world.x, world.y, selection);
                    if (handle) {
                        isResizing = true;
                        resizeHandle = handle;
                        resizeStartMouse = { x: world.x, y: world.y };
                        resizeStartRect = { x: selection.x, y: selection.y, w: selection.w, h: selection.h };
                        return;
                    }
                }

                // LAYER PRIORITY SEARCH: Search from most specific to least specific
                const priorityOrder = ['measure', 'rack', 'wall_rack', 'tower_rack', 'single_shelf', 'tank', 'equip', 'path', 'entry', 'building', 'plot'];
                let found = null;
                
                for (const type of priorityOrder) {
                    found = [...objects].reverse().find(o => 
                        o.type === type &&
                        world.x >= o.x && world.x <= o.x + o.w && 
                        world.y >= o.y && world.y <= o.y + o.h
                    );
                    if (found) break;
                }

                if (found) {
                    selection = found;
                    showInspector(true);
                    if (!isOpsMode) {
                        isDragging = true;
                        dragOffset = { x: world.x - selection.x, y: world.y - selection.y };
                    }
                } else if (!isOpsMode) {
                    selection = null;
                    showInspector(false);
                    isDrawing = true; // Start marquee selection
                    rectStart = world;
                }
            } else {
                // Drawing begins using the settings currently visible in the UI
                isDrawing = true;
                rectStart = world;
            }
            draw();
        }

        // UI Helper
        window.toggleSpanUI = () => {
            const type = document.getElementById('buildType').value;
            document.getElementById('span-selector').style.display = (type === 'polytunnel') ? 'block' : 'none';
            document.getElementById('buildWidth').disabled = (type === 'polytunnel');
            if(selection) { selection.subType = type; sync3D(); draw(); }
        };
        function moveAction(e) {
            const r = canvas.getBoundingClientRect();
            window.lastWorld = toWorld(e.clientX - r.left, e.clientY - r.top);
            
            if (isPanning) {
                offsetX += e.clientX - window.lastMouse.x;
                offsetY += e.clientY - window.lastMouse.y;
                window.lastMouse = { x: e.clientX, y: e.clientY };
                canvas.style.cursor = 'grabbing';
            } else if (isResizing && selection && resizeHandle) {
                let newX = resizeStartRect.x;
                let newY = resizeStartRect.y;
                let newW = resizeStartRect.w;
                let newH = resizeStartRect.h;
                
                if (resizeHandle.includes('n')) {
                    const dy = window.lastWorld.y - resizeStartMouse.y;
                    let proposedY = snapVal(resizeStartRect.y + dy);
                    let proposedH = resizeStartRect.h - (proposedY - resizeStartRect.y);
                    if (proposedH >= 0.1) { newY = proposedY; newH = proposedH; }
                }
                if (resizeHandle.includes('s')) {
                    const dy = window.lastWorld.y - resizeStartMouse.y;
                    let proposedH = snapVal(resizeStartRect.h + dy);
                    if (proposedH >= 0.1) newH = proposedH;
                }
                if (resizeHandle.includes('w')) {
                    const dx = window.lastWorld.x - resizeStartMouse.x;
                    let proposedX = snapVal(resizeStartRect.x + dx);
                    let proposedW = resizeStartRect.w - (proposedX - resizeStartRect.x);
                    if (proposedW >= 0.1) { newX = proposedX; newW = proposedW; }
                }
                if (resizeHandle.includes('e')) {
                    const dx = window.lastWorld.x - resizeStartMouse.x;
                    let proposedW = snapVal(resizeStartRect.w + dx);
                    if (proposedW >= 0.1) newW = proposedW;
                }
                
                selection.x = newX;
                selection.y = newY;
                selection.w = newW;
                selection.h = newH;
                
                showInspector(true);
                autoAdjustCeiling();
                updateRackKPIs();
                sync3D();
            } else if (isDragging && selection && !isOpsMode) {
                if (selection.type === 'measure') {
                    const newX = snapVal(window.lastWorld.x - dragOffset.x);
                    const newY = snapVal(window.lastWorld.y - dragOffset.y);
                    const dx = newX - selection.x;
                    const dy = newY - selection.y;
                    selection.startX += dx;
                    selection.endX += dx;
                    selection.startY += dy;
                    selection.endY += dy;
                    selection.x = newX;
                    selection.y = newY;
                } else {
                    selection.x = snapVal(window.lastWorld.x - dragOffset.x);
                    selection.y = snapVal(window.lastWorld.y - dragOffset.y);
                }
                autoAdjustCeiling();
                canvas.style.cursor = 'move';
                sync3D();
            } else {
                const tool = document.getElementById('toolSelect')?.value;
                if (!isDrawing && !isOpsMode && tool === 'select' && selection) {
                    const handle = getResizeHandle(window.lastWorld.x, window.lastWorld.y, selection);
                    if (handle) {
                        canvas.style.cursor = handle + '-resize';
                    } else if (
                        window.lastWorld.x >= selection.x && window.lastWorld.x <= selection.x + selection.w &&
                        window.lastWorld.y >= selection.y && window.lastWorld.y <= selection.y + selection.h
                    ) {
                        canvas.style.cursor = 'move';
                    } else {
                        canvas.style.cursor = 'default';
                    }
                } else {
                    canvas.style.cursor = (spacePressed || e.button === 1) ? 'grab' : (isDrawing ? 'crosshair' : 'default');
                }
            }
            draw();
        }

        function endAction() {
            if (isOpsMode) {
                isDrawing = false; isDragging = false; isPanning = false; rectStart = null;
                return;
            }

            if (isResizing) {
                isResizing = false;
                resizeHandle = null;
                updateStats(); sync3D(); draw(); notifyParent();
                return;
            }

            if (isDrawing && rectStart && window.lastWorld) {
                const tool = document.getElementById('toolSelect').value;
                let fw = Math.abs(window.lastWorld.x - rectStart.x);
                let fh = Math.abs(window.lastWorld.y - rectStart.y);
                const dx = (window.lastWorld.x >= rectStart.x) ? 1 : -1;
                const dy = (window.lastWorld.y >= rectStart.y) ? 1 : -1;

                if (tool === 'select') {
                    const x1 = Math.min(rectStart.x, window.lastWorld.x);
                    const y1 = Math.min(rectStart.y, window.lastWorld.y);
                    const x2 = Math.max(rectStart.x, window.lastWorld.x);
                    const y2 = Math.max(rectStart.y, window.lastWorld.y);

                    // MULTI-SELECT LOGIC: Only select if ENTIRELY inside
                    // We prioritize the "top" object in the group that fits
                    const priorityOrder = ['rack', 'wall_rack', 'tower_rack', 'single_shelf', 'tank', 'equip', 'path', 'entry', 'building', 'plot'];
                    let found = null;

                    for (const type of priorityOrder) {
                        found = objects.find(o => 
                            o.type === type &&
                            o.x >= x1 && (o.x + o.w) <= x2 &&
                            o.y >= y1 && (o.y + o.h) <= y2
                        );
                        if (found) break;
                    }

                    if (found) {
                        selection = found;
                        showInspector(true);
                    }
                } else if (tool === 'building') {
                    const bt = document.getElementById('buildType').value;
                    if (bt === 'polytunnel') fw = parseFloat(document.getElementById('standardSpan').value);
                    objects.push({
                        id: Date.now(), name: bt.toUpperCase(), type: 'building', subType: bt,
                        x: dx > 0 ? rectStart.x : rectStart.x - fw,
                        y: dy > 0 ? rectStart.y : rectStart.y - fh,
                        w: fw, h: fh, height: bt === 'polytunnel' ? fw/2.1 : 4.0, layers: 1, crops: []
                    });
                } else if (tool === 'equip') {
                    const eType = document.getElementById('equipType').value;
                    objects.push({
                        id: Date.now(), name: eType.toUpperCase() + "_" + (objects.length + 1), type: 'equip', subType: eType,
                        x: dx > 0 ? rectStart.x : rectStart.x - fw,
                        y: dy > 0 ? rectStart.y : rectStart.y - fh,
                        w: fw, h: fh, height: parseFloat(document.getElementById('equipHeight').value) || 2.0
                    });
                } else if (tool === 'tank') {
                    objects.push({
                        id: Date.now(), name: "TANK_" + (objects.length + 1), type: 'tank',
                        x: dx > 0 ? rectStart.x : rectStart.x - fw,
                        y: dy > 0 ? rectStart.y : rectStart.y - fh,
                        w: fw, h: fh, height: 1.5, // Default depth 1.5m
                        layers: 1, crops: []
                    });
                } else if (tool === 'path') {
                    objects.push({
                        id: Date.now(), name: "PATH_" + (objects.length + 1), type: 'path',
                        x: dx > 0 ? rectStart.x : rectStart.x - fw,
                        y: dy > 0 ? rectStart.y : rectStart.y - fh,
                        w: fw, h: fh, height: 0.1
                    });
                } else if (['rack', 'wall_rack', 'tower_rack', 'single_shelf'].includes(tool)) {
                    const sx=snapVal(dx>0?rectStart.x:rectStart.x-fw);
                    const sy=snapVal(dy>0?rectStart.y:rectStart.y-fh);
                    const dc=(FARM_CROPS&&FARM_CROPS[0])||'None';
                    let rType = 'standard';
                    let w = Math.max(0.1, snapVal(fw));
                    let h = Math.max(0.1, snapVal(fh));
                    let lH = 2.5, lL = 5, lS = 0.6;
                    if (tool === 'tower_rack') {
                        rType = 'tower';
                        lL = 20;
                        lS = 0.15;
                        lH = 2.0;
                    } else if (tool === 'wall_rack') {
                        rType = 'wall';
                        lL = 1;
                        lH = 2.4;
                        lS = 0.0;
                    } else if (tool === 'single_shelf') {
                        rType = 'bench';
                        lL = 1;
                        lS = 0.0;
                        lH = 0.9;
                    }
                    objects.push({id:Date.now(),name:'RACK_'+(objects.filter(o=>o.type==='rack').length+1),
                        type:'rack',rackType:rType,x:sx,y:sy,w:w,h:h,
                        height:lH,layers:lL,spacing:lS,crops:Array(lL).fill(dc),layerStatus:[],cycleStatus:''});
                } else if (tool === 'measure') {
                    let mStartX = document.getElementById('snapToggle')?.checked ? snapVal(rectStart.x) : rectStart.x;
                    let mStartY = document.getElementById('snapToggle')?.checked ? snapVal(rectStart.y) : rectStart.y;
                    let mEndX = document.getElementById('snapToggle')?.checked ? snapVal(window.lastWorld.x) : window.lastWorld.x;
                    let mEndY = document.getElementById('snapToggle')?.checked ? snapVal(window.lastWorld.y) : window.lastWorld.y;
                    if (Math.abs(mEndX - mStartX) > 0.1 || Math.abs(mEndY - mStartY) > 0.1) {
                        objects.push({
                            id: Date.now(), name: "MEASURE_" + (objects.filter(o=>o.type==='measure').length + 1), type: 'measure',
                            x: Math.min(mStartX, mEndX) - 0.2, y: Math.min(mStartY, mEndY) - 0.2,
                            w: Math.abs(mEndX - mStartX) + 0.4, h: Math.abs(mEndY - mStartY) + 0.4,
                            startX: mStartX, startY: mStartY, endX: mEndX, endY: mEndY
                        });
                    }
                } else {
                    objects.push({id:Date.now(),name:tool.toUpperCase(),type:tool,
                        x:snapVal(dx>0?rectStart.x:rectStart.x-fw),y:snapVal(dy>0?rectStart.y:rectStart.y-fh),
                        w:snapVal(fw),h:snapVal(fh),height:2.5,layers:5,spacing:0.6,crops:[]});
                }
            }
            isDrawing = false; isDragging = false; rectStart = null;
            updateStats(); sync3D(); draw(); notifyParent();
        }
        function isPointInObj(p, obj) {
            return p.x >= obj.x && p.x <= obj.x + obj.w && p.y >= obj.y && p.y <= obj.y + obj.h;
        }

        function showInspector(show) {
            document.getElementById('no-selection').style.display = show ? 'none' : 'block';
            document.getElementById('editor-ui').style.display = show ? 'flex' : 'none';
            const sp = document.getElementById('farm-summary-panel');
            if (sp) sp.style.display = show ? 'none' : 'none'; // always hide on selection
            if (!show) { hideOpsCyclePanel(); hideTankCyclePanel(); }
            if (show && selection) {
                document.getElementById('objName').value = selection.name;
                document.getElementById('building-ui').style.display = selection.type === 'building' ? 'block' : 'none';
                document.getElementById('rack-ui').style.display = selection.type === 'rack' ? 'block' : 'none';
                document.getElementById('tank-ui').style.display = selection.type === 'tank' ? 'block' : 'none';
                document.getElementById('equip-ui').style.display = selection.type === 'equip' ? 'block' : 'none';
                document.getElementById('path-ui').style.display = selection.type === 'path' ? 'block' : 'none';

                if(selection.type === 'tank') {
                    document.getElementById('tankWidth').value = selection.w.toFixed(2);
                    document.getElementById('tankLength').value = selection.h.toFixed(2);
                    document.getElementById('tankDepth').value = selection.height.toFixed(1);
                    updateTankKPIs();
                    if (isOpsMode) { showTankCyclePanel(selection); hideOpsCyclePanel(); }
                    else { hideTankCyclePanel(); hideOpsCyclePanel(); }
                }
                if(selection.type === 'equip') {
                    document.getElementById('equipType').value = selection.subType || 'hvac';
                    document.getElementById('equipHeight').value = selection.height.toFixed(1);
                }
                if(selection.type === 'path') {
                    document.getElementById('pathWidth').value = selection.w.toFixed(2);
                    document.getElementById('pathLength').value = selection.h.toFixed(2);
                }
                if(selection.type === 'building') {
                    document.getElementById('buildHeight').value = selection.height.toFixed(2);
                    document.getElementById('buildWidth').value = selection.w.toFixed(2);
                    document.getElementById('buildLength').value = selection.h.toFixed(2);
                    document.getElementById('buildType').value = selection.subType || 'warehouse';
                    window.toggleSpanUI();
                    if (selection.subType === 'polytunnel') {
                        document.getElementById('standardSpan').value = selection.w.toFixed(1);
                    }
                }
                if(selection.type === 'rack') {
                    const rt = selection.rackType || 'standard';
                    document.getElementById('rackWidth').value  = selection.w.toFixed(2);
                    document.getElementById('rackHeight').value = (selection.height || 2.5).toFixed(2);
                    if (selection.rackType === 'wall') {
                        // Show correct values based on orientation
                        const portrait = selection.h > selection.w;
                        document.getElementById('rackWidth').value  = portrait ? '0.30' : selection.w.toFixed(2);
                        document.getElementById('rackLength').value = portrait ? selection.h.toFixed(2) : '0.30';
                        // Re-apply wall rack UI state
                        setTimeout(()=>setRackSubtype('wall'), 10);
                    } else {
                        document.getElementById('rackWidth').value  = selection.w.toFixed(2);
                        document.getElementById('rackLength').value = selection.h.toFixed(2);
                    }
                    document.getElementById('objLayers').value = selection.layers;
                    document.getElementById('layerSpacing').value = selection.spacing || 0.6;
                    if(selection.rackType === 'tower') setTowerShape(selection.towerShape || 'round');
                    document.getElementById('towerPlants').value  = selection.layers || 20;
                    if (selection.rackType === 'tower') {
                        setTimeout(() => setTowerShape(selection.towerShape || 'round'), 15);
                    }
                    setRackSubtype(rt);
                    updateRackKPIs();
                    if (isOpsMode) { showOpsCyclePanel(selection); hideTankCyclePanel(); }
                    else { hideOpsCyclePanel(); hideTankCyclePanel(); }
                } else if (selection.type !== 'tank') {
                    hideOpsCyclePanel();
                    hideTankCyclePanel();
                }
            }
        }

        function handleZoom(e) {
            e.preventDefault();
            const delta = e.deltaY > 0 ? 0.9 : 1.1;
            const rect = canvas.getBoundingClientRect();
            const mX = e.clientX - rect.left;
            const mY = e.clientY - rect.top;
            const worldM = toWorld(mX, mY);
            zoom = Math.min(Math.max(zoom * delta, 5), 200);
            offsetX = mX - worldM.x * zoom;
            offsetY = mY - worldM.y * zoom;
            draw();
        }

        function autoAdjustCeiling() {
            if (!selection || selection.type !== 'rack') return;
            // Calculate minimum height: rack height + buffer
            const requiredHeight = (selection.height || 2.5) + 0.5;
            
            // Find the building containing this rack
            const building = objects.find(o => o.type === 'building' && 
                selection.x >= o.x && (selection.x + selection.w) <= (o.x + o.w) &&
                selection.y >= o.y && (selection.y + selection.h) <= (o.y + o.h));
            
            if (building && building.height < requiredHeight) {
                building.height = requiredHeight;
            }
        }

        function checkSafety() {
            let conflict = false;
            const warnMsg = document.getElementById('warn-msg');
            objects.forEach(o => o.isWarning = false);

            const plots = objects.filter(o => o.type === 'plot');
            const buildings = objects.filter(o => o.type === 'building');
            const racks = objects.filter(o => o.type === 'rack');

            buildings.forEach(b => {
                // Plot Constraint: Building must be inside a plot
                if (plots.length > 0) {
                    const insidePlot = plots.some(p => 
                        b.x >= p.x && (b.x + b.w) <= (p.x + p.w) &&
                        b.y >= p.y && (b.y + b.h) <= (p.y + p.h)
                    );
                    if (!insidePlot) { b.isWarning = true; conflict = true; }
                }
            });

            racks.forEach(rack => {
                const building = buildings.find(b => 
                    rack.x >= b.x && (rack.x + rack.w) <= (b.x + b.w) &&
                    rack.y >= b.y && (rack.y + rack.h) <= (b.y + b.h)
                );
                const totalRackHeight = rack.height || ((rack.layers * (rack.spacing || 0.6)) + 0.5);
                if (!building || totalRackHeight > building.height - 0.2) {
                    rack.isWarning = true;
                    conflict = true;
                }
            });

            if (warnMsg) warnMsg.style.display = conflict ? 'block' : 'none';
        }

        function deleteSelected() {
            if(!selection) return;
            if (selection.type === 'measure') {
                executeDelete();
            } else {
                customConfirm(`Delete <span style="color:#e74c3c;font-weight:bold;">${selection.name}</span>?`, executeDelete);
            }
        }
        function executeDelete() {
            if(!selection) return;
            objects = objects.filter(o => o.id !== selection.id);
            selection = null; showInspector(false);
            updateStats(); sync3D(); draw(); notifyParent();
        }

        function drawAlignmentGuides(activeRect, activeId) {
            const peers = objects.filter(o => o.id !== activeId && o.type !== 'plot' && o.type !== 'path');
            if (peers.length === 0) return;

            let closestX = null, minDistX = Infinity;
            let closestY = null, minDistY = Infinity;

            const ax1 = activeRect.x, ax2 = activeRect.x + activeRect.w;
            const ay1 = activeRect.y, ay2 = activeRect.y + activeRect.h;

            ctx.save();
            ctx.strokeStyle = "rgba(52, 152, 219, 0.8)";
            ctx.fillStyle = "rgba(52, 152, 219, 1.0)";
            ctx.lineWidth = 1;
            ctx.setLineDash([4, 4]);
            ctx.font = "10px Inter";

            peers.forEach(p => {
                const px1 = p.x, px2 = p.x + p.w;
                const py1 = p.y, py2 = p.y + p.h;
                
                [px1, px2].forEach(xEdge => {
                    if (Math.abs(ax1 - xEdge) < 0.05 || Math.abs(ax2 - xEdge) < 0.05) {
                        ctx.beginPath(); ctx.moveTo(xEdge * zoom + offsetX, 0); ctx.lineTo(xEdge * zoom + offsetX, canvas.height); ctx.stroke();
                    }
                });

                [py1, py2].forEach(yEdge => {
                    if (Math.abs(ay1 - yEdge) < 0.05 || Math.abs(ay2 - yEdge) < 0.05) {
                        ctx.beginPath(); ctx.moveTo(0, yEdge * zoom + offsetY); ctx.lineTo(canvas.width, yEdge * zoom + offsetY); ctx.stroke();
                    }
                });
                
                if (ay2 > py1 && ay1 < py2) {
                    let dX = Infinity;
                    if (ax2 <= px1) dX = px1 - ax2;
                    else if (ax1 >= px2) dX = ax1 - px2;
                    if (dX > 0 && dX < minDistX) { minDistX = dX; closestX = p; }
                }
                
                if (ax2 > px1 && ax1 < px2) {
                    let dY = Infinity;
                    if (ay2 <= py1) dY = py1 - ay2;
                    else if (ay1 >= py2) dY = ay1 - py2;
                    if (dY > 0 && dY < minDistY) { minDistY = dY; closestY = p; }
                }
            });

            ctx.setLineDash([]);
            ctx.strokeStyle = "#c0573a";
            ctx.fillStyle = "#c0573a";

            if (closestX && minDistX < 20) {
                const px1 = closestX.x, px2 = closestX.x + closestX.w;
                const overlapY1 = Math.max(ay1, closestX.y);
                const overlapY2 = Math.min(ay2, closestX.y + closestX.h);
                const lineY = ((overlapY1 + overlapY2) / 2) * zoom + offsetY;
                let lineX1 = ax2 * zoom + offsetX;
                let lineX2 = px1 * zoom + offsetX;
                if (ax1 >= px2) { lineX1 = px2 * zoom + offsetX; lineX2 = ax1 * zoom + offsetX; }
                ctx.beginPath(); ctx.moveTo(lineX1, lineY); ctx.lineTo(lineX2, lineY); ctx.stroke();
                ctx.beginPath(); ctx.moveTo(lineX1, lineY); ctx.lineTo(lineX1+5, lineY-3); ctx.lineTo(lineX1+5, lineY+3); ctx.fill();
                ctx.beginPath(); ctx.moveTo(lineX2, lineY); ctx.lineTo(lineX2-5, lineY-3); ctx.lineTo(lineX2-5, lineY+3); ctx.fill();
                ctx.textAlign = "center";
                let tX = (lineX1 + lineX2) / 2;
                let tY = lineY - 5;
                tX = Math.max(30, Math.min(canvas.width - 30, tX));
                tY = Math.max(10, Math.min(canvas.height - 10, tY));
                ctx.fillText(minDistX.toFixed(2) + "m", tX, tY);
            }

            if (closestY && minDistY < 20) {
                const py1 = closestY.y, py2 = closestY.y + closestY.h;
                const overlapX1 = Math.max(ax1, closestY.x);
                const overlapX2 = Math.min(ax2, closestY.x + closestY.w);
                const lineX = ((overlapX1 + overlapX2) / 2) * zoom + offsetX;
                let lineY1 = ay2 * zoom + offsetY;
                let lineY2 = py1 * zoom + offsetY;
                if (ay1 >= py2) { lineY1 = py2 * zoom + offsetY; lineY2 = ay1 * zoom + offsetY; }
                ctx.beginPath(); ctx.moveTo(lineX, lineY1); ctx.lineTo(lineX, lineY2); ctx.stroke();
                ctx.beginPath(); ctx.moveTo(lineX, lineY1); ctx.lineTo(lineX-3, lineY1+5); ctx.lineTo(lineX+3, lineY1+5); ctx.fill();
                ctx.beginPath(); ctx.moveTo(lineX, lineY2); ctx.lineTo(lineX-3, lineY2-5); ctx.lineTo(lineX+3, lineY2-5); ctx.fill();
                ctx.textAlign = "left";
                let tX = lineX + 5;
                let tY = (lineY1 + lineY2) / 2 + 3;
                tX = Math.max(5, Math.min(canvas.width - 30, tX));
                tY = Math.max(10, Math.min(canvas.height - 10, tY));
                ctx.fillText(minDistY.toFixed(2) + "m", tX, tY);
            }

            ctx.restore();
        }

        function positionSun(){
          const el=sunElevation*Math.PI/180,az=sunAzimuth*Math.PI/180,R=60;
          sun.position.set(R*Math.cos(el)*Math.sin(az),Math.max(R*Math.sin(el),2),-R*Math.cos(el)*Math.cos(az));
          sun.visible=showShadows&&sunElevation>2;
        }
        function draw() {
            ctx.globalAlpha = 1.0;
            ctx.fillStyle = "#0f1310";
            ctx.fillRect(0, 0, canvas.width, canvas.height);
            
            if (isOpsMode) ctx.globalAlpha = 0.5;

            // Grid
            ctx.strokeStyle = "#1d241c"; 
            ctx.lineWidth = 1;
            for(let i = offsetX % zoom; i < canvas.width; i += zoom){ ctx.beginPath(); ctx.moveTo(i, 0); ctx.lineTo(i, canvas.height); ctx.stroke(); }
            for(let j = offsetY % zoom; j < canvas.height; j += zoom){ ctx.beginPath(); ctx.moveTo(0, j); ctx.lineTo(canvas.width, j); ctx.stroke(); }

            // ── Shadow pass (drawn before objects so shadows appear underneath) ──
            if (showShadows && sunElevation > 2) {
                const elevRad = sunElevation * Math.PI / 180;
                const azRad   = sunAzimuth   * Math.PI / 180;
                const tanElev = Math.tan(Math.max(elevRad, 0.017)); // floor at ~1°
                objects.forEach(o => {
                    // Height that casts a shadow; paths, plots, tanks are ground-level
                    const objH = (o.type === 'building' || o.type === 'equip')
                        ? (o.height || 0)
                        : o.type === 'rack'
                        ? ((o.layers || 1) * (o.spacing || 0.6) + 0.2)
                        : 0;
                    if (objH <= 0) return;
                    const rx = o.x * zoom + offsetX, ry = o.y * zoom + offsetY;
                    const rw = o.w * zoom, rh = o.h * zoom;
                    // Shadow vector in canvas pixels:
                    //   azimuth is from North clockwise; canvas +x=East, +y=South.
                    //   Sun direction: (sin(az), -cos(az)); shadow = opposite.
                    const shadowLenPx = Math.min(objH / tanElev, 200) * zoom;
                    const sdx = -Math.sin(azRad) * shadowLenPx;
                    const sdy =  Math.cos(azRad) * shadowLenPx;
                    ctx.save();
                    ctx.globalAlpha = 0.65;
                    ctx.fillStyle = "rgba(0,0,0,0.50)";
                    // Minkowski sum of footprint rect and shadow vector = correct shadow for any direction.
                    // Draw 4 edge quads + the shifted footprint.
                    [
                        [[rx,    ry],    [rx+rw, ry]],
                        [[rx+rw, ry],    [rx+rw, ry+rh]],
                        [[rx+rw, ry+rh], [rx,    ry+rh]],
                        [[rx,    ry+rh], [rx,    ry]],
                    ].forEach(([[x1,y1],[x2,y2]]) => {
                        ctx.beginPath();
                        ctx.moveTo(x1,     y1);
                        ctx.lineTo(x2,     y2);
                        ctx.lineTo(x2+sdx, y2+sdy);
                        ctx.lineTo(x1+sdx, y1+sdy);
                        ctx.closePath();
                        ctx.fill();
                    });
                    ctx.fillRect(rx+sdx, ry+sdy, rw, rh); // shifted top footprint
                    ctx.restore();
                });
            }

            objects.forEach(o => {
                const isSel = selection && selection.id === o.id;
                const rx = o.x * zoom + offsetX, ry = o.y * zoom + offsetY, rw = o.w * zoom, rh = o.h * zoom;

                if (o.type === 'measure') {
                    const rx1 = o.startX * zoom + offsetX;
                    const ry1 = o.startY * zoom + offsetY;
                    const rx2 = o.endX * zoom + offsetX;
                    const ry2 = o.endY * zoom + offsetY;
                    const dist = Math.sqrt(Math.pow(o.endX - o.startX, 2) + Math.pow(o.endY - o.startY, 2));

                    ctx.strokeStyle = isSel ? "#3f7d9c" : "#c0573a";
                    ctx.lineWidth = 2;
                    ctx.setLineDash([4, 4]);
                    ctx.beginPath();
                    ctx.moveTo(rx1, ry1);
                    ctx.lineTo(rx2, ry2);
                    ctx.stroke();
                    ctx.setLineDash([]);
                    
                    ctx.fillStyle = ctx.strokeStyle;
                    ctx.beginPath(); ctx.arc(rx1, ry1, 4, 0, Math.PI*2); ctx.fill();
                    ctx.beginPath(); ctx.arc(rx2, ry2, 4, 0, Math.PI*2); ctx.fill();
                    
                    ctx.fillStyle = "rgba(0, 0, 0, 0.8)";
                    let midX = (rx1 + rx2) / 2;
                    let midY = (ry1 + ry2) / 2;
                    midX = Math.max(40, Math.min(canvas.width - 40, midX));
                    midY = Math.max(30, Math.min(canvas.height - 30, midY));
                    
                    ctx.fillRect(midX - 35, midY - 25, 70, 24);
                    ctx.fillStyle = "#fff";
                    ctx.font = "bold 12px Inter";
                    ctx.textAlign = "center";
                    ctx.fillText(`${dist.toFixed(2)} m`, midX, midY - 8);
                    ctx.textAlign = "left";

                    if (isSel && !isOpsMode) {
                        ctx.strokeStyle = "rgba(52, 152, 219, 0.5)"; ctx.setLineDash([2, 2]); ctx.lineWidth = 1;
                        ctx.strokeRect(rx, ry, rw, rh);
                        ctx.setLineDash([]);
                    }
                    return;
                }

                // Colors from our Decided Palette
                if (o.type === 'plot') {
                    ctx.strokeStyle = isSel ? "#FFD43B" : "#f03e3e"; // Red border for property line
                    ctx.setLineDash([10, 5]);
                    ctx.fillStyle = "rgba(240, 62, 62, 0.05)";
                } else if (o.type === 'building') {
                    ctx.strokeStyle = isSel ? "#FFD43B" : "#5C7CFA";
                    ctx.fillStyle = "rgba(92, 124, 250, 0.1)";
                } else if (o.type === 'rack') {
                    const rt2d = o.rackType || 'standard';
                    const rColor = {standard:'#40C057', wall:'#74c0fc', tower:'#ffd43b', bench:'#cc5de8'}[rt2d] || '#40C057';
                    ctx.strokeStyle = isSel ? "#FFD43B" : rColor;
                    ctx.fillStyle   = `rgba(${parseInt(rColor.slice(1,3),16)},${parseInt(rColor.slice(3,5),16)},${parseInt(rColor.slice(5,7),16)},0.15)`;
                } else if (o.type === 'entry') {
                    ctx.strokeStyle = isSel ? "#FFD43B" : "#E599F7";
                    ctx.fillStyle = "rgba(229, 153, 247, 0.2)";
                } else if (o.type === 'tank') {
                    ctx.strokeStyle = isSel ? "#FFD43B" : "#0969da";
                    ctx.fillStyle = "rgba(9, 105, 218, 0.2)";
                } else if (o.type === 'equip') {
                    ctx.strokeStyle = isSel ? "#FFD43B" : (o.subType === 'hvac' ? "#ff922b" : "#868e96");
                    ctx.fillStyle = o.subType === 'hvac' ? "rgba(255, 146, 43, 0.2)" : "rgba(134, 142, 150, 0.2)";
                } else if (o.type === 'path') {
                    ctx.strokeStyle = isSel ? "#FFD43B" : "#495057";
                    ctx.fillStyle = "rgba(73, 80, 87, 0.4)";
                }
                
                ctx.lineWidth = (isSel || o.type === 'plot') ? 2 : 1;
                if (o.isWarning) {
                    ctx.fillStyle = "rgba(231, 76, 60, 0.4)";
                }
                if (o.type === 'path') ctx.setLineDash([4, 4]); // Dashed "caution" lines
                ctx.fillRect(rx, ry, rw, rh);
                ctx.strokeRect(rx, ry, rw, rh);
                if (o.type === 'path' || o.type === 'plot') ctx.setLineDash([]);
                
                if (o.isWarning) {
                    ctx.strokeStyle = "#e74c3c"; ctx.setLineDash([2, 2]);
                    ctx.strokeRect(rx - 5, ry - 5, rw + 10, rh + 10); ctx.setLineDash([]);
                }
                ctx.fillStyle = isSel ? "#FFD43B" : "#999";
                ctx.font = "9px Inter";
                const rTypeLabel = o.rackType && o.rackType !== 'standard' ? ` [${o.rackType.toUpperCase()}]` : '';
                ctx.fillText(o.name + rTypeLabel, rx + 4, ry + 13);
                // Layer count badge
                if (o.type === 'rack' && rw > 30) {
                    const badge = (o.layers||1) + 'L';
                    ctx.fillStyle = 'rgba(0,0,0,0.6)'; ctx.fillRect(rx + rw - 22, ry + 2, 20, 13);
                    ctx.fillStyle = '#2ecc71'; ctx.font = 'bold 9px Inter';
                    ctx.fillText(badge, rx + rw - 18, ry + 12);
                }

                if (isSel && !isOpsMode && o.type === 'rack') {
                    ctx.fillStyle = "#FFD43B";
                    const handles = [
                        [rx, ry], [rx + rw/2, ry], [rx + rw, ry],
                        [rx, ry + rh/2], [rx + rw, ry + rh/2],
                        [rx, ry + rh], [rx + rw/2, ry + rh], [rx + rw, ry + rh]
                    ];
                    handles.forEach(([hx, hy]) => {
                        ctx.fillRect(hx - 3, hy - 3, 6, 6);
                    });
                }
            });

            if (isDrawing && rectStart && window.lastWorld) {
                const tool = document.getElementById('toolSelect').value;
                const bType = document.getElementById('buildType').value;
                const isSelectTool = tool === 'select';
                
                if (tool === 'measure') {
                    let mStartX = document.getElementById('snapToggle')?.checked ? snapVal(rectStart.x) : rectStart.x;
                    let mStartY = document.getElementById('snapToggle')?.checked ? snapVal(rectStart.y) : rectStart.y;
                    let mEndX = document.getElementById('snapToggle')?.checked ? snapVal(window.lastWorld.x) : window.lastWorld.x;
                    let mEndY = document.getElementById('snapToggle')?.checked ? snapVal(window.lastWorld.y) : window.lastWorld.y;

                    const rx1 = mStartX * zoom + offsetX;
                    const ry1 = mStartY * zoom + offsetY;
                    const rx2 = mEndX * zoom + offsetX;
                    const ry2 = mEndY * zoom + offsetY;
                    
                    const dx = mEndX - mStartX;
                    const dy = mEndY - mStartY;
                    const dist = Math.sqrt(dx*dx + dy*dy);
                    
                    ctx.strokeStyle = "#e74c3c";
                    ctx.lineWidth = 2;
                    ctx.setLineDash([4, 4]);
                    ctx.beginPath();
                    ctx.moveTo(rx1, ry1);
                    ctx.lineTo(rx2, ry2);
                    ctx.stroke();
                    ctx.setLineDash([]);
                    
                    ctx.fillStyle = "#e74c3c";
                    ctx.beginPath(); ctx.arc(rx1, ry1, 4, 0, Math.PI*2); ctx.fill();
                    ctx.beginPath(); ctx.arc(rx2, ry2, 4, 0, Math.PI*2); ctx.fill();
                    
                    ctx.fillStyle = "rgba(0, 0, 0, 0.8)";
                    let midX = (rx1 + rx2) / 2;
                    let midY = (ry1 + ry2) / 2;
                    midX = Math.max(40, Math.min(canvas.width - 40, midX));
                    midY = Math.max(30, Math.min(canvas.height - 30, midY));
                    
                    ctx.fillRect(midX - 35, midY - 25, 70, 24);
                    ctx.fillStyle = "#fff";
                    ctx.font = "bold 12px Inter";
                    ctx.textAlign = "center";
                    ctx.fillText(`${dist.toFixed(2)} m`, midX, midY - 8);
                    ctx.textAlign = "left";
                } else {
                    let ew = Math.abs(window.lastWorld.x - rectStart.x);
                    let eh = Math.abs(window.lastWorld.y - rectStart.y);
                    if (tool === 'building' && bType === 'polytunnel') ew = parseFloat(document.getElementById('standardSpan').value);

                    const rx = rectStart.x * zoom + offsetX, ry = rectStart.y * zoom + offsetY;
                    const dx = (window.lastWorld.x >= rectStart.x) ? 1 : -1, dy = (window.lastWorld.y >= rectStart.y) ? 1 : -1;
                    const rw_px = ew * zoom * dx, rh_px = eh * zoom * dy;

                    ctx.strokeStyle = isSelectTool ? "#3f7d9c" : "#e8c14e"; 
                    ctx.setLineDash([5,5]);
                    ctx.strokeRect(rx, ry, rw_px, rh_px);
                    ctx.setLineDash([]);

                    // RESTORED MEASUREMENT HUD
                    if(!isSelectTool) {
                        ctx.fillStyle = "rgba(0, 0, 0, 0.8)";
                        let labelX = rx + rw_px + (dx > 0 ? 5 : -105);
                        let labelY = ry + rh_px + (dy > 0 ? 5 : -45);
                        
                        labelX = Math.max(5, Math.min(canvas.width - 105, labelX));
                        labelY = Math.max(5, Math.min(canvas.height - 45, labelY));

                        ctx.fillRect(labelX, labelY, 100, 40);
                        
                        ctx.fillStyle = "#e8c14e";
                        ctx.font = "bold 11px Inter";
                        ctx.fillText(`${ew.toFixed(2)}m x ${eh.toFixed(2)}m`, labelX + 8, labelY + 18);
                        ctx.fillStyle = "#52a066";
                        ctx.fillText(`${(ew * eh).toFixed(2)} m²`, labelX + 8, labelY + 32);
                    }
                }
            }

            if (isDragging && selection) {
                drawAlignmentGuides(selection, selection.id);
            } else if (isResizing && selection) {
                drawAlignmentGuides(selection, selection.id);
            } else if (isDrawing && rectStart && window.lastWorld && !isOpsMode) {
                const tool = document.getElementById('toolSelect')?.value;
                if (['rack', 'wall_rack', 'tower_rack', 'single_shelf', 'building', 'tank', 'equip', 'path'].includes(tool)) {
                    const fw = Math.abs(window.lastWorld.x - rectStart.x);
                    const fh = Math.abs(window.lastWorld.y - rectStart.y);
                    const dx = window.lastWorld.x >= rectStart.x ? 1 : -1;
                    const dy = window.lastWorld.y >= rectStart.y ? 1 : -1;
                    const sx = snapVal(dx > 0 ? rectStart.x : rectStart.x - fw);
                    const sy = snapVal(dy > 0 ? rectStart.y : rectStart.y - fh);
                    drawAlignmentGuides({ x: sx, y: sy, w: Math.max(0.1, snapVal(fw)), h: Math.max(0.1, snapVal(fh)) }, null);
                }
            }

            drawCycleOverlay();
            drawOverlays();
            ctx.globalAlpha = 1.0;
            positionSun();
        }

        function sync3D() {
            while(objectGroup.children.length > 0) {
                const child = objectGroup.children[0];
                if(child.geometry) child.geometry.dispose();
                if(child.material) child.material.dispose();
                objectGroup.remove(child);
            }

            objects.forEach(obj => {
                if (obj.type === 'building') {
                    const bType = obj.subType || 'warehouse';
                    let geom = (bType === 'polytunnel') ? 
                        new THREE.CylinderGeometry(obj.w / 2, obj.w / 2, obj.h, 32, 1, false, 0, Math.PI) :
                        new THREE.BoxGeometry(obj.w, obj.height, obj.h);

                    if(bType === 'polytunnel') { geom.rotateZ(Math.PI / 2); geom.rotateY(Math.PI / 2); }

                    // PENCIL DRAW EFFECT: Add clear outlines
                    const edges = new THREE.EdgesGeometry(geom);
                    const line = new THREE.LineSegments(edges, new THREE.LineBasicMaterial({ color: 0x93c79e, transparent:true, opacity:0.5 }));

                    const mat = new THREE.MeshStandardMaterial({ color: bType==='warehouse'?0x5b8fb0:0x6fb0cf, roughness:0.3, metalness:0.1, transparent:true, opacity:(bType==='greenhouse'||bType==='polytunnel')?0.14:0.08 });
                    const mesh = new THREE.Mesh(geom, mat);
                    
                    const posY = (bType === 'polytunnel') ? 0 : obj.height/2;
                    mesh.position.set(obj.x + obj.w/2, posY, obj.y + obj.h/2);
                    line.position.copy(mesh.position);
                    
                    objectGroup.add(mesh);
                    objectGroup.add(line); // Add the "pencil" outline
                } 
                else if (obj.type === 'tank') {
                    const tw = obj.w, td = obj.height || 1.5, tl = obj.h;
                    const cx = obj.x + tw/2, cz = obj.y + tl/2;
                    const wall = 0.04; // wall thickness

                    // ── Structural frame (dark metal) ─────────────────────────
                    const frameMat = new THREE.MeshStandardMaterial({color:0x3a4038, roughness:0.65, metalness:0.35});
                    // 4 corner uprights
                    [[0,0],[tw,0],[0,tl],[tw,tl]].forEach(([fx,fz]) => {
                        const fg = new THREE.BoxGeometry(wall, td + wall, wall);
                        const fm = new THREE.Mesh(fg, frameMat);
                        fm.position.set(obj.x + fx, td/2, obj.y + fz);
                        fm.castShadow = true;
                        objectGroup.add(fm);
                    });
                    // Bottom rim
                    const rimMat = new THREE.MeshStandardMaterial({color:0x4a524a, roughness:0.6, metalness:0.3});
                    [[cx, 0, obj.y,      tw, wall, wall],
                     [cx, 0, obj.y + tl, tw, wall, wall],
                     [obj.x,      0, cz, wall, wall, tl],
                     [obj.x + tw, 0, cz, wall, wall, tl]].forEach(([px,py,pz,rw,rh,rl]) => {
                        const rg = new THREE.BoxGeometry(rw, rh, rl);
                        const rm = new THREE.Mesh(rg, rimMat);
                        rm.position.set(px, py, pz);
                        objectGroup.add(rm);
                    });
                    // Top rim
                    [[cx, td, obj.y,      tw + wall, wall, wall],
                     [cx, td, obj.y + tl, tw + wall, wall, wall],
                     [obj.x,      td, cz, wall, wall, tl],
                     [obj.x + tw, td, cz, wall, wall, tl]].forEach(([px,py,pz,rw,rh,rl]) => {
                        const rg = new THREE.BoxGeometry(rw, rh, rl);
                        const rm = new THREE.Mesh(rg, rimMat);
                        rm.position.set(px, py, pz);
                        objectGroup.add(rm);
                    });

                    // ── Glass walls (4 translucent panels) ────────────────────
                    const glassMat = new THREE.MeshPhysicalMaterial({
                        color: 0x4f97c0, roughness: 0.05, metalness: 0,
                        transparent: true, opacity: 0.22,
                        transmission: 0.78, thickness: 0.3,
                        side: THREE.DoubleSide
                    });
                    // Front & back
                    [[obj.y, false],[obj.y + tl, false]].forEach(([pz, _]) => {
                        const pg = new THREE.BoxGeometry(tw - wall, td - wall*2, wall * 0.5);
                        const pm = new THREE.Mesh(pg, glassMat);
                        pm.position.set(cx, td/2, pz);
                        objectGroup.add(pm);
                    });
                    // Left & right
                    [[obj.x, true],[obj.x + tw, true]].forEach(([px, _]) => {
                        const pg = new THREE.BoxGeometry(wall * 0.5, td - wall*2, tl - wall);
                        const pm = new THREE.Mesh(pg, glassMat);
                        pm.position.set(px, td/2, cz);
                        objectGroup.add(pm);
                    });

                    // ── Water fill (deeper tint inside) ───────────────────────
                    const waterMat = new THREE.MeshPhysicalMaterial({
                        color: 0x2c5a78, roughness: 0.0, metalness: 0,
                        transparent: true, opacity: 0.18, transmission: 0.9,
                    });
                    const wg = new THREE.BoxGeometry(tw - wall*2, td * 0.88, tl - wall*2);
                    const wm = new THREE.Mesh(wg, waterMat);
                    wm.position.set(cx, td * 0.44 + wall, cz);
                    objectGroup.add(wm);

                    // ── Water surface ──────────────────────────────────────────
                    const surfMat = new THREE.MeshStandardMaterial({
                        color: 0x3a7fa8, roughness: 0.05, metalness: 0.1,
                        transparent: true, opacity: 0.55
                    });
                    const sg = new THREE.PlaneGeometry(tw - wall*2, tl - wall*2);
                    const sm = new THREE.Mesh(sg, surfMat);
                    sm.rotation.x = -Math.PI / 2;
                    sm.position.set(cx, td * 0.92, cz);
                    objectGroup.add(sm);
                } else if (obj.type === 'equip') {
                    const geom = new THREE.BoxGeometry(obj.w, obj.height, obj.h);
                    const color = obj.subType === 'hvac' ? 0xc0734a : obj.subType === 'biofilter' ? 0x4a7a4a : 0x6b7570;
                    const mat = new THREE.MeshStandardMaterial({ color: color, roughness: 0.6, metalness: 0.2 });
                    const mesh = new THREE.Mesh(geom, mat);
                    mesh.position.set(obj.x + obj.w/2, obj.height/2, obj.y + obj.h/2);
                    
                    const edges = new THREE.EdgesGeometry(geom);
                    const line = new THREE.LineSegments(edges, new THREE.LineBasicMaterial({ color: 0x93c79e, transparent:true, opacity:0.5 }));
                    line.position.copy(mesh.position);
                    
                    objectGroup.add(mesh);
                    objectGroup.add(line);
                } else if (obj.type === 'rack') {
                    const spacing  = obj.spacing || 0.6;
                    const rType    = obj.rackType || 'standard';
                    const baseColor = {standard:0x52a066, wall:0x3f7d9c, tower:0xcf9b3f, bench:0x8d6a9f}[rType] || 0x52a066;
                    // Per-layer status colours (from cycle data)
                    const statusColors = {seeding:0x3f7d9c, growing:0x52a066, ready:0xcf9b3f, failed:0xc0573a};

                    if (rType === 'tower') {
                        // Professional tower rack: structural frame + growing panels
                        const tH      = obj.height || 2.0;
                        const nPlants = obj.layers  || 20;
                        const cx      = obj.x + obj.w / 2;
                        const cz      = obj.y + obj.h / 2;
                        const isRect  = obj.towerShape === 'rect';

                        // ── Structural frame ──────────────────────────────────
                        const frameR  = isRect ? null : 0.035;
                        const frameMat = new THREE.MeshStandardMaterial({color:0x4a4e48, roughness:0.7, metalness:0.15});
                        if (isRect) {
                            // 4 corner posts for rectangular tower
                            const hw = (obj.w || 0.4) / 2 - 0.04;
                            const hd = (obj.h || 0.4) / 2 - 0.04;
                            [[-hw,-hd],[hw,-hd],[hw,hd],[-hw,hd]].forEach(([dx,dz]) => {
                                const pg = new THREE.BoxGeometry(0.04, tH, 0.04);
                                const p  = new THREE.Mesh(pg, frameMat);
                                p.position.set(cx+dx, tH/2, cz+dz);
                                p.castShadow = true;
                                objectGroup.add(p);
                            });
                            // Horizontal cross-braces every ~0.5m
                            const nBraces = Math.max(2, Math.round(tH / 0.5));
                            for (let b = 0; b <= nBraces; b++) {
                                const by = (b / nBraces) * tH;
                                const bg1 = new THREE.BoxGeometry(obj.w - 0.04, 0.025, 0.025);
                                const bm1 = new THREE.Mesh(bg1, frameMat);
                                bm1.position.set(cx, by, cz - (obj.h||0.4)/2 + 0.02);
                                objectGroup.add(bm1);
                                const bm2 = bm1.clone();
                                bm2.position.z = cz + (obj.h||0.4)/2 - 0.02;
                                objectGroup.add(bm2);
                            }
                        } else {
                            // Round: central pole + 3 outer guide rails
                            const poleG = new THREE.CylinderGeometry(0.03, 0.03, tH, 12);
                            const pole  = new THREE.Mesh(poleG, frameMat);
                            pole.position.set(cx, tH/2, cz);
                            pole.castShadow = true;
                            objectGroup.add(pole);
                            const railR = Math.min(obj.w, obj.h) * 0.38;
                            for (let r = 0; r < 3; r++) {
                                const ang = (r / 3) * Math.PI * 2;
                                const rg  = new THREE.CylinderGeometry(0.012, 0.012, tH, 6);
                                const rm  = new THREE.Mesh(rg, frameMat);
                                rm.position.set(cx + railR * Math.cos(ang), tH/2, cz + railR * Math.sin(ang));
                                objectGroup.add(rm);
                            }
                        }

                        // ── Growing panels / net cups ─────────────────────────
                        const panelStep = (tH - 0.25) / Math.max(1, nPlants - 1);
                        const panelR    = Math.min(obj.w, obj.h) * 0.42;
                        for (let i = 0; i < nPlants; i++) {
                            const layerStatus = obj.layerStatus?.[i] || '';
                            const col  = statusColors[layerStatus] || baseColor;
                            const panelMat = new THREE.MeshStandardMaterial({
                                color: col, roughness:0.45, metalness:0.05,
                                emissive: col, emissiveIntensity: 0.22,
                                transparent:true, opacity:0.92
                            });
                            const yPos = 0.15 + i * panelStep;
                            if (isRect) {
                                // Rectangular: alternating side panels
                                const side  = i % 2 === 0;
                                const pW    = (side ? obj.w : obj.h) * 0.72;
                                const pg    = new THREE.BoxGeometry(side ? pW : 0.018, 0.055, side ? 0.018 : pW);
                                const pm    = new THREE.Mesh(pg, panelMat);
                                pm.position.set(cx, yPos, cz);
                                pm.castShadow = true;
                                objectGroup.add(pm);
                            } else {
                                // Round: small discs fanned around the pole
                                const ang  = (i / nPlants) * Math.PI * 2 * 2.5; // ~2.5 rotations
                                const dg   = new THREE.CylinderGeometry(0.065, 0.065, 0.018, 10);
                                const dm   = new THREE.Mesh(dg, panelMat);
                                dm.position.set(cx + panelR * Math.cos(ang), yPos, cz + panelR * Math.sin(ang));
                                dm.castShadow = true;
                                objectGroup.add(dm);
                                // Thin stem connecting disc to pole/rail
                                const stemLen = panelR - 0.03;
                                const sg2 = new THREE.CylinderGeometry(0.005, 0.005, stemLen, 4);
                                const sm2 = new THREE.Mesh(sg2, frameMat);
                                sm2.rotation.z = Math.PI / 2;
                                sm2.position.set(
                                    cx + (panelR/2) * Math.cos(ang), yPos,
                                    cz + (panelR/2) * Math.sin(ang)
                                );
                                sm2.lookAt(cx + panelR * Math.cos(ang), yPos, cz + panelR * Math.sin(ang));
                                objectGroup.add(sm2);
                            }
                        }

                        // ── Top cap ───────────────────────────────────────────
                        const capG = isRect
                            ? new THREE.BoxGeometry(obj.w, 0.03, obj.h)
                            : new THREE.CylinderGeometry(Math.min(obj.w,obj.h)*0.48, Math.min(obj.w,obj.h)*0.48, 0.03, 16);
                        const capM = new THREE.Mesh(capG, frameMat);
                        capM.position.set(cx, tH + 0.015, cz);
                        objectGroup.add(capM);
                    } else if (rType === 'wall') {
                        // Wall rack: single vertical growing surface
                        const layerStatus = obj.layerStatus?.[0] || obj.cycleStatus || '';
                        const col = statusColors[layerStatus] || baseColor;
                        const panelG = new THREE.BoxGeometry(obj.w || 0.3, obj.height || 2.4, obj.h);
                        const panelM = new THREE.MeshStandardMaterial({color: col, roughness:0.5, metalness:0.05, transparent:true, opacity:0.95, emissive: col, emissiveIntensity:0.28});
                        const panel  = new THREE.Mesh(panelG, panelM);
                        panel.position.set(obj.x + (obj.w||0.3)/2, (obj.height||2.4)/2, obj.y + obj.h/2);
                        objectGroup.add(panel);
                        const eg = new THREE.EdgesGeometry(panelG);
                        const el = new THREE.LineSegments(eg, new THREE.LineBasicMaterial({color:0x93c79e, transparent:true, opacity:0.5}));
                        el.position.copy(panel.position);
                        objectGroup.add(el);
                    } else if (rType === 'bench') {
                        // Single bench: legs + surface — height-aware
                        const legH = parseFloat(obj.height) || 0.9;
                        const lInset = Math.min(0.12, obj.w * 0.12, obj.h * 0.12);
                        const legMat = new THREE.MeshStandardMaterial({color:0x3a3e38, roughness:0.75, metalness:0.1});
                        [[lInset, lInset],[obj.w-lInset, lInset],[lInset, obj.h-lInset],[obj.w-lInset, obj.h-lInset]].forEach(([lx,ly]) => {
                            const lg = new THREE.BoxGeometry(0.04, legH, 0.04);
                            const l  = new THREE.Mesh(lg, legMat);
                            l.position.set(obj.x+lx, legH/2, obj.y+ly);
                            l.castShadow = true;
                            objectGroup.add(l);
                        });
                        // Cross-braces at 1/3 height for realism
                        const braceMat = new THREE.MeshStandardMaterial({color:0x2e322c, roughness:0.8, metalness:0.1});
                        const braceY = legH * 0.3;
                        [[obj.x + lInset, obj.x + obj.w - lInset, obj.y + lInset],
                         [obj.x + lInset, obj.x + obj.w - lInset, obj.y + obj.h - lInset]].forEach(([x1,x2,pz]) => {
                            const bg = new THREE.BoxGeometry(x2-x1, 0.025, 0.025);
                            const bm = new THREE.Mesh(bg, braceMat);
                            bm.position.set((x1+x2)/2, braceY, pz);
                            objectGroup.add(bm);
                        });
                        [[obj.x + lInset, obj.y + lInset, obj.y + obj.h - lInset],
                         [obj.x + obj.w - lInset, obj.y + lInset, obj.y + obj.h - lInset]].forEach(([px,z1,z2]) => {
                            const bg = new THREE.BoxGeometry(0.025, 0.025, z2-z1);
                            const bm = new THREE.Mesh(bg, braceMat);
                            bm.position.set(px, braceY, (z1+z2)/2);
                            objectGroup.add(bm);
                        });
                        // Surface
                        const layerStatus = obj.layerStatus?.[0] || obj.cycleStatus || '';
                        const topCol = statusColors[layerStatus] || baseColor;
                        const tg = new THREE.BoxGeometry(obj.w, 0.045, obj.h);
                        const tm = new THREE.MeshStandardMaterial({color: topCol, roughness:0.5, metalness:0.05,
                            transparent:true, opacity:0.95, emissive: topCol, emissiveIntensity:0.22});
                        const top = new THREE.Mesh(tg, tm);
                        top.position.set(obj.x+obj.w/2, legH, obj.y+obj.h/2);
                        top.castShadow = true;
                        objectGroup.add(top);
                        const eg = new THREE.EdgesGeometry(tg);
                        const el = new THREE.LineSegments(eg, new THREE.LineBasicMaterial({color:0x93c79e, transparent:true, opacity:0.5}));
                        el.position.copy(top.position);
                        objectGroup.add(el);
                    } else {
                        // Standard rack: column frames + colour-coded shelves
                        // Frame posts
                        const postH = obj.height || (spacing * obj.layers + 0.3);
                        [[0.04,0.04],[obj.w-0.04,0.04],[0.04,obj.h-0.04],[obj.w-0.04,obj.h-0.04]].forEach(([px,py]) => {
                            const pg = new THREE.CylinderGeometry(0.025,0.025,postH,6);
                            const pm = new THREE.MeshStandardMaterial({color:0x3a3e38, roughness:0.8});
                            const p  = new THREE.Mesh(pg, pm);
                            p.position.set(obj.x+px, postH/2, obj.y+py);
                            objectGroup.add(p);
                        });
                        // Shelves with per-layer colour
                        for (let i = 0; i < obj.layers; i++) {
                            const layerStatus = obj.layerStatus?.[i] || '';
                            const col  = statusColors[layerStatus] || baseColor;
                            const shelfG = new THREE.BoxGeometry(obj.w, 0.04, obj.h);
                            const shelfM = new THREE.MeshStandardMaterial({color: col, roughness:0.5, metalness:0.05, transparent:true, opacity:0.95, emissive: col, emissiveIntensity:0.28});
                            const shelf  = new THREE.Mesh(shelfG, shelfM);
                            const yPos = 0.2 + i * ((postH - 0.3) / Math.max(1, obj.layers));
                            shelf.position.set(obj.x+obj.w/2, yPos, obj.y+obj.h/2);
                            objectGroup.add(shelf);
                            // Shelf edge highlight
                            const eg = new THREE.EdgesGeometry(shelfG);
                            const el = new THREE.LineSegments(eg, new THREE.LineBasicMaterial({color:0x93c79e, transparent:true, opacity:0.5}));
                            el.position.copy(shelf.position);
                            objectGroup.add(el);
                        }
                    }
                } else if (obj.type === 'path') {
                    const geom = new THREE.BoxGeometry(obj.w, 0.02, obj.h);
                    const mat = new THREE.MeshStandardMaterial({ color: 0x2a2d27, roughness: 0.9 });
                    const mesh = new THREE.Mesh(geom, mat);
                    mesh.position.set(obj.x + obj.w/2, 0.01, obj.y + obj.h/2);
                    objectGroup.add(mesh);
                } else if (obj.type === 'plot') {
                    const geom = new THREE.PlaneGeometry(obj.w, obj.h);
                    const edges = new THREE.EdgesGeometry(new THREE.BoxGeometry(obj.w, 0.01, obj.h));
                    const line = new THREE.LineSegments(edges, new THREE.LineBasicMaterial({ color: 0xc0573a, transparent:true, opacity:0.7 }));
                    line.position.set(obj.x + obj.w/2, 0.01, obj.y + obj.h/2);
                    objectGroup.add(line);
                } else if (obj.type === 'measure') {
                    const points = [];
                    points.push(new THREE.Vector3(obj.startX, 0.02, obj.startY));
                    points.push(new THREE.Vector3(obj.endX, 0.02, obj.endY));
                    const geom = new THREE.BufferGeometry().setFromPoints(points);
                    const line = new THREE.Line(geom, new THREE.LineBasicMaterial({ color: 0xc0573a, linewidth: 2 }));
                    objectGroup.add(line);
                }
            });
        }

        function updateStats() {
            let bA=0,cA=0,maxH=0,rackCnt=0,tG=0;
            objects.forEach(o=>{
                if(o.type==='building'){bA+=o.w*o.h;if(o.height>maxH)maxH=o.height;}
                else if(o.type==='tank'){const wt=o.w*o.h*o.height*1000;if(selection&&selection.id===o.id)document.getElementById('water-weight').innerText=wt.toLocaleString();tG+=o.w*o.h;}
                else if(o.type==='rack'){
                    // Wall racks: grow area = wall length × rack height
                    // Wall length = max(w, h); thickness = min(w, h) = 0.30m
                    const rackCanopy = (o.rackType === 'wall')
                        ? Math.max(o.w, o.h) * (o.height || 2.4)
                        : o.w * o.h * (o.layers || 1);
                    cA += rackCanopy;
                    tG += o.w * o.h;  // floor footprint always uses w × h (thickness for wall)
                    rackCnt++;
                }
            });
            document.getElementById('m-build').innerText=bA.toFixed(1);
            document.getElementById('m-canopy').innerText=cA.toFixed(1);
            document.getElementById('m-height').innerText=maxH.toFixed(1);
            document.getElementById('m-racks').innerText=rackCnt;
            document.getElementById('m-eff').innerText=bA>0?Math.round(tG/bA*100):0;
            // Crop-aware yield: weighted average of actual crop assignments per rack
            let totalYieldKg = 0, hasAssignments = false;
            objects.forEach(o => {
                if (o.type !== 'rack') return;
                const wallLen = (o.rackType === 'wall') ? Math.max(o.w, o.h) : 0;
                const rCanopy = (o.rackType === 'wall') ? wallLen * (o.height || 2.4) : o.w * o.h * (o.layers || 1);
                if (rCanopy <= 0) return;
                const crops = o.crops || [];
                const layers = o.layers || 1;
                let sumY = 0, sumC = 0, n = 0;
                crops.slice(0, layers).forEach(c => {
                    if (c && c !== 'None') {
                        const d = getCropData(c); sumY += d.y; sumC += d.c; n++;
                    }
                });
                if (n > 0) {
                    hasAssignments = true;
                    const netGrow = FARM_DATA ? parseFloat(FARM_DATA.net_grow_factor || 0.85) : 0.85;
                    const lossRate = FARM_DATA ? parseFloat(FARM_DATA.loss_rate || 5) / 100 : 0.05;
                    totalYieldKg += rCanopy * (sumY / n) * netGrow * (1 - lossRate);
                } else {
                    // no crop assigned: use lettuce default but mark as estimate
                    const d = getCropData('default');
                    const netGrow = FARM_DATA ? parseFloat(FARM_DATA.net_grow_factor || 0.85) : 0.85;
                    totalYieldKg += rCanopy * d.y * netGrow;
                }
            });
            const yieldLabel = hasAssignments
                ? Math.round(totalYieldKg).toLocaleString() + ' kg/yr'
                : (cA > 0 ? '~' + Math.round(totalYieldKg).toLocaleString() + ' kg/yr' : '—');
            document.getElementById('m-yield').innerText = yieldLabel;
            checkSafety();
        }

        // ── View swap (2D ↔ 3D) ───────────────────────────────────────────────
        let _viewSwapped = false;
        function swapViews() {
            _viewSwapped = !_viewSwapped;
            const mainView    = document.getElementById('main-view');
            const canvasCont  = document.getElementById('canvas-container');
            const inspector   = document.getElementById('inspector');
            const vpWrap      = document.getElementById('viewport-wrap');
            const badge       = document.getElementById('vp-badge-label');

            if (_viewSwapped) {
                // 3D goes big (into main slot), inspector + small 2D go to right column
                mainView.style.flexDirection = 'row';
                // Move 3D viewport before inspector in the flex row, make it big
                vpWrap.style.cssText = 'flex:2;border:1px solid var(--line);border-radius:10px;overflow:hidden;position:relative;height:auto;margin-top:0;flex-shrink:0;';
                canvasCont.style.cssText = 'flex:1;background:var(--s0);border-radius:10px;position:relative;border:1px solid var(--line);overflow:hidden;min-width:180px;max-width:220px;';
                inspector.style.maxWidth = '270px';
                // Re-insert vpWrap as first child of mainView
                mainView.insertBefore(vpWrap, mainView.firstChild);
                if (badge) badge.textContent = '3D · Forest Studio';
                // Resize 3D renderer
                setTimeout(() => {
                    if (typeof renderer !== 'undefined' && vpWrap.clientHeight > 0) {
                        renderer.setSize(vpWrap.clientWidth, vpWrap.clientHeight);
                        if (typeof camera !== 'undefined') { camera.aspect = vpWrap.clientWidth / vpWrap.clientHeight; camera.updateProjectionMatrix(); }
                    }
                    resizeCanvas();
                }, 60);
            } else {
                // Back to normal: 2D big, 3D thumbnail in inspector column
                vpWrap.style.cssText = 'border:1px solid var(--line);border-radius:9px;overflow:hidden;position:relative;margin-top:auto;flex-shrink:0;height:260px;';
                canvasCont.style.cssText = 'flex:2;background:var(--s0);border-radius:10px;position:relative;border:1px solid var(--line);overflow:hidden;';
                inspector.style.maxWidth = '270px';
                // Move inspector back to last position, vpWrap inside inspector column
                mainView.appendChild(inspector);
                if (badge) badge.textContent = '3D · Forest Studio';
                setTimeout(() => {
                    if (typeof renderer !== 'undefined' && typeof cont3d !== 'undefined' && cont3d.clientHeight > 0) {
                        renderer.setSize(cont3d.clientWidth, cont3d.clientHeight);
                        if (typeof camera !== 'undefined') { camera.aspect = cont3d.clientWidth / cont3d.clientHeight; camera.updateProjectionMatrix(); }
                    }
                    resizeCanvas();
                }, 60);
            }
        }

        // ── Farm Summary ──────────────────────────────────────────────────────
        function openFarmSummary() {
            const panel = document.getElementById('farm-summary-panel');
            const content = document.getElementById('farm-summary-content');
            if (!panel || !content) return;

            // Aggregate by crop across all racks
            const cropMap = {}; // cropName → { canopy, yieldKg, revenueEur }
            const netGrow  = FARM_DATA ? parseFloat(FARM_DATA.net_grow_factor || 0.85) : 0.85;
            const lossRate = FARM_DATA ? parseFloat(FARM_DATA.loss_rate || 5) / 100 : 0.05;
            const packCost = FARM_DATA ? parseFloat(FARM_DATA.packaging_cost || 0.3) : 0.3;
            const priceOverride = FARM_DATA ? parseFloat(FARM_DATA.price_override || 0) : 0;

            let totalCanopy = 0, totalYield = 0, totalRev = 0;

            objects.forEach(o => {
                if (o.type !== 'rack') return;
                const wallLen  = (o.rackType === 'wall') ? Math.max(o.w, o.h) : 0;
                const rCanopy  = (o.rackType === 'wall')
                    ? wallLen * (o.height || 2.4)
                    : o.w * o.h * (o.layers || 1);
                if (rCanopy <= 0) return;
                const layers = o.layers || 1;
                const crops  = o.crops || [];
                const layerCanopy = rCanopy / layers;

                for (let i = 0; i < layers; i++) {
                    const cropName = (crops[i] && crops[i] !== 'None') ? crops[i] : 'default';
                    const d = getCropData(cropName);
                    const effPrice = priceOverride > 0 ? priceOverride : d.p;
                    const layerYield = layerCanopy * d.y * netGrow * (1 - lossRate);
                    const layerRev   = layerYield * effPrice - (layerYield * packCost);
                    const displayName = cropName === 'default' ? 'Unassigned' : cropName;
                    if (!cropMap[displayName]) cropMap[displayName] = { canopy: 0, yieldKg: 0, revenueEur: 0 };
                    cropMap[displayName].canopy     += layerCanopy;
                    cropMap[displayName].yieldKg    += layerYield;
                    cropMap[displayName].revenueEur += layerRev;
                    totalCanopy += layerCanopy;
                    totalYield  += layerYield;
                    totalRev    += layerRev;
                }
            });

            // Also summarise tanks
            const tankSummary = [];
            objects.forEach(o => {
                if (o.type !== 'tank') return;
                const vol = o.w * o.h * (o.height || 1.5);
                const crop = (o.crops && o.crops[0] && o.crops[0] !== 'None') ? o.crops[0] : null;
                tankSummary.push({ name: o.name, vol: vol.toFixed(1), crop: crop || '—' });
            });

            const sorted = Object.entries(cropMap).sort((a,b) => b[1].revenueEur - a[1].revenueEur);

            let html = '';
            if (sorted.length === 0 && tankSummary.length === 0) {
                html = '<div style="color:var(--ink3);font-style:italic;font-size:11px;">No racks or tanks on this layout.</div>';
            } else {
                // Crop table
                if (sorted.length > 0) {
                    html += '<div class="kpi-card-hdr" style="margin-bottom:3px;">Crop Breakdown</div>';
                    html += '<div style="display:grid;grid-template-columns:1fr auto auto auto;gap:3px 8px;font-size:10px;align-items:center;">';
                    html += '<span style="color:var(--ink3);font-weight:700;">Crop</span><span style="color:var(--ink3);font-weight:700;text-align:right;">Canopy</span><span style="color:var(--ink3);font-weight:700;text-align:right;">Yield/yr</span><span style="color:var(--ink3);font-weight:700;text-align:right;">Rev/yr</span>';
                    sorted.forEach(([name, v]) => {
                        const isUnassigned = name === 'Unassigned';
                        const nameColor = isUnassigned ? 'var(--ink3)' : 'var(--ink)';
                        html += `<span style="color:${nameColor};font-style:${isUnassigned?'italic':'normal'}">${name}</span>`;
                        html += `<span style="color:var(--accent);font-family:\'JetBrains Mono\',monospace;text-align:right;">${v.canopy.toFixed(1)}m²</span>`;
                        html += `<span style="color:var(--accent-gold);font-family:\'JetBrains Mono\',monospace;text-align:right;">${Math.round(v.yieldKg).toLocaleString()} kg</span>`;
                        html += `<span style="color:var(--plum);font-family:\'JetBrains Mono\',monospace;text-align:right;">$${Math.round(v.revenueEur).toLocaleString()}</span>`;
                    });
                    html += '</div>';
                    html += `<div style="margin-top:5px;padding-top:5px;border-top:1px solid var(--line-soft);display:grid;grid-template-columns:1fr auto auto auto;gap:3px 8px;font-size:10px;">`;
                    html += `<span style="color:var(--ink);font-weight:700;">TOTAL</span>`;
                    html += `<span style="color:var(--accent);font-family:\'JetBrains Mono\',monospace;text-align:right;font-weight:700;">${totalCanopy.toFixed(1)}m²</span>`;
                    html += `<span style="color:var(--accent-gold);font-family:\'JetBrains Mono\',monospace;text-align:right;font-weight:700;">${Math.round(totalYield).toLocaleString()} kg</span>`;
                    html += `<span style="color:var(--plum);font-family:\'JetBrains Mono\',monospace;text-align:right;font-weight:700;">$${Math.round(totalRev).toLocaleString()}</span>`;
                    html += '</div>';
                }
                // Tank table
                if (tankSummary.length > 0) {
                    html += '<div class="kpi-card-hdr" style="margin-top:8px;margin-bottom:3px;">Fish Tanks</div>';
                    tankSummary.forEach(t => {
                        html += `<div class="kpi-row"><span class="kl">${t.name}</span><span class="kv azure">${t.vol} m³</span><span class="kv" style="color:var(--ink3);font-size:10px;">${t.crop}</span></div>`;
                    });
                }
            }

            content.innerHTML = html;

            // Hide editor-ui, show summary panel
            document.getElementById('editor-ui').style.display = 'none';
            document.getElementById('no-selection').style.display = 'none';
            panel.style.display = 'flex';
        }

        function closeFarmSummary() {
            const panel = document.getElementById('farm-summary-panel');
            if (panel) panel.style.display = 'none';
            document.getElementById('no-selection').style.display = 'block';
        }

        function animate() { requestAnimationFrame(animate); renderer.render(scene, camera); }
        window.clearAll = () => { 
            customConfirm('Clear <b>everything</b> from the layout?', () => {
                objects = []; selection = null; updateStats(); sync3D(); draw(); notifyParent(); 
            });
        };
    </script>
    '''
    
    # Inject farm data and preloaded objects into the JS
    html_with_data = html_code.replace(
        "let objects = [];",
        (
            f"let objects = {_preload_objects_js};\n"
            f"        const FARM_DATA = {_farm_js};\n"
            f"        const SUPABASE_CONFIG = {_supabase_js};\n"
            f"        let SUN_DATA = {_sun_js};\n"
            f"        let sunAzimuth = SUN_DATA ? SUN_DATA.azimuth : 180;\n"
            f"        let sunElevation = SUN_DATA ? SUN_DATA.elevation : 45;\n"
            f"        const FARM_CROPS = {_farm_crops_js};\n"
            f"        const ALL_CROPS  = {_all_crops_js};\n"
            f"        const FISH_DATA  = {_fish_js};\n"
            f"        const HIGHLIGHT_RACK  = {json.dumps(st.session_state.pop('highlight_rack', None))};\n"
            f"        const HIGHLIGHT_CYCLE = {json.dumps(st.session_state.pop('highlight_cycle', None))};"
        )
    )

    components.html(html_with_data, height=1000, scrolling=False)


garden_planner()

# ── Layout ↔ Financial model consistency (runs on saved layout) ────────────────
if active_farm and _preload_objects_js != "[]":
    try:
        _loaded_objects = json.loads(_preload_objects_js)
        if _loaded_objects:
            st.divider()
            st.markdown("### 🔄 Layout ↔ Financial Model Consistency")
            st.caption(
                "Checks the last **saved** layout against the financial model parameters. "
                "Save the canvas first, then reload to update these checks."
            )
            _lm = _compute_layout_metrics(_loaded_objects)
            _conflicts = _run_consistency_check(_lm, active_farm)
            _render_consistency_panel(_conflicts, active_farm, _lm)
    except Exception:
        pass

# ── Layout history ──────────────────────────────────────────────────────────────
if active_farm:
    # Layout history
    with st.expander("📋 Layout history for this farm"):
        try:
            _hist = supabase.table("farm_layouts").select(
                "id, name, is_active, updated_at, notes"
            ).eq("farm_id", active_farm["id"]).order(
                "updated_at", desc=True
            ).limit(10).execute()
            if _hist.data:
                for _h in _hist.data:
                    _ha1, _ha2, _ha3 = st.columns([4, 2, 1])
                    _ha1.markdown(
                        f"{'✅ ' if _h['is_active'] else ''}"
                        f"**{_h['name']}** — {(_h.get('updated_at') or '')[:10]}"
                        + (f"  \n_{_h['notes']}_" if _h.get('notes') else "")
                    )
                    with _ha2:
                        if not _h["is_active"]:
                            if st.button("Restore", key=f"restore_{_h['id']}", use_container_width=True):
                                supabase.table("farm_layouts").update(
                                    {"is_active": False}
                                ).eq("farm_id", active_farm["id"]).execute()
                                supabase.table("farm_layouts").update(
                                    {"is_active": True}
                                ).eq("id", _h["id"]).execute()
                                st.rerun()
                    with _ha3:
                        if st.button("🗑", key=f"del_layout_{_h['id']}", help="Delete this layout version"):
                            supabase.table("farm_layouts").delete().eq("id", _h["id"]).execute()
                            st.rerun()
            else:
                st.caption("No saved layouts yet.")
        except Exception as _he:
            st.caption(f"Could not load history: {_he}")

# ── Solar Analysis Panel ──────────────────────────────────────────────────────
if active_farm and active_farm.get("lat") and active_farm.get("lon"):
    st.divider()
    st.markdown("### ☀️ Solar Analysis")
    st.caption(
        "Deterministic sun position model (NOAA algorithm). No API required — computed from "
        "farm coordinates and date. Useful for greenhouse and polytunnel siting. "
        "→ Assumptions §15 for DLI calibration notes."
    )
    _lat = float(active_farm["lat"])
    _lon = float(active_farm["lon"])
    _modality = active_farm.get("modality", "vertical_farm")
    _is_outdoor = _modality in ("greenhouse", "polytunnel", "aquaponics_decoupled", "aquaponics_coupled")

    if not _is_outdoor:
        st.info(
            "☀️ Solar analysis is most relevant for greenhouse and polytunnel farms. "
            "For vertical farms, outdoor conditions affect HVAC load only — "
            "see the weather widget in the Harvest Tracker."
        )

    _sun_c1, _sun_c2 = st.columns([1, 2])
    from datetime import datetime as _dtnow
    import math as _math
    _now = _dtnow.now()
    _now_pos = get_sun_position(_lat, _lon, _now)
    _ss      = get_sunrise_sunset(_lat, _lon, _now.date())

    with _sun_c1:
        st.markdown("**Current sun position**")
        st.metric("Elevation", f"{_now_pos['elevation']:.1f}°")
        st.metric("Azimuth",   f"{_now_pos['azimuth']:.1f}°")
        if _now_pos["is_daytime"]:
            st.success("🌞 Above horizon")
        else:
            st.info("🌙 Below horizon")
        st.markdown("**Today**")
        st.metric("Sunrise",    _ss["sunrise"])
        st.metric("Sunset",     _ss["sunset"])
        st.metric("Day length", f"{_ss['day_length_h']:.1f} h")

    with _sun_c2:
        _sel_date = st.date_input("Analyse date", value=date.today(), key="sun_date_sel")
        _sel_hour = st.slider("Hour of day", 5, 21, 12, key="sun_hour_sel", format="%d:00")
        _sel_dt   = _dtnow(_sel_date.year, _sel_date.month, _sel_date.day, _sel_hour, 0)
        _sel_pos  = get_sun_position(_lat, _lon, _sel_dt)
        _s1, _s2, _s3 = st.columns(3)
        _s1.metric("Elevation", f"{_sel_pos['elevation']:.1f}°")
        _s2.metric("Azimuth",   f"{_sel_pos['azimuth']:.1f}°")
        _shadow_mult = (
            round(1 / _math.tan(_math.radians(max(1, _sel_pos["elevation"]))), 1)
            if _sel_pos["elevation"] > 2 else None
        )
        _s3.metric("Shadow length",
                   f"{_shadow_mult:.1f}× height" if _shadow_mult else "∞ (below horizon)",
                   help="A 3m tall rack casts a shadow this many metres long at this moment.")

    # Monthly DLI chart
    st.markdown("**Monthly clear-sky DLI and day length**")
    st.caption(
        "DLI formula: 2.0 mol/m²/hr × sin(noon_elevation) × day_length_hours (clear sky). "
        "Actual DLI = clear-sky DLI × (1 − cloud_cover). "
        "Stored historical DLI from Open-Meteo is the more accurate value when available."
    )

    _monthly = get_monthly_sun_summary(_lat, _lon, year=date.today().year)
    _mlabels = [m["month_name"] for m in _monthly]

    if _is_outdoor:
        _min_dli = st.slider(
            "Crop minimum DLI (mol/m²/day)",
            5, 30, 12, key="min_dli_slider",
            help="Lettuce ~12 | Herbs ~14 | Strawberry ~16 | Tomato ~20"
        )
    else:
        _min_dli = None

    _fig_sun = go.Figure()
    _fig_sun.add_trace(go.Bar(
        name="Clear-sky DLI",
        x=_mlabels,
        y=[m["dli_clear_sky"] for m in _monthly],
        marker_color="#f1c40f",
        text=[f"{m['dli_clear_sky']:.0f}" for m in _monthly],
        textposition="outside",
        textfont=dict(size=10, color="#161a16"),
        yaxis="y",
    ))
    _fig_sun.add_trace(go.Scatter(
        name="Day length (h)",
        x=_mlabels,
        y=[m["day_length_h"] for m in _monthly],
        mode="lines+markers",
        line=dict(color="#3498db", width=2),
        yaxis="y2",
    ))
    _fig_sun.add_trace(go.Scatter(
        name="Noon elevation (°)",
        x=_mlabels,
        y=[m["max_elevation"] for m in _monthly],
        mode="lines+markers",
        line=dict(color="#2ecc71", width=2, dash="dot"),
        yaxis="y2",
    ))
    if _min_dli:
        _fig_sun.add_hline(
            y=_min_dli, line_dash="dash", line_color="#e74c3c",
            annotation_text=f"Min DLI ({_min_dli})",
            annotation_position="right",
            annotation_font_color="#e74c3c",
        )
    _fig_sun.update_layout(
        plot_bgcolor="#ffffff", paper_bgcolor="#ffffff", font_color="#161a16",
        height=360, margin=dict(t=20, b=60, l=10, r=10),
        legend=dict(orientation="h", y=-0.18),
        yaxis=dict(title="DLI (mol/m²/day)", showgrid=True, gridcolor="#e8e3d4"),
        yaxis2=dict(title="Hours / Degrees", overlaying="y", side="right", showgrid=False),
    )
    style_fig(_fig_sun)
    st.plotly_chart(_fig_sun, use_container_width=True)

    if _min_dli:
        _deficit = [m["month_name"] for m in _monthly if m["dli_clear_sky"] < _min_dli]
        if _deficit:
            st.warning(
                f"⚡ Supplemental lighting likely required in: **{', '.join(_deficit)}** "
                f"(clear-sky DLI < {_min_dli} mol/m²/day). "
                f"Actual deficit months will be more given cloud cover."
            )
        else:
            st.success(f"✅ Clear-sky DLI exceeds {_min_dli} mol/m²/day year-round.")

    if _is_outdoor:
        st.markdown("**🏗️ Orientation guidance**")
        _summer = get_sun_position(_lat, _lon, _dtnow(date.today().year, 6, 21, 12, 0))
        _winter = get_sun_position(_lat, _lon, _dtnow(date.today().year, 12, 21, 12, 0))
        st.markdown(
            f"Summer solstice noon: **{_summer['elevation']:.1f}°** elevation  |  "
            f"Winter solstice noon: **{_winter['elevation']:.1f}°** elevation"
        )
        if _lat > 20:
            st.info(
                "🧭 **Recommended:** Orient greenhouse ridge **East–West** so the south-facing "
                "roof slope maximises winter solar gain. A north-south orientation loses up to "
                "15% winter DLI at latitudes above 45°N. Source: Van Kooten & Heuvelink (2005)."
            )
        elif _lat > 0:
            st.info("🧭 Near-equatorial location — sun angle high year-round, orientation less critical.")
        else:
            st.info("🧭 **Southern hemisphere:** Orient ridge East–West with north-facing slope.")

elif active_farm:
    st.divider()
    st.info(
        "☀️ Solar analysis requires farm coordinates. "
        "Add lat/lon to the farm profile in the ROI Calculator to enable this panel."
    )
