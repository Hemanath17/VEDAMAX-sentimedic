"""Chat interface component for V.E.D.A.M.A.X."""

import streamlit as st
from pathlib import Path
import tempfile
from datetime import datetime
from typing import Optional


def render_chat_interface():
    """Render the main chat interface with integrated document upload."""
    st.markdown(
        """
        <div style="text-align: center; margin-bottom: 2rem;">
            <h3>💬 Chat with V.E.D.A.M.A.X.</h3>
            <p style="color: #6b7280;">
                Ask questions about your medical documents or get general health information
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # Chat messages container
    chat_container = st.container()

    with chat_container:
        # Display chat history
        if st.session_state.messages:
            for message in st.session_state.messages:
                with st.chat_message(message["role"]):
                    st.markdown(message["content"])
                    
                    # Show metadata if available
                    if message.get("metadata") and message["metadata"].get("source"):
                        with st.expander("📎 Sources"):
                            st.write(message["metadata"]["source"])
        else:
            # Welcome message
            st.markdown(
                """
                <div style="text-align: center; padding: 3rem 2rem; color: #6b7280;">
                    <h4>👋 Welcome to V.E.D.A.M.A.X.</h4>
                    <p>I'm your intelligent medical assistant. I can help you:</p>
                    <ul style="text-align: left; display: inline-block;">
                        <li>Analyze medical reports and documents</li>
                        <li>Answer questions about your health data</li>
                        <li>Provide empathetic, clinically-grounded responses</li>
                        <li>Summarize complex medical information</li>
                    </ul>
                    <p style="margin-top: 2rem;">
                        <strong>Start by uploading a document or asking a question!</strong>
                    </p>
                </div>
                """,
                unsafe_allow_html=True,
            )

    # File upload area - above chat input
    st.markdown("<br>", unsafe_allow_html=True)
    
    # File uploader in a collapsible section
    with st.expander("📎 Attach Documents", expanded=False):
        uploaded_files = st.file_uploader(
            "Upload medical documents (PDF, DOCX, DOC, Images)",
            type=["pdf", "docx", "doc", "png", "jpg", "jpeg"],
            accept_multiple_files=True,
            help="Upload your medical reports, lab results, or other documents",
            key="chat_file_uploader",
        )
        
        if uploaded_files:
            st.markdown("**Uploaded Files:**")
            for uploaded_file in uploaded_files:
                file_size_mb = uploaded_file.size / (1024 * 1024)
                file_icon = get_file_icon(uploaded_file.name)
                
                col1, col2, col3 = st.columns([1, 4, 1])
                with col1:
                    st.markdown(f"<div style='font-size: 2rem;'>{file_icon}</div>", unsafe_allow_html=True)
                with col2:
                    st.markdown(f"**{uploaded_file.name}**")
                    st.caption(f"{file_size_mb:.2f} MB • {uploaded_file.type}")
                with col3:
                    if st.button("🗑️", key=f"remove_{uploaded_file.name}", help="Remove file"):
                        # Remove file from session state
                        if "uploaded_files" in st.session_state:
                            st.session_state.uploaded_files = [
                                f for f in st.session_state.uploaded_files 
                                if f.get("name") != uploaded_file.name
                            ]
                        st.rerun()
            
            # Process button
            if st.button("🔄 Process & Add to Chat", type="primary", use_container_width=True):
                process_uploaded_files_in_chat(uploaded_files)

    # Display attached files in chat if any
    if st.session_state.get("attached_files"):
        with st.chat_message("assistant"):
            st.markdown("**📎 Attached Documents:**")
            for file_info in st.session_state.attached_files:
                file_icon = get_file_icon(file_info.get("name", ""))
                st.markdown(f"{file_icon} **{file_info.get('name')}** - {file_info.get('status', 'ready')}")

    # Chat input - st.chat_input handles its own positioning
    user_input = st.chat_input(
        "Ask V.E.D.A.M.A.X. about your medical documents...",
        key="chat_input",
    )

    # Process user input when submitted
    if user_input:
        process_user_message(user_input)


def process_user_message(user_input: str):
    """
    Process user message and generate response.

    Args:
        user_input: User's message
    """
    # Check if there are attached files
    attached_files = st.session_state.get("attached_files", [])
    metadata = {}
    if attached_files:
        metadata["attached_files"] = [f.get("name") for f in attached_files]
    
    # Add user message to chat
    st.session_state.messages.append({
        "role": "user",
        "content": user_input,
        "metadata": metadata,
    })

    # Show user message
    with st.chat_message("user"):
        st.markdown(user_input)
        
        # Show attached files if any
        if attached_files:
            st.markdown("**📎 Attached:** " + ", ".join([f["name"] for f in attached_files]))

    # Generate assistant response (placeholder for now)
    with st.chat_message("assistant"):
        with st.spinner("V.E.D.A.M.A.X. is thinking..."):
            response = generate_response(user_input, attached_files)
            st.markdown(response)
            
            # Add assistant message to chat
            st.session_state.messages.append({
                "role": "assistant",
                "content": response,
                "metadata": {
                    "source": "V.E.D.A.M.A.X. RAG System",
                    "timestamp": datetime.now().isoformat(),
                },
            })


def get_file_icon(filename: str) -> str:
    """Get icon for file type."""
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


def process_uploaded_files_in_chat(uploaded_files):
    """Process uploaded files and add them to chat context."""
    if "attached_files" not in st.session_state:
        st.session_state.attached_files = []
    
    for uploaded_file in uploaded_files:
        file_info = {
            "name": uploaded_file.name,
            "size": uploaded_file.size,
            "type": uploaded_file.type,
            "uploaded_at": datetime.now().isoformat(),
            "status": "processing",
        }
        
        # Save file temporarily
        try:
            with tempfile.NamedTemporaryFile(delete=False, suffix=Path(uploaded_file.name).suffix) as tmp_file:
                tmp_file.write(uploaded_file.getbuffer())
                file_info["temp_path"] = tmp_file.name
                file_info["status"] = "ready"
        except Exception as e:
            file_info["status"] = f"error: {str(e)}"
        
        st.session_state.attached_files.append(file_info)
    
    # Add message to chat showing files were attached
    if st.session_state.attached_files:
        file_names = ", ".join([f["name"] for f in st.session_state.attached_files])
        st.session_state.messages.append({
            "role": "user",
            "content": f"📎 Attached files: {file_names}",
            "metadata": {"type": "file_upload", "files": st.session_state.attached_files},
        })
        
        # Add assistant acknowledgment
        st.session_state.messages.append({
            "role": "assistant",
            "content": f"I've received {len(st.session_state.attached_files)} document(s). You can now ask me questions about them!",
            "metadata": {},
        })
    
    st.rerun()


def generate_response(user_input: str, attached_files: list = None) -> str:
    """
    Generate response to user input.

    Args:
        user_input: User's message
        attached_files: List of attached files

    Returns:
        Assistant's response
    """
    # TODO: Integrate with actual RAG system
    # For now, return placeholder response
    
    has_files = attached_files and len(attached_files) > 0
    
    if "hello" in user_input.lower() or "hi" in user_input.lower():
        response = """
        Hello! I'm V.E.D.A.M.A.X., your intelligent medical assistant. 
        I'm here to help you understand your medical documents and answer 
        health-related questions with empathy and clinical accuracy.
        """
        if has_files:
            response += f"\n\nI can see you've attached {len(attached_files)} document(s). I'm ready to analyze them!"
        response += "\n\nHow can I assist you today?"
        return response
    
    elif "summary" in user_input.lower() or "summarize" in user_input.lower():
        if has_files:
            file_names = ", ".join([f["name"] for f in attached_files])
            return f"""
            I can see you've attached {len(attached_files)} document(s): {file_names}
            
            Let me analyze them and provide you with a comprehensive summary.
            
            *Note: Full RAG integration coming soon. This is a preview interface.*
            """
        else:
            return """
            I'd be happy to summarize your medical documents! 
            Please attach a document first using the "📎 Attach Documents" option above.
            """
    
    elif has_files:
        file_names = ", ".join([f["name"] for f in attached_files])
        return f"""
        Thank you for your question: "{user_input}"
        
        I can see you've attached {len(attached_files)} document(s): {file_names}
        
        I'm currently in preview mode. Once fully integrated with the 
        RAG system, I'll be able to provide detailed, empathetic responses 
        based on your attached medical documents and clinical knowledge.
        
        *Full functionality coming soon!*
        """
    
    else:
        return f"""
        Thank you for your question: "{user_input}"
        
        I'm currently in preview mode. Once fully integrated with the 
        RAG system, I'll be able to provide detailed, empathetic responses 
        based on your medical documents and clinical knowledge.
        
        *Tip: You can attach documents using the "📎 Attach Documents" option above!*
        """

