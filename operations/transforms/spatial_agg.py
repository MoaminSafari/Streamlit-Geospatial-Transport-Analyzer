"""
Spatial Aggregation Operation - Complete with UI and execution
"""

import streamlit as st
import pandas as pd
import logging
from typing import Dict, Any, Optional
from pathlib import Path
from operations.base import BaseOperation
from operations.config import GRID_SIZES, DEFAULT_GRID_SIZE, ENDPOINT_OPTIONS
from ui_helpers import utils

_logger = logging.getLogger("spatial_agg")


class SpatialAggOperation(BaseOperation):
    """Aggregate data into spatial grid"""
    
    def get_metadata(self) -> Dict[str, str]:
        return {
            'key': 'spatial_agg',
            'title': 'Spatial Aggregation',
            'description': 'Aggregate data into spatial grid',
            'category': 'transforms'
        }
    
    def render_ui(self) -> Optional[Dict[str, Any]]:
        """Render UI and return params if Run clicked"""
        
        aggregated_files = utils.get_aggregated_files()
        if not aggregated_files:
            st.warning("⚠️ Please run an analysis first.")
            return None
        
        file_options = {f.name: str(f) for f in aggregated_files}
        
        selected_file = st.selectbox("Input file:", options=list(file_options.keys()))
        
        col1, col2 = st.columns(2)
        with col1:
            endpoint = st.selectbox("Target field:", 
                                   options=list(ENDPOINT_OPTIONS.keys()),
                                   format_func=lambda x: ENDPOINT_OPTIONS[x])
        with col2:
            grid_size = st.selectbox("Grid size:", 
                                    options=list(GRID_SIZES.keys()),
                                    index=list(GRID_SIZES.keys()).index(DEFAULT_GRID_SIZE))
        
        grid_meters = GRID_SIZES[grid_size]
        # Auto-generate suffix based on time filter
        time_suffix = utils.get_time_filter_suffix()
        default_suffix = f"_{time_suffix}_spatial_{grid_size}_{endpoint}"
        output_suffix = st.text_input("Output suffix:", value=default_suffix)
        
        if st.button("▶️ Run", type="primary", width='stretch'):
            return {
                'input_file': file_options[selected_file],
                'endpoint': endpoint,
                'grid_size_meters': grid_meters,
                'output_suffix': output_suffix
            }
        
        return None
    
    def execute(self, **kwargs) -> Dict[str, Any]:
        """Execute spatial aggregation"""
        input_file = kwargs['input_file']
        endpoint = kwargs['endpoint']
        grid_size_meters = kwargs['grid_size_meters']
        output_suffix = kwargs['output_suffix']
        
        try:
            _logger.info(f"spatial_agg start input={input_file} endpoint={endpoint} grid={grid_size_meters}")
            df = pd.read_csv(input_file)
            
            if endpoint == 'origin':
                lat_col = next((c for c in ['org_lat', 'origin_lat'] if c in df.columns), None)
                lon_col = next((c for c in ['org_lng', 'org_long', 'origin_lng', 'origin_long'] if c in df.columns), None)
            elif endpoint == 'destination':
                lat_col = next((c for c in ['dst_lat', 'dest_lat', 'destination_lat'] if c in df.columns), None)
                lon_col = next((c for c in ['dst_lng', 'dst_long', 'dest_lng', 'dest_long'] if c in df.columns), None)
            else:
                lat_col = next((c for c in ['org_lat', 'dst_lat', 'origin_lat', 'dest_lat', 'latitude', 'lat'] if c in df.columns), None)
                lon_col = next((c for c in ['org_lng', 'org_long', 'dst_lng', 'dst_long', 'origin_lng', 'dest_lng', 'longitude', 'lon', 'lng'] if c in df.columns), None)
            
            if not lat_col or not lon_col:
                return {"success": False, "error": "Coordinate columns not found"}
            
            grid_deg = grid_size_meters / 111000.0
            df['x_bin'] = (df[lon_col] / grid_deg).astype('Int64')
            df['y_bin'] = (df[lat_col] / grid_deg).astype('Int64')
            agg = df.groupby(['x_bin', 'y_bin']).size().reset_index(name='count')
            agg['longitude'] = agg['x_bin'] * grid_deg + grid_deg / 2
            agg['latitude'] = agg['y_bin'] * grid_deg + grid_deg / 2
            
            input_path = Path(input_file)
            output_path = input_path.parent / f"{input_path.stem}{output_suffix}.csv"
            agg[['longitude', 'latitude', 'count']].to_csv(output_path, index=False)
            
            _logger.info(f"spatial_agg success cells={len(agg)}")
            return {
                "success": True,
                "output_path": str(output_path),
                "total_cells": len(agg),
                "total_count": int(agg['count'].sum())
            }
            
        except Exception as e:
            _logger.error(f"spatial_agg error: {e}")
            return {"success": False, "error": str(e)}
