"""
Global Configuration for Operations
Centralized settings that are shared across all operations
"""

from typing import Dict, List


# ==========================================
# Boundary/Shapefile Configuration
# ==========================================

BOUNDARY_SOURCES = {
    "neighborhoods": "Neighborhoods",
    "districts": "Districts",
    "subregions": "Subregions",
    "traffic_zones": "Traffic Zones"
}

# Attribute fields for each boundary source
BOUNDARY_ATTRIBUTE_FIELDS = {
    "neighborhoods": ["CODE", "NAME_MAHAL", "NAME"],
    "districts": ["DISTRICT", "NAME"],
    "subregions": ["SUBREGION", "NAME"],
    "traffic_zones": ["ZoneNumber"]
}

# Default join field for each boundary
BOUNDARY_DEFAULT_FIELD = {
    "neighborhoods": "CODE",
    "districts": "DISTRICT",
    "subregions": "SUBREGION",
    "traffic_zones": "ZoneNumber"
}


# ==========================================
# Spatial Grid Configuration
# ==========================================

GRID_SIZES = {
    "50m": 50,
    "100m": 100,
    "250m": 250,
    "500m": 500,
    "1km": 1000
}

DEFAULT_GRID_SIZE = "100m"


# ==========================================
# Temporal Bin Configuration
# ==========================================

TIME_BINS = {
    "15 min": 15,
    "30 min": 30,
    "60 min": 60,
    "2 hours": 120,
    "3 hours": 180
}

DEFAULT_TIME_BIN = "30 min"


# ==========================================
# Output Format Configuration
# ==========================================

OUTPUT_FORMATS = ["csv", "shapefile"]
DEFAULT_OUTPUT_FORMAT = "csv"


# ==========================================
# Endpoint/Target Field Configuration
# ==========================================

ENDPOINT_OPTIONS = {
    "origin": "Origin",
    "destination": "Destination",
    "all": "All (Origin + Destination)"
}

# Filter field options (for filtering operations)
FILTER_FIELD_OPTIONS = {
    "all": "All Points",
    "origin": "Origin Only",
    "destination": "Destination Only"
}


# ==========================================
# Aggregation Field Configuration
# ==========================================

# Available aggregation fields by endpoint
AGGREGATION_FIELDS = {
    "origin": {
        "snapp_org_count": "Snapp Count",
        "tapsi_org_count": "Tapsi Count",
        "total_origin": "Total Count"
    },
    "destination": {
        "snapp_dst_count": "Snapp Count",
        "tapsi_dst_count": "Tapsi Count",
        "total_destination": "Total Count"
    },
    "all": {
        "snapp_org_count": "Snapp Origin Count",
        "tapsi_org_count": "Tapsi Origin Count",
        "total_origin": "Total Origin Count",
        "snapp_dst_count": "Snapp Destination Count",
        "tapsi_dst_count": "Tapsi Destination Count",
        "total_destination": "Total Destination Count"
    }
}

# Default aggregation fields by endpoint
DEFAULT_AGGREGATION_FIELDS = {
    "origin": ["total_origin"],
    "destination": ["total_destination"],
    "all": ["total_origin", "total_destination"]
}

# Aggregation levels
AGGREGATION_LEVELS = {
    "total": "Total only (Snapp + Tapsi combined)",
    "separate": "Snapp & Tapsi (separate)",
    "all": "All (Total + Snapp + Tapsi)"
}


# ==========================================
# Helper Functions
# ==========================================

def get_aggregation_fields_for_endpoint(endpoint: str, level: str = "total") -> List[str]:
    """
    Get aggregation fields based on endpoint and level.
    
    Args:
        endpoint: 'origin', 'destination', or 'all'
        level: 'total', 'separate', or 'all'
    
    Returns:
        List of field names to aggregate
    """
    if endpoint == "origin":
        if level == "total":
            return ["total_origin"]
        elif level == "separate":
            return ["snapp_org_count", "tapsi_org_count"]
        else:  # all
            return ["snapp_org_count", "tapsi_org_count", "total_origin"]
    
    elif endpoint == "destination":
        if level == "total":
            return ["total_destination"]
        elif level == "separate":
            return ["snapp_dst_count", "tapsi_dst_count"]
        else:  # all
            return ["snapp_dst_count", "tapsi_dst_count", "total_destination"]
    
    else:  # all
        if level == "total":
            return ["total_origin", "total_destination"]
        elif level == "separate":
            return ["snapp_org_count", "tapsi_org_count", "snapp_dst_count", "tapsi_dst_count"]
        else:  # all
            return ["snapp_org_count", "tapsi_org_count", "total_origin",
                   "snapp_dst_count", "tapsi_dst_count", "total_destination"]


def get_output_path(base_name: str, suffix: str, format: str = "csv"):
    """
    Get standardized output path for operation results.
    
    Args:
        base_name: Base filename
        suffix: Output suffix
        format: 'csv' or 'shapefile'
    
    Returns:
        Path object for output file/directory
    """
    from config import Config
    from pathlib import Path
    
    config = Config()
    
    if format == "csv":
        # CSV files go to Dataset/Aggregated
        return config.aggregated_path / f"{base_name}{suffix}.csv"
    else:
        # Shapefiles go to GIS Files/Layers/Output
        return config.gis_output_path / f"{base_name}{suffix}"

