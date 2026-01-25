"""Sidebar component for V.E.D.A.M.A.X."""

import streamlit as st
from datetime import datetime


def render_sidebar():
    """Render the application sidebar."""
    with st.sidebar:
        st.markdown(
            """
            <div style="text-align: center; padding: 1rem 0;">
                <h2>🩺 V.E.D.A.M.A.X.</h2>
                <p style="color: #6b7280; font-size: 0.9rem;">
                    Your Intelligent Medical Assistant
                </p>
            </div>
            """,
            unsafe_allow_html=True,
        )

        st.divider()

        # Quick Actions
        st.markdown("### ⚡ Quick Actions")
        
        if st.button("🔄 New Chat", use_container_width=True):
            st.session_state.messages = []
            st.session_state.chat_history = []
            st.rerun()

        if st.button("📊 View Documents", use_container_width=True):
            st.session_state.current_view = "documents"
            st.rerun()

        st.divider()

        # Document Statistics
        st.markdown("### 📈 Statistics")
        
        total_docs = len(st.session_state.get("processed_documents", []))
        total_chats = len(st.session_state.get("chat_history", []))
        
        col1, col2 = st.columns(2)
        with col1:
            st.metric("Documents", total_docs)
        with col2:
            st.metric("Chats", total_chats)

        st.divider()

        # Settings
        st.markdown("### ⚙️ Settings")
        
        chunk_strategy = st.selectbox(
            "Chunking Strategy",
            ["semantic", "token"],
            index=0,
            help="Choose how documents are chunked for processing",
        )
        st.session_state.chunk_strategy = chunk_strategy

        enable_ocr = st.checkbox(
            "Enable OCR",
            value=False,
            help="Enable OCR for scanned documents",
        )
        st.session_state.enable_ocr = enable_ocr

        st.divider()

        # About
        st.markdown("### ℹ️ About")
        st.markdown(
            """
            <div style="font-size: 0.85rem; color: #6b7280;">
                <p><strong>V.E.D.A.M.A.X.</strong> is an intelligent medical 
                document analysis system powered by advanced RAG technology.</p>
                <p>Upload medical reports, ask questions, and get intelligent 
                insights with empathetic responses.</p>
            </div>
            """,
            unsafe_allow_html=True,
        )

        st.divider()

        # Footer
        st.markdown(
            f"""
            <div style="text-align: center; color: #9ca3af; font-size: 0.75rem; padding-top: 2rem;">
                <p>Version 1.0.0</p>
                <p>© {datetime.now().year} V.E.D.A.M.A.X.</p>
            </div>
            """,
            unsafe_allow_html=True,
        )

