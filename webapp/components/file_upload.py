"""File upload component for V.E.D.A.M.A.X."""

import streamlit as st
from pathlib import Path
import tempfile
from datetime import datetime


def render_file_upload():
    """Render the file upload interface."""
    st.markdown(
        """
        <div style="text-align: center; margin-bottom: 2rem;">
            <h3>📄 Upload Medical Documents</h3>
            <p style="color: #6b7280;">
                Upload PDF, DOCX, or image files of your medical reports for analysis
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # File uploader
    uploaded_files = st.file_uploader(
        "Choose files to upload",
        type=["pdf", "docx", "doc", "png", "jpg", "jpeg"],
        accept_multiple_files=True,
        help="Supported formats: PDF, DOCX, DOC, PNG, JPG, JPEG",
    )

    if uploaded_files:
        st.markdown("### 📋 Uploaded Files")
        
        for uploaded_file in uploaded_files:
            display_file_info(uploaded_file)

        # Process button
        if st.button("🔄 Process Documents", type="primary", use_container_width=True):
            process_uploaded_files(uploaded_files)

    # Display processed documents
    if st.session_state.get("processed_documents"):
        st.markdown("### ✅ Processed Documents")
        display_processed_documents()


def display_file_info(uploaded_file):
    """
    Display information about an uploaded file.

    Args:
        uploaded_file: Uploaded file object
    """
    file_size_mb = uploaded_file.size / (1024 * 1024)
    
    col1, col2, col3 = st.columns([3, 1, 1])
    
    with col1:
        st.markdown(
            f"""
            <div class="document-card">
                <h4>📄 {uploaded_file.name}</h4>
                <p style="color: #6b7280; font-size: 0.9rem;">
                    Size: {file_size_mb:.2f} MB | Type: {uploaded_file.type}
                </p>
            </div>
            """,
            unsafe_allow_html=True,
        )
    
    with col2:
        st.metric("Size", f"{file_size_mb:.2f} MB")
    
    with col3:
        file_type_icon = get_file_type_icon(uploaded_file.name)
        st.markdown(f"<div style='font-size: 2rem; text-align: center;'>{file_type_icon}</div>", unsafe_allow_html=True)


def get_file_type_icon(filename: str) -> str:
    """
    Get icon for file type.

    Args:
        filename: File name

    Returns:
        Icon emoji
    """
    ext = Path(filename).suffix.lower()
    icons = {
        ".pdf": "📕",
        ".docx": "📘",
        ".doc": "📗",
        ".png": "🖼️",
        ".jpg": "🖼️",
        ".jpeg": "🖼️",
    }
    return icons.get(ext, "📄")


def process_uploaded_files(uploaded_files):
    """
    Process uploaded files through ETL pipeline.

    Args:
        uploaded_files: List of uploaded files
    """
    progress_bar = st.progress(0)
    status_text = st.empty()

    total_files = len(uploaded_files)
    
    for idx, uploaded_file in enumerate(uploaded_files):
        status_text.text(f"Processing {uploaded_file.name}... ({idx + 1}/{total_files})")
        
        try:
            # Save uploaded file temporarily
            with tempfile.NamedTemporaryFile(delete=False, suffix=Path(uploaded_file.name).suffix) as tmp_file:
                tmp_file.write(uploaded_file.getbuffer())
                tmp_path = Path(tmp_file.name)

            # TODO: Integrate with actual ETL pipeline
            # For now, simulate processing
            import time
            time.sleep(1)  # Simulate processing time

            # Add to processed documents
            document_info = {
                "name": uploaded_file.name,
                "size": uploaded_file.size,
                "type": uploaded_file.type,
                "processed_at": datetime.now().isoformat(),
                "status": "success",
                "chunks": 0,  # Placeholder
            }
            
            st.session_state.processed_documents.append(document_info)
            st.session_state.uploaded_files.append({
                "name": uploaded_file.name,
                "path": str(tmp_path),
            })

            progress_bar.progress((idx + 1) / total_files)

        except Exception as e:
            st.error(f"Error processing {uploaded_file.name}: {str(e)}")
            document_info = {
                "name": uploaded_file.name,
                "status": "error",
                "error": str(e),
            }
            st.session_state.processed_documents.append(document_info)

    status_text.text("✅ Processing complete!")
    st.success(f"Successfully processed {total_files} file(s)")
    st.rerun()


def display_processed_documents():
    """Display list of processed documents."""
    for doc in st.session_state.processed_documents:
        with st.expander(f"📄 {doc.get('name', 'Unknown')}"):
            col1, col2 = st.columns(2)
            
            with col1:
                st.write("**Status:**", doc.get("status", "unknown"))
                st.write("**Processed At:**", doc.get("processed_at", "N/A"))
            
            with col2:
                if doc.get("chunks"):
                    st.metric("Chunks", doc["chunks"])
                if doc.get("size"):
                    size_mb = doc["size"] / (1024 * 1024)
                    st.metric("Size", f"{size_mb:.2f} MB")
            
            if doc.get("status") == "error":
                st.error(f"Error: {doc.get('error', 'Unknown error')}")

