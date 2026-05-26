"""
core/energy_labour.py
─────────────────────────────────────────────────────────────────────────────
Global electricity price and labour cost reference module.

Architecture
------------
Two pure lookup functions are the primary interface:
    get_energy_rates(country_code: str) -> dict
    get_labour_rates(country_code: str) -> dict

Both return instantly from static matrices (no I/O, safe to call anywhere).

Live API layer (optional, opt-in):
    fetch_live_energy(country_code, secrets) -> dict | None
    fetch_live_labour(country_code, secrets) -> dict | None

These attempt real-time overrides where server-accessible APIs exist and
fall back to None on any failure. Callers decide whether to use the live
value or the static baseline.

APIs that work from Streamlit Cloud (confirmed server-accessible):
  - EIA v2  (US electricity)     — free key, st.secrets["EIA_KEY"]
  - BLS v2  (US manufacturing)   — free key, st.secrets["BLS_KEY"] (optional)
  - ENTSO-E (EU day-ahead spot)  — free registration, st.secrets["ENTSOE_KEY"]

APIs that are blocked from cloud datacenter IPs (do NOT use):
  - aWATTar public demo          — blocks non-browser / datacenter IPs
  - Nord Pool public endpoint    — same restriction
  - ONS Brazil CKAN endpoint     — same restriction

Static data sources
-------------------
Energy: IEA World Energy Prices 2023, Eurostat nrg_pc_205 H2 2023,
        national regulator publications. Industrial tariff used throughout
        (non-household commercial rate — appropriate for CEA operations).
Labour: ILO/ILOSTAT + national statistical agencies. Base hourly wage
        × overhead multiplier = true employer cost (wages + social
        contributions + mandatory benefits). Methodology matches the
        existing COUNTRIES table in core/data_tables.py.

Integration with core/data_tables.py COUNTRIES table
------------------------------------------------------
The existing COUNTRIES table uses country NAME as key and carries a single
kwh rate and a single labour rate. This module provides:
  - A second kwh rate (retail vs industrial split)
  - Source attribution per country
  - Coverage for ~95 additional countries not in COUNTRIES
  - Live override layer for US and EU

Use get_energy_rates(iso2) / get_labour_rates(iso2) directly, or use the
bridge function get_rates_for_country_name(name) which accepts the country
name strings used in the COUNTRIES table.

Last data update: 2024-Q4
"""

import requests
from datetime import datetime, timezone

# ─────────────────────────────────────────────────────────────────────────────
# COUNTRY NAME → ISO-2 BRIDGE
# Maps every country name used in core/data_tables.py COUNTRIES to its ISO code
# ─────────────────────────────────────────────────────────────────────────────

COUNTRY_NAME_TO_ISO = {
    "Germany":             "DE",
    "France":              "FR",
    "Italy":               "IT",
    "Spain":               "ES",
    "Netherlands":         "NL",
    "Belgium":             "BE",
    "Austria":             "AT",
    "Sweden":              "SE",
    "Finland":             "FI",
    "Norway":              "NO",
    "Switzerland":         "CH",
    "United Kingdom":      "GB",
    "Denmark":             "DK",
    "Portugal":            "PT",
    "Greece":              "GR",
    "Ireland":             "IE",
    "Poland":              "PL",
    "Czech Republic":      "CZ",
    "Romania":             "RO",
    "Hungary":             "HU",
    "Slovakia":            "SK",
    "Bulgaria":            "BG",
    "Croatia":             "HR",
    "Slovenia":            "SI",
    "Lithuania":           "LT",
    "Latvia":              "LV",
    "Estonia":             "EE",
    "United States":       "US",
    "Canada":              "CA",
    "Australia":           "AU",
    "Japan":               "JP",
    "China":               "CN",
    "India":               "IN",
    "South Korea":         "KR",
    "Singapore":           "SG",
    "United Arab Emirates":"AE",
    "Saudi Arabia":        "SA",
    "Turkey":              "TR",
    "Brazil":              "BR",
    "Mexico":              "MX",
    "South Africa":        "ZA",
    "Egypt":               "EG",
    "Israel":              "IL",
    "New Zealand":         "NZ",
    "Ukraine":             "UA",
    "Argentina":           "AR",
}

# ─────────────────────────────────────────────────────────────────────────────
# ENERGY PRICE MATRIX
# retail  = consumer/residential tariff ($/kWh)
# industrial = commercial/industrial tariff ($/kWh) ← what CEA farms pay
# source  = regulatory authority / data origin
# ─────────────────────────────────────────────────────────────────────────────

