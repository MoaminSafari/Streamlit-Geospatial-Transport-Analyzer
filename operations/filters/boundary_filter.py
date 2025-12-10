"""
Boundary Filter Operation - Complete with UI and execution
"""

import streamlit as st
import pandas as pd
import geopandas as gpd
from shapely.geometry import Point
import logging
from typing import Dict, Any, Optional
from pathlib import Path
from operations.base import BaseOperation
from operations.config import BOUNDARY_SOURCES, FILTER_FIELD_OPTIONS, OUTPUT_FORMATS
from ui_helpers import utils
from config import Config

# Setup logger
_logger = logging.getLogger("boundary_filter")


class BoundaryFilterOperation(BaseOperation):
    """Filter data by geographic boundaries"""
    
    def get_metadata(self) -> Dict[str, str]:
        return {
            'key': 'boundary_filter',
            'title': 'Boundary Filter',
            'description': 'Filter data by geographic boundaries',
            'category': 'filters'
        }
    
    def render_ui(self) -> Optional[Dict[str, Any]]:
        """Render UI and return params if Run clicked"""
        
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
            # Get aggregated files
            aggregated_files = utils.get_aggregated_files()
            if not aggregated_files:
                st.warning("⚠️ No aggregated files found. Please run an analysis first.")
                return None
            file_options = {f.name: str(f) for f in aggregated_files}
            
            st.markdown("### Configuration")
            col1, col2 = st.columns(2)
            with col1:
                selected_file = st.selectbox("Input file:", options=list(file_options.keys()))
            with col2:
                filter_field = st.selectbox("Filter field:", 
                                           options=list(FILTER_FIELD_OPTIONS.keys()),
                                           format_func=lambda x: FILTER_FIELD_OPTIONS[x])
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
            filter_field = st.selectbox("Filter field:", 
                                       options=list(FILTER_FIELD_OPTIONS.keys()),
                                       format_func=lambda x: FILTER_FIELD_OPTIONS[x])
        
        col3, col4 = st.columns(2)
        with col3:
            boundary_options = list(BOUNDARY_SOURCES.keys()) + ["shapefile"]
            boundary_labels = {**BOUNDARY_SOURCES, "shapefile": "Custom Shapefile"}
            boundary_source = st.selectbox("Boundary source:", 
                                          options=boundary_options,
                                          format_func=lambda x: boundary_labels[x])
        with col4:
            output_format = st.selectbox("Output format:", options=OUTPUT_FORMATS)
        
        # Inside/Outside selection
        st.markdown("**🎯 Filter mode:**")
        filter_mode = st.radio(
            "Keep points:",
            options=["inside", "outside"],
            format_func=lambda x: {
                "inside": "✅ Inside boundary (نقاط داخل محدوده)",
                "outside": "❌ Outside boundary (نقاط خارج محدوده)"
            }[x],
            index=0,
            horizontal=True,
            help="Choose whether to keep points inside or outside the boundary"
        )
        
        config_obj = Config()
        if boundary_source == "shapefile":
            boundary_path = st.text_input("Shapefile path:", value="")
        else:
            # Use dynamic shapefile path discovery
            boundary_path = str(config_obj.get_shapefile_path(boundary_source))
            st.caption(f"📁 {boundary_path}")
        
        # Auto-generate suffix based on time filter and boundary
        time_suffix = utils.get_time_filter_suffix()
        default_suffix = f"_{time_suffix}_{boundary_source}_boundary_filtered"
        output_suffix = st.text_input("Output suffix:", value=default_suffix)
        
        if st.button("▶️ Run", type="primary", width='stretch'):
            params = {
                'boundary_source': boundary_source,
                'boundary_path': boundary_path,
                'filter_field': filter_field,
                'filter_mode': filter_mode,
                'output_suffix': output_suffix,
                'output_format': output_format,
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
        """Execute boundary filter"""
        boundary_source = kwargs['boundary_source']
        boundary_path = kwargs.get('boundary_path')
        filter_field = kwargs['filter_field']
        filter_mode = kwargs.get('filter_mode', 'inside')
        output_suffix = kwargs['output_suffix']
        output_format = kwargs['output_format']
        data_source_type = kwargs.get('data_source_type', 'aggregated')
        use_global_filter = kwargs.get('use_global_filter', False)
        
        try:
            _logger.info(f"boundary_filter start source={boundary_source} use_global={use_global_filter}")
            
            # Create a placeholder for status updates
            import streamlit as st
            status_placeholder = st.empty()
            
            # Load data based on source type
            if use_global_filter:
                status_placeholder.info("📂 **Step 1/4:** Loading raw dataset files...")
                
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
                status_placeholder.info(f"📂 **Step 1/4:** Found {total_files} files ({len(files['snapp'])} Snapp, {len(files['tapsi'])} Tapsi)")
                
                # Load ALL columns (don't filter by column)
                all_dfs = []
                chunk_size = 100000  # Process 100k rows at a time
                
                # Process Snapp files - load ALL columns
                for idx, snapp_file in enumerate(files['snapp'], 1):
                    status_placeholder.info(f"📂 **Step 1/4:** Loading Snapp file {idx}/{len(files['snapp'])}: {snapp_file.name}")
                    _logger.info(f"Loading Snapp file: {snapp_file.name}")
                    
                    # Read ALL columns in chunks
                    df_temp = pd.read_csv(
                        snapp_file, 
                        header=None, 
                        names=DataColumnMetadata.get_snapp_columns(),
                        chunksize=chunk_size
                    )
                    # Combine chunks
                    df_temp = pd.concat(df_temp, ignore_index=True)
                    all_dfs.append(df_temp)
                
                # Process Tapsi files - load ALL columns
                for idx, tapsi_file in enumerate(files['tapsi'], 1):
                    status_placeholder.info(f"📂 **Step 1/4:** Loading Tapsi file {idx}/{len(files['tapsi'])}: {tapsi_file.name}")
                    _logger.info(f"Loading Tapsi file: {tapsi_file.name}")
                    
                    # Read ALL columns in chunks
                    df_temp = pd.read_csv(
                        tapsi_file,
                        chunksize=chunk_size
                    )
                    # Combine chunks
                    df_temp = pd.concat(df_temp, ignore_index=True)
                    
                    # Apply column mapping for ALL columns
                    tapsi_mapping = DataColumnMetadata.get_tapsi_mapping()
                    df_temp.rename(columns=tapsi_mapping, inplace=True)
                    all_dfs.append(df_temp)
                
                # Combine all dataframes
                status_placeholder.info(f"📂 **Step 1/4:** Combining {total_files} files...")
                df = pd.concat(all_dfs, ignore_index=True)
                _logger.info(f"Combined {total_files} files with {len(df)} total rows")
                
                # Clear memory
                del all_dfs
                import gc
                gc.collect()
                
            else:
                status_placeholder.info("📂 **Step 1/4:** Loading aggregated file...")
                # Use single selected file (aggregated)
                input_file = kwargs['input_file']
                _logger.info(f"Loading aggregated file: {input_file}")
                df = pd.read_csv(input_file)
            
            total_count = len(df)
            status_placeholder.success(f"✅ **Step 1/4:** Loaded {total_count:,} records")
            
            # Load boundary
            status_placeholder.info(f"🗺️ **Step 2/4:** Loading boundary shapefile ({boundary_source})...")
            config = Config()
            if boundary_source == "shapefile":
                if not boundary_path or not Path(boundary_path).exists():
                    status_placeholder.empty()
                    return {"success": False, "error": "Boundary shapefile not found"}
                boundary_gdf = gpd.read_file(boundary_path)
            else:
                # Use dynamic shapefile path discovery
                shp_path = config.get_shapefile_path(boundary_source)
                if not shp_path.exists():
                    status_placeholder.empty()
                    return {"success": False, "error": f"Shapefile not found: {shp_path}"}
                boundary_gdf = gpd.read_file(shp_path)
            
            status_placeholder.success(f"✅ **Step 2/4:** Loaded boundary with {len(boundary_gdf)} zones")
            
            # Determine coordinate columns (try camelCase first, then snake_case)
            status_placeholder.info(f"🎯 **Step 3/4:** Preparing spatial filtering (field: {filter_field})...")
            
            if filter_field == "origin":
                lat_col = next((c for c in ['originLatitude', 'org_lat', 'origin_lat'] if c in df.columns), None)
                lon_col = next((c for c in ['originLongitude', 'org_lng', 'org_long', 'origin_lng', 'origin_long'] if c in df.columns), None)
            elif filter_field == "destination":
                lat_col = next((c for c in ['destinationLatitude', 'dst_lat', 'dest_lat', 'destination_lat'] if c in df.columns), None)
                lon_col = next((c for c in ['destinationLongitude', 'dst_lng', 'dst_long', 'dest_lng', 'dest_long'] if c in df.columns), None)
            else:
                possible_lat = ["originLatitude", "destinationLatitude", "org_lat", "dst_lat", "origin_lat", "dest_lat", "latitude", "lat"]
                possible_lon = ["originLongitude", "destinationLongitude", "org_lng", "org_long", "dst_lng", "dst_long", "origin_lng", "dest_lng", "longitude", "lon", "lng"]
                lat_col = next((col for col in possible_lat if col in df.columns), None)
                lon_col = next((col for col in possible_lon if col in df.columns), None)
            
            if not lat_col or not lon_col:
                status_placeholder.empty()
                return {"success": False, "error": f"Coordinate columns not found. Available: {list(df.columns)}"}
            
            # Create points using vectorized operations (much faster)
            status_placeholder.info(f"🎯 **Step 3/4:** Creating point geometries...")
            
            # Check for valid coordinates
            valid_mask = df[lat_col].notna() & df[lon_col].notna()
            
            if valid_mask.sum() == 0:
                status_placeholder.empty()
                return {"success": False, "error": "No valid coordinates"}
            
            # Create GeoDataFrame with ALL columns, but use only valid coordinates for geometry
            # Use vectorized point creation (faster than list comprehension)
            geometry = gpd.points_from_xy(df.loc[valid_mask, lon_col], df.loc[valid_mask, lat_col])
            points_gdf = gpd.GeoDataFrame(df[valid_mask], geometry=geometry, crs="EPSG:4326")
            
            # Store original dataframe indices for later filtering
            original_indices = points_gdf.index
            
            if points_gdf.crs != boundary_gdf.crs:
                status_placeholder.info(f"🎯 **Step 3/4:** Reprojecting coordinates to match boundary CRS...")
                points_gdf = points_gdf.to_crs(boundary_gdf.crs)
            
            # Spatial join - process in batches if dataset is large
            mode_text = "inside" if filter_mode == "inside" else "outside"
            status_placeholder.info(f"🎯 **Step 3/4:** Performing spatial filtering ({mode_text} boundary, checking {len(points_gdf):,} points)...")
            
            if len(points_gdf) > 500000:
                # Process in batches for large datasets
                batch_size = 100000
                filtered_indices = []
                
                for i in range(0, len(points_gdf), batch_size):
                    batch = points_gdf.iloc[i:i+batch_size]
                    joined_batch = gpd.sjoin(batch, boundary_gdf, how='inner', predicate='within')
                    
                    if filter_mode == "inside":
                        # Keep points that ARE inside (matched)
                        filtered_indices.extend(joined_batch.index.tolist())
                    else:
                        # Keep points that are NOT inside (not matched)
                        outside_indices = batch.index.difference(joined_batch.index)
                        filtered_indices.extend(outside_indices.tolist())
                    
                    # Update progress
                    progress = min(100, int((i + batch_size) / len(points_gdf) * 100))
                    status_placeholder.info(f"🎯 **Step 3/4:** Filtering... {progress}%")
                    
                    # Clear batch from memory
                    del batch, joined_batch
                    import gc
                    gc.collect()
                
                # Get filtered dataframe using original indices - this keeps ALL columns
                filtered_df = df.loc[filtered_indices].copy()
            else:
                # Process all at once for smaller datasets
                joined = gpd.sjoin(points_gdf, boundary_gdf, how='inner', predicate='within')
                
                if filter_mode == "inside":
                    # Keep points that ARE inside (matched)
                    filtered_df = df.loc[joined.index].copy()
                else:
                    # Keep points that are NOT inside (not matched)
                    outside_indices = points_gdf.index.difference(joined.index)
                    filtered_df = df.loc[outside_indices].copy()
                
                del joined
            
            filtered_count = len(filtered_df)
            
            # Clear memory
            del points_gdf, df
            import gc
            gc.collect()
            
            filter_percentage = (filtered_count / total_count * 100) if total_count > 0 else 0
            status_placeholder.success(f"✅ **Step 3/4:** Filtered to {filtered_count:,} records ({filter_percentage:.1f}% of original)")
            
            # Save output
            status_placeholder.info(f"💾 **Step 4/4:** Saving output as {output_format.upper()}...")
            
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
                input_file = kwargs['input_file']
                input_path = Path(input_file)
            
            config = Config()
            if output_format == "csv":
                output_path = config.aggregated_path / f"{input_path.stem}{output_suffix}.csv"
                filtered_df.to_csv(output_path, index=False)
            else:
                # Save to GIS output directory
                output_dir = config.gis_output_path / f"{input_path.stem}{output_suffix}"
                output_dir.mkdir(exist_ok=True, parents=True)
                # Use vectorized point creation
                filtered_geometry = gpd.points_from_xy(filtered_df[lon_col], filtered_df[lat_col])
                filtered_gdf = gpd.GeoDataFrame(filtered_df, geometry=filtered_geometry, crs="EPSG:4326")
                output_path = output_dir / f"{input_path.stem}{output_suffix}.shp"
                filtered_gdf.to_file(output_path)
            
            status_placeholder.success(f"✅ **Step 4/4:** Saved to {output_path.name}")
            status_placeholder.empty()
            
            _logger.info(f"boundary_filter success rows={filtered_count}")
            return {
                "success": True,
                "filtered_count": filtered_count,
                "total_count": total_count,
                "output_path": str(output_path)
            }
            
        except Exception as e:
            _logger.error(f"boundary_filter error: {e}")
            return {"success": False, "error": str(e)}
