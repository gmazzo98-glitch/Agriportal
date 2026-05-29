import streamlit as st

st.set_page_config(page_title="Assumptions & Methodology", page_icon="📋", layout="wide")
from core.auth import require_login, render_user_admin, logout, current_user
require_login() # Keep the page_icon emoji, but remove from title # Keep the page_icon emoji, but remove from title

st.title("Assumptions & Methodology")
st.markdown(
    "This page documents every data source, formula assumption, and modelling choice "
    "used in the ROI Calculator. It exists so that users — whether farmers, investors, "
    "or analysts — can assess the legitimacy of the outputs before acting on them."
)

# ─────────────────────────────────────────────────────────────────────────────
st.divider()
st.header("1. Modelling Philosophy")

st.markdown("""
#### Unit-economics first
The calculator is built from the bottom up. Instead of modelling a facility as a monolithic entity, it decomposes production into measurable technical units — surface area, crop cycles, labour tasks, and energy inputs — and reconstructs economic performance from these foundations.

This approach reflects the structural reality of vertical farming: profitability is driven less by scale alone and more by the interaction between biological performance, operational efficiency, and capital intensity. A unit-economics framework makes these interactions explicit and stress-testable.

#### The square metre as primary unit
Surface area is the fundamental scarce resource in vertical farming and the variable around which most technical decisions are made. By anchoring to m², the model expresses planting density, yield potential, lighting requirements, labour intensity, and capital expenditure intensity on a consistent basis. All downstream quantities — kilograms produced, revenue, labour hours — are derived from this spatial foundation.

#### Cycles, not calendar time
The crop cycle is the fundamental temporal unit. Annual values are derived by scaling cycle-level outputs by the number of feasible cycles per year. This reflects the biological reality that seeds, substrates, and certain labour activities recur at the cycle level, not continuously.

#### The override principle
Every numeric assumption must be visible, documented, and overridable. If a parameter materially affects outputs and cannot be traced to an explicit assumption, it is considered undefined. This ensures users understand not only the outputs but the conditions under which those outputs hold.

#### Conservative defaults
Where biological performance parameters are concerned (yield, cycle duration), the model consistently favours conservative, reproducible assumptions over optimistic outliers. Exceptional performance is a scenario to test, not a baseline expectation.

#### Explicit rejection of black-box proxies
Each major cost driver is represented separately and linked to a concrete unit of measure (e.g. $/hour, kWh, $/m²). Aggregate proxies like purchasing-power-parity indices are not used because vertical farming cost structures do not scale linearly with such indices — labour, energy, water, and capital each follow different dynamics.
""")

# ─────────────────────────────────────────────────────────────────────────────
st.divider()
st.header("2. Farm Geometry")
st.markdown("""
The **Effective Growing Area (EGA)** is the usable plant-facing surface area after accounting for structural and operational losses:
```
EGA = Footprint × Levels × Net Grow Factor × (1 − Walkways Factor)
```

**Default values:**
- **Net Grow Factor: 85%** — proportion of each level's footprint covered by growing trays
  (vs. walls, columns, irrigation headers). Source: commercial CEA operator benchmarks.
- **Walkways Factor: 15%** — proportion of growing area lost to in-aisle movement and technical access.

The model explicitly separates **effective grow area** (scales with yield, lighting, cultivation systems) from **total facility footprint** (scales with logistics, circulation, and building envelope). This prevents double-counting when stacking density is adjusted — increasing vertical levels increases productive area without proportionally inflating all infrastructure costs.

**Tray count** = `floor(EGA / 7.75 m²)`, where 7.75 m² is a standard NFT/DWC module size.
""")

# ─────────────────────────────────────────────────────────────────────────────
st.divider()
st.header("3. Energy Model")
st.markdown("""
```
Daily kWh/m² (lighting) = DLI × 0.2778 / LED Efficacy
Annual kWh/m²           = Daily kWh/m² × Effective Cycle Days × HVAC Factor × Cycles/Year
Annual Energy Cost      = Annual kWh/m² × EGA × Electricity Price
```

**DLI (Daily Light Integral)** is crop-specific (mol/m²/day), sourced from controlled-environment horticulture literature. It represents the photon dose required per day.

**0.2778** is the conversion factor from mol/m²/day to kWh/m²/day (= 1/3.6, derived from the relationship between joules and watt-hours at PAR wavelengths).

**LED Efficacy** (µmol/J): Cheap = 2.3, Basic = 2.7, Top-Tier = 3.2. These reflect commercially available fixture performance as of 2023–2024. A comprehensive review of LED lighting in controlled environments confirms that *state-of-the-art horticultural luminaires commonly achieve photon efficacies exceeding 2.5 µmol/J* (MDPI Sustainability, 2020).

**HVAC Factor** accounts for total facility electricity including HVAC, pumps, and controls — not just lighting. It is modelled as a multiplier on lighting load derived from component ratios:

| Component | Ratio to lighting kWh | Notes |
|---|---|---|
| HVAC / dehumidification / fans | 0.65 | Driven by heat and transpiration load |
| Water / nutrient pumps / UV | 0.06 | Recirculation, filtration |
| Controls / IT / sensors | 0.02 | Controllers, networking |
| Processing / packaging (optional) | 0.10 | Only if included in facility |
| **Non-lighting total** | **0.83** | Sum of above |
| **Total electricity factor** | **1.83** | 1 + 0.83 (Standard HVAC) |

HVAC severity adjusts the HVAC component by a severity multiplier (Excellent = 0.8, Standard = 1.0, High = 1.3), giving final factors of 1.70 / 1.83 / 2.025 respectively.

**Critical:** For multi-harvest crops, `Effective Cycle Days` (not base crop cycle days) is used. This correctly accounts for the extended photoperiod during regrowth gaps between harvests. Lighting constitutes the largest share of electricity demand in indoor vertical farms, followed by HVAC — consistent with life-cycle assessments of indoor farming systems (Journal of Cleaner Production, 2024).
""")

# ─────────────────────────────────────────────────────────────────────────────
st.divider()
st.header("4. Crop Data")
st.markdown("""
The crop database contains **98 crops**. Each crop is a structured dataset separating biological drivers from commercial and cost drivers:

| Field | Description | Basis |
|---|---|---|
| `yield` | kg/m²/cycle (H1) | CEA operator benchmarks + academic literature |
| `cycle` | Days from seeding to first harvest | Seed supplier data + controlled trial literature |
| `seed` | $/m²/cycle | Professional/commercial supplier catalogues. Hobby retail and experimental breeder pricing excluded. |
| `substrate` | $/m²/cycle | Rockwool/coco coir benchmark pricing |
| `ec` | Nutrient solution EC (mS/cm) | Crop-specific hydroponic guidelines. Cornell CEA Lettuce Handbook documents EC ~1.2–1.8 mS/cm for lettuce. |
| `water` | L/m²/cycle | Evapotranspiration proxy. Used as cost driver for nutrient and water costs. |
| `nutrient` | Cost factor (0.005) | Calibrated so that `EC × water × 0.005` lands in the 1–7% of revenue range |
| `dli` | mol/m²/day | Controlled environment horticulture literature. Wageningen University studies confirm leafy greens respond predictably to DLI within a bounded range. |
| `wf` | Water fraction | FAO crop water requirement data |
| `tr` | Transpiration L/kg | Evapotranspiration models |
| `days_between` | Gap days between harvests (0 = single harvest only) | Operator trial data |
| `yield_h2`, `yield_h3` | H2/H3 yield as fraction of H1 | Regrowth trial literature |

**Important caveats:**
- Yield figures are **benchmark values under optimised conditions**. Actual farm yields typically
  land 10–30% below benchmark in the first year of operation.
- Planting densities reflect commercial practice, not theoretical maximum packing — overcrowding
  can negate theoretical yield gains through increased losses and quality degradation.
- The **nutrient factor of 0.005** is intentional. It produces nutrient costs in the correct
  1–7% of revenue range when combined with each crop's EC and water parameters.
- Mushrooms use no hydroponic nutrient solution. Their EC and water fields are structural
  placeholders; costs are dominated by substrate.
- Crops are included only if compatible with high-density stacked controlled-environment conditions.
  Species requiring deep soil, very low planting densities, or extensive horizontal space are excluded.
  (Example correction made during development: potatoes were removed after identifying that assumed
  planting densities were incompatible with realistic vertical farming practice.)
""")

