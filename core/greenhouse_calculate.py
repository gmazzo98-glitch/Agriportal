import math
from core.greenhouse_data_tables import GREENHOUSE_CROPS, POLYTUNNEL_CROPS, GREENHOUSE_CAPEX
from core.data_tables import COUNTRIES
from core.greenhouse_data_tables import GREENHOUSE_LABOUR_TASKS, GREENHOUSE_AUTO_COL


def calculate_greenhouse(inputs: dict) -> dict:

    # ── SECTION 1 — UNPACK INPUTS ─────────────────────────────────────────────
    country           = inputs["country"]
    crop_name         = inputs["crop"]
    crop_source       = inputs["crop_source"]       # "greenhouse" or "polytunnel"
    footprint         = float(inputs["footprint"])
    automation        = inputs["automation"]
    price_scenario    = inputs["price_scenario"]
    price_override    = float(inputs.get("price_override", 0.0))
    packaging_cost    = float(inputs.get("packaging_cost", 0.15))
    loss_rate         = float(inputs.get("loss_rate", 5.0)) / 100
    net_grow_factor   = float(inputs.get("net_grow_factor", 90.0)) / 100
    walkways_factor   = float(inputs.get("walkways_factor", 10.0)) / 100
    water_price       = float(inputs.get("water_price", 2.0))
    rent_monthly      = float(inputs.get("rent_monthly", 0.0))
    real_estate_capex = float(inputs.get("real_estate_capex", 0.0))
    harvest_mode      = inputs.get("harvest_mode", "Single")
    depreciation_years = int(inputs.get("depreciation_years", 15))
    tax_rate          = float(inputs.get("tax_rate", 25.0)) / 100
    ltv               = float(inputs.get("ltv", 60.0)) / 100
    interest_rate     = float(inputs.get("interest_rate", 5.5)) / 100
    loan_term_years   = int(inputs.get("loan_term_years", 15))
    discount_rate     = float(inputs.get("discount_rate", 8.0)) / 100

    # Climate data — populated from Open-Meteo when a farm location is known.
    # Falls back to crop's static natural_dli_fraction when not available.
    ambient_temp_override = inputs.get("ambient_temp_annual")   # °C or None
    mean_annual_dli       = inputs.get("mean_annual_dli")       # mol/m²/day or None

    # ── SECTION 2 — LOAD CROP AND COUNTRY DATA ────────────────────────────────
    if crop_source == "polytunnel":
        crop = POLYTUNNEL_CROPS[crop_name]
    else:
        crop = GREENHOUSE_CROPS[crop_name]

    country_data = COUNTRIES[country]
    elec_price   = country_data["kwh"]     # $/kWh
    labour_rate  = country_data["labour"]  # $/hour

    # ── SECTION 3 — GEOMETRY ─────────────────────────────────────────────────
    # Greenhouses have no levels
    gross_area          = footprint
    effective_grow_area = footprint * net_grow_factor * (1 - walkways_factor)

    # ── SECTION 4 — HARVEST CYCLES AND YIELD ─────────────────────────────────
    # Step 4a — effective cycle days
    if harvest_mode == "2 Harvests" and crop["days_between"] > 0:
        effective_cycle_days = crop["cycle"] + crop["days_between"]
    elif harvest_mode == "3 Harvests" and crop["days_between"] > 0:
        effective_cycle_days = crop["cycle"] + 2 * crop["days_between"]
    else:
        effective_cycle_days = crop["cycle"]

    # Step 4b — cycles per year
    cycles_per_year = max(math.floor(365 / effective_cycle_days), 1)

    # Step 4c — yield per cycle per m²
    if harvest_mode == "2 Harvests":
        yield_per_cycle = crop["yield"] + crop["yield_h2"]
    elif harvest_mode == "3 Harvests":
        yield_per_cycle = crop["yield"] + crop["yield_h2"] + crop["yield_h3"]
    else:
        yield_per_cycle = crop["yield"]

    # Step 4d — total annual saleable kg
    total_annual_kg = (
        yield_per_cycle
        * effective_grow_area
        * cycles_per_year
        * (1 - loss_rate)
    )

    # ── SECTION 5 — SELLING PRICE ─────────────────────────────────────────────
    if price_override > 0:
        effective_price = price_override
    elif price_scenario == "low":
        effective_price = crop["price_low"]
    elif price_scenario == "high":
        effective_price = crop["price_high"]
    else:
        effective_price = crop["price_base"]

    annual_revenue = total_annual_kg * effective_price

    # ── SECTION 6 — ENERGY COST ───────────────────────────────────────────────
    # Supplemental lighting covers only the DLI fraction not met by natural light.
    # Polytunnel crops have natural_dli_fraction = 1.0 → supplemental_dli = 0.
    total_dli = crop["dli"]                                  # mol/m²/day
    if mean_annual_dli is not None and total_dli > 0:
        # Location-aware: fraction of DLI met by natural light at this farm's coordinates
        nat_frac = min(1.0, mean_annual_dli / total_dli)
    else:
        # Fall back to crop's static natural_dli_fraction (Northern Europe default)
        nat_frac = crop["natural_dli_fraction"]
    supplemental_dli = total_dli * (1 - nat_frac)            # mol/m²/day

    # 1 mol PAR ≈ 0.0216 kWh (46 W/mol efficacy for HPS/LED hybrid)
    operating_days        = min(365, effective_cycle_days * cycles_per_year)
    lighting_kwh_m2_year  = supplemental_dli * 0.0216 * operating_days

    # Climate energy: heating/ventilation as fraction of lighting energy
    # Greenhouses are far more efficient than VF — factor 0.35
    climate_kwh_m2_year   = lighting_kwh_m2_year * 0.35

    total_kwh_m2_year     = lighting_kwh_m2_year + climate_kwh_m2_year
    annual_kwh            = total_kwh_m2_year * effective_grow_area
    annual_energy_cost    = annual_kwh * elec_price

    # ── SECTION 7 — VARIABLE COSTS ────────────────────────────────────────────
    annual_seed_cost      = crop["seed"]      * effective_grow_area * cycles_per_year
    annual_substrate_cost = crop["substrate"] * effective_grow_area * cycles_per_year
    annual_nutrient_cost  = crop["nutrient"]  * effective_grow_area * cycles_per_year
    annual_packaging_cost = packaging_cost * total_annual_kg
    annual_variable_cost  = (
        annual_seed_cost
        + annual_substrate_cost
        + annual_nutrient_cost
        + annual_packaging_cost
    )

    # ── SECTION 8 — WATER COST ────────────────────────────────────────────────
    # crop["water"] is L/m²/cycle — convert to m³
    annual_water_m3   = (crop["water"] / 1000) * effective_grow_area * cycles_per_year
    annual_water_cost = annual_water_m3 * water_price

    # ── SECTION 9 — LABOUR COST ───────────────────────────────────────────────
    auto_idx = GREENHOUSE_AUTO_COL[automation]

    per_harvest_tasks = [
        "seeding", "germination", "transplanting", "internal_movement",
        "harvest", "post_harvest", "washing", "drying", "packaging",
        "waste_handling",
    ]
    harvest_minutes_per_cycle = 0.0
    for task in per_harvest_tasks:
        row = GREENHOUSE_LABOUR_TASKS[task]
        base_min = row[0]
        factor   = row[auto_idx]
        harvest_minutes_per_cycle += base_min * factor

    annual_harvest_hours = (
        harvest_minutes_per_cycle / 60
        * (effective_grow_area / 100)
        * cycles_per_year
    )

    weekly_tasks = [
        "nutrient_mixing", "water_checks", "climate_mon", "sensor_cal",
        "cleaning", "quality_ctrl", "ipm_scouting", "preventive_maint", "admin",
    ]
    weekly_minutes = 0.0
    for task in weekly_tasks:
        row = GREENHOUSE_LABOUR_TASKS[task]
        base_min = row[0]
        factor   = row[auto_idx]
        weekly_minutes += base_min * factor

    annual_monitoring_hours = (
        weekly_minutes / 60
        * (effective_grow_area / 100)
        * 52
    )

    annual_labour_hours = annual_harvest_hours + annual_monitoring_hours
    annual_labour_cost  = annual_labour_hours * labour_rate

    # ── SECTION 10 — CAPEX ────────────────────────────────────────────────────
    structure_map = {
        "venlo":      "Venlo",
        "multi-span": "Multi-span",
        "polytunnel": "Polytunnel",
    }
    structure_key      = structure_map.get(crop["structure_type"], "Multi-span")
    capex_data         = GREENHOUSE_CAPEX[structure_key]
    inst_factor        = capex_data["installation_factor"]

    structure_capex    = capex_data["structure_cost_per_m2"] * footprint * inst_factor
    climate_capex      = capex_data["climate_system_per_m2"] * footprint * inst_factor
    irrigation_capex   = capex_data["irrigation_per_m2"]     * footprint * inst_factor
    lighting_capex     = capex_data["lighting_per_m2"]       * footprint * inst_factor
    automation_capex   = capex_data["automation_per_m2"]     * footprint * inst_factor
    real_estate_capex_val = real_estate_capex

    total_capex = (
        structure_capex
        + climate_capex
        + irrigation_capex
        + lighting_capex
        + automation_capex
        + real_estate_capex_val
    )

    # ── SECTION 11 — OPEX TOTALS AND EBITDA ──────────────────────────────────
    annual_rent        = rent_monthly * 12
    annual_maintenance = total_capex * 0.02     # 2% of CAPEX per year

    total_annual_costs = (
        annual_energy_cost
        + annual_variable_cost
        + annual_water_cost
        + annual_labour_cost
        + annual_rent
        + annual_maintenance
    )

    ebitda        = annual_revenue - total_annual_costs
    ebitda_margin = ebitda / annual_revenue if annual_revenue > 0 else 0.0

    # ── SECTION 12 — DEPRECIATION, DEBT SERVICE, DSCR ────────────────────────
    annual_depreciation = total_capex / depreciation_years

    loan_amount = total_capex * ltv
    if loan_amount > 0 and interest_rate > 0:
        r_m = interest_rate / 12
        n_m = loan_term_years * 12
        monthly_payment     = loan_amount * r_m / (1 - (1 + r_m) ** (-n_m))
        annual_debt_service = monthly_payment * 12
    else:
        annual_debt_service = 0.0

    ebit       = ebitda - annual_depreciation
    nopat      = ebit * (1 - tax_rate)
    net_income = nopat - (annual_debt_service - annual_depreciation * (1 - tax_rate))

    dscr = (ebitda / annual_debt_service) if annual_debt_service > 0 else None

    # ── SECTION 13 — PAYBACK PERIOD ───────────────────────────────────────────
    equity_invested = total_capex * (1 - ltv)
    annual_fcfe     = ebitda - annual_debt_service - annual_depreciation * tax_rate

    if annual_fcfe > 0 and equity_invested > 0:
        payback_years = equity_invested / annual_fcfe
    else:
        payback_years = None

    # ── SECTION 14 — 10-YEAR DCF ──────────────────────────────────────────────
    dcf_cashflows  = []
    cumulative_npv = -equity_invested

    for yr in range(1, 11):
        fcfe = annual_fcfe
        pv   = fcfe / ((1 + discount_rate) ** yr)
        cumulative_npv += pv
        dcf_cashflows.append({
            "year":           yr,
            "fcfe":           fcfe,
            "pv":             pv,
            "cumulative_npv": cumulative_npv,
        })

    npv = cumulative_npv

    # ── SECTION 15 — RETURN DICT ──────────────────────────────────────────────
    return {
        # Geometry
        "gross_area":             gross_area,
        "effective_grow_area":    effective_grow_area,
        # Production
        "cycles_per_year":        cycles_per_year,
        "effective_cycle_days":   effective_cycle_days,
        "harvest_mode":           harvest_mode,
        "yield_per_cycle":        yield_per_cycle,
        "total_annual_kg":        total_annual_kg,
        # Prices
        "effective_price":        effective_price,
        # Revenue
        "annual_revenue":         annual_revenue,
        # Costs
        "annual_energy_cost":     annual_energy_cost,
        "annual_variable_cost":   annual_variable_cost,
        "annual_water_cost":      annual_water_cost,
        "annual_labour_cost":     annual_labour_cost,
        "annual_rent":            annual_rent,
        "annual_maintenance":     annual_maintenance,
        "total_annual_costs":     total_annual_costs,
        # Labour detail
        "annual_labour_hours":    annual_labour_hours,
        # Energy detail
        "annual_kwh":             annual_kwh,
        "lighting_kwh_m2_year":   lighting_kwh_m2_year,
        "supplemental_dli":       supplemental_dli,
        # EBITDA
        "ebitda":                 ebitda,
        "ebitda_margin":          ebitda_margin,
        # CAPEX
        "structure_capex":        structure_capex,
        "climate_capex":          climate_capex,
        "irrigation_capex":       irrigation_capex,
        "lighting_capex":         lighting_capex,
        "automation_capex":       automation_capex,
        "real_estate_capex":      real_estate_capex_val,
        "total_capex":            total_capex,
        "structure_type":         structure_key,
        # Financial
        "annual_depreciation":    annual_depreciation,
        "annual_debt_service":    annual_debt_service,
        "net_income":             net_income,
        "dscr":                   dscr,
        "payback_years":          payback_years,
        "npv":                    npv,
        "dcf_cashflows":          dcf_cashflows,
        "equity_invested":        equity_invested,
    }
