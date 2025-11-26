"""
Origin-Destination Matrix Operation - Complete with UI and execution
"""

import streamlit as st
import pandas as pd
import geopandas as gpd
from shapely.geometry import Point
import logging
from typing import Dict, Any, Optional
from pathlib import Path
from operations.base import BaseOperation
from operations.config import BOUNDARY_SOURCES
from ui_helpers import utils
from config import Config

_logger = logging.getLogger("od_matrix")


class ODMatrixOperation(BaseOperation):
    """Create origin-destination matrix"""
    
    def get_metadata(self) -> Dict[str, str]:
        return {
            'key': 'od_matrix',
            'title': 'OD Matrix',
            'description': 'Create origin-destination matrix',
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
        
        boundary_options = list(BOUNDARY_SOURCES.keys()) + ["custom"]
        boundary_labels = {**BOUNDARY_SOURCES, "custom": "Custom Shapefile"}
        
        boundary_source = st.selectbox(
            "Boundary zones:",
            options=boundary_options,
            format_func=lambda x: boundary_labels[x],
            help="Zone definition for OD matrix"
        )
        
        boundary_path = None
        if boundary_source == "custom":
            boundary_path = st.text_input("Custom shapefile path:")
        
        # Auto-generate suffix based on time filter
        time_suffix = utils.get_time_filter_suffix()
        default_suffix = f"_{time_suffix}_{boundary_source}_od_matrix"
        output_suffix = st.text_input("Output suffix:", value=default_suffix)
        
        if st.button("▶️ Run", type="primary", width='stretch'):
            return {
                'input_file': file_options[selected_file],
                'boundary_source': boundary_source,
                'boundary_path': boundary_path,
                'output_suffix': output_suffix
            }
        
        return None
    
    def execute(self, **kwargs) -> Dict[str, Any]:
        """Execute OD matrix creation"""
        input_file = kwargs['input_file']
        boundary_source = kwargs['boundary_source']
        boundary_path = kwargs.get('boundary_path')
        output_suffix = kwargs['output_suffix']
        
        try:
            _logger.info(f"od_matrix start input={input_file} boundary={boundary_source}")
            df = pd.read_csv(input_file)
            
            # Find coordinate columns
            org_lat = next((c for c in ['org_lat', 'origin_lat'] if c in df.columns), None)
            org_lon = next((c for c in ['org_lng', 'org_long', 'origin_lng', 'origin_long'] if c in df.columns), None)
            dst_lat = next((c for c in ['dst_lat', 'dest_lat', 'destination_lat'] if c in df.columns), None)
            dst_lon = next((c for c in ['dst_lng', 'dst_long', 'dest_lng', 'dest_long'] if c in df.columns), None)
            
            if not all([org_lat, org_lon, dst_lat, dst_lon]):
                return {"success": False, "error": "Origin/destination columns incomplete"}
            
            config = Config()
            if boundary_source == 'neighborhoods':
                boundary = gpd.read_file(config.neighborhoods_shapefile)
                zone_field = 'CODE' if 'CODE' in boundary.columns else boundary.columns[0]
            elif boundary_source == 'districts':
                boundary = gpd.read_file(config.districts_shapefile)
                zone_field = boundary.columns[0]
            elif boundary_source == 'traffic_zones':
                boundary = gpd.read_file(config.traffic_zones_shapefile)
                zone_field = 'ZONE' if 'ZONE' in boundary.columns else ('CODE' if 'CODE' in boundary.columns else boundary.columns[0])
            else:
                if not boundary_path or not Path(boundary_path).exists():
                    return {"success": False, "error": "Invalid Shapefile path"}
                boundary = gpd.read_file(boundary_path)
                zone_field = boundary.columns[0]
            
            # Create GeoDataFrames
            org_gdf = gpd.GeoDataFrame(df, geometry=[Point(xy) for xy in zip(df[org_lon], df[org_lat])], crs='EPSG:4326')
            dst_gdf = gpd.GeoDataFrame(df, geometry=[Point(xy) for xy in zip(df[dst_lon], df[dst_lat])], crs='EPSG:4326')
            
            if org_gdf.crs != boundary.crs:
                org_gdf = org_gdf.to_crs(boundary.crs)
                dst_gdf = dst_gdf.to_crs(boundary.crs)
            
            # Spatial joins
            org_join = gpd.sjoin(org_gdf, boundary[[zone_field, 'geometry']], how='left', predicate='within').rename(columns={zone_field: 'origin_zone'})
            dst_join = gpd.sjoin(dst_gdf, boundary[[zone_field, 'geometry']], how='left', predicate='within').rename(columns={zone_field: 'dest_zone'})
            
            zones_df = pd.DataFrame({
                'origin_zone': org_join['origin_zone'].values,
                'dest_zone': dst_join['dest_zone'].values
            })
            
            od = zones_df.groupby(['origin_zone', 'dest_zone']).size().reset_index(name='count')
            
            input_path = Path(input_file)
            output_path = input_path.parent / f"{input_path.stem}{output_suffix}.csv"
            od.to_csv(output_path, index=False)
            
            _logger.info(f"od_matrix success rows={len(od)}")
            return {"success": True, "output_path": str(output_path), "rows": len(od)}
            
        except Exception as e:
            _logger.error(f"od_matrix error: {e}")
            return {"success": False, "error": str(e)}