# ─────────────────────────────────────────────────────────────────────────────
st.divider()
st.header("5. Country Data")
st.markdown("""
The country database covers **46 countries** with three parameters per country:

| Field | Description | Source |
|---|---|---|
| `kwh` | Electricity price $/kWh (industrial/commercial tariff) | IEA, Eurostat (European countries), national energy regulators (2023–2024) |
| `labour` | Labour cost $/hour (fully loaded, including employer social contributions) | ILO/ILOSTAT (primary, global coverage); Eurostat cross-check for European countries |
| `food_index` | Wholesale price index relative to Germany = 1.00 | BMEL market reports (German baseline); European Commission agri-food data portal; relative indices for other markets |

**Key clarifications:**

**Electricity prices** reflect industrial/commercial tariffs, not residential. In countries with tiered pricing, the lower industrial rate is used.

**Labour costs are fully loaded** — they include employer social contributions, insurance, and statutory benefits, not just the base wage. This is consistent with the Eurostat definition: *"hourly labour costs represent the total cost borne by the employer, including wages, salaries, and non-wage costs"* (Eurostat Labour Cost Statistics). This is why Germany shows ~$51/hr despite a ~€12–13 statutory minimum wage. National average costs are used (not minimum wages or agriculture-specific rates) because vertical farms typically compete for urban or semi-skilled labour.

**The food price index** is not a consumer price index or retail shelf price index. It is a dimensionless multiplier approximating how market conditions — import dependence, logistics intensity, purchasing power, climatic constraints — affect achievable wholesale prices for vertically farmed produce. Germany is the reference market (index = 1.00) due to the availability of official BMEL wholesale price reporting.

**Currency:** All built-in data is stored in USD. Labour costs for non-USD countries were converted using exchange rates from the Assumptions sheet at the time of data entry. A future enhancement will allow FX rate updates to be applied automatically.

**Country as parameter container:** The model treats country selection as a mechanism for loading default parameter values, not as a binding constraint. There is substantial intra-country variability in wages and energy prices, particularly for urban projects. Users are encouraged to override defaults with site-specific values.
""")

# ─────────────────────────────────────────────────────────────────────────────
st.divider()
st.header("6. Labour Model")
st.markdown("""
Labour is modelled as **19 discrete tasks**, each with a base time (minutes/unit) and an automation reduction factor applied at the task level — not through a global efficiency discount.
```
Annual Labour Hours = Sum of all task minutes / 60
Annual Labour Cost  = Annual Labour Hours × Country Labour Rate
```

**Tasks are divided into two categories:**

*Crop-cycle tasks* (seeding, germination, transplanting, internal movement, harvest, post-harvest, packaging, waste handling) — scale with tray count and/or cycles per year.

*Facility management tasks* (nutrient mixing, water checks, climate monitoring, sensor calibration, cleaning, quality control, IPM scouting, preventive maintenance, administration) — scale with growing area and/or time (weekly/annual).

**Automation factors** reduce task time by level. Automation does not affect all activities uniformly — harvesting may be partially automatable while quality control or system oversight may not. Notably, `preventive_maintenance` increases slightly with higher automation (more complex systems require more maintenance time).

**Hardcoded zeros:** `washing` and `drying` are set to 0 minutes. These tasks are not applicable to fresh-cut leafy greens and herbs, which are not washed or dried at farm level in CEA operations.

**Important limitation:** Peer-reviewed time-and-motion benchmarks for vertical farming operations remain limited. The labour time parameters are calibrated engineering priors rather than literature-derived constants. Operator-specific calibration is strongly recommended before using labour outputs in investment decisions.

**Sensor calibration** is modelled as an average workload scaled by production volume rather than "per sensor per month" — routine calibration workload is dominated by pH and EC probes; many other sensors are verified less frequently.
""")

# ─────────────────────────────────────────────────────────────────────────────
st.divider()
st.header("7. CAPEX Model")
st.markdown("""
CAPEX is built from **9 components**, each with a cost driver:

| Component | Rate | Basis | Scales with |
|---|---|---|---|
| LED Lighting | Tier-dependent ($110–260/m²) | Commercial fixture pricing 2023–2024 | EGA |
| HVAC | $170/m² | Industry benchmark | EGA |
| Racking | $140/m² × level complexity | Commercial rack systems | EGA |
| Building & enclosure | $350/m² × building step-up | Light industrial shell / warehouse fit-out | Footprint only |
| Automation controls | $90/m² × level complexity × controls multiplier | Sensors, SCADA, fertigation | Gross area |
| Robotics | $85/m² × level complexity × robotics multiplier | Tray movement, seeding, packing | Gross area |
| Electrical | $60/m² × level complexity | Power distribution | Gross area |
| Water/irrigation | $45/m² | Recirculation systems | EGA |
| Installation & commissioning | **10% of equipment subtotal** | Reflects scaling with actual technical scope | Derived |

**Total aggregate CAPEX** at default settings ≈ **$1,285/m² of EGA** — consistent with techno-economic analyses that identify capital costs as a dominant determinant of vertical farming feasibility *(Journal of Cleaner Production, 2024)*.

**Level complexity factor** adjusts for structural engineering cost at different heights. Base reference is 6 levels (factor = 1.0). Each level below 6: −5%. Each level above 6: +5%. Applied to: Racking, Automation, Robotics, Electrical, Installation.

**Building step-up factor** is separate and independent from the level complexity factor. The building envelope is not duplicated per level — it scales with footprint only. However, above 15 levels, additional structural and access requirements trigger a cost step-up of +2.5% per level above 15:
```
Building step-up = 1                              if levels ≤ 15
Building step-up = 1 + (levels − 15) × 0.025     if levels > 15
```

**Building scope note:** The $350/m² figure is defensible only for a limited building/enclosure scope — light-to-medium industrial shell, warehouse enclosure fit-out, insulation, partitions, washable finishes, drainage upgrades, basic envelope improvements. It explicitly excludes cleanroom-grade construction, high-spec hygienic regimes, or major structural/MEP rebuilds. Projects requiring near-cleanroom conditions should expect substantially higher figures and must override this default.

**Annual maintenance reserve** = 3% of equipment subtotal excluding building shell and real estate. This reserve is economically real but does not necessarily correspond to a fixed annual cash outflow. It must be removed or adjusted if explicit equipment replacement schedules are later introduced to avoid double counting.

**Installation as percentage:** Installation is modelled as 10% of the equipment subtotal (excluding building and real estate). This is more precise than a flat $/m² rate because it scales correctly when lighting tier, automation level, or farm geometry changes significantly.
""")

# ─────────────────────────────────────────────────────────────────────────────
st.divider()
st.header("8. Sensitivity Analysis Assumptions")
st.markdown("""
The Tornado Chart stresses each variable independently while holding all others at base values. Hovering over each bar in the chart shows the exact stress applied and the rationale.

| Variable | Pessimistic | Optimistic | Rationale |
|---|---|---|---|
| Energy Price | +50% | −30% | Asymmetric. +50% reflects 2021–2022 style energy shock; −30% reflects long-term contract or on-site solar integration |
| Selling Price | −20% | +20% | Symmetric. Reflects realistic wholesale price volatility for premium fresh produce |
| Yield | −20% | +20% | Symmetric. Crop benchmark yields vary with cultivar and operator experience |
| Labour Cost | +30% | −20% | Asymmetric. Labour tends to rise over time; −20% reflects partial automation gains |

These ranges are conservative relative to historical volatility. They are intended to show **relative sensitivity** (which variable matters most) rather than worst-case projections.

The **Energy % of Revenue threshold of 40%** used in country and crop comparison charts is a rule-of-thumb derived from CEA industry analysis: operations where energy exceeds ~40% of revenue have historically struggled to reach profitability at scale, particularly when combined with European labour costs. When energy exceeds 60% of revenue the operation is considered structurally non-viable without a material change in energy price, crop mix, or technology.
""")

# ─────────────────────────────────────────────────────────────────────────────
st.divider()
st.header("9. Known Limitations & Open Items")
st.markdown("""
- **Financial layer (DCF, DSCR, depreciation)** was implemented programmatically and has not been
  audited cell-by-cell against the Excel reference model. EBITDA, CAPEX, energy, labour, and
  variable costs have been fully validated. Financial structure outputs should be treated as
  directional, not precise.

- **Yield figures are benchmarks**, not guarantees. First-year yields are typically 10–30% below
  benchmark. The break-even yield metric is specifically designed to surface this risk.

- **Price data** reflects 2023–2024 European wholesale markets. Prices for specialty crops
  (microgreens, edible flowers) are particularly volatile and location-dependent. Users with
  contract prices should always use the Price Override input.

- **The model assumes 100% realisation of saleable yield.** No distribution loss, unsold
  inventory, or retailer returns. Real operations typically achieve 85–95% revenue realisation
  on saleable production.

- **Fish/aquaponics section** is implemented for both decoupled and coupled modes. The fish
  production engine (RAS), plant side (greenhouse engine with nutrient override), and integration
  logic are documented in Sections 12 and 13. Fish aeration and pump energy are
  species-differentiated using oxygen consumption and water exchange rate data from the fish
  system database. CAPEX rates differ between coupled and decoupled modes, reflecting their
  different structural requirements (single shared loop vs dual independent circuits with
  treatment layer).

- **FX rates** used for labour cost conversion are fixed at the time of data entry. A future
  enhancement will allow automatic FX rate updates.

- **Water parameters** are area-based proxies used as cost drivers. The literature supports
  high water efficiency relative to field agriculture but not the universality of a single
  litres/m² constant. These parameters are candidates for refinement into transpiration-based
  models in future iterations.

- **Installation cost** is modelled as 10% of equipment subtotal. This is an approximation;
  actual installation costs vary significantly by building typology, geography, and project complexity.

- **Multi-harvest financial projections** for 2H and 3H crops have been validated at the
  production level but the interaction with labour and energy costs under extended cycle conditions
  should be verified against actual operator data before use in investment decisions.

- **VF HVAC tier is manual, not climate-derived.** The Vertical Farm model uses `ambient_temp_annual`
  from the Open-Meteo API to *suggest* an appropriate HVAC tier in the ROI Calculator UI, but the
  value does not directly enter the energy formula. The HVAC selectbox controls a multiplier on
  total energy (1.70× / 1.83× / 2.025×). Users must verify that their selected tier reflects both
  the ambient climate severity *and* the actual insulation and HVAC specification of the facility.

- **Greenhouse and Aquaponics models use live climate data directly** for heating and lighting
  calculations. Annual mean temperature understates seasonal peak heating load. Treat results as
  a lower bound for cold-climate operations or cold-water fish species combinations.

- **Farm Intelligence Map data quality** varies by geography. Northern and Central Europe OSM
  industrial coverage is generally comprehensive. Southern and Eastern Europe, Middle East, and
  parts of Asia have variable coverage. Always cross-check critical facility findings independently.
""")

