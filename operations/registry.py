"""
Updated Operation Registry
"""

from typing import Dict, List, Type, Union
from operations.base import BaseOperation


class OperationRegistry:
    """Central registry for all operations"""
    
    def __init__(self):
        self._operations: Dict[str, Union[Type[BaseOperation], BaseOperation]] = {}
        self._categories: Dict[str, List[str]] = {
            'filters': [],
            'transforms': [],
            'joins': [],
            'utilities': []
        }
    
    def register(self, operation_class: Union[Type[BaseOperation], BaseOperation]):
        """Register an operation (class or instance)"""
        # Handle both classes and instances
        if isinstance(operation_class, type):
            op = operation_class()
        else:
            op = operation_class
            
        metadata = op.get_metadata()
        
        key = metadata['key']
        category = metadata.get('category', 'utilities')
        
        self._operations[key] = operation_class
        if category in self._categories:
            if key not in self._categories[category]:
                self._categories[category].append(key)
    
    def get_operation(self, key: str) -> BaseOperation:
        """Get operation instance by key"""
        if key in self._operations:
            op_or_class = self._operations[key]
            if isinstance(op_or_class, type):
                return op_or_class()
            return op_or_class
        raise KeyError(f"Operation '{key}' not found")
    
    def get_all_operations(self) -> Dict[str, BaseOperation]:
        """Get all operations as instances"""
        result = {}
        for key, op_or_class in self._operations.items():
            if isinstance(op_or_class, type):
                result[key] = op_or_class()
            else:
                result[key] = op_or_class
        return result
    
    def get_operations_by_category(self, category: str) -> Dict[str, BaseOperation]:
        """Get operations in a specific category"""
        if category not in self._categories:
            return {}
        return {key: self.get_operation(key) for key in self._categories[category]}
    
    def get_categories(self) -> Dict[str, List[str]]:
        """Get all categories with their operation keys"""
        return self._categories.copy()


# Global registry instance
registry = OperationRegistry()


def register_all_operations():
    """Register all operations"""
    
    # Filters (3)
    from operations.filters.boundary_filter import BoundaryFilterOperation
    from operations.filters.hour_filter import HourFilterOperation
    from operations.filters.time_space_filter import TimeSpaceFilterOperation
    
    registry.register(BoundaryFilterOperation)
    registry.register(HourFilterOperation)
    registry.register(TimeSpaceFilterOperation)
    
    # Transforms (5)
    from operations.transforms.time_slice import TimeSliceOperation
    from operations.transforms.spatial_agg import SpatialAggOperation
    from operations.transforms.spatiotemporal_agg import SpatiotemporalAggOperation
    from operations.transforms.temporal_agg import TemporalAggOperation
    from operations.transforms.time_binning import TimeBinningOperation
    
    registry.register(TimeSliceOperation)
    registry.register(SpatialAggOperation)
    registry.register(SpatiotemporalAggOperation)
    registry.register(TemporalAggOperation)
    registry.register(TimeBinningOperation)
    
    # Joins (2)
    from operations.joins.shapefile_join import ShapefileJoinOperation
    from operations.joins.od_matrix import ODMatrixOperation
    
    registry.register(ShapefileJoinOperation)
    registry.register(ODMatrixOperation)
    
    # Utilities (1)
    from operations.utilities.file_preview import FilePreviewOperation
    
    registry.register(FilePreviewOperation)
    
    return registry


# Initialize
register_all_operations()
