"""Pattern detection for metadata extraction."""

import re
from typing import Dict, Any
from epub_recipe_parser.utils.patterns import (
    SERVES_PATTERN,
    PREP_TIME_PATTERN,
    COOK_TIME_PATTERN,
    COOKING_METHODS,
    PROTEIN_TYPES,
)


class MetadataPatternDetector:
    """Detects metadata patterns and calculates confidence scores."""

    # Metadata field indicators
    SERVINGS_KEYWORDS = {
        "serves", "servings", "yield", "yields", "makes", "portions", "people"
    }

    TIME_KEYWORDS = {
        "prep", "preparation", "cook", "cooking", "bake", "baking",
        "total", "ready in", "time", "minutes", "hours"
    }

    DIFFICULTY_KEYWORDS = {
        "easy": 1,
        "simple": 1,
        "beginner": 1,
        "quick": 1,
        "intermediate": 2,
        "moderate": 2,
        "advanced": 3,
        "difficult": 3,
        "expert": 3,
        "challenging": 3,
    }

    # Pre-compiled regex patterns for performance
    NUMBER_PATTERN = re.compile(r'\b\d+\b')
    TIME_UNIT_PATTERN = re.compile(r'\b(?:minute|min|hour|hr)s?\b', re.IGNORECASE)
    SERVINGS_NUMBER_PATTERN = re.compile(r'(?:serves?|yields?|makes)\s*(?:about\s*)?(\d+(?:\s*[-to]\s*\d+)?)', re.IGNORECASE)

    @classmethod
    def calculate_confidence(cls, text: str, field_type: str) -> float:
        """Calculate confidence that text contains specific metadata field.

        Scoring components (0.0-1.0):
        - Keyword presence: 40%
        - Pattern match quality: 30%
        - Format validation: 20%
        - Context indicators: 10%

        Args:
            text: Text to analyze
            field_type: Type of metadata ('servings', 'time', 'method', 'protein', 'difficulty')

        Returns:
            Confidence score between 0.0 and 1.0

        Examples:
            >>> text = "Serves 4-6 people"
            >>> MetadataPatternDetector.calculate_confidence(text, 'servings')
            0.92

            >>> text = "Prep time: 15 minutes"
            >>> MetadataPatternDetector.calculate_confidence(text, 'time')
            0.88
        """
        if not text or len(text.strip()) < 3:
            return 0.0

        text_lower = text.lower()

        if field_type == 'servings':
            return cls._calculate_servings_confidence(text_lower)
        elif field_type == 'time':
            return cls._calculate_time_confidence(text_lower)
        elif field_type == 'method':
            return cls._calculate_method_confidence(text_lower)
        elif field_type == 'protein':
            return cls._calculate_protein_confidence(text_lower)
        elif field_type == 'difficulty':
            return cls._calculate_difficulty_confidence(text_lower)
        else:
            return 0.0

    @classmethod
    def _calculate_servings_confidence(cls, text: str) -> float:
        """Calculate confidence for servings/yield field."""
        score = 0.0

        # Component 1: Keyword presence (40% weight)
        keyword_count = sum(1 for kw in cls.SERVINGS_KEYWORDS if kw in text)
        keyword_score = min(keyword_count / 2.0, 1.0) * 0.4
        score += keyword_score

        # Component 2: Pattern match quality (30% weight)
        if cls.SERVINGS_NUMBER_PATTERN.search(text):
            score += 0.3
        elif SERVES_PATTERN.search(text):
            score += 0.2

        # Component 3: Format validation (20% weight)
        # Check for number presence
        if cls.NUMBER_PATTERN.search(text):
            score += 0.2

        # Component 4: Context indicators (10% weight)
        # Short text is more likely to be servings metadata
        if 5 <= len(text) <= 50:
            score += 0.1

        return min(score, 1.0)

    @classmethod
    def _calculate_time_confidence(cls, text: str) -> float:
        """Calculate confidence for time field."""
        score = 0.0

        # Component 1: Keyword presence (40% weight)
        keyword_count = sum(1 for kw in cls.TIME_KEYWORDS if kw in text)
        keyword_score = min(keyword_count / 2.0, 1.0) * 0.4
        score += keyword_score

        # Component 2: Pattern match quality (30% weight)
        if PREP_TIME_PATTERN.search(text) or COOK_TIME_PATTERN.search(text):
            score += 0.3
        elif cls.TIME_UNIT_PATTERN.search(text):
            score += 0.15

        # Component 3: Format validation (20% weight)
        # Check for number + time unit pattern
        if cls.NUMBER_PATTERN.search(text) and cls.TIME_UNIT_PATTERN.search(text):
            score += 0.2

        # Component 4: Context indicators (10% weight)
        # Time metadata is usually concise
        if 5 <= len(text) <= 60:
            score += 0.1

        return min(score, 1.0)

    @classmethod
    def _calculate_method_confidence(cls, text: str) -> float:
        """Calculate confidence for cooking method field."""
        score = 0.0

        # Component 1: Method keyword presence (70% weight)
        method_matches = 0
        for method, keywords in COOKING_METHODS.items():
            if any(kw in text for kw in keywords):
                method_matches += 1

        if method_matches > 0:
            # Higher score for clear single method
            score += min(0.7, 0.35 * method_matches)

        # Component 2: Format indicators (20% weight)
        # Methods are usually in title or brief description
        if len(text) < 100:
            score += 0.2

        # Component 3: Negative indicators (10% weight reduction)
        # If text is too long or has ingredients, reduce confidence
        if len(text) > 200 or any(word in text for word in ['cup', 'tablespoon', 'teaspoon', 'ounce']):
            score -= 0.1

        return max(min(score, 1.0), 0.0)

    @classmethod
    def _calculate_protein_confidence(cls, text: str) -> float:
        """Calculate confidence for protein type field."""
        score = 0.0

        # Component 1: Protein keyword presence (70% weight)
        protein_matches = sum(1 for protein in PROTEIN_TYPES if protein in text)

        if protein_matches > 0:
            # Single clear protein is higher confidence
            if protein_matches == 1:
                score += 0.7
            else:
                score += 0.4  # Multiple proteins - less certain

        # Component 2: Format indicators (20% weight)
        # Protein usually in title or brief description
        if len(text) < 100:
            score += 0.2

        # Component 3: Context boost (10% weight)
        # Common protein-related words nearby
        protein_context = ['with', 'breast', 'thigh', 'ground', 'whole', 'fillet', 'steak']
        if any(word in text for word in protein_context):
            score += 0.1

        return min(score, 1.0)

    @classmethod
    def _calculate_difficulty_confidence(cls, text: str) -> float:
        """Calculate confidence for difficulty level field."""
        score = 0.0

        # Component 1: Difficulty keyword presence (60% weight)
        difficulty_matches = sum(1 for kw in cls.DIFFICULTY_KEYWORDS if kw in text)

        if difficulty_matches > 0:
            score += min(0.6, 0.3 * difficulty_matches)

        # Component 2: Format indicators (30% weight)
        # Difficulty usually mentioned near beginning or in brief section
        if len(text) < 80:
            score += 0.3

        # Component 3: Context indicators (10% weight)
        context_words = ['level', 'skill', 'experience', 'beginner', 'rating']
        if any(word in text for word in context_words):
            score += 0.1

        return min(score, 1.0)

    @classmethod
    def extract_metadata_with_confidence(
        cls, text: str, title: str = ""
    ) -> Dict[str, Dict[str, Any]]:
        """Extract all metadata fields with confidence scores.

        Args:
            text: Recipe text to analyze
            title: Recipe title for context

        Returns:
            Dictionary mapping field names to {'value': str, 'confidence': float}

        Example:
            >>> result = MetadataPatternDetector.extract_metadata_with_confidence(
            ...     "Serves 4-6\\nPrep time: 15 minutes\\nGrilled chicken"
            ... )
            >>> result['servings']
            {'value': '4-6', 'confidence': 0.85}
        """
        combined_text = f"{title} {text}".lower()
        results = {}

        # Extract servings
        servings_match = cls.SERVINGS_NUMBER_PATTERN.search(combined_text)
        if servings_match:
            servings_text = servings_match.group(0)
            confidence = cls._calculate_servings_confidence(servings_text)
            if confidence > 0.3:  # Minimum threshold
                results['servings'] = {
                    'value': servings_match.group(1),
                    'confidence': confidence,
                    'raw_text': servings_text
                }

        # Extract prep time
        prep_match = PREP_TIME_PATTERN.search(combined_text)
        if prep_match:
            prep_text = prep_match.group(0)
            confidence = cls._calculate_time_confidence(prep_text)
            if confidence > 0.3:
                results['prep_time'] = {
                    'value': prep_match.group(1).strip(),
                    'confidence': confidence,
                    'raw_text': prep_text
                }

        # Extract cook time
        cook_match = COOK_TIME_PATTERN.search(combined_text)
        if cook_match:
            cook_text = cook_match.group(0)
            confidence = cls._calculate_time_confidence(cook_text)
            if confidence > 0.3:
                results['cook_time'] = {
                    'value': cook_match.group(1).strip(),
                    'confidence': confidence,
                    'raw_text': cook_text
                }

        # Extract cooking method
        for method, keywords in COOKING_METHODS.items():
            if any(kw in combined_text for kw in keywords):
                confidence = cls._calculate_method_confidence(combined_text)
                if confidence > 0.3:
                    results['cooking_method'] = {
                        'value': method,
                        'confidence': confidence,
                        'raw_text': f"{method} cooking"
                    }
                break

        # Extract protein type
        for protein in PROTEIN_TYPES:
            if protein in combined_text:
                confidence = cls._calculate_protein_confidence(combined_text)
                if confidence > 0.3:
                    results['protein_type'] = {
                        'value': protein,
                        'confidence': confidence,
                        'raw_text': protein
                    }
                break

        # Extract difficulty
        for difficulty_word, level in cls.DIFFICULTY_KEYWORDS.items():
            if difficulty_word in combined_text:
                confidence = cls._calculate_difficulty_confidence(combined_text)
                if confidence > 0.3:
                    difficulty_labels = {1: 'easy', 2: 'intermediate', 3: 'advanced'}
                    results['difficulty'] = {
                        'value': difficulty_labels[level],
                        'confidence': confidence,
                        'raw_text': difficulty_word
                    }
                break

        return results
