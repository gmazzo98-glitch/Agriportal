"""
core/weather.py
Open-Meteo 7-day weather forecast fetcher.
No API key required. Free public API.

Usage:
    from core.weather import fetch_forecast, get_crop_alerts

    fc = fetch_forecast(lat, lon)
    alerts = get_crop_alerts(fc, crop_name, modality, crop_data)
"""

from __future__ import annotations
import requests
from datetime import datetime, date

FORECAST_URL = "https://api.open-meteo.com/v1/forecast"


def fetch_forecast(lat: float, lon: float) -> dict | None:
    """
    Fetch 7-day daily weather forecast for a location.
    Returns a dict with daily arrays, or None on failure.

    Returned keys:
        dates           list[str]   — forecast dates YYYY-MM-DD
        temp_max        list[float] — daily max temp °C
        temp_min        list[float] — daily min temp °C
        temp_mean       list[float] — daily mean temp °C
        precipitation   list[float] — daily precipitation mm
        solar_radiation list[float] — daily shortwave radiation sum MJ/m²
        cloud_cover     list[float] — daily mean cloud cover %
        wind_speed_max  list[float] — daily max wind speed km/h
        humidity_mean   list[float] — daily mean relative humidity %
    """
    if not lat or not lon:
        return None
    try:
        params = {
            "latitude":             lat,
            "longitude":            lon,
            "daily": ",".join([
                "temperature_2m_max",
                "temperature_2m_min",
                "temperature_2m_mean",
                "precipitation_sum",
                "shortwave_radiation_sum",
                "cloud_cover_mean",
                "wind_speed_10m_max",
                "relative_humidity_2m_mean",
            ]),
            "timezone":             "auto",
            "forecast_days":        7,
        }
        resp = requests.get(FORECAST_URL, params=params, timeout=10)
        resp.raise_for_status()
        d = resp.json().get("daily", {})
        return {
            "dates":           d.get("time", []),
            "temp_max":        d.get("temperature_2m_max", []),
            "temp_min":        d.get("temperature_2m_min", []),
            "temp_mean":       d.get("temperature_2m_mean", []),
            "precipitation":   d.get("precipitation_sum", []),
            "solar_radiation": d.get("shortwave_radiation_sum", []),
            "cloud_cover":     d.get("cloud_cover_mean", []),
            "wind_speed_max":  d.get("wind_speed_10m_max", []),
            "humidity_mean":   d.get("relative_humidity_2m_mean", []),
        }
    except Exception:
        return None


def fetch_current_conditions(lat: float, lon: float) -> dict | None:
    """
    Fetch current (hourly) conditions: temperature, humidity, cloud cover.
    Returns latest available hour, or None on failure.
    """
    if not lat or not lon:
        return None
    try:
        params = {
            "latitude":   lat,
            "longitude":  lon,
            "hourly": "temperature_2m,relative_humidity_2m,cloud_cover",
            "timezone":   "auto",
            "forecast_days": 1,
        }
        resp = requests.get(FORECAST_URL, params=params, timeout=10)
        resp.raise_for_status()
        h = resp.json().get("hourly", {})
        times = h.get("time", [])
        temps = h.get("temperature_2m", [])
        humid = h.get("relative_humidity_2m", [])
        cloud = h.get("cloud_cover", [])
        if not times:
            return None
        # Pick current hour (last non-future entry)
        now_str = datetime.now().strftime("%Y-%m-%dT%H:00")
        idx = 0
        for i, t in enumerate(times):
            if t <= now_str:
                idx = i
        return {
            "time":        times[idx],
            "temperature": temps[idx] if idx < len(temps) else None,
            "humidity":    humid[idx] if idx < len(humid) else None,
            "cloud_cover": cloud[idx] if idx < len(cloud) else None,
        }
    except Exception:
        return None