_ENERGY = {
    # ── NORTH & CENTRAL AMERICA ──────────────────────────────────────────────
    "US": {"retail": 0.160, "industrial": 0.080, "source": "EIA (US Energy Information Administration)"},
    "CA": {"retail": 0.120, "industrial": 0.070, "source": "Provincial utilities (Hydro-Québec baseline)"},
    "MX": {"retail": 0.100, "industrial": 0.080, "source": "CFE (Comisión Federal de Electricidad)"},
    "GT": {"retail": 0.220, "industrial": 0.160, "source": "CNEE Guatemala"},
    "BZ": {"retail": 0.210, "industrial": 0.180, "source": "Belize Electricity Limited"},
    "SV": {"retail": 0.240, "industrial": 0.170, "source": "SIGET El Salvador"},
    "HN": {"retail": 0.210, "industrial": 0.160, "source": "ENEE Honduras"},
    "NI": {"retail": 0.260, "industrial": 0.190, "source": "INE Nicaragua"},
    "CR": {"retail": 0.150, "industrial": 0.120, "source": "ICE Costa Rica"},
    "PA": {"retail": 0.180, "industrial": 0.140, "source": "ASEP Panama"},
    "CU": {"retail": 0.030, "industrial": 0.050, "source": "Unión Eléctrica (heavily subsidised)"},
    "JM": {"retail": 0.300, "industrial": 0.240, "source": "Jamaica Public Service Company"},
    "HT": {"retail": 0.350, "industrial": 0.300, "source": "Électricité d'Haïti"},
    "DO": {"retail": 0.200, "industrial": 0.160, "source": "SIE Dominican Republic"},
    "PR": {"retail": 0.230, "industrial": 0.200, "source": "PREPA / LUMA Energy"},
    "TT": {"retail": 0.050, "industrial": 0.040, "source": "T&TEC Trinidad & Tobago"},
    "BS": {"retail": 0.320, "industrial": 0.280, "source": "Bahamas Power and Light"},
    "BB": {"retail": 0.340, "industrial": 0.290, "source": "Barbados Light & Power"},

    # ── SOUTH AMERICA ────────────────────────────────────────────────────────
    "BR": {"retail": 0.170, "industrial": 0.130, "source": "ANEEL / ONS Brazil"},
    "AR": {"retail": 0.090, "industrial": 0.060, "source": "CAMMESA / ENRE (subsidised)"},
    "CO": {"retail": 0.160, "industrial": 0.130, "source": "XM / CREG Colombia"},
    "PE": {"retail": 0.180, "industrial": 0.110, "source": "OSINERGMIN Peru"},
    "CL": {"retail": 0.190, "industrial": 0.120, "source": "Coordinador Eléctrico Nacional Chile"},
    "EC": {"retail": 0.100, "industrial": 0.080, "source": "ARCONEL Ecuador"},
    "BO": {"retail": 0.130, "industrial": 0.100, "source": "AE Bolivia"},
    "PY": {"retail": 0.066, "industrial": 0.055, "source": "ANDE Paraguay"},
    "UY": {"retail": 0.220, "industrial": 0.150, "source": "UTE Uruguay"},
    "VE": {"retail": 0.010, "industrial": 0.010, "source": "Corpoelec (hyper-subsidised/volatile)"},
    "GY": {"retail": 0.260, "industrial": 0.240, "source": "Guyana Power and Light"},
    "SR": {"retail": 0.060, "industrial": 0.050, "source": "N.V. EBS Suriname"},

    # ── EUROPE ───────────────────────────────────────────────────────────────
    # Note: ENTSO-E live override available for EU countries (see fetch_live_energy)
    "GB": {"retail": 0.410, "industrial": 0.250, "source": "Ofgem / Elexon UK"},
    "DE": {"retail": 0.400, "industrial": 0.200, "source": "Bundesnetzagentur — Eurostat nrg_pc_205 H2 2023"},
    "FR": {"retail": 0.280, "industrial": 0.140, "source": "CRE France — Eurostat nrg_pc_205 H2 2023"},
    "IT": {"retail": 0.350, "industrial": 0.180, "source": "ARERA Italy — Eurostat nrg_pc_205 H2 2023"},
    "ES": {"retail": 0.240, "industrial": 0.140, "source": "OMIE / Red Eléctrica España — Eurostat H2 2023"},
    "NL": {"retail": 0.350, "industrial": 0.170, "source": "ACM Netherlands — Eurostat nrg_pc_205 H2 2023"},
    "BE": {"retail": 0.380, "industrial": 0.160, "source": "CREG Belgium — Eurostat nrg_pc_205 H2 2023"},
    "CH": {"retail": 0.260, "industrial": 0.180, "source": "ElCom Switzerland"},
    "AT": {"retail": 0.270, "industrial": 0.150, "source": "E-Control Austria — Eurostat H2 2023"},
    "SE": {"retail": 0.180, "industrial": 0.090, "source": "Nord Pool / Energimarknadsinspektionen"},
    "NO": {"retail": 0.140, "industrial": 0.070, "source": "Nord Pool / NVE Norway"},
    "FI": {"retail": 0.190, "industrial": 0.090, "source": "Nord Pool / Energiavirasto Finland"},
    "DK": {"retail": 0.440, "industrial": 0.120, "source": "Nord Pool / Energistyrelsen Denmark"},
    "PT": {"retail": 0.230, "industrial": 0.130, "source": "ERSE Portugal — Eurostat H2 2023"},
    "GR": {"retail": 0.240, "industrial": 0.150, "source": "RAE Greece — Eurostat H2 2023"},
    "IE": {"retail": 0.450, "industrial": 0.220, "source": "CRU Ireland — Eurostat H2 2023"},
    "PL": {"retail": 0.250, "industrial": 0.160, "source": "URE Poland — Eurostat H2 2023"},
    "CZ": {"retail": 0.320, "industrial": 0.170, "source": "ERÚ Czech Republic — Eurostat H2 2023"},
    "RO": {"retail": 0.200, "industrial": 0.140, "source": "ANRE Romania — Eurostat H2 2023"},
    "HU": {"retail": 0.100, "industrial": 0.180, "source": "MEKH Hungary (state-capped retail)"},
    "SK": {"retail": 0.210, "industrial": 0.150, "source": "ÚRSO Slovakia — Eurostat H2 2023"},
    "BG": {"retail": 0.130, "industrial": 0.140, "source": "EWRC Bulgaria — Eurostat H2 2023"},
    "HR": {"retail": 0.160, "industrial": 0.140, "source": "HERA Croatia — Eurostat H2 2023"},
    "RS": {"retail": 0.090, "industrial": 0.110, "source": "AERS / EPS Serbia"},
    "SI": {"retail": 0.200, "industrial": 0.130, "source": "AGEN-RS Slovenia — Eurostat H2 2023"},
    "LT": {"retail": 0.280, "industrial": 0.170, "source": "VERT Lithuania — Eurostat H2 2023"},
    "LV": {"retail": 0.290, "industrial": 0.160, "source": "SPRK Latvia — Eurostat H2 2023"},
    "EE": {"retail": 0.220, "industrial": 0.140, "source": "ECA Estonia — Eurostat H2 2023"},
    "UA": {"retail": 0.070, "industrial": 0.150, "source": "Ukrenergo (regulated wartime caps)"},
    "BY": {"retail": 0.080, "industrial": 0.110, "source": "Belenergo"},
    "RU": {"retail": 0.060, "industrial": 0.080, "source": "FAS Russia"},
    "IS": {"retail": 0.150, "industrial": 0.060, "source": "Orkustofnun Iceland"},
    "AL": {"retail": 0.100, "industrial": 0.140, "source": "ERE Albania"},
    "BA": {"retail": 0.090, "industrial": 0.100, "source": "SERC Bosnia & Herzegovina"},
    "MK": {"retail": 0.110, "industrial": 0.140, "source": "ERC North Macedonia"},
    "ME": {"retail": 0.110, "industrial": 0.120, "source": "REGAGEN Montenegro"},
    "MD": {"retail": 0.160, "industrial": 0.150, "source": "ANRE Moldova"},
    "CY": {"retail": 0.340, "industrial": 0.280, "source": "CERA Cyprus — Eurostat H2 2023"},
    "MT": {"retail": 0.150, "industrial": 0.160, "source": "REWS Malta — Eurostat H2 2023"},

    # ── ASIA ─────────────────────────────────────────────────────────────────
    "CN": {"retail": 0.080, "industrial": 0.090, "source": "NDRC China"},
    "IN": {"retail": 0.080, "industrial": 0.100, "source": "CERC / State Discoms India"},
    "JP": {"retail": 0.260, "industrial": 0.180, "source": "METI Japan / regional utilities"},
    "KR": {"retail": 0.110, "industrial": 0.090, "source": "KEPCO South Korea"},
    "ID": {"retail": 0.100, "industrial": 0.070, "source": "PLN Indonesia"},
    "PK": {"retail": 0.070, "industrial": 0.120, "source": "NEPRA Pakistan"},
    "BD": {"retail": 0.060, "industrial": 0.090, "source": "BPDB Bangladesh"},
    "PH": {"retail": 0.200, "industrial": 0.140, "source": "ERC / Meralco Philippines"},
    "VN": {"retail": 0.080, "industrial": 0.070, "source": "EVN Vietnam"},
    "TH": {"retail": 0.120, "industrial": 0.100, "source": "ERC Thailand"},
    "MY": {"retail": 0.060, "industrial": 0.080, "source": "TNB Malaysia"},
    "SG": {"retail": 0.220, "industrial": 0.190, "source": "EMA Singapore"},
    "TW": {"retail": 0.100, "industrial": 0.090, "source": "Taipower Taiwan"},
    "LK": {"retail": 0.120, "industrial": 0.150, "source": "CEB / PUCSL Sri Lanka"},
    "MM": {"retail": 0.040, "industrial": 0.060, "source": "MOEE Myanmar"},
    "KH": {"retail": 0.150, "industrial": 0.140, "source": "EAC Cambodia"},
    "LA": {"retail": 0.050, "industrial": 0.060, "source": "EdL Laos"},
    "BN": {"retail": 0.040, "industrial": 0.050, "source": "DES Brunei"},
    "NP": {"retail": 0.080, "industrial": 0.090, "source": "NEA Nepal"},
    "MN": {"retail": 0.050, "industrial": 0.060, "source": "ERC Mongolia"},
    "UZ": {"retail": 0.030, "industrial": 0.040, "source": "Ministry of Energy Uzbekistan"},
    "KZ": {"retail": 0.050, "industrial": 0.060, "source": "KEGOC Kazakhstan"},
    "KG": {"retail": 0.010, "industrial": 0.030, "source": "State Regulatory Agency Kyrgyzstan"},
    "TJ": {"retail": 0.020, "industrial": 0.040, "source": "Barki Tojik Tajikistan"},
    "TM": {"retail": 0.010, "industrial": 0.010, "source": "Ministry of Energy Turkmenistan"},
    "AF": {"retail": 0.040, "industrial": 0.060, "source": "DABS Afghanistan"},
    "IR": {"retail": 0.010, "industrial": 0.020, "source": "TAVANIR Iran (heavily subsidised)"},

    # ── MIDDLE EAST ──────────────────────────────────────────────────────────
    "SA": {"retail": 0.050, "industrial": 0.040, "source": "SEC Saudi Arabia"},
    "AE": {"retail": 0.080, "industrial": 0.050, "source": "DEWA / ADDC UAE"},
    "IL": {"retail": 0.160, "industrial": 0.110, "source": "Electricity Authority Israel"},
    "TR": {"retail": 0.060, "industrial": 0.090, "source": "EMRA Turkey"},
    "IQ": {"retail": 0.020, "industrial": 0.030, "source": "Ministry of Electricity Iraq"},
    "QA": {"retail": 0.030, "industrial": 0.030, "source": "Kahramaa Qatar"},
    "KW": {"retail": 0.010, "industrial": 0.010, "source": "MEW Kuwait"},
    "OM": {"retail": 0.040, "industrial": 0.040, "source": "OETC / APSR Oman"},
    "BH": {"retail": 0.080, "industrial": 0.070, "source": "EWA Bahrain"},
    "JO": {"retail": 0.100, "industrial": 0.140, "source": "EMRC Jordan"},
    "LB": {"retail": 0.080, "industrial": 0.120, "source": "EDL Lebanon"},
    "SY": {"retail": 0.020, "industrial": 0.030, "source": "Ministry of Electricity Syria"},
    "YE": {"retail": 0.080, "industrial": 0.100, "source": "PEC Yemen"},

    # ── AFRICA ───────────────────────────────────────────────────────────────
    "ZA": {"retail": 0.150, "industrial": 0.090, "source": "Eskom / NERSA South Africa"},
    "EG": {"retail": 0.040, "industrial": 0.030, "source": "EgyptERA"},
    "NG": {"retail": 0.050, "industrial": 0.060, "source": "NERC Nigeria"},
    "DZ": {"retail": 0.040, "industrial": 0.030, "source": "Sonelgaz / CREG Algeria"},
    "MA": {"retail": 0.110, "industrial": 0.100, "source": "ONEE Morocco"},
    "KE": {"retail": 0.210, "industrial": 0.150, "source": "EPRA / Kenya Power"},
    "ET": {"retail": 0.010, "industrial": 0.020, "source": "EEU Ethiopia"},
    "GH": {"retail": 0.110, "industrial": 0.130, "source": "PURC Ghana"},
    "TZ": {"retail": 0.100, "industrial": 0.080, "source": "EWURA / TANESCO Tanzania"},
    "UG": {"retail": 0.190, "industrial": 0.150, "source": "ERA / Umeme Uganda"},
    "CI": {"retail": 0.120, "industrial": 0.110, "source": "CIE Côte d'Ivoire"},
    "SN": {"retail": 0.170, "industrial": 0.160, "source": "CRSE / Senelec Senegal"},
    "CM": {"retail": 0.130, "industrial": 0.140, "source": "ARSEL / Eneo Cameroon"},
    "AO": {"retail": 0.030, "industrial": 0.040, "source": "IRSEA / ENDE Angola"},
    "MZ": {"retail": 0.110, "industrial": 0.080, "source": "EDM Mozambique"},
    "ZM": {"retail": 0.040, "industrial": 0.050, "source": "ERB / ZESCO Zambia"},
    "ZW": {"retail": 0.100, "industrial": 0.120, "source": "ZERA / ZESA Zimbabwe"},
    "BW": {"retail": 0.100, "industrial": 0.080, "source": "BPC Botswana"},
    "NA": {"retail": 0.130, "industrial": 0.110, "source": "ECB / NamPower Namibia"},
    "SD": {"retail": 0.020, "industrial": 0.030, "source": "SEDC Sudan"},
    "TN": {"retail": 0.080, "industrial": 0.070, "source": "STEG Tunisia"},
    "LY": {"retail": 0.010, "industrial": 0.020, "source": "GECOL Libya"},
    "RW": {"retail": 0.220, "industrial": 0.150, "source": "RURA / REG Rwanda"},
    "MG": {"retail": 0.160, "industrial": 0.180, "source": "JIRAMA Madagascar"},
    "ML": {"retail": 0.180, "industrial": 0.160, "source": "EDM-SA Mali"},
    "BF": {"retail": 0.200, "industrial": 0.180, "source": "SONABEL Burkina Faso"},

    # ── OCEANIA ──────────────────────────────────────────────────────────────
    "AU": {"retail": 0.250, "industrial": 0.120, "source": "AEMO Australia"},
    "NZ": {"retail": 0.200, "industrial": 0.110, "source": "Electricity Authority New Zealand"},
    "FJ": {"retail": 0.160, "industrial": 0.140, "source": "Energy Fiji Limited"},
    "PG": {"retail": 0.300, "industrial": 0.250, "source": "PNG Power"},
    "NC": {"retail": 0.350, "industrial": 0.300, "source": "Enercal New Caledonia"},
    "PF": {"retail": 0.360, "industrial": 0.320, "source": "EDT Engie French Polynesia"},
}

