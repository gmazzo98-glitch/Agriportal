import streamlit as st
import sys, os, json
import datetime as _dt
from supabase import create_client, Client

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from core._styles import inject_styles
from core._home_styles import inject_home_styles
from core.auth import require_login, current_user, logout
from core.farm_context import (
    load_farm, clear_farm, get_active_farm,
    MODALITY_LABELS, MODALITY_RADIO, MODALITY_COLOURS,
)
from core.data_tables import COUNTRIES, CROPS
from core.greenhouse_data_tables import GREENHOUSE_CROPS, POLYTUNNEL_CROPS, FISH_SPECIES

st.set_page_config(
    page_title="Agricultural Intelligence Portal",
    page_icon="🌱",
    layout="wide",
)
inject_styles()
require_login()

# ══════════════════════════════════════════════════════════════════════════════
# DESIGN — "Workspace, not catalogue."
# ----------------------------------------------------------------------------
# Two-column layout. Left: compact farm finder (rows, search, single-select).
# Right: context panel — when a farm is selected, shows recent activity
# timeline + three destination cards framed as next-step actions.
# Single accent (#3a6b40, moss green). Native system sans only.
# ══════════════════════════════════════════════════════════════════════════════

inject_home_styles()

# ──────────────────────────────────────────────────────────────────────────────
# Supabase
# ──────────────────────────────────────────────────────────────────────────────
@st.cache_resource
def get_supabase() -> Client:
    return create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])

supabase = get_supabase()

# ──────────────────────────────────────────────────────────────────────────────
# Modality lookups
# ──────────────────────────────────────────────────────────────────────────────
_MOD_LABEL = {
    "vertical_farm":        "Vertical Farm",
    "greenhouse":           "Greenhouse",
    "polytunnel":           "Polytunnel",
    "aquaponics_decoupled": "Decoupled Aquaponics",
    "aquaponics_coupled":   "Coupled Aquaponics",
}
_MOD_SWITCH = {
    "vertical_farm":        "🏭 Indoor Vertical Farm",
    "greenhouse":           "🌿 High-Tech Greenhouse",
    "polytunnel":           "🌿 High-Tech Greenhouse",
    "aquaponics_decoupled": "🐟 Decoupled Aquaponics",
    "aquaponics_coupled":   "♻️ Coupled Aquaponics",
}
_MOD_MONOGRAM = {
    "vertical_farm":        "VF",
    "greenhouse":           "GH",
    "polytunnel":           "PT",
    "aquaponics_decoupled": "AD",
    "aquaponics_coupled":   "AC",
}

def _fmt_date(s):
    if not s:
        return None
    return str(s)[:10]

def _days_since(s):
    if not s:
        return None
    try:
        d = _dt.date.fromisoformat(str(s)[:10])
        return (_dt.date.today() - d).days
    except Exception:
        return None

# ──────────────────────────────────────────────────────────────────────────────
# Top bar (persistent active-farm indicator)
# ──────────────────────────────────────────────────────────────────────────────
_active = st.session_state.get("active_farm")

if _active:
    _pill = (
        f'<span class="session-pill">'
        f'<span class="dot"></span>'
        f'<span>Active &nbsp;</span>'
        f'<span class="farm">{_active["name"]}</span>'
        f'</span>'
    )
else:
    _pill = (
        '<span class="session-pill empty">'
        '<span class="dot"></span>'
        '<span>No farm selected</span>'
        '</span>'
    )

st.markdown(
    f"""
    <div class="topbar">
      <div class="brand">
        <span class="mark">A</span>
        <span>AgriPortal</span>
        <span class="sub">Agricultural Intelligence</span>
      </div>
      {_pill}
    </div>
    """,
    unsafe_allow_html=True,
)

# ── User info + logout ────────────────────────────────────────────────────────
_uc1, _uc2 = st.columns([6, 1])
with _uc1:
    st.caption(f"Signed in as **{current_user()}**")
with _uc2:
    if st.button("Sign out", use_container_width=True):
        logout()

# ──────────────────────────────────────────────────────────────────────────────
# Load farms — filtered to current user
# ──────────────────────────────────────────────────────────────────────────────
try:
    _resp = supabase.table("farms").select(
        "id, name, modality, country, crop, footprint, created_at, model_updated_at, lat, lon"
    ).eq("owner_id", current_user()).order("created_at", desc=True).execute()
    _farms = _resp.data or []
except Exception as e:
    _farms = []
    st.error(f"Could not load farm profiles: {e}")

# Local UI selection (separate from session active_farm — selection is just preview)
if "_selected_farm_id" not in st.session_state:
    st.session_state["_selected_farm_id"] = (_active or {}).get("id") if _active else (
        _farms[0]["id"] if _farms else None
    )

# Handle selection clicks (set via query param trick — but Streamlit columns of
# transparent buttons over the row are simplest). We use st.button per row.

