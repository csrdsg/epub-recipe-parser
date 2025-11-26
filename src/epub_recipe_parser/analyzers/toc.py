"""Table of Contents analysis and validation."""

from pathlib import Path
from typing import List, Optional
from dataclasses import dataclass
from difflib import SequenceMatcher
import re
from ebooklib import epub

from epub_recipe_parser.core.models import Recipe
from epub_recipe_parser.utils.patterns import EXCLUDE_KEYWORDS


@dataclass
class TOCEntry:
    """TOC entry data."""

    title: str
    href: Optional[str] = None
    category: Optional[str] = None
    level: int = 0


@dataclass
class ValidationReport:
    """Validation report for TOC vs extracted recipes."""

    toc_count: int
    extracted_count: int
    matched: int
    coverage: float
    missing: List[TOCEntry]
    book_name: str


class TOCAnalyzer:
    """Analyze EPUB Table of Contents."""

    def extract_toc_recipes(self, epub_path: str | Path) -> List[TOCEntry]:
        """Extract potential recipe entries from EPUB TOC."""
        try:
            book = epub.read_epub(str(epub_path))
        except Exception as e:
            print(f"   ❌ Error reading EPUB: {e}")
            return []

        toc = book.toc
        if not toc:
            return []

        recipes = []

        def process_toc_item(item, level=0, parent_category=None):
            """Recursively process TOC items."""
            if isinstance(item, tuple):
                # Nested structure: (section, children)
                section, children = item
                category = section.title if hasattr(section, "title") else None

                # Process children
                for child in children:
                    process_toc_item(child, level + 1, category)

            else:
                # Simple link
                if hasattr(item, "title"):
                    title = item.title
                    href = getattr(item, "href", None)

                    # Filter out obvious non-recipes
                    if self.is_likely_recipe(title):
                        recipes.append(
                            TOCEntry(title=title, href=href, category=parent_category, level=level)
                        )

        for item in toc:
            process_toc_item(item)

        return recipes

    @staticmethod
    def is_likely_recipe(title: str) -> bool:
        """Determine if TOC entry is likely a recipe."""
        title_lower = title.lower()

        # Exclude obvious non-recipes
        exclude_patterns = [
            r"^chapter\s+\d+",
            r"^part\s+\d+",
        ]

        for pattern in exclude_patterns:
            if re.search(pattern, title_lower):
                return False

        for keyword in EXCLUDE_KEYWORDS:
            if keyword in title_lower:
                return False

        # Too short to be a recipe title
        if len(title) < 3:
            return False

        # Just a number
        if title.strip().isdigit():
            return False

        # Likely a recipe if contains food words or is longer
        food_indicators = [
            "chicken",
            "beef",
            "pork",
            "lamb",
            "fish",
            "salmon",
            "shrimp",
            "salad",
            "soup",
            "sauce",
            "bread",
            "cake",
            "pie",
            "cookie",
            "grilled",
            "smoked",
            "roasted",
            "baked",
            "fried",
            "steak",
            "ribs",
            "burger",
            "sandwich",
            "taco",
            "pizza",
        ]

        has_food_word = any(word in title_lower for word in food_indicators)
        if has_food_word:
            return True

        # Or is longer and at deeper level (likely recipe)
        if len(title) > 10:
            return True

        return False

    @staticmethod
    def fuzzy_match(str1: str, str2: str) -> float:
        """Calculate fuzzy match score between two strings."""
        # Input validation
        if not str1 or not str2:
            return 0.0

        # Normalize strings
        s1 = re.sub(r"[^\w\s]", "", str1.lower())
        s2 = re.sub(r"[^\w\s]", "", str2.lower())

        # Remove common prefixes
        s1 = re.sub(r"^\[\]", "", s1).strip()
        s2 = re.sub(r"^\[\]", "", s2).strip()

        # Edge case: both empty after normalization
        if not s1 or not s2:
            return 0.0

        # Calculate similarity
        return SequenceMatcher(None, s1, s2).ratio()

    def validate_extraction(self, recipes: List[Recipe], epub_path: str | Path) -> ValidationReport:
        """Validate extraction against TOC."""
        epub_path = Path(epub_path)
        toc_recipes = self.extract_toc_recipes(epub_path)

        if not toc_recipes:
            return ValidationReport(
                toc_count=0,
                extracted_count=len(recipes),
                matched=0,
                coverage=0.0,
                missing=[],
                book_name=epub_path.name,
            )

        # Match TOC entries with extracted recipes
        matches = []
        missing = []
        match_threshold = 0.6  # 60% similarity required

        for toc_recipe in toc_recipes:
            best_match = None
            best_score = 0.0

            # Bounds checking: Ensure recipes list is not empty
            if recipes:
                for extracted in recipes:
                    score = self.fuzzy_match(toc_recipe.title, extracted.title)
                    if score > best_score:
                        best_score = score
                        best_match = extracted

            if best_score >= match_threshold and best_match is not None:
                matches.append((toc_recipe, best_match, best_score))
            else:
                missing.append(toc_recipe)

        # Bounds checking: Prevent division by zero
        coverage = len(matches) / len(toc_recipes) if toc_recipes else 0.0

        return ValidationReport(
            toc_count=len(toc_recipes),
            extracted_count=len(recipes),
            matched=len(matches),
            coverage=coverage,
            missing=missing,
            book_name=epub_path.name,
        )