# ─────────────────────────────────────────────────────────────────────────────
# LABOUR COST MATRIX
# Values are BASE hourly rates in USD before overhead multiplier
# The overhead multiplier captures mandatory employer social contributions,
# payroll taxes, insurance, and statutory benefits (same methodology as the
# existing COUNTRIES table — "fully loaded" employer cost)
# general    = general/minimum wage track (unskilled/entry level)
# industrial = skilled industrial/operational track (relevant for CEA)
# overhead   = employer cost multiplier (1.0 = base wage only, 1.25 = +25% burden)
# source     = national statistical authority
#
# NOTE: The overhead multiplier is applied by get_labour_rates() to produce
# the fully-loaded cost. Do NOT pre-apply it when reading the matrix directly.
# ─────────────────────────────────────────────────────────────────────────────

_LABOUR = {
    # ── NORTH & CENTRAL AMERICA ──────────────────────────────────────────────
    "US": {"general": 15.00, "industrial": 30.10, "overhead": 1.30, "source": "US BLS ECEC Survey"},
    "CA": {"general": 12.10, "industrial": 23.40, "overhead": 1.16, "source": "Statistics Canada Labour Remuneration Index"},
    "MX": {"general":  1.80, "industrial":  4.90, "overhead": 1.35, "source": "INEGI / IMSS employer contribution scales"},
    "GT": {"general":  1.50, "industrial":  2.80, "overhead": 1.22, "source": "IGSS Guatemala"},
    "BZ": {"general":  2.50, "industrial":  4.10, "overhead": 1.10, "source": "Social Security Board Belize"},
    "SV": {"general":  1.40, "industrial":  2.60, "overhead": 1.15, "source": "ISSS El Salvador"},
    "HN": {"general":  1.25, "industrial":  2.40, "overhead": 1.14, "source": "IHSS Honduras"},
    "NI": {"general":  0.95, "industrial":  1.85, "overhead": 1.23, "source": "INSS Nicaragua"},
    "CR": {"general":  3.10, "industrial":  5.40, "overhead": 1.26, "source": "CCSS Costa Rica"},
    "PA": {"general":  2.20, "industrial":  4.80, "overhead": 1.22, "source": "CSS Panamá"},
    "CU": {"general":  0.15, "industrial":  0.40, "overhead": 1.25, "source": "ONEI Cuba national wage scale"},
    "JM": {"general":  1.80, "industrial":  3.50, "overhead": 1.12, "source": "NIS Jamaica"},
    "HT": {"general":  0.65, "industrial":  1.20, "overhead": 1.08, "source": "OFATMA Haiti"},
    "DO": {"general":  1.40, "industrial":  2.90, "overhead": 1.20, "source": "TSS Dominican Republic"},
    "PR": {"general": 10.50, "industrial": 15.80, "overhead": 1.15, "source": "US BLS / PR Dept of Labor"},
    "TT": {"general":  3.00, "industrial":  6.50, "overhead": 1.14, "source": "NIBTT Trinidad & Tobago"},
    "BS": {"general":  5.25, "industrial":  9.50, "overhead": 1.09, "source": "National Insurance Board Bahamas"},
    "BB": {"general":  4.25, "industrial":  8.00, "overhead": 1.12, "source": "NIS Barbados"},

    # ── SOUTH AMERICA ────────────────────────────────────────────────────────
    "BR": {"general":  1.15, "industrial":  4.20, "overhead": 1.58, "source": "FGTS / INSS Brazil (encargos sociais)"},
    "AR": {"general":  1.10, "industrial":  3.80, "overhead": 1.45, "source": "INDEC / SUSS Argentina"},
    "CO": {"general":  1.30, "industrial":  3.10, "overhead": 1.52, "source": "SENA / ICBF / Colpensiones Colombia"},
    "PE": {"general":  1.25, "industrial":  3.40, "overhead": 1.40, "source": "EsSalud / CTS Peru"},
    "CL": {"general":  2.60, "industrial":  6.80, "overhead": 1.15, "source": "Mutual de Seguridad / AFC Chile"},
    "EC": {"general":  2.65, "industrial":  4.10, "overhead": 1.22, "source": "IESS Ecuador"},
    "BO": {"general":  1.40, "industrial":  2.90, "overhead": 1.17, "source": "Ministerio de Trabajo Bolivia"},
    "PY": {"general":  1.45, "industrial":  3.20, "overhead": 1.27, "source": "IPS Paraguay"},
    "UY": {"general":  2.90, "industrial":  7.10, "overhead": 1.31, "source": "BPS Uruguay"},
    "VE": {"general":  0.05, "industrial":  1.50, "overhead": 1.30, "source": "IVSS Venezuela (volatile)"},
    "GY": {"general":  1.80, "industrial":  3.90, "overhead": 1.08, "source": "NIS Guyana"},
    "SR": {"general":  1.10, "industrial":  2.80, "overhead": 1.10, "source": "Ministry of Labor Suriname"},

    # ── EUROPE ───────────────────────────────────────────────────────────────
    # Industrial rates are skilled operational/manufacturing wages (not senior management)
    # Overhead covers employer social security, pension, insurance, mandatory levies
    "GB": {"general": 14.50, "industrial": 26.20, "overhead": 1.14, "source": "ONS UK / HMRC Class 1 National Insurance"},
    "DE": {"general": 13.40, "industrial": 30.50, "overhead": 1.22, "source": "Destatis Lohnnebenkosten (manufacturing sector average)"},
    "FR": {"general": 12.60, "industrial": 22.80, "overhead": 1.44, "source": "URSSAF corporate social contributions"},
    "IT": {"general":  9.50, "industrial": 19.40, "overhead": 1.38, "source": "INPS / INAIL Italy"},
    "ES": {"general":  8.80, "industrial": 16.30, "overhead": 1.32, "source": "Seguridad Social España"},
    "NL": {"general": 14.10, "industrial": 31.50, "overhead": 1.28, "source": "CBS Netherlands premium employer overhead"},
    "BE": {"general": 13.10, "industrial": 29.80, "overhead": 1.30, "source": "ONSS Belgium"},
    "CH": {"general": 24.50, "industrial": 36.10, "overhead": 1.14, "source": "FSO Switzerland AHV/ALV"},
    "AT": {"general": 11.80, "industrial": 25.50, "overhead": 1.29, "source": "Statistik Austria non-wage labour"},
    "SE": {"general": 14.80, "industrial": 26.20, "overhead": 1.31, "source": "SCB Sweden arbetsgivaravgifter"},
    "NO": {"general": 21.20, "industrial": 35.40, "overhead": 1.14, "source": "SSB Norway arbeidsgiveravgift"},
    "FI": {"general": 12.90, "industrial": 24.10, "overhead": 1.21, "source": "Statistics Finland indirect labour costs"},
    "DK": {"general": 22.40, "industrial": 38.10, "overhead": 1.05, "source": "Danmarks Statistik ATP"},
    "PT": {"general":  5.40, "industrial": 10.20, "overhead": 1.24, "source": "Segurança Social Portugal TSU"},
    "GR": {"general":  5.10, "industrial":  9.50, "overhead": 1.22, "source": "EFKA Greece"},
    "IE": {"general": 13.80, "industrial": 22.40, "overhead": 1.11, "source": "Revenue Commissioners Ireland Class A PRSI"},
    "PL": {"general":  4.80, "industrial":  8.20, "overhead": 1.21, "source": "ZUS Poland"},
    "CZ": {"general":  5.10, "industrial":  9.40, "overhead": 1.34, "source": "ČSSZ Czech Republic"},
    "RO": {"general":  3.80, "industrial":  6.40, "overhead": 1.03, "source": "ANAF Romania (CAM tax)"},
    "HU": {"general":  4.10, "industrial":  7.90, "overhead": 1.13, "source": "NAV Hungary social contribution tax"},
    "SK": {"general":  4.50, "industrial":  8.20, "overhead": 1.35, "source": "Sociálna poisťovňa Slovakia"},
    "BG": {"general":  2.80, "industrial":  5.40, "overhead": 1.19, "source": "NSSI Bulgaria"},
    "HR": {"general":  4.90, "industrial":  8.10, "overhead": 1.17, "source": "HZZO / HZMO Croatia"},
    "RS": {"general":  2.70, "industrial":  4.80, "overhead": 1.15, "source": "Tax Administration Serbia"},
    "SI": {"general":  8.20, "industrial": 14.40, "overhead": 1.16, "source": "ZPIZ / ZZZS Slovenia"},
    "LT": {"general":  5.90, "industrial": 10.10, "overhead": 1.02, "source": "Sodra Lithuania"},
    "LV": {"general":  4.60, "industrial":  8.80, "overhead": 1.24, "source": "VSAA Latvia"},
    "EE": {"general":  5.40, "industrial": 10.90, "overhead": 1.33, "source": "Estonian Tax and Customs Board"},
    "UA": {"general":  1.20, "industrial":  3.10, "overhead": 1.22, "source": "State Tax Service Ukraine (ERU)"},
    "BY": {"general":  1.45, "industrial":  4.10, "overhead": 1.34, "source": "FSZN Belarus"},
    "RU": {"general":  1.10, "industrial":  4.50, "overhead": 1.30, "source": "SFR Russia unified insurance"},
    "IS": {"general": 19.50, "industrial": 32.60, "overhead": 1.06, "source": "RSK Iceland tryggingagjald"},
    "AL": {"general":  2.10, "industrial":  4.20, "overhead": 1.17, "source": "General Directorate of Taxes Albania"},
    "BA": {"general":  2.30, "industrial":  4.90, "overhead": 1.11, "source": "Tax Administration BiH / RS"},
    "MK": {"general":  2.40, "industrial":  5.10, "overhead": 1.27, "source": "Public Revenue Office North Macedonia"},
    "ME": {"general":  3.10, "industrial":  6.20, "overhead": 1.21, "source": "Tax Administration Montenegro"},
    "MD": {"general":  1.60, "industrial":  3.80, "overhead": 1.24, "source": "CNAS Moldova"},
    "CY": {"general":  6.20, "industrial": 12.40, "overhead": 1.12, "source": "Social Insurance Services Cyprus"},
    "MT": {"general":  5.80, "industrial": 11.10, "overhead": 1.10, "source": "Commissioner for Revenue Malta"},

    # ── ASIA ─────────────────────────────────────────────────────────────────
    "CN": {"general":  1.90, "industrial":  6.40, "overhead": 1.38, "source": "China Social Insurance Bureau (5 social pools + housing fund)"},
    "IN": {"general":  0.90, "industrial":  2.40, "overhead": 1.20, "source": "EPFO & ESIC India"},
    "JP": {"general":  7.20, "industrial": 14.50, "overhead": 1.16, "source": "MHLW Japan shakai hoken"},
    "KR": {"general":  7.40, "industrial": 18.10, "overhead": 1.12, "source": "National Health & Pension South Korea"},
    "ID": {"general":  1.10, "industrial":  2.30, "overhead": 1.11, "source": "BPJS Ketenagakerjaan Indonesia"},
    "PK": {"general":  0.85, "industrial":  1.90, "overhead": 1.07, "source": "EOBI Pakistan"},
    "BD": {"general":  0.55, "industrial":  1.40, "overhead": 1.05, "source": "Bangladesh Labour Act"},
    "PH": {"general":  1.40, "industrial":  2.90, "overhead": 1.10, "source": "SSS / PhilHealth / Pag-IBIG Philippines"},
    "VN": {"general":  0.95, "industrial":  2.60, "overhead": 1.22, "source": "Social Insurance Agency Vietnam"},
    "TH": {"general":  1.55, "industrial":  3.40, "overhead": 1.05, "source": "SSO Thailand"},
    "MY": {"general":  1.60, "industrial":  4.10, "overhead": 1.13, "source": "EPF (KWSP) / SOCSO Malaysia"},
    "SG": {"general":  9.00, "industrial": 18.80, "overhead": 1.17, "source": "CPF Singapore employer contribution"},
    "TW": {"general":  5.60, "industrial": 10.40, "overhead": 1.15, "source": "Labor Insurance Bureau Taiwan"},
    "LK": {"general":  0.70, "industrial":  1.60, "overhead": 1.15, "source": "EPF / ETF Sri Lanka"},
    "MM": {"general":  0.35, "industrial":  0.95, "overhead": 1.03, "source": "Social Security Board Myanmar"},
    "KH": {"general":  0.98, "industrial":  1.80, "overhead": 1.04, "source": "NSSF Cambodia"},
    "LA": {"general":  0.45, "industrial":  1.10, "overhead": 1.06, "source": "NSSF Laos"},
    "BN": {"general":  2.10, "industrial":  4.90, "overhead": 1.05, "source": "TAP / SCP Brunei"},
    "NP": {"general":  0.70, "industrial":  1.40, "overhead": 1.11, "source": "SSF Nepal"},
    "MN": {"general":  1.15, "industrial":  2.80, "overhead": 1.13, "source": "Social Insurance General Office Mongolia"},
    "UZ": {"general":  0.50, "industrial":  1.30, "overhead": 1.12, "source": "State Tax Committee Uzbekistan"},
    "KZ": {"general":  1.20, "industrial":  3.40, "overhead": 1.11, "source": "Ministry of Labor Kazakhstan"},
    "KG": {"general":  0.30, "industrial":  0.90, "overhead": 1.17, "source": "Social Fund Kyrgyzstan"},
    "TJ": {"general":  0.25, "industrial":  0.75, "overhead": 1.25, "source": "Tax Committee Tajikistan"},
    "TM": {"general":  0.90, "industrial":  2.10, "overhead": 1.20, "source": "Pension Fund Turkmenistan"},
    "AF": {"general":  0.40, "industrial":  0.95, "overhead": 1.05, "source": "Ministry of Finance Afghanistan"},
    "IR": {"general":  0.80, "industrial":  2.20, "overhead": 1.23, "source": "Social Security Organization Iran"},

    # ── MIDDLE EAST ──────────────────────────────────────────────────────────
    "SA": {"general":  2.80, "industrial":  7.50, "overhead": 1.12, "source": "GOSI Saudi Arabia"},
    "AE": {"general":  3.50, "industrial":  9.20, "overhead": 1.13, "source": "GPSSA UAE"},
    "IL": {"general":  8.40, "industrial": 16.60, "overhead": 1.07, "source": "National Insurance Institute Israel"},
    "TR": {"general":  2.90, "industrial":  5.40, "overhead": 1.21, "source": "SGK Turkey"},
    "IQ": {"general":  1.10, "industrial":  2.60, "overhead": 1.12, "source": "Ministry of Labor Iraq"},
    "QA": {"general":  2.75, "industrial":  6.80, "overhead": 1.14, "source": "GRPIA Qatar"},
    "KW": {"general":  3.25, "industrial":  8.10, "overhead": 1.11, "source": "PIFSS Kuwait"},
    "OM": {"general":  3.30, "industrial":  7.40, "overhead": 1.11, "source": "PASI Oman"},
    "BH": {"general":  3.90, "industrial":  8.40, "overhead": 1.12, "source": "SIO Bahrain"},
    "JO": {"general":  1.45, "industrial":  3.10, "overhead": 1.14, "source": "SSC Jordan"},
    "LB": {"general":  0.50, "industrial":  2.20, "overhead": 1.22, "source": "NSSF Lebanon"},
    "SY": {"general":  0.15, "industrial":  0.90, "overhead": 1.15, "source": "Social Insurance Institution Syria"},
    "YE": {"general":  0.40, "industrial":  1.10, "overhead": 1.09, "source": "GCSS Yemen"},

    # ── AFRICA ───────────────────────────────────────────────────────────────
    "ZA": {"general":  1.55, "industrial":  5.40, "overhead": 1.04, "source": "SARS South Africa COIDA/UIF"},
    "EG": {"general":  0.60, "industrial":  1.40, "overhead": 1.12, "source": "NOSI Egypt"},
    "NG": {"general":  0.45, "industrial":  1.20, "overhead": 1.12, "source": "NSITF / PenCom Nigeria"},
    "DZ": {"general":  0.95, "industrial":  2.40, "overhead": 1.26, "source": "CNAS Algeria"},
    "MA": {"general":  1.65, "industrial":  3.60, "overhead": 1.21, "source": "CNSS Morocco"},
    "KE": {"general":  0.85, "industrial":  2.10, "overhead": 1.06, "source": "NSSF / NHIF Kenya"},
    "ET": {"general":  0.30, "industrial":  0.80, "overhead": 1.11, "source": "POESSA Ethiopia"},
    "GH": {"general":  0.55, "industrial":  1.40, "overhead": 1.13, "source": "SSNIT Ghana"},
    "TZ": {"general":  0.45, "industrial":  1.10, "overhead": 1.15, "source": "NSSF / WCF Tanzania"},
    "UG": {"general":  0.25, "industrial":  0.95, "overhead": 1.10, "source": "NSSF Uganda"},
    "CI": {"general":  0.65, "industrial":  1.80, "overhead": 1.14, "source": "CNPS Côte d'Ivoire"},
    "SN": {"general":  0.60, "industrial":  1.60, "overhead": 1.16, "source": "IPRES / CSS Senegal"},
    "CM": {"general":  0.55, "industrial":  1.45, "overhead": 1.16, "source": "CNPS Cameroon"},
    "AO": {"general":  0.40, "industrial":  1.30, "overhead": 1.08, "source": "INSS Angola"},
    "MZ": {"general":  0.50, "industrial":  1.20, "overhead": 1.04, "source": "INSS Mozambique"},
    "ZM": {"general":  0.45, "industrial":  1.15, "overhead": 1.06, "source": "NAPSA Zambia"},
    "ZW": {"general":  0.60, "industrial":  1.70, "overhead": 1.05, "source": "NSSA Zimbabwe"},
    "BW": {"general":  0.95, "industrial":  2.60, "overhead": 1.02, "source": "Botswana Unified Revenue Service"},
    "NA": {"general":  1.10, "industrial":  3.10, "overhead": 1.03, "source": "SSC Namibia"},
    "SD": {"general":  0.20, "industrial":  0.70, "overhead": 1.17, "source": "SIC Sudan"},
    "TN": {"general":  0.90, "industrial":  2.10, "overhead": 1.16, "source": "CNSS Tunisia"},
    "LY": {"general":  1.20, "industrial":  2.80, "overhead": 1.11, "source": "SSF Libya"},
    "RW": {"general":  0.40, "industrial":  1.10, "overhead": 1.08, "source": "RSSB Rwanda"},
    "MG": {"general":  0.35, "industrial":  0.85, "overhead": 1.13, "source": "CNaPS Madagascar"},
    "ML": {"general":  0.45, "industrial":  1.15, "overhead": 1.22, "source": "INPS Mali"},
    "BF": {"general":  0.50, "industrial":  1.20, "overhead": 1.21, "source": "CNSS Burkina Faso"},

    # ── OCEANIA ──────────────────────────────────────────────────────────────
    "AU": {"general": 16.10, "industrial": 25.40, "overhead": 1.18, "source": "ABS / ATO superannuation guarantee & WorkCover"},
    "NZ": {"general": 14.20, "industrial": 20.80, "overhead": 1.04, "source": "ACC New Zealand employer levies"},
    "FJ": {"general":  1.85, "industrial":  3.90, "overhead": 1.06, "source": "FNPF Fiji"},
    "PG": {"general":  1.10, "industrial":  2.50, "overhead": 1.08, "source": "Nasfund Papua New Guinea"},
    "NC": {"general":  7.40, "industrial": 12.60, "overhead": 1.28, "source": "CAFAT Nouvelle-Calédonie"},
    "PF": {"general":  7.80, "industrial": 13.20, "overhead": 1.26, "source": "CPS Polynésie Française"},
}

