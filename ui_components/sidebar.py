"""
Sidebar Component
Handles sidebar rendering with categorized operations
"""

import streamlit as st
from operations.registry import registry


# Category metadata
CATEGORY_INFO = {
    'filters': {
        'emoji': '🔍',
        'title': 'Filters',
        'description': 'Filter and slice your data'
    },
    'transforms': {
        'emoji': '🔄',
        'title': 'Transforms',
        'description': 'Transform and aggregate data'
    },
    'joins': {
        'emoji': '🔗',
        'title': 'Joins & Matrices',
        'description': 'Join data and create matrices'
    },
    'utilities': {
        'emoji': '🛠️',
        'title': 'Utilities',
        'description': 'Helpful tools'
    }
}


def render_categorized_sidebar():
    """
    Render sidebar with categorized operations
    
    Returns:
        Selected operation key or None
    """
    st.sidebar.title("📋 Operations")
    
    operations = registry.get_all_operations()
    categories = registry.get_categories()
    
    # State for selected operation
    if 'selected_operation' not in st.session_state:
        st.session_state.selected_operation = None
    
    selected_key = None
    
    # Render each category
    for category_key, category_ops in categories.items():
        if category_ops:  # Only show non-empty categories
            category_meta = CATEGORY_INFO.get(category_key, {})
            emoji = category_meta.get('emoji', '📦')
            title = category_meta.get('title', category_key.title())
            
            with st.sidebar.expander(f"{emoji} {title}", expanded=True):
                for op_key in category_ops:
                    op = operations[op_key]
                    metadata = op.get_metadata()
                    
                    button_text = metadata['title']
                    
                    if st.button(button_text, key=f"select_{op_key}", width='stretch'):
                        st.session_state.selected_operation = op_key
                        selected_key = op_key
    
    return selected_key or st.session_state.selected_operation
