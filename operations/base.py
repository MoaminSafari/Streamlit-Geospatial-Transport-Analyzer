"""
Base Operation Class
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
import streamlit as st


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
