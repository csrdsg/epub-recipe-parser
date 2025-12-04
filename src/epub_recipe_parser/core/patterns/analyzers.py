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
