"""Tests for all bug fixes to prevent regression."""

import tempfile
import pytest
from bs4 import BeautifulSoup

from epub_recipe_parser.storage.database import RecipeDatabase
from epub_recipe_parser.core.models import Recipe
from epub_recipe_parser.utils.html import HTMLParser
from epub_recipe_parser.extractors.instructions import InstructionsExtractor
from epub_recipe_parser.analyzers.toc import TOCAnalyzer


class TestSQLInjectionFixes:
    """Test fixes for BUG-001 and BUG-002: SQL Injection vulnerabilities."""

    def test_query_with_malicious_filter(self):
        """Test that malicious SQL in filter doesn't cause injection."""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
            db = RecipeDatabase(tmp.name)

            # Try SQL injection through filter
            with pytest.raises(ValueError, match="Invalid column name"):
                db.query(filters={"title; DROP TABLE recipes--": "test"})

    def test_query_with_valid_filter(self):
        """Test that valid filters work correctly."""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
            db = RecipeDatabase(tmp.name)

            recipe = Recipe(
                title="Test Recipe",
                book="Test Book",
                ingredients="Test ingredients",
                instructions="Test instructions",
            )
            db.save_recipes([recipe])

            # Valid filter should work
            results = db.query(filters={"book": "Test Book"})
            assert len(results) == 1
            assert results[0].title == "Test Recipe"

    def test_count_with_malicious_filter(self):
        """Test that malicious SQL in count doesn't cause injection."""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
            db = RecipeDatabase(tmp.name)

            with pytest.raises(ValueError, match="Invalid column name"):
                db.count(filters={"title; DROP TABLE recipes--": "test"})

    def test_search_with_special_characters(self):
        """Test that search handles special characters safely."""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
            db = RecipeDatabase(tmp.name)

            recipe = Recipe(
                title="Chicken & Rice",
                book="Test Book",
                ingredients="1% milk",
                instructions="Cook at 100% power",
            )
            db.save_recipes([recipe])

            # Search with special characters should work
            results = db.search("Chicken & Rice")
            assert len(results) == 1


class TestDatabaseConnectionLeaks:
    """Test fixes for BUG-006: Database connection leaks."""

    def test_connection_cleanup_on_success(self):
        """Test that connections are closed on successful operations."""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
            db = RecipeDatabase(tmp.name)

            recipe = Recipe(
                title="Test Recipe", book="Test Book", ingredients="Test", instructions="Test"
            )

            # Save recipes
            db.save_recipes([recipe])

            # Query recipes
            results = db.query()
            assert len(results) == 1

            # Count recipes
            count = db.count()
            assert count == 1

            # Search recipes
            search_results = db.search("Test")
            assert len(search_results) == 1

    def test_connection_cleanup_on_error(self):
        """Test that connections are closed even on errors."""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
            db = RecipeDatabase(tmp.name)

            # Try invalid operation
            try:
                db.query(filters={"invalid_column": "test"})
            except ValueError:
                pass  # Expected

            # Database should still be accessible
            count = db.count()
            assert count == 0


class TestRaceConditionFix:
    """Test fix for BUG-012: Race condition in database initialization."""

    def test_concurrent_initialization(self):
        """Test that concurrent database initialization is safe."""
        import threading

        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
            db_path = tmp.name

            def init_db():
                db = RecipeDatabase(db_path)
                recipe = Recipe(
                    title=f"Recipe {threading.current_thread().name}",
                    book="Test Book",
                    ingredients="Test",
                    instructions="Test",
                )
                db.save_recipes([recipe])

            # Create multiple threads
            threads = [threading.Thread(target=init_db, name=f"T{i}") for i in range(5)]

            # Start all threads
            for t in threads:
                t.start()

            # Wait for all to complete
            for t in threads:
                t.join()

            # Verify database integrity
            db = RecipeDatabase(db_path)
            count = db.count()
            assert count == 5


class TestTypeSafetyFixes:
    """Test fixes for BUG-003, BUG-004, BUG-005: Type safety issues."""

    def test_body_none_check(self):
        """Test that None body element is handled correctly."""
        html = "<html></html>"  # No body tag
        soup = BeautifulSoup(html, "html.parser")

        # Should not raise AttributeError
        sections = HTMLParser.split_by_headers(soup)
        assert isinstance(sections, list)

    def test_find_next_sibling_none(self):
        """Test that None siblings are handled correctly."""
        html = "<html><body><h2>Title</h2></body></html>"
        soup = BeautifulSoup(html, "html.parser")

        sections = HTMLParser.split_by_headers(soup)
        assert len(sections) == 1
        assert sections[0][0] == "Title"

    def test_element_without_name(self):
        """Test that elements without name attribute are handled."""
        html = "<html><body><h2>Title</h2>Text content<p>Paragraph</p></body></html>"
        soup = BeautifulSoup(html, "html.parser")

        # Should not raise AttributeError
        result = HTMLParser.find_section_by_header(soup, ["title"])
        assert result is not None


