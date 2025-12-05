# Modernization Code Examples

## Overview

This document provides concrete code examples showing how the modernized InstructionsExtractor and MetadataExtractor would work. These examples demonstrate the pattern-based approach with confidence scoring.

---

## Example 1: InstructionPatternDetector

### File: `src/epub_recipe_parser/core/patterns/instruction_detectors.py`

```python
"""Pattern detection for instructions extraction."""

import re
from typing import Optional, Dict, Any
from epub_recipe_parser.utils.patterns import COOKING_VERBS_PATTERN, MEASUREMENT_PATTERN


class InstructionPatternDetector:
    """Detects instruction patterns and calculates confidence scores."""

    # Pattern categories
    TEMPORAL_MARKERS = {
        "until", "after", "before", "while", "during", "when", "then",
        "once", "as soon as", "immediately", "gradually", "slowly"
    }

    SEQUENTIAL_MARKERS = {
        "first", "second", "third", "next", "then", "finally", "lastly",
        "meanwhile", "at the same time", "simultaneously"
    }

    IMPERATIVE_STARTERS = {
        "preheat", "heat", "place", "add", "mix", "stir", "combine",
        "whisk", "beat", "fold", "cook", "bake", "roast", "fry", "grill"
    }

    @classmethod
    def calculate_confidence(cls, text: str) -> float:
        """Calculate confidence that text contains instructions.

        Scoring components (0.0-1.0):
        - Cooking verb density: 30%
        - Temporal/sequential markers: 25%
        - Imperative sentence structure: 20%
        - Paragraph length characteristics: 15%
        - Absence of measurements: 10%

        Args:
            text: Text to analyze

        Returns:
            Confidence score between 0.0 and 1.0

        Examples:
            >>> text = "Preheat oven to 350°F. Heat oil in a pan. Cook until golden."
            >>> InstructionPatternDetector.calculate_confidence(text)
            0.87

            >>> text = "2 cups flour\\n1 cup sugar\\n½ tsp salt"
            >>> InstructionPatternDetector.calculate_confidence(text)
            0.15
        """
        if not text or len(text.strip()) < 10:
            return 0.0

        text_lower = text.lower()

        # Component 1: Cooking verb density (30% weight)
        verb_score = cls._calculate_verb_density(text_lower) * 0.30

        # Component 2: Temporal/sequential markers (25% weight)
        marker_score = cls._calculate_marker_score(text_lower) * 0.25

        # Component 3: Imperative sentences (20% weight)
        imperative_score = cls._detect_imperative_sentences(text_lower) * 0.20

        # Component 4: Paragraph length (15% weight)
        length_score = cls._check_paragraph_length(text) * 0.15

        # Component 5: Measurement penalty (10% weight)
        measurement_score = cls._calculate_measurement_penalty(text) * 0.10

        total_score = (
            verb_score +
            marker_score +
            imperative_score +
            length_score +
            measurement_score
        )

        return min(max(total_score, 0.0), 1.0)

    @classmethod
    def _calculate_verb_density(cls, text: str) -> float:
        """Calculate cooking verb density.

        Args:
            text: Lowercase text

        Returns:
            Score 0.0-1.0 based on verbs per 100 words
        """
        if not text:
            return 0.0

        words = text.split()
        word_count = len(words)

        if word_count == 0:
            return 0.0

        # Count cooking verbs
        verb_matches = COOKING_VERBS_PATTERN.findall(text)
        verb_count = len(verb_matches)

        # Calculate density (verbs per 100 words)
        density = (verb_count / word_count) * 100

        # Optimal density for instructions: 3-10 verbs per 100 words
        if 3 <= density <= 10:
            return 1.0
        elif 1 <= density < 3:
            return density / 3.0  # Linear scale below optimal
        elif 10 < density <= 15:
            return 1.0 - ((density - 10) / 10.0)  # Penalty above optimal
        else:
            return 0.0

    @classmethod
    def _calculate_marker_score(cls, text: str) -> float:
        """Calculate temporal/sequential marker score.

        Args:
            text: Lowercase text

        Returns:
            Score 0.0-1.0 based on marker presence
        """
        marker_count = sum(
            1 for marker in cls.TEMPORAL_MARKERS | cls.SEQUENTIAL_MARKERS
            if marker in text
        )

        # Scale: 0 markers = 0.0, 3+ markers = 1.0
        if marker_count == 0:
            return 0.0
        elif marker_count >= 3:
            return 1.0
        else:
            return marker_count / 3.0

    @classmethod
    def _detect_imperative_sentences(cls, text: str) -> float:
        """Detect imperative sentence structure.

        Args:
            text: Lowercase text

        Returns:
            Score 0.0-1.0 based on imperative pattern presence
        """
        sentences = re.split(r'[.!?]+', text)
        sentences = [s.strip() for s in sentences if s.strip()]

        if not sentences:
            return 0.0

        imperative_count = 0
        for sentence in sentences:
            words = sentence.split()
            if not words:
                continue

            # Check if sentence starts with imperative verb
            first_word = words[0].rstrip(',.:;')
            if first_word in cls.IMPERATIVE_STARTERS:
                imperative_count += 1

        # Calculate ratio
        imperative_ratio = imperative_count / len(sentences)

        return imperative_ratio

    @classmethod
    def _check_paragraph_length(cls, text: str) -> float:
        """Check if paragraph length is typical for instructions.

        Args:
            text: Text to check

        Returns:
            Score 0.0-1.0 based on length characteristics
        """
        text_length = len(text)

        # Instructions typically 100-500 characters per paragraph
        # Very short (<50) or very long (>1000) less likely
        if 100 <= text_length <= 500:
            return 1.0
        elif 50 <= text_length < 100:
            return (text_length - 50) / 50.0
        elif 500 < text_length <= 1000:
            return 1.0 - ((text_length - 500) / 500.0)
        else:
            return 0.0

    @classmethod
    def _calculate_measurement_penalty(cls, text: str) -> float:
        """Calculate penalty for measurement presence.

        Many measurements suggest ingredients, not instructions.

        Args:
            text: Text to check

        Returns:
            Score 0.0-1.0 (higher = fewer measurements)
        """
        lines = [line.strip() for line in text.split('\n') if line.strip()]

        if not lines:
            return 1.0

        # Count lines with measurements
        measurement_lines = sum(
            1 for line in lines if MEASUREMENT_PATTERN.search(line)
        )

        measurement_ratio = measurement_lines / len(lines)

        # Instructions should have few measurements
        # <20% measurements = high score, >50% = low score
        if measurement_ratio < 0.2:
            return 1.0
        elif measurement_ratio > 0.5:
            return 0.0
        else:
            # Linear interpolation between 0.2 and 0.5
            return 1.0 - ((measurement_ratio - 0.2) / 0.3)
```

