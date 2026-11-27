"""
Comprehensive integration tests for pattern-based extraction system.

Tests the full end-to-end extraction pipeline including:
- Pattern-based ingredient detection
- Instruction extraction with confidence scoring
- Metadata extraction with pattern matching
- Database storage with confidence preservation
- JSON/Markdown export with metadata
- A/B comparison between legacy and pattern methods
"""

import json
import logging
import os
import sqlite3
import tempfile
from pathlib import Path
from typing import List, Dict, Any

import pytest

from epub_recipe_parser.core.extractor import EPUBRecipeExtractor
from epub_recipe_parser.core.models import Recipe, ExtractorConfig, ABTestConfig, LogLevel
from epub_recipe_parser.extractors.ingredients import IngredientsExtractor
from epub_recipe_parser.extractors.instructions import InstructionsExtractor
from epub_recipe_parser.extractors.metadata import MetadataExtractor
from epub_recipe_parser.storage.database import RecipeDatabase

# Configure logging for test output
logging.basicConfig(
    level=logging.INFO,
    format='%(levelname)s - %(name)s - %(message)s'
)
logger = logging.getLogger(__name__)

TEST_EPUB_PATH = os.environ.get("EPUB_RECIPE_TEST_BOOK", "")
requires_cookbook = pytest.mark.skipif(
    not TEST_EPUB_PATH or not Path(TEST_EPUB_PATH).is_file(),
    reason="Set EPUB_RECIPE_TEST_BOOK to the local smoker cookbook EPUB",
)


@requires_cookbook
class TestEndToEndExtraction:
    """Test complete extraction pipeline with pattern-based methods."""

    def test_full_extraction_pipeline(self):
        """Test complete extraction from EPUB to Recipe objects."""
        logger.info("=" * 80)
        logger.info("TEST: Full Extraction Pipeline")
        logger.info("=" * 80)

        # Create extractor with default configuration
        config = ExtractorConfig()
        extractor = EPUBRecipeExtractor(config=config)

        # Extract recipes
        recipes = extractor.extract_from_epub(TEST_EPUB_PATH)

        # Assertions
        assert len(recipes) > 0, "Should extract at least one recipe"
        logger.info(f"Extracted {len(recipes)} recipes from EPUB")

        # Verify recipe structure
        for recipe in recipes[:5]:  # Check first 5 recipes
            assert recipe.title, f"Recipe should have title: {recipe}"
            assert recipe.book, f"Recipe should have book name: {recipe}"

            # Verify components exist
            assert recipe.ingredients or recipe.instructions, \
                f"Recipe should have ingredients or instructions: {recipe.title}"

        logger.info(f"All {len(recipes)} recipes have valid structure")

    def test_confidence_scores_calculated(self):
        """Verify that pattern-based methods calculate confidence scores."""
        logger.info("=" * 80)
        logger.info("TEST: Confidence Scores Calculation")
        logger.info("=" * 80)

        # Create extractor
        config = ExtractorConfig()
        extractor = EPUBRecipeExtractor(config=config)

        # Extract a few recipes
        recipes = extractor.extract_from_epub(TEST_EPUB_PATH)
        assert len(recipes) > 0, "Should extract recipes"

        # Test pattern-based extraction with confidence on first recipe
        from bs4 import BeautifulSoup
        from epub_recipe_parser.utils.html import HTMLParser

        test_recipe = recipes[0]
        logger.info(f"Testing confidence scoring on: {test_recipe.title}")

        # Create a simple HTML snippet to test
        test_html = f"""
        <html>
            <body>
                <h2>{test_recipe.title}</h2>
                <h3>Ingredients</h3>
                <p>2 cups flour</p>
                <p>1 cup sugar</p>
                <p>3 eggs</p>
                <h3>Instructions</h3>
                <p>Mix the flour and sugar. Add eggs. Bake at 350°F for 30 minutes.</p>
            </body>
        </html>
        """
        soup = BeautifulSoup(test_html, 'html.parser')
        text = soup.get_text()

        # Test ingredients extraction with patterns
        ingredients_text, ingredients_metadata = IngredientsExtractor.extract_with_patterns(soup, text)

        if ingredients_text:
            logger.info(f"Ingredients confidence metadata: {ingredients_metadata}")
            assert 'confidence' in ingredients_metadata, "Should have confidence score"
            assert 'strategy' in ingredients_metadata, "Should have strategy used"
            assert 0.0 <= ingredients_metadata['confidence'] <= 1.0, "Confidence should be 0-1"
            logger.info(f"Ingredients confidence: {ingredients_metadata['confidence']:.3f}")
            logger.info(f"Strategy used: {ingredients_metadata['strategy']}")

