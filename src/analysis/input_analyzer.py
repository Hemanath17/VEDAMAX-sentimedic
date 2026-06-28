"""Input analyzer that orchestrates NER and sentiment analysis."""

from typing import Dict, Any, Optional, List
import asyncio
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

from src.analysis.ner.medical_ner import MedicalNER
from src.analysis.sentiment.sentiment_analyzer import SentimentAnalyzer
from src.analysis.sentiment.persona_mapper import PersonaMapper
from src.config.logging_config import get_logger
from src.config.settings import settings

logger = get_logger(__name__)


class InputAnalyzer:
    """
    Orchestrates NER and sentiment analysis for user input.
    
    Runs analyses in parallel for optimal performance.
    """

    def __init__(
        self,
        ner_model: Optional[str] = None,
        use_parallel: bool = True,
        max_workers: int = 2,
    ):
        """
        Initialize input analyzer.

        Args:
            ner_model: NER model name (defaults to settings)
            use_parallel: Whether to use parallel processing
            max_workers: Maximum number of parallel workers
        """
        self.use_parallel = use_parallel
        self.max_workers = max_workers

        # Initialize components
        self.ner = MedicalNER(model_name=ner_model)
        self.sentiment_analyzer = SentimentAnalyzer()
        self.persona_mapper = PersonaMapper()

        logger.info(
            f"Initialized InputAnalyzer: parallel={use_parallel}, workers={max_workers}"
        )

    def analyze(
        self,
        text: str,
        include_persona: bool = True,
        include_entities: bool = True,
        include_sentiment: bool = True,
    ) -> Dict[str, Any]:
        """
        Analyze user input with NER and sentiment analysis.

        Args:
            text: Input text to analyze
            include_persona: Whether to include persona mapping
            include_entities: Whether to extract medical entities
            include_sentiment: Whether to perform sentiment analysis

        Returns:
            Comprehensive analysis dictionary:
            {
                "text": str,                    # Original text
                "entities": List[MedicalEntity], # Extracted medical entities
                "sentiment": Dict,              # Sentiment analysis result
                "persona": Dict,                # Persona parameters (if include_persona)
                "summary": Dict,                 # Analysis summary
                "processing_time": float,       # Processing time in seconds
            }
        """
        start_time = time.time()

        if not text or not text.strip():
            return self._empty_result(text)

        try:
            if self.use_parallel:
                result = self._analyze_parallel(
                    text, include_entities, include_sentiment, include_persona
                )
            else:
                result = self._analyze_sequential(
                    text, include_entities, include_sentiment, include_persona
                )

            processing_time = time.time() - start_time
            result["processing_time"] = processing_time

            logger.info(
                f"Analyzed input: {len(result.get('entities', []))} entities, "
                f"{result.get('sentiment', {}).get('sentiment', 'unknown')} sentiment, "
                f"{processing_time:.3f}s"
            )

            return result

        except Exception as e:
            logger.error(f"Error analyzing input: {e}", exc_info=True)
            return self._empty_result(text)

    def _analyze_parallel(
        self,
        text: str,
        include_entities: bool,
        include_sentiment: bool,
        include_persona: bool,
    ) -> Dict[str, Any]:
        """Analyze input using parallel processing."""
        results = {}

        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            futures = {}

            # Submit NER task
            if include_entities:
                def extract_and_process():
                    raw_entities = self.ner.extract_entities(text)
                    return self.ner.post_process_entities(raw_entities)
                futures["entities"] = executor.submit(extract_and_process)

            # Submit sentiment analysis task
            if include_sentiment:
                futures["sentiment"] = executor.submit(self.sentiment_analyzer.analyze, text)

            # Wait for results
            for key, future in futures.items():
                try:
                    results[key] = future.result()
                except Exception as e:
                    logger.error(f"Error in {key} analysis: {e}", exc_info=True)
                    results[key] = [] if key == "entities" else {}

        # Get persona mapping if requested
        if include_persona and "sentiment" in results:
            emotion_result = results["sentiment"].get("emotion_analysis", {})
            results["persona"] = self.persona_mapper.map_to_persona(emotion_result)

        # Create summary
        results["summary"] = self._create_summary(results)

        return {
            "text": text,
            **results,
        }

    def _analyze_sequential(
        self,
        text: str,
        include_entities: bool,
        include_sentiment: bool,
        include_persona: bool,
    ) -> Dict[str, Any]:
        """Analyze input sequentially."""
        results = {}

        # Extract entities
        if include_entities:
            raw_entities = self.ner.extract_entities(text)
            # Post-process entities (Step 8)
            results["entities"] = self.ner.post_process_entities(raw_entities)

        # Analyze sentiment
        if include_sentiment:
            results["sentiment"] = self.sentiment_analyzer.analyze(text)

        # Map to persona
        if include_persona and "sentiment" in results:
            emotion_result = results["sentiment"].get("emotion_analysis", {})
            results["persona"] = self.persona_mapper.map_to_persona(emotion_result)

        # Create summary
        results["summary"] = self._create_summary(results)

        return {
            "text": text,
            **results,
        }

    async def analyze_async(
        self,
        text: str,
        include_persona: bool = True,
        include_entities: bool = True,
        include_sentiment: bool = True,
    ) -> Dict[str, Any]:
        """
        Asynchronously analyze user input.

        Args:
            text: Input text to analyze
            include_persona: Whether to include persona mapping
            include_entities: Whether to extract medical entities
            include_sentiment: Whether to perform sentiment analysis

        Returns:
            Comprehensive analysis dictionary
        """
        loop = asyncio.get_event_loop()

        # Run analysis in executor
        result = await loop.run_in_executor(
            None,
            self.analyze,
            text,
            include_persona,
            include_entities,
            include_sentiment,
        )

        return result

    def analyze_batch(
        self,
        texts: List[str],
        include_persona: bool = True,
    ) -> List[Dict[str, Any]]:
        """
        Analyze multiple texts in batch.

        Args:
            texts: List of input texts
            include_persona: Whether to include persona mapping

        Returns:
            List of analysis results
        """
        results = []
        for text in texts:
            result = self.analyze(text, include_persona=include_persona)
            results.append(result)
        return results

    def _create_summary(self, results: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create summary of analysis results.

        Args:
            results: Analysis results dictionary

        Returns:
            Summary dictionary
        """
        summary = {
            "has_entities": False,
            "entity_count": 0,
            "entity_types": {},
            "sentiment": "unknown",
            "dominant_bucket": None,
            "risk_level": 0.0,
            "anxiety_level": 0.0,
            "persona_level": None,
        }

        # Entity summary
        entities = results.get("entities", [])
        if entities:
            summary["has_entities"] = True
            summary["entity_count"] = len(entities)

            # Count by type
            from collections import Counter
            entity_types = Counter(e.entity_type.value for e in entities)
            summary["entity_types"] = dict(entity_types)

        # Sentiment summary
        sentiment = results.get("sentiment", {})
        if sentiment:
            summary["sentiment"] = sentiment.get("sentiment", "unknown")
            summary["dominant_bucket"] = sentiment.get("dominant_bucket")
            summary["risk_level"] = sentiment.get("risk_level", 0.0)
            summary["anxiety_level"] = sentiment.get("anxiety_level", 0.0)

        # Persona summary
        persona = results.get("persona", {})
        if persona:
            summary["persona_level"] = persona.get("persona_level")
            summary["empathy_level"] = persona.get("empathy_level", 0.5)
            summary["safety_priority"] = persona.get("safety_priority", False)

        return summary

    def _empty_result(self, text: str) -> Dict[str, Any]:
        """Return empty analysis result."""
        return {
            "text": text,
            "entities": [],
            "sentiment": {},
            "persona": {},
            "summary": {
                "has_entities": False,
                "entity_count": 0,
                "sentiment": "neutral",
                "risk_level": 0.0,
            },
            "processing_time": 0.0,
        }

    def get_analysis_metadata(self, analysis_result: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extract metadata from analysis result.

        Args:
            analysis_result: Analysis result dictionary

        Returns:
            Metadata dictionary
        """
        return {
            "text_length": len(analysis_result.get("text", "")),
            "entity_count": len(analysis_result.get("entities", [])),
            "processing_time": analysis_result.get("processing_time", 0.0),
            "has_sentiment": bool(analysis_result.get("sentiment")),
            "has_persona": bool(analysis_result.get("persona")),
        }

