import sys
import os

# Ensure UTF-8 stdout encoding on Windows
if sys.platform.startswith("win"):
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")

import numpy as np
import networkx as nx
import osmnx as ox
import pulp
from shapely.geometry import Polygon, LineString
from shapely.ops import transform
import pyproj
from geopy.distance import geodesic

print("=" * 80)
print(f"{'DISASTER RELIEF LOGISTICS & ROUTING OPTIMIZER':^80}")
print("=" * 80)

# ==============================================================================
# 1. GEOGRAPHY & BASELINE SUPPLY SETUP
# ==============================================================================
center_lat, center_lon = 34.0522, -118.2437
depots = {"Depot_North": (34.0650, -118.2350), "Depot_South": (34.0350, -118.2550)}
zones = {"Zone_East_Impact": (34.0500, -118.2200), "Zone_West_Impact": (34.0550, -118.2700)}

supplies = {"Depot_North": 15000, "Depot_South": 20000}  # kg
demands = {"Zone_East_Impact": 12000, "Zone_West_Impact": 8000}   # kg

print("📥 Ingesting street layout graph arrays from OpenStreetMap (4km radius)...")
G_raw = ox.graph_from_point((center_lat, center_lon), dist=4000, network_type="drive")
G = ox.project_graph(G_raw)
G_unprojected = ox.project_graph(G, to_crs="EPSG:4326")
crs = G.graph["crs"]
print(f"   ✓ Road network ingested: {len(G.nodes)} nodes, {len(G.edges)} edges (CRS: {crs})")

# Define Hazard Perimeter
# Coordinates are (lat, lon); convert to (lon, lat) for proper EPSG:4326 Shapely geometry
hazard_coords_latlon = [(34.0580, -118.2500), (34.0420, -118.2500), (34.0420, -118.2300), (34.0580, -118.2300)]
hazard_coords_lonlat = [(lon, lat) for lat, lon in hazard_coords_latlon]
hazard_poly_unprojected = Polygon(hazard_coords_lonlat)

# Robust projection of hazard polygon to graph CRS using pyproj
transformer = pyproj.Transformer.from_crs("EPSG:4326", crs, always_xy=True)
hazard_poly_projected = transform(transformer.transform, hazard_poly_unprojected)
print("   ✓ Hazard perimeter polygon projected to metric CRS.")

# ==============================================================================
# 2. VEHICLE SPECS & REAL-TIME COMMODITY PRICING CONSTANTS
# ==============================================================================
PAYLOAD_BOUNDS = {"Truck": 5000.0, "Drone": 30.0}
BASE_SPEED_KMH = {"Truck": 50.0, "Drone": 72.0}

# Financial Parameter Sheet
DIESEL_PRICE_GALLON = 6.00      # 2026 National Diesel Average ($)
KM_PER_GALLON = 6.2             # Fuel economy (~2.64 km/L)
BATTERY_CYCLE_COST = 5.87       # $2349 battery value / 400 lifecycles ($)

TRUCK_CLEAR_OP_COST_PER_KM = 0.45 
TRUCK_HAZARD_WEAR_PER_KM = 0.75 # Incremental wear inside damaged/hazard perimeter ($/km)
DRONE_WEAR_PER_KM = 0.15        # Aerodynamic motor stress wear ($/km)

# Weather Conditions
real_time_weather = {"wind_speed_knots": 22.0, "precipitation_mm_hr": 6.0}
repair_factor = 0.5

# ==============================================================================
# 3. ASYMMETRIC LOGISTICS ROUTING & VARIABLE ASSIGNMENTS
# ==============================================================================
time_matrix = {"Truck": {}, "Drone": {}}
dist_matrix = {"Truck": {}, "Drone": {}}
hazard_dist_matrix = {"Truck": {}, "Drone": {}}
modes = ["Truck", "Drone"]

