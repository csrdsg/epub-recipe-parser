"""Comprehensive tests for EPUBStructureAnalyzer."""

import pytest
from unittest.mock import Mock, patch
import ebooklib

from epub_recipe_parser.analyzers.structure import EPUBStructureAnalyzer, StructureReport


class TestStructureReport:
    """Test StructureReport dataclass."""

    def test_structure_report_creation(self):
        """Test creating a StructureReport."""
        report = StructureReport(
            epub_name="test.epub",
            title="Test Book",
            author="Test Author",
            total_items=50,
            document_items=20,
            image_items=15,
            toc_entries=10,
            has_toc=True,
            header_distribution={"h1": 5, "h2": 10},
            recipe_indicators={"ingredients": 15, "instructions": 15},
        )

        assert report.epub_name == "test.epub"
        assert report.title == "Test Book"
        assert report.total_items == 50
        assert report.has_toc is True


class TestEPUBStructureAnalyzer:
    """Test EPUBStructureAnalyzer functionality."""

    def test_analyze_structure_success(self, tmp_path, capsys):
        """Test successful structure analysis."""
        analyzer = EPUBStructureAnalyzer()
        epub_file = tmp_path / "test.epub"
        epub_file.write_text("dummy epub")

        # Create mock book with all required attributes
        mock_book = Mock()
        mock_book.get_metadata.side_effect = [
            [("Test Cookbook",)],  # title
            [("Test Author",)],  # creator
        ]
        mock_book.toc = []

        # Create mock items
        mock_doc_item = Mock()
        mock_doc_item.get_type.return_value = ebooklib.ITEM_DOCUMENT
        mock_doc_item.get_content.return_value = b"<html><body><h2>Test</h2></body></html>"

        mock_image_item = Mock()
        mock_image_item.get_type.return_value = ebooklib.ITEM_IMAGE

        mock_book.get_items.return_value = [mock_doc_item, mock_image_item]

        with patch("epub_recipe_parser.analyzers.structure.epub.read_epub", return_value=mock_book):
            report = analyzer.analyze_structure(epub_file)

        assert report.epub_name == "test.epub"
        assert report.title == "Test Cookbook"
        assert report.author == "Test Author"
        assert report.total_items == 2
        assert report.document_items == 1
        assert report.image_items == 1
        assert report.has_toc is False
        assert report.toc_entries == 0

    def test_analyze_structure_with_toc(self, tmp_path):
        """Test structure analysis with TOC."""
        analyzer = EPUBStructureAnalyzer()
        epub_file = tmp_path / "test.epub"
        epub_file.write_text("dummy epub")

        mock_toc_item1 = Mock()
        mock_toc_item1.href = "chapter1.xhtml"

        mock_toc_item2 = Mock()
        mock_toc_item2.href = "chapter2.xhtml"

        mock_book = Mock()
        mock_book.get_metadata.side_effect = [[("Test Cookbook",)], [("Test Author",)]]
        mock_book.toc = [mock_toc_item1, mock_toc_item2]
        mock_book.get_items.return_value = []

        with patch("epub_recipe_parser.analyzers.structure.epub.read_epub", return_value=mock_book):
            report = analyzer.analyze_structure(epub_file)

        assert report.has_toc is True
        assert report.toc_entries == 2

    def test_analyze_structure_with_nested_toc(self, tmp_path):
        """Test structure analysis with nested TOC."""
        analyzer = EPUBStructureAnalyzer()
        epub_file = tmp_path / "test.epub"
        epub_file.write_text("dummy epub")

        mock_child1 = Mock()
        mock_child2 = Mock()

        mock_parent = Mock()

        mock_book = Mock()
        mock_book.get_metadata.side_effect = [[("Test Cookbook",)], [("Test Author",)]]
        # Nested structure: (parent, [children])
        mock_book.toc = [
            (mock_parent, [mock_child1, mock_child2]),
        ]
        mock_book.get_items.return_value = []

        with patch("epub_recipe_parser.analyzers.structure.epub.read_epub", return_value=mock_book):
            report = analyzer.analyze_structure(epub_file)

        assert report.has_toc is True
        # Parent + 2 children = 3 total entries
        assert report.toc_entries == 3

    def test_analyze_structure_no_metadata(self, tmp_path):
        """Test analysis when EPUB has no metadata."""
        analyzer = EPUBStructureAnalyzer()
        epub_file = tmp_path / "no_metadata.epub"
        epub_file.write_text("dummy epub")

        mock_book = Mock()
        mock_book.get_metadata.return_value = []
        mock_book.toc = []
        mock_book.get_items.return_value = []

        with patch("epub_recipe_parser.analyzers.structure.epub.read_epub", return_value=mock_book):
            report = analyzer.analyze_structure(epub_file)

        # Should use stem as title when no metadata
        assert report.title == "no_metadata"
        assert report.author == "Unknown"

    def test_analyze_structure_invalid_epub(self, tmp_path):
        """Test analysis with invalid EPUB raises ValueError."""
        analyzer = EPUBStructureAnalyzer()
        epub_file = tmp_path / "invalid.epub"
        epub_file.write_text("invalid epub content")

        with patch("epub_recipe_parser.analyzers.structure.epub.read_epub") as mock_read:
            mock_read.side_effect = Exception("Corrupted file")

            with pytest.raises(ValueError, match="Error reading EPUB"):
                analyzer.analyze_structure(epub_file)

    def test_analyze_headers(self, tmp_path):
        """Test header distribution analysis."""
        analyzer = EPUBStructureAnalyzer()
        epub_file = tmp_path / "test.epub"
        epub_file.write_text("dummy epub")

        mock_doc_item = Mock()
        mock_doc_item.get_type.return_value = ebooklib.ITEM_DOCUMENT
        mock_doc_item.get_content.return_value = b"""
        <html>
            <body>
                <h1>Main Title</h1>
                <h2>Section 1</h2>
                <h3>Subsection 1.1</h3>
                <h3>Subsection 1.2</h3>
                <h2>Section 2</h2>
            </body>
        </html>
        """

        mock_book = Mock()
        mock_book.get_metadata.side_effect = [[("Test Cookbook",)], [("Test Author",)]]
        mock_book.toc = []
        mock_book.get_items.return_value = [mock_doc_item]

        with patch("epub_recipe_parser.analyzers.structure.epub.read_epub", return_value=mock_book):
            report = analyzer.analyze_structure(epub_file)

        assert report.header_distribution["h1"] == 1
        assert report.header_distribution["h2"] == 2
        assert report.header_distribution["h3"] == 2
        assert report.header_distribution["h4"] == 0

    def test_analyze_headers_with_error(self, tmp_path):
        """Test header analysis handles item errors gracefully."""
        analyzer = EPUBStructureAnalyzer()
        epub_file = tmp_path / "test.epub"
        epub_file.write_text("dummy epub")

        # First item is good, second raises error
        mock_good_item = Mock()
        mock_good_item.get_type.return_value = ebooklib.ITEM_DOCUMENT
        mock_good_item.get_content.return_value = b"<html><body><h1>Title</h1></body></html>"

        mock_bad_item = Mock()
        mock_bad_item.get_type.return_value = ebooklib.ITEM_DOCUMENT
        mock_bad_item.get_content.side_effect = Exception("Cannot read item")

        mock_book = Mock()
        mock_book.get_metadata.side_effect = [[("Test Cookbook",)], [("Test Author",)]]
        mock_book.toc = []
        mock_book.get_items.return_value = [mock_good_item, mock_bad_item]

        with patch("epub_recipe_parser.analyzers.structure.epub.read_epub", return_value=mock_book):
            report = analyzer.analyze_structure(epub_file)

        # Should still analyze the good item
        assert report.header_distribution["h1"] == 1

    def test_detect_recipe_patterns(self, tmp_path):
        """Test recipe pattern detection."""
        analyzer = EPUBStructureAnalyzer()
        epub_file = tmp_path / "test.epub"
        epub_file.write_text("dummy epub")

        mock_doc_item = Mock()
        mock_doc_item.get_type.return_value = ebooklib.ITEM_DOCUMENT
        mock_doc_item.get_content.return_value = b"""
        <html>
            <body>
                <h2>Grilled Chicken</h2>
                <h3>Ingredients</h3>
                <ul>
                    <li>Chicken</li>
                </ul>
                <h3>Instructions</h3>
                <ol>
                    <li>Grill chicken</li>
                </ol>
                <p>Serves: 4</p>
                <p>Prep time: 10 minutes</p>
                <p>Cook time: 15 minutes</p>
            </body>
        </html>
        """

        mock_book = Mock()
        mock_book.get_metadata.side_effect = [[("Test Cookbook",)], [("Test Author",)]]
        mock_book.toc = []
        mock_book.get_items.return_value = [mock_doc_item]

        with patch("epub_recipe_parser.analyzers.structure.epub.read_epub", return_value=mock_book):
            report = analyzer.analyze_structure(epub_file)

        assert report.recipe_indicators["ingredients"] == 1
        assert report.recipe_indicators["instructions"] == 1
        assert report.recipe_indicators["serves"] == 1
        assert report.recipe_indicators["prep time"] == 1
        assert report.recipe_indicators["cook time"] == 1

    def test_detect_recipe_patterns_multiple_docs(self, tmp_path):
        """Test recipe pattern detection across multiple documents."""
        analyzer = EPUBStructureAnalyzer()
        epub_file = tmp_path / "test.epub"
        epub_file.write_text("dummy epub")

        mock_doc1 = Mock()
        mock_doc1.get_type.return_value = ebooklib.ITEM_DOCUMENT
        mock_doc1.get_content.return_value = b"<html><body>Ingredients: flour, sugar</body></html>"

        mock_doc2 = Mock()
        mock_doc2.get_type.return_value = ebooklib.ITEM_DOCUMENT
        mock_doc2.get_content.return_value = (
            b"<html><body>Directions: mix and bake. Yield: 12 servings</body></html>"
        )

        mock_book = Mock()
        mock_book.get_metadata.side_effect = [[("Test Cookbook",)], [("Test Author",)]]
        mock_book.toc = []
        mock_book.get_items.return_value = [mock_doc1, mock_doc2]

        with patch("epub_recipe_parser.analyzers.structure.epub.read_epub", return_value=mock_book):
            report = analyzer.analyze_structure(epub_file)

        assert report.recipe_indicators["ingredients"] == 1
        assert report.recipe_indicators["directions"] == 1
        assert report.recipe_indicators["yield"] == 1

    def test_detect_recipe_patterns_with_error(self, tmp_path):
        """Test recipe pattern detection handles errors gracefully."""
        analyzer = EPUBStructureAnalyzer()
        epub_file = tmp_path / "test.epub"
        epub_file.write_text("dummy epub")

        mock_good_item = Mock()
        mock_good_item.get_type.return_value = ebooklib.ITEM_DOCUMENT
        mock_good_item.get_content.return_value = b"Ingredients: test"

        mock_bad_item = Mock()
        mock_bad_item.get_type.return_value = ebooklib.ITEM_DOCUMENT
        mock_bad_item.get_content.side_effect = Exception("Cannot read")

        mock_book = Mock()
        mock_book.get_metadata.side_effect = [[("Test Cookbook",)], [("Test Author",)]]
        mock_book.toc = []
        mock_book.get_items.return_value = [mock_good_item, mock_bad_item]

        with patch("epub_recipe_parser.analyzers.structure.epub.read_epub", return_value=mock_book):
            report = analyzer.analyze_structure(epub_file)

        # Should still detect patterns in good item
        assert report.recipe_indicators["ingredients"] == 1

    def test_print_report(self, capsys):
        """Test print_report output."""
        analyzer = EPUBStructureAnalyzer()

        report = StructureReport(
            epub_name="test_cookbook.epub",
            title="Test Cookbook",
            author="John Doe",
            total_items=100,
            document_items=50,
            image_items=40,
            toc_entries=25,
            has_toc=True,
            header_distribution={"h1": 10, "h2": 20, "h3": 15, "h4": 0, "h5": 0, "h6": 0},
            recipe_indicators={
                "ingredients": 45,
                "instructions": 43,
                "serves": 40,
                "prep time": 38,
                "cook time": 35,
                "directions": 5,
                "yield": 3,
            },
        )

        analyzer.print_report(report)
        captured = capsys.readouterr()

        # Check metadata section
        assert "test_cookbook.epub" in captured.out
        assert "Title: Test Cookbook" in captured.out
        assert "Author: John Doe" in captured.out

        # Check structure section
        assert "Total items: 100" in captured.out
        assert "Document items: 50" in captured.out
        assert "Image items: 40" in captured.out

        # Check TOC section
        assert "TOC entries: 25" in captured.out

        # Check header distribution
        assert "h1: 10" in captured.out
        assert "h2: 20" in captured.out
        assert "h3: 15" in captured.out

        # Check recipe patterns (sorted by count)
        assert "'ingredients': found in 45/50 documents" in captured.out
        assert "'instructions': found in 43/50 documents" in captured.out

    def test_print_report_no_toc(self, capsys):
        """Test print_report with no TOC."""
        analyzer = EPUBStructureAnalyzer()

        report = StructureReport(
            epub_name="test.epub",
            title="Test",
            author="Author",
            total_items=10,
            document_items=5,
            image_items=3,
            toc_entries=0,
            has_toc=False,
            header_distribution={"h1": 0, "h2": 0, "h3": 0, "h4": 0, "h5": 0, "h6": 0},
            recipe_indicators={},
        )

        analyzer.print_report(report)
        captured = capsys.readouterr()

        assert "No TOC found" in captured.out

    def test_count_toc_entries_static_method(self):
        """Test _count_toc_entries static method."""
        mock_item1 = Mock()
        mock_item2 = Mock()
        mock_item3 = Mock()

        # Simple list
        toc_simple = [mock_item1, mock_item2]
        count = EPUBStructureAnalyzer._count_toc_entries(toc_simple)
        assert count == 2

        # Nested structure
        toc_nested = [
            mock_item1,
            (mock_item2, [mock_item3]),
        ]
        count = EPUBStructureAnalyzer._count_toc_entries(toc_nested)
        assert count == 3  # item1 + (item2 + item3)

    def test_analyze_headers_static_method(self):
        """Test _analyze_headers static method."""
        mock_item = Mock()
        mock_item.get_content.return_value = b"""
        <html>
            <body>
                <h1>Title</h1>
                <h2>Section 1</h2>
                <h2>Section 2</h2>
                <h3>Subsection</h3>
            </body>
        </html>
        """

        header_dist = EPUBStructureAnalyzer._analyze_headers([mock_item])

        assert header_dist["h1"] == 1
        assert header_dist["h2"] == 2
        assert header_dist["h3"] == 1
        assert header_dist["h4"] == 0

    def test_detect_recipe_patterns_static_method(self):
        """Test _detect_recipe_patterns static method."""
        mock_item = Mock()
        mock_item.get_content.return_value = b"""
        Ingredients: flour, sugar
        Instructions: mix and bake
        Serves 6 people
        """

        indicators = EPUBStructureAnalyzer._detect_recipe_patterns([mock_item])

        assert indicators["ingredients"] == 1
        assert indicators["instructions"] == 1
        assert indicators["serves"] == 1
