"""Tests for extraction utility functions."""

import pytest
from epub_recipe_parser.utils.extraction import (
    normalize_extraction_result,
    merge_extraction_metadata,
    get_extraction_confidence,
    get_extraction_strategy,
)


class TestNormalizeExtractionResult:
    """Tests for normalize_extraction_result function."""

    def test_none_result(self):
        """Test normalizing None result."""
        text, metadata = normalize_extraction_result(None)
        assert text is None
        assert metadata == {}

    def test_legacy_string_result(self):
        """Test normalizing legacy string result."""
        text, metadata = normalize_extraction_result("some ingredients")
        assert text == "some ingredients"
        assert metadata == {}

    def test_modern_tuple_result(self):
        """Test normalizing modern tuple result."""
        input_metadata = {
            "strategy": "structural_zones",
            "confidence": 0.85,
            "linguistic_score": 0.92,
        }
        text, metadata = normalize_extraction_result(("ingredients text", input_metadata))
        assert text == "ingredients text"
        assert metadata == input_metadata

    def test_tuple_with_none_text(self):
        """Test normalizing tuple with None text."""
        input_metadata = {"strategy": "failed", "confidence": 0.0}
        text, metadata = normalize_extraction_result((None, input_metadata))
        assert text is None
        assert metadata == input_metadata

    def test_invalid_tuple_non_dict_metadata(self):
        """Test normalizing tuple with non-dict metadata."""
        text, metadata = normalize_extraction_result(("text", "not a dict"))
        assert text == "text"
        assert metadata == {}

    def test_empty_string_result(self):
        """Test normalizing empty string."""
        text, metadata = normalize_extraction_result("")
        assert text == ""
        assert metadata == {}


class TestMergeExtractionMetadata:
    """Tests for merge_extraction_metadata function."""

    def test_merge_into_empty_metadata(self):
        """Test merging into empty recipe metadata."""
        base = {}
        extraction = {"confidence": 0.9, "strategy": "pattern"}
        result = merge_extraction_metadata(base, extraction, "ingredients")

        assert "extraction" in result
        assert "ingredients" in result["extraction"]
        assert result["extraction"]["ingredients"]["confidence"] == 0.9
        assert result["extraction"]["ingredients"]["strategy"] == "pattern"

    def test_merge_into_existing_metadata(self):
        """Test merging into existing recipe metadata."""
        base = {"some_field": "value"}
        extraction = {"confidence": 0.85}
        result = merge_extraction_metadata(base, extraction, "ingredients")

        assert result["some_field"] == "value"
        assert result["extraction"]["ingredients"]["confidence"] == 0.85

    def test_merge_multiple_components(self):
        """Test merging metadata for multiple components."""
        base = {}
        ingredients_meta = {"confidence": 0.9, "strategy": "structural"}
        instructions_meta = {"confidence": 0.8, "strategy": "pattern"}

        result = merge_extraction_metadata(base, ingredients_meta, "ingredients")
        result = merge_extraction_metadata(result, instructions_meta, "instructions")

        assert result["extraction"]["ingredients"]["confidence"] == 0.9
        assert result["extraction"]["instructions"]["confidence"] == 0.8

    def test_merge_empty_extraction_metadata(self):
        """Test merging empty extraction metadata."""
        base = {"field": "value"}
        result = merge_extraction_metadata(base, {}, "ingredients")

        # Should not add extraction section
        assert result == {"field": "value"}

    def test_merge_none_extraction_metadata(self):
        """Test merging None extraction metadata."""
        base = {"field": "value"}
        result = merge_extraction_metadata(base, None, "ingredients")

        # Should handle None gracefully
        assert result == {"field": "value"}