# Global fallbacks
_ENERGY_FALLBACK  = {"retail": 0.140, "industrial": 0.100, "source": "GlobalPetrolPrices / World Bank estimate"}
_LABOUR_FALLBACK  = {"general": 2.50, "industrial": 6.50, "overhead": 1.25, "source": "ILO / World Bank global mean"}


# ─────────────────────────────────────────────────────────────────────────────
# PRIMARY INTERFACE — pure dict lookups, no I/O
# ─────────────────────────────────────────────────────────────────────────────

def get_energy_rates(country_code: str) -> dict:
    """
    Return electricity price data for a country.

    Parameters
    ----------
    country_code : str
        ISO 3166-1 alpha-2 code (e.g. "DE", "US"). Case-insensitive.

    Returns
    -------
    dict with keys:
        retail      float  Consumer/residential tariff ($/kWh)
        industrial  float  Industrial/commercial tariff ($/kWh) — use for CEA
        source      str    Regulatory authority / data origin
        live        bool   Whether values come from a live API override
        live_note   str    Description of live data source, if applicable
    """
    base = _ENERGY.get(country_code.upper(), _ENERGY_FALLBACK).copy()
    base.setdefault("live", False)
    base.setdefault("live_note", "")
    return base


def get_labour_rates(country_code: str) -> dict:
    """
    Return fully-loaded employer labour cost for a country.

    The returned hourly_loaded values already incorporate the overhead
    multiplier (employer social contributions, mandatory benefits).

    Parameters
    ----------
    country_code : str
        ISO 3166-1 alpha-2 code. Case-insensitive.

    Returns
    -------
    dict with keys:
        general_loaded      float  Fully-loaded general/min-wage track ($/hr)
        industrial_loaded   float  Fully-loaded industrial/skilled track ($/hr)
        general_base        float  Pre-overhead base hourly rate ($/hr)
        industrial_base     float  Pre-overhead base hourly rate ($/hr)
        overhead            float  Employer overhead multiplier (e.g. 1.22)
        overhead_pct        str    Human-readable overhead e.g. "+22%"
        source              str    Data authority
        live                bool   Whether values come from a live API override
        live_note           str    Description of live data source, if applicable
    """
    raw = _LABOUR.get(country_code.upper(), _LABOUR_FALLBACK).copy()
    mult = raw.get("overhead", 1.25)
    base_gen = raw.get("general", 2.50)
    base_ind = raw.get("industrial", 6.50)
    return {
        "general_base":      round(base_gen, 2),
        "industrial_base":   round(base_ind, 2),
        "general_loaded":    round(base_gen * mult, 2),
        "industrial_loaded": round(base_ind * mult, 2),
        "overhead":          mult,
        "overhead_pct":      f"+{(mult - 1) * 100:.0f}%",
        "source":            raw.get("source", _LABOUR_FALLBACK["source"]),
        "live":              raw.get("live", False),
        "live_note":         raw.get("live_note", ""),
    }