G_truck = G.copy()
weather_friction = 1.0 + (real_time_weather["precipitation_mm_hr"] * 0.08)
damage_friction_multiplier = 12.0 * repair_factor

for u, v, k, data in G_truck.edges(keys=True, data=True):
    if "geometry" in data:
        edge_geom = data["geometry"]
    else:
        u_data = G_truck.nodes[u]
        v_data = G_truck.nodes[v]
        edge_geom = LineString([(u_data["x"], u_data["y"]), (v_data["x"], v_data["y"])])
    
    base_hours = (data.get("length", 0) / 1000.0) / BASE_SPEED_KMH["Truck"]
    is_impacted = hazard_poly_projected.contains(edge_geom) or hazard_poly_projected.intersects(edge_geom)
    data["is_hazard"] = is_impacted
    
    # Calculate travel speed friction scaling
    damage_friction = damage_friction_multiplier if is_impacted else 0.0
    data["truck_hours"] = base_hours * weather_friction * (1.0 + damage_friction)

print("🧭 Computing multimodal route networks (Fastest Path + Hazard Segment Tracking)...")
for d_name, d_coords in depots.items():
    time_matrix["Truck"][d_name], time_matrix["Drone"][d_name] = {}, {}
    dist_matrix["Truck"][d_name], dist_matrix["Drone"][d_name] = {}, {}
    hazard_dist_matrix["Truck"][d_name] = {}
    
    # Transform depot coordinates (lon, lat) to projected graph CRS
    depot_x, depot_y = transformer.transform(d_coords[1], d_coords[0])
    depot_node = ox.nearest_nodes(G, X=depot_x, Y=depot_y)
    
    for z_name, z_coords in zones.items():
        zone_x, zone_y = transformer.transform(z_coords[1], z_coords[0])
        zone_node = ox.nearest_nodes(G, X=zone_x, Y=zone_y)
        
        # 🚚 Truck Calculations:
        # FIX #2: Extract actual distance and hazard exposure along the FASTEST path
        try:
            fastest_path = nx.shortest_path(G_truck, source=depot_node, target=zone_node, weight="truck_hours")
            path_time = nx.shortest_path_length(G_truck, source=depot_node, target=zone_node, weight="truck_hours")
            
            # Trace edges along fastest path to measure true distance and hazard distance
            path_total_len_m = 0.0
            path_hazard_len_m = 0.0
            for u_node, v_node in zip(fastest_path[:-1], fastest_path[1:]):
                edge_dict = G_truck[u_node][v_node]
                # Pick edge with the lowest truck_hours
                best_edge = min(edge_dict.values(), key=lambda d: d.get("truck_hours", float("inf")))
                length_val = best_edge.get("length", 0.0)
                path_total_len_m += length_val
                if best_edge.get("is_hazard", False):
                    path_hazard_len_m += length_val
            
            time_matrix["Truck"][d_name][z_name] = path_time
            dist_matrix["Truck"][d_name][z_name] = path_total_len_m / 1000.0
            hazard_dist_matrix["Truck"][d_name][z_name] = path_hazard_len_m / 1000.0
        except nx.NetworkXNoPath:
            time_matrix["Truck"][d_name][z_name] = 9999.0
            dist_matrix["Truck"][d_name][z_name] = 9999.0
            hazard_dist_matrix["Truck"][d_name][z_name] = 0.0
            
        # 🛸 Drone Calculations (Air distance vectors)
        air_dist = geodesic(d_coords, z_coords).km
        dist_matrix["Drone"][d_name][z_name] = air_dist
        drone_wind_delay = 1.0 + (max(0, real_time_weather["wind_speed_knots"] - 15) * 0.08)
        time_matrix["Drone"][d_name][z_name] = (air_dist / BASE_SPEED_KMH["Drone"]) * drone_wind_delay

