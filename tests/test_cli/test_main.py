"""Comprehensive tests for CLI commands."""

import pytest
import json
from click.testing import CliRunner
from unittest.mock import Mock, patch

from epub_recipe_parser import __version__
from epub_recipe_parser.cli.main import cli, _export_json, _export_markdown
from epub_recipe_parser.core.models import Recipe


@pytest.fixture
def runner():
    """Create CLI test runner."""
    return CliRunner()


@pytest.fixture
def mock_recipes():
    """Create mock recipes for testing."""
    return [
        Recipe(
            title="Grilled Chicken",
            book="Test Cookbook",
            author="Test Author",
            chapter="Chapter 1",
            ingredients="- 2 pounds chicken\n- Salt",
            instructions="1. Grill chicken\n2. Serve hot",
            serves="4",
            prep_time="10 minutes",
            cook_time="15 minutes",
            cooking_method="grill",
        ),
        Recipe(
            title="Baked Salmon",
            book="Test Cookbook",
            author="Test Author",
            chapter="Chapter 2",
            ingredients="- 1 salmon fillet\n- Lemon",
            instructions="1. Bake salmon\n2. Add lemon",
            serves="2",
            prep_time="5 minutes",
            cook_time="20 minutes",
            cooking_method="bake",
        ),
    ]


class TestCLIVersion:
    """Test CLI version command."""

    def test_version_option(self, runner):
        """Test --version option displays version."""
        result = runner.invoke(cli, ["--version"])
        assert result.exit_code == 0
        assert result.output.strip() == f"cli, version {__version__}"


class TestExtractCommand:
    """Test extract command."""

    def test_extract_success(self, runner, tmp_path, mock_recipes):
        """Test successful recipe extraction."""
        epub_file = tmp_path / "test.epub"
        epub_file.write_text("dummy epub")
        output_db = tmp_path / "recipes.db"

        with patch("epub_recipe_parser.cli.main.EPUBRecipeExtractor") as mock_extractor_class:
            mock_extractor = Mock()
            mock_extractor.extract_from_epub.return_value = mock_recipes
            mock_extractor_class.return_value = mock_extractor

            with patch("epub_recipe_parser.cli.main.RecipeDatabase") as mock_db_class:
                mock_db = Mock()
                mock_db.save_recipes.return_value = 2
                mock_db_class.return_value = mock_db

                result = runner.invoke(cli, ["extract", str(epub_file), "--output", str(output_db)])

        assert result.exit_code == 0
        assert "extracted 2 recipes" in result.output
        assert "Saved 2 recipes" in result.output

    def test_extract_no_recipes_found(self, runner, tmp_path):
        """Test extract when no recipes are found."""
        epub_file = tmp_path / "empty.epub"
        epub_file.write_text("dummy epub")

        with patch("epub_recipe_parser.cli.main.EPUBRecipeExtractor") as mock_extractor_class:
            mock_extractor = Mock()
            mock_extractor.extract_from_epub.return_value = []
            mock_extractor_class.return_value = mock_extractor

            result = runner.invoke(cli, ["extract", str(epub_file)])

        assert result.exit_code == 0
        assert "No recipes found" in result.output

    def test_extract_file_not_found(self, runner):
        """Test extract with non-existent file."""
        result = runner.invoke(cli, ["extract", "/nonexistent/file.epub"])
        # Click handles file existence checking
        assert result.exit_code != 0


