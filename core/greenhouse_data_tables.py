# ─────────────────────────────────────────────────────────────────────────────
# GREENHOUSE_CROPS
# Units: cycle=days, yield=kg/m²/harvest, dli=mol/m²/day, water=L/m²/cycle
# seed/substrate/nutrient=$/m²/cycle, natural_dli_fraction=0-1
# Sources: Wageningen UR KWIN 2024, Tridge Market Intelligence
# ─────────────────────────────────────────────────────────────────────────────

GREENHOUSE_CROPS = {
    "Tomato (Beef)": {
        "cycle": 330, "days_between": 0, "yield": 68.5, "yield_h2": 0, "yield_h3": 0,
        "dli": 28.0, "ec": 2.5, "water": 1200, "nutrient": 0.15, "seed": 0.65, "substrate": 1.20,
        "wf": 25.0, "tr": 0.85, "price_low": 1.45, "price_base": 2.15, "price_high": 3.10,
        "natural_dli_fraction": 0.65, "structure_type": "venlo"
    },
    "Tomato (Cherry)": {
        "cycle": 330, "days_between": 0, "yield": 32.0, "yield_h2": 0, "yield_h3": 0,
        "dli": 26.0, "ec": 3.5, "water": 1050, "nutrient": 0.18, "seed": 0.85, "substrate": 1.20,
        "wf": 45.0, "tr": 0.82, "price_low": 3.20, "price_base": 4.50, "price_high": 6.80,
        "natural_dli_fraction": 0.65, "structure_type": "venlo"
    },
    "Tomato (Cocktail)": {
        "cycle": 330, "days_between": 0, "yield": 45.0, "yield_h2": 0, "yield_h3": 0,
        "dli": 27.0, "ec": 3.0, "water": 1100, "nutrient": 0.17, "seed": 0.75, "substrate": 1.20,
        "wf": 35.0, "tr": 0.83, "price_low": 2.50, "price_base": 3.40, "price_high": 4.90,
        "natural_dli_fraction": 0.65, "structure_type": "venlo"
    },
    "Cucumber": {
        "cycle": 330, "days_between": 0, "yield": 78.0, "yield_h2": 0, "yield_h3": 0,
        "dli": 25.0, "ec": 2.2, "water": 1400, "nutrient": 0.12, "seed": 0.45, "substrate": 1.10,
        "wf": 22.0, "tr": 0.90, "price_low": 1.10, "price_base": 1.80, "price_high": 2.60,
        "natural_dli_fraction": 0.60, "structure_type": "venlo"
    },
    "Sweet Pepper": {
        "cycle": 330, "days_between": 0, "yield": 31.5, "yield_h2": 0, "yield_h3": 0,
        "dli": 25.0, "ec": 2.8, "water": 950, "nutrient": 0.16, "seed": 0.55, "substrate": 1.30,
        "wf": 38.0, "tr": 0.75, "price_low": 2.10, "price_base": 2.85, "price_high": 4.20,
        "natural_dli_fraction": 0.70, "structure_type": "venlo"
    },
    # Aubergine/Eggplant — heated Venlo substrate production (also available as soil crop in POLYTUNNEL_CROPS)
    "Eggplant": {
        "cycle": 330, "days_between": 0, "yield": 35.0, "yield_h2": 0, "yield_h3": 0,
        "dli": 26.0, "ec": 2.5, "water": 1150, "nutrient": 0.14, "seed": 0.40, "substrate": 1.25,
        "wf": 32.0, "tr": 0.88, "price_low": 1.50, "price_base": 2.20, "price_high": 3.10,
        "natural_dli_fraction": 0.65, "structure_type": "venlo"
    },
    "Lettuce (Romaine)": {
        "cycle": 40, "days_between": 0, "yield": 4.5, "yield_h2": 0, "yield_h3": 0,
        "dli": 16.0, "ec": 1.8, "water": 42, "nutrient": 0.08, "seed": 0.14, "substrate": 0.48,
        "wf": 20.0, "tr": 0.94, "price_low": 1.50, "price_base": 2.20, "price_high": 3.15,
        "natural_dli_fraction": 0.55, "structure_type": "multi-span"
    },
    "Baby Spinach": {
        "cycle": 28, "days_between": 0, "yield": 1.8, "yield_h2": 0, "yield_h3": 0,
        "dli": 15.5, "ec": 1.7, "water": 30, "nutrient": 0.09, "seed": 0.28, "substrate": 0.45,
        "wf": 22.0, "tr": 0.96, "price_low": 4.80, "price_base": 6.20, "price_high": 9.50,
        "natural_dli_fraction": 0.55, "structure_type": "multi-span"
    },
    "Basil": {
        "cycle": 42, "days_between": 14, "yield": 2.2, "yield_h2": 0.8, "yield_h3": 0.6,
        "dli": 17.0, "ec": 1.8, "water": 45, "nutrient": 0.10, "seed": 0.15, "substrate": 0.50,
        "wf": 25.0, "tr": 0.92, "price_low": 8.50, "price_base": 12.00, "price_high": 18.50,
        "natural_dli_fraction": 0.60, "structure_type": "multi-span"
    },
    "Mint": {
        "cycle": 65, "days_between": 24, "yield": 2.1, "yield_h2": 0.85, "yield_h3": 0.75,
        "dli": 18.0, "ec": 2.2, "water": 55, "nutrient": 0.11, "seed": 0.18, "substrate": 0.55,
        "wf": 28.0, "tr": 0.90, "price_low": 10.50, "price_base": 14.20, "price_high": 21.00,
        "natural_dli_fraction": 0.60, "structure_type": "multi-span"
    },
    "Strawberry": {
        "cycle": 210, "days_between": 0, "yield": 12.5, "yield_h2": 0, "yield_h3": 0,
        "dli": 22.0, "ec": 1.5, "water": 600, "nutrient": 0.15, "seed": 1.20, "substrate": 2.10,
        "wf": 65.0, "tr": 0.70, "price_low": 3.80, "price_base": 5.50, "price_high": 9.20,
        "natural_dli_fraction": 0.65, "structure_type": "venlo"
    },
    "Wasabi Supreme (2-Year Rhizome)": {
        "yield": 6.50, "cycle": 540, "days_between": 0,
        "yield_h2": 0.0, "yield_h3": 0.0,
        "dli": 8.0, "ec": 1.2, "water": 450.0, "nutrient": 0.12,
        "seed": 25.00, "substrate": 8.50, "wf": 69.2, "tr": 0.88,
        "price_low": 180.0, "price_base": 280.0, "price_high": 420.0,
        "natural_dli_fraction": 0.40, "structure_type": "venlo"
    },
    "Cannabis Flower (Greenhouse Auto-flower)": {
        "yield": 1.65, "cycle": 90, "days_between": 0,
        "yield_h2": 0.0, "yield_h3": 0.0,
        "dli": 30.0, "ec": 2.0, "water": 180.0, "nutrient": 0.15,
        "seed": 15.00, "substrate": 5.20, "wf": 109.0, "tr": 0.85,
        "price_low": 1200.0, "price_base": 1900.0, "price_high": 2600.0,
        "natural_dli_fraction": 0.65, "structure_type": "venlo"
    },
    "Australian Finger Lime (Caviar Citrus)": {
        "yield": 4.20, "cycle": 365, "days_between": 0,
        "yield_h2": 0.0, "yield_h3": 0.0,
        "dli": 25.0, "ec": 1.6, "water": 550.0, "nutrient": 0.10,
        "seed": 45.00, "substrate": 12.00, "wf": 130.9, "tr": 0.75,
        "price_low": 90.0, "price_base": 160.0, "price_high": 240.0,
        "natural_dli_fraction": 0.70, "structure_type": "venlo"
    },
    "Vanilla Orchid (Hand-pollinated)": {
        "yield": 0.45, "cycle": 300, "days_between": 0,
        "yield_h2": 0.0, "yield_h3": 0.0,
        "dli": 15.0, "ec": 1.4, "water": 380.0, "nutrient": 0.08,
        "seed": 65.00, "substrate": 18.00, "wf": 844.4, "tr": 0.90,
        "price_low": 350.0, "price_base": 550.0, "price_high": 850.0,
        "natural_dli_fraction": 0.55, "structure_type": "venlo"
    },
    # Source: WUR (Wageningen), Dutch KWIN Greenhouse Horticulture benchmark
    "Courgette (Greenhouse)": {
        "cycle": 150, "days_between": 0, "yield": 35.0, "yield_h2": 0.0, "yield_h3": 0.0,
        "dli": 20.0, "ec": 2.2, "water": 600.0, "nutrient": 0.15, "seed": 0.50, "substrate": 1.10,
        "wf": 30.0, "tr": 0.85, "price_low": 1.00, "price_base": 1.50, "price_high": 2.50,
        "natural_dli_fraction": 0.65, "structure_type": "venlo"
    },
    # Source: KWIN, WUR (Spain, Morocco, Netherlands benchmarks)
    "Chilli Pepper (Greenhouse)": {
        "cycle": 320, "days_between": 0, "yield": 26.0, "yield_h2": 0.0, "yield_h3": 0.0,
        "dli": 24.0, "ec": 2.5, "water": 800.0, "nutrient": 0.16, "seed": 0.60, "substrate": 1.20,
        "wf": 28.0, "tr": 0.85, "price_low": 2.50, "price_base": 4.50, "price_high": 7.00,
        "natural_dli_fraction": 0.68, "structure_type": "venlo"
    },
    # Source: KWIN, WUR (Heated venlo substrate)
    "Aubergine (Venlo)": {
        "cycle": 330, "days_between": 0, "yield": 55.0, "yield_h2": 0.0, "yield_h3": 0.0,
        "dli": 22.0, "ec": 2.0, "water": 1000.0, "nutrient": 0.15, "seed": 0.70, "substrate": 1.20,
        "wf": 25.0, "tr": 0.88, "price_low": 1.20, "price_base": 1.80, "price_high": 2.80,
        "natural_dli_fraction": 0.65, "structure_type": "venlo"
    },
    # Source: AHDB Soft Fruit, Wageningen Blueberry Research
    "Blueberry (Protected Cultivation)": {
        "cycle": 365, "days_between": 0, "yield": 9.0, "yield_h2": 0.0, "yield_h3": 0.0,
        "dli": 15.0, "ec": 1.0, "water": 450.0, "nutrient": 0.12, "seed": 1.50, "substrate": 2.50,
        "wf": 50.0, "tr": 0.75, "price_low": 5.00, "price_base": 8.00, "price_high": 14.00,
        "natural_dli_fraction": 0.70, "structure_type": "venlo"
    },
    # Source: KWIN, WUR
    "Cherry Tomato (On-vine Premium)": {
        "cycle": 330, "days_between": 0, "yield": 32.0, "yield_h2": 0.0, "yield_h3": 0.0,
        "dli": 28.0, "ec": 2.8, "water": 850.0, "nutrient": 0.16, "seed": 0.80, "substrate": 1.20,
        "wf": 35.0, "tr": 0.85, "price_low": 3.50, "price_base": 5.50, "price_high": 8.50,
        "natural_dli_fraction": 0.65, "structure_type": "venlo"
    },
    # Source: DLV Plant, Koppert, WUR Cut Flower Research
    "Cut Rose (Hybrid Tea)": {
        "cycle": 365, "days_between": 0, "yield": 8.8, "yield_h2": 0.0, "yield_h3": 0.0,
        "dli": 28.0, "ec": 1.8, "water": 900.0, "nutrient": 0.18, "seed": 2.00, "substrate": 1.80,
        "wf": 45.0, "tr": 0.80, "price_low": 8.00, "price_base": 12.00, "price_high": 18.00,
        "natural_dli_fraction": 0.65, "structure_type": "venlo"
    },
    # Source: DLV Plant, Dutch auction price data
    "Chrysanthemum (Pot/Cut)": {
        "cycle": 90, "days_between": 14, "yield": 5.6, "yield_h2": 0.0, "yield_h3": 0.0,
        "dli": 20.0, "ec": 1.6, "water": 200.0, "nutrient": 0.12, "seed": 0.80, "substrate": 0.60,
        "wf": 35.0, "tr": 0.85, "price_low": 3.00, "price_base": 4.50, "price_high": 6.50,
        "natural_dli_fraction": 0.60, "structure_type": "venlo"
    },
    # Source: WUR, Dutch Flower Auctions (Royal FloraHolland price data)
    "Gerbera": {
        "cycle": 365, "days_between": 0, "yield": 7.5, "yield_h2": 0.0, "yield_h3": 0.0,
        "dli": 22.0, "ec": 1.5, "water": 600.0, "nutrient": 0.14, "seed": 1.20, "substrate": 1.50,
        "wf": 40.0, "tr": 0.82, "price_low": 6.00, "price_base": 9.00, "price_high": 14.00,
        "natural_dli_fraction": 0.62, "structure_type": "venlo"
    },
    # Source: Dutch herb grower benchmarks
    "Dill": {
        "cycle": 35, "days_between": 0, "yield": 1.8, "yield_h2": 0.0, "yield_h3": 0.0,
        "dli": 15.0, "ec": 1.6, "water": 35.0, "nutrient": 0.10, "seed": 0.10, "substrate": 0.40,
        "wf": 20.0, "tr": 0.90, "price_low": 6.00, "price_base": 9.00, "price_high": 13.00,
        "natural_dli_fraction": 0.60, "structure_type": "multi-span"
    },
    # Source: KWIN, AHDB Horticulture
    "Parsley (Greenhouse)": {
        "cycle": 60, "days_between": 14, "yield": 2.5, "yield_h2": 0.8, "yield_h3": 0.6,
        "dli": 18.0, "ec": 1.8, "water": 60.0, "nutrient": 0.12, "seed": 0.12, "substrate": 0.50,
        "wf": 22.0, "tr": 0.92, "price_low": 5.50, "price_base": 8.50, "price_high": 12.00,
        "natural_dli_fraction": 0.60, "structure_type": "multi-span"
    },
    # Source: Dutch herb benchmarks, AHDB
    "Coriander (Greenhouse)": {
        "cycle": 35, "days_between": 0, "yield": 1.5, "yield_h2": 0.0, "yield_h3": 0.0,
        "dli": 14.0, "ec": 1.5, "water": 30.0, "nutrient": 0.10, "seed": 0.12, "substrate": 0.40,
        "wf": 20.0, "tr": 0.90, "price_low": 7.00, "price_base": 10.00, "price_high": 15.00,
        "natural_dli_fraction": 0.58, "structure_type": "multi-span"
    },
    # Source: Cornell CEA, Rakocy aquaponics nutrient management papers
    "Swiss Chard (GH Hydroponic)": {
        "cycle": 40, "days_between": 10, "yield": 3.5, "yield_h2": 0.7, "yield_h3": 0.5,
        "dli": 17.0, "ec": 1.8, "water": 45.0, "nutrient": 0.12, "seed": 0.15, "substrate": 0.50,
        "wf": 18.0, "tr": 0.90, "price_low": 3.50, "price_base": 5.00, "price_high": 7.50,
        "natural_dli_fraction": 0.60, "structure_type": "multi-span"
    },
    # Source: Rakocy 2006 UVI system papers, FAO Aquaponics Food and Agriculture
    "Watercress (GH Hydroponic)": {
        "cycle": 30, "days_between": 0, "yield": 2.0, "yield_h2": 0.0, "yield_h3": 0.0,
        "dli": 14.0, "ec": 1.2, "water": 80.0, "nutrient": 0.10, "seed": 0.10, "substrate": 0.30,
        "wf": 40.0, "tr": 0.85, "price_low": 8.00, "price_base": 12.00, "price_high": 18.00,
        "natural_dli_fraction": 0.58, "structure_type": "multi-span"
    },
    # Source: Cornell CEA Kale trials, WUR
    "Kale (GH Hydroponic)": {
        "cycle": 35, "days_between": 0, "yield": 1.8, "yield_h2": 0.0, "yield_h3": 0.0,
        "dli": 16.0, "ec": 1.8, "water": 40.0, "nutrient": 0.12, "seed": 0.15, "substrate": 0.45,
        "wf": 20.0, "tr": 0.90, "price_low": 4.50, "price_base": 7.00, "price_high": 11.00,
        "natural_dli_fraction": 0.60, "structure_type": "multi-span"
    },
    # Source: Cornell CEA, WUR
    "Pak Choi (GH Substrate)": {
        "cycle": 35, "days_between": 0, "yield": 3.0, "yield_h2": 0.0, "yield_h3": 0.0,
        "dli": 18.0, "ec": 1.8, "water": 45.0, "nutrient": 0.12, "seed": 0.18, "substrate": 0.50,
        "wf": 18.0, "tr": 0.90, "price_low": 3.00, "price_base": 4.50, "price_high": 7.00,
        "natural_dli_fraction": 0.60, "structure_type": "venlo"
    },
}

