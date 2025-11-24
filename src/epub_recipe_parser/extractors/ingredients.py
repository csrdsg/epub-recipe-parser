"""Extract ingredient lists from HTML."""

from typing import Optional
from bs4 import BeautifulSoup
import re

from epub_recipe_parser.utils.html import HTMLParser
from epub_recipe_parser.utils.patterns import (
    INGREDIENT_KEYWORDS,
    MEASUREMENT_PATTERN,
)


class IngredientsExtractor:
    """Extract ingredient lists from HTML."""

    @staticmethod
    def extract(soup: BeautifulSoup, text: str) -> Optional[str]:
        """Extract ingredients using multiple strategies."""
        # Strategy 1: Find by header
        ingredients = HTMLParser.find_section_by_header(soup, INGREDIENT_KEYWORDS)
        if ingredients and len(ingredients) > 50:
            return ingredients

        # Strategy 2: Find lists with measurements
        for list_elem in soup.find_all(["ol", "ul"]):
            items = HTMLParser.extract_from_list(list_elem)
            if not items:
                continue

            # Check if items have measurements
            measurement_count = sum(
                1 for item in items if MEASUREMENT_PATTERN.search(item)
            )

            if measurement_count >= max(2, len(items) * 0.3):
                return "\n".join(f"- {item}" for item in items)

        # Strategy 3: Find paragraphs with measurements (fallback)
        for paragraph in soup.find_all("p"):
            text_content = paragraph.get_text(strip=True)
            if len(text_content) < 30:
                continue

            measurement_count = len(MEASUREMENT_PATTERN.findall(text_content))

            if measurement_count >= 3:
                return text_content

        return None