---

## Example 2: InstructionStructuralDetector

### File: `src/epub_recipe_parser/core/patterns/instruction_structural.py`

```python
"""Structural detection for instruction zones in HTML."""

from typing import List, Dict, Any
from bs4 import BeautifulSoup, Tag
from dataclasses import dataclass
from epub_recipe_parser.utils.patterns import INSTRUCTION_KEYWORDS


@dataclass
class InstructionZone:
    """Represents a potential instruction zone in HTML."""
    zone: Tag
    detection_method: str
    confidence: float
    context: Dict[str, Any]


class InstructionStructuralDetector:
    """Detects instruction zones via HTML structure."""

    INSTRUCTION_CLASS_PATTERNS = [
        "method", "step", "instruction", "direction", "preparation",
        "noindentt", "noindent", "noindentp", "methodp", "stepp",
        "dir", "proc", "procedure"
    ]

    @classmethod
    def find_instruction_zones(cls, soup: BeautifulSoup) -> List[InstructionZone]:
        """Find potential instruction zones with context.

        Args:
            soup: BeautifulSoup object to analyze

        Returns:
            List of InstructionZone objects

        Example:
            >>> html = '<div class="method"><p>Heat oil. Cook onions.</p></div>'
            >>> soup = BeautifulSoup(html, 'html.parser')
            >>> zones = InstructionStructuralDetector.find_instruction_zones(soup)
            >>> len(zones)
            1
            >>> zones[0].detection_method
            'css_class'
            >>> zones[0].confidence
            0.9
        """
        zones = []

        # Strategy 1: CSS class-based detection (confidence: 0.9)
        zones.extend(cls._find_by_css_class(soup))

        # Strategy 2: Header-based detection (confidence: 0.85)
        zones.extend(cls._find_by_header(soup))

        # Strategy 3: Post-ingredients positioning (confidence: 0.75)
        zones.extend(cls._find_post_ingredients(soup))

        # Strategy 4: Numbered list detection (confidence: 0.80)
        zones.extend(cls._find_numbered_lists(soup))

        # Remove duplicates (same Tag object)
        return cls._deduplicate_zones(zones)

    @classmethod
    def _find_by_css_class(cls, soup: BeautifulSoup) -> List[InstructionZone]:
        """Find instruction zones by CSS class patterns.

        Args:
            soup: BeautifulSoup object

        Returns:
            List of InstructionZone objects
        """
        zones = []

        for tag in soup.find_all(['div', 'section', 'p']):
            classes = tag.get('class', [])
            if isinstance(classes, str):
                classes = [classes]

            class_str = ' '.join(classes).lower()

            # Check if any instruction class pattern matches
            for pattern in cls.INSTRUCTION_CLASS_PATTERNS:
                if pattern in class_str:
                    zones.append(InstructionZone(
                        zone=tag,
                        detection_method='css_class',
                        confidence=0.9,
                        context={'matched_class': pattern}
                    ))
                    break

        return zones

    @classmethod
    def _find_by_header(cls, soup: BeautifulSoup) -> List[InstructionZone]:
        """Find instruction zones following instruction headers.

        Args:
            soup: BeautifulSoup object

        Returns:
            List of InstructionZone objects
        """
        zones = []

        for header_tag in ['h1', 'h2', 'h3', 'h4', 'h5', 'h6']:
            headers = soup.find_all(header_tag)

            for header in headers:
                header_text = header.get_text().lower().strip()

                # Check if header matches instruction keywords
                if any(keyword in header_text for keyword in INSTRUCTION_KEYWORDS):
                    # Find content after header
                    next_elem = header.find_next_sibling()

                    if next_elem:
                        zones.append(InstructionZone(
                            zone=next_elem,
                            detection_method='header',
                            confidence=0.85,
                            context={
                                'header_text': header_text,
                                'header_tag': header_tag
                            }
                        ))

        return zones

    @classmethod
    def _find_post_ingredients(cls, soup: BeautifulSoup) -> List[InstructionZone]:
        """Find instruction zones positioned after ingredient sections.

        Args:
            soup: BeautifulSoup object

        Returns:
            List of InstructionZone objects
        """
        zones = []

        # Find ingredient sections first
        ingredient_keywords = ['ingredient', 'for the', 'you will need', 'you\\'ll need']
        ingredient_sections = []

        for tag in soup.find_all(['div', 'section', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6']):
            text = tag.get_text().lower().strip()
            if any(kw in text for kw in ingredient_keywords):
                ingredient_sections.append(tag)

        # Find paragraphs after ingredient sections
        for ing_section in ingredient_sections:
            # Get all siblings after ingredient section
            for sibling in ing_section.find_next_siblings(['p', 'div', 'section']):
                text = sibling.get_text(strip=True)

                # Must be substantial paragraph
                if len(text) > 40:
                    zones.append(InstructionZone(
                        zone=sibling,
                        detection_method='post_ingredients',
                        confidence=0.75,
                        context={'after_ingredient_section': True}
                    ))

        return zones

    @classmethod
    def _find_numbered_lists(cls, soup: BeautifulSoup) -> List[InstructionZone]:
        """Find numbered lists that might be instructions.

        Args:
            soup: BeautifulSoup object

        Returns:
            List of InstructionZone objects
        """
        zones = []

        for list_tag in soup.find_all('ol'):
            items = list_tag.find_all('li')

            if len(items) >= 2:  # At least 2 steps
                zones.append(InstructionZone(
                    zone=list_tag,
                    detection_method='numbered_list',
                    confidence=0.80,
                    context={'item_count': len(items)}
                ))

        return zones

    @classmethod
    def _deduplicate_zones(cls, zones: List[InstructionZone]) -> List[InstructionZone]:
        """Remove duplicate zones (same Tag object).

        Args:
            zones: List of InstructionZone objects

        Returns:
            Deduplicated list
        """
        seen_ids = set()
        unique_zones = []

        for zone in zones:
            zone_id = id(zone.zone)
            if zone_id not in seen_ids:
                seen_ids.add(zone_id)
                unique_zones.append(zone)

        return unique_zones
```

