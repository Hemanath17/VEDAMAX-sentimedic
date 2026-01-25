"""
V.E.D.A.M.A.X. - Vectorized Empathetic Data Assistant for Maximum Analytic Extraction
Main Streamlit Application
"""

import streamlit as st
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from webapp.components.sidebar import render_sidebar
from webapp.components.chat_interface import render_chat_interface
from webapp.utils.config import initialize_session_state
from webapp.utils.styling import apply_custom_css

# Page configuration
st.set_page_config(
    page_title="V.E.D.A.M.A.X.",
    page_icon="🩺",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Apply custom styling
apply_custom_css()

# Initialize session state
initialize_session_state()

# Main app title
st.markdown(
    """
    <div class="main-header">
        <h1>🩺 V.E.D.A.M.A.X.</h1>
        <p class="subtitle">Vectorized Empathetic Data Assistant for Maximum Analytic Extraction</p>
    </div>
    """,
    unsafe_allow_html=True,
)

# Sidebar
render_sidebar()

# Main content area - Chat interface with integrated document upload
render_chat_interface()

