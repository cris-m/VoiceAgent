import httpx
from langchain_core.tools import tool

_HEADERS = {"User-Agent": "VoiceAgent/1.0", "Accept": "application/json"}
_TIMEOUT = 20

_WMO = {
    0: "Clear sky", 1: "Mainly clear", 2: "Partly cloudy", 3: "Overcast",
    45: "Fog", 48: "Icy fog",
    51: "Light drizzle", 53: "Moderate drizzle", 55: "Dense drizzle",
    61: "Slight rain", 63: "Moderate rain", 65: "Heavy rain",
    71: "Slight snowfall", 73: "Moderate snowfall", 75: "Heavy snowfall",
    80: "Slight showers", 81: "Moderate showers", 82: "Violent showers",
    95: "Thunderstorm", 96: "Thunderstorm with hail", 99: "Thunderstorm with heavy hail",
}


def _get(url: str, params: dict | None = None) -> dict:
    try:
        with httpx.Client(timeout=_TIMEOUT, follow_redirects=True) as client:
            r = client.get(url, headers=_HEADERS, params=params)
            r.raise_for_status()
            return {"ok": True, "data": r.json()}
    except Exception as e:
        return {"ok": False, "error": str(e)}


@tool
def get_weather(location: str, days: int = 3) -> dict:
    """Get current weather and forecast for any city worldwide.

    Uses Open-Meteo (free, no API key). Includes temperature, precipitation,
    humidity, wind, and UV index.

    Args:
        location: City or place name, e.g. "Tokyo", "Paris", "New York", "Cape Town".
        days: Forecast days (1–7, default: 3)

    Returns:
        dict with current conditions and daily forecast.
    """
    geo = _get(
        "https://geocoding-api.open-meteo.com/v1/search",
        params={"name": location, "count": 1, "language": "en", "format": "json"},
    )
    if not geo["ok"] or not geo["data"].get("results"):
        return {"error": f"Location '{location}' not found."}

    place = geo["data"]["results"][0]
    lat, lon = place["latitude"], place["longitude"]
    city_name = place.get("name", location)
    country = place.get("country", "")
    admin1 = place.get("admin1", "")

    weather = _get(
        "https://api.open-meteo.com/v1/forecast",
        params={
            "latitude": lat,
            "longitude": lon,
            "current": "temperature_2m,relative_humidity_2m,precipitation,weather_code,wind_speed_10m,uv_index",
            "daily": "temperature_2m_max,temperature_2m_min,precipitation_sum,weather_code,uv_index_max",
            "forecast_days": min(max(days, 1), 7),
            "timezone": "auto",
        },
    )
    if not weather["ok"]:
        return {"error": weather["error"]}

    d = weather["data"]
    current = d.get("current", {})
    daily = d.get("daily", {})

    forecast = []
    for i, date in enumerate(daily.get("time", [])):
        forecast.append({
            "date": date,
            "condition": _WMO.get(daily["weather_code"][i], "Unknown"),
            "temp_max_c": daily["temperature_2m_max"][i],
            "temp_min_c": daily["temperature_2m_min"][i],
            "precipitation_mm": daily["precipitation_sum"][i],
            "uv_index_max": daily.get("uv_index_max", [None] * (i + 1))[i],
        })

    return {
        "location": f"{city_name}, {admin1}, {country}".strip(", "),
        "coordinates": {"lat": lat, "lon": lon},
        "current": {
            "condition": _WMO.get(current.get("weather_code"), "Unknown"),
            "temperature_c": current.get("temperature_2m"),
            "humidity_pct": current.get("relative_humidity_2m"),
            "precipitation_mm": current.get("precipitation"),
            "wind_speed_kmh": current.get("wind_speed_10m"),
            "uv_index": current.get("uv_index"),
        },
        "forecast_days": forecast,
        "source": "Open-Meteo (open-meteo.com)",
    }