# ─────────────────────────────────────────────────────────────────────────────
# POLYTUNNEL_CROPS
# Units: same as GREENHOUSE_CROPS. EC=0 for soil-based crops.
# Seasonal production (Northern Europe), no supplemental lighting.
# Sources: AHDB Horticulture, CTIFL, FAO Irrigation Paper 56
# ─────────────────────────────────────────────────────────────────────────────

POLYTUNNEL_CROPS = {
    "Tomato (Round Soil)": {
        "cycle": 165, "days_between": 0, "yield": 28.0, "yield_h2": 0, "yield_h3": 0,
        "dli": 28.0, "ec": 0.0, "water": 450, "nutrient": 0.35, "seed": 0.55, "substrate": 0.25,
        "wf": 45.0, "tr": 0.82, "price_low": 0.95, "price_base": 1.40, "price_high": 2.10,
        "natural_dli_fraction": 1.0, "structure_type": "polytunnel"
    },
    "Cucumber (Soil)": {
        "cycle": 135, "days_between": 0, "yield": 32.0, "yield_h2": 0, "yield_h3": 0,
        "dli": 25.0, "ec": 0.0, "water": 400, "nutrient": 0.30, "seed": 0.40, "substrate": 0.20,
        "wf": 35.0, "tr": 0.88, "price_low": 0.80, "price_base": 1.25, "price_high": 1.95,
        "natural_dli_fraction": 1.0, "structure_type": "polytunnel"
    },
    "Sweet Pepper": {
        "cycle": 170, "days_between": 0, "yield": 20.0, "yield_h2": 0, "yield_h3": 0,
        "dli": 25.0, "ec": 0.0, "water": 380, "nutrient": 0.40, "seed": 0.50, "substrate": 0.25,
        "wf": 65.0, "tr": 0.75, "price_low": 1.40, "price_base": 1.95, "price_high": 2.80,
        "natural_dli_fraction": 1.0, "structure_type": "polytunnel"
    },
    "Strawberry (Elevated)": {
        "cycle": 135, "days_between": 0, "yield": 8.5, "yield_h2": 0, "yield_h3": 0,
        "dli": 22.0, "ec": 1.6, "water": 280, "nutrient": 0.85, "seed": 2.40, "substrate": 3.60,
        "wf": 85.0, "tr": 0.70, "price_low": 3.50, "price_base": 5.20, "price_high": 8.50,
        "natural_dli_fraction": 1.0, "structure_type": "polytunnel"
    },
    "Raspberry (Primocane)": {
        "cycle": 105, "days_between": 0, "yield": 2.4, "yield_h2": 0, "yield_h3": 0,
        "dli": 22.0, "ec": 1.5, "water": 350, "nutrient": 0.75, "seed": 4.50, "substrate": 4.80,
        "wf": 180.0, "tr": 0.72, "price_low": 8.50, "price_base": 12.40, "price_high": 18.20,
        "natural_dli_fraction": 1.0, "structure_type": "polytunnel"
    },
    "Lettuce (Soil)": {
        "cycle": 52, "days_between": 0, "yield": 3.8, "yield_h2": 0, "yield_h3": 0,
        "dli": 15.0, "ec": 0.0, "water": 120, "nutrient": 0.15, "seed": 0.18, "substrate": 0.10,
        "wf": 50.0, "tr": 0.92, "price_low": 0.75, "price_base": 1.15, "price_high": 1.80,
        "natural_dli_fraction": 1.0, "structure_type": "polytunnel"
    },
    "Basil (Soil Cuts)": {
        "cycle": 100, "days_between": 20, "yield": 1.3, "yield_h2": 0.85, "yield_h3": 0.70,
        "dli": 18.0, "ec": 0.0, "water": 180, "nutrient": 0.25, "seed": 0.20, "substrate": 0.15,
        "wf": 65.0, "tr": 0.90, "price_low": 6.50, "price_base": 9.80, "price_high": 15.20,
        "natural_dli_fraction": 1.0, "structure_type": "polytunnel"
    },
    "Courgette": {
        "cycle": 100, "days_between": 0, "yield": 12.5, "yield_h2": 0, "yield_h3": 0,
        "dli": 25.0, "ec": 0.0, "water": 320, "nutrient": 0.20, "seed": 0.35, "substrate": 0.15,
        "wf": 60.0, "tr": 0.85, "price_low": 0.65, "price_base": 1.05, "price_high": 1.65,
        "natural_dli_fraction": 1.0, "structure_type": "polytunnel"
    },
    "Aubergine": {
        "cycle": 160, "days_between": 0, "yield": 16.0, "yield_h2": 0, "yield_h3": 0,
        "dli": 26.0, "ec": 0.0, "water": 420, "nutrient": 0.45, "seed": 0.50, "substrate": 0.25,
        "wf": 75.0, "tr": 0.85, "price_low": 1.10, "price_base": 1.70, "price_high": 2.65,
        "natural_dli_fraction": 1.0, "structure_type": "polytunnel"
    },
    "Melon": {
        "cycle": 110, "days_between": 0, "yield": 4.2, "yield_h2": 0, "yield_h3": 0,
        "dli": 30.0, "ec": 0.0, "water": 280, "nutrient": 0.40, "seed": 0.85, "substrate": 0.20,
        "wf": 120.0, "tr": 0.78, "price_low": 1.20, "price_base": 1.80, "price_high": 2.85,
        "natural_dli_fraction": 1.0, "structure_type": "polytunnel"
    },
    "Watermelon": {
        "cycle": 120, "days_between": 0, "yield": 5.5, "yield_h2": 0, "yield_h3": 0,
        "dli": 30.0, "ec": 0.0, "water": 300, "nutrient": 0.40, "seed": 0.85, "substrate": 0.20,
        "wf": 140.0, "tr": 0.75, "price_low": 0.85, "price_base": 1.45, "price_high": 2.20,
        "natural_dli_fraction": 1.0, "structure_type": "polytunnel"
    },
    "Spinach (Baby Cuts)": {
        "cycle": 75, "days_between": 14, "yield": 1.2, "yield_h2": 0.90, "yield_h3": 0.75,
        "dli": 15.0, "ec": 0.0, "water": 110, "nutrient": 0.18, "seed": 0.35, "substrate": 0.10,
        "wf": 65.0, "tr": 0.95, "price_low": 2.80, "price_base": 4.10, "price_high": 6.80,
        "natural_dli_fraction": 1.0, "structure_type": "polytunnel"
    },
    "Rocket (Baby Cuts)": {
        "cycle": 90, "days_between": 15, "yield": 1.4, "yield_h2": 0.85, "yield_h3": 0.75,
        "dli": 16.0, "ec": 0.0, "water": 130, "nutrient": 0.15, "seed": 0.25, "substrate": 0.10,
        "wf": 70.0, "tr": 0.94, "price_low": 3.50, "price_base": 5.40, "price_high": 8.90,
        "natural_dli_fraction": 1.0, "structure_type": "polytunnel"
    },
    "French Bean": {
        "cycle": 90, "days_between": 0, "yield": 2.5, "yield_h2": 0, "yield_h3": 0,
        "dli": 22.0, "ec": 0.0, "water": 240, "nutrient": 0.25, "seed": 0.65, "substrate": 0.15,
        "wf": 150.0, "tr": 0.80, "price_low": 2.80, "price_base": 4.20, "price_high": 6.50,
        "natural_dli_fraction": 1.0, "structure_type": "polytunnel"
    },
    "Ginseng Root (Shaded Polytunnel)": {
        "yield": 2.10, "cycle": 365, "days_between": 0,
        "yield_h2": 0.0, "yield_h3": 0.0,
        "dli": 7.0, "ec": 0.0, "water": 290.0, "nutrient": 0.05,
        "seed": 14.00, "substrate": 3.00, "wf": 138.1, "tr": 0.65,
        "price_low": 250.0, "price_base": 450.0, "price_high": 750.0,
        "natural_dli_fraction": 1.0, "structure_type": "polytunnel"
    },
    "Caterpillar Fungus Mimic (Cordyceps Substrate)": {
        "yield": 0.35, "cycle": 120, "days_between": 0,
        "yield_h2": 0.0, "yield_h3": 0.0,
        "dli": 4.0, "ec": 0.0, "water": 45.0, "nutrient": 0.0,
        "seed": 35.00, "substrate": 22.00, "wf": 128.5, "tr": 0.40,
        "price_low": 4000.0, "price_base": 7000.0, "price_high": 12000.0,
        "natural_dli_fraction": 1.0, "structure_type": "polytunnel"
    },
    # Source: AHDB Horticulture, Brassica Grower Market Research, NIAB Brassica trials
    "Broccoli (Polytunnel)": {
        "cycle": 90, "days_between": 0, "yield": 2.8, "yield_h2": 0.0, "yield_h3": 0.0,
        "dli": 15.0, "ec": 0.0, "water": 120.0, "nutrient": 0.25, "seed": 0.30, "substrate": 0.15,
        "wf": 42.0, "tr": 0.85, "price_low": 1.50, "price_base": 2.00, "price_high": 3.00,
        "natural_dli_fraction": 1.0, "structure_type": "polytunnel"
    },
    # Source: AHDB, NIAB
    "Cauliflower (Polytunnel)": {
        "cycle": 100, "days_between": 0, "yield": 3.2, "yield_h2": 0.0, "yield_h3": 0.0,
        "dli": 15.0, "ec": 0.0, "water": 140.0, "nutrient": 0.28, "seed": 0.35, "substrate": 0.15,
        "wf": 44.0, "tr": 0.85, "price_low": 1.60, "price_base": 2.20, "price_high": 3.20,
        "natural_dli_fraction": 1.0, "structure_type": "polytunnel"
    },
    # Source: AHDB, Fresh Produce Journal
    "Kale (Polytunnel)": {
        "cycle": 120, "days_between": 25, "yield": 1.8, "yield_h2": 0.70, "yield_h3": 0.50,
        "dli": 14.0, "ec": 0.0, "water": 160.0, "nutrient": 0.20, "seed": 0.25, "substrate": 0.15,
        "wf": 55.0, "tr": 0.88, "price_low": 2.00, "price_base": 3.50, "price_high": 5.50,
        "natural_dli_fraction": 1.0, "structure_type": "polytunnel"
    },
    # Source: AHDB Blueberry Production Guide, USDA ERS Blueberry, Spanish MAPA stats
    "Blueberry (Polytunnel Soil)": {
        "cycle": 365, "days_between": 0, "yield": 3.0, "yield_h2": 0.0, "yield_h3": 0.0,
        "dli": 18.0, "ec": 0.0, "water": 350.0, "nutrient": 0.40, "seed": 3.50, "substrate": 0.55,
        "wf": 115.0, "tr": 0.75, "price_low": 4.50, "price_base": 7.00, "price_high": 11.00,
        "natural_dli_fraction": 1.0, "structure_type": "polytunnel"
    },
    # Source: AHDB Currant Guide, JKI Germany
    "Blackcurrant (Polytunnel)": {
        "cycle": 365, "days_between": 0, "yield": 2.0, "yield_h2": 0.0, "yield_h3": 0.0,
        "dli": 16.0, "ec": 0.0, "water": 300.0, "nutrient": 0.35, "seed": 2.50, "substrate": 0.40,
        "wf": 150.0, "tr": 0.75, "price_low": 3.00, "price_base": 4.50, "price_high": 7.00,
        "natural_dli_fraction": 1.0, "structure_type": "polytunnel"
    },
    # Source: AHDB, Dutch herb grower associations
    "Parsley (Polytunnel)": {
        "cycle": 120, "days_between": 21, "yield": 1.5, "yield_h2": 0.80, "yield_h3": 0.60,
        "dli": 15.0, "ec": 0.0, "water": 200.0, "nutrient": 0.25, "seed": 0.15, "substrate": 0.20,
        "wf": 60.0, "tr": 0.88, "price_low": 3.50, "price_base": 5.50, "price_high": 8.50,
        "natural_dli_fraction": 1.0, "structure_type": "polytunnel"
    },
    # Source: AHDB, KWIN
    "Chives (Polytunnel)": {
        "cycle": 150, "days_between": 20, "yield": 1.2, "yield_h2": 0.90, "yield_h3": 0.85,
        "dli": 14.0, "ec": 0.0, "water": 220.0, "nutrient": 0.28, "seed": 0.40, "substrate": 0.20,
        "wf": 55.0, "tr": 0.85, "price_low": 4.50, "price_base": 7.00, "price_high": 11.00,
        "natural_dli_fraction": 1.0, "structure_type": "polytunnel"
    },
    # Source: MAPA Spain, AHDB
    "Chilli Pepper (Unheated)": {
        "cycle": 180, "days_between": 0, "yield": 8.5, "yield_h2": 0.0, "yield_h3": 0.0,
        "dli": 22.0, "ec": 0.0, "water": 350.0, "nutrient": 0.45, "seed": 0.60, "substrate": 0.35,
        "wf": 40.0, "tr": 0.82, "price_low": 1.80, "price_base": 2.80, "price_high": 4.50,
        "natural_dli_fraction": 1.0, "structure_type": "polytunnel"
    },
    # Source: AHDB Root Vegetable trials, Fresh Produce Journal
    "Beetroot (Baby Polytunnel)": {
        "cycle": 60, "days_between": 0, "yield": 2.5, "yield_h2": 0.0, "yield_h3": 0.0,
        "dli": 16.0, "ec": 0.0, "water": 100.0, "nutrient": 0.20, "seed": 0.45, "substrate": 0.15,
        "wf": 40.0, "tr": 0.80, "price_low": 2.50, "price_base": 4.00, "price_high": 6.50,
        "natural_dli_fraction": 1.0, "structure_type": "polytunnel"
    },
    # Source: AHDB, CTIFL France
    "Butternut Squash": {
        "cycle": 120, "days_between": 0, "yield": 6.5, "yield_h2": 0.0, "yield_h3": 0.0,
        "dli": 20.0, "ec": 0.0, "water": 280.0, "nutrient": 0.35, "seed": 0.35, "substrate": 0.25,
        "wf": 45.0, "tr": 0.80, "price_low": 1.20, "price_base": 1.80, "price_high": 2.80,
        "natural_dli_fraction": 1.0, "structure_type": "polytunnel"
    },
    # Source: British Leafy Salad Association, AHDB Salad Crops
    "Baby Leaf Salad Mix": {
        "cycle": 40, "days_between": 15, "yield": 1.2, "yield_h2": 0.70, "yield_h3": 0.50,
        "dli": 12.0, "ec": 0.0, "water": 80.0, "nutrient": 0.15, "seed": 0.30, "substrate": 0.15,
        "wf": 45.0, "tr": 0.90, "price_low": 3.50, "price_base": 5.50, "price_high": 9.00,
        "natural_dli_fraction": 1.0, "structure_type": "polytunnel"
    },
}

