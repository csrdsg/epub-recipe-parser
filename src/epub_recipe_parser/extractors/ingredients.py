"""Extract ingredient lists from HTML."""

import logging
import re
from typing import Optional, List
from bs4 import BeautifulSoup

from epub_recipe_parser.utils.html import HTMLParser
from epub_recipe_parser.utils.patterns import (
    INGREDIENT_KEYWORDS,
    MEASUREMENT_PATTERN,
)

logger = logging.getLogger(__name__)


class IngredientsExtractor:
    """Extract ingredient lists from HTML."""

    # Additional ingredient section keywords for text-based extraction
    TEXT_INGREDIENT_KEYWORDS = [
        "for the",
        "ingredient",
        "what you need",
        "you'll need",
        "you will need",
        "shopping list",
    ]

    # Common cooking instruction verbs to detect where ingredients end
    INSTRUCTION_VERBS = [
        "preheat",
        "heat",
        "cook",
        "place",
        "add",
        "mix",
        "stir",
        "combine",
        "whisk",
        "beat",
        "fold",
        "bring",
        "remove",
        "transfer",
        "spread",
        "pour",
        "serve",
        "garnish",
        "drizzle",
        "sprinkle",
        "arrange",
        "prepare",
        "chop",
        "slice",
        "dice",
        "mince",
        "season",
        "cover",
        "simmer",
        "boil",
        "bake",
        "roast",
        "grill",
        "fry",
        "saute",
        "sear",
    ]

    @staticmethod
    def extract(soup: BeautifulSoup, text: str) -> Optional[str]:
        """Extract ingredients using multiple strategies with detailed logging."""
        logger.debug("Starting ingredient extraction")

        # Strategy 1: Find by HTML header
        logger.debug("Strategy 1: Searching for ingredient section by header keywords")
        ingredients = HTMLParser.find_section_by_header(soup, INGREDIENT_KEYWORDS)
        if ingredients and len(ingredients) > 50:
            logger.info(
                f"Strategy 1 SUCCESS: Found ingredients by header ({len(ingredients)} chars)"
            )
            return ingredients
        elif ingredients:
            logger.debug(
                f"Strategy 1 PARTIAL: Found section but too short ({len(ingredients)} chars)"
            )

        # Strategy 2: Find lists with measurements in HTML
        logger.debug("Strategy 2: Searching for lists with measurements")
        list_count = 0
        for list_elem in soup.find_all(["ol", "ul"]):
            list_count += 1
            items = HTMLParser.extract_from_list(list_elem)
            if not items:
                continue

            # Check if items have measurements
            measurement_count = sum(1 for item in items if MEASUREMENT_PATTERN.search(item))
            measurement_ratio = measurement_count / len(items) if items else 0

            logger.debug(
                f"Strategy 2: List {list_count} has {len(items)} items, {measurement_count} with measurements ({measurement_ratio:.1%})"
            )

            if measurement_count >= max(2, len(items) * 0.3):
                result = "\n".join(f"- {item}" for item in items)
                logger.info(
                    f"Strategy 2 SUCCESS: Found ingredients in list ({len(result)} chars, {len(items)} items)"
                )
                return result

        logger.debug(f"Strategy 2: Checked {list_count} lists, none matched criteria")

        # Strategy 3: Find paragraphs with measurements in HTML
        logger.debug("Strategy 3: Searching for paragraphs with measurements")
        para_count = 0
        for paragraph in soup.find_all("p"):
            text_content = paragraph.get_text(strip=True)
            if len(text_content) < 30:
                continue

            para_count += 1
            measurement_count = len(MEASUREMENT_PATTERN.findall(text_content))

            logger.debug(
                f"Strategy 3: Paragraph {para_count} has {measurement_count} measurements ({len(text_content)} chars)"
            )

            if measurement_count >= 3:
                logger.info(
                    f"Strategy 3 SUCCESS: Found ingredients in paragraph ({len(text_content)} chars, {measurement_count} measurements)"
                )
                return text_content

        logger.debug(f"Strategy 3: Checked {para_count} paragraphs, none matched criteria")

        # Strategy 4: Text-based extraction with "For the" patterns
        logger.debug(
            "Strategy 4: Attempting text-based extraction (section headers and consecutive measurements)"
        )
        text_ingredients = IngredientsExtractor._extract_from_text(text)
        if text_ingredients:
            logger.info(
                f"Strategy 4 SUCCESS: Found ingredients via text extraction ({len(text_ingredients)} chars)"
            )
            return text_ingredients

        logger.warning("All extraction strategies FAILED: No ingredients found")
        return None

    @staticmethod
    def _extract_from_text(text: str) -> Optional[str]:
        """Extract ingredients from plain text using pattern matching.

        This handles cases where HTML structure is lost but text patterns remain,
        such as "For the X" section headers followed by ingredient lists.
        """
        lines = text.split("\n")
        ingredient_sections = []

        # Find all ingredient sections
        i = 0
        while i < len(lines):
            line = lines[i].strip()

            # Check if line is an ingredient section header
            if IngredientsExtractor._is_ingredient_header(line):
                section_name = line
                section_ingredients = []
                i += 1

                # Collect ingredients until we hit instructions or another section
                while i < len(lines):
                    ingredient_line = lines[i].strip()

                    # Skip empty lines
                    if not ingredient_line:
                        i += 1
                        continue

                    # Stop if we hit instructions
                    if IngredientsExtractor._is_instruction_line(ingredient_line):
                        break

                    # Stop if we hit another ingredient section header
                    if IngredientsExtractor._is_ingredient_header(ingredient_line):
                        break

                    # Add line if it looks like an ingredient
                    if IngredientsExtractor._is_ingredient_line(ingredient_line):
                        section_ingredients.append(ingredient_line)

                    i += 1

                # Add section if it has enough ingredients (allow single ingredient sections)
                if len(section_ingredients) >= 1:
                    ingredient_sections.append(
                        {"header": section_name, "items": section_ingredients}
                    )
            else:
                i += 1

        # Format and return ingredients
        if ingredient_sections:
            return IngredientsExtractor._format_ingredient_sections(ingredient_sections)

        # Fallback: Look for consecutive lines with measurements (no headers)
        return IngredientsExtractor._extract_consecutive_measurements(lines)

    @staticmethod
    def _is_ingredient_header(line: str) -> bool:
        """Check if a line is an ingredient section header."""
        if not line or len(line) > 60:
            return False

        lower_line = line.lower()

        # Check for common patterns
        for keyword in IngredientsExtractor.TEXT_INGREDIENT_KEYWORDS:
            if keyword in lower_line:
                # Make sure it's not part of an ingredient line
                if not MEASUREMENT_PATTERN.search(line):
                    return True

        return False

    @staticmethod
    def _is_ingredient_line(line: str) -> bool:
        """Check if a line looks like an ingredient."""
        if not line or len(line) < 5:
            return False

        # Must have measurement
        if not MEASUREMENT_PATTERN.search(line):
            return False

        # Should not start with an instruction verb
        words = line.split()
        if words:
            first_word = words[0].lower().rstrip(",.:;")
            if first_word in IngredientsExtractor.INSTRUCTION_VERBS:
                return False

        # Should be relatively short (typical ingredient lines)
        if len(line) > 150:
            return False

        return True

    @staticmethod
    def _is_instruction_line(line: str) -> bool:
        """Check if a line looks like an instruction."""
        if not line or len(line) < 10:
            return False

        # Longer lines are more likely instructions
        if len(line) > 100:
            return True

        # Check if it starts with an instruction verb
        first_word = line.split()[0].lower().rstrip(",.:;")
        if first_word in IngredientsExtractor.INSTRUCTION_VERBS:
            return True

        return False

    @staticmethod
    def _extract_consecutive_measurements(lines: List[str]) -> Optional[str]:
        """Extract consecutive lines with measurements as fallback strategy.

        This function handles recipes where ingredients appear as consecutive lines
        without section headers. It's more lenient than requiring strict measurements,
        allowing gaps in the sequence for lines that look like ingredients.
        """
        ingredient_candidates = []
        current_run: List[str] = []

        # Track if we've seen metadata markers (like "Serves", "Yield", etc.)
        in_ingredient_zone = False
        metadata_markers = [
            "serves",
            "yield",
            "makes",
            "prep time",
            "cook time",
            "active time",
            "soaking time",
        ]
        instruction_starters = [
            "preheat",
            "heat",
            "combine",
            "mix",
            "place",
            "cook",
            "add",
            "whisk",
            "bring",
        ]

        for i, line in enumerate(lines):
            line_stripped = line.strip()
            if not line_stripped:
                continue

            line_lower = line_stripped.lower()

            # Detect if we're past metadata section (entering ingredient zone)
            if any(marker in line_lower for marker in metadata_markers):
                in_ingredient_zone = True
                continue

            # Detect numbered steps (like "1." or "1.") - this means instructions started
            if re.match(r"^\d+\.$", line_stripped):
                # If we have accumulated ingredients, save them before breaking
                if len(current_run) >= 2:
                    ingredient_candidates.append(current_run)
                break

            # Check if line looks like an instruction (starts with instruction verb)
            first_word = (
                line_stripped.split()[0].lower().rstrip(",.:;") if line_stripped.split() else ""
            )
            if first_word in instruction_starters and len(line_stripped) > 50:
                # Long line starting with instruction verb = instructions started
                if len(current_run) >= 2:
                    ingredient_candidates.append(current_run)
                break

            # Check if line is an ingredient
            if IngredientsExtractor._is_ingredient_line(line_stripped):
                current_run.append(line_stripped)
            elif in_ingredient_zone and IngredientsExtractor._looks_like_ingredient_no_measurement(
                line_stripped
            ):
                # In ingredient zone, be more lenient - accept lines that look like ingredients
                # even without strict measurements
                current_run.append(line_stripped)
            else:
                # Save current run if it has at least 2 ingredients
                if len(current_run) >= 2:
                    ingredient_candidates.append(current_run)
                    current_run = []
                # Allow small gaps in ingredient zone
                elif in_ingredient_zone and len(current_run) > 0:
                    # Don't reset yet, might be a gap like "divided" or empty line
                    pass
                else:
                    current_run = []

        # Check last run
        if len(current_run) >= 2:
            ingredient_candidates.append(current_run)

        # Return the longest run (most likely to be the main ingredient list)
        if ingredient_candidates:
            longest_run = max(ingredient_candidates, key=len)
            return "\n".join(f"- {item}" for item in longest_run)

        return None

    @staticmethod
    def _looks_like_ingredient_no_measurement(line: str) -> bool:
        """Check if a line looks like an ingredient even without measurements.

        This catches lines like "1 lemon", "6 garlic cloves", "Salt and pepper"
        which may not match strict measurement patterns.
        """
        if not line or len(line) < 3 or len(line) > 150:
            return False

        # Common ingredient patterns without strict units
        ingredient_indicators = [
            r"\b\d+\s+(large|medium|small|whole)?\s*(egg|garlic|onion|carrot|potato|tomato|lemon|lime|orange|apple|pear)s?\b",
            r"\b\d+\s+(fresh|dried|frozen)?\s*\w+\s+(leave|sprig|stalk|bunch|head)s?\b",
            r"\bsalt\s+and\s+(pepper|black\s+pepper)\b",
            r"\b(coarse|sea|kosher)\s+salt\b",
            r"\b(olive|vegetable|canola|coconut)\s+oil\b",
            r"\b(fresh|ground|dried)\s+(black\s+)?pepper\b",
            r"\bto\s+taste\b",
        ]

        line_lower = line.lower()
        for pattern in ingredient_indicators:
            if re.search(pattern, line_lower):
                return True

        # If it starts with a number and contains food words
        if re.match(r"^\d+", line):
            food_words = [
                "garlic",
                "onion",
                "carrot",
                "potato",
                "tomato",
                "pepper",
                "egg",
                "lemon",
                "lime",
                "basil",
                "parsley",
                "cilantro",
                "mint",
                "thyme",
                "rosemary",
                "oregano",
                "chicken",
                "beef",
                "pork",
                "fish",
                "shrimp",
                "lamb",
                "turkey",
                "flour",
                "sugar",
                "butter",
                "oil",
                "salt",
                "water",
                "milk",
                "cream",
                "cheese",
                "yogurt",
                "bread",
                "rice",
                "pasta",
                "noodle",
            ]
            if any(word in line_lower for word in food_words):
                return True

        return False

    @staticmethod
    def _format_ingredient_sections(sections: List[dict]) -> str:
        """Format ingredient sections with headers."""
        result = []

        for section in sections:
            # Add header
            result.append(f"\n{section['header']}")
            # Add ingredients
            for item in section["items"]:
                result.append(f"- {item}")

        return "\n".join(result).strip()
