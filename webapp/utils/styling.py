"""Custom styling for V.E.D.A.M.A.X. application."""

import streamlit as st


def apply_custom_css():
    """Apply custom CSS styling to the application."""
    custom_css = """
    <style>
        /* Main Header */
        .main-header {
            text-align: center;
            padding: 2rem 0;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
            margin-bottom: 2rem;
        }
        
        .main-header h1 {
            font-size: 3rem;
            font-weight: 700;
            margin: 0;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }
        
        .subtitle {
            font-size: 1.1rem;
            color: #6b7280;
            margin-top: 0.5rem;
            font-weight: 400;
        }
        
        /* Chat Interface */
        .chat-container {
            max-width: 900px;
            margin: 0 auto;
            padding: 1rem;
        }
        
        .message-user {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 1rem 1.5rem;
            border-radius: 18px 18px 4px 18px;
            margin: 1rem 0;
            margin-left: auto;
            max-width: 80%;
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
        }
        
        .message-assistant {
            background: #f3f4f6;
            color: #1f2937;
            padding: 1rem 1.5rem;
            border-radius: 18px 18px 18px 4px;
            margin: 1rem 0;
            margin-right: auto;
            max-width: 80%;
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
            border-left: 4px solid #667eea;
        }
        
        /* Input Area */
        .stTextInput > div > div > input {
            border-radius: 24px;
            border: 2px solid #e5e7eb;
            padding: 0.75rem 1.5rem;
            font-size: 1rem;
        }
        
        .stTextInput > div > div > input:focus {
            border-color: #667eea;
            box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.1);
        }
        
        /* Buttons */
        .stButton > button {
            border-radius: 24px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            border: none;
            padding: 0.75rem 2rem;
            font-weight: 600;
            transition: all 0.3s ease;
        }
        
        .stButton > button:hover {
            transform: translateY(-2px);
            box-shadow: 0 4px 12px rgba(102, 126, 234, 0.4);
        }
        
        /* Sidebar */
        .css-1d391kg {
            background: linear-gradient(180deg, #f9fafb 0%, #ffffff 100%);
        }
        
        /* File Upload */
        .uploadedFile {
            border: 2px dashed #667eea;
            border-radius: 12px;
            padding: 1rem;
            margin: 1rem 0;
            background: #f9fafb;
            transition: all 0.3s ease;
        }
        
        .uploadedFile:hover {
            background: #f3f4f6;
            border-color: #764ba2;
        }
        
        /* Tabs */
        .stTabs [data-baseweb="tab-list"] {
            gap: 8px;
        }
        
        .stTabs [data-baseweb="tab"] {
            border-radius: 12px 12px 0 0;
            padding: 0.75rem 1.5rem;
            font-weight: 600;
        }
        
        /* Status Indicators */
        .status-processing {
            color: #f59e0b;
            font-weight: 600;
        }
        
        .status-success {
            color: #10b981;
            font-weight: 600;
        }
        
        .status-error {
            color: #ef4444;
            font-weight: 600;
        }
        
        /* Document Cards */
        .document-card {
            background: white;
            border-radius: 12px;
            padding: 1.5rem;
            margin: 1rem 0;
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
            border-left: 4px solid #667eea;
            transition: all 0.3s ease;
        }
        
        .document-card:hover {
            box-shadow: 0 4px 16px rgba(0,0,0,0.15);
            transform: translateY(-2px);
        }
        
        /* Hide Streamlit default elements */
        #MainMenu {visibility: hidden;}
        footer {visibility: hidden;}
        header {visibility: hidden;}
        
        /* Scrollbar styling */
        ::-webkit-scrollbar {
            width: 8px;
        }
        
        ::-webkit-scrollbar-track {
            background: #f1f1f1;
        }
        
        ::-webkit-scrollbar-thumb {
            background: #667eea;
            border-radius: 4px;
        }
        
        ::-webkit-scrollbar-thumb:hover {
            background: #764ba2;
        }
    </style>
    """
    st.markdown(custom_css, unsafe_allow_html=True)