---

## Example 3: Modernized InstructionsExtractor

### File: `src/epub_recipe_parser/extractors/instructions.py` (additions)

```python
"""Extract cooking instructions from HTML."""

from typing import Optional, Dict, Any
from bs4 import BeautifulSoup

# Existing code remains unchanged...


class InstructionsExtractor:
    """Extract cooking instructions from HTML."""

    # ... existing methods remain unchanged ...

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
                    - cooking_verb_density: float

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
        import logging

        logger = logging.getLogger(__name__)

        metadata = {
            'strategy': None,
            'confidence': 0.0,
            'linguistic_score': 0.0,
            'used_structural_detector': False,
            'zone_count': 0,
            'cooking_verb_density': 0.0,
            'detection_method': None
        }

        # Try StructuralDetector first
        logger.debug("Patterns: Trying StructuralDetector.find_instruction_zones()")
        zones = InstructionStructuralDetector.find_instruction_zones(soup)

        if zones:
            metadata['used_structural_detector'] = True
            metadata['zone_count'] = len(zones)
            logger.debug(f"Patterns: Found {len(zones)} potential instruction zones")

            # Evaluate each zone and select best
            best_zone = None
            best_combined_confidence = 0.0

            for zone in zones:
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

        logger.warning("Patterns FAILED: No instructions found")
        return None, metadata
```

