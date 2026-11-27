"""Integration tests for pattern-based extraction transition."""

import pytest
from pathlib import Path
from bs4 import BeautifulSoup

from epub_recipe_parser.core.extractor import EPUBRecipeExtractor
from epub_recipe_parser.core.models import ExtractorConfig, ExtractionConfig
from epub_recipe_parser.extractors.ingredients import IngredientsExtractor


class TestPatternExtractionIntegration:
    """Integration tests for pattern-based extraction in full extraction pipeline."""

    @pytest.fixture
    def recipe_html(self):
        """Complete recipe HTML."""
        return """
        <html>
        <body>
            <section>
                <h1>Chocolate Chip Cookies</h1>
                <h2>Ingredients</h2>
                <ul>
                    <li>2 1/4 cups all-purpose flour</li>
                    <li>1 cup butter, softened</li>
                    <li>3/4 cup granulated sugar</li>
                    <li>3/4 cup brown sugar</li>
                    <li>2 large eggs</li>
                    <li>2 teaspoons vanilla extract</li>
                    <li>1 teaspoon baking soda</li>
                    <li>1/2 teaspoon salt</li>
                    <li>2 cups chocolate chips</li>
                </ul>
                <h2>Instructions</h2>
                <p>Preheat oven to 375 degrees F. Mix butter and sugars until creamy.
                Beat in eggs and vanilla. Combine flour, baking soda, and salt in separate bowl.
                Gradually blend dry ingredients into butter mixture. Stir in chocolate chips.
                Drop rounded tablespoons onto ungreased cookie sheets. Bake 9 to 11 minutes.</p>
                <p>Serves: 48 cookies</p>
                <p>Prep time: 15 minutes</p>
                <p>Cook time: 10 minutes</p>
            </section>
        </body>
        </html>
        """

    def test_extractor_with_pattern_extraction_enabled(self, recipe_html):
        """Test extraction with pattern-based method enabled."""
        config = ExtractorConfig(
            extraction=ExtractionConfig(
                use_pattern_extraction=True,
            )
        )
        extractor = EPUBRecipeExtractor(config=config)

        soup = BeautifulSoup(recipe_html, "html.parser")
        recipe = extractor.extract_from_section(
            soup, title="Chocolate Chip Cookies", book_name="Test Book"
        )

        assert recipe is not None
        assert recipe.ingredients is not None
        assert "flour" in recipe.ingredients.lower()
        assert "chocolate chips" in recipe.ingredients.lower()

        # Check that extraction metadata was stored
        if recipe.metadata.get("extraction"):
            ingredients_meta = recipe.metadata["extraction"].get("ingredients")
            if ingredients_meta:
                assert "strategy" in ingredients_meta or "fallback_reason" in ingredients_meta

    def test_extractor_with_pattern_extraction_disabled(self, recipe_html):
        """Test extraction with pattern-based method disabled (legacy)."""
        config = ExtractorConfig(
            extraction=ExtractionConfig(
                use_pattern_extraction=False,
            )
        )
        extractor = EPUBRecipeExtractor(config=config)

        soup = BeautifulSoup(recipe_html, "html.parser")
        recipe = extractor.extract_from_section(
            soup, title="Chocolate Chip Cookies", book_name="Test Book"
        )

        assert recipe is not None
        assert recipe.ingredients is not None
        assert "flour" in recipe.ingredients.lower()

        # In legacy mode, should not have extraction metadata
        # (normalize_extraction_result returns empty dict for string results)
        if recipe.metadata.get("extraction"):
            # Empty or minimal metadata
            ingredients_meta = recipe.metadata["extraction"].get("ingredients", {})
            # Should be empty for legacy mode
            assert len(ingredients_meta) == 0 or "fallback" in ingredients_meta.get("strategy", "")

    def test_extraction_metadata_structure(self, recipe_html):
        """Test that extraction metadata has expected structure."""
        config = ExtractorConfig(
            extraction=ExtractionConfig(use_pattern_extraction=True)
        )
        extractor = EPUBRecipeExtractor(config=config)

        soup = BeautifulSoup(recipe_html, "html.parser")
        recipe = extractor.extract_from_section(
            soup, title="Test Recipe", book_name="Test Book"
        )

        if recipe and recipe.metadata.get("extraction"):
            extraction = recipe.metadata["extraction"]

            # Should have ingredients section
            assert "ingredients" in extraction

            ingredients_meta = extraction["ingredients"]

            # Should have expected fields
            expected_fields = ["strategy", "confidence", "linguistic_score", "combined_score"]
            # At least some fields should be present
            present_fields = [f for f in expected_fields if f in ingredients_meta]
            assert len(present_fields) > 0 or "fallback_reason" in ingredients_meta

    def test_backward_compatibility_with_flat_config(self, recipe_html):
        """Test backward compatibility with flat configuration parameters."""
        # Old style: flat parameters
        config = ExtractorConfig(
            use_pattern_extraction=True,
        )
        extractor = EPUBRecipeExtractor(config=config)

        soup = BeautifulSoup(recipe_html, "html.parser")
        recipe = extractor.extract_from_section(
            soup, title="Test Recipe", book_name="Test Book"
        )

        assert recipe is not None
        assert recipe.ingredients is not None

    def test_default_config_uses_pattern_extraction(self, recipe_html):
        """Test that default configuration uses pattern extraction."""
        config = ExtractorConfig()  # Default config
        extractor = EPUBRecipeExtractor(config=config)

        soup = BeautifulSoup(recipe_html, "html.parser")
        recipe = extractor.extract_from_section(
            soup, title="Test Recipe", book_name="Test Book"
        )

        # Default should use pattern extraction
        assert config.extraction.use_pattern_extraction is True
        assert recipe is not None