# ─────────────────────────────────────────────────────────────────────────────
# FISH_SPECIES
# Units: grow_cycle_days, harvest_weight_kg, stocking_density=kg/m³
# FCR=feed conversion ratio, fingerling_cost and feed_cost_per_kg in $
# mortality_rate=%, protein_content=%, nutrient_output_per_kg_fish=g N/kg/day
# Sources: FAO Technical Paper 589, Ebeling & Timmons, European Price Reports 2024
# ─────────────────────────────────────────────────────────────────────────────

FISH_SPECIES = {
    "Tilapia (Nile)": {
        "grow_cycle_days": 210, "harvest_weight_kg": 0.70, "stocking_density": 60,
        "feed_conversion_ratio": 1.4, "fingerling_cost": 0.15, "feed_cost_per_kg": 1.15,
        "mortality_rate": 5, "protein_content": 32, "tank_type": "ras",
        "nutrient_output_per_kg_fish": 0.45, "price_low": 3.20, "price_base": 4.10, "price_high": 5.50
    },
    "Rainbow Trout": {
        "grow_cycle_days": 240, "harvest_weight_kg": 0.45, "stocking_density": 80,
        "feed_conversion_ratio": 1.1, "fingerling_cost": 0.35, "feed_cost_per_kg": 1.65,
        "mortality_rate": 8, "protein_content": 42, "tank_type": "ras",
        "nutrient_output_per_kg_fish": 0.38, "price_low": 5.80, "price_base": 7.20, "price_high": 9.50
    },
    "European Perch": {
        "grow_cycle_days": 300, "harvest_weight_kg": 0.25, "stocking_density": 65,
        "feed_conversion_ratio": 1.5, "fingerling_cost": 0.55, "feed_cost_per_kg": 1.90,
        "mortality_rate": 12, "protein_content": 45, "tank_type": "ras",
        "nutrient_output_per_kg_fish": 0.32, "price_low": 9.50, "price_base": 12.50, "price_high": 16.00
    },
    "Zander (Pike-perch)": {
        "grow_cycle_days": 420, "harvest_weight_kg": 1.1, "stocking_density": 80,
        "feed_conversion_ratio": 1.2, "fingerling_cost": 1.10, "feed_cost_per_kg": 2.05,
        "mortality_rate": 15, "protein_content": 48, "tank_type": "ras",
        "nutrient_output_per_kg_fish": 0.32, "price_low": 11.00, "price_base": 14.50, "price_high": 19.00
    },
    "Common Carp": {
        "grow_cycle_days": 270, "harvest_weight_kg": 1.20, "stocking_density": 45,
        "feed_conversion_ratio": 1.7, "fingerling_cost": 0.45, "feed_cost_per_kg": 1.05,
        "mortality_rate": 8, "protein_content": 30, "tank_type": "ras",
        "nutrient_output_per_kg_fish": 0.48, "price_low": 3.80, "price_base": 5.20, "price_high": 6.80
    },
    "African Catfish": {
        "grow_cycle_days": 180, "harvest_weight_kg": 1.10, "stocking_density": 150,
        "feed_conversion_ratio": 1.1, "fingerling_cost": 0.22, "feed_cost_per_kg": 1.25,
        "mortality_rate": 10, "protein_content": 38, "tank_type": "ras",
        "nutrient_output_per_kg_fish": 0.52, "price_low": 4.10, "price_base": 4.90, "price_high": 6.20
    },
    "Atlantic Salmon": {
        "grow_cycle_days": 480, "harvest_weight_kg": 4.5, "stocking_density": 100,
        "feed_conversion_ratio": 1.1, "fingerling_cost": 2.50, "feed_cost_per_kg": 1.95,
        "mortality_rate": 12, "protein_content": 44, "tank_type": "ras",
        "nutrient_output_per_kg_fish": 0.35, "price_low": 8.50, "price_base": 11.80, "price_high": 15.50
    },
    "Siberian Sturgeon": {
        "grow_cycle_days": 730, "harvest_weight_kg": 6.5, "stocking_density": 35.0,
        "feed_conversion_ratio": 1.35, "fingerling_cost": 18.50, "feed_cost_per_kg": 2.80,
        "mortality_rate": 6.5, "protein_content": 45.0, "tank_type": "ras",
        "nutrient_output_per_kg_fish": 0.42,
        "price_low": 22.0, "price_base": 38.0, "price_high": 55.0
    },
    "Arctic Char": {
        "grow_cycle_days": 410, "harvest_weight_kg": 1.8, "stocking_density": 50.0,
        "feed_conversion_ratio": 1.15, "fingerling_cost": 3.20, "feed_cost_per_kg": 3.10,
        "mortality_rate": 8.0, "protein_content": 48.0, "tank_type": "ras",
        "nutrient_output_per_kg_fish": 0.49,
        "price_low": 18.0, "price_base": 26.0, "price_high": 36.0
    },
}

