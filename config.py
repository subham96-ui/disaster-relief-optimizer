"""
Configuration and Parameters Module for Disaster Relief Logistics Optimizer.
Centralizes geographic coordinates, vehicle specifications, commodity pricing,
and atmospheric friction coefficients.
"""

from typing import Dict, Tuple, List

# ==============================================================================
# 1. DEFAULT GEOGRAPHY & LOGISTICS BASELINE
# ==============================================================================
CENTER_LAT: float = 34.0522
CENTER_LON: float = -118.2437

# Supply Hubs: {Name: {"lat": float, "lon": float, "supply": float (kg)}}
DEFAULT_DEPOTS: Dict[str, Dict[str, float]] = {
    "Depot_North": {"lat": 34.0650, "lon": -118.2350, "supply": 15000.0},
    "Depot_South": {"lat": 34.0350, "lon": -118.2550, "supply": 20000.0}
}

# Disaster Impact Zones: {Name: {"lat": float, "lon": float, "demand": float (kg)}}
DEFAULT_ZONES: Dict[str, Dict[str, float]] = {
    "Zone_East_Impact": {"lat": 34.0500, "lon": -118.2200, "demand": 12000.0},
    "Zone_West_Impact": {"lat": 34.0550, "lon": -118.2700, "demand": 8000.0}
}

# Default Hazard Perimeter Anchor Points [(lat, lon), ...]
DEFAULT_HAZARD_COORDS: List[List[float]] = [
    [34.0580, -118.2500],
    [34.0420, -118.2500],
    [34.0420, -118.2300],
    [34.0580, -118.2300]
]

DEFAULT_HAZARD_RADIUS_KM: float = 1.5

# ==============================================================================
# 2. VEHICLE SPECIFICATIONS & KINEMATICS
# ==============================================================================
PAYLOAD_BOUNDS: Dict[str, float] = {
    "Truck": 5000.0,   # Maximum legal freight payload (kg)
    "Drone": 30.0      # Medium-heavy UAV emergency relief payload (kg)
}

BASE_SPEED_KMH: Dict[str, float] = {
    "Truck": 50.0,     # Urban arterial average speed (km/h)
    "Drone": 72.0      # Fixed-wing/multirotor cruising airspeed (km/h)
}

# ==============================================================================
# 3. FINANCIAL CONSTANTS & UNIT COMMODITY PRICING
# ==============================================================================
DIESEL_PRICE_GALLON: float = 6.00      # 2026 National Diesel Average ($/gal)
KM_PER_GALLON: float = 6.2             # Medium-duty freight fuel economy (~2.64 km/L)
BATTERY_CYCLE_COST: float = 5.87       # $2349 battery value / 400 lifecycles ($/cycle)

TRUCK_CLEAR_OP_COST_PER_KM: float = 0.45   # Maintenance & wear on clear roads ($/km)
TRUCK_HAZARD_WEAR_PER_KM: float = 0.75     # Incremental wear in debris/hazard zones ($/km)
DRONE_WEAR_PER_KM: float = 0.15            # Motor & airframe aerodynamic stress wear ($/km)

SHORTAGE_PENALTY_PER_KG: float = 50.0      # Emergency unmet demand penalty ($/kg)

# ==============================================================================
# 4. WEATHER & ROAD FRICTION COEFFICIENTS
# ==============================================================================
DEFAULT_WEATHER: Dict[str, float] = {
    "wind_speed_knots": 22.0,
    "precipitation_mm_hr": 6.0
}

DEFAULT_REPAIR_FACTOR: float = 0.5   # 0.0 (cleared) to 1.0 (impassable/severe rupture)

def calculate_weather_friction(precipitation_mm_hr: float) -> float:
    """Calculates road travel delay scaling factor caused by rain/precipitation."""
    return 1.0 + (max(0.0, precipitation_mm_hr) * 0.08)

def calculate_damage_friction(is_impacted: bool, repair_factor: float) -> float:
    """Calculates friction penalty multiplier for road edges in hazard zones."""
    return (12.0 * repair_factor) if is_impacted else 0.0

def calculate_drone_wind_delay(wind_speed_knots: float) -> float:
    """Calculates drone airspeed reduction scaling caused by sustained headwinds."""
    return 1.0 + (max(0.0, wind_speed_knots - 15.0) * 0.08)
