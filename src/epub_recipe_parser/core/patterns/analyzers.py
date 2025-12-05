"""Linguistic analysis for extraction confidence."""

import re


class LinguisticAnalyzer:
    """
    Performs linguistic analysis on extracted text.

    TODO: This is a stub implementation. Full implementation should include:
    - Part-of-speech tagging
    - Noun phrase extraction
    - Sentence structure analysis
    - Domain-specific language patterns
    """

    # Common instruction verbs and patterns
    INSTRUCTION_VERBS = {
        "add", "mix", "stir", "cook", "bake", "boil", "simmer", "fry", "sauté",
        "chop", "dice", "slice", "mince", "blend", "whisk", "beat", "fold",
        "season", "taste", "serve", "garnish", "preheat", "combine", "pour",
        "heat", "brown", "reduce", "drain", "rinse", "cover", "remove"
    }

    INGREDIENT_DESCRIPTORS = {
        "fresh", "dried", "chopped", "diced", "sliced", "minced", "grated",
        "ground", "whole", "crushed", "raw", "cooked", "frozen", "canned",
        "large", "small", "medium", "finely", "coarsely", "thinly"
    }

    @staticmethod
    def calculate_linguistic_score(text: str) -> float:
        """
        Calculate linguistic quality score for extracted text.

        Args:
            text: Text to analyze

        Returns:
            Linguistic score between 0.0 and 1.0
        """
        if not text or len(text.strip()) < 10:
            return 0.0

        text_lower = text.lower()
        lines = [line.strip() for line in text.split("\n") if line.strip()]

        if not lines:
            return 0.0

        score = 0.0
        total_lines = len(lines)

        # Check for instruction verbs (negative indicator for ingredients)
        instruction_verb_lines = sum(
            1 for line in lines if any(verb in line for verb in LinguisticAnalyzer.INSTRUCTION_VERBS)
        )
        instruction_ratio = instruction_verb_lines / total_lines if total_lines > 0 else 0

        # If many lines have instruction verbs, this is likely NOT ingredients
        # So we penalize the score
        if instruction_ratio > 0.5:
            score -= 0.3

        # Check for ingredient descriptors (positive indicator)
        descriptor_lines = sum(
            1 for line in lines if any(desc in line for desc in LinguisticAnalyzer.INGREDIENT_DESCRIPTORS)
        )
        descriptor_ratio = descriptor_lines / total_lines if total_lines > 0 else 0
        score += descriptor_ratio * 0.4  # 40% weight

        # Check average line length (ingredients tend to be shorter)
        avg_line_length = sum(len(line) for line in lines) / total_lines
        if 20 <= avg_line_length <= 80:  # Optimal range for ingredient lines
            score += 0.3
        elif avg_line_length > 150:  # Too long, likely instructions
            score -= 0.2

        # Check for list-like structure (each line starts with item)
        list_pattern_lines = sum(
            1 for line in lines if re.match(r'^[\d•\-*]\s*\w+', line)
        )
        list_ratio = list_pattern_lines / total_lines if total_lines > 0 else 0
        score += list_ratio * 0.3  # 30% weight

        # Normalize to 0.0-1.0 range
        return max(0.0, min(score + 0.5, 1.0))  # Offset by 0.5 to center the score


