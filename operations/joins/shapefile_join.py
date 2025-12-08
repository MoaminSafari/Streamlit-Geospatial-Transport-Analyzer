"""
Shapefile Join Operation - Complete with UI and execution
"""

import streamlit as st
import pandas as pd
import geopandas as gpd
from shapely.geometry import Point
import logging
from typing import Dict, Any, Optional
from pathlib import Path
from operations.base import BaseOperation
from operations.config import (
    BOUNDARY_SOURCES, BOUNDARY_ATTRIBUTE_FIELDS, BOUNDARY_DEFAULT_FIELD,
    ENDPOINT_OPTIONS, AGGREGATION_LEVELS, get_aggregation_fields_for_endpoint
)
from ui_helpers import utils
from config import Config

_logger = logging.getLogger("shapefile_join")


class ShapefileJoinOperation(BaseOperation):
    """Join data with GIS layers"""
    
    def get_metadata(self) -> Dict[str, str]:
        return {
            'key': 'shapefile_join',
            'title': 'Shapefile Join',
            'description': 'Join data with GIS layers',
            'category': 'joins'
        }
    
    def render_ui(self) -> Optional[Dict[str, Any]]:
        """Render UI"""
        
        st.markdown("### Data Source")
        
        # Data source selector
        data_source_type = st.radio(
            "Select data source:",
            options=["aggregated", "raw"],
            format_func=lambda x: {
                "aggregated": "📊 Aggregated (Processed CSV files)",
                "raw": "📁 Raw Dataset (Uses global sidebar filters)"
            }[x],
            horizontal=True,
            help="Choose between processed aggregated files or raw dataset filtered by sidebar settings"
        )
        
        file_options = {}
        use_global_filter = False
        
        if data_source_type == "aggregated":
            aggregated_files = utils.get_aggregated_files()
            if not aggregated_files:
                st.warning("⚠️ No aggregated files found. Please run an analysis first.")
                return None
            file_options = {f.name: str(f) for f in aggregated_files}
            
            st.markdown("### Configuration")
            selected_file = st.selectbox("Input file:", options=list(file_options.keys()))
            
        else:  # raw - use global sidebar filters
            use_global_filter = True
            
            # Get global filter settings from session state
            data_source = st.session_state.get('data_source', 'both')
            filter_type = st.session_state.get('filter_type', 'all')
            filter_params = st.session_state.get('time_filter_params', {})
            
            # Format data source display
            data_source_labels = {"both": "Snapp + Tapsi", "snapp": "Snapp", "tapsi": "Tapsi"}
            data_source_display = data_source_labels.get(data_source, data_source)
            
            # Build info message
            info_parts = [
                "📌 **Using Global Sidebar Settings:**",
                f"- Data Source: {data_source_display}",
                f"- Time Filter: {filter_type.replace('_', ' ').title()}"
            ]
            
            if 'year' in filter_params:
                info_parts.append(f"- Year: {filter_params.get('year', 'N/A')}")
            if 'month' in filter_params:
                info_parts.append(f"- Month: {filter_params.get('month', 'N/A')}")
            if 'season' in filter_params:
                info_parts.append(f"- Season: {filter_params.get('season', 'N/A')}")
            
            st.info("\n".join(info_parts))
            
            st.markdown("### Configuration")
            selected_file = None  # Will use filtered files instead
        
        col1, col2 = st.columns(2)
        with col1:
            endpoint = st.selectbox("Target field:", options=list(ENDPOINT_OPTIONS.keys()),
                                   format_func=lambda x: ENDPOINT_OPTIONS[x])
        with col2:
            boundary_source = st.selectbox("Boundary:", 
                                          options=list(BOUNDARY_SOURCES.keys()),
                                          format_func=lambda x: BOUNDARY_SOURCES[x])
        
        # Attribute field selection from global config
        attribute_field = st.selectbox(
            "Join field:",
            options=BOUNDARY_ATTRIBUTE_FIELDS.get(boundary_source, ["CODE"]),
            help="Field from shapefile to join with"
        )
        
        st.markdown("---")
        st.markdown("### Aggregation Settings")
        
        aggregate = st.checkbox(
            "Aggregate by zones",
            value=True,
            help="Aggregate records by zones (sum counts)"
        )
        
        # Temporal aggregation option
        separate_by_hour = False
        hour_field = None
        if aggregate:
            st.markdown("**Temporal Aggregation:**")
            temporal_agg = st.radio(
                "Time handling:",
                options=["total", "by_time"],
                format_func=lambda x: {
                    "total": "Total (sum all time periods together)",
                    "by_time": "Keep separate by time (one row per zone per time period)"
                }[x],
                index=0,
                horizontal=True,
                help="Aggregate all time periods or keep them as separate rows"
            )
            separate_by_hour = (temporal_agg == "by_time")
            
            if separate_by_hour:
                # Let user specify the time/hour field
                hour_field = st.text_input(
                    "Time field name:",
                    value="hour",
                    help="Name of the time/hour field in your data (e.g., 'hour', 'time_bin', 'time_slot')"
                )
            
            st.markdown("**Select aggregation type:**")
            
            # Use global aggregation levels
            agg_level = st.radio(
                "Aggregation level:",
                options=list(AGGREGATION_LEVELS.keys()),
                format_func=lambda x: AGGREGATION_LEVELS[x],
                index=0,
                help="Choose which fields to aggregate"
            )
            
            # Get fields from global config
            selected_agg_fields = get_aggregation_fields_for_endpoint(endpoint, agg_level)
        else:
            selected_agg_fields = []
        
        # Auto-generate suffix based on time filter and boundary source
        time_suffix = utils.get_time_filter_suffix()
        default_suffix = f"_{time_suffix}_{boundary_source}_joined"
        output_suffix = st.text_input("Output suffix:", value=default_suffix)
        
        if st.button("▶️ Run", type="primary", width='stretch'):
            cfg = Config()
            if boundary_source == "neighborhoods":
                shp_path = str(cfg.neighborhoods_shapefile)
            elif boundary_source == "districts":
                shp_path = str(cfg.districts_shapefile)
            elif boundary_source == "subregions":
                shp_path = str(cfg.subregions_shapefile)
            else:
                shp_path = str(cfg.traffic_zones_shapefile)
            
            params = {
                'shp_path': shp_path,
                'attribute_field': attribute_field,
                'endpoint': endpoint,
                'aggregate': aggregate,
                'separate_by_hour': separate_by_hour,
                'hour_field': hour_field,
                'aggregation_fields': selected_agg_fields,
                'output_suffix': output_suffix,
                'data_source_type': data_source_type,
                'use_global_filter': use_global_filter
            }
            
            if use_global_filter:
                # Pass global filter settings
                params['global_data_source'] = st.session_state.get('data_source', 'both')
                params['global_filter_type'] = st.session_state.get('filter_type', 'all')
                params['global_filter_params'] = st.session_state.get('time_filter_params', {})
            else:
                # Pass selected file
                params['input_file'] = file_options[selected_file]
            
            return params
        
        return None
    
    def execute(self, **kwargs) -> Dict[str, Any]:
        """Execute shapefile join with spatial aggregation"""
        shp_path = kwargs['shp_path']
        attribute_field = kwargs['attribute_field']
        endpoint = kwargs['endpoint']
        aggregate = kwargs['aggregate']
        separate_by_hour = kwargs.get('separate_by_hour', False)
        hour_field = kwargs.get('hour_field', 'hour')
        aggregation_fields = kwargs.get('aggregation_fields', [])
        output_suffix = kwargs['output_suffix']
        data_source_type = kwargs.get('data_source_type', 'aggregated')
        use_global_filter = kwargs.get('use_global_filter', False)
        
        try:
            _logger.info(f"shapefile_join start shp={shp_path} source={data_source_type} use_global={use_global_filter} aggregate={aggregate}")
            
            # Create a placeholder for status updates
            import streamlit as st
            status_placeholder = st.empty()
            
            # Load data based on source type
            if use_global_filter:
                status_placeholder.info("📂 **Step 1/5:** Loading raw dataset files...")
                
                # Use global filter settings from sidebar
                from analysis_engine import DataAnalysisEngine, TimeFilter
                from config import DataColumnMetadata
                
                engine = DataAnalysisEngine()
                
                # Build TimeFilter from global settings
                filter_type = kwargs.get('global_filter_type', 'all')
                filter_params = kwargs.get('global_filter_params', {})
                time_filter = TimeFilter(type=filter_type, **filter_params)
                
                data_source = kwargs.get('global_data_source', 'both')
                
                # Get filtered files
                files = engine.get_filtered_files(data_source, time_filter)
                total_files = len(files['snapp']) + len(files['tapsi'])
                
                if total_files == 0:
                    status_placeholder.empty()
                    return {"success": False, "error": "No files found matching the filter criteria"}
                
                _logger.info(f"Found {len(files['snapp'])} Snapp files and {len(files['tapsi'])} Tapsi files")
                status_placeholder.info(f"📂 **Step 1/5:** Found {total_files} files ({len(files['snapp'])} Snapp, {len(files['tapsi'])} Tapsi)")
                
                # Load and combine all files
                all_dfs = []
                
                # Process Snapp files
                for idx, snapp_file in enumerate(files['snapp'], 1):
                    status_placeholder.info(f"📂 **Step 1/5:** Loading Snapp file {idx}/{len(files['snapp'])}: {snapp_file.name}")
                    _logger.info(f"Loading Snapp file: {snapp_file.name}")
                    df_temp = pd.read_csv(snapp_file, header=None, names=DataColumnMetadata.get_snapp_columns())
                    all_dfs.append(df_temp)
                
                # Process Tapsi files
                for idx, tapsi_file in enumerate(files['tapsi'], 1):
                    status_placeholder.info(f"📂 **Step 1/5:** Loading Tapsi file {idx}/{len(files['tapsi'])}: {tapsi_file.name}")
                    _logger.info(f"Loading Tapsi file: {tapsi_file.name}")
                    df_temp = pd.read_csv(tapsi_file)
                    tapsi_mapping = DataColumnMetadata.get_tapsi_mapping()
                    df_temp.rename(columns=tapsi_mapping, inplace=True)
                    all_dfs.append(df_temp)
                
                # Combine all dataframes
                status_placeholder.info(f"📂 **Step 1/5:** Combining {total_files} files...")
                df = pd.concat(all_dfs, ignore_index=True)
                _logger.info(f"Combined {total_files} files with {len(df)} total rows")
                
            else:
                status_placeholder.info("📂 **Step 1/5:** Loading aggregated file...")
                # Use single selected file (aggregated)
                input_file = kwargs['input_file']
                _logger.info(f"Loading aggregated file: {input_file}")
                df = pd.read_csv(input_file)
            
            total_records = len(df)
            status_placeholder.success(f"✅ **Step 1/5:** Loaded {total_records:,} records")
            
            # Check for possible column name variations
            status_placeholder.info(f"🎯 **Step 2/5:** Preparing coordinates (endpoint: {endpoint})...")
            
            if endpoint == 'origin':
                lat_col = next((c for c in ['org_lat', 'origin_lat', 'latitude'] if c in df.columns), None)
                lon_col = next((c for c in ['org_lng', 'org_long', 'origin_lng', 'origin_long', 'longitude'] if c in df.columns), None)
            elif endpoint == 'destination':
                lat_col = next((c for c in ['dst_lat', 'dest_lat', 'destination_lat'] if c in df.columns), None)
                lon_col = next((c for c in ['dst_lng', 'dst_long', 'dest_lng', 'dest_long', 'destination_lng'] if c in df.columns), None)
            else:
                lat_col = next((c for c in ['org_lat', 'dst_lat', 'origin_lat', 'dest_lat', 'latitude', 'lat'] if c in df.columns), None)
                lon_col = next((c for c in ['org_lng', 'org_long', 'dst_lng', 'dst_long', 'origin_lng', 'dest_lng', 'longitude', 'lon', 'lng'] if c in df.columns), None)
            
            if not lat_col or not lon_col:
                status_placeholder.empty()
                return {"success": False, "error": "Coordinate columns not found"}
            
            # Create GeoDataFrame from points
            status_placeholder.info(f"🎯 **Step 2/5:** Creating point geometries...")
            gdf_points = gpd.GeoDataFrame(df, geometry=[Point(xy) for xy in zip(df[lon_col], df[lat_col])], crs='EPSG:4326')
            
            # Load shapefile
            status_placeholder.info(f"🗺️ **Step 3/5:** Loading shapefile...")
            shp = gpd.read_file(shp_path)
            status_placeholder.success(f"✅ **Step 3/5:** Loaded shapefile with {len(shp)} zones")
            
            # Ensure CRS match
            if gdf_points.crs != shp.crs:
                status_placeholder.info(f"🗺️ **Step 3/5:** Reprojecting coordinates to match shapefile CRS...")
                gdf_points = gdf_points.to_crs(shp.crs)
            
            # Spatial join (points within polygons)
            status_placeholder.info(f"🔗 **Step 4/5:** Performing spatial join (matching {len(gdf_points):,} points to zones)...")
            joined = gpd.sjoin(gdf_points, shp, how='inner', predicate='within')
            
            join_percentage = (len(joined) / len(gdf_points) * 100) if len(gdf_points) > 0 else 0
            status_placeholder.success(f"✅ **Step 4/5:** Matched {len(joined):,} points ({join_percentage:.1f}%)")
            
            # Determine output base name
            if use_global_filter:
                # Generate name based on filter settings
                filter_type = kwargs.get('global_filter_type', 'all')
                filter_params = kwargs.get('global_filter_params', {})
                data_source = kwargs.get('global_data_source', 'both')
                
                if filter_type == "specific_month":
                    base_name = f"{data_source}_{filter_params.get('year', '')}_{filter_params.get('month', '')}"
                elif filter_type == "year":
                    base_name = f"{data_source}_{filter_params.get('year', '')}"
                elif filter_type == "season":
                    base_name = f"{data_source}_{filter_params.get('year', '')}_{filter_params.get('season', '')}"
                else:
                    base_name = f"{data_source}_{filter_type}"
                
                input_path = Path(base_name)
            else:
                input_path = Path(kwargs['input_file'])
            
            if aggregate:
                status_placeholder.info(f"📊 **Step 5/5:** Aggregating by zones...")
                
                if attribute_field not in joined.columns:
                    status_placeholder.empty()
                    return {"success": False, "error": f"Attribute field '{attribute_field}' not found in joined data"}
                
                # Determine which fields to aggregate
                available_agg_fields = [f for f in aggregation_fields if f in joined.columns]
                
                if not available_agg_fields:
                    status_placeholder.empty()
                    return {"success": False, "error": "No aggregation fields found in data"}
                
                # Check if time-based separation is requested
                if separate_by_hour:
                    # Check if the specified hour field exists
                    if hour_field not in joined.columns:
                        _logger.warning(f"Time field '{hour_field}' not found in data, falling back to total aggregation")
                        separate_by_hour = False
                
                if separate_by_hour:
                    # Aggregate by zone AND time (keep as rows, not columns)
                    status_placeholder.info(f"📊 **Step 5/5:** Aggregating by zone and time (field: {hour_field})...")
                    _logger.info(f"Aggregating by zone and time using field '{hour_field}' (row-based)")
                    
                    # Group by zone and time field - output is row-based
                    agg_dict = {field: 'sum' for field in available_agg_fields}
                    aggregated = joined.groupby([attribute_field, hour_field]).agg(agg_dict).reset_index()
                    
                    _logger.info(f"Created time-based aggregation: {len(aggregated)} rows (zone × time)")
                    status_placeholder.info(f"📊 **Step 5/5:** Created {len(aggregated)} rows (zones × time periods)")
                else:
                    # Total aggregation (sum all time periods together)
                    status_placeholder.info(f"📊 **Step 5/5:** Aggregating by zone (total across all times)...")
                    agg_dict = {field: 'sum' for field in available_agg_fields}
                    aggregated = joined.groupby(attribute_field).agg(agg_dict).reset_index()
                    
                    _logger.info(f"Created total aggregation: {len(aggregated)} zones")
                
                # Merge back with shapefile to get geometries
                status_placeholder.info(f"📊 **Step 5/5:** Merging aggregated data with geometries...")
                # Note: If time-separated, each zone will have multiple rows (one per time period)
                result_gdf = shp.merge(aggregated, on=attribute_field, how='inner')
                
                # Important: When time-separated, the shapefile will have duplicate geometries
                # (same zone geometry repeated for each time period)
                
                # Save as shapefile to GIS output directory
                status_placeholder.info(f"💾 **Step 5/5:** Saving shapefile...")
                config = Config()
                output_dir = config.gis_output_path / f"{input_path.stem}{output_suffix}"
                output_dir.mkdir(exist_ok=True, parents=True)
                output_shp = output_dir / f"{input_path.stem}{output_suffix}.shp"
                
                result_gdf.to_file(output_shp)
                
                status_placeholder.success(f"✅ **Step 5/5:** Saved {len(result_gdf)} records to {output_shp.name}")
                status_placeholder.empty()
                
                _logger.info(f"shapefile_join success aggregated zones={len(result_gdf)} path={output_shp}")
                return {
                    "success": True,
                    "output_path": str(output_shp),
                    "zones": len(result_gdf),
                    "aggregated_fields": available_agg_fields,
                    "hourly_separation": separate_by_hour
                }
            else:
                # No aggregation - just join and save to GIS output directory
                status_placeholder.info(f"💾 **Step 5/5:** Saving shapefile (no aggregation)...")
                config = Config()
                output_dir = config.gis_output_path / f"{input_path.stem}{output_suffix}"
                output_dir.mkdir(exist_ok=True, parents=True)
                output_shp = output_dir / f"{input_path.stem}{output_suffix}.shp"
                
                joined.to_file(output_shp)
                
                status_placeholder.success(f"✅ **Step 5/5:** Saved {len(joined)} records to {output_shp.name}")
                status_placeholder.empty()
                
                _logger.info(f"shapefile_join success rows={len(joined)} path={output_shp}")
                return {
                    "success": True,
                    "output_path": str(output_shp),
                    "rows": len(joined)
                }
                
        except Exception as e:
            _logger.error(f"shapefile_join error: {e}")
            import traceback
            _logger.error(traceback.format_exc())
            return {"success": False, "error": str(e)}
