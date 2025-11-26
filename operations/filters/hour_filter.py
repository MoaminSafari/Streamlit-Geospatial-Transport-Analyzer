"""
Hour Filter Operation - Complete with UI and execution
"""

import streamlit as st
import pandas as pd
import geopandas as gpd
import logging
from typing import Dict, Any, Optional
from pathlib import Path
from operations.base import BaseOperation
from operations.config import OUTPUT_FORMATS
from ui_helpers import utils
from config import Config

_logger = logging.getLogger("hour_filter")


class HourFilterOperation(BaseOperation):
    """Select specific hours from data"""
    
    def get_metadata(self) -> Dict[str, str]:
        return {
            'key': 'hour_filter',
            'title': 'Hour Filter',
            'description': 'Select specific hours from data',
            'category': 'filters'
        }
    
    def render_ui(self) -> Optional[Dict[str, Any]]:
        """Render UI and return params if Run clicked"""
        
        aggregated_files = utils.get_aggregated_files()
        if not aggregated_files:
            st.warning("⚠️ Please run an analysis first to generate aggregated files.")
            return None
        
        file_options = {f.name: str(f) for f in aggregated_files}
        
        selected_file = st.selectbox("Input file:", options=list(file_options.keys()))
        
        col1, col2 = st.columns(2)
        with col1:
            hour_start = st.number_input("Start hour:", min_value=0, max_value=23, value=8, step=1)
        with col2:
            hour_end = st.number_input("End hour:", min_value=0, max_value=23, value=20, step=1)
        
        col3, col4 = st.columns(2)
        with col3:
            # Auto-generate suffix based on time filter
            time_suffix = utils.get_time_filter_suffix()
            default_suffix = f"_{time_suffix}_hour{hour_start}to{hour_end}"
            output_suffix = st.text_input("Output suffix:", value=default_suffix)
        with col4:
            output_format = st.selectbox("Output format:", options=OUTPUT_FORMATS)
        
        if st.button("▶️ Run", type="primary", width='stretch'):
            return {
                'input_file': file_options[selected_file],
                'hour_start': int(hour_start),
                'hour_end': int(hour_end),
                'output_suffix': output_suffix,
                'output_format': output_format
            }
        
        return None
    
    def execute(self, **kwargs) -> Dict[str, Any]:
        """Execute hour filter"""
        input_file = kwargs['input_file']
        hour_start = kwargs['hour_start']
        hour_end = kwargs['hour_end']
        output_suffix = kwargs['output_suffix']
        output_format = kwargs['output_format']
        
        try:
            _logger.info(f"hour_filter start input={input_file} {hour_start}-{hour_end}")
            df = pd.read_csv(input_file)
            
            if 'time_bin_datetime' in df.columns:
                df['time_bin_datetime'] = pd.to_datetime(df['time_bin_datetime'], errors='coerce')
                df = df[df['time_bin_datetime'].notna()]
                df['hour'] = df['time_bin_datetime'].dt.hour
                filtered_df = df[(df['hour'] >= hour_start) & (df['hour'] <= hour_end)].copy()
            elif 'TIME' in df.columns:
                df['hour'] = pd.to_datetime(df['TIME'], format='%H:%M', errors='coerce').dt.hour
                filtered_df = df[(df['hour'] >= hour_start) & (df['hour'] <= hour_end)].copy()
            else:
                return {"success": False, "error": "Time column not found (time_bin_datetime/TIME)"}
            
            input_path = Path(input_file)
            if output_format == "csv":
                output_path = input_path.parent / f"{input_path.stem}{output_suffix}.csv"
                filtered_df.to_csv(output_path, index=False)
                _logger.info(f"hour_filter success csv rows={len(filtered_df)}")
                return {
                    "success": True,
                    "output_path": str(output_path),
                    "filtered_count": len(filtered_df),
                    "total_count": len(df)
                }
            else:
                if 'CODE' not in filtered_df.columns:
                    return {"success": False, "error": "CODE column required for Shapefile"}
                
                config = Config()
                neighborhoods = gpd.read_file(config.neighborhoods_shapefile)
                gdf = neighborhoods[['CODE', 'geometry']].merge(filtered_df, on='CODE', how='inner')
                # Save to GIS output directory
                output_dir = config.gis_output_path / f"{input_path.stem}{output_suffix}"
                output_dir.mkdir(exist_ok=True, parents=True)
                shp_path = output_dir / f"{input_path.stem}{output_suffix}.shp"
                gdf.to_file(shp_path)
                _logger.info(f"hour_filter success shp rows={len(gdf)}")
                return {
                    "success": True,
                    "output_path": str(shp_path),
                    "filtered_count": len(gdf),
                    "total_count": len(df)
                }
                
        except Exception as e:
            _logger.error(f"hour_filter error: {e}")
            return {"success": False, "error": str(e)}