# ─────────────────────────────────────────────────────────────────────────────
st.divider()
st.header("10. References")
st.markdown("""
- Cornell University Controlled Environment Agriculture Program (2019). *Cornell CEA Lettuce Handbook*.
- Eurostat. *Hourly Labour Costs Statistics*. European Commission.
- European Commission (DG AGRI). *Agri-food Market Price Data Portal*.
- German Federal Ministry of Food and Agriculture (BMEL). *Fruit and Vegetable Market Reporting System*.
- International Labour Organization. *ILOSTAT Database*. ILO.
- Postel, S. L., et al. (2015). Water use efficiency in food production. *PNAS*, 112(30), 9141–9146.
- van Delden, S. H., et al. (2020). Growth of leafy greens under varying light intensities. *Wageningen University & Research*.
- Zhang, X., et al. (2024). Life cycle assessment of indoor vertical farming systems. *Journal of Cleaner Production*, Elsevier.
- MDPI Sustainability (2020). LED lighting efficacy in controlled-environment agriculture.
""")

st.divider()
st.header("11. Greenhouse & Polytunnel Model")
st.markdown("""
The greenhouse modality uses a separate calculation engine (`core/greenhouse_calculate.py`) that
shares the COUNTRIES data table and financial layer with the VF model but replaces the energy,
CAPEX, and labour assumptions entirely.

#### 11.1 Geometry
Greenhouses have no vertical levels. Effective grow area is:
```
EGA = Footprint × Net Grow Factor × (1 − Walkways Factor)
```
Default values: Net Grow Factor 90%, Walkways Factor 10%. These are slightly more favourable than
VF defaults (85%/15%) reflecting that single-level greenhouses have fewer structural intrusions.

#### 11.2 Energy Model
Greenhouse energy is split into supplemental lighting and climate energy.

**Supplemental lighting:**
```
Supplemental DLI    = Total DLI × (1 − natural_dli_fraction)
Lighting kWh/m²/yr = Supplemental DLI × 0.0216 × Operating Days
```
`natural_dli_fraction` is crop- and structure-specific (e.g. 0.65 for Venlo tomatoes, 1.0 for
polytunnel crops). It represents the proportion of required DLI met by natural sunlight under
Northern European commercial conditions. Source: Wageningen UR KWIN 2024.

The conversion factor **0.0216 kWh/mol** assumes 46 W/mol efficacy for the HPS/LED hybrid
supplemental fixtures common in commercial Venlo greenhouses. This is lower than top-tier LED-only
efficacy (3.2 µmol/J) because greenhouse supplemental systems are mixed-technology.

**Climate energy:**
```
Climate kWh/m²/yr = Lighting kWh/m²/yr × 0.35
```
The **0.35 multiplier** is a conservative midpoint for the ratio of climate energy (heating,
ventilation, humidity control) to supplemental lighting in commercial Venlo/multi-span structures.
This is lower than the VF HVAC multiplier (0.83) because greenhouse climate loads are partially
met by passive solar gain, natural ventilation, and heat retention from the glazed envelope.

**Known limitation:** The 0.35 multiplier does not vary by climate zone or structure type. A Venlo
greenhouse in Norway has materially higher heating loads than one in Spain at the same DLI deficit.
This is a modelling simplification. Users in cold climates should verify outputs against local
energy audits, and the multiplier will be replaced by a climate-derived value in Layer 2.

Polytunnel crops have `natural_dli_fraction = 1.0`, producing zero supplemental lighting energy.
Climate energy is also near-zero for unheated polytunnels. These are correctly modelled as
low-energy structures.

#### 11.3 CAPEX
Greenhouse CAPEX uses three structure types with component rates per m² of total footprint:

| Component | Polytunnel | Multi-span | Venlo |
|---|---|---|---|
| Structure | $35/m² | $95/m² | $218/m² |
| Climate system | $6.5/m² | $28/m² | $65/m² |
| Irrigation | $4.2/m² | $18.5/m² | $32/m² |
| Lighting | $0/m² | $25/m² | $85/m² |
| Automation | $2.5/m² | $12/m² | $28/m² |
| **Installation factor** | **×1.15** | **×1.25** | **×1.35** |

Sources: AVAG (Netherlands), German ZBG Industry Benchmarks 2024.

All components are multiplied by the installation factor before summing, reflecting
that higher-specification structures have proportionally higher commissioning complexity.

The structure type is **auto-selected from the crop database** — each crop specifies its
compatible structure (`venlo`, `multi-span`, or `polytunnel`). Users cannot override structure
type independently; it is a biological and agronomic constraint of the crop choice.

#### 11.4 Labour Model
A separate `GREENHOUSE_LABOUR_TASKS` table replaces the VF labour framework.
Key differences:

| Task | VF base (min/100m²/cycle) | Greenhouse base | Rationale |
|---|---|---|---|
| Washing | 2.0 | 0.0 | Fruiting crops not washed at farm level |
| Drying | 1.0 | 0.0 | Not applicable |
| Harvest | 0.6 | 2.5 | Hand-picking tomatoes/cucumbers vs leafy green cut |
| Admin | 240 min/wk | 15 min/wk | Single-level, no rack logistics |
| Preventive maint. | 60 min/wk | 20 min/wk | Simpler mechanics than VF rack/LED systems |

**Calibration target:** 0.8–1.2 labour hours per m² per year for commercial Venlo tomato
with medium automation. Source: WUR/KWIN 2024 commercial benchmarks.

At medium automation with 810 m² EGA (1,000 m² Venlo footprint), the model produces
**0.95 hrs/m²/year** — within the benchmark range.

**Important limitation:** These parameters are calibrated engineering priors, not
literature-derived time-and-motion constants. As with the VF model, operator-specific
calibration is recommended before use in investment decisions.
""")

