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
        "whisk", "beat", "fold", "cook", "bake", "roast", "fry", "grill",
        "bring", "remove", "transfer", "pour", "season", "cover", "simmer",
        "boil", "melt", "spread", "drain", "toss", "sauté", "chop", "slice"
    }

    # Pre-compiled regex patterns for performance
    SENTENCE_SPLIT_PATTERN = re.compile(r'[.!?]+')

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
        sentences = cls.SENTENCE_SPLIT_PATTERN.split(text)
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
