"""
Spatial Aggregation Operation - Complete with UI and execution
"""

import streamlit as st
import pandas as pd
import logging
from typing import Dict, Any, Optional
from pathlib import Path
from operations.base import BaseOperation, DataSourceHelper
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
        
        st.markdown("### Configuration")
        selected_file = st.selectbox("Input file:", options=list(file_options.keys()))
        
        # Load file preview for column selection
        try:
            preview_df = pd.read_csv(file_options[selected_file], nrows=5)
            
            # Coordinate column selection
            lat_col, lon_col = DataSourceHelper.render_coordinate_selector(preview_df)
            
            # Show preview
            with st.expander("📋 Preview first 5 rows"):
                st.dataframe(preview_df)
                
        except Exception as e:
            st.error(f"❌ Error loading file: {e}")
            return None
        
        st.markdown("---")
        
        grid_size = st.selectbox("Grid size:", 
                                options=list(GRID_SIZES.keys()),
                                index=list(GRID_SIZES.keys()).index(DEFAULT_GRID_SIZE))
        
        # Aggregation field selection
        st.markdown("### Aggregation Settings")
        aggregation_fields = DataSourceHelper.render_aggregation_field_selector(preview_df, lat_col, lon_col)
        
        grid_meters = GRID_SIZES[grid_size]
        # Simple suffix without time filter for manual files
        default_suffix = f"_spatial_{grid_size}"
        output_suffix = st.text_input("Output suffix:", value=default_suffix)
        
        if st.button("▶️ Run", type="primary", width='stretch'):
            return {
                'input_file': file_options[selected_file],
                'manual_lat_col': lat_col,
                'manual_lon_col': lon_col,
                'aggregation_fields': aggregation_fields,
                'grid_size_meters': grid_meters,
                'output_suffix': output_suffix
            }
        
        return None
    
    def execute(self, **kwargs) -> Dict[str, Any]:
        """Execute spatial aggregation"""
        input_file = kwargs['input_file']
        grid_size_meters = kwargs['grid_size_meters']
        output_suffix = kwargs['output_suffix']
        manual_lat_col = kwargs.get('manual_lat_col')
        manual_lon_col = kwargs.get('manual_lon_col')
        aggregation_fields = kwargs.get('aggregation_fields', [])
        
        try:
            _logger.info(f"spatial_agg start input={input_file} grid={grid_size_meters}")
            df = pd.read_csv(input_file)
            
            # Use manual column selection
            lat_col, lon_col = DataSourceHelper.get_coordinate_columns(
                df, endpoint='all', manual_lat=manual_lat_col, manual_lon=manual_lon_col
            )
            
            if not lat_col or not lon_col:
                error_msg = f"Coordinate columns not found. Available: {', '.join(df.columns.tolist())}"
                _logger.error(error_msg)
                return {"success": False, "error": error_msg}
            
            _logger.info(f"Using coordinates: lat={lat_col}, lon={lon_col}")
            
            # Create grid bins (using camelCase names)
            grid_deg = grid_size_meters / 111000.0
            df['xBin'] = (df[lon_col] / grid_deg).astype('Int64')
            df['yBin'] = (df[lat_col] / grid_deg).astype('Int64')
            
            # Determine aggregation strategy
            if aggregation_fields:
                # Aggregate selected fields
                available_agg_fields = [f for f in aggregation_fields if f in df.columns]
                if not available_agg_fields:
                    _logger.warning("Selected aggregation fields not found, using count")
                    df['count'] = 1
                    available_agg_fields = ['count']
                
                agg_dict = {field: 'sum' for field in available_agg_fields}
                agg = df.groupby(['xBin', 'yBin']).agg(agg_dict).reset_index()
            else:
                # Just count records
                df['count'] = 1
                agg = df.groupby(['xBin', 'yBin'])['count'].sum().reset_index()
            
            # Add centroid coordinates
            agg['longitude'] = agg['xBin'] * grid_deg + grid_deg / 2
            agg['latitude'] = agg['yBin'] * grid_deg + grid_deg / 2
            
            # Reorder columns
            cols = ['longitude', 'latitude'] + [c for c in agg.columns if c not in ['longitude', 'latitude', 'xBin', 'yBin']]
            agg = agg[cols]
            
            input_path = Path(input_file)
            output_path = input_path.parent / f"{input_path.stem}{output_suffix}.csv"
            agg.to_csv(output_path, index=False)
            
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
