"""Extract ingredient lists from HTML."""

import logging
import re
from typing import Optional, List, Union, Dict, Any, Tuple
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
    # Note: "for the" headers are allowed WITHIN recipes to organize multi-section
    # ingredient lists (e.g., "For the Dough", "For the Filling"). The RecipeValidator
    # will filter out "FOR THE X" patterns when they appear as standalone section titles.
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
    def extract(
        soup: BeautifulSoup,
        text: str,
        use_patterns: bool = True
    ) -> Union[Optional[str], Tuple[Optional[str], Dict[str, Any]]]:
        """Extract ingredients with optional pattern-based detection.

        This method acts as a dispatcher that routes to either pattern-based
        or legacy extraction based on the use_patterns flag.

        Args:
            soup: BeautifulSoup object containing the HTML
            text: Plain text version of the content
            use_patterns: If True, use pattern-based extraction with metadata (default: True)
                         If False, use legacy extraction (returns just text)

        Returns:
            If use_patterns=True:
                tuple[Optional[str], Dict[str, Any]]: (ingredients_text, metadata)
            If use_patterns=False:
                Optional[str]: ingredients_text only (legacy behavior)

        The metadata dict includes:
            - strategy: Detection strategy used
            - confidence: Pattern confidence score (0.0-1.0)
            - linguistic_score: Linguistic quality score (0.0-1.0)
            - combined_score: Weighted combination score
        """
        if use_patterns:
            try:
                # Use pattern-based extraction
                result, metadata = IngredientsExtractor.extract_with_patterns(soup, text)

                # Fallback to legacy if pattern extraction fails
                if result is None:
                    logger.debug("Pattern extraction returned None, falling back to legacy")
                    legacy_result = IngredientsExtractor._extract_legacy(soup, text)

                    if legacy_result:
                        # Add fallback metadata
                        metadata = {
                            "strategy": "legacy_fallback",
                            "confidence": 0.5,  # Conservative confidence for fallback
                            "linguistic_score": 0.0,
                            "combined_score": 0.5,
                            "fallback_reason": "pattern_extraction_failed"
                        }
                        return legacy_result, metadata
                    else:
                        # Both methods failed
                        return None, metadata

                return result, metadata
            except Exception as e:
                # Graceful degradation on error
                logger.warning(f"Pattern extraction failed with error: {e}, falling back to legacy")
                legacy_result = IngredientsExtractor._extract_legacy(soup, text)

                if legacy_result:
                    metadata = {
                        "strategy": "legacy_fallback",
                        "confidence": 0.5,
                        "linguistic_score": 0.0,
                        "combined_score": 0.5,
                        "fallback_reason": f"pattern_extraction_error: {str(e)}"
                    }
                    return legacy_result, metadata
                else:
                    return None, {}
        else:
            # Legacy mode - return just the text
            return IngredientsExtractor._extract_legacy(soup, text)

    @staticmethod
    def _extract_legacy(soup: BeautifulSoup, text: str) -> Optional[str]:
        """Extract ingredients using multiple strategies with detailed logging.

        This is the legacy extraction method, renamed from the original extract().
        It uses HTML structure and text patterns without advanced pattern detection.
        """
        logger.debug("Starting ingredient extraction (legacy mode)")

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

        # Strategy 2.5: Find ingredients in paragraph tags with specific classes
        logger.debug("Strategy 2.5: Searching for paragraph-based ingredients (class-based)")
        para_ingredients = IngredientsExtractor._extract_from_paragraph_classes(soup)
        if para_ingredients:
            logger.info(
                f"Strategy 2.5 SUCCESS: Found ingredients in paragraphs ({len(para_ingredients)} chars)"
            )
            return para_ingredients

        # Strategy 3: Find multiple short paragraphs with measurements
        logger.debug("Strategy 3: Searching for multiple consecutive paragraphs with measurements")
        consecutive_ingredients = []
        para_count = 0

        for paragraph in soup.find_all("p"):
            text_content = paragraph.get_text(strip=True)

            # Check each paragraph for measurements (typical ingredient length)
            if len(text_content) >= 10 and len(text_content) < 150:
                para_count += 1
                if MEASUREMENT_PATTERN.search(text_content):
                    consecutive_ingredients.append(text_content)
                elif len(consecutive_ingredients) > 0:
                    # Break run if gap is too large
                    if len(consecutive_ingredients) >= 3:
                        # Found a good run
                        result = "\n".join(f"- {item}" for item in consecutive_ingredients)
                        logger.info(
                            f"Strategy 3 SUCCESS: Found ingredients in consecutive paragraphs ({len(result)} chars, {len(consecutive_ingredients)} items)"
                        )
                        return result
                    consecutive_ingredients = []

        # Check final run
        if len(consecutive_ingredients) >= 3:
            result = "\n".join(f"- {item}" for item in consecutive_ingredients)
            logger.info(
                f"Strategy 3 SUCCESS: Found ingredients in consecutive paragraphs ({len(result)} chars, {len(consecutive_ingredients)} items)"
            )
            return result

        logger.debug(f"Strategy 3: Checked {para_count} paragraphs, no suitable runs found")

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

        logger.debug("All extraction strategies FAILED: No ingredients found (expected for non-recipe sections)")
        return None

    @staticmethod
    def extract_with_patterns(
        soup: BeautifulSoup, text: str
    ) -> tuple[Optional[str], dict]:
        """Extract ingredients using pattern-based detection with confidence scoring.

        Uses multi-dimensional extraction strategy:
        1. Structural Detection (HTML zones) - 30% weight
        2. Pattern Matching (measurements, nouns) - 50% weight
        3. Linguistic Analysis (text quality) - 20% weight

        Returns:
            tuple: (ingredients_text, analysis_metadata)
                - ingredients_text: Extracted ingredients or None
                - analysis_metadata: {
                    'strategy': str,  # Detection strategy used
                    'confidence': float,  # Pattern confidence 0.0-1.0
                    'linguistic_score': float,  # Linguistic quality 0.0-1.0
                    'used_structural_detector': bool,
                    'zone_count': int,  # Number of HTML zones found
                    'combined_score': float  # Weighted combination
                  }
        """
        from epub_recipe_parser.core.patterns import (
            IngredientPatternDetector,
            IngredientLinguisticAnalyzer,
            IngredientStructuralDetector,
        )

        metadata = {
            "strategy": None,
            "confidence": 0.0,
            "linguistic_score": 0.0,
            "structural_confidence": 0.0,
            "used_structural_detector": False,
            "zone_count": 0,
            "combined_score": 0.0,
        }

        # Try IngredientStructuralDetector first
        logger.debug("Patterns: Trying IngredientStructuralDetector.find_ingredient_zones()")
        zones = IngredientStructuralDetector.find_ingredient_zones(soup)

        if zones:
            metadata["used_structural_detector"] = True
            metadata["zone_count"] = len(zones)

            # Use highest confidence zone
            best_zone = zones[0]  # Already sorted by confidence
            metadata["structural_confidence"] = best_zone.confidence

            # Extract text from zone
            ingredients_text = best_zone.get_text()

            if len(ingredients_text) > 50:
                # Calculate pattern and linguistic scores
                pattern_confidence = IngredientPatternDetector.calculate_confidence(
                    ingredients_text
                )
                linguistic_score = IngredientLinguisticAnalyzer.calculate_ingredient_score(
                    ingredients_text
                )

                # Combined score: Structural 30% + Pattern 50% + Linguistic 20%
                combined = (
                    (best_zone.confidence * 0.30) +
                    (pattern_confidence * 0.50) +
                    (linguistic_score * 0.20)
                )

                metadata["strategy"] = "structural_zones"  # type: ignore[assignment]
                metadata["confidence"] = pattern_confidence
                metadata["linguistic_score"] = linguistic_score
                metadata["combined_score"] = combined
                metadata["detection_method"] = best_zone.detection_method  # type: ignore[assignment]

                # Use combined score for threshold
                if combined >= 0.5:
                    logger.info(
                        f"Patterns SUCCESS: Structural zones (combined={combined:.2f}, "
                        f"method={best_zone.detection_method}, zones={len(zones)})"
                    )
                    return ingredients_text, metadata
                else:
                    logger.debug(
                        f"Patterns: Structural zones found but low combined score ({combined:.2f})"
                    )

        # Fall back to original extraction with pattern augmentation
        logger.debug("Patterns: Falling back to original extraction with pattern augmentation")
        ingredients = IngredientsExtractor._extract_legacy(soup, text)

        if ingredients:
            pattern_confidence = IngredientPatternDetector.calculate_confidence(ingredients)
            linguistic_score = IngredientLinguisticAnalyzer.calculate_ingredient_score(ingredients)

            # Combined score for fallback (no structural component)
            combined = (pattern_confidence * 0.70) + (linguistic_score * 0.30)

            metadata["strategy"] = "original_with_patterns"  # type: ignore[assignment]
            metadata["confidence"] = pattern_confidence
            metadata["linguistic_score"] = linguistic_score
            metadata["combined_score"] = combined

            logger.info(
                f"Patterns SUCCESS: Original method enhanced "
                f"(pattern={pattern_confidence:.2f}, linguistic={linguistic_score:.2f}, combined={combined:.2f})"
            )
            return ingredients, metadata

        logger.debug("Patterns FAILED: No ingredients found (expected for non-recipe sections)")
        return None, metadata

    @staticmethod
    def _extract_from_paragraph_classes(soup: BeautifulSoup) -> Optional[str]:
        """Extract ingredients from <p> tags with ingredient-related classes.

        Many modern EPUBs format ingredients as individual paragraphs with
        semantic CSS classes rather than lists.
        """
        # CSS classes used for ingredients in various EPUBs
        ingredient_classes = [
            "ing",
            "ingt",
            "ings",
            "ingst",
            "ingd",  # Common patterns
            "ingredient",
            "ing-item",
            "recipe-ingredient",
        ]

        ingredients = []

        for para in soup.find_all("p"):
            para_classes_raw = para.get("class")

            # Handle both list and string types for class attribute
            if isinstance(para_classes_raw, str):
                para_classes = [para_classes_raw]
            elif isinstance(para_classes_raw, list):
                para_classes = [str(c) for c in para_classes_raw]
            elif para_classes_raw is None:
                para_classes = []
            else:
                para_classes = []

            # Check if any class matches ingredient patterns
            if any(cls in ingredient_classes for cls in para_classes):
                text = para.get_text(strip=True)

                # Skip sub-headers like "For the sauce:", "INGREDIENTS", etc.
                if not text or len(text) < 3:
                    continue

                lower_text = text.lower()
                # Skip common section headers that aren't actual ingredients
                skip_patterns = [
                    "ingredients",
                    "you will need",
                    "you'll need",
                    "what you need",
                    "shopping list",
                ]
                # Also skip "for the X" patterns (recipe sub-sections)
                if any(pattern in lower_text for pattern in skip_patterns):
                    # This is a section header, not an ingredient
                    continue
                if lower_text.startswith("for the ") and len(text) < 40:
                    # This is likely a sub-section header like "For the dressing"
                    continue

                # Valid ingredient
                ingredients.append(text)

        # Return formatted ingredients if we found at least 3
        if len(ingredients) >= 3:
            return "\n".join(f"- {item}" for item in ingredients)

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
