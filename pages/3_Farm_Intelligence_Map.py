"""
Farm Intelligence Map
=====================
Unified map page combining two intelligence layers:
  - Layer 1: Circular Economy / Waste Sources (industrial facilities with fertilizer potential)
  - Layer 2: Logistics Infrastructure (transport, ports, rail, cold storage)

Architecture: each layer is fully self-contained (its own data, query, classification).
Adding future layers (meteorological, aquaculture suitability, etc.) follows the same pattern.

Data: OpenStreetMap via Overpass API — free, no API key required.
Map: Folium / Leaflet.js — lighter and clickable.
"""

import streamlit as st
import pandas as pd
import requests
import math
import folium
from streamlit_folium import st_folium
import plotly.express as px
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from supabase import create_client, Client
from core._styles import inject_styles
from core.farm_context import render_farm_context_sidebar

# ═════════════════════════════════════════════════════════════════════════════ # Keep page_icon emoji, but remove from title
# SHARED UTILITIES
# ═════════════════════════════════════════════════════════════════════════════

@st.cache_resource
def get_supabase() -> Client:
    return create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    R = 6371
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi    = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def _ors_road_distances(src_lat: float, src_lon: float, targets: list[dict]) -> list[float | None]:
    """
    Queries OpenRouteService matrix API for real road distances.
    Requires ORS_API_KEY in st.secrets. Returns list of km values (None on failure).
    Free tier: 2,000 matrix requests/day, up to 50 destinations per call.
    Register at https://openrouteservice.org/dev/#/login to get a free key.
    """
    try:
        api_key = st.secrets.get("ORS_API_KEY", "")
    except Exception:
        api_key = ""
    if not api_key:
        return [None] * len(targets)

    locations = [[src_lon, src_lat]] + [[t["lon"], t["lat"]] for t in targets]
    payload = {
        "locations": locations,
        "sources":   [0],
        "metrics":   ["duration"],   # free tier only supports duration (seconds)
    }
    try:
        resp = requests.post(
            "https://api.openrouteservice.org/v2/matrix/driving-car",
            json=payload,
            headers={
                "Accept":        "application/json, application/geo+json",
                "Authorization": api_key,
                "Content-Type":  "application/json; charset=utf-8",
            },
            timeout=15,
        )
        resp.raise_for_status()
        data = resp.json()
        row = data["durations"][0]          # source=0 → one row, values in seconds
        # Convert seconds → km using 60 km/h average road speed (free tier has no distance metric)
        AVG_SPEED_KMH = 60.0
        st.session_state.pop("_ors_last_error", None)  # clear any previous error on success
        return [round(s / 3600 * AVG_SPEED_KMH, 2) if s is not None else None for s in row[1:]]
    except Exception as e:
        try:
            st.session_state["_ors_last_error"] = str(e)
        except Exception:
            pass
        return [None] * len(targets)


def add_osrm_distances(df: pd.DataFrame, src_lat: float, src_lon: float) -> pd.DataFrame:
    """
    Calculates straight-line (Haversine) distance for all rows, then upgrades
    high-priority points to real road distances via OpenRouteService if an
    ORS_API_KEY is present in st.secrets.
    Falls back silently to Haversine when the key is absent or the call fails.
    """
    if df.empty:
        return df

    # Haversine baseline for every row
    df["Distance (km)"] = df.apply(
        lambda row: round(haversine_km(src_lat, src_lon, row["lat"], row["lon"]), 2), axis=1
    )
    df["Routing"] = "Haversine (Direct)"
    df = df.sort_values("Distance (km)").reset_index(drop=True)

    # Select subset to upgrade with road distances
    if "Type" in df.columns:
        priority_infra = [
            "Airport", "Airport Terminal", "Commercial Port", "Harbour / Port",
            "Rail Freight Terminal", "Rail Station", "Motorway Junction", "Cold Storage",
        ]
        subset = df[df["Type"].isin(priority_infra)].head(40).copy()
    else:
        subset = df.head(20).copy()

    if subset.empty:
        return df

    targets = [{"lat": row.lat, "lon": row.lon} for _, row in subset.iterrows()]
    road_km = _ors_road_distances(src_lat, src_lon, targets)

    for i, idx in enumerate(subset.index):
        if road_km[i] is not None:
            df.at[idx, "Distance (km)"] = road_km[i]
            df.at[idx, "Routing"] = "ORS (Drive time)"

    df = df.sort_values("Distance (km)").reset_index(drop=True)
    return df


def get_default_location() -> tuple[float, float]:
    try:
        resp = requests.get("https://ipapi.co/json/", timeout=5)
        data = resp.json()
        return float(data["latitude"]), float(data["longitude"])
    except Exception:
        return 45.4642, 9.1900


def reverse_geocode_country(lat: float, lng: float) -> tuple[str | None, str | None]:
    try:
        resp = requests.get(
            "https://nominatim.openstreetmap.org/reverse",
            params={"lat": lat, "lon": lng, "format": "json"},
            headers={"User-Agent": "AgriculturalPortal/1.0"},
            timeout=5,
        )
        data    = resp.json()
        address = data.get("address", {})
        return address.get("country"), address.get("country_code", "").upper()
    except Exception:
        return None, None


def _autosave_fim_to_supabase(
    active_farm: dict,
    waste_df,
    logistics_df,
) -> None:
    """
    Automatically saves FIM results to farms.metadata in Supabase.
    Called after every successful search — no user action required.
    Silently swallows errors so a save failure never blocks the UI.
    """
    if not active_farm or not active_farm.get("id"):
        return
    if waste_df is None and logistics_df is None:
        return
    try:
        sb        = get_supabase()
        resp      = sb.table("farms").select("metadata").eq("id", active_farm["id"]).execute()
        _raw      = resp.data[0].get("metadata") if resp.data else None
        if isinstance(_raw, str):
            import json as _j
            try:    _raw = _j.loads(_raw)
            except: _raw = {}
        meta = _raw if isinstance(_raw, dict) else {}
        if waste_df is not None and not waste_df.empty:
            meta["fim_waste_data"]     = waste_df.to_dict(orient="records")
        if logistics_df is not None and not logistics_df.empty:
            meta["fim_logistics_data"] = logistics_df.to_dict(orient="records")
        sb.table("farms").update({"metadata": meta}).eq("id", active_farm["id"]).execute()
        # Keep local session state in sync
        if st.session_state.get("active_farm"):
            if not st.session_state["active_farm"].get("metadata"):
                st.session_state["active_farm"]["metadata"] = {}
            st.session_state["active_farm"]["metadata"].update(meta)
    except Exception:
        pass  # Never surface auto-save errors to the user


def run_overpass_query(query: str) -> list[dict]:
    """
    Queries Overpass API with fallback mirrors and smart retry logic.
    - timeout=60s per endpoint (below Streamlit Cloud 90s limit)
    - Retries on 429/503/502 (rate-limit/overload) only
    - Does NOT retry on 400 (bad query) or 404
    - Sends User-Agent to avoid mirror blocks
    """
    endpoints = [
        "https://overpass-api.de/api/interpreter",
        "https://overpass.kumi.systems/api/interpreter",
        "https://overpass.openstreetmap.fr/api/interpreter",
    ]
    headers = {"User-Agent": "AgriculturalIntelligencePortal/1.0 (contact@agriportal.io)"}
    last_error = "Unknown error"
    for endpoint in endpoints:
        try:
            resp = requests.post(
                endpoint,
                data={"data": query},
                headers=headers,
                timeout=60,
            )
            if resp.status_code in (429, 502, 503):
                # Rate-limited or overloaded — try next mirror
                last_error = f"HTTP {resp.status_code} from {endpoint}"
                continue
            if resp.status_code == 400:
                # Bad query syntax — no point retrying on other endpoints
                raise RuntimeError(f"Overpass query syntax error (HTTP 400): {resp.text[:200]}")
            resp.raise_for_status()
            return resp.json().get("elements", [])
        except requests.exceptions.Timeout:
            last_error = f"Timeout on {endpoint}"
            continue
        except requests.exceptions.ConnectionError:
            last_error = f"Connection error on {endpoint}"
            continue
        except RuntimeError:
            raise
        except Exception as e:
            last_error = str(e)
            continue
    raise RuntimeError(
        f"All Overpass API mirrors failed. Last error: {last_error}. "
        "Try reducing the search radius or try again in a few minutes."
    )


