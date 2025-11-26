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


def get_shapefile_zones(boundary_source: str) -> Dict[str, List]:
    """
    Get unique zone values from a shapefile for multi-select filtering.
    
    Args:
        boundary_source: One of 'neighborhoods', 'districts', 'traffic_zones'
        
    Returns:
        Dictionary with 'field' (field name) and 'values' (sorted unique values)
    """
    try:
        import geopandas as gpd
        config = Config()
        
        # Determine shapefile path and field name
        if boundary_source == "neighborhoods":
            shp_path = config.neighborhoods_shapefile
            field_name = "NAME_MAHAL"  # Use Persian name for neighborhoods
            fallback_field = "CODE"
        elif boundary_source == "districts":
            shp_path = config.districts_shapefile
            field_name = "STRING_"
            fallback_field = "REGION"
        elif boundary_source == "subregions":
            shp_path = config.subregions_shapefile
            field_name = "TEXT"
            fallback_field = "NAHIYEH"
        elif boundary_source == "traffic_zones":
            shp_path = config.gis_layers_path / "traffic_zone"
            shp_files = list(shp_path.rglob("*.shp")) if shp_path.exists() else []
            if not shp_files:
                return {"field": None, "values": [], "error": "Traffic zones shapefile not found"}
            shp_path = shp_files[0]
            field_name = "ZoneNumber"
            fallback_field = "OBJECTID"
        else:
            return {"field": None, "values": [], "error": f"Unknown boundary source: {boundary_source}"}
        
        # Load shapefile
        if not shp_path.exists():
            return {"field": None, "values": [], "error": f"Shapefile not found: {shp_path}"}
        
        gdf = gpd.read_file(shp_path)
        
        # Get field (use fallback if primary doesn't exist)
        if field_name not in gdf.columns:
            if fallback_field in gdf.columns:
                field_name = fallback_field
            else:
                return {"field": None, "values": [], "error": f"Field {field_name} not found in shapefile"}
        
        # Extract unique values and sort
        unique_values = gdf[field_name].dropna().unique()
        
        # Convert to appropriate type and sort
        if boundary_source == "traffic_zones" or boundary_source == "districts":
            # Numeric zones - convert to int and sort numerically
            try:
                unique_values = sorted([int(v) for v in unique_values])
            except (ValueError, TypeError):
                unique_values = sorted(unique_values.tolist())
        else:
            # String values (neighborhood names) - sort alphabetically
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

