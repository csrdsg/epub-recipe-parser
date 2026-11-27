"""Tests for defuddle HTML cleaning integration."""

import pytest
from epub_recipe_parser.utils.defuddle import DefuddleHTMLCleaner, clean_section_html


class TestDefuddleHTMLCleaner:
    """Test DefuddleHTMLCleaner functionality."""

    def test_is_available(self):
        """Test defuddle availability check."""
        # This will be True if defuddle CLI is installed
        available = DefuddleHTMLCleaner.is_available()
        assert isinstance(available, bool)

    def test_clean_html_removes_nav(self):
        """Test that defuddle removes navigation elements."""
        html_with_nav = """
        <html>
        <body>
        <nav><a href="/">Home</a></nav>
        <article>
        <h2>Recipe Title</h2>
        <p>Recipe content here</p>
        </article>
        <footer>Copyright</footer>
        </body>
        </html>
        """

        if not DefuddleHTMLCleaner.is_available():
            pytest.skip("defuddle CLI not installed")

        result = DefuddleHTMLCleaner.clean_html(html_with_nav)
        assert result is not None
        # Check that main content remains
        assert "Recipe content" in result
        # Nav and footer should be removed
        assert "nav" not in result.lower()
        # Size should be smaller than original
        assert len(result) < len(html_with_nav)

    def test_clean_html_with_sidebar(self):
        """Test that defuddle removes sidebar clutter."""
        html_with_sidebar = """
        <html>
        <body>
        <div class="sidebar">
            <h3>Popular Recipes</h3>
            <ul>
            <li><a href="/pasta">Pasta</a></li>
            <li><a href="/soup">Soup</a></li>
            </ul>
        </div>
        <main>
            <h2>Chocolate Chip Cookies</h2>
            <h3>Ingredients</h3>
            <ul>
            <li>2 cups flour</li>
            <li>1 cup butter</li>
            </ul>
        </main>
        </body>
        </html>
        """

        if not DefuddleHTMLCleaner.is_available():
            pytest.skip("defuddle CLI not installed")

        result = DefuddleHTMLCleaner.clean_html(html_with_sidebar)
        assert result is not None
        # Main content should be preserved
        assert "Ingredients" in result
        assert "2 cups flour" in result
        # Sidebar should be removed
        assert "Popular Recipes" not in result

    def test_clean_html_fails_gracefully(self):
        """Test that clean_html returns None on error."""
        if not DefuddleHTMLCleaner.is_available():
            pytest.skip("defuddle CLI not installed")

        # Empty or invalid HTML should not crash
        result = DefuddleHTMLCleaner.clean_html("")
        # Should return None or empty string, not crash
        assert result is None or result == ""

    def test_clean_section_html_without_defuddle(self):
        """Test clean_section_html returns original when defuddle disabled."""
        html = "<article>Test</article>"
        result = clean_section_html(html, use_defuddle=False)
        assert result == html

    def test_clean_section_html_with_defuddle(self):
        """Test clean_section_html uses defuddle when enabled."""
        if not DefuddleHTMLCleaner.is_available():
            pytest.skip("defuddle CLI not installed")

        html = """
        <article>
        <nav>Navigation</nav>
        <h1>Recipe</h1>
        <footer>Footer</footer>
        </article>
        """
        result = clean_section_html(html, use_defuddle=True)
        # Should contain the main content
        assert "Recipe" in result

    def test_clean_html_with_ads_and_tracking(self):
        """Test that defuddle removes ads and tracking elements."""
        html_with_clutter = """
        <html>
        <body>
        <div class="advertisement">
            <img src="ad.jpg" />
        </div>
        <article>
            <h2>Recipe Title</h2>
            <h3>Ingredients</h3>
            <ul>
            <li>1 cup sugar</li>
            <li>2 eggs</li>
            </ul>
            <h3>Instructions</h3>
            <ol>
            <li>Mix ingredients</li>
            <li>Bake</li>
            </ol>
        </article>
        <div id="comments">
            <h3>Comments</h3>
            <p>Some user comment</p>
        </div>
        <script>
            // Tracking code
        </script>
        </body>
        </html>
        """

        if not DefuddleHTMLCleaner.is_available():
            pytest.skip("defuddle CLI not installed")

        result = DefuddleHTMLCleaner.clean_html(html_with_clutter)
        assert result is not None
        # Recipe content should be present
        assert "Ingredients" in result
        assert "1 cup sugar" in result
        # Ads and comments should be removed
        assert "ad.jpg" not in result
        # Size should be much smaller
        assert len(result) < len(html_with_clutter)

    def test_clean_html_preserves_lists(self):
        """Test that defuddle preserves list structures."""
        html_with_lists = """
        <html>
        <body>
        <article>
            <h2>Ingredients</h2>
            <ul>
            <li>2 cups all-purpose flour</li>
            <li>1 tsp baking soda</li>
            <li>1 tsp salt</li>
            <li>1 cup butter, softened</li>
            </ul>
            <h2>Instructions</h2>
            <ol>
            <li>Preheat oven to 375°F</li>
            <li>Mix flour, baking soda and salt in small bowl</li>
            <li>Bake for 9-11 minutes</li>
            </ol>
        </article>
        </body>
        </html>
        """

        if not DefuddleHTMLCleaner.is_available():
            pytest.skip("defuddle CLI not installed")

        result = DefuddleHTMLCleaner.clean_html(html_with_lists)
        assert result is not None
        # All ingredients should be present
        assert "flour" in result
        assert "baking soda" in result
        assert "butter" in result
        # All instructions should be present
        assert "Preheat oven" in result
        assert "Bake" in result
