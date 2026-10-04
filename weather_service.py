"""
Weather Ingestion Service for Disaster Relief Optimizer.
Fetches real-time atmospheric data from OpenWeatherMap (if API key is supplied)
or automatically falls back to Open-Meteo Global API (zero key needed).
Includes in-memory TTL caching to reduce redundant network latency.
"""

import time
import logging
from typing import Dict, Any, Optional
import requests

logger = logging.getLogger("WeatherService")

# In-memory cache for weather results: {(round(lat, 2), round(lon, 2)): (timestamp, data)}
_WEATHER_CACHE: Dict[tuple, tuple] = {}
CACHE_TTL_SECONDS = 300  # 5 minutes

def fetch_live_weather(lat: float, lon: float, owm_key: Optional[str] = None) -> Dict[str, Any]:
    """
    Retrieves atmospheric weather metrics for given coordinates.
    Returns:
        dict: {
            "source": str,
            "temperature_c": float,
            "wind_speed_knots": float,
            "precipitation_mm_hr": float,
            "condition": str,
            "humidity": int,
            "icon": str
        }
    """
    cache_key = (round(lat, 2), round(lon, 2), bool(owm_key))
    now = time.time()

    if cache_key in _WEATHER_CACHE:
        cached_time, cached_val = _WEATHER_CACHE[cache_key]
        if now - cached_time < CACHE_TTL_SECONDS:
            logger.info("Serving weather from cache")
            return cached_val

    # Default fallback
    weather_data = {
        "source": "Default Baseline",
        "temperature_c": 20.0,
        "wind_speed_knots": 15.0,
        "precipitation_mm_hr": 0.0,
        "condition": "Clear / Baseline",
        "humidity": 50,
        "icon": "sunny"
    }

    # 1. Try OpenWeatherMap if key is provided
    if owm_key and owm_key.strip():
        try:
            url = f"https://api.openweathermap.org/data/2.5/weather?lat={lat}&lon={lon}&appid={owm_key.strip()}&units=metric"
            resp = requests.get(url, timeout=5)
            if resp.status_code == 200:
                data = resp.json()
                wind_mps = data.get("wind", {}).get("speed", 0.0)
                wind_knots = wind_mps * 1.94384
                
                precip = 0.0
                if "rain" in data and "1h" in data["rain"]:
                    precip += data["rain"]["1h"]
                if "snow" in data and "1h" in data["snow"]:
                    precip += data["snow"]["1h"]
                
                weather_data = {
                    "source": "OpenWeatherMap (Live)",
                    "temperature_c": round(data.get("main", {}).get("temp", 20.0), 1),
                    "wind_speed_knots": round(wind_knots, 1),
                    "precipitation_mm_hr": round(precip, 2),
                    "condition": data.get("weather", [{}])[0].get("description", "Normal").title(),
                    "humidity": data.get("main", {}).get("humidity", 50),
                    "icon": data.get("weather", [{}])[0].get("icon", "01d")
                }
                _WEATHER_CACHE[cache_key] = (now, weather_data)
                return weather_data
            else:
                logger.warning(f"OWM returned status {resp.status_code}: {resp.text}")
        except Exception as e:
            logger.error(f"Error querying OpenWeatherMap: {e}")

    # 2. Try Open-Meteo (Free global meteorological API, zero key needed)
    try:
        url = (
            f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}"
            "&current=temperature_2m,relative_humidity_2m,precipitation,wind_speed_10m,weather_code"
        )
        resp = requests.get(url, timeout=5)
        if resp.status_code == 200:
            data = resp.json().get("current", {})
            wind_kmh = data.get("wind_speed_10m", 0.0)
            wind_knots = wind_kmh * 0.539957
            precip = data.get("precipitation", 0.0)
            temp = data.get("temperature_2m", 20.0)
            humid = data.get("relative_humidity_2m", 50)
            code = data.get("weather_code", 0)
            
            cond = "Clear Sky"
            if code in [1, 2, 3]: cond = "Partly Cloudy"
            elif code in [45, 48]: cond = "Foggy"
            elif code in [51, 53, 55, 61, 63, 65]: cond = "Rain / Showers"
            elif code in [71, 73, 75]: cond = "Snowfall"
            elif code in [80, 81, 82]: cond = "Heavy Rain"
            elif code in [95, 96, 99]: cond = "Thunderstorm"

            weather_data = {
                "source": "Open-Meteo (Live Global)",
                "temperature_c": round(temp, 1),
                "wind_speed_knots": round(wind_knots, 1),
                "precipitation_mm_hr": round(precip, 2),
                "condition": cond,
                "humidity": round(humid, 0),
                "icon": "meteo"
            }
            _WEATHER_CACHE[cache_key] = (now, weather_data)
            return weather_data
    except Exception as e:
        logger.warning(f"Open-Meteo query failed: {e}")

    return weather_data
