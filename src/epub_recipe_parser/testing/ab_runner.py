"""A/B test runner for comparing extraction strategies."""

import logging
from typing import Optional, Dict, Any
from bs4 import BeautifulSoup

from epub_recipe_parser.core.models import ABTestConfig
from epub_recipe_parser.core.protocols import IComponentExtractor

logger = logging.getLogger(__name__)


class ABTestRunner:
    """Runs A/B tests comparing extraction strategies.

    Implements Strategy Pattern to separate A/B testing concerns from main extraction logic.
    """

    def __init__(self, config: ABTestConfig):
        """Initialize A/B test runner with configuration.

        Args:
            config: A/B testing configuration
        """
        self.config = config

    def compare_extractors(
        self,
        control_extractor: IComponentExtractor,
        treatment_extractor: IComponentExtractor,
        soup: BeautifulSoup,
        text: str,
        control_result: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Compare two extraction strategies (control vs treatment).

        Args:
            control_extractor: The current/old extraction strategy
            treatment_extractor: The new extraction strategy to test
            soup: BeautifulSoup object to extract from
            text: Plain text to extract from
            control_result: Pre-computed control result (optional, will compute if not provided)

        Returns:
            dict: Comparison results including:
                - old_ingredients: Result from control
                - new_ingredients: Result from treatment
                - old_length: Length of control result
                - new_length: Length of treatment result
                - old_success: Whether control succeeded
                - new_success: Whether treatment succeeded
                - agreement: Whether both methods agreed
                - confidence: Confidence score from treatment
                - linguistic_score: Linguistic quality score
                - strategy: Strategy used by treatment
                - used_structural_detector: Whether structural detection was used
        """
        # Get control result if not provided
        if control_result is None:
            control_result = control_extractor.extract(soup, text)  # type: ignore[assignment]

        # Run treatment extraction
        # The treatment extractor is expected to return a tuple: (result, metadata)
        treatment_result, pattern_metadata = self._extract_with_metadata(
            treatment_extractor, soup, text
        )

        # Compare results using configurable success threshold
        threshold = self.config.success_threshold
        old_success = control_result is not None and len(control_result) > threshold
        new_success = treatment_result is not None and len(treatment_result) > threshold
        agreement = old_success == new_success

        comparison = {
            "old_ingredients": control_result,
            "new_ingredients": treatment_result,
            "old_length": len(control_result) if control_result else 0,
            "new_length": len(treatment_result) if treatment_result else 0,
            "old_success": old_success,
            "new_success": new_success,
            "agreement": agreement,
            "confidence": pattern_metadata.get("confidence", 0.0),
            "linguistic_score": pattern_metadata.get("linguistic_score", 0.0),
            "strategy": pattern_metadata.get("strategy"),
            "used_structural_detector": pattern_metadata.get(
                "used_structural_detector", False
            ),
        }

        # Log comparison based on config
        self._log_comparison(comparison)

        return comparison

    def _extract_with_metadata(
        self, extractor: IComponentExtractor, soup: BeautifulSoup, text: str
    ) -> tuple[Optional[str], Dict[str, Any]]:
        """Extract using an extractor that may return metadata.

        Args:
            extractor: Extractor to use
            soup: BeautifulSoup object
            text: Plain text

        Returns:
            tuple: (extracted_result, metadata_dict)
        """
        result = extractor.extract(soup, text)

        # Check if extractor returns tuple (result, metadata)
        if isinstance(result, tuple) and len(result) == 2:
            return result  # type: ignore[return-value]

        # Otherwise, it's just a result with no metadata
        return result, {}  # type: ignore[return-value]

    def _log_comparison(self, comparison: Dict[str, Any]) -> None:
        """Log comparison results based on configuration.

        Args:
            comparison: Comparison results dictionary
        """
        if self.config.log_level.value == "NONE":
            return

        agreement = comparison["agreement"]
        old_success = comparison["old_success"]
        new_success = comparison["new_success"]
        confidence = comparison["confidence"]

        if self.config.log_level.value in ["DEBUG", "INFO"]:
            if not agreement:
                logger.warning(
                    "A/B DISAGREEMENT: old=%s, new=%s, confidence=%.2f",
                    old_success,
                    new_success,
                    confidence,
                )
            else:
                log_msg = f"A/B AGREEMENT: both {'succeeded' if old_success else 'failed'}"
                if self.config.log_level.value == "DEBUG":
                    logger.debug(log_msg)

    def should_use_treatment(self, comparison: Dict[str, Any]) -> bool:
        """Determine if treatment result should be used in production.

        Args:
            comparison: Comparison results from compare_extractors()

        Returns:
            bool: True if treatment should be used based on config
        """
        return self.config.use_new_method and comparison.get("new_ingredients") is not None