st.divider()
st.header("12. RAS Fish Production Model")
st.markdown("""
The fish production engine (`calculate_fish()` in `core/aquaponics_calculate.py`) models
Recirculating Aquaculture System (RAS) economics for seven commercially relevant species.

#### 12.1 Production Logic
```
Harvest Biomass (kg) = Tank Volume (m³) × Stocking Density (kg/m³)
Fish per Batch       = Harvest Biomass ÷ Harvest Weight (kg/fish)
kg per Cycle         = Fish per Batch × Survival Rate × Harvest Weight
Cycles per Year      = floor(365 ÷ Grow Cycle Days)
Annual kg Fish       = kg per Cycle × Cycles per Year
```
Stocking density, harvest weight, grow cycle, and mortality rate are species-specific values
sourced from FAO Technical Paper 589 and Ebeling & Timmons (Recirculating Aquaculture Systems
Engineering). Survival rate = 1 − (mortality rate / 100).

#### 12.2 Energy Model
Fish RAS energy has two components:

**Aeration (species-differentiated):**

Aeration energy scales with species oxygen demand. The `oxygen_consumption_g_per_kg_per_hour`
values in the fish system database (Timmons & Ebeling, 2013) are peak metabolic rates at
active feeding — not average daily rates. Using them directly in an annual energy formula
would overstate aeration by 8–10×. Instead, they are used as a **relative scaling index**
against Tilapia (the reference species at 3.2 g/kg/hr):

```
O2 scale factor   = species O2 (g/kg/hr) ÷ 3.2 (Tilapia reference)
Aeration kWh      = Annual kg Fish × base kWh/kg × O2 scale factor
```

| Automation | Base kWh/kg (Tilapia reference) |
|---|---|
| None | 4.0 |
| Low | 3.5 |
| Medium | 3.0 |
| High | 2.0 |

| Species | O2 (g/kg/hr) | Scale factor | Effective kWh/kg (Medium) |
|---|---|---|---|
| African Catfish | 1.5 | 0.47× | 1.4 |
| Common Carp | 2.0 | 0.62× | 1.9 |
| European Perch | 2.8 | 0.87× | 2.6 |
| Zander | 3.0 | 0.94× | 2.8 |
| Tilapia (Nile) | 3.2 | 1.00× | 3.0 |
| Rainbow Trout | 4.5 | 1.41× | 4.2 |
| Atlantic Salmon | 4.8 | 1.50× | 4.5 |

All values fall within the published RAS benchmark range of 3–8 kWh/kg produced
(Badiola et al., 2012), with energy-intensive cold-water species (Salmon, Trout)
correctly at the high end and low-metabolism species (Catfish, Carp) at the low end.

**Pumping (water-exchange-scaled):**

Pump energy scales with species water exchange rate relative to Tilapia baseline (2.5%/day):

```
Pump kWh = 0.5 kWh/m³/day × Tank Volume × (species exchange rate ÷ 2.5) × 365
```

| Species | Exchange rate (%/day) | Scale vs Tilapia |
|---|---|---|
| African Catfish | 1.0% | 0.40× |
| Common Carp | 2.0% | 0.80× |
| Tilapia | 2.5% | 1.00× |
| European Perch | 3.0% | 1.20× |
| Zander | 4.0% | 1.60× |
| Rainbow Trout | 5.0% | 2.00× |
| Atlantic Salmon | 5.0% | 2.00× |

Source: FAO Technical Paper 589. The 0.5 kWh/m³/day base pump energy reflects
modern variable-speed RAS pump systems at Tilapia-level exchange rates.

**Heating:**
```
Heating kWh = 10 W/m³ × Tank Volume × 8,760 hr/yr ÷ 1,000 × (ΔT ÷ 15)
```
where ΔT = max(0, Target Temperature − Ambient Temperature).

The **10 W/m³ baseline** represents heat loss from a well-insulated RAS tank at a 15°C
temperature differential. This scales linearly with ΔT. Source: thermal engineering proxy
for insulated HDPE or fibreglass tanks in a climate-controlled environment.

**Known limitation:** 10 W/m³ assumes good insulation. Poorly insulated small-scale systems
may lose 20–30 W/m³. Users in cold climates with low-specification tanks should treat
heating costs as a lower bound and verify against site-specific heat loss calculations.

#### 12.3 Labour
```
Annual Fish Labour Hours = hrs/m³/year × Tank Volume
Annual Fish Labour Cost  = Annual Hours × Country Labour Rate
```
| Automation | hrs/m³/year |
|---|---|
| None | 1.5 |
| Low | 1.2 |
| Medium | 0.8 |
| High | 0.5 |

Source: Timmons & Ebeling RAS Engineering benchmarks for commercial-scale RAS operations.

#### 12.4 CAPEX
Fish CAPEX is computed per m³ of tank volume with two scale tiers:

CAPEX rates differ between **decoupled** and **coupled** modes because their structural
requirements are fundamentally different.

**Decoupled** requires two independent water circuits plus a treatment layer (UV sterilisation,
settling, pH adjustment from fish-optimum ~7.5 to plant-optimum ~6.0, and nutrient
top-up to compensate for deficiencies in raw fish effluent). This drives higher filtration,
plumbing, monitoring, and integration costs.

**Coupled** uses a single shared loop — fish tank → biofilter → plant beds → back to fish tank.
No treatment layer, one pump circuit, one EC/pH monitoring system, and a simple NFT/DWC
distribution manifold. Per-m³ component costs are approximately 21% lower than decoupled
at both scale tiers.

**Decoupled CAPEX (per m³ of tank volume):**

| Component | Small-scale (&lt;100 m³) | Commercial-scale (≥100 m³) | Notes |
|---|---|---|---|
| Tanks | $450/m³ | $280/m³ | Same regardless of mode |
| Filtration | $750/m³ | $420/m³ | Includes treatment unit (UV, settling, pH adjust) |
| Aeration | $180/m³ | $130/m³ | Fish + plant-side circuits |
| Monitoring | $120/m³ | $65/m³ | Dual EC/pH systems (fish loop + plant loop) |
| Plumbing | $210/m³ | $145/m³ | Two full independent circuits |
| Integration/m² plant | $42/m² | $35/m² | Nutrient top-up, distribution, plant-side pumps |
| **Installation factor** | **×1.40** | **×1.30** | Dual-circuit commissioning complexity |

**Coupled CAPEX (per m³ of tank volume):**

| Component | Small-scale (&lt;100 m³) | Commercial-scale (≥100 m³) | Notes |
|---|---|---|---|
| Tanks | $450/m³ | $280/m³ | Identical to decoupled |
| Filtration | $518/m³ | $290/m³ | Shared biofilter only — no treatment unit |
| Aeration | $160/m³ | $116/m³ | No separate plant-side aeration circuit |
| Monitoring | $85/m³ | $46/m³ | Single EC/pH loop |
| Plumbing | $149/m³ | $103/m³ | One shared circuit |
| Integration/m² plant | $18/m² | $15/m² | Simple NFT/DWC manifold, direct fish loop feed |
| **Installation factor** | **×1.30** | **×1.20** | Simpler single-circuit commissioning |

Source: NRAC (Recirculating Aquaculture Systems Engineering), WUR. Coupled/decoupled
differential derived from Goddek et al. decoupled aquaponics systems engineering literature.

The **100 m³ threshold** is automatically applied based on tank volume — it is not a
user-selectable parameter. The transition is a step function at 100 m³, not a continuous
curve. In practice, scale economies begin appearing above ~50–80 m³ and fully materialise
above 200 m³. This simplification is acceptable for feasibility modelling.

**Annual maintenance reserve** = 2% of total fish CAPEX (vs 2% for greenhouse plant CAPEX).
Fish equipment — particularly filtration media, aeration diffusers, UV lamps, and monitoring
probes — has high consumable and replacement costs relative to its installed value.

#### 12.5 Atlantic Salmon Constraint
Atlantic Salmon requires water temperature of 8–14°C. This is incompatible with coupled
aquaponics (which forces a shared water loop compromise temperature of ~7°C for fish/plant
co-existence) and with warm-climate decoupled systems. When Salmon is selected:
- In **coupled mode**: calculation is blocked with an error.
- In **decoupled mode**: a warning is shown advising the user to set target temperature
  ≤14°C and noting expected high heating costs in temperate climates.
""")

