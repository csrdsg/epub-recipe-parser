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
        """Extract all recipes from an EPUB file with proper error handling.

        Args:
            epub_path: Path to EPUB file

        Returns:
            List of extracted Recipe objects

        Raises:
            FileNotFoundError: If EPUB file does not exist
            PermissionError: If EPUB file cannot be accessed
            ValueError: If EPUB file is invalid or corrupted
        """
        epub_path = Path(epub_path)

        if not epub_path.exists():
            raise FileNotFoundError(f"EPUB file not found: {epub_path}")

        if not epub_path.is_file():
            raise ValueError(f"Path is not a file: {epub_path}")

        print(f"\n📖 Processing EPUB: {epub_path.name}")

        try:
            book = epub.read_epub(str(epub_path))
        except PermissionError as e:
            print(f"   ❌ Permission denied reading EPUB: {e}")
            raise PermissionError(f"Cannot access EPUB file: {epub_path}") from e
        except (OSError, IOError) as e:
            print(f"   ❌ I/O error reading EPUB: {e}")
            raise ValueError(f"Cannot read EPUB file (possibly corrupted): {epub_path}") from e
        except Exception as e:
            print(f"   ❌ Unexpected error reading EPUB: {e}")
            raise ValueError(f"Invalid EPUB file: {epub_path}") from e

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

            # Extract section title from HTML if present
            section_tag = main_soup.find("section")
            section_title_attr = None
            if section_tag:
                title_value = section_tag.get("title")
                # Type safety: Ensure title is a string
                if title_value and isinstance(title_value, str):
                    section_title_attr = title_value

            # Split into sections, passing section title for fallback
            sections = HTMLParser.split_by_headers(main_soup, section_title=section_title_attr)

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

    def extract_from_section(
        self, section_soup, title: str = "", book_name: str = "", author: str = ""
    ) -> Optional[Recipe]:
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
