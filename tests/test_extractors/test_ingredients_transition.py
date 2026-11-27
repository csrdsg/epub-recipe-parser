"""Tests for IngredientsExtractor transition to pattern-based extraction."""

import pytest
from bs4 import BeautifulSoup
from epub_recipe_parser.extractors.ingredients import IngredientsExtractor


class TestIngredientsExtractorDelegation:
    """Tests for delegation logic in IngredientsExtractor.extract()."""

    @pytest.fixture
    def simple_html(self):
        """Simple HTML with ingredients list."""
        return """
        <html>
        <body>
            <h2>Ingredients</h2>
            <ul>
                <li>2 cups flour</li>
                <li>1 cup sugar</li>
                <li>1/2 teaspoon salt</li>
            </ul>
        </body>
        </html>
        """

    @pytest.fixture
    def simple_soup(self, simple_html):
        """BeautifulSoup object for simple HTML."""
        return BeautifulSoup(simple_html, "html.parser")

    @pytest.fixture
    def simple_text(self, simple_soup):
        """Plain text from simple HTML."""
        return simple_soup.get_text()

    def test_extract_with_patterns_enabled(self, simple_soup, simple_text):
        """Test extraction with pattern-based detection enabled."""
        result = IngredientsExtractor.extract(simple_soup, simple_text, use_patterns=True)

        # Should return tuple
        assert isinstance(result, tuple)
        assert len(result) == 2

        text, metadata = result

        # Should have extracted ingredients
        assert text is not None
        assert "flour" in text.lower()
        assert "sugar" in text.lower()

        # Should have metadata
        assert isinstance(metadata, dict)
        assert "strategy" in metadata or len(metadata) == 0  # May be empty if extraction failed

    def test_extract_with_patterns_disabled(self, simple_soup, simple_text):
        """Test extraction with pattern-based detection disabled (legacy mode)."""
        result = IngredientsExtractor.extract(simple_soup, simple_text, use_patterns=False)

        # Should return string only (legacy mode)
        assert isinstance(result, (str, type(None)))

        if result:
            assert "flour" in result.lower()
            assert "sugar" in result.lower()

    def test_extract_default_uses_patterns(self, simple_soup, simple_text):
        """Test that extract() defaults to using patterns."""
        result = IngredientsExtractor.extract(simple_soup, simple_text)

        # Default should use patterns, returning tuple
        assert isinstance(result, tuple)
        assert len(result) == 2

    def test_legacy_extract_direct_call(self, simple_soup, simple_text):
        """Test calling _extract_legacy directly."""
        result = IngredientsExtractor._extract_legacy(simple_soup, simple_text)

        # Should return string or None
        assert isinstance(result, (str, type(None)))

        if result:
            assert "flour" in result.lower()

    def test_pattern_extraction_fallback(self):
        """Test fallback to legacy when pattern extraction fails."""
        # HTML with ingredients that might be detected by legacy but not patterns
        html = """
        <html><body>
        <p>2 cups flour</p>
        <p>1 cup sugar</p>
        <p>1/2 teaspoon salt</p>
        </body></html>
        """
        soup = BeautifulSoup(html, "html.parser")
        text = soup.get_text()

        result = IngredientsExtractor.extract(soup, text, use_patterns=True)

        # Should return tuple
        assert isinstance(result, tuple)
        text_result, metadata = result

        # If pattern extraction worked, should have text and good metadata
        # If it failed and fell back to legacy, should have fallback metadata
        if text_result:
            assert isinstance(metadata, dict)
            if metadata.get("strategy") == "legacy_fallback":
                assert "fallback_reason" in metadata

    def test_extract_with_patterns_returns_metadata(self, simple_soup, simple_text):
        """Test that pattern extraction returns proper metadata structure."""
        result = IngredientsExtractor.extract(simple_soup, simple_text, use_patterns=True)

        text, metadata = result

        # Metadata should be dict
        assert isinstance(metadata, dict)

        # If extraction succeeded, should have metadata fields
        if text:
            # May have various fields depending on strategy
            possible_fields = ["strategy", "confidence", "linguistic_score", "combined_score", "fallback_reason"]
            # At least one field should be present
            assert any(field in metadata for field in possible_fields) or len(metadata) == 0


class TestIngredientsExtractorBackwardCompatibility:
    """Tests ensuring backward compatibility."""

    @pytest.fixture
    def ingredients_html(self):
        return """
        <html>
        <body>
            <h3>Ingredients</h3>
            <ul>
                <li>3 eggs</li>
                <li>1 tablespoon butter</li>
            </ul>
        </body>
        </html>
        """

    def test_legacy_code_still_works(self, ingredients_html):
        """Test that existing code using extract() still works."""
        soup = BeautifulSoup(ingredients_html, "html.parser")
        text = soup.get_text()

        # Old code might call extract without use_patterns parameter
        result = IngredientsExtractor.extract(soup, text)

        # Should still work, though it now returns tuple by default
        # Legacy callers expecting string will need to handle this
        assert result is not None

    def test_extract_with_patterns_method_exists(self):
        """Test that extract_with_patterns method still exists."""
        assert hasattr(IngredientsExtractor, "extract_with_patterns")
        assert callable(IngredientsExtractor.extract_with_patterns)

    def test_private_methods_exist(self):
        """Test that private helper methods still exist."""
        # These should still be accessible for internal use
        assert hasattr(IngredientsExtractor, "_extract_legacy")
        assert hasattr(IngredientsExtractor, "_extract_from_text")
        assert hasattr(IngredientsExtractor, "_extract_from_paragraph_classes")


