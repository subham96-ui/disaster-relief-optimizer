import math
import urllib.request
import urllib.parse
import json
from shapely.geometry import Point, Polygon
from geopy.distance import geodesic

def is_point_water(lat, lon):
    """
    Checks if a candidate point is on water (river, ocean, lake)
    via fast Nominatim reverse lookup.
    """
    url = f"https://nominatim.openstreetmap.org/reverse?lat={lat}&lon={lon}&format=json&zoom=15"
    req = urllib.request.Request(url, headers={"User-Agent": "DisasterReliefOptimizer/1.0"})
    try:
        with urllib.request.urlopen(req, timeout=3) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            addr = data.get("address", {})
            cat = data.get("category", "").lower()
            ptype = data.get("type", "").lower()
            display_name = data.get("display_name", "").lower()
            
            # Check for water signatures
            water_terms = ["river", "riverbank", "water", "waterway", "lake", "ocean", "sea", "bay", "harbor", "canal", "reservoir", "basin", "estuary", "creek"]
            
            if cat in ("water", "waterway", "natural") and ptype in water_terms:
                return True, f"Categorized as {cat}/{ptype}"
                
            for term in ["hooghly river", "river", "lake", "ocean", "bay of bengal", "pacific ocean", "atlantic ocean"]:
                if term in display_name and not any(urban in display_name for urban in ["road", "street", "avenue", "lane", "bridge", "nagar", "sarani", "ghat"]):
                    return True, f"Display name contains waterbody: {term}"
                    
            return False, f"Land/Urban: {data.get('type')} ({display_name[:40]})"
    except Exception as e:
        return False, f"Check error ({e})"

# Test Point A (River) vs Point B (Mainland Kolkata)
res_a, desc_a = is_point_water(22.6064, 88.3648)
res_b, desc_b = is_point_water(22.6064, 88.3750)
res_c, desc_c = is_point_water(22.6064, 88.3550)

print(f"Point A (River 22.6064, 88.3648): Is Water? {res_a} -> {desc_a}")
print(f"Point B (Mainland 22.6064, 88.3750): Is Water? {res_b} -> {desc_b}")
print(f"Point C (Mainland 22.6064, 88.3550): Is Water? {res_c} -> {desc_c}")
