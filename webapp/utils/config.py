"""Configuration and session state management."""

import streamlit as st
from typing import List, Dict, Any


def initialize_session_state():
    """Initialize Streamlit session state variables."""
    if "messages" not in st.session_state:
        st.session_state.messages = []

    if "uploaded_files" not in st.session_state:
        st.session_state.uploaded_files = []

    if "processed_documents" not in st.session_state:
        st.session_state.processed_documents = []

    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []

    if "document_summaries" not in st.session_state:
        st.session_state.document_summaries = {}

    if "current_document" not in st.session_state:
        st.session_state.current_document = None

    if "processing_status" not in st.session_state:
        st.session_state.processing_status = "idle"

    if "attached_files" not in st.session_state:
        st.session_state.attached_files = []


def add_message(role: str, content: str, metadata: Dict[str, Any] = None):
    """
    Add a message to chat history.

    Args:
        role: Message role ('user' or 'assistant')
        content: Message content
        metadata: Optional metadata
    """
    message = {
        "role": role,
        "content": content,
        "metadata": metadata or {},
    }
    st.session_state.messages.append(message)
    st.session_state.chat_history.append(message)


def clear_chat_history():
    """Clear chat history."""
    st.session_state.messages = []
    st.session_state.chat_history = []


def add_uploaded_file(file_info: Dict[str, Any]):
    """
    Add uploaded file to session state.

    Args:
        file_info: File information dictionary
    """
    st.session_state.uploaded_files.append(file_info)


def add_processed_document(document_info: Dict[str, Any]):
    """
    Add processed document to session state.

    Args:
        document_info: Document information dictionary
    """
    st.session_state.processed_documents.append(document_info)

