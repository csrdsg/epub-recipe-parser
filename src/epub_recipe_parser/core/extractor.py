"""Main EPUB recipe extractor."""

from pathlib import Path
from typing import List, Optional
import ebooklib
from ebooklib import epub

from epub_recipe_parser.core.models import Recipe, ExtractorConfig
from epub_recipe_parser.core.validator import RecipeValidator
from epub_recipe_parser.core.quality import QualityScorer
from epub_recipe_parser.extractors import (
    IngredientsExtractor,
    InstructionsExtractor,
    MetadataExtractor,
)
from epub_recipe_parser.utils.html import HTMLParser
from epub_recipe_parser.utils.text import clean_text


class EPUBRecipeExtractor:
    """Extract recipes directly from EPUB files using HTML structure."""

    def __init__(self, config: Optional[ExtractorConfig] = None):
        """Initialize extractor with optional configuration."""
        self.config = config or ExtractorConfig()
        self.validator = RecipeValidator()
        self.scorer = QualityScorer()
        self.ingredients_extractor = IngredientsExtractor()
        self.instructions_extractor = InstructionsExtractor()
        self.metadata_extractor = MetadataExtractor()

    def extract_from_epub(self, epub_path: str | Path) -> List[Recipe]:
        """Extract all recipes from an EPUB file."""
        epub_path = Path(epub_path)
        print(f"\n📖 Processing EPUB: {epub_path.name}")

        try:
            book = epub.read_epub(str(epub_path))
        except Exception as e:
            print(f"   ❌ Error reading EPUB: {e}")
            return []

        # Get metadata
        creator_meta = book.get_metadata("DC", "creator")
        author = creator_meta[0][0] if creator_meta else "Unknown"

        title_meta = book.get_metadata("DC", "title")
        book_title = title_meta[0][0] if title_meta else epub_path.stem

        # Get TOC for chapter information
        toc = book.toc
        chapter_map = {}
        if toc:
            for item in toc:
                if isinstance(item, tuple):
                    section, _ = item
                    if hasattr(section, "href") and hasattr(section, "title"):
                        chapter_map[section.href] = section.title
                elif hasattr(item, "href") and hasattr(item, "title"):
                    chapter_map[item.href] = item.title

        # Get all document items
        doc_items = list(book.get_items_of_type(ebooklib.ITEM_DOCUMENT))
        print(f"   Found {len(doc_items)} HTML documents")

        recipes = []
        for item in doc_items:
            # Determine chapter from TOC
            item_name = item.get_name()
            chapter = chapter_map.get(item_name, "Unknown")

            # Get HTML content and split by headers
            content = item.get_content()
            main_soup = HTMLParser.parse_html(content)

            # Split into sections
            sections = HTMLParser.split_by_headers(main_soup)

            for section_title, section_soup in sections:
                # Extract text for validation
                text = HTMLParser.extract_text(section_soup)

                # Quick validation before full extraction
                if len(text) < 100:
                    continue

                # Get clean title
                title = clean_text(section_title)

                # Validate as recipe
                if not self.validator.is_valid_recipe(section_soup, text, title):
                    continue

                # Extract components
                ingredients = self.ingredients_extractor.extract(section_soup, text)
                instructions = self.instructions_extractor.extract(section_soup, text)
                metadata = self.metadata_extractor.extract(section_soup, text, title)

                # Create recipe object
                recipe = Recipe(
                    title=title,
                    book=book_title,
                    author=author,
                    chapter=chapter,
                    epub_section=item_name,
                    ingredients=ingredients,
                    instructions=instructions,
                    serves=metadata.get("serves"),
                    prep_time=metadata.get("prep_time"),
                    cook_time=metadata.get("cook_time"),
                    cooking_method=metadata.get("cooking_method"),
                    protein_type=metadata.get("protein_type"),
                    raw_content=text if self.config.include_raw_content else None,
                )

                # Calculate quality score
                recipe.quality_score = self.scorer.score_recipe(recipe)

                # Filter by quality threshold
                if recipe.quality_score < self.config.min_quality_score:
                    continue

                recipes.append(recipe)
                print(f"   ✓ [{len(recipes)}] {recipe.title[:60]} (score: {recipe.quality_score})")

        print(f"   ✅ Extracted {len(recipes)} recipes from EPUB\n")
        return recipes

    def extract_from_section(self, section_soup, title: str = "", book_name: str = "", author: str = "") -> Optional[Recipe]:
        """Extract a single recipe from HTML section."""
        text = HTMLParser.extract_text(section_soup)

        if not self.validator.is_valid_recipe(section_soup, text, title):
            return None

        ingredients = self.ingredients_extractor.extract(section_soup, text)
        instructions = self.instructions_extractor.extract(section_soup, text)
        metadata = self.metadata_extractor.extract(section_soup, text, title)

        recipe = Recipe(
            title=title,
            book=book_name,
            author=author,
            ingredients=ingredients,
            instructions=instructions,
            serves=metadata.get("serves"),
            prep_time=metadata.get("prep_time"),
            cook_time=metadata.get("cook_time"),
            cooking_method=metadata.get("cooking_method"),
            protein_type=metadata.get("protein_type"),
            raw_content=text if self.config.include_raw_content else None,
        )

        recipe.quality_score = self.scorer.score_recipe(recipe)

        if recipe.quality_score < self.config.min_quality_score:
            return None

        return recipe