class TestGetExtractionConfidence:
    """Tests for get_extraction_confidence function."""

    def test_get_existing_confidence(self):
        """Test getting confidence from recipe metadata."""
        metadata = {"extraction": {"ingredients": {"confidence": 0.85}}}
        confidence = get_extraction_confidence(metadata, "ingredients")
        assert confidence == 0.85

    def test_get_missing_component(self):
        """Test getting confidence for missing component."""
        metadata = {"extraction": {"ingredients": {"confidence": 0.85}}}
        confidence = get_extraction_confidence(metadata, "instructions")
        assert confidence is None

    def test_get_no_extraction_metadata(self):
        """Test getting confidence when no extraction metadata exists."""
        metadata = {"other_field": "value"}
        confidence = get_extraction_confidence(metadata, "ingredients")
        assert confidence is None

    def test_get_empty_metadata(self):
        """Test getting confidence from empty metadata."""
        confidence = get_extraction_confidence({}, "ingredients")
        assert confidence is None

    def test_get_confidence_missing_in_component(self):
        """Test getting confidence when component exists but confidence missing."""
        metadata = {"extraction": {"ingredients": {"strategy": "pattern"}}}
        confidence = get_extraction_confidence(metadata, "ingredients")
        assert confidence is None


class TestGetExtractionStrategy:
    """Tests for get_extraction_strategy function."""

    def test_get_existing_strategy(self):
        """Test getting strategy from recipe metadata."""
        metadata = {"extraction": {"ingredients": {"strategy": "structural_zones"}}}
        strategy = get_extraction_strategy(metadata, "ingredients")
        assert strategy == "structural_zones"

    def test_get_missing_component(self):
        """Test getting strategy for missing component."""
        metadata = {"extraction": {"ingredients": {"strategy": "pattern"}}}
        strategy = get_extraction_strategy(metadata, "instructions")
        assert strategy is None

    def test_get_no_extraction_metadata(self):
        """Test getting strategy when no extraction metadata exists."""
        metadata = {"other_field": "value"}
        strategy = get_extraction_strategy(metadata, "ingredients")
        assert strategy is None

    def test_get_empty_metadata(self):
        """Test getting strategy from empty metadata."""
        strategy = get_extraction_strategy({}, "ingredients")
        assert strategy is None

    def test_get_strategy_missing_in_component(self):
        """Test getting strategy when component exists but strategy missing."""
        metadata = {"extraction": {"ingredients": {"confidence": 0.9}}}
        strategy = get_extraction_strategy(metadata, "ingredients")
        assert strategy is None


class TestExtractionUtilitiesIntegration:
    """Integration tests for extraction utilities."""

    def test_full_workflow(self):
        """Test complete workflow of normalizing and storing metadata."""
        # Simulate extraction result
        extraction_result = (
            "- 2 cups flour\n- 1 cup sugar",
            {
                "strategy": "structural_zones",
                "confidence": 0.92,
                "linguistic_score": 0.88,
                "combined_score": 0.90,
            },
        )

        # Normalize
        text, metadata = normalize_extraction_result(extraction_result)
        assert text == "- 2 cups flour\n- 1 cup sugar"
        assert metadata["confidence"] == 0.92

        # Merge into recipe metadata
        recipe_metadata = {}
        merge_extraction_metadata(recipe_metadata, metadata, "ingredients")

        # Verify retrieval
        assert get_extraction_confidence(recipe_metadata, "ingredients") == 0.92
        assert get_extraction_strategy(recipe_metadata, "ingredients") == "structural_zones"

    def test_legacy_workflow(self):
        """Test workflow with legacy extraction result."""
        # Legacy result (just text)
        extraction_result = "- 1 egg\n- 2 tablespoons butter"

        # Normalize
        text, metadata = normalize_extraction_result(extraction_result)
        assert text == "- 1 egg\n- 2 tablespoons butter"
        assert metadata == {}

        # Merge into recipe metadata (should not add extraction section)
        recipe_metadata = {}
        merge_extraction_metadata(recipe_metadata, metadata, "ingredients")

        # Verify no extraction metadata
        assert get_extraction_confidence(recipe_metadata, "ingredients") is None
        assert get_extraction_strategy(recipe_metadata, "ingredients") is None