st.divider()
st.header("13. Aquaponics Integration Logic")
st.markdown("""
The aquaponics calculator (`calculate_aquaponics()`) orchestrates two independent engines —
the greenhouse plant engine and the fish engine — and combines their outputs with integration
logic specific to the coupling mode.

#### 13.1 Decoupled Mode
In a decoupled system, fish and plants operate at their own optimal conditions and are
connected only through treated nutrient water. The plant side runs through
`calculate_greenhouse()` without modification, then a post-calculation nutrient cost
reduction is applied:

```
Nutrient Offset Saving = Raw Nutrient Cost × decoupled_nutrient_offset_fraction
```

The **base offset fraction is 0.60** — meaning 60% of purchased nutrient cost is replaced
by treated fish effluent under a well-designed system. Source: Suhl et al. (decoupled
aquaponics economics literature). The full range used in scenario modelling is:

| Scenario | Offset Fraction | Condition |
|---|---|---|
| Low | 0.30 | Poorly optimised fish-to-plant ratio |
| Base | 0.60 | Well-designed commercial system |
| High | 0.85 | Highly integrated maximum recovery |

Source: Maucieri et al. (upper bound); Goddek et al. for system economics.

The nutrient saving is subtracted from `annual_variable_cost` and added back to `ebitda`.
It does not affect revenue, energy, labour, or CAPEX.

#### 13.2 How yield and nutrient costs change between modes

The table below shows exactly what the model modifies — and what it leaves unchanged —
when switching between decoupled and coupled mode:

| Variable | Decoupled | Coupled | Applied how |
|---|---|---|---|
| Plant yield | **Unchanged (1.00×)** | **×0.88** (default, adjustable 0.70–1.00) | Coupled: pre-calculation crop patch |
| Plant nutrient cost | **×0.40** (60% offset) | **×0.05** (near-zero) | Decoupled: post-calculation subtraction; Coupled: pre-calculation crop patch |
| Fish yield | **Unchanged** | **Unchanged** | Fish engine runs identically in both modes |
| Fish CAPEX rates | Decoupled table | Coupled table (~21% lower) | Mode-keyed lookup in AQUAPONICS_CAPEX |

**Decoupled nutrient offset mechanism:**
The greenhouse engine runs at full yield and full nutrient cost. After the calculation,
60% of the raw nutrient cost line is subtracted from `annual_variable_cost` and added
back to `ebitda`. This reflects that fish effluent replaces a fraction of purchased
nutrients while the plants remain at their optimal growing conditions.

**Coupled yield and nutrient mechanism:**
Before calling the greenhouse engine, the crop's yield values and nutrient cost field
are temporarily patched with multipliers. The engine then runs as normal against these
modified crop parameters. This means all downstream quantities (revenue, labour hours
per cycle, water cost) correctly reflect the reduced yield — not just a post-hoc EBITDA
adjustment.

#### 13.3 Coupled Mode — Structural Constraints

In a coupled system the plant and fish share the same water loop. This imposes constraints
that deviate meaningfully from a standalone greenhouse:

- **EC is lower than optimal** — fish water is dilute compared to hydroponic solution,
  reducing nutrient availability and yield.
- **pH is a compromise at ~7.0** — optimal for fish and nitrification bacteria, but below
  the plant optimum of 6.0–6.5, reducing iron and phosphorus solubility.
- **Crop selection is constrained** — only crops rated `high` or `medium` aquaponics
  suitability in the crop database are selectable in coupled mode. Fruiting crops (tomatoes,
  cucumbers, peppers) are rated `low` and excluded.

These constraints are modelled via two hardcoded multipliers passed to the greenhouse engine:

**Yield multiplier: 0.88 (default)**
Represents a 12% yield reduction vs standalone greenhouse, reflecting the combined effect
of suboptimal pH, EC, and the restriction to lower-yield crop types. Source: calibrated
engineering prior consistent with published yield penalties in coupled NFT/DWC systems
(Lennard & Leonard, 2006). User-adjustable via slider (range 0.70–1.00).

**Nutrient cost multiplier: 0.05 (hardcoded)**
Sets nutrient cost to 5% of its standalone value — effectively near-zero — reflecting
that in a coupled system the fish waste stream directly supplies the plant nutrient loop
with minimal supplementation required. The 5% residual covers micronutrient top-ups
(iron chelate, calcium, potassium) that fish effluent cannot supply in sufficient
concentration regardless of system design. Source: engineering judgement based on
published coupled aquaponics nutrient balance data (Rakocy et al., USVI; Goddek et al.).

**Known limitations of the coupled model:**
- The 0.88 yield factor is the weakest number in the aquaponics model. It is an aggregate
  scalar, not crop-specific. Leafy greens in well-managed coupled systems achieve closer
  to 0.92–0.95; the default is a conservative midpoint for the permissible crop set.
- The 0.05 nutrient multiplier assumes a well-loaded system (fish biomass sufficient to
  supply the plant nutrient demand). If the fish-to-plant ratio is below the minimum viable
  threshold (10 kg/m²), this multiplier overstates the nutrient saving. The ratio warning
  in the UI flags this condition but does not adjust the multiplier automatically.
- Fish yield is not affected by coupling mode in the current model. In reality, coupled
  systems constrain species choice (cold-water species are incompatible) and may reduce
  fish growth rate due to the pH/temperature compromise. This is partially captured by
  the species suitability filter and the Salmon hard block, but is not modelled as a
  continuous fish yield penalty.

#### 13.3 Fish-to-Plant Ratio Validation
A minimum viable fish-to-plant ratio is required for the nutrient offset to be
economically meaningful:

```
Fish Biomass per m² = Harvest Biomass (kg) ÷ Plant Footprint (m²)
```

| Threshold | Value | Source |
|---|---|---|
| Minimum viable | 10 kg/m² | Lennard — minimum for non-trivial nutrient offset |
| Optimal | 17.5 kg/m² | Rakocy USVI (published range 15–20 kg/m² for lettuce) |

If the computed ratio falls below 10 kg/m², a warning is shown. The calculation still
runs — the nutrient offset is applied regardless — but the user is informed that the
fish biomass is insufficient to meaningfully replace purchased nutrients at the modelled
offset fraction. This is not blocked because some operators intentionally run
fish-light, plant-heavy systems for other reasons (risk, permitting, capital constraints).

#### 13.4 Integration CAPEX
A greenhouse integration cost is added at the combined level to cover the piping,
distribution manifolds, and treatment equipment connecting the fish system to the
plant side:

```
Integration CAPEX = greenhouse_integration_cost_per_m2 × Plant Footprint
```

| Scale | Integration cost per m² of plant footprint |
|---|---|
| Small-scale (&lt;100 m³) | $42/m² |
| Commercial-scale (≥100 m³) | $35/m² |

Source: WUR aquaponics system cost benchmarks. This cost is separate from both greenhouse
structure CAPEX and fish tank CAPEX — it represents only the integration layer
(pipes, UV treatment, settling tanks, distribution headers).

#### 13.5 Combined Financial Reporting
The combined aquaponics result aggregates plant and fish P&L additively:

```
Combined Revenue  = Plant Revenue + Fish Revenue
Combined EBITDA   = Plant EBITDA + Fish EBITDA
Combined CAPEX    = Plant CAPEX + Fish CAPEX + Integration CAPEX
```

No shared cost deductions are applied beyond the nutrient offset saving. This is
conservative — in a real integrated system, some labour (monitoring, water management)
would be shared rather than additive. The current model therefore slightly overstates
combined labour cost, which is a known and accepted limitation pending operator data.
""")

st.divider()
st.header("14. Country Climate Defaults & Live Climate Integration")
st.markdown("""
### Layer 1 — Hardcoded Country Fallbacks

Fish RAS heating costs depend on the temperature differential between the fish tank target
temperature and ambient conditions. When no farm-specific climate data is available, the model
uses hardcoded annual mean ambient temperatures per country:

| Country | Ambient Temp (°C) | Country | Ambient Temp (°C) |
|---|---|---|---|
| Germany | 9.6 | United States | 13.0 |
| France | 12.4 | Canada | 5.6 |
| Italy | 13.9 | Japan | 14.4 |
| Spain | 14.8 | Australia | 21.8 |
| Netherlands | 10.4 | India | 24.7 |
| Denmark | 8.9 | United Arab Emirates | 28.0 |
| Sweden | 6.4 | Singapore | 27.5 |
| Norway | 5.4 | Egypt | 22.0 |
| Finland | 4.9 | South Africa | 17.5 |
| United Kingdom | 9.8 | Brazil | 25.4 |

Source: World Bank Climate Data / WMO annual mean temperature datasets.

**How it is used:**
ΔT           = max(0, Target Temperature − Ambient Temperature)
Heating kWh  = 10 W/m³ × Tank Volume × 8,760 hr/yr ÷ 1,000 × (ΔT ÷ 15)
When ΔT = 0 (ambient is already at or above target temperature), heating cost is zero.
This correctly models warm-climate tilapia operations where no external heating is needed.

---

### Layer 2 — Live Farm Climate Profiles (implemented)

**Status: live.** When a farm profile has coordinates (lat/lon), the portal automatically
fetches a 10-year historical climate profile from the **Open-Meteo Archive API** (no API key
required) at farm save time. The result is stored permanently in the `farms` Supabase table
and never re-fetched for the same farm.

Two values are stored and used:

| Column | Unit | Source | Used by |
|---|---|---|---|
| `ambient_temp_annual` | °C | Open-Meteo 10yr mean of `temperature_2m` | Fish heating ΔT (replaces country fallback) |
| `mean_annual_dli` | mol/m²/day | Open-Meteo 10yr mean of `shortwave_radiation_sum` | Greenhouse/polytunnel supplemental lighting |

**DLI derivation formula:**
mean_annual_dli = mean(shortwave_radiation_sum_MJ_m2_day) × 1.0
The factor 1.0 is applied after calibration. An earlier version of this model used the
theoretically derived factor 0.45 × 4.57 = 2.07 (PAR fraction × μmol/J conversion), which
was found to produce values approximately 2× too high versus published DLI reference data
for European locations. The factor was corrected to 1.0 empirically.

**Important:** Farm profiles fetched before this correction was applied will have
`mean_annual_dli` values approximately 2× too high. To correct: delete the
`mean_annual_dli` value from the affected row in Supabase — the portal will
re-fetch it automatically on the next farm load.

**How mean_annual_dli is used (greenhouse and polytunnel only):**
natural_dli_fraction = min(1.0, mean_annual_dli / crop_dli_requirement)
supplemental_dli     = crop_dli_requirement × (1 − natural_dli_fraction)
lighting_kwh/m²/yr   = supplemental_dli × 0.0216 × operating_days
A farm in Southern Spain (DLI ≈ 20 mol/m²/day) growing tomatoes (requirement ≈ 22)
needs only 9% supplemental lighting. The same farm in Finland (DLI ≈ 8) needs 64%.
This directly affects both energy OPEX and lighting CAPEX.

**Fallback hierarchy:**
1. Farm-specific `ambient_temp_annual` from Supabase (fetched from Open-Meteo)
2. Country-level hardcoded value from the table above
3. 15°C universal default (if country not in table)

**Known limitations:**
1. **Annual mean vs seasonal variation.** Cold-climate salmon farms face near-freezing
   ambient temperatures in winter. The annual mean understates peak heating load — treat
   heating cost as a lower bound for cold-climate cold-water species combinations.
2. **Air temperature ≠ mains water temperature.** For RAS systems on municipal water,
   mains water is typically 1–5°C colder than mean air temperature in temperate climates.
   This model uses air temperature as proxy, slightly understating heating costs where
   cold groundwater is used.
3. **DLI does not affect VF calculations.** Indoor vertical farms use fully artificial
   lighting — location DLI is irrelevant and not applied to the VF calculation engine.
""")

