"""
Time Slice Operation - Complete with UI and execution
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

_logger = logging.getLogger("time_slice")


class TimeSliceOperation(BaseOperation):
    """Extract specific time points"""
    
    def get_metadata(self) -> Dict[str, str]:
        return {
            'key': 'time_slice',
            'title': 'Time Slice',
            'description': 'Extract specific time points',
            'category': 'transforms'
        }
    
    def render_ui(self) -> Optional[Dict[str, Any]]:
        """Render UI and return params if Run clicked"""
        
        aggregated_files = utils.get_aggregated_files()
        if not aggregated_files:
            st.warning("⚠️ Please run an analysis first to generate aggregated files.")
            return None
        
        file_options = {f.name: str(f) for f in aggregated_files}
        
        selected_file = st.selectbox("Input file:", options=list(file_options.keys()))
        times = st.text_input("Time points (HH:MM, comma separated):", value="08:00,12:30,18:00")
        
        col1, col2 = st.columns(2)
        with col1:
            # Auto-generate suffix based on time filter
            time_suffix = utils.get_time_filter_suffix()
            default_suffix = f"_{time_suffix}_times_selected"
            output_suffix = st.text_input("Output suffix:", value=default_suffix)
        with col2:
            output_format = st.selectbox("Output format:", options=OUTPUT_FORMATS)
        
        if st.button("▶️ Run", type="primary", width='stretch'):
            time_list = [t.strip() for t in times.split(",") if t.strip()]
            return {
                'input_file': file_options[selected_file],
                'times': time_list,
                'output_suffix': output_suffix,
                'output_format': output_format
            }
        
        return None
    
    def execute(self, **kwargs) -> Dict[str, Any]:
        """Execute time slice"""
        input_file = kwargs['input_file']
        times = kwargs['times']
        output_suffix = kwargs['output_suffix']
        output_format = kwargs['output_format']
        
        try:
            _logger.info(f"time_slice start input={input_file} times={times}")
            df = pd.read_csv(input_file)
            
            if 'TIME' not in df.columns:
                if 'time_bin_datetime' in df.columns:
                    df['time_bin_datetime'] = pd.to_datetime(df['time_bin_datetime'], errors='coerce')
                    df = df[df['time_bin_datetime'].notna()]
                    df['TIME'] = df['time_bin_datetime'].dt.strftime('%H:%M')
                else:
                    return {"success": False, "error": "Time column not found (TIME/time_bin_datetime)"}
            
            filtered_df = df[df['TIME'].isin(times)].copy()
            input_path = Path(input_file)
            
            if output_format == "csv":
                output_path = input_path.parent / f"{input_path.stem}{output_suffix}.csv"
                filtered_df.to_csv(output_path, index=False)
                _logger.info(f"time_slice success csv rows={len(filtered_df)}")
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
                _logger.info(f"time_slice success shp rows={len(gdf)}")
                return {
                    "success": True,
                    "output_path": str(shp_path),
                    "filtered_count": len(gdf),
                    "total_count": len(df)
                }
                
        except Exception as e:
            _logger.error(f"time_slice error: {e}")
            return {"success": False, "error": str(e)}