class TestBatchCommand:
    """Test batch command."""

    def test_batch_success(self, runner, tmp_path, mock_recipes):
        """Test successful batch processing."""
        # Create test EPUB files
        epub1 = tmp_path / "book1.epub"
        epub2 = tmp_path / "book2.epub"
        epub1.write_text("dummy epub 1")
        epub2.write_text("dummy epub 2")

        with patch("epub_recipe_parser.cli.main.EPUBRecipeExtractor") as mock_extractor_class:
            mock_extractor = Mock()
            mock_extractor.extract_from_epub.return_value = mock_recipes
            mock_extractor_class.return_value = mock_extractor

            with patch("epub_recipe_parser.cli.main.RecipeDatabase") as mock_db_class:
                mock_db = Mock()
                mock_db.save_recipes.return_value = 2
                mock_db_class.return_value = mock_db

                result = runner.invoke(cli, ["batch", str(tmp_path)])

        assert result.exit_code == 0
        assert ("Batch Processing" in result.output or "Files: 2" in result.output)
        assert "Total recipes extracted: 4" in result.output

    def test_batch_no_files_found(self, runner, tmp_path):
        """Test batch when no EPUB files are found."""
        result = runner.invoke(cli, ["batch", str(tmp_path)])
        assert result.exit_code == 0
        assert "No EPUB files found" in result.output

    def test_batch_with_custom_pattern(self, runner, tmp_path, mock_recipes):
        """Test batch with custom file pattern."""
        # Create test files
        epub1 = tmp_path / "cookbook.epub"
        txt1 = tmp_path / "readme.txt"
        epub1.write_text("dummy epub")
        txt1.write_text("not epub")

        with patch("epub_recipe_parser.cli.main.EPUBRecipeExtractor") as mock_extractor_class:
            mock_extractor = Mock()
            mock_extractor.extract_from_epub.return_value = mock_recipes
            mock_extractor_class.return_value = mock_extractor

            with patch("epub_recipe_parser.cli.main.RecipeDatabase") as mock_db_class:
                mock_db = Mock()
                mock_db.save_recipes.return_value = 2
                mock_db_class.return_value = mock_db

                result = runner.invoke(cli, ["batch", str(tmp_path), "--pattern", "cookbook.epub"])

        assert result.exit_code == 0
        assert ("Batch Processing" in result.output or "Files: 1" in result.output)

class TestAnalyzeCommand:
    """Test analyze command."""

    def test_analyze_success(self, runner, tmp_path):
        """Test successful EPUB analysis."""
        epub_file = tmp_path / "test.epub"
        epub_file.write_text("dummy epub")

        mock_report = Mock()
        mock_report.epub_name = "test.epub"
        mock_report.title = "Test Cookbook"
        mock_report.author = "Test Author"

        with patch("epub_recipe_parser.cli.main.EPUBStructureAnalyzer") as mock_analyzer_class:
            mock_analyzer = Mock()
            mock_analyzer.analyze_structure.return_value = mock_report
            mock_analyzer.print_report.return_value = None
            mock_analyzer_class.return_value = mock_analyzer

            result = runner.invoke(cli, ["analyze", str(epub_file)])

        assert result.exit_code == 0
        assert "Analyzing" in result.output
        mock_analyzer.analyze_structure.assert_called_once_with(str(epub_file))
        mock_analyzer.print_report.assert_called_once_with(mock_report)


class TestValidateCommand:
    """Test validate command."""

    def test_validate_success(self, runner, tmp_path, mock_recipes):
        """Test successful validation."""
        epub_file = tmp_path / "test.epub"
        db_file = tmp_path / "recipes.db"
        epub_file.write_text("dummy epub")
        db_file.write_text("dummy db")

        mock_report = Mock()
        mock_report.toc_count = 10
        mock_report.extracted_count = 8
        mock_report.matched = 7
        mock_report.coverage = 0.7
        mock_report.missing = []

        with patch("epub_recipe_parser.cli.main.RecipeDatabase") as mock_db_class:
            mock_db = Mock()
            mock_db.query.return_value = mock_recipes
            mock_db_class.return_value = mock_db

            with patch("epub_recipe_parser.cli.main.TOCAnalyzer") as mock_analyzer_class:
                mock_analyzer = Mock()
                mock_analyzer.validate_extraction.return_value = mock_report
                mock_analyzer_class.return_value = mock_analyzer

                result = runner.invoke(cli, ["validate", str(epub_file), str(db_file)])

        assert result.exit_code == 0
        assert "Validation Results" in result.output
        assert "Likely recipe entries in the TOC: 10" in result.output
        assert "Recipes extracted: 8" in result.output
        assert "TOC match rate: 70.0%" in result.output

    def test_validate_with_missing_recipes(self, runner, tmp_path, mock_recipes):
        """Test validation with missing recipes."""
        mock_recipes[0].title = "Untitled"
        mock_recipes[0].chapter = None
        mock_recipes[0].instructions = None
        epub_file = tmp_path / "test.epub"
        db_file = tmp_path / "recipes.db"
        epub_file.write_text("dummy epub")
        db_file.write_text("dummy db")

        mock_missing = [Mock(title=f"Missing Recipe {i}") for i in range(15)]
        mock_report = Mock()
        mock_report.toc_count = 20
        mock_report.extracted_count = 5
        mock_report.matched = 5
        mock_report.coverage = 0.25
        mock_report.missing = mock_missing

        with patch("epub_recipe_parser.cli.main.RecipeDatabase") as mock_db_class:
            mock_db = Mock()
            mock_db.query.return_value = mock_recipes
            mock_db_class.return_value = mock_db

            with patch("epub_recipe_parser.cli.main.TOCAnalyzer") as mock_analyzer_class:
                mock_analyzer = Mock()
                mock_analyzer.validate_extraction.return_value = mock_report
                mock_analyzer_class.return_value = mock_analyzer

                result = runner.invoke(cli, ["validate", str(epub_file), str(db_file)])

        assert result.exit_code == 0
        assert "Unmatched TOC entries: 15" in result.output
        assert "Missing chapter: 1" in result.output
        assert "Missing title: 1" in result.output
        assert "Missing instructions: 1" in result.output
        assert "and 5 more" in result.output  # Should truncate at 10