# ─────────────────────────────────────────────────────────────────────────────
# GREENHOUSE_CAPEX
# Units: USD ($) per m² of total footprint
# Sources: AVAG (NL), German ZBG Industry Benchmarks 2024
# ─────────────────────────────────────────────────────────────────────────────

GREENHOUSE_CAPEX = {
    "Polytunnel": {
        "structure_cost_per_m2": 35.0,
        "climate_system_per_m2": 6.5,
        "irrigation_per_m2": 4.2,
        "lighting_per_m2": 0.0,
        "automation_per_m2": 2.5,
        "installation_factor": 1.15
    },
    "Multi-span": {
        "structure_cost_per_m2": 95.0,
        "climate_system_per_m2": 28.0,
        "irrigation_per_m2": 18.5,
        "lighting_per_m2": 25.0,
        "automation_per_m2": 12.0,
        "installation_factor": 1.25
    },
    "Venlo": {
        "structure_cost_per_m2": 218.0,
        "climate_system_per_m2": 65.0,
        "irrigation_per_m2": 32.0,
        "lighting_per_m2": 85.0,
        "automation_per_m2": 28.0,
        "installation_factor": 1.35
    },
}

# ─────────────────────────────────────────────────────────────────────────────
# AQUAPONICS_CAPEX
# Units: USD ($) per m³ of tank volume
# greenhouse_integration_cost_per_m2 is footprint-based
# Sources: NRAC Recirculating Aquaculture Systems Engineering, WUR
# ─────────────────────────────────────────────────────────────────────────────