def find_triangulation_target(target_label: str, lat: float, lng: float, search_radius_km: int, df_w: pd.DataFrame, df_l: pd.DataFrame) -> dict | None:
    """Finds the nearest target by first checking local DFs, then querying Overpass if needed."""
    # 1. Check existing DataFrames first to save API calls
    if df_l is not None and not df_l.empty and target_label in df_l["Type"].values:
        subset = df_l[df_l["Type"] == target_label]
        nearest = subset.loc[subset["Distance (km)"].idxmin()]
        if nearest["Distance (km)"] <= search_radius_km:
            return {"lat": nearest["lat"], "lon": nearest["lon"], "name": nearest["Name"]}

    if df_w is not None and not df_w.empty and target_label in df_w["Potential Fertilizer Waste"].values:
        subset = df_w[df_w["Potential Fertilizer Waste"] == target_label]
        nearest = subset.loc[subset["Distance (km)"].idxmin()]
        if nearest["Distance (km)"] <= search_radius_km:
            return {"lat": nearest["lat"], "lon": nearest["lon"], "name": nearest["Company Name"]}

    # 2. If not found locally, build a targeted Overpass query
    search_radius_m = search_radius_km * 1000
    query_inner = ""

    # Check if target is an Infrastructure type
    for key, val, label, _, _ in INFRA_TYPES:
        if label == target_label:
            if val:
                query_inner += f'node["{key}"="{val}"](around:{search_radius_m},{lat},{lng});\n'
                query_inner += f'way["{key}"="{val}"](around:{search_radius_m},{lat},{lng});\n'
            else:
                query_inner += f'node["{key}"](around:{search_radius_m},{lat},{lng});\n'
                query_inner += f'way["{key}"](around:{search_radius_m},{lat},{lng});\n'

    # Check if target is a Waste type
    if not query_inner:
        for tags_key, (ind, waste) in TAG_WASTE_MAP.items():
            if waste == target_label:
                k, v = tags_key.split("=")
                query_inner += f'node["{k}"="{v}"](around:{search_radius_m},{lat},{lng});\n'
                query_inner += f'way["{k}"="{v}"](around:{search_radius_m},{lat},{lng});\n'

    if not query_inner:
        return None 

    query = f"[out:json][timeout:60];\n(\n  {query_inner});\nout center tags;"
    try:
        elements = run_overpass_query(query)
        if not elements:
            return None
        
        # Find the closest coordinate from the Overpass results
        best_dist = float('inf')
        best_match = None
        for el in elements:
            t_lat = el.get("center", {}).get("lat") or el.get("lat")
            t_lon = el.get("center", {}).get("lon") or el.get("lon")
            if not t_lat or not t_lon: continue
            
            dist = haversine_km(lat, lng, t_lat, t_lon)
            if dist < best_dist and dist <= search_radius_km:
                best_dist = dist
                tags = el.get("tags", {})
                name = tags.get("name", tags.get("operator", "Unnamed Facility"))
                best_match = {"lat": t_lat, "lon": t_lon, "name": name}
        return best_match
    except Exception as e:
        print(f"Triangulation query failed: {e}")
        return None


# ═════════════════════════════════════════════════════════════════════════════
# LAYER 1 — CIRCULAR ECONOMY / WASTE SOURCES
# ═════════════════════════════════════════════════════════════════════════════

TAG_WASTE_MAP = {
    "craft=brewery":                    ("Brewery / Distillery",          "Spent Grains (Organic Matter)"),
    "craft=winery":                     ("Brewery / Distillery",          "Spent Grains (Organic Matter)"),
    "craft=distillery":                 ("Brewery / Distillery",          "Spent Grains (Organic Matter)"),
    "craft=sawmill":                    ("Wood / Paper / Pulp",           "Wood Ash / Biochar (Potassium / pH amendment)"),
    "craft=carpenter":                  ("Wood / Paper / Pulp",           "Wood Ash / Biochar (Potassium / pH amendment)"),
    "craft=slaughterhouse":             ("Meat Processing",               "Blood Meal / Bone Meal (Nitrogen / Phosphorus)"),
    "craft=dairy":                      ("Dairy / Milk Processing",       "Whey / Sludge (Nitrogen / Phosphorus)"),
    "craft=cheese":                     ("Dairy / Milk Processing",       "Whey / Sludge (Nitrogen / Phosphorus)"),
    "craft=tannery":                    ("Textile Manufacturing",         "Lint / Cotton Sludge (Organic Carbon)"),
    "craft=textile":                    ("Textile Manufacturing",         "Lint / Cotton Sludge (Organic Carbon)"),
    "craft=bakery":                     ("Grain / Flour Milling",         "Bran / Flour Dust (Organic Matter)"),
    "craft=mill":                       ("Grain / Flour Milling",         "Bran / Flour Dust (Organic Matter)"),
    "industrial=brewery":               ("Brewery / Distillery",          "Spent Grains (Organic Matter)"),
    "industrial=distillery":            ("Brewery / Distillery",          "Spent Grains (Organic Matter)"),
    "industrial=dairy":                 ("Dairy / Milk Processing",       "Whey / Sludge (Nitrogen / Phosphorus)"),
    "industrial=slaughterhouse":        ("Meat Processing",               "Blood Meal / Bone Meal (Nitrogen / Phosphorus)"),
    "industrial=sawmill":               ("Wood / Paper / Pulp",           "Wood Ash / Biochar (Potassium / pH amendment)"),
    "industrial=steel":                 ("Steel / Foundry",               "Steel Slag (Silicates / Calcium)"),
    "industrial=metal":                 ("Steel / Foundry",               "Steel Slag (Silicates / Calcium)"),
    "industrial=foundry":               ("Steel / Foundry",               "Steel Slag (Silicates / Calcium)"),
    "industrial=chemical":              ("Chemical / Fertilizer Plant",   "Off-spec Product / Process Sludge (Variable NPK)"),
    "industrial=pharmaceutical":        ("Pharmaceutical / Biotech",      "Fermentation Biomass (Nitrogen)"),
    "industrial=food_processing":       ("Food Processing",               "Organic Sludge (Broad NPK)"),
    "industrial=oil":                   ("Vegetable Oil / Olive Mill",    "Olive Mill Wastewater / Press Cake (Potassium / Phosphorus)"),
    "industrial=recycling":             ("Waste Management / Composting", "Digestate / Compost (Broad NPK)"),
    "industrial=agricultural":          ("Agriculture / Livestock",       "Animal Manure (Broad NPK)"),
    "industrial=paper":                 ("Wood / Paper / Pulp",           "Wood Ash / Biochar (Potassium / pH amendment)"),
    "industrial=textile":               ("Textile Manufacturing",         "Lint / Cotton Sludge (Organic Carbon)"),
    "landuse=farmyard":                 ("Agriculture / Livestock",       "Animal Manure (Broad NPK)"),
    "landuse=greenhouse_horticulture":  ("Agriculture / Livestock",       "Organic Compost (Broad NPK)"),
    "man_made=works":                   ("Industrial Works",              "Process Waste (Variable)"),
    "man_made=wastewater_plant":        ("Waste Management / Composting", "Digestate / Compost (Broad NPK)"),
    "man_made=composting_facility":     ("Waste Management / Composting", "Digestate / Compost (Broad NPK)"),
}

NAME_KEYWORD_MAP = [
    {"keywords": ["poultry","chicken","broiler","hatchery"],                   "exclude": [],                                                                          "industry": "Poultry / Egg Production",          "waste": "High Nitrogen Manure"},
    {"keywords": ["brewery","birrificio","distillery","winery","cantina","brewing","malt"], "exclude": [],                                                             "industry": "Brewery / Distillery",              "waste": "Spent Grains (Organic Matter)"},
    {"keywords": ["steel","foundry","smelting","iron","metallurg"],            "exclude": [],                                                                          "industry": "Steel / Foundry",                   "waste": "Steel Slag (Silicates / Calcium)"},
    {"keywords": ["dairy","milk","cheese","creamery","caseificio","latteria"], "exclude": [],                                                                          "industry": "Dairy / Milk Processing",           "waste": "Whey / Sludge (Nitrogen / Phosphorus)"},
    {"keywords": ["sugar","zuccherificio","molasses"],                         "exclude": [],                                                                          "industry": "Sugar Processing",                  "waste": "Press Mud (Potassium)"},
    {"keywords": ["slaughterhouse","macello","abattoir","meat","rendering"],   "exclude": [],                                                                          "industry": "Meat Processing",                   "waste": "Blood Meal / Bone Meal (Nitrogen / Phosphorus)"},
    {"keywords": ["fish","seafood","cannery","fishery","pescheria industriale"],"exclude": [],                                                                         "industry": "Fish / Seafood Processing",         "waste": "Fish Emulsion / Bone Meal (Nitrogen)"},
    {"keywords": ["sawmill","segheria","pulp","cellulose","timber"],           "exclude": [],                                                                          "industry": "Wood / Paper / Pulp",               "waste": "Wood Ash / Biochar (Potassium / pH amendment)"},
    {"keywords": ["textile","tessile","cotton","wool","dyeing","tintoria"],    "exclude": [],                                                                          "industry": "Textile Manufacturing",             "waste": "Lint / Cotton Sludge (Organic Carbon)"},
    {"keywords": ["olive","oil mill","frantoio"],                              "exclude": [],                                                                          "industry": "Vegetable Oil / Olive Mill",         "waste": "Olive Mill Wastewater / Press Cake (Potassium / Phosphorus)"},
    {"keywords": ["compost","biogas","anaerobic","digestore"],                 "exclude": [],                                                                          "industry": "Waste Management / Composting",     "waste": "Digestate / Compost (Broad NPK)"},
    {"keywords": ["pharmaceutical","pharma","biotech","farmaceutic"],          "exclude": ["photographic","fotografic","dental","optical"],                            "industry": "Pharmaceutical / Biotech",          "waste": "Fermentation Biomass (Nitrogen)"},
    {"keywords": ["laboratory","laboratorio"],                                 "exclude": ["photographic","fotografic","dental","optical","medical","analisi","clinical"], "industry": "Pharmaceutical / Biotech",       "waste": "Fermentation Biomass (Nitrogen)"},
    {"keywords": ["bakery","panificio","forno","flour","farina","mulino"],     "exclude": [],                                                                          "industry": "Grain / Flour Milling",             "waste": "Bran / Flour Dust (Organic Matter)"},
]