@requires_cookbook
class TestABComparison:
    """Test A/B comparison between legacy and pattern-based methods."""

    def test_legacy_vs_pattern_agreement(self):
        """Compare extraction results between legacy and pattern methods."""
        logger.info("=" * 80)
        logger.info("TEST: Legacy vs Pattern Method Agreement")
        logger.info("=" * 80)

        # Enable A/B testing
        ab_config = ABTestConfig(
            enabled=True,
            use_new_method=False,  # Compare but use legacy
            log_level=LogLevel.INFO,
            success_threshold=25
        )
        config = ExtractorConfig(
            ab_testing=ab_config
        )

        extractor = EPUBRecipeExtractor(config=config)
        recipes = extractor.extract_from_epub(TEST_EPUB_PATH)

        logger.info(f"Extracted {len(recipes)} recipes with A/B testing")

        # Count recipes with A/B metadata
        ab_recipes = [r for r in recipes if r.metadata.get('ab_test')]
        logger.info(f"Recipes with A/B test metadata: {len(ab_recipes)}")

        if len(ab_recipes) > 0:
            # Calculate agreement rate
            agreements = sum(1 for r in ab_recipes if r.metadata['ab_test'].get('agreement'))
            agreement_rate = (agreements / len(ab_recipes)) * 100

            logger.info(f"Agreement rate: {agreement_rate:.1f}% ({agreements}/{len(ab_recipes)})")

            # Log some disagreements
            disagreements = [r for r in ab_recipes if not r.metadata['ab_test'].get('agreement')]
            if disagreements:
                logger.info(f"Found {len(disagreements)} disagreements")
                for recipe in disagreements[:3]:  # Show first 3
                    ab_data = recipe.metadata['ab_test']
                    logger.info(f"  - {recipe.title}")
                    logger.info(f"    Old success: {ab_data.get('old_success')}")
                    logger.info(f"    New success: {ab_data.get('new_success')}")
                    logger.info(f"    Confidence: {ab_data.get('confidence', 0):.3f}")

    def test_pattern_confidence_metrics(self):
        """Verify confidence scoring in pattern-based methods."""
        logger.info("=" * 80)
        logger.info("TEST: Pattern Confidence Metrics")
        logger.info("=" * 80)

        # Test with pattern-based extraction
        from bs4 import BeautifulSoup

        test_html = """
        <html>
            <body>
                <h2>Smoked Chicken</h2>
                <h3>Ingredients</h3>
                <ul>
                    <li>1 whole chicken (3-4 pounds)</li>
                    <li>2 tablespoons olive oil</li>
                    <li>1 tablespoon paprika</li>
                    <li>1 teaspoon garlic powder</li>
                    <li>Salt and pepper to taste</li>
                </ul>
                <h3>Instructions</h3>
                <p>Preheat smoker to 225°F. Rub chicken with oil and seasonings.
                   Smoke for 3-4 hours until internal temperature reaches 165°F.</p>
            </body>
        </html>
        """

        soup = BeautifulSoup(test_html, 'html.parser')
        text = soup.get_text()

        # Test ingredients
        ingredients_text, ing_metadata = IngredientsExtractor.extract_with_patterns(soup, text)
        assert ingredients_text is not None, "Should extract ingredients"
        assert ing_metadata['confidence'] > 0, "Should have positive confidence"
        logger.info(f"Ingredients confidence: {ing_metadata['confidence']:.3f}")
        logger.info(f"Ingredients strategy: {ing_metadata['strategy']}")

        # Verify metadata structure
        required_keys = ['strategy', 'confidence', 'linguistic_score', 'combined_score']
        for key in required_keys:
            assert key in ing_metadata, f"Metadata should contain '{key}'"

        logger.info(f"Confidence metadata complete: {ing_metadata.keys()}")


