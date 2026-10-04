"""
Multimodal Routing & Kinematics Engine for Disaster Relief Logistics.
Handles road friction scaling, fastest-route network tracing, hazard exposure metrics,
and drone aerial vector calculations.

Optimizations:
- Bounding-box pre-filtering on graph edges reduces hazard intersection checks from O(E) to O(E_intersect).
- Trace-based path extraction computes true route mileage along time-optimal paths in a single pass.
"""

import logging
from typing import Dict, List, Tuple, Any
import networkx as nx
import osmnx as ox
from shapely.geometry import LineString, box
from geopy.distance import geodesic

from config import (
    BASE_SPEED_KMH,
    calculate_weather_friction,
    calculate_damage_friction,
    calculate_drone_wind_delay
)

logger = logging.getLogger("RoutingEngine")

def apply_edge_frictions(
    G: nx.MultiDiGraph,
    hazard_poly_projected: Any,
    precipitation_mm_hr: float,
    repair_factor: float
) -> nx.MultiDiGraph:
    """
    Applies atmospheric and infrastructure damage delay scaling to all road edges.
    Uses bounding-box pre-filtering to optimize spatial checks.
    """
    G_truck = G.copy()
    weather_friction = calculate_weather_friction(precipitation_mm_hr)
    hazard_bbox = box(*hazard_poly_projected.bounds)

    for u, v, k, data in G_truck.edges(keys=True, data=True):
        if "geometry" in data:
            edge_geom = data["geometry"]
        else:
            u_data = G_truck.nodes[u]
            v_data = G_truck.nodes[v]
            edge_geom = LineString([(u_data["x"], u_data["y"]), (v_data["x"], v_data["y"])])

        base_hours = (data.get("length", 0.0) / 1000.0) / BASE_SPEED_KMH["Truck"]

        # Fast bounding-box check first (O(1)) before expensive polygon intersection
        is_impacted = False
        if hazard_bbox.intersects(edge_geom):
            is_impacted = hazard_poly_projected.contains(edge_geom) or hazard_poly_projected.intersects(edge_geom)

        data["is_hazard"] = is_impacted
        damage_friction = calculate_damage_friction(is_impacted, repair_factor)
        data["truck_hours"] = base_hours * weather_friction * (1.0 + damage_friction)

    return G_truck

def compute_multimodal_matrices(
    G_truck: nx.MultiDiGraph,
    G_unprojected: nx.MultiDiGraph,
    depots: Dict[str, Dict[str, float]],
    zones: Dict[str, Dict[str, float]],
    wind_speed_knots: float,
    transformer: Any
) -> Dict[str, Any]:
    """
    Computes travel times, path distances, hazard exposures, and route geometries
    for both Truck and Drone modes between all depot-zone pairs.
    """
    time_matrix = {"Truck": {}, "Drone": {}}
    dist_matrix = {"Truck": {}, "Drone": {}}
    hazard_dist_matrix = {"Truck": {}, "Drone": {}}
    route_paths_latlon = {"Truck": {}, "Drone": {}}
    modes = ["Truck", "Drone"]

    drone_wind_delay = calculate_drone_wind_delay(wind_speed_knots)

    for d_name, d_info in depots.items():
        time_matrix["Truck"][d_name], time_matrix["Drone"][d_name] = {}, {}
        dist_matrix["Truck"][d_name], dist_matrix["Drone"][d_name] = {}, {}
        hazard_dist_matrix["Truck"][d_name] = {}
        route_paths_latlon["Truck"][d_name], route_paths_latlon["Drone"][d_name] = {}, {}

        # Project depot coordinates to graph CRS
        depot_x, depot_y = transformer.transform(d_info["lon"], d_info["lat"])
        depot_node = ox.nearest_nodes(G_truck, X=depot_x, Y=depot_y)

        for z_name, z_info in zones.items():
            zone_x, zone_y = transformer.transform(z_info["lon"], z_info["lat"])
            zone_node = ox.nearest_nodes(G_truck, X=zone_x, Y=zone_y)

            # ------------------------------------------------------------------
            # 🚚 Truck Calculations (Fastest Path + Road Edge Tracing)
            # ------------------------------------------------------------------
            try:
                fastest_path = nx.shortest_path(G_truck, source=depot_node, target=zone_node, weight="truck_hours")
                path_time = nx.shortest_path_length(G_truck, source=depot_node, target=zone_node, weight="truck_hours")

                path_total_m = 0.0
                path_hazard_m = 0.0
                coords_list = []

                for u_node, v_node in zip(fastest_path[:-1], fastest_path[1:]):
                    edge_dict = G_truck[u_node][v_node]
                    best_edge = min(edge_dict.values(), key=lambda d: d.get("truck_hours", float("inf")))
                    length_val = best_edge.get("length", 0.0)
                    path_total_m += length_val
                    if best_edge.get("is_hazard", False):
                        path_hazard_m += length_val

                    u_node_data = G_unprojected.nodes[u_node]
                    coords_list.append([u_node_data["y"], u_node_data["x"]])

                last_node_data = G_unprojected.nodes[fastest_path[-1]]
                coords_list.append([last_node_data["y"], last_node_data["x"]])

                time_matrix["Truck"][d_name][z_name] = path_time
                dist_matrix["Truck"][d_name][z_name] = path_total_m / 1000.0
                hazard_dist_matrix["Truck"][d_name][z_name] = path_hazard_m / 1000.0
                route_paths_latlon["Truck"][d_name][z_name] = coords_list

            except nx.NetworkXNoPath:
                time_matrix["Truck"][d_name][z_name] = 9999.0
                dist_matrix["Truck"][d_name][z_name] = 9999.0
                hazard_dist_matrix["Truck"][d_name][z_name] = 0.0
                route_paths_latlon["Truck"][d_name][z_name] = []

            # ------------------------------------------------------------------
            # 🛸 Drone Calculations (Great-Circle Direct Air Vectors)
            # ------------------------------------------------------------------
            air_dist = geodesic((d_info["lat"], d_info["lon"]), (z_info["lat"], z_info["lon"])).km
            drone_time = (air_dist / BASE_SPEED_KMH["Drone"]) * drone_wind_delay

            dist_matrix["Drone"][d_name][z_name] = air_dist
            time_matrix["Drone"][d_name][z_name] = drone_time
            route_paths_latlon["Drone"][d_name][z_name] = [
                [d_info["lat"], d_info["lon"]],
                [z_info["lat"], z_info["lon"]]
            ]

    return {
        "time_matrix": time_matrix,
        "dist_matrix": dist_matrix,
        "hazard_dist_matrix": hazard_dist_matrix,
        "route_paths_latlon": route_paths_latlon
    }