AQUAPONICS_CAPEX = {
    # ── Decoupled mode ────────────────────────────────────────────────────────
    # Two independent water circuits (fish loop + plant loop) with a treatment
    # layer between them. Higher filtration, plumbing, monitoring and integration
    # costs reflecting dual-circuit complexity and pH/UV treatment infrastructure.
    "decoupled": {
        "Small-scale (<100m³)": {
            "tank_cost_per_m3":                  450.0,
            "filtration_per_m3":                 750.0,   # includes treatment unit (UV, settling, pH adjust)
            "aeration_per_m3":                   180.0,
            "monitoring_per_m3":                 120.0,   # dual EC/pH monitoring (fish loop + plant loop)
            "plumbing_per_m3":                   210.0,   # two full circuits
            "greenhouse_integration_cost_per_m2": 42.0,   # nutrient top-up, distribution, plant-side pumps
            "installation_factor":               1.40,
        },
        "Commercial-scale (>100m³)": {
            "tank_cost_per_m3":                  280.0,
            "filtration_per_m3":                 420.0,
            "aeration_per_m3":                   130.0,
            "monitoring_per_m3":                  65.0,
            "plumbing_per_m3":                   145.0,
            "greenhouse_integration_cost_per_m2": 35.0,
            "installation_factor":               1.30,
        },
    },
    # ── Coupled mode ──────────────────────────────────────────────────────────
    # Single shared water loop: fish tank → biofilter → plant beds → fish tank.
    # Lower filtration (one shared biofilter), simpler plumbing (one circuit),
    # single monitoring system, and lower integration cost (direct NFT/DWC feed,
    # no treatment layer or separate plant pump circuit).
    # Per-m³ component cost is ~21% lower than decoupled at both scale tiers.
    "coupled": {
        "Small-scale (<100m³)": {
            "tank_cost_per_m3":                  450.0,   # same tanks regardless of mode
            "filtration_per_m3":                 518.0,   # shared biofilter only, no treatment unit
            "aeration_per_m3":                   160.0,   # no separate plant-side aeration circuit
            "monitoring_per_m3":                  85.0,   # single EC/pH loop
            "plumbing_per_m3":                   149.0,   # one circuit
            "greenhouse_integration_cost_per_m2": 18.0,   # simple NFT/DWC manifold direct from fish loop
            "installation_factor":               1.30,    # simpler commissioning
        },
        "Commercial-scale (>100m³)": {
            "tank_cost_per_m3":                  280.0,
            "filtration_per_m3":                 290.0,
            "aeration_per_m3":                   116.0,
            "monitoring_per_m3":                  46.0,
            "plumbing_per_m3":                   103.0,
            "greenhouse_integration_cost_per_m2": 15.0,
            "installation_factor":               1.20,
        },
    },
}
# ==============================================================================
# AQUAPONICS & GREENHOUSE MODELLING LAYER
# Version: 3.1 (Production Ready — key names verified against crop dictionaries)
# Data Calibration: European Commercial Midpoints (WUR, FAO, AHDB, CTIFL benchmarks)
# Currency: USD ($)
# ==============================================================================
# KEY NAMING CONVENTION:
#   All keys in CROP_NUTRIENT_DEMAND match EXACTLY the keys used in
#   GREENHOUSE_CROPS and POLYTUNNEL_CROPS. Do not rename keys independently.
# ==============================================================================


# ==============================================================================
# DICTIONARY 1 - FISH_SYSTEM_PARAMS
# PURPOSE: Sizing of RAS engineering systems (aeration, biofiltration, volume)
# and determination of plant compatibility in coupled aquaponics systems.
# UNITS:
#   oxygen_consumption_g_per_kg_per_hour : g O2 / kg fish / hour
#   water_exchange_rate_pct_per_day      : % of total system volume per day
#   optimal_temp_min/max_c               : degrees Celsius (optimal growth range)
#   temp_min/max_survival_c              : degrees Celsius (survival limits)
#   ph_min / ph_max                      : standard pH scale
#   ammonia_tolerance_mg_per_l           : mg/L Total Ammonia Nitrogen (TAN)
#   min_system_volume_m3                 : cubic metres
#   feed_protein_requirement_pct         : % of diet by weight
#   waste_solids_per_kg_feed_g           : grams dry matter TSS per kg of feed
# SOURCES: Timmons & Ebeling RAS Engineering (2013), FAO Technical Paper 589,
#   FAO Species Fact Sheets, FishBase, Boyd & Tucker (1998),
#   Rakocy USVI Aquaponics Research, Masser et al. (1999).
# ==============================================================================