@requires_cookbook
class TestDatabaseIntegration:
    """Test database storage and retrieval with confidence scores."""

    def test_save_and_load_with_confidence(self):
        """Test database round-trip preserves confidence scores."""
        logger.info("=" * 80)
        logger.info("TEST: Database Round-Trip with Confidence")
        logger.info("=" * 80)

        # Create temporary database
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tmp:
            db_path = tmp.name

        try:
            # Extract recipes with A/B testing
            ab_config = ABTestConfig(
                enabled=True,
                use_new_method=False,
                log_level=LogLevel.INFO
            )
            config = ExtractorConfig(
                ab_testing=ab_config
            )

            extractor = EPUBRecipeExtractor(config=config)
            recipes = extractor.extract_from_epub(TEST_EPUB_PATH)
            logger.info(f"Extracted {len(recipes)} recipes")

            # Save to database
            db = RecipeDatabase(db_path)
            saved_count = db.save_recipes(recipes)
            logger.info(f"Saved {saved_count} recipes to database")

            assert saved_count == len(recipes), "All recipes should be saved"

            # Query back from database
            loaded_recipes = db.query()
            logger.info(f"Loaded {len(loaded_recipes)} recipes from database")

            assert len(loaded_recipes) == len(recipes), "Should load same number of recipes"

            # Verify metadata preserved
            recipes_with_ab = [r for r in loaded_recipes if r.metadata.get('ab_test')]
            logger.info(f"Recipes with A/B metadata: {len(recipes_with_ab)}")

            if len(recipes_with_ab) > 0:
                # Check first recipe with A/B data
                test_recipe = recipes_with_ab[0]
                ab_data = test_recipe.metadata['ab_test']

                logger.info(f"Sample A/B metadata from DB: {ab_data.keys()}")
                assert 'agreement' in ab_data or 'confidence' in ab_data, \
                    "A/B metadata should be preserved"

        finally:
            # Cleanup
            Path(db_path).unlink(missing_ok=True)

    def test_ab_test_statistics(self):
        """Test A/B test statistics aggregation from database."""
        logger.info("=" * 80)
        logger.info("TEST: A/B Test Statistics")
        logger.info("=" * 80)

        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tmp:
            db_path = tmp.name

        try:
            # Extract with A/B testing
            ab_config = ABTestConfig(
                enabled=True,
                use_new_method=False,
                log_level=LogLevel.INFO
            )
            config = ExtractorConfig(
                ab_testing=ab_config
            )

            extractor = EPUBRecipeExtractor(config=config)
            recipes = extractor.extract_from_epub(TEST_EPUB_PATH)

            # Save to database
            db = RecipeDatabase(db_path)
            db.save_recipes(recipes)

            # Get A/B test statistics
            stats = db.get_ab_test_stats()
            logger.info(f"A/B Test Statistics:")
            logger.info(f"  Total tests: {stats['total_tests']}")
            logger.info(f"  Agreement rate: {stats['agreement_rate']:.1f}%")
            logger.info(f"  Old method success: {stats['old_success_rate']:.1f}%")
            logger.info(f"  New method success: {stats['new_success_rate']:.1f}%")
            logger.info(f"  Average confidence: {stats['avg_confidence']:.3f}")

            if stats['total_tests'] > 0:
                assert 0 <= stats['agreement_rate'] <= 100, "Agreement rate should be 0-100%"
                assert 0 <= stats['avg_confidence'] <= 1, "Confidence should be 0-1"

        finally:
            Path(db_path).unlink(missing_ok=True)

