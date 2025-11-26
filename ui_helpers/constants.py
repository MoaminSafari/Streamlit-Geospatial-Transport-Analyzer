"""
Constants for Web UI
"""

# Persian Month Names (kept as Persian for reference)
PERSIAN_MONTHS = {
    "01": "Farvardin",
    "02": "Ordibehesht",
    "03": "Khordad",
    "04": "Tir",
    "05": "Mordad",
    "06": "Shahrivar",
    "07": "Mehr",
    "08": "Aban",
    "09": "Azar",
    "10": "Dey",
    "11": "Bahman",
    "12": "Esfand"
}

# Persian Seasons
PERSIAN_SEASONS = {
    "spring": "Spring (Farvardin, Ordibehesht, Khordad)",
    "summer": "Summer (Tir, Mordad, Shahrivar)",
    "fall": "Fall (Mehr, Aban, Azar)",
    "winter": "Winter (Dey, Bahman, Esfand)"
}

# Available Operations
OPERATIONS = {
    "neighborhood_aggregation_30min": "Neighborhood 30min Aggregation",
    "grid_temporal_aggregation_100m_30min": "Grid 100m 30min Aggregation",
    "grid_aggregation_100m": "Grid 100m Aggregation",
    "neighborhood_temporal_aggregation_30min": "Neighborhood Temporal 30min",
    "od_matrix_by_neighborhood": "OD Matrix by Neighborhood",
    "peak_hours_analysis": "Peak Hours Analysis",
    "temporal_pattern_analysis": "Temporal Pattern Analysis",
    "shapefile_join_neighborhoods": "Join Data to Neighborhood Shapefile",
    "shapefile_join_neighborhoods_time": "Join Temporal Data to Shapefile",
    "shapefile_filter_peak_hours": "Filter Shapefile by Peak Hours",
    "shapefile_add_regions": "Add Region Info to Shapefile"
}

# Data Source Labels
DATA_SOURCE_LABELS = {
    "both": "Both (Snapp + Tapsi)",
    "snapp": "Snapp Only",
    "tapsi": "Tapsi Only"
}

# Filter Type Labels
FILTER_TYPE_LABELS = {
    "all": "All Files",
    "specific_month": "Specific Month",
    "year": "Entire Year",
    "season": "One Season",
    "month_all_years": "One Month Across All Years",
    "custom": "Custom (Specific Files)"
}
