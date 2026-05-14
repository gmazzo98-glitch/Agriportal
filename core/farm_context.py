"""
core/farm_context.py
Agricultural Intelligence Portal — shared farm context module.

Provides a single source of truth for the active farm across all pages.
Every page imports this module and calls the functions it needs.

Public API
----------
load_farm(farm_dict)            — populate session state from a farm record
get_active_farm()               — return active farm dict or None
save_farm(farm_dict, supabase)  — write farm to Supabase + update session state
clear_farm()                    — clear active farm from session state
require_farm(page_name)         — guard: stop page if no farm loaded
render_farm_context_sidebar()   — persistent sidebar block (call at top of every page sidebar)
"""

from __future__ import annotations
import json
import streamlit as st

# ── Modality helpers ──────────────────────────────────────────────────────────

MODALITY_LABELS: dict[str, str] = {
    "vertical_farm":        "🏭 Vertical Farm",
    "greenhouse":           "🌿 Greenhouse",
    "polytunnel":           "🌿 Polytunnel",
    "aquaponics_decoupled": "🐟 Decoupled Aquaponics",
    "aquaponics_coupled":   "♻️ Coupled Aquaponics",
}

MODALITY_RADIO: dict[str, str] = {
    "vertical_farm":        "🏭 Indoor Vertical Farm",
    "greenhouse":           "🌿 High-Tech Greenhouse",
    "polytunnel":           "🌿 High-Tech Greenhouse",
    "aquaponics_decoupled": "🐟 Decoupled Aquaponics",
    "aquaponics_coupled":   "♻️ Coupled Aquaponics",
}

# Colours for modality badges (background, text)
MODALITY_COLOURS: dict[str, tuple[str, str]] = {
    "vertical_farm":        ("#3b3b52", "#ffffff"),
    "greenhouse":           ("#2f5d3a", "#ffffff"),
    "polytunnel":           ("#2f5d3a", "#ffffff"),
    "aquaponics_decoupled": ("#2c5a78", "#ffffff"),
    "aquaponics_coupled":   ("#1f4d39", "#ffffff"),
}

# Widget key prefixes for each modality — used when populating sidebar widgets
_VF_WIDGET_KEYS: list[str] = [
    "roi_country", "roi_crop", "roi_footprint", "roi_levels",
    "roi_lights_tier", "roi_hvac", "roi_automation", "roi_price_scenario",
    "roi_harvest_mode", "roi_price_override", "roi_packaging_cost",
    "roi_loss_rate", "roi_net_grow_factor", "roi_walkways_factor",
    "roi_water_price", "roi_rent_monthly", "roi_real_estate_capex",
    "roi_depreciation_years", "roi_tax_rate", "roi_ltv",
    "roi_interest_rate", "roi_loan_term_years", "roi_multi_crop",
]

_GH_WIDGET_KEYS: list[str] = [
    "gh_country", "gh_crop", "gh_footprint", "gh_crop_source",
    "gh_automation", "gh_price_scenario", "gh_harvest_mode",
    "gh_price_override", "gh_packaging_cost", "gh_loss_rate",
    "gh_net_grow_factor", "gh_walkways_factor", "gh_water_price",
    "gh_rent_monthly", "gh_real_estate_capex", "gh_depreciation_years",
    "gh_tax_rate", "gh_ltv", "gh_interest_rate", "gh_loan_term_years",
    "gh_discount_rate", "gh_multi_crop",
]

_AQ_WIDGET_KEYS: list[str] = [
    "aq_country", "aq_plant_crop", "aq_plant_crop_source",
    "aq_plant_footprint", "aq_automation", "aq_price_scenario",
    "aq_harvest_mode", "aq_packaging_cost", "aq_loss_rate",
    "aq_net_grow_factor", "aq_walkways_factor", "aq_water_price",
    "aq_rent_monthly", "aq_real_estate_capex", "aq_depreciation_years",
    "aq_tax_rate", "aq_ltv", "aq_interest_rate", "aq_loan_term_years",
    "aq_discount_rate", "aq_multi_crop",
]


# ── Core functions ────────────────────────────────────────────────────────────

def get_active_farm() -> dict | None:
    """Return the active farm dict from session state, or None."""
    return st.session_state.get("active_farm")


def clear_farm() -> None:
    """Clear the active farm from session state."""
    st.session_state.pop("active_farm", None)
    st.session_state.pop("active_farm_result", None)


def load_farm(farm_dict: dict) -> None:
    """
    Populate session state from a farm record fetched from Supabase.
    Sets active_farm and _pending_farm_load (consumed by ROI Calculator
    at the top of its render cycle before any widgets instantiate).
    Also sets _pending_modality so the modality radio switches correctly.
    """
    if not farm_dict:
        return

    st.session_state["active_farm"]        = farm_dict
    st.session_state["_pending_farm_load"] = farm_dict

    # Coordinates
    if farm_dict.get("lat") and farm_dict.get("lon"):
        st.session_state["shared_lat"] = farm_dict["lat"]
        st.session_state["shared_lng"] = farm_dict["lon"]
        st.session_state["fim_lat"]    = farm_dict["lat"]
        st.session_state["fim_lng"]    = farm_dict["lon"]

    # Modality radio switch
    modality = farm_dict.get("modality", "vertical_farm")
    st.session_state["_pending_modality"] = MODALITY_RADIO.get(
        modality, "🏭 Indoor Vertical Farm"
    )


