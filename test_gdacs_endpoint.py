import urllib.request
import json

payload = {
    "center_lat": 34.0522,
    "center_lon": -118.2437,
    "hazard_radius_km": 2.5,
    "search_radius_km": 1500.0
}

req = urllib.request.Request(
    "http://127.0.0.1:5000/api/gdacs",
    data=json.dumps(payload).encode("utf-8"),
    headers={"Content-Type": "application/json"}
)

with urllib.request.urlopen(req) as resp:
    data = json.loads(resp.read().decode("utf-8"))
    print("Status:", data.get("status"))
    print("Source:", data.get("source"))
    print("Total global events queried:", data.get("total_global_events_queried"))
    print("Direct hazard inside count:", data.get("inside_polygon_count"))
    print("Nearby regional buffer count:", data.get("nearby_buffer_count"))
    print(f"Nearest global events ({len(data.get('nearest_global_events', []))}):")
    for ev in data.get("nearest_global_events", []):
        print(f"  - {ev.get('icon')} {ev.get('name')} | Level: {ev.get('alert_level')} | Distance: {ev.get('distance_km')} km | Link: {ev.get('link')}")
