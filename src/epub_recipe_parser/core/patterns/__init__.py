"""
Pattern-based extraction components for A/B testing.

This module provides alternative extraction strategies using pattern detection,
linguistic analysis, and structural detection.

Note: These are currently stub implementations to prevent runtime errors.
Full implementations should be added as part of the A/B testing refactoring.
"""

from .detectors import IngredientPatternDetector
from .analyzers import LinguisticAnalyzer
from .structural import StructuralDetector

__all__ = [
    "IngredientPatternDetector",
    "LinguisticAnalyzer",
    "StructuralDetector",
]