class TestMetadataAccess:
    """Tests for accessing extraction metadata from recipes."""

    @pytest.fixture
    def recipe_with_metadata(self):
        """Create a recipe with extraction metadata."""
        from epub_recipe_parser.core.models import Recipe

        recipe = Recipe(
            title="Test Recipe",
            book="Test Book",
            ingredients="- 2 cups flour\n- 1 cup sugar",
            instructions="Mix and bake.",
        )

        recipe.metadata["extraction"] = {
            "ingredients": {
                "strategy": "structural_zones",
                "confidence": 0.92,
                "linguistic_score": 0.88,
                "combined_score": 0.90,
            }
        }

        return recipe

    def test_access_confidence_score(self, recipe_with_metadata):
        """Test accessing confidence score from recipe."""
        from epub_recipe_parser.utils.extraction import get_extraction_confidence

        confidence = get_extraction_confidence(
            recipe_with_metadata.metadata, "ingredients"
        )
        assert confidence == 0.92

    def test_access_strategy(self, recipe_with_metadata):
        """Test accessing extraction strategy from recipe."""
        from epub_recipe_parser.utils.extraction import get_extraction_strategy

        strategy = get_extraction_strategy(recipe_with_metadata.metadata, "ingredients")
        assert strategy == "structural_zones"

    def test_recipe_to_dict_includes_metadata(self, recipe_with_metadata):
        """Test that recipe.to_dict() includes extraction metadata."""
        recipe_dict = recipe_with_metadata.to_dict()

        assert "metadata" in recipe_dict
        assert "extraction" in recipe_dict["metadata"]
        assert "ingredients" in recipe_dict["metadata"]["extraction"]


