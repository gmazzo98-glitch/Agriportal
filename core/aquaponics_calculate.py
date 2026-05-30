import math
import copy

from core.data_tables import COUNTRIES, LABOUR_TASKS
from core.greenhouse_data_tables import (
    GREENHOUSE_CROPS, POLYTUNNEL_CROPS, GREENHOUSE_CAPEX,
    AQUAPONICS_CAPEX, FISH_SPECIES, FISH_SYSTEM_PARAMS, COUPLING_PARAMS,
)
from core.greenhouse_calculate import calculate_greenhouse

# ─────────────────────────────────────────────────────────────────────────────
# COUNTRY AMBIENT TEMPERATURE DEFAULTS (°C annual mean)
# Source: World Bank Climate Data / WMO. Replaced by Layer 2 climate API.
# ─────────────────────────────────────────────────────────────────────────────
COUNTRY_AMBIENT_TEMP = {
    "Germany": 9.6, "France": 12.4, "Italy": 13.9, "Spain": 14.8,
    "Netherlands": 10.4, "Denmark": 8.9, "Sweden": 6.4, "Norway": 5.4,
    "Finland": 4.9, "Switzerland": 8.6, "Austria": 8.8, "Belgium": 10.5,
    "United Kingdom": 9.8, "Ireland": 9.8, "Poland": 8.9, "Czech Republic": 9.1,
    "United States": 13.0, "Canada": 5.6, "Mexico": 21.0, "Brazil": 25.4,
    "Chile": 13.5, "Argentina": 18.0, "Colombia": 24.0,
    "United Arab Emirates": 28.0, "Saudi Arabia": 25.0, "Qatar": 28.0,
    "Kuwait": 26.0, "Bahrain": 27.0, "Oman": 28.0, "Israel": 19.5,
    "Japan": 14.4, "South Korea": 12.5, "Taiwan": 23.0, "China": 13.0,
    "Singapore": 27.5, "Malaysia": 27.0, "Thailand": 28.0, "Vietnam": 25.5,
    "Indonesia": 27.0, "Australia": 21.8, "New Zealand": 12.5,
    "India": 24.7, "Morocco": 17.5, "Egypt": 22.0, "South Africa": 17.5,
    "Kenya": 19.0,
}

# ─────────────────────────────────────────────────────────────────────────────
# SALMON COLD-WATER WARNING THRESHOLD
# ─────────────────────────────────────────────────────────────────────────────
SALMON_WARNING_SPECIES = {"Atlantic Salmon"}
SALMON_OPTIMAL_TEMP_MAX = 14.0   # °C — above this, salmon welfare is impaired


# ─────────────────────────────────────────────────────────────────────────────
# FISH LABOUR HOURS PER M³ PER YEAR (by automation level)
# Source: Timmons & Ebeling RAS Engineering benchmarks
# ─────────────────────────────────────────────────────────────────────────────
FISH_LABOUR_HRS_M3 = {"None": 1.5, "Low": 1.2, "Medium": 0.8, "High": 0.5}

# kWh per kg fish produced — aeration + pumping (automation-adjusted)
FISH_AERATION_KWH_PER_KG = {"None": 4.0, "Low": 3.5, "Medium": 3.0, "High": 2.0}