FISH_SYSTEM_PARAMS = {
    "Tilapia (Nile)": {
        "oxygen_consumption_g_per_kg_per_hour": 3.2,    # Timmons & Ebeling (2013) warm-water species benchmark
        "water_exchange_rate_pct_per_day": 2.5,          # FAO Technical Paper 589 rule of thumb
        "optimal_temp_min_c": 25.0,                      # FAO culturing guidelines Oreochromis niloticus
        "optimal_temp_max_c": 30.0,                      # FAO culturing guidelines Oreochromis niloticus
        "temp_min_survival_c": 10.0,                     # FishBase thermal tolerance limits
        "temp_max_survival_c": 35.0,                     # FishBase thermal tolerance limits
        "ph_min": 6.5,                                   # Boyd & Tucker (1998)
        "ph_max": 9.0,                                   # Boyd & Tucker (1998)
        "ammonia_tolerance_mg_per_l": 3.0,               # Emerson et al. — relatively high tolerance
        "coupled_aquaponics_compatible": True,           # Warm optimal temp (25-30C) overlaps greenhouse crops; adaptable to pH 7.0
        "decoupled_aquaponics_compatible": True,         # All species compatible with decoupled systems
        "min_system_volume_m3": 1.0,                     # Rakocy (2006) USVI minimum viable buffering volume
        "feed_protein_requirement_pct": 32.0,            # NRC (2011) Nutrient Requirements of Fish
        "waste_solids_per_kg_feed_g": 280.0,             # Masser et al. (1999) RAS waste characterisation
    },
    "Rainbow Trout": {
        "oxygen_consumption_g_per_kg_per_hour": 4.5,    # Timmons & Ebeling cold-water active species benchmark
        "water_exchange_rate_pct_per_day": 5.0,          # Requires pristine water quality; higher exchange rates
        "optimal_temp_min_c": 10.0,                      # FAO species fact sheet Oncorhynchus mykiss
        "optimal_temp_max_c": 16.0,                      # FAO species fact sheet Oncorhynchus mykiss
        "temp_min_survival_c": 0.0,                      # FishBase thermal data
        "temp_max_survival_c": 25.0,                     # FishBase (high stress above 21C)
        "ph_min": 6.5,                                   # Boyd & Tucker
        "ph_max": 8.0,                                   # Boyd & Tucker
        "ammonia_tolerance_mg_per_l": 0.5,               # Emerson et al. — highly sensitive
        "coupled_aquaponics_compatible": False,          # Cold optimal temp (10-16C) does not overlap warm-water plant production
        "decoupled_aquaponics_compatible": True,         # All species compatible with decoupled systems
        "min_system_volume_m3": 2.0,                     # Commercial RAS guidelines — needs high stability
        "feed_protein_requirement_pct": 42.0,            # NRC (2011) — higher protein for carnivores
        "waste_solids_per_kg_feed_g": 250.0,             # Lower due to high digestibility of premium feeds
    },
    "European Perch": {
        "oxygen_consumption_g_per_kg_per_hour": 2.8,    # Fontaine et al. bioenergetics of Perca fluviatilis
        "water_exchange_rate_pct_per_day": 3.0,          # Moderate exchange requirement
        "optimal_temp_min_c": 20.0,                      # FAO and European RAS production guidelines
        "optimal_temp_max_c": 25.0,                      # FAO and European RAS production guidelines
        "temp_min_survival_c": 2.0,                      # FishBase
        "temp_max_survival_c": 30.0,                     # FishBase
        "ph_min": 6.0,                                   # Slightly more tolerant of acidic conditions
        "ph_max": 8.0,                                   # Standard aquaculture limits
        "ammonia_tolerance_mg_per_l": 1.0,               # Moderate sensitivity benchmark
        "coupled_aquaponics_compatible": True,           # Temp range overlaps well with many hydroponic crops
        "decoupled_aquaponics_compatible": True,         # All species compatible with decoupled systems
        "min_system_volume_m3": 1.0,                     # Standard RAS minimum buffering requirement
        "feed_protein_requirement_pct": 40.0,            # Carnivorous diet requirements
        "waste_solids_per_kg_feed_g": 260.0,             # Intermediate solid waste production
    },
    "Zander (Pike-perch)": {
        "oxygen_consumption_g_per_kg_per_hour": 3.0,    # RAS bioenergetics for Sander lucioperca
        "water_exchange_rate_pct_per_day": 4.0,          # Sensitive to poor water quality
        "optimal_temp_min_c": 22.0,                      # European intensive RAS guidelines
        "optimal_temp_max_c": 26.0,                      # European intensive RAS guidelines
        "temp_min_survival_c": 4.0,                      # FishBase
        "temp_max_survival_c": 30.0,                     # FishBase
        "ph_min": 6.5,                                   # Typical sensitivity
        "ph_max": 8.0,                                   # Typical sensitivity
        "ammonia_tolerance_mg_per_l": 0.8,               # Highly sensitive to TAN spikes
        "coupled_aquaponics_compatible": True,           # 22-26C excellent for greenhouse crops (tomato, cucumber)
        "decoupled_aquaponics_compatible": True,         # All species compatible with decoupled systems
        "min_system_volume_m3": 2.0,                     # Stress-prone species; needs larger buffering volume
        "feed_protein_requirement_pct": 45.0,            # High protein carnivore
        "waste_solids_per_kg_feed_g": 240.0,             # High digestibility carnivorous feed
    },
    "Common Carp": {
        "oxygen_consumption_g_per_kg_per_hour": 2.0,    # Timmons & Ebeling benchmark for cyprinids
        "water_exchange_rate_pct_per_day": 2.0,          # Very hardy; low exchange viable
        "optimal_temp_min_c": 24.0,                      # FAO species fact sheet Cyprinus carpio
        "optimal_temp_max_c": 28.0,                      # FAO species fact sheet Cyprinus carpio
        "temp_min_survival_c": 2.0,                      # FishBase
        "temp_max_survival_c": 35.0,                     # FishBase
        "ph_min": 6.5,                                   # Boyd & Tucker
        "ph_max": 9.0,                                   # Boyd & Tucker — highly alkaline tolerant
        "ammonia_tolerance_mg_per_l": 2.5,               # High tolerance typical of carp
        "coupled_aquaponics_compatible": True,           # Optimal temp overlaps greenhouse crops
        "decoupled_aquaponics_compatible": True,         # All species compatible with decoupled systems
        "min_system_volume_m3": 1.0,                     # Robust species; standard volume adequate
        "feed_protein_requirement_pct": 30.0,            # Omnivore requirements (NRC)
        "waste_solids_per_kg_feed_g": 300.0,             # Lower digestibility of omnivorous diets yields more solids
    },
    "African Catfish": {
        "oxygen_consumption_g_per_kg_per_hour": 1.5,    # Lower due to air-breathing capability (Clarias gariepinus)
        "water_exchange_rate_pct_per_day": 1.0,          # Extremely robust; tolerant of turbid/low-exchange water
        "optimal_temp_min_c": 25.0,                      # FAO culturing guidelines
        "optimal_temp_max_c": 30.0,                      # FAO culturing guidelines
        "temp_min_survival_c": 15.0,                     # Cold stress sensitive
        "temp_max_survival_c": 35.0,                     # High heat tolerance
        "ph_min": 6.0,                                   # Highly adaptable
        "ph_max": 8.5,                                   # Highly adaptable
        "ammonia_tolerance_mg_per_l": 3.5,               # Most ammonia-tolerant commercial species
        "coupled_aquaponics_compatible": True,           # Good temperature overlap for warm greenhouse crops
        "decoupled_aquaponics_compatible": True,         # All species compatible with decoupled systems
        "min_system_volume_m3": 0.5,                     # Can be raised at very high density in small volumes
        "feed_protein_requirement_pct": 35.0,            # NRC requirements
        "waste_solids_per_kg_feed_g": 280.0,             # Masser et al. benchmark
    },
    "Atlantic Salmon": {
        "oxygen_consumption_g_per_kg_per_hour": 4.8,    # Thorarensen & Farrell (2011) — high O2 demand
        "water_exchange_rate_pct_per_day": 5.0,          # Intensive smolt/grow-out RAS requirement
        "optimal_temp_min_c": 12.0,                      # FAO species fact sheet Salmo salar
        "optimal_temp_max_c": 16.0,                      # FAO species fact sheet Salmo salar
        "temp_min_survival_c": 0.0,                      # FishBase
        "temp_max_survival_c": 22.0,                     # FishBase (high mortality risk above 20C)
        "ph_min": 6.5,                                   # Narrow optimal band
        "ph_max": 8.0,                                   # Narrow optimal band
        "ammonia_tolerance_mg_per_l": 0.5,               # Highly sensitive
        "coupled_aquaponics_compatible": False,          # Cold water species; optimal temps incompatible with greenhouse crops
        "decoupled_aquaponics_compatible": True,         # All species compatible with decoupled systems
        "min_system_volume_m3": 5.0,                     # Requires large buffering and specific hydrodynamics
        "feed_protein_requirement_pct": 45.0,            # Premium carnivore diet
        "waste_solids_per_kg_feed_g": 220.0,             # Highly digestible modern salmon feeds produce fewer solids
    },
    "Siberian Sturgeon": {
        "oxygen_consumption_g_per_kg_per_hour": 0.38,
        "water_exchange_rate_pct_per_day": 6.0,
        "target_water_temp_c": 17.5,
        "ammonia_sensitivity": "high",
        "salinity_tolerance_ppt": 5.0
    },
    "Arctic Char": {
        "oxygen_consumption_g_per_kg_per_hour": 0.65,
        "water_exchange_rate_pct_per_day": 12.0,
        "target_water_temp_c": 11.5,
        "ammonia_sensitivity": "high",
        "salinity_tolerance_ppt": 15.0
    },
}


# ==============================================================================
# DICTIONARY 2 - CROP_NUTRIENT_DEMAND
# PURPOSE: Plant nutrient offset calculations and fish-to-plant ratio balancing
# in both coupled and decoupled aquaponics configurations.
# UNITS:
#   n/p/k_demand_g_per_m2_per_day : grams per m² per day (peak active growth)
#   preferred_temp_min/max_c      : degrees Celsius
#   aquaponics_suitability        : "high" | "medium" | "low"
# SOURCES: Sonneveld & Voogt — Plant Nutrition of Greenhouse Crops (Wageningen),
#   Rakocy et al. USVI aquaponics system data, Lennard & Leonard (2006),
#   Love et al. (2015) aquaponics production survey,
#   Graber & Junge (2009) Swiss aquaponics trials.
# NOTE: Keys match EXACTLY the keys in GREENHOUSE_CROPS and POLYTUNNEL_CROPS.
#   Polytunnel (soil-based) crops are rated "low" suitability since aquaponics
#   nutrient delivery is incompatible with soil-based production systems.
# ==============================================================================

