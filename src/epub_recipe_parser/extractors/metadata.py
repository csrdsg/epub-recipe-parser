"""Extract recipe metadata (servings, time, etc)."""

from typing import Dict
from bs4 import BeautifulSoup

from epub_recipe_parser.utils.patterns import (
    SERVES_PATTERN,
    PREP_TIME_PATTERN,
    COOK_TIME_PATTERN,
    COOKING_METHODS,
    PROTEIN_TYPES,
)


class MetadataExtractor:
    """Extract recipe metadata."""

    @staticmethod
    def extract(soup: BeautifulSoup, text: str, title: str = "") -> Dict[str, str]:
        """Extract all metadata fields."""
        metadata = {}
        text_lower = text.lower()

        # Serves/Yield
        serves_match = SERVES_PATTERN.search(text_lower)
        if serves_match:
            metadata["serves"] = serves_match.group(1)

        # Prep time
        prep_match = PREP_TIME_PATTERN.search(text_lower)
        if prep_match:
            metadata["prep_time"] = prep_match.group(1).strip()

        # Cook time
        cook_match = COOK_TIME_PATTERN.search(text_lower)
        if cook_match:
            metadata["cook_time"] = cook_match.group(1).strip()

        # Cooking method
        combined = f"{title} {text}".lower()
        for method, keywords in COOKING_METHODS.items():
            if any(keyword in combined for keyword in keywords):
                metadata["cooking_method"] = method
                break

        # Protein type
        for protein in PROTEIN_TYPES:
            if protein in combined:
                metadata["protein_type"] = protein
                break

        return metadata
