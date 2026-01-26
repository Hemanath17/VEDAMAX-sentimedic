# SentiMedical-RAG

An autonomous, Agentic RAG system that integrates sentiment analysis to adjust response modality and clinical groundedness for personal health management.

## Overview

SentiMedical-RAG is a production-ready, sentiment-aware Agentic RAG system designed for medical domain tasks. It prioritizes:

- **Factual Groundedness** via Hybrid Retrieval/Reranking
- **User Safety** via Sentiment Analysis and Input/Output Guardrails
- **Continuous Evaluation** via LLMOps pipeline ensuring observability

## Architecture

The system operates as a Multi-Stage Pipeline with an Agentic Supervisor:

1. **Ingestion**: Asynchronous ETL pipeline parsing PDF/Docx using Docling, chunking via Semantic Chunking
2. **User Input Analysis**: Parallel execution of NER for medical terms and Emotion Classification
3. **Agentic Decisioning**: LangGraph-based Router decides query routing
4. **Retrieval**: Hybrid Search (BM25 + Vector) followed by Cross-Encoder Reranker
5. **Generation**: Context-injected generation with sentiment-aware system prompts

## Technology Stack

- **Orchestration**: LangGraph / CrewAI
- **Data Ingestion**: Unstructured.io / Docling
- **Vector Engine**: Qdrant (Cloud/Local)
- **Embeddings**: BGE-M3
- **NLP Engine**: Hugging Face Transformers
- **Evaluation**: Ragas & DeepEval
- **Monitoring**: Arize Phoenix / LangSmith
- **Deployment**: FastAPI + Docker + AWS


