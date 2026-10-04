import urllib.request
import json

# Send the adjusted coordinates
adj_coords = [
  [34.052193, -118.203539],
  [34.081015, -118.223612],
  [34.081015, -118.263788],
  [34.052193, -118.283861],
  [34.023382, -118.263774],
  [34.023382, -118.223626]
]

payload = {
    "hazard_coords": adj_coords,
    "hazard_radius_km": 2.5,
    "repair_factor": 0.5,
    "weather": {"wind_speed_knots": 20.0, "precipitation_mm_hr": 5.0}
}

req = urllib.request.Request(
    "http://127.0.0.1:5000/api/optimize",
    data=json.dumps(payload).encode("utf-8"),
    headers={"Content-Type": "application/json"}
)

with urllib.request.urlopen(req) as resp:
    data = json.loads(resp.read().decode("utf-8"))
    print("Solver status:", data.get("solver_status"))
    print("Objective value: $", data.get("objective_value"))
    print("Routes assigned:", len(data.get("routes", [])))
    print("Hazard GeoJSON present:", bool(data.get("hazard_geojson")))
