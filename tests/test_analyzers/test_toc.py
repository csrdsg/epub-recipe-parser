"""Tests for TOC analyzer."""

import pytest
from unittest.mock import Mock, patch

from epub_recipe_parser.analyzers.toc import TOCAnalyzer, TOCEntry, ValidationReport
from epub_recipe_parser.core.models import Recipe


def test_is_likely_recipe_valid():
    """Test identifying valid recipe titles."""
    assert TOCAnalyzer.is_likely_recipe("Grilled Chicken Breast") is True
    assert TOCAnalyzer.is_likely_recipe("Beef Steak with Sauce") is True
    assert TOCAnalyzer.is_likely_recipe("Simple Salad") is True


def test_is_likely_recipe_excludes_meta():
    """Test excluding meta content."""
    assert TOCAnalyzer.is_likely_recipe("Introduction") is False
    assert TOCAnalyzer.is_likely_recipe("Index") is False
    assert TOCAnalyzer.is_likely_recipe("Table of Contents") is False
    assert TOCAnalyzer.is_likely_recipe("About the Author") is False


def test_is_likely_recipe_excludes_chapters():
    """Test excluding chapter titles."""
    assert TOCAnalyzer.is_likely_recipe("Chapter 1") is False
    assert TOCAnalyzer.is_likely_recipe("Part 2") is False


def test_is_likely_recipe_excludes_short():
    """Test excluding very short titles."""
    assert TOCAnalyzer.is_likely_recipe("A") is False
    assert TOCAnalyzer.is_likely_recipe("1") is False


def test_is_likely_recipe_with_food_indicators():
    """Test recipe detection with food keywords."""
    assert TOCAnalyzer.is_likely_recipe("Chicken Stir Fry") is True
    assert TOCAnalyzer.is_likely_recipe("Salmon Pasta") is True
    assert TOCAnalyzer.is_likely_recipe("Chocolate Cake") is True
    assert TOCAnalyzer.is_likely_recipe("Roasted Vegetables") is True


def test_fuzzy_match_exact():
    """Test fuzzy matching with exact match."""
    score = TOCAnalyzer.fuzzy_match("Grilled Chicken", "Grilled Chicken")
    assert score >= 0.95


def test_fuzzy_match_similar():
    """Test fuzzy matching with similar strings."""
    score = TOCAnalyzer.fuzzy_match("Grilled Chicken Breast", "Grilled Chicken")
    assert score > 0.6


def test_fuzzy_match_different():
    """Test fuzzy matching with different strings."""
    score = TOCAnalyzer.fuzzy_match("Grilled Chicken", "Beef Steak")
    assert score < 0.4


def test_fuzzy_match_ignores_case():
    """Test that fuzzy matching is case-insensitive."""
    score = TOCAnalyzer.fuzzy_match("GRILLED CHICKEN", "grilled chicken")
    assert score >= 0.95


def test_fuzzy_match_ignores_punctuation():
    """Test that fuzzy matching ignores punctuation."""
    score = TOCAnalyzer.fuzzy_match("Grilled Chicken!", "Grilled Chicken")
    assert score >= 0.9


def test_toc_entry_creation():
    """Test creating TOCEntry instances."""
    entry = TOCEntry(title="Test Recipe", href="recipe.xhtml", category="Main Dishes", level=1)
    assert entry.title == "Test Recipe"
    assert entry.href == "recipe.xhtml"
    assert entry.category == "Main Dishes"
    assert entry.level == 1