def calculate_fish(inputs: dict, mode: str = "decoupled") -> dict:
    """
    Fish production economics for a standalone RAS system.
    Returns fish P&L, CAPEX, and nutrient output.
    Called by calculate_aquaponics(); can also be used standalone.
    """
    # ── SECTION 1 — UNPACK ───────────────────────────────────────────────────
    species_name     = inputs["species"]
    tank_volume_m3   = float(inputs["tank_volume_m3"])
    system_scale     = inputs["system_scale"]
    country          = inputs["country"]
    automation       = inputs["automation"]
    price_scenario   = inputs.get("price_scenario", "base")
    price_override   = float(inputs.get("price_override_fish", 0.0))
    water_price      = float(inputs.get("water_price", 2.0))
    target_temp_c    = float(inputs.get("target_temp_c", 26.0))
    depreciation_years = int(inputs.get("fish_depreciation_years", 10))
    tax_rate         = float(inputs.get("tax_rate", 25.0)) / 100
    ltv              = float(inputs.get("ltv", 60.0)) / 100
    interest_rate    = float(inputs.get("interest_rate", 5.5)) / 100
    loan_term_years  = int(inputs.get("loan_term_years", 15))
    discount_rate    = float(inputs.get("discount_rate", 8.0)) / 100

    country_data  = COUNTRIES[country]
    elec_price    = country_data["kwh"]
    labour_rate   = country_data["labour"]
    # Use location-specific ambient temperature if available (from Open-Meteo),
    # otherwise fall back to the hardcoded country default table.
    _ambient_override = inputs.get("ambient_temp_annual")
    ambient_temp = float(_ambient_override) if _ambient_override is not None \
                   else COUNTRY_AMBIENT_TEMP.get(country, 15.0)

    sd = FISH_SPECIES[species_name]

    # ── SECTION 2 — SALMON WARNING ────────────────────────────────────────────
    salmon_warning = None
    if species_name in SALMON_WARNING_SPECIES:
        if target_temp_c > SALMON_OPTIMAL_TEMP_MAX:
            salmon_warning = (
                f"⚠️ Atlantic Salmon requires water temperature below {SALMON_OPTIMAL_TEMP_MAX}°C. "
                f"Your target ({target_temp_c}°C) exceeds this. Salmon cannot be used in coupled "
                f"aquaponics systems (shared loop forces a compromise temperature). "
                f"For aquaponics, reduce target temp or switch to a warm-water species."
            )

    # ── SECTION 3 — PRODUCTION ────────────────────────────────────────────────
    harvest_biomass_kg  = tank_volume_m3 * sd["stocking_density"]
    fish_per_batch      = harvest_biomass_kg / sd["harvest_weight_kg"]
    survival_rate       = 1 - sd["mortality_rate"] / 100
    kg_per_cycle        = fish_per_batch * survival_rate * sd["harvest_weight_kg"]
    cycles_per_year     = max(math.floor(365 / sd["grow_cycle_days"]), 1)
    annual_kg_fish      = kg_per_cycle * cycles_per_year

    # ── SECTION 4 — REVENUE ──────────────────────────────────────────────────
    if price_override > 0:
        effective_fish_price = price_override
    elif price_scenario == "low":
        effective_fish_price = sd["price_low"]
    elif price_scenario == "high":
        effective_fish_price = sd["price_high"]
    else:
        effective_fish_price = sd["price_base"]

    annual_fish_revenue = annual_kg_fish * effective_fish_price

    # ── SECTION 5 — FEED COST ────────────────────────────────────────────────
    annual_feed_kg   = annual_kg_fish * sd["feed_conversion_ratio"]
    annual_feed_cost = annual_feed_kg * sd["feed_cost_per_kg"] * country_data.get("feed_cost_index", 1.0)

    # ── SECTION 6 — FINGERLING COST ──────────────────────────────────────────
    annual_fingerling_cost = fish_per_batch * sd["fingerling_cost"] * country_data.get("fingerling_cost_index", 1.0) * cycles_per_year

    # ── SECTION 7 — ENERGY COST ──────────────────────────────────────────────
    # Aeration: production-based benchmark scaled by species O2 demand relative to Tilapia
    # FISH_SYSTEM_PARAMS oxygen values are peak metabolic rates — used as relative index only.
    # Tilapia (3.2 g/kg/hr) is the reference species at the base benchmark rate.
    _o2_ref   = 3.2  # Tilapia reference O2 consumption (g/kg/hr)
    _o2_scale = FISH_SYSTEM_PARAMS[species_name]["oxygen_consumption_g_per_kg_per_hour"] / _o2_ref
    aeration_kwh = annual_kg_fish * FISH_AERATION_KWH_PER_KG[automation] * _o2_scale

    # Pump: scales with water exchange rate relative to Tilapia baseline (2.5%/day)
    _we_ref   = 2.5  # Tilapia reference water exchange rate (%/day)
    _we_scale = FISH_SYSTEM_PARAMS[species_name]["water_exchange_rate_pct_per_day"] / _we_ref
    pump_kwh  = 0.5 * tank_volume_m3 * _we_scale * 365

    aeration_pump_kwh = aeration_kwh + pump_kwh

    # Heating: heat loss model — 10 W/m³ at ΔT=15°C baseline, scales linearly
    delta_t = max(0.0, target_temp_c - ambient_temp)
    heating_kwh = 10.0 * tank_volume_m3 * 8760 / 1000 * (delta_t / 15.0) if delta_t > 0 else 0.0

    annual_fish_kwh     = aeration_pump_kwh + heating_kwh
    annual_fish_energy  = annual_fish_kwh * elec_price

    # ── SECTION 8 — WATER COST ───────────────────────────────────────────────
    water_l_per_kg   = COUPLING_PARAMS["water_consumption_l_per_kg_fish_produced"]
    annual_water_m3  = (water_l_per_kg / 1000) * annual_kg_fish
    annual_water_cost = annual_water_m3 * water_price

    # ── SECTION 9 — LABOUR ───────────────────────────────────────────────────
    annual_fish_labour_hours = FISH_LABOUR_HRS_M3[automation] * tank_volume_m3
    annual_fish_labour_cost  = annual_fish_labour_hours * labour_rate

    # ── SECTION 10 — CAPEX ───────────────────────────────────────────────────
    capex_data = AQUAPONICS_CAPEX.get(mode, AQUAPONICS_CAPEX["decoupled"])[system_scale]
    inst       = capex_data["installation_factor"]

    tank_capex       = capex_data["tank_cost_per_m3"]    * tank_volume_m3 * inst
    filtration_capex = capex_data["filtration_per_m3"]   * tank_volume_m3 * inst
    aeration_capex   = capex_data["aeration_per_m3"]     * tank_volume_m3 * inst
    monitoring_capex = capex_data["monitoring_per_m3"]   * tank_volume_m3 * inst
    plumbing_capex   = capex_data["plumbing_per_m3"]     * tank_volume_m3 * inst
    # greenhouse_integration_cost_per_m2 handled at combined level

    total_fish_capex = (tank_capex + filtration_capex + aeration_capex +
                        monitoring_capex + plumbing_capex)

    # ── SECTION 11 — OPEX TOTALS AND EBITDA ──────────────────────────────────
    annual_fish_maintenance = total_fish_capex * 0.02

    total_fish_costs = (
        annual_feed_cost
        + annual_fingerling_cost
        + annual_fish_energy
        + annual_water_cost
        + annual_fish_labour_cost
        + annual_fish_maintenance
    )

    fish_ebitda        = annual_fish_revenue - total_fish_costs
    fish_ebitda_margin = fish_ebitda / annual_fish_revenue if annual_fish_revenue > 0 else 0.0

    # ── SECTION 12 — FINANCIAL ────────────────────────────────────────────────
    annual_depreciation = total_fish_capex / depreciation_years

    loan_amount = total_fish_capex * ltv
    if loan_amount > 0 and interest_rate > 0:
        r_m = interest_rate / 12
        n_m = loan_term_years * 12
        monthly_payment     = loan_amount * r_m / (1 - (1 + r_m) ** (-n_m))
        annual_debt_service = monthly_payment * 12
    else:
        annual_debt_service = 0.0

    ebit       = fish_ebitda - annual_depreciation
    nopat      = ebit * (1 - tax_rate)
    net_income = nopat - (annual_debt_service - annual_depreciation * (1 - tax_rate))

    dscr = fish_ebitda / annual_debt_service if annual_debt_service > 0 else None

    equity_invested = total_fish_capex * (1 - ltv)
    annual_fcfe     = fish_ebitda - annual_debt_service - annual_depreciation * tax_rate
    payback_years   = equity_invested / annual_fcfe if annual_fcfe > 0 and equity_invested > 0 else None

    dcf_cashflows  = []
    cumulative_npv = -equity_invested
    for yr in range(1, 11):
        pv = annual_fcfe / ((1 + discount_rate) ** yr)
        cumulative_npv += pv
        dcf_cashflows.append({"year": yr, "fcfe": annual_fcfe, "pv": pv, "cumulative_npv": cumulative_npv})
    npv = cumulative_npv

    # ── SECTION 13 — NUTRIENT OUTPUT ─────────────────────────────────────────
    # Average standing biomass ≈ 50% of harvest biomass (stocking progression)
    avg_biomass_kg         = harvest_biomass_kg * 0.5
    daily_n_g_per_kg_fish  = sd["nutrient_output_per_kg_fish"]
    annual_n_output_g      = daily_n_g_per_kg_fish * avg_biomass_kg * 365

    return {
        # Identity
        "species":                  species_name,
        "tank_volume_m3":           tank_volume_m3,
        "system_scale":             system_scale,
        "ambient_temp_c":           ambient_temp,
        "target_temp_c":            target_temp_c,
        "delta_t":                  delta_t,
        "salmon_warning":           salmon_warning,
        # Production
        "harvest_biomass_kg":       harvest_biomass_kg,
        "fish_per_batch":           fish_per_batch,
        "kg_per_cycle":             kg_per_cycle,
        "cycles_per_year":          cycles_per_year,
        "annual_kg_fish":           annual_kg_fish,
        "effective_fish_price":     effective_fish_price,
        # Revenue & costs
        "annual_fish_revenue":      annual_fish_revenue,
        "annual_feed_cost":         annual_feed_cost,
        "annual_fingerling_cost":   annual_fingerling_cost,
        "annual_fish_energy_cost":  annual_fish_energy,
        "annual_fish_kwh":          annual_fish_kwh,
        "aeration_pump_kwh":        aeration_pump_kwh,
        "aeration_kwh":             aeration_kwh,
        "pump_kwh":                 pump_kwh,
        "heating_kwh":              heating_kwh,
        "annual_water_cost":        annual_water_cost,
        "annual_fish_labour_cost":  annual_fish_labour_cost,
        "annual_fish_labour_hours": annual_fish_labour_hours,
        "annual_fish_maintenance":  annual_fish_maintenance,
        "total_fish_costs":         total_fish_costs,
        "fish_ebitda":              fish_ebitda,
        "fish_ebitda_margin":       fish_ebitda_margin,
        # CAPEX
        "tank_capex":               tank_capex,
        "filtration_capex":         filtration_capex,
        "aeration_capex":           aeration_capex,
        "monitoring_capex":         monitoring_capex,
        "plumbing_capex":           plumbing_capex,
        "total_fish_capex":         total_fish_capex,
        # Financial
        "annual_depreciation":      annual_depreciation,
        "annual_debt_service":      annual_debt_service,
        "net_income":               net_income,
        "dscr":                     dscr,
        "payback_years":            payback_years,
        "npv":                      npv,
        "dcf_cashflows":            dcf_cashflows,
        "equity_invested":          equity_invested,
        # Nutrient link
        "annual_n_output_g":        annual_n_output_g,
    }


