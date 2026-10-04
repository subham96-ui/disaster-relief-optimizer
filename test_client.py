import urllib.request
import json

payload = {
    "center_lat": 34.0522,
    "center_lon": -118.2437,
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
    print("Data source:", data.get("data_source"))
    print("Inner zone est pop:", data.get("inner_zone_stats", {}).get("estimated_population"))
    print("Outer ring est pop:", data.get("outer_ring_stats", {}).get("estimated_population"))
    print("Total affected pop:", data.get("total_affected_population"))
    print(f"Pinpointed {len(data.get('impact_targets', []))} Potential Impact Targets in Outer Ring:")
    for t in data.get("impact_targets", []):
        print(f"  * {t['name']}: ~{t['estimated_population']} people | Priority: {t['priority']} | Dist: {t.get('distance_km')} km ({t.get('bearing_deg')}°) | Coords: [{t['lat']}, {t['lon']}]")
    
    adj = data.get("adjusted_hazard_polygon", {})
    coords = adj.get("coordinates", [])
    print(f"Population-Adjusted Hazard Polygon: {len(coords)} vertices")
    for i, c in enumerate(coords):
        print(f"  Vertex {i+1}: [{c[0]}, {c[1]}]")