# ==============================================================================
# 4. COMPUTE INTEGRATED FINANCIAL VALUE MATRIX
# ==============================================================================
financial_cost_matrix = {"Truck": {}, "Drone": {}}
for m in modes:
    for d in depots:
        financial_cost_matrix[m][d] = {}
        for z in zones:
            d_km = dist_matrix[m][d][z]
            # Compute total expenses per single vehicle round-trip (2x distance)
            if m == "Truck":
                h_km = hazard_dist_matrix["Truck"][d][z]
                fuel_used = (2 * d_km) / KM_PER_GALLON
                fuel_expense = fuel_used * DIESEL_PRICE_GALLON
                # Standard wear applies to all km; hazard wear applies to hazard segment
                clear_wear = (2 * d_km) * TRUCK_CLEAR_OP_COST_PER_KM
                hazard_wear = (2 * h_km) * TRUCK_HAZARD_WEAR_PER_KM
                financial_cost_matrix["Truck"][d][z] = fuel_expense + clear_wear + hazard_wear
            elif m == "Drone":
                battery_expense = BATTERY_CYCLE_COST
                wear_expense = (2 * d_km) * DRONE_WEAR_PER_KM
                financial_cost_matrix["Drone"][d][z] = battery_expense + wear_expense

# ==============================================================================
# 5. MIXED-INTEGER LP OPTIMIZATION SOLVER (True MILP)
# ==============================================================================
# FIX #3: Formulate as a true MILP with integer sorties (y) and continuous payload (x)
# This eliminates the discrepancy between LP solver objective and post-hoc ceil ledger.
prob = pulp.LpProblem("Disaster_Relief_MILP_Optimizer", pulp.LpMinimize)

# Decision variables defined cleanly via dict comprehensions (compatible across all PuLP versions)
y = {
    m: {
        d: {
            z: pulp.LpVariable(f"Trips_{m}_{d}_{z}", lowBound=0, cat="Integer")
            for z in zones
        }
        for d in depots
    }
    for m in modes
}

x = {
    m: {
        d: {
            z: pulp.LpVariable(f"Qty_kg_{m}_{d}_{z}", lowBound=0, cat="Continuous")
            for z in zones
        }
        for d in depots
    }
    for m in modes
}

u = {
    z: pulp.LpVariable(f"Shortage_{z}", lowBound=0, cat="Continuous")
    for z in zones
}

# Objective: Minimize integer round-trip sortie expenses + unmet supply penalty ($50/kg)
prob += (
    pulp.lpSum(y[m][d][z] * financial_cost_matrix[m][d][z] for m in modes for d in depots for z in zones) +
    pulp.lpSum(u[z] * 50.0 for z in zones)
)

# Constraints:
# 1. Capacity per vehicle trip: Qty delivered cannot exceed Payload * Trips
for m in modes:
    for d in depots:
        for z in zones:
            prob += x[m][d][z] <= y[m][d][z] * PAYLOAD_BOUNDS[m]

# 2. Depot Supply limits
for d in depots:
    prob += pulp.lpSum(x[m][d][z] for m in modes for z in zones) <= supplies[d]

# 3. Zone Demand fulfillment with shortage variable
for z in zones:
    prob += pulp.lpSum(x[m][d][z] for m in modes for d in depots) + u[z] == demands[z]

print("\n⚡ Solving Mixed-Integer Linear Program (MILP)...")
if "HiGHS" in pulp.listSolvers(onlyAvailable=True):
    prob.solve(pulp.HiGHS(msg=False))
else:
    prob.solve(pulp.PULP_CBC_CMD(msg=False))
print(f"   ✓ Solver Status: {pulp.LpStatus[prob.status]} (Optimal Objective: ${pulp.value(prob.objective):.2f})")

# ==============================================================================
# 6. GENERATE ITEMIZED FINANCIAL BALANCE LEDGER
# ==============================================================================
total_fuel_cost = 0.0
total_battery_cost = 0.0
total_truck_wear = 0.0
total_drone_wear = 0.0
total_hazard_wear = 0.0
total_shortage_penalty = 0.0
grand_total_cost = 0.0