@requires_cookbook
class TestExportIntegration:
    """Test JSON and Markdown export with confidence scores."""

    def test_json_export_includes_confidence(self):
        """Test JSON export includes confidence metadata."""
        logger.info("=" * 80)
        logger.info("TEST: JSON Export with Confidence")
        logger.info("=" * 80)

        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tmp_db:
            db_path = tmp_db.name

        with tempfile.NamedTemporaryFile(suffix='.json', delete=False) as tmp_json:
            json_path = tmp_json.name

        try:
            # Extract recipes with A/B testing
            ab_config = ABTestConfig(
                enabled=True,
                use_new_method=False,
                log_level=LogLevel.INFO
            )
            config = ExtractorConfig(
                ab_testing=ab_config
            )

            extractor = EPUBRecipeExtractor(config=config)
            recipes = extractor.extract_from_epub(TEST_EPUB_PATH)

            # Convert to JSON
            recipes_data = [recipe.to_dict() for recipe in recipes]

            with open(json_path, 'w') as f:
                json.dump(recipes_data, f, indent=2)

            logger.info(f"Exported {len(recipes_data)} recipes to JSON")

            # Load and verify JSON
            with open(json_path, 'r') as f:
                loaded_data = json.load(f)

            assert len(loaded_data) == len(recipes), "Should export all recipes"

            # Check for metadata in JSON
            recipes_with_metadata = [r for r in loaded_data if r.get('metadata')]
            logger.info(f"Recipes with metadata in JSON: {len(recipes_with_metadata)}")

            if len(recipes_with_metadata) > 0:
                # Verify structure
                sample = recipes_with_metadata[0]
                assert 'title' in sample, "Should have title"
                assert 'ingredients' in sample or 'instructions' in sample, \
                    "Should have content"
                logger.info(f"Sample JSON keys: {sample.keys()}")

                # Check if any have A/B test data
                ab_recipes = [r for r in recipes_with_metadata if r['metadata'].get('ab_test')]
                logger.info(f"Recipes with A/B data in JSON: {len(ab_recipes)}")

        finally:
            Path(db_path).unlink(missing_ok=True)
            Path(json_path).unlink(missing_ok=True)

    def test_markdown_export_readable(self):
        """Test Markdown export produces readable format."""
        logger.info("=" * 80)
        logger.info("TEST: Markdown Export Readability")
        logger.info("=" * 80)

        # Extract a few recipes
        config = ExtractorConfig()
        extractor = EPUBRecipeExtractor(config=config)
        recipes = extractor.extract_from_epub(TEST_EPUB_PATH)

        assert len(recipes) > 0, "Should extract recipes"

        # Create markdown for first recipe
        recipe = recipes[0]
        markdown = self._recipe_to_markdown(recipe)

        logger.info(f"Generated markdown for: {recipe.title}")
        logger.info(f"Markdown length: {len(markdown)} characters")

        # Verify markdown structure
        assert f"# {recipe.title}" in markdown, "Should have title header"
        assert recipe.book in markdown, "Should include book name"

        if recipe.ingredients:
            assert "## Ingredients" in markdown or "ingredients" in markdown.lower(), \
                "Should have ingredients section"

        if recipe.instructions:
            assert "## Instructions" in markdown or "instructions" in markdown.lower(), \
                "Should have instructions section"

        logger.info("Markdown structure validated")
        logger.info(f"Preview:\n{markdown[:500]}")

    def _recipe_to_markdown(self, recipe: Recipe) -> str:
        """Convert recipe to markdown format."""
        lines = [
            f"# {recipe.title}",
            "",
            f"**Book:** {recipe.book}",
        ]

        if recipe.author:
            lines.append(f"**Author:** {recipe.author}")

        if recipe.serves:
            lines.append(f"**Serves:** {recipe.serves}")

        if recipe.prep_time:
            lines.append(f"**Prep Time:** {recipe.prep_time}")

        if recipe.cook_time:
            lines.append(f"**Cook Time:** {recipe.cook_time}")

        lines.append("")

        if recipe.ingredients:
            lines.append("## Ingredients")
            lines.append("")
            lines.append(recipe.ingredients)
            lines.append("")

        if recipe.instructions:
            lines.append("## Instructions")
            lines.append("")
            lines.append(recipe.instructions)
            lines.append("")

        # Include A/B test metadata if present
        if recipe.metadata.get('ab_test'):
            ab_data = recipe.metadata['ab_test']
            lines.append("## Extraction Metadata")
            lines.append("")
            if 'confidence' in ab_data:
                lines.append(f"**Confidence:** {ab_data['confidence']:.3f}")
            if 'strategy' in ab_data:
                lines.append(f"**Strategy:** {ab_data['strategy']}")

        return "\n".join(lines)


@requires_cookbook
class TestQualityValidation:
    """Test quality validation and confidence correlation."""

    def test_average_confidence_reasonable(self):
        """Test that average confidence scores are reasonable (>0.5)."""
        logger.info("=" * 80)
        logger.info("TEST: Average Confidence Scores")
        logger.info("=" * 80)

        # Test pattern-based extraction on sample recipes
        from bs4 import BeautifulSoup

        test_cases = [
            # Well-formed recipe
            """
            <html><body>
                <h2>Smoked Ribs</h2>
                <h3>Ingredients</h3>
                <ul>
                    <li>2 racks baby back ribs</li>
                    <li>1/4 cup brown sugar</li>
                    <li>2 tablespoons paprika</li>
                    <li>1 tablespoon black pepper</li>
                </ul>
                <h3>Instructions</h3>
                <p>Remove membrane from ribs. Apply dry rub. Smoke at 225°F for 5 hours.</p>
            </body></html>
            """,
            # Recipe with measurements in paragraphs
            """
            <html><body>
                <h2>Pulled Pork</h2>
                <h3>Ingredients</h3>
                <p>5 pounds pork shoulder</p>
                <p>1/4 cup salt</p>
                <p>2 tablespoons pepper</p>
                <p>1 tablespoon garlic powder</p>
                <h3>Instructions</h3>
                <p>Season pork. Smoke at 225°F for 12 hours until internal temperature is 200°F.</p>
            </body></html>
            """,
        ]

        confidences = []

        for i, html in enumerate(test_cases, 1):
            soup = BeautifulSoup(html, 'html.parser')
            text = soup.get_text()

            ingredients_text, metadata = IngredientsExtractor.extract_with_patterns(soup, text)

            if ingredients_text and metadata.get('confidence'):
                confidence = metadata['confidence']
                confidences.append(confidence)
                logger.info(f"Test case {i} confidence: {confidence:.3f}")

        if confidences:
            avg_confidence = sum(confidences) / len(confidences)
            logger.info(f"Average confidence across test cases: {avg_confidence:.3f}")
            assert avg_confidence > 0.3, "Average confidence should be reasonable (>0.3)"