INDUSTRY_COLORS = {
    "Brewery / Distillery":          "#FFA500",
    "Dairy / Milk Processing":       "#ADD8E6",
    "Steel / Foundry":               "#B22222",
    "Meat Processing":               "#DC143C",
    "Wood / Paper / Pulp":           "#8B5A2B",
    "Textile Manufacturing":         "#9370DB",
    "Vegetable Oil / Olive Mill":    "#9ACD32",
    "Waste Management / Composting": "#696969",
    "Pharmaceutical / Biotech":      "#00CED1",
    "Chemical / Fertilizer Plant":   "#FF4500",
    "Agriculture / Livestock":       "#228B22",
    "Grain / Flour Milling":         "#DAA520",
    "Poultry / Egg Production":      "#FFD700",
    "Fish / Seafood Processing":     "#4682B4",
    "Food Processing":               "#FF8C00",
    "Industrial Works":              "#A9A9A9",
    "Sugar Processing":              "#FFB6C1",
    "Unknown / Other":               "#505050",
}

NPK_SCORES = {
    "High Nitrogen Manure":                                           {"N": 9, "P": 5, "K": 4, "label": "High N"},
    "Spent Grains (Organic Matter)":                                  {"N": 6, "P": 3, "K": 2, "label": "Med N"},
    "Steel Slag (Silicates / Calcium)":                               {"N": 0, "P": 4, "K": 1, "label": "Low P"},
    "Whey / Sludge (Nitrogen / Phosphorus)":                          {"N": 7, "P": 6, "K": 2, "label": "High N+P"},
    "Press Mud (Potassium)":                                          {"N": 2, "P": 2, "K": 8, "label": "High K"},
    "Blood Meal / Bone Meal (Nitrogen / Phosphorus)":                 {"N": 9, "P": 7, "K": 1, "label": "High N+P"},
    "Fish Emulsion / Bone Meal (Nitrogen)":                           {"N": 8, "P": 6, "K": 2, "label": "High N+P"},
    "Wood Ash / Biochar (Potassium / pH amendment)":                  {"N": 0, "P": 2, "K": 7, "label": "High K"},
    "Lint / Cotton Sludge (Organic Carbon)":                          {"N": 3, "P": 2, "K": 2, "label": "Low NPK"},
    "Olive Mill Wastewater / Press Cake (Potassium / Phosphorus)":    {"N": 2, "P": 5, "K": 6, "label": "Med P+K"},
    "Digestate / Compost (Broad NPK)":                                {"N": 5, "P": 4, "K": 5, "label": "Balanced"},
    "Off-spec Product / Process Sludge (Variable NPK)":               {"N": 4, "P": 4, "K": 4, "label": "Variable"},
    "Fermentation Biomass (Nitrogen)":                                {"N": 7, "P": 3, "K": 2, "label": "High N"},
    "Organic Sludge (Broad NPK)":                                     {"N": 5, "P": 4, "K": 4, "label": "Balanced"},
    "Animal Manure (Broad NPK)":                                      {"N": 6, "P": 4, "K": 5, "label": "Balanced"},
    "Organic Compost (Broad NPK)":                                    {"N": 4, "P": 3, "K": 4, "label": "Balanced"},
    "Process Waste (Variable)":                                       {"N": 3, "P": 3, "K": 3, "label": "Variable"},
    "Bran / Flour Dust (Organic Matter)":                             {"N": 4, "P": 3, "K": 2, "label": "Low NPK"},
}


def classify_facility(name: str, tags: dict) -> tuple[str, str]:
    for key, value in tags.items():
        tag_string = f"{key}={value}".lower()
        if tag_string in TAG_WASTE_MAP:
            return TAG_WASTE_MAP[tag_string]
    tag_values    = " ".join(str(v) for v in tags.values())
    combined_text = (name + " " + tag_values).lower()
    for entry in NAME_KEYWORD_MAP:
        if any(excl in combined_text for excl in entry["exclude"]):
            continue
        if any(kw in combined_text for kw in entry["keywords"]):
            return entry["industry"], entry["waste"]
    return "Unknown / Other", "No match in waste dictionary"


def _fetch_waste_layer_raw(lat: float, lng: float, radius_m: int) -> list[dict]:
    query = f"""
    [out:json][timeout:60][maxsize:536870912];
    (
      node["landuse"="industrial"](around:{radius_m},{lat},{lng});
      way["landuse"="industrial"](around:{radius_m},{lat},{lng});
      node["man_made"="works"](around:{radius_m},{lat},{lng});
      way["man_made"="works"](around:{radius_m},{lat},{lng});
      node["industrial"](around:{radius_m},{lat},{lng});
      way["industrial"](around:{radius_m},{lat},{lng});
      node["craft"](around:{radius_m},{lat},{lng});
      way["craft"](around:{radius_m},{lat},{lng});
    );
    out center tags;
    """
    return run_overpass_query(query)


@st.cache_data(ttl=1800, show_spinner=False)
def fetch_waste_layer(lat: float, lng: float, radius_m: int) -> list[dict]:
    """Cached wrapper — same coordinates + radius reuses results for 30 minutes."""
    return _fetch_waste_layer_raw(lat, lng, radius_m)

@st.cache_data(ttl=1800, show_spinner=False)
def fetch_logistics_layer(lat: float, lng: float, radius_m: int) -> list[dict]:
    """Cached wrapper — same coordinates + radius reuses results for 30 minutes."""
    return _fetch_logistics_layer_raw(lat, lng, radius_m)

def build_waste_dataframe(elements: list[dict], search_lat: float, search_lon: float) -> pd.DataFrame:
    rows = []
    for el in elements:
        tags = el.get("tags", {})
        name = tags.get("name", tags.get("operator", "Unnamed Facility"))
        if el["type"] == "way":
            center = el.get("center", {})
            lat    = center.get("lat")
            lon    = center.get("lon")
        else:
            lat = el.get("lat")
            lon = el.get("lon")
        if lat is None or lon is None:
            continue
        addr_parts = [tags.get("addr:street",""), tags.get("addr:housenumber",""), tags.get("addr:city","")]
        address    = ", ".join(p for p in addr_parts if p) or "—"
        categories = ", ".join(f"{k}={tags[k]}" for k in ["landuse","industrial","man_made","craft","amenity"] if k in tags)
        industry, waste = classify_facility(name, tags)
        rows.append({
            "Company Name":               name,
            "Address":                    address,
            "OSM Categories":             categories,
            "Predicted Industry":         industry,
            "Potential Fertilizer Waste": waste,
            "lat":  lat, "lon": lon, # Distance is now calculated in add_osrm_distances
            "N Score":   NPK_SCORES.get(waste, {}).get("N", 0),
            "P Score":   NPK_SCORES.get(waste, {}).get("P", 0),
            "K Score":   NPK_SCORES.get(waste, {}).get("K", 0),
            "NPK Label": NPK_SCORES.get(waste, {}).get("label", "—"),
        })
    df = pd.DataFrame(rows)
    df = add_osrm_distances(df, search_lat, search_lon)
    return df


# ═════════════════════════════════════════════════════════════════════════════
# LAYER 2 — LOGISTICS INFRASTRUCTURE
# ═════════════════════════════════════════════════════════════════════════════

INFRA_TYPES = [
    ("aeroway",   "aerodrome",         "Airport",               "#E040FB", 1),  # vivid purple
    ("aeroway",   "terminal",          "Airport Terminal",      "#CE93D8", 1),  # light purple
    ("amenity",   "ferry_terminal",    "Ferry Terminal",        "#00B4FF", 2),  # cyan blue
    ("harbour",   None,                "Harbour / Port",        "#0064C8", 2),  # mid blue
    ("landuse",   "port",              "Commercial Port",       "#00388A", 2),  # dark navy
    ("man_made",  "pier",              "Pier / Jetty",          "#80D8FF", 3),  # pale sky blue
    ("railway",   "station",           "Rail Station",          "#FFA500", 2),  # orange
    ("railway",   "halt",              "Rail Halt",             "#FFC350", 3),  # light orange
    ("railway",   "freight_terminal",  "Rail Freight Terminal", "#C87800", 1),  # dark amber
    ("railway",   "yard",              "Rail Yard",             "#B46400", 2),  # brown amber
    ("highway",   "motorway_junction", "Motorway Junction",     "#FF4D4D", 1),  # red
    ("highway",   "trunk",             "Trunk Road",            "#FF7878", 2),  # light red
    ("highway",   "motorway",          "Motorway",              "#DC3232", 1),  # dark red
    ("landuse",   "industrial",        "Industrial Zone",       "#969696", 4),  # grey
    ("building",  "warehouse",         "Warehouse",             "#B4B478", 4),  # olive
    ("industrial","cold_storage",      "Cold Storage",          "#00E5A0", 2),  # green (matches app accent)
    ("amenity",   "fuel",              "Fuel Station (HGV)",    "#C8C800", 4),  # yellow
]

COLOUR_BY_LABEL = {label: color for _, _, label, color, _ in INFRA_TYPES}


def classify_infra(tags: dict):
    best = None
    best_priority = 999
    for key, val, label, color, priority in INFRA_TYPES:
        tag_val = tags.get(key)
        if tag_val is None:
            continue
        if val is None or tag_val == val:
            if priority < best_priority:
                best = (label, color)
                best_priority = priority
    return best


