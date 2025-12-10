"""
Spatiotemporal Aggregation Operation - Complete with UI and execution
"""

import streamlit as st
import pandas as pd
import logging
from typing import Dict, Any, Optional
from pathlib import Path
from operations.base import BaseOperation, DataSourceHelper
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
        
        st.markdown("### Configuration")
        selected_file = st.selectbox("Input file:", options=list(file_options.keys()))
        
        # Load file preview for column selection
        try:
            preview_df = pd.read_csv(file_options[selected_file], nrows=5)
            
            # Coordinate column selection
            lat_col, lon_col = DataSourceHelper.render_coordinate_selector(preview_df)
            
            # Time column selection
            st.markdown("**⏰ Select time column:**")
            time_columns = [c for c in preview_df.columns if 'time' in c.lower() or 'date' in c.lower() or 'datetime' in c.lower()]
            if not time_columns:
                time_columns = list(preview_df.columns)
            
            time_col = st.selectbox("Time/datetime column:", options=time_columns)
            
            # Show preview
            with st.expander("📋 Preview first 5 rows"):
                st.dataframe(preview_df)
                
        except Exception as e:
            st.error(f"❌ Error loading file: {e}")
            return None
        
        st.markdown("---")
        
        col1, col2 = st.columns(2)
        with col1:
            grid_size = st.selectbox("Grid size:", 
                                    options=list(GRID_SIZES.keys()),
                                    index=list(GRID_SIZES.keys()).index(DEFAULT_GRID_SIZE))
        with col2:
            time_bin = st.selectbox("Time bin:", 
                                   options=list(TIME_BINS.keys()),
                                   index=list(TIME_BINS.keys()).index(DEFAULT_TIME_BIN))
        
        # Aggregation field selection
        st.markdown("### Aggregation Settings")
        aggregation_fields = DataSourceHelper.render_aggregation_field_selector(preview_df, lat_col, lon_col)
        
        grid_meters = GRID_SIZES[grid_size]
        time_minutes = TIME_BINS[time_bin]
        # Simple suffix without time filter for manual files
        default_suffix = f"_spatiotemporal_{grid_size}_{time_minutes}min"
        output_suffix = st.text_input("Output suffix:", value=default_suffix)
        
        if st.button("▶️ Run", type="primary", width='stretch'):
            return {
                'input_file': file_options[selected_file],
                'manual_lat_col': lat_col,
                'manual_lon_col': lon_col,
                'time_col': time_col,
                'aggregation_fields': aggregation_fields,
                'grid_size_meters': grid_meters,
                'time_bin_minutes': time_minutes,
                'output_suffix': output_suffix
            }
        
        return None
    
    def execute(self, **kwargs) -> Dict[str, Any]:
        """Execute spatiotemporal aggregation"""
        input_file = kwargs['input_file']
        grid_size_meters = kwargs['grid_size_meters']
        time_bin_minutes = kwargs['time_bin_minutes']
        output_suffix = kwargs['output_suffix']
        manual_lat_col = kwargs.get('manual_lat_col')
        manual_lon_col = kwargs.get('manual_lon_col')
        time_col = kwargs['time_col']
        aggregation_fields = kwargs.get('aggregation_fields', [])
        
        try:
            _logger.info(f"spatiotemporal_agg start input={input_file}")
            df = pd.read_csv(input_file)
            
            # Get coordinate columns
            lat_col, lon_col = DataSourceHelper.get_coordinate_columns(
                df, endpoint='all', manual_lat=manual_lat_col, manual_lon=manual_lon_col
            )
            
            if not lat_col or not lon_col:
                return {"success": False, "error": "Coordinate columns not found"}
            
            # Check time column
            if time_col not in df.columns:
                return {"success": False, "error": f"Time column '{time_col}' not found"}
            
            df[time_col] = pd.to_datetime(df[time_col], errors='coerce')
            df = df[df[time_col].notna()].copy()
            
            if len(df) == 0:
                return {"success": False, "error": "No valid time data found"}
            
            # Create spatial grid bins (using camelCase names)
            grid_deg = grid_size_meters / 111000.0
            df['xBin'] = (df[lon_col] / grid_deg).astype('Int64')
            df['yBin'] = (df[lat_col] / grid_deg).astype('Int64')
            
            # Create time bins (using camelCase names)
            minutes = df[time_col].dt.hour * 60 + df[time_col].dt.minute
            df['timeBinMinutes'] = (minutes // time_bin_minutes) * time_bin_minutes + time_bin_minutes
            df['timeBinDatetime'] = pd.to_datetime(df[time_col].dt.date.astype(str)) + pd.to_timedelta(df['timeBinMinutes'], unit='m')
            
            # Determine aggregation strategy
            if aggregation_fields:
                # Aggregate selected fields
                available_agg_fields = [f for f in aggregation_fields if f in df.columns]
                if not available_agg_fields:
                    _logger.warning("Selected aggregation fields not found, using count")
                    df['count'] = 1
                    agg = df.groupby(['xBin', 'yBin', 'timeBinDatetime'])['count'].sum().reset_index()
                else:
                    agg_dict = {field: 'sum' for field in available_agg_fields}
                    agg = df.groupby(['xBin', 'yBin', 'timeBinDatetime']).agg(agg_dict).reset_index()
            else:
                # Just count records
                df['count'] = 1
                agg = df.groupby(['xBin', 'yBin', 'timeBinDatetime'])['count'].sum().reset_index()
            
            # Add centroid coordinates
            agg['longitude'] = agg['xBin'] * grid_deg + grid_deg / 2
            agg['latitude'] = agg['yBin'] * grid_deg + grid_deg / 2
            
            # Reorder columns
            cols = ['longitude', 'latitude', 'timeBinDatetime'] + [c for c in agg.columns if c not in ['longitude', 'latitude', 'timeBinDatetime', 'xBin', 'yBin']]
            agg = agg[cols]
            
            input_path = Path(input_file)
            output_path = input_path.parent / f"{input_path.stem}{output_suffix}.csv"
            agg.to_csv(output_path, index=False)
            
            _logger.info(f"spatiotemporal_agg success rows={len(agg)}")
            return {"success": True, "output_path": str(output_path), "rows": len(agg)}
            
        except Exception as e:
            _logger.error(f"spatiotemporal_agg error: {e}")
            return {"success": False, "error": str(e)}