# ──────────────────────────────────────────────────────────────────────────────
# Farm Setup state (triggered from empty state or "New Farm" button)
# ──────────────────────────────────────────────────────────────────────────────
if "farm_setup_mode" not in st.session_state:
    st.session_state["farm_setup_mode"] = False
if "farm_setup_step" not in st.session_state:
    st.session_state["farm_setup_step"] = 1
if "farm_setup_data" not in st.session_state:
    st.session_state["farm_setup_data"] = {}

def _render_farm_setup():
    """Multi-step guided farm creation form."""
    _country_list = sorted(COUNTRIES.keys())
    _step = st.session_state["farm_setup_step"]
    _data = st.session_state["farm_setup_data"]

    # Progress bar
    st.markdown(
        f'<div style="display:flex;gap:8px;margin-bottom:20px;">'
        + "".join([
            f'<div style="flex:1;height:4px;background:{"#2f5d3a" if i <= _step else "#d9d4c5"};'
            f'border-radius:2px;"></div>'
            for i in range(1, 5)
        ])
        + f'</div><div style="font-size:12px;color:#7a807a;margin-bottom:16px;">'
        f'Step {_step} of 4</div>',
        unsafe_allow_html=True,
    )

    if _step == 1:
        st.markdown("### Farm Identity")
        _name = st.text_input("Farm name *", value=_data.get("name", ""),
                               key="fs_name", placeholder="e.g. Berlin Rooftop Farm")
        st.markdown("**Modality** *")
        _mod_options = {
            "vertical_farm":        ("🏭", "Indoor Vertical Farm",
                                     "Fully controlled, artificial lighting, multiple crop levels."),
            "greenhouse":           ("🌿", "High-Tech Greenhouse",
                                     "Venlo or multi-span glass, supplemental lighting optional."),
            "polytunnel":           ("🌿", "Polytunnel",
                                     "Low-cost plastic structure, natural light primary."),
            "aquaponics_decoupled": ("🐟", "Decoupled Aquaponics",
                                     "Fish and plant systems with separate water loops."),
            "aquaponics_coupled":   ("♻️", "Coupled Aquaponics",
                                     "Fully integrated fish-plant nutrient cycle."),
        }
        _current_mod = _data.get("modality", "vertical_farm")
        _mod_cols = st.columns(len(_mod_options))
        for _ci, (_mk, (_icon, _mlabel, _mdesc)) in enumerate(_mod_options.items()):
            with _mod_cols[_ci]:
                _bg = "#e6ede4" if _mk == _current_mod else "#ffffff"
                _border = "2px solid #2f5d3a" if _mk == _current_mod else "1px solid #d9d4c5"
                st.markdown(
                    f'<div style="background:{_bg};border:{_border};border-radius:3px;'
                    f'padding:10px 8px;text-align:center;cursor:pointer;">'
                    f'<div style="font-size:20px;">{_icon}</div>'
                    f'<div style="font-size:12px;font-weight:700;margin:4px 0 2px;">{_mlabel}</div>'
                    f'<div style="font-size:10px;color:#7a807a;">{_mdesc}</div>'
                    f'</div>',
                    unsafe_allow_html=True,
                )
                if st.button("Select", key=f"fs_mod_{_mk}", use_container_width=True):
                    st.session_state["farm_setup_data"]["modality"] = _mk
                    st.rerun()
        _country = st.selectbox("Country *", _country_list,
                                 index=_country_list.index(_data.get("country", "Germany"))
                                 if _data.get("country", "Germany") in _country_list else 0,
                                 key="fs_country")
        _s1c1, _s1c2 = st.columns([2, 1])
        with _s1c1:
            if st.button("Next →", type="primary", use_container_width=True, key="fs_next1"):
                if not _name.strip():
                    st.error("Please enter a farm name.")
                elif not _data.get("modality"):
                    st.error("Please select a modality.")
                else:
                    st.session_state["farm_setup_data"].update({
                        "name": _name.strip(), "country": _country,
                    })
                    st.session_state["farm_setup_step"] = 2
                    st.rerun()
        with _s1c2:
            if st.button("Cancel", use_container_width=True, key="fs_cancel1"):
                st.session_state["farm_setup_mode"] = False
                st.session_state["farm_setup_step"] = 1
                st.session_state["farm_setup_data"] = {}
                st.rerun()

    elif _step == 2:
        st.markdown("### Physical Parameters")
        _mod = _data.get("modality", "vertical_farm")
        if _mod == "vertical_farm":
            _fp   = st.number_input("Footprint (m²) *", min_value=100, max_value=100000,
                                     value=int(_data.get("footprint", 1000)), step=100, key="fs_footprint")
            _lv   = st.number_input("Levels *", min_value=1, max_value=20,
                                     value=int(_data.get("levels", 5)), step=1, key="fs_levels")
            _lt   = st.selectbox("Lights tier *",
                                  ["Basic", "Top-Tier"],
                                  index=["Basic","Top-Tier"].index(_data.get("lights_tier","Basic")),
                                  key="fs_lights_tier")
            _hv   = st.selectbox("HVAC *", ["Standard", "Advanced"],
                                  index=["Standard","Advanced"].index(_data.get("hvac","Standard")),
                                  key="fs_hvac")
            _au   = st.selectbox("Automation *", ["None", "Low", "Medium", "High"],
                                  index=["None","Low","Medium","High"].index(_data.get("automation","Medium")),
                                  key="fs_automation")
            _params = {"footprint": _fp, "levels": _lv, "lights_tier": _lt,
                       "hvac": _hv, "automation": _au}
        elif _mod in ("greenhouse", "polytunnel"):
            _fp   = st.number_input("Footprint (m²) *", min_value=500, max_value=500000,
                                     value=int(_data.get("footprint", 5000)), step=500, key="fs_footprint")
            _au   = st.selectbox("Automation *", ["None", "Low", "Medium", "High"],
                                  index=["None","Low","Medium","High"].index(_data.get("automation","Medium")),
                                  key="fs_automation")
            _params = {"footprint": _fp, "automation": _au,
                       "crop_source": "Polytunnel" if _mod == "polytunnel" else "Greenhouse"}
        else:  # aquaponics
            _fp   = st.number_input("Plant footprint (m²) *", min_value=100, max_value=50000,
                                     value=int(_data.get("footprint", 1000)), step=100, key="fs_footprint")
            _tv   = st.number_input("Fish tank volume (m³) *", min_value=5, max_value=10000,
                                     value=int(_data.get("tank_volume_m3", 50)), step=5, key="fs_tank_vol")
            _au   = st.selectbox("Automation *", ["None", "Low", "Medium", "High"],
                                  index=["None","Low","Medium","High"].index(_data.get("automation","Medium")),
                                  key="fs_automation")
            _params = {"footprint": _fp, "automation": _au, "tank_volume_m3": _tv,
                       "crop_source": "Greenhouse"}

        _s2c1, _s2c2, _s2c3 = st.columns([1, 1, 2])
        with _s2c1:
            if st.button("← Back", use_container_width=True, key="fs_back2"):
                st.session_state["farm_setup_step"] = 1
                st.rerun()
        with _s2c2:
            if st.button("Next →", type="primary", use_container_width=True, key="fs_next2"):
                st.session_state["farm_setup_data"].update(_params)
                st.session_state["farm_setup_step"] = 3
                st.rerun()

    elif _step == 3:
        st.markdown("### Crop Selection")
        _mod = _data.get("modality", "vertical_farm")

        # ── Determine correct crop dict for this modality ─────────────────────
        if _mod == "vertical_farm":
            _crop_source = "vertical_farm"
            _crop_dict   = CROPS
        elif _mod == "polytunnel":
            _crop_source = "Polytunnel"
            _crop_dict   = POLYTUNNEL_CROPS
        elif _mod in ("aquaponics_decoupled", "aquaponics_coupled"):
            # Aquaponics plant zone can be greenhouse OR polytunnel — let user choose
            _aq_plant_src = st.radio(
                "Plant zone type",
                options=["Greenhouse", "Polytunnel"],
                index=0 if _data.get("crop_source", "Greenhouse") != "Polytunnel" else 1,
                horizontal=True,
                key="fs_aq_plant_src",
            )
            _crop_source = _aq_plant_src
            _crop_dict   = POLYTUNNEL_CROPS if _aq_plant_src == "Polytunnel" else GREENHOUSE_CROPS
        else:
            # greenhouse
            _crop_source = "Greenhouse"
            _crop_dict   = GREENHOUSE_CROPS

        _crop_list = sorted(_crop_dict.keys())
        _default_crop = _data.get("crop", _crop_list[0])
        if _default_crop not in _crop_list:
            _default_crop = _crop_list[0]

        _multi = st.toggle("Multi-crop farm", value=_data.get("multi_crop", False), key="fs_multi")
        if not _multi:
            _crop = st.selectbox("Primary crop *", _crop_list,
                                  index=_crop_list.index(_default_crop), key="fs_crop_single")
            _crop_mix = [{"crop": _crop, "pct": 100}]
        else:
            st.caption("Allocate 100% across crops. Use the + button to add crops.")
            _saved_mix = _data.get("crop_mix", [{"crop": _default_crop, "pct": 100}])
            # Migration: rename Sweet Pepper inside crop mix
            for _m_row in _saved_mix:
                if _m_row.get("crop") == "Sweet Pepper":
                    if _crop_source == "Polytunnel":
                        _m_row["crop"] = "Sweet Pepper (Polytunnel)"
                    else:
                        _m_row["crop"] = "Sweet Pepper (GH Substrate)"

            _n_crops   = st.number_input("Number of crops", min_value=2, max_value=6,
                                          value=max(2, len(_saved_mix)), step=1, key="fs_n_crops")
            _crop_mix  = []
            _total     = 0
            for _ci in range(int(_n_crops)):
                _cc1, _cc2 = st.columns([3, 1])
                _ci_default = _saved_mix[_ci]["crop"] if _ci < len(_saved_mix) else _crop_list[0]
                _ci_pct     = _saved_mix[_ci]["pct"] if _ci < len(_saved_mix) else round(100 / int(_n_crops))
                with _cc1:
                    _ci_crop = st.selectbox(f"Crop {_ci+1}", _crop_list,
                                             index=_crop_list.index(_ci_default)
                                             if _ci_default in _crop_list else 0,
                                             key=f"fs_crop_{_ci}")
                with _cc2:
                    _ci_pct_val = st.number_input(f"%", min_value=1, max_value=100,
                                                   value=_ci_pct, key=f"fs_pct_{_ci}")
                _crop_mix.append({"crop": _ci_crop, "pct": _ci_pct_val})
                _total += _ci_pct_val
            if _total != 100:
                st.warning(f"Allocation sums to {_total}% — must be exactly 100%.")

        # ── Aquaponics: fish species selector ─────────────────────────────────
        _selected_fish_species = _data.get("fish_species", "Tilapia (Nile)")
        if _mod in ("aquaponics_decoupled", "aquaponics_coupled"):
            st.divider()
            st.markdown("**Fish Species**")
            _fish_list = list(FISH_SPECIES.keys())
            if _selected_fish_species not in _fish_list:
                _selected_fish_species = _fish_list[0]
            _selected_fish_species = st.selectbox(
                "Primary fish species",
                _fish_list,
                index=_fish_list.index(_selected_fish_species),
                key="fs_fish_species",
            )
            if _selected_fish_species == "Atlantic Salmon" and _mod == "aquaponics_coupled":
                st.error("⚠️ Salmon is incompatible with coupled aquaponics (cold water ≤14°C conflicts with shared nutrient loop).")

        _s3c1, _s3c2, _s3c3 = st.columns([1, 1, 2])
        with _s3c1:
            if st.button("← Back", use_container_width=True, key="fs_back3"):
                # Clear stale crop widget keys so they don't corrupt the new modality's crop list
                for _si in range(6):
                    st.session_state.pop(f"fs_crop_{_si}", None)
                    st.session_state.pop(f"fs_pct_{_si}", None)
                st.session_state.pop("fs_crop_single", None)
                st.session_state.pop("fs_multi", None)
                st.session_state.pop("fs_n_crops", None)
                st.session_state.pop("fs_aq_plant_src", None)
                st.session_state.pop("fs_fish_species", None)
                # Clear saved crop mix from data so it doesn't pre-populate with wrong modality crops
                st.session_state["farm_setup_data"].pop("crop_mix", None)
                st.session_state["farm_setup_data"].pop("crop_mix_json", None)
                st.session_state["farm_setup_data"].pop("crop", None)
                st.session_state["farm_setup_step"] = 2
                st.rerun()
        with _s3c2:
            _mix_ok = (not _multi) or (sum(r["pct"] for r in _crop_mix) == 100)
            _salmon_coupled_block = (_selected_fish_species == "Atlantic Salmon" and _mod == "aquaponics_coupled")
            if st.button("Next →", type="primary", use_container_width=True,
                          key="fs_next3", disabled=(not _mix_ok or _salmon_coupled_block)):
                st.session_state["farm_setup_data"].update({
                    "crop":             _crop_mix[0]["crop"],
                    "multi_crop":       _multi,
                    "crop_mix_json":    json.dumps(_crop_mix),
                    "crop_source":      _crop_source,
                    "fish_species":     _selected_fish_species if _mod.startswith("aquaponics") else None,
                })
                st.session_state["farm_setup_step"] = 4
                st.rerun()


    elif _step == 4:
        st.markdown("### Financial Structure")
        _dep  = st.number_input("Depreciation years *", min_value=3, max_value=30,
                                  value=int(_data.get("depreciation_years", 10)), key="fs_dep")
        _tax  = st.number_input("Tax rate (%)", min_value=0.0, max_value=60.0,
                                  value=float(_data.get("tax_rate", 25.0)), step=0.5, key="fs_tax")
        _ltv  = st.number_input("LTV (%)", min_value=0.0, max_value=90.0,
                                  value=float(_data.get("ltv", 60.0)), step=5.0, key="fs_ltv")
        _ir   = st.number_input("Interest rate (%)", min_value=0.0, max_value=20.0,
                                  value=float(_data.get("interest_rate", 5.5)), step=0.25, key="fs_ir")
        _lt   = st.number_input("Loan term (years)", min_value=1, max_value=30,
                                  value=int(_data.get("loan_term_years", 10)), key="fs_lt")
        _ps   = st.selectbox("Price scenario", ["low", "base", "high"],
                              index=["low","base","high"].index(_data.get("price_scenario","base")),
                              key="fs_ps")
        _rent = st.number_input("Monthly rent ($/mo) — 0 if owned",
                                 min_value=0.0, value=float(_data.get("rent_monthly", 0.0)),
                                 step=100.0, key="fs_rent")

        _s4c1, _s4c2, _s4c3 = st.columns([1, 1, 2])
        with _s4c1:
            if st.button("← Back", use_container_width=True, key="fs_back4"):
                st.session_state["farm_setup_step"] = 3
                st.rerun()
        with _s4c2:
            if st.button("💾 Save Farm", type="primary", use_container_width=True, key="fs_save"):
                _fin = {
                    "depreciation_years": _dep, "tax_rate": _tax,
                    "ltv": _ltv, "interest_rate": _ir,
                    "loan_term_years": _lt, "price_scenario": _ps,
                    "rent_monthly": _rent,
                    # shared defaults
                    "automation": _data.get("automation","Medium"),
                    "packaging_cost": 0.15, "loss_rate": 5.0,
                    "net_grow_factor": 85.0, "walkways_factor": 15.0,
                    "water_price": 2.0, "real_estate_capex": 0.0,
                    "price_override": 0.0, "harvest_mode": "Single",
                    "discount_rate": 8.0,
                    "levels": _data.get("levels", 5),
                    "lights_tier": _data.get("lights_tier","Basic"),
                    "hvac": _data.get("hvac","Standard"),
                }
                _final = {**_data, **_fin}
                _final["modality"]       = _data.get("modality","vertical_farm")
                _final["agriculture_type"] = _final["modality"]
                _final["metadata"]       = json.dumps({
                    "tank_volume_m3": _data.get("tank_volume_m3"),
                    "crop_source":    _data.get("crop_source"),
                }) if _final["modality"].startswith("aquaponics") else {}
                
                # Remove auxiliary keys not present in the database schema
                for _k in ["multi_crop", "crop_mix", "tank_volume_m3", "fish_species_temp"]:
                    _final.pop(_k, None)
                # fish_species is a valid DB column for aquaponics farms — keep it if present
                if not _final.get("modality", "").startswith("aquaponics"):
                    _final.pop("fish_species", None)

                _final["owner_id"] = current_user()

                try:
                    _resp = supabase.table("farms").insert(_final).execute()
                    _new_farm = _resp.data[0] if _resp.data else _final
                    load_farm(_new_farm)
                    st.session_state["farm_setup_mode"] = False
                    st.session_state["farm_setup_step"] = 1
                    st.session_state["farm_setup_data"] = {}
                    st.success(f"✅ Farm **{_final['name']}** created.")
                    st.switch_page("pages/1_ROI_Calculator.py")
                except Exception as _e:
                    st.error(f"Could not save farm: {_e}")

