"""Tests for title extraction from various HTML structures."""

from bs4 import BeautifulSoup

from epub_recipe_parser.utils.html import HTMLParser


class TestTitleExtraction:
    """Test title extraction with various HTML structures."""

    def test_section_title_attribute(self):
        """Test extraction from section title attribute."""
        html = """
        <html>
        <body>
            <section title="Grilled Ribeye Steak">
                <p>This is a delicious recipe...</p>
            </section>
        </body>
        </html>
        """
        soup = BeautifulSoup(html, "html.parser")
        sections = HTMLParser.split_by_headers(soup)

        assert len(sections) == 1
        title, _ = sections[0]
        assert title == "Grilled Ribeye Steak"

    def test_bold_text_as_title(self):
        """Test extraction from bold text at beginning."""
        html = """
        <html>
        <body>
            <p><b>Steel-Cut Oats with Squash and Tahini</b></p>
            <p>This recipe combines the nutty flavor of steel-cut oats...</p>
            <p>Ingredients: oats, squash, tahini</p>
        </body>
        </html>
        """
        soup = BeautifulSoup(html, "html.parser")
        sections = HTMLParser.split_by_headers(soup)

        assert len(sections) == 1
        title, _ = sections[0]
        assert title == "Steel-Cut Oats with Squash and Tahini"

    def test_strong_text_as_title(self):
        """Test extraction from strong text at beginning."""
        html = """
        <html>
        <body>
            <p><strong>Tandoori Chicken Skewers</strong></p>
            <p>Marinated chicken pieces grilled to perfection...</p>
        </body>
        </html>
        """
        soup = BeautifulSoup(html, "html.parser")
        sections = HTMLParser.split_by_headers(soup)

        assert len(sections) == 1
        title, _ = sections[0]
        assert title == "Tandoori Chicken Skewers"

    def test_first_paragraph_as_title(self):
        """Test extraction from first short paragraph."""
        html = """
        <html>
        <body>
            <p>Creamy Risotto</p>
            <p>This is a long paragraph describing the recipe in detail.
            You'll need arborio rice, chicken stock, parmesan cheese, and butter.
            Cook slowly, stirring constantly for best results.</p>
        </body>
        </html>
        """
        soup = BeautifulSoup(html, "html.parser")
        sections = HTMLParser.split_by_headers(soup)

        assert len(sections) == 1
        title, _ = sections[0]
        assert title == "Creamy Risotto"

    def test_skip_all_caps_bold(self):
        """Test that all-caps bold text is skipped as likely section heading."""
        html = """
        <html>
        <body>
            <p><b>APPETIZERS AND STARTERS</b></p>
            <p><b>Grilled Shrimp Skewers</b></p>
            <p>Fresh shrimp marinated in garlic...</p>
        </body>
        </html>
        """
        soup = BeautifulSoup(html, "html.parser")
        sections = HTMLParser.split_by_headers(soup)

        assert len(sections) == 1
        title, _ = sections[0]
        assert title == "Grilled Shrimp Skewers"

    def test_skip_common_keywords(self):
        """Test that common non-title keywords are skipped."""
        html = """
        <html>
        <body>
            <p><b>For the marinade</b></p>
            <p><b>Herb-Crusted Lamb Chops</b></p>
            <p>Tender lamb chops with a flavorful herb crust...</p>
        </body>
        </html>
        """
        soup = BeautifulSoup(html, "html.parser")
        sections = HTMLParser.split_by_headers(soup)

        assert len(sections) == 1
        title, _ = sections[0]
        assert title == "Herb-Crusted Lamb Chops"

    def test_first_line_fallback(self):
        """Test extraction from first text line as last resort."""
        html = """
        <html>
        <body>
            <p>Chocolate Lava Cake</p>
            <p>Serves 4</p>
            <p>Rich chocolate dessert with molten center...</p>
        </body>
        </html>
        """
        soup = BeautifulSoup(html, "html.parser")
        sections = HTMLParser.split_by_headers(soup)

        assert len(sections) == 1
        title, _ = sections[0]
        # Should get either "Chocolate Lava Cake" or fallback to first line
        assert title in ["Chocolate Lava Cake", "Serves 4"]

    def test_section_title_overrides_content(self):
        """Test that section title attribute takes precedence."""
        html = """
        <html>
        <body>
            <section title="Perfect Title from Attribute">
                <p><b>Wrong Title from Bold</b></p>
                <p>Recipe content here...</p>
            </section>
        </body>
        </html>
        """
        soup = BeautifulSoup(html, "html.parser")
        sections = HTMLParser.split_by_headers(soup)

        assert len(sections) == 1
        title, _ = sections[0]
        assert title == "Perfect Title from Attribute"

    def test_multiple_headers_split(self):
        """Test that documents with headers are split correctly."""
        html = """
        <html>
        <body>
            <h2>Recipe One</h2>
            <p>Content for recipe one...</p>
            <h2>Recipe Two</h2>
            <p>Content for recipe two...</p>
            <h2>Recipe Three</h2>
            <p>Content for recipe three...</p>
        </body>
        </html>
        """
        soup = BeautifulSoup(html, "html.parser")
        sections = HTMLParser.split_by_headers(soup)

        assert len(sections) == 3
        assert sections[0][0] == "Recipe One"
        assert sections[1][0] == "Recipe Two"
        assert sections[2][0] == "Recipe Three"

    def test_very_short_title_ignored(self):
        """Test that very short titles are ignored."""
        html = """
        <html>
        <body>
            <p><b>A</b></p>
            <p><b>Better Recipe Title Here</b></p>
            <p>Recipe content...</p>
        </body>
        </html>
        """
        soup = BeautifulSoup(html, "html.parser")
        sections = HTMLParser.split_by_headers(soup)

        assert len(sections) == 1
        title, _ = sections[0]
        assert title == "Better Recipe Title Here"

    def test_very_long_title_ignored(self):
        """Test that very long titles (> 100 chars) are ignored from bold."""
        html = """
        <html>
        <body>
            <p><b>This is an extremely long title that probably isn't actually a recipe title but rather some kind of introductory text or description that goes on and on</b></p>
            <p><b>Actual Recipe Name</b></p>
            <p>Recipe content...</p>
        </body>
        </html>
        """
        soup = BeautifulSoup(html, "html.parser")
        sections = HTMLParser.split_by_headers(soup)

        assert len(sections) == 1
        title, _ = sections[0]
        assert title == "Actual Recipe Name"

    def test_untitled_fallback(self):
        """Test that 'Untitled' is used as last resort."""
        html = """
        <html>
        <body>
            <p>a</p>
            <p>b</p>
        </body>
        </html>
        """
        soup = BeautifulSoup(html, "html.parser")
        sections = HTMLParser.split_by_headers(soup)

        assert len(sections) == 1
        title, _ = sections[0]
        # Should either extract first line or fallback to Untitled
        assert title in ["Untitled", "a"]

    def test_mixed_header_levels(self):
        """Test handling of mixed header levels."""
        html = """
        <html>
        <body>
            <h1>Chapter Title</h1>
            <h3>Recipe Alpha</h3>
            <p>Content for recipe alpha...</p>
            <h3>Recipe Beta</h3>
            <p>Content for recipe beta...</p>
            <h3>Recipe Gamma</h3>
            <p>Content for recipe gamma...</p>
        </body>
        </html>
        """
        soup = BeautifulSoup(html, "html.parser")
        sections = HTMLParser.split_by_headers(soup)

        # Should split by h3 (most common)
        assert len(sections) == 3
        assert sections[0][0] == "Recipe Alpha"
        assert sections[1][0] == "Recipe Beta"
        assert sections[2][0] == "Recipe Gamma"

    def test_section_title_with_extra_whitespace(self):
        """Test that title whitespace is properly stripped."""
        html = """
        <html>
        <body>
            <section title="
                Recipe Title With Whitespace
            ">
                <p>Recipe content...</p>
            </section>
        </body>
        </html>
        """
        soup = BeautifulSoup(html, "html.parser")
        sections = HTMLParser.split_by_headers(soup)

        assert len(sections) == 1
        title, _ = sections[0]
        # BeautifulSoup normalizes whitespace in attributes
        assert "Recipe Title With Whitespace" in title.strip()

    def test_bold_in_link(self):
        """Test extraction of bold text within a link."""
        html = """
        <html>
        <body>
            <p><a href="#"><b>Roasted Vegetable Medley</b></a></p>
            <p>A colorful array of roasted vegetables...</p>
        </body>
        </html>
        """
        soup = BeautifulSoup(html, "html.parser")
        sections = HTMLParser.split_by_headers(soup)

        assert len(sections) == 1
        title, _ = sections[0]
        assert title == "Roasted Vegetable Medley"
