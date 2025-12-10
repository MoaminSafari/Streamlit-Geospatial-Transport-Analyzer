"""
Data Analysis Engine - Main API
================================

Unified API for running data analysis tasks on Snapp/Tapsi trip data.

Features:
    - Time-based filtering (month, year, season, custom)
    - Multiple operation types (aggregation, shapefile creation, analysis)
    - Flexible data source selection (Snapp, Tapsi, or both)
    - Automatic path management and output organization

Usage Example:
    from analysis_engine import DataAnalysisEngine
    
    engine = DataAnalysisEngine()
    
    # Run neighborhood aggregation for Mordad 1404
    result = engine.run_task(
        data_source="both",
        time_filter={"type": "specific_month", "year": "1404", "month": "05"},
        operations=["neighborhood_aggregation"]
    )
"""

import os
import sys
from pathlib import Path
from typing import Dict, List, Literal, Optional, Union, Any
from datetime import datetime
import pandas as pd
import geopandas as gpd
from dataclasses import dataclass, field
import json

# Import configuration
from config import Config


# ==========================================
# Utility Functions
# ==========================================

def aggregate_to_single_day_df(
    df: pd.DataFrame,
    fixed_date: str = "2025-01-01"
) -> pd.DataFrame:
    """
    Aggregate all dates in a temporal dataset into a single day by time only.
    
    Args:
        df: DataFrame with temporal data (must have time_bin_datetime column)
        fixed_date: Date to use for all records (default: "2025-01-01")
    
    Returns:
        DataFrame with aggregated data
    """
    # Extract only time (HH:MM)
    df['time_bin_datetime'] = pd.to_datetime(df['time_bin_datetime'])
    df['TIME'] = df['time_bin_datetime'].dt.strftime('%H:%M')
    
    # Group by CODE, NAME_MAHAL, and TIME - sum the counts
    aggregated = df.groupby(['CODE', 'NAME_MAHAL', 'TIME']).agg({
        'snapp_org_count': 'sum',
        'tapsi_org_count': 'sum',
        'total_origin': 'sum',
        'snapp_dst_count': 'sum',
        'tapsi_dst_count': 'sum',
        'total_destination': 'sum'
    }).reset_index()
    
    # Create new datetime with fixed date
    aggregated['time_bin_datetime'] = pd.to_datetime(fixed_date + ' ' + aggregated['TIME'])
    
    # Reorder columns
    final = aggregated[['CODE', 'NAME_MAHAL', 'time_bin_datetime', 'TIME',
                        'snapp_org_count', 'tapsi_org_count', 'total_origin',
                        'snapp_dst_count', 'tapsi_dst_count', 'total_destination']]
    
    return final


# ==========================================
# Type Definitions
# ==========================================

DataSource = Literal["snapp", "tapsi", "both"]
FilterType = Literal["all", "specific_month", "year", "season", "month_all_years", "custom"]
OperationType = Literal[
    "grid_aggregation_100m",
    "grid_temporal_aggregation_100m_30min",
    "neighborhood_aggregation_30min",
    "neighborhood_temporal_aggregation_30min",
    "shapefile_join_neighborhoods",
    "shapefile_join_neighborhoods_time",
    "shapefile_filter_peak_hours",
    "shapefile_add_regions",
    "od_matrix_by_neighborhood",
    "peak_hours_analysis",
    "temporal_pattern_analysis"
]


@dataclass
class TimeFilter:
    """
    Time filter configuration for data selection.
    
    Attributes:
        type: Type of filter (all, specific_month, year, season, etc.)
        year: Year in Persian calendar (e.g., "1404")
        month: Month number as string (e.g., "05" for Mordad)
        season: Season name (spring, summer, fall, winter)
        custom_patterns: Custom file patterns for Snapp and Tapsi
    """
    type: FilterType = "all"
    year: Optional[str] = None
    month: Optional[str] = None
    season: Optional[str] = None
    custom_patterns: Optional[Dict[str, List[str]]] = None
    
    def __post_init__(self):
        """Validate filter configuration."""
        if self.type == "specific_month" and (not self.year or not self.month):
            raise ValueError("specific_month requires both year and month")
        if self.type == "year" and not self.year:
            raise ValueError("year filter requires year parameter")
        if self.type == "season" and not self.season:
            raise ValueError("season filter requires season parameter")
        if self.type == "custom" and not self.custom_patterns:
            raise ValueError("custom filter requires custom_patterns")


