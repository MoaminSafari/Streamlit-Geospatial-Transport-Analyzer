"""
Column Name Mapping: snake_case to camelCase
This file contains the mapping for standardizing column names to camelCase
"""

# Complete mapping from snake_case to camelCase
COLUMN_NAME_MAPPING = {
    # Coordinate columns
    'org_lat': 'originLatitude',
    'org_lng': 'originLongitude',
    'org_long': 'originLongitude',
    'origin_lat': 'originLatitude',
    'origin_lng': 'originLongitude',
    'origin_long': 'originLongitude',
    
    'dst_lat': 'destinationLatitude',
    'dst_lng': 'destinationLongitude',
    'dst_long': 'destinationLongitude',
    'dest_lat': 'destinationLatitude',
    'dest_lng': 'destinationLongitude',
    'dest_long': 'destinationLongitude',
    'destination_lat': 'destinationLatitude',
    'destination_lng': 'destinationLongitude',
    'destination_long': 'destinationLongitude',
    
    # Time columns
    'org_time': 'originTime',
    'dst_time': 'destinationTime',
    'origin_time': 'originTime',
    'dest_time': 'destinationTime',
    'destination_time': 'destinationTime',
    
    # Aggregation count columns
    'snapp_org_count': 'snappOriginCount',
    'snapp_dst_count': 'snappDestinationCount',
    'tapsi_org_count': 'tapsiOriginCount',
    'tapsi_dst_count': 'tapsiDestinationCount',
    'total_origin': 'totalOrigin',
    'total_destination': 'totalDestination',
    
    # Grid/bin columns
    'x_bin': 'xBin',
    'y_bin': 'yBin',
    'time_bin': 'timeBin',
    'time_bin_minutes': 'timeBinMinutes',
    'time_bin_datetime': 'timeBinDatetime',
    
    # Registration columns
    'reg_date': 'registrationDate',
    'registration_date': 'registrationDate',
}

# Reverse mapping (camelCase to snake_case) for backward compatibility
REVERSE_COLUMN_NAME_MAPPING = {v: k for k, v in COLUMN_NAME_MAPPING.items()}


def to_camel_case(snake_str: str) -> str:
    """
    Convert snake_case string to camelCase
    
    Args:
        snake_str: String in snake_case format
        
    Returns:
        String in camelCase format
    """
    if snake_str in COLUMN_NAME_MAPPING:
        return COLUMN_NAME_MAPPING[snake_str]
    
    # General conversion for any snake_case
    components = snake_str.split('_')
    return components[0] + ''.join(x.title() for x in components[1:])


def to_snake_case(camel_str: str) -> str:
    """
    Convert camelCase string to snake_case
    
    Args:
        camel_str: String in camelCase format
        
    Returns:
        String in snake_case format
    """
    if camel_str in REVERSE_COLUMN_NAME_MAPPING:
        return REVERSE_COLUMN_NAME_MAPPING[camel_str]
    
    # General conversion for any camelCase
    import re
    return re.sub(r'(?<!^)(?=[A-Z])', '_', camel_str).lower()
