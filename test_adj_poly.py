import math
import numpy as np

def generate_adjusted_polygon(center_lat, center_lon, sides, base_radius_km, impact_targets):
    """
    Adjusts the hazard polygon vertices based on population impact targets,
    stretching towards high-density corridors instead of a regular polygon.
    """
    sides = max(3, int(sides))
    adjusted_coords = []
    
    # Calculate angular influence of each impact target
    target_angles = []
    for t in impact_targets:
        dlat = t["lat"] - center_lat
        dlon = (t["lon"] - center_lon) * math.cos(math.radians(center_lat))
        angle_rad = math.atan2(dlat, dlon) % (2 * math.pi)
        pop_weight = min(2.0, max(0.5, t.get("estimated_population", 2000) / 3000.0))
        target_angles.append((angle_rad, pop_weight))
    
    for i in range(sides):
        theta = (2 * math.pi / sides) * i
        # Base expansion factor
        factor = 1.0
        # Check proximity to impact target directions
        for t_angle, t_weight in target_angles:
            angle_diff = abs(theta - t_angle)
            if angle_diff > math.pi:
                angle_diff = 2 * math.pi - angle_diff
            
            # Influence window ~ 45 degrees (pi/4)
            if angle_diff < (math.pi / 3):
                influence = math.cos(angle_diff * 1.5) ** 2
                factor += 0.35 * t_weight * influence
        
        # Add slight natural terrain irregularity
        factor += 0.08 * math.sin(3 * theta)
        # Clamp factor so it stays between 0.75x and 1.48x of base_radius_km
        adj_radius_km = base_radius_km * min(1.48, max(0.72, factor))
        
        # Geodesic point
        R_earth = 6371.0
        d = adj_radius_km / R_earth
        lat0 = math.radians(center_lat)
        lon0 = math.radians(center_lon)
        # bearing clockwise from North
        brng = (math.pi / 2 - theta) % (2 * math.pi)
        
        lat = math.asin(math.sin(lat0) * math.cos(d) + math.cos(lat0) * math.sin(d) * math.cos(brng))
        lon = lon0 + math.atan2(math.sin(brng) * math.sin(d) * math.cos(lat0),
                                math.cos(d) - math.sin(lat0) * math.sin(lat))
        
        adjusted_coords.append([round(math.degrees(lat), 6), round(math.degrees(lon), 6)])
    
    return adjusted_coords

# Quick test
targets = [
    {"lat": 34.07, "lon": -118.23, "estimated_population": 8500},
    {"lat": 34.03, "lon": -118.26, "estimated_population": 6200}
]
pts = generate_adjusted_polygon(34.0522, -118.2437, 6, 2.5, targets)
print(f"Generated {len(pts)} adjusted vertices:")
for p in pts:
    print(" ", p)