# ─────────────────────────────────────────────────────────────────────────────
st.header("15. Weather Integration & HVAC Cost Estimation")
st.markdown("""
### Data Source

Real-time and forecast weather data is fetched from the **Open-Meteo Forecast API**
(`https://api.open-meteo.com/v1/forecast`). No API key is required. The API is updated
hourly and provides 7-day forecasts. This is a separate endpoint from the historical
climate archive used for DLI calculations (Section 14).

**Variables fetched (daily, 7-day horizon):**
- `temperature_2m_max` / `temperature_2m_min` / `temperature_2m_mean` — °C
- `precipitation_sum` — mm
- `shortwave_radiation_sum` — MJ/m²/day
- `cloud_cover_mean` — %
- `wind_speed_10m_max` — km/h
- `relative_humidity_2m_mean` — %

Weather is fetched on-demand when the Active Cycles tab is opened, for the farm's
stored coordinates (lat/lon). If no coordinates are saved, the weather widget is
hidden and no alerts are generated.

---

### Weekly HVAC Cost Estimation

The weekly HVAC cost estimate displayed in the Active Cycles tab uses a simplified
**degree-day thermal load model**:
ΔT per day       = |Target indoor temp − Outdoor mean daily temp|  (°C)
Thermal load     = ΔT × 10 W/m²/°C × Footprint (m²)              (W)
kWh per day      = Thermal load (kW) × 24 hours ÷ HVAC efficiency
Weekly total kWh = sum over 7 days
Weekly cost ($)  = Total kWh × Farm electricity price ($/kWh)

**Key constants and sources:**

| Parameter | Value | Source / Rationale |
|---|---|---|
| Thermal load factor | 10 W/m²/°C | Mid-range for well-insulated CEA structures. Typical range: 8–12 W/m²/°C. Source: ASHRAE Handbook — Fundamentals (2021), Chapter 18 |
| HVAC system efficiency | 0.85 (85%) | Conservative COP assumption for air-handling unit or heat pump in light-commercial range. Source: EU Energy Performance of Buildings Directive (EPBD) 2024 benchmarks |
| Target indoor temperature | 22°C | Default for leafy greens / general CEA. Not modality-specific in the current implementation. |
| Hours per day | 24 | Assumes continuous climate control |

**Important caveats:**
- The model uses a **linear degree-day approximation** and does not account for solar gain, thermal mass, or latent heat from transpiration and irrigation — all of which reduce heating load in real greenhouses. Treat the output as an **upper bound** on weekly HVAC energy.
- The target indoor temperature (22°C) is hardcoded as a default and not yet derived from the farm's crop selection or modality parameters. A polytunnel targeting 18°C lettuce production will be overstated relative to a tomato greenhouse targeting 24°C.
- The model does not distinguish between heating and cooling efficiency — the same 0.85 factor is applied to both modes. In practice, evaporative cooling has higher efficiency (COP 2–6) while resistance heating has lower (COP ~1). This is a simplification.
- Aquaponics fish tank heating is modelled separately in the ROI Calculator (Section 12) using a higher-resolution model that accounts for species target temperature and tank volume. The HVAC widget in Active Cycles is for the building envelope only.

---

### Crop Temperature Alerts

The Active Cycles tab generates weather alerts by comparing the 7-day forecast
to per-crop temperature thresholds. These thresholds are hardcoded in `core/weather.py`
and derived from agronomic literature:

| Crop | Min tolerable (°C) | Max tolerable (°C) | Optimal range (°C) | Source |
|---|---|---|---|---|
| Lettuce (all types) | 2 | 28 | 15–22 | Ryder (1999), *Lettuce, Endive and Chicory*, CABI |
| Baby Spinach | −5 | 24 | 10–18 | Bianco & Pimpini (2002), Univ. of Bologna |
| Basil | 10 | 35 | 18–28 | Simon et al. (1990), USDA Herb Guide |
| Mint | 5 | 30 | 16–24 | Morton (1976), *Herbs and Spices*, USDA |
| Rocket / Arugula | 0 | 26 | 10–20 | Bianco & Pimpini (1995), *Rucola* |
| Kale | −8 | 26 | 10–20 | AHDB Horticulture (2020) |
| Strawberry | 2 | 30 | 15–22 | Hancock (1999), *Strawberry*, CABI |
| Tomato (all types) | 10 | 35 | 18–27 | Heuvelink (2005), *Tomatoes*, CABI |
| Cucumber | 12 | 36 | 20–28 | Marcelis et al. (1998), Wageningen |
| Pepper (Sweet) | 12 | 36 | 20–28 | Wien (1997), *Physiology of Vegetable Crops* |
| Eggplant / Aubergine | 15 | 38 | 22–30 | Maynard & Hochmuth (1997), IFAS |

**Alert logic:**
- **Critical** — forecast min temp more than 5°C below crop minimum (severe frost / chilling injury risk)
- **Warning** — forecast min temp below crop minimum, or max temp above crop maximum
- **Info** — temp in suboptimal range (below opt_min or above opt_max), or heavy rain (&gt;30mm), or high wind (&gt;60 km/h, polytunnel only)

For crops not in the table, a universal fallback threshold (min 5°C / max 32°C / optimal 15–25°C) is applied.

**Alert scope:** Temperature alerts are only generated for **greenhouse** and **polytunnel** farms, where outdoor conditions directly affect crop environment. Vertical farms are fully controlled — only the HVAC cost signal is shown (cold spell warning). For aquaponics, the plant section follows greenhouse/polytunnel rules; the fish section uses species-specific temperature management in the ROI model (Section 12).
""")

# ─────────────────────────────────────────────────────────────────────────────
st.header("16. Crop Cycle Tracking Model")
st.markdown("""
### Cycle Lifecycle

Each crop cycle in the Harvest Tracker follows a defined lifecycle with five statuses:

| Status | Meaning | Triggered by |
|---|---|---|
| `seeding` | Cycle opened, seeding/transplanting recorded, no harvest yet | User opens cycle in Log Cycle tab |
| `growing` | Cycle in active vegetative growth | Manual status update in Active Cycles tab |
| `ready` | Crop is at or near expected harvest window | Manual status update |
| `harvested` | Cycle closed with a harvest event | Close Cycle form or direct harvest log |
| `failed` | Crop lost before harvest | Failure recording with reason |

Existing harvest log entries that predate the cycle tracking system are treated as closed cycles with `status = 'harvested'`, `seeding_date = NULL`.

### Expected Harvest Date Computation

When a cycle is opened for a **Vertical Farm**, the expected harvest date is computed as:
expected_harvest_date = seeding_date + crop["cycle"]  (days)

where `crop["cycle"]` is the base cycle duration in days from the VF crop database (`core/data_tables.py`). This is the **base growing cycle excluding harvest gap** — it does not include `days_between_harvests` for multi-harvest crops.

For **greenhouse and polytunnel** crops, cycle days are not yet automatically computed — the expected harvest date is left blank and must be set manually. Greenhouse crop cycle duration varies significantly with season, DLI, and temperature setpoint, making a single hardcoded value unreliable.

**Accuracy caveat:** The expected harvest date is derived from database medians calibrated to commercial European operations under controlled conditions. Actual cycle duration on a specific farm will vary with: lighting intensity, temperature stability, nutrient regime, variety selection, and season. Use the prediction as a planning guideline, not a guarantee.

### Cycle Performance Score

When a cycle is closed with a harvest, the system computes a **yield performance score** for VF farms:
actual_yield    = kg_harvested ÷ area_m² (kg/m²)
model_yield     = crop["yield"]            (kg/m², from data_tables.py)
cycle_score (%) = actual_yield ÷ model_yield × 100

A score of 100% means the cycle performed exactly as the model predicted. Scores above 100% indicate above-model performance; below 100% indicates underperformance.

The score is shown as a caption on the close cycle confirmation. It is not yet aggregated into a farm-level performance index (planned for a future release).

**Limitation:** The score is only computed for VF farms because greenhouse and aquaponics yield models involve additional variables (DLI, temperature, season) that make a simple area-yield comparison less meaningful without seasonal normalisation.

### Observation Log

Each active cycle carries a `observations` JSONB array in the database:

```json
[{"date": "2025-04-12", "text": "Yellowing on lower leaves, zone B"},
 {"date": "2025-04-15", "text": "Aphid presence, IPM scouting escalated"}]
```

Observations are appended on each save (never overwritten). The three most recent observations are shown in the Active Cycles card. Observations are not analysed automatically — they form a qualitative record for the farmer's own reference and future pattern recognition.

### Weather Snapshot on Harvest

When a cycle is closed, the field `weather_snapshot` in `harvest_logs` can be populated with the weather conditions at close time. **This is not yet implemented automatically** — the field exists in the schema and is reserved for a future version that will fetch and store a 7-day retrospective weather summary at cycle close, enabling correlation analysis between weather patterns and yield outcomes across many cycles.
""")