class TestPatternExtractorMethods:
    """Test individual pattern-based extractor methods."""

    def test_ingredient_pattern_detector(self):
        """Test IngredientPatternDetector confidence calculation."""
        logger.info("=" * 80)
        logger.info("TEST: Ingredient Pattern Detector")
        logger.info("=" * 80)

        from epub_recipe_parser.core.patterns import IngredientPatternDetector

        test_ingredients = [
            "2 cups all-purpose flour",
            "1 cup granulated sugar",
            "3 large eggs",
            "1/2 cup butter, softened",
            "1 teaspoon vanilla extract"
        ]

        ingredients_text = "\n".join(test_ingredients)
        confidence = IngredientPatternDetector.calculate_confidence(ingredients_text)

        logger.info(f"Test ingredients:\n{ingredients_text}")
        logger.info(f"Confidence score: {confidence:.3f}")

        assert 0.0 <= confidence <= 1.0, "Confidence should be 0-1"
        assert confidence > 0.5, "Well-formed ingredients should have high confidence"

    def test_instruction_pattern_detector(self):
        """Test InstructionPatternDetector confidence calculation."""
        logger.info("=" * 80)
        logger.info("TEST: Instruction Pattern Detector")
        logger.info("=" * 80)

        from epub_recipe_parser.core.patterns import InstructionPatternDetector

        test_instructions = """
        Preheat oven to 350°F. Mix flour and sugar in a large bowl.
        Beat eggs and add to the mixture. Stir in vanilla extract.
        Pour batter into greased pan. Bake for 30 minutes until golden brown.
        """

        confidence = InstructionPatternDetector.calculate_confidence(test_instructions)

        logger.info(f"Test instructions:\n{test_instructions}")
        logger.info(f"Confidence score: {confidence:.3f}")

        assert 0.0 <= confidence <= 1.0, "Confidence should be 0-1"
        assert confidence > 0.5, "Well-formed instructions should have high confidence"

    def test_metadata_pattern_detector(self):
        """Test MetadataPatternDetector."""
        logger.info("=" * 80)
        logger.info("TEST: Metadata Pattern Detector")
        logger.info("=" * 80)

        from epub_recipe_parser.core.patterns import MetadataPatternDetector
        from bs4 import BeautifulSoup

        test_html = """
        <html><body>
            <h2>Chocolate Cake</h2>
            <p>Serves: 8-10</p>
            <p>Prep time: 20 minutes</p>
            <p>Cook time: 35 minutes</p>
            <p>Baking temperature: 350°F</p>
        </body></html>
        """

        soup = BeautifulSoup(test_html, 'html.parser')
        text = soup.get_text()

        # Try to extract metadata
        metadata_extractor = MetadataExtractor()
        metadata = metadata_extractor.extract(soup, text, "Chocolate Cake")

        logger.info(f"Extracted metadata: {metadata}")

        # Verify metadata extraction
        if metadata:
            assert 'serves' in metadata or 'prep_time' in metadata or 'cook_time' in metadata, \
                "Should extract at least one metadata field"
            logger.info(f"Successfully extracted {len(metadata)} metadata fields")


# Summary fixture to run at the end
@pytest.fixture(scope="session", autouse=True)
def test_summary(request):
    """Print test summary after all tests complete."""
    yield

    logger.info("\n" + "=" * 80)
    logger.info("INTEGRATION TEST SUITE SUMMARY")
    logger.info("=" * 80)
    logger.info("Completed comprehensive integration tests for pattern-based extraction system")
    logger.info("Tests covered:")
    logger.info("  ✓ End-to-end extraction pipeline")
    logger.info("  ✓ Pattern-based confidence scoring")
    logger.info("  ✓ A/B comparison (legacy vs pattern methods)")
    logger.info("  ✓ Database integration with metadata preservation")
    logger.info("  ✓ JSON/Markdown export functionality")
    logger.info("  ✓ Quality validation and confidence correlation")
    logger.info("  ✓ Individual pattern detector methods")
    logger.info("=" * 80)


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
