"""
File Preview Operation
"""

import streamlit as st
import pandas as pd
from pathlib import Path
from typing import Dict, Any, Optional
from operations.base import BaseOperation
from config import DataColumnMetadata


def get_aggregated_files():
    """Get list of aggregated files"""
    from ui_helpers import utils
    return utils.get_aggregated_files()


def get_available_files():
    """Get list of raw files"""
    from ui_helpers.utils import get_time_filter_from_sidebar
    from analysis_engine import TimeFilter
    import streamlit as st
    
    data_source = st.session_state.get('data_source', 'all')
    time_filter = get_time_filter_from_sidebar()
    tf = TimeFilter(**time_filter)
    files = st.session_state.engine.get_filtered_files(data_source=data_source, time_filter=tf)
    all_files = list(files.get('snapp', [])) + list(files.get('tapsi', []))
    return all_files


class FilePreviewOperation(BaseOperation):
    """File Preview operation"""
    
    def get_metadata(self) -> Dict[str, str]:
        return {
            'key': 'file_preview',
            'title': 'File Preview',
            'description': 'Preview first N rows of any file',
            'category': 'utilities'
        }
    
    def render_ui(self) -> Optional[Dict[str, Any]]:
        """Render UI and return params if Run clicked"""
        
        # Choose file source
        file_source = st.radio("Select file source:", ["Aggregated", "Raw"], horizontal=True)
        
        if file_source == "Aggregated":
            aggregated_files = get_aggregated_files()
            if not aggregated_files:
                st.warning("⚠️ No aggregated files found. Please run an analysis first.")
                return None
            file_options = {f.name: str(f) for f in aggregated_files}
        else:  # Raw
            all_files = get_available_files()
            if not all_files:
                st.warning("⚠️ No raw files found.")
                return None
            file_options = {f.name: str(f) for f in all_files}
        
        if not file_options:
            return None
            
        selected_file = st.selectbox("Select file to preview:", options=list(file_options.keys()))
        n_rows = st.number_input("Number of rows to preview:", min_value=1, max_value=1000, value=10)
        
        if st.button("👁️ Show Preview", type="primary", width='stretch'):
            return {
                'file_path': file_options[selected_file],
                'file_name': selected_file,
                'n_rows': n_rows,
                'file_source': file_source
            }
        
        return None
    
    def execute(self, file_path: str, file_name: str, n_rows: int, file_source: str) -> Dict[str, Any]:
        """Execute preview"""
        try:
            # Try to detect format for raw files
            if file_source == "Raw":
                sample = pd.read_csv(file_path, nrows=2)
                if "originLatitude" in sample.columns:
                    # Tapsi format
                    df = pd.read_csv(file_path, nrows=n_rows)
                elif len(sample.columns) == 9:
                    # Snapp format (no headers)
                    df = pd.read_csv(file_path, nrows=n_rows, header=None, names=DataColumnMetadata.get_snapp_columns())
                else:
                    # Generic
                    df = pd.read_csv(file_path, nrows=n_rows)
            else:
                df = pd.read_csv(file_path, nrows=n_rows)
            
            st.success(f"✅ Showing first {len(df)} rows of {file_name}")
            st.dataframe(df, width='stretch')
            
            # Show file info
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Rows Shown", len(df))
            with col2:
                st.metric("Columns", len(df.columns))
            with col3:
                st.metric("Source", file_source)
            
            with st.expander("📊 Column Names"):
                st.write(", ".join(df.columns.tolist()))
            
            return {'success': True}
            
        except Exception as e:
            return {'success': False, 'error': str(e)}