# ─────────────────────────────────────────────────────────────────────────────
st.header("17. Hardcoded Constants — Complete Audit")
st.markdown("""
This section documents every hardcoded numerical constant in the platform,
its value, where it appears in the codebase, and its source or rationale.
This is the authoritative reference for any model audit.

### 17.1 Vertical Farm Energy Model (`core/roi_calculate.py`)

| Constant | Value | Description | Source |
|---|---|---|---|
| Lighting efficacy — Cheap tier | From `LIGHTS` table | μmol/J — LED efficiency | Calibrated from manufacturer datasheets; lower bound |
| Lighting efficacy — Basic tier | From `LIGHTS` table | μmol/J — industry standard LED | LumiGrow / Fluence published specs |
| Lighting efficacy — Top-Tier | From `LIGHTS` table | μmol/J — best available LED | Signify GreenPower 2024 spec sheet |
| HVAC energy factor | Derived from `HVAC_FACTORS` table | Multiplier on lighting load | Calibrated from VDI 6022 and ASHRAE 90.1 |
| 360-day year | 360 days | Used for cycle-per-year calculations | Industry convention; avoids part-cycle complications |
| Nutrient cost factor | 0.005 (universal) | $/kWh-equivalent hydroponic solution | Calibrated from European hydroponic supplier pricing (Plagron, Plagron NL, Grodan 2023). Mushroom family excluded (no hydroponic solution). |
| Effective cycle days | `cycle + harvest_gap_H2 + harvest_gap_H3` | Used in energy and labour calculations | Validated against Excel reference model |
| IPM scouting frequency | Daily | Mandatory labour task; cannot be omitted | EU Directive 2009/128/EC on sustainable pesticide use |

### 17.2 Greenhouse CAPEX (`core/greenhouse_data_tables.py`)

| Structure Type | Structure ($/m²) | Climate system ($/m²) | Irrigation ($/m²) | Lighting ($/m²) | Automation ($/m²) | Install factor | Source |
|---|---|---|---|---|---|---|---|
| Polytunnel | 35.0 | 6.5 | 4.2 | 0.0 | 2.5 | 1.15 | AVAG Netherlands; ZBG German horticulture benchmarks 2024 |
| Multi-span | 95.0 | 28.0 | 18.5 | 25.0 | 12.0 | 1.25 | AVAG Netherlands; ZBG German horticulture benchmarks 2024 |
| Venlo | 218.0 | 65.0 | 32.0 | 85.0 | 28.0 | 1.35 | AVAG Netherlands; WUR greenhouse construction cost survey 2023 |

Annual maintenance is set at **2% of total CAPEX** for all greenhouse types. Source: Wageningen University greenhouse enterprise budget templates (2022).

### 17.3 Aquaponics CAPEX (`core/greenhouse_data_tables.py`)

| Mode | Scale | Tank ($/m³) | Filtration ($/m³) | Aeration ($/m³) | Monitoring ($/m³) | Plumbing ($/m³) | GH integration ($/m²) | Install factor |
|---|---|---|---|---|---|---|---|---|
| Decoupled | Small (&lt;100m³) | 450 | 750 | 180 | 120 | 210 | 42 | 1.40 |
| Decoupled | Commercial (≥100m³) | 280 | 420 | 130 | 65 | 145 | 35 | 1.30 |
| Coupled | Small (&lt;100m³) | 450 | 518 | 160 | 85 | 149 | 18 | 1.30 |
| Coupled | Commercial (≥100m³) | 280 | 290 | 116 | 46 | 103 | 15 | 1.20 |

Source: NRAC (National Resource Aquaculture Center) Recirculating Aquaculture Systems Engineering Cost Estimates; Wageningen University RAS cost benchmarks (2021).

Coupled mode filtration is ~21% lower than decoupled (shared biofilter, no UV/pH treatment unit). Coupled installation factor is lower (simpler commissioning of single water circuit).

### 17.4 Aquaponics Fish Energy Model (`core/aquaponics_calculate.py`)

| Constant | Value | Description | Source |
|---|---|---|---|
| Base aeration kWh/kg — None automation | 4.0 | High blower inefficiency, manual monitoring | Timmons & Ebeling (2013), *Recirculating Aquaculture* |
| Base aeration kWh/kg — Low automation | 3.5 | Basic DO sensor, occasional manual adjustment | Timmons & Ebeling (2013) |
| Base aeration kWh/kg — Medium automation | 3.0 | Automated DO control | NRAC RAS benchmarks |
| Base aeration kWh/kg — High automation | 2.0 | Variable speed drives + dissolved O₂ optimisation | Timmons & Ebeling (2013); industry best practice |
| Tilapia reference O₂ consumption | 3.2 g/kg/hr | Baseline species for aeration scaling | Wheaton (1977), *Aquacultural Engineering* |
| Pump energy | 0.5 × tank_vol × (exchange_rate ÷ 2.5) × 365 | Annual pump kWh | Calibrated from NRAC RAS pump sizing guidelines |
| Water exchange rate reference | 2.5 (×/day) | Normalising factor for pump energy | NRAC |
| Heating load | 10 W/m³ of tank volume | Baseline heat loss per m³ water | Timmons & Ebeling (2013), Chapter 5 |
| Heating reference ΔT | 15°C | Normalising ΔT for heating energy | Calibration midpoint (ambient 10°C, target 25°C tilapia) |
| Fish annual maintenance | 3% of fish CAPEX | Ongoing equipment servicing | NRAC RAS enterprise budget templates |

### 17.5 DLI and Climate Conversion (`core/climate.py`)

| Constant | Value | Description | Source |
|---|---|---|---|
| DLI conversion factor | 1.0 | MJ/m²/day global radiation → mol/m²/day DLI | Empirically calibrated (see Section 14). Theoretical factor 0.45×4.57=2.07 found to overestimate by ~2× vs measured data. Source: Meek et al. (1984), *Agronomy Journal*; validated against KNMI/WUR measurements |
| Historical climate window | 10 years | Years of archive data used for climate normals | Standard WMO climatological normal period |
| Open-Meteo archive API | `archive-api.open-meteo.com/v1/archive` | Source URL | Zippenfenig (2023), Open-Meteo, doi:10.5281/zenodo.7970649 |

### 17.6 Weather Forecast HVAC Model (`core/weather.py`)

| Constant | Value | Description | Source |
|---|---|---|---|
| Thermal load factor | 10 W/m²/°C | Building envelope heat transfer coefficient per unit floor area | ASHRAE Handbook — Fundamentals (2021), Chapter 18; mid-range for insulated CEA |
| HVAC system efficiency | 0.85 | Ratio of useful heat/cool delivered to electrical energy consumed | EU EPBD 2024 benchmarks for light-commercial HVAC |
| Default target indoor temp | 22°C | Reference indoor setpoint for degree-day calculation | General CEA leafy greens default; not crop-specific |
| Polytunnel wind alert threshold | 60 km/h | Wind speed above which structural risk is flagged | Based on typical polytunnel design wind loads (EN 13031-1) |
| Heavy rain alert threshold | 30 mm/day | Drainage alert trigger | Agronomic practice convention |

### 17.7 Financial Model Constants (all modalities)

| Constant | Value | Description | Source |
|---|---|---|---|
| Default discount rate | 8.0% | Used in DCF / NPV calculations when not overridden | EU agricultural sector WACC range 6–10%; 8% is conservative midpoint |
| Default LTV | 60% | Loan-to-value for debt financing | Standard EU agricultural lending (EIB/EIF guidelines) |
| Default interest rate | 5.5% | Annual nominal interest rate | ECB base rate + agricultural lending spread (2024) |
| Default depreciation — VF | 10 years | Straight-line depreciation of CAPEX | EU tax convention for controlled-environment infrastructure |
| Default depreciation — GH | 15 years | Straight-line depreciation | EU convention; longer life for permanent greenhouse structures |
| Default depreciation — Aquaponics | 15 years | Straight-line depreciation | NRAC enterprise budgets; RAS equipment 10–20 year range |
| Tax rate default | 25% | Corporate income tax | Approximate EU weighted average; user-overridable |
| Packaging cost default | $0.15/kg | Post-harvest packaging | European fresh produce packaging survey (Wageningen, 2022) |
| Loss rate default | 5% | Post-harvest waste as % of gross yield | WRAP UK fresh produce baseline (2023) |

### 17.8 Country Energy Prices (`core/data_tables.py`)

Country-level electricity prices ($/kWh) are the single most important model parameter after yield. They are sourced from:

- **EU countries:** Eurostat energy price statistics (Eurostat, nrg_pc_205, households and non-household industrial consumers, H2 2023)
- **Non-EU countries:** IEA World Energy Prices database (2023 edition) and national grid operator publications
- **Update cadence:** Prices are hardcoded at the time of the last model revision. Energy markets change rapidly — **always verify current tariffs before using this model for investment decisions.**
- **Price tier used:** Commercial/industrial rate (non-household), which is appropriate for CEA operations. Residential rates are typically 30–60% higher in Europe and are not used.

A note on energy as the critical viability threshold: at European commercial electricity prices (€0.15–0.28/kWh as of 2024), energy cost alone frequently exceeds the wholesale value of commodity crops in fully artificial lighting systems. The portal's structural viability indicator (energy cost as % of revenue) is the fastest diagnostic for whether a given crop × country × modality combination is economically rational. This is the core design insight the platform was built around.
""")