class TestSearchCommand:
    """Test search command."""

    def test_search_success(self, runner, tmp_path, mock_recipes):
        """Test successful recipe search."""
        db_file = tmp_path / "recipes.db"
        db_file.write_text("dummy db")

        with patch("epub_recipe_parser.cli.main.RecipeDatabase") as mock_db_class:
            mock_db = Mock()
            mock_db.search.return_value = mock_recipes
            mock_db_class.return_value = mock_db

            result = runner.invoke(cli, ["search", str(db_file), "chicken"])

        assert result.exit_code == 0
        assert "Found 2 recipes" in result.output
        assert "Grilled Chicken" in result.output

    def test_search_no_results(self, runner, tmp_path):
        """Test search with no results."""
        db_file = tmp_path / "recipes.db"
        db_file.write_text("dummy db")

        with patch("epub_recipe_parser.cli.main.RecipeDatabase") as mock_db_class:
            mock_db = Mock()
            mock_db.search.return_value = []
            mock_db_class.return_value = mock_db

            result = runner.invoke(cli, ["search", str(db_file), "pizza"])

        assert result.exit_code == 0
        assert "No recipes found for 'pizza'" in result.output

    def test_search_with_limit(self, runner, tmp_path, mock_recipes):
        """Test search with custom limit."""
        db_file = tmp_path / "recipes.db"
        db_file.write_text("dummy db")

        with patch("epub_recipe_parser.cli.main.RecipeDatabase") as mock_db_class:
            mock_db = Mock()
            mock_db.search.return_value = [mock_recipes[0]]
            mock_db_class.return_value = mock_db

            result = runner.invoke(cli, ["search", str(db_file), "chicken", "--limit", "1"])

        assert result.exit_code == 0
        # Updated to include tags parameter added in improvements
        mock_db.search.assert_called_once_with("chicken", limit=1, tags=None)


class TestExportCommand:
    """Test export command."""

    def test_export_json_success(self, runner, tmp_path, mock_recipes):
        """Test successful JSON export."""
        db_file = tmp_path / "recipes.db"
        output_file = tmp_path / "export.json"
        db_file.write_text("dummy db")

        with patch("epub_recipe_parser.cli.main.RecipeDatabase") as mock_db_class:
            mock_db = Mock()
            mock_db.query.return_value = mock_recipes
            mock_db_class.return_value = mock_db

            result = runner.invoke(
                cli, ["export", str(db_file), "--format", "json", "--output", str(output_file)]
            )

        assert result.exit_code == 0
        assert ("exported 2 recipes" in result.output or "Successfully exported 2" in result.output)
        assert output_file.exists()

        # Check JSON content
        with open(output_file) as f:
            data = json.load(f)
        assert data["metadata"]["count"] == 2
        assert len(data["recipes"]) == 2

    def test_export_markdown_success(self, runner, tmp_path, mock_recipes):
        """Test successful Markdown export."""
        db_file = tmp_path / "recipes.db"
        output_file = tmp_path / "export.md"
        db_file.write_text("dummy db")

        with patch("epub_recipe_parser.cli.main.RecipeDatabase") as mock_db_class:
            mock_db = Mock()
            mock_db.query.return_value = mock_recipes
            mock_db_class.return_value = mock_db

            result = runner.invoke(
                cli, ["export", str(db_file), "--format", "markdown", "--output", str(output_file)]
            )

        assert result.exit_code == 0
        assert ("exported 2 recipes" in result.output or "Successfully exported 2" in result.output)
        assert output_file.exists()

        # Check markdown content
        content = output_file.read_text()
        assert "# Recipe Collection" in content
        assert "Total Recipes: 2" in content
        assert "Grilled Chicken" in content
        assert "Baked Salmon" in content

    def test_export_default_output_filename(self, runner, tmp_path, mock_recipes):
        """Test export with default output filename."""
        db_file = tmp_path / "recipes.db"
        db_file.write_text("dummy db")

        with patch("epub_recipe_parser.cli.main.RecipeDatabase") as mock_db_class:
            mock_db = Mock()
            mock_db.query.return_value = mock_recipes
            mock_db_class.return_value = mock_db

            with runner.isolated_filesystem(temp_dir=tmp_path):
                result = runner.invoke(cli, ["export", str(db_file), "--format", "json"])

        assert result.exit_code == 0
        assert "recipes.json" in result.output

    def test_export_no_recipes(self, runner, tmp_path):
        """Test export when no recipes are found."""
        db_file = tmp_path / "empty.db"
        db_file.write_text("dummy db")

        with patch("epub_recipe_parser.cli.main.RecipeDatabase") as mock_db_class:
            mock_db = Mock()
            mock_db.query.return_value = []
            mock_db_class.return_value = mock_db

            result = runner.invoke(cli, ["export", str(db_file), "--format", "json"])

        assert result.exit_code == 0
        assert "No recipes found to export" in result.output


