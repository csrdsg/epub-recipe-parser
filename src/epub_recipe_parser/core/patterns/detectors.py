"""Pattern detection for ingredients extraction."""

import re


class IngredientPatternDetector:
    """
    Detects ingredient patterns and calculates confidence scores.

    TODO: This is a stub implementation. Full implementation should include:
    - Pattern matching for common ingredient formats
    - Measurement unit detection
    - Ingredient keyword recognition
    - Contextual analysis
    """

    # Common measurement units and ingredient keywords
    MEASUREMENT_UNITS = {
        "cup", "cups", "tablespoon", "tablespoons", "tbsp", "teaspoon", "teaspoons", "tsp",
        "ounce", "ounces", "oz", "pound", "pounds", "lb", "lbs", "gram", "grams", "g",
        "kilogram", "kilograms", "kg", "milliliter", "milliliters", "ml", "liter", "liters", "l",
        "pinch", "dash", "clove", "cloves", "piece", "pieces"
    }

    INGREDIENT_KEYWORDS = {
        "salt", "pepper", "oil", "butter", "flour", "sugar", "egg", "eggs", "milk", "water",
        "onion", "garlic", "chicken", "beef", "pork", "fish", "cheese", "tomato", "rice",
        "pasta", "bread", "cream", "sauce", "stock", "broth", "wine", "lemon", "lime"
    }

    @staticmethod
    def calculate_confidence(text: str) -> float:
        """
        Calculate confidence that the text contains ingredients.

        Args:
            text: Text to analyze

        Returns:
            Confidence score between 0.0 and 1.0
        """
        if not text or len(text.strip()) < 10:
            return 0.0

        text.lower()
        lines = [line.strip() for line in text.split("\n") if line.strip()]

        if not lines:
            return 0.0

        score = 0.0
        total_lines = len(lines)

        # Check for measurement units
        measurement_lines = sum(
            1 for line in lines if any(unit in line for unit in IngredientPatternDetector.MEASUREMENT_UNITS)
        )
        measurement_ratio = measurement_lines / total_lines if total_lines > 0 else 0
        score += measurement_ratio * 0.4  # 40% weight

        # Check for ingredient keywords
        keyword_lines = sum(
            1 for line in lines if any(keyword in line for keyword in IngredientPatternDetector.INGREDIENT_KEYWORDS)
        )
        keyword_ratio = keyword_lines / total_lines if total_lines > 0 else 0
        score += keyword_ratio * 0.3  # 30% weight

        # Check for numeric patterns (quantities)
        numeric_lines = sum(
            1 for line in lines if re.search(r'\d+[/\d\s]*', line)
        )
        numeric_ratio = numeric_lines / total_lines if total_lines > 0 else 0
        score += numeric_ratio * 0.3  # 30% weight

        return min(score, 1.0)
