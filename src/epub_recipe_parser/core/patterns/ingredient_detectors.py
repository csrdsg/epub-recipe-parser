"""Pattern detection for ingredients extraction."""

import re
from typing import Optional, Dict, Any


class IngredientPatternDetector:
    """Detects ingredient patterns and calculates confidence scores."""

    # Common measurement units
    MEASUREMENT_UNITS = {
        # Volume
        "cup", "cups", "c", "tablespoon", "tablespoons", "tbsp", "tbs", "t",
        "teaspoon", "teaspoons", "tsp", "ts", "fluid ounce", "fluid ounces", "fl oz",
        "pint", "pints", "pt", "quart", "quarts", "qt", "gallon", "gallons", "gal",
        "milliliter", "milliliters", "ml", "liter", "liters", "l",
        # Weight
        "ounce", "ounces", "oz", "pound", "pounds", "lb", "lbs",
        "gram", "grams", "g", "kilogram", "kilograms", "kg",
        # Other
        "pinch", "dash", "drop", "drops", "smidgen", "hint",
        "clove", "cloves", "piece", "pieces", "slice", "slices",
        "can", "cans", "package", "packages", "pkg", "box", "boxes",
        "jar", "jars", "bunch", "bunches", "head", "heads",
        "stalk", "stalks", "sprig", "sprigs", "leaf", "leaves",
        "strip", "strips", "stick", "sticks"
    }

    # Ingredient descriptors
    DESCRIPTORS = {
        # Size
        "large", "medium", "small", "jumbo", "extra-large", "xl",
        # State
        "fresh", "frozen", "dried", "canned", "fresh-squeezed",
        "room temperature", "cold", "warm", "hot",
        # Preparation
        "chopped", "diced", "minced", "sliced", "grated", "shredded",
        "peeled", "crushed", "ground", "whole", "halved", "quartered",
        "cubed", "julienned", "thinly sliced", "finely chopped",
        "roughly chopped", "coarsely chopped",
        # Quality
        "ripe", "unripe", "tender", "crisp", "firm", "soft",
        # Origin/Type
        "organic", "kosher", "sea", "iodized", "extra-virgin",
        "unsalted", "salted", "sweetened", "unsweetened"
    }

    # Common ingredient nouns
    INGREDIENT_NOUNS = {
        # Proteins
        "chicken", "beef", "pork", "fish", "shrimp", "salmon", "tuna",
        "turkey", "lamb", "bacon", "sausage", "ham", "steak", "ribs",
        "brisket", "tenderloin", "thighs", "breast", "wings",
        # Dairy
        "milk", "cream", "butter", "cheese", "yogurt", "sour cream",
        "half-and-half", "buttermilk", "parmesan", "cheddar", "mozzarella",
        # Produce
        "onion", "garlic", "tomato", "potato", "carrot", "celery",
        "pepper", "bell pepper", "jalapeño", "chili", "cucumber",
        "lettuce", "spinach", "kale", "broccoli", "cauliflower",
        "mushroom", "zucchini", "eggplant", "corn", "peas",
        # Herbs & Spices
        "salt", "pepper", "paprika", "cumin", "oregano", "basil",
        "thyme", "rosemary", "parsley", "cilantro", "mint", "dill",
        "cinnamon", "nutmeg", "cloves", "ginger", "turmeric",
        # Pantry
        "flour", "sugar", "oil", "vinegar", "soy sauce", "worcestershire",
        "ketchup", "mustard", "mayonnaise", "honey", "molasses",
        "stock", "broth", "wine", "beer", "water",
        # Baking
        "egg", "eggs", "yeast", "baking powder", "baking soda",
        "vanilla", "vanilla extract", "chocolate", "cocoa",
        # Grains/Pasta
        "rice", "pasta", "noodles", "bread", "breadcrumbs", "flour",
        "cornstarch", "oats", "quinoa", "couscous",
        # Fruits
        "lemon", "lime", "orange", "apple", "banana", "berries",
        "strawberry", "blueberry", "raspberry", "mango", "pineapple"
    }

    # Pre-compiled patterns for performance
    MEASUREMENT_PATTERN = re.compile(
        r'\b\d+[\s/\d]*\s*(?:' + '|'.join(MEASUREMENT_UNITS) + r')\b',
        re.IGNORECASE
    )

    FRACTION_PATTERN = re.compile(r'[¼½¾⅓⅔⅛⅜⅝⅞]|(?:\d+/)?\d+/\d+')
    NUMERIC_PATTERN = re.compile(r'\b\d+[\s/\d.]*\b')

    # Ingredient list item markers
    LIST_MARKERS = re.compile(r'^[\s•\-*·○●▪▫■□➤➢→⇒]\s*|\d+\.\s*')

    @classmethod
    def calculate_confidence(cls, text: str) -> float:
        """Calculate confidence that text contains ingredients.

        Scoring components (0.0-1.0):
        - Measurement presence: 30%
        - Ingredient noun density: 25%
        - Descriptor usage: 15%
        - List structure: 15%
        - Line length characteristics: 10%
        - Absence of cooking verbs: 5%

        Args:
            text: Text to analyze

        Returns:
            Confidence score between 0.0 and 1.0

        Examples:
            >>> text = "2 cups flour\\n1 tsp salt\\n3 eggs, beaten"
            >>> IngredientPatternDetector.calculate_confidence(text)
            0.91

            >>> text = "Preheat oven to 350°F. Mix ingredients together."
            >>> IngredientPatternDetector.calculate_confidence(text)
            0.12
        """
        if not text or len(text.strip()) < 10:
            return 0.0

        text_lower = text.lower()
        lines = [line.strip() for line in text.split("\n") if line.strip()]

        if not lines:
            return 0.0

        # Component 1: Measurement presence (30% weight)
        measurement_score = cls._calculate_measurement_score(lines, text_lower) * 0.30

        # Component 2: Ingredient noun density (25% weight)
        noun_score = cls._calculate_noun_density(text_lower) * 0.25

        # Component 3: Descriptor usage (15% weight)
        descriptor_score = cls._calculate_descriptor_score(text_lower) * 0.15

        # Component 4: List structure (15% weight)
        list_score = cls._check_list_structure(lines) * 0.15

        # Component 5: Line length characteristics (10% weight)
        length_score = cls._check_line_length(lines) * 0.10

        # Component 6: Cooking verb penalty (5% weight)
        verb_penalty = cls._calculate_verb_penalty(text_lower) * 0.05

        total_score = (
            measurement_score +
            noun_score +
            descriptor_score +
            list_score +
            length_score +
            verb_penalty
        )

        return min(max(total_score, 0.0), 1.0)

    @classmethod
    def _calculate_measurement_score(cls, lines: list, text_lower: str) -> float:
        """Calculate score based on measurement presence.

        Args:
            lines: List of text lines
            text_lower: Lowercase full text

        Returns:
            Score 0.0-1.0 based on measurement density
        """
        if not lines:
            return 0.0

        # Count lines with measurements
        measurement_count = 0
        for line in lines:
            if cls.MEASUREMENT_PATTERN.search(line.lower()):
                measurement_count += 1
            elif cls.FRACTION_PATTERN.search(line):
                measurement_count += 1

        ratio = measurement_count / len(lines)

        # High ratio = high confidence
        if ratio >= 0.7:
            return 1.0
        elif ratio >= 0.5:
            return 0.85
        elif ratio >= 0.3:
            return 0.65
        elif ratio >= 0.15:
            return 0.40
        else:
            return ratio * 2  # Scale small ratios

    @classmethod
    def _calculate_noun_density(cls, text: str) -> float:
        """Calculate ingredient noun density.

        Args:
            text: Lowercase text

        Returns:
            Score 0.0-1.0 based on ingredient nouns per 100 chars
        """
        if not text:
            return 0.0

        word_count = sum(1 for word in cls.INGREDIENT_NOUNS if word in text)

        # Normalize by text length
        density = (word_count / len(text)) * 100

        if density >= 3.0:
            return 1.0
        elif density >= 2.0:
            return 0.85
        elif density >= 1.0:
            return 0.65
        elif density >= 0.5:
            return 0.45
        else:
            return density  # Scale linearly for low density

    @classmethod
    def _calculate_descriptor_score(cls, text: str) -> float:
        """Calculate score based on ingredient descriptors.

        Args:
            text: Lowercase text

        Returns:
            Score 0.0-1.0 based on descriptor presence
        """
        if not text:
            return 0.0

        descriptor_count = sum(1 for desc in cls.DESCRIPTORS if desc in text)

        # Normalize by text length
        density = (descriptor_count / len(text)) * 100

        if density >= 2.0:
            return 1.0
        elif density >= 1.0:
            return 0.75
        elif density >= 0.5:
            return 0.50
        else:
            return density * 0.5  # Scale small values

    @classmethod
    def _check_list_structure(cls, lines: list) -> float:
        """Check for list-like structure.

        Args:
            lines: List of text lines

        Returns:
            Score 0.0-1.0 based on list markers and structure
        """
        if not lines or len(lines) < 3:
            return 0.0

        # Count lines with list markers
        marker_count = sum(1 for line in lines if cls.LIST_MARKERS.match(line))
        ratio = marker_count / len(lines)

        # Check for consistent line structure
        avg_length = sum(len(line) for line in lines) / len(lines)
        length_variance = sum(abs(len(line) - avg_length) for line in lines) / len(lines)

        # Low variance = consistent structure
        consistency = 1.0 - min(length_variance / 50, 1.0)

        # Combine marker ratio and consistency
        list_score = (ratio * 0.6) + (consistency * 0.4)
        return min(list_score, 1.0)

    @classmethod
    def _check_line_length(cls, lines: list) -> float:
        """Check line length characteristics typical of ingredients.

        Args:
            lines: List of text lines

        Returns:
            Score 0.0-1.0 based on typical ingredient line lengths
        """
        if not lines:
            return 0.0

        # Ingredients typically 20-100 chars per line
        ideal_range = sum(1 for line in lines if 20 <= len(line) <= 100)
        ratio = ideal_range / len(lines)

        # Check average line length
        avg_length = sum(len(line) for line in lines) / len(lines)

        # Ideal average: 40-70 chars
        if 40 <= avg_length <= 70:
            avg_score = 1.0
        elif 30 <= avg_length <= 80:
            avg_score = 0.75
        else:
            avg_score = 0.5

        return (ratio * 0.6) + (avg_score * 0.4)

    @classmethod
    def _calculate_verb_penalty(cls, text: str) -> float:
        """Calculate penalty for cooking verbs (instructions indicator).

        Args:
            text: Lowercase text

        Returns:
            Score 0.0-1.0 (higher = fewer verbs, better for ingredients)
        """
        cooking_verbs = [
            "preheat", "heat", "cook", "bake", "roast", "fry", "grill",
            "mix", "stir", "combine", "whisk", "beat", "fold",
            "bring", "remove", "transfer", "pour", "serve"
        ]

        verb_count = sum(text.count(f" {verb} ") for verb in cooking_verbs)

        # More verbs = lower score (penalty)
        if verb_count == 0:
            return 1.0
        elif verb_count == 1:
            return 0.75
        elif verb_count == 2:
            return 0.50
        elif verb_count == 3:
            return 0.25
        else:
            return 0.0

    @classmethod
    def extract_with_confidence(cls, text: str) -> Dict[str, Any]:
        """Extract ingredients with confidence metadata.

        Args:
            text: Text to analyze

        Returns:
            Dictionary containing:
            - 'text': Extracted ingredient text
            - 'confidence': Overall confidence score
            - 'components': Individual component scores
            - 'line_count': Number of ingredient lines
        """
        if not text:
            return {
                'text': None,
                'confidence': 0.0,
                'components': {},
                'line_count': 0
            }

        lines = [line.strip() for line in text.split("\n") if line.strip()]
        text_lower = text.lower()

        # Calculate individual components
        components = {
            'measurement': cls._calculate_measurement_score(lines, text_lower),
            'nouns': cls._calculate_noun_density(text_lower),
            'descriptors': cls._calculate_descriptor_score(text_lower),
            'list_structure': cls._check_list_structure(lines),
            'line_length': cls._check_line_length(lines),
            'verb_absence': cls._calculate_verb_penalty(text_lower)
        }

        # Calculate overall confidence
        overall = cls.calculate_confidence(text)

        return {
            'text': text,
            'confidence': overall,
            'components': components,
            'line_count': len(lines)
        }
