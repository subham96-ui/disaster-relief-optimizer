"""
GDACS (Global Disaster Alert and Coordination System) Integration Service.
Provides live natural disaster and humanitarian emergency intelligence
from the United Nations (OCHA) & European Commission Joint Research Centre (JRC).

Supported disaster categories:
- EQ: Earthquakes
- TC: Tropical Cyclones (Hurricanes, Typhoons)
- FL: Floods
- VO: Volcanoes
- WF: Wildfires
- DR: Droughts
"""

import os
import math
import time
import logging
import urllib.request
import json
from typing import Dict, List, Tuple, Any, Optional

from shapely.geometry import Point, Polygon, shape
from geopy.distance import geodesic

logger = logging.getLogger("GDACSService")

# Live GDACS GeoJSON Endpoint
GDACS_GEOJSON_URL = "https://www.gdacs.org/xml/gdacs.geojson"
GDACS_SEARCH_API_URL = "https://www.gdacs.org/gdacsapi/api/events/geteventlist/SEARCH"

CACHE_FILE = os.path.join(os.path.dirname(__file__), "cache", "gdacs_live_cache.json")
CACHE_TTL_SECONDS = 300  # 5 minutes in-memory / file cache

# In-memory cache
_FEED_CACHE: Dict[str, Any] = {"timestamp": 0, "data": None}

EVENT_ICONS = {
    "EQ": "📉",  # Earthquake
    "TC": "🌪️",  # Tropical Cyclone
    "FL": "🌊",  # Flood
    "VO": "🌋",  # Volcano
    "WF": "🔥",  # Wildfire
    "DR": "☀️",  # Drought
}

EVENT_NAMES = {
    "EQ": "Earthquake",
    "TC": "Tropical Cyclone",
    "FL": "Flood",
    "VO": "Volcano",
    "WF": "Wildfire",
    "DR": "Drought",
}


def _extract_feature_lat_lon(feature: Dict[str, Any]) -> Optional[Tuple[float, float]]:
    """Safely extracts (lat, lon) from properties or GeoJSON geometry."""
    props = feature.get("properties", {})
    geom = feature.get("geometry", {})

    # 1. Direct properties
    p_lat = props.get("latitude")
    p_lon = props.get("longitude")
    if p_lat is not None and p_lon is not None:
        try:
            return float(p_lat), float(p_lon)
        except (ValueError, TypeError):
            pass

    # 2. Geometry check
    coords = geom.get("coordinates")
    g_type = geom.get("type")
    if g_type == "Point" and isinstance(coords, (list, tuple)) and len(coords) >= 2:
        try:
            return float(coords[1]), float(coords[0])
        except (ValueError, TypeError):
            pass
    elif g_type in ("Polygon", "MultiPolygon") and coords:
        try:
            c = shape(geom).centroid
            return float(c.y), float(c.x)
        except Exception:
            pass

    return None


