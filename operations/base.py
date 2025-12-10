"""
Base Operation Class
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List, Tuple
import streamlit as st
import pandas as pd
import logging
from operations.column_name_mapping import to_camel_case, COLUMN_NAME_MAPPING

_logger = logging.getLogger("base_operation")


class DataSourceHelper:
    """Helper methods for handling data source selection and column mapping"""
    
    @staticmethod
    def normalize_column_names(df: pd.DataFrame) -> pd.DataFrame:
        """
        Normalize DataFrame column names to camelCase
        
        Args:
            df: DataFrame with potentially mixed column naming conventions
            
        Returns:
            DataFrame with camelCase column names
        """
        # Create a mapping for columns that exist in the dataframe
        rename_dict = {}
        for col in df.columns:
            col_lower = col.lower()
            if col_lower in COLUMN_NAME_MAPPING:
                rename_dict[col] = COLUMN_NAME_MAPPING[col_lower]
            elif col != to_camel_case(col):
                # Convert any remaining snake_case to camelCase
                rename_dict[col] = to_camel_case(col)
        
        if rename_dict:
            _logger.info(f"Normalizing column names: {rename_dict}")
            df = df.rename(columns=rename_dict)
        
        return df
    
    @staticmethod
    def render_coordinate_selector(df: pd.DataFrame, endpoint: str = None) -> Tuple[str, str]:
        """
        Render coordinate column selector with auto-detection
        
        Args:
            df: DataFrame to select columns from (preview)
            endpoint: Optional endpoint hint for auto-detection
            
        Returns:
            Tuple of (latitude_column, longitude_column)
        """
        available_columns = list(df.columns)
        
        st.markdown("**📍 Select coordinate columns:**")
        col1, col2 = st.columns(2)
        
        with col1:
            # Try to auto-detect latitude column - prefer camelCase
            if endpoint == 'origin':
                lat_default = next((c for c in available_columns if c in ['originLatitude', 'org_lat', 'origin_lat']), None)
            elif endpoint == 'destination':
                lat_default = next((c for c in available_columns if c in ['destinationLatitude', 'dst_lat', 'dest_lat', 'destination_lat']), None)
            else:
                lat_default = next((c for c in available_columns if 'lat' in c.lower()), None)
            
            if not lat_default:
                lat_default = available_columns[0] if available_columns else None
                
            lat_col = st.selectbox(
                "Latitude column:", 
                options=available_columns,
                index=available_columns.index(lat_default) if lat_default in available_columns else 0
            )
        
        with col2:
            # Try to auto-detect longitude column - prefer camelCase
            if endpoint == 'origin':
                lon_default = next((c for c in available_columns if c in ['originLongitude', 'org_lng', 'org_long', 'origin_lng']), None)
            elif endpoint == 'destination':
                lon_default = next((c for c in available_columns if c in ['destinationLongitude', 'dst_lng', 'dst_long', 'dest_lng']), None)
            else:
                lon_default = next((c for c in available_columns if 'lon' in c.lower() or 'lng' in c.lower()), None)
            
            if not lon_default:
                lon_default = available_columns[1] if len(available_columns) > 1 else None
                
            lon_col = st.selectbox(
                "Longitude column:",
                options=available_columns,
                index=available_columns.index(lon_default) if lon_default in available_columns else (1 if len(available_columns) > 1 else 0)
            )
        
        return lat_col, lon_col
    
    @staticmethod
    def render_aggregation_field_selector(df: pd.DataFrame, lat_col: str, lon_col: str) -> List[str]:
        """
        Render aggregation field selector with auto-filtering of ID columns
        
        Args:
            df: DataFrame to select columns from (preview)
            lat_col: Latitude column to exclude
            lon_col: Longitude column to exclude
            
        Returns:
            List of selected aggregation field names
        """
        numeric_cols = df.select_dtypes(include=['number']).columns.tolist()
        
        # Exclude coordinate columns and common ID/index fields
        exclude_patterns = ['id', 'index', lat_col, lon_col, 'objectid', 'fid']
        filtered_numeric_cols = [
            col for col in numeric_cols 
            if col.lower() not in exclude_patterns and col not in [lat_col, lon_col]
        ]
        
        if filtered_numeric_cols:
            selected_fields = st.multiselect(
                "Fields to aggregate (sum):",
                options=filtered_numeric_cols,
                default=[],  # Empty by default
                help="Select numeric fields to sum during aggregation. If none selected, will count occurrences."
            )
            
            if not selected_fields:
                st.info("ℹ️ No fields selected. Will count number of records.")
        else:
            st.info("ℹ️ No numeric fields found (excluding ID fields). Will count number of records.")
            selected_fields = []
        
        return selected_fields
    
    @staticmethod
    def get_coordinate_columns(df: pd.DataFrame, endpoint: str, manual_lat: str = None, manual_lon: str = None) -> Tuple[str, str]:
        """
        Get coordinate columns either from manual selection or auto-detection
        Supports both camelCase and snake_case column names
        
        Args:
            df: DataFrame
            endpoint: 'origin', 'destination', or 'all'
            manual_lat: Manually selected latitude column
            manual_lon: Manually selected longitude column
            
        Returns:
            Tuple of (latitude_column, longitude_column)
        """
        if manual_lat and manual_lon:
            lat_col = manual_lat if manual_lat in df.columns else None
            lon_col = manual_lon if manual_lon in df.columns else None
            _logger.info(f"Using manual column selection: lat={lat_col}, lon={lon_col}")
            return lat_col, lon_col
        
        # Auto-detect based on endpoint - try camelCase first, then snake_case
        if endpoint == 'origin':
            lat_col = next((c for c in ['originLatitude', 'org_lat', 'origin_lat', 'latitude'] if c in df.columns), None)
            lon_col = next((c for c in ['originLongitude', 'org_lng', 'org_long', 'origin_lng', 'origin_long', 'longitude'] if c in df.columns), None)
        elif endpoint == 'destination':
            lat_col = next((c for c in ['destinationLatitude', 'dst_lat', 'dest_lat', 'destination_lat'] if c in df.columns), None)
            lon_col = next((c for c in ['destinationLongitude', 'dst_lng', 'dst_long', 'dest_lng', 'dest_long'] if c in df.columns), None)
        else:
            lat_col = next((c for c in ['originLatitude', 'destinationLatitude', 'org_lat', 'dst_lat', 'origin_lat', 'dest_lat', 'latitude', 'lat'] if c in df.columns), None)
            lon_col = next((c for c in ['originLongitude', 'destinationLongitude', 'org_lng', 'org_long', 'dst_lng', 'dst_long', 'origin_lng', 'dest_lng', 'longitude', 'lon', 'lng'] if c in df.columns), None)
        
        return lat_col, lon_col


class BaseOperation(ABC):
    """Base class for all data operations"""
    
    def __init__(self):
        self.metadata = self.get_metadata()
    
    @abstractmethod
    def get_metadata(self) -> Dict[str, str]:
        """
        Return operation metadata
        
        Returns:
            dict with keys: 'key', 'title', 'description', 'category'
        """
        pass
    
    @abstractmethod
    def render_ui(self) -> Optional[Dict[str, Any]]:
        """
        Render the UI panel for this operation
        
        Returns:
            Dictionary of parameters if user clicks Run, None otherwise
        """
        pass
    
    @abstractmethod
    def execute(self, **kwargs) -> Dict[str, Any]:
        """
        Execute the operation
        
        Args:
            **kwargs: Operation-specific parameters
            
        Returns:
            dict with keys: 'success' (bool), 'output_path' (str), 'error' (str)
        """
        pass
    
    def run(self):
        """Main entry point - renders UI and executes if requested"""
        st.header(self.metadata['title'])
        
        params = self.render_ui()
        if params is not None:
            with st.spinner(f"Running {self.metadata['title']}..."):
                result = self.execute(**params)
                
                if result.get('success'):
                    st.success("✅ Operation completed successfully!")
                    if 'output_path' in result:
                        st.info(f"📁 Output file: {result['output_path']}")
                else:
                    st.error(f"❌ Error: {result.get('error', 'Unknown error')}")
