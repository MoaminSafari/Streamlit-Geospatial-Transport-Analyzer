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
        
        st.markdown("### Configuration")
        selected_file = st.selectbox("Input file:", options=list(file_options.keys()))
        
        # Load file preview for column selection
        try:
            preview_df = pd.read_csv(file_options[selected_file], nrows=5)
            
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
        
        time_bin = st.selectbox("Time bin:", 
                               options=list(TIME_BINS.keys()),
                               index=list(TIME_BINS.keys()).index(DEFAULT_TIME_BIN))
        
        # Aggregation field selection (optional for temporal)
        st.markdown("### Aggregation Settings")
        st.info("ℹ️ Will count records per time bin. You can optionally select numeric fields to sum.")
        
        numeric_cols = preview_df.select_dtypes(include=['number']).columns.tolist()
        exclude_patterns = ['id', 'index', 'objectid', 'fid']
        filtered_numeric_cols = [col for col in numeric_cols if col.lower() not in exclude_patterns]
        
        aggregation_fields = []
        if filtered_numeric_cols:
            aggregation_fields = st.multiselect(
                "Fields to aggregate (sum):",
                options=filtered_numeric_cols,
                default=[],
                help="Optional: Select numeric fields to sum. If none, will just count records."
            )
        
        time_minutes = TIME_BINS[time_bin]
        # Simple suffix without time filter for manual files
        default_suffix = f"_temporal_{time_minutes}min"
        output_suffix = st.text_input("Output suffix:", value=default_suffix)
        
        if st.button("▶️ Run", type="primary", width='stretch'):
            return {
                'input_file': file_options[selected_file],
                'time_col': time_col,
                'time_bin_minutes': time_minutes,
                'aggregation_fields': aggregation_fields,
                'output_suffix': output_suffix
            }
        
        return None
    
    def execute(self, **kwargs) -> Dict[str, Any]:
        """Execute temporal aggregation"""
        input_file = kwargs['input_file']
        time_col = kwargs['time_col']
        time_bin_minutes = kwargs['time_bin_minutes']
        output_suffix = kwargs['output_suffix']
        aggregation_fields = kwargs.get('aggregation_fields', [])
        
        try:
            _logger.info(f"temporal_agg start input={input_file} time_col={time_col} time_bin={time_bin_minutes}")
            df = pd.read_csv(input_file)
            
            # Check if time column exists
            if time_col not in df.columns:
                return {"success": False, "error": f"Time column '{time_col}' not found"}
            
            # Convert to datetime
            df[time_col] = pd.to_datetime(df[time_col], errors='coerce')
            df = df[df[time_col].notna()].copy()
            
            if len(df) == 0:
                return {"success": False, "error": "No valid time data found"}
            
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
                    agg = df.groupby(['timeBinDatetime'])['count'].sum().reset_index()
                else:
                    agg_dict = {field: 'sum' for field in available_agg_fields}
                    agg = df.groupby(['timeBinDatetime']).agg(agg_dict).reset_index()
            else:
                # Just count records
                df['count'] = 1
                agg = df.groupby(['timeBinDatetime'])['count'].sum().reset_index()
            
            # Save output
            input_path = Path(input_file)
            output_path = input_path.parent / f"{input_path.stem}{output_suffix}.csv"
            agg.to_csv(output_path, index=False)
            
            total_count = int(agg['count'].sum()) if 'count' in agg.columns else int(agg[agg.columns[1]].sum())
            _logger.info(f"temporal_agg success time_bins={len(agg)}")
            return {
                "success": True,
                "output_path": str(output_path),
                "total_bins": len(agg),
                "total_count": total_count
            }
            
        except Exception as e:
            _logger.error(f"temporal_agg error: {e}")
            return {"success": False, "error": str(e)}