# ── Crop temperature thresholds ───────────────────────────────────────────────
# (outdoor temp °C — relevant for polytunnel and greenhouse)
# min_temp: below this, crop is at risk (frost / cold stress)
# max_temp: above this, crop is heat-stressed
# opt_min, opt_max: optimal range
CROP_TEMP_THRESHOLDS: dict[str, dict] = {
    # VF crops
    "Lettuce (Butterhead)":  {"min": 2,  "max": 28, "opt_min": 15, "opt_max": 22},
    "Lettuce (Romaine)":     {"min": 2,  "max": 28, "opt_min": 15, "opt_max": 22},
    "Lettuce (Loose Leaf)":  {"min": 2,  "max": 28, "opt_min": 15, "opt_max": 22},
    "Baby Spinach":          {"min": -5, "max": 24, "opt_min": 10, "opt_max": 18},
    "Basil":                 {"min": 10, "max": 35, "opt_min": 18, "opt_max": 28},
    "Mint":                  {"min": 5,  "max": 30, "opt_min": 16, "opt_max": 24},
    "Rocket":                {"min": 0,  "max": 26, "opt_min": 10, "opt_max": 20},
    "Kale":                  {"min": -8, "max": 26, "opt_min": 10, "opt_max": 20},
    "Strawberry":            {"min": 2,  "max": 30, "opt_min": 15, "opt_max": 22},
    "Tomato (Beefsteak)":    {"min": 10, "max": 35, "opt_min": 18, "opt_max": 27},
    "Tomato (Cherry)":       {"min": 10, "max": 35, "opt_min": 18, "opt_max": 27},
    "Tomato (Beef)":         {"min": 10, "max": 35, "opt_min": 18, "opt_max": 27},
    "Cucumber":              {"min": 12, "max": 36, "opt_min": 20, "opt_max": 28},
    "Pepper (Sweet)":        {"min": 12, "max": 36, "opt_min": 20, "opt_max": 28},
    "Eggplant":              {"min": 15, "max": 38, "opt_min": 22, "opt_max": 30},
}

_DEFAULT_THRESHOLDS = {"min": 5, "max": 32, "opt_min": 15, "opt_max": 25}


def get_crop_thresholds(crop_name: str) -> dict:
    """Return temperature thresholds for a crop, using defaults if not found."""
    for key, val in CROP_TEMP_THRESHOLDS.items():
        if key.lower() in crop_name.lower() or crop_name.lower() in key.lower():
            return val
    return _DEFAULT_THRESHOLDS


def get_crop_alerts(
    forecast: dict,
    crop_name: str,
    modality: str,
) -> list[dict]:
    """
    Generate weather alerts for a crop given a 7-day forecast.
    Returns list of alert dicts: {level, date, message}
    level: "critical" | "warning" | "info"

    Only meaningful for polytunnel and greenhouse — VF is fully controlled
    so only HVAC cost projections apply there, not crop safety alerts.
    """
    if not forecast:
        return []

    alerts = []
    thresholds = get_crop_thresholds(crop_name)
    is_outdoor_relevant = modality in ("polytunnel", "greenhouse")
    dates    = forecast.get("dates", [])
    temp_min = forecast.get("temp_min", [])
    temp_max = forecast.get("temp_max", [])
    precip   = forecast.get("precipitation", [])
    wind     = forecast.get("wind_speed_max", [])

    for i in range(min(len(dates), 7)):
        d      = dates[i]
        t_min  = temp_min[i] if i < len(temp_min) else None
        t_max  = temp_max[i] if i < len(temp_max) else None
        p      = precip[i]   if i < len(precip)   else None
        w      = wind[i]     if i < len(wind)      else None

        if is_outdoor_relevant:
            # Cold stress / frost
            if t_min is not None:
                if t_min < thresholds["min"]:
                    level = "critical" if t_min < thresholds["min"] - 5 else "warning"
                    alerts.append({
                        "level":   level,
                        "date":    d,
                        "message": (
                            f"Night temperature {t_min:.1f}°C on {d} — below "
                            f"{crop_name} minimum tolerance ({thresholds['min']}°C). "
                            f"{'Frost risk — consider crop protection.' if t_min < 0 else 'Cold stress likely.'}"
                        ),
                    })
                elif t_min < thresholds["opt_min"]:
                    alerts.append({
                        "level":   "info",
                        "date":    d,
                        "message": (
                            f"Night temperature {t_min:.1f}°C on {d} below optimal "
                            f"({thresholds['opt_min']}°C) — may slow growth."
                        ),
                    })

            # Heat stress
            if t_max is not None and t_max > thresholds["max"]:
                alerts.append({
                    "level":   "warning",
                    "date":    d,
                    "message": (
                        f"Daytime temperature {t_max:.1f}°C on {d} exceeds "
                        f"{crop_name} maximum tolerance ({thresholds['max']}°C). "
                        f"Ventilation and shading required."
                    ),
                })

            # High wind (polytunnel structure risk)
            if w is not None and w > 60 and modality == "polytunnel":
                alerts.append({
                    "level":   "warning",
                    "date":    d,
                    "message": (
                        f"Wind speed {w:.0f} km/h forecast on {d} — "
                        f"check polytunnel fixings and close all vents."
                    ),
                })

            # Heavy rain
            if p is not None and p > 30:
                alerts.append({
                    "level":   "info",
                    "date":    d,
                    "message": (
                        f"Heavy rainfall ({p:.0f} mm) forecast on {d} — "
                        f"check drainage and guttering."
                    ),
                })

    # HVAC cost signal for VF (always relevant)
    if modality == "vertical_farm":
        cold_days = [
            dates[i] for i in range(min(len(dates), 7))
            if i < len(temp_min) and temp_min[i] is not None and temp_min[i] < -5
        ]
        if cold_days:
            alerts.append({
                "level":   "info",
                "date":    cold_days[0],
                "message": (
                    f"Cold spell forecast ({len(cold_days)} days below -5°C) — "
                    f"expect elevated HVAC heating costs this week."
                ),
            })

    return alerts