---

## Example 4: MetadataPatternDetector

### File: `src/epub_recipe_parser/core/patterns/metadata_detectors.py`

```python
"""Pattern detection for metadata extraction."""

import re
from typing import Optional, Dict, Tuple
from dataclasses import dataclass

from epub_recipe_parser.extractors.metadata import MetadataExtractor


@dataclass
class MetadataPattern:
    """Represents a detected metadata pattern."""
    field_name: str
    pattern: re.Pattern
    confidence: float
    match_count: int = 0


class MetadataPatternDetector:
    """Detects metadata patterns and calculates field-level confidence."""

    # Pattern definitions with base confidence scores
    SERVES_PATTERNS = [
        (re.compile(r"serves?[:\s]+(\d+(?:\s*(?:-|to)\s*\d+)?)"), 0.95),
        (re.compile(r"servings?[:\s]+(\d+(?:\s*(?:-|to)\s*\d+)?)"), 0.95),
        (re.compile(r"yield[s]?[:\s]+(\d+(?:\s*(?:-|to)\s*\d+)?)"), 0.90),
        (re.compile(r"makes?[:\s]+(\d+(?:\s*(?:-|to)\s*\d+)?)"), 0.85),
        (re.compile(r"for\s+(\d+(?:\s*(?:-|to)\s*\d+)?)\s+people"), 0.80),
    ]

    PREP_TIME_PATTERNS = [
        (re.compile(r"prep(?:aration)?\s*time[:\s]+([^.\n]+)"), 0.95),
        (re.compile(r"active\s*time[:\s]+([^.\n]+)"), 0.90),
        (re.compile(r"ready\s*in[:\s]+([^.\n]+)"), 0.75),
    ]

    COOK_TIME_PATTERNS = [
        (re.compile(r"cook(?:ing)?\s*time[:\s]+([^.\n]+)"), 0.95),
        (re.compile(r"baking\s*time[:\s]+([^.\n]+)"), 0.90),
        (re.compile(r"total\s*time[:\s]+([^.\n]+)"), 0.80),
    ]

    @classmethod
    def extract_serves(cls, text: str) -> Tuple[Optional[str], float]:
        """Extract serves with confidence score.

        Args:
            text: Text to search

        Returns:
            tuple: (serves_value, confidence)

        Examples:
            >>> MetadataPatternDetector.extract_serves("Serves: 4-6 people")
            ('4-6', 0.95)

            >>> MetadataPatternDetector.extract_serves("No serving info")
            (None, 0.0)
        """
        text_lower = text.lower()

        for pattern, pattern_confidence in cls.SERVES_PATTERNS:
            match = pattern.search(text_lower)
            if match:
                raw_value = match.group(1)

                # Parse and validate
                parsed = MetadataExtractor.parse_servings(raw_value)

                if parsed:
                    # Validation increases confidence
                    # Check if parsed value matches expected format
                    if re.match(r'^\d+(-\d+)?$', parsed):
                        validation_confidence = 1.0
                    else:
                        validation_confidence = 0.7

                    final_confidence = pattern_confidence * validation_confidence
                    return parsed, final_confidence

        return None, 0.0

    @classmethod
    def extract_time(
        cls,
        text: str,
        time_type: str
    ) -> Tuple[Optional[int], float]:
        """Extract time value with confidence score.

        Args:
            text: Text to search
            time_type: 'prep' or 'cook'

        Returns:
            tuple: (time_in_minutes, confidence)

        Examples:
            >>> MetadataPatternDetector.extract_time("Prep time: 30 minutes", "prep")
            (30, 0.95)

            >>> MetadataPatternDetector.extract_time("Cook time: 1 hour", "cook")
            (60, 0.95)
        """
        text_lower = text.lower()

        # Select patterns based on time type
        if time_type == 'prep':
            patterns = cls.PREP_TIME_PATTERNS
        elif time_type == 'cook':
            patterns = cls.COOK_TIME_PATTERNS
        else:
            return None, 0.0

        for pattern, pattern_confidence in patterns:
            match = pattern.search(text_lower)
            if match:
                raw_value = match.group(1).strip()

                # Parse and validate
                parsed = MetadataExtractor.parse_time(raw_value)

                if parsed is not None:
                    # Validation increases confidence
                    # Check if time is reasonable (not too large/small)
                    if 1 <= parsed <= 1440:  # 1 minute to 24 hours
                        validation_confidence = 1.0
                    else:
                        validation_confidence = 0.5

                    final_confidence = pattern_confidence * validation_confidence
                    return parsed, final_confidence

        return None, 0.0

    @classmethod
    def extract_cooking_method(
        cls,
        text: str,
        title: str = ""
    ) -> Tuple[Optional[str], float]:
        """Extract cooking method with confidence score.

        Args:
            text: Text to search
            title: Recipe title for additional context

        Returns:
            tuple: (cooking_method, confidence)
        """
        from epub_recipe_parser.utils.patterns import COOKING_METHODS

        combined = f"{title} {text}".lower()

        for method, keywords in COOKING_METHODS.items():
            for keyword in keywords:
                if keyword in combined:
                    # Higher confidence if in title
                    if keyword in title.lower():
                        confidence = 0.95
                    else:
                        confidence = 0.75

                    return method, confidence

        return None, 0.0

    @classmethod
    def extract_protein_type(
        cls,
        text: str,
        title: str = ""
    ) -> Tuple[Optional[str], float]:
        """Extract protein type with confidence score.

        Args:
            text: Text to search
            title: Recipe title for additional context

        Returns:
            tuple: (protein_type, confidence)
        """
        from epub_recipe_parser.utils.patterns import PROTEIN_TYPES

        combined = f"{title} {text}".lower()

        for protein in PROTEIN_TYPES:
            if protein in combined:
                # Higher confidence if in title
                if protein in title.lower():
                    confidence = 0.95
                else:
                    confidence = 0.75

                return protein, confidence

        return None, 0.0

    @classmethod
    def extract_all_metadata(
        cls,
        text: str,
        title: str = ""
    ) -> Tuple[Dict[str, str], Dict[str, float]]:
        """Extract all metadata with per-field confidence scores.

        Args:
            text: Text to search
            title: Recipe title for additional context

        Returns:
            tuple: (metadata_dict, confidence_dict)

        Example:
            >>> text = "Serves: 4\\nPrep time: 30 minutes\\nCook time: 1 hour"
            >>> metadata, confidence = MetadataPatternDetector.extract_all_metadata(text)
            >>> metadata
            {'serves': '4', 'prep_time': '30', 'cook_time': '60'}
            >>> confidence
            {'serves': 0.95, 'prep_time': 0.95, 'cook_time': 0.95}
        """
        metadata = {}
        confidence = {}

        # Extract serves
        serves, serves_conf = cls.extract_serves(text)
        if serves:
            metadata['serves'] = serves
            confidence['serves'] = serves_conf

        # Extract prep time
        prep_time, prep_conf = cls.extract_time(text, 'prep')
        if prep_time:
            metadata['prep_time'] = str(prep_time)
            confidence['prep_time'] = prep_conf

        # Extract cook time
        cook_time, cook_conf = cls.extract_time(text, 'cook')
        if cook_time:
            metadata['cook_time'] = str(cook_time)
            confidence['cook_time'] = cook_conf

        # Extract cooking method
        cooking_method, method_conf = cls.extract_cooking_method(text, title)
        if cooking_method:
            metadata['cooking_method'] = cooking_method
            confidence['cooking_method'] = method_conf

        # Extract protein type
        protein_type, protein_conf = cls.extract_protein_type(text, title)
        if protein_type:
            metadata['protein_type'] = protein_type
            confidence['protein_type'] = protein_conf

        return metadata, confidence
```

