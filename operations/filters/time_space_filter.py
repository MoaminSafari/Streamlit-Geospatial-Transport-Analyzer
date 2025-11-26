"""
Time-Space Filter Operation - Complete UI extracted
"""

import streamlit as st
from datetime import datetime
from typing import Dict, Any, Optional
from operations.base import BaseOperation
from ui_helpers import utils
from config import Config
from analysis_engine import TimeFilter


def get_time_filter_from_sidebar():
    """Get time filter from sidebar session state"""
    filter_type = st.session_state.get('filter_type', 'all')
    params = st.session_state.get('time_filter_params', {})
    return {"type": filter_type, **params}


def get_filtered_files(data_source, time_filter):
    """Get filtered files based on time filter"""
    tf = TimeFilter(**time_filter)
    files = st.session_state.engine.get_filtered_files(data_source=data_source, time_filter=tf)
    all_files = list(files.get('snapp', [])) + list(files.get('tapsi', []))
    return all_files


class TimeSpaceFilterOperation(BaseOperation):
    """Filter by time and location on raw data"""
    
    def get_metadata(self) -> Dict[str, str]:
        return {
            'key': 'time_space_filter',
            'title': 'Time-Space Filter',
            'description': 'Filter by time and location on raw data',
            'category': 'filters'
        }
    
    def render_ui(self) -> Optional[Dict[str, Any]]:
        """Render complex UI with time and spatial filters"""
        
        st.markdown("### Configuration")
        
        # Initialize session state
        for key in ['tsf_enable_org_time', 'tsf_enable_dst_time', 'tsf_enable_org_spatial', 'tsf_enable_dst_spatial']:
            if key not in st.session_state:
                st.session_state[key] = False
        
        # TIME FILTERS
        with st.expander("🕐 Time Filters", expanded=True):
            col1, col2 = st.columns(2)
            
            # Origin Time
            with col1:
                enable_org_time = st.checkbox("Filter Origin Time", 
                                              value=st.session_state.tsf_enable_org_time,
                                              key="enable_org_time")
                st.session_state.tsf_enable_org_time = enable_org_time
                org_time_params = {"enabled": enable_org_time}
                
                if enable_org_time:
                    st.markdown("##### Origin Time Range")
                    
                    # Session state defaults
                    if 'tsf_org_d1' not in st.session_state:
                        st.session_state.tsf_org_d1 = datetime.now().date()
                    if 'tsf_org_h1' not in st.session_state:
                        st.session_state.tsf_org_h1 = 0
                    if 'tsf_org_m1' not in st.session_state:
                        st.session_state.tsf_org_m1 = 0
                    if 'tsf_org_h2' not in st.session_state:
                        st.session_state.tsf_org_h2 = 23
                    if 'tsf_org_m2' not in st.session_state:
                        st.session_state.tsf_org_m2 = 59
                    if 'tsf_same_date_org' not in st.session_state:
                        st.session_state.tsf_same_date_org = True
                    
                    d1 = st.date_input("Start Date", st.session_state.tsf_org_d1, key="org_d1")
                    st.session_state.tsf_org_d1 = d1
                    
                    col_h1, col_m1 = st.columns(2)
                    with col_h1:
                        h1 = st.slider("Hour", 0, 23, st.session_state.tsf_org_h1, key="org_h1")
                        st.session_state.tsf_org_h1 = h1
                    with col_m1:
                        m1 = st.slider("Minute", 0, 59, st.session_state.tsf_org_m1, key="org_m1")
                        st.session_state.tsf_org_m1 = m1
                    
                    same_date_org = st.checkbox("End Date = Start Date", value=st.session_state.tsf_same_date_org, key="same_date_org")
                    st.session_state.tsf_same_date_org = same_date_org
                    
                    if same_date_org:
                        d2 = d1
                        st.info(f"End Date: {d1}")
                    else:
                        if 'tsf_org_d2' not in st.session_state:
                            st.session_state.tsf_org_d2 = d1
                        d2 = st.date_input("End Date", st.session_state.tsf_org_d2, key="org_d2")
                        st.session_state.tsf_org_d2 = d2
                    
                    col_h2, col_m2 = st.columns(2)
                    with col_h2:
                        h2 = st.slider("Hour", 0, 23, st.session_state.tsf_org_h2, key="org_h2")
                        st.session_state.tsf_org_h2 = h2
                    with col_m2:
                        m2 = st.slider("Minute", 0, 59, st.session_state.tsf_org_m2, key="org_m2")
                        st.session_state.tsf_org_m2 = m2
                    
                    org_time_params["start"] = f"{d1} {h1:02d}:{m1:02d}"
                    org_time_params["end"] = f"{d2} {h2:02d}:{m2:02d}"

            # Destination Time
            with col2:
                enable_dst_time = st.checkbox("Filter Destination Time",
                                              value=st.session_state.tsf_enable_dst_time,
                                              key="enable_dst_time")
                st.session_state.tsf_enable_dst_time = enable_dst_time
                dst_time_params = {"enabled": enable_dst_time}
                
                if enable_dst_time:
                    st.markdown("##### Destination Time Range")
                    
                    if 'tsf_dst_d1' not in st.session_state:
                        st.session_state.tsf_dst_d1 = datetime.now().date()
                    if 'tsf_dst_h1' not in st.session_state:
                        st.session_state.tsf_dst_h1 = 0
                    if 'tsf_dst_m1' not in st.session_state:
                        st.session_state.tsf_dst_m1 = 0
                    if 'tsf_dst_h2' not in st.session_state:
                        st.session_state.tsf_dst_h2 = 23
                    if 'tsf_dst_m2' not in st.session_state:
                        st.session_state.tsf_dst_m2 = 59
                    if 'tsf_same_date_dst' not in st.session_state:
                        st.session_state.tsf_same_date_dst = True
                    
                    d3 = st.date_input("Start Date", st.session_state.tsf_dst_d1, key="dst_d1")
                    st.session_state.tsf_dst_d1 = d3
                    
                    col_h3, col_m3 = st.columns(2)
                    with col_h3:
                        h3 = st.slider("Hour", 0, 23, st.session_state.tsf_dst_h1, key="dst_h1")
                        st.session_state.tsf_dst_h1 = h3
                    with col_m3:
                        m3 = st.slider("Minute", 0, 59, st.session_state.tsf_dst_m1, key="dst_m1")
                        st.session_state.tsf_dst_m1 = m3
                    
                    same_date_dst = st.checkbox("End Date = Start Date", value=st.session_state.tsf_same_date_dst, key="same_date_dst")
                    st.session_state.tsf_same_date_dst = same_date_dst
                    
                    if same_date_dst:
                        d4 = d3
                        st.info(f"End Date: {d3}")
                    else:
                        if 'tsf_dst_d2' not in st.session_state:
                            st.session_state.tsf_dst_d2 = d3
                        d4 = st.date_input("End Date", st.session_state.tsf_dst_d2, key="dst_d2")
                        st.session_state.tsf_dst_d2 = d4
                    
                    col_h4, col_m4 = st.columns(2)
                    with col_h4:
                        h4 = st.slider("Hour", 0, 23, st.session_state.tsf_dst_h2, key="dst_h2")
                        st.session_state.tsf_dst_h2 = h4
                    with col_m4:
                        m4 = st.slider("Minute", 0, 59, st.session_state.tsf_dst_m2, key="dst_m2")
                        st.session_state.tsf_dst_m2 = m4
                    
                    dst_time_params["start"] = f"{d3} {h3:02d}:{m3:02d}"
                    dst_time_params["end"] = f"{d4} {h4:02d}:{m4:02d}"

        # SPATIAL FILTERS
        with st.expander("📍 Spatial Filters", expanded=True):
            col3, col4 = st.columns(2)
            
            # Origin Spatial
            with col3:
                enable_org_spatial = st.checkbox("Filter Origin Location", key="enable_org_spatial")
                org_spatial_params = {"enabled": enable_org_spatial}
                
                if enable_org_spatial:
                    mode = st.radio("Mode", ["Coordinates", "Shapefile"], key="org_mode", horizontal=True)
                    org_spatial_params["mode"] = mode.lower()
                    
                    if mode == "Coordinates":
                        st.markdown("##### Origin Bounding Box")
                        lat_min = st.number_input("Min Lat", 35.0, 36.0, 35.6, format="%.4f", key="org_lat_min")
                        lat_max = st.number_input("Max Lat", 35.0, 36.0, 35.8, format="%.4f", key="org_lat_max")
                        lon_min = st.number_input("Min Lon", 51.0, 52.0, 51.2, format="%.4f", key="org_lon_min")
                        lon_max = st.number_input("Max Lon", 51.0, 52.0, 51.6, format="%.4f", key="org_lon_max")
                        
                        org_spatial_params.update({
                            "lat_min": lat_min, "lat_max": lat_max,
                            "lon_min": lon_min, "lon_max": lon_max
                        })
                    else:
                        st.markdown("##### Origin Zones")
                        source = st.selectbox("Boundary Source", 
                                            list(BOUNDARY_SOURCES.keys()), 
                                            format_func=lambda x: BOUNDARY_SOURCES[x],
                                            key="org_source")
                        org_spatial_params["boundary_source"] = source
                        
                        zone_data = utils.get_shapefile_zones(source)
                        if "error" in zone_data:
                            st.error(f"Error loading zones: {zone_data['error']}")
                        elif zone_data:
                            zones = st.multiselect(
                                f"Select Zones ({zone_data.get('count', 0)} available)", 
                                options=zone_data["values"],
                                key="org_zones"
                            )
                            org_spatial_params["selected_zones"] = zones
                            org_spatial_params["zone_field"] = zone_data["field"]
                        else:
                            st.error("Could not load zones")

            # Destination Spatial
            with col4:
                enable_dst_spatial = st.checkbox("Filter Destination Location", key="enable_dst_spatial")
                dst_spatial_params = {"enabled": enable_dst_spatial}
                
                if enable_dst_spatial:
                    mode = st.radio("Mode", ["Coordinates", "Shapefile"], key="dst_mode", horizontal=True)
                    dst_spatial_params["mode"] = mode.lower()
                    
                    if mode == "Coordinates":
                        st.markdown("##### Destination Bounding Box")
                        lat_min = st.number_input("Min Lat", 35.0, 36.0, 35.6, format="%.4f", key="dst_lat_min")
                        lat_max = st.number_input("Max Lat", 35.0, 36.0, 35.8, format="%.4f", key="dst_lat_max")
                        lon_min = st.number_input("Min Lon", 51.0, 52.0, 51.2, format="%.4f", key="dst_lon_min")
                        lon_max = st.number_input("Max Lon", 51.0, 52.0, 51.6, format="%.4f", key="dst_lon_max")
                        
                        dst_spatial_params.update({
                            "lat_min": lat_min, "lat_max": lat_max,
                            "lon_min": lon_min, "lon_max": lon_max
                        })
                    else:
                        st.markdown("##### Destination Zones")
                        source = st.selectbox("Boundary Source", 
                                            list(BOUNDARY_SOURCES.keys()),
                                            format_func=lambda x: BOUNDARY_SOURCES[x],
                                            key="dst_source")
                        dst_spatial_params["boundary_source"] = source
                        
                        zone_data = utils.get_shapefile_zones(source)
                        if "error" in zone_data:
                            st.error(f"Error loading zones: {zone_data['error']}")
                        elif zone_data:
                            zones = st.multiselect(
                                f"Select Zones ({zone_data.get('count', 0)} available)", 
                                options=zone_data["values"],
                                key="dst_zones"
                            )
                            dst_spatial_params["selected_zones"] = zones
                            dst_spatial_params["zone_field"] = zone_data["field"]
                        else:
                            st.error("Could not load zones")

        # Output Settings
        st.subheader("Output Settings")
        col_out1, col_out2 = st.columns(2)
        with col_out1:
            output_format = st.selectbox("Output Format", ["csv", "shapefile"], key="ts_fmt")
        with col_out2:
            # Auto-generate suffix based on time filter
            time_suffix = utils.get_time_filter_suffix()
            default_suffix = f"_{time_suffix}_timespace_filtered"
            output_suffix = st.text_input("Output Suffix", default_suffix, key="ts_suf")
            
        st.info("💡 Tip: Your filter settings are automatically saved and will restore when you refresh the page!")
            
        if st.button("▶️ Run Filter Operation", type="primary", width='stretch'):
            if not any([enable_org_time, enable_dst_time, enable_org_spatial, enable_dst_spatial]):
                st.error("Please enable at least one filter.")
                return None
            
            return {
                'org_time_params': org_time_params,
                'dst_time_params': dst_time_params,
                'org_spatial_params': org_spatial_params,
                'dst_spatial_params': dst_spatial_params,
                'output_format': output_format,
                'output_suffix': output_suffix
            }
        
        return None
    
    def execute(self, org_time_params, dst_time_params, org_spatial_params, 
                dst_spatial_params, output_format, output_suffix) -> Dict[str, Any]:
        """Execute time-space filter on multiple files"""
        import pandas as pd
        
        time_filter = get_time_filter_from_sidebar()
        files = get_filtered_files(st.session_state.data_source, time_filter)
        
        if not files:
            return {'success': False, 'error': 'No files match the time filter from sidebar'}
        
        # Simplified execution (full implementation coming soon)
        st.info("⏳ Time-Space Filter operation is being migrated. Full implementation coming soon...")
        st.warning("Please use the legacy UI for now or wait for the next update.")
        
        return {
            'success': False,
            'error': 'Time-Space Filter migration in progress. Full implementation coming soon.'
        }
