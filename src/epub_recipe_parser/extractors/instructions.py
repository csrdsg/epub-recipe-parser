"""Extract cooking instructions from HTML."""

import logging
import re
from typing import Optional, Dict, Any
from bs4 import BeautifulSoup

from epub_recipe_parser.utils.html import HTMLParser
from epub_recipe_parser.utils.patterns import (
    INSTRUCTION_KEYWORDS,
    COOKING_VERBS_PATTERN,
    MEASUREMENT_PATTERN,
    NARRATIVE_INSTRUCTION_PREFIXES,
)

logger = logging.getLogger(__name__)


class InstructionsExtractor:
    """Extract cooking instructions from HTML."""

    # CSS classes commonly used for instruction paragraphs
    INSTRUCTION_CLASSES = {
        "method",
        "step",
        "instruction",
        "direction",
        "preparation",
        "noindentt",
        "noindent",
        "noindentp",
        "methodp",
        "stepp",
        "dir",
        "proc",
        "procedure",
    }

    # Patterns that indicate we've moved past instructions
    STOP_PATTERNS = [
        r"^tip[s]?:",
        r"^note[s]?:",
        r"^serving suggestion[s]?:",
        r"^variation[s]?:",
        r"^chef'?s? note:",
        r"^what else",
        r"^storage:",
        r"^make ahead:",
    ]

    @staticmethod
    def extract(soup: BeautifulSoup, text: str) -> Optional[str]:
        """Extract instructions using multiple strategies."""
        # Strategy 1: Find by CSS class (most reliable when present)
        instructions = InstructionsExtractor._extract_by_class(soup)
        if instructions and len(instructions) > 100:
            return instructions

        # Strategy 2: Find by header with enhanced keywords
        instructions = InstructionsExtractor._extract_by_header(soup)
        if instructions and len(instructions) > 100:
            return instructions

        # Strategy 3: Find narrative instructions with keyword prefixes (e.g., "To make:")
        instructions = InstructionsExtractor._extract_narrative_with_prefix(soup)
        if instructions and len(instructions) > 100:
            return instructions

        # Strategy 4: Find long narrative paragraphs with many cooking verbs
        # Moved up priority since it's good at catching single-paragraph instructions
        instructions = InstructionsExtractor._extract_long_narrative(soup)
        if instructions and len(instructions) > 100:
            return instructions

        # Strategy 5: Find paragraphs after ingredient sections
        instructions = InstructionsExtractor._extract_post_ingredients(soup)
        if instructions and len(instructions) > 100:
            return instructions

        # Strategy 6: Find numbered lists with cooking verbs
        instructions = InstructionsExtractor._extract_from_lists(soup)
        if instructions and len(instructions) > 100:
            return instructions

        # Strategy 7: Find consecutive paragraphs with cooking verbs (improved)
        instructions = InstructionsExtractor._extract_by_cooking_verbs(soup)
        if instructions and len(instructions) > 100:
            return instructions

        # Strategy 8: Fallback - find any paragraph with high cooking verb density
        instructions = InstructionsExtractor._extract_any_cooking_paragraph(soup)
        if instructions and len(instructions) > 100:
            return instructions

        return None

    @staticmethod
    def _extract_by_class(soup: BeautifulSoup) -> Optional[str]:
        """Extract instructions based on CSS classes."""
        instruction_paragraphs = []

        for paragraph in soup.find_all("p"):
            classes = paragraph.get("class")
            if not classes:
                continue

            # Check if any class matches our instruction class patterns
            # Type safety: Handle both list and string class attributes
            if isinstance(classes, list):
                class_str = " ".join(str(c) for c in classes).lower()
            else:
                class_str = str(classes).lower()

            if any(
                inst_class in class_str for inst_class in InstructionsExtractor.INSTRUCTION_CLASSES
            ):
                text_content = paragraph.get_text(strip=True)
                if len(text_content) >= 30:
                    instruction_paragraphs.append(text_content)

        if len(instruction_paragraphs) >= 2:
            return "\n\n".join(instruction_paragraphs)

        return None

    @staticmethod
    def _extract_by_header(soup: BeautifulSoup) -> Optional[str]:
        """Extract instructions by finding instruction section headers."""
        # Enhanced keyword list
        enhanced_keywords = INSTRUCTION_KEYWORDS + [
            "to make",
            "how to prepare",
            "let's cook",
            "cooking instructions",
            "recipe method",
            "the method",
        ]

        instructions = HTMLParser.find_section_by_header(soup, enhanced_keywords)
        return instructions

    @staticmethod
    def _extract_post_ingredients(soup: BeautifulSoup) -> Optional[str]:
        """Extract instructions that come after ingredient sections.

        Many recipes have a structure like:
        - Description
        - FOR THE SAUCE (ingredients)
        - FOR THE PASTA (ingredients)
        - TO SERVE (ingredients)
        - [Instructions start here without header]
        """
        instruction_paragraphs = []
        past_ingredients = False
        ingredient_header_count = 0

        for element in soup.find_all(["p", "h1", "h2", "h3", "h4", "h5", "h6"]):
            text_content = element.get_text(strip=True).lower()

            # Check for ingredient section headers
            if element.name in ["h1", "h2", "h3", "h4", "h5", "h6", "p"]:
                # Get paragraph class to help identify ingredient headers
                classes = element.get("class")
                if isinstance(classes, list):
                    class_str = " ".join(str(c) for c in classes).lower()
                elif classes:
                    class_str = str(classes).lower()
                else:
                    class_str = ""

                # Headers like "FOR THE SAUCE", "INGREDIENTS", "YOU'LL NEED", "TO SERVE"
                # Only match if it's short (likely a header) or has specific header class
                is_likely_header = (
                    len(text_content) < 50
                    or "ihead" in class_str
                    or "head" in class_str
                    or element.name in ["h1", "h2", "h3", "h4", "h5", "h6"]
                )

                if is_likely_header and any(
                    keyword in text_content
                    for keyword in [
                        "for the",
                        "you'll need",
                        "you will need",
                        "to serve",
                        "to garnish",
                        "for serving",
                    ]
                ):
                    ingredient_header_count += 1
                    past_ingredients = False  # Reset for each new ingredient section
                    continue

                # Check for standalone "ingredients" header (not part of instruction text)
                if is_likely_header and text_content.strip() == "ingredients":
                    ingredient_header_count += 1
                    past_ingredients = False
                    continue

                # Check if this looks like an instruction header
                if any(keyword in text_content for keyword in INSTRUCTION_KEYWORDS):
                    past_ingredients = True
                    continue

            # If we're in a paragraph and have seen ingredient sections
            if element.name == "p" and ingredient_header_count > 0:
                # Get paragraph class
                classes = element.get("class")
                if isinstance(classes, list):
                    class_str = " ".join(str(c) for c in classes).lower()
                elif classes:
                    class_str = str(classes).lower()
                else:
                    class_str = ""

                # Skip if it's an ingredient item class
                if "item" in class_str or "ingredient" in class_str:
                    continue

                # Skip if it's a serving/metadata class
                if "serv" in class_str or "yield" in class_str or "time" in class_str:
                    continue

                # Check if paragraph has cooking verbs
                verb_count = len(COOKING_VERBS_PATTERN.findall(text_content))

                if verb_count >= 2 and len(text_content) >= 40:
                    past_ingredients = True
                    instruction_paragraphs.append(element.get_text(strip=True))
                elif past_ingredients and verb_count >= 1 and len(text_content) >= 40:
                    # Continue collecting if we're in instruction section
                    instruction_paragraphs.append(element.get_text(strip=True))

                    # Check for stop patterns
                    if InstructionsExtractor._is_stop_pattern(text_content):
                        break

        if len(instruction_paragraphs) >= 2:
            return "\n\n".join(instruction_paragraphs)

        return None

    @staticmethod
    def _extract_from_lists(soup: BeautifulSoup) -> Optional[str]:
        """Extract instructions from ordered or unordered lists."""
        for list_elem in soup.find_all(["ol", "ul"]):
            items = HTMLParser.extract_from_list(list_elem)
            if not items or len(items) < 2:
                continue

            # Check for cooking verbs
            combined_text = " ".join(items).lower()
            cooking_verbs = COOKING_VERBS_PATTERN.findall(combined_text)

            if len(cooking_verbs) >= 3 and len(combined_text) > 100:
                # Use numbered format for better readability
                return "\n\n".join(f"{i+1}. {item}" for i, item in enumerate(items))

        return None

    @staticmethod
    def _extract_by_cooking_verbs(soup: BeautifulSoup) -> Optional[str]:
        """Extract instructions by finding consecutive paragraphs with cooking verbs.

        Improved version that doesn't break too early and handles various paragraph structures.
        """
        instruction_paragraphs = []
        in_instruction_section = False
        consecutive_low_verb_count = 0  # Track paragraphs with few verbs

        for paragraph in soup.find_all("p"):
            text_content = paragraph.get_text(strip=True)

            # Skip very short paragraphs
            if len(text_content) < 40:
                continue

            # Get paragraph class to skip non-instruction classes
            classes = paragraph.get("class")
            if isinstance(classes, list):
                class_str = " ".join(str(c) for c in classes).lower()
            elif classes:
                class_str = str(classes).lower()
            else:
                class_str = ""

            # Skip ingredient, metadata, and header classes
            if any(
                skip in class_str
                for skip in ["item", "ingredient", "serv", "yield", "time", "ihead"]
            ):
                continue

            text_lower = text_content.lower()
            cooking_verb_count = len(COOKING_VERBS_PATTERN.findall(text_lower))

            # Start collecting if we find a paragraph with multiple cooking verbs
            if cooking_verb_count >= 2:
                in_instruction_section = True
                consecutive_low_verb_count = 0
                instruction_paragraphs.append(text_content)

            # Continue collecting if we're in instruction section and have at least 1 verb
            elif in_instruction_section and cooking_verb_count >= 1:
                consecutive_low_verb_count = 0
                instruction_paragraphs.append(text_content)

            # Even with 0 verbs, continue if it's short and we're in instructions
            # (might be a transition sentence like "Meanwhile" or "At the same time")
            elif in_instruction_section and len(text_content) < 100:
                consecutive_low_verb_count += 1
                # Only break if we have multiple consecutive low-verb paragraphs
                if consecutive_low_verb_count >= 2:
                    break
                instruction_paragraphs.append(text_content)

            # Break if we hit stop patterns
            elif in_instruction_section:
                if InstructionsExtractor._is_stop_pattern(text_lower):
                    break
                # If we have enough instructions and hit a paragraph with no verbs, stop
                if len(instruction_paragraphs) >= 3 and cooking_verb_count == 0:
                    break

        if len(instruction_paragraphs) >= 2:
            return "\n\n".join(instruction_paragraphs)

        return None

    @staticmethod
    def _is_stop_pattern(text: str) -> bool:
        """Check if text matches a stop pattern indicating end of instructions."""
        text_lower = text.lower().strip()
        return any(re.match(pattern, text_lower) for pattern in InstructionsExtractor.STOP_PATTERNS)

    @staticmethod
    def _extract_narrative_with_prefix(soup: BeautifulSoup) -> Optional[str]:
        """Extract narrative-style instructions that start with keywords like 'To make:' or 'To prepare:'.

        These are often found in recipes where the instructions are written in narrative/prose format
        rather than as discrete steps. For example:
        "To make ghee: Melt two sticks of butter in a saucepan over medium heat. Cook for 20 minutes..."
        """
        instruction_paragraphs = []

        for paragraph in soup.find_all("p"):
            text_content = paragraph.get_text(strip=True)

            # Skip very short paragraphs
            if len(text_content) < 50:
                continue

            # Check if paragraph starts with a narrative instruction prefix
            match = NARRATIVE_INSTRUCTION_PREFIXES.match(text_content)
            if match:
                # Check that it has multiple cooking verbs (to confirm it's instructions, not ingredients)
                cooking_verb_count = len(COOKING_VERBS_PATTERN.findall(text_content.lower()))

                # Also check that it doesn't look like an ingredient list
                # (ingredient lists have many measurements but few cooking verbs)
                measurement_count = len(MEASUREMENT_PATTERN.findall(text_content))

                # If more measurements than cooking verbs, likely an ingredient list
                if measurement_count > cooking_verb_count * 2:
                    continue

                # If it has good cooking verb density, it's likely instructions
                # Lowered threshold from 3 to 2 to catch shorter instructions
                if cooking_verb_count >= 2:
                    instruction_paragraphs.append(text_content)

        if len(instruction_paragraphs) >= 1:
            return "\n\n".join(instruction_paragraphs)

        return None

    @staticmethod
    def _extract_long_narrative(soup: BeautifulSoup) -> Optional[str]:
        """Extract instructions from single long narrative paragraphs.

        Some recipes have all instructions in one or two very long paragraphs
        with many cooking verbs and detailed instructions. For example:
        "Preheat your oven to 350°F and prepare a baking pan... In a large bowl,
        combine the flour, sugar, and salt... Beat the eggs in a separate bowl..."
        """
        instruction_paragraphs = []

        for paragraph in soup.find_all("p"):
            text_content = paragraph.get_text(strip=True)

            # Look for long paragraphs (narrative instructions tend to be long)
            # Lowered from 200 to 150 to catch more edge cases
            if len(text_content) < 150:
                continue

            # Get paragraph class to skip non-instruction classes
            classes = paragraph.get("class")
            if isinstance(classes, list):
                class_str = " ".join(str(c) for c in classes).lower()
            elif classes:
                class_str = str(classes).lower()
            else:
                class_str = ""

            # Skip ingredient, metadata, and header classes
            if any(
                skip in class_str
                for skip in ["item", "ingredient", "serv", "yield", "time", "ihead"]
            ):
                continue

            text_lower = text_content.lower()

            # Count cooking verbs
            cooking_verb_count = len(COOKING_VERBS_PATTERN.findall(text_lower))

            # Count measurements to distinguish from ingredient lists
            measurement_count = len(MEASUREMENT_PATTERN.findall(text_content))

            # For long narrative instructions, we expect:
            # 1. Many cooking verbs (at least 4 for a long paragraph, lowered from 5)
            # 2. High density of cooking verbs relative to length
            # 3. Not too many measurements (which would indicate ingredients)
            words = len(text_content.split())
            verb_density = cooking_verb_count / (words / 100.0) if words > 0 else 0

            # If has many cooking verbs and good density, likely instructions
            # Relaxed thresholds: verb_count from 5->4, density from 2.0->1.5
            if (
                cooking_verb_count >= 4
                and verb_density >= 1.5
                and measurement_count <= cooking_verb_count * 2
            ):
                instruction_paragraphs.append(text_content)

        if len(instruction_paragraphs) >= 1:
            return "\n\n".join(instruction_paragraphs)

        return None

    @staticmethod
    def _looks_like_ingredient_line(text: str) -> bool:
        """Check if a line of text looks like an ingredient (measurement + item)."""
        # Very short lines are likely ingredient items
        if len(text) < 50:
            # Has measurement pattern and few cooking verbs
            has_measurement = MEASUREMENT_PATTERN.search(text) is not None
            cooking_verbs = len(COOKING_VERBS_PATTERN.findall(text.lower()))
            return has_measurement and cooking_verbs <= 1
        return False

    @staticmethod
    def _extract_any_cooking_paragraph(soup: BeautifulSoup) -> Optional[str]:
        """Fallback strategy: Extract any paragraph with high cooking verb density.

        This is used as a last resort when other strategies fail. It looks for
        any paragraph that has a high concentration of cooking verbs, indicating
        it's likely to be instructions.
        """
        best_paragraph = None
        best_verb_count = 0

        for paragraph in soup.find_all("p"):
            text_content = paragraph.get_text(strip=True)

            # Need reasonable length
            if len(text_content) < 100:
                continue

            # Get paragraph class to skip non-instruction classes
            classes = paragraph.get("class")
            if isinstance(classes, list):
                class_str = " ".join(str(c) for c in classes).lower()
            elif classes:
                class_str = str(classes).lower()
            else:
                class_str = ""

            # Skip obvious non-instruction classes
            if any(
                skip in class_str
                for skip in ["item", "ingredient", "serv", "yield", "time", "ihead", "intro"]
            ):
                continue

            text_lower = text_content.lower()
            cooking_verb_count = len(COOKING_VERBS_PATTERN.findall(text_lower))
            measurement_count = len(MEASUREMENT_PATTERN.findall(text_content))

            # Must have good cooking verb count and not be ingredient-heavy
            if cooking_verb_count >= 3 and measurement_count <= cooking_verb_count:
                if cooking_verb_count > best_verb_count:
                    best_verb_count = cooking_verb_count
                    best_paragraph = text_content

        return best_paragraph if best_paragraph else None

    @staticmethod
    def extract_with_patterns(
        soup: BeautifulSoup, text: str
    ) -> tuple[Optional[str], Dict[str, Any]]:
        """Modern pattern-based extraction with confidence scoring.

        This method uses structural detection, pattern matching, and linguistic
        analysis to extract instructions with confidence metrics.

        Args:
            soup: BeautifulSoup object containing the HTML
            text: Plain text version of the content

        Returns:
            tuple: (instructions_text, metadata_dict)
                - instructions_text: Extracted instructions or None
                - metadata_dict: Extraction metadata including:
                    - strategy: str - Detection strategy used
                    - confidence: float - Confidence score (0.0-1.0)
                    - linguistic_score: float - Linguistic quality score
                    - used_structural_detector: bool
                    - zone_count: int - Number of zones detected
                    - detection_method: str - Specific detection method used

        Example:
            >>> html = '<div class="method"><p>Heat oil. Cook onions.</p></div>'
            >>> soup = BeautifulSoup(html, 'html.parser')
            >>> text = soup.get_text()
            >>> instructions, metadata = InstructionsExtractor.extract_with_patterns(soup, text)
            >>> print(f"Confidence: {metadata['confidence']:.2f}")
            Confidence: 0.87
            >>> print(f"Strategy: {metadata['strategy']}")
            Strategy: structural_css_class
        """
        from epub_recipe_parser.core.patterns import (
            InstructionPatternDetector,
            InstructionLinguisticAnalyzer,
            InstructionStructuralDetector,
        )

        metadata = {
            'strategy': None,
            'confidence': 0.0,
            'linguistic_score': 0.0,
            'used_structural_detector': False,
            'zone_count': 0,
            'detection_method': None
        }

        # Try StructuralDetector first
        logger.debug("Patterns: Trying InstructionStructuralDetector.find_instruction_zones()")
        zones = InstructionStructuralDetector.find_instruction_zones(soup)

        if zones:
            metadata['used_structural_detector'] = True
            metadata['zone_count'] = len(zones)
            logger.debug(f"Patterns: Found {len(zones)} potential instruction zones")

            # Evaluate each zone and select best
            best_zone = None
            best_combined_confidence = 0.0

            for zone in zones:
                # Safety check: ensure zone and zone.zone are not None
                if not zone or not zone.zone:
                    logger.debug("Skipping None zone")
                    continue

                zone_text = zone.zone.get_text(strip=True)

                # Skip very short zones
                if len(zone_text) < 50:
                    continue

                # Calculate pattern confidence
                pattern_confidence = InstructionPatternDetector.calculate_confidence(zone_text)

                # Calculate linguistic score
                linguistic_score = InstructionLinguisticAnalyzer.calculate_instruction_score(zone_text)

                # Combine structural detection confidence with content confidence
                # Weighted: 30% structural, 50% pattern, 20% linguistic
                combined_confidence = (
                    zone.confidence * 0.30 +
                    pattern_confidence * 0.50 +
                    linguistic_score * 0.20
                )

                logger.debug(
                    f"Zone ({zone.detection_method}): "
                    f"structural={zone.confidence:.2f}, "
                    f"pattern={pattern_confidence:.2f}, "
                    f"linguistic={linguistic_score:.2f}, "
                    f"combined={combined_confidence:.2f}"
                )

                if combined_confidence > best_combined_confidence:
                    best_combined_confidence = combined_confidence
                    best_zone = zone
                    metadata['confidence'] = pattern_confidence
                    metadata['linguistic_score'] = linguistic_score
                    metadata['strategy'] = f"structural_{zone.detection_method}"
                    metadata['detection_method'] = zone.detection_method

            # Use best zone if confidence is sufficient
            if best_zone and best_combined_confidence >= 0.5:
                instructions_text = best_zone.zone.get_text(strip=True)
                logger.info(
                    f"Patterns SUCCESS: {metadata['strategy']} "
                    f"(confidence={metadata['confidence']:.2f}, "
                    f"combined={best_combined_confidence:.2f})"
                )
                return instructions_text, metadata
            else:
                logger.debug(
                    f"Patterns: Best zone has low combined confidence "
                    f"({best_combined_confidence:.2f}), falling back"
                )

        # Fall back to original strategies with confidence augmentation
        logger.debug("Patterns: Falling back to original extraction with augmentation")
        instructions = InstructionsExtractor.extract(soup, text)

        if instructions:
            # Calculate confidence for original extraction
            confidence = InstructionPatternDetector.calculate_confidence(instructions)
            linguistic = InstructionLinguisticAnalyzer.calculate_instruction_score(instructions)

            metadata['strategy'] = 'original_with_patterns'
            metadata['confidence'] = confidence
            metadata['linguistic_score'] = linguistic

            logger.info(
                f"Patterns SUCCESS: Original method enhanced "
                f"(confidence={confidence:.2f})"
            )
            return instructions, metadata

        logger.debug("Patterns FAILED: No instructions found (expected for non-recipe sections)")
        return None, metadata