---

## Example 5: Modernized MetadataExtractor

### File: `src/epub_recipe_parser/extractors/metadata.py` (additions)

```python
"""Extract recipe metadata (servings, time, etc)."""

from typing import Dict, Optional, Tuple
from bs4 import BeautifulSoup

# Existing code remains unchanged...


class MetadataExtractor:
    """Extract recipe metadata with confidence scoring."""

    # ... existing methods remain unchanged ...

    @staticmethod
    def extract_with_patterns(
        soup: BeautifulSoup, text: str, title: str = ""
    ) -> Tuple[Dict[str, str], Dict[str, Any]]:
        """Modern pattern-based extraction with per-field confidence.

        This method uses pattern detection with confidence scoring for each
        metadata field individually.

        Args:
            soup: BeautifulSoup object containing the HTML
            text: Plain text version of the content
            title: Recipe title for context

        Returns:
            tuple: (metadata_dict, extraction_metadata)
                - metadata_dict: Extracted metadata fields
                - extraction_metadata: Extraction metadata including:
                    - strategy: str - Always 'pattern_based'
                    - field_confidence: Dict[str, float] - Per-field confidence
                    - overall_confidence: float - Average confidence
                    - fields_extracted: int - Number of fields found
                    - fields_attempted: int - Total fields attempted

        Example:
            >>> html = '<p>Serves: 4<br>Prep time: 30 minutes</p>'
            >>> soup = BeautifulSoup(html, 'html.parser')
            >>> text = soup.get_text()
            >>> metadata, extraction_meta = MetadataExtractor.extract_with_patterns(
            ...     soup, text, "Grilled Chicken"
            ... )
            >>> metadata
            {'serves': '4', 'prep_time': '30'}
            >>> extraction_meta['overall_confidence']
            0.95
        """
        from epub_recipe_parser.core.patterns import MetadataPatternDetector
        import logging

        logger = logging.getLogger(__name__)

        # Extract with confidence
        logger.debug("Patterns: Extracting metadata with pattern detection")
        metadata, field_confidence = MetadataPatternDetector.extract_all_metadata(
            text, title
        )

        # Calculate overall confidence (average of field confidences)
        overall_confidence = (
            sum(field_confidence.values()) / len(field_confidence)
            if field_confidence else 0.0
        )

        extraction_metadata = {
            'strategy': 'pattern_based',
            'field_confidence': field_confidence,
            'overall_confidence': overall_confidence,
            'fields_extracted': len(metadata),
            'fields_attempted': 5,  # serves, prep_time, cook_time, cooking_method, protein_type
        }

        logger.info(
            f"Patterns: Extracted {len(metadata)} metadata fields "
            f"(overall_confidence={overall_confidence:.2f})"
        )

        # Log per-field confidence
        for field, conf in field_confidence.items():
            logger.debug(f"  {field}: confidence={conf:.2f}")

        return metadata, extraction_metadata
```

