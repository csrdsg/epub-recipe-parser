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

        assert confidence > 0.7, f"Clear instructions should have high confidence, got {confidence}"
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

        assert confidence < 0.4, f"Ingredient list should have low confidence, got {confidence}"

    def test_medium_confidence_mixed_content(self):
        """Test medium confidence for mixed content."""
        text = """
        For the sauce, you'll need 2 cups of tomatoes.
        Heat them in a pan until they start to break down.
        Add 1 tablespoon of butter and stir.
        """

        confidence = InstructionPatternDetector.calculate_confidence(text)

        assert 0.3 <= confidence <= 0.8, f"Mixed content should have medium confidence, got {confidence}"

    def test_empty_text_returns_zero(self):
        """Test that empty text returns zero confidence."""
        assert InstructionPatternDetector.calculate_confidence("") == 0.0
        assert InstructionPatternDetector.calculate_confidence("   ") == 0.0
        assert InstructionPatternDetector.calculate_confidence(None) == 0.0

    def test_short_text_returns_zero(self):
        """Test that very short text returns zero confidence."""
        assert InstructionPatternDetector.calculate_confidence("Heat.") == 0.0
        assert InstructionPatternDetector.calculate_confidence("Cook") == 0.0

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
        # Realistic instruction text with good verb density
        text_instructions = "Heat the oil in a pan. Add the onions and cook until soft. Stir in garlic and mix well."
        density_high = InstructionPatternDetector._calculate_verb_density(
            text_instructions.lower()
        )

        # Text with few cooking verbs (ingredient-like)
        text_few_verbs = "The recipe is delicious and easy to make for dinner tonight."
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

    def test_paragraph_length_scoring(self):
        """Test paragraph length characteristic scoring."""
        # Optimal length (100-500 chars)
        text_optimal = "Cook the onions until they are soft and translucent. " * 3
        score_optimal = InstructionPatternDetector._check_paragraph_length(text_optimal)

        # Too short
        text_short = "Heat oil."
        score_short = InstructionPatternDetector._check_paragraph_length(text_short)

        # Too long
        text_long = "Cook the ingredients. " * 100
        score_long = InstructionPatternDetector._check_paragraph_length(text_long)

        assert score_optimal > score_short
        assert score_optimal > score_long
        assert score_optimal >= 0.8

    def test_measurement_penalty(self):
        """Test measurement presence penalty calculation."""
        # Few measurements (instructions)
        text_few = """
        Heat the oil in a pan over medium heat.
        Cook the onions until soft.
        Add the tomatoes and simmer.
        """
        score_few = InstructionPatternDetector._calculate_measurement_penalty(text_few)

        # Many measurements (ingredients)
        text_many = """
        2 cups flour
        1 cup sugar
        ½ teaspoon salt
        1 tablespoon butter
        """
        score_many = InstructionPatternDetector._calculate_measurement_penalty(text_many)

        assert score_few > score_many
        assert score_few >= 0.8
        assert score_many <= 0.2

    def test_real_world_instruction_example(self):
        """Test with real-world instruction text."""
        text = """
        Preheat the oven to 375°F. In a large bowl, combine the flour, sugar,
        and baking powder. In a separate bowl, beat the eggs and add the milk.
        Gradually mix the wet ingredients into the dry ingredients until just
        combined. Pour into a greased pan and bake for 25-30 minutes until
        golden brown.
        """

        confidence = InstructionPatternDetector.calculate_confidence(text)

        assert confidence > 0.7, f"Real instruction example should have high confidence, got {confidence}"

    def test_real_world_ingredient_example(self):
        """Test with real-world ingredient text."""
        text = """
        2 cups all-purpose flour
        1 cup granulated sugar
        2 teaspoons baking powder
        ½ teaspoon salt
        3 large eggs
        1 cup whole milk
        ½ cup vegetable oil
        """

        confidence = InstructionPatternDetector.calculate_confidence(text)

        assert confidence < 0.4, f"Real ingredient example should have low confidence, got {confidence}"

    def test_narrative_style_instructions(self):
        """Test with narrative-style instructions."""
        text = """
        To make the pasta, bring a large pot of salted water to a boil.
        Once boiling, add the pasta and cook according to package directions.
        Meanwhile, heat olive oil in a skillet and sauté the garlic until fragrant.
        When the pasta is done, drain and toss with the garlic oil.
        """

        confidence = InstructionPatternDetector.calculate_confidence(text)

        assert confidence > 0.7, f"Narrative instructions should have high confidence, got {confidence}"

    def test_edge_case_numbered_steps(self):
        """Test with numbered instruction steps."""
        text = """
        1. Preheat oven to 350°F.
        2. Mix dry ingredients in a bowl.
        3. Combine wet ingredients separately.
        4. Fold wet into dry until just combined.
        5. Bake for 30 minutes.
        """

        confidence = InstructionPatternDetector.calculate_confidence(text)

        # Should have good confidence despite measurements in step numbering
        assert confidence > 0.5, f"Numbered steps should have good confidence, got {confidence}"
