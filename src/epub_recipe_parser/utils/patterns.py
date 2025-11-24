"""Regex patterns and constants for recipe extraction."""

import re

# Measurement patterns
MEASUREMENT_PATTERN = re.compile(
    r"\b\d+[\s/-]*(?:cup|tablespoon|teaspoon|pound|ounce|gram|kg|lb|oz|tsp|tbsp|clove|slice)s?\b",
    re.IGNORECASE,
)

# Cooking verb patterns
COOKING_VERBS_PATTERN = re.compile(
    r"\b(heat|cook|grill|place|add|mix|stir|combine|season|serve|roast|smoke|bake|"
    r"prepare|chop|slice|transfer|remove|cover|simmer)\b",
    re.IGNORECASE,
)

# Metadata patterns
SERVES_PATTERN = re.compile(
    r"(?:serves?|servings?|yield[s]?|makes?)[:\s]+(\d+(?:\s*-\s*\d+)?)", re.IGNORECASE
)

PREP_TIME_PATTERN = re.compile(
    r"prep(?:aration)?\s*time[:\s]+([^.\n]+?)(?=\n|cook|total|$)", re.IGNORECASE
)

COOK_TIME_PATTERN = re.compile(
    r"cook(?:ing)?\s*time[:\s]+([^.\n]+?)(?=\n|prep|total|$)", re.IGNORECASE
)

# Ingredient section keywords
INGREDIENT_KEYWORDS = ["ingredient", "what you need", "you'll need"]

# Instruction section keywords
INSTRUCTION_KEYWORDS = [
    "instruction",
    "direction",
    "method",
    "preparation",
    "how to",
    "steps",
]

# Exclude patterns for recipe validation
EXCLUDE_KEYWORDS = [
    "contents",
    "introduction",
    "foreword",
    "preface",
    "acknowledgment",
    "index",
    "about the author",
    "copyright",
    "dedication",
    "cover",
    "equipment list",
    "tools needed",
    "conversion chart",
    "glossary",
]

# Cooking methods
COOKING_METHODS = {
    "smoke": ["smoke", "smoked"],
    "grill": ["grill", "grilled"],
    "roast": ["roast", "roasted"],
    "bake": ["bake", "baked"],
    "fry": ["fry", "fried"],
}

# Protein types
PROTEIN_TYPES = ["beef", "pork", "chicken", "lamb", "fish", "seafood", "turkey", "duck"]
