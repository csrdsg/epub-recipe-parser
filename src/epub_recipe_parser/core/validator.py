"""Recipe validation logic."""

import re
from bs4 import BeautifulSoup

from epub_recipe_parser.utils.patterns import (
    COOKING_VERBS_PATTERN,
    MEASUREMENT_PATTERN,
    EXCLUDE_KEYWORDS,
)


class RecipeValidator:
    """Validate if extracted content is actually a recipe."""

    @staticmethod
    def is_valid_recipe(soup: BeautifulSoup, text: str, title: str) -> bool:
        """Check if content represents a valid recipe."""
        text_lower = text.lower()
        title_lower = title.lower()

        # Exclude non-recipe sections
        for keyword in EXCLUDE_KEYWORDS:
            if keyword in title_lower:
                return False

        # Count cooking verbs
        cooking_verbs = COOKING_VERBS_PATTERN.findall(text_lower)

        # Count measurements
        measurements = MEASUREMENT_PATTERN.findall(text_lower)

        # Calculate score
        score = 0
        if len(cooking_verbs) >= 3:
            score += 3
        if len(measurements) >= 2:
            score += 2
        if re.search(r"\b(?:ingredient|what you need)\b", text_lower):
            score += 2
        if re.search(r"\b(?:instruction|direction|method|steps?)\b", text_lower):
            score += 2
        if len(text) > 200:
            score += 1

        return score >= 5

    @staticmethod
    def calculate_confidence(text: str, ingredients: str, instructions: str) -> float:
        """Calculate confidence score for extraction (0-1)."""
        confidence = 0.0

        # Base confidence on text length
        if len(text) > 500:
            confidence += 0.2
        elif len(text) > 200:
            confidence += 0.1

        # Confidence from ingredients
        if ingredients:
            if len(ingredients) > 200:
                confidence += 0.3
            elif len(ingredients) > 100:
                confidence += 0.2
            elif len(ingredients) > 50:
                confidence += 0.1

        # Confidence from instructions
        if instructions:
            if len(instructions) > 300:
                confidence += 0.3
            elif len(instructions) > 150:
                confidence += 0.2
            elif len(instructions) > 100:
                confidence += 0.1

        # Both present bonus
        if ingredients and instructions:
            confidence += 0.2

        return min(confidence, 1.0)
