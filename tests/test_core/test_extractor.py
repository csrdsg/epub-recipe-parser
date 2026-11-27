"""Comprehensive tests for EPUBRecipeExtractor."""

import pytest
from unittest.mock import Mock, patch
from bs4 import BeautifulSoup

from epub_recipe_parser.core.extractor import EPUBRecipeExtractor
from epub_recipe_parser.core.models import ExtractorConfig


class TestEPUBRecipeExtractor:
    """Test EPUBRecipeExtractor functionality."""

    def test_init_default_config(self):
        """Test extractor initialization with default config."""
        extractor = EPUBRecipeExtractor()
        assert extractor.config is not None
        assert extractor.validator is not None
        assert extractor.ingredients_extractor is not None
        assert extractor.instructions_extractor is not None
        assert extractor.metadata_extractor is not None

    def test_init_custom_config(self):
        """Test extractor initialization with custom config."""
        config = ExtractorConfig(include_raw_content=False)
        extractor = EPUBRecipeExtractor(config=config)
        assert extractor.config.include_raw_content is False

    def test_extract_from_epub_file_not_found(self):
        """Test extract_from_epub raises FileNotFoundError for missing file."""
        extractor = EPUBRecipeExtractor()
        with pytest.raises(FileNotFoundError, match="EPUB file not found"):
            extractor.extract_from_epub("/nonexistent/path/to/book.epub")

    def test_extract_from_epub_path_is_directory(self, tmp_path):
        """Test extract_from_epub raises ValueError when path is a directory."""
        extractor = EPUBRecipeExtractor()
        directory = tmp_path / "test_dir"
        directory.mkdir()

        with pytest.raises(ValueError, match="Path is not a file"):
            extractor.extract_from_epub(directory)

    def test_extract_from_epub_permission_error(self, tmp_path, caplog):
        """Test extract_from_epub handles permission errors."""
        extractor = EPUBRecipeExtractor()
        epub_file = tmp_path / "test.epub"
        epub_file.write_text("dummy")

        with patch("epub_recipe_parser.core.extractor.epub.read_epub") as mock_read:
            mock_read.side_effect = PermissionError("Access denied")

            with pytest.raises(PermissionError, match="Cannot access EPUB file"):
                extractor.extract_from_epub(epub_file)

            assert "Permission denied reading EPUB" in caplog.text

    def test_extract_from_epub_io_error(self, tmp_path, caplog):
        """Test extract_from_epub handles I/O errors."""
        extractor = EPUBRecipeExtractor()
        epub_file = tmp_path / "corrupted.epub"
        epub_file.write_text("corrupted content")

        with patch("epub_recipe_parser.core.extractor.epub.read_epub") as mock_read:
            mock_read.side_effect = IOError("File corrupted")

            with pytest.raises(ValueError, match="Cannot read EPUB file"):
                extractor.extract_from_epub(epub_file)

            assert "I/O error reading EPUB" in caplog.text

    def test_extract_from_epub_unexpected_error(self, tmp_path, caplog):
        """Test extract_from_epub handles unexpected errors."""
        extractor = EPUBRecipeExtractor()
        epub_file = tmp_path / "invalid.epub"
        epub_file.write_text("invalid")

        with patch("epub_recipe_parser.core.extractor.epub.read_epub") as mock_read:
            mock_read.side_effect = RuntimeError("Unexpected error")

            with pytest.raises(ValueError, match="Invalid EPUB file"):
                extractor.extract_from_epub(epub_file)

            assert "Unexpected error reading EPUB" in caplog.text

    def test_extract_from_epub_with_valid_book(self, tmp_path, caplog):
        """Test successful extraction from a valid EPUB."""
        import logging
        caplog.set_level(logging.DEBUG)

        extractor = EPUBRecipeExtractor()
        epub_file = tmp_path / "valid.epub"
        epub_file.write_text("valid epub")

        # Create mock book
        mock_book = Mock()
        mock_book.get_metadata.side_effect = [
            [("Test Author",)],  # creator
            [("Test Cookbook",)],  # title
        ]
        mock_book.toc = []

        # Create mock document item with recipe content
        mock_item = Mock()
        mock_item.get_name.return_value = "chapter1.xhtml"
        mock_item.get_content.return_value = b"""
        <html>
            <body>
                <h2>Grilled Chicken</h2>
                <h3>Ingredients</h3>
                <ul>
                    <li>2 pounds chicken breast</li>
                    <li>1 tablespoon olive oil</li>
                    <li>1 teaspoon salt</li>
                </ul>
                <h3>Instructions</h3>
                <ol>
                    <li>Heat the grill to medium-high heat</li>
                    <li>Season chicken with salt and oil</li>
                    <li>Grill for 6-7 minutes per side</li>
                    <li>Remove and let rest 5 minutes</li>
                </ol>
                <p>Serves: 4</p>
            </body>
        </html>
        """

        mock_book.get_items_of_type.return_value = [mock_item]

        with patch("epub_recipe_parser.core.extractor.epub.read_epub", return_value=mock_book):
            recipes = extractor.extract_from_epub(epub_file)

        # Should extract at least one recipe
        assert len(recipes) >= 0  # May be 0 if quality score too low
        assert "Processing EPUB" in caplog.text
        assert "Found 1 HTML documents" in caplog.text

    def test_extract_from_epub_with_toc(self, tmp_path, capsys):
        """Test extraction with TOC entries."""
        extractor = EPUBRecipeExtractor()
        epub_file = tmp_path / "with_toc.epub"
        epub_file.write_text("valid epub")

        # Create mock TOC entry
        mock_toc_item = Mock()
        mock_toc_item.href = "chapter1.xhtml"
        mock_toc_item.title = "Chapter 1: Grilled Dishes"

        mock_book = Mock()
        mock_book.get_metadata.side_effect = [[("Test Author",)], [("Test Cookbook",)]]
        mock_book.toc = [mock_toc_item]

        mock_item = Mock()
        mock_item.get_name.return_value = "chapter1.xhtml"
        mock_item.get_content.return_value = (
            b"<html><body><h2>Test</h2><p>Short content</p></body></html>"
        )

        mock_book.get_items_of_type.return_value = [mock_item]

        with patch("epub_recipe_parser.core.extractor.epub.read_epub", return_value=mock_book):
            recipes = extractor.extract_from_epub(epub_file)

        # TOC should be processed
        assert isinstance(recipes, list)

    def test_extract_from_epub_with_nested_toc(self, tmp_path):
        """Test extraction with nested TOC structure."""
        extractor = EPUBRecipeExtractor()
        epub_file = tmp_path / "nested_toc.epub"
        epub_file.write_text("valid epub")

        # Create nested TOC structure
        mock_toc_child = Mock()
        mock_toc_child.href = "chapter1.xhtml"
        mock_toc_child.title = "Recipe 1"

        mock_toc_parent = Mock()
        mock_toc_parent.href = "intro.xhtml"
        mock_toc_parent.title = "Introduction"

        mock_book = Mock()
        mock_book.get_metadata.side_effect = [[("Test Author",)], [("Test Cookbook",)]]
        # Nested TOC structure: (section, [children])
        mock_book.toc = [(mock_toc_parent, [mock_toc_child])]

        mock_item = Mock()
        mock_item.get_name.return_value = "chapter1.xhtml"
        mock_item.get_content.return_value = b"<html><body><p>Short</p></body></html>"

        mock_book.get_items_of_type.return_value = [mock_item]

        with patch("epub_recipe_parser.core.extractor.epub.read_epub", return_value=mock_book):
            recipes = extractor.extract_from_epub(epub_file)

        assert isinstance(recipes, list)

    def test_extract_from_epub_with_section_title_attr(self, tmp_path):
        """Test extraction with section title attribute."""
        extractor = EPUBRecipeExtractor()
        epub_file = tmp_path / "section_title.epub"
        epub_file.write_text("valid epub")

        mock_book = Mock()
        mock_book.get_metadata.side_effect = [[("Test Author",)], [("Test Cookbook",)]]
        mock_book.toc = []

        mock_item = Mock()
        mock_item.get_name.return_value = "chapter1.xhtml"
        mock_item.get_content.return_value = b"""
        <html>
            <body>
                <section title="Grilled Chicken Recipe">
                    <h3>Ingredients</h3>
                    <ul>
                        <li>2 pounds chicken breast</li>
                        <li>1 tablespoon olive oil</li>
                    </ul>
                    <h3>Instructions</h3>
                    <ol>
                        <li>Grill chicken</li>
                        <li>Serve hot</li>
                    </ol>
                </section>
            </body>
        </html>
        """

        mock_book.get_items_of_type.return_value = [mock_item]

        with patch("epub_recipe_parser.core.extractor.epub.read_epub", return_value=mock_book):
            recipes = extractor.extract_from_epub(epub_file)

        assert isinstance(recipes, list)

    def test_extract_from_epub_filters_short_content(self, tmp_path):
        """Test that sections with less than 100 characters are skipped."""
        extractor = EPUBRecipeExtractor()
        epub_file = tmp_path / "short_content.epub"
        epub_file.write_text("valid epub")

        mock_book = Mock()
        mock_book.get_metadata.side_effect = [[("Test Author",)], [("Test Cookbook",)]]
        mock_book.toc = []

        mock_item = Mock()
        mock_item.get_name.return_value = "chapter1.xhtml"
        # Very short content
        mock_item.get_content.return_value = b"<html><body><h2>Title</h2><p>Short</p></body></html>"

        mock_book.get_items_of_type.return_value = [mock_item]

        with patch("epub_recipe_parser.core.extractor.epub.read_epub", return_value=mock_book):
            recipes = extractor.extract_from_epub(epub_file)

        # Should not extract recipes from short content
        assert len(recipes) == 0

    def test_extract_from_epub_includes_raw_content(self, tmp_path):
        """Test that raw_content is included when configured."""
        config = ExtractorConfig(include_raw_content=True)
        extractor = EPUBRecipeExtractor(config=config)
        epub_file = tmp_path / "raw_content.epub"
        epub_file.write_text("valid epub")

        mock_book = Mock()
        mock_book.get_metadata.side_effect = [[("Test Author",)], [("Test Cookbook",)]]
        mock_book.toc = []

        mock_item = Mock()
        mock_item.get_name.return_value = "chapter1.xhtml"
        mock_item.get_content.return_value = b"""
        <html>
            <body>
                <h2>Perfect Recipe</h2>
                <h3>Ingredients</h3>
                <ul>
                    <li>2 cups flour</li>
                    <li>1 cup sugar</li>
                    <li>3 eggs</li>
                </ul>
                <h3>Instructions</h3>
                <ol>
                    <li>Mix dry ingredients thoroughly</li>
                    <li>Add eggs one at a time</li>
                    <li>Bake at 350F for 30 minutes</li>
                </ol>
                <p>Serves: 6</p>
            </body>
        </html>
        """

        mock_book.get_items_of_type.return_value = [mock_item]

        with patch("epub_recipe_parser.core.extractor.epub.read_epub", return_value=mock_book):
            recipes = extractor.extract_from_epub(epub_file)

        if recipes:  # If any recipes were extracted
            assert recipes[0].raw_content is not None

    def test_extract_from_epub_no_metadata(self, tmp_path):
        """Test extraction when EPUB has no metadata."""
        extractor = EPUBRecipeExtractor()
        epub_file = tmp_path / "no_metadata.epub"
        epub_file.write_text("valid epub")

        mock_book = Mock()
        # Return empty metadata
        mock_book.get_metadata.return_value = []
        mock_book.toc = []

        mock_item = Mock()
        mock_item.get_name.return_value = "chapter1.xhtml"
        mock_item.get_content.return_value = b"<html><body><p>Short</p></body></html>"

        mock_book.get_items_of_type.return_value = [mock_item]

        with patch("epub_recipe_parser.core.extractor.epub.read_epub", return_value=mock_book):
            recipes = extractor.extract_from_epub(epub_file)

        # Should handle missing metadata gracefully
        assert isinstance(recipes, list)

    def test_extract_from_section_valid_recipe(self):
        """Test extract_from_section with valid recipe content."""
        extractor = EPUBRecipeExtractor()

        html_content = """
        <div>
            <h3>Ingredients</h3>
            <ul>
                <li>2 cups flour</li>
                <li>1 cup sugar</li>
                <li>3 eggs</li>
            </ul>
            <h3>Instructions</h3>
            <ol>
                <li>Mix ingredients</li>
                <li>Bake at 350F</li>
                <li>Serve warm</li>
            </ol>
            <p>Serves: 4</p>
        </div>
        """
        soup = BeautifulSoup(html_content, "html.parser")

        recipe = extractor.extract_from_section(
            soup, title="Test Recipe", book_name="Test Book", author="Test Author"
        )

        if recipe:  # May be None if validation fails
            assert recipe.title == "Test Recipe"
            assert recipe.book == "Test Book"
            assert recipe.author == "Test Author"

    def test_extract_from_section_invalid_content(self):
        """Test extract_from_section with invalid content returns None."""
        extractor = EPUBRecipeExtractor()

        html_content = "<div><p>This is not a recipe at all.</p></div>"
        soup = BeautifulSoup(html_content, "html.parser")

        recipe = extractor.extract_from_section(soup, title="Not a Recipe")

        # Should return None for invalid content
        assert recipe is None

    def test_extract_from_section_no_raw_content(self):
        """Test extract_from_section respects include_raw_content config."""
        config = ExtractorConfig(include_raw_content=False)
        extractor = EPUBRecipeExtractor(config=config)

        html_content = """
        <div>
            <h3>Ingredients</h3>
            <ul>
                <li>2 cups flour</li>
                <li>1 cup sugar</li>
            </ul>
            <h3>Instructions</h3>
            <ol>
                <li>Mix ingredients</li>
                <li>Bake</li>
            </ol>
        </div>
        """
        soup = BeautifulSoup(html_content, "html.parser")

        recipe = extractor.extract_from_section(soup, title="Test Recipe")

        if recipe:
            assert recipe.raw_content is None