class TestExtractTocRecipes:
    """Test extract_toc_recipes functionality."""

    def test_extract_toc_recipes_file_not_found(self, capsys):
        """Test extract_toc_recipes with non-existent file."""
        analyzer = TOCAnalyzer()
        result = analyzer.extract_toc_recipes("/nonexistent/file.epub")
        assert result == []

    def test_extract_toc_recipes_invalid_epub(self, tmp_path, capsys):
        """Test extract_toc_recipes with invalid EPUB."""
        analyzer = TOCAnalyzer()
        epub_file = tmp_path / "invalid.epub"
        epub_file.write_text("invalid content")

        with patch("epub_recipe_parser.analyzers.toc.epub.read_epub") as mock_read:
            mock_read.side_effect = Exception("Cannot read EPUB")
            result = analyzer.extract_toc_recipes(epub_file)

        assert result == []

    def test_extract_toc_recipes_no_toc(self, tmp_path):
        """Test extract_toc_recipes with EPUB that has no TOC."""
        analyzer = TOCAnalyzer()
        epub_file = tmp_path / "no_toc.epub"
        epub_file.write_text("valid epub")

        mock_book = Mock()
        mock_book.toc = None

        with patch("epub_recipe_parser.analyzers.toc.epub.read_epub", return_value=mock_book):
            result = analyzer.extract_toc_recipes(epub_file)

        assert result == []

    def test_extract_toc_recipes_empty_toc(self, tmp_path):
        """Test extract_toc_recipes with empty TOC."""
        analyzer = TOCAnalyzer()
        epub_file = tmp_path / "empty_toc.epub"
        epub_file.write_text("valid epub")

        mock_book = Mock()
        mock_book.toc = []

        with patch("epub_recipe_parser.analyzers.toc.epub.read_epub", return_value=mock_book):
            result = analyzer.extract_toc_recipes(epub_file)

        assert result == []

    def test_extract_toc_recipes_simple_toc(self, tmp_path):
        """Test extract_toc_recipes with simple TOC entries."""
        analyzer = TOCAnalyzer()
        epub_file = tmp_path / "simple.epub"
        epub_file.write_text("valid epub")

        mock_item1 = Mock()
        mock_item1.title = "Grilled Chicken"
        mock_item1.href = "recipe1.xhtml"

        mock_item2 = Mock()
        mock_item2.title = "Baked Salmon"
        mock_item2.href = "recipe2.xhtml"

        mock_item3 = Mock()
        mock_item3.title = "Introduction"
        mock_item3.href = "intro.xhtml"

        mock_book = Mock()
        mock_book.toc = [mock_item1, mock_item2, mock_item3]

        with patch("epub_recipe_parser.analyzers.toc.epub.read_epub", return_value=mock_book):
            result = analyzer.extract_toc_recipes(epub_file)

        # Should extract only recipes (not introduction)
        assert len(result) == 2
        assert result[0].title == "Grilled Chicken"
        assert result[1].title == "Baked Salmon"

    def test_extract_toc_recipes_nested_toc(self, tmp_path):
        """Test extract_toc_recipes with nested TOC structure."""
        analyzer = TOCAnalyzer()
        epub_file = tmp_path / "nested.epub"
        epub_file.write_text("valid epub")

        mock_recipe1 = Mock()
        mock_recipe1.title = "Chicken Soup"
        mock_recipe1.href = "recipe1.xhtml"

        mock_recipe2 = Mock()
        mock_recipe2.title = "Beef Stew"
        mock_recipe2.href = "recipe2.xhtml"

        mock_section = Mock()
        mock_section.title = "Main Dishes"

        mock_book = Mock()
        # Nested structure: (section, [children])
        mock_book.toc = [(mock_section, [mock_recipe1, mock_recipe2])]

        with patch("epub_recipe_parser.analyzers.toc.epub.read_epub", return_value=mock_book):
            result = analyzer.extract_toc_recipes(epub_file)

        assert len(result) == 2
        assert result[0].title == "Chicken Soup"
        assert result[0].category == "Main Dishes"
        assert result[1].title == "Beef Stew"
        assert result[1].category == "Main Dishes"