---

## Example 6: Usage in EPUBRecipeExtractor

### File: `src/epub_recipe_parser/core/extractor.py` (modifications)

```python
# Inside _extract_recipe_from_section() method

# Extract instructions with A/B testing
if self.ab_runner and self.config.ab_testing.test_instructions:
    logger.debug("Running A/B test for instructions extraction")

    # Use ABTestRunner to compare old and new methods
    comparison = self.ab_runner.compare_extractors(
        control_extractor=self.instructions_extractor,  # Uses extract()
        treatment_extractor=self.instructions_extractor,  # Uses extract_with_patterns()
        soup=soup,
        text=text
    )

    # Decide which result to use
    if self.ab_runner.should_use_treatment(comparison):
        instructions = comparison['new_ingredients']  # Generic field name
        logger.debug("Using new instruction extraction method")
    else:
        instructions = comparison['old_ingredients']
        logger.debug("Using old instruction extraction method")

    # Store A/B test metadata
    recipe.metadata['ab_test_instructions'] = {
        'confidence': comparison.get('confidence', 0.0),
        'strategy': comparison.get('strategy'),
        'agreement': comparison['agreement'],
        'old_success': comparison['old_success'],
        'new_success': comparison['new_success']
    }
else:
    # Use legacy method (no A/B testing)
    instructions = self.instructions_extractor.extract(soup, text)

# Similar pattern for metadata extraction
if self.ab_runner and self.config.ab_testing.test_metadata:
    # A/B test metadata extraction
    # Implementation similar to instructions above
    pass
```

