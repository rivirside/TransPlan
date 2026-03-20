"""
Shared utility functions for the TransPlan backend.
"""

import math


def haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    Compute great-circle distance in miles between two points using the haversine formula.

    Args:
        lat1, lon1: First point (decimal degrees)
        lat2, lon2: Second point (decimal degrees)

    Returns:
        Distance in miles
    """
    R = 3959  # Earth radius in miles
    lat1, lon1, lat2, lon2 = map(math.radians, [lat1, lon1, lat2, lon2])
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
    return R * 2 * math.asin(math.sqrt(a))


def haversine_distance_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Compute great-circle distance in kilometers."""
    return haversine_distance(lat1, lon1, lat2, lon2) * 1.60934


def haversine_distance_nm(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Compute great-circle distance in nautical miles (for UNOS allocation circles)."""
    return haversine_distance(lat1, lon1, lat2, lon2) * 0.868976
