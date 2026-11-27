"""Integration tests demonstrating title extraction improvements on real cookbook patterns."""

from bs4 import BeautifulSoup

from epub_recipe_parser.utils.html import HTMLParser


class TestRealWorldTitleExtraction:
    """Test title extraction with real cookbook HTML patterns."""

    def test_start_simple_pattern(self):
        """Test Start Simple cookbook pattern (section title + bold in link)."""
        html = """
        <html>
        <body>
            <section id="ch4_6" title="Steel-Cut Oats with Squash and Tahini">
                <p class="middlehead">
                    <a href="#recipe"><b>Steel-Cut Oats with Squash and Tahini</b></a>
                </p>
                <p>This hearty breakfast combines the nutty flavor...</p>
                <p><b>For the oatmeal</b></p>
                <p>1 cup steel-cut oats</p>
            </section>
        </body>
        </html>
        """
        soup = BeautifulSoup(html, "html.parser")
        sections = HTMLParser.split_by_headers(soup)

        assert len(sections) == 1
        title, _ = sections[0]
        # Should extract from section title attribute
        assert title == "Steel-Cut Oats with Squash and Tahini"

    def test_tandoori_pattern(self):
        """Test Tandoori cookbook pattern (first paragraph as title)."""
        html = """
        <html>
        <body>
            <p>Creamy Chicken Skewers with Green Chilli & Coriander</p>
            <p>These succulent chicken skewers are marinated in a creamy yogurt-based
            marinade infused with fresh green chilies and coriander...</p>
            <p>Serves 4</p>
            <p>Prep time: 30 minutes</p>
        </body>
        </html>
        """
        soup = BeautifulSoup(html, "html.parser")
        sections = HTMLParser.split_by_headers(soup)

        assert len(sections) == 1
        title, _ = sections[0]
        # Should extract first paragraph as title
        assert title == "Creamy Chicken Skewers with Green Chilli & Coriander"

    def test_seven_fires_pattern(self):
        """Test Seven Fires cookbook pattern (descriptive first line)."""
        html = """
        <html>
        <body>
            <p>Savory Corn Pudding</p>
            <div>This rich and creamy corn pudding is a perfect side dish for grilled meats.
            The sweet corn is balanced by savory herbs and a touch of cream.</div>
            <p>Serves 6-8</p>
        </body>
        </html>
        """
        soup = BeautifulSoup(html, "html.parser")
        sections = HTMLParser.split_by_headers(soup)

        assert len(sections) == 1
        title, _ = sections[0]
        assert title == "Savory Corn Pudding"

    def test_filters_ingredient_lines(self):
        """Test that ingredient lines are not used as titles."""
        html = """
        <html>
        <body>
            <p><b>4 large red bell peppers</b></p>
            <p><b>2 tablespoons olive oil</b></p>
            <p><b>Roasted Peppers</b></p>
            <p>This simple preparation brings out the natural sweetness...</p>
        </body>
        </html>
        """
        soup = BeautifulSoup(html, "html.parser")
        sections = HTMLParser.split_by_headers(soup)

        assert len(sections) == 1
        title, _ = sections[0]
        # Should skip ingredient lines and find the recipe name
        assert title == "Roasted Peppers"

    def test_filters_section_headers(self):
        """Test that section headers are skipped in favor of recipe titles."""
        html = """
        <html>
        <body>
            <p><b>APPETIZERS AND STARTERS</b></p>
            <p><b>Grilled Shrimp Skewers</b></p>
            <p>Fresh shrimp marinated in garlic, lemon, and herbs...</p>
        </body>
        </html>
        """
        soup = BeautifulSoup(html, "html.parser")
        sections = HTMLParser.split_by_headers(soup)

        assert len(sections) == 1
        title, _ = sections[0]
        # Should skip all-caps section header
        assert title == "Grilled Shrimp Skewers"

    def test_filters_preparation_keywords(self):
        """Test that preparation sections are skipped."""
        html = """
        <html>
        <body>
            <p><b>FOR THE MARINADE</b></p>
            <p><b>FOR THE SAUCE</b></p>
            <p><b>Tandoori Lamb Chops</b></p>
            <p>Tender lamb chops marinated in traditional tandoori spices...</p>
        </body>
        </html>
        """
        soup = BeautifulSoup(html, "html.parser")
        sections = HTMLParser.split_by_headers(soup)

        assert len(sections) == 1
        title, _ = sections[0]
        # Should skip "for the" patterns and find recipe name
        assert title == "Tandoori Lamb Chops"

    def test_mixed_content_cookbook(self):
        """Test cookbook with mixed content types."""
        html = """
        <html>
        <body>
            <p>Some introductory text about grilling techniques...</p>
            <p><b>The First Commandment—Don't Touch!</b></p>
            <p>One of the most important rules of grilling is patience.
            Don't constantly flip or move your food...</p>
        </body>
        </html>
        """
        soup = BeautifulSoup(html, "html.parser")
        sections = HTMLParser.split_by_headers(soup)

        assert len(sections) == 1
        title, _ = sections[0]
        # Should find the bold title, not the intro text
        assert title == "The First Commandment—Don't Touch!"

    def test_section_attribute_overrides_content(self):
        """Test that section title attribute takes precedence."""
        html = """
        <html>
        <body>
            <section title="Butternut Squash Soup with Garlic and White Wine">
                <p><b>SOUPS</b></p>
                <p>This warming soup combines roasted butternut squash...</p>
            </section>
        </body>
        </html>
        """
        soup = BeautifulSoup(html, "html.parser")
        sections = HTMLParser.split_by_headers(soup)

        assert len(sections) == 1
        title, _ = sections[0]
        # Section attribute should be preferred
        assert title == "Butternut Squash Soup with Garlic and White Wine"

    def test_complex_title_with_special_chars(self):
        """Test titles with special characters and formatting."""
        html = """
        <html>
        <body>
            <p><b>Croque Courge</b></p>
            <p>A play on the classic croque monsieur, this "squash grilled cheese"...</p>
        </body>
        </html>
        """
        soup = BeautifulSoup(html, "html.parser")
        sections = HTMLParser.split_by_headers(soup)

        assert len(sections) == 1
        title, _ = sections[0]
        assert title == "Croque Courge"

    def test_recipe_with_subtitle(self):
        """Test recipe with main title and subtitle."""
        html = """
        <html>
        <body>
            <p><b>Tandoori Chicken Wings with Tamarind & Chilli</b></p>
            <p>A modern twist on traditional tandoori chicken...</p>
        </body>
        </html>
        """
        soup = BeautifulSoup(html, "html.parser")
        sections = HTMLParser.split_by_headers(soup)

        assert len(sections) == 1
        title, _ = sections[0]
        assert title == "Tandoori Chicken Wings with Tamarind & Chilli"