print("\n" + "=" * 80)
print(f"{'OPERATIONAL FREIGHT LEDGER':^80}")
print("=" * 80)

for m in modes:
    for d in depots:
        for z in zones:
            trips = int(y[m][d][z].varValue) if y[m][d][z].varValue else 0
            qty = x[m][d][z].varValue if x[m][d][z].varValue else 0.0
            
            if trips > 0 or qty > 0:
                one_way_dist = dist_matrix[m][d][z]
                total_route_km = trips * 2 * one_way_dist
                hours_per_sortie = time_matrix[m][d][z] * 2  # round-trip duration
                
                if m == "Truck":
                    hazard_km = hazard_dist_matrix["Truck"][d][z]
                    total_hazard_km = trips * 2 * hazard_km
                    fuel = (total_route_km / KM_PER_GALLON) * DIESEL_PRICE_GALLON
                    clear_wear = total_route_km * TRUCK_CLEAR_OP_COST_PER_KM
                    hazard_wear = total_hazard_km * TRUCK_HAZARD_WEAR_PER_KM
                    
                    total_fuel_cost += fuel
                    total_truck_wear += clear_wear
                    total_hazard_wear += hazard_wear
                    route_cost = fuel + clear_wear + hazard_wear
                else:
                    bat = trips * BATTERY_CYCLE_COST
                    drone_wear = total_route_km * DRONE_WEAR_PER_KM
                    total_battery_cost += bat
                    total_drone_wear += drone_wear
                    route_cost = bat + drone_wear
                    
                grand_total_cost += route_cost
                print(f"📦 {m:5s} Loop | {d} ➔ {z}")
                print(f"       ↳ Allocation: {qty:7.1f} kg over {trips:3d} round-trip sorties")
                print(f"       ↳ Distance  : {one_way_dist:5.2f} km (1-way) | {total_route_km:6.1f} km total round-trip")
                print(f"       ↳ Duration  : {hours_per_sortie * 60:.1f} mins per round-trip sortie")
                if m == "Truck":
                    print(f"       ↳ Hazard Exposure: {hazard_km:5.2f} km/sortie ({total_hazard_km:5.1f} km total in hazard)")
                print(f"       ↳ Subtotal Cost  : ${route_cost:9.2f}")
                print("-" * 80)

for z in zones:
    shortage_qty = u[z].varValue if u[z].varValue else 0.0
    if shortage_qty > 0:
        penalty = shortage_qty * 50.0
        total_shortage_penalty += penalty
        grand_total_cost += penalty
        print(f"⚠️  UNMET DEMAND SHORTAGE in {z}: {shortage_qty:.1f} kg (Penalty: ${penalty:.2f})")

print("=" * 80)
print(f"{'ITEMIZED DISASTER COST ANALYSIS REPORT':^80}")
print("=" * 80)
print(f"⛽ Real-Time Diesel Cost Pool (Trucks):         ${total_fuel_cost:12.2f}")
print(f"🔋 DJI Flight Battery Depletion Pool (Drones):  ${total_battery_cost:12.2f}")
print(f"🛠️  Standard Baseline Fleet Mechanical Wear:     ${total_truck_wear + total_drone_wear:12.2f}")
print(f"🌧️ Severe Hazard Perimeter Mechanical Damage:   ${total_hazard_wear:12.2f}")
if total_shortage_penalty > 0:
    print(f"⚠️  Supply Shortage Disaster Penalty:           ${total_shortage_penalty:12.2f}")
print("-" * 80)
print(f"💰 GRAND TOTAL OPERATION EXPENDITURE BALANCE:    ${grand_total_cost:12.2f}")
print(f"🎯 MILP Mathematical Objective Function Value:   ${pulp.value(prob.objective):12.2f}")
print("=" * 80)