def compute_weekly_hvac_cost(
    forecast: dict,
    target_temp_indoor: float,
    footprint_m2: float,
    kwh_price: float,
    hvac_efficiency: float = 0.85,
) -> dict:
    """
    Estimate weekly HVAC energy cost from forecast temperatures.
    Uses a simplified degree-day heating/cooling model.

    Returns:
        {
            "heating_kwh": float,
            "cooling_kwh": float,
            "total_kwh":   float,
            "total_cost":  float,
            "daily":       list[dict]  — per-day breakdown
        }
    """
    if not forecast:
        return {"heating_kwh": 0, "cooling_kwh": 0, "total_kwh": 0, "total_cost": 0, "daily": []}

    # W/m² per °C delta — simplified thermal load factor
    # Typical insulated CEA structure: ~8-12 W/m²/°C
    THERMAL_LOAD_W_M2_K = 10.0
    hours_per_day = 24

    total_heating_kwh = 0.0
    total_cooling_kwh = 0.0
    daily = []

    dates    = forecast.get("dates", [])
    temp_min = forecast.get("temp_min", [])
    temp_max = forecast.get("temp_max", [])
    temp_mean = forecast.get("temp_mean", [])

    for i in range(min(len(dates), 7)):
        t_mean = temp_mean[i] if i < len(temp_mean) else None
        if t_mean is None:
            continue
        delta      = target_temp_indoor - t_mean
        load_kw    = (THERMAL_LOAD_W_M2_K * footprint_m2 * abs(delta)) / 1000
        kwh_day    = load_kw * hours_per_day / hvac_efficiency
        if delta > 0:
            total_heating_kwh += kwh_day
            daily.append({"date": dates[i], "heating_kwh": round(kwh_day, 1),
                          "cooling_kwh": 0, "outdoor_mean": round(t_mean, 1)})
        else:
            total_cooling_kwh += kwh_day
            daily.append({"date": dates[i], "heating_kwh": 0,
                          "cooling_kwh": round(kwh_day, 1), "outdoor_mean": round(t_mean, 1)})

    total_kwh  = total_heating_kwh + total_cooling_kwh
    return {
        "heating_kwh": round(total_heating_kwh, 1),
        "cooling_kwh": round(total_cooling_kwh, 1),
        "total_kwh":   round(total_kwh, 1),
        "total_cost":  round(total_kwh * kwh_price, 2),
        "daily":       daily,
    }
