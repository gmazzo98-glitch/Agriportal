import math

# ─────────────────────────────────────────────────────────────────────────────
# LIGHTS
# ─────────────────────────────────────────────────────────────────────────────
LIGHTS = {
    "Cheap":    {"efficacy": 2.3, "capex_per_m2": 110},
    "Basic":    {"efficacy": 2.7, "capex_per_m2": 170},
    "Top-Tier": {"efficacy": 3.2, "capex_per_m2": 260},
}

# ─────────────────────────────────────────────────────────────────────────────
# HVAC FACTORS
# Derivation: 1 + 0.18 + 0.65 x hvac_severity
# Excellent=0.8 -> 1.70, Standard=1.0 -> 1.83, High=1.3 -> 2.025
# ─────────────────────────────────────────────────────────────────────────────
HVAC_FACTORS = {
    "Excellent conditions": 1.70,
    "Standard":             1.83,
    "High HVAC":            2.025,
}

# ─────────────────────────────────────────────────────────────────────────────
# AUTOMATION CAPEX MULTIPLIERS
# ─────────────────────────────────────────────────────────────────────────────
AUTOMATION_CAPEX = {
    "None":   {"controls_mult": 1.0,  "robotics_mult": 1.0},
    "Low":    {"controls_mult": 1.15, "robotics_mult": 1.25},
    "Medium": {"controls_mult": 1.35, "robotics_mult": 1.6},
    "High":   {"controls_mult": 1.6,  "robotics_mult": 2.1},
}

# ─────────────────────────────────────────────────────────────────────────────
# LABOUR TASKS
# Format: [base_min, none_factor, low_factor, med_factor, high_factor]
# AUTO_COL index: None=1, Low=2, Medium=3, High=4
# ─────────────────────────────────────────────────────────────────────────────
LABOUR_TASKS = {
    "seeding":           [1.2,  1, 0.90, 0.60, 0.30],
    "germination":       [0.5,  1, 0.95, 0.75, 0.50],
    "transplanting":     [1.5,  1, 0.90, 0.70, 0.40],
    "internal_movement": [0.6,  1, 0.90, 0.60, 0.30],
    "harvest":           [0.6,  1, 0.95, 0.85, 0.65],
    "post_harvest":      [0.33, 1, 0.95, 0.80, 0.55],
    "washing":           [2.0,  1, 1.00, 0.85, 0.70],
    "drying":            [1.0,  1, 0.95, 0.80, 0.60],
    "packaging":         [0.8,  1, 0.95, 0.75, 0.45],
    "waste_handling":    [0.5,  1, 1.00, 0.90, 0.80],
    "nutrient_mixing":   [45,   1, 0.85, 0.60, 0.40],
    "water_checks":      [30,   1, 0.85, 0.60, 0.40],
    "climate_mon":       [25,   1, 0.80, 0.55, 0.35],
    "sensor_cal":        [12,   1, 0.95, 0.90, 0.85],
    "cleaning":          [10,   1, 1.00, 0.90, 0.80],
    "quality_ctrl":      [4,    1, 1.00, 0.90, 0.85],
    "ipm_scouting":      [40,   1, 1.00, 0.90, 0.85],
    "preventive_maint":  [60,   1, 1.00, 1.05, 1.10],
    "admin":             [240,  1, 0.95, 0.90, 0.85],
}

AUTO_COL = {"None": 1, "Low": 2, "Medium": 3, "High": 4}

def task_rate(task: str, automation: str) -> float:
    t = LABOUR_TASKS[task]
    return t[0] * t[AUTO_COL[automation]]

# ─────────────────────────────────────────────────────────────────────────────
# COUNTRIES (46 total)
# ─────────────────────────────────────────────────────────────────────────────
COUNTRY_CODE_MAP = {
    "AT": "Austria",
    "AU": "Australia",
    "BE": "Belgium",
    "BH": "Bahrain",
    "BR": "Brazil",
    "CA": "Canada",
    "CH": "Switzerland",
    "CL": "Chile",
    "CN": "China",
    "CO": "Colombia",
    "DE": "Germany",
    "DK": "Denmark",
    "EG": "Egypt",
    "ES": "Spain",
    "FI": "Finland",
    "FR": "France",
    "GB": "United Kingdom",
    "GR": "Greece",
    "ID": "Indonesia",
    "IL": "Israel",
    "IN": "India",
    "IT": "Italy",
    "JP": "Japan",
    "KR": "South Korea",
    "KW": "Kuwait",
    "MA": "Morocco",
    "MX": "Mexico",
    "MY": "Malaysia",
    "NL": "Netherlands",
    "NO": "Norway",
    "NZ": "New Zealand",
    "OM": "Oman",
    "PL": "Poland",
    "PT": "Portugal",
    "QA": "Qatar",
    "SA": "Saudi Arabia",
    "SE": "Sweden",
    "SG": "Singapore",
    "TH": "Thailand",
    "TW": "Taiwan",
    "AE": "United Arab Emirates",
    "US": "United States",
    "VN": "Vietnam",
    "ZA": "South Africa",
    "MX": "Mexico",
    "AR": "Argentina",
}