def get_rates_for_country_name(country_name: str) -> dict:
    """
    Convenience wrapper accepting country names from core/data_tables.py COUNTRIES.
    Returns {"energy": {...}, "labour": {...}, "iso": str | None}.
    """
    iso = COUNTRY_NAME_TO_ISO.get(country_name)
    return {
        "iso":    iso,
        "energy": get_energy_rates(iso) if iso else _ENERGY_FALLBACK.copy(),
        "labour": get_labour_rates(iso) if iso else get_labour_rates("GLOBAL"),
    }


# ─────────────────────────────────────────────────────────────────────────────
# LIVE API LAYER — optional, non-blocking
# Call these once on page load and cache with @st.cache_data(ttl=3600)
# Each returns a partial dict to MERGE into the static baseline, or None on failure
# ─────────────────────────────────────────────────────────────────────────────

def fetch_live_energy(country_code: str, secrets: dict) -> dict | None:
    """
    Attempt a live electricity price override for supported countries.

    Supported pipelines
    -------------------
    US  — EIA v2 API (requires EIA_KEY in secrets)
          Returns monthly average retail and industrial prices.
    EU  — ENTSO-E Transparency Platform (requires ENTSOE_KEY in secrets)
          Returns day-ahead spot price (MWh → kWh). Applies to:
          AT, BE, BG, HR, CZ, DK, EE, FI, FR, DE, GR, HU, IE, IT, LV,
          LT, LU, NL, NO, PL, PT, RO, SK, SI, ES, SE, CH, GB

    Parameters
    ----------
    country_code : str   ISO-2 country code
    secrets      : dict  st.secrets or equivalent (keys: EIA_KEY, ENTSOE_KEY)

    Returns
    -------
    dict  with keys: industrial, retail, live=True, live_note, fetched_at
          or None if no live pipeline exists or call fails
    """
    cc = country_code.upper()

    # ── US: EIA v2 API ───────────────────────────────────────────────────────
    if cc == "US":
        key = secrets.get("EIA_KEY", "")
        if not key:
            return None
        try:
            # Retail (all sectors, monthly average cents/kWh → $/kWh)
            retail_url = (
                "https://api.eia.gov/v2/electricity/retail-electricity-sales/data/"
                f"?api_key={key}&frequency=monthly&data[]=price&length=1&sort[0][column]=period&sort[0][direction]=desc"
            )
            r_ret = requests.get(retail_url, timeout=8)
            r_ret.raise_for_status()
            retail_cents = float(r_ret.json()["response"]["data"][0]["price"])
            retail_usd   = round(retail_cents / 100.0, 4)

            # Industrial sector (facets filter)
            ind_url = (
                "https://api.eia.gov/v2/electricity/retail-electricity-sales/data/"
                f"?api_key={key}&frequency=monthly&data[]=price"
                "&facets[sectorName][]=industrial"
                "&length=1&sort[0][column]=period&sort[0][direction]=desc"
            )
            r_ind = requests.get(ind_url, timeout=8)
            r_ind.raise_for_status()
            ind_cents = float(r_ind.json()["response"]["data"][0]["price"])
            ind_usd   = round(ind_cents / 100.0, 4)

            period = r_ret.json()["response"]["data"][0].get("period", "latest")
            return {
                "retail":      retail_usd,
                "industrial":  ind_usd,
                "live":        True,
                "live_note":   f"EIA v2 API — period: {period}",
                "fetched_at":  datetime.now(timezone.utc).isoformat(),
            }
        except Exception:
            return None

    # ── EU + Nordic + UK: ENTSO-E Transparency Platform ─────────────────────
    # Returns day-ahead spot price in EUR/MWh for the given bidding zone
    # This is a wholesale market price — approximate proxy for industrial rate
    _entsoe_zones = {
        "AT": "10YAT-APG------L", "BE": "10YBE----------2",
        "BG": "10YCA-BULGARIA-R", "HR": "10YHR-HEP------M",
        "CZ": "10YCZ-CEPS-----N", "DK": "10Y1001A1001A65H",
        "EE": "10Y1001A1001A39I", "FI": "10YFI-1--------U",
        "FR": "10YFR-RTE------C", "DE": "10Y1001A1001A83F",
        "GR": "10YGR-HTSO-----Y", "HU": "10YHU-MAVIR----U",
        "IE": "10YIE-1001A00010", "IT": "10YIT-GRTN-----B",
        "LV": "10YLV-1001A00074", "LT": "10YLT-10YGEN---W",
        "NL": "10YNL----------L", "NO": "10YNO-0--------C",
        "PL": "10YPL-AREA-----S", "PT": "10YPT-REN------W",
        "RO": "10YRO-TEL------P", "SK": "10YSK-SEPS-----K",
        "SI": "10YSI-ELES-----O", "ES": "10YES-REE------0",
        "SE": "10YSE-1--------K", "CH": "10YCH-SWISSGRID-",
        "GB": "10YGB----------A",
    }
    if cc in _entsoe_zones:
        key = secrets.get("ENTSOE_KEY", "")
        if not key:
            return None
        try:
            zone = _entsoe_zones[cc]
            now  = datetime.now(timezone.utc)
            # Day-ahead prices for today
            period_start = now.strftime("%Y%m%d0000")
            period_end   = now.strftime("%Y%m%d2300")
            url = (
                f"https://web-api.tp.entsoe.eu/api"
                f"?documentType=A44"
                f"&in_Domain={zone}&out_Domain={zone}"
                f"&periodStart={period_start}&periodEnd={period_end}"
                f"&securityToken={key}"
            )
            r = requests.get(url, timeout=10)
            r.raise_for_status()
            # Parse XML — extract mean price from TimeSeries Points
            import xml.etree.ElementTree as ET
            ns = {"ns": "urn:iec62325.351:tc57wg16:451-3:publicationdocument:7:3"}
            root = ET.fromstring(r.text)
            prices = []
            for pt in root.findall(".//ns:Point", ns):
                p_elem = pt.find("ns:price.amount", ns)
                if p_elem is not None:
                    prices.append(float(p_elem.text))
            if not prices:
                return None
            mean_eur_mwh = sum(prices) / len(prices)
            # MWh → kWh, EUR → USD (approximate; update with FX feed if needed)
            EUR_USD = 1.08
            spot_usd_kwh = round(mean_eur_mwh / 1000.0 * EUR_USD, 4)
            # Guard against negative spot prices (renewables surplus events)
            spot_usd_kwh = max(spot_usd_kwh, 0.0)
            return {
                "industrial":  spot_usd_kwh,     # spot ≈ wholesale/industrial proxy
                "live":        True,
                "live_note":   f"ENTSO-E day-ahead mean — zone {zone} — {len(prices)} intervals",
                "fetched_at":  now.isoformat(),
            }
        except Exception:
            return None

    return None  # no live pipeline for this country


