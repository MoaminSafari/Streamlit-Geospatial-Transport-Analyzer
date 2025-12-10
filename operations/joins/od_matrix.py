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
from operations.base import BaseOperation, DataSourceHelper
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
        
        # Load file preview for column selection
        try:
            preview_df = pd.read_csv(file_options[selected_file], nrows=5)
            
            # Origin coordinate selection
            st.markdown("**📍 Origin coordinates:**")
            col1, col2 = st.columns(2)
            with col1:
                origin_lat_default = next((c for c in preview_df.columns if c in ['org_lat', 'origin_lat', 'originLatitude'] or ('origin' in c.lower() and 'lat' in c.lower())), None)
                if not origin_lat_default:
                    origin_lat_default = preview_df.columns[0] if len(preview_df.columns) > 0 else None
                
                origin_lat = st.selectbox(
                    "Origin latitude:",
                    options=list(preview_df.columns),
                    index=list(preview_df.columns).index(origin_lat_default) if origin_lat_default in preview_df.columns else 0
                )
            with col2:
                origin_lon_default = next((c for c in preview_df.columns if c in ['org_lng', 'org_long', 'origin_lng', 'originLongitude'] or ('origin' in c.lower() and ('lon' in c.lower() or 'lng' in c.lower()))), None)
                if not origin_lon_default:
                    origin_lon_default = preview_df.columns[1] if len(preview_df.columns) > 1 else None
                
                origin_lon = st.selectbox(
                    "Origin longitude:",
                    options=list(preview_df.columns),
                    index=list(preview_df.columns).index(origin_lon_default) if origin_lon_default in preview_df.columns else (1 if len(preview_df.columns) > 1 else 0)
                )
            
            # Destination coordinate selection
            st.markdown("**📍 Destination coordinates:**")
            col3, col4 = st.columns(2)
            with col3:
                dest_lat_default = next((c for c in preview_df.columns if c in ['dst_lat', 'dest_lat', 'destination_lat', 'destinationLatitude'] or ('dest' in c.lower() and 'lat' in c.lower())), None)
                if not dest_lat_default:
                    dest_lat_default = preview_df.columns[2] if len(preview_df.columns) > 2 else None
                
                dest_lat = st.selectbox(
                    "Destination latitude:",
                    options=list(preview_df.columns),
                    index=list(preview_df.columns).index(dest_lat_default) if dest_lat_default in preview_df.columns else (2 if len(preview_df.columns) > 2 else 0)
                )
            with col4:
                dest_lon_default = next((c for c in preview_df.columns if c in ['dst_lng', 'dst_long', 'dest_lng', 'destinationLongitude'] or ('dest' in c.lower() and ('lon' in c.lower() or 'lng' in c.lower()))), None)
                if not dest_lon_default:
                    dest_lon_default = preview_df.columns[3] if len(preview_df.columns) > 3 else None
                
                dest_lon = st.selectbox(
                    "Destination longitude:",
                    options=list(preview_df.columns),
                    index=list(preview_df.columns).index(dest_lon_default) if dest_lon_default in preview_df.columns else (3 if len(preview_df.columns) > 3 else 0)
                )
            
            # Show preview
            with st.expander("📋 Preview first 5 rows"):
                st.dataframe(preview_df)
                
        except Exception as e:
            st.error(f"❌ Error loading file: {e}")
            return None
        
        st.markdown("---")
        
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
        
        # Simple suffix without time filter for manual files
        default_suffix = f"_{boundary_source}_od_matrix"
        output_suffix = st.text_input("Output suffix:", value=default_suffix)
        
        if st.button("▶️ Run", type="primary", width='stretch'):
            return {
                'input_file': file_options[selected_file],
                'origin_lat': origin_lat,
                'origin_lon': origin_lon,
                'dest_lat': dest_lat,
                'dest_lon': dest_lon,
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
        
        # Get manual column selections
        origin_lat = kwargs.get('origin_lat')
        origin_lon = kwargs.get('origin_lon')
        dest_lat = kwargs.get('dest_lat')
        dest_lon = kwargs.get('dest_lon')
        
        try:
            _logger.info(f"od_matrix start input={input_file} boundary={boundary_source}")
            df = pd.read_csv(input_file)
            
            # Use manual selections or auto-detect
            if origin_lat and origin_lon and dest_lat and dest_lon:
                org_lat, org_lon, dst_lat, dst_lon = origin_lat, origin_lon, dest_lat, dest_lon
                _logger.info(f"Using manual columns: org=({org_lat},{org_lon}), dst=({dst_lat},{dst_lon})")
            else:
                # Auto-detect (fallback)
                org_lat = next((c for c in ['org_lat', 'origin_lat'] if c in df.columns), None)
                org_lon = next((c for c in ['org_lng', 'org_long', 'origin_lng', 'origin_long'] if c in df.columns), None)
                dst_lat = next((c for c in ['dst_lat', 'dest_lat', 'destination_lat'] if c in df.columns), None)
                dst_lon = next((c for c in ['dst_lng', 'dst_long', 'dest_lng', 'dest_long'] if c in df.columns), None)
            
            if not all([org_lat, org_lon, dst_lat, dst_lon]):
                error_msg = f"Origin/destination columns incomplete. Available: {', '.join(df.columns.tolist())}"
                _logger.error(error_msg)
                return {"success": False, "error": error_msg}
            
            config = Config()
            if boundary_source == 'custom':
                if not boundary_path or not Path(boundary_path).exists():
                    return {"success": False, "error": "Invalid Shapefile path"}
                boundary = gpd.read_file(boundary_path)
                zone_field = boundary.columns[0]
            else:
                # Use dynamic shapefile path discovery
                from operations.config import get_default_field
                shp_path = config.get_shapefile_path(boundary_source)
                if not shp_path.exists():
                    return {"success": False, "error": f"Shapefile not found: {shp_path}"}
                boundary = gpd.read_file(shp_path)
                zone_field = get_default_field(boundary_source)
            
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
