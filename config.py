"""
Configuration Module for Data Analysis Project
==============================================

This module provides centralized path management and project configuration.
All scripts and notebooks should import paths from this module to ensure consistency.

Usage:
    from config import Config
    
    config = Config()
    print(config.raw_data_path)
    print(config.snapp_raw_path)
"""

import os
from pathlib import Path
from typing import Dict, Optional


class DataColumnMetadata:
    """
    Metadata for data column structure (Snapp, Tapsi).
    """
    
    # Standard columns (internal system format)
    STANDARD_COLUMNS = {
        'id': 'id',
        'date': 'reg_date',
        'org_lat': 'org_lat',
        'org_lng': 'org_lng',
        'dst_lat': 'dst_lat',
        'dst_lng': 'dst_lng',
        'distance': 'distance',
        'start_time': 'start_time',
        'end_time': 'end_time'
    }
    
    # Snapp columns (no header - order matters)
    SNAPP_COLUMNS = ['id', 'reg_date', 'org_lat', 'org_lng', 'dst_lat', 'dst_lng', 'distance', 'start_time', 'end_time']
    
    # Mapping from Tapsi to standard format
    TAPSI_COLUMN_MAPPING = {
        "originLatitude": "org_lat",
        "originLongitude": "org_lng",
        "destinationLatitude": "dst_lat",
        "destinationLongitude": "dst_lng",
        "startTime": "start_time",
        "endTime": "end_time"
    }
    
    @classmethod
    def get_snapp_columns(cls):
        """Return list of Snapp columns"""
        return cls.SNAPP_COLUMNS.copy()
    
    @classmethod
    def get_tapsi_mapping(cls):
        """Return mapping from Tapsi to standard format"""
        return cls.TAPSI_COLUMN_MAPPING.copy()