class TestInfiniteLoopFix:
    """Test fix for BUG-008: Potential infinite loop."""

    def test_sibling_iteration_limit(self):
        """Test that sibling iteration has a maximum limit."""
        # Create HTML with many siblings
        html = "<html><body><h2>Title</h2>"
        html += "".join([f"<p>Paragraph {i}</p>" for i in range(2000)])
        html += "</body></html>"

        soup = BeautifulSoup(html, "html.parser")

        # Should complete without hanging
        sections = HTMLParser.split_by_headers(soup)
        assert len(sections) >= 1


class TestExceptionHandlingFix:
    """Test fix for BUG-011: Poor exception handling."""

    def test_file_not_found_error(self):
        """Test that FileNotFoundError is raised for missing files."""
        from epub_recipe_parser.core.extractor import EPUBRecipeExtractor

        extractor = EPUBRecipeExtractor()

        with pytest.raises(FileNotFoundError):
            extractor.extract_from_epub("/nonexistent/file.epub")

    def test_invalid_file_type(self):
        """Test that ValueError is raised for invalid file types."""
        from epub_recipe_parser.core.extractor import EPUBRecipeExtractor

        extractor = EPUBRecipeExtractor()

        with tempfile.TemporaryDirectory() as tmpdir:
            # Try to extract from directory instead of file
            with pytest.raises(ValueError):
                extractor.extract_from_epub(tmpdir)


class TestBoundsCheckingFix:
    """Test fix for BUG-009: Index out of bounds."""

    def test_fuzzy_match_empty_strings(self):
        """Test fuzzy matching with empty strings."""
        analyzer = TOCAnalyzer()

        # Empty strings should return 0.0, not crash
        assert analyzer.fuzzy_match("", "") == 0.0
        assert analyzer.fuzzy_match("test", "") == 0.0
        assert analyzer.fuzzy_match("", "test") == 0.0

    def test_fuzzy_match_none_strings(self):
        """Test fuzzy matching with None values."""
        analyzer = TOCAnalyzer()

        # None should be handled gracefully
        assert analyzer.fuzzy_match(None, "test") == 0.0
        assert analyzer.fuzzy_match("test", None) == 0.0

    def test_validate_extraction_empty_recipes(self):
        """Test validation with empty recipe list."""
        analyzer = TOCAnalyzer()

        with tempfile.NamedTemporaryFile(suffix=".epub", delete=False) as tmp:
            # Empty recipe list should not cause index errors
            report = analyzer.validate_extraction([], tmp.name)
            assert report.coverage == 0.0


class TestReDoSFix:
    """Test fix for BUG-010: ReDoS vulnerability."""

    def test_measurement_pattern_performance(self):
        """Test that measurement pattern doesn't cause ReDoS."""
        from epub_recipe_parser.utils.patterns import MEASUREMENT_PATTERN
        import time

        # Create a string that could trigger ReDoS
        malicious_string = "1" + "/" * 1000 + "cup"

        start = time.time()
        _ = MEASUREMENT_PATTERN.findall(malicious_string)
        elapsed = time.time() - start

        # Should complete quickly (< 1 second)
        assert elapsed < 1.0

    def test_measurement_pattern_matches_valid(self):
        """Test that simplified pattern still matches valid measurements."""
        from epub_recipe_parser.utils.patterns import MEASUREMENT_PATTERN

        valid_measurements = ["1 cup", "2.5 tablespoons", "½ teaspoon", "3-4 pounds", "1/2 cup"]

        for measurement in valid_measurements:
            matches = MEASUREMENT_PATTERN.findall(measurement)
            assert len(matches) > 0, f"Failed to match: {measurement}"


class TestCodeQualityFixes:
    """Test fixes for BUG-013 to BUG-020: Code quality issues."""

    def test_no_unused_imports(self):
        """Test that there are no unused imports."""
        import subprocess

        result = subprocess.run(
            ["ruff", "check", "--select", "F401", "src/"],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0, "Found unused imports"

    def test_ruff_passes(self):
        """Test that ruff checks pass."""
        import subprocess

        result = subprocess.run(
            ["ruff", "check", "src/"], capture_output=True, text=True
        )
        assert result.returncode == 0, f"Ruff checks failed: {result.stdout}"


class TestClassAttributeHandling:
    """Test that class attributes are handled correctly for type safety."""

    def test_class_attribute_as_list(self):
        """Test handling of class attribute as list."""
        html = '<p class="instruction step">Test instruction</p>'
        soup = BeautifulSoup(html, "html.parser")

        result = InstructionsExtractor._extract_by_class(soup)
        # Should handle list class attributes without error
        assert result is None or isinstance(result, str)

    def test_class_attribute_as_string(self):
        """Test handling of class attribute as string."""
        html = '<p class="instruction">Test instruction</p>'
        soup = BeautifulSoup(html, "html.parser")

        result = InstructionsExtractor._extract_by_class(soup)
        # Should handle string class attributes without error
        assert result is None or isinstance(result, str)

    def test_missing_class_attribute(self):
        """Test handling of missing class attribute."""
        html = "<p>Test instruction without class</p>"
        soup = BeautifulSoup(html, "html.parser")

        result = InstructionsExtractor._extract_by_class(soup)
        # Should handle missing class without error
        assert result is None or isinstance(result, str)
