"""
Time-Space Filter Operation - Complete with separated date and time controls
"""

import streamlit as st
from datetime import datetime, date, time
from typing import Dict, Any, Optional
import pandas as pd
import geopandas as gpd
import logging
from pathlib import Path
from operations.base import BaseOperation
from operations.config import BOUNDARY_SOURCES, OUTPUT_FORMATS
from ui_helpers import utils
from config import Config
from analysis_engine import TimeFilter

_logger = logging.getLogger("time_space_filter")


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
    """Filter by time and location on raw data - with separated date and time ranges"""
    
    def get_metadata(self) -> Dict[str, str]:
        return {
            'key': 'time_space_filter',
            'title': 'Time-Space Filter',
            'description': 'Filter trips by date range, time range, and location',
            'category': 'filters'
        }
    
    def render_ui(self) -> Optional[Dict[str, Any]]:
        """Render improved UI with separated date and time ranges"""
        
        st.markdown("### 📊 Time-Space Filter Configuration")
        st.markdown("Filter trips by **date range**, **time range**, and **location**")
        st.markdown("---")
        
        # Initialize session state
        for key in ['tsf_enable_org_time', 'tsf_enable_dst_time', 'tsf_enable_org_spatial', 'tsf_enable_dst_spatial']:
            if key not in st.session_state:
                st.session_state[key] = False
        
        # TIME FILTERS - Improved with separated date and time
        with st.expander("🕐 Time Filters (Date Range + Time Range)", expanded=True):
            col1, col2 = st.columns(2)
            
            # Origin Time
            with col1:
                enable_org_time = st.checkbox("Filter Origin Time", 
                                              value=st.session_state.tsf_enable_org_time,
                                              key="enable_org_time")
                st.session_state.tsf_enable_org_time = enable_org_time
                org_time_params = {"enabled": enable_org_time}
                
                if enable_org_time:
                    st.markdown("##### 📅 Origin - Date Range")
                    
                    # Initialize defaults
                    if 'tsf_org_start_date' not in st.session_state:
                        st.session_state.tsf_org_start_date = datetime.now().date()
                    if 'tsf_org_end_date' not in st.session_state:
                        st.session_state.tsf_org_end_date = datetime.now().date()
                    
                    start_date = st.date_input("Start Date", 
                                              value=st.session_state.tsf_org_start_date,
                                              key="org_start_date")
                    end_date = st.date_input("End Date", 
                                            value=st.session_state.tsf_org_end_date,
                                            key="org_end_date")
                    
                    st.session_state.tsf_org_start_date = start_date
                    st.session_state.tsf_org_end_date = end_date
                    
                    # Time Range (separate from dates)
                    st.markdown("##### ⏰ Origin - Time Range")
                    st.caption("Example: 7:00 to 8:00 for morning rush hour")
                    
                    if 'tsf_org_start_hour' not in st.session_state:
                        st.session_state.tsf_org_start_hour = 7
                    if 'tsf_org_start_min' not in st.session_state:
                        st.session_state.tsf_org_start_min = 0
                    if 'tsf_org_end_hour' not in st.session_state:
                        st.session_state.tsf_org_end_hour = 8
                    if 'tsf_org_end_min' not in st.session_state:
                        st.session_state.tsf_org_end_min = 0
                    
                    col_t1, col_t2 = st.columns(2)
                    with col_t1:
                        start_hour = st.number_input("Start Hour", 0, 23, 
                                                    st.session_state.tsf_org_start_hour,
                                                    key="org_start_hour")
                        start_min = st.number_input("Start Min", 0, 59, 
                                                   st.session_state.tsf_org_start_min,
                                                   key="org_start_min")
                    with col_t2:
                        end_hour = st.number_input("End Hour", 0, 23, 
                                                  st.session_state.tsf_org_end_hour,
                                                  key="org_end_hour")
                        end_min = st.number_input("End Min", 0, 59, 
                                                 st.session_state.tsf_org_end_min,
                                                 key="org_end_min")
                    
                    st.session_state.tsf_org_start_hour = start_hour
                    st.session_state.tsf_org_start_min = start_min
                    st.session_state.tsf_org_end_hour = end_hour
                    st.session_state.tsf_org_end_min = end_min
                    
                    # Display summary
                    st.success(f"✓ Filter: {start_date} to {end_date} between {start_hour:02d}:{start_min:02d} - {end_hour:02d}:{end_min:02d}")
                    
                    org_time_params.update({
                        "start_date": str(start_date),
                        "end_date": str(end_date),
                        "start_time": f"{start_hour:02d}:{start_min:02d}",
                        "end_time": f"{end_hour:02d}:{end_min:02d}"
                    })

            # Destination Time
            with col2:
                enable_dst_time = st.checkbox("Filter Destination Time",
                                              value=st.session_state.tsf_enable_dst_time,
                                              key="enable_dst_time")
                st.session_state.tsf_enable_dst_time = enable_dst_time
                dst_time_params = {"enabled": enable_dst_time}
                
                if enable_dst_time:
                    st.markdown("##### 📅 Destination - Date Range")
                    
                    if 'tsf_dst_start_date' not in st.session_state:
                        st.session_state.tsf_dst_start_date = datetime.now().date()
                    if 'tsf_dst_end_date' not in st.session_state:
                        st.session_state.tsf_dst_end_date = datetime.now().date()
                    
                    dst_start_date = st.date_input("Start Date", 
                                                  value=st.session_state.tsf_dst_start_date,
                                                  key="dst_start_date")
                    dst_end_date = st.date_input("End Date", 
                                                value=st.session_state.tsf_dst_end_date,
                                                key="dst_end_date")
                    
                    st.session_state.tsf_dst_start_date = dst_start_date
                    st.session_state.tsf_dst_end_date = dst_end_date
                    
                    # Time Range (separate from dates)
                    st.markdown("##### ⏰ Destination - Time Range")
                    st.caption("Example: 17:00 to 19:00 for evening rush hour")
                    
                    if 'tsf_dst_start_hour' not in st.session_state:
                        st.session_state.tsf_dst_start_hour = 17
                    if 'tsf_dst_start_min' not in st.session_state:
                        st.session_state.tsf_dst_start_min = 0
                    if 'tsf_dst_end_hour' not in st.session_state:
                        st.session_state.tsf_dst_end_hour = 19
                    if 'tsf_dst_end_min' not in st.session_state:
                        st.session_state.tsf_dst_end_min = 0
                    
                    col_t3, col_t4 = st.columns(2)
                    with col_t3:
                        dst_start_hour = st.number_input("Start Hour", 0, 23, 
                                                        st.session_state.tsf_dst_start_hour,
                                                        key="dst_start_hour")
                        dst_start_min = st.number_input("Start Min", 0, 59, 
                                                       st.session_state.tsf_dst_start_min,
                                                       key="dst_start_min")
                    with col_t4:
                        dst_end_hour = st.number_input("End Hour", 0, 23, 
                                                      st.session_state.tsf_dst_end_hour,
                                                      key="dst_end_hour")
                        dst_end_min = st.number_input("End Min", 0, 59, 
                                                     st.session_state.tsf_dst_end_min,
                                                     key="dst_end_min")
                    
                    st.session_state.tsf_dst_start_hour = dst_start_hour
                    st.session_state.tsf_dst_start_min = dst_start_min
                    st.session_state.tsf_dst_end_hour = dst_end_hour
                    st.session_state.tsf_dst_end_min = dst_end_min
                    
                    # Display summary
                    st.success(f"✓ Filter: {dst_start_date} to {dst_end_date} between {dst_start_hour:02d}:{dst_start_min:02d} - {dst_end_hour:02d}:{dst_end_min:02d}")
                    
                    dst_time_params.update({
                        "start_date": str(dst_start_date),
                        "end_date": str(dst_end_date),
                        "start_time": f"{dst_start_hour:02d}:{dst_start_min:02d}",
                        "end_time": f"{dst_end_hour:02d}:{dst_end_min:02d}"
                    })

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
        """Execute time-space filter on raw data files"""
        
        try:
            _logger.info("Starting time-space filter operation")
            
            # Get files to process
            time_filter = get_time_filter_from_sidebar()
            files = get_filtered_files(st.session_state.data_source, time_filter)
            
            if not files:
                return {'success': False, 'error': 'No files match the time filter from sidebar'}
            
            _logger.info(f"Processing {len(files)} files")
            
            # Load and concatenate all files
            all_data = []
            for file_path in files:
                try:
                    # Determine if Snapp or Tapsi
                    if 'Snapp' in str(file_path) or 'snapp' in str(file_path).lower():
                        # Snapp: no header
                        from config import DataColumnMetadata
                        df = pd.read_csv(file_path, names=DataColumnMetadata.get_snapp_columns())
                    else:
                        # Tapsi: has header
                        df = pd.read_csv(file_path)
                        from config import DataColumnMetadata
                        df = df.rename(columns=DataColumnMetadata.get_tapsi_mapping())
                    
                    all_data.append(df)
                    _logger.info(f"Loaded {len(df)} rows from {Path(file_path).name}")
                except Exception as e:
                    _logger.warning(f"Error loading {file_path}: {e}")
                    continue
            
            if not all_data:
                return {'success': False, 'error': 'Could not load any data from files'}
            
            # Combine all data
            combined_df = pd.concat(all_data, ignore_index=True)
            initial_count = len(combined_df)
            _logger.info(f"Combined {initial_count} total trips")
            
            # Parse datetime columns
            combined_df['start_datetime'] = pd.to_datetime(combined_df['start_time'], errors='coerce')
            combined_df['end_datetime'] = pd.to_datetime(combined_df['end_time'], errors='coerce')
            
            # Apply time filters
            if org_time_params.get('enabled'):
                combined_df = self._apply_time_filter(
                    combined_df, 'start_datetime', org_time_params
                )
                _logger.info(f"After origin time filter: {len(combined_df)} trips")
            
            if dst_time_params.get('enabled'):
                combined_df = self._apply_time_filter(
                    combined_df, 'end_datetime', dst_time_params
                )
                _logger.info(f"After destination time filter: {len(combined_df)} trips")
            
            # Apply spatial filters
            if org_spatial_params.get('enabled'):
                combined_df = self._apply_spatial_filter(
                    combined_df, 'org', org_spatial_params
                )
                _logger.info(f"After origin spatial filter: {len(combined_df)} trips")
            
            if dst_spatial_params.get('enabled'):
                combined_df = self._apply_spatial_filter(
                    combined_df, 'dst', dst_spatial_params
                )
                _logger.info(f"After destination spatial filter: {len(combined_df)} trips")
            
            final_count = len(combined_df)
            
            if final_count == 0:
                return {'success': False, 'error': 'No trips match the filter criteria'}
            
            # Save output
            config = Config()
            if output_format == "csv":
                output_path = config.aggregated_path / f"filtered_trips{output_suffix}.csv"
                combined_df.to_csv(output_path, index=False)
                _logger.info(f"Saved CSV to {output_path}")
            else:
                # For shapefile, we need to create geometry
                gdf = gpd.GeoDataFrame(
                    combined_df,
                    geometry=gpd.points_from_xy(combined_df.org_lng, combined_df.org_lat),
                    crs="EPSG:4326"
                )
                output_path = config.gis_output_path / f"filtered_trips{output_suffix}"
                output_path.mkdir(exist_ok=True, parents=True)
                shp_path = output_path / f"filtered_trips{output_suffix}.shp"
                gdf.to_file(shp_path)
                _logger.info(f"Saved shapefile to {shp_path}")
                output_path = shp_path
            
            return {
                'success': True,
                'output_path': str(output_path),
                'initial_count': initial_count,
                'filtered_count': final_count,
                'filter_rate': f"{(final_count/initial_count)*100:.1f}%"
            }
            
        except Exception as e:
            _logger.error(f"Error in time-space filter: {e}")
            import traceback
            _logger.error(traceback.format_exc())
            return {'success': False, 'error': str(e)}
    
    def _apply_time_filter(self, df: pd.DataFrame, datetime_col: str, 
                          params: Dict[str, Any]) -> pd.DataFrame:
        """Apply time filter (date range + time range)"""
        
        # Parse parameters
        start_date = pd.to_datetime(params['start_date'])
        end_date = pd.to_datetime(params['end_date'])
        start_time = params['start_time']  # "HH:MM"
        end_time = params['end_time']      # "HH:MM"
        
        # Parse time strings
        start_h, start_m = map(int, start_time.split(':'))
        end_h, end_m = map(int, end_time.split(':'))
        
        # Filter by date range
        df_filtered = df[
            (df[datetime_col].dt.date >= start_date.date()) &
            (df[datetime_col].dt.date <= end_date.date())
        ].copy()
        
        # Filter by time range (hour and minute)
        df_filtered['_hour'] = df_filtered[datetime_col].dt.hour
        df_filtered['_minute'] = df_filtered[datetime_col].dt.minute
        
        # Create time as total minutes from midnight for comparison
        df_filtered['_time_mins'] = df_filtered['_hour'] * 60 + df_filtered['_minute']
        start_mins = start_h * 60 + start_m
        end_mins = end_h * 60 + end_m
        
        df_filtered = df_filtered[
            (df_filtered['_time_mins'] >= start_mins) &
            (df_filtered['_time_mins'] <= end_mins)
        ]
        
        # Clean up temporary columns
        df_filtered = df_filtered.drop(columns=['_hour', '_minute', '_time_mins'])
        
        return df_filtered
    
    def _apply_spatial_filter(self, df: pd.DataFrame, endpoint: str,
                             params: Dict[str, Any]) -> pd.DataFrame:
        """Apply spatial filter (coordinates or shapefile zones)"""
        
        lat_col = f"{endpoint}_lat"
        lng_col = f"{endpoint}_lng"
        
        mode = params.get('mode', 'coordinates')
        
        if mode == 'coordinates':
            # Bounding box filter
            lat_min = params['lat_min']
            lat_max = params['lat_max']
            lon_min = params['lon_min']
            lon_max = params['lon_max']
            
            df_filtered = df[
                (df[lat_col] >= lat_min) & (df[lat_col] <= lat_max) &
                (df[lng_col] >= lon_min) & (df[lng_col] <= lon_max)
            ]
            
        else:  # shapefile mode
            # Load shapefile
            config = Config()
            boundary_source = params['boundary_source']
            
            if boundary_source == 'neighborhoods':
                shp_path = config.neighborhoods_shapefile
            elif boundary_source == 'districts':
                shp_path = config.districts_shapefile
            elif boundary_source == 'subregions':
                shp_path = config.subregions_shapefile
            elif boundary_source == 'traffic_zones':
                shp_path = config.traffic_zones_shapefile
            else:
                raise ValueError(f"Unknown boundary source: {boundary_source}")
            
            boundaries = gpd.read_file(shp_path)
            zone_field = params['zone_field']
            selected_zones = params.get('selected_zones', [])
            
            if selected_zones:
                # Filter to selected zones
                boundaries = boundaries[boundaries[zone_field].isin(selected_zones)]
            
            # Create GeoDataFrame from trip data
            gdf = gpd.GeoDataFrame(
                df,
                geometry=gpd.points_from_xy(df[lng_col], df[lat_col]),
                crs="EPSG:4326"
            )
            
            # Spatial join
            gdf_filtered = gpd.sjoin(gdf, boundaries, how='inner', predicate='within')
            
            # Convert back to regular DataFrame
            df_filtered = pd.DataFrame(gdf_filtered.drop(columns='geometry'))
        
        return df_filtered