def calculate_aquaponics(inputs: dict) -> dict:
    """
    Combined aquaponics system: fish + plant.
    Mode: 'decoupled' or 'coupled' (from inputs["aquaponics_mode"]).
    Plant side runs through calculate_greenhouse() with nutrient override.
    Fish side runs through calculate_fish().
    Returns combined P&L and full breakdown.
    """
    mode = inputs.get("aquaponics_mode", "decoupled")

    # ── PLANT SIDE ────────────────────────────────────────────────────────────
    # Build plant inputs — everything from inputs prefixed "plant_" or shared
    plant_inputs = {
        "country":            inputs["country"],
        "crop":               inputs["plant_crop"],
        "crop_source":        inputs.get("plant_crop_source", "greenhouse"),
        "footprint":          inputs["plant_footprint"],
        "automation":         inputs["automation"],
        "price_scenario":     inputs.get("price_scenario", "base"),
        "price_override":     float(inputs.get("plant_price_override", 0.0)),
        "packaging_cost":     float(inputs.get("packaging_cost", 0.15)),
        "loss_rate":          float(inputs.get("loss_rate", 5.0)),
        "net_grow_factor":    float(inputs.get("net_grow_factor", 90.0)),
        "walkways_factor":    float(inputs.get("walkways_factor", 10.0)),
        "water_price":        float(inputs.get("water_price", 2.0)),
        "rent_monthly":       float(inputs.get("rent_monthly", 0.0)),
        "real_estate_capex":  float(inputs.get("real_estate_capex", 0.0)),
        "harvest_mode":       inputs.get("harvest_mode", "Single"),
        "depreciation_years": int(inputs.get("depreciation_years", 15)),
        "tax_rate":           float(inputs.get("tax_rate", 25.0)),
        "ltv":                float(inputs.get("ltv", 60.0)),
        "interest_rate":      float(inputs.get("interest_rate", 5.5)),
        "loan_term_years":    int(inputs.get("loan_term_years", 15)),
        "discount_rate":      float(inputs.get("discount_rate", 8.0)),
    }

    # Apply mode-specific plant modifications
    if mode == "coupled":
        # Coupled: yield reduced by efficiency factor, nutrient cost near zero
        coupled_efficiency = float(inputs.get("coupled_efficiency_factor", 0.88))
        # Pass yield multiplier as a special override key
        plant_inputs["_yield_multiplier"]    = coupled_efficiency
        plant_inputs["_nutrient_multiplier"] = 0.05   # near zero — fish waste covers it
    # Decoupled: nutrient cost reduced by offset fraction, applied post-calculation

    # Run greenhouse engine
    plant_r = _calculate_greenhouse_with_overrides(plant_inputs)

    # Apply decoupled nutrient offset post-calculation
    nutrient_offset_saving = 0.0
    if mode == "decoupled":
        offset_fraction     = COUPLING_PARAMS["decoupled_nutrient_offset_fraction"]["base"]
        # nutrient cost is embedded in annual_variable_cost; isolate it
        # We re-derive it from plant inputs and crop data
        crop_source = plant_inputs.get("crop_source", "greenhouse").lower()
        crop_dict   = POLYTUNNEL_CROPS if crop_source == "polytunnel" else GREENHOUSE_CROPS
        if plant_inputs["crop"] in crop_dict:
            crop_data = crop_dict[plant_inputs["crop"]]
            ega       = plant_r["effective_grow_area"]
            cyc       = plant_r["cycles_per_year"]
            raw_nutrient_cost = crop_data["nutrient"] * ega * cyc
            nutrient_offset_saving = raw_nutrient_cost * offset_fraction
        # Adjust plant EBITDA
        plant_r = dict(plant_r)
        plant_r["annual_variable_cost"] = plant_r["annual_variable_cost"] - nutrient_offset_saving
        plant_r["total_annual_costs"]   = plant_r["total_annual_costs"]   - nutrient_offset_saving
        plant_r["ebitda"]               = plant_r["ebitda"]               + nutrient_offset_saving
        plant_r["ebitda_margin"]        = (plant_r["ebitda"] / plant_r["annual_revenue"]
                                           if plant_r["annual_revenue"] > 0 else 0.0)

    # ── FISH SIDE ─────────────────────────────────────────────────────────────
    fish_inputs = {
        "species":               inputs["species"],
        "tank_volume_m3":        inputs["tank_volume_m3"],
        "system_scale":          inputs["system_scale"],
        "country":               inputs["country"],
        "automation":            inputs["automation"],
        "price_scenario":        inputs.get("fish_price_scenario", "base"),
        "price_override_fish":   float(inputs.get("price_override_fish", 0.0)),
        "water_price":           float(inputs.get("water_price", 2.0)),
        "target_temp_c":         float(inputs.get("target_temp_c", 26.0)),
        "fish_depreciation_years": int(inputs.get("fish_depreciation_years", 10)),
        "tax_rate":              float(inputs.get("tax_rate", 25.0)),
        "ltv":                   float(inputs.get("ltv", 60.0)),
        "interest_rate":         float(inputs.get("interest_rate", 5.5)),
        "loan_term_years":       int(inputs.get("loan_term_years", 15)),
        "discount_rate":         float(inputs.get("discount_rate", 8.0)),
    }

    # Coupled mode: warn if salmon is selected
    if mode == "coupled" and inputs.get("species") in SALMON_WARNING_SPECIES:
        fish_inputs["target_temp_c"] = SALMON_OPTIMAL_TEMP_MAX  # force to safe temp

    fish_r = calculate_fish(fish_inputs, mode=mode)

    # ── INTEGRATION CAPEX ─────────────────────────────────────────────────────
    # greenhouse_integration_cost_per_m2 — piping, distribution from fish to plant
    capex_data          = AQUAPONICS_CAPEX[mode][inputs["system_scale"]]
    integration_capex   = capex_data["greenhouse_integration_cost_per_m2"] * float(inputs["plant_footprint"]) * capex_data["installation_factor"]

    # ── COMBINED FINANCIALS ───────────────────────────────────────────────────
    combined_revenue   = plant_r["annual_revenue"]  + fish_r["annual_fish_revenue"]
    combined_ebitda    = plant_r["ebitda"]           + fish_r["fish_ebitda"]
    combined_capex     = plant_r["total_capex"]      + fish_r["total_fish_capex"] + integration_capex
    combined_costs     = plant_r["total_annual_costs"] + fish_r["total_fish_costs"]
    combined_margin    = combined_ebitda / combined_revenue if combined_revenue > 0 else 0.0

    # Validate fish-to-plant ratio
    fish_biomass_per_m2 = fish_r["harvest_biomass_kg"] / float(inputs["plant_footprint"])
    ratio_warning = None
    if fish_biomass_per_m2 < COUPLING_PARAMS["min_fish_to_plant_ratio_kg_per_m2"]:
        ratio_warning = (
            f"⚠️ Fish-to-plant ratio ({fish_biomass_per_m2:.1f} kg/m²) is below the minimum "
            f"viable threshold of {COUPLING_PARAMS['min_fish_to_plant_ratio_kg_per_m2']:.0f} kg/m². "
            f"Nutrient offset will be negligible. Increase tank volume or reduce plant footprint."
        )

    return {
        "mode":                    mode,
        "plant":                   plant_r,
        "fish":                    fish_r,
        # Combined
        "combined_revenue":        combined_revenue,
        "combined_ebitda":         combined_ebitda,
        "combined_ebitda_margin":  combined_margin,
        "combined_capex":          combined_capex,
        "combined_costs":          combined_costs,
        "integration_capex":       integration_capex,
        "nutrient_offset_saving":  nutrient_offset_saving,
        # Warnings
        "ratio_warning":           ratio_warning,
        "salmon_warning":          fish_r["salmon_warning"],
        # Nutrient link
        "annual_n_output_g":       fish_r["annual_n_output_g"],
        "fish_biomass_per_m2":     fish_biomass_per_m2,
    }