def fetch_gdacs_live_feed(timeout_sec: int = 15) -> Optional[Dict[str, Any]]:
    """
    Fetches the live GDACS global disasters GeoJSON feed.
    Caches in memory and on disk with 5-minute TTL.
    """
    now = time.time()
    # 1. In-memory cache
    if _FEED_CACHE["data"] and (now - _FEED_CACHE["timestamp"]) < CACHE_TTL_SECONDS:
        return _FEED_CACHE["data"]

    # 2. Disk cache
    if os.path.exists(CACHE_FILE):
        try:
            mtime = os.path.getmtime(CACHE_FILE)
            if (now - mtime) < CACHE_TTL_SECONDS:
                with open(CACHE_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    _FEED_CACHE["data"] = data
                    _FEED_CACHE["timestamp"] = mtime
                    logger.info("Loaded GDACS live feed from disk cache.")
                    return data
        except Exception as e:
            logger.debug(f"Could not load GDACS disk cache: {e}")

    # 3. Live network query
    logger.info("Fetching fresh live GDACS GeoJSON feed from www.gdacs.org...")
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "*/*"
    }
    req = urllib.request.Request(GDACS_GEOJSON_URL, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=timeout_sec) as resp:
            raw = resp.read().decode("utf-8")
            data = json.loads(raw)
            _FEED_CACHE["data"] = data
            _FEED_CACHE["timestamp"] = now

            # Save to disk cache
            try:
                os.makedirs(os.path.dirname(CACHE_FILE), exist_ok=True)
                with open(CACHE_FILE, "w", encoding="utf-8") as f:
                    f.write(raw)
            except Exception as e:
                logger.debug(f"Failed to persist GDACS cache to disk: {e}")

            logger.info(f"Successfully fetched {len(data.get('features', []))} GDACS events.")
            return data
    except Exception as exc:
        logger.warning(f"Live GDACS GeoJSON fetch failed: {exc}")
        # Try returning stale disk cache if available
        if os.path.exists(CACHE_FILE):
            try:
                with open(CACHE_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    _FEED_CACHE["data"] = data
                    logger.info("Using stale disk cache for GDACS data.")
                    return data
            except Exception:
                pass
        return _FEED_CACHE.get("data")


def query_emergencies_in_hazard_polygon(
    hazard_coords: Optional[List[List[float]]],
    center_lat: float,
    center_lon: float,
    hazard_radius_km: float,
    search_radius_km: Optional[float] = None
) -> Dict[str, Any]:
    """
    Queries GDACS live events and filters for emergencies intersecting
    or located within proximity of the hazard polygon and outer buffer zone.
    """
    if search_radius_km is None:
        search_radius_km = max(50.0, hazard_radius_km * 2.5)

    # Construct Shapely Polygon for containment test
    poly = None
    if hazard_coords and len(hazard_coords) >= 3:
        try:
            poly_pts = [(p[1], p[0]) for p in hazard_coords]  # (lon, lat)
            poly = Polygon(poly_pts)
            if not poly.is_valid:
                poly = poly.buffer(0)
        except Exception as e:
            logger.warning(f"Error constructing hazard polygon for GDACS check: {e}")
            poly = None

    feed = fetch_gdacs_live_feed()
    features = feed.get("features", []) if feed else []

    inside_polygon_events = []
    nearby_events = []
    all_events_with_dist = []

    for f in features:
        lat_lon = _extract_feature_lat_lon(f)
        if not lat_lon:
            continue

        ev_lat, ev_lon = lat_lon
        props = f.get("properties", {})
        pt = Point(ev_lon, ev_lat)

        # Distance from epicenter
        try:
            dist_km = geodesic((center_lat, center_lon), (ev_lat, ev_lon)).km
        except Exception:
            dist_km = math.hypot(
                (center_lat - ev_lat) * 111.0,
                (center_lon - ev_lon) * 111.0 * math.cos(math.radians(center_lat))
            )

        is_inside = False
        if poly and poly.contains(pt):
            is_inside = True
        elif dist_km <= hazard_radius_km:
            is_inside = True

        ev_type = str(props.get("eventtype") or "EQ").upper()
        alert_level = str(props.get("alertlevel") or "Green").capitalize()
        alert_score = props.get("alertscore") or 0

        event_obj = {
            "id": f"{props.get('eventtype')}_{props.get('eventid')}",
            "name": props.get("name") or props.get("eventname") or f"{EVENT_NAMES.get(ev_type, ev_type)} Alert",
            "event_type": ev_type,
            "event_type_name": EVENT_NAMES.get(ev_type, ev_type),
            "icon": EVENT_ICONS.get(ev_type, "⚠️"),
            "alert_level": alert_level,
            "alert_score": alert_score,
            "severity": props.get("severity") or props.get("htmldescription") or "Disaster event registered",
            "from_date": props.get("fromdate") or "",
            "to_date": props.get("todate") or "",
            "country": props.get("country") or props.get("iso3") or "International",
            "lat": round(ev_lat, 5),
            "lon": round(ev_lon, 5),
            "distance_km": round(dist_km, 2),
            "is_inside_polygon": is_inside,
            "link": props.get("link") or f"https://www.gdacs.org/report.aspx?eventtype={ev_type}&eventid={props.get('eventid')}",
            "description": props.get("description") or "",
        }

        all_events_with_dist.append(event_obj)

        if is_inside:
            inside_polygon_events.append(event_obj)
        elif dist_km <= search_radius_km:
            nearby_events.append(event_obj)

    # Sort by alert level (Red > Orange > Green) and distance
    level_rank = {"Red": 3, "Orange": 2, "Green": 1}
    inside_polygon_events.sort(key=lambda x: (level_rank.get(x["alert_level"], 0), -x["distance_km"]), reverse=True)
    nearby_events.sort(key=lambda x: (level_rank.get(x["alert_level"], 0), -x["distance_km"]), reverse=True)

    # All global events sorted by distance (no limit)
    all_events_with_dist.sort(key=lambda x: x["distance_km"])

    return {
        "status": "success",
        "source": "Global Disaster Alert and Coordination System (GDACS)",
        "source_url": "https://www.gdacs.org",
        "hazard_center": [center_lat, center_lon],
        "hazard_radius_km": hazard_radius_km,
        "search_radius_km": search_radius_km,
        "total_global_events_queried": len(features),
        "inside_polygon_count": len(inside_polygon_events),
        "nearby_buffer_count": len(nearby_events),
        "inside_polygon_events": inside_polygon_events,
        "nearby_events": nearby_events,
        "nearest_global_events": all_events_with_dist,
    }