class TestValidateExtraction:
    """Test validate_extraction functionality."""

    def test_validate_extraction_perfect_match(self, tmp_path):
        """Test validation with perfect match."""
        analyzer = TOCAnalyzer()
        epub_file = tmp_path / "test.epub"
        epub_file.write_text("valid epub")

        recipes = [
            Recipe(
                title="Grilled Chicken", book="Test Book", author="Test Author",
                chapter="Poultry Recipes",
            ),
            Recipe(title="Baked Salmon", book="Test Book", author="Test Author"),
        ]

        mock_item1 = Mock()
        mock_item1.title = "Grilled Chicken"
        mock_item1.href = "recipe1.xhtml"

        mock_item2 = Mock()
        mock_item2.title = "Baked Salmon"
        mock_item2.href = "recipe2.xhtml"

        mock_chapter = Mock(title="Poultry Recipes", href="poultry.xhtml")
        mock_book = Mock()
        mock_book.toc = [mock_chapter, mock_item1, mock_item2]

        with patch("epub_recipe_parser.analyzers.toc.epub.read_epub", return_value=mock_book):
            report = analyzer.validate_extraction(recipes, epub_file)

        assert report.toc_count == 2
        assert report.extracted_count == 2
        assert report.matched == 2
        assert report.coverage == 1.0
        assert len(report.missing) == 0

    def test_validate_extraction_partial_match(self, tmp_path):
        """Test validation with partial matches."""
        analyzer = TOCAnalyzer()
        epub_file = tmp_path / "test.epub"
        epub_file.write_text("valid epub")

        recipes = [
            Recipe(title="Grilled Chicken", book="Test Book", author="Test Author"),
        ]

        mock_item1 = Mock()
        mock_item1.title = "Grilled Chicken"
        mock_item1.href = "recipe1.xhtml"

        mock_item2 = Mock()
        mock_item2.title = "Baked Salmon"
        mock_item2.href = "recipe2.xhtml"

        mock_item3 = Mock()
        mock_item3.title = "Roasted Beef"
        mock_item3.href = "recipe3.xhtml"

        mock_book = Mock()
        mock_book.toc = [mock_item1, mock_item2, mock_item3]

        with patch("epub_recipe_parser.analyzers.toc.epub.read_epub", return_value=mock_book):
            report = analyzer.validate_extraction(recipes, epub_file)

        assert report.toc_count == 3
        assert report.extracted_count == 1
        assert report.matched == 1
        assert report.coverage == pytest.approx(0.333, rel=0.01)
        assert len(report.missing) == 2

    def test_validate_extraction_no_toc(self, tmp_path):
        """Test validation when EPUB has no TOC."""
        analyzer = TOCAnalyzer()
        epub_file = tmp_path / "no_toc.epub"
        epub_file.write_text("valid epub")

        recipes = [
            Recipe(title="Test Recipe", book="Test Book", author="Test Author"),
        ]

        mock_book = Mock()
        mock_book.toc = []

        with patch("epub_recipe_parser.analyzers.toc.epub.read_epub", return_value=mock_book):
            report = analyzer.validate_extraction(recipes, epub_file)

        assert report.toc_count == 0
        assert report.extracted_count == 1
        assert report.matched == 0
        assert report.coverage == 0.0

    def test_validate_extraction_fuzzy_matching(self, tmp_path):
        """Test validation with fuzzy matching for similar titles."""
        analyzer = TOCAnalyzer()
        epub_file = tmp_path / "test.epub"
        epub_file.write_text("valid epub")

        # Recipe has slightly different title than TOC
        recipes = [
            Recipe(
                title="Grilled Chicken Breast with Herbs", book="Test Book", author="Test Author"
            ),
        ]

        mock_item = Mock()
        mock_item.title = "Grilled Chicken Breast"
        mock_item.href = "recipe.xhtml"

        mock_book = Mock()
        mock_book.toc = [mock_item]

        with patch("epub_recipe_parser.analyzers.toc.epub.read_epub", return_value=mock_book):
            report = analyzer.validate_extraction(recipes, epub_file)

        # Should match with fuzzy matching
        assert report.matched >= 1
        assert report.coverage > 0.7


class TestValidationReport:
    """Test ValidationReport dataclass."""

    def test_validation_report_creation(self):
        """Test creating a ValidationReport."""
        missing_entry = TOCEntry(
            title="Missing Recipe", href="missing.xhtml", category=None, level=0
        )

        report = ValidationReport(
            toc_count=10,
            extracted_count=8,
            matched=7,
            coverage=0.7,
            missing=[missing_entry],
            book_name="Test Cookbook",
        )

        assert report.toc_count == 10
        assert report.extracted_count == 8
        assert report.matched == 7
        assert report.coverage == 0.7
        assert report.book_name == "Test Cookbook"
        assert len(report.missing) == 1
        assert report.missing[0].title == "Missing Recipe"