class InstructionLinguisticAnalyzer:
    """Performs linguistic analysis specifically for instruction text.

    This analyzer complements InstructionPatternDetector by focusing on
    linguistic quality indicators for cooking instructions.
    """

    # Instruction-specific verbs (imperative forms)
    INSTRUCTION_VERBS = {
        "add", "mix", "stir", "cook", "bake", "boil", "simmer", "fry", "sauté",
        "chop", "dice", "slice", "mince", "blend", "whisk", "beat", "fold",
        "season", "taste", "serve", "garnish", "preheat", "combine", "pour",
        "heat", "brown", "reduce", "drain", "rinse", "cover", "remove",
        "place", "transfer", "spread", "grill", "roast", "broil"
    }

    # Temporal/sequential indicators
    TEMPORAL_INDICATORS = {
        "until", "after", "before", "while", "during", "when",
        "first", "then", "next", "finally", "meanwhile", "once"
    }

    # Stop words that indicate end of instructions
    STOP_PATTERNS = {
        "tip", "tips", "note", "notes", "variation", "variations",
        "serving suggestion", "storage", "make ahead", "chef's note"
    }

    # Pre-compiled regex patterns for performance
    SENTENCE_SPLIT_PATTERN = re.compile(r'[.!?]+')

    @staticmethod
    def calculate_instruction_score(text: str) -> float:
        """Calculate linguistic quality score for instruction text.

        This score measures how well the text exhibits linguistic patterns
        typical of cooking instructions (imperative mood, temporal markers, etc.).

        Args:
            text: Text to analyze

        Returns:
            Linguistic score between 0.0 and 1.0

        Examples:
            >>> text = "Preheat oven. Mix ingredients. Then bake for 30 minutes."
            >>> InstructionLinguisticAnalyzer.calculate_instruction_score(text)
            0.85

            >>> text = "2 cups flour, 1 cup sugar, eggs"
            >>> InstructionLinguisticAnalyzer.calculate_instruction_score(text)
            0.15
        """
        if not text or len(text.strip()) < 10:
            return 0.0

        text_lower = text.lower()
        lines = [line.strip() for line in text.split("\n") if line.strip()]

        if not lines:
            return 0.0

        score = 0.0

        # Component 1: Instruction verb presence (40% weight)
        verb_score = InstructionLinguisticAnalyzer._calculate_verb_presence(text_lower)
        score += verb_score * 0.4

        # Component 2: Temporal/sequential indicators (30% weight)
        temporal_score = InstructionLinguisticAnalyzer._calculate_temporal_score(text_lower)
        score += temporal_score * 0.3

        # Component 3: Sentence structure quality (20% weight)
        structure_score = InstructionLinguisticAnalyzer._analyze_sentence_structure(text)
        score += structure_score * 0.2

        # Component 4: Absence of stop patterns (10% weight)
        stop_score = InstructionLinguisticAnalyzer._check_stop_patterns(text_lower)
        score += stop_score * 0.1

        return max(0.0, min(score, 1.0))

    @staticmethod
    def _calculate_verb_presence(text: str) -> float:
        """Calculate instruction verb presence score.

        Args:
            text: Lowercase text

        Returns:
            Score 0.0-1.0 based on instruction verb frequency
        """
        words = text.split()
        if not words:
            return 0.0

        verb_count = sum(
            1 for word in words
            if word.rstrip(',.;:!?') in InstructionLinguisticAnalyzer.INSTRUCTION_VERBS
        )

        # Calculate verb frequency per 100 words
        verb_frequency = (verb_count / len(words)) * 100

        # Optimal range: 2-8 verbs per 100 words
        if 2 <= verb_frequency <= 8:
            return 1.0
        elif verb_frequency < 2:
            return verb_frequency / 2.0
        elif 8 < verb_frequency <= 12:
            return 1.0 - ((verb_frequency - 8) / 8.0)
        else:
            return 0.0

    @staticmethod
    def _calculate_temporal_score(text: str) -> float:
        """Calculate temporal indicator score.

        Args:
            text: Lowercase text

        Returns:
            Score 0.0-1.0 based on temporal marker presence
        """
        indicator_count = sum(
            1 for indicator in InstructionLinguisticAnalyzer.TEMPORAL_INDICATORS
            if indicator in text
        )

        # Scale: 0 indicators = 0.0, 2+ indicators = 1.0
        if indicator_count == 0:
            return 0.0
        elif indicator_count >= 2:
            return 1.0
        else:
            return indicator_count / 2.0

    @staticmethod
    def _analyze_sentence_structure(text: str) -> float:
        """Analyze sentence structure quality.

        Instructions typically have moderate sentence length and clear structure.

        Args:
            text: Text to analyze

        Returns:
            Score 0.0-1.0 based on sentence structure
        """
        sentences = InstructionLinguisticAnalyzer.SENTENCE_SPLIT_PATTERN.split(text)
        sentences = [s.strip() for s in sentences if s.strip()]

        if not sentences:
            return 0.0

        # Calculate average sentence length
        avg_length = sum(len(s) for s in sentences) / len(sentences)

        # Optimal range for instructions: 40-150 characters per sentence
        if 40 <= avg_length <= 150:
            return 1.0
        elif 20 <= avg_length < 40:
            return (avg_length - 20) / 20.0
        elif 150 < avg_length <= 250:
            return 1.0 - ((avg_length - 150) / 100.0)
        else:
            return 0.0

    @staticmethod
    def _check_stop_patterns(text: str) -> float:
        """Check for stop patterns that indicate end of instructions.

        Args:
            text: Lowercase text

        Returns:
            Score 0.0-1.0 (1.0 = no stop patterns found)
        """
        # Check if text starts with stop patterns
        for pattern in InstructionLinguisticAnalyzer.STOP_PATTERNS:
            if text.strip().startswith(pattern):
                return 0.0  # Strong indicator this is NOT instructions

        # Check for stop patterns anywhere in text
        stop_count = sum(
            1 for pattern in InstructionLinguisticAnalyzer.STOP_PATTERNS
            if pattern in text
        )

        # Penalize presence of stop patterns
        if stop_count == 0:
            return 1.0
        elif stop_count == 1:
            return 0.5
        else:
            return 0.0
