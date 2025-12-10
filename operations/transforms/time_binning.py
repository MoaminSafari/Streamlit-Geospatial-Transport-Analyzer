"""
Time Binning Operation
Maps timestamps to time bins without aggregation - keeps all rows
"""

import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Any
import logging

from operations.base import BaseOperation, DataSourceHelper
from operations.config import TIME_BINS, DEFAULT_TIME_BIN, OUTPUT_FORMATS
from config import Config
from ui_helpers import utils

_logger = logging.getLogger("time_binning")


class TimeBinningOperation(BaseOperation):
    """Map timestamps to time bins without aggregating data"""
    
    def get_id(self) -> str:
        return "time_binning"
    
    def get_name(self) -> str:
        return "⏰ Time Binning"
    
    def get_description(self) -> str:
        return "Map timestamps to time bins (e.g., round to nearest 30-min interval) without aggregation"
    
    def get_category(self) -> str:
        return "Transform"
    
    def get_metadata(self) -> Dict[str, str]:
        return {
            'key': 'time_binning',
            'title': 'Time Binning',
            'description': 'Map timestamps to time bins without aggregation',
            'category': 'transforms'
        }
    
    def render_ui(self):
        """Render the Time Binning configuration UI"""
        
        st.markdown("### ⏰ Time Binning Configuration")
        st.markdown("""
        Map timestamps to time bins without aggregating data.
        Each row will be kept, but time fields will be rounded to the nearest bin.
        
        **Example:** 14:23:15 with 30-min bins → 14:30:00
        """)
        
        st.markdown("---")
        
        # Data source selection
        aggregated_files = utils.get_aggregated_files()
        if not aggregated_files:
            st.warning("⚠️ Please run an analysis first to generate aggregated files.")
            return None
        
        file_options = {f.name: str(f) for f in aggregated_files}
        
        st.markdown("### 📊 Data Source")
        selected_file = st.selectbox("Input file:", options=list(file_options.keys()))
        
        st.markdown("---")
        st.markdown("### ⏱️ Time Binning Settings")
        
        col1, col2 = st.columns(2)
        
        with col1:
            # Time bin size selection
            time_bin_label = st.selectbox(
                "Time bin size:",
                options=list(TIME_BINS.keys()),
                index=list(TIME_BINS.keys()).index(DEFAULT_TIME_BIN),
                help="Size of time bins to map timestamps to"
            )
            time_bin_minutes = TIME_BINS[time_bin_label]
        
        with col2:
            # Rounding method
            rounding_method = st.selectbox(
                "Rounding method:",
                options=["nearest", "floor", "ceil"],
                format_func=lambda x: {
                    "nearest": "Nearest (round to closest bin)",
                    "floor": "Floor (round down)",
                    "ceil": "Ceiling (round up)"
                }[x],
                help="How to round times to bins"
            )
        
        # Time field selection
        st.markdown("#### Select time fields to bin:")
        
        col1, col2 = st.columns(2)
        
        with col1:
            bin_start_time = st.checkbox(
                "Bin start times",
                value=True,
                help="Map startTime/start_time to time bins"
            )
        
        with col2:
            bin_end_time = st.checkbox(
                "Bin end times",
                value=False,
                help="Map endTime/end_time to time bins"
            )
        
        if not bin_start_time and not bin_end_time:
            st.warning("⚠️ Select at least one time field to bin")
            return
        
        # Additional options
        st.markdown("#### Additional Options")
        
        col1, col2 = st.columns(2)
        
        with col1:
            add_bin_label = st.checkbox(
                "Add bin label column",
                value=True,
                help="Add a readable time bin label (e.g., '14:00-14:30')"
            )
        
        with col2:
            preserve_original = st.checkbox(
                "Keep original time columns",
                value=False,
                help="Keep original time columns with '_original' suffix"
            )
        
        st.markdown("---")
        st.markdown("### 💾 Output Settings")
        
        col1, col2 = st.columns(2)
        
        with col1:
            output_format = st.selectbox("Output format:", options=OUTPUT_FORMATS)
        
        with col2:
            time_suffix = utils.get_time_filter_suffix()
            bin_suffix = time_bin_label.replace(" ", "")
            default_suffix = f"_{time_suffix}_binned_{bin_suffix}"
            output_suffix = st.text_input("Output suffix:", value=default_suffix)
        
        if st.button("▶️ Run Time Binning", type="primary", use_container_width=True):
            return {
                'input_file': file_options[selected_file],
                'time_bin_minutes': time_bin_minutes,
                'time_bin_label': time_bin_label,
                'rounding_method': rounding_method,
                'bin_start_time': bin_start_time,
                'bin_end_time': bin_end_time,
                'add_bin_label': add_bin_label,
                'preserve_original': preserve_original,
                'output_format': output_format,
                'output_suffix': output_suffix
            }
        
        return None
    
    def execute(self, **kwargs) -> Dict[str, Any]:
        """
        Execute time binning operation.
        
        Args:
            **kwargs: Dictionary with binning parameters
        
        Returns:
            Dictionary with success status and results
        """
        input_file = kwargs['input_file']
        time_bin_minutes = kwargs['time_bin_minutes']
        rounding_method = kwargs['rounding_method']
        bin_start_time = kwargs['bin_start_time']
        bin_end_time = kwargs['bin_end_time']
        add_bin_label = kwargs['add_bin_label']
        preserve_original = kwargs['preserve_original']
        output_format = kwargs['output_format']
        output_suffix = kwargs['output_suffix']
        
        try:
            _logger.info("Starting time binning operation")
            
            # Load data
            df = pd.read_csv(input_file)
            if df is None or df.empty:
                return {"success": False, "error": "No data loaded"}
            
            input_rows = len(df)
            _logger.info(f"Loaded {input_rows} rows")
            
            # Apply time binning
            df_binned = self._apply_time_binning(
                df,
                time_bin_minutes=time_bin_minutes,
                rounding_method=rounding_method,
                bin_start_time=bin_start_time,
                bin_end_time=bin_end_time,
                add_bin_label=add_bin_label,
                preserve_original=preserve_original
            )
            
            if df_binned is None or df_binned.empty:
                return {"success": False, "error": "Time binning failed"}
            
            # Calculate statistics
            unique_bins = 0
            if add_bin_label and 'timeBin' in df_binned.columns:
                unique_bins = df_binned['timeBin'].nunique()
            
            stats = {
                'input_rows': input_rows,
                'output_rows': len(df_binned),
                'unique_bins': unique_bins
            }
            
            # Save output
            input_path = Path(input_file)
            
            if output_format == 'csv':
                output_path = input_path.parent / f"{input_path.stem}{output_suffix}.csv"
                df_binned.to_csv(output_path, index=False)
            else:
                # Shapefile not applicable for this operation
                output_path = input_path.parent / f"{input_path.stem}{output_suffix}.csv"
                df_binned.to_csv(output_path, index=False)
            
            _logger.info(f"Saved output to {output_path}")
            
            return {
                "success": True,
                "output_file": str(output_path),
                "stats": stats,
                "preview": df_binned.head(10)
            }
            
        except Exception as e:
            _logger.error(f"Time binning error: {e}", exc_info=True)
            return {"success": False, "error": str(e)}
    
    def _apply_time_binning(
        self,
        df: pd.DataFrame,
        time_bin_minutes: int,
        rounding_method: str = "nearest",
        bin_start_time: bool = True,
        bin_end_time: bool = False,
        add_bin_label: bool = True,
        preserve_original: bool = False
    ) -> pd.DataFrame:
        """
        Apply time binning to dataframe.
        
        Args:
            df: Input dataframe
            time_bin_minutes: Size of time bins in minutes
            rounding_method: 'nearest', 'floor', or 'ceil'
            bin_start_time: Whether to bin start times
            bin_end_time: Whether to bin end times
            add_bin_label: Whether to add readable bin label
            preserve_original: Whether to keep original time columns
        
        Returns:
            DataFrame with binned times
        """
        df_result = df.copy()
        
        # Identify time columns
        start_time_col = None
        end_time_col = None
        
        for col in df_result.columns:
            if 'start' in col.lower() and 'time' in col.lower():
                start_time_col = col
            if 'end' in col.lower() and 'time' in col.lower():
                end_time_col = col
        
        if not start_time_col and not end_time_col:
            _logger.warning("No time columns found")
            return df_result
        
        # Preserve originals if requested
        if preserve_original:
            if start_time_col and bin_start_time:
                df_result[f"{start_time_col}_original"] = df_result[start_time_col]
            if end_time_col and bin_end_time:
                df_result[f"{end_time_col}_original"] = df_result[end_time_col]
        
        # Bin start time
        if bin_start_time and start_time_col:
            df_result[start_time_col] = df_result[start_time_col].apply(
                lambda x: self._bin_timestamp(x, time_bin_minutes, rounding_method)
            )
        
        # Bin end time
        if bin_end_time and end_time_col:
            df_result[end_time_col] = df_result[end_time_col].apply(
                lambda x: self._bin_timestamp(x, time_bin_minutes, rounding_method)
            )
        
        # Add bin label
        if add_bin_label:
            # Use the first binned time column for label
            time_col = start_time_col if (bin_start_time and start_time_col) else end_time_col
            if time_col:
                df_result['timeBin'] = df_result[time_col].apply(
                    lambda x: self._create_bin_label(x, time_bin_minutes)
                )
        
        return df_result
    
    def _bin_timestamp(self, timestamp, bin_minutes: int, method: str = "nearest"):
        """
        Bin a single timestamp.
        
        Args:
            timestamp: Time string or datetime
            bin_minutes: Bin size in minutes
            method: 'nearest', 'floor', or 'ceil'
        
        Returns:
            Binned time string
        """
        try:
            # Parse timestamp if string
            if isinstance(timestamp, str):
                # Try different time formats
                for fmt in ['%H:%M:%S', '%H:%M', '%Y-%m-%d %H:%M:%S']:
                    try:
                        dt = datetime.strptime(timestamp, fmt)
                        break
                    except:
                        continue
                else:
                    return timestamp
            elif isinstance(timestamp, pd.Timestamp):
                dt = timestamp.to_pydatetime()
            elif isinstance(timestamp, datetime):
                dt = timestamp
            else:
                return timestamp
            
            # Calculate bin
            total_minutes = dt.hour * 60 + dt.minute
            
            if method == "floor":
                binned_minutes = (total_minutes // bin_minutes) * bin_minutes
            elif method == "ceil":
                binned_minutes = ((total_minutes + bin_minutes - 1) // bin_minutes) * bin_minutes
            else:  # nearest
                binned_minutes = round(total_minutes / bin_minutes) * bin_minutes
            
            # Handle overflow (24:00)
            if binned_minutes >= 24 * 60:
                binned_minutes = 0
            
            hour = binned_minutes // 60
            minute = binned_minutes % 60
            
            # Return in same format
            return f"{hour:02d}:{minute:02d}:00"
            
        except Exception as e:
            _logger.warning(f"Could not bin timestamp {timestamp}: {e}")
            return timestamp
    
    def _create_bin_label(self, timestamp, bin_minutes: int):
        """
        Create readable bin label (e.g., '14:00-14:30').
        
        Args:
            timestamp: Binned timestamp
            bin_minutes: Bin size in minutes
        
        Returns:
            Readable label string
        """
        try:
            if isinstance(timestamp, str):
                for fmt in ['%H:%M:%S', '%H:%M']:
                    try:
                        dt = datetime.strptime(timestamp, fmt)
                        break
                    except:
                        continue
                else:
                    return timestamp
            elif isinstance(timestamp, (pd.Timestamp, datetime)):
                dt = timestamp if isinstance(timestamp, datetime) else timestamp.to_pydatetime()
            else:
                return str(timestamp)
            
            # Create end time
            end_dt = dt + timedelta(minutes=bin_minutes)
            
            return f"{dt.strftime('%H:%M')}-{end_dt.strftime('%H:%M')}"
            
        except:
            return str(timestamp)


# Register the operation
def register():
    """Register this operation"""
    from operations.registry import register_operation
    register_operation(TimeBinningOperation())
