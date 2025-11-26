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

    # Sub-section patterns that indicate this is NOT a complete recipe
    SUB_SECTION_PATTERNS = [
        # Equipment and metadata sections
        r"^(?:special\s+)?equipment(?:\s+needed)?:?$",
        r"^(?:gear|tools?)(?:\s+needed)?:?$",
        r"^(?:what\s+you(?:'ll)?\s+need):?$",
        r"^(?:prep|cook|active|passive|total)\s+time:?",
        r"^(?:serves?|servings?|yield[s]?|makes?):?\s*\d*$",

        # Serving and presentation sections
        r"^to\s+serve:?$",
        r"^for\s+serving:?$",
        r"^garnish:?$",
        r"^presentation:?$",

        # Recipe component sub-sections (ALL CAPS "FOR THE X" pattern)
        r"^FOR\s+THE\s+",  # "FOR THE VINAIGRETTE", "FOR THE FILLING"

        # Short ingredient-like titles
        r"^(?:coarse|sea|kosher)\s+salt$",
        r"^(?:black|white)\s+pepper$",
        r"^(?:olive|vegetable|canola)\s+oil$",
        r"^dressing$",
        r"^sauce$",
        r"^marinade$",
        r"^glaze$",
        r"^rub$",
        r"^brine$",

        # Very generic component names (but allow if longer/more specific)
        r"^(?:the\s+)?(?:filling|topping|coating|crust)$",

        # Notes and tips sections
        r"^(?:note|tip|variation)s?:?$",
        r"^(?:indoor|outdoor)\s+alternative:?$",
        r"^(?:chef(?:'s)?|cook(?:'s)?)\s+(?:note|tip)s?:?$",
    ]

    @staticmethod
    def is_valid_recipe(soup: BeautifulSoup, text: str, title: str) -> bool:
        """Check if content represents a valid recipe.

        This validator filters out:
        1. Equipment lists and metadata sections
        2. Serving instructions and presentation notes
        3. Recipe sub-components (sauces, dressings, etc.)
        4. Single ingredient titles
        5. Generic section headers

        Args:
            soup: BeautifulSoup object of the section
            text: Plain text content of the section
            title: Title/header of the section

        Returns:
            True if this appears to be a complete recipe, False otherwise
        """
        text_lower = text.lower()
        title_lower = title.lower()
        title_stripped = title.strip()

        # First, check for sub-section patterns
        if RecipeValidator._is_sub_section(title_stripped):
            return False

        # Exclude non-recipe sections (from original logic)
        for keyword in EXCLUDE_KEYWORDS:
            if keyword in title_lower:
                return False

        # Check for very short titles that are likely ingredients or components
        if RecipeValidator._is_likely_ingredient_title(title_stripped):
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
    def _is_sub_section(title: str) -> bool:
        """Check if title indicates a recipe sub-section rather than a complete recipe.

        Args:
            title: The section title to check

        Returns:
            True if this is a sub-section, False if it could be a complete recipe
        """
        # Check against all sub-section patterns
        for pattern in RecipeValidator.SUB_SECTION_PATTERNS:
            if re.match(pattern, title, re.IGNORECASE):
                return True

        return False

    @staticmethod
    def _is_likely_ingredient_title(title: str) -> bool:
        """Check if title looks like a single ingredient rather than a recipe name.

        Characteristics of ingredient titles:
        1. Very short (< 20 chars)
        2. Contains common ingredient words
        3. Contains measurements or quantities
        4. Matches ingredient patterns

        Args:
            title: The section title to check

        Returns:
            True if this looks like an ingredient, False otherwise
        """
        # If title is reasonably long, it's probably a real recipe title
        if len(title) > 30:
            return False

        # If very short and contains measurement/quantity patterns, likely ingredient
        if len(title) < 20:
            # Check if it contains numbers (quantity indicator)
            if re.search(r'\d+', title):
                return True

            # Common single-ingredient patterns
            single_ingredient_words = [
                'coarse salt', 'sea salt', 'kosher salt', 'black pepper',
                'white pepper', 'olive oil', 'vegetable oil', 'butter',
                'flour', 'sugar', 'water', 'salt', 'pepper', 'oil',
            ]

            title_lower = title.lower()
            for ingredient in single_ingredient_words:
                if ingredient == title_lower or title_lower.startswith(ingredient + ' '):
                    return True

        # Check if entire title matches ingredient patterns (contains measurements)
        if len(title) < 25 and MEASUREMENT_PATTERN.search(title):
            # Title contains measurement units - likely an ingredient line
            return True

        return False

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