COUNTRIES = {
    "Germany":              {"kwh": 0.40, "labour": 51.212,  "food_index": 1.00},
    "France":               {"kwh": 0.28, "labour": 51.566,  "food_index": 1.02},
    "Italy":                {"kwh": 0.42, "labour": 36.462,  "food_index": 0.95},
    "Spain":                {"kwh": 0.25, "labour": 30.09,   "food_index": 0.90},
    "Netherlands":          {"kwh": 0.29, "labour": 53.336,  "food_index": 1.05},
    "Denmark":              {"kwh": 0.36, "labour": 59.118,  "food_index": 1.20},
    "Sweden":               {"kwh": 0.23, "labour": 47.554,  "food_index": 1.10},
    "Norway":               {"kwh": 0.15, "labour": 63.366,  "food_index": 1.35},
    "Finland":              {"kwh": 0.18, "labour": 44.486,  "food_index": 1.05},
    "Switzerland":          {"kwh": 0.36, "labour": 82.706,  "food_index": 1.30},
    "Austria":              {"kwh": 0.34, "labour": 52.51,   "food_index": 1.05},
    "Belgium":              {"kwh": 0.40, "labour": 56.876,  "food_index": 1.05},
    "United Kingdom":       {"kwh": 0.40, "labour": 26.7512, "food_index": 1.05},
    "Ireland":              {"kwh": 0.44, "labour": 50.15,   "food_index": 1.10},
    "Poland":               {"kwh": 0.23, "labour": 20.414,  "food_index": 0.75},
    "Czech Republic":       {"kwh": 0.35, "labour": 21.476,  "food_index": 0.80},
    "United States":        {"kwh": 0.18, "labour": 45.65,   "food_index": 0.95},
    "Canada":               {"kwh": 0.12, "labour": 27.0538, "food_index": 1.00},
    "Mexico":               {"kwh": 0.11, "labour": 4.8252,  "food_index": 0.55},
    "Brazil":               {"kwh": 0.16, "labour": 3.9596,  "food_index": 0.60},
    "Chile":                {"kwh": 0.21, "labour": 9.2885,  "food_index": 0.80},
    "Argentina":            {"kwh": 0.08, "labour": 7.6273,  "food_index": 0.50},
    "Colombia":             {"kwh": 0.20, "labour": 2.1354,  "food_index": 0.55},
    "United Arab Emirates": {"kwh": 0.08, "labour": 30.3615, "food_index": 1.35},
    "Saudi Arabia":         {"kwh": 0.05, "labour": 8.9424,  "food_index": 1.10},
    "Qatar":                {"kwh": 0.03, "labour": 19.5264, "food_index": 1.40},
    "Kuwait":               {"kwh": 0.04, "labour": 6.3896,  "food_index": 1.30},
    "Bahrain":              {"kwh": 0.05, "labour": 14.045,  "food_index": 1.20},
    "Oman":                 {"kwh": 0.03, "labour": 4.888,   "food_index": 1.15},
    "Israel":               {"kwh": 0.18, "labour": 21.8592, "food_index": 1.15},
    "Japan":                {"kwh": 0.23, "labour": 28.5185, "food_index": 1.20},
    "South Korea":          {"kwh": 0.13, "labour": 18.039,  "food_index": 1.05},
    "Taiwan":               {"kwh": 0.10, "labour": 11.1767, "food_index": 0.95},
    "China":                {"kwh": 0.08, "labour": 8.65,    "food_index": 0.70},
    "Singapore":            {"kwh": 0.23, "labour": 29.3011, "food_index": 1.60},
    "Malaysia":             {"kwh": 0.05, "labour": 4.3925,  "food_index": 0.75},
    "Thailand":             {"kwh": 0.13, "labour": 2.4516,  "food_index": 0.60},
    "Vietnam":              {"kwh": 0.08, "labour": 2.0541,  "food_index": 0.55},
    "Indonesia":            {"kwh": 0.09, "labour": 1.2876,  "food_index": 0.55},
    "Australia":            {"kwh": 0.26, "labour": 28.8189, "food_index": 1.10},
    "New Zealand":          {"kwh": 0.21, "labour": 26.448,  "food_index": 1.10},
    "India":                {"kwh": 0.08, "labour": 1.3417,  "food_index": 0.45},
    "Morocco":              {"kwh": 0.12, "labour": 1.9158,  "food_index": 0.65},
    "Egypt":                {"kwh": 0.02, "labour": 1.2925,  "food_index": 0.50},
    "South Africa":         {"kwh": 0.19, "labour": 9.1876,  "food_index": 0.70},
    "Kenya":                {"kwh": 0.22, "labour": 0.535,   "food_index": 0.60},
}