def _fetch_logistics_layer_raw(lat: float, lng: float, radius_m: int) -> list[dict]:
    # Deduplicate: collect unique (key, val) pairs — seen set covers both keyed and unkeyed
    tag_filters  = []
    seen_kv      = set()
    seen_key_only = set()
    for key, val, *_ in INFRA_TYPES:
        if val is not None:
            kv = (key, val)
            if kv not in seen_kv:
                tag_filters.append(f'node["{key}"="{val}"](around:{radius_m},{lat},{lng});')
                tag_filters.append(f'way["{key}"="{val}"](around:{radius_m},{lat},{lng});')
                seen_kv.add(kv)
        else:
            if key not in seen_key_only:
                tag_filters.append(f'node["{key}"](around:{radius_m},{lat},{lng});')
                tag_filters.append(f'way["{key}"](around:{radius_m},{lat},{lng});')
                seen_key_only.add(key)
    inner = "\n  ".join(tag_filters)
    query = f"[out:json][timeout:60][maxsize:536870912];\n(\n  {inner}\n);\nout center tags;"
    return run_overpass_query(query)


def build_logistics_dataframe(elements: list[dict], search_lat: float, search_lng: float) -> pd.DataFrame:
    rows = []
    for el in elements:
        tags = el.get("tags", {})
        name = tags.get("name", tags.get("operator", tags.get("ref", "Unnamed")))
        if el["type"] == "way":
            center = el.get("center", {})
            lat    = center.get("lat")
            lon    = center.get("lon")
        else:
            lat = el.get("lat")
            lon = el.get("lon")
        if lat is None or lon is None:
            continue
        classified = classify_infra(tags)
        if classified is None:
            continue
        label, color = classified
        addr_parts   = [tags.get("addr:street",""), tags.get("addr:city","")]
        address      = ", ".join(p for p in addr_parts if p) or "—"
        rows.append({
            "Name":          name,
            "Type":          label,
            "Address":       address,
            "lat":  lat, "lon": lon,
            "color": color,
        })
    df = pd.DataFrame(rows) if rows else pd.DataFrame()
    df = add_osrm_distances(df, search_lat, search_lng)
    return df


def compute_logistics_score(df: pd.DataFrame) -> tuple[int, dict]:
    if df.empty:
        return 0, {}
    weights = {
        "Motorway Junction":     25,
        "Rail Freight Terminal": 20,
        "Commercial Port":       20,
        "Airport":               15,
        "Cold Storage":          15,
        "Rail Station":          10,
        "Harbour / Port":        10,
        "Ferry Terminal":         5,
        "Warehouse":              5,
        "Trunk Road":             5,
        "Rail Yard":              5,
    }
    present   = set(df["Type"].unique())
    score     = 0
    breakdown = {}
    for infra_type, weight in weights.items():
        if any(infra_type in p for p in present):
            score += weight
            breakdown[infra_type] = weight
    return min(score, 100), breakdown

def compute_nearest_by_category(df: pd.DataFrame) -> list[dict]:
    """Computes the nearest instance for a set of priority infrastructure categories."""
    if df.empty:
        return []

    priority_categories = [
        {"label": "✈️ Airport", "types": ["Airport", "Airport Terminal"]},
        {"label": "⚓ Port / Harbour", "types": ["Commercial Port", "Harbour / Port"]},
        {"label": "🛣️ Motorway Access", "types": ["Motorway Junction", "Motorway"]},
        {"label": "🚂 Rail", "types": ["Rail Freight Terminal", "Rail Station"]},
        {"label": "❄️ Cold Storage", "types": ["Cold Storage"]},
        {"label": "⛽ Fuel Station", "types": ["Fuel Station (HGV)"]},
        {"label": "⛴️ Ferry", "types": ["Ferry Terminal"]},
    ]

    results = []
    for category in priority_categories:
        subset = df[df["Type"].isin(category["types"])]
        if not subset.empty:
            nearest = subset.loc[subset["Distance (km)"].idxmin()]
            results.append({
                "label": category["label"], "name": nearest["Name"],
                "distance_km": nearest["Distance (km)"], "found": True,
            })
        else:
            results.append({
                "label": category["label"], "name": None, "distance_km": None, "found": False,
            })
    return results

# ═════════════════════════════════════════════════════════════════════════════
# [LAYER 3 PLACEHOLDER — Climate / Meteorological]
# When ready: add fetch_climate_layer(), build_climate_dataframe() here.
# Toggle key: "layer_climate"
# ═════════════════════════════════════════════════════════════════════════════


# ═════════════════════════════════════════════════════════════════════════════
# SHARED FARM LINKING FLOW
# ═════════════════════════════════════════════════════════════════════════════

def render_farm_linking_ui(plat, plng, matched_country, prefix: str):
    """
    Renders the farm linking UI (radio + selectbox + overwrite gate).
    prefix: "fim_wm" or "fim_lm" — used to namespace session state keys.
    Returns (link_mode, target_farm, new_farm_name, confirmed).
    """
    try:
        sb         = get_supabase()
        _uid       = current_user()
        farms_resp = (
            sb.table("farms")
            .select("id, name, lat, lon")
            .eq("owner_id", _uid)
            .order("created_at", desc=True)
            .execute()
        ) if _uid else type("_R", (), {"data": []})()
        farms_list = farms_resp.data or []
    except Exception:
        farms_list = []

    st.divider()
    st.markdown("**📌 Link this location to a farm profile (optional)**")

    link_mode = st.radio(
        "What would you like to do?",
        options=[
            "Just search here — do not link to any farm",
            "Link to an existing farm profile",
            "Create a new farm profile at this location",
        ],
        key=f"{prefix}_link_mode",
    )

    selected_farm_name = "— Do not link —"
    new_farm_name      = ""
    target_farm        = None

    if link_mode == "Link to an existing farm profile":
        if farms_list:
            farms_with_coords = [f for f in farms_list if f.get("lat") is not None]
            if farms_with_coords:
                st.caption(
                    f"⚠️ {len(farms_with_coords)} farm(s) already have coordinates: "
                    f"{', '.join(f['name'] for f in farms_with_coords)}. Overwriting requires confirmation."
                )

            def farm_label(f):
                if f.get("lat") is not None:
                    return f"🟢 {f['name']}  ({f['lat']:.4f}, {f['lon']:.4f})"
                return f"🟡 {f['name']}  — no coordinates yet"

            farm_display_options = ["— Select a farm —"] + [farm_label(f) for f in farms_list]
            selected_label       = st.selectbox(
                "Select farm profile:", options=farm_display_options,
                key=f"{prefix}_farm_select",
                help="🟢 = coordinates already saved  |  🟡 = no coordinates yet",
            )
            if selected_label != "— Select a farm —":
                for f in farms_list:
                    if f["name"] in selected_label:
                        selected_farm_name = f["name"]
                        target_farm        = f
                        break
        else:
            st.caption("No farm profiles yet. Create one below or from the ROI Calculator.")

    elif link_mode == "Create a new farm profile at this location":
        new_farm_name = st.text_input(
            "New farm name:", placeholder="e.g. Farm Nord Milano",
            key=f"{prefix}_new_farm_name",
        )
        st.caption(
            "Creates a farm profile with these coordinates. "
            "Go to the ROI Calculator to complete the financial configuration."
        )

    # Overwrite gate
    needs_overwrite = (
        link_mode == "Link to an existing farm profile"
        and target_farm is not None
        and target_farm.get("lat") is not None
    )
    overwrite_key = f"{prefix}_overwrite_confirmed"

    if needs_overwrite and not st.session_state.get(overwrite_key, False):
        st.error(
            f"🔴 **{selected_farm_name}** already has coordinates saved "
            f"(`{target_farm['lat']:.4f}, {target_farm['lon']:.4f}`). "
            f"You must explicitly confirm before proceeding."
        )
        ow1, ow2 = st.columns(2)
        with ow1:
            if st.button("⚠️ Yes, overwrite existing coordinates", use_container_width=True,
                         type="primary", key=f"{prefix}_overwrite_yes"):
                st.session_state[overwrite_key] = True
                st.rerun()
        with ow2:
            if st.button("✖ Cancel", use_container_width=True, key=f"{prefix}_overwrite_no"):
                st.session_state["fim_pending_lat"]     = None
                st.session_state["fim_pending_lng"]     = None
                st.session_state["fim_pending_country"] = None
                st.session_state["fim_pending_code"]    = None
                st.session_state[overwrite_key]         = False
                st.rerun()
        return link_mode, target_farm, new_farm_name, False  # not confirmed yet

    if needs_overwrite and st.session_state.get(overwrite_key, False):
        st.success("✅ Overwrite confirmed. Click **Confirm** below to save.")

    return link_mode, target_farm, new_farm_name, True


