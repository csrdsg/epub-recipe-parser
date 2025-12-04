"""Regex patterns and constants for recipe extraction."""

import re

# Measurement patterns
# Matches quantities with units, including fractions (½, ¾, etc.) and plain numbers
# Fixed: Simplified to prevent ReDoS vulnerability by avoiding nested quantifiers
# Enhanced to catch more ingredient formats like "1 lemon", "10 basil leaves", etc.
# Pre-compiled for performance optimization
MEASUREMENT_PATTERN = re.compile(
    r"(?:\b\d+(?:[.,]\d+)?|[¼½¾⅓⅔⅕⅖⅗⅘⅙⅚⅐⅛⅜⅝⅞])"
    r"[\s/-]?"
    r"(?:cup|tablespoon|teaspoon|pound|ounce|gram|kg|lb|oz|tsp|tbsp|clove|slice|"
    r"liter|litre|ml|milliliter|pint|quart|gallon|stick|head|bunch|sprig|stalk|"
    r"can|jar|package|box|bag|container)s?\b|"
    r"\b\d+(?:\s+-\s+\d+)?\s+"
    r"(?:large|medium|small|whole|fresh|dried|frozen|good-sized)?\s*"
    r"(?:egg|garlic|onion|carrot|potato|tomato|pepper|clove|lemon|lime|orange|"
    r"basil|parsley|mint|leaf|leaves|zucchini|squash|chicken|apple|pear|banana)s?\b",
    re.IGNORECASE,
)

# Cooking verb patterns
# Pre-compiled for performance optimization
COOKING_VERBS_PATTERN = re.compile(
    r"\b(heat|cook|grill|place|add|mix|stir|combine|season|serve|roast|smoke|bake|"
    r"prepare|chop|slice|transfer|remove|cover|simmer|melt|boil|whisk|fold|pour|"
    r"spread|drain|toss|sauté|fry|bring|preheat|beat|knead|strain|swirl|watch|"
    r"continue|sprinkle|garnish|arrange|chill|freeze|refrigerate|dunk|toast|crush|"
    r"divide|roll|lay|brush|repeat|spray|drizzle|take|let|cool|seal|store|dissolve|"
    r"steep|adjust|dilute|caramelize|harden|slowly|reduce)\b",
    re.IGNORECASE,
)

# Metadata patterns
# Updated to match ranges with "to" as well as hyphens (e.g., "4-6", "4 to 6")
# Pre-compiled for performance optimization
SERVES_PATTERN = re.compile(
    r"(?:serves?|servings?|yield[s]?|makes?)[:\s]+(\d+(?:\s*(?:-|to)\s*\d+)?)", re.IGNORECASE
)

# Pre-compiled for performance optimization
PREP_TIME_PATTERN = re.compile(
    r"(?:prep(?:aration)?|active|total)(?:\s*time)?[:\s]+([^.\n]+?)(?=\n|cook|$)", re.IGNORECASE
)

# Pre-compiled for performance optimization
COOK_TIME_PATTERN = re.compile(
    r"(?:cook(?:ing)?|passive|baking)(?:\s*time)?[:\s]+([^.\n]+?)(?=\n|prep|$)", re.IGNORECASE
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
    "to make",
    "to prepare",
    "to cook",
    "to serve",
    "let's cook",
    "cooking instructions",
    "recipe method",
    "the method",
]

# Narrative instruction prefixes (used for detecting instructions in narrative format)
# Pre-compiled for performance optimization
NARRATIVE_INSTRUCTION_PREFIXES = re.compile(
    r"^(to make|to prepare|to cook|to assemble|to serve|for the)\s+(?:the\s+)?(\w+)[:\s]",
    re.IGNORECASE,
)

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
    "chapter",
    "how to cut",
    "how to make",
    "techniques",
    "basics",
    "fundamentals",
    "tips",
    "mechanics",
    "history",
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

# Additional pre-compiled patterns for performance optimization
# Used in ingredient extraction for detecting numbered steps
NUMBERED_STEP_PATTERN = re.compile(r"^\d+\.$")

# Used in ingredient extraction for lines starting with numbers
STARTS_WITH_NUMBER_PATTERN = re.compile(r"^\d+")

# Used in metadata extraction for parsing servings
SERVINGS_NUMBER_PATTERN = re.compile(r"(\d+)\s*(?:-|to)\s*(\d+)|(\d+)")

# Used in metadata extraction for parsing time values
HOUR_PATTERN = re.compile(r"(\d+(?:\.\d+)?)\s*(?:hour|hr)s?")
MINUTE_PATTERN = re.compile(r"(\d+)\s*(?:minute|min)s?")
SIMPLE_NUMBER_PATTERN = re.compile(r"^\d+$")
NEGATIVE_TIME_PATTERN = re.compile(r"(?:^|\s)-\s*\d")