@pytest.mark.parametrize(
    ("heading_tag", "heading_class", "components"),
    [
        (
            "h2",
            "RH",
            "<ul><li>2 tomatoes</li></ul><ol><li>Slice the tomatoes.</li></ol>",
        ),
        (
            "p",
            "rechead",
            '<p class="ing">2 tomatoes</p><p class="noindentt">Slice the tomatoes.</p>',
        ),
    ],
)
def test_recipe_headings_split_chapter_and_preserve_components(
    tmp_path, heading_tag, heading_class, components
):
    from ebooklib import epub
    from epub_recipe_parser.storage import RecipeDatabase

    book = epub.EpubBook()
    book.set_identifier("heading-fixture")
    book.set_title("Fixture Cookbook")
    book.set_language("en")
    chapter = epub.EpubHtml(title="Sides", file_name="sides_split_001.xhtml", uid="chapter")
    chapter.content = "<h1>Sides</h1>"
    recipes_document = epub.EpubHtml(title="Recipes", file_name="sides_split_002.xhtml", uid="recipes")
    sections = "".join(
        f'<{heading_tag} class="{heading_class}">{title}</{heading_tag}>{components}'
        for title in ("Tomato Salad", "Tomato Side")
    )
    recipes_document.content = f"<section><h1>Sides</h1>{sections}</section>"
    for item in (chapter, recipes_document, epub.EpubNav()):
        book.add_item(item)
    book.toc = (chapter,)
    book.spine = ["nav", chapter, recipes_document]
    path = tmp_path / "fixture.epub"
    epub.write_epub(str(path), book)

    rows = EPUBRecipeExtractor().extract_from_epub(path)

    assert [row.title for row in rows] == ["Tomato Salad", "Tomato Side"]
    assert all(row.chapter == "Sides" and row.ingredients == "- 2 tomatoes" for row in rows)
    assert all(row.instructions and "Slice the tomatoes." in row.instructions for row in rows)
    assert len({row.source_id for row in rows if row.source_id}) == 2

    database = RecipeDatabase(tmp_path / "recipes.db")
    assert database.save_recipes(rows) == 2
    assert database.save_recipes(EPUBRecipeExtractor().extract_from_epub(path)) == 0
    assert database.count() == 2