def execute_farm_save(link_mode, target_farm, new_farm_name, plat, plng, matched_country, prefix):
    sb = get_supabase()
    overwrite_key = f"{prefix}_overwrite_confirmed"

    if link_mode == "Link to an existing farm profile" and target_farm:
        try:
            payload = {"lat": plat, "lon": plng}
            if matched_country:
                payload["country"] = matched_country
            sb.table("farms").update(payload).eq("id", target_farm["id"]).execute()
            st.success(f"✅ Coordinates saved to **{target_farm['name']}**.")
        except Exception as e:
            st.error(f"Could not update farm: {e}")

    elif link_mode == "Create a new farm profile at this location":
        if not new_farm_name.strip():
            st.error("Please enter a name for the new farm profile.")
            return
        try:
            payload = {
                "name":             new_farm_name.strip(),
                "lat":              plat,
                "lon":              plng,
                "agriculture_type": "CEA",
                "metadata":         {},
                "notes":            "Created from map. Complete financial details in the ROI Calculator.",
            }
            if matched_country:
                payload["country"] = matched_country
            sb.table("farms").insert(payload).execute()
            st.success(
                f"✅ Farm profile **{new_farm_name}** created. "
                f"Go to the ROI Calculator to complete its configuration."
            )
        except Exception as e:
            st.error(f"Could not create farm profile: {e}")

    st.session_state[overwrite_key] = False


# ═════════════════════════════════════════════════════════════════════════════
# PAGE CONFIG
# ═════════════════════════════════════════════════════════════════════════════

st.set_page_config(page_title="Farm Intelligence Map", page_icon="🗺️", layout="wide")
inject_styles()
from core.auth import require_login, current_user
require_login()

