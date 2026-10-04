"""
CLI Runner for Disaster Relief Logistics Optimizer.
Executes the end-to-end pipeline in command-line mode:
1. Ingests live weather (OWM / Open-Meteo)
2. Generates metric hazard buffer
3. Ingests OSM road network
4. Calculates asymmetric friction delays
5. Solves the Mixed-Integer Linear Program
6. Prints the Itemized Financial Balance Ledger
"""

import sys
import os

if sys.platform.startswith("win"):
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")

import logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

from config import (
    DEFAULT_DEPOTS,
    DEFAULT_ZONES,
    DEFAULT_HAZARD_COORDS,
    DEFAULT_HAZARD_RADIUS_KM,
    DEFAULT_REPAIR_FACTOR
)
from weather_service import fetch_live_weather
from spatial_engine import (
    calculate_bounding_radius,
    get_road_network,
    create_hazard_buffer
)
from routing_engine import (
    apply_edge_frictions,
    compute_multimodal_matrices
)
from optimizer_engine import (
    build_financial_cost_matrix,
    solve_disaster_relief_milp
)

def run():
    print("=" * 80)
    print(f"{'DISASTER RELIEF LOGISTICS & ROUTING OPTIMIZER (CLI)':^80}")
    print("=" * 80)

    # 1. Weather Ingestion
    center_lat, center_lon, query_dist_m = calculate_bounding_radius(
        DEFAULT_DEPOTS, DEFAULT_ZONES, DEFAULT_HAZARD_COORDS, DEFAULT_HAZARD_RADIUS_KM
    )
    print(f"🌤️ Fetching real-time atmospheric conditions for ({center_lat:.4f}, {center_lon:.4f})...")
    weather = fetch_live_weather(center_lat, center_lon)
    print(f"   ✓ Source: {weather['source']}")
    print(f"   ✓ Wind Speed: {weather['wind_speed_knots']:.1f} knots | Precipitation: {weather['precipitation_mm_hr']:.2f} mm/h | Temp: {weather['temperature_c']}°C")

    # 2. Road Network Ingestion
    print(f"\n📥 Ingesting road network from OpenStreetMap (dist={query_dist_m}m)...")
    net = get_road_network(center_lat, center_lon, dist_m=query_dist_m)
    G = net["G"]
    G_unprojected = net["G_unprojected"]
    transformer = net["transformer"]
    rev_transformer = net["rev_transformer"]

    # 3. Hazard Buffer Creation (n km)
    print(f"\n⚠️ Generating metric hazard perimeter buffer (n = {DEFAULT_HAZARD_RADIUS_KM:.2f} km)...")
    hazard_poly_projected, _ = create_hazard_buffer(
        DEFAULT_HAZARD_COORDS, DEFAULT_HAZARD_RADIUS_KM, transformer, rev_transformer
    )
    print(f"   ✓ Metric buffer polygon formed ({hazard_poly_projected.area / 1e6:.2f} km² area)")

    # 4. Routing & Edge Friction
    print("\n🧭 Applying weather & road damage friction scaling...")
    G_truck = apply_edge_frictions(
        G, hazard_poly_projected, weather["precipitation_mm_hr"], DEFAULT_REPAIR_FACTOR
    )

    print("🛣️ Computing fastest road paths and aerial flight vectors...")
    matrices = compute_multimodal_matrices(
        G_truck, G_unprojected, DEFAULT_DEPOTS, DEFAULT_ZONES, weather["wind_speed_knots"], transformer
    )

    # 5. Financial Unit Cost Matrix & Optimization
    print("\n⚡ Formulating & Solving Mixed-Integer Linear Program (MILP)...")
    financial_costs = build_financial_cost_matrix(
        matrices["dist_matrix"], matrices["hazard_dist_matrix"], {}
    )

    results = solve_disaster_relief_milp(
        DEFAULT_DEPOTS,
        DEFAULT_ZONES,
        financial_costs,
        matrices["time_matrix"],
        matrices["dist_matrix"],
        matrices["hazard_dist_matrix"],
        matrices["route_paths_latlon"],
        {}
    )

    # 6. Display Operational Freight Ledger
    print("\n" + "=" * 80)
    print(f"{'OPERATIONAL FREIGHT LEDGER':^80}")
    print("=" * 80)
    for rt in results["routes"]:
        m = rt["mode"]
        d = rt["depot"]
        z = rt["zone"]
        qty = rt["quantity_kg"]
        trips = rt["trips"]
        one_way = rt["one_way_km"]
        total_rt = rt["total_route_km"]
        dur = rt["duration_minutes"]
        h_km = rt["hazard_km_per_trip"]
        cost = rt["cost"]

        print(f"📦 {m:5s} Loop | {d} ➔ {z}")
        print(f"       ↳ Allocation: {qty:7.1f} kg over {trips:3d} round-trip sorties")
        print(f"       ↳ Distance  : {one_way:5.2f} km (1-way) | {total_rt:6.1f} km total round-trip")
        print(f"       ↳ Duration  : {dur:.1f} mins per round-trip sortie")
        if m == "Truck":
            print(f"       ↳ Hazard Exposure: {h_km:5.2f} km/sortie")
        print(f"       ↳ Subtotal Cost  : ${cost:9.2f}")
        print("-" * 80)

    for sh in results["shortages"]:
        print(f"⚠️ UNMET DEMAND SHORTAGE in {sh['zone']}: {sh['shortage_kg']:.1f} kg (Penalty: ${sh['penalty']:.2f})")

    cb = results["cost_breakdown"]
    print("=" * 80)
    print(f"{'ITEMIZED DISASTER COST ANALYSIS REPORT':^80}")
    print("=" * 80)
    print(f"⛽ Real-Time Diesel Cost Pool (Trucks):         ${cb['diesel_fuel']:12.2f}")
    print(f"🔋 DJI Flight Battery Depletion Pool (Drones):  ${cb['drone_battery']:12.2f}")
    print(f"🛠️  Clear Road Vehicle Wear (Trucks):            ${cb['truck_wear']:12.2f}")
    print(f"🛸 Motor Aerodynamic Stress Wear (Drones):      ${cb['drone_wear']:12.2f}")
    print(f"🌧️ Severe Hazard Perimeter Wreckage Wear:       ${cb['hazard_damage']:12.2f}")
    if cb["shortage_penalty"] > 0:
        print(f"⚠️  Supply Shortage Disaster Penalty:           ${cb['shortage_penalty']:12.2f}")
    print("-" * 80)
    print(f"💰 GRAND TOTAL OPERATION EXPENDITURE BALANCE:    ${cb['grand_total']:12.2f}")
    print(f"🎯 MILP Mathematical Objective Function Value:   ${results['objective_value']:12.2f}")
    print("=" * 80)

if __name__ == "__main__":
    run()