def fetch_live_labour(country_code: str, secrets: dict) -> dict | None:
    """
    Attempt a live labour cost override for supported countries.

    Supported pipelines
    -------------------
    US — BLS v2 API, series CES3000000003 (manufacturing avg hourly earnings)
         Key: BLS_KEY in secrets (optional — works without key at low volume)

    Returns
    -------
    dict with keys: industrial_base, live=True, live_note, fetched_at
         or None on failure
    """
    cc = country_code.upper()

    if cc == "US":
        key = secrets.get("BLS_KEY", "")
        headers = {"Content-Type": "application/json"}
        payload = {
            "seriesid": ["CES3000000003"],  # avg hourly earnings, manufacturing
            "startyear": str(datetime.now().year - 1),
            "endyear":   str(datetime.now().year),
        }
        if key:
            payload["registrationkey"] = key
        try:
            r = requests.post(
                "https://api.bls.gov/publicAPI/v2/timeseries/data/",
                json=payload, headers=headers, timeout=8
            )
            r.raise_for_status()
            data = r.json()
            latest = data["Results"]["series"][0]["data"][0]
            base_hourly = float(latest["value"])
            period = f"{latest.get('periodName', '')} {latest.get('year', '')}"
            return {
                "industrial_base":  round(base_hourly, 2),
                "live":             True,
                "live_note":        f"BLS CES3000000003 manufacturing avg hourly earnings — {period}",
                "fetched_at":       datetime.now(timezone.utc).isoformat(),
            }
        except Exception:
            return None

    return None


