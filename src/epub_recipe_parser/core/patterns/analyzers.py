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


class MetadataLinguisticAnalyzer:
    """Performs linguistic analysis specifically for metadata text.

    This analyzer complements MetadataPatternDetector by focusing on
    linguistic quality indicators for recipe metadata.
    """

    # Metadata-specific keywords
    METADATA_KEYWORDS = {
        "serves", "servings", "yield", "yields", "makes", "portions",
        "prep", "preparation", "cook", "cooking", "bake", "baking",
        "time", "minutes", "hours", "total", "ready",
        "difficulty", "easy", "medium", "hard", "skill", "level"
    }

    # Numeric patterns for metadata
    NUMBER_INDICATORS = {
        "digit_count": re.compile(r'\d'),
        "time_unit": re.compile(r'\b(?:minute|min|hour|hr)s?\b', re.IGNORECASE),
        "range_pattern": re.compile(r'\d+\s*[-to]\s*\d+'),
    }

    # Narrative indicators (negative for metadata)
    NARRATIVE_WORDS = {
        "the", "then", "when", "after", "before", "until", "while",
        "you", "your", "will", "should", "can", "may", "this", "that"
    }

    @staticmethod
    def calculate_metadata_score(text: str) -> float:
        """Calculate linguistic quality score for metadata text.

        This score measures how well the text exhibits linguistic patterns
        typical of recipe metadata (concise, numeric, keyword-rich).

        Args:
            text: Text to analyze

        Returns:
            Linguistic score between 0.0 and 1.0

        Examples:
            >>> text = "Serves 4-6 | Prep: 15 minutes | Cook: 30 minutes"
            >>> MetadataLinguisticAnalyzer.calculate_metadata_score(text)
            0.92

            >>> text = "This recipe will serve you and your family well..."
            >>> MetadataLinguisticAnalyzer.calculate_metadata_score(text)
            0.15
        """
        if not text or len(text.strip()) < 3:
            return 0.0

        text_lower = text.lower()

        score = 0.0

        # Component 1: Metadata keyword presence (35% weight)
        keyword_score = MetadataLinguisticAnalyzer._calculate_keyword_presence(text_lower)
        score += keyword_score * 0.35

        # Component 2: Numeric content (30% weight)
        numeric_score = MetadataLinguisticAnalyzer._calculate_numeric_score(text_lower)
        score += numeric_score * 0.30

        # Component 3: Conciseness (20% weight)
        conciseness_score = MetadataLinguisticAnalyzer._check_conciseness(text)
        score += conciseness_score * 0.20

        # Component 4: Absence of narrative (15% weight)
        narrative_score = MetadataLinguisticAnalyzer._check_narrative_absence(text_lower)
        score += narrative_score * 0.15

        return max(0.0, min(score, 1.0))

    @staticmethod
    def _calculate_keyword_presence(text: str) -> float:
        """Calculate metadata keyword presence score.

        Args:
            text: Lowercase text

        Returns:
            Score 0.0-1.0 based on metadata keyword frequency
        """
        words = text.split()
        if not words:
            return 0.0

        keyword_count = sum(
            1 for word in words
            if word.rstrip(',.;:!?') in MetadataLinguisticAnalyzer.METADATA_KEYWORDS
        )

        # Calculate keyword frequency per 10 words
        keyword_frequency = (keyword_count / len(words)) * 10

        # Optimal range: 1-3 keywords per 10 words for metadata
        if 1 <= keyword_frequency <= 3:
            return 1.0
        elif keyword_frequency < 1:
            return keyword_frequency
        elif 3 < keyword_frequency <= 5:
            return 1.0 - ((keyword_frequency - 3) / 4.0)
        else:
            return 0.0

    @staticmethod
    def _calculate_numeric_score(text: str) -> float:
        """Calculate numeric content score.

        Metadata typically contains numbers (servings, times).

        Args:
            text: Lowercase text

        Returns:
            Score 0.0-1.0 based on numeric content
        """
        score = 0.0

        # Check for digit presence
        digit_matches = MetadataLinguisticAnalyzer.NUMBER_INDICATORS['digit_count'].findall(text)
        if digit_matches:
            # More digits generally better for metadata (up to a point)
            digit_count = len(digit_matches)
            if 1 <= digit_count <= 8:
                score += 0.4
            elif digit_count > 8:
                score += 0.2  # Too many digits might be ingredients

        # Check for time units
        if MetadataLinguisticAnalyzer.NUMBER_INDICATORS['time_unit'].search(text):
            score += 0.3

        # Check for range patterns (e.g., "4-6")
        if MetadataLinguisticAnalyzer.NUMBER_INDICATORS['range_pattern'].search(text):
            score += 0.3

        return min(score, 1.0)

    @staticmethod
    def _check_conciseness(text: str) -> float:
        """Check if text is concise (metadata is typically brief).

        Args:
            text: Text to check

        Returns:
            Score 0.0-1.0 based on conciseness
        """
        text_length = len(text)

        # Metadata typically 5-100 characters
        # Very short (<5) or very long (>200) less likely
        if 5 <= text_length <= 100:
            return 1.0
        elif text_length < 5:
            return text_length / 5.0
        elif 100 < text_length <= 200:
            return 1.0 - ((text_length - 100) / 100.0)
        else:
            return 0.0

    @staticmethod
    def _check_narrative_absence(text: str) -> float:
        """Check for absence of narrative words.

        Metadata should not contain narrative/instructional language.

        Args:
            text: Lowercase text

        Returns:
            Score 0.0-1.0 (higher = fewer narrative words)
        """
        words = text.split()
        if not words:
            return 1.0

        # Count narrative words
        narrative_count = sum(
            1 for word in words
            if word.rstrip(',.;:!?') in MetadataLinguisticAnalyzer.NARRATIVE_WORDS
        )

        narrative_ratio = narrative_count / len(words)

        # Metadata should have very few narrative words
        # <10% = excellent, >30% = poor
        if narrative_ratio < 0.1:
            return 1.0
        elif narrative_ratio < 0.3:
            return 1.0 - ((narrative_ratio - 0.1) / 0.2)
        else:
            return 0.0