CROP_NUTRIENT_DEMAND = {

    # ── GREENHOUSE CROPS (hydroponic production) ─────────────────────────────

    "Tomato (Beef)": {
        "n_demand_g_per_m2_per_day": 1.30,              # Sonneveld & Voogt — large fruiting crop, high N demand
        "p_demand_g_per_m2_per_day": 0.35,              # Peak fruiting phosphorus demand
        "k_demand_g_per_m2_per_day": 2.90,              # Very high K for large fruit development
        "preferred_temp_min_c": 18.0,
        "preferred_temp_max_c": 28.0,                   # Pollination failure above 30C
        "aquaponics_suitability": "low",                # Love et al. (2015) — frequent deficiencies in coupled systems
        "notes": "Performs best in decoupled systems. Severe K and Ca supplementation needed if coupled.",
    },
    "Tomato (Cherry)": {
        "n_demand_g_per_m2_per_day": 1.10,
        "p_demand_g_per_m2_per_day": 0.30,
        "k_demand_g_per_m2_per_day": 2.50,
        "preferred_temp_min_c": 18.0,
        "preferred_temp_max_c": 28.0,
        "aquaponics_suitability": "medium",             # Slightly more forgiving than beef tomatoes
        "notes": "Requires K supplementation during generative phase. Decoupled systems preferred.",
    },
    "Tomato (Cocktail)": {
        "n_demand_g_per_m2_per_day": 1.15,
        "p_demand_g_per_m2_per_day": 0.32,
        "k_demand_g_per_m2_per_day": 2.60,
        "preferred_temp_min_c": 18.0,
        "preferred_temp_max_c": 28.0,
        "aquaponics_suitability": "medium",
        "notes": "Requires K supplementation during generative phase. Decoupled systems preferred.",
    },
    "Cucumber": {
        "n_demand_g_per_m2_per_day": 1.40,              # Rapid vegetative and fruiting growth
        "p_demand_g_per_m2_per_day": 0.30,
        "k_demand_g_per_m2_per_day": 2.40,
        "preferred_temp_min_c": 22.0,
        "preferred_temp_max_c": 28.0,
        "aquaponics_suitability": "medium",
        "notes": "Prone to powdery mildew. High N input suits pairing with heavy-feeding fish species.",
    },
    "Sweet Pepper": {
        "n_demand_g_per_m2_per_day": 1.05,              # Sonneveld & Voogt
        "p_demand_g_per_m2_per_day": 0.28,
        "k_demand_g_per_m2_per_day": 2.00,              # High K for fruit development
        "preferred_temp_min_c": 21.0,
        "preferred_temp_max_c": 26.0,
        "aquaponics_suitability": "low",
        "notes": "Not recommended for coupled systems due to strict nutrient ratios during generative phase.",
    },
    "Eggplant": {
        "n_demand_g_per_m2_per_day": 1.10,
        "p_demand_g_per_m2_per_day": 0.25,
        "k_demand_g_per_m2_per_day": 2.10,
        "preferred_temp_min_c": 22.0,
        "preferred_temp_max_c": 28.0,
        "aquaponics_suitability": "low",
        "notes": "Heavy feeder. Frequent macro-nutrient deficiencies reported in coupled systems.",
    },
    "Lettuce (Romaine)": {
        "n_demand_g_per_m2_per_day": 0.55,              # Sonneveld & Voogt (2009) standard
        "p_demand_g_per_m2_per_day": 0.12,
        "k_demand_g_per_m2_per_day": 0.65,
        "preferred_temp_min_c": 15.0,
        "preferred_temp_max_c": 24.0,                   # Heat stress / bolting above this
        "aquaponics_suitability": "high",               # Rakocy USVI — standard baseline crop
        "notes": "Excellent performance in coupled systems. Standard baseline crop for fish-to-plant ratio calculations.",
    },
    "Baby Spinach": {
        "n_demand_g_per_m2_per_day": 0.45,
        "p_demand_g_per_m2_per_day": 0.10,
        "k_demand_g_per_m2_per_day": 0.50,
        "preferred_temp_min_c": 10.0,
        "preferred_temp_max_c": 20.0,
        "aquaponics_suitability": "medium",
        "notes": "Sensitive to Pythium in warm water. Best paired with cold-water fish in coupled systems.",
    },
    "Basil": {
        "n_demand_g_per_m2_per_day": 0.60,              # Lennard (2012) aquaponics nutrient balance
        "p_demand_g_per_m2_per_day": 0.15,
        "k_demand_g_per_m2_per_day": 0.70,
        "preferred_temp_min_c": 20.0,
        "preferred_temp_max_c": 28.0,
        "aquaponics_suitability": "high",               # FAO Technical Paper 589
        "notes": "Highly profitable in aquaponics. Roots sensitive to Pythium if dissolved oxygen is low.",
    },
    "Mint": {
        "n_demand_g_per_m2_per_day": 0.50,
        "p_demand_g_per_m2_per_day": 0.12,
        "k_demand_g_per_m2_per_day": 0.60,
        "preferred_temp_min_c": 15.0,
        "preferred_temp_max_c": 25.0,
        "aquaponics_suitability": "high",
        "notes": "Aggressive root growth can clog NFT channels; DWC or media bed systems preferred.",
    },
    "Strawberry": {
        "n_demand_g_per_m2_per_day": 0.40,
        "p_demand_g_per_m2_per_day": 0.15,              # Elevated P demand during flowering
        "k_demand_g_per_m2_per_day": 0.60,              # K needed for fruit brix/sugar
        "preferred_temp_min_c": 15.0,
        "preferred_temp_max_c": 22.0,
        "aquaponics_suitability": "medium",             # Graber & Junge (2009) Swiss aquaponics trials
        "notes": "Sensitive to elevated pH and EC. Iron chlorosis common in coupled systems above pH 7.0.",
    },

    # ── POLYTUNNEL CROPS (soil-based production) ──────────────────────────────
    # All polytunnel crops rated aquaponics_suitability: "low" — soil-based
    # production systems are incompatible with aquaponics nutrient delivery.
    # Nutrient demand figures reflect soil-mediated uptake rates, which are
    # lower than hydroponic figures due to soil buffering and slower release.

    "Tomato (Round Soil)": {
        "n_demand_g_per_m2_per_day": 0.80,
        "p_demand_g_per_m2_per_day": 0.20,
        "k_demand_g_per_m2_per_day": 1.80,
        "preferred_temp_min_c": 16.0,
        "preferred_temp_max_c": 26.0,
        "aquaponics_suitability": "low",
        "notes": "Soil-based production; incompatible with aquaponics nutrient delivery.",
    },
    "Cucumber (Soil)": {
        "n_demand_g_per_m2_per_day": 0.90,
        "p_demand_g_per_m2_per_day": 0.18,
        "k_demand_g_per_m2_per_day": 1.50,
        "preferred_temp_min_c": 18.0,
        "preferred_temp_max_c": 26.0,
        "aquaponics_suitability": "low",
        "notes": "Soil-based production; incompatible with aquaponics nutrient delivery.",
    },
    "Sweet Pepper": {
        # NOTE: This entry covers both GREENHOUSE_CROPS "Sweet Pepper" and
        # POLYTUNNEL_CROPS "Sweet Pepper". The greenhouse version (hydroponic)
        # uses higher daily demand figures from Sonneveld & Voogt. The polytunnel
        # version is soil-based and would have lower effective demand, but since
        # aquaponics suitability is "low" for polytunnel crops regardless, the
        # same entry serves both use cases in the calculation engine. If the
        # engine needs to differentiate, add "Sweet Pepper (Polytunnel)" as a
        # separate key matching the polytunnel crop key exactly.
        "n_demand_g_per_m2_per_day": 1.05,
        "p_demand_g_per_m2_per_day": 0.28,
        "k_demand_g_per_m2_per_day": 2.00,
        "preferred_temp_min_c": 18.0,
        "preferred_temp_max_c": 26.0,
        "aquaponics_suitability": "low",
        "notes": "Not recommended for coupled systems. Strict nutrient ratios required during generative phase.",
    },
    "Strawberry (Elevated)": {
        "n_demand_g_per_m2_per_day": 0.25,
        "p_demand_g_per_m2_per_day": 0.10,
        "k_demand_g_per_m2_per_day": 0.45,
        "preferred_temp_min_c": 14.0,
        "preferred_temp_max_c": 24.0,
        "aquaponics_suitability": "low",
        "notes": "Substrate/soil trough setup; relies on fertigation rather than RAS effluent.",
    },
    "Raspberry (Primocane)": {
        "n_demand_g_per_m2_per_day": 0.30,
        "p_demand_g_per_m2_per_day": 0.10,
        "k_demand_g_per_m2_per_day": 0.50,
        "preferred_temp_min_c": 14.0,
        "preferred_temp_max_c": 22.0,
        "aquaponics_suitability": "low",
        "notes": "Soil-based production; incompatible with aquaponics nutrient delivery.",
    },
    "Lettuce (Soil)": {
        "n_demand_g_per_m2_per_day": 0.35,
        "p_demand_g_per_m2_per_day": 0.08,
        "k_demand_g_per_m2_per_day": 0.40,
        "preferred_temp_min_c": 12.0,
        "preferred_temp_max_c": 22.0,
        "aquaponics_suitability": "low",
        "notes": "Soil-based production; incompatible with aquaponics nutrient delivery.",
    },
    "Basil (Soil Cuts)": {
        "n_demand_g_per_m2_per_day": 0.40,
        "p_demand_g_per_m2_per_day": 0.10,
        "k_demand_g_per_m2_per_day": 0.50,
        "preferred_temp_min_c": 18.0,
        "preferred_temp_max_c": 28.0,
        "aquaponics_suitability": "low",
        "notes": "Soil-based production; incompatible with aquaponics nutrient delivery.",
    },
    "Courgette": {
        "n_demand_g_per_m2_per_day": 0.85,
        "p_demand_g_per_m2_per_day": 0.20,
        "k_demand_g_per_m2_per_day": 1.60,
        "preferred_temp_min_c": 18.0,
        "preferred_temp_max_c": 26.0,
        "aquaponics_suitability": "low",
        "notes": "Soil-based production; incompatible with aquaponics nutrient delivery.",
    },
    "Aubergine": {
        "n_demand_g_per_m2_per_day": 0.75,
        "p_demand_g_per_m2_per_day": 0.18,
        "k_demand_g_per_m2_per_day": 1.50,
        "preferred_temp_min_c": 20.0,
        "preferred_temp_max_c": 28.0,
        "aquaponics_suitability": "low",
        "notes": "Soil-based production; incompatible with aquaponics nutrient delivery.",
    },
    "Melon": {
        "n_demand_g_per_m2_per_day": 0.80,
        "p_demand_g_per_m2_per_day": 0.20,
        "k_demand_g_per_m2_per_day": 1.80,
        "preferred_temp_min_c": 22.0,
        "preferred_temp_max_c": 30.0,
        "aquaponics_suitability": "low",
        "notes": "Soil-based production; incompatible with aquaponics nutrient delivery.",
    },
    "Watermelon": {
        "n_demand_g_per_m2_per_day": 0.75,
        "p_demand_g_per_m2_per_day": 0.18,
        "k_demand_g_per_m2_per_day": 1.60,
        "preferred_temp_min_c": 22.0,
        "preferred_temp_max_c": 30.0,
        "aquaponics_suitability": "low",
        "notes": "Soil-based production; incompatible with aquaponics nutrient delivery.",
    },
    "Spinach (Baby Cuts)": {
        "n_demand_g_per_m2_per_day": 0.30,
        "p_demand_g_per_m2_per_day": 0.08,
        "k_demand_g_per_m2_per_day": 0.35,
        "preferred_temp_min_c": 10.0,
        "preferred_temp_max_c": 20.0,
        "aquaponics_suitability": "low",
        "notes": "Soil-based production; incompatible with aquaponics nutrient delivery.",
    },
    "Rocket (Baby Cuts)": {
        "n_demand_g_per_m2_per_day": 0.35,
        "p_demand_g_per_m2_per_day": 0.08,
        "k_demand_g_per_m2_per_day": 0.40,
        "preferred_temp_min_c": 10.0,
        "preferred_temp_max_c": 20.0,
        "aquaponics_suitability": "low",
        "notes": "Soil-based production; incompatible with aquaponics nutrient delivery.",
    },
    "French Bean": {
        "n_demand_g_per_m2_per_day": 0.40,
        "p_demand_g_per_m2_per_day": 0.12,
        "k_demand_g_per_m2_per_day": 0.60,
        "preferred_temp_min_c": 16.0,
        "preferred_temp_max_c": 24.0,
        "aquaponics_suitability": "low",
        "notes": "Soil-based production; incompatible with aquaponics nutrient delivery.",
    },
}


