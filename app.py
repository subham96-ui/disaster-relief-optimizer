"""
Flask Web Application Controller for Interactive Disaster Relief Logistics Simulator.
Coordinates the modular weather, spatial GIS, routing, and MILP optimization engines.
"""

import sys
import os
import logging
from typing import Dict, Any

# Ensure UTF-8 stdout encoding on Windows
if sys.platform.startswith("win"):
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")

from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS

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
    create_hazard_buffer,
    generate_regular_polygon_coords
)
from population_engine import analyze_population
from gdacs_service import query_emergencies_in_hazard_polygon
from routing_engine import (
    apply_edge_frictions,
    compute_multimodal_matrices
)
from optimizer_engine import (
    build_financial_cost_matrix,
    solve_disaster_relief_milp
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("DisasterReliefApp")

app = Flask(__name__, static_folder="static", static_url_path="")
CORS(app)

@app.route("/")
def index():
    """Serves the interactive single-page simulation dashboard."""
    return send_from_directory("static", "index.html")

@app.route("/api/weather", methods=["POST"])
def fetch_weather_endpoint():
    """Endpoint for retrieving live atmospheric metrics from OWM / Open-Meteo."""
    data = request.json or {}
    lat = float(data.get("lat", 34.0522))
    lon = float(data.get("lon", -118.2437))
    owm_key = data.get("owm_key", None)
    
    result = fetch_live_weather(lat, lon, owm_key)
    return jsonify(result)

@app.route("/api/population", methods=["POST"])
def population_analysis():
    """
    Population density analysis endpoint.
    Queries OSM building footprints as population proxy to:
    - Estimate populations in hazard core zone and outer ring (1.5x radius)
    - Generate a density heatmap grid
    - Detect top-K high-density impact zone candidates
    - Build an adaptive hazard polygon from the convex hull of inner buildings
    """
    try:
        body = request.json or {}
        center_lat = float(body.get("center_lat", 34.0522))
        center_lon = float(body.get("center_lon", -118.2437))
        hazard_radius_km = float(body.get("hazard_radius_km", DEFAULT_HAZARD_RADIUS_KM))
        hazard_coords = body.get("hazard_coords", None)
        hazard_sides = int(body.get("hazard_sides", 6))
        top_k = int(body.get("top_k", 5))

        result = analyze_population(
            center_lat=center_lat,
            center_lon=center_lon,
            hazard_radius_km=hazard_radius_km,
            hazard_coords=hazard_coords,
            hazard_sides=hazard_sides,
            top_k=top_k,
        )
        return jsonify(result)
    except Exception as e:
        logger.exception("Error during population analysis:")
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route("/api/gdacs", methods=["POST"])
def gdacs_emergencies_endpoint():
    """
    GDACS Live Natural Disaster & Humanitarian Emergencies endpoint.
    Queries the UN OCHA / European Commission GDACS live alerts feed
    and filters for emergencies intersecting or near the hazard polygon perimeter.
    """
    try:
        body = request.json or {}
        center_lat = float(body.get("center_lat", 34.0522))
        center_lon = float(body.get("center_lon", -118.2437))
        hazard_radius_km = float(body.get("hazard_radius_km", DEFAULT_HAZARD_RADIUS_KM))
        hazard_coords = body.get("hazard_coords", None)
        search_radius_km = float(body.get("search_radius_km", max(100.0, hazard_radius_km * 3.0)))

        result = query_emergencies_in_hazard_polygon(
            hazard_coords=hazard_coords,
            center_lat=center_lat,
            center_lon=center_lon,
            hazard_radius_km=hazard_radius_km,
            search_radius_km=search_radius_km
        )
        return jsonify(result)
    except Exception as e:
        logger.exception("Error querying GDACS emergency data:")
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route("/api/optimize", methods=["POST"])
def optimize_relief():
    """
    Main simulation endpoint:
    Ingests OSM road graph, buffers hazard perimeter by n km,
    computes time-optimal routes under weather/damage friction,
    and solves the MILP optimization model.
    """
    try:
        body = request.json or {}

        depots = body.get("depots", DEFAULT_DEPOTS)
        zones = body.get("zones", DEFAULT_ZONES)
        hazard_radius_km = float(body.get("hazard_radius_km", DEFAULT_HAZARD_RADIUS_KM))
        
        # Prioritize custom or population-adjusted hazard_coords if provided by client
        hazard_coords = body.get("hazard_coords")
        if not hazard_coords or len(hazard_coords) < 3:
            hazard_center = body.get("hazard_center")
            hazard_sides = body.get("hazard_sides")
            if hazard_center and hazard_sides:
                c_lat = float(hazard_center[0])
                c_lon = float(hazard_center[1])
                hazard_coords = generate_regular_polygon_coords(
                    c_lat, c_lon, sides=int(hazard_sides), radius_km=hazard_radius_km
                )
            else:
                hazard_coords = DEFAULT_HAZARD_COORDS

        repair_factor = float(body.get("repair_factor", DEFAULT_REPAIR_FACTOR))

        weather = body.get("weather", {})
        wind_speed_knots = float(weather.get("wind_speed_knots", 22.0))
        precip_mm_hr = float(weather.get("precipitation_mm_hr", 6.0))

        params = body.get("params", {})

        # 1. Determine spatial scope and retrieve road network
        center_lat, center_lon, query_dist_m = calculate_bounding_radius(
            depots, zones, hazard_coords, hazard_radius_km
        )
        net = get_road_network(center_lat, center_lon, dist_m=query_dist_m)
        G = net["G"]
        G_unprojected = net["G_unprojected"]
        transformer = net["transformer"]
        rev_transformer = net["rev_transformer"]

        # 2. Metric Hazard Buffer (n km)
        hazard_poly_projected, hazard_geojson = create_hazard_buffer(
            hazard_coords, hazard_radius_km, transformer, rev_transformer
        )

        # 3. Asymmetric Road & Kinematic Edge Frictions
        G_truck = apply_edge_frictions(
            G, hazard_poly_projected, precip_mm_hr, repair_factor
        )

        # 4. Multimodal Routing Matrices
        matrices = compute_multimodal_matrices(
            G_truck, G_unprojected, depots, zones, wind_speed_knots, transformer
        )

        # 5. Financial Unit Cost Matrix & MILP Optimization
        financial_cost_matrix = build_financial_cost_matrix(
            matrices["dist_matrix"], matrices["hazard_dist_matrix"], params
        )

        results = solve_disaster_relief_milp(
            depots,
            zones,
            financial_cost_matrix,
            matrices["time_matrix"],
            matrices["dist_matrix"],
            matrices["hazard_dist_matrix"],
            matrices["route_paths_latlon"],
            params
        )

        results["hazard_geojson"] = hazard_geojson
        return jsonify(results)

    except Exception as e:
        logger.exception("Error during optimization pipeline:")
        return jsonify({"status": "error", "message": str(e)}), 500

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    print(f"🚀 Starting Disaster Relief Optimizer Web Application on http://localhost:{port}")
    app.run(host="0.0.0.0", port=port, debug=False)