# ── Sidebar Dropdown & Expander Readability Fix ───────────────────────────
st.markdown("""
<style>
  /* Selectboxes and Multiselects inside sidebar expanders */
  /* Since expanders have a light background, these must use the light-theme palette 
     to avoid dark-on-dark text from inheriting sidebar styles. */
  [data-testid="stSidebar"] [data-testid="stExpander"] [data-baseweb="select"] > div {
    background-color: var(--surface) !important;
    border-color: var(--rule) !important;
  }
  [data-testid="stSidebar"] [data-testid="stExpander"] [data-baseweb="select"] * {
    color: var(--ink) !important;
    fill: var(--ink) !important;
  }
  /* Sidebar selectboxes outside of expanders: ensure borders use style tokens */
  [data-testid="stSidebar"] [data-baseweb="select"] > div {
    border-color: var(--rule-soft) !important;
  }

  /* ── Radio Button Visibility Fix ── */
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

st.title("Farm Intelligence Map")
st.markdown(
    "Explore your farm's environment through multiple intelligence layers. "
    "Click anywhere on the map to set or change the search origin. "
    "Data from OpenStreetMap — free, no API key required."
)

# ── Session state ─────────────────────────────────────────────────────────────

# Check for active farm and sync coordinates + rehydrate saved FIM data from metadata.
# Only sync when the active farm *changes* (new farm selected), not on every rerun —
# otherwise the sync clears freshly-fetched search results whenever the user searches
# at a location different from the active farm's saved coordinates.
_active_farm_init = st.session_state.get("active_farm")
if _active_farm_init and _active_farm_init.get("lat") and _active_farm_init.get("lon"):
    _farm_id = _active_farm_init.get("id")
    if _farm_id != st.session_state.get("fim_synced_farm_id"):
        st.session_state["fim_lat"] = _active_farm_init["lat"]
        st.session_state["fim_lng"] = _active_farm_init["lon"]
        st.session_state["fim_waste_df"]     = None
        st.session_state["fim_logistics_df"] = None
        st.session_state["fim_synced_farm_id"] = _farm_id

    # Rehydrate saved FIM data from farm metadata if session cache is empty
    _raw_meta_init = _active_farm_init.get("metadata")
    if isinstance(_raw_meta_init, str):
        import json as _json
        try:
            _raw_meta_init = _json.loads(_raw_meta_init)
        except Exception:
            _raw_meta_init = {}
    _meta = _raw_meta_init if isinstance(_raw_meta_init, dict) else {}
    if st.session_state.get("fim_waste_df") is None and "fim_waste_data" in _meta:
        try:
            _df = pd.DataFrame(_meta["fim_waste_data"])
            if not _df.empty:
                st.session_state["fim_waste_df"] = _df
        except Exception:
            pass
    if st.session_state.get("fim_logistics_df") is None and "fim_logistics_data" in _meta:
        try:
            _df = pd.DataFrame(_meta["fim_logistics_data"])
            if not _df.empty:
                st.session_state["fim_logistics_df"] = _df
        except Exception:
            pass

# Fallback for first load without an active farm
if "fim_lat" not in st.session_state:
    if "shared_lat" in st.session_state:
        st.session_state["fim_lat"] = st.session_state["shared_lat"]
        st.session_state["fim_lng"] = st.session_state["shared_lng"]
    else:
        st.session_state["fim_lat"], st.session_state["fim_lng"] = get_default_location()

for key, default in [
    ("fim_pending_lat",     None),
    ("fim_pending_lng",     None),
    ("fim_pending_country", None),
    ("fim_pending_code",    None),
    ("fim_wm_overwrite_confirmed", False),
    ("fim_lm_overwrite_confirmed", False),
    ("fim_waste_df",        None),
    ("fim_logistics_df",    None),
    ("fim_suitability_active", False),
    ("fim_suitability_count",  2),
    ("fim_suitability_results", {}),
    ("fim_synced_farm_id",  None),
]:
    if key not in st.session_state:
        st.session_state[key] = default

lat = st.session_state["fim_lat"]
lng = st.session_state["fim_lng"]

# ── Pending click confirmation ────────────────────────────────────────────────

if st.session_state["fim_pending_lat"] is not None:
    plat = st.session_state["fim_pending_lat"]
    plng = st.session_state["fim_pending_lng"]

    if st.session_state["fim_pending_country"] is None:
        detected_country, detected_code              = reverse_geocode_country(plat, plng)
        st.session_state["fim_pending_country"]      = detected_country
        st.session_state["fim_pending_code"]         = detected_code

    detected_country = st.session_state["fim_pending_country"]
    detected_code    = st.session_state.get("fim_pending_code", "")

    from core.data_tables import COUNTRIES, COUNTRY_CODE_MAP
    matched_country = COUNTRY_CODE_MAP.get(detected_code)

    with st.container(border=True):
        st.markdown(f"**New location selected: `{plat:.4f}, {plng:.4f}`**")

        if detected_country:
            if matched_country and matched_country in COUNTRIES:
                st.success(
                    f"✅ Country detected: **{matched_country}** — present in ROI Calculator presets. "
                    f"Will be set automatically if you save a farm profile here."
                )
            else:
                st.warning(
                    f"⚠️ Country detected: **{detected_country}** (code: {detected_code}) — "
                    f"not in ROI Calculator presets. Select country manually in the ROI Calculator."
                )
        else:
            st.caption("Country could not be detected automatically.")

        # Farm linking UI — shared for both layers
        link_mode, target_farm, new_farm_name, confirmed = render_farm_linking_ui(
            plat, plng, matched_country, prefix="fim_wm"
        )

        if confirmed:
            btn1, btn2 = st.columns(2)
            with btn1:
                if st.button("✅ Confirm — search here", use_container_width=True):
                    st.session_state["fim_lat"]             = plat
                    st.session_state["fim_lng"]             = plng
                    st.session_state["fim_pending_lat"]     = None
                    st.session_state["fim_pending_lng"]     = None
                    st.session_state["fim_pending_country"] = None
                    st.session_state["fim_waste_df"]        = None
                    st.session_state["fim_logistics_df"]    = None
                    st.session_state["shared_lat"]          = plat
                    st.session_state["shared_lng"]          = plng

                    execute_farm_save(link_mode, target_farm, new_farm_name, plat, plng, matched_country, prefix="fim_wm")
                    st.rerun()

            with btn2:
                if st.button("✖ Cancel", use_container_width=True):
                    st.session_state["fim_pending_lat"]             = None
                    st.session_state["fim_pending_lng"]             = None
                    st.session_state["fim_pending_country"]         = None
                    st.session_state["fim_wm_overwrite_confirmed"]  = False
                    st.rerun()

# ── Sidebar ───────────────────────────────────────────────────────────────────

with st.sidebar:
    render_farm_context_sidebar()
    st.title("🗺️ Farm Intelligence Map")
    st.markdown("Powered by **OpenStreetMap** — free, no API key required.")
    st.divider()

    st.markdown(f"**Current origin:** `{lat:.4f}, {lng:.4f}`")
    st.caption("Click anywhere on the map to move the search origin.")

    # Show active farm indicator and offer to jump to its location
    _active_farm = st.session_state.get("active_farm")
    if _active_farm:
        st.divider()
        st.markdown(f"**🏭 Active farm:** {_active_farm['name']}")
        if _active_farm.get("lat") and _active_farm.get("lon"): # Keep emoji in badge
            st.caption(f"📍 `{_active_farm['lat']:.4f}, {_active_farm['lon']:.4f}`")
        else:
            st.caption("No coordinates saved for this farm yet.")

    with st.expander("✏️ Enter coordinates manually"):
        manual_lat = st.number_input("Latitude",  value=lat, format="%.4f", step=0.001, key="fim_manual_lat")
        manual_lng = st.number_input("Longitude", value=lng, format="%.4f", step=0.001, key="fim_manual_lng")
        if st.button("Apply coordinates", use_container_width=True):
            st.session_state["fim_lat"]          = manual_lat
            st.session_state["fim_lng"]          = manual_lng
            st.session_state["fim_waste_df"]     = None
            st.session_state["fim_logistics_df"] = None
            st.rerun()

    st.divider()
    st.markdown("**Active Layers**")
    layer_waste     = st.checkbox("♻️ Circular Economy / Waste Sources", value=True) # Keep emoji in checkbox
    layer_logistics = st.checkbox("🚛 Logistics Infrastructure",         value=True) # Keep emoji in checkbox
    # layer_climate = st.checkbox("🌤️ Climate / Meteorological", value=False)  # Layer 3 placeholder

    st.divider()
    radius_km = st.slider("Search Radius (km)", min_value=1, max_value=100, value=15, step=1)
    radius_m  = radius_km * 1000

    st.divider()
    
    # Layer-specific filters
    if layer_waste:
        all_waste_types = sorted(set(
            [e["waste"] for e in NAME_KEYWORD_MAP] +
            [v[1] for v in TAG_WASTE_MAP.values()]
        ))
        selected_waste_types = st.multiselect(
            "♻️ Filter waste types:", options=all_waste_types, default=[], # Keep emoji in multiselect
            placeholder="All waste types shown",
        )
    else:
        selected_waste_types = []

    if layer_logistics:
        all_infra_types  = sorted(set(label for _, _, label, _, _ in INFRA_TYPES))
        selected_infra_types = st.multiselect(
            "🚛 Filter infrastructure types:", options=all_infra_types, default=[], # Keep emoji in multiselect
            placeholder="All types shown",
        )
    else:
        selected_infra_types = []

    st.divider()
    search_clicked = st.button("🔍 Search All Active Layers", use_container_width=True)
    st.caption("**Data:** OpenStreetMap contributors via Overpass API.")

    # ORS routing status
    try:
        _ors_key_present = bool(st.secrets.get("ORS_API_KEY", ""))
    except Exception:
        _ors_key_present = False
    if _ors_key_present:
        _ors_err = st.session_state.get("_ors_last_error")
        if _ors_err:
            st.caption(f"🔴 ORS road routing: key found but last call failed — {_ors_err}")
        else:
            st.caption("🟢 ORS road routing active (priority infrastructure uses real road distances)")
    else:
        st.caption("⚪ ORS road routing inactive — add `ORS_API_KEY` to secrets for real road distances")

    with st.expander("🔧 Debug", expanded=False):
        _wdf = st.session_state.get("fim_waste_df")
        _ldf = st.session_state.get("fim_logistics_df")
        _af  = st.session_state.get("active_farm") or {}
        _raw_meta = _af.get("metadata") or {}
        if isinstance(_raw_meta, str):
            import json as _json
            try:
                _raw_meta = _json.loads(_raw_meta)
            except Exception:
                _raw_meta = {}
        _meta = _raw_meta if isinstance(_raw_meta, dict) else {}

        st.markdown(f"**Farm:** `{_af.get('name','—')}` id=`{_af.get('id','—')}`")
        st.markdown(f"**Synced farm id:** `{st.session_state.get('fim_synced_farm_id','—')}`")
        st.markdown(f"**fim_lat/lng:** `{st.session_state.get('fim_lat','—')}, {st.session_state.get('fim_lng','—')}`")

        st.markdown("**Waste DF:**")
        if _wdf is None:
            st.caption("None")
        else:
            st.caption(f"{len(_wdf)} rows · cols: `{list(_wdf.columns)}`")
            if "lat" in _wdf.columns and "lon" in _wdf.columns:
                _bad = _wdf[["lat","lon"]].apply(pd.to_numeric, errors="coerce").isna().any(axis=1).sum()
                st.caption(f"Invalid lat/lon rows: {int(_bad)}")

        st.markdown("**Logistics DF:**")
        if _ldf is None:
            st.caption("None")
        else:
            st.caption(f"{len(_ldf)} rows · cols: `{list(_ldf.columns)}`")
            if "lat" in _ldf.columns and "lon" in _ldf.columns:
                _bad = _ldf[["lat","lon"]].apply(pd.to_numeric, errors="coerce").isna().any(axis=1).sum()
                st.caption(f"Invalid lat/lon rows: {int(_bad)}")

        st.markdown("**Saved metadata keys:**")
        st.caption(str(list(_meta.keys())) if _meta else "none")
        st.caption(f"Saved waste records: {len(_meta.get('fim_waste_data', []))}")
        st.caption(f"Saved logistics records: {len(_meta.get('fim_logistics_data', []))}")

        if st.button("🗑️ Clear session cache (force fresh state)", use_container_width=True, key="fim_debug_clear"):
            for _k in [k for k in st.session_state if k.startswith("fim_")]:
                del st.session_state[_k]
            st.rerun()

    with st.expander("Location Suitability Finder", expanded=False): # Remove emoji from expander title
        st.caption(
            "Select up to 3 targets. The map will automatically search a wide radius, "
            "pinpoint the closest matches, and draw their suitability zones."
        )
        
        # Build unified dropdown options
        all_infra_types = sorted(set(label for _, _, label, _, _ in INFRA_TYPES))
        all_waste_types = sorted(set([e["waste"] for e in NAME_KEYWORD_MAP] + [v[1] for v in TAG_WASTE_MAP.values()]))
        dropdown_options = ["None / Skip"] + all_infra_types + all_waste_types

        st.slider(
            "Global Search Radius (km) — how far to look for targets", 
            min_value=10, max_value=150, value=50, step=10,
            key="fim_suit_search_radius",
            help="If the target isn't in your active layers, the app will search this far to find it."
        )

        st.checkbox("Show suitability circles on map", value=False, key="fim_suitability_active")

        for i in range(3):
            st.markdown(f"**Target {i+1}**")
            st.selectbox(
                "Facility / Waste Type", options=dropdown_options, 
                key=f"fim_suit_target_{i}"
            )
            st.slider(
                f"Ideal Proximity (km) for Target {i+1}", 
                min_value=1, max_value=100, value=20, step=1, 
                key=f"fim_suit_radius_{i}",
                help="Draws a circle of this radius around the discovered target."
            )

# ── Map (always visible) ──────────────────────────────────────────────────────

st.subheader("Intelligence Map") # Remove emoji from subheader
st.caption("Click anywhere on the map to move the search origin, then confirm.")

# Centre on pending location if one exists, so the map does not jump back on rerun
_map_center_lat = st.session_state.get("fim_pending_lat") or lat
_map_center_lng = st.session_state.get("fim_pending_lng") or lng
m = folium.Map(location=[_map_center_lat, _map_center_lng], zoom_start=12, tiles="CartoDB Positron")

# Origin marker — shows current confirmed origin
folium.Marker( # Keep icon
    location=[lat, lng],
    tooltip="Current search origin",
    popup="Current search origin",
    icon=folium.Icon(color="green", icon="crosshairs", prefix="fa"),
).add_to(m)

# Pending marker — shows clicked location awaiting confirmation
if st.session_state.get("fim_pending_lat") is not None:
    plat_preview = st.session_state["fim_pending_lat"]
    plng_preview = st.session_state["fim_pending_lng"] # Keep icon
    folium.Marker(
        location=[plat_preview, plng_preview],
        tooltip=f"📍 Pending: {plat_preview:.4f}, {plng_preview:.4f} — confirm below",
        popup=f"Pending location: {plat_preview:.4f}, {plng_preview:.4f}",
        icon=folium.Icon(color="orange", icon="map-marker", prefix="fa"),
    ).add_to(m)
    folium.Circle(
        location=[plat_preview, plng_preview],
        radius=radius_m,
        color="#ffc13d",
        weight=1.5,
        fill=True,
        fill_opacity=0.03,
        dash_array="6",
    ).add_to(m)

# Search radius circle
folium.Circle(
    location=[lat, lng], radius=radius_m,
    color="#00e5a0", weight=1.5, fill=True, fill_opacity=0.04,
).add_to(m)

# Suitability circles overlay — data pre-computed above, no st.* calls here
if st.session_state.get("fim_suitability_active", False):
    _suit_colors = ["#FF6B6B", "#FFD93D", "#6BCB77"]
    _suit_results = st.session_state.get("fim_suitability_results", {})
    for _i in range(3):
        _target      = st.session_state.get(f"fim_suit_target_{_i}", "None / Skip")
        _srad        = st.session_state.get(f"fim_suit_radius_{_i}", 20) * 1000
        _scol        = _suit_colors[_i]
        nearest_data = _suit_results.get(_i)
        if _target != "None / Skip" and nearest_data:
            _slat  = nearest_data["lat"]
            _slng  = nearest_data["lon"]
            _sname = nearest_data["name"] # Keep icon
            folium.Circle(
                location=[_slat, _slng],
                radius=_srad,
                color=_scol,
                weight=2,
                fill=True,
                fill_opacity=0.08,
                dash_array="4",
                tooltip=f"Suitability zone: {_sname} (≤ {_srad//1000} km)",
            ).add_to(m)
            folium.Marker( # Keep icon
                location=[_slat, _slng],
                tooltip=f"📌 {_target}: {_sname}",
                icon=folium.Icon(color="red" if _i==0 else ("orange" if _i==1 else "green"), icon="map-pin", prefix="fa"),
            ).add_to(m)

# Active farm pin — shown as a flag marker distinct from the search origin
_active_farm_map = st.session_state.get("active_farm")
if _active_farm_map and _active_farm_map.get("lat") and _active_farm_map.get("lon"): # Keep icon
    folium.Marker(
        location=[_active_farm_map["lat"], _active_farm_map["lon"]],
        tooltip=f"🏭 {_active_farm_map['name']} (active farm)",
        popup=folium.Popup(
            f"<b>🏭 {_active_farm_map['name']}</b><br>"
            f"Active farm profile<br>"
            f"{_active_farm_map['lat']:.4f}, {_active_farm_map['lon']:.4f}",
            max_width=220,
        ),
        icon=folium.Icon(color="red", icon="flag", prefix="fa"),
    ).add_to(m)

# Plot waste layer results
waste_cached = st.session_state.get("fim_waste_df")
if layer_waste and waste_cached is not None and not waste_cached.empty:
    for _, row in waste_cached.iterrows():
        try:
            hex_color = INDUSTRY_COLORS.get(row.get("Predicted Industry", "Unknown / Other"), "#505050")
            dist_label = f"{row['Distance (km)']} km" if "Distance (km)" in row.index else "—"
            folium.CircleMarker(
                location=[row["lat"], row["lon"]],
                radius=7,
                color=hex_color, fill=True, fill_color=hex_color, fill_opacity=0.85,
                tooltip=f"♻️ {row.get('Company Name','?')} | {row.get('Predicted Industry','?')} | {dist_label}",
                popup=folium.Popup(
                    f"<b>♻️ {row.get('Company Name','?')}</b><br>"
                    f"Industry: {row.get('Predicted Industry','?')}<br>"
                    f"Waste: {row.get('Potential Fertilizer Waste','?')}<br>"
                    f"NPK: {row.get('NPK Label','?')}<br>"
                    f"Distance: {dist_label}",
                    max_width=300,
                ),
            ).add_to(m)
        except Exception:
            continue

# Plot logistics layer results
logistics_cached = st.session_state.get("fim_logistics_df")
if layer_logistics and logistics_cached is not None and not logistics_cached.empty:
    for _, row in logistics_cached.iterrows():
        try:
            _lcolor    = row.get("color", "#969696")
            dist_label = f"{row['Distance (km)']} km" if "Distance (km)" in row.index else "—"
            folium.CircleMarker(
                location=[row["lat"], row["lon"]],
                radius=9,
                color=_lcolor, fill=True, fill_color=_lcolor, fill_opacity=0.75,
                tooltip=f"🚛 {row.get('Name','?')} | {row.get('Type','?')} | {dist_label}",
                popup=folium.Popup(
                    f"<b>🚛 {row.get('Name','?')}</b><br>"
                    f"Type: {row.get('Type','?')}<br>"
                    f"Distance: {dist_label}<br>"
                    f"Address: {row.get('Address','—')}",
                    max_width=260,
                ),
            ).add_to(m)
        except Exception:
            continue

map_result = st_folium(m, width="100%", height=540, returned_objects=["last_clicked"], key="fim_main_map")

# Capture map click
if map_result and map_result.get("last_clicked"):
    clicked = map_result["last_clicked"]
    clat    = round(clicked["lat"], 4)
    clng    = round(clicked["lng"], 4)
    if (clat != lat or clng != lng) and clat != st.session_state.get("fim_pending_lat"):
        st.session_state["fim_pending_lat"]     = clat
        st.session_state["fim_pending_lng"]     = clng
        st.session_state["fim_pending_country"] = None
        st.rerun()

# Combined legend
legend_html = ""
if layer_waste and waste_cached is not None and not waste_cached.empty: # Keep emojis in legend
    for ind in sorted(waste_cached["Predicted Industry"].unique()):
        c = INDUSTRY_COLORS.get(ind, "#505050")
        legend_html += f'<span style="margin-right:14px;white-space:nowrap;"><span style="color:{c};font-size:16px;">●</span> ♻️ {ind}</span>' # Keep emoji in legend
if layer_logistics and logistics_cached is not None and not logistics_cached.empty:
    for t in sorted(logistics_cached["Type"].unique()):
        c = COLOUR_BY_LABEL.get(t, "#969696")
        legend_html += f'<span style="margin-right:14px;white-space:nowrap;"><span style="color:{c};font-size:16px;">●</span> 🚛 {t}</span>'
if legend_html:
    st.markdown(
        f'<div style="display:flex;flex-wrap:wrap;gap:4px 0;margin:6px 0 12px 0;font-size:12px;">{legend_html}</div>',
        unsafe_allow_html=True,
    )

st.divider()

# ── Deferred Pre-computations & Search Execution ──
# This block runs AFTER the map has been sent to the browser, ensuring the map remains visible.
# NOTE: do NOT add "or suitability_active" here — that would create an infinite rerun loop
# whenever the suitability checkbox is ticked (block runs → st.rerun() → block runs → …).
if search_clicked:
    # Clear old caches instantly so ghost data doesn't persist if a massive query fails
    st.session_state["fim_waste_df"] = None
    st.session_state["fim_logistics_df"] = None

    # ── Suitability Finder Logic (runs as part of the same Search click) ──
    if st.session_state.get("fim_suitability_active", False):
        _search_radius_km = st.session_state.get("fim_suit_search_radius", 50)
        _suit_results = {}
        for _i in range(3):
            _target = st.session_state.get(f"fim_suit_target_{_i}", "None / Skip")
            if _target and _target != "None / Skip":
                with st.spinner(f"Locating nearest: {_target}…"):
                    _suit_results[_i] = find_triangulation_target(
                        _target, lat, lng, _search_radius_km,
                        st.session_state.get("fim_waste_df"),
                        st.session_state.get("fim_logistics_df"),
                    )
        st.session_state["fim_suitability_results"] = _suit_results

    with st.sidebar:
        # Warn user about expected query time at large radii
        if search_clicked and radius_km > 40:
            st.warning(
                f"⏳ Large search radius ({radius_km} km) — this may take 60–90 seconds. "
                "If the search times out, reduce the radius and try again.",
                icon="⚠️",
            )
        elif search_clicked and radius_km > 20:
            st.info(f"⏳ Querying {radius_km} km radius — expect 20–40 seconds.")
        
        if search_clicked and layer_waste:
            with st.spinner("♻️ Querying waste sources (may take up to 90s for large radius)…"):
                try:
                    elements = fetch_waste_layer(lat, lng, radius_m)
                    df_w     = build_waste_dataframe(elements, lat, lng)
                    st.session_state["fim_waste_df"] = df_w
                except Exception as e:
                    st.error(f"Waste layer error: {e}")

        if search_clicked and layer_logistics:
            with st.spinner("🚛 Querying logistics infrastructure…"):
                try:
                    elements = fetch_logistics_layer(lat, lng, radius_m)
                    df_l     = build_logistics_dataframe(elements, lat, lng)
                    st.session_state["fim_logistics_df"] = df_l
                except Exception as e:
                    st.error(f"Logistics layer error: {e}")

        # Auto-save to Supabase if a farm is active — no user action required
        _af = st.session_state.get("active_farm") if search_clicked else None
        if _af:
            _autosave_fim_to_supabase(_af, st.session_state.get("fim_waste_df"), st.session_state.get("fim_logistics_df"))

    st.rerun()

if waste_cached is None and logistics_cached is None:
    st.info("Toggle the layers you want in the sidebar, set your radius, and click **Search**.") # Remove emoji from info message
    st.stop()

# ── Farm Profile sync status ──────────────────────────────────────────────────
active_farm = st.session_state.get("active_farm")
if active_farm and (waste_cached is not None or logistics_cached is not None):
    _meta_check   = active_farm.get("metadata") or {}
    _has_saved_w  = "fim_waste_data"     in _meta_check and bool(_meta_check["fim_waste_data"])
    _has_saved_l  = "fim_logistics_data" in _meta_check and bool(_meta_check["fim_logistics_data"])
    _has_any_saved = _has_saved_w or _has_saved_l

    if _has_any_saved:
        _saved_parts = []
        if _has_saved_w: _saved_parts.append(f"{len(_meta_check['fim_waste_data'])} waste facilities")
        if _has_saved_l: _saved_parts.append(f"{len(_meta_check['fim_logistics_data'])} logistics points")
        st.caption(
            f"💾 Auto-saved to **{active_farm['name']}** · {' · '.join(_saved_parts)} · "
            f"Reloads automatically on next visit."
        )
    else:
        st.caption(f"💾 Results will be auto-saved to **{active_farm['name']}** on next search.")

    # Keep clear option — useful when relocating a farm to a new area
    if _has_any_saved:
        if st.button("🗑️ Clear Saved Map Data", use_container_width=False):
            with st.spinner("Clearing..."):
                try:
                    sb = get_supabase()
                    farm_resp     = sb.table("farms").select("metadata").eq("id", active_farm["id"]).execute()
                    _raw_meta     = farm_resp.data[0].get("metadata") if farm_resp.data else None
                    if isinstance(_raw_meta, str):
                        import json as _json
                        _raw_meta = _json.loads(_raw_meta)
                    existing_meta = _raw_meta if isinstance(_raw_meta, dict) else {}
                    existing_meta.pop("fim_waste_data",     None)
                    existing_meta.pop("fim_logistics_data", None)
                    sb.table("farms").update({"metadata": existing_meta}).eq("id", active_farm["id"]).execute()
                    if st.session_state["active_farm"].get("metadata"):
                        st.session_state["active_farm"]["metadata"].pop("fim_waste_data",     None)
                        st.session_state["active_farm"]["metadata"].pop("fim_logistics_data", None)
                    st.success("Saved map data cleared.")
                    st.rerun()
                except Exception as e:
                    st.error(f"Failed to clear data: {e}")

    st.divider()

# ═════════════════════════════════════════════════════════════════════════════
# RESULTS — shown as tabs, one per active layer
# ═════════════════════════════════════════════════════════════════════════════

active_tabs  = []
if layer_waste     and waste_cached     is not None: active_tabs.append("♻️ Waste Sources") # Keep emoji in tab label
if layer_logistics and logistics_cached is not None: active_tabs.append("🚛 Logistics")

if not active_tabs:
    st.info("Enable at least one layer in the sidebar and click Search.")
    st.stop()

tabs = st.tabs(active_tabs)
tab_idx = 0

# ── Waste Sources tab ─────────────────────────────────────────────────────────
if layer_waste and waste_cached is not None:
    with tabs[tab_idx]:
        tab_idx += 1
        df_w = waste_cached.copy()

        if selected_waste_types:
            df_w = df_w[df_w["Potential Fertilizer Waste"].isin(selected_waste_types)]

        if df_w.empty:
            st.warning("No waste sources match the current filters.")
        else:
            waste_counts = (
                df_w[df_w["Potential Fertilizer Waste"] != "No match in waste dictionary"]
                ["Potential Fertilizer Waste"].value_counts().reset_index()
            )
            waste_counts.columns = ["Waste Stream", "Count"]

            total        = len(df_w)
            matched      = (df_w["Predicted Industry"] != "Unknown / Other").sum()
            unique_waste = df_w[df_w["Potential Fertilizer Waste"] != "No match in waste dictionary"]["Potential Fertilizer Waste"].nunique()
            top_npk      = df_w[df_w["N Score"] > 0].nlargest(1, "N Score")
            top_n_source = top_npk["Company Name"].values[0] if not top_npk.empty else "—"

            m1, m2, m3, m4 = st.columns(4)
            m1.metric("Facilities Found",         total)
            m2.metric("Waste-Matched Facilities", matched)
            m3.metric("Distinct Waste Streams",   unique_waste)
            m4.metric("Top Nitrogen Source",      top_n_source)

            if matched > 0:
                top_wastes   = waste_counts.nlargest(3, "Count")["Waste Stream"].tolist()
                avg_distance = df_w[df_w["Predicted Industry"] != "Unknown / Other"]["Distance (km)"].mean()
                closest      = df_w[df_w["Predicted Industry"] != "Unknown / Other"].iloc[0] # Keep emoji in info message
                st.info(
                    f"📊 Within **{radius_km} km**: **{total}** facilities, **{matched}** waste-matched "
                    f"across **{unique_waste}** categories. Top streams: **{', '.join(top_wastes)}**. "
                    f"Closest: **{closest['Company Name']}** ({closest['Distance (km)']} km) — "
                    f"**{closest['Predicted Industry']}**. Avg distance: **{avg_distance:.2f} km**."
                )

            st.divider()
            display_cols      = ["Company Name","Distance (km)","Routing","Address","OSM Categories",
                                 "Predicted Industry","Potential Fertilizer Waste","NPK Label","N Score","P Score","K Score"]
            show_matched_only = st.toggle("Show only waste-matched facilities", value=False, key="fim_wm_toggle")
            display_df        = df_w[df_w["Predicted Industry"] != "Unknown / Other"] if show_matched_only else df_w

            def highlight_matched(row):
                if row["Predicted Industry"] != "Unknown / Other":
                    return ["background-color: rgba(0,229,160,0.08)"] * len(row)
                return [""] * len(row)

            st.dataframe(
                display_df[display_cols].style.apply(highlight_matched, axis=1),
                use_container_width=True, hide_index=True,
            )

            st.divider()
            csv = df_w[display_cols + ["lat","lon"]].to_csv(index=False).encode("utf-8")
            st.download_button("⬇️ Export Waste Sources CSV", csv,
                               f"waste_{lat:.3f}_{lng:.3f}_{radius_km}km.csv", "text/csv")

            st.divider()
            if not waste_counts.empty:
                wc_sorted = waste_counts.sort_values("Count", ascending=True)
                fig = px.bar(wc_sorted, x="Count", y="Waste Stream", orientation="h",
                             text="Count", color="Count", color_continuous_scale="Greens")
                fig.update_traces(textposition="outside")
                fig.update_layout(
                    plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
                    font_color="#e8ecf0", coloraxis_showscale=False,
                    height=max(300, len(wc_sorted) * 45),
                    margin=dict(l=10, r=60, t=10, b=10),
                    xaxis=dict(showgrid=False), yaxis=dict(tickfont=dict(size=12)),
                )
                st.plotly_chart(fig, use_container_width=True)

# ── Logistics tab ─────────────────────────────────────────────────────────────
if layer_logistics and logistics_cached is not None:
    with tabs[tab_idx]:
        df_l = logistics_cached.copy()

        if selected_infra_types:
            df_l = df_l[df_l["Type"].isin(selected_infra_types)]

        if df_l.empty:
            st.warning("No logistics infrastructure matches the current filters.")
        else:
            score, breakdown = compute_logistics_score(df_l)
            total   = len(df_l)
            types   = df_l["Type"].nunique()
            nearest = df_l.iloc[0]

            m1, m2, m3, m4 = st.columns(4)
            m1.metric("Infrastructure Found", total)
            m2.metric("Distinct Types",       types)
            m3.metric("Nearest Feature",      f"{nearest['Distance (km)']} km")
            m4.metric("Logistics Score", f"{score}/100",
                help=(
                    "Composite score based on presence of key logistics infrastructure within the search radius. "
                    "Points awarded per type: Motorway Junction (25), Rail Freight Terminal (20), "
                    "Commercial Port (20), Airport (15), Cold Storage (15), Rail Station (10), "
                    "Harbour / Port (10), Ferry Terminal (5), Warehouse (5), Trunk Road (5), Rail Yard (5). "
                    "Capped at 100."
                ),
            )

            score_color = "#00e5a0" if score >= 60 else ("#ffc13d" if score >= 35 else "#ff4d4d")
            st.markdown(
                f"""<div style="background:#1a1a2e;border-radius:8px;padding:12px 16px;margin:8px 0 16px 0;">
                <div style="font-size:12px;color:#8892a0;margin-bottom:6px;">Logistics Score Breakdown</div>
                <div style="background:#2a2a3e;border-radius:4px;height:10px;width:100%;">
                  <div style="background:{score_color};border-radius:4px;height:10px;width:{score}%;"></div>
                </div>
                <div style="font-size:11px;color:#8892a0;margin-top:6px;">
                  {" &nbsp;·&nbsp; ".join(f"{k} (+{v})" for k,v in breakdown.items())}
                </div></div>""",
                unsafe_allow_html=True,
            )

            st.caption("📍 Nearest key infrastructure from current origin")
            nearest_infra = compute_nearest_by_category(logistics_cached) # Remove emoji from caption
            if nearest_infra:
                cols = st.columns(7)
                for i, item in enumerate(nearest_infra):
                    with cols[i]:
                        st.markdown(f"**{item['label']}**")
                        if item['found']:
                            name_trunc = (item['name'][:20] + '…') if len(item['name']) > 20 else item['name']
                            st.markdown(
                                f"<div style='color:#00e5a0; font-weight:600;'>{item['distance_km']:.1f} km</div>"
                                f"<div style='font-size:11px; color:#8892a0;'>{name_trunc}</div>",
                                unsafe_allow_html=True
                            )
                        else:
                            st.markdown(
                                f"<div style='color:#696969; font-weight:600;'>—</div>"
                                f"<div style='font-size:11px; color:#696969;'>Not found</div>",
                                unsafe_allow_html=True
                            )

            st.divider()
            display_cols   = ["Name", "Type", "Distance (km)", "Routing", "Address"]
            priority_types = {"Airport","Airport Terminal","Commercial Port","Harbour / Port",
                              "Rail Freight Terminal","Ferry Terminal","Motorway Junction","Cold Storage"}
            show_priority  = st.toggle("Show only high-priority types", value=False, key="fim_lm_toggle")
            display_df     = df_l[df_l["Type"].isin(priority_types)] if show_priority else df_l

            def highlight_priority(row):
                if row["Type"] in priority_types:
                    return ["background-color: rgba(0,229,160,0.08)"] * len(row)
                return [""] * len(row)

            st.dataframe(
                display_df[display_cols].style.apply(highlight_priority, axis=1),
                use_container_width=True, hide_index=True,
            )

            st.divider()
            csv = df_l[display_cols + ["lat","lon"]].to_csv(index=False).encode("utf-8")
            st.download_button("⬇️ Export Logistics CSV", csv,
                               f"logistics_{lat:.3f}_{lng:.3f}_{radius_km}km.csv", "text/csv")

            st.divider()
            type_counts = df_l["Type"].value_counts().reset_index()
            type_counts.columns = ["Type", "Count"]
            type_counts = type_counts.sort_values("Count", ascending=True)
            bar_colors  = [COLOUR_BY_LABEL.get(t, "#969696") for t in type_counts["Type"]]

            fig = px.bar(type_counts, x="Count", y="Type", orientation="h",
                         text="Count", color="Type", color_discrete_sequence=bar_colors)
            fig.update_traces(textposition="outside", showlegend=False)
            fig.update_layout(
                plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
                font_color="#e8ecf0",
                height=max(300, len(type_counts) * 40),
                margin=dict(l=10, r=60, t=10, b=10),
                xaxis=dict(showgrid=False), yaxis=dict(showgrid=False, title=""),
            )
            st.plotly_chart(fig, use_container_width=True)