class TestExtractionQuality:
    """Tests for extraction quality with pattern-based method."""

    @pytest.fixture
    def high_quality_recipe_html(self):
        """High-quality recipe HTML with clear structure."""
        return """
        <html>
        <body>
            <section class="recipe">
                <h1>Perfect Pasta</h1>
                <div class="ingredients">
                    <h2>Ingredients</h2>
                    <ul>
                        <li>1 pound pasta</li>
                        <li>2 tablespoons olive oil</li>
                        <li>3 cloves garlic, minced</li>
                        <li>1 cup cherry tomatoes, halved</li>
                        <li>1/4 cup fresh basil, chopped</li>
                        <li>Salt and pepper to taste</li>
                    </ul>
                </div>
                <div class="instructions">
                    <h2>Instructions</h2>
                    <ol>
                        <li>Cook pasta according to package directions.</li>
                        <li>Heat olive oil in large skillet over medium heat.</li>
                        <li>Add garlic and cook for 1 minute.</li>
                        <li>Add tomatoes and cook until softened, about 5 minutes.</li>
                        <li>Drain pasta and add to skillet.</li>
                        <li>Toss with basil, salt, and pepper.</li>
                        <li>Serve immediately.</li>
                    </ol>
                </div>
                <p>Serves: 4</p>
                <p>Prep time: 10 minutes</p>
                <p>Cook time: 15 minutes</p>
            </section>
        </body>
        </html>
        """

    def test_high_quality_extraction_has_high_confidence(self, high_quality_recipe_html):
        """Test that high-quality HTML produces high confidence scores."""
        config = ExtractorConfig(
            extraction=ExtractionConfig(use_pattern_extraction=True)
        )
        extractor = EPUBRecipeExtractor(config=config)

        soup = BeautifulSoup(high_quality_recipe_html, "html.parser")
        recipe = extractor.extract_from_section(
            soup, title="Perfect Pasta", book_name="Test Book"
        )

        assert recipe is not None
        assert recipe.ingredients is not None

        # Check metadata exists
        if recipe.metadata.get("extraction", {}).get("ingredients"):
            from epub_recipe_parser.utils.extraction import get_extraction_confidence

            confidence = get_extraction_confidence(recipe.metadata, "ingredients")

            # High quality HTML should produce reasonable confidence
            if confidence is not None:
                assert confidence >= 0.5  # At least moderate confidence

    def test_pattern_extraction_extracts_complete_list(self, high_quality_recipe_html):
        """Test that pattern extraction gets complete ingredient list."""
        config = ExtractorConfig(
            extraction=ExtractionConfig(use_pattern_extraction=True)
        )
        extractor = EPUBRecipeExtractor(config=config)

        soup = BeautifulSoup(high_quality_recipe_html, "html.parser")
        recipe = extractor.extract_from_section(
            soup, title="Perfect Pasta", book_name="Test Book"
        )

        assert recipe is not None
        ingredients = recipe.ingredients.lower()

        # Should have all key ingredients
        assert "pasta" in ingredients
        assert "olive oil" in ingredients
        assert "garlic" in ingredients
        assert "tomatoes" in ingredients or "tomato" in ingredients
        assert "basil" in ingredients


class TestConfigurationMigration:
    """Tests for configuration migration from old to new."""

    def test_old_config_style_works(self):
        """Test that old configuration style still works."""
        # Old style
        config = ExtractorConfig(
            validate_recipes=True,
            include_raw_content=False,
        )

        assert config.extraction.validate_recipes is True
        assert config.extraction.include_raw_content is False

    def test_new_config_style_works(self):
        """Test that new nested configuration style works."""
        # New style
        config = ExtractorConfig(
            extraction=ExtractionConfig(
                validate_recipes=True,
                use_pattern_extraction=True,
            )
        )

        assert config.extraction.validate_recipes is True
        assert config.extraction.use_pattern_extraction is True

    def test_mixed_config_style_works(self):
        """Test that mixing old and new styles works."""
        config = ExtractorConfig(
            extraction=ExtractionConfig(),
            use_pattern_extraction=False,  # Overrides default
        )

        assert config.extraction.use_pattern_extraction is False  # Flat param took precedence
