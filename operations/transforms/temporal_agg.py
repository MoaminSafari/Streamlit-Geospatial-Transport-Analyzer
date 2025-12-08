"""
Temporal Aggregation Operation - Complete with UI and execution
"""

import streamlit as st
import pandas as pd
import logging
from typing import Dict, Any, Optional
from pathlib import Path
from operations.base import BaseOperation
from operations.config import TIME_BINS, DEFAULT_TIME_BIN, ENDPOINT_OPTIONS
from ui_helpers import utils

_logger = logging.getLogger("temporal_agg")


class TemporalAggOperation(BaseOperation):
    """Aggregate data into temporal bins"""
    
    def get_metadata(self) -> Dict[str, str]:
        return {
            'key': 'temporal_agg',
            'title': 'Temporal Aggregation',
            'description': 'Aggregate data into temporal bins',
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
            time_bin = st.selectbox("Time bin:", 
                                   options=list(TIME_BINS.keys()),
                                   index=list(TIME_BINS.keys()).index(DEFAULT_TIME_BIN))
        
        time_minutes = TIME_BINS[time_bin]
        # Auto-generate suffix based on time filter
        time_suffix = utils.get_time_filter_suffix()
        default_suffix = f"_{time_suffix}_temporal_{time_minutes}min_{endpoint}"
        output_suffix = st.text_input("Output suffix:", value=default_suffix)
        
        if st.button("▶️ Run", type="primary", width='stretch'):
            return {
                'input_file': file_options[selected_file],
                'endpoint': endpoint,
                'time_bin_minutes': time_minutes,
                'output_suffix': output_suffix
            }
        
        return None
    
    def execute(self, **kwargs) -> Dict[str, Any]:
        """Execute temporal aggregation"""
        input_file = kwargs['input_file']
        endpoint = kwargs['endpoint']
        time_bin_minutes = kwargs['time_bin_minutes']
        output_suffix = kwargs['output_suffix']
        
        try:
            _logger.info(f"temporal_agg start input={input_file} endpoint={endpoint} time_bin={time_bin_minutes}")
            df = pd.read_csv(input_file)
            
            # Determine time column based on endpoint
            if endpoint == 'origin':
                time_col = 'org_time'
            elif endpoint == 'destination':
                time_col = 'dst_time'
            else:  # all - use both origin and destination
                # Process both endpoints separately and combine
                if 'org_time' not in df.columns or 'dst_time' not in df.columns:
                    return {"success": False, "error": "Time columns not found for both endpoints"}
                
                # Process origin
                df_org = df[['org_time']].copy()
                df_org.rename(columns={'org_time': 'time'}, inplace=True)
                df_org['endpoint_type'] = 'origin'
                
                # Process destination
                df_dst = df[['dst_time']].copy()
                df_dst.rename(columns={'dst_time': 'time'}, inplace=True)
                df_dst['endpoint_type'] = 'destination'
                
                # Combine
                df = pd.concat([df_org, df_dst], ignore_index=True)
                time_col = 'time'
            
            # Check if time column exists
            if time_col not in df.columns:
                return {"success": False, "error": f"Time column '{time_col}' not found"}
            
            # Convert to datetime
            df[time_col] = pd.to_datetime(df[time_col], errors='coerce')
            df = df[df[time_col].notna()].copy()
            
            if len(df) == 0:
                return {"success": False, "error": "No valid time data found"}
            
            # Create time bins
            minutes = df[time_col].dt.hour * 60 + df[time_col].dt.minute
            df['time_bin_minutes'] = (minutes // time_bin_minutes) * time_bin_minutes + time_bin_minutes
            df['time_bin_datetime'] = pd.to_datetime(df[time_col].dt.date.astype(str)) + pd.to_timedelta(df['time_bin_minutes'], unit='m')
            
            # Aggregate by time bin
            if endpoint == 'all':
                # Group by time bin and endpoint type
                agg = df.groupby(['time_bin_datetime', 'endpoint_type']).size().reset_index(name='count')
                # Pivot to have separate columns for origin and destination
                agg = agg.pivot(index='time_bin_datetime', columns='endpoint_type', values='count').reset_index()
                agg = agg.fillna(0).astype({'origin': int, 'destination': int})
                agg['total'] = agg['origin'] + agg['destination']
                output_columns = ['time_bin_datetime', 'origin', 'destination', 'total']
            else:
                # Simple aggregation by time bin
                agg = df.groupby(['time_bin_datetime']).size().reset_index(name='count')
                output_columns = ['time_bin_datetime', 'count']
            
            # Save output
            input_path = Path(input_file)
            output_path = input_path.parent / f"{input_path.stem}{output_suffix}.csv"
            agg[output_columns].to_csv(output_path, index=False)
            
            _logger.info(f"temporal_agg success time_bins={len(agg)}")
            return {
                "success": True,
                "output_path": str(output_path),
                "total_bins": len(agg),
                "total_count": int(agg['count'].sum()) if endpoint != 'all' else int(agg['total'].sum())
            }
            
        except Exception as e:
            _logger.error(f"temporal_agg error: {e}")
            return {"success": False, "error": str(e)}