@dataclass
class TaskResult:
    """
    Result of a data analysis task.
    
    Attributes:
        success: Whether the task completed successfully
        operation: Operation type that was executed
        outputs: Dictionary of output file paths
        metadata: Additional metadata (row counts, processing time, etc.)
        errors: List of error messages if any
    """
    success: bool
    operation: str
    outputs: Dict[str, Path] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    errors: List[str] = field(default_factory=list)
    
    def __repr__(self) -> str:
        status = "✅ SUCCESS" if self.success else "❌ FAILED"
        return (
            f"TaskResult({status})\n"
            f"  Operation: {self.operation}\n"
            f"  Outputs: {len(self.outputs)} file(s)\n"
            f"  Errors: {len(self.errors)}"
        )


# ==========================================
# Main Engine Class
# ==========================================

class DataAnalysisEngine:
    """
    Main engine for executing data analysis tasks.
    
    This class provides a high-level API for running various analysis operations
    on Snapp/Tapsi trip data with flexible filtering and output options.
    """
    
    def __init__(self, config: Optional[Config] = None):
        """
        Initialize the Data Analysis Engine.
        
        Args:
            config: Optional Config instance. If None, creates default config.
        """
        self.config = config or Config()
        self.results_history: List[TaskResult] = []
        
        print(f"🚀 Data Analysis Engine initialized")
        print(f"📁 Project root: {self.config.project_root}")
    
    # ==========================================
    # Main Task Execution
    # ==========================================
    
    def run_task(
        self,
        data_source: DataSource = "both",
        time_filter: Optional[Union[Dict, TimeFilter]] = None,
        operations: List[OperationType] = None,
        output_suffix: str = "",
        aggregate_to_single_day: bool = False,
        verbose: bool = True,
        operation_config: Optional[Dict] = None
    ) -> List[TaskResult]:
        """
        Run one or more analysis operations on the data.
        
        Args:
            data_source: Which data to process ("snapp", "tapsi", or "both")
            time_filter: Time filter configuration (dict or TimeFilter object)
            operations: List of operations to execute
            output_suffix: Optional suffix for output filenames
            aggregate_to_single_day: If True, aggregate all dates to single day by time
            verbose: Whether to print progress messages
            operation_config: Optional operation configuration (spatial/temporal aggregation, output format, etc.)
        
        Returns:
            List of TaskResult objects, one per operation
        
        Example:
            results = engine.run_task(
                data_source="both",
                time_filter={"type": "specific_month", "year": "1404", "month": "05"},
                operations=["neighborhood_aggregation_30min"],
                aggregate_to_single_day=True
            )
        """
        if operations is None:
            operations = ["neighborhood_aggregation_30min"]
        
        # Convert dict to TimeFilter if needed
        if isinstance(time_filter, dict):
            time_filter = TimeFilter(**time_filter)
        elif time_filter is None:
            time_filter = TimeFilter(type="all")
        
        results = []
        
        if verbose:
            print(f"\n{'='*60}")
            print(f"🎯 Starting Task Execution")
            print(f"{'='*60}")
            print(f"📊 Data Source: {data_source}")
            print(f"📅 Time Filter: {time_filter.type}")
            print(f"⚙️ Operations: {len(operations)}")
            print(f"{'='*60}\n")
        
        for i, operation in enumerate(operations, 1):
            if verbose:
                print(f"\n[{i}/{len(operations)}] Executing: {operation}")
                print(f"{'-'*60}")
            
            try:
                result = self._execute_operation(
                    operation=operation,
                    data_source=data_source,
                    time_filter=time_filter,
                    output_suffix=output_suffix,
                    aggregate_to_single_day=aggregate_to_single_day,
                    verbose=verbose,
                    operation_config=operation_config
                )
                results.append(result)
                self.results_history.append(result)
                
                if verbose:
                    if result.success:
                        print(f"✅ {operation} completed successfully")
                    else:
                        print(f"❌ {operation} failed: {result.errors}")
            
            except Exception as e:
                error_result = TaskResult(
                    success=False,
                    operation=operation,
                    errors=[str(e)]
                )
                results.append(error_result)
                self.results_history.append(error_result)
                
                if verbose:
                    print(f"❌ {operation} failed with exception: {e}")
        
        if verbose:
            print(f"\n{'='*60}")
            print(f"📊 Task Summary")
            print(f"{'='*60}")
            successful = sum(1 for r in results if r.success)
            print(f"✅ Successful: {successful}/{len(results)}")
            print(f"❌ Failed: {len(results) - successful}/{len(results)}")
            print(f"{'='*60}\n")
        
        return results
    
    # ==========================================
    # Operation Execution
    # ==========================================
    
    def _execute_operation(
        self,
        operation: OperationType,
        data_source: DataSource,
        time_filter: TimeFilter,
        output_suffix: str,
        aggregate_to_single_day: bool,
        verbose: bool,
        operation_config: Optional[Dict] = None
    ) -> TaskResult:
        """
        Execute a single operation.
        
        Args:
            operation: Operation type to execute
            data_source: Data source selection
            time_filter: Time filter configuration
            output_suffix: Output filename suffix
            verbose: Verbose output flag
        
        Returns:
            TaskResult object with execution results
        """
        # Map operations to execution methods
        operation_map = {
            "neighborhood_aggregation_30min": self._run_neighborhood_aggregation,
            "grid_temporal_aggregation_100m_30min": self._run_grid_temporal_aggregation,
            "od_matrix_by_neighborhood": self._run_od_matrix,
            "peak_hours_analysis": self._run_peak_hours_analysis,
            "temporal_pattern_analysis": self._run_temporal_pattern_analysis,
            "shapefile_join_neighborhoods": self._run_shapefile_join_neighborhoods,
        }
        
        if operation not in operation_map:
            return TaskResult(
                success=False,
                operation=operation,
                errors=[f"Operation '{operation}' not yet implemented"]
            )
        
        # Execute the operation
        execution_func = operation_map[operation]
        
        # Store operation config for use in execution methods
        if operation_config:
            self._current_operation_config = operation_config
        
        return execution_func(
            data_source=data_source,
            time_filter=time_filter,
            output_suffix=output_suffix,
            aggregate_to_single_day=aggregate_to_single_day,
            verbose=verbose,
            operation_config=operation_config
        )
    
    # ==========================================
    # File Filtering
    # ==========================================
    
    def get_filtered_files(
        self,
        data_source: DataSource,
        time_filter: TimeFilter
    ) -> Dict[str, List[Path]]:
        """
        Get list of files matching the data source and time filter.
        
        Args:
            data_source: Which data source to filter
            time_filter: Time filter configuration
        
        Returns:
            Dictionary with 'snapp' and 'tapsi' keys containing file lists
        """
        files = {"snapp": [], "tapsi": []}
        
        # Get file patterns based on filter type
        if time_filter.type == "all":
            snapp_patterns = ["*.csv"]
            tapsi_patterns = ["*.csv"]
        
        elif time_filter.type == "specific_month":
            # Snapp format: YYYYMM.csv (4-digit year + 2-digit month)
            # Example: year=1404, month=05 -> 140405.csv
            snapp_patterns = [f"{time_filter.year}{time_filter.month}.csv"]
            tapsi_patterns = [f"{time_filter.year}-{time_filter.month}.csv"]
        
        elif time_filter.type == "year":
            # Snapp: YYYYMM.csv format
            snapp_patterns = [f"{time_filter.year}*.csv"]
            tapsi_patterns = [f"{time_filter.year}-*.csv"]
        
        elif time_filter.type == "season":
            season_months = {
                "spring": ["01", "02", "03"],
                "summer": ["04", "05", "06"],
                "fall": ["07", "08", "09"],
                "winter": ["10", "11", "12"]
            }
            months = season_months.get(time_filter.season, [])
            if time_filter.year:
                # Snapp: YYYYMM.csv format
                snapp_patterns = [f"{time_filter.year}{m}.csv" for m in months]
                tapsi_patterns = [f"{time_filter.year}-{m}.csv" for m in months]
            else:
                snapp_patterns = [f"*{m}.csv" for m in months]
                tapsi_patterns = [f"*-{m}.csv" for m in months]
        
        elif time_filter.type == "month_all_years":
            # Snapp: Match any year with specific month (e.g., *05.csv for all Mordads)
            snapp_patterns = [f"*{time_filter.month}.csv"]
            tapsi_patterns = [f"*-{time_filter.month}.csv"]
        
        elif time_filter.type == "custom":
            snapp_patterns = time_filter.custom_patterns.get("snapp", [])
            tapsi_patterns = time_filter.custom_patterns.get("tapsi", [])
        
        else:
            return files
        
        # Collect matching files
        if data_source in ["snapp", "both"]:
            for pattern in snapp_patterns:
                files["snapp"].extend(self.config.snapp_raw_path.glob(pattern))
        
        if data_source in ["tapsi", "both"]:
            for pattern in tapsi_patterns:
                files["tapsi"].extend(self.config.tapsi_raw_path.glob(pattern))
        
        # Sort files
        files["snapp"] = sorted(files["snapp"])
        files["tapsi"] = sorted(files["tapsi"])
        
        return files
    
    # ==========================================
    # Helper Methods for Operation Config
    # ==========================================
    
    def _get_operation_params(self, operation_config: Optional[Dict] = None) -> Dict:
        """
        Get operation parameters from config or defaults.
        
        Args:
            operation_config: Optional operation configuration dict
        
        Returns:
            Dictionary with operation parameters
        """
        if operation_config is None:
            operation_config = {}
        
        # Get default params from config
        default_params = self.config.analysis_params
        
        # Override with operation_config if provided
        params = {
            "grid_size": default_params["grid_size"],
            "time_bin_minutes": default_params["time_bin_minutes"],
            "fixed_date": default_params["fixed_date"],
            "crs": default_params["crs"]
        }
        
        # Spatial aggregation
        spatial = operation_config.get("spatial_aggregation", {})
        if spatial.get("enabled"):
            params["grid_size"] = spatial.get("grid_size_value", params["grid_size"])
        
        # Temporal aggregation
        temporal = operation_config.get("temporal_aggregation", {})
        if temporal.get("enabled"):
            params["time_bin_minutes"] = temporal.get("time_bin_value", params["time_bin_minutes"])
        
        # Output format
        output = operation_config.get("output", {})
        params["output_csv"] = output.get("csv", True)
        params["output_shapefile"] = output.get("shapefile", False)
        params["output_both"] = output.get("both", False)
        
        # Shapefile join
        shapefile_join = operation_config.get("shapefile_join", {})
        params["shapefile_join_enabled"] = shapefile_join.get("enabled", False)
        params["shapefile_join_source"] = shapefile_join.get("shapefile_source", "neighborhoods")
        params["shapefile_join_path"] = shapefile_join.get("shapefile_path", "")
        params["shapefile_join_fields"] = shapefile_join.get("join_fields", [])
        params["shapefile_join_type"] = shapefile_join.get("join_type", "left")
        
        return params
    
    # ==========================================
    # Specific Operation Implementations
    # ==========================================
    
    def _run_neighborhood_aggregation(
        self,
        data_source: DataSource,
        time_filter: TimeFilter,
        output_suffix: str,
        aggregate_to_single_day: bool,
        verbose: bool,
        operation_config: Optional[Dict] = None
    ) -> TaskResult:
        """Run neighborhood-based aggregation with configurable time bins."""
        start_time = datetime.now()
        
        try:
            # Get operation parameters
            params = self._get_operation_params(operation_config)
            time_bin_minutes = params["time_bin_minutes"]
            
            # Import required modules
            from shapely.geometry import Point
            import glob
            
            # Get filtered files
            files = self.get_filtered_files(data_source, time_filter)
            total_files = len(files["snapp"]) + len(files["tapsi"])
            
            if total_files == 0:
                return TaskResult(
                    success=False,
                    operation="neighborhood_aggregation_30min",
                    errors=["No files found matching the filter criteria"]
                )
            
            if verbose:
                print(f"  📂 Found {len(files['snapp'])} Snapp files")
                print(f"  📂 Found {len(files['tapsi'])} Tapsi files")
                print(f"  ⚙️ Using time bin: {time_bin_minutes} minutes")
            
            # Load neighborhood shapefile
            if verbose:
                print(f"  🗺️ Loading neighborhoods shapefile...")
            
            neighborhoods = gpd.read_file(self.config.neighborhoods_shapefile)
            
            if verbose:
                print(f"  ✅ Loaded {len(neighborhoods)} neighborhoods")
            
            # Initialize aggregation dataframe
            all_data = []
            
            # Process each file
            for i, (source, file_list) in enumerate([("snapp", files["snapp"]), ("tapsi", files["tapsi"])]):
                if not file_list:
                    continue
                
                for j, file_path in enumerate(file_list, 1):
                    if verbose:
                        print(f"  📄 Processing {source}: {file_path.name} ({j}/{len(file_list)})")
                    
                    # Process in chunks to avoid memory issues
                    chunk_size = 500000  # Process 500k rows at a time
                    file_org_counts = []
                    file_dst_counts = []
                    
                    # Read CSV with appropriate settings for each source
                    if source == "snapp":
                        chunks = pd.read_csv(
                            file_path,
                            header=None,
                            names=['id', 'date', 'org_lat', 'org_long', 'dst_lat', 'dst_long', 
                                   'num', 'origin_datetime', 'destination_datetime'],
                            chunksize=chunk_size,
                            usecols=['org_lat', 'org_long', 'dst_lat', 'dst_long', 'origin_datetime']
                        )
                    else:  # tapsi
                        chunks = pd.read_csv(
                            file_path,
                            chunksize=chunk_size,
                            usecols=['originLatitude', 'originLongitude', 'destinationLatitude', 
                                    'destinationLongitude', 'startTime']
                        )
                    
                    for chunk_idx, df in enumerate(chunks):
                        # Rename Tapsi columns
                        if source == "tapsi":
                            df = df.rename(columns={
                                'originLatitude': 'org_lat',
                                'originLongitude': 'org_long',
                                'destinationLatitude': 'dst_lat',
                                'destinationLongitude': 'dst_long',
                                'startTime': 'origin_datetime'
                            })
                        
                        # Convert to time bins (remove timezone to avoid comparison issues)
                        df['origin_datetime'] = pd.to_datetime(df['origin_datetime'], errors='coerce').dt.tz_localize(None)
                        df['time_bin'] = df['origin_datetime'].dt.floor(f"{time_bin_minutes}T")
                        
                        # Process origins - vectorized Point creation
                        df['geometry_org'] = gpd.points_from_xy(df['org_long'], df['org_lat'])
                        gdf_org = gpd.GeoDataFrame(df[['geometry_org', 'time_bin']], 
                                                   geometry='geometry_org', 
                                                   crs=self.config.analysis_params['crs'])
                        
                        # Reproject to match neighborhoods CRS for accurate spatial join
                        gdf_org = gdf_org.to_crs(neighborhoods.crs)
                        
                        # Spatial join for origins
                        joined_org = gpd.sjoin(gdf_org, neighborhoods[['CODE', 'geometry']], 
                                              how='left', predicate='within')
                        org_counts = joined_org.groupby(['CODE', 'time_bin']).size().reset_index(name='count')
                        file_org_counts.append(org_counts)
                        
                        # Process destinations - vectorized Point creation
                        df['geometry_dst'] = gpd.points_from_xy(df['dst_long'], df['dst_lat'])
                        gdf_dst = gpd.GeoDataFrame(df[['geometry_dst', 'time_bin']], 
                                                   geometry='geometry_dst',
                                                   crs=self.config.analysis_params['crs'])
                        
                        # Reproject to match neighborhoods CRS for accurate spatial join
                        gdf_dst = gdf_dst.to_crs(neighborhoods.crs)
                        
                        # Spatial join for destinations
                        joined_dst = gpd.sjoin(gdf_dst, neighborhoods[['CODE', 'geometry']], 
                                              how='left', predicate='within')
                        dst_counts = joined_dst.groupby(['CODE', 'time_bin']).size().reset_index(name='count')
                        file_dst_counts.append(dst_counts)
                        
                        # Clear memory
                        del df, gdf_org, gdf_dst, joined_org, joined_dst
                    
                    # Aggregate all chunks for this file
                    org_agg = pd.concat(file_org_counts).groupby(['CODE', 'time_bin'])['count'].sum().reset_index(name=f'{source}_org_count')
                    dst_agg = pd.concat(file_dst_counts).groupby(['CODE', 'time_bin'])['count'].sum().reset_index(name=f'{source}_dst_count')
                    
                    # Merge and append
                    merged = pd.merge(org_agg, dst_agg, on=['CODE', 'time_bin'], how='outer').fillna(0)
                    all_data.append(merged)
            
            # Combine all data
            if verbose:
                print(f"  🔄 Combining all aggregations...")
            
            combined = pd.concat(all_data, ignore_index=True)
            
            # Group by neighborhood and time
            final = combined.groupby(['CODE', 'time_bin']).sum().reset_index()
            
            # Add total columns
            if 'snapp_org_count' in final.columns and 'tapsi_org_count' in final.columns:
                final['total_origin'] = final['snapp_org_count'] + final['tapsi_org_count']
                final['total_destination'] = final['snapp_dst_count'] + final['tapsi_dst_count']
            
            # Join with neighborhood info
            final = final.merge(
                neighborhoods[['CODE', 'NAME_MAHAL', 'geometry']],
                on='CODE',
                how='left'
            )
            
            # Fix time_bin datetime - remove timezone info to avoid comparison issues
            fixed_date = pd.to_datetime(self.config.analysis_params['fixed_date']).tz_localize(None)
            final['time_bin'] = pd.to_datetime(final['time_bin']).dt.tz_localize(None)
            final['time_bin_datetime'] = final['time_bin'].apply(
                lambda x: fixed_date + pd.Timedelta(
                    hours=x.hour,
                    minutes=x.minute
                )
            )
            
            # If aggregate_to_single_day is True, use utility function
            if aggregate_to_single_day:
                if verbose:
                    print(f"  📅 Aggregating all dates to single day...")
                
                # Use the utility function for single day aggregation
                final = aggregate_to_single_day_df(
                    df=final,
                    fixed_date=fixed_date.strftime('%Y-%m-%d')
                )
                
                # Re-merge geometry (it was lost in aggregation)
                final = final.merge(
                    neighborhoods[['CODE', 'geometry']],
                    on='CODE',
                    how='left'
                )
            
            # Generate output filename
            filter_desc = f"{time_filter.year}_{time_filter.month}" if time_filter.type == "specific_month" else time_filter.type
            outputs = {}
            
            # Prepare CSV columns
            csv_columns = ['CODE', 'NAME_MAHAL', 'time_bin_datetime', 
                          'snapp_org_count', 'tapsi_org_count', 'total_origin',
                          'snapp_dst_count', 'tapsi_dst_count', 'total_destination']
            
            # Save CSV if requested
            if params["output_csv"]:
                output_csv = self.config.aggregated_path / f"neighborhood_aggregation_{time_bin_minutes}min_{filter_desc}{output_suffix}.csv"
                final[csv_columns].to_csv(output_csv, index=False)
                outputs["csv"] = output_csv
                if verbose:
                    print(f"  💾 CSV saved: {output_csv.name}")
            
            # Save shapefile if requested
            if params["output_shapefile"]:
                output_shp_dir = self.config.gis_output_path / f"neighborhoods_{time_bin_minutes}min_{filter_desc}{output_suffix}"
                output_shp = output_shp_dir / "neighborhoods_aggregated.shp"
                output_shp_dir.mkdir(parents=True, exist_ok=True)
                
                # Add TIME column as string format HH:MM for shapefile
                if 'TIME' not in final.columns:
                    final['TIME'] = final['time_bin_datetime'].dt.strftime('%H:%M')
                
                # Handle shapefile join if enabled
                if params["shapefile_join_enabled"]:
                    if verbose:
                        print(f"  🔗 Joining with shapefile: {params['shapefile_join_source']}")
                    
                    # Load join shapefile
                    if params["shapefile_join_source"] == "custom":
                        join_gdf = gpd.read_file(params["shapefile_join_path"])
                    else:
                        # Use dynamic shapefile path discovery
                        shp_path = self.config.get_shapefile_path(params["shapefile_join_source"])
                        join_gdf = gpd.read_file(shp_path)
                    
                    # Select join fields
                    join_fields = params["shapefile_join_fields"]
                    if join_fields:
                        available_fields = [f for f in join_fields if f in join_gdf.columns]
                        if available_fields:
                            # Perform spatial join
                            final_gdf = gpd.GeoDataFrame(final, geometry='geometry', crs=neighborhoods.crs)
                            joined = gpd.sjoin(
                                final_gdf,
                                join_gdf[available_fields + ['geometry']],
                                how=params["shapefile_join_type"],
                                predicate='within'
                            )
                            final = joined.drop(columns=['index_right'] if 'index_right' in joined.columns else [])
                            if verbose:
                                print(f"  ✅ Joined with fields: {', '.join(available_fields)}")
                
                gdf_final = gpd.GeoDataFrame(final, geometry='geometry', crs=neighborhoods.crs)
                gdf_final.to_file(output_shp)
                outputs["shapefile"] = output_shp
                if verbose:
                    print(f"  💾 Shapefile saved: {output_shp.name}")
            
            elapsed = (datetime.now() - start_time).total_seconds()
            
            return TaskResult(
                success=True,
                operation="neighborhood_aggregation_30min",
                outputs=outputs,
                metadata={
                    "total_files_processed": total_files,
                    "total_records": len(final),
                    "neighborhoods": len(final['CODE'].unique()),
                    "time_bins": len(final['time_bin_datetime'].unique()),
                    "time_bin_minutes": time_bin_minutes,
                    "processing_time_seconds": elapsed
                }
            )
        
        except Exception as e:
            return TaskResult(
                success=False,
                operation="neighborhood_aggregation_30min",
                errors=[f"Exception during execution: {str(e)}"]
            )
    
    def _run_grid_temporal_aggregation(
        self,
        data_source: DataSource,
        time_filter: TimeFilter,
        output_suffix: str,
        aggregate_to_single_day: bool,
        verbose: bool,
        operation_config: Optional[Dict] = None,
        **kwargs
    ) -> TaskResult:
        """Run grid-based temporal aggregation (100m grid, 30min bins)."""
        return TaskResult(
            success=False,
            operation="grid_temporal_aggregation_100m_30min",
            errors=["Not yet implemented - use existing notebook"]
        )
    
    def _run_od_matrix(
        self,
        data_source: DataSource,
        time_filter: TimeFilter,
        output_suffix: str,
        aggregate_to_single_day: bool,
        verbose: bool,
        operation_config: Optional[Dict] = None,
        **kwargs
    ) -> TaskResult:
        """Generate origin-destination matrix by neighborhoods."""
        return TaskResult(
            success=False,
            operation="od_matrix_by_neighborhood",
            errors=["Not yet implemented - use existing notebook"]
        )
    
    def _run_peak_hours_analysis(
        self,
        data_source: DataSource,
        time_filter: TimeFilter,
        output_suffix: str,
        aggregate_to_single_day: bool,
        verbose: bool,
        operation_config: Optional[Dict] = None,
        **kwargs
    ) -> TaskResult:
        """Analyze peak hours and traffic patterns."""
        return TaskResult(
            success=False,
            operation="peak_hours_analysis",
            errors=["Not yet implemented - use existing script"]
        )
    
    def _run_temporal_pattern_analysis(
        self,
        data_source: DataSource,
        time_filter: TimeFilter,
        output_suffix: str,
        aggregate_to_single_day: bool,
        verbose: bool,
        operation_config: Optional[Dict] = None,
        **kwargs
    ) -> TaskResult:
        """Analyze temporal patterns in trip data."""
        return TaskResult(
            success=False,
            operation="temporal_pattern_analysis",
            errors=["Not yet implemented - use existing notebook"]
        )
    
    def _run_shapefile_join_neighborhoods(
        self,
        data_source: DataSource,
        time_filter: TimeFilter,
        output_suffix: str,
        aggregate_to_single_day: bool,
        verbose: bool,
        operation_config: Optional[Dict] = None,
        **kwargs
    ) -> TaskResult:
        """Join shapefile with neighborhood aggregation data."""
        return TaskResult(
            success=False,
            operation="shapefile_join_neighborhoods",
            errors=["Not yet implemented - use existing script"]
        )
    
    # ==========================================
    # Utility Methods
    # ==========================================
    
    def print_results_summary(self):
        """Print summary of all executed tasks."""
        if not self.results_history:
            print("ℹ️ No tasks have been executed yet")
            return
        
        print(f"\n{'='*60}")
        print(f"📊 Results History ({len(self.results_history)} tasks)")
        print(f"{'='*60}")
        
        for i, result in enumerate(self.results_history, 1):
            status = "✅" if result.success else "❌"
            print(f"\n{i}. {status} {result.operation}")
            
            if result.outputs:
                print(f"   📁 Outputs:")
                for output_type, path in result.outputs.items():
                    print(f"      • {output_type}: {path.name}")
            
            if result.metadata:
                print(f"   📊 Metadata:")
                for key, value in result.metadata.items():
                    print(f"      • {key}: {value}")
            
            if result.errors:
                print(f"   ❌ Errors:")
                for error in result.errors:
                    print(f"      • {error}")
        
        print(f"\n{'='*60}\n")
    
    def save_results_log(self, output_path: Optional[Path] = None):
        """
        Save execution results to a JSON log file.
        
        Args:
            output_path: Optional custom output path. 
                        If None, saves to Dataset/Summary/task_results_log.json
        """
        if output_path is None:
            output_path = self.config.summary_path / "task_results_log.json"
        
        # Convert results to serializable format
        log_data = {
            "timestamp": datetime.now().isoformat(),
            "total_tasks": len(self.results_history),
            "successful_tasks": sum(1 for r in self.results_history if r.success),
            "results": []
        }
        
        for result in self.results_history:
            log_data["results"].append({
                "success": result.success,
                "operation": result.operation,
                "outputs": {k: str(v) for k, v in result.outputs.items()},
                "metadata": result.metadata,
                "errors": result.errors
            })
        
        # Save to file
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(log_data, f, indent=2, ensure_ascii=False)
        
        print(f"💾 Results log saved to: {output_path}")


# ==========================================
# Convenience function
# ==========================================

def create_engine(config: Optional[Config] = None) -> DataAnalysisEngine:
    """
    Factory function to create a DataAnalysisEngine instance.
    
    Args:
        config: Optional Config instance
    
    Returns:
        Configured DataAnalysisEngine instance
    """
    return DataAnalysisEngine(config)


if __name__ == "__main__":
    # Demo code
    print("=" * 60)
    print("Data Analysis Engine - Demo")
    print("=" * 60)
    
    # Create engine
    engine = DataAnalysisEngine()
    
    # Example 1: Run neighborhood aggregation for Mordad 1404
    print("\n📌 Example 1: Neighborhood aggregation for Mordad 1404")
    results = engine.run_task(
        data_source="both",
        time_filter={"type": "specific_month", "year": "1404", "month": "05"},
        operations=["neighborhood_aggregation_30min"]
    )
    
    # Print results
    engine.print_results_summary()
