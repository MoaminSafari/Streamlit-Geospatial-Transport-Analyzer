"""
Shapefile Join Operation - Complete with UI and execution
"""

import streamlit as st
import pandas as pd
import geopandas as gpd
from shapely.geometry import Point
import logging
from typing import Dict, Any, Optional
from pathlib import Path
from operations.base import BaseOperation
from operations.config import (
    BOUNDARY_SOURCES, BOUNDARY_ATTRIBUTE_FIELDS, BOUNDARY_DEFAULT_FIELD,
    ENDPOINT_OPTIONS, AGGREGATION_LEVELS, get_aggregation_fields_for_endpoint
)
from ui_helpers import utils
from config import Config

_logger = logging.getLogger("shapefile_join")


class ShapefileJoinOperation(BaseOperation):
    """Join data with GIS layers"""
    
    def get_metadata(self) -> Dict[str, str]:
        return {
            'key': 'shapefile_join',
            'title': 'Shapefile Join',
            'description': 'Join data with GIS layers',
            'category': 'joins'
        }
    
    def render_ui(self) -> Optional[Dict[str, Any]]:
        """Render UI"""
        
        aggregated_files = utils.get_aggregated_files()
        if not aggregated_files:
            st.warning("⚠️ Please run an analysis first.")
            return None
        
        file_options = {f.name: str(f) for f in aggregated_files}
        
        st.markdown("### Configuration")
        
        selected_file = st.selectbox("Input file:", options=list(file_options.keys()))
        
        col1, col2 = st.columns(2)
        with col1:
            endpoint = st.selectbox("Target field:", options=list(ENDPOINT_OPTIONS.keys()),
                                   format_func=lambda x: ENDPOINT_OPTIONS[x])
        with col2:
            boundary_source = st.selectbox("Boundary:", 
                                          options=list(BOUNDARY_SOURCES.keys()),
                                          format_func=lambda x: BOUNDARY_SOURCES[x])
        
        # Attribute field selection from global config
        attribute_field = st.selectbox(
            "Join field:",
            options=BOUNDARY_ATTRIBUTE_FIELDS.get(boundary_source, ["CODE"]),
            help="Field from shapefile to join with"
        )
        
        st.markdown("---")
        st.markdown("### Aggregation Settings")
        
        aggregate = st.checkbox(
            "Aggregate by zones",
            value=True,
            help="Aggregate records by zones (sum counts)"
        )
        
        # Temporal aggregation option
        separate_by_hour = False
        hour_field = None
        if aggregate:
            st.markdown("**Temporal Aggregation:**")
            temporal_agg = st.radio(
                "Time handling:",
                options=["total", "by_time"],
                format_func=lambda x: {
                    "total": "Total (sum all time periods together)",
                    "by_time": "Keep separate by time (one row per zone per time period)"
                }[x],
                index=0,
                horizontal=True,
                help="Aggregate all time periods or keep them as separate rows"
            )
            separate_by_hour = (temporal_agg == "by_time")
            
            if separate_by_hour:
                # Let user specify the time/hour field
                hour_field = st.text_input(
                    "Time field name:",
                    value="hour",
                    help="Name of the time/hour field in your data (e.g., 'hour', 'time_bin', 'time_slot')"
                )
            
            st.markdown("**Select aggregation type:**")
            
            # Use global aggregation levels
            agg_level = st.radio(
                "Aggregation level:",
                options=list(AGGREGATION_LEVELS.keys()),
                format_func=lambda x: AGGREGATION_LEVELS[x],
                index=0,
                help="Choose which fields to aggregate"
            )
            
            # Get fields from global config
            selected_agg_fields = get_aggregation_fields_for_endpoint(endpoint, agg_level)
        else:
            selected_agg_fields = []
        
        # Auto-generate suffix based on time filter and boundary source
        time_suffix = utils.get_time_filter_suffix()
        default_suffix = f"_{time_suffix}_{boundary_source}_joined"
        output_suffix = st.text_input("Output suffix:", value=default_suffix)
        
        if st.button("▶️ Run", type="primary", width='stretch'):
            cfg = Config()
            if boundary_source == "neighborhoods":
                shp_path = str(cfg.neighborhoods_shapefile)
            elif boundary_source == "districts":
                shp_path = str(cfg.districts_shapefile)
            elif boundary_source == "subregions":
                shp_path = str(cfg.subregions_shapefile)
            else:
                shp_path = str(cfg.traffic_zones_shapefile)
            
            return {
                'input_file': file_options[selected_file],
                'shp_path': shp_path,
                'attribute_field': attribute_field,
                'endpoint': endpoint,
                'aggregate': aggregate,
                'separate_by_hour': separate_by_hour,
                'hour_field': hour_field,
                'aggregation_fields': selected_agg_fields,
                'output_suffix': output_suffix
            }
        
        return None
    
    def execute(self, **kwargs) -> Dict[str, Any]:
        """Execute shapefile join with spatial aggregation"""
        input_file = kwargs['input_file']
        shp_path = kwargs['shp_path']
        attribute_field = kwargs['attribute_field']
        endpoint = kwargs['endpoint']
        aggregate = kwargs['aggregate']
        separate_by_hour = kwargs.get('separate_by_hour', False)
        hour_field = kwargs.get('hour_field', 'hour')
        aggregation_fields = kwargs.get('aggregation_fields', [])
        output_suffix = kwargs['output_suffix']
        
        try:
            _logger.info(f"shapefile_join start input={input_file} shp={shp_path} aggregate={aggregate} hourly={separate_by_hour}")
            df = pd.read_csv(input_file)
            
            # Check for possible column name variations
            if endpoint == 'origin':
                lat_col = next((c for c in ['org_lat', 'origin_lat', 'latitude'] if c in df.columns), None)
                lon_col = next((c for c in ['org_lng', 'org_long', 'origin_lng', 'origin_long', 'longitude'] if c in df.columns), None)
            elif endpoint == 'destination':
                lat_col = next((c for c in ['dst_lat', 'dest_lat', 'destination_lat'] if c in df.columns), None)
                lon_col = next((c for c in ['dst_lng', 'dst_long', 'dest_lng', 'dest_long', 'destination_lng'] if c in df.columns), None)
            else:
                lat_col = next((c for c in ['org_lat', 'dst_lat', 'origin_lat', 'dest_lat', 'latitude', 'lat'] if c in df.columns), None)
                lon_col = next((c for c in ['org_lng', 'org_long', 'dst_lng', 'dst_long', 'origin_lng', 'dest_lng', 'longitude', 'lon', 'lng'] if c in df.columns), None)
            
            if not lat_col or not lon_col:
                return {"success": False, "error": "Coordinate columns not found"}
            
            # Create GeoDataFrame from points
            gdf_points = gpd.GeoDataFrame(df, geometry=[Point(xy) for xy in zip(df[lon_col], df[lat_col])], crs='EPSG:4326')
            
            # Load shapefile
            shp = gpd.read_file(shp_path)
            
            # Ensure CRS match
            if gdf_points.crs != shp.crs:
                gdf_points = gdf_points.to_crs(shp.crs)
            
            # Spatial join (points within polygons)
            joined = gpd.sjoin(gdf_points, shp, how='inner', predicate='within')
            
            input_path = Path(input_file)
            
            if aggregate:
                if attribute_field not in joined.columns:
                    return {"success": False, "error": f"Attribute field '{attribute_field}' not found in joined data"}
                
                # Determine which fields to aggregate
                available_agg_fields = [f for f in aggregation_fields if f in joined.columns]
                
                if not available_agg_fields:
                    return {"success": False, "error": "No aggregation fields found in data"}
                
                # Check if time-based separation is requested
                if separate_by_hour:
                    # Check if the specified hour field exists
                    if hour_field not in joined.columns:
                        _logger.warning(f"Time field '{hour_field}' not found in data, falling back to total aggregation")
                        separate_by_hour = False
                
                if separate_by_hour:
                    # Aggregate by zone AND time (keep as rows, not columns)
                    _logger.info(f"Aggregating by zone and time using field '{hour_field}' (row-based)")
                    
                    # Group by zone and time field - output is row-based
                    agg_dict = {field: 'sum' for field in available_agg_fields}
                    aggregated = joined.groupby([attribute_field, hour_field]).agg(agg_dict).reset_index()
                    
                    _logger.info(f"Created time-based aggregation: {len(aggregated)} rows (zone × time)")
                else:
                    # Total aggregation (sum all time periods together)
                    agg_dict = {field: 'sum' for field in available_agg_fields}
                    aggregated = joined.groupby(attribute_field).agg(agg_dict).reset_index()
                    
                    _logger.info(f"Created total aggregation: {len(aggregated)} zones")
                
                # Merge back with shapefile to get geometries
                # Note: If time-separated, each zone will have multiple rows (one per time period)
                result_gdf = shp.merge(aggregated, on=attribute_field, how='inner')
                
                # Important: When time-separated, the shapefile will have duplicate geometries
                # (same zone geometry repeated for each time period)
                
                # Save as shapefile to GIS output directory
                config = Config()
                output_dir = config.gis_output_path / f"{input_path.stem}{output_suffix}"
                output_dir.mkdir(exist_ok=True, parents=True)
                output_shp = output_dir / f"{input_path.stem}{output_suffix}.shp"
                
                result_gdf.to_file(output_shp)
                
                _logger.info(f"shapefile_join success aggregated zones={len(result_gdf)} path={output_shp}")
                return {
                    "success": True,
                    "output_path": str(output_shp),
                    "zones": len(result_gdf),
                    "aggregated_fields": available_agg_fields,
                    "hourly_separation": separate_by_hour
                }
            else:
                # No aggregation - just join and save to GIS output directory
                config = Config()
                output_dir = config.gis_output_path / f"{input_path.stem}{output_suffix}"
                output_dir.mkdir(exist_ok=True, parents=True)
                output_shp = output_dir / f"{input_path.stem}{output_suffix}.shp"
                
                joined.to_file(output_shp)
                
                _logger.info(f"shapefile_join success rows={len(joined)} path={output_shp}")
                return {
                    "success": True,
                    "output_path": str(output_shp),
                    "rows": len(joined)
                }
                
        except Exception as e:
            _logger.error(f"shapefile_join error: {e}")
            import traceback
            _logger.error(traceback.format_exc())
            return {"success": False, "error": str(e)}
