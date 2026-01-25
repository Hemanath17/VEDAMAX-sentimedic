"""Application constants."""

# Medical Entity Types
MEDICAL_ENTITY_TYPES = [
    "DISEASE",
    "SYMPTOM",
    "MEDICATION",
    "DOSAGE",
    "LAB_RESULT",
    "VITAL_SIGN",
    "PROCEDURE",
    "BODY_PART",
    "CONDITION",
]

# Emotion Categories
EMOTION_CATEGORIES = [
    "joy",
    "sadness",
    "anger",
    "fear",
    "surprise",
    "disgust",
    "neutral",
    "anxiety",
]

# Persona Levels
PERSONA_LEVELS = {
    "LOW": {"empathy": 0.3, "formality": 0.7},
    "MEDIUM": {"empathy": 0.5, "formality": 0.5},
    "HIGH": {"empathy": 0.8, "formality": 0.3},
}

# Risk Levels
RISK_LEVELS = {
    "LOW": 0.0,
    "MEDIUM": 0.5,
    "HIGH": 0.8,
    "CRITICAL": 0.95,
}

# Router Decision Types
ROUTER_DECISIONS = {
    "DIRECT_RETRIEVAL": "direct_knowledge_retrieval",
    "CALCULATION": "calculation_log_analysis",
    "SAFETY_INTERCEPTION": "safety_interception",
}

# Chunking Defaults
DEFAULT_CHUNK_SIZE = 512
DEFAULT_CHUNK_OVERLAP = 50
SEMANTIC_CHUNK_THRESHOLD = 0.7

# Retrieval Defaults
DEFAULT_TOP_K = 10
DEFAULT_RERANK_TOP_K = 5
DEFAULT_SIMILARITY_THRESHOLD = 0.7

# File Extensions
SUPPORTED_FILE_EXTENSIONS = [".pdf", ".docx", ".doc", ".txt"]

