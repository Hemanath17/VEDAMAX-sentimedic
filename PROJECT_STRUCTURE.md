# SentiMedical-RAG Project Structure

## Proposed Folder Structure

```
SentiMedical-RAG/
├── README.md                          # Project overview and setup instructions
├── .gitignore                         # Git ignore patterns
├── .env.example                       # Environment variables template
├── pyproject.toml                     # Modern Python project configuration
├── requirements.txt                   # Python dependencies
├── requirements-dev.txt               # Development dependencies
├── docker-compose.yml                 # Docker orchestration for services
├── Dockerfile                         # Main application container
├── .dockerignore                      # Docker ignore patterns
│
├── src/                               # Main source code
│   ├── __init__.py
│   │
│   ├── ingestion/                     # Data ingestion pipeline
│   │   ├── __init__.py
│   │   ├── parsers/                   # Document parsers
│   │   │   ├── __init__.py
│   │   │   ├── pdf_parser.py         # PDF parsing with Docling
│   │   │   ├── docx_parser.py        # DOCX parsing
│   │   │   └── base_parser.py        # Base parser interface
│   │   ├── chunkers/                  # Text chunking strategies
│   │   │   ├── __init__.py
│   │   │   ├── semantic_chunker.py   # Semantic chunking (topic shift detection)
│   │   │   ├── token_chunker.py      # Token-based chunking (fallback)
│   │   │   └── chunk_strategy.py     # Base chunking interface
│   │   ├── etl_pipeline.py           # Main ETL orchestration
│   │   └── processors/                # Data processors
│   │       ├── __init__.py
│   │       ├── table_extractor.py    # Medical table extraction
│   │       └── ocr_processor.py      # OCR processing
│   │
│   ├── analysis/                      # User input analysis
│   │   ├── __init__.py
│   │   ├── ner/                       # Named Entity Recognition
│   │   │   ├── __init__.py
│   │   │   ├── medical_ner.py        # Medical term extraction
│   │   │   └── entity_types.py       # Medical entity type definitions
│   │   ├── sentiment/                 # Sentiment/Emotion analysis
│   │   │   ├── __init__.py
│   │   │   ├── emotion_classifier.py # DistilRoBERTa emotion model
│   │   │   ├── sentiment_analyzer.py # Sentiment analysis wrapper
│   │   │   └── persona_mapper.py      # Emotion-to-Persona mapping
│   │   └── input_analyzer.py         # Orchestrates NER + Sentiment
│   │
│   ├── agentic/                       # Agentic decision framework
│   │   ├── __init__.py
│   │   ├── router/                    # LangGraph-based routing
│   │   │   ├── __init__.py
│   │   │   ├── agent_router.py       # Main routing logic
│   │   │   ├── decision_nodes.py     # Router decision nodes
│   │   │   └── routing_state.py      # State management
│   │   ├── agents/                    # Specialized agents
│   │   │   ├── __init__.py
│   │   │   ├── retrieval_agent.py    # Direct knowledge retrieval agent
│   │   │   ├── calculation_agent.py  # Code interpreter for lab results
│   │   │   └── safety_agent.py       # Safety interception agent
│   │   └── supervisor.py              # Agentic supervisor orchestration
│   │
│   ├── retrieval/                     # Hybrid retrieval system
│   │   ├── __init__.py
│   │   ├── vector_store/              # Vector database integration
│   │   │   ├── __init__.py
│   │   │   ├── qdrant_client.py      # Qdrant client wrapper
│   │   │   ├── embeddings.py         # BGE-M3 embedding generation
│   │   │   └── collection_manager.py # Collection management
│   │   ├── hybrid_search.py          # BM25 + Vector search
│   │   ├── reranker.py               # Cross-encoder reranker
│   │   └── retrieval_pipeline.py     # End-to-end retrieval orchestration
│   │
│   ├── generation/                    # Response generation
│   │   ├── __init__.py
│   │   ├── prompt_templates/         # Prompt templates
│   │   │   ├── __init__.py
│   │   │   ├── system_prompts.py     # System meta-prompts
│   │   │   ├── user_prompts.py       # User prompt templates
│   │   │   └── sentiment_prompts.py  # Sentiment-aware prompts
│   │   ├── llm_client.py             # LLM client abstraction
│   │   ├── response_generator.py     # Main generation logic
│   │   └── post_processor.py         # Response post-processing
│   │
│   ├── safety/                        # Safety and guardrails
│   │   ├── __init__.py
│   │   ├── input_guardrails.py       # Input validation and filtering
│   │   ├── output_guardrails.py      # Output validation and filtering
│   │   ├── risk_detector.py          # High-risk input detection
│   │   └── protocols.py              # Safety protocols and rules
│   │
│   ├── evaluation/                    # Evaluation and metrics
│   │   ├── __init__.py
│   │   ├── ragas_evaluator.py        # Ragas-based evaluation
│   │   ├── deepeval_evaluator.py     # DeepEval integration
│   │   ├── metrics/                   # Custom metrics
│   │   │   ├── __init__.py
│   │   │   ├── faithfulness.py       # Faithfulness scoring
│   │   │   ├── relevancy.py          # Relevancy scoring
│   │   │   └── correctness.py        # Answer correctness
│   │   └── evaluation_pipeline.py    # Evaluation orchestration
│   │
│   ├── monitoring/                    # Observability and monitoring
│   │   ├── __init__.py
│   │   ├── phoenix_integration.py    # Arize Phoenix integration
│   │   ├── langsmith_integration.py  # LangSmith integration
│   │   ├── tracing.py                # Trace-level logging
│   │   └── metrics_collector.py      # Custom metrics collection
│   │
│   ├── api/                           # FastAPI application
│   │   ├── __init__.py
│   │   ├── main.py                   # FastAPI app entry point
│   │   ├── routes/                    # API routes
│   │   │   ├── __init__.py
│   │   │   ├── health.py             # Health check endpoints
│   │   │   ├── ingestion.py          # Document ingestion endpoints
│   │   │   ├── query.py              # Query endpoints
│   │   │   └── evaluation.py         # Evaluation endpoints
│   │   ├── models/                    # Pydantic models
│   │   │   ├── __init__.py
│   │   │   ├── request_models.py     # Request schemas
│   │   │   └── response_models.py    # Response schemas
│   │   ├── middleware/                # API middleware
│   │   │   ├── __init__.py
│   │   │   ├── auth.py               # Authentication middleware
│   │   │   ├── logging.py            # Request logging
│   │   │   └── error_handler.py      # Error handling
│   │   └── dependencies.py           # FastAPI dependencies
│   │
│   ├── config/                        # Configuration management
│   │   ├── __init__.py
│   │   ├── settings.py               # Application settings (Pydantic)
│   │   ├── logging_config.py         # Logging configuration
│   │   └── constants.py              # Application constants
│   │
│   └── utils/                         # Utility functions
│       ├── __init__.py
│       ├── file_utils.py             # File operations
│       ├── text_utils.py             # Text processing utilities
│       └── validators.py             # Data validators
│
├── tests/                             # Test suite
│   ├── __init__.py
│   ├── unit/                          # Unit tests
│   │   ├── __init__.py
│   │   ├── test_ingestion/
│   │   ├── test_analysis/
│   │   ├── test_agentic/
│   │   ├── test_retrieval/
│   │   ├── test_generation/
│   │   └── test_safety/
│   ├── integration/                   # Integration tests
│   │   ├── __init__.py
│   │   ├── test_pipeline.py
│   │   └── test_api.py
│   ├── e2e/                           # End-to-end tests
│   │   ├── __init__.py
│   │   └── test_full_workflow.py
│   ├── fixtures/                      # Test fixtures
│   │   ├── sample_documents/
│   │   └── test_data.json
│   └── conftest.py                   # Pytest configuration
│
├── scripts/                           # Utility scripts
│   ├── setup_environment.sh          # Environment setup script
│   ├── ingest_documents.py           # Document ingestion script
│   ├── run_evaluation.py             # Evaluation script
│   ├── seed_vector_db.py             # Vector DB seeding
│   └── migrate_data.py               # Data migration scripts
│
├── notebooks/                         # Jupyter notebooks for experimentation
│   ├── exploration/
│   │   ├── embedding_analysis.ipynb
│   │   ├── chunking_strategies.ipynb
│   │   └── sentiment_analysis.ipynb
│   └── evaluation/
│       └── evaluation_results.ipynb
│
├── data/                              # Data directory (gitignored)
│   ├── raw/                           # Raw documents
│   │   ├── pdfs/
│   │   └── docx/
│   ├── processed/                     # Processed chunks
│   │   └── chunks/
│   ├── embeddings/                    # Cached embeddings
│   └── evaluation/                     # Evaluation datasets
│       └── test_queries.json
│
├── models/                            # Model storage (gitignored)
│   ├── embeddings/                    # Embedding models cache
│   ├── sentiment/                     # Sentiment models cache
│   └── ner/                           # NER models cache
│
├── logs/                              # Application logs (gitignored)
│   ├── app.log
│   └── evaluation.log
│
├── docker/                            # Docker-related files
│   ├── Dockerfile.api                 # API service Dockerfile
│   ├── Dockerfile.worker              # Worker service Dockerfile
│   └── nginx.conf                     # Nginx configuration (if needed)
│
├── infrastructure/                    # Infrastructure as Code
│   ├── aws/                           # AWS deployment configs
│   │   ├── cloudformation/
│   │   ├── terraform/
│   │   └── ecs/
│   └── kubernetes/                    # K8s manifests (if needed)
│       ├── deployments/
│       └── services/
│
├── docs/                              # Documentation
│   ├── architecture.md               # System architecture details
│   ├── api_documentation.md          # API documentation
│   ├── deployment.md                  # Deployment guide
│   ├── development.md                # Development guide
│   └── evaluation.md                 # Evaluation methodology
│
└── .github/                           # GitHub workflows
    └── workflows/
        ├── ci.yml                    # Continuous Integration
        ├── cd.yml                    # Continuous Deployment
        └── evaluation.yml            # Automated evaluation pipeline
```

## Key Design Decisions

### 1. **Modular Architecture**
   - Each major component (ingestion, analysis, agentic, retrieval, generation) is isolated
   - Clear separation of concerns for maintainability and testing

### 2. **Configuration Management**
   - Centralized config using Pydantic Settings
   - Environment-based configuration via `.env` files

### 3. **Testing Strategy**
   - Unit tests for individual components
   - Integration tests for pipeline flows
   - E2E tests for complete workflows

### 4. **Observability**
   - Dedicated monitoring module for Phoenix/LangSmith
   - Structured logging throughout

### 5. **Production Readiness**
   - Docker containerization
   - Infrastructure as Code (AWS/K8s)
   - CI/CD pipelines
   - Comprehensive documentation

### 6. **Development Experience**
   - Jupyter notebooks for experimentation
   - Utility scripts for common tasks
   - Clear project structure

## Next Steps After Confirmation

1. Create all folder structures
2. Initialize Python package structure with `__init__.py` files
3. Set up configuration files (pyproject.toml, requirements.txt, .env.example)
4. Create base classes and interfaces
5. Set up Docker configuration
6. Initialize testing framework
7. Create initial README with setup instructions

