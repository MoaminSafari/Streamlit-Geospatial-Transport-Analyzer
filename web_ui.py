"""
Simplified Web UI using Operation Registry
Complete sidebar for time filters and data source selection
"""

import streamlit as st
from operations.registry import registry
from analysis_engine import DataAnalysisEngine as DataEngine
from ui_helpers import constants

# Page config
st.set_page_config(
    page_title="Data Analysis Tool",
    page_icon="📊",
    layout="wide"
)

# Initialize engine
if 'engine' not in st.session_state:
    from config import Config
    config = Config()
    st.session_state.engine = DataEngine(config=config)

# SIDEBAR - Compact Filters
with st.sidebar:
    # Data Source (compact)
    st.markdown("**📂 Data Source**")
    data_source = st.radio(
        "Source:",
        options=["both", "snapp", "tapsi"],
        format_func=lambda x: {"both": "Both", "snapp": "Snapp", "tapsi": "Tapsi"}[x],
        horizontal=True,
        key="data_source_select",
        label_visibility="collapsed"
    )
    st.session_state.data_source = data_source
    
    st.divider()
    
    # Time Filter (compact)
    st.markdown("**📅 Time Filter**")
    filter_type = st.selectbox(
        "Type:",
        options=list(constants.FILTER_TYPE_LABELS.keys()),
        format_func=lambda x: constants.FILTER_TYPE_LABELS[x],
        key="filter_type_select",
        label_visibility="collapsed"
    )
    st.session_state.filter_type = filter_type
    
    params = {}
    if filter_type == "specific_month":
        col1, col2 = st.columns([1, 2])
        with col1:
            year = st.text_input("Year", value="1404", key="year_input", label_visibility="collapsed", placeholder="Year")
        with col2:
            month = st.selectbox(
                "Month", 
                options=list(constants.PERSIAN_MONTHS.keys()),
                format_func=lambda x: f"{x}",
                key="month_select",
                label_visibility="collapsed"
            )
        params = {"year": year, "month": month}
    elif filter_type == "year":
        year = st.text_input("Year", value="1404", key="year_input_y", label_visibility="collapsed", placeholder="Year")
        params = {"year": year}
    elif filter_type == "season":
        year = st.text_input("Year", value="1404", key="year_input_s", label_visibility="collapsed", placeholder="Year")
        season = st.selectbox(
            "Season",
            options=list(constants.PERSIAN_SEASONS.keys()),
            format_func=lambda x: constants.PERSIAN_SEASONS[x],
            key="season_select",
            label_visibility="collapsed"
        )
        params = {"year": year, "season": season}
    elif filter_type == "month_all_years":
        month = st.selectbox(
            "Month",
            options=list(constants.PERSIAN_MONTHS.keys()),
            format_func=lambda x: f"{x} - {constants.PERSIAN_MONTHS[x]}",
            key="month_all_select",
            label_visibility="collapsed"
        )
        params = {"month": month}
    
    st.session_state.time_filter_params = params
    
    st.divider()
    st.caption("📊 v3.0")

# Main layout
st.title("📊 Data Analysis Tool")

# Initialize selected operation in session state
if 'selected_operation' not in st.session_state:
    st.session_state.selected_operation = None

# Category metadata
CATEGORY_INFO = {
    'filters': {'emoji': '🔍', 'title': 'Filters', 'description': 'Filter and slice your data'},
    'transforms': {'emoji': '🔄', 'title': 'Transforms', 'description': 'Transform and aggregate data'},
    'joins': {'emoji': '🔗', 'title': 'Joins & Matrices', 'description': 'Join data and create matrices'},
    'utilities': {'emoji': '🛠️', 'title': 'Utilities', 'description': 'Helpful tools'}
}

# Get operations from registry
operations = registry.get_all_operations()
categories = registry.get_categories()

# Render main content
if st.session_state.selected_operation:
    try:
        # Get operation from registry
        operation = registry.get_operation(st.session_state.selected_operation)
        
        # Add back button
        if st.button("⬅️ Back to Operations", key="back_button"):
            st.session_state.selected_operation = None
            st.rerun()
        
        st.markdown("---")
        
        # Run operation (renders UI and executes if requested)
        operation.run()
        
    except KeyError:
        st.error(f"❌ Operation '{st.session_state.selected_operation}' not found in registry")
        if st.button("⬅️ Back to Operations"):
            st.session_state.selected_operation = None
            st.rerun()
    except Exception as e:
        st.error(f"❌ Error running operation: {e}")
        import traceback
        with st.expander("Debug Info"):
            st.code(traceback.format_exc())
        if st.button("⬅️ Back to Operations"):
            st.session_state.selected_operation = None
            st.rerun()
else:
    # Welcome screen
    st.markdown("""
    ## Welcome! 👋
    
    **Step 1:** Configure global filters in the left sidebar
    - 📂 Select data source (Snapp/Tapsi/Both)
    - 📅 Set time filters (month, year, season, etc.)
    
    **Step 2:** Choose an operation from below
    """)
    
    st.markdown("---")
    
    # Render operations by category
    for category_key, category_ops in categories.items():
        if category_ops:  # Only show non-empty categories
            category_meta = CATEGORY_INFO.get(category_key, {})
            emoji = category_meta.get('emoji', '📦')
            title = category_meta.get('title', category_key.title())
            description = category_meta.get('description', '')
            
            st.subheader(f"{emoji} {title}")
            st.caption(description)
            
            # Create columns for operation buttons (3 per row)
            cols = st.columns(3)
            for idx, op_key in enumerate(category_ops):
                op = operations[op_key]
                metadata = op.get_metadata()
                
                col_idx = idx % 3
                with cols[col_idx]:
                    if st.button(
                        f"**{metadata['title']}**",
                        key=f"op_btn_{op_key}",
                        help=metadata.get('description', ''),
                        use_container_width=True
                    ):
                        st.session_state.selected_operation = op_key
                        st.rerun()
            
            st.markdown("---")
