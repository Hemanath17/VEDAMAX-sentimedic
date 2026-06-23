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

# Emotion Categories (GoEmotions 28 labels)
GO_EMOTIONS_LABELS = [
    "admiration", "amusement", "anger", "annoyance", "approval", "caring",
    "confusion", "curiosity", "desire", "disappointment", "disapproval",
    "disgust", "embarrassment", "excitement", "fear", "gratitude", "grief",
    "joy", "love", "nervousness", "optimism", "pride", "realization",
    "relief", "remorse", "sadness", "surprise", "neutral"
]

# VEDAMAX Emotion Buckets (7 clinically interpretable buckets)
VEDAMAX_EMOTION_BUCKETS = {
    "NEUTRAL": {
        "purpose": "Pure info",
        "emotions": ["neutral", "curiosity"],
        "empathy_level": 0.3,
        "risk_level": 0.0,
    },
    "LOW_CONCERN": {
        "purpose": "Mild unease",
        "emotions": ["nervous", "unsure", "nervousness", "confusion"],
        "empathy_level": 0.4,
        "risk_level": 0.2,
    },
    "ANTICIPATORY_STRESS": {
        "purpose": "Waiting anxiety",
        "emotions": ["worried", "uneasy", "disappointment", "embarrassment"],
        "empathy_level": 0.6,
        "risk_level": 0.4,
    },
    "HIGH_ANXIETY": {
        "purpose": "Health fear",
        "emotions": ["anxiety", "fear", "nervousness"],
        "empathy_level": 0.8,
        "risk_level": 0.6,
    },
    "SADNESS_GRIEF": {
        "purpose": "Emotional pain",
        "emotions": ["sadness", "grief", "disappointment", "remorse"],
        "empathy_level": 0.9,
        "risk_level": 0.5,
    },
    "FRUSTRATION_ANGER": {
        "purpose": "System friction",
        "emotions": ["anger", "irritation", "annoyance", "disapproval"],
        "empathy_level": 0.7,
        "risk_level": 0.4,
    },
    "HIGH_RISK": {
        "purpose": "Emergency",
        "emotions": ["panic", "self-harm", "despair", "extreme_fear"],
        "empathy_level": 1.0,
        "risk_level": 0.95,
    },
}

# Legacy emotion categories (for backward compatibility)
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

# Vector store corpus types (dual-collection partitioning)
CORPUS_KB = "kb"
CORPUS_USER_DOC = "user_doc"
VALID_CORPORA = {CORPUS_KB, CORPUS_USER_DOC}

# Chunking Defaults
DEFAULT_CHUNK_SIZE = 512
DEFAULT_CHUNK_OVERLAP = 50
SEMANTIC_CHUNK_THRESHOLD = 0.7

# Retrieval Defaults
DEFAULT_TOP_K = 10
DEFAULT_RERANK_TOP_K = 5
DEFAULT_SIMILARITY_THRESHOLD = 0.7
RRF_K = 60
RERANK_POOL_MAX = 30
RETRIEVAL_SCORE_FLOOR = 0.3

# File Extensions
SUPPORTED_FILE_EXTENSIONS = [".pdf", ".docx", ".doc", ".txt"]

