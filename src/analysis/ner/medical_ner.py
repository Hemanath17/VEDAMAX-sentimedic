"""Medical Named Entity Recognition using spaCy and medical models."""

from typing import List, Dict, Any, Optional
from pathlib import Path

from src.analysis.ner.entity_types import (
    MedicalEntity,
    MedicalEntityType,
    EntityTypeMapper,
    EntityNormalizer,
)
from src.config.logging_config import get_logger
from src.config.settings import settings

logger = get_logger(__name__)

# Try to import spaCy
try:
    import spacy
    from spacy import displacy
    SPACY_AVAILABLE = True
except ImportError:
    SPACY_AVAILABLE = False
    logger.warning("spaCy not available, medical NER will be limited")

# Try to import transformers as fallback
try:
    from transformers import pipeline
    TRANSFORMERS_AVAILABLE = True
except ImportError:
    TRANSFORMERS_AVAILABLE = False
    logger.warning("transformers not available for NER fallback")


class MedicalNER:
    """Medical Named Entity Recognition system."""

    def __init__(
        self,
        model_name: Optional[str] = None,
        use_med7: bool = True,
        confidence_threshold: float = 0.5,
    ):
        """
        Initialize Medical NER system.

        Args:
            model_name: Custom model name (defaults to settings)
            use_med7: Whether to use Med7 model (if available)
            confidence_threshold: Minimum confidence for entity extraction
        """
        self.model_name = model_name or settings.NER_MODEL
        self.use_med7 = use_med7
        self.confidence_threshold = confidence_threshold
        self._nlp = None
        self._transformer_pipeline = None
        self._initialize_model()

    def _initialize_model(self) -> None:
        """Initialize the NER model."""
        if not SPACY_AVAILABLE:
            logger.warning("spaCy not available, initializing transformer fallback")
            self._initialize_transformer_fallback()
            return

        try:
            # Try to load spaCy model
            logger.info(f"Loading spaCy model: {self.model_name}")
            self._nlp = spacy.load(self.model_name)
            logger.info(f"Successfully loaded spaCy model: {self.model_name}")

            # Check if model has NER component
            if "ner" not in self._nlp.pipe_names:
                logger.warning(f"Model {self.model_name} does not have NER component")
                self._initialize_transformer_fallback()

        except OSError:
            logger.warning(
                f"spaCy model {self.model_name} not found. "
                f"Please install it with: python -m spacy download {self.model_name}"
            )
            self._initialize_transformer_fallback()
        except Exception as e:
            logger.error(f"Error loading spaCy model: {e}", exc_info=True)
            self._initialize_transformer_fallback()

    def _initialize_transformer_fallback(self) -> None:
        """Initialize transformer-based NER as fallback."""
        if not TRANSFORMERS_AVAILABLE:
            logger.warning("No NER model available - using basic keyword matching")
            return

        try:
            # Use a general medical NER model
            logger.info("Initializing transformer NER pipeline")
            self._transformer_pipeline = pipeline(
                "ner",
                model="dslim/bert-base-NER",
                aggregation_strategy="simple",
            )
            logger.info("Transformer NER pipeline initialized")
        except Exception as e:
            logger.error(f"Error initializing transformer NER: {e}", exc_info=True)

    def extract_entities(self, text: str) -> List[MedicalEntity]:
        """
        Extract medical entities from text.

        Args:
            text: Input text to analyze

        Returns:
            List of MedicalEntity objects
        """
        if not text or not text.strip():
            logger.warning("Empty text provided for entity extraction")
            return []

        try:
            if self._nlp:
                return self._extract_with_spacy(text)
            elif self._transformer_pipeline:
                return self._extract_with_transformers(text)
            else:
                return self._extract_with_keywords(text)

        except Exception as e:
            logger.error(f"Error extracting entities: {e}", exc_info=True)
            return []

    def _extract_with_spacy(self, text: str) -> List[MedicalEntity]:
        """Extract entities using spaCy model."""
        doc = self._nlp(text)
        entities = []

        for ent in doc.ents:
            # Map spaCy entity label to our entity type
            entity_type = EntityTypeMapper.map_entity_type(
                ent.label_, source_model="spacy_med7" if self.use_med7 else "general"
            )

            # Normalize entity text
            normalized_text = EntityNormalizer.normalize(ent.text)

            # Calculate confidence (spaCy doesn't provide confidence by default)
            confidence = 0.8  # Default confidence for spaCy entities

            medical_entity = MedicalEntity(
                text=ent.text,
                entity_type=entity_type,
                start_char=ent.start_char,
                end_char=ent.end_char,
                confidence=confidence,
                normalized_text=normalized_text,
                metadata={
                    "spacy_label": ent.label_,
                    "spacy_label_id": ent.label,
                },
            )

            # Filter by confidence threshold
            if confidence >= self.confidence_threshold:
                entities.append(medical_entity)

        logger.debug(f"Extracted {len(entities)} entities using spaCy")
        return entities

    def _extract_with_transformers(self, text: str) -> List[MedicalEntity]:
        """Extract entities using transformer pipeline."""
        results = self._transformer_pipeline(text)
        entities = []

        for result in results:
            entity_text = result.get("word", "").strip()
            if not entity_text:
                continue

            # Map transformer labels to medical entity types
            label = result.get("entity_group", result.get("label", "O"))
            entity_type = EntityTypeMapper.map_entity_type(label, source_model="general")

            # Get position information
            start_char = result.get("start", 0)
            end_char = result.get("end", len(entity_text))
            confidence = result.get("score", 0.5)

            normalized_text = EntityNormalizer.normalize(entity_text)

            medical_entity = MedicalEntity(
                text=entity_text,
                entity_type=entity_type,
                start_char=start_char,
                end_char=end_char,
                confidence=confidence,
                normalized_text=normalized_text,
                metadata={
                    "transformer_label": label,
                    "score": confidence,
                },
            )

            if confidence >= self.confidence_threshold:
                entities.append(medical_entity)

        logger.debug(f"Extracted {len(entities)} entities using transformers")
        return entities

    def _extract_with_keywords(self, text: str) -> List[MedicalEntity]:
        """Basic keyword-based entity extraction (fallback)."""
        # This is a very basic fallback - just identifies common medical terms
        common_medications = [
            "aspirin",
            "ibuprofen",
            "acetaminophen",
            "penicillin",
            "insulin",
        ]
        common_conditions = [
            "diabetes",
            "hypertension",
            "asthma",
            "arthritis",
        ]

        entities = []
        text_lower = text.lower()

        # Simple keyword matching
        for med in common_medications:
            if med in text_lower:
                idx = text_lower.find(med)
                entities.append(
                    MedicalEntity(
                        text=text[idx : idx + len(med)],
                        entity_type=MedicalEntityType.MEDICATION,
                        start_char=idx,
                        end_char=idx + len(med),
                        confidence=0.6,
                        normalized_text=med,
                    )
                )

        for condition in common_conditions:
            if condition in text_lower:
                idx = text_lower.find(condition)
                entities.append(
                    MedicalEntity(
                        text=text[idx : idx + len(condition)],
                        entity_type=MedicalEntityType.CONDITION,
                        start_char=idx,
                        end_char=idx + len(condition),
                        confidence=0.6,
                        normalized_text=condition,
                    )
                )

        logger.debug(f"Extracted {len(entities)} entities using keyword matching")
        return entities

    def extract_entities_batch(self, texts: List[str]) -> List[List[MedicalEntity]]:
        """
        Extract entities from multiple texts in batch.

        Args:
            texts: List of input texts

        Returns:
            List of entity lists (one per input text)
        """
        results = []
        for text in texts:
            entities = self.extract_entities(text)
            results.append(entities)
        return results

    def get_entities_by_type(
        self, entities: List[MedicalEntity], entity_type: MedicalEntityType
    ) -> List[MedicalEntity]:
        """
        Filter entities by type.

        Args:
            entities: List of entities
            entity_type: Entity type to filter

        Returns:
            Filtered list of entities
        """
        return [e for e in entities if e.entity_type == entity_type]

    def get_entity_summary(self, entities: List[MedicalEntity]) -> Dict[str, Any]:
        """
        Get summary statistics of extracted entities.

        Args:
            entities: List of entities

        Returns:
            Summary dictionary
        """
        summary = {
            "total_entities": len(entities),
            "by_type": {},
            "average_confidence": 0.0,
        }

        if not entities:
            return summary

        # Count by type
        for entity in entities:
            entity_type_str = entity.entity_type.value
            summary["by_type"][entity_type_str] = summary["by_type"].get(entity_type_str, 0) + 1

        # Calculate average confidence
        total_confidence = sum(e.confidence for e in entities)
        summary["average_confidence"] = total_confidence / len(entities)

        return summary

    def post_process_entities(self, entities: List[MedicalEntity]) -> List[MedicalEntity]:
        """
        Post-process extracted entities (Step 8).

        Args:
            entities: List of raw extracted entities

        Returns:
            List of post-processed entities
        """
        if not entities:
            return []

        processed = []

        for entity in entities:
            # Normalize entity text
            normalized = EntityNormalizer.normalize(entity.text)
            entity.normalized_text = normalized

            # Validate entity
            if self._validate_entity(entity):
                # Enrich metadata
                entity.metadata = entity.metadata or {}
                entity.metadata["normalized"] = True
                entity.metadata["validation_passed"] = True

                processed.append(entity)
            else:
                logger.debug(f"Entity validation failed: {entity.text}")

        # Remove duplicates (same text and type)
        processed = self._remove_duplicates(processed)

        # Sort by confidence (highest first)
        processed.sort(key=lambda e: e.confidence, reverse=True)

        logger.debug(f"Post-processed {len(entities)} entities to {len(processed)} valid entities")
        return processed

    def _validate_entity(self, entity: MedicalEntity) -> bool:
        """
        Validate an entity.

        Args:
            entity: Entity to validate

        Returns:
            True if entity is valid
        """
        # Check minimum confidence
        if entity.confidence < self.confidence_threshold:
            return False

        # Check text is not empty
        if not entity.text or not entity.text.strip():
            return False

        # Check text length is reasonable
        if len(entity.text) > 100:  # Very long entities might be errors
            return False

        # Check position is valid
        if entity.start_char < 0 or entity.end_char <= entity.start_char:
            return False

        return True

    def _remove_duplicates(self, entities: List[MedicalEntity]) -> List[MedicalEntity]:
        """
        Remove duplicate entities.

        Args:
            entities: List of entities

        Returns:
            List with duplicates removed
        """
        seen = set()
        unique = []

        for entity in entities:
            # Create unique key from text, type, and position
            key = (
                entity.normalized_text.lower(),
                entity.entity_type.value,
                entity.start_char,
            )

            if key not in seen:
                seen.add(key)
                unique.append(entity)

        return unique

    def enrich_entity_metadata(self, entities: List[MedicalEntity], context: str = "") -> List[MedicalEntity]:
        """
        Enrich entity metadata with additional information.

        Args:
            entities: List of entities
            context: Optional context text

        Returns:
            List of entities with enriched metadata
        """
        for entity in entities:
            if not entity.metadata:
                entity.metadata = {}

            # Add entity relationships
            from src.analysis.ner.entity_types import EntityRelationship
            related_types = EntityRelationship.get_related_types(entity.entity_type)
            entity.metadata["related_entity_types"] = [t.value for t in related_types]

            # Add context information if available
            if context:
                # Find surrounding context
                start = max(0, entity.start_char - 20)
                end = min(len(context), entity.end_char + 20)
                entity.metadata["context"] = context[start:end]

        return entities