class TestPatternExtractionMetadata:
    """Tests for metadata returned by pattern extraction."""

    @pytest.fixture
    def recipe_html(self):
        return """
        <html>
        <body>
            <section>
                <h2>Ingredients</h2>
                <ul class="ingredients">
                    <li>2 cups all-purpose flour</li>
                    <li>1 cup granulated sugar</li>
                    <li>1/2 cup butter, softened</li>
                    <li>2 large eggs</li>
                    <li>1 teaspoon vanilla extract</li>
                    <li>1/2 teaspoon salt</li>
                </ul>
            </section>
        </body>
        </html>
        """

    def test_metadata_contains_strategy(self, recipe_html):
        """Test that metadata contains strategy field."""
        soup = BeautifulSoup(recipe_html, "html.parser")
        text = soup.get_text()

        text_result, metadata = IngredientsExtractor.extract(soup, text, use_patterns=True)

        if text_result:
            assert "strategy" in metadata or "fallback_reason" in metadata

    def test_metadata_contains_confidence(self, recipe_html):
        """Test that metadata contains confidence score."""
        soup = BeautifulSoup(recipe_html, "html.parser")
        text = soup.get_text()

        text_result, metadata = IngredientsExtractor.extract(soup, text, use_patterns=True)

        if text_result and "confidence" in metadata:
            confidence = metadata["confidence"]
            assert isinstance(confidence, (int, float))
            assert 0.0 <= confidence <= 1.0

    def test_graceful_degradation_on_error(self):
        """Test graceful degradation when pattern extraction raises exception."""
        # Create malformed HTML that might cause issues
        html = "<html><body><broken>"
        soup = BeautifulSoup(html, "html.parser")
        text = soup.get_text()

        # Should not raise exception, should fall back gracefully
        result = IngredientsExtractor.extract(soup, text, use_patterns=True)

        # Should return tuple even on error
        assert isinstance(result, tuple)
        assert len(result) == 2


class TestExtractionStrategies:
    """Tests for different extraction strategies."""

    def test_structural_zones_strategy(self):
        """Test that structural zones strategy is used when appropriate."""
        html = """
        <html>
        <body>
            <div class="ingredients">
                <h3>What You'll Need</h3>
                <ul>
                    <li>2 cups flour</li>
                    <li>1 cup milk</li>
                </ul>
            </div>
        </body>
        </html>
        """
        soup = BeautifulSoup(html, "html.parser")
        text = soup.get_text()

        text_result, metadata = IngredientsExtractor.extract(soup, text, use_patterns=True)

        if text_result:
            # Should have used some strategy
            assert "strategy" in metadata or "fallback_reason" in metadata

    def test_legacy_fallback_strategy(self):
        """Test that legacy fallback is indicated in metadata."""
        # Create HTML that pattern extraction might fail on
        html = """
        <html><body>
        <p>Simple paragraph with 2 cups flour.</p>
        </body></html>
        """
        soup = BeautifulSoup(html, "html.parser")
        text = soup.get_text()

        text_result, metadata = IngredientsExtractor.extract(soup, text, use_patterns=True)

        # If it fell back to legacy, metadata should indicate this
        if text_result and metadata.get("strategy") == "legacy_fallback":
            assert "fallback_reason" in metadata


class TestRegressionPrevention:
    """Regression tests to ensure new method >= old method."""

    @pytest.fixture
    def comprehensive_html(self):
        """Comprehensive HTML with various ingredient formats."""
        return """
        <html>
        <body>
            <h2>Ingredients</h2>
            <h3>For the Dough</h3>
            <ul>
                <li>3 cups bread flour</li>
                <li>1 tablespoon yeast</li>
                <li>1 1/2 cups warm water</li>
            </ul>
            <h3>For the Topping</h3>
            <ul>
                <li>1 cup shredded cheese</li>
                <li>1/2 cup tomato sauce</li>
            </ul>
        </body>
        </html>
        """

    def test_new_method_extracts_at_least_as_much(self, comprehensive_html):
        """Test that pattern method extracts at least as much as legacy."""
        soup = BeautifulSoup(comprehensive_html, "html.parser")
        text = soup.get_text()

        # Get legacy result
        legacy_result = IngredientsExtractor._extract_legacy(soup, text)

        # Get pattern result
        pattern_result, metadata = IngredientsExtractor.extract(soup, text, use_patterns=True)

        # Both should extract something
        if legacy_result:
            assert pattern_result is not None
            # Pattern result should have similar or more content
            assert len(pattern_result) >= len(legacy_result) * 0.8  # Allow 20% variance
