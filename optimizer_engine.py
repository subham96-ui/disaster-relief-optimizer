"""
Mathematical Optimization Engine for Disaster Relief Logistics.
Implements a true Mixed-Integer Linear Program (MILP) in PuLP,
allocating integer vehicle sorties and continuous cargo weight while
minimizing operational costs and shortage penalties.
"""

import logging
from typing import Dict, List, Any, Tuple
import pulp

from config import (
    PAYLOAD_BOUNDS,
    DIESEL_PRICE_GALLON,
    KM_PER_GALLON,
    BATTERY_CYCLE_COST,
    TRUCK_CLEAR_OP_COST_PER_KM,
    TRUCK_HAZARD_WEAR_PER_KM,
    DRONE_WEAR_PER_KM,
    SHORTAGE_PENALTY_PER_KG
)

logger = logging.getLogger("OptimizerEngine")

def build_financial_cost_matrix(
    dist_matrix: Dict[str, Dict[str, Dict[str, float]]],
    hazard_dist_matrix: Dict[str, Dict[str, Dict[str, float]]],
    params: Dict[str, float]
) -> Dict[str, Dict[str, Dict[str, float]]]:
    """
    Computes total round-trip operational expense (2x distance) per single vehicle sortie.
    """
    diesel_price = params.get("diesel_price", DIESEL_PRICE_GALLON)
    km_per_gal = params.get("km_per_gallon", KM_PER_GALLON)
    bat_cost = params.get("battery_cost", BATTERY_CYCLE_COST)
    truck_clear_wear = params.get("truck_clear_wear", TRUCK_CLEAR_OP_COST_PER_KM)
    truck_haz_wear = params.get("truck_hazard_wear", TRUCK_HAZARD_WEAR_PER_KM)
    drone_wear = params.get("drone_wear_km", DRONE_WEAR_PER_KM)

    financial_matrix = {"Truck": {}, "Drone": {}}
    modes = ["Truck", "Drone"]

    for m in modes:
        for d in dist_matrix[m]:
            financial_matrix[m][d] = {}
            for z in dist_matrix[m][d]:
                d_km = dist_matrix[m][d][z]

                if m == "Truck":
                    h_km = hazard_dist_matrix["Truck"][d].get(z, 0.0)
                    fuel_used = (2.0 * d_km) / km_per_gal
                    fuel_expense = fuel_used * diesel_price
                    clear_wear = (2.0 * d_km) * truck_clear_wear
                    hazard_wear = (2.0 * h_km) * truck_haz_wear
                    financial_matrix["Truck"][d][z] = fuel_expense + clear_wear + hazard_wear
                elif m == "Drone":
                    battery_expense = bat_cost
                    wear_expense = (2.0 * d_km) * drone_wear
                    financial_matrix["Drone"][d][z] = battery_expense + wear_expense

    return financial_matrix