# ──────────────────────────────────────────────────────────────────────────────
# Onboarding state — no farms at all
# ──────────────────────────────────────────────────────────────────────────────
if not _farms:
    if st.session_state.get("farm_setup_mode"):
        _render_farm_setup()
    else:
        st.markdown(
            """
            <div class="pg-head">
              <h1>Set up your first farm</h1>
              <p>The portal models CEA feasibility, tracks operations, and maps circular-economy infrastructure. Begin by configuring a farm profile.</p>
            </div>
            <div class="onboard">
              <div class="glyph">🌱</div>
              <h2>No farms on record yet</h2>
              <p>Configure a farm — modality, location, footprint, target crop — and the rest of the portal will calibrate around it. You can always add more later.</p>
            </div>
            """,
            unsafe_allow_html=True,
        )
        st.write("")
        _o1, _o2, _o3 = st.columns([3, 2, 5])
        with _o1:
            if st.button("🌱 Create your first farm", type="primary",
                          use_container_width=True, key="onboard_create"):
                st.session_state["farm_setup_mode"] = True
                st.session_state["farm_setup_step"] = 1
                st.session_state["farm_setup_data"] = {}
                st.rerun()
    st.stop()

# ──────────────────────────────────────────────────────────────────────────────
# Page heading
# ──────────────────────────────────────────────────────────────────────────────
# Show setup form if triggered from workspace
if st.session_state.get("farm_setup_mode"):
    _render_farm_setup()
    st.stop()