class TestExportHelpers:
    """Test export helper functions."""

    def test_export_json_function(self, tmp_path, mock_recipes):
        """Test _export_json helper function."""
        output_file = tmp_path / "test.json"
        _export_json(mock_recipes, output_file)

        assert output_file.exists()

        with open(output_file) as f:
            data = json.load(f)

        assert data["metadata"]["count"] == 2
        assert data["metadata"]["format_version"] == "1.0"
        assert len(data["recipes"]) == 2
        assert data["recipes"][0]["title"] == "Grilled Chicken"
        assert "quality_score" not in data["recipes"][0]

    def test_export_markdown_function(self, tmp_path, mock_recipes):
        """Test _export_markdown helper function."""
        output_file = tmp_path / "test.md"
        _export_markdown(mock_recipes, output_file)

        assert output_file.exists()
        content = output_file.read_text()

        assert "# Recipe Collection" in content
        assert "Total Recipes: 2" in content
        assert "## 1. Grilled Chicken" in content
        assert "## 2. Baked Salmon" in content
        assert "### Ingredients" in content
        assert "### Instructions" in content
        assert "**Author:** Test Author" in content
        assert "**Book:** Test Cookbook" in content
        assert "Serves: 4" in content
        assert "Quality Score" not in content

    def test_export_markdown_with_notes(self, tmp_path):
        """Test markdown export includes notes when present."""
        recipe = Recipe(
            title="Test Recipe",
            book="Test Book",
            author="Test Author",
            ingredients="- Test ingredient",
            instructions="1. Test instruction",
            notes="These are test notes.",
        )

        output_file = tmp_path / "test.md"
        _export_markdown([recipe], output_file)

        content = output_file.read_text()
        assert "### Notes" in content
        assert "These are test notes." in content


def test_import_vault_directly_preserves_edited_notes(runner, tmp_path):
    from pathlib import Path

    sample = Path(__file__).resolve().parents[2] / "examples" / "sample-cookbook" / "sample.epub"
    vault = tmp_path / "Existing Vault"
    args = ["import-vault", str(sample), str(vault)]

    first = runner.invoke(cli, args)
    assert first.exit_code == 0, first.output
    assert "Added 2 recipe notes" in first.output
    note = next(vault.glob("*/Ginger-Tofu.md"))
    edited = note.read_text(encoding="utf-8") + "\nPersonal note.\n"
    note.write_text(edited, encoding="utf-8")

    second = runner.invoke(cli, args)
    assert second.exit_code == 0, second.output
    assert "Preserved 2 existing recipe notes" in second.output
    assert note.read_text(encoding="utf-8") == edited
    assert len(list(vault.glob("*/*.md"))) == 2
    assert "**Total Recipes:** 2" in (vault / "README.md").read_text(encoding="utf-8")
    assert not list(tmp_path.rglob("*.db"))
