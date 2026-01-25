"""Medical entity type definitions and mappings."""

from enum import Enum
from typing import Dict, List, Optional, Set
from dataclasses import dataclass

from src.config.constants import MEDICAL_ENTITY_TYPES


class MedicalEntityType(str, Enum):
    """Enumeration of medical entity types."""

    DISEASE = "DISEASE"
    SYMPTOM = "SYMPTOM"
    MEDICATION = "MEDICATION"
    DOSAGE = "DOSAGE"
    LAB_RESULT = "LAB_RESULT"
    VITAL_SIGN = "VITAL_SIGN"
    PROCEDURE = "PROCEDURE"
    BODY_PART = "BODY_PART"
    CONDITION = "CONDITION"
    ALLERGY = "ALLERGY"
    DIAGNOSIS = "DIAGNOSIS"
    TREATMENT = "TREATMENT"
    TIME = "TIME"
    FREQUENCY = "FREQUENCY"
    DURATION = "DURATION"


@dataclass
class MedicalEntity:
    """Represents a medical entity extracted from text."""

    text: str
    entity_type: MedicalEntityType
    start_char: int
    end_char: int
    confidence: float
    normalized_text: Optional[str] = None
    metadata: Optional[Dict] = None

    def __post_init__(self):
        """Initialize default values."""
        if self.normalized_text is None:
            self.normalized_text = self.text
        if self.metadata is None:
            self.metadata = {}


class EntityTypeMapper:
    """Maps entity types from different NER models to standardized types."""

    # Mapping from spaCy Med7 labels to our entity types
    SPACY_MED7_MAPPING = {
        "DOSAGE": MedicalEntityType.DOSAGE,
        "DRUG": MedicalEntityType.MEDICATION,
        "DURATION": MedicalEntityType.DURATION,
        "FORM": MedicalEntityType.MEDICATION,  # Medication form
        "FREQUENCY": MedicalEntityType.FREQUENCY,
        "ROUTE": MedicalEntityType.MEDICATION,  # Administration route
        "STRENGTH": MedicalEntityType.DOSAGE,
    }

    # Mapping from general medical NER labels
    GENERAL_MEDICAL_MAPPING = {
        "DISEASE": MedicalEntityType.DISEASE,
        "SYMPTOM": MedicalEntityType.SYMPTOM,
        "MEDICATION": MedicalEntityType.MEDICATION,
        "LAB_RESULT": MedicalEntityType.LAB_RESULT,
        "VITAL_SIGN": MedicalEntityType.VITAL_SIGN,
        "PROCEDURE": MedicalEntityType.PROCEDURE,
        "BODY_PART": MedicalEntityType.BODY_PART,
        "CONDITION": MedicalEntityType.CONDITION,
        "ALLERGY": MedicalEntityType.ALLERGY,
        "DIAGNOSIS": MedicalEntityType.DIAGNOSIS,
        "TREATMENT": MedicalEntityType.TREATMENT,
    }

    @classmethod
    def map_entity_type(cls, source_type: str, source_model: str = "spacy_med7") -> MedicalEntityType:
        """
        Map entity type from source model to standardized type.

        Args:
            source_type: Entity type from source model
            source_model: Source model identifier

        Returns:
            Standardized MedicalEntityType
        """
        source_type = source_type.upper()

        if source_model == "spacy_med7":
            return cls.SPACY_MED7_MAPPING.get(source_type, MedicalEntityType.CONDITION)
        else:
            return cls.GENERAL_MEDICAL_MAPPING.get(source_type, MedicalEntityType.CONDITION)

    @classmethod
    def get_all_entity_types(cls) -> List[MedicalEntityType]:
        """
        Get all supported entity types.

        Returns:
            List of all MedicalEntityType values
        """
        return list(MedicalEntityType)

    @classmethod
    def get_entity_type_description(cls, entity_type: MedicalEntityType) -> str:
        """
        Get description for an entity type.

        Args:
            entity_type: Entity type

        Returns:
            Description string
        """
        descriptions = {
            MedicalEntityType.DISEASE: "A disease or medical condition",
            MedicalEntityType.SYMPTOM: "A symptom or sign of illness",
            MedicalEntityType.MEDICATION: "A medication or drug",
            MedicalEntityType.DOSAGE: "Medication dosage information",
            MedicalEntityType.LAB_RESULT: "Laboratory test result",
            MedicalEntityType.VITAL_SIGN: "Vital sign measurement",
            MedicalEntityType.PROCEDURE: "Medical procedure or intervention",
            MedicalEntityType.BODY_PART: "Anatomical body part",
            MedicalEntityType.CONDITION: "General medical condition",
            MedicalEntityType.ALLERGY: "Allergy or adverse reaction",
            MedicalEntityType.DIAGNOSIS: "Medical diagnosis",
            MedicalEntityType.TREATMENT: "Treatment or therapy",
            MedicalEntityType.TIME: "Time-related information",
            MedicalEntityType.FREQUENCY: "Frequency of medication or treatment",
            MedicalEntityType.DURATION: "Duration of treatment or condition",
        }
        return descriptions.get(entity_type, "Medical entity")


class EntityRelationship:
    """Defines relationships between medical entities."""

    # Entity relationships (entity_type -> related_types)
    RELATIONSHIPS = {
        MedicalEntityType.MEDICATION: [
            MedicalEntityType.DOSAGE,
            MedicalEntityType.FREQUENCY,
            MedicalEntityType.DURATION,
        ],
        MedicalEntityType.SYMPTOM: [
            MedicalEntityType.DISEASE,
            MedicalEntityType.CONDITION,
        ],
        MedicalEntityType.DISEASE: [
            MedicalEntityType.SYMPTOM,
            MedicalEntityType.TREATMENT,
        ],
        MedicalEntityType.LAB_RESULT: [
            MedicalEntityType.DISEASE,
            MedicalEntityType.CONDITION,
        ],
        MedicalEntityType.PROCEDURE: [
            MedicalEntityType.BODY_PART,
            MedicalEntityType.DISEASE,
        ],
    }

    @classmethod
    def get_related_types(cls, entity_type: MedicalEntityType) -> List[MedicalEntityType]:
        """
        Get related entity types for a given entity type.

        Args:
            entity_type: Entity type

        Returns:
            List of related entity types
        """
        return cls.RELATIONSHIPS.get(entity_type, [])

    @classmethod
    def are_related(cls, entity_type1: MedicalEntityType, entity_type2: MedicalEntityType) -> bool:
        """
        Check if two entity types are related.

        Args:
            entity_type1: First entity type
            entity_type2: Second entity type

        Returns:
            True if related
        """
        related = cls.get_related_types(entity_type1)
        return entity_type2 in related or entity_type1 in cls.get_related_types(entity_type2)


class EntityNormalizer:
    """Normalizes medical entity text to standard forms."""

    # Common medical term normalizations
    NORMALIZATIONS = {
        # Medication abbreviations
        "aspirin": "acetylsalicylic acid",
        "tylenol": "acetaminophen",
        "advil": "ibuprofen",
        # Common misspellings
        "diabetis": "diabetes",
        "hypertention": "hypertension",
    }

    @classmethod
    def normalize(cls, text: str) -> str:
        """
        Normalize entity text.

        Args:
            text: Entity text

        Returns:
            Normalized text
        """
        text_lower = text.lower().strip()
        return cls.NORMALIZATIONS.get(text_lower, text)

    @classmethod
    def add_normalization(cls, original: str, normalized: str):
        """
        Add a custom normalization rule.

        Args:
            original: Original text
            normalized: Normalized text
        """
        cls.NORMALIZATIONS[original.lower()] = normalized