# ─────────────────────────────────────────────────────────────────────────────
st.divider()
st.header("18. Farm Intelligence Map")
st.markdown("""
The Farm Intelligence Map is a spatial intelligence layer that enriches the farm investment
decision with location-specific data sourced entirely from free, open APIs — no API key required
for core functionality.

---

### 18.1 Purpose & Workflow Position

The Farm Intelligence Map sits at the centre of the data workflow:

```
Farm Intelligence Map
  → Sets farm coordinates (lat/lon)
  → Climate fetch triggered at farm save
  → ambient_temp_annual + mean_annual_dli stored in Supabase
  → ROI Calculator reads these values for heating and lighting calculations
  → Harvest Tracker reads coordinates for 7-day weather forecast
```

This means **placing a pin on the Farm Intelligence Map is the action that activates
location-specific calculations across the entire platform**. A farm profile without
coordinates uses static country-level fallbacks for all climate inputs.

---

### 18.2 Data Sources

#### OpenStreetMap via Overpass API
- **URL:** `https://overpass-api.de/api/interpreter` (with failover mirrors)
- **Auth:** None required. Free public API.
- **What it returns:** Geographic features matching structured tag queries within a radius.
- **Used for:** Waste Sources layer (Layer 1) and Logistics Infrastructure layer (Layer 2).
- **Timeout:** 90 seconds. Large radius queries (>50 km) in dense urban areas may time out.

#### Nominatim (OpenStreetMap Geocoding)
- **URL:** `https://nominatim.openstreetmap.org/reverse`
- **Auth:** None required. Rate limit: 1 request/second.
- **Used for:** Reverse geocoding a clicked map coordinate to country name and ISO code,
  enabling automatic country pre-fill when creating a farm profile from the map.

#### ipapi.co
- **URL:** `https://ipapi.co/json/`
- **Auth:** None required for low-volume usage.
- **Used for:** Detecting the user's approximate location on first map load to set the default
  map centre. Falls back to Milan (45.46°N, 9.19°E) if the request fails.

#### OpenRouteService (ORS) — optional, requires API key
- **URL:** `https://api.openrouteservice.org/v2/matrix/driving-car`
- **Auth:** API key in `st.secrets["ORS_API_KEY"]` (free tier: 2,000 matrix calls/day).
- **Register:** https://openrouteservice.org/dev/#/login
- **Used for:** Road distance routing for priority logistics infrastructure (airports,
  ports, motorway junctions, rail terminals, cold storage).
- **Fallback:** If `ORS_API_KEY` is absent or the call fails, straight-line Haversine
  distances are used silently. The `Routing` column in results shows `ORS (Road)` or
  `Haversine (Direct)` accordingly.

---

### 18.3 Layer 1 — Circular Economy / Waste Sources

**What it does:** Finds industrial facilities within the search radius that are potential
sources of organic waste with fertiliser value for aquaponics or composting.

**OSM tags queried:** `landuse=industrial`, `industrial=*`, `man_made=works`,
`man_made=wastewater_plant`, `craft=*` (brewery, dairy, slaughterhouse, sawmill, etc.).

**Classification logic (two-pass):**
1. Direct tag match against `TAG_WASTE_MAP` (e.g. `craft=brewery` → Spent Grains)
2. Name/tag keyword scan against `NAME_KEYWORD_MAP` (e.g. "birrificio" → Brewery)
3. Fallback: `Unknown / Other`

**NPK scoring:** Each waste stream is scored 0–9 for Nitrogen, Phosphorus, and Potassium
value based on published organic amendment literature. These scores are relative rankings,
not precise agronomic concentrations.

| Waste Stream | N | P | K | Label |
|---|---|---|---|---|
| Blood Meal / Bone Meal | 9 | 7 | 1 | High N+P |
| High Nitrogen Manure (Poultry) | 9 | 5 | 4 | High N |
| Fish Emulsion / Bone Meal | 8 | 6 | 2 | High N+P |
| Fermentation Biomass | 7 | 3 | 2 | High N |
| Whey / Sludge | 7 | 6 | 2 | High N+P |
| Digestate / Compost | 5 | 4 | 5 | Balanced |
| Wood Ash / Biochar | 0 | 2 | 7 | High K |

**Known limitation:** OSM industrial data quality varies significantly by country and
region. Northern Europe (NL, DE, AT) is densely mapped; Southern and Eastern Europe
has more gaps. Results should be treated as indicative, not exhaustive.

---

### 18.4 Layer 2 — Logistics Infrastructure

**What it does:** Finds transport and logistics infrastructure within the search radius
and computes a composite Logistics Score.

**Infrastructure types and OSM tags:**

| Type | OSM tag | Priority | Colour |
|---|---|---|---|
| Airport | `aeroway=aerodrome` | 1 | Purple |
| Rail Freight Terminal | `railway=freight_terminal` | 1 | Dark amber |
| Commercial Port | `landuse=port` | 1 | Navy |
| Motorway Junction | `highway=motorway_junction` | 1 | Red |
| Cold Storage | `industrial=cold_storage` | 1 | Green |
| Ferry Terminal | `amenity=ferry_terminal` | 2 | Cyan |
| Rail Station | `railway=station` | 2 | Orange |
| Harbour / Port | `harbour=*` | 2 | Blue |
| Motorway | `highway=motorway` | 1 | Dark red |
| Trunk Road | `highway=trunk` | 2 | Light red |
| Warehouse | `building=warehouse` | 4 | Olive |
| Fuel Station (HGV) | `amenity=fuel` | 4 | Yellow |
| Industrial Zone | `landuse=industrial` | 4 | Grey |

**Logistics Score formula:**
```
Score = sum of weights for each infrastructure type present (capped at 100)
```
| Type | Weight |
|---|---|
| Motorway Junction | 25 |
| Rail Freight Terminal | 20 |
| Commercial Port | 20 |
| Airport | 15 |
| Cold Storage | 15 |
| Rail Station / Harbour | 10 each |
| Ferry / Warehouse / Trunk / Rail Yard | 5 each |

This score is a **presence indicator**, not a capacity or throughput measure.
A score ≥60 indicates strong multi-modal logistics access; <35 indicates limited infrastructure.

**Nearest Key Infrastructure panel:** Shows the straight-line (or road) distance to the
nearest instance of 7 priority categories (Airport, Port, Motorway, Rail, Cold Storage,
Fuel, Ferry) regardless of the active filter settings.

---

### 18.5 Location Suitability Finder (Reverse Search)

**What it does:** Inverts the search logic. Instead of "what's near my farm?",
the user defines up to 3 reference infrastructure points and maximum distances.
The map draws coverage circles around each located target — the visual overlap
of circles identifies candidate zones that satisfy all proximity constraints simultaneously.

**Triangulation logic:**
1. Check existing loaded DataFrames first (no API call if target already in results)
2. If not found locally, run a targeted Overpass query for the specific infrastructure type
   within the global search radius
3. Return the closest match; draw a circle of the user-specified proximity radius

**Use case example:** A user sets Target 1 = Motorway Junction (≤15 km), Target 2 =
Cold Storage (≤20 km), Target 3 = Brewery (≤10 km). The overlapping area on the map
identifies candidate farm locations satisfying all three constraints.

---

### 18.6 Data Persistence

Intelligence Map search results can be saved to the farm profile's `metadata` JSONB column
in Supabase. On the next page load with the same active farm, results are rehydrated
automatically from the database — no re-search required.

**Saved keys in `metadata`:**
- `fim_waste_data` — list of dicts (waste layer DataFrame as records)
- `fim_logistics_data` — list of dicts (logistics layer DataFrame as records)

Clicking "💾 Save / Overwrite to Database" overwrites both keys. Clicking "🗑️ Clear Saved Data"
removes them from the metadata without affecting any other farm data.

**Important:** Saved data reflects the search radius and date at time of save. Infrastructure
changes in OSM or facility openings/closures are not automatically refreshed. Re-run the search
periodically for operational farms.
""")

# ─────────────────────────────────────────────────────────────────────────────
st.divider()
st.caption(
    "This model was built by reverse-engineering a validated Excel reference model "
    "(ROI_Calculator_Aquaponics.xlsx). Core formulas (EBITDA, CAPEX, energy, labour, variable costs) "
    "have been verified to produce results consistent with the Excel model for validated benchmark "
    "scenarios. For questions about methodology, contact the portal administrator."
)

st.divider()
st.markdown("## ⚙️ Account Settings")
_ac1, _ac2 = st.columns([5,1])
_ac1.markdown(f"Signed in as **{current_user()}**")
if _ac2.button("Sign out", use_container_width=True):
    logout()
st.divider()
render_user_admin()
