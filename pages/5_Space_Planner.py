import streamlit as st
import streamlit.components.v1 as components
import json, os, sys
from datetime import date

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from supabase import create_client, Client
from core._styles import inject_styles
from core.farm_context import render_farm_context_sidebar, get_active_farm
from core.sun import get_sun_position, get_daily_sun_path, get_monthly_sun_summary, get_sunrise_sunset
import plotly.graph_objects as go

st.set_page_config(layout="wide", page_title="CEA Space Planner", page_icon="🏗️")
inject_styles()

@st.cache_resource
def get_supabase() -> Client:
    return create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])

supabase = get_supabase()

with st.sidebar:
    render_farm_context_sidebar(supabase=supabase)
    st.markdown("### 🏗️ Space Planner")
    st.caption("Design your farm layout in 2D and 3D. Save to link with financials and crop cycles.")

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
    _farm_js = json.dumps({
        "id":             active_farm.get("id"),
        "name":           active_farm.get("name", "My Farm"),
        "modality":       active_farm.get("modality", "vertical_farm"),
        "footprint":      float(active_farm.get("footprint") or active_farm.get("plant_footprint") or 0),
        "levels":         int(active_farm.get("levels") or 1),
        "country":        active_farm.get("country", ""),
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
            layers = int(o.get("layers") or 1)
            canopy_area  += area * layers
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
    model_ngf = float(farm.get("net_grow_factor") or 0)
    if model_ngf > 0 and lm["net_grow_pct"] > 0:
        diff_pp = abs(lm["net_grow_pct"] - model_ngf)
        if diff_pp > 10:
            conflicts.append({
                "field":      "Net grow factor",
                "layout_val": f"{lm['net_grow_pct']:.0f}%",
                "model_val":  f"{model_ngf:.0f}%",
                "diff":       f"{diff_pp:.0f}pp difference",
                "severity":   "warning",
                "suggestion": "The fraction of floor space occupied by racks differs from the model. "
                              "This affects yield per m² calculations.",
                "sync_key":   "net_grow_factor",
                "sync_val":   lm["net_grow_pct"],
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
                                f"✅ **{_cf['field']}** updated to {_cf['layout_val']} in the financial model. "
                                f"Re-run the ROI Calculator to see updated projections."
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
            st.metric("Rack canopy area", f"{layout_metrics['canopy_area']:,.1f} m²")
            st.metric("Path area", f"{layout_metrics['path_area']:,.1f} m²")
        with _lmc2:
            st.metric("Max rack levels", layout_metrics["max_rack_levels"])
            st.metric("Net grow factor", f"{layout_metrics['net_grow_pct']:.1f}%")
            st.metric("Walkways factor", f"{layout_metrics['walkways_pct']:.1f}%")
            if layout_metrics["tank_volume_m3"] > 0:
                st.metric("Tank volume", f"{layout_metrics['tank_volume_m3']:.1f} m³")


def garden_planner():
    html_code = r'''

    <style>
        body, html { margin: 0; padding: 0; background: #0B0E14; overflow: hidden; height: 100vh; }
        #ui-wrapper { height: 100vh; display: flex; flex-direction: column; box-sizing: border-box; padding: 10px; font-family: 'Inter', sans-serif; color: #eee; }
        #main-view { flex: 1; min-height: 0; }
    </style>

    <div id="ui-wrapper">
        
    <div style="display: flex; justify-content: space-between; align-items: center; background: #0D1117; padding: 10px 20px; border-radius: 8px; border: 1px solid #333; margin-bottom: 10px; flex-shrink: 0;">
        <div style="display: flex; gap: 20px;">
            <button id="opsBtn" onclick="toggleOpsMode()" style="padding: 10px 20px; background: #2ecc71; color: black; font-weight: bold; border: none; border-radius: 4px; cursor: pointer;">🚀 COMMIT TO OPERATIONS</button>
            <button onclick="saveToSupabase()" style="padding: 10px 20px; background: #3498db; color: white; border: none; border-radius: 4px; cursor: pointer;">💾 SAVE TO CLOUD</button>
            <button onclick="window.clearAll()" style="padding: 10px 20px; background: #441111; color: #ff9999; border: 1px solid #662222; border-radius: 4px; cursor: pointer;">🗑️ RESET</button>
            <button id="shadowBtn" onclick="toggleShadows()" style="padding: 10px 20px; background: #2c3e50; color: #f1c40f; border: 1px solid #444; border-radius: 4px; cursor: pointer;">☀️ SHADOWS ON</button>
            <button onclick="toggleFullscreen()" style="padding: 10px 20px; background: #555; color: white; border: none; border-radius: 4px; cursor: pointer;">⛶ FULLSCREEN</button>
        </div>
        <div style="font-size: 14px; color: #888; font-weight: bold;">
            STATUS: <span id="mode-status" style="color: #2ecc71;">ARCHITECT MODE (EDITABLE)</span>
        </div>
    </div>

        <div style="display:flex;flex-wrap:wrap;gap:16px;background:#161B22;padding:12px 16px;border-radius:8px;border:1px solid #333;margin-bottom:10px;align-items:center;">
        <div><label style="font-size:9px;color:#888;letter-spacing:.08em;">BUILDING AREA</label><div style="font-size:17px;font-weight:bold;color:#3498db;"><span id="m-build">0.0</span> m&#178;</div></div>
        <div><label style="font-size:9px;color:#888;letter-spacing:.08em;">MAX HEIGHT</label><div style="font-size:17px;font-weight:bold;color:#f1c40f;"><span id="m-height">0.0</span> m</div></div>
        <div><label style="font-size:9px;color:#888;letter-spacing:.08em;">CANOPY AREA</label><div style="font-size:17px;font-weight:bold;color:#2ecc71;"><span id="m-canopy">0.0</span> m&#178;</div></div>
        <div><label style="font-size:9px;color:#888;letter-spacing:.08em;">EFFICIENCY</label><div style="font-size:17px;font-weight:bold;color:#E599F7;"><span id="m-eff">0</span>%</div></div>
        <div><label style="font-size:9px;color:#888;letter-spacing:.08em;">EST. YIELD/YR</label><div style="font-size:17px;font-weight:bold;color:#f1c40f;"><span id="m-yield">&#8212;</span></div></div>
        <div><label style="font-size:9px;color:#888;letter-spacing:.08em;">RACKS</label><div style="font-size:17px;font-weight:bold;color:#aaa;"><span id="m-racks">0</span></div></div>
        <div style="margin-left:auto;display:flex;align-items:center;gap:8px;flex-wrap:wrap;">
            <label style="font-size:11px;color:#888;display:flex;align-items:center;gap:4px;cursor:pointer;">
                <input type="checkbox" id="snapToggle" checked style="accent-color:#3498db;"> Snap 0.5m
            </label>
            <div style="display:flex;align-items:center;gap:4px;">
                <span style="font-size:10px;color:#888;">N&#8593;</span>
                <input type="range" id="northSlider" min="0" max="359" value="0" step="1"
                    style="width:60px;accent-color:#f1c40f;" oninput="updateNorth(this.value)">
                <span id="northLabel" style="font-size:10px;color:#f1c40f;min-width:28px;">0&#176;</span>
                <span style="font-size:10px;color:#888;margin-left:8px;">&#9728; Time:</span>
                <input type="range" id="sunHourSlider" min="6" max="20" value="12" step="0.5"
                    style="width:80px;accent-color:#f1c40f;" oninput="updateSunFromSlider()">
                <span id="sunHourLabel" style="font-size:10px;color:#f1c40f;min-width:36px;">12:00</span>
                <button id="sunPlayBtn" onclick="toggleSunAnimation()" style="margin-top:6px;padding:4px 14px;background:#2d6a4f;color:#fff;border:none;border-radius:4px;cursor:pointer;font-size:12px;">&#9654; Play</button>
            </div>
            <select id="toolSelect" onchange="handleToolChange()" style="padding:7px 10px;background:#1e2530;color:white;border:1px solid #444;border-radius:5px;font-size:13px;">
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

            <div id="main-view" style="display: flex; gap: 10px;">
            <div id="canvas-container" style="flex: 2; background: #000; border-radius: 8px; position: relative; border: 1px solid #333; overflow: hidden;">
                <canvas id="canvas2d" style="display: block; width: 100%; height: 100%;"></canvas>
            </div>

            <div id="inspector" style="flex: 1; background: #0D1117; border-radius: 8px; border: 1px solid #333; padding: 20px; display: flex; flex-direction: column; gap: 20px;">
                <h3 style="margin: 0; color: #fff;">Object Inspector</h3>
                <div id="no-selection" style="color: #666; font-style: italic;">Select an element to edit properties.</div>
                
                <div id="editor-ui" style="display: none; flex-direction: column; gap: 15px;">
                    <div>
                        <label style="font-size: 11px; color: #888;">NAME</label>
                        <input type="text" id="objName" style="width: 100%; padding: 8px; background: #222; border: 1px solid #444; color: #fff; margin-top: 5px;">
                    </div>
                    
                    <div id="building-ui" style="display:none;">
    <div>
        <label style="font-size: 11px; color: #888;">FACILITY CATEGORY</label>
        <select id="buildType" onchange="toggleSpanUI()" style="width: 100%; padding: 8px; background: #222; border: 1px solid #444; color: #fff; margin-top: 5px;">
            <option value="warehouse">Vertical Farm (Warehouse)</option>
            <option value="greenhouse">High-Tech Greenhouse</option>
            <option value="polytunnel">Polytunnel (Arched)</option>
        </select>
    </div>

    <div id="span-selector" style="display:none; margin-top:10px;">
        <label style="font-size: 11px; color: #888;">STANDARD SPAN (WIDTH)</label>
        <select id="standardSpan" style="width: 100%; padding: 8px; background: #333; border: 1px solid #444; color: #fff; margin-top: 5px;">
            <option value="6.0">6.0m Small Span</option>
            <option value="8.0">8.0m Medium Span</option>
            <option value="9.6" selected>9.6m Professional Span</option>
            <option value="12.0">12.0m Wide Span</option>
        </select>
    </div>

    <div id="dim-inputs" style="margin-top:10px;">
        <div style="display: flex; gap: 10px;">
            <div style="flex: 1;">
                <label id="w-label" style="font-size: 11px; color: #888;">WIDTH (m)</label>
                <input type="number" id="buildWidth" step="0.1" style="width: 100%; padding: 8px; background: #222; border: 1px solid #444; color: #fff;">
            </div>
            <div style="flex: 1;">
                <label style="font-size: 11px; color: #888;">LENGTH (m)</label>
                <input type="number" id="buildLength" step="0.1" style="width: 100%; padding: 8px; background: #222; border: 1px solid #444; color: #fff;">
            </div>
        </div>
        <div style="margin-top:10px;">
            <label style="font-size: 11px; color: #888;">MAX HEIGHT (m)</label>
            <input type="number" id="buildHeight" step="0.5" style="width: 100%; padding: 8px; background: #222; border: 1px solid #444; color: #fff;">
        </div>
    </div>
                        <div id="warn-msg" style="display:none; margin-top:10px; color:#e74c3c; font-size:11px; padding:10px; background:rgba(231,76,60,0.1); border:1px solid #e74c3c; border-radius:4px;">
                            ⚠️ Warning: Racks are outside building bounds!
                        </div>
                    </div>

                    <div id="rack-ui" style="display:none;">
                        <!-- Rack subtype selector -->
                        <div style="margin-bottom:8px;">
                            <label style="font-size:11px;color:#888;display:block;margin-bottom:4px;">RACK TYPE</label>
                            <div id="rack-type-btns" style="display:flex;gap:4px;flex-wrap:wrap;">
                                <button onclick="setRackSubtype('standard')" id="rtype-standard"
                                    style="flex:1;padding:6px 4px;font-size:10px;font-weight:700;border:1px solid #444;border-radius:3px;cursor:pointer;background:#1e3a2a;color:#2ecc71;">
                                    &#128752; STANDARD</button>
                                <button onclick="setRackSubtype('wall')" id="rtype-wall"
                                    style="flex:1;padding:6px 4px;font-size:10px;font-weight:700;border:1px solid #444;border-radius:3px;cursor:pointer;background:#222;color:#888;">
                                    &#128255; WALL</button>
                                <button onclick="setRackSubtype('tower')" id="rtype-tower"
                                    style="flex:1;padding:6px 4px;font-size:10px;font-weight:700;border:1px solid #444;border-radius:3px;cursor:pointer;background:#222;color:#888;">
                                    &#11835; TOWER</button>
                                <button onclick="setRackSubtype('bench')" id="rtype-bench"
                                    style="flex:1;padding:6px 4px;font-size:10px;font-weight:700;border:1px solid #444;border-radius:3px;cursor:pointer;background:#222;color:#888;">
                                    &#9645; BENCH</button>
                            </div>
                        </div>
                        <!-- Subtype descriptions -->
                        <div id="rack-desc" style="font-size:10px;color:#666;margin-bottom:8px;padding:6px;background:#0d1117;border-radius:3px;"></div>
                        <!-- Universal Rack Dimensions -->
                        <div style="display:flex;gap:8px;margin-bottom:8px;">
                            <div style="flex:1;">
                                <label style="font-size:11px;color:#888;display:block;">WIDTH (m)</label>
                                <input type="number" id="rackWidth" step="0.1" min="0.1" style="width:100%;padding:8px;background:#222;border:1px solid #444;color:#fff;margin-top:5px;">
                            </div>
                            <div style="flex:1;">
                                <label style="font-size:11px;color:#888;display:block;">LENGTH (m)</label>
                                <input type="number" id="rackLength" step="0.1" min="0.1" style="width:100%;padding:8px;background:#222;border:1px solid #444;color:#fff;margin-top:5px;">
                            </div>
                            <div style="flex:1;">
                                <label style="font-size:11px;color:#888;display:block;">HEIGHT (m)</label>
                                <input type="number" id="rackHeight" step="0.1" min="0.1" style="width:100%;padding:8px;background:#222;border:1px solid #444;color:#fff;margin-top:5px;">
                            </div>
                        </div>

                        <!-- Layers and Spacing (Applies to standard) -->
                        <div id="rack-layer-controls" style="margin-bottom:8px;">
                            <div style="display:flex;gap:8px;">
                                <div style="flex:1;">
                                    <label style="font-size:11px;color:#888;">LAYERS</label>
                                    <input type="number" id="objLayers" min="1" max="20" value="5" style="width:100%;padding:8px;background:#222;border:1px solid #444;color:#fff;margin-top:5px;">
                                </div>
                                <div style="flex:1;" id="spacing-wrapper">
                                    <label style="font-size:11px;color:#888;display:block;">SPACING (m)</label>
                                    <input type="number" id="layerSpacing" step="0.1" value="0.6" style="width:100%;padding:8px;background:#222;border:1px solid #444;color:#fff;margin-top:5px;">
                                </div>
                            </div>
                        </div>
                        
                        <!-- Tower rack controls (shows for tower only) -->
                        <div id="rack-tower-controls" style="display:none;margin-bottom:8px;">
                            <label style="font-size:11px;color:#888;display:block;">PLANTS PER TOWER</label>
                            <input type="number" id="towerPlants" step="1" value="20" min="4" max="60" style="width:100%;padding:8px;background:#222;border:1px solid #444;color:#fff;margin-top:5px;">
                        </div>
                        <!-- Live KPIs — two sections: Model forecast & Layout actual -->
                        <div id="rack-kpis" style="margin-top:10px;background:#0d1117;border:1px solid #2a3a2a;border-radius:4px;padding:8px;font-size:11px;color:#aaa;">
                            <div style="font-size:9px;font-weight:700;color:#2ecc71;letter-spacing:.08em;margin-bottom:4px;">📐 THIS RACK</div>
                            <div style="display:grid;grid-template-columns:1fr 1fr;gap:3px;margin-bottom:8px;">
                                <span style="color:#888;">Canopy:</span><span id="kpi-canopy" style="color:#2ecc71;font-weight:600;"></span>
                                <span style="color:#888;">Yield/cycle:</span><span id="kpi-yield-cycle" style="color:#f1c40f;font-weight:600;"></span>
                                <span style="color:#888;">Yield/year:</span><span id="kpi-yield-year" style="color:#f1c40f;font-weight:600;"></span>
                                <span style="color:#888;">Revenue/yr:</span><span id="kpi-revenue" style="color:#e599f7;font-weight:600;"></span>
                                <span style="color:#888;">Energy/yr:</span><span id="kpi-energy" style="color:#ff9f43;font-weight:600;"></span>
                                <span style="color:#888;">Gross margin:</span><span id="kpi-margin" style="color:#54a0ff;font-weight:600;"></span>
                            </div>
                            <div style="font-size:9px;font-weight:700;color:#888;letter-spacing:.08em;margin-bottom:4px;border-top:1px solid #222;padding-top:6px;">📊 VS MODEL (pro-rated)</div>
                            <div style="display:grid;grid-template-columns:1fr 1fr;gap:3px;">
                                <span style="color:#666;">Model canopy:</span><span id="kpi-model-canopy" style="color:#888;font-weight:600;"></span>
                                <span style="color:#666;">Model yield/yr:</span><span id="kpi-model-yield" style="color:#888;font-weight:600;"></span>
                                <span style="color:#666;">Model revenue:</span><span id="kpi-model-rev" style="color:#888;font-weight:600;"></span>
                                <span style="color:#666;">Δ Revenue:</span><span id="kpi-delta-rev" style="font-weight:600;"></span>
                            </div>
                        </div>
                        <button onclick="duplicateSelected()" style="width:100%;margin-top:6px;padding:8px;background:#1e3a5f;border:1px solid #3498db;color:#3498db;font-weight:bold;border-radius:4px;cursor:pointer;">&#10064; DUPLICATE (Ctrl+D)</button>
                        <div id="aisle-warn" style="display:none;margin-top:8px;font-size:10px;color:#e74c3c;padding:6px;background:rgba(231,76,60,0.1);border:1px solid #e74c3c;border-radius:3px;">
                            &#9888; Aisle &lt;0.8m &#8212; too narrow for trolley access
                        </div>
                    </div>

                    <div id="tank-ui" style="display:none;">
                        <div style="display: flex; gap: 10px;">
                            <div style="flex: 1;">
                                <label style="font-size: 11px; color: #888;">WIDTH (m)</label>
                                <input type="number" id="tankWidth" step="0.1" style="width: 100%; padding: 8px; background: #222; border: 1px solid #444; color: #fff;">
                            </div>
                            <div style="flex: 1;">
                                <label style="font-size: 11px; color: #888;">LENGTH (m)</label>
                                <input type="number" id="tankLength" step="0.1" style="width: 100%; padding: 8px; background: #222; border: 1px solid #444; color: #fff;">
                            </div>
                        </div>
                        <div style="margin-top:10px;">
                            <label style="font-size: 11px; color: #888;">TANK DEPTH (m)</label>
                            <input type="number" id="tankDepth" step="0.1" style="width: 100%; padding: 8px; background: #222; border: 1px solid #444; color: #fff; margin-top: 5px;">
                        </div>
                        <!-- Live KPIs -->
                        <div id="tank-kpis" style="margin-top:10px;background:#0d1117;border:1px solid #1a3a5a;border-radius:4px;padding:8px;font-size:11px;color:#aaa;">
                            <div style="font-size:9px;font-weight:700;color:#3498db;letter-spacing:.08em;margin-bottom:4px;">🐟 THIS TANK</div>
                            <div style="display:grid;grid-template-columns:1fr 1fr;gap:4px;">
                                <span style="color:#888;">Volume:</span><span id="kpi-tank-vol" style="color:#3498db;font-weight:600;"></span>
                                <span style="color:#888;">Yield/cycle:</span><span id="kpi-fish-cycle" style="color:#f1c40f;font-weight:600;"></span>
                                <span style="color:#888;">Yield/year:</span><span id="kpi-fish-year" style="color:#f1c40f;font-weight:600;"></span>
                                <span style="color:#888;">Revenue/yr:</span><span id="kpi-fish-rev" style="color:#e599f7;font-weight:600;"></span>
                                <span style="color:#888;">Gross margin:</span><span id="kpi-fish-margin" style="color:#54a0ff;font-weight:600;"></span>
                            </div>
                            <div style="font-size:9px;font-weight:700;color:#888;letter-spacing:.08em;margin-bottom:4px;border-top:1px solid #222;padding-top:6px;">📊 VS MODEL (pro-rated)</div>
                            <div style="display:grid;grid-template-columns:1fr 1fr;gap:3px;">
                                <span style="color:#666;">Model vol:</span><span id="kpi-model-tank-vol" style="color:#888;font-weight:600;"></span>
                                <span style="color:#666;">Model yield/yr:</span><span id="kpi-model-fish-yield" style="color:#888;font-weight:600;"></span>
                                <span style="color:#666;">Model revenue:</span><span id="kpi-model-fish-rev" style="color:#888;font-weight:600;"></span>
                                <span style="color:#666;">Δ Revenue:</span><span id="kpi-delta-fish-rev" style="font-weight:600;"></span>
                            </div>
                        </div>
                        <div style="margin-top:10px; font-size: 10px; color: #3498db;">
                            Estimated Water Weight: <span id="water-weight">0</span> kg
                        </div>

                        <!-- Fish Ops Panel — visible in Operations Mode only -->
                        <div id="fish-ops-panel" style="display:none;margin-top:10px;background:#0d1117;border:1px solid #1a3a5a;border-radius:6px;padding:10px;font-size:11px;color:#ccc;">
                            <div style="font-size:10px;font-weight:700;color:#3498db;margin-bottom:6px;letter-spacing:1px;">🐟 LIVE FISH CYCLE</div>
                            <div id="fish-ops-content"></div>
                            <div id="fish-no-cycle" style="display:none;color:#666;font-style:italic;">No active fish cycle in this tank.</div>
                            <button id="fish-open-ht-btn" onclick="openFishInHarvestTracker()" style="display:none;width:100%;margin-top:8px;padding:7px;background:#1e3a5f;border:1px solid #3498db;color:#3498db;font-weight:bold;border-radius:4px;cursor:pointer;font-size:11px;">&#128640; Open in Harvest Tracker</button>
                            <button id="fish-stock-btn" onclick="openStockTankModal()" style="display:none;width:100%;margin-top:6px;padding:7px;background:#0d2a3a;border:1px solid #3498db;color:#3498db;font-weight:bold;border-radius:4px;cursor:pointer;font-size:11px;">&#43; Stock Tank</button>
                        </div>

                        <!-- Stock Tank Modal -->
                        <div id="stock-tank-modal" style="display:none;margin-top:10px;background:#111;border:1px solid #444;border-radius:6px;padding:12px;font-size:11px;color:#ccc;">
                            <div style="font-weight:700;color:#3498db;margin-bottom:8px;">🐟 Stock Tank</div>
                            <label style="display:block;color:#888;margin-bottom:2px;">Fish Species</label>
                            <select id="st-species" onchange="onSpeciesChange()" style="width:100%;padding:6px;background:#222;border:1px solid #444;color:#fff;border-radius:3px;margin-bottom:6px;"></select>
                            <div id="st-species-info" style="font-size:10px;color:#3498db;margin-bottom:6px;"></div>
                            <label style="display:block;color:#888;margin-bottom:2px;">Stocking Date</label>
                            <input type="date" id="st-stock-date" style="width:100%;padding:6px;background:#222;border:1px solid #444;color:#fff;border-radius:3px;margin-bottom:6px;">
                            <label style="display:block;color:#888;margin-bottom:2px;">Expected Harvest Date <span style="color:#555;">(auto-computed)</span></label>
                            <input type="date" id="st-harvest-date" style="width:100%;padding:6px;background:#222;border:1px solid #444;color:#fff;border-radius:3px;margin-bottom:6px;">
                            <label style="display:block;color:#888;margin-bottom:2px;">Tank Volume (m³) <span style="color:#555;">(auto from tank)</span></label>
                            <input type="number" id="st-volume" step="0.1" style="width:100%;padding:6px;background:#222;border:1px solid #444;color:#fff;border-radius:3px;margin-bottom:8px;">
                            <div style="display:flex;gap:6px;">
                                <button onclick="submitStockTank()" style="flex:1;padding:7px;background:#3498db;border:none;color:#fff;font-weight:bold;border-radius:4px;cursor:pointer;">💾 Save</button>
                                <button onclick="closeStockTankModal()" style="flex:1;padding:7px;background:#333;border:1px solid #555;color:#aaa;border-radius:4px;cursor:pointer;">✖ Cancel</button>
                            </div>
                            <div id="st-status" style="margin-top:6px;font-size:10px;"></div>
                        </div>
                    </div>

                    <div id="equip-ui" style="display:none;">
                        <label style="font-size: 11px; color: #888;">EQUIPMENT TYPE</label>
                        <select id="equipType" style="width: 100%; padding: 8px; background: #222; border: 1px solid #444; color: #fff; margin-top: 5px;">
                            <option value="hvac">HVAC Unit</option>
                            <option value="biofilter">Biofilter System</option>
                            <option value="pump">Pump Station</option>
                        </select>
                        <div style="margin-top:10px;">
                            <label style="font-size: 11px; color: #888;">UNIT HEIGHT (m)</label>
                            <input type="number" id="equipHeight" step="0.1" value="2.0" style="width: 100%; padding: 8px; background: #222; border: 1px solid #444; color: #fff;">
                        </div>
                    </div>

                    <div id="path-ui" style="display:none;">
                        <div style="display: flex; gap: 10px;">
                            <div style="flex: 1;">
                                <label style="font-size: 11px; color: #888;">PATH WIDTH (m)</label>
                                <input type="number" id="pathWidth" step="0.1" style="width: 100%; padding: 8px; background: #222; border: 1px solid #444; color: #fff;">
                            </div>
                            <div style="flex: 1;">
                                <label style="font-size: 11px; color: #888;">PATH LENGTH (m)</label>
                                <input type="number" id="pathLength" step="0.1" style="width: 100%; padding: 8px; background: #222; border: 1px solid #444; color: #fff;">
                            </div>
                        </div>
                    </div>

                    <!-- Ops Cycle Panel — visible in Operations Mode only -->
                    <div id="ops-cycle-panel" style="display:none;margin-top:10px;background:#0d1117;border:1px solid #2a4a3a;border-radius:6px;padding:10px;font-size:11px;color:#ccc;">
                        <div style="font-size:10px;font-weight:700;color:#f1c40f;margin-bottom:6px;letter-spacing:1px;">⚡ LIVE CYCLE DATA</div>
                        <div id="ops-cycle-content"></div>
                        <div id="ops-no-cycle" style="display:none;color:#666;font-style:italic;">No active cycle on this unit.</div>
                        <button id="ops-open-ht-btn" onclick="openInHarvestTracker()" style="display:none;width:100%;margin-top:8px;padding:7px;background:#1e3a5f;border:1px solid #3498db;color:#3498db;font-weight:bold;border-radius:4px;cursor:pointer;font-size:11px;">&#128640; Open in Harvest Tracker</button>
                        <button id="ops-start-cycle-btn" onclick="openStartCycleModal()" style="display:none;width:100%;margin-top:6px;padding:7px;background:#1a3a1a;border:1px solid #2ecc71;color:#2ecc71;font-weight:bold;border-radius:4px;cursor:pointer;font-size:11px;">&#43; Start New Cycle</button>
                    </div>

                    <!-- Start Cycle Modal -->
                    <div id="start-cycle-modal" style="display:none;margin-top:10px;background:#111;border:1px solid #444;border-radius:6px;padding:12px;font-size:11px;color:#ccc;">
                        <div style="font-weight:700;color:#2ecc71;margin-bottom:8px;">🌱 Start New Cycle</div>
                        <label style="display:block;color:#888;margin-bottom:2px;">Crop / Species</label>
                        <select id="sc-crop" style="width:100%;padding:6px;background:#222;border:1px solid #444;color:#fff;border-radius:3px;margin-bottom:6px;"></select>
                        <label style="display:block;color:#888;margin-bottom:2px;">Seeding Date</label>
                        <input type="date" id="sc-seed-date" style="width:100%;padding:6px;background:#222;border:1px solid #444;color:#fff;border-radius:3px;margin-bottom:6px;">
                        <label style="display:block;color:#888;margin-bottom:2px;">Expected Harvest Date</label>
                        <input type="date" id="sc-harvest-date" style="width:100%;padding:6px;background:#222;border:1px solid #444;color:#fff;border-radius:3px;margin-bottom:6px;">
                        <label style="display:block;color:#888;margin-bottom:2px;">Area (m²) <span style="color:#555;">(auto from unit)</span></label>
                        <input type="number" id="sc-area" step="0.1" style="width:100%;padding:6px;background:#222;border:1px solid #444;color:#fff;border-radius:3px;margin-bottom:8px;">
                        <div style="display:flex;gap:6px;">
                            <button onclick="submitStartCycle()" style="flex:1;padding:7px;background:#2ecc71;border:none;color:#000;font-weight:bold;border-radius:4px;cursor:pointer;">💾 Save</button>
                            <button onclick="closeStartCycleModal()" style="flex:1;padding:7px;background:#333;border:1px solid #555;color:#aaa;border-radius:4px;cursor:pointer;">✖ Cancel</button>
                        </div>
                        <div id="sc-status" style="margin-top:6px;font-size:10px;"></div>
                    </div>

                <div style="margin-top: auto; padding-top: 15px; border-top: 1px solid #333;">
                    <button onclick="deleteSelected()" style="width: 100%; padding: 10px; background: #882222; border: none; color: white; border-radius: 4px; cursor: pointer;">Delete Selected</button>
                </div>
                </div>

                <div style="margin-top: auto; border: 1px solid #222; border-radius: 8px; overflow: hidden;">
                    <div id="container3d" style="height: 300px; background: #000;"></div>
                </div>
            </div>
        </div>

        <!-- Custom Confirm Modal -->
        <div id="custom-confirm-modal" style="display:none; position: fixed; top: 50%; left: 50%; transform: translate(-50%, -50%); background: #161B22; border: 1px solid #e74c3c; border-radius: 8px; z-index: 1000; padding: 20px; box-shadow: 0 4px 12px rgba(0,0,0,0.8); text-align: center; min-width: 250px;">
            <div id="custom-confirm-msg" style="color: #eee; font-size: 14px; margin-bottom: 20px;">Are you sure?</div>
            <div style="display:flex;gap:10px;justify-content:center;">
                <button id="custom-confirm-yes" style="flex: 1; padding: 8px 16px; background: #e74c3c; border: none; color: white; border-radius: 4px; cursor: pointer; font-weight: bold;">Yes</button>
                <button onclick="closeCustomConfirm()" style="flex: 1; padding: 8px 16px; background: #333; border: 1px solid #555; color: #ccc; border-radius: 4px; cursor: pointer;">Cancel</button>
            </div>
        </div>
    </div>

    <script src="https://cdnjs.cloudflare.com/ajax/libs/three.js/r128/three.min.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/three@0.128.0/examples/js/controls/OrbitControls.js"></script>

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
        const renderer = new THREE.WebGLRenderer({ antialias: true });
        renderer.setSize(cont3d.clientWidth, cont3d.clientHeight);
        cont3d.appendChild(renderer.domElement);
        camera.position.set(15, 15, 15);
        const controls = new THREE.OrbitControls(camera, renderer.domElement);
        // --- 3D ENGINE RE-FIX ---
        scene.background = new THREE.Color(0x05070A); // Match 2D background

        // Ensure 3D Grid is permanent and added directly to scene
        const gridHelper = new THREE.GridHelper(500, 100, 0x30363D, 0x1C2128);
        scene.add(gridHelper);

        // Lights
        scene.add(new THREE.AmbientLight(0xffffff, 0.8));
        const sun = new THREE.DirectionalLight(0xffffff, 0.5); 
        sun.position.set(10, 20, 10); 
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
                btn.innerText = "🛠️ MODIFY STRUCTURE";
                btn.style.background = "#f1c40f";
                status.innerText = "OPERATIONS MODE (LIVE DATA)";
                status.style.color = "#f1c40f";
                toolSel.value = "select";
                toolSel.disabled = true;

                fetchAndApplyCycleData();  // Load live cycle data
            } else {
                btn.innerText = "🚀 COMMIT TO OPERATIONS";
                btn.style.background = "#2ecc71";
                status.innerText = "ARCHITECT MODE (EDITABLE)";
                status.style.color = "#2ecc71";
                toolSel.disabled = false;
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
                    statusEl.innerText = `OPERATIONS MODE — ${cycles.length} active cycles, ${totalAssigned} units with data`;
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
            if (saveBtn) { saveBtn.innerText = "⏳ Saving..."; saveBtn.disabled = true; saveBtn.style.background = "#888"; }

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
                    saveBtn.innerText = "✅ SAVED (ID " + newId + ")";
                    saveBtn.style.background = "#2ecc71"; saveBtn.disabled = false;
                    saveBtn.style.boxShadow = "";
                    setTimeout(() => { saveBtn.innerText = "💾 SAVE TO CLOUD"; saveBtn.style.background = "#3498db"; }, 4000);
                }
            } catch(err) {
                console.error("Save error:", err);
                if (saveBtn) {
                    saveBtn.innerText = "❌ " + err.message.substring(0,50);
                    saveBtn.style.background = "#e74c3c"; saveBtn.disabled = false;
                    setTimeout(() => { saveBtn.innerText = "💾 SAVE TO CLOUD"; saveBtn.style.background = "#3498db"; }, 6000);
                }
            }
        }

        function toggleShadows() {
            showShadows = !showShadows;
            const btn = document.getElementById('shadowBtn');
            if (btn) {
                btn.innerText  = showShadows ? "☀️ SHADOWS ON" : "☀️ SHADOWS OFF";
                btn.style.background = showShadows ? "#2c3e50" : "#1a1a1a";
                btn.style.color      = showShadows ? "#f1c40f" : "#555";
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
                        b.style.boxShadow = "0 0 10px rgba(52,152,219,0.9)";
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

            const statusColours = {seeding:'#5C7CFA', growing:'#2ecc71', ready:'#f1c40f', failed:'#e74c3c'};
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

            const statusColours = {seeding:'#3498db', growing:'#2ecc71', ready:'#f1c40f', failed:'#e74c3c'};
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
                statusEl.textContent = '❌ No active farm.'; statusEl.style.color = '#e74c3c'; return;
            }
            const species     = document.getElementById('st-species').value;
            const stockDate   = document.getElementById('st-stock-date').value;
            const harvestDate = document.getElementById('st-harvest-date').value || null;
            const volume      = parseFloat(document.getElementById('st-volume').value) || 0;
            const tankName    = selection ? selection.name : null;

            if (!species || !stockDate) {
                statusEl.textContent = '❌ Species and stocking date required.';
                statusEl.style.color = '#e74c3c'; return;
            }

            statusEl.textContent = '⏳ Saving...'; statusEl.style.color = '#aaa';

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
                statusEl.textContent = '✅ Tank stocked!'; statusEl.style.color = '#2ecc71';
                setTimeout(() => { closeStockTankModal(); fetchAndApplyCycleData(); }, 1200);
            } catch(err) {
                statusEl.textContent = '❌ ' + err.message.substring(0, 60);
                statusEl.style.color = '#e74c3c';
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
                const area = selection.type === 'tank' ? (selection.w * selection.h * (selection.height || 1.5)) : (selection.w * selection.h * (selection.layers || 1));
                const areaEl = document.getElementById('sc-area');
                if (areaEl) {
                    areaEl.value = area.toFixed(1);
                    areaEl.previousElementSibling.innerHTML = selection.type === 'tank' ? `Volume (m³) <span style="color:#555;">(auto from tank)</span>` : `Area (m²) <span style="color:#555;">(auto from rack)</span>`;
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
                statusEl.textContent = '❌ No active farm.'; statusEl.style.color = '#e74c3c'; return;
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
                statusEl.textContent = '❌ Crop and seeding date required.'; statusEl.style.color = '#e74c3c'; return;
            }

            statusEl.textContent = '⏳ Saving...'; statusEl.style.color = '#aaa';

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
                statusEl.textContent = '✅ Cycle started!'; statusEl.style.color = '#2ecc71';

                // If rack has layers, also insert rack_layer_assignments for all layers
                if (newId && rackName && selection && selection.layers > 0) {
                    const layerRows = [];
                    for (let i = 0; i < selection.layers; i++) {
                        layerRows.push({
                            farm_id:     FARM_DATA.id,
                            cycle_id:    newId,
                            rack_name:   rackName,
                            layer_index: i,
                            area_m2:     parseFloat(((selection.w * selection.h)).toFixed(2)),
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
                statusEl.style.color = '#e74c3c';
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
                    selection.layers  = 1;
                    selection.spacing = 0.0;
                    selection.height  = selection.height || 2.4;
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
                btn.style.background = isActive ? '#1e3a2a' : '#222';
                btn.style.color      = isActive ? RACK_TYPES[t].color2d : '#888';
                btn.style.borderColor = isActive ? RACK_TYPES[t].color2d : '#444';
            });
            // Show/hide subtype-specific controls
            document.getElementById('rack-layer-controls').style.display = ['standard'].includes(subtype) ? 'block' : 'none';
            document.getElementById('spacing-wrapper').style.display     = subtype === 'standard' ? 'block' : 'none';
            document.getElementById('rack-tower-controls').style.display = subtype === 'tower' ? 'block' : 'none';
            // Update description
            const descEl = document.getElementById('rack-desc');
            if (descEl) descEl.innerText = RACK_TYPES[subtype]?.desc || '';
        }
        window.setRackSubtype = setRackSubtype;

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
            const canopy    = layerArea * layers;

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
                activeCycles.forEach(c => {
                    // Canopy from assignment area or rack area
                    const cAssign = _liveAssignments.filter(a => a.cycle_id === c.id && a.rack_name === selection.name);
                    const cArea   = cAssign.reduce((s, a) => s + (parseFloat(a.area_m2) || layerArea), 0)
                                    || parseFloat(c.area_m2) || layerArea;
                    liveCanopy += cArea;

                    // Yield from crop data
                    const d = getCropData(c.crop);
                    const priceOverride = FARM_DATA ? parseFloat(FARM_DATA.price_override || 0) : 0;
                    const effPrice = priceOverride > 0 ? priceOverride : d.p;
                    const annualYield = cArea * d.y;
                    liveYieldYear   += annualYield;
                    liveYieldCycle  += annualYield / Math.max(1, Math.round(d.c));
                    liveRevYear     += annualYield * effPrice;
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
                    document.getElementById('kpi-revenue').innerText      = '€' + Math.round(liveRevYear).toLocaleString() + '/yr';
                } else {
                    // No cycles — show model forecast greyed
                    document.getElementById('kpi-canopy').innerText      = canopy.toFixed(1) + ' m²';
                    document.getElementById('kpi-yield-cycle').innerText  = (modelYield / Math.max(1, cyclesEst)).toFixed(0) + ' kg (est)';
                    document.getElementById('kpi-yield-year').innerText   = Math.round(modelYield).toLocaleString() + ' kg/yr (est)';
                    document.getElementById('kpi-revenue').innerText      = '€' + Math.round(modelRev).toLocaleString() + '/yr (est)';
                }

                // Energy estimate
                const isVF = !FARM_DATA || (FARM_DATA.modality === 'vertical_farm');
                const kwh_per_m2_yr = isVF ? (200 * 8760 / 1000) : (50 * 4380 / 1000);
                const energyCost = canopy * kwh_per_m2_yr * 0.25;
                const revForMargin = hasLiveData ? liveRevYear : modelRev;
                const margin = revForMargin > 0 ? ((revForMargin - energyCost) / revForMargin * 100) : 0;
                document.getElementById('kpi-energy').innerText       = '€' + Math.round(energyCost).toLocaleString() + '/yr';
                document.getElementById('kpi-margin').innerText       = (margin > 0 ? '+' : '') + margin.toFixed(0) + '%';
                document.getElementById('kpi-margin').style.color     = margin > 30 ? '#2ecc71' : margin > 0 ? '#f1c40f' : '#e74c3c';
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
                    document.getElementById('kpi-model-rev').innerText    = '€' + Math.round(mRev).toLocaleString() + '/yr';
                    document.getElementById('kpi-delta-rev').innerText    = (deltaRev >= 0 ? '+' : '') + '€' + Math.round(deltaRev).toLocaleString();
                    document.getElementById('kpi-delta-rev').style.color  = deltaRev >= 0 ? '#2ecc71' : '#e74c3c';
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
                    document.getElementById('kpi-fish-rev').innerText      = '€' + Math.round(liveRevYear).toLocaleString() + '/yr';
                } else {
                    document.getElementById('kpi-tank-vol').innerText      = vol.toFixed(1) + ' m³';
                    document.getElementById('kpi-fish-cycle').innerText    = (modelYield / Math.max(1, cyclesEst)).toFixed(0) + ' kg (est)';
                    document.getElementById('kpi-fish-year').innerText     = Math.round(modelYield).toLocaleString() + ' kg/yr (est)';
                    document.getElementById('kpi-fish-rev').innerText      = '€' + Math.round(modelRev).toLocaleString() + '/yr (est)';
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
                    document.getElementById('kpi-model-fish-rev').innerText   = '€' + Math.round(mRev).toLocaleString() + '/yr';
                    document.getElementById('kpi-delta-fish-rev').innerText   = (deltaRev >= 0 ? '+' : '') + '€' + Math.round(deltaRev).toLocaleString();
                    document.getElementById('kpi-delta-fish-rev').style.color = deltaRev >= 0 ? '#2ecc71' : '#e74c3c';
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
                    document.getElementById('rackLength').value = selection.h.toFixed(2);
                    document.getElementById('rackHeight').value = (selection.height || 2.5).toFixed(2);
                    document.getElementById('objLayers').value = selection.layers;
                    document.getElementById('layerSpacing').value = selection.spacing || 0.6;
                    document.getElementById('towerPlants').value  = selection.layers || 20;
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
            ctx.strokeStyle = "#e74c3c";
            ctx.fillStyle = "#e74c3c";

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

        function draw() {
            ctx.globalAlpha = 1.0;
            ctx.fillStyle = "#05070A"; // Deep Navy Background
            ctx.fillRect(0, 0, canvas.width, canvas.height);
            
            if (isOpsMode) ctx.globalAlpha = 0.5;

            // Grid
            ctx.strokeStyle = "#1C2128"; 
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
                    ctx.fillStyle = "#1a2850";
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

                    ctx.strokeStyle = isSel ? "#3498db" : "#e74c3c";
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

                    ctx.strokeStyle = isSelectTool ? "#3498db" : "#FFD43B"; 
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
                        
                        ctx.fillStyle = "#FFD43B";
                        ctx.font = "bold 11px Inter";
                        ctx.fillText(`${ew.toFixed(2)}m x ${eh.toFixed(2)}m`, labelX + 8, labelY + 18);
                        ctx.fillStyle = "#40C057";
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
                    const line = new THREE.LineSegments(edges, new THREE.LineBasicMaterial({ color: 0xFFFFFF, linewidth: 2 }));

                    const mat = new THREE.MeshPhongMaterial({ 
                        color: bType === 'warehouse' ? 0x5C7CFA : 0x00d4ff, 
                        transparent: true, opacity: 0.1, shininess: 100 
                    });
                    const mesh = new THREE.Mesh(geom, mat);
                    
                    const posY = (bType === 'polytunnel') ? 0 : obj.height/2;
                    mesh.position.set(obj.x + obj.w/2, posY, obj.y + obj.h/2);
                    line.position.copy(mesh.position);
                    
                    objectGroup.add(mesh);
                    objectGroup.add(line); // Add the "pencil" outline
                } 
                else if (obj.type === 'tank') {
                    // NEW: Blue translucent water volume with a dark frame
                    const geom = new THREE.BoxGeometry(obj.w, obj.height, obj.h);
                    const mat = new THREE.MeshPhongMaterial({ color: 0x0969da, transparent: true, opacity: 0.6 });
                    const mesh = new THREE.Mesh(geom, mat);
                    mesh.position.set(obj.x + obj.w/2, obj.height/2, obj.y + obj.h/2);
                    
                    const edges = new THREE.EdgesGeometry(geom);
                    const line = new THREE.LineSegments(edges, new THREE.LineBasicMaterial({ color: 0x3498db }));
                    line.position.copy(mesh.position);
                    
                    objectGroup.add(mesh);
                    objectGroup.add(line);
                } else if (obj.type === 'equip') {
                    const geom = new THREE.BoxGeometry(obj.w, obj.height, obj.h);
                    const color = obj.subType === 'hvac' ? 0xff922b : 0x868e96;
                    const mat = new THREE.MeshPhongMaterial({ color: color });
                    const mesh = new THREE.Mesh(geom, mat);
                    mesh.position.set(obj.x + obj.w/2, obj.height/2, obj.y + obj.h/2);
                    
                    const edges = new THREE.EdgesGeometry(geom);
                    const line = new THREE.LineSegments(edges, new THREE.LineBasicMaterial({ color: 0xffffff }));
                    line.position.copy(mesh.position);
                    
                    objectGroup.add(mesh);
                    objectGroup.add(line);
                } else if (obj.type === 'rack') {
                    const spacing  = obj.spacing || 0.6;
                    const rType    = obj.rackType || 'standard';
                    const baseColor = {standard:0x40C057, wall:0x74c0fc, tower:0xffd43b, bench:0xcc5de8}[rType] || 0x40C057;
                    // Per-layer status colours (from cycle data)
                    const statusColors = {seeding:0x3498db, growing:0x2ecc71, ready:0xf1c40f, failed:0xe74c3c};

                    if (rType === 'tower') {
                        // Tower: vertical cylinder with plant nodes
                        const poleG = new THREE.CylinderGeometry(0.04, 0.04, obj.height || 2.0, 8);
                        const poleM = new THREE.MeshPhongMaterial({color: 0x888888});
                        const pole  = new THREE.Mesh(poleG, poleM);
                        pole.position.set(obj.x + obj.w/2, (obj.height||2.0)/2, obj.y + obj.h/2);
                        objectGroup.add(pole);
                        // Plant nodes as small spheres at regular intervals
                        const nPlants = obj.layers || 20;
                        const stepH   = (obj.height || 2.0) / nPlants;
                        for (let i = 0; i < nPlants; i++) {
                            const layerStatus = obj.layerStatus?.[i] || '';
                            const col  = statusColors[layerStatus] || baseColor;
                            const sg   = new THREE.SphereGeometry(0.06, 6, 6);
                            const sm   = new THREE.MeshPhongMaterial({color: col});
                            const s    = new THREE.Mesh(sg, sm);
                            const angle = (i / nPlants) * Math.PI * 4; // spiral
                            s.position.set(
                                obj.x + obj.w/2 + 0.12 * Math.cos(angle),
                                i * stepH + 0.2,
                                obj.y + obj.h/2 + 0.12 * Math.sin(angle)
                            );
                            objectGroup.add(s);
                        }
                    } else if (rType === 'wall') {
                        // Wall rack: single vertical growing surface
                        const layerStatus = obj.layerStatus?.[0] || obj.cycleStatus || '';
                        const col = statusColors[layerStatus] || baseColor;
                        const panelG = new THREE.BoxGeometry(obj.w || 0.3, obj.height || 2.4, obj.h);
                        const panelM = new THREE.MeshPhongMaterial({color: col, transparent:true, opacity:0.85});
                        const panel  = new THREE.Mesh(panelG, panelM);
                        panel.position.set(obj.x + (obj.w||0.3)/2, (obj.height||2.4)/2, obj.y + obj.h/2);
                        objectGroup.add(panel);
                        const eg = new THREE.EdgesGeometry(panelG);
                        const el = new THREE.LineSegments(eg, new THREE.LineBasicMaterial({color:0xffffff,linewidth:1}));
                        el.position.copy(panel.position);
                        objectGroup.add(el);
                    } else if (rType === 'bench') {
                        // Single bench: legs + surface
                        const legH = obj.height || 0.9;
                        [[0.1,0.1],[obj.w-0.1,0.1],[0.1,obj.h-0.1],[obj.w-0.1,obj.h-0.1]].forEach(([lx,ly]) => {
                            const lg = new THREE.CylinderGeometry(0.03,0.03,legH,6);
                            const lm = new THREE.MeshPhongMaterial({color:0x555555});
                            const l  = new THREE.Mesh(lg, lm);
                            l.position.set(obj.x+lx, legH/2, obj.y+ly);
                            objectGroup.add(l);
                        });
                        const layerStatus = obj.layerStatus?.[0] || obj.cycleStatus || '';
                        const topCol = statusColors[layerStatus] || baseColor;
                        const tg = new THREE.BoxGeometry(obj.w, 0.04, obj.h);
                        const tm = new THREE.MeshPhongMaterial({color: topCol, transparent:true, opacity:0.85});
                        const top = new THREE.Mesh(tg, tm);
                        top.position.set(obj.x+obj.w/2, legH, obj.y+obj.h/2);
                        objectGroup.add(top);
                        // Edges
                        const eg = new THREE.EdgesGeometry(tg);
                        const el = new THREE.LineSegments(eg, new THREE.LineBasicMaterial({color:0xffffff,linewidth:1}));
                        el.position.copy(top.position);
                        objectGroup.add(el);
                    } else {
                        // Standard rack: column frames + colour-coded shelves
                        // Frame posts
                        const postH = obj.height || (spacing * obj.layers + 0.3);
                        [[0.04,0.04],[obj.w-0.04,0.04],[0.04,obj.h-0.04],[obj.w-0.04,obj.h-0.04]].forEach(([px,py]) => {
                            const pg = new THREE.CylinderGeometry(0.025,0.025,postH,6);
                            const pm = new THREE.MeshPhongMaterial({color:0x555555});
                            const p  = new THREE.Mesh(pg, pm);
                            p.position.set(obj.x+px, postH/2, obj.y+py);
                            objectGroup.add(p);
                        });
                        // Shelves with per-layer colour
                        for (let i = 0; i < obj.layers; i++) {
                            const layerStatus = obj.layerStatus?.[i] || '';
                            const col  = statusColors[layerStatus] || baseColor;
                            const shelfG = new THREE.BoxGeometry(obj.w, 0.04, obj.h);
                            const shelfM = new THREE.MeshPhongMaterial({color: col, transparent:true, opacity:0.85});
                            const shelf  = new THREE.Mesh(shelfG, shelfM);
                            const yPos = 0.2 + i * ((postH - 0.3) / Math.max(1, obj.layers));
                            shelf.position.set(obj.x+obj.w/2, yPos, obj.y+obj.h/2);
                            objectGroup.add(shelf);
                            // Shelf edge highlight
                            const eg = new THREE.EdgesGeometry(shelfG);
                            const el = new THREE.LineSegments(eg, new THREE.LineBasicMaterial({color:0xffffff,linewidth:1}));
                            el.position.copy(shelf.position);
                            objectGroup.add(el);
                        }
                    }
                } else if (obj.type === 'path') {
                    const geom = new THREE.BoxGeometry(obj.w, 0.02, obj.h);
                    const mat = new THREE.MeshPhongMaterial({ color: 0x212529 });
                    const mesh = new THREE.Mesh(geom, mat);
                    mesh.position.set(obj.x + obj.w/2, 0.01, obj.y + obj.h/2);
                    objectGroup.add(mesh);
                } else if (obj.type === 'plot') {
                    const geom = new THREE.PlaneGeometry(obj.w, obj.h);
                    const edges = new THREE.EdgesGeometry(new THREE.BoxGeometry(obj.w, 0.01, obj.h));
                    const line = new THREE.LineSegments(edges, new THREE.LineBasicMaterial({ color: 0xf03e3e, dashSize: 1, gapSize: 0.5 }));
                    line.position.set(obj.x + obj.w/2, 0.01, obj.y + obj.h/2);
                    objectGroup.add(line);
                } else if (obj.type === 'measure') {
                    const points = [];
                    points.push(new THREE.Vector3(obj.startX, 0.02, obj.startY));
                    points.push(new THREE.Vector3(obj.endX, 0.02, obj.endY));
                    const geom = new THREE.BufferGeometry().setFromPoints(points);
                    const line = new THREE.Line(geom, new THREE.LineBasicMaterial({ color: 0xe74c3c, linewidth: 2 }));
                    objectGroup.add(line);
                }
            });
        }

        function updateStats() {
            let bA=0,cA=0,maxH=0,rackCnt=0,tG=0;
            objects.forEach(o=>{
                if(o.type==='building'){bA+=o.w*o.h;if(o.height>maxH)maxH=o.height;}
                else if(o.type==='tank'){const wt=o.w*o.h*o.height*1000;if(selection&&selection.id===o.id)document.getElementById('water-weight').innerText=wt.toLocaleString();tG+=o.w*o.h;}
                else if(o.type==='rack'){cA+=o.w*o.h*(o.layers||1);tG+=o.w*o.h;rackCnt++;}
            });
            document.getElementById('m-build').innerText=bA.toFixed(1);
            document.getElementById('m-canopy').innerText=cA.toFixed(1);
            document.getElementById('m-height').innerText=maxH.toFixed(1);
            document.getElementById('m-racks').innerText=rackCnt;
            document.getElementById('m-eff').innerText=bA>0?Math.round(tG/bA*100):0;
            document.getElementById('m-yield').innerText=cA>0?Math.round(cA*4.2*13).toLocaleString()+' kg/yr':'—';
            checkSafety();
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