class Config:
    """
    Centralized configuration for the Data Analysis project.
    
    Automatically detects the project root and provides all necessary paths
    as both absolute paths and relative paths from the Helper Scripts directory.
    """
    
    def __init__(self, project_root: Optional[str] = None):
        """
        Initialize configuration with automatic or manual project root detection.
        
        Args:
            project_root: Optional manual override for project root path.
                         If None, auto-detects based on current file location.
        """
        if project_root:
            self._project_root = Path(project_root)
        else:
            # Auto-detect: Go up from Helper Scripts to Data Analysis folder
            self._project_root = Path(__file__).parent.parent
        
        # Validate that we found the correct directory
        if not (self._project_root / "Dataset").exists():
            raise ValueError(
                f"Invalid project root: {self._project_root}\n"
                "Expected to find 'Dataset' folder in project root."
            )
    
    # ==========================================
    # Core Project Paths
    # ==========================================
    
    @property
    def project_root(self) -> Path:
        """Root directory of the Data Analysis project."""
        return self._project_root
    
    @property
    def helper_scripts_path(self) -> Path:
        """Path to Helper Scripts directory."""
        return self._project_root / "Helper Scripts"
    
    # ==========================================
    # Dataset Paths
    # ==========================================
    
    @property
    def dataset_path(self) -> Path:
        """Root dataset directory."""
        return self._project_root / "Dataset"
    
    @property
    def raw_data_path(self) -> Path:
        """Raw data directory."""
        return self.dataset_path / "Raw"
    
    @property
    def snapp_raw_path(self) -> Path:
        """Snapp raw data directory."""
        return self.raw_data_path / "Snapp Raw"
    
    @property
    def tapsi_raw_path(self) -> Path:
        """Tapsi raw data directory."""
        return self.raw_data_path / "Tapsi Raw"
    
    @property
    def aggregated_path(self) -> Path:
        """Aggregated/processed data output directory."""
        return self.dataset_path / "Aggregated"
    
    @property
    def summary_path(self) -> Path:
        """Dataset summary and analysis results directory."""
        return self.dataset_path / "Summary"

    @property
    def logs_path(self) -> Path:
        path = self.summary_path / "Logs"
        path.mkdir(parents=True, exist_ok=True)
        return path

    @property
    def ops_log_file(self) -> Path:
        return self.logs_path / "ops.log"
    
    # ==========================================
    # GIS Paths
    # ==========================================
    
    @property
    def gis_files_path(self) -> Path:
        """Root GIS files directory."""
        return self._project_root / "GIS FIles"
    
    @property
    def gis_layers_path(self) -> Path:
        """GIS layers directory."""
        return self.gis_files_path / "Layers"
    
    @property
    def neighborhoods_shapefile(self) -> Path:
        """Neighborhoods shapefile (neighborhood.shp)."""
        # Check common locations
        possible_paths = [
            self.gis_layers_path / "neighborhood" / "neighborhood.shp",
            self.gis_layers_path / "Neighborhoods" / "mahale.shp",
            self.gis_layers_path / "Neighbor" / "mahale.shp",
        ]
        for path in possible_paths:
            if path.exists():
                return path
        # Return first option as default
        return possible_paths[0]
    
    @property
    def districts_shapefile(self) -> Path:
        """Districts shapefile."""
        possible_paths = [
            self.gis_layers_path / "district" / "district.shp",
            self.gis_layers_path / "Districts" / "districts.shp",
            self.gis_layers_path / "Districts" / "district.shp",
            self.gis_layers_path / "Districts"
        ]
        for path in possible_paths:
            if path.exists():
                return path
        return possible_paths[0]
    
    @property
    def subregions_shapefile(self) -> Path:
        """Subregions shapefile."""
        possible_paths = [
            self.gis_layers_path / "Subregion" / "subregion.shp",
            self.gis_layers_path / "Subregions" / "subregions.shp",
            self.gis_layers_path / "Subregion"
        ]
        for path in possible_paths:
            if path.exists():
                return path
        return possible_paths[0]

    @property
    def traffic_zones_shapefile(self) -> Path:
        """Traffic zones shapefile."""
        possible_paths = [
            self.gis_layers_path / "traffic_zone" / "traffic_zone.shp",
            self.gis_layers_path / "TrafficZones" / "traffic_zones.shp",
            self.gis_layers_path / "Traffic Zone" / "traffic_zone.shp",
            self.gis_layers_path / "traffic_zone"
        ]
        for path in possible_paths:
            if path.exists():
                return path
        return possible_paths[0]
    
    @property
    def gis_output_path(self) -> Path:
        """GIS output directory for generated shapefiles."""
        output_dir = self.gis_layers_path / "Output"
        output_dir.mkdir(parents=True, exist_ok=True)
        return output_dir
    
    # ==========================================
    # Analysis Parameters
    # ==========================================
    
    @property
    def analysis_params(self) -> Dict:
        """
        Default analysis parameters used across scripts.
        
        Returns:
            Dictionary containing:
                - grid_size: Grid resolution in degrees (0.001° ≈ 100m)
                - time_bin_minutes: Time bin size in minutes
                - fixed_date: Fixed reference date for ArcGIS compatibility
                - crs: Coordinate Reference System (EPSG:4326 = WGS84)
        """
        return {
            "grid_size": 0.001,              # ~100 meters
            "time_bin_minutes": 30,          # 30-minute bins
            "fixed_date": "2025-01-01",      # For ArcGIS time series
            "crs": "EPSG:4326",              # WGS84
        }
    
    # ==========================================
    # Utility Methods
    # ==========================================
    
    def get_relative_path(self, absolute_path: Path, from_dir: Optional[Path] = None) -> Path:
        """
        Convert an absolute path to relative path.
        
        Args:
            absolute_path: The absolute path to convert
            from_dir: Base directory for relative path (default: Helper Scripts)
        
        Returns:
            Relative path from from_dir to absolute_path
        """
        if from_dir is None:
            from_dir = self.helper_scripts_path
        
        try:
            return Path(os.path.relpath(absolute_path, from_dir))
        except ValueError:
            # If on different drives (Windows), return absolute
            return absolute_path
    
    def ensure_output_dir(self, output_path: Path) -> Path:
        """
        Ensure output directory exists, create if necessary.
        
        Args:
            output_path: Path to output directory
        
        Returns:
            The same path (for chaining)
        """
        output_path.mkdir(parents=True, exist_ok=True)
        return output_path
    
    def __repr__(self) -> str:
        """String representation showing key paths."""
        return (
            f"Config(\n"
            f"  project_root={self.project_root}\n"
            f"  dataset_path={self.dataset_path}\n"
            f"  gis_files_path={self.gis_files_path}\n"
            f")"
        )


# ==========================================
# Convenience Functions
# ==========================================

def get_config(project_root: Optional[str] = None) -> Config:
    """
    Factory function to get a Config instance.
    
    Args:
        project_root: Optional manual project root path
    
    Returns:
        Configured Config instance
    """
    return Config(project_root)


# ==========================================
# Module-level instance for quick access
# ==========================================

# Create a default instance that can be imported directly
try:
    config = Config()
except Exception as e:
    # If auto-detection fails, user must create Config manually
    print(f"⚠️ Warning: Could not auto-detect project root: {e}")
    print("Please create Config instance manually: config = Config(project_root='...')")
    config = None


if __name__ == "__main__":
    # Demo/test code
    print("=" * 60)
    print("Configuration Module - Path Demo")
    print("=" * 60)
    
    cfg = Config()
    print(f"\n📁 Project Root: {cfg.project_root}")
    print(f"\n📊 Dataset Paths:")
    print(f"  • Raw Data: {cfg.raw_data_path}")
    print(f"  • Snapp Raw: {cfg.snapp_raw_path}")
    print(f"  • Tapsi Raw: {cfg.tapsi_raw_path}")
    print(f"  • Aggregated: {cfg.aggregated_path}")
    
    print(f"\n🗺️ GIS Paths:")
    print(f"  • GIS Files: {cfg.gis_files_path}")
    print(f"  • Neighborhoods: {cfg.neighborhoods_shapefile}")
    print(f"  • Output: {cfg.gis_output_path}")
    
    print(f"\n⚙️ Analysis Parameters:")
    for key, value in cfg.analysis_params.items():
        print(f"  • {key}: {value}")
    
    print(f"\n✅ Configuration loaded successfully!")
