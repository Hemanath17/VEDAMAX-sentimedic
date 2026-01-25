# V.E.D.A.M.A.X. Web Application

Vectorized Empathetic Data Assistant for Maximum Analytic Extraction

## Overview

V.E.D.A.M.A.X. is an intelligent medical document analysis web application that provides users with an intuitive, Gemini-like interface for interacting with medical documents and getting empathetic, clinically-grounded responses.

## Features

- 💬 **Chat Interface**: Interactive chat with V.E.D.A.M.A.X. for asking questions about medical documents
- 📄 **Document Upload**: Upload PDF, DOCX, DOC, and image files for analysis
- 🔍 **Intelligent Analysis**: Powered by advanced RAG technology for accurate document understanding
- 💜 **Empathetic Responses**: Sentiment-aware responses that adjust based on user emotional state
- 📊 **Document Management**: View and manage processed documents

## Installation

```bash
# Install webapp dependencies
pip install -r webapp/requirements.txt
```

## Running the Application

```bash
# From project root
streamlit run webapp/app.py

# Or from webapp directory
cd webapp
streamlit run app.py
```

## Interface Components

- **Chat Tab**: Main conversation interface
- **Documents Tab**: File upload and document management
- **Sidebar**: Quick actions, statistics, and settings

## Integration

The webapp is designed to integrate with the main SentiMedical-RAG system:
- ETL Pipeline for document processing
- RAG system for intelligent responses
- Sentiment analysis for empathetic interactions

## Future Enhancements

- Real-time document processing
- Advanced visualization of medical data
- Export capabilities
- Multi-language support

