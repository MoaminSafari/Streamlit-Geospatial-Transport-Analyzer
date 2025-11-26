"""
Spatiotemporal Aggregation Operation - Complete with UI and execution
"""

import streamlit as st
import pandas as pd
import logging
from typing import Dict, Any, Optional
from pathlib import Path
from operations.base import BaseOperation
from operations.config import GRID_SIZES, DEFAULT_GRID_SIZE, TIME_BINS, DEFAULT_TIME_BIN, ENDPOINT_OPTIONS
from ui_helpers import utils

_logger = logging.getLogger("spatiotemporal_agg")


class SpatiotemporalAggOperation(BaseOperation):
    """Aggregate by space and time"""
    
    def get_metadata(self) -> Dict[str, str]:
        return {
            'key': 'spatiotemporal_agg',
            'title': 'Spatiotemporal Aggregation',
            'description': 'Aggregate by space and time',
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
                                   format_func=lambda x: ENDPOINT_OPTIONS[x],
                                   index=0)  # Default to origin
        with col2:
            grid_size = st.selectbox("Grid size:", 
                                    options=list(GRID_SIZES.keys()),
                                    index=list(GRID_SIZES.keys()).index(DEFAULT_GRID_SIZE))
        
        time_bin = st.selectbox("Time bin:", 
                               options=list(TIME_BINS.keys()),
                               index=list(TIME_BINS.keys()).index(DEFAULT_TIME_BIN))
        
        grid_meters = GRID_SIZES[grid_size]
        time_minutes = TIME_BINS[time_bin]
        # Auto-generate suffix based on time filter
        time_suffix = utils.get_time_filter_suffix()
        default_suffix = f"_{time_suffix}_spatiotemporal_{grid_size}_{time_minutes}min_{endpoint}"
        output_suffix = st.text_input("Output suffix:", value=default_suffix)
        
        if st.button("▶️ Run", type="primary", width='stretch'):
            return {
                'input_file': file_options[selected_file],
                'endpoint': endpoint,
                'grid_size_meters': grid_meters,
                'time_bin_minutes': time_minutes,
                'output_suffix': output_suffix
            }
        
        return None
    
    def execute(self, **kwargs) -> Dict[str, Any]:
        """Execute spatiotemporal aggregation"""
        input_file = kwargs['input_file']
        endpoint = kwargs['endpoint']
        grid_size_meters = kwargs['grid_size_meters']
        time_bin_minutes = kwargs['time_bin_minutes']
        output_suffix = kwargs['output_suffix']
        
        try:
            _logger.info(f"spatiotemporal_agg start input={input_file} endpoint={endpoint}")
            df = pd.read_csv(input_file)
            
            time_col = 'org_time' if endpoint == 'origin' else 'dst_time'
            if time_col not in df.columns:
                return {"success": False, "error": f"Time column '{time_col}' not found"}
            
            df[time_col] = pd.to_datetime(df[time_col], errors='coerce')
            df = df[df[time_col].notna()].copy()
            
            if endpoint == 'origin':
                lat_col = next((c for c in ['org_lat', 'origin_lat'] if c in df.columns), None)
                lon_col = next((c for c in ['org_lng', 'org_long', 'origin_lng', 'origin_long'] if c in df.columns), None)
            else:
                lat_col = next((c for c in ['dst_lat', 'dest_lat', 'destination_lat'] if c in df.columns), None)
                lon_col = next((c for c in ['dst_lng', 'dst_long', 'dest_lng', 'dest_long'] if c in df.columns), None)
            
            if not lat_col or not lon_col:
                return {"success": False, "error": "Coordinate columns not found"}
            
            grid_deg = grid_size_meters / 111000.0
            df['x_bin'] = (df[lon_col] / grid_deg).astype('Int64')
            df['y_bin'] = (df[lat_col] / grid_deg).astype('Int64')
            
            minutes = df[time_col].dt.hour * 60 + df[time_col].dt.minute
            df['time_bin_minutes'] = (minutes // time_bin_minutes) * time_bin_minutes + time_bin_minutes
            df['time_bin_datetime'] = pd.to_datetime(df[time_col].dt.date.astype(str)) + pd.to_timedelta(df['time_bin_minutes'], unit='m')
            
            agg = df.groupby(['x_bin', 'y_bin', 'time_bin_datetime']).size().reset_index(name='count')
            agg['longitude'] = agg['x_bin'] * grid_deg + grid_deg / 2
            agg['latitude'] = agg['y_bin'] * grid_deg + grid_deg / 2
            
            input_path = Path(input_file)
            output_path = input_path.parent / f"{input_path.stem}{output_suffix}.csv"
            agg[['longitude', 'latitude', 'time_bin_datetime', 'count']].to_csv(output_path, index=False)
            
            _logger.info(f"spatiotemporal_agg success rows={len(agg)}")
            return {"success": True, "output_path": str(output_path), "rows": len(agg)}
            
        except Exception as e:
            _logger.error(f"spatiotemporal_agg error: {e}")
            return {"success": False, "error": str(e)}
