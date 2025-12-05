"""
Pattern-based extraction components for A/B testing.

This module provides alternative extraction strategies using pattern detection,
linguistic analysis, and structural detection.
"""

# Legacy imports (deprecated - kept for backward compatibility)
from .detectors import IngredientPatternDetector as LegacyIngredientPatternDetector
from .analyzers import LinguisticAnalyzer
from .structural import StructuralDetector

# Modern ingredient extraction components
from .ingredient_detectors import IngredientPatternDetector
from .ingredient_structural import IngredientStructuralDetector, IngredientZone
from .analyzers import IngredientLinguisticAnalyzer

# Instruction extraction components
from .instruction_detectors import InstructionPatternDetector
from .instruction_structural import InstructionStructuralDetector
from .analyzers import InstructionLinguisticAnalyzer

# Metadata extraction components
from .metadata_detectors import MetadataPatternDetector
from .metadata_structural import MetadataStructuralDetector, MetadataZone
from .analyzers import MetadataLinguisticAnalyzer

__all__ = [
    # Ingredient extraction (modern)
    "IngredientPatternDetector",
    "IngredientLinguisticAnalyzer",
    "IngredientStructuralDetector",
    "IngredientZone",
    # Instruction extraction
    "InstructionPatternDetector",
    "InstructionLinguisticAnalyzer",
    "InstructionStructuralDetector",
    # Metadata extraction
    "MetadataPatternDetector",
    "MetadataLinguisticAnalyzer",
    "MetadataStructuralDetector",
    "MetadataZone",
    # Legacy (deprecated - kept for backward compatibility)
    "LinguisticAnalyzer",
    "StructuralDetector",
]
