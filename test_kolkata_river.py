from population_engine import analyze_population

res = analyze_population(22.6064, 88.3648, 2.5, hazard_sides=6)
print("Status:", res["status"])
print("Data Source:", res["data_source"])
print("Water Detected in Area:", res["water_detected"])
print("Inner Zone Estimated Pop:", res["inner_zone_stats"]["estimated_population"])
print("Outer Ring Estimated Pop:", res["outer_ring_stats"]["estimated_population"])
print(f"\nDetected {len(res['impact_targets'])} Impact Targets (Mainland Only):")
for t in res["impact_targets"]:
    print(f"  * {t['name']}: ~{t['estimated_population']} pop | Priority: {t['priority']} | Dist: {t['distance_km']} km ({t['bearing_deg']}°) | Coords: [{t['lat']}, {t['lon']}]")

print(f"\nPopulation-Adjusted Hazard Polygon ({len(res['adjusted_hazard_polygon']['coordinates'])} vertices):")
for i, c in enumerate(res["adjusted_hazard_polygon"]["coordinates"]):
    print(f"  Vertex {i+1}: [{c[0]}, {c[1]}]")
