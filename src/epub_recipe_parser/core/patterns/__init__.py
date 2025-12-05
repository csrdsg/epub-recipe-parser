"""
Pattern-based extraction components for A/B testing.

This module provides alternative extraction strategies using pattern detection,
linguistic analysis, and structural detection.
"""

from .detectors import IngredientPatternDetector
from .analyzers import LinguisticAnalyzer, InstructionLinguisticAnalyzer, MetadataLinguisticAnalyzer
from .structural import StructuralDetector
from .instruction_detectors import InstructionPatternDetector
from .instruction_structural import InstructionStructuralDetector
from .metadata_detectors import MetadataPatternDetector
from .metadata_structural import MetadataStructuralDetector, MetadataZone

__all__ = [
    # Ingredient extraction
    "IngredientPatternDetector",
    "LinguisticAnalyzer",
    "StructuralDetector",
    # Instruction extraction
    "InstructionPatternDetector",
    "InstructionLinguisticAnalyzer",
    "InstructionStructuralDetector",
    # Metadata extraction
    "MetadataPatternDetector",
    "MetadataLinguisticAnalyzer",
    "MetadataStructuralDetector",
    "MetadataZone",
]