# ─────────────────────────────────────────────────────────────────────────────
# COMPOSITE HELPER — static + live merged, ready to display in Streamlit
# ─────────────────────────────────────────────────────────────────────────────

def get_full_rates(country_code: str, secrets: dict | None = None) -> dict:
    """
    Return the best available rates: static baseline merged with live override
    where available. Safe to call from Streamlit — all exceptions are caught.

    Parameters
    ----------
    country_code : str   ISO-2 code
    secrets      : dict  st.secrets or {} — if None, live APIs are skipped

    Returns
    -------
    dict:
        energy  : dict from get_energy_rates() + live override applied
        labour  : dict from get_labour_rates() + live override applied
    """
    energy = get_energy_rates(country_code)
    labour = get_labour_rates(country_code)

    if secrets is not None:
        live_e = fetch_live_energy(country_code, secrets)
        if live_e:
            energy.update(live_e)

        live_l = fetch_live_labour(country_code, secrets)
        if live_l:
            # Recalculate loaded rate with updated base
            mult = labour["overhead"]
            if "industrial_base" in live_l:
                new_base = live_l["industrial_base"]
                labour["industrial_base"]   = new_base
                labour["industrial_loaded"] = round(new_base * mult, 2)
                labour["live"]              = True
                labour["live_note"]         = live_l.get("live_note", "")

    return {"energy": energy, "labour": labour}