def _calculate_greenhouse_with_overrides(plant_inputs: dict) -> dict:
    """
    Calls calculate_greenhouse() with optional yield and nutrient multipliers
    for coupled aquaponics mode. Multipliers are popped before passing to
    calculate_greenhouse() — the function signature is not changed.
    """
    yield_mult     = plant_inputs.pop("_yield_multiplier", 1.0)
    nutrient_mult  = plant_inputs.pop("_nutrient_multiplier", 1.0)

    if yield_mult == 1.0 and nutrient_mult == 1.0:
        return calculate_greenhouse(plant_inputs)

    # Apply yield multiplier via temporary crop patch
    import core.greenhouse_data_tables as _ghdt

    crop_source = plant_inputs.get("crop_source", "greenhouse").lower()
    crop_dict   = _ghdt.POLYTUNNEL_CROPS if crop_source == "polytunnel" else _ghdt.GREENHOUSE_CROPS
    crop_name   = plant_inputs["crop"]

    if crop_name not in crop_dict:
        _fallback = _ghdt.GREENHOUSE_CROPS if crop_source == "polytunnel" else _ghdt.POLYTUNNEL_CROPS
        if crop_name in _fallback:
            crop_dict   = _fallback
            crop_source = "greenhouse" if crop_source == "polytunnel" else "polytunnel"
        elif crop_name not in crop_dict:
            crop_name   = list(crop_dict.keys())[0]

    # Sync plant_inputs to the resolved crop and source so calculate_greenhouse()
    # looks in the correct dict
    plant_inputs["crop"]        = crop_name
    plant_inputs["crop_source"] = crop_source

    original_crop = crop_dict[crop_name]
    modified_crop = copy.deepcopy(original_crop)
    modified_crop["yield"]    = original_crop["yield"]    * yield_mult
    modified_crop["yield_h2"] = original_crop["yield_h2"] * yield_mult
    modified_crop["yield_h3"] = original_crop["yield_h3"] * yield_mult
    modified_crop["nutrient"] = original_crop["nutrient"] * nutrient_mult

    crop_dict[crop_name] = modified_crop
    try:
        result = calculate_greenhouse(plant_inputs)
    finally:
        crop_dict[crop_name] = original_crop

    return result