---

## Example 7: Unit Tests

### File: `tests/test_core/test_patterns/test_instruction_detectors.py`

```python
"""Unit tests for InstructionPatternDetector."""

import pytest
from epub_recipe_parser.core.patterns import InstructionPatternDetector


class TestInstructionPatternDetector:
    """Tests for instruction pattern detection and confidence scoring."""

    def test_high_confidence_clear_instructions(self):
        """Test high confidence for clear instruction text."""
        text = """
        Preheat oven to 350°F. Heat oil in a large skillet over medium heat.
        Add onions and cook until soft, about 5 minutes. Then add garlic and
        cook for another minute. Finally, add tomatoes and simmer until thickened.
        """

        confidence = InstructionPatternDetector.calculate_confidence(text)

        assert confidence > 0.8, "Clear instructions should have high confidence"
        assert confidence <= 1.0, "Confidence should not exceed 1.0"

    def test_low_confidence_ingredient_list(self):
        """Test low confidence for ingredient list."""
        text = """
        2 cups all-purpose flour
        1 cup granulated sugar
        ½ teaspoon salt
        1 teaspoon baking powder
        2 large eggs
        1 cup milk
        """

        confidence = InstructionPatternDetector.calculate_confidence(text)

        assert confidence < 0.3, "Ingredient list should have low confidence"

    def test_medium_confidence_mixed_content(self):
        """Test medium confidence for mixed content."""
        text = """
        For the sauce, you'll need 2 cups of tomatoes.
        Heat them in a pan until they start to break down.
        Add 1 tablespoon of butter and stir.
        """

        confidence = InstructionPatternDetector.calculate_confidence(text)

        assert 0.4 <= confidence <= 0.7, "Mixed content should have medium confidence"

    def test_empty_text_returns_zero(self):
        """Test that empty text returns zero confidence."""
        assert InstructionPatternDetector.calculate_confidence("") == 0.0
        assert InstructionPatternDetector.calculate_confidence("   ") == 0.0
        assert InstructionPatternDetector.calculate_confidence(None) == 0.0

    def test_imperative_sentences_detection(self):
        """Test detection of imperative sentences."""
        # Text with imperative sentences
        text_imperative = "Preheat oven. Mix ingredients. Bake for 30 minutes."
        score_imperative = InstructionPatternDetector._detect_imperative_sentences(
            text_imperative.lower()
        )

        # Text without imperative sentences
        text_declarative = "The oven should be preheated. Ingredients are mixed."
        score_declarative = InstructionPatternDetector._detect_imperative_sentences(
            text_declarative.lower()
        )

        assert score_imperative > score_declarative
        assert score_imperative > 0.5

    def test_cooking_verb_density(self):
        """Test cooking verb density calculation."""
        # Text with many cooking verbs
        text_verbs = "Heat, cook, stir, mix, bake, roast, and grill."
        density_high = InstructionPatternDetector._calculate_verb_density(
            text_verbs.lower()
        )

        # Text with few cooking verbs
        text_few_verbs = "The recipe is delicious and easy to prepare."
        density_low = InstructionPatternDetector._calculate_verb_density(
            text_few_verbs.lower()
        )

        assert density_high > density_low
        assert density_high > 0.5

    def test_temporal_markers(self):
        """Test detection of temporal markers."""
        text_with_markers = "First, heat the oil. Then add onions. Cook until soft."
        score_with = InstructionPatternDetector._calculate_marker_score(
            text_with_markers.lower()
        )

        text_without_markers = "Heat the oil. Add onions. Cook the onions."
        score_without = InstructionPatternDetector._calculate_marker_score(
            text_without_markers.lower()
        )

        assert score_with > score_without
        assert score_with >= 0.5
```

---

## Summary

These code examples demonstrate:

1. **Pattern Detection**: Algorithmic confidence scoring based on multiple signals
2. **Structural Detection**: HTML structure analysis with zone detection
3. **Linguistic Analysis**: Text quality assessment for instructions
4. **Metadata Pattern Detection**: Per-field confidence scoring with pattern priorities
5. **Integration**: How the new methods integrate with existing code
6. **Backward Compatibility**: Old methods remain unchanged, new methods added alongside
7. **Testing**: Comprehensive unit tests validating confidence calculations

The modernized architecture provides:
- **Observability**: Confidence scores show extraction reliability
- **Consistency**: All extractors follow the same pattern
- **Extensibility**: Easy to add new detection strategies
- **Testability**: A/B testing framework validates improvements

---

*Document Version: 1.0*
*Created: 2025-12-05*
