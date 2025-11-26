"""
Boundary Filter Operation - Complete with UI and execution
"""

import streamlit as st
import pandas as pd
import geopandas as gpd
from shapely.geometry import Point
import logging
from typing import Dict, Any, Optional
from pathlib import Path
from operations.base import BaseOperation
from operations.config import BOUNDARY_SOURCES, FILTER_FIELD_OPTIONS, OUTPUT_FORMATS
from ui_helpers import utils
from config import Config

# Setup logger
_logger = logging.getLogger("boundary_filter")


class BoundaryFilterOperation(BaseOperation):
    """Filter data by geographic boundaries"""
    
    def get_metadata(self) -> Dict[str, str]:
        return {
            'key': 'boundary_filter',
            'title': 'Boundary Filter',
            'description': 'Filter data by geographic boundaries',
            'category': 'filters'
        }
    
    def render_ui(self) -> Optional[Dict[str, Any]]:
        """Render UI and return params if Run clicked"""
        
        # Get aggregated files
        aggregated_files = utils.get_aggregated_files()
        if not aggregated_files:
            st.warning("⚠️ Please run an analysis first to generate aggregated files.")
            return None
        
        file_options = {f.name: str(f) for f in aggregated_files}
        
        col1, col2 = st.columns(2)
        with col1:
            selected_file = st.selectbox("Input file:", options=list(file_options.keys()))
        with col2:
            filter_field = st.selectbox("Filter field:", 
                                       options=list(FILTER_FIELD_OPTIONS.keys()),
                                       format_func=lambda x: FILTER_FIELD_OPTIONS[x])
        
        col3, col4 = st.columns(2)
        with col3:
            boundary_options = list(BOUNDARY_SOURCES.keys()) + ["shapefile"]
            boundary_labels = {**BOUNDARY_SOURCES, "shapefile": "Custom Shapefile"}
            boundary_source = st.radio("Boundary source:", 
                                      options=boundary_options,
                                      format_func=lambda x: boundary_labels[x])
        with col4:
            output_format = st.selectbox("Output format:", options=OUTPUT_FORMATS)
        
        config_obj = Config()
        if boundary_source == "shapefile":
            boundary_path = st.text_input("Shapefile path:", value="")
        elif boundary_source == "neighborhoods":
            boundary_path = str(config_obj.neighborhoods_shapefile)
            st.caption(f"📁 {boundary_path}")
        else:
            boundary_path = str(config_obj.districts_shapefile)
            st.caption(f"📁 {boundary_path}")
        
        # Auto-generate suffix based on time filter and boundary
        time_suffix = utils.get_time_filter_suffix()
        default_suffix = f"_{time_suffix}_{boundary_source}_boundary_filtered"
        output_suffix = st.text_input("Output suffix:", value=default_suffix)
        
        if st.button("▶️ Run", type="primary", width='stretch'):
            return {
                'input_file': file_options[selected_file],
                'boundary_source': boundary_source,
                'boundary_path': boundary_path,
                'filter_field': filter_field,
                'output_suffix': output_suffix,
                'output_format': output_format
            }
        
        return None
    
    def execute(self, **kwargs) -> Dict[str, Any]:
        """Execute boundary filter"""
        input_file = kwargs['input_file']
        boundary_source = kwargs['boundary_source']
        boundary_path = kwargs.get('boundary_path')
        filter_field = kwargs['filter_field']
        output_suffix = kwargs['output_suffix']
        output_format = kwargs['output_format']
        
        try:
            _logger.info(f"boundary_filter start input={input_file} source={boundary_source}")
            
            # Load input data
            df = pd.read_csv(input_file)
            total_count = len(df)
            
            # Load boundary
            config = Config()
            if boundary_source == "neighborhoods":
                boundary_gdf = gpd.read_file(config.neighborhoods_shapefile)
            elif boundary_source == "districts":
                boundary_gdf = gpd.read_file(config.districts_shapefile)
            else:
                if not boundary_path or not Path(boundary_path).exists():
                    return {"success": False, "error": "Boundary shapefile not found"}
                boundary_gdf = gpd.read_file(boundary_path)
            
            # Determine coordinate columns
            if filter_field == "origin":
                lat_col = next((c for c in ['org_lat', 'origin_lat'] if c in df.columns), None)
                lon_col = next((c for c in ['org_lng', 'org_long', 'origin_lng', 'origin_long'] if c in df.columns), None)
            elif filter_field == "destination":
                lat_col = next((c for c in ['dst_lat', 'dest_lat', 'destination_lat'] if c in df.columns), None)
                lon_col = next((c for c in ['dst_lng', 'dst_long', 'dest_lng', 'dest_long'] if c in df.columns), None)
            else:
                possible_lat = ["org_lat", "dst_lat", "origin_lat", "dest_lat", "latitude", "lat"]
                possible_lon = ["org_lng", "org_long", "dst_lng", "dst_long", "origin_lng", "dest_lng", "longitude", "lon", "lng"]
                lat_col = next((col for col in possible_lat if col in df.columns), None)
                lon_col = next((col for col in possible_lon if col in df.columns), None)
            
            if not lat_col or not lon_col:
                return {"success": False, "error": f"Coordinate columns not found. Available: {list(df.columns)}"}
            
            # Create points
            df_clean = df[[lat_col, lon_col]].dropna()
            if len(df_clean) == 0:
                return {"success": False, "error": "No valid coordinates"}
            
            geometry = [Point(xy) for xy in zip(df_clean[lon_col], df_clean[lat_col])]
            points_gdf = gpd.GeoDataFrame(df_clean, geometry=geometry, crs="EPSG:4326")
            
            if points_gdf.crs != boundary_gdf.crs:
                points_gdf = points_gdf.to_crs(boundary_gdf.crs)
            
            # Spatial join
            joined = gpd.sjoin(points_gdf, boundary_gdf, how='inner', predicate='within')
            filtered_indices = df_clean.index[joined.index]
            filtered_df = df.loc[filtered_indices].copy()
            filtered_count = len(filtered_df)
            
            # Save output
            input_path = Path(input_file)
            if output_format == "csv":
                output_path = input_path.parent / f"{input_path.stem}{output_suffix}.csv"
                filtered_df.to_csv(output_path, index=False)
            else:
                # Save to GIS output directory
                config = Config()
                output_dir = config.gis_output_path / f"{input_path.stem}{output_suffix}"
                output_dir.mkdir(exist_ok=True, parents=True)
                filtered_geometry = [Point(xy) for xy in zip(filtered_df[lon_col], filtered_df[lat_col])]
                filtered_gdf = gpd.GeoDataFrame(filtered_df, geometry=filtered_geometry, crs="EPSG:4326")
                output_path = output_dir / f"{input_path.stem}{output_suffix}.shp"
                filtered_gdf.to_file(output_path)
            
            _logger.info(f"boundary_filter success rows={filtered_count}")
            return {
                "success": True,
                "filtered_count": filtered_count,
                "total_count": total_count,
                "output_path": str(output_path)
            }
            
        except Exception as e:
            _logger.error(f"boundary_filter error: {e}")
            return {"success": False, "error": str(e)}