def save_farm(farm_dict: dict, supabase) -> bool:
    """
    Write updated farm parameters to Supabase and update session state.
    Returns True on success, False on failure.
    farm_dict must contain 'id'.
    """
    farm_id = farm_dict.get("id")
    if not farm_id:
        return False
    try:
        payload = {k: v for k, v in farm_dict.items() if k != "id"}
        supabase.table("farms").update(payload).eq("id", farm_id).execute()
        st.session_state["active_farm"] = farm_dict
        return True
    except Exception as e:
        st.error(f"Could not save farm: {e}")
        return False


def require_farm(page_name: str = "this page") -> None:
    """
    Guard function. Call at the top of any page that requires an active farm.
    If no farm is loaded, renders a message and calls st.stop().
    """
    if st.session_state.get("active_farm"):
        return
    st.info(
        f"**No active farm selected.**\n\n"
        f"{page_name} requires an active farm profile. "
        f"Go to the Farm Manager to select or create one."
    )
    st.page_link("Home.py", label="🏠 Go to Farm Manager →")
    st.stop()


# ── Modality badge HTML ───────────────────────────────────────────────────────

def modality_badge_html(modality: str) -> str:
    """Return a styled HTML badge for the given modality string."""
    label  = MODALITY_LABELS.get(modality, modality.replace("_", " ").title())
    bg, fg = MODALITY_COLOURS.get(modality, ("#4a524a", "#ffffff"))
    return (
        f'<span style="display:inline-block;background:{bg};color:{fg};'
        f'font-size:11px;font-weight:700;letter-spacing:0.05em;'
        f'padding:2px 8px;border-radius:2px;white-space:nowrap;">'
        f'{label}</span>'
    )


# ── Persistent sidebar context block ─────────────────────────────────────────

def render_farm_context_sidebar(supabase=None) -> dict | None:
    """
    Render the persistent farm context block at the top of the sidebar.
    Shows active farm name, modality badge, location, and action buttons.
    Optionally accepts a supabase client for the farm load selectbox.
    Returns the active farm dict or None.

    Usage (at the top of any page's sidebar section):
        from core.farm_context import render_farm_context_sidebar
        active_farm = render_farm_context_sidebar(supabase=supabase)
    """
    active = st.session_state.get("active_farm")

    with st.sidebar:
        # ── Active farm display ───────────────────────────────────────────
        if active:
            modality = active.get("modality", "vertical_farm")
            bg, fg   = MODALITY_COLOURS.get(modality, ("#4a524a", "#ffffff"))
            label    = MODALITY_LABELS.get(modality, modality.replace("_", " ").title())
            country  = active.get("country", "")
            footprint = active.get("footprint") or active.get("plant_footprint") or 0

            st.markdown(
                f"""
                <div style="background:#2a2f2a;border:1px solid #3a4039;
                            border-radius:3px;padding:10px 12px;margin-bottom:6px;">
                  <div style="font-size:13px;font-weight:700;color:#ffffff;
                              margin-bottom:4px;white-space:nowrap;overflow:hidden;
                              text-overflow:ellipsis;">{active.get('name','')}</div>
                  <div style="display:flex;align-items:center;gap:6px;flex-wrap:wrap;">
                    <span style="background:{bg};color:{fg};font-size:10px;
                                 font-weight:700;padding:1px 6px;border-radius:2px;
                                 white-space:nowrap;">{label}</span>
                    <span style="color:#9ba39a;font-size:11px;">{country}</span>
                    <span style="color:#9ba39a;font-size:11px;">{int(footprint):,} m²</span>
                  </div>
                </div>
                """,
                unsafe_allow_html=True,
            )

            _c1, _c2 = st.columns(2)
            with _c1:
                if st.button("🏠 Farms", use_container_width=True,
                             key="fc_go_home", help="Return to Farm Manager"):
                    st.switch_page("Home.py")
            with _c2:
                if st.button("✖ Clear", use_container_width=True,
                             key="fc_clear_farm", help="Unload active farm"):
                    clear_farm()
                    st.rerun()

        else:
            st.markdown(
                '<div style="background:#2a2f2a;border:1px solid #3a4039;'
                'border-radius:3px;padding:10px 12px;margin-bottom:6px;'
                'color:#9ba39a;font-size:12px;">No farm loaded</div>',
                unsafe_allow_html=True,
            )
            if st.button("🏠 Select a Farm", use_container_width=True,
                         key="fc_go_home_empty"):
                st.switch_page("Home.py")

        st.divider()

    return active
