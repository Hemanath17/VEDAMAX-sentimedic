"""Chunker factory for automatic chunker selection based on strategy."""

from typing import Dict, Type, Optional

from src.ingestion.chunkers.chunk_strategy import ChunkStrategy, ChunkingError
from src.ingestion.chunkers.token_chunker import TokenChunker
from src.ingestion.chunkers.semantic_chunker import SemanticChunker
from src.config.logging_config import get_logger

logger = get_logger(__name__)


class ChunkerFactory:
    """Factory class for creating appropriate chunkers based on strategy."""

    def __init__(self):
        """Initialize chunker factory with default chunkers."""
        self._chunkers: Dict[str, Type[ChunkStrategy]] = {}
        self._chunker_instances: Dict[str, ChunkStrategy] = {}
        self._register_default_chunkers()

    def _register_default_chunkers(self) -> None:
        """Register default chunkers (semantic, token)."""
        self.register_chunker(SemanticChunker, strategy_name="semantic", create_instance=False)
        self.register_chunker(TokenChunker, strategy_name="token", create_instance=False)
        logger.info("Registered default chunkers: semantic, token")

    def register_chunker(
        self,
        chunker_class: Type[ChunkStrategy],
        strategy_name: Optional[str] = None,
        create_instance: bool = False,
    ) -> None:
        """
        Register a chunker class with the factory.

        Args:
            chunker_class: Chunker class to register
            strategy_name: Name for the strategy (defaults to class name)
            create_instance: Whether to create and cache an instance
        """
        try:
            name = strategy_name or chunker_class.__name__.lower().replace("chunker", "")
            name = name.lower()

            self._chunkers[name] = chunker_class
            logger.debug(f"Registered chunker {chunker_class.__name__} as '{name}'")

            # Create and cache instance if requested
            if create_instance:
                if name not in self._chunker_instances:
                    self._chunker_instances[name] = chunker_class()
                    logger.debug(f"Cached instance of {chunker_class.__name__}")

        except Exception as e:
            logger.error(f"Failed to register chunker {chunker_class.__name__}: {e}")
            raise ChunkingError(f"Failed to register chunker: {e}") from e

    def get_chunker(
        self,
        strategy: str = "semantic",
        chunk_size: Optional[int] = None,
        chunk_overlap: Optional[int] = None,
        use_cached: bool = False,
        **kwargs,
    ) -> ChunkStrategy:
        """
        Get appropriate chunker for the given strategy.

        Args:
            strategy: Chunking strategy name ("semantic" or "token")
            chunk_size: Optional chunk size override
            chunk_overlap: Optional chunk overlap override
            use_cached: Whether to use cached chunker instances
            **kwargs: Additional arguments for chunker initialization

        Returns:
            Appropriate chunker instance

        Raises:
            ChunkingError: If no chunker is found for the strategy
        """
        strategy = strategy.lower()

        # Check if chunker is registered
        chunker_class = self._chunkers.get(strategy)
        if not chunker_class:
            supported = ", ".join(self._chunkers.keys())
            raise ChunkingError(
                f"No chunker found for strategy '{strategy}'. "
                f"Supported strategies: {supported}"
            )

        # Check for cached instance
        if use_cached and strategy in self._chunker_instances:
            cached = self._chunker_instances[strategy]
            # Check if cached instance matches requested parameters
            if chunk_size is None and chunk_overlap is None:
                logger.debug(f"Using cached chunker instance: {strategy}")
                return cached

        # Create new instance with parameters
        try:
            init_kwargs = {}
            if chunk_size is not None:
                init_kwargs["chunk_size"] = chunk_size
            if chunk_overlap is not None:
                init_kwargs["chunk_overlap"] = chunk_overlap
            init_kwargs.update(kwargs)

            chunker_instance = chunker_class(**init_kwargs)
            logger.debug(f"Created new chunker instance: {chunker_class.__name__}")

            # Cache instance if caching is enabled
            if use_cached:
                self._chunker_instances[strategy] = chunker_instance

            return chunker_instance

        except Exception as e:
            logger.error(f"Failed to create chunker instance {chunker_class.__name__}: {e}")
            raise ChunkingError(f"Failed to create chunker: {e}") from e

    def get_supported_strategies(self) -> list:
        """
        Get list of all supported chunking strategies.

        Returns:
            List of supported strategy names
        """
        return sorted(list(self._chunkers.keys()))

    def is_strategy_supported(self, strategy: str) -> bool:
        """
        Check if a chunking strategy is supported.

        Args:
            strategy: Strategy name to check

        Returns:
            True if strategy is supported
        """
        return strategy.lower() in self._chunkers

    def get_chunker_info(self) -> Dict[str, str]:
        """
        Get information about registered chunkers.

        Returns:
            Dictionary mapping strategy names to chunker class names
        """
        return {
            strategy: chunker_class.__name__
            for strategy, chunker_class in self._chunkers.items()
        }

    def clear_cache(self) -> None:
        """Clear cached chunker instances."""
        self._chunker_instances.clear()
        logger.debug("Cleared chunker instance cache")

    def unregister_chunker(self, strategy: str) -> None:
        """
        Unregister a chunker for a specific strategy.

        Args:
            strategy: Strategy name to unregister
        """
        strategy = strategy.lower()
        if strategy in self._chunkers:
            chunker_class = self._chunkers.pop(strategy)
            logger.info(f"Unregistered chunker {chunker_class.__name__} for strategy: {strategy}")

            # Also remove cached instance if it exists
            if strategy in self._chunker_instances:
                del self._chunker_instances[strategy]
        else:
            logger.warning(f"Strategy {strategy} not registered, nothing to unregister")


# Global factory instance
_default_factory: Optional[ChunkerFactory] = None


def get_chunker_factory() -> ChunkerFactory:
    """
    Get the default global chunker factory instance.

    Returns:
        Global ChunkerFactory instance
    """
    global _default_factory
    if _default_factory is None:
        _default_factory = ChunkerFactory()
    return _default_factory


def get_chunker(strategy: str = "semantic", **kwargs) -> ChunkStrategy:
    """
    Convenience function to get a chunker using the default factory.

    Args:
        strategy: Chunking strategy name
        **kwargs: Additional arguments for chunker initialization

    Returns:
        Appropriate chunker instance
    """
    factory = get_chunker_factory()
    return factory.get_chunker(strategy=strategy, **kwargs)

