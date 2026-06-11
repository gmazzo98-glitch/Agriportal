import math
from core.data_tables import (
    LIGHTS, HVAC_FACTORS, AUTOMATION_CAPEX,
    task_rate, COUNTRIES, CROPS
)


def calculate(inputs: dict) -> dict:
    country_name       = inputs["country"]
    footprint          = inputs.get("footprint", 1000)
    levels             = inputs.get("levels", 5)
    crop_name          = inputs["crop"]
    lights_tier        = inputs["lights_tier"]
    hvac_key           = inputs["hvac"]
    automation         = inputs["automation"]
    price_scenario     = inputs["price_scenario"]
    price_override     = inputs.get("price_override", 0)
    packaging_cost     = inputs.get("packaging_cost", 0.15)
    loss_rate          = inputs.get("loss_rate", 5) / 100
    net_grow_factor    = inputs.get("net_grow_factor", 85) / 100
    walkways_factor    = inputs.get("walkways_factor", 15) / 100
    water_price        = inputs.get("water_price", 2)
    rent_monthly       = inputs.get("rent_monthly", 0)
    real_estate_capex  = inputs.get("real_estate_capex", 0)
    harvest_mode       = inputs.get("harvest_mode", "Single")
    depreciation_years = inputs.get("depreciation_years", 10)
    tax_rate           = inputs.get("tax_rate", 25) / 100
    ltv                = inputs.get("ltv", 60) / 100
    interest_rate      = inputs.get("interest_rate", 5.5) / 100
    loan_term_years    = inputs.get("loan_term_years", 10)

    country = COUNTRIES[country_name]
    crop    = CROPS[crop_name]
    lights  = LIGHTS[lights_tier]

    # ── Step 1: Geometry ──────────────────────────────────────────────────────
    gross_area          = footprint * levels
    effective_grow_area = footprint * levels * net_grow_factor * (1 - walkways_factor)

    # ── Step 2: Multi-harvest cycle ───────────────────────────────────────────
    has_h2 = (harvest_mode in ("2 Harvests", "3 Harvests")) and crop["days_between"] > 0
    has_h3 = (harvest_mode == "3 Harvests") and crop["days_between"] > 0
    gap_h2 = crop["days_between"] if has_h2 else 0
    gap_h3 = crop["days_between"] * 1.15 if has_h3 else 0
    effective_cycle_days = round(crop["cycle"] + gap_h2 + gap_h3)
    cycles_per_year      = math.floor(360 / effective_cycle_days)

    # ── Step 3: Yield ─────────────────────────────────────────────────────────
    yield_h1               = crop["yield"]
    yield_h2               = crop["yield_h2"] * yield_h1 if has_h2 else 0
    yield_h3               = crop["yield_h3"] * yield_h1 if has_h3 else 0
    total_yield_per_cycle  = yield_h1 + yield_h2 + yield_h3
    yield_after_loss       = total_yield_per_cycle * (1 - loss_rate)
    total_annual_kg        = yield_after_loss * cycles_per_year * effective_grow_area
    total_production_gross = total_yield_per_cycle * cycles_per_year * effective_grow_area

    # ── Step 4: Revenue ───────────────────────────────────────────────────────
    if price_override > 0:
        effective_price = price_override
    else:
        effective_price = crop[f"price_{price_scenario}"] * country["food_index"]
    annual_revenue = total_annual_kg * effective_price

    # ── Step 5: Energy ────────────────────────────────────────────────────────
    daily_kwh_per_m2     = crop["dli"] * 0.2778 / lights["efficacy"]
    hvac_factor          = HVAC_FACTORS[hvac_key]
    kwh_per_m2_per_cycle = daily_kwh_per_m2 * effective_cycle_days * hvac_factor
    annual_kwh_per_m2    = kwh_per_m2_per_cycle * cycles_per_year
    total_annual_kwh     = annual_kwh_per_m2 * effective_grow_area
    annual_energy_cost   = total_annual_kwh * country["kwh"]

    # ── Step 6: Variable costs ────────────────────────────────────────────────
    nutrient_per_m2_cycle  = crop["ec"] * crop["water"] * crop["nutrient"]
    packaging_per_m2_cycle = packaging_cost * yield_after_loss
    variable_per_m2_cycle  = (crop["seed"] + crop["substrate"]
                               + packaging_per_m2_cycle + nutrient_per_m2_cycle)
    annual_variable_cost   = variable_per_m2_cycle * cycles_per_year * effective_grow_area

    # ── Step 7: Water cost ────────────────────────────────────────────────────
    water_m3_per_kg    = (crop["wf"] + crop["tr"] * 1) / 1000  # recovery=0
    annual_water_cost  = water_m3_per_kg * water_price * total_production_gross

    # ── Step 8: Labour ────────────────────────────────────────────────────────
    trays         = math.floor(effective_grow_area / 7.75)
    harvest_count = 3 if has_h3 else (2 if has_h2 else 1)
    waste_kg      = total_production_gross - total_annual_kg
    ega           = effective_grow_area

    m_seeding      = task_rate("seeding", automation)           * trays * cycles_per_year
    m_germination  = task_rate("germination", automation)       * trays * cycles_per_year
    m_transplant   = task_rate("transplanting", automation)     * trays * cycles_per_year
    m_movement     = task_rate("internal_movement", automation) * trays * cycles_per_year
    m_harvest      = task_rate("harvest", automation)           * trays * harvest_count * cycles_per_year
    m_post_harv    = task_rate("post_harvest", automation)      * total_production_gross
    m_washing      = 0
    m_drying       = 0
    m_packaging    = task_rate("packaging", automation)         * total_annual_kg
    m_waste        = task_rate("waste_handling", automation)    * waste_kg
    m_nutrient     = task_rate("nutrient_mixing", automation)   * cycles_per_year
    m_water        = task_rate("water_checks", automation)      * cycles_per_year * effective_cycle_days
    m_climate      = task_rate("climate_mon", automation)       * cycles_per_year * effective_cycle_days
    m_sensor       = task_rate("sensor_cal", automation)        * 7.36 * (total_production_gross / 2_000_000) * 12
    m_cleaning     = task_rate("cleaning", automation)          * (ega / 100) * 365
    m_quality_ctrl = task_rate("quality_ctrl", automation)      * (ega / 100) * 365
    m_ipm_scouting = task_rate("ipm_scouting", automation)      * (ega / 100) * 365
    m_prev_maint   = task_rate("preventive_maint", automation)  * (ega / 100) * 52
    m_admin        = task_rate("admin", automation)             * 52

    total_task_minutes = (
        m_seeding + m_germination + m_transplant + m_movement +
        m_harvest + m_post_harv + m_washing + m_drying + m_packaging +
        m_waste + m_nutrient + m_water + m_climate + m_sensor +
        m_cleaning + m_quality_ctrl + m_ipm_scouting + m_prev_maint + m_admin
    )
    annual_labour_hours = total_task_minutes / 60
    annual_labour_cost  = annual_labour_hours * country["labour"]

    # ── Step 9: CAPEX ─────────────────────────────────────────────────────────
    base_levels = 6
    if levels <= base_levels:
        level_complexity = 1.0 - 0.05 * (base_levels - levels)
    else:
        level_complexity = 1.0 + 0.05 * (levels - base_levels)

    auto_capex       = AUTOMATION_CAPEX[automation]
    led_capex        = lights["capex_per_m2"] * effective_grow_area
    hvac_capex       = 170 * effective_grow_area
    racks_capex      = 140 * effective_grow_area * level_complexity
    max_levels_base  = 15
    building_cost_increase = 1 if levels <= max_levels_base else 1 + (levels - max_levels_base) * 0.025
    building_capex   = 350 * footprint * building_cost_increase
    automation_capex = 90  * gross_area * level_complexity * auto_capex["controls_mult"]
    robotics_capex   = 85  * gross_area * level_complexity * auto_capex["robotics_mult"]
    electrical_capex = 60  * gross_area * level_complexity
    water_capex      = 45  * effective_grow_area
    equipment_subtotal = (led_capex + hvac_capex + racks_capex + building_capex +
                          automation_capex + robotics_capex + electrical_capex + water_capex)
    # Installation: 10% of technical equipment subtotal (excluding building and real estate)
    # More precise than the flat €105/m² approximation which drifts when lighting or automation changes
    # equipment_subtotal is not yet defined at this point so we compute pre-installation subtotal first
    pre_install_subtotal = (led_capex + hvac_capex + racks_capex + building_capex +
                            automation_capex + robotics_capex + electrical_capex + water_capex)
    installation_capex = 0.10 * pre_install_subtotal
    total_capex        = equipment_subtotal + installation_capex
    total_capex_all_in = total_capex + real_estate_capex
    annual_maintenance = 0.03 * (equipment_subtotal - building_capex)

    # ── Step 10: EBITDA ───────────────────────────────────────────────────────
    annual_rent        = rent_monthly * 12
    total_annual_costs = (annual_variable_cost + annual_water_cost + annual_energy_cost +
                          annual_labour_cost + annual_maintenance + annual_rent)
    ebitda             = annual_revenue - total_annual_costs
    ebitda_margin      = ebitda / annual_revenue if annual_revenue > 0 else 0
    payback_years      = total_capex_all_in / ebitda if ebitda > 0 else None

    # ── Step 11: Financial structure ──────────────────────────────────────────
    depreciable_base    = equipment_subtotal - building_capex
    annual_depreciation = depreciable_base / depreciation_years
    ebit                = ebitda - annual_depreciation
    debt_amount         = total_capex_all_in * ltv
    equity_amount       = total_capex_all_in - debt_amount
    monthly_rate        = interest_rate / 12
    n_payments          = int(loan_term_years * 12)
    if debt_amount > 0 and monthly_rate > 0:
        monthly_ds = debt_amount * (monthly_rate * (1 + monthly_rate) ** n_payments) / ((1 + monthly_rate) ** n_payments - 1)
    else:
        monthly_ds = 0
    annual_debt_service    = monthly_ds * 12
    annual_interest_year1  = debt_amount * interest_rate
    annual_principal_year1 = annual_debt_service - annual_interest_year1
    ebt                    = ebit - annual_interest_year1
    tax_charge             = max(0, ebt * tax_rate)
    net_income             = ebt - tax_charge
    dscr                   = ebitda / annual_debt_service if annual_debt_service > 0 else None

    # ── Step 12: DCF (10-year) ────────────────────────────────────────────────
    discount_rate = interest_rate + 0.05
    npv           = -equity_amount
    dcf_cashflows = [{"year": 0, "fcfe": -equity_amount, "pv": -equity_amount, "cumulative_npv": -equity_amount}]
    for yr in range(1, 11):
        fcfe = net_income + annual_depreciation - annual_principal_year1
        pv   = fcfe / (1 + discount_rate) ** yr
        npv += pv
        dcf_cashflows.append({"year": yr, "fcfe": fcfe, "pv": pv, "cumulative_npv": npv})

    return {
        "gross_area":            gross_area,
        "effective_grow_area":   effective_grow_area,
        "cycles_per_year":       cycles_per_year,
        "effective_cycle_days":  effective_cycle_days,
        "total_annual_kg":       total_annual_kg,
        "total_production_gross": total_production_gross,
        "effective_price":       effective_price,
        "annual_revenue":        annual_revenue,
        "annual_energy_cost":    annual_energy_cost,
        "annual_variable_cost":  annual_variable_cost,
        "annual_water_cost":     annual_water_cost,
        "annual_labour_cost":    annual_labour_cost,
        "annual_maintenance":    annual_maintenance,
        "annual_rent":           annual_rent,
        "total_annual_costs":    total_annual_costs,
        "ebitda":                ebitda,
        "ebitda_margin":         ebitda_margin,
        "payback_years":         payback_years,
        "total_capex":           total_capex_all_in,
        "equipment_subtotal":    equipment_subtotal,
        "led_capex":             led_capex,
        "hvac_capex":            hvac_capex,
        "racks_capex":           racks_capex,
        "building_capex":        building_capex,
        "automation_capex":      automation_capex,
        "robotics_capex":        robotics_capex,
        "electrical_capex":      electrical_capex,
        "water_capex":           water_capex,
        "installation_capex":    installation_capex,
        "annual_labour_hours":   annual_labour_hours,
        "total_annual_kwh":      total_annual_kwh,
        "annual_depreciation":   annual_depreciation,
        "ebit":                  ebit,
        "net_income":            net_income,
        "tax_charge":            tax_charge,
        "debt_amount":           debt_amount,
        "annual_debt_service":   annual_debt_service,
        "dscr":                  dscr,
        "dcf_cashflows":         dcf_cashflows,
        "npv":                   npv,
        "harvest_mode":          harvest_mode,
        "harvest_count":         harvest_count,
    }
