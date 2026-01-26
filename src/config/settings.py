"""Application settings using Pydantic Settings."""

from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Application
    APP_NAME: str = "SentiMedical-RAG"
    APP_VERSION: str = "0.1.0"
    ENVIRONMENT: str = "development"
    DEBUG: bool = True
    LOG_LEVEL: str = "INFO"

    # API
    API_HOST: str = "0.0.0.0"
    API_PORT: int = 8000
    API_RELOAD: bool = True

    # Qdrant
    QDRANT_HOST: str = "localhost"
    QDRANT_PORT: int = 6333
    QDRANT_API_KEY: Optional[str] = None
    QDRANT_COLLECTION_NAME: str = "medical_documents"
    QDRANT_VECTOR_SIZE: int = 1024

    # Embeddings
    EMBEDDING_MODEL: str = "BAAI/bge-m3"
    EMBEDDING_DEVICE: str = "cpu"
    EMBEDDING_BATCH_SIZE: int = 32

    # LLM
    OPENAI_API_KEY: Optional[str] = None
    ANTHROPIC_API_KEY: Optional[str] = None
    LLM_MODEL: str = "gpt-4-turbo-preview"
    LLM_TEMPERATURE: float = 0.7
    LLM_MAX_TOKENS: int = 2000

    # Sentiment
    SENTIMENT_MODEL: str = "SamLowe/roberta-base-go_emotions"
    SENTIMENT_DEVICE: str = "cpu"

    # NER
    NER_MODEL: str = "en_core_med7_lg"
    SPACY_MODEL: str = "en_core_web_sm"

    # LangChain
    LANGCHAIN_API_KEY: Optional[str] = None
    LANGCHAIN_TRACING_V2: bool = True
    LANGCHAIN_PROJECT: str = "SentiMedical-RAG"

    # Monitoring
    PHOENIX_HOST: str = "localhost"
    PHOENIX_PORT: int = 6006
    LANGSMITH_API_KEY: Optional[str] = None

    # Evaluation
    EVALUATION_ENABLED: bool = True
    RAGAS_METRICS: str = "faithfulness,relevancy,answer_correctness"

    # Safety
    SAFETY_ENABLED: bool = True
    RISK_THRESHOLD: float = 0.8
    MAX_INPUT_LENGTH: int = 5000
    MAX_OUTPUT_LENGTH: int = 5000

    # Retrieval
    HYBRID_SEARCH_ENABLED: bool = True
    BM25_K1: float = 1.5
    BM25_B: float = 0.75
    VECTOR_SEARCH_TOP_K: int = 10
    RERANKER_TOP_K: int = 5
    RERANKER_MODEL: str = "cross-encoder/ms-marco-MiniLM-L-6-v2"

    # Paths
    DATA_DIR: str = "./data"
    RAW_DOCUMENTS_DIR: str = "./data/raw"
    PROCESSED_CHUNKS_DIR: str = "./data/processed/chunks"
    EMBEDDINGS_CACHE_DIR: str = "./data/embeddings"
    MODELS_DIR: str = "./models"
    LOGS_DIR: str = "./logs"

    # AWS
    AWS_REGION: Optional[str] = None
    AWS_ACCESS_KEY_ID: Optional[str] = None
    AWS_SECRET_ACCESS_KEY: Optional[str] = None
    S3_BUCKET_NAME: Optional[str] = None

    # Database
    DATABASE_URL: str = "postgresql://user:password@localhost:5432/vedamax"
    DATABASE_POOL_SIZE: int = 5
    DATABASE_MAX_OVERFLOW: int = 10
    
    # User Context & Memory
    CONTEXT_ENABLED: bool = True
    MEMORY_SESSION_SIZE: int = 10  # Last N messages in session
    MEMORY_RETENTION_DAYS: int = 30  # Keep last N days
    EMOTION_TRACKING_ENABLED: bool = True
    RISK_ESCALATION_ENABLED: bool = True
    RISK_ESCALATION_THRESHOLD: float = 0.2  # 20% increase
    RISK_ESCALATION_DURATION: int = 5  # minutes
    USER_ID_HASH_SALT: str = "vedamax-salt-change-in-production"

    # Authentication
    JWT_SECRET_KEY: str = "your-secret-key-change-in-production"
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRATION_HOURS: int = 24


# Global settings instance
settings = Settings()