class IngredientLinguisticAnalyzer:
    """Performs linguistic analysis specifically for ingredient text.

    This analyzer complements IngredientPatternDetector by focusing on
    linguistic quality indicators for recipe ingredients.
    """

    # Ingredient-specific descriptors and modifiers
    INGREDIENT_DESCRIPTORS = {
        "fresh", "dried", "frozen", "canned", "fresh-squeezed",
        "chopped", "diced", "minced", "sliced", "grated", "shredded",
        "peeled", "crushed", "ground", "whole", "halved", "quartered",
        "large", "medium", "small", "jumbo", "extra-large",
        "ripe", "unripe", "tender", "crisp", "firm", "soft",
        "organic", "kosher", "sea", "extra-virgin",
        "unsalted", "salted", "sweetened", "unsweetened"
    }

    # Common ingredient nouns
    INGREDIENT_NOUNS = {
        "salt", "pepper", "oil", "butter", "flour", "sugar", "egg", "eggs",
        "milk", "water", "cream", "cheese", "onion", "garlic", "chicken",
        "beef", "pork", "fish", "tomato", "potato", "carrot", "lemon", "lime"
    }

    # Measurement indicators (positive for ingredients)
    MEASUREMENT_WORDS = {
        "cup", "cups", "tablespoon", "tbsp", "teaspoon", "tsp",
        "ounce", "oz", "pound", "lb", "gram", "g", "kilogram", "kg",
        "pinch", "dash", "clove", "piece"
    }

    # Cooking verbs (negative for ingredients)
    COOKING_VERBS = {
        "preheat", "heat", "cook", "bake", "roast", "fry", "grill",
        "mix", "stir", "combine", "whisk", "beat", "fold",
        "bring", "remove", "transfer", "pour", "serve"
    }

    # Pre-compiled patterns
    LIST_MARKER_PATTERN = re.compile(r'^[\s•\-*·○●]\s*|\d+\.\s*')

    @staticmethod
    def calculate_ingredient_score(text: str) -> float:
        """Calculate linguistic quality score for ingredient text.

        This score measures how well the text exhibits linguistic patterns
        typical of ingredient lists (measurements, descriptors, concise format).

        Args:
            text: Text to analyze

        Returns:
            Linguistic score between 0.0 and 1.0

        Examples:
            >>> text = "2 cups flour\\n1 tsp salt\\n3 large eggs, beaten"
            >>> IngredientLinguisticAnalyzer.calculate_ingredient_score(text)
            0.88

            >>> text = "Preheat oven to 350°F. Mix all ingredients together."
            >>> IngredientLinguisticAnalyzer.calculate_ingredient_score(text)
            0.18
        """
        if not text or len(text.strip()) < 10:
            return 0.0

        text_lower = text.lower()
        lines = [line.strip() for line in text.split("\n") if line.strip()]

        if not lines:
            return 0.0

        score = 0.0

        # Component 1: Descriptor presence (30% weight)
        descriptor_score = IngredientLinguisticAnalyzer._calculate_descriptor_score(text_lower)
        score += descriptor_score * 0.30

        # Component 2: Measurement word presence (25% weight)
        measurement_score = IngredientLinguisticAnalyzer._calculate_measurement_presence(text_lower)
        score += measurement_score * 0.25

        # Component 3: Line structure quality (20% weight)
        structure_score = IngredientLinguisticAnalyzer._analyze_line_structure(lines)
        score += structure_score * 0.20

        # Component 4: Ingredient noun presence (15% weight)
        noun_score = IngredientLinguisticAnalyzer._calculate_noun_presence(text_lower)
        score += noun_score * 0.15

        # Component 5: Absence of cooking verbs (10% weight)
        verb_score = IngredientLinguisticAnalyzer._check_verb_absence(text_lower)
        score += verb_score * 0.10

        return max(0.0, min(score, 1.0))

    @staticmethod
    def _calculate_descriptor_score(text: str) -> float:
        """Calculate ingredient descriptor presence score.

        Args:
            text: Lowercase text

        Returns:
            Score 0.0-1.0 based on descriptor frequency
        """
        words = text.split()
        if not words:
            return 0.0

        descriptor_count = sum(
            1 for word in words
            if word.rstrip(',.;:!?') in IngredientLinguisticAnalyzer.INGREDIENT_DESCRIPTORS
        )

        # Calculate descriptor frequency per 20 words
        descriptor_frequency = (descriptor_count / len(words)) * 20

        # Optimal range: 1-4 descriptors per 20 words
        if 1 <= descriptor_frequency <= 4:
            return 1.0
        elif descriptor_frequency < 1:
            return descriptor_frequency
        elif 4 < descriptor_frequency <= 6:
            return 1.0 - ((descriptor_frequency - 4) / 4.0)
        else:
            return 0.0

    @staticmethod
    def _calculate_measurement_presence(text: str) -> float:
        """Calculate measurement word presence score.

        Args:
            text: Lowercase text

        Returns:
            Score 0.0-1.0 based on measurement word presence
        """
        words = text.split()
        if not words:
            return 0.0

        measurement_count = sum(
            1 for word in words
            if word.rstrip(',.;:!?s') in IngredientLinguisticAnalyzer.MEASUREMENT_WORDS
        )

        # Calculate measurement frequency per 10 words
        measurement_frequency = (measurement_count / len(words)) * 10

        # Optimal range: 0.5-3 measurements per 10 words
        if 0.5 <= measurement_frequency <= 3:
            return 1.0
        elif measurement_frequency < 0.5:
            return measurement_frequency / 0.5
        elif 3 < measurement_frequency <= 5:
            return 1.0 - ((measurement_frequency - 3) / 4.0)
        else:
            return 0.0

    @staticmethod
    def _analyze_line_structure(lines: list) -> float:
        """Analyze ingredient line structure quality.

        Ingredients typically have:
        - Short to medium lines (20-100 chars)
        - Consistent length across lines
        - List markers

        Args:
            lines: List of text lines

        Returns:
            Score 0.0-1.0 based on line structure
        """
        if not lines:
            return 0.0

        score = 0.0

        # Check line length distribution
        ideal_length_count = sum(1 for line in lines if 20 <= len(line) <= 100)
        length_ratio = ideal_length_count / len(lines)
        score += length_ratio * 0.4

        # Check for list markers
        marker_count = sum(
            1 for line in lines
            if IngredientLinguisticAnalyzer.LIST_MARKER_PATTERN.match(line)
        )
        marker_ratio = marker_count / len(lines)
        score += marker_ratio * 0.3

        # Check line count (ingredients usually 3+ items)
        if len(lines) >= 3:
            score += 0.3
        elif len(lines) == 2:
            score += 0.15

        return min(score, 1.0)

    @staticmethod
    def _calculate_noun_presence(text: str) -> float:
        """Calculate ingredient noun presence score.

        Args:
            text: Lowercase text

        Returns:
            Score 0.0-1.0 based on ingredient noun presence
        """
        words = text.split()
        if not words:
            return 0.0

        noun_count = sum(
            1 for noun in IngredientLinguisticAnalyzer.INGREDIENT_NOUNS
            if noun in text
        )

        # Normalize by text length
        # More nouns per 100 chars = higher score
        density = (noun_count / len(text)) * 100

        if density >= 2.0:
            return 1.0
        elif density >= 1.0:
            return 0.75
        elif density >= 0.5:
            return 0.50
        else:
            return density

    @staticmethod
    def _check_verb_absence(text: str) -> float:
        """Check for absence of cooking verbs (indicator it's NOT instructions).

        Args:
            text: Lowercase text

        Returns:
            Score 0.0-1.0 (higher = fewer cooking verbs)
        """
        verb_count = sum(
            1 for verb in IngredientLinguisticAnalyzer.COOKING_VERBS
            if f" {verb} " in f" {text} "  # Word boundary check
        )

        # Ingredients should have minimal cooking verbs
        if verb_count == 0:
            return 1.0
        elif verb_count == 1:
            return 0.6
        elif verb_count == 2:
            return 0.3
        else:
            return 0.0