# ==============================================================================
# DICTIONARY 3 - COUPLING_PARAMS
# PURPOSE: System-level constants for engineering limits, cost equations,
# and efficiency factors in coupled vs decoupled aquaponics configurations.
# UNITS:
#   biofilter_n_utilisation_efficiency     : fraction (0-1)
#   coupled_system_n_uptake_efficiency     : fraction (0-1)
#   decoupled_treatment_cost_per_m3        : USD per m³ of treated effluent
#   decoupled_nutrient_offset_fraction     : fraction (0-1), nested low/base/high
#   coupled_ph_target                      : pH units
#   decoupled_fish_ph_target               : pH units
#   decoupled_plant_ph_target              : pH units
#   min/optimal_fish_to_plant_ratio        : kg fish biomass per m² of plant area
#   water_consumption_l_per_kg_fish        : net litres consumed per kg produced
#   solid_waste_fertiliser_value_usd_per_kg: USD per kg of RAS sludge
#   heating_energy_kwh_per_m3_per_degree_c : kWh/m³/°C (physics constant)
#   aeration_kwh_per_kg_o2_delivered       : kWh per kg O2, nested by method
# SOURCES: Goddek et al. (Decoupled aquaponics economics), Rakocy et al. USVI,
#   Timmons & Ebeling, Lennard & Leonard (2006), Verdegem et al.,
#   Boyd & Tucker, Suhl et al., Maucieri et al.
# ==============================================================================

COUPLING_PARAMS = {
    "biofilter_n_utilisation_efficiency": 0.90,         # Midpoint of 0.85-0.95 range (Timmons & Ebeling)
    "coupled_system_n_uptake_efficiency": 0.75,         # Midpoint of 0.70-0.85 range (Lennard & Leonard)
    "decoupled_treatment_cost_per_m3": 0.85,            # Goddek et al. — UV, solids removal, pH adjustment (USD/m³)
    "decoupled_nutrient_offset_fraction": {
        "low": 0.30,                                    # Poorly optimised fish-to-plant ratio
        "base": 0.60,                                   # Well-designed commercial system (Suhl et al.)
        "high": 0.85,                                   # Highly integrated maximum recovery (Maucieri et al.)
    },
    "coupled_ph_target": 7.0,                           # Rakocy USVI consensus — compromise fish/plant/biofilter
    "decoupled_fish_ph_target": 7.5,                    # Optimal for nitrification and fish welfare
    "decoupled_plant_ph_target": 6.0,                   # Optimal hydroponic pH for nutrient solubility
    "min_fish_to_plant_ratio_kg_per_m2": 10.0,          # Lennard — minimum viable economic nutrient offset
    "optimal_fish_to_plant_ratio_kg_per_m2": 17.5,      # Rakocy USVI optimal for lettuce (published range 15-20)
    "water_consumption_l_per_kg_fish_produced": 100.0,  # Verdegem et al. — net RAS consumption, well within <200L benchmark
    "solid_waste_fertiliser_value_usd_per_kg": 0.05,    # Goddek et al. circular economy offset estimate
    "heating_energy_kwh_per_m3_per_degree_c": 1.16,    # Physics constant: specific heat capacity of water
    "aeration_kwh_per_kg_o2_delivered": {
        "standard_aeration": 1.8,                       # Boyd & Tucker midpoint for surface/diffused aerators
        "pure_oxygen_injection": 0.5,                   # High-efficiency oxygen cones in intensive RAS
    },
}

# ─────────────────────────────────────────────────────────────────────────────
# GREENHOUSE_LABOUR_TASKS
# Format: [base_min, none_factor, low_factor, med_factor, high_factor]
# Units:
#   Per-harvest tasks : minutes per 100 m² per cycle
#   Weekly tasks      : minutes per week per 100 m²
# Calibration target : 0.8–1.2 labour hours per m² per year (commercial Venlo
#                      tomato benchmark, WUR / KWIN 2024)
# Key differences from VF LABOUR_TASKS:
#   - washing / drying set to 0 (not applicable to fruiting/greenhouse crops)
#   - harvest base raised (hand-picked tomatoes/cucumbers vs leafy greens)
#   - admin reduced to 15 min/100m²/wk (fixed overhead spread across footprint)
#   - preventive_maint reduced to 20 min/100m²/wk (simpler mechanics than VF racks)
# ─────────────────────────────────────────────────────────────────────────────

GREENHOUSE_LABOUR_TASKS = {
    # ── Per-harvest tasks (min / 100 m² / cycle) ─────────────────────────────
    "seeding":           [0.8,  1, 0.90, 0.60, 0.30],  # seedling trays, less frequent than VF
    "germination":       [0.3,  1, 0.95, 0.75, 0.50],  # simpler monitoring
    "transplanting":     [1.2,  1, 0.90, 0.70, 0.40],  # single-level, no racking
    "internal_movement": [0.3,  1, 0.90, 0.60, 0.30],  # minimal — no multi-level logistics
    "harvest":           [2.5,  1, 0.95, 0.85, 0.70],  # hand-picked tomatoes/cucumbers
    "post_harvest":      [0.5,  1, 0.95, 0.80, 0.55],  # grading and sorting
    "washing":           [0.0,  1, 1.00, 1.00, 1.00],  # not applicable to greenhouse crops
    "drying":            [0.0,  1, 1.00, 1.00, 1.00],  # not applicable
    "packaging":         [0.6,  1, 0.95, 0.75, 0.45],
    "waste_handling":    [0.4,  1, 1.00, 0.90, 0.80],  # plant waste, stem removal
    # ── Weekly monitoring tasks (min / week / 100 m²) ────────────────────────
    "nutrient_mixing":   [15,   1, 0.85, 0.60, 0.40],  # automated fertigation — spot checks only
    "water_checks":      [10,   1, 0.85, 0.60, 0.40],  # drip irrigation, less intensive than VF
    "climate_mon":       [20,   1, 0.80, 0.55, 0.35],  # greenhouse climate control is critical
    "sensor_cal":        [10,   1, 0.95, 0.90, 0.85],
    "cleaning":          [8,    1, 1.00, 0.90, 0.80],
    "quality_ctrl":      [6,    1, 1.00, 0.90, 0.85],  # tomato grading — slightly more than VF leafy
    "ipm_scouting":      [30,   1, 1.00, 0.90, 0.85],  # critical in greenhouse environment
    "preventive_maint":  [20,   1, 1.00, 1.05, 1.10],  # simpler mechanics than VF rack/LED systems
    "admin":             [15,   1, 0.95, 0.90, 0.85],  # fixed overhead spread per 100 m²
}

# GREENHOUSE_AUTO_COL — identical to VF AUTO_COL, kept separate for modularity
GREENHOUSE_AUTO_COL = {"None": 1, "Low": 2, "Medium": 3, "High": 4}
