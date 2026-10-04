import urllib.request
import json

payload = {
    "center_lat": 22.6064,
    "center_lon": 88.3648,
    "hazard_radius_km": 2.5,
    "hazard_sides": 6,
    "top_k": 5
}

req = urllib.request.Request(
    "http://127.0.0.1:5000/api/population",
    data=json.dumps(payload).encode("utf-8"),
    headers={"Content-Type": "application/json"}
)

with urllib.request.urlopen(req) as resp:
    data = json.loads(resp.read().decode("utf-8"))
    print("Status:", data.get("status"))
    print("Source:", data.get("data_source"))
    print("Inner Pop:", data.get("inner_zone_stats", {}).get("estimated_population"))
    print("Outer Pop:", data.get("outer_ring_stats", {}).get("estimated_population"))
    print(f"Detected {len(data.get('impact_targets', []))} Mainland Impact Targets:")
    for t in data.get("impact_targets", []):
        print(f"  * {t['name']}: ~{t['estimated_population']} pop | {t['distance_km']} km ({t['bearing_deg']}°) | [{t['lat']}, {t['lon']}]")
    print(f"Adjusted Polygon Vertices ({len(data.get('adjusted_hazard_polygon', {}).get('coordinates', []))}):")
    for i, c in enumerate(data.get('adjusted_hazard_polygon', {}).get('coordinates', [])):
        print(f"  V{i+1}: [{c[0]}, {c[1]}]")