# ─────────────────────────────────────────────────────────────────────────────
# CROPS (98 total)
# Fields: yield, cycle, seed, substrate, ec, water, nutrient, price_base,
#         price_low, price_high, dli, harvest_mult, wf, tr,
#         days_between, yield_h2, yield_h3
# ─────────────────────────────────────────────────────────────────────────────
CROPS = {
    "Lettuce (Butterhead)":               {"yield": 4,   "cycle": 35,  "seed": 0.45,  "substrate": 1.255,  "ec": 1.6, "water": 30,  "nutrient": 0.005, "price_base": 1.6,  "price_low": 1.2, "price_high": 2,    "dli": 15, "harvest_mult": 1,    "wf": 0.95, "tr": 15, "days_between": 0,  "yield_h2": 0,    "yield_h3": 0},
    "Lettuce (Romaine)":                  {"yield": 4,   "cycle": 35,  "seed": 0.45,  "substrate": 1.255,  "ec": 1.7, "water": 30,  "nutrient": 0.005, "price_base": 1.6,  "price_low": 1.2, "price_high": 2,    "dli": 15, "harvest_mult": 1,    "wf": 0.95, "tr": 15, "days_between": 0,  "yield_h2": 0,    "yield_h3": 0},
    "Lettuce (Iceberg - mini varieties)": {"yield": 4,   "cycle": 40,  "seed": 0.45,  "substrate": 1.255,  "ec": 1.5, "water": 30,  "nutrient": 0.005, "price_base": 1.4,  "price_low": 1.0, "price_high": 1.8,  "dli": 12, "harvest_mult": 1.05, "wf": 0.96, "tr": 12, "days_between": 0,  "yield_h2": 0,    "yield_h3": 0},
    "Leaf Lettuce (Green)":               {"yield": 3,   "cycle": 25,  "seed": 0.95,  "substrate": 2.65,   "ec": 1.4, "water": 30,  "nutrient": 0.005, "price_base": 1.5,  "price_low": 1.1, "price_high": 1.9,  "dli": 14, "harvest_mult": 1,    "wf": 0.95, "tr": 15, "days_between": 6,  "yield_h2": 0.8,  "yield_h3": 0.6},
    "Leaf Lettuce (Red)":                 {"yield": 3,   "cycle": 25,  "seed": 0.95,  "substrate": 2.65,   "ec": 1.4, "water": 30,  "nutrient": 0.005, "price_base": 1.5,  "price_low": 1.1, "price_high": 1.9,  "dli": 14, "harvest_mult": 1,    "wf": 0.95, "tr": 15, "days_between": 6,  "yield_h2": 0.8,  "yield_h3": 0.6},
    "Oakleaf Lettuce":                    {"yield": 3,   "cycle": 25,  "seed": 0.95,  "substrate": 2.65,   "ec": 1.5, "water": 30,  "nutrient": 0.005, "price_base": 1.6,  "price_low": 1.2, "price_high": 2,    "dli": 14, "harvest_mult": 1,    "wf": 0.95, "tr": 15, "days_between": 7,  "yield_h2": 0.75, "yield_h3": 0.55},
    "Lollo Rosso":                        {"yield": 3,   "cycle": 25,  "seed": 0.95,  "substrate": 2.65,   "ec": 1.5, "water": 30,  "nutrient": 0.005, "price_base": 1.6,  "price_low": 1.2, "price_high": 2,    "dli": 14, "harvest_mult": 1,    "wf": 0.95, "tr": 15, "days_between": 8,  "yield_h2": 0.75, "yield_h3": 0.5},
    "Lollo Bionda":                       {"yield": 3,   "cycle": 25,  "seed": 0.95,  "substrate": 2.65,   "ec": 1.5, "water": 30,  "nutrient": 0.005, "price_base": 1.6,  "price_low": 1.2, "price_high": 2,    "dli": 14, "harvest_mult": 1,    "wf": 0.95, "tr": 15, "days_between": 8,  "yield_h2": 0.75, "yield_h3": 0.5},
    "Batavia Lettuce":                    {"yield": 3.5, "cycle": 30,  "seed": 0.45,  "substrate": 1.255,  "ec": 1.6, "water": 30,  "nutrient": 0.005, "price_base": 1.6,  "price_low": 1.2, "price_high": 2,    "dli": 15, "harvest_mult": 1,    "wf": 0.95, "tr": 15, "days_between": 6,  "yield_h2": 0.8,  "yield_h3": 0.6},
    "Frisee":                             {"yield": 3.5, "cycle": 30,  "seed": 0.45,  "substrate": 1.255,  "ec": 1.6, "water": 30,  "nutrient": 0.005, "price_base": 1.7,  "price_low": 1.3, "price_high": 2.1,  "dli": 14, "harvest_mult": 1.1,  "wf": 0.94, "tr": 18, "days_between": 6,  "yield_h2": 0.8,  "yield_h3": 0.6},
    "Escarole":                           {"yield": 3.5, "cycle": 30,  "seed": 0.45,  "substrate": 1.255,  "ec": 1.8, "water": 30,  "nutrient": 0.005, "price_base": 1.7,  "price_low": 1.3, "price_high": 2.1,  "dli": 14, "harvest_mult": 1.1,  "wf": 0.94, "tr": 18, "days_between": 6,  "yield_h2": 0.8,  "yield_h3": 0.6},
    "Baby Lettuce Mix":                   {"yield": 3,   "cycle": 20,  "seed": 0.95,  "substrate": 1.744,  "ec": 1.3, "water": 25,  "nutrient": 0.005, "price_base": 2,    "price_low": 1.5, "price_high": 2.8,  "dli": 12, "harvest_mult": 0.95, "wf": 0.95, "tr": 15, "days_between": 6,  "yield_h2": 0.8,  "yield_h3": 0.6},
    "Spinach":                            {"yield": 2.5, "cycle": 28,  "seed": 0.7,   "substrate": 1.744,  "ec": 2,   "water": 25,  "nutrient": 0.005, "price_base": 2,    "price_low": 1.5, "price_high": 2.6,  "dli": 16, "harvest_mult": 1.1,  "wf": 0.91, "tr": 27, "days_between": 10, "yield_h2": 0.75, "yield_h3": 0.55},
    "Baby Spinach":                       {"yield": 2.5, "cycle": 20,  "seed": 0.7,   "substrate": 1.744,  "ec": 1.8, "water": 25,  "nutrient": 0.005, "price_base": 2.4,  "price_low": 1.8, "price_high": 3.2,  "dli": 14, "harvest_mult": 1,    "wf": 0.91, "tr": 27, "days_between": 10, "yield_h2": 0.8,  "yield_h3": 0.6},
    "Kale (Curly)":                       {"yield": 3.5, "cycle": 30,  "seed": 0.7,   "substrate": 2.093,  "ec": 2,   "water": 40,  "nutrient": 0.005, "price_base": 2.2,  "price_low": 1.6, "price_high": 3,    "dli": 18, "harvest_mult": 1.15, "wf": 0.85, "tr": 45, "days_between": 14, "yield_h2": 0.8,  "yield_h3": 0.65},
    "Kale (Tuscan/Lacinato)":             {"yield": 3.5, "cycle": 30,  "seed": 0.7,   "substrate": 2.093,  "ec": 2,   "water": 40,  "nutrient": 0.005, "price_base": 2.2,  "price_low": 1.6, "price_high": 3,    "dli": 18, "harvest_mult": 1.15, "wf": 0.85, "tr": 45, "days_between": 14, "yield_h2": 0.8,  "yield_h3": 0.65},
    "Baby Kale":                          {"yield": 3.5, "cycle": 22,  "seed": 0.7,   "substrate": 1.744,  "ec": 2,   "water": 25,  "nutrient": 0.005, "price_base": 2.8,  "price_low": 2,   "price_high": 3.8,  "dli": 14, "harvest_mult": 1.05, "wf": 0.87, "tr": 39, "days_between": 14, "yield_h2": 0.8,  "yield_h3": 0.65},
    "Mizuna":                             {"yield": 3.5, "cycle": 25,  "seed": 0.7,   "substrate": 1.744,  "ec": 1.4, "water": 25,  "nutrient": 0.005, "price_base": 2.5,  "price_low": 1.9, "price_high": 3.2,  "dli": 12, "harvest_mult": 1.05, "wf": 0.93, "tr": 21, "days_between": 10, "yield_h2": 0.8,  "yield_h3": 0.6},
    "Arugula (Rocket)":                   {"yield": 3.5, "cycle": 20,  "seed": 0.7,   "substrate": 1.744,  "ec": 1.4, "water": 25,  "nutrient": 0.005, "price_base": 2.8,  "price_low": 2.1, "price_high": 3.8,  "dli": 13, "harvest_mult": 1.1,  "wf": 0.91, "tr": 27, "days_between": 10, "yield_h2": 0.8,  "yield_h3": 0.6},
    "Tatsoi":                             {"yield": 3.5, "cycle": 25,  "seed": 0.7,   "substrate": 1.744,  "ec": 1.5, "water": 25,  "nutrient": 0.005, "price_base": 2.5,  "price_low": 1.9, "price_high": 3.2,  "dli": 12, "harvest_mult": 1.05, "wf": 0.93, "tr": 21, "days_between": 10, "yield_h2": 0.8,  "yield_h3": 0.6},
    "Pak Choi (Bok Choy - dwarf)":        {"yield": 3.5, "cycle": 30,  "seed": 0.7,   "substrate": 2.093,  "ec": 1.6, "water": 30,  "nutrient": 0.005, "price_base": 2.2,  "price_low": 1.6, "price_high": 3,    "dli": 14, "harvest_mult": 1.1,  "wf": 0.95, "tr": 15, "days_between": 10, "yield_h2": 0.8,  "yield_h3": 0.6},
    "Shanghai Bok Choy":                  {"yield": 3.5, "cycle": 30,  "seed": 0.7,   "substrate": 2.093,  "ec": 1.6, "water": 30,  "nutrient": 0.005, "price_base": 2.2,  "price_low": 1.6, "price_high": 3,    "dli": 14, "harvest_mult": 1.1,  "wf": 0.95, "tr": 15, "days_between": 10, "yield_h2": 0.8,  "yield_h3": 0.6},
    "Mustard Greens":                     {"yield": 3.5, "cycle": 25,  "seed": 0.7,   "substrate": 1.744,  "ec": 1.8, "water": 25,  "nutrient": 0.005, "price_base": 2.3,  "price_low": 1.8, "price_high": 3.2,  "dli": 12, "harvest_mult": 1.1,  "wf": 0.93, "tr": 21, "days_between": 10, "yield_h2": 0.8,  "yield_h3": 0.6},
    "Mibuna":                             {"yield": 3.5, "cycle": 25,  "seed": 0.7,   "substrate": 1.744,  "ec": 1.5, "water": 25,  "nutrient": 0.005, "price_base": 2.5,  "price_low": 1.9, "price_high": 3.2,  "dli": 12, "harvest_mult": 1.05, "wf": 0.93, "tr": 21, "days_between": 10, "yield_h2": 0.8,  "yield_h3": 0.6},
    "Choi Sum (baby)":                    {"yield": 3.5, "cycle": 25,  "seed": 0.7,   "substrate": 1.744,  "ec": 1.6, "water": 25,  "nutrient": 0.005, "price_base": 2.3,  "price_low": 1.7, "price_high": 3.1,  "dli": 14, "harvest_mult": 1.1,  "wf": 0.94, "tr": 18, "days_between": 10, "yield_h2": 0.8,  "yield_h3": 0.6},
    "Komatsuna":                          {"yield": 3.5, "cycle": 25,  "seed": 0.7,   "substrate": 1.744,  "ec": 1.5, "water": 25,  "nutrient": 0.005, "price_base": 2.3,  "price_low": 1.7, "price_high": 3.1,  "dli": 13, "harvest_mult": 1.05, "wf": 0.94, "tr": 18, "days_between": 10, "yield_h2": 0.8,  "yield_h3": 0.6},
    "Swiss Chard (baby)":                 {"yield": 3.5, "cycle": 28,  "seed": 0.7,   "substrate": 2.093,  "ec": 1.8, "water": 25,  "nutrient": 0.005, "price_base": 2.2,  "price_low": 1.6, "price_high": 3,    "dli": 14, "harvest_mult": 1.1,  "wf": 0.92, "tr": 24, "days_between": 7,  "yield_h2": 0.85, "yield_h3": 0.75},
    "Microgreens - Broccoli":             {"yield": 0.3, "cycle": 10,  "seed": 0.36,  "substrate": 2.326,  "ec": 1,   "water": 10,  "nutrient": 0.005, "price_base": 12,   "price_low": 8,   "price_high": 18,   "dli": 10, "harvest_mult": 1.6,  "wf": 0.9,  "tr": 30, "days_between": 0,  "yield_h2": 0,    "yield_h3": 0},
    "Microgreens - Radish":               {"yield": 0.3, "cycle": 10,  "seed": 0.24,  "substrate": 2.326,  "ec": 1,   "water": 10,  "nutrient": 0.005, "price_base": 12,   "price_low": 8,   "price_high": 18,   "dli": 10, "harvest_mult": 1.55, "wf": 0.9,  "tr": 30, "days_between": 0,  "yield_h2": 0,    "yield_h3": 0},
    "Microgreens - Sunflower":            {"yield": 0.3, "cycle": 12,  "seed": 0.8,   "substrate": 2.326,  "ec": 1,   "water": 10,  "nutrient": 0.005, "price_base": 12,   "price_low": 8,   "price_high": 18,   "dli": 10, "harvest_mult": 1.7,  "wf": 0.88, "tr": 36, "days_between": 0,  "yield_h2": 0,    "yield_h3": 0},
    "Microgreens - Pea Shoots":           {"yield": 0.3, "cycle": 12,  "seed": 1.5,   "substrate": 2.326,  "ec": 1,   "water": 10,  "nutrient": 0.005, "price_base": 12,   "price_low": 8,   "price_high": 18,   "dli": 10, "harvest_mult": 1.65, "wf": 0.9,  "tr": 30, "days_between": 0,  "yield_h2": 0,    "yield_h3": 0},
    "Microgreens - Mustard":              {"yield": 0.3, "cycle": 10,  "seed": 0.12,  "substrate": 2.326,  "ec": 1,   "water": 10,  "nutrient": 0.005, "price_base": 12,   "price_low": 8,   "price_high": 18,   "dli": 10, "harvest_mult": 1.55, "wf": 0.9,  "tr": 30, "days_between": 0,  "yield_h2": 0,    "yield_h3": 0},
    "Microgreens - Kale":                 {"yield": 0.3, "cycle": 10,  "seed": 0.4,   "substrate": 2.326,  "ec": 1,   "water": 10,  "nutrient": 0.005, "price_base": 12,   "price_low": 8,   "price_high": 18,   "dli": 10, "harvest_mult": 1.6,  "wf": 0.9,  "tr": 30, "days_between": 0,  "yield_h2": 0,    "yield_h3": 0},
    "Microgreens - Basil":                {"yield": 0.3, "cycle": 14,  "seed": 0.32,  "substrate": 2.326,  "ec": 1,   "water": 10,  "nutrient": 0.005, "price_base": 12,   "price_low": 8,   "price_high": 18,   "dli": 10, "harvest_mult": 1.7,  "wf": 0.89, "tr": 33, "days_between": 0,  "yield_h2": 0,    "yield_h3": 0},
    "Microgreens - Amaranth":             {"yield": 0.3, "cycle": 10,  "seed": 0.36,  "substrate": 2.326,  "ec": 1,   "water": 10,  "nutrient": 0.005, "price_base": 12,   "price_low": 8,   "price_high": 18,   "dli": 10, "harvest_mult": 1.65, "wf": 0.88, "tr": 36, "days_between": 0,  "yield_h2": 0,    "yield_h3": 0},
    "Microgreens - Wheatgrass":           {"yield": 0.3, "cycle": 10,  "seed": 0.36,  "substrate": 2.326,  "ec": 1,   "water": 10,  "nutrient": 0.005, "price_base": 10,   "price_low": 7,   "price_high": 15,   "dli": 10, "harvest_mult": 1.5,  "wf": 0.9,  "tr": 30, "days_between": 0,  "yield_h2": 0,    "yield_h3": 0},
    "Basil (Genovese)":                   {"yield": 2,   "cycle": 35,  "seed": 0.9,   "substrate": 2.907,  "ec": 1.8, "water": 40,  "nutrient": 0.005, "price_base": 8,    "price_low": 6,   "price_high": 12,   "dli": 18, "harvest_mult": 1.2,  "wf": 0.85, "tr": 45, "days_between": 14, "yield_h2": 0.7,  "yield_h3": 0.55},
    "Basil (Thai)":                       {"yield": 2,   "cycle": 35,  "seed": 0.9,   "substrate": 2.907,  "ec": 1.8, "water": 40,  "nutrient": 0.005, "price_base": 8,    "price_low": 6,   "price_high": 12,   "dli": 18, "harvest_mult": 1.2,  "wf": 0.85, "tr": 45, "days_between": 14, "yield_h2": 0.7,  "yield_h3": 0.55},
    "Basil (Purple)":                     {"yield": 2,   "cycle": 35,  "seed": 0.9,   "substrate": 2.907,  "ec": 1.8, "water": 40,  "nutrient": 0.005, "price_base": 8,    "price_low": 6,   "price_high": 12,   "dli": 18, "harvest_mult": 1.2,  "wf": 0.85, "tr": 45, "days_between": 14, "yield_h2": 0.7,  "yield_h3": 0.55},
    "Basil (Lemon)":                      {"yield": 2,   "cycle": 35,  "seed": 0.9,   "substrate": 2.907,  "ec": 1.8, "water": 40,  "nutrient": 0.005, "price_base": 8,    "price_low": 6,   "price_high": 12,   "dli": 18, "harvest_mult": 1.2,  "wf": 0.85, "tr": 45, "days_between": 14, "yield_h2": 0.7,  "yield_h3": 0.55},
    "Mint (Spearmint)":                   {"yield": 2,   "cycle": 35,  "seed": 0.9,   "substrate": 2.907,  "ec": 2,   "water": 40,  "nutrient": 0.005, "price_base": 6.5,  "price_low": 5,   "price_high": 9,    "dli": 16, "harvest_mult": 1.25, "wf": 0.86, "tr": 42, "days_between": 14, "yield_h2": 0.85, "yield_h3": 0.7},
    "Mint (Peppermint)":                  {"yield": 2,   "cycle": 35,  "seed": 0.9,   "substrate": 2.907,  "ec": 2,   "water": 40,  "nutrient": 0.005, "price_base": 6.5,  "price_low": 5,   "price_high": 9,    "dli": 16, "harvest_mult": 1.25, "wf": 0.86, "tr": 42, "days_between": 14, "yield_h2": 0.85, "yield_h3": 0.7},
    "Parsley (Curly)":                    {"yield": 2,   "cycle": 45,  "seed": 0.9,   "substrate": 2.907,  "ec": 1.6, "water": 40,  "nutrient": 0.005, "price_base": 3,    "price_low": 2.2, "price_high": 4.2,  "dli": 14, "harvest_mult": 1.2,  "wf": 0.85, "tr": 45, "days_between": 7,  "yield_h2": 0.85, "yield_h3": 0.75},
    "Parsley (Flat-leaf)":                {"yield": 2,   "cycle": 45,  "seed": 0.9,   "substrate": 2.907,  "ec": 1.6, "water": 40,  "nutrient": 0.005, "price_base": 3,    "price_low": 2.2, "price_high": 4.2,  "dli": 14, "harvest_mult": 1.2,  "wf": 0.85, "tr": 45, "days_between": 7,  "yield_h2": 0.85, "yield_h3": 0.75},
    "Cilantro (Coriander)":               {"yield": 2,   "cycle": 35,  "seed": 0.9,   "substrate": 2.907,  "ec": 1.5, "water": 40,  "nutrient": 0.005, "price_base": 3.5,  "price_low": 2.5, "price_high": 5,    "dli": 14, "harvest_mult": 1.25, "wf": 0.92, "tr": 24, "days_between": 14, "yield_h2": 0.7,  "yield_h3": 0.4},
    "Chives":                             {"yield": 2,   "cycle": 45,  "seed": 0.9,   "substrate": 2.907,  "ec": 1.8, "water": 40,  "nutrient": 0.005, "price_base": 6,    "price_low": 4.5, "price_high": 9,    "dli": 16, "harvest_mult": 1.3,  "wf": 0.88, "tr": 36, "days_between": 28, "yield_h2": 0.85, "yield_h3": 0.7},
    "Dill":                               {"yield": 2,   "cycle": 35,  "seed": 0.9,   "substrate": 2.907,  "ec": 1.4, "water": 40,  "nutrient": 0.005, "price_base": 4,    "price_low": 3,   "price_high": 6,    "dli": 14, "harvest_mult": 1.25, "wf": 0.9,  "tr": 30, "days_between": 14, "yield_h2": 0.65, "yield_h3": 0.4},
    "Oregano":                            {"yield": 1.5, "cycle": 45,  "seed": 0.56,  "substrate": 3.488,  "ec": 2.2, "water": 50,  "nutrient": 0.005, "price_base": 7,    "price_low": 5,   "price_high": 10,   "dli": 18, "harvest_mult": 1.3,  "wf": 0.8,  "tr": 60, "days_between": 21, "yield_h2": 0.85, "yield_h3": 0.75},
    "Thyme":                              {"yield": 1.5, "cycle": 50,  "seed": 0.56,  "substrate": 3.488,  "ec": 2.2, "water": 50,  "nutrient": 0.005, "price_base": 7,    "price_low": 5,   "price_high": 10,   "dli": 18, "harvest_mult": 1.35, "wf": 0.8,  "tr": 60, "days_between": 28, "yield_h2": 0.8,  "yield_h3": 0.7},
    "Sage":                               {"yield": 1.5, "cycle": 50,  "seed": 0.56,  "substrate": 3.488,  "ec": 2.2, "water": 50,  "nutrient": 0.005, "price_base": 7,    "price_low": 5,   "price_high": 10,   "dli": 18, "harvest_mult": 1.35, "wf": 0.8,  "tr": 60, "days_between": 28, "yield_h2": 0.8,  "yield_h3": 0.7},
    "Rosemary (dwarf)":                   {"yield": 1.5, "cycle": 60,  "seed": 0.56,  "substrate": 3.488,  "ec": 2.3, "water": 50,  "nutrient": 0.005, "price_base": 7,    "price_low": 5,   "price_high": 10,   "dli": 18, "harvest_mult": 1.4,  "wf": 0.75, "tr": 75, "days_between": 35, "yield_h2": 0.75, "yield_h3": 0.6},
    "Lemongrass":                         {"yield": 1.5, "cycle": 60,  "seed": 0.56,  "substrate": 3.488,  "ec": 2,   "water": 50,  "nutrient": 0.005, "price_base": 4.5,  "price_low": 3.5, "price_high": 6.5,  "dli": 16, "harvest_mult": 1.3,  "wf": 0.78, "tr": 66, "days_between": 30, "yield_h2": 0.9,  "yield_h3": 0.85},
    "Stevia":                             {"yield": 2,   "cycle": 60,  "seed": 0.9,   "substrate": 2.907,  "ec": 1.6, "water": 40,  "nutrient": 0.005, "price_base": 6,    "price_low": 4.5, "price_high": 8.5,  "dli": 14, "harvest_mult": 1.35, "wf": 0.8,  "tr": 60, "days_between": 21, "yield_h2": 0.85, "yield_h3": 0.75},
    "Watercress":                         {"yield": 3,   "cycle": 21,  "seed": 0.7,   "substrate": 1.744,  "ec": 1.2, "water": 20,  "nutrient": 0.005, "price_base": 3.5,  "price_low": 2.5, "price_high": 5,    "dli": 10, "harvest_mult": 1.15, "wf": 0.95, "tr": 15, "days_between": 14, "yield_h2": 0.85, "yield_h3": 0.75},
    "Upland Cress":                       {"yield": 3,   "cycle": 21,  "seed": 0.7,   "substrate": 1.744,  "ec": 1.2, "water": 20,  "nutrient": 0.005, "price_base": 3.5,  "price_low": 2.5, "price_high": 5,    "dli": 10, "harvest_mult": 1.15, "wf": 0.94, "tr": 18, "days_between": 10, "yield_h2": 0.8,  "yield_h3": 0.6},
    "Claytonia (Miners Lettuce)":         {"yield": 3,   "cycle": 25,  "seed": 0.7,   "substrate": 1.744,  "ec": 1.2, "water": 20,  "nutrient": 0.005, "price_base": 3.2,  "price_low": 2.4, "price_high": 4.8,  "dli": 10, "harvest_mult": 1.05, "wf": 0.95, "tr": 15, "days_between": 14, "yield_h2": 0.85, "yield_h3": 0.75},
    "Purslane":                           {"yield": 3,   "cycle": 25,  "seed": 0.7,   "substrate": 1.744,  "ec": 1.3, "water": 25,  "nutrient": 0.005, "price_base": 3,    "price_low": 2.2, "price_high": 4.8,  "dli": 12, "harvest_mult": 1.1,  "wf": 0.93, "tr": 21, "days_between": 14, "yield_h2": 0.85, "yield_h3": 0.75},
    "Sorrel (Red Vein)":                  {"yield": 3,   "cycle": 35,  "seed": 0.7,   "substrate": 1.744,  "ec": 1.6, "water": 25,  "nutrient": 0.005, "price_base": 3.8,  "price_low": 2.8, "price_high": 6,    "dli": 12, "harvest_mult": 1.1,  "wf": 0.9,  "tr": 30, "days_between": 14, "yield_h2": 0.85, "yield_h3": 0.75},
    "Fennel (leaf/baby bulb only)":       {"yield": 3,   "cycle": 45,  "seed": 0.7,   "substrate": 2.326,  "ec": 1.6, "water": 35,  "nutrient": 0.005, "price_base": 2,    "price_low": 1.4, "price_high": 2.8,  "dli": 14, "harvest_mult": 1.15, "wf": 0.9,  "tr": 30, "days_between": 21, "yield_h2": 0.8,  "yield_h3": 0.6},
    "Spring Onions (Green Onions/Scallions)": {"yield": 4, "cycle": 60, "seed": 2.6, "substrate": 2.326, "ec": 1.8, "water": 35, "nutrient": 0.005, "price_base": 1.8, "price_low": 1.3, "price_high": 2.6, "dli": 14, "harvest_mult": 1.4, "wf": 0.89, "tr": 33, "days_between": 0, "yield_h2": 0, "yield_h3": 0},
    "Garlic Chives":                      {"yield": 2,   "cycle": 45,  "seed": 0.9,   "substrate": 2.907,  "ec": 1.8, "water": 40,  "nutrient": 0.005, "price_base": 6,    "price_low": 4.5, "price_high": 9,    "dli": 16, "harvest_mult": 1.3,  "wf": 0.88, "tr": 36, "days_between": 14, "yield_h2": 0.85, "yield_h3": 0.7},
    "Baby Carrots (only special mini cultivars)": {"yield": 2, "cycle": 50, "seed": 0.4, "substrate": 2.326, "ec": 1.8, "water": 35, "nutrient": 0.005, "price_base": 1.6, "price_low": 1.2, "price_high": 2.2, "dli": 14, "harvest_mult": 1.6, "wf": 0.88, "tr": 36, "days_between": 0, "yield_h2": 0, "yield_h3": 0},
    "Radishes (fast/compact varieties)":  {"yield": 2,   "cycle": 28,  "seed": 0.06,  "substrate": 2.326,  "ec": 2,   "water": 35,  "nutrient": 0.005, "price_base": 1.5,  "price_low": 1.1, "price_high": 2.1,  "dli": 14, "harvest_mult": 1.5,  "wf": 0.95, "tr": 15, "days_between": 0,  "yield_h2": 0,    "yield_h3": 0},
    "Beets (baby leaves/beet greens)":    {"yield": 3.5, "cycle": 35,  "seed": 0.7,   "substrate": 2.326,  "ec": 1.8, "water": 35,  "nutrient": 0.005, "price_base": 1.5,  "price_low": 1.1, "price_high": 2.1,  "dli": 14, "harvest_mult": 1.35, "wf": 0.9,  "tr": 30, "days_between": 0,  "yield_h2": 0,    "yield_h3": 0},
    "Turnip Greens":                      {"yield": 3.5, "cycle": 28,  "seed": 0.7,   "substrate": 2.326,  "ec": 1.6, "water": 35,  "nutrient": 0.005, "price_base": 1.6,  "price_low": 1.2, "price_high": 2.4,  "dli": 12, "harvest_mult": 1.3,  "wf": 0.92, "tr": 24, "days_between": 10, "yield_h2": 0.8,  "yield_h3": 0.6},
    "Micro-Turnips (Tokyo Cross type)":   {"yield": 2,   "cycle": 35,  "seed": 0.32,  "substrate": 2.326,  "ec": 1.6, "water": 35,  "nutrient": 0.005, "price_base": 1.8,  "price_low": 1.4, "price_high": 2.8,  "dli": 14, "harvest_mult": 1.55, "wf": 0.94, "tr": 18, "days_between": 0,  "yield_h2": 0,    "yield_h3": 0},
    "Strawberries (day-neutral, everbearing)": {"yield": 7, "cycle": 240, "seed": 3, "substrate": 15.116, "ec": 1.6, "water": 120, "nutrient": 0.005, "price_base": 3.5, "price_low": 2.5, "price_high": 5, "dli": 18, "harvest_mult": 2.5, "wf": 0.91, "tr": 27, "days_between": 0, "yield_h2": 0, "yield_h3": 0},
    "Dwarf Alpine Strawberries":          {"yield": 6,   "cycle": 240, "seed": 3,    "substrate": 15.116, "ec": 1.6, "water": 120, "nutrient": 0.005, "price_base": 3.8,  "price_low": 2.8, "price_high": 5.5,  "dli": 18, "harvest_mult": 2.6,  "wf": 0.91, "tr": 27, "days_between": 0,  "yield_h2": 0,    "yield_h3": 0},
    "Cherry Tomatoes (dwarf cultivars)":  {"yield": 25,  "cycle": 240, "seed": 1.2,  "substrate": 15.116, "ec": 2.5, "water": 120, "nutrient": 0.005, "price_base": 2.5,  "price_low": 1.9, "price_high": 3.5,  "dli": 25, "harvest_mult": 2.3,  "wf": 0.94, "tr": 18, "days_between": 0,  "yield_h2": 0,    "yield_h3": 0},
    "Micro-Tomatoes (micro-dwarf varieties like 'Micro Tom')": {"yield": 20, "cycle": 240, "seed": 0.75, "substrate": 15.116, "ec": 2.5, "water": 120, "nutrient": 0.005, "price_base": 2.5, "price_low": 1.9, "price_high": 3.5, "dli": 25, "harvest_mult": 2.2, "wf": 0.94, "tr": 18, "days_between": 0, "yield_h2": 0, "yield_h3": 0},
    "Peppers (dwarf sweet)":              {"yield": 15,  "cycle": 240, "seed": 1.75, "substrate": 15.116, "ec": 2.4, "water": 120, "nutrient": 0.005, "price_base": 2.8,  "price_low": 2,   "price_high": 4,    "dli": 22, "harvest_mult": 2.4,  "wf": 0.92, "tr": 24, "days_between": 0,  "yield_h2": 0,    "yield_h3": 0},
    "Chili Peppers (compact ornamental/capsicum annuum)": {"yield": 20, "cycle": 240, "seed": 1.75, "substrate": 15.116, "ec": 2.4, "water": 120, "nutrient": 0.005, "price_base": 3, "price_low": 2.2, "price_high": 4.5, "dli": 22, "harvest_mult": 2.5, "wf": 0.91, "tr": 27, "days_between": 0, "yield_h2": 0, "yield_h3": 0},
    "Eggplant (micro/dwarf)":             {"yield": 12,  "cycle": 240, "seed": 0.62, "substrate": 15.116, "ec": 2.5, "water": 120, "nutrient": 0.005, "price_base": 2.2,  "price_low": 1.7, "price_high": 3.2,  "dli": 22, "harvest_mult": 2.4,  "wf": 0.92, "tr": 24, "days_between": 0,  "yield_h2": 0,    "yield_h3": 0},
    "Cucumbers (mini greenhouse varieties)": {"yield": 23, "cycle": 240, "seed": 0.7, "substrate": 15.116, "ec": 2.3, "water": 120, "nutrient": 0.005, "price_base": 1.8, "price_low": 1.3, "price_high": 2.8, "dli": 22, "harvest_mult": 2.2, "wf": 0.96, "tr": 12, "days_between": 0, "yield_h2": 0, "yield_h3": 0},
    "Dwarf Beans (very limited yield but feasible)": {"yield": 4, "cycle": 240, "seed": 0.25, "substrate": 15.116, "ec": 2, "water": 120, "nutrient": 0.005, "price_base": 2.2, "price_low": 1.7, "price_high": 3.2, "dli": 18, "harvest_mult": 2.1, "wf": 0.9, "tr": 30, "days_between": 0, "yield_h2": 0, "yield_h3": 0},
    "Pea Shoots":                         {"yield": 0.3, "cycle": 14,  "seed": 1.5,  "substrate": 2.326,  "ec": 1,   "water": 10,  "nutrient": 0.005, "price_base": 8,    "price_low": 6,   "price_high": 12,   "dli": 10, "harvest_mult": 1.65, "wf": 0.9,  "tr": 30, "days_between": 10, "yield_h2": 0.6,  "yield_h3": 0.3},
    "Edible Flowers - Nasturtium":        {"yield": 1.5, "cycle": 30,  "seed": 0.45, "substrate": 2.907,  "ec": 1.4, "water": 30,  "nutrient": 0.005, "price_base": 10,   "price_low": 7,   "price_high": 18,   "dli": 14, "harvest_mult": 1.4,  "wf": 0.93, "tr": 21, "days_between": 0,  "yield_h2": 0,    "yield_h3": 0},
    "Edible Flowers - Viola/Pansy":       {"yield": 1.5, "cycle": 45,  "seed": 0.45, "substrate": 2.907,  "ec": 1.4, "water": 30,  "nutrient": 0.005, "price_base": 12,   "price_low": 8,   "price_high": 20,   "dli": 12, "harvest_mult": 1.5,  "wf": 0.92, "tr": 24, "days_between": 0,  "yield_h2": 0,    "yield_h3": 0},
    "Edible Flowers - Marigold (Tagetes)": {"yield": 1.5, "cycle": 45, "seed": 0.45, "substrate": 2.907, "ec": 1.4, "water": 30, "nutrient": 0.005, "price_base": 10, "price_low": 7, "price_high": 18, "dli": 14, "harvest_mult": 1.45, "wf": 0.9, "tr": 30, "days_between": 0, "yield_h2": 0, "yield_h3": 0},
    "Edible Flowers - Borage":            {"yield": 1.5, "cycle": 45,  "seed": 0.45, "substrate": 2.907,  "ec": 1.5, "water": 30,  "nutrient": 0.005, "price_base": 9,    "price_low": 6.5, "price_high": 16,   "dli": 14, "harvest_mult": 1.5,  "wf": 0.95, "tr": 15, "days_between": 0,  "yield_h2": 0,    "yield_h3": 0},
    "Edible Flowers - Calendula":         {"yield": 1.5, "cycle": 45,  "seed": 0.45, "substrate": 2.907,  "ec": 1.5, "water": 30,  "nutrient": 0.005, "price_base": 9,    "price_low": 6.5, "price_high": 16,   "dli": 14, "harvest_mult": 1.45, "wf": 0.9,  "tr": 30, "days_between": 0,  "yield_h2": 0,    "yield_h3": 0},
    "Shiso (Perilla)":                    {"yield": 3,   "cycle": 30,  "seed": 0.7,  "substrate": 2.907,  "ec": 1.8, "water": 30,  "nutrient": 0.005, "price_base": 6,    "price_low": 4.5, "price_high": 9.5,  "dli": 16, "harvest_mult": 1.3,  "wf": 0.9,  "tr": 30, "days_between": 10, "yield_h2": 0.8,  "yield_h3": 0.6},
    "Wasabi Greens":                      {"yield": 3,   "cycle": 30,  "seed": 0.7,  "substrate": 2.907,  "ec": 1.6, "water": 30,  "nutrient": 0.005, "price_base": 6.5,  "price_low": 5,   "price_high": 10,   "dli": 14, "harvest_mult": 1.2,  "wf": 0.9,  "tr": 30, "days_between": 10, "yield_h2": 0.8,  "yield_h3": 0.6},
    "Celery (leaf and dwarf stalk celery)": {"yield": 3, "cycle": 60, "seed": 0.7, "substrate": 2.326, "ec": 1.8, "water": 35, "nutrient": 0.005, "price_base": 1.8, "price_low": 1.3, "price_high": 2.8, "dli": 14, "harvest_mult": 1.25, "wf": 0.95, "tr": 15, "days_between": 14, "yield_h2": 0.8, "yield_h3": 0.65},
    "Chinese Celery":                     {"yield": 3,   "cycle": 60,  "seed": 0.7,  "substrate": 2.326,  "ec": 1.8, "water": 35,  "nutrient": 0.005, "price_base": 1.8,  "price_low": 1.3, "price_high": 2.8,  "dli": 14, "harvest_mult": 1.3,  "wf": 0.95, "tr": 15, "days_between": 14, "yield_h2": 0.8,  "yield_h3": 0.65},
    "Endive":                             {"yield": 3.5, "cycle": 45,  "seed": 0.45, "substrate": 1.255,  "ec": 1.8, "water": 30,  "nutrient": 0.005, "price_base": 2,    "price_low": 1.5, "price_high": 2.8,  "dli": 14, "harvest_mult": 1.15, "wf": 0.94, "tr": 18, "days_between": 0,  "yield_h2": 0,    "yield_h3": 0},
    "Radicchio":                          {"yield": 3.5, "cycle": 60,  "seed": 0.45, "substrate": 1.255,  "ec": 1.8, "water": 30,  "nutrient": 0.005, "price_base": 2.2,  "price_low": 1.7, "price_high": 3.2,  "dli": 14, "harvest_mult": 1.15, "wf": 0.93, "tr": 21, "days_between": 0,  "yield_h2": 0,    "yield_h3": 0},
    "Chicory":                            {"yield": 3.5, "cycle": 60,  "seed": 0.45, "substrate": 1.255,  "ec": 1.8, "water": 30,  "nutrient": 0.005, "price_base": 2,    "price_low": 1.5, "price_high": 2.8,  "dli": 14, "harvest_mult": 1.15, "wf": 0.93, "tr": 21, "days_between": 0,  "yield_h2": 0,    "yield_h3": 0},
    "Broccoli (baby leaf)":               {"yield": 3.5, "cycle": 28,  "seed": 0.7,  "substrate": 1.744,  "ec": 1.6, "water": 30,  "nutrient": 0.005, "price_base": 2.4,  "price_low": 1.8, "price_high": 3.2,  "dli": 14, "harvest_mult": 1.1,  "wf": 0.91, "tr": 27, "days_between": 10, "yield_h2": 0.75, "yield_h3": 0.55},
    "Cauliflower (microgreens and leaf)": {"yield": 3,   "cycle": 28,  "seed": 0.7,  "substrate": 1.744,  "ec": 1,   "water": 10,  "nutrient": 0.005, "price_base": 10,   "price_low": 7,   "price_high": 15,   "dli": 10, "harvest_mult": 1.6,  "wf": 0.9,  "tr": 30, "days_between": 0,  "yield_h2": 0,    "yield_h3": 0},
    "Brussels Sprouts (leaf only)":       {"yield": 3,   "cycle": 35,  "seed": 0.7,  "substrate": 1.744,  "ec": 1.8, "water": 30,  "nutrient": 0.005, "price_base": 2.2,  "price_low": 1.7, "price_high": 3.2,  "dli": 14, "harvest_mult": 1.2,  "wf": 0.88, "tr": 36, "days_between": 10, "yield_h2": 0.75, "yield_h3": 0.55},
    "Okra (dwarf cultivars, experimental)": {"yield": 5, "cycle": 240, "seed": 0.88, "substrate": 15.116, "ec": 2.4, "water": 120, "nutrient": 0.005, "price_base": 3, "price_low": 2.2, "price_high": 4.8, "dli": 22, "harvest_mult": 2.6, "wf": 0.9, "tr": 30, "days_between": 0, "yield_h2": 0, "yield_h3": 0},
    "Mushrooms - Oyster":                 {"yield": 14,  "cycle": 45,  "seed": 3.5,  "substrate": 23.256, "ec": 1.2, "water": 20,  "nutrient": 0.005, "price_base": 2.2,  "price_low": 1.8, "price_high": 3,    "dli": 0,  "harvest_mult": 2.8,  "wf": 0.92, "tr": 24, "days_between": 0,  "yield_h2": 0,    "yield_h3": 0},
    "Mushrooms - Shiitake":               {"yield": 10,  "cycle": 60,  "seed": 3.5,  "substrate": 23.256, "ec": 1.2, "water": 20,  "nutrient": 0.005, "price_base": 4.5,  "price_low": 3.5, "price_high": 6.5,  "dli": 0,  "harvest_mult": 3,    "wf": 0.9,  "tr": 30, "days_between": 0,  "yield_h2": 0,    "yield_h3": 0},
    "Mushrooms - Lions Mane":             {"yield": 8,   "cycle": 60,  "seed": 3.5,  "substrate": 23.256, "ec": 1.2, "water": 20,  "nutrient": 0.005, "price_base": 5.5,  "price_low": 4.2, "price_high": 7.5,  "dli": 0,  "harvest_mult": 3.1,  "wf": 0.92, "tr": 24, "days_between": 0,  "yield_h2": 0,    "yield_h3": 0},
    "Mushrooms - Enoki":                  {"yield": 8,   "cycle": 40,  "seed": 3.5,  "substrate": 23.256, "ec": 1.2, "water": 20,  "nutrient": 0.005, "price_base": 3.8,  "price_low": 3,   "price_high": 5.5,  "dli": 0,  "harvest_mult": 2.9,  "wf": 0.93, "tr": 21, "days_between": 0,  "yield_h2": 0,    "yield_h3": 0},
    "Mushrooms - Nameko":                 {"yield": 8,   "cycle": 60,  "seed": 3.5,  "substrate": 23.256, "ec": 1.2, "water": 20,  "nutrient": 0.005, "price_base": 4.8,  "price_low": 3.8, "price_high": 6.8,  "dli": 0,  "harvest_mult": 3,    "wf": 0.9,  "tr": 30, "days_between": 0,  "yield_h2": 0,    "yield_h3": 0},
    "Mushrooms - Maitake":                {"yield": 8,   "cycle": 60,  "seed": 3.5,  "substrate": 23.256, "ec": 1.2, "water": 20,  "nutrient": 0.005, "price_base": 6,    "price_low": 4.5, "price_high": 8.5,  "dli": 0,  "harvest_mult": 3.2,  "wf": 0.9,  "tr": 30, "days_between": 0,  "yield_h2": 0,    "yield_h3": 0},
    "Saffron Crocus (Micro-forcing)": {
        "yield": 0.05, "cycle": 90, "seed": 18.50, "substrate": 1.20,
        "ec": 1.8, "water": 15.0, "nutrient": 0.005,
        "price_base": 8000.0, "price_low": 5000.0, "price_high": 12000.0,
        "dli": 12.0, "harvest_mult": 1.0, "wf": 0.90, "tr": 250.0,
        "days_between": 0, "yield_h2": 0.0, "yield_h3": 0.0
    },
    "Cannabis (Medicinal Elite Clones)": {
        "yield": 2.40, "cycle": 70, "seed": 12.50, "substrate": 4.50,
        "ec": 2.2, "water": 85.0, "nutrient": 0.005,
        "price_base": 2500.0, "price_low": 1800.0, "price_high": 3500.0,
        "dli": 35.0, "harvest_mult": 1.0, "wf": 0.85, "tr": 320.0,
        "days_between": 0, "yield_h2": 0.0, "yield_h3": 0.0
    },
    "Wasabi (Premium Leaf & Petioles)": {
        "yield": 1.80, "cycle": 45, "seed": 6.00, "substrate": 2.20,
        "ec": 1.4, "water": 40.0, "nutrient": 0.005,
        "price_base": 95.0, "price_low": 65.0, "price_high": 140.0,
        "dli": 10.0, "harvest_mult": 1.3, "wf": 0.92, "tr": 180.0,
        "days_between": 15, "yield_h2": 0.85, "yield_h3": 0.70
    },
    "Lion's Mane Mushroom": {
        "yield": 14.50, "cycle": 35, "seed": 0.0, "substrate": 9.50,
        "ec": 0.0, "water": 12.0, "nutrient": 0.0,
        "price_base": 45.0, "price_low": 30.0, "price_high": 65.0,
        "dli": 0.0, "harvest_mult": 1.6, "wf": 0.20, "tr": 0.0,
        "days_between": 14, "yield_h2": 0.50, "yield_h3": 0.25
    },
    "Oyster Leaf (Mertensia maritima)": {
        "yield": 0.95, "cycle": 30, "seed": 4.50, "substrate": 1.80,
        "ec": 1.5, "water": 22.0, "nutrient": 0.005,
        "price_base": 150.0, "price_low": 100.0, "price_high": 220.0,
        "dli": 14.0, "harvest_mult": 1.4, "wf": 0.90, "tr": 190.0,
        "days_between": 12, "yield_h2": 0.90, "yield_h3": 0.75
    },
    "Sea Asparagus / Samphire": {
        "yield": 2.10, "cycle": 50, "seed": 2.50, "substrate": 1.50,
        "ec": 3.5, "water": 45.0, "nutrient": 0.005,
        "price_base": 75.0, "price_low": 50.0, "price_high": 110.0,
        "dli": 22.0, "harvest_mult": 1.2, "wf": 0.88, "tr": 210.0,
        "days_between": 20, "yield_h2": 0.80, "yield_h3": 0.60
    },
}