def solve_disaster_relief_milp(
    depots: Dict[str, Dict[str, float]],
    zones: Dict[str, Dict[str, float]],
    financial_cost_matrix: Dict[str, Dict[str, Dict[str, float]]],
    time_matrix: Dict[str, Dict[str, Dict[str, float]]],
    dist_matrix: Dict[str, Dict[str, Dict[str, float]]],
    hazard_dist_matrix: Dict[str, Dict[str, Dict[str, float]]],
    route_paths_latlon: Dict[str, Dict[str, Dict[str, list]]],
    params: Dict[str, float]
) -> Dict[str, Any]:
    """
    Formulates and solves the Mixed-Integer Linear Program.
    Returns:
        dict containing solver status, objective value, itemized ledger,
        cost breakdown pools, and route summaries.
    """
    modes = ["Truck", "Drone"]
    truck_payload = params.get("truck_payload", PAYLOAD_BOUNDS["Truck"])
    drone_payload = params.get("drone_payload", PAYLOAD_BOUNDS["Drone"])
    shortage_rate = params.get("shortage_penalty", SHORTAGE_PENALTY_PER_KG)
    payloads = {"Truck": truck_payload, "Drone": drone_payload}

    prob = pulp.LpProblem("Disaster_Relief_MILP", pulp.LpMinimize)

    # Decision variables defined cleanly via dict comprehensions
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

    # Objective: Minimize total sortie expenses + unmet demand penalties
    prob += (
        pulp.lpSum(y[m][d][z] * financial_cost_matrix[m][d][z] for m in modes for d in depots for z in zones) +
        pulp.lpSum(u[z] * shortage_rate for z in zones)
    )

    # 1. Capacity Constraints per sortie
    for m in modes:
        for d in depots:
            for z in zones:
                prob += x[m][d][z] <= y[m][d][z] * payloads[m]

    # 2. Depot Supply Limits
    for d, d_info in depots.items():
        prob += pulp.lpSum(x[m][d][z] for m in modes for z in zones) <= float(d_info.get("supply", 0.0))

    # 3. Zone Demand Satisfaction (with shortage)
    for z, z_info in zones.items():
        prob += pulp.lpSum(x[m][d][z] for m in modes for d in depots) + u[z] == float(z_info.get("demand", 0.0))

    # Solve with HiGHS or CBC solver
    if "HiGHS" in pulp.listSolvers(onlyAvailable=True):
        prob.solve(pulp.HiGHS(msg=False))
    else:
        prob.solve(pulp.PULP_CBC_CMD(msg=False))

    solver_status = pulp.LpStatus[prob.status]
    objective_val = float(pulp.value(prob.objective)) if prob.objective else 0.0

    # -------------------------------------------------------------------------
    # Generate Itemized Ledger & Financial Cost Pools
    # -------------------------------------------------------------------------
    routes_output = []
    cost_breakdown = {
        "diesel_fuel": 0.0,
        "drone_battery": 0.0,
        "truck_wear": 0.0,
        "drone_wear": 0.0,
        "hazard_damage": 0.0,
        "shortage_penalty": 0.0,
        "grand_total": 0.0
    }

    total_delivered_kg = 0.0
    total_truck_sorties = 0
    total_drone_sorties = 0

    diesel_price = params.get("diesel_price", DIESEL_PRICE_GALLON)
    km_per_gal = params.get("km_per_gallon", KM_PER_GALLON)
    bat_cost = params.get("battery_cost", BATTERY_CYCLE_COST)
    truck_clear_wear = params.get("truck_clear_wear", TRUCK_CLEAR_OP_COST_PER_KM)
    truck_haz_wear = params.get("truck_hazard_wear", TRUCK_HAZARD_WEAR_PER_KM)
    drone_wear = params.get("drone_wear_km", DRONE_WEAR_PER_KM)

    for m in modes:
        for d in depots:
            for z in zones:
                trips_val = int(y[m][d][z].varValue) if y[m][d][z].varValue else 0
                qty_val = float(x[m][d][z].varValue) if x[m][d][z].varValue else 0.0

                if trips_val > 0 or qty_val > 0:
                    one_way_km = dist_matrix[m][d][z]
                    total_route_km = trips_val * 2.0 * one_way_km
                    duration_per_trip = time_matrix[m][d][z] * 2.0 * 60.0  # minutes

                    if m == "Truck":
                        h_km = hazard_dist_matrix["Truck"][d].get(z, 0.0)
                        total_h_km = trips_val * 2.0 * h_km
                        fuel = (total_route_km / km_per_gal) * diesel_price
                        c_wear = total_route_km * truck_clear_wear
                        h_wear = total_h_km * truck_haz_wear
                        route_cost = fuel + c_wear + h_wear

                        cost_breakdown["diesel_fuel"] += fuel
                        cost_breakdown["truck_wear"] += c_wear
                        cost_breakdown["hazard_damage"] += h_wear
                        total_truck_sorties += trips_val
                    else:
                        bat = trips_val * bat_cost
                        d_wear = total_route_km * drone_wear
                        route_cost = bat + d_wear

                        cost_breakdown["drone_battery"] += bat
                        cost_breakdown["drone_wear"] += d_wear
                        total_drone_sorties += trips_val

                    cost_breakdown["grand_total"] += route_cost
                    total_delivered_kg += qty_val

                    routes_output.append({
                        "mode": m,
                        "depot": d,
                        "zone": z,
                        "trips": trips_val,
                        "quantity_kg": round(qty_val, 1),
                        "one_way_km": round(one_way_km, 2),
                        "total_route_km": round(total_route_km, 2),
                        "hazard_km_per_trip": round(hazard_dist_matrix["Truck"][d].get(z, 0.0), 2) if m == "Truck" else 0.0,
                        "duration_minutes": round(duration_per_trip, 1),
                        "cost": round(route_cost, 2),
                        "path": route_paths_latlon[m][d].get(z, [])
                    })

    # Shortages
    shortage_items = []
    total_shortage_kg = 0.0
    for z, z_info in zones.items():
        shortage_qty = float(u[z].varValue) if u[z].varValue else 0.0
        if shortage_qty > 0.001:
            pen = shortage_qty * shortage_rate
            cost_breakdown["shortage_penalty"] += pen
            cost_breakdown["grand_total"] += pen
            total_shortage_kg += shortage_qty
            shortage_items.append({
                "zone": z,
                "shortage_kg": round(shortage_qty, 1),
                "penalty": round(pen, 2)
            })

    for k in cost_breakdown:
        cost_breakdown[k] = round(cost_breakdown[k], 2)

    total_demanded = sum(float(z_data.get("demand", 0.0)) for z_data in zones.values())

    return {
        "status": "success",
        "solver_status": solver_status,
        "objective_value": round(objective_val, 2),
        "routes": routes_output,
        "shortages": shortage_items,
        "cost_breakdown": cost_breakdown,
        "summary": {
            "total_delivered_kg": round(total_delivered_kg, 1),
            "total_demanded_kg": round(total_demanded, 1),
            "total_shortage_kg": round(total_shortage_kg, 1),
            "total_truck_sorties": total_truck_sorties,
            "total_drone_sorties": total_drone_sorties,
            "grand_total_cost": cost_breakdown["grand_total"]
        }
    }
