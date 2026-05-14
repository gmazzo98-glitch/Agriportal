"""
core/sun.py
Solar position calculator — no API needed, fully deterministic.
Based on NOAA Solar Calculator algorithm (Spencer 1971, Iqbal 1983).
"""

from __future__ import annotations
import math
from datetime import datetime, date, timedelta


def get_sun_position(lat: float, lon: float, dt: datetime) -> dict:
    """
    Compute sun azimuth and elevation for a location and datetime.
    Returns azimuth (degrees from North clockwise), elevation (degrees above horizon).
    """
    lat_r = math.radians(lat)
    doy   = dt.timetuple().tm_yday

    B = math.radians((360 / 365) * (doy - 81))
    declination = math.radians(23.45 * math.sin(B))

    eot        = 9.87 * math.sin(2 * B) - 7.53 * math.cos(B) - 1.5 * math.sin(B)
    local_hour = dt.hour + dt.minute / 60 + dt.second / 3600
    solar_time = local_hour + eot / 60 + lon / 15
    hour_angle = math.radians(15 * (solar_time - 12))

    sin_elev  = (
        math.sin(lat_r) * math.sin(declination)
        + math.cos(lat_r) * math.cos(declination) * math.cos(hour_angle)
    )
    elevation  = math.degrees(math.asin(max(-1.0, min(1.0, sin_elev))))
    cos_elev   = math.cos(math.radians(elevation))

    if cos_elev > 1e-6:
        cos_az = max(-1.0, min(1.0, (
            (math.sin(declination) - math.sin(lat_r) * sin_elev) / (math.cos(lat_r) * cos_elev)
        )))
        azimuth_raw = math.degrees(math.acos(cos_az))
        azimuth = azimuth_raw if solar_time < 12 else 360 - azimuth_raw
    else:
        azimuth = 180.0

    return {
        "azimuth":    round(azimuth, 2),
        "elevation":  round(elevation, 2),
        "is_daytime": elevation > 0,
        "solar_time": round(solar_time, 3),
    }


def get_daily_sun_path(lat: float, lon: float, target_date: date, interval_min: int = 30) -> list:
    """Compute sun positions throughout a day at regular intervals."""
    positions = []
    current   = datetime(target_date.year, target_date.month, target_date.day, 0, 0)
    delta     = timedelta(minutes=interval_min)
    end       = datetime(target_date.year, target_date.month, target_date.day, 23, 59)

    while current <= end:
        pos        = get_sun_position(lat, lon, current)
        pos["time"] = current.strftime("%H:%M")
        pos["hour"] = current.hour + current.minute / 60
        positions.append(pos)
        current += delta

    return positions


def get_sunrise_sunset(lat: float, lon: float, target_date: date) -> dict:
    """Compute sunrise and sunset times. Returns HH:MM strings and day length."""
    path    = get_daily_sun_path(lat, lon, target_date, interval_min=5)
    sunrise = None
    sunset  = None
    prev    = path[0]

    for pos in path[1:]:
        if not prev["is_daytime"] and pos["is_daytime"] and sunrise is None:
            sunrise = pos["time"]
        if prev["is_daytime"] and not pos["is_daytime"] and sunset is None:
            sunset = pos["time"]
        prev = pos

    day_length = 0.0
    if sunrise and sunset:
        sr_h = int(sunrise.split(":")[0]) + int(sunrise.split(":")[1]) / 60
        ss_h = int(sunset.split(":")[0])  + int(sunset.split(":")[1])  / 60
        day_length = max(0.0, ss_h - sr_h)

    return {
        "sunrise":      sunrise or "N/A",
        "sunset":       sunset  or "N/A",
        "day_length_h": round(day_length, 2),
    }


def get_monthly_sun_summary(lat: float, lon: float, year: int = 2025) -> list:
    """
    Monthly solar summary: max noon elevation, day length, theoretical clear-sky DLI.
    Uses the 15th of each month as representative day.
    DLI estimate: 2.0 mol/m2/hr at 90 deg elevation, scaled by sin(elevation).
    Source: calibrated against published European DLI atlases.
    """
    months = []
    for month in range(1, 13):
        rep_date = date(year, month, 15)
        midday   = datetime(year, month, 15, 12, 0)
        noon_pos = get_sun_position(lat, lon, midday)
        ss_info  = get_sunrise_sunset(lat, lon, rep_date)

        elev_r  = math.radians(max(0, noon_pos["elevation"]))
        dli_est = 2.0 * math.sin(elev_r) * ss_info["day_length_h"]

        months.append({
            "month":         month,
            "month_name":    rep_date.strftime("%b"),
            "max_elevation": noon_pos["elevation"],
            "day_length_h":  ss_info["day_length_h"],
            "sunrise":       ss_info["sunrise"],
            "sunset":        ss_info["sunset"],
            "dli_clear_sky": round(dli_est, 1),
        })

    return months


def compute_shadow_footprint(
    obj_x: float, obj_y: float,
    obj_w: float, obj_h: float,
    obj_height: float,
    sun_azimuth: float,
    sun_elevation: float,
) -> dict | None:
    """
    Compute 2D ground shadow of a rectangular object.
    Returns shadow tip polygon and length, or None if sun below horizon.
    """
    if sun_elevation <= 2:
        return None

    shadow_len  = obj_height / math.tan(math.radians(sun_elevation))
    shadow_az_r = math.radians(sun_azimuth + 180)
    dx          = shadow_len * math.sin(shadow_az_r)
    dy          = shadow_len * math.cos(shadow_az_r)

    return {
        "polygon": [
            [round(obj_x + dx, 3),         round(obj_y + dy, 3)],
            [round(obj_x + obj_w + dx, 3), round(obj_y + dy, 3)],
            [round(obj_x + obj_w + dx, 3), round(obj_y + obj_h + dy, 3)],
            [round(obj_x + dx, 3),         round(obj_y + obj_h + dy, 3)],
        ],
        "length": round(shadow_len, 2),
        "dx":     round(dx, 3),
        "dy":     round(dy, 3),
    }
