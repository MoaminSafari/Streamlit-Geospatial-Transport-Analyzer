"""
Utility Functions for Web UI
"""

from pathlib import Path
from typing import Dict, List
from config import Config
import streamlit as st


def get_time_filter_from_sidebar():
    """Get time filter configuration from session state."""
    filter_type = st.session_state.get('filter_type', 'all')
    params = st.session_state.get('time_filter_params', {})
    return {"type": filter_type, **params}


def get_time_filter_suffix() -> str:
    """
    Generate suffix based on time filter from sidebar.
    
    Returns:
        Suffix string like: 140405, 1404, 1403SP, 05, ALL
    """
    filter_type = st.session_state.get('filter_type', 'all')
    params = st.session_state.get('time_filter_params', {})
    
    if filter_type == "specific_month":
        year = params.get('year', '')
        month = params.get('month', '')
        return f"{year}{month}"  # e.g., 140405
    
    elif filter_type == "year":
        year = params.get('year', '')
        return f"{year}"  # e.g., 1404
    
    elif filter_type == "season":
        year = params.get('year', '')
        season = params.get('season', '')
        season_abbr = {
            'spring': 'SP',
            'summer': 'SU', 
            'fall': 'FA',
            'winter': 'WI'
        }.get(season, 'SS')
        return f"{year}{season_abbr}"  # e.g., 1403SP
    
    elif filter_type == "month_all_years":
        month = params.get('month', '')
        return f"M{month}"  # e.g., M05
    
    else:  # all or custom
        return "ALL"


def get_available_files(data_source: str) -> Dict[str, List[str]]:
    """Get list of available files for a data source."""
    try:
        config = Config()
        if data_source == "snapp":
            path = config.snapp_raw_path
            files = [f.name for f in path.glob("*.csv")] if path.exists() else []
            return {"snapp": files}
        elif data_source == "tapsi":
            path = config.tapsi_raw_path
            files = [f.name for f in path.glob("*.csv")] if path.exists() else []
            return {"tapsi": files}
        else:  # both
            snapp_path = config.snapp_raw_path
            tapsi_path = config.tapsi_raw_path
            snapp_files = [f.name for f in snapp_path.glob("*.csv")] if snapp_path.exists() else []
            tapsi_files = [f.name for f in tapsi_path.glob("*.csv")] if tapsi_path.exists() else []
            return {"snapp": snapp_files, "tapsi": tapsi_files}
    except Exception as e:
        return {"error": str(e)}


def get_aggregated_files() -> List[Path]:
    """Get list of aggregated CSV files."""
    try:
        config = Config()
        aggregated_path = config.aggregated_path
        if aggregated_path.exists():
            return list(aggregated_path.glob("*.csv"))
        return []
    except Exception:
        return []


def get_raw_files() -> Dict[str, List[Path]]:
    """
    Get list of raw CSV files from both Snapp and Tapsi directories.
    
    Returns:
        Dictionary with 'snapp' and 'tapsi' keys containing lists of file paths
    """
    try:
        config = Config()
        snapp_files = list(config.snapp_raw_path.glob("*.csv")) if config.snapp_raw_path.exists() else []
        tapsi_files = list(config.tapsi_raw_path.glob("*.csv")) if config.tapsi_raw_path.exists() else []
        return {
            "snapp": snapp_files,
            "tapsi": tapsi_files
        }
    except Exception:
        return {"snapp": [], "tapsi": []}


def get_boundary_shapefile_path(boundary_source: str, config_obj=None):
    """
    Get shapefile path for any boundary source dynamically.
    
    Args:
        boundary_source: The boundary source key (e.g., 'neighborhoods', 'metro_area_stations')
        config_obj: Optional Config instance (will create if not provided)
    
    Returns:
        Path to shapefile
    """
    if config_obj is None:
        config_obj = Config()
    
    return config_obj.get_shapefile_path(boundary_source)


def get_shapefile_zones(boundary_source: str) -> Dict[str, List]:
    """
    Get unique zone values from a shapefile for multi-select filtering.
    Dynamically discovers shapefile and its fields.
    
    Args:
        boundary_source: Shapefile key (e.g., 'neighborhoods', 'districts', etc.)
        
    Returns:
        Dictionary with 'field' (field name) and 'values' (sorted unique values)
    """
    try:
        import geopandas as gpd
        from operations.config import get_shapefile_fields, get_default_field
        config = Config()
        
        # Get shapefile path dynamically
        layers_path = config.gis_layers_path
        shp_dir = layers_path / boundary_source
        
        if not shp_dir.exists():
            return {"field": None, "values": [], "error": f"Shapefile directory not found: {shp_dir}"}
        
        # Find .shp file in directory
        shp_files = list(shp_dir.glob("*.shp"))
        if not shp_files:
            return {"field": None, "values": [], "error": f"No shapefile found in: {shp_dir}"}
        
        shp_path = shp_files[0]
        
        # Load shapefile
        gdf = gpd.read_file(shp_path)
        
        # Get the default field for this shapefile
        field_name = get_default_field(boundary_source)
        
        # Verify field exists, otherwise try to find a suitable one
        if field_name not in gdf.columns:
            available_fields = get_shapefile_fields(boundary_source)
            # Prefer NAME-like fields for display
            name_fields = [f for f in available_fields if 'NAME' in f.upper()]
            if name_fields:
                field_name = name_fields[0]
            elif available_fields:
                field_name = available_fields[0]
            else:
                return {"field": None, "values": [], "error": f"No valid fields found in shapefile"}
        
        # Extract unique values and sort
        unique_values = gdf[field_name].dropna().unique()
        
        # Convert to appropriate type and sort
        # Try numeric first
        try:
            unique_values = sorted([int(v) for v in unique_values])
        except (ValueError, TypeError):
            # Fall back to string sorting
            unique_values = sorted(str(v) for v in unique_values)
        
        return {
            "field": field_name,
            "values": unique_values,
            "count": len(unique_values)
        }
        
    except Exception as e:
        return {"field": None, "values": [], "error": str(e)}


def save_filter_config(config_dict: Dict) -> None:
    """Save filter configuration to JSON file."""
    try:
        import json
        from pathlib import Path
        config_path = Path(__file__).parent.parent / "last_filter_config.json"
        with open(config_path, 'w') as f:
            json.dump(config_dict, f, indent=2)
    except Exception as e:
        import logging
        logging.error(f"Failed to save filter config: {e}")


def load_filter_config() -> Dict:
    """Load filter configuration from JSON file."""
    try:
        import json
        from pathlib import Path
        config_path = Path(__file__).parent.parent / "last_filter_config.json"
        if config_path.exists():
            with open(config_path, 'r') as f:
                return json.load(f)
    except Exception as e:
        import logging
        logging.error(f"Failed to load filter config: {e}")
    return {}

