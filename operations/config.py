"""
Global Configuration for Operations
Centralized settings that are shared across all operations
"""

from typing import Dict, List
import os
from pathlib import Path
import geopandas as gpd


# ==========================================
# Dynamic Shapefile Discovery
# ==========================================

def _get_layers_path():
    """Get the GIS Layers directory path."""
    # Use relative path from this file
    current_file = Path(__file__).resolve()
    helper_scripts = current_file.parent.parent
    project_root = helper_scripts.parent
    return project_root / "GIS FIles" / "Layers"


def _discover_shapefiles():
    """
    Automatically discover all shapefiles in the Layers directory.
    
    Returns:
        Dict mapping shapefile key to display name
    """
    layers_path = _get_layers_path()
    
    if not layers_path.exists():
        return {}
    
    shapefiles = {}
    
    # Scan all subdirectories in Layers folder
    for item in layers_path.iterdir():
        if item.is_dir() and item.name != "Output":
            # Check if this directory contains a shapefile
            shp_files = list(item.glob("*.shp"))
            if shp_files:
                # Use directory name as key
                key = item.name
                # Convert to readable display name (replace _ with space, title case)
                display_name = key.replace("_", " ").title()
                shapefiles[key] = display_name
    
    return shapefiles


def _get_shapefile_fields(shapefile_key: str) -> List[str]:
    """
    Get available fields from a shapefile.
    
    Args:
        shapefile_key: The shapefile identifier (directory name)
    
    Returns:
        List of field names
    """
    try:
        layers_path = _get_layers_path()
        shapefile_dir = layers_path / shapefile_key
        
        # Find the .shp file
        shp_files = list(shapefile_dir.glob("*.shp"))
        if not shp_files:
            return ["OBJECTID"]
        
        # Read shapefile and get columns (excluding geometry)
        gdf = gpd.read_file(shp_files[0])
        fields = [col for col in gdf.columns if col != 'geometry']
        
        return fields if fields else ["OBJECTID"]
    except:
        # Fallback to common field
        return ["OBJECTID"]


def _get_default_field(shapefile_key: str, fields: List[str]) -> str:
    """
    Determine the default field for a shapefile based on available fields.
    
    Args:
        shapefile_key: The shapefile identifier
        fields: List of available fields
    
    Returns:
        Default field name
    """
    # Priority order for default field selection
    priority_fields = [
        "CODE", "DISTRICT", "SUBREGION", "ZoneNumber", 
        "OBJECTID", "ID", "FID", "Name"
    ]
    
    for field in priority_fields:
        if field in fields:
            return field
    
    # Return first available field as fallback
    return fields[0] if fields else "OBJECTID"


# ==========================================
# Boundary/Shapefile Configuration (Dynamic)
# ==========================================

# Discover all available shapefiles automatically
BOUNDARY_SOURCES = _discover_shapefiles()

# Cache for shapefile fields (to avoid repeated file reads)
_SHAPEFILE_FIELDS_CACHE = {}


def get_shapefile_fields(shapefile_key: str) -> List[str]:
    """
    Get available fields for a shapefile (cached).
    
    Args:
        shapefile_key: The shapefile identifier
    
    Returns:
        List of field names
    """
    if shapefile_key not in _SHAPEFILE_FIELDS_CACHE:
        _SHAPEFILE_FIELDS_CACHE[shapefile_key] = _get_shapefile_fields(shapefile_key)
    return _SHAPEFILE_FIELDS_CACHE[shapefile_key]


def get_default_field(shapefile_key: str) -> str:
    """
    Get the default field for a shapefile.
    
    Args:
        shapefile_key: The shapefile identifier
    
    Returns:
        Default field name
    """
    fields = get_shapefile_fields(shapefile_key)
    return _get_default_field(shapefile_key, fields)


# For backward compatibility - these will be generated dynamically
BOUNDARY_ATTRIBUTE_FIELDS = {}
BOUNDARY_DEFAULT_FIELD = {}


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

# Available aggregation fields by endpoint (using camelCase)
AGGREGATION_FIELDS = {
    "origin": {
        "snappOriginCount": "Snapp Count",
        "tapsiOriginCount": "Tapsi Count",
        "totalOrigin": "Total Count"
    },
    "destination": {
        "snappDestinationCount": "Snapp Count",
        "tapsiDestinationCount": "Tapsi Count",
        "totalDestination": "Total Count"
    },
    "all": {
        "snappOriginCount": "Snapp Origin Count",
        "tapsiOriginCount": "Tapsi Origin Count",
        "totalOrigin": "Total Origin Count",
        "snappDestinationCount": "Snapp Destination Count",
        "tapsiDestinationCount": "Tapsi Destination Count",
        "totalDestination": "Total Destination Count"
    }
}

# Default aggregation fields by endpoint (using camelCase)
DEFAULT_AGGREGATION_FIELDS = {
    "origin": ["totalOrigin"],
    "destination": ["totalDestination"],
    "all": ["totalOrigin", "totalDestination"]
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
    Get aggregation fields based on endpoint and level (camelCase names).
    
    Args:
        endpoint: 'origin', 'destination', or 'all'
        level: 'total', 'separate', or 'all'
    
    Returns:
        List of field names to aggregate (in camelCase)
    """
    if endpoint == "origin":
        if level == "total":
            return ["totalOrigin"]
        elif level == "separate":
            return ["snappOriginCount", "tapsiOriginCount"]
        else:  # all
            return ["snappOriginCount", "tapsiOriginCount", "totalOrigin"]
    
    elif endpoint == "destination":
        if level == "total":
            return ["totalDestination"]
        elif level == "separate":
            return ["snappDestinationCount", "tapsiDestinationCount"]
        else:  # all
            return ["snappDestinationCount", "tapsiDestinationCount", "totalDestination"]
    
    else:  # all
        if level == "total":
            return ["totalOrigin", "totalDestination"]
        elif level == "separate":
            return ["snappOriginCount", "tapsiOriginCount", "snappDestinationCount", "tapsiDestinationCount"]
        else:  # all
            return ["snappOriginCount", "tapsiOriginCount", "totalOrigin",
                   "snappDestinationCount", "tapsiDestinationCount", "totalDestination"]


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