_ph1, _ph2 = st.columns([6, 1])
with _ph1:
    st.markdown(
        """
        <div class="pg-head">
          <h1>Workspace</h1>
          <p>Pick a farm on the left to see its activity and continue your work.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )
with _ph2:
    if st.button("＋ New Farm", use_container_width=True, key="new_farm_btn"):
        st.session_state["farm_setup_mode"] = True
        st.session_state["farm_setup_step"] = 1
        st.session_state["farm_setup_data"] = {}
        st.rerun()

# ──────────────────────────────────────────────────────────────────────────────
# Two-column workspace
# ──────────────────────────────────────────────────────────────────────────────
_left, _right = st.columns([35, 65], gap="large")

# ── LEFT: Finder ──────────────────────────────────────────────────────────────
with _left:
    st.markdown(
        f"""
        <div class="finder-head">
          <span class="h">Farm Roster</span>
          <span class="count">{len(_farms):02d} on record</span>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # Search
    _q = st.text_input(
        "search",
        key="_farm_search",
        placeholder="Search by name, country, crop…",
        label_visibility="collapsed",
    )
    _q_norm = (_q or "").strip().lower()

    def _matches(f):
        if not _q_norm:
            return True
        hay = " ".join(str(f.get(k) or "") for k in ("name", "country", "crop", "modality")).lower()
        return _q_norm in hay

    _visible = [f for f in _farms if _matches(f)]

    if not _visible:
        st.markdown(
            '<div class="finder-empty">No farms match that search.</div>',
            unsafe_allow_html=True,
        )
    else:
        # Single clickable list: each row IS a Streamlit button, styled to look
        # like a rich row (monogram · name · country · footprint).
        st.markdown('<div class="finder-buttons">', unsafe_allow_html=True)
        for _f in _visible:
            _is_sel = (st.session_state["_selected_farm_id"] == _f["id"])
            _mk = _f.get("modality", "") or ""
            _mono = _MOD_MONOGRAM.get(_mk, "—")
            _country = _f.get("country") or ""
            _foot = f"{int(_f.get('footprint') or 0):,} m²" if _f.get("footprint") else "—"
            # Use a separator the CSS will split into columns via flex
            _sep = "  ·  "
            _country_part = f"{_sep}{_country}" if _country else ""
            _label = f"{_mono}\u2003{_f['name']}{_country_part}\u2003{_foot}"
            _btn_class = "row-btn selected-row" if _is_sel else "row-btn"
            st.markdown(f'<div class="{_btn_class}">', unsafe_allow_html=True)
            if st.button(_label, key=f"sel_{_f['id']}", use_container_width=True):
                st.session_state["_selected_farm_id"] = _f["id"]
                st.rerun()
            st.markdown('</div>', unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)

    # Roster summary — uses freed vertical space
    if _farms:
        _total_foot = sum(int(f.get("footprint") or 0) for f in _farms)
        _mod_counts = {}
        for f in _farms:
            k = f.get("modality") or "—"
            _mod_counts[k] = _mod_counts.get(k, 0) + 1
        _most_recent = None
        for f in _farms:
            d = f.get("model_updated_at") or f.get("created_at")
            if d and (_most_recent is None or str(d) > str(_most_recent)):
                _most_recent = d
        _recent_days = _days_since(_most_recent)
        _recent_str = f"{_recent_days}d ago" if _recent_days is not None else "—"

        _mod_chips = "".join(
            f'<span class="chip"><b>{_MOD_MONOGRAM.get(k,"—")}</b> {v}</span>'
            for k, v in sorted(_mod_counts.items(), key=lambda x: -x[1])
        )
        st.markdown(
            f"""
            <div class="roster-summary">
              <div class="rs-h">Roster summary</div>
              <div class="rs-stats">
                <div class="rs-stat"><div class="lbl">Total footprint</div>
                  <div class="val">{_total_foot:,} m²</div></div>
                <div class="rs-stat"><div class="lbl">Last activity</div>
                  <div class="val">{_recent_str}</div></div>
              </div>
              <div class="rs-chips">{_mod_chips}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

# ── RIGHT: Context panel ──────────────────────────────────────────────────────
with _right:
    _selected = next(
        (f for f in _farms if f["id"] == st.session_state.get("_selected_farm_id")),
        None,
    )

    if not _selected:
        # No selection — show "what you can do here" overview
        st.markdown(
            """
            <div class="panel panel-empty">
              <div class="h2">No farm selected</div>
              <div class="sub">Pick a farm from the roster to see its recent activity and continue work. Here's what the portal does:</div>
              <div class="what-row">
                <div class="num">01</div>
                <div class="body">
                  <strong>Model feasibility</strong>
                  <span>Project CAPEX, EBITDA, energy costs and payback across four CEA modalities.</span>
                </div>
              </div>
              <div class="what-row">
                <div class="num">02</div>
                <div class="body">
                  <strong>Track operations</strong>
                  <span>Log harvests and expenses; compare actuals against your projections over time.</span>
                </div>
              </div>
              <div class="what-row">
                <div class="num">03</div>
                <div class="body">
                  <strong>Map your context</strong>
                  <span>Find waste-stream sources and logistics infrastructure within reach of your site.</span>
                </div>
              </div>
              <div class="what-row">
                <div class="num">04</div>
                <div class="body">
                  <strong>Read the methodology</strong>
                  <span>Every assumption, source, and calibration note — in plain view.</span>
                </div>
              </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    else:
        # Selected farm — header
        _mk = _selected.get("modality", "") or ""
        _mod_disp = _MOD_LABEL.get(_mk, _mk.replace("_", " ").title() or "—")
        _country = _selected.get("country") or "—"
        _foot = f"{int(_selected.get('footprint') or 0):,} m²" if _selected.get("footprint") else "—"
        _crop = _selected.get("crop") or "—"

        # Activity timeline values
        _last_modeled = _fmt_date(_selected.get("model_updated_at"))
        _modeled_days = _days_since(_selected.get("model_updated_at"))

        _last_harvest = None
        _harvest_count = 0
        _last_expense = None
        _expense_count = 0
        try:
            # harvest_logs: date column is "date", status filters to closed cycles
            _hr = supabase.table("harvest_logs").select("date").eq(
                "farm_id", _selected["id"]
            ).eq("status", "harvested").order("date", desc=True).limit(1).execute()
            if _hr.data:
                _last_harvest = _fmt_date(_hr.data[0]["date"])
            _hc = supabase.table("harvest_logs").select("id", count="exact").eq(
                "farm_id", _selected["id"]
            ).eq("status", "harvested").execute()
            _harvest_count = _hc.count or 0
        except Exception:
            _last_harvest = None
            _harvest_count = 0

        try:
            _er = supabase.table("expense_logs").select("date").eq(
                "farm_id", _selected["id"]
            ).order("date", desc=True).limit(1).execute()
            if _er.data:
                _last_expense = _fmt_date(_er.data[0]["date"])
            _ec = supabase.table("expense_logs").select("id", count="exact").eq(
                "farm_id", _selected["id"]
            ).execute()
            _expense_count = _ec.count or 0
        except Exception:
            _last_expense = None
            _expense_count = 0

        _harvest_days = _days_since(_last_harvest)
        _expense_days = _days_since(_last_expense)

        # Format activity values
        if _last_modeled:
            _modeled_val = f"{_modeled_days}d ago" if _modeled_days is not None else _last_modeled
            _modeled_sub = _last_modeled
            _modeled_muted = ""
        else:
            _modeled_val = "Never modelled"
            _modeled_sub = "Open the Calculator to run"
            _modeled_muted = "muted"

        if _last_harvest:
            _harvest_val = f"{_harvest_days}d ago" if _harvest_days is not None else _last_harvest
            _harvest_sub = f"{_harvest_count} harvest{'s' if _harvest_count != 1 else ''} logged"
            _harvest_muted = ""
        else:
            _harvest_val = "No harvests logged yet"
            _harvest_sub = "Start in Harvest Tracker →"
            _harvest_muted = "muted"

        if _last_expense:
            _expense_val = f"{_expense_days}d ago" if _expense_days is not None else _last_expense
            _expense_sub = f"{_expense_count} expense entr{'ies' if _expense_count != 1 else 'y'} logged"
            _expense_muted = ""
        else:
            _expense_val = "No expenses logged yet"
            _expense_sub = "Log in Harvest Tracker →"
            _expense_muted = "muted"

        _created_date = _fmt_date(_selected.get("created_at"))
        _created_days = _days_since(_selected.get("created_at"))
        if _created_date:
            _created_val = _created_date
            _created_sub = f"{_created_days}d on record" if _created_days is not None else ""
            _created_muted = ""
        else:
            _created_val = "—"
            _created_sub = ""
            _created_muted = "muted"

        st.markdown(
            f"""
            <div class="panel">
              <div class="panel-head">
                <div>
                  <h2 class="farm-name">{_selected['name']}</h2>
                  <div class="farm-meta">
                    <span class="mod">{_mod_disp}</span>
                    <span class="dot"></span>{_country}
                    <span class="dot"></span>{_foot}
                    <span class="dot"></span>{_crop}
                  </div>
                </div>
              </div>

              <div class="activity">
                <div class="h">Recent Activity</div>
                <div class="timeline">
                  <div class="stat">
                    <div class="lbl">Last modelled</div>
                    <div class="val {_modeled_muted}">{_modeled_val}</div>
                    <div class="sub">{_modeled_sub}</div>
                  </div>
                  <div class="stat">
                    <div class="lbl">Last harvest</div>
                    <div class="val {_harvest_muted}">{_harvest_val}</div>
                    <div class="sub">{_harvest_sub}</div>
                  </div>
                  <div class="stat">
                    <div class="lbl">Last expense</div>
                    <div class="val {_expense_muted}">{_expense_val}</div>
                    <div class="sub">{_expense_sub}</div>
                  </div>
                  <div class="stat">
                    <div class="lbl">Created</div>
                    <div class="val {_created_muted}">{_created_val}</div>
                    <div class="sub">{_created_sub}</div>
                  </div>
                </div>
              </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        # Destinations — framed as actions on this farm
        st.markdown(
            """
            <div class="destinations" style="margin-top:18px;">
              <div class="h">Continue with this farm</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        # Helper for activation pattern
        def _activate_and_switch(target_page: str, with_modality: bool):
            try:
                _full = supabase.table("farms").select("*").eq("id", _selected["id"]).single().execute()
                _fd = _full.data
            except Exception:
                _fd = _selected
            st.session_state["active_farm"]        = _fd
            st.session_state["_pending_farm_load"] = _fd
            if _fd.get("lat") and _fd.get("lon"):
                st.session_state["shared_lat"] = _fd["lat"]
                st.session_state["shared_lng"] = _fd["lon"]
            if with_modality:
                st.session_state["_pending_modality"] = _MOD_SWITCH.get(
                    _fd.get("modality", "vertical_farm"), "🏭 Indoor Vertical Farm"
                )
            st.switch_page(target_page)

        # Destination 1 — ROI
        if _last_modeled:
            _roi_lead = "Re-run the ROI model"
            _roi_desc = f"Refresh CAPEX, EBITDA and payback projections — last modelled {_modeled_days}d ago."
        else:
            _roi_lead = "Run the ROI model"
            _roi_desc = "Project CAPEX, EBITDA, energy costs and payback for this configuration."
        st.markdown(
            f'<div class="dest-card"><div class="lead">{_roi_lead}</div>'
            f'<div class="desc">{_roi_desc}</div></div>',
            unsafe_allow_html=True,
        )
        _r1, _r2 = st.columns([1, 3])
        with _r1:
            if st.button("Open Calculator →", key="dest_roi", type="primary", use_container_width=True):
                _activate_and_switch("pages/1_ROI_Calculator.py", with_modality=True)

        # Destination 2 — Harvest Tracker
        if _last_harvest:
            _h_lead = "Log a new harvest"
            _h_desc = f"Last entry was {_harvest_days}d ago. Continue tracking actuals against projections."
        else:
            _h_lead = "Begin tracking harvests"
            _h_desc = "Record yields and expenses as the farm ramps up — actuals vs projections over time."
        st.markdown(
            f'<div class="dest-card"><div class="lead">{_h_lead}</div>'
            f'<div class="desc">{_h_desc}</div></div>',
            unsafe_allow_html=True,
        )
        _h1, _h2 = st.columns([1, 3])
        with _h1:
            if st.button("Open Tracker →", key="dest_harvest", use_container_width=True):
                _activate_and_switch("pages/2_Harvest_Tracker.py", with_modality=False)

        # Destination 3 — Map
        _has_geo = bool(_selected.get("lat") and _selected.get("lon"))
        if _has_geo:
            _m_lead = "Survey the area"
            _m_desc = "Locate waste-stream sources and logistics infrastructure within reach of this site."
        else:
            _m_lead = "Locate this farm on the map"
            _m_desc = "Set coordinates to unlock circular-economy mapping for waste streams and logistics."
        st.markdown(
            f'<div class="dest-card"><div class="lead">{_m_lead}</div>'
            f'<div class="desc">{_m_desc}</div></div>',
            unsafe_allow_html=True,
        )
        _m1, _m2 = st.columns([1, 3])
        with _m1:
            if st.button("Open Map →", key="dest_map", use_container_width=True):
                _activate_and_switch("pages/3_Farm_Intelligence_Map.py", with_modality=False)

        # Destination 4 — Space Planner
        st.markdown(
            '<div class="dest-card"><div class="lead">Design the farm layout</div>'
            '<div class="desc">Place buildings, racks, paths and tanks on a 2D canvas. '
            'Visualise sun shadows, check layout-to-model consistency, and save to the cloud.</div></div>',
            unsafe_allow_html=True,
        )
        _sp1, _sp2 = st.columns([1, 3])
        with _sp1:
            if st.button("Open Planner →", key="dest_space", use_container_width=True):
                _activate_and_switch("pages/5_Space_Planner.py", with_modality=False)

        # Footer actions: Assumptions + Delete
        st.markdown('<div style="height:18px;border-top:1px solid var(--rule);margin-top:24px;"></div>', unsafe_allow_html=True)
        _f1, _f2, _f3 = st.columns([2, 4, 2])
        with _f1:
            st.page_link("pages/14_Assumptions.py", label="View assumptions →", use_container_width=True)
        with _f3:
            st.markdown('<div class="danger-btn">', unsafe_allow_html=True)
            if st.button("Delete this farm", key=f"del_{_selected['id']}", use_container_width=True):
                try:
                    supabase.table("farms").delete().eq("id", _selected["id"]).execute()
                    if _active and _active.get("id") == _selected["id"]:
                        st.session_state.pop("active_farm", None)
                    st.session_state["_selected_farm_id"] = None
                    st.rerun()
                except Exception as ex:
                    st.error(f"Delete failed: {ex}")
            st.markdown('</div>', unsafe_allow_html=True)
