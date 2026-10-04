import math
import osmnx as ox
from shapely.geometry import Point, Polygon
from shapely.ops import unary_union
import numpy as np

center_lat = 22.6064
center_lon = 88.3648
dist_m = 2500

print(f"Testing water & land detection for ({center_lat}, {center_lon})...")
ox.settings.requests_timeout = 6

water_poly = None
try:
    water_gdf = ox.features_from_point(
        (center_lat, center_lon),
        tags={"natural": "water", "waterway": ["riverbank", "river", "canal"]},
        dist=dist_m
    )
    if not water_gdf.empty:
        water_polys = water_gdf[water_gdf.geometry.geom_type.isin(["Polygon", "MultiPolygon"])].geometry
        water_poly = unary_union(water_polys)
        print(f"Found water polygon with area coverage! Water geometry type: {water_poly.geom_type}")
except Exception as e:
    print(f"Water fetch note: {e}")

# Test sample points:
# Point A: (22.6064, 88.3648) - In the river
# Point B: (22.6064, 88.3750) - Mainland East (Kolkata residential/commercial)
# Point C: (22.6064, 88.3550) - Mainland West (Howrah)

pts = [
    ("Point A (River Center)", 22.6064, 88.3648),
    ("Point B (East Mainland)", 22.6064, 88.3750),
    ("Point C (West Mainland)", 22.6064, 88.3550)
]

for name, lat, lon in pts:
    p = Point(lon, lat)
    is_water = water_poly.contains(p) if water_poly is not None else False
    print(f"{name} [{lat}, {lon}]: Is Water? -> {is_water}")
