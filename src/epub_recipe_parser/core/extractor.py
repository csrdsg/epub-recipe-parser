"""Main EPUB recipe extractor."""

import copy
import logging
import warnings
from pathlib import Path
from typing import List, Optional
from urllib.parse import unquote, urlsplit

import ebooklib
from bs4 import BeautifulSoup
from ebooklib import epub

from epub_recipe_parser.core.models import Recipe, ExtractorConfig
from epub_recipe_parser.core.validator import RecipeValidator
from epub_recipe_parser.core.protocols import (
    IComponentExtractor,
    IRecipeValidator,
)
from epub_recipe_parser.extractors import (
    IngredientsExtractor,
    InstructionsExtractor,
    MetadataExtractor,
)
from epub_recipe_parser.utils.html import HTMLParser
from epub_recipe_parser.utils.text import clean_text
from epub_recipe_parser.utils.extraction import (
    normalize_extraction_result,
    merge_extraction_metadata,
)
from epub_recipe_parser.utils.defuddle import clean_section_html

logger = logging.getLogger(__name__)


def _chapter_lookup(entries):
    """Index TOC chapters by document path and child entry title."""
    by_path: dict[str, str] = {}
    by_title: dict[tuple[str, str], str] = {}

    def visit(nodes, chapter: str | None = None):
        for node in nodes:
            entry, children = node if isinstance(node, tuple) else (node, ())
            title = getattr(entry, "title", None)
            href = getattr(entry, "href", None)
            if title and href:
                path = unquote(urlsplit(href).path)
                if path:
                    by_path.setdefault(path, chapter or title)
                    if chapter:
                        by_title.setdefault((path, clean_text(title).casefold()), chapter)
            if children:
                visit(children, title or chapter)

    visit(entries or ())
    return by_path, by_title


class EPUBRecipeExtractor:
    """Extract recipes directly from EPUB files using HTML structure.

    Supports dependency injection for better testability and extensibility.
    All dependencies are optional - defaults will be used if not provided.
    """

    def __init__(
        self,
        config: Optional[ExtractorConfig] = None,
        validator: Optional[IRecipeValidator] = None,
        ingredients_extractor: Optional[IComponentExtractor] = None,
        instructions_extractor: Optional[IComponentExtractor] = None,
        metadata_extractor: Optional[IComponentExtractor] = None,
    ):
        """Initialize extractor with optional configuration and dependencies.

        Args:
            config: Extraction configuration
            validator: Recipe validator (defaults to RecipeValidator)
            ingredients_extractor: Ingredients extractor (defaults to IngredientsExtractor)
            instructions_extractor: Instructions extractor (defaults to InstructionsExtractor)
            metadata_extractor: Metadata extractor (defaults to MetadataExtractor)
        """
        self.config = config or ExtractorConfig()
        self.validator = validator or RecipeValidator()
        self.ingredients_extractor = ingredients_extractor or IngredientsExtractor()
        self.instructions_extractor = instructions_extractor or InstructionsExtractor()
        self.metadata_extractor = metadata_extractor or MetadataExtractor()

        # Initialize A/B test runner if enabled
        self.ab_runner = None
        if self.config.ab_testing.enabled:
            from epub_recipe_parser.testing.ab_runner import ABTestRunner
            from epub_recipe_parser.extractors.ingredients import IngredientsExtractor as TreatmentExtractor

            self.ab_runner = ABTestRunner(self.config.ab_testing)
            self.treatment_extractor = TreatmentExtractor()

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

        logger.info("Processing EPUB: %s", epub_path.name)

        try:
            book = epub.read_epub(str(epub_path))
        except PermissionError as e:
            logger.error("Permission denied reading EPUB: %s", e)
            raise PermissionError(f"Cannot access EPUB file: {epub_path}") from e
        except (OSError, IOError) as e:
            logger.error("I/O error reading EPUB: %s", e)
            raise ValueError(f"Cannot read EPUB file (possibly corrupted): {epub_path}") from e
        except Exception as e:
            logger.error("Unexpected error reading EPUB: %s", e)
            raise ValueError(f"Invalid EPUB file: {epub_path}") from e

        # Get metadata
        creator_meta = book.get_metadata("DC", "creator")
        author = creator_meta[0][0] if creator_meta else "Unknown"

        title_meta = book.get_metadata("DC", "title")
        book_title = title_meta[0][0] if title_meta else epub_path.stem

        chapters_by_path, chapters_by_title = _chapter_lookup(book.toc)

        # Get all document items
        doc_items = list(book.get_items_of_type(ebooklib.ITEM_DOCUMENT))
        logger.debug("Found %d HTML documents", len(doc_items))

        recipes = []
        for item in doc_items:
            item_name = item.get_name()
            document_path = unquote(item_name)

            sections = self._find_sections(item.get_content())
            for section_title, section_soup in sections:
                if self.config.extraction.use_defuddle_cleaning:
                    original_html = str(section_soup)
                    cleaned_html = clean_section_html(original_html, use_defuddle=True)
                    if cleaned_html and cleaned_html != original_html:
                        section_soup = HTMLParser.parse_html(cleaned_html.encode())

                title = clean_text(section_title) if section_title else ""
                chapter = chapters_by_title.get(
                    (document_path, title.casefold()), chapters_by_path.get(document_path, "Unknown")
                )
                recipe = self._extract_candidate(
                    section_soup,
                    title,
                    book_title,
                    author,
                    chapter=chapter,
                    epub_section=item_name,
                )
                if recipe is not None:
                    recipes.append(recipe)
                    logger.debug(
                        "Extracted recipe [%d]: %s",
                        len(recipes),
                        recipe.title[:60],
                    )

        logger.info("Extracted %d recipes from EPUB", len(recipes))
        return recipes

    @staticmethod
    def _find_sections(content: bytes) -> list[tuple[str, BeautifulSoup]]:
        """Find candidate recipe sections in an EPUB document."""
        main_soup = HTMLParser.parse_html(content)
        sections = []
        for section in main_soup.find_all("section"):
            if section.get("epub:type") == "part" or len(section.get_text(strip=True)) <= 100:
                continue

            title = str(section.get("aria-label") or "Untitled")
            for header in section.find_all(["h1", "h2", "h3", "h4", "h5"], limit=3):
                header_text = header.get_text(strip=True)
                if len(header_text) > 3 and not header_text.isdigit():
                    title = header_text
                    break

            section_soup = BeautifulSoup("<html><body></body></html>", "html.parser")
            if section_soup.body is not None:
                section_soup.body.append(copy.copy(section))
            sections.append((title, section_soup))

        if sections:
            return sections

        section_tag = main_soup.find("section")
        title_value = section_tag.get("title") if section_tag is not None else None
        section_title = title_value if isinstance(title_value, str) else None
        return HTMLParser.split_by_headers(main_soup, section_title=section_title)

    def extract_from_section(
        self, section_soup, title: str = "", book_name: str = "", author: str = ""
    ) -> Optional[Recipe]:
        """Extract a single recipe from HTML section."""
        return self._extract_candidate(section_soup, title, book_name, author)

    def _extract_candidate(
        self,
        section_soup,
        title: str,
        book_name: str,
        author: str,
        *,
        chapter: str | None = None,
        epub_section: str | None = None,
    ) -> Optional[Recipe]:
        from_epub = epub_section is not None
        text = HTMLParser.extract_text(section_soup)
        if from_epub and len(text) < 100:
            return None

        if not self.validator.is_valid_recipe(section_soup, text, title):
            return None

        # Extract with pattern-based detection
        use_patterns = self.config.extraction.use_pattern_extraction
        ingredients_result = self.ingredients_extractor.extract(
            section_soup, text, use_patterns=use_patterns
        )
        ingredients, ingredients_metadata = normalize_extraction_result(ingredients_result)  # type: ignore[arg-type]

        ab_metadata = None
        if from_epub and self.ab_runner:
            warnings.warn(
                "A/B testing is deprecated. Use use_pattern_extraction=True instead.",
                DeprecationWarning,
                stacklevel=3,
            )
            ab_metadata = self.ab_runner.compare_extractors(
                control_extractor=self.ingredients_extractor,
                treatment_extractor=self.treatment_extractor,
                soup=section_soup,
                text=text,
                control_result=ingredients,
            )

            # Optionally use treatment result in production
            if self.ab_runner.should_use_treatment(ab_metadata):
                ingredients = ab_metadata["new_ingredients"]
                logger.info("A/B Test: Using treatment extraction method")

        if from_epub and not ingredients:
            logger.debug("Skipping %r: No ingredients found", title)
            return None

        instructions_result = self.instructions_extractor.extract(section_soup, text)
        # Instructions extractor returns Optional[str], not tuple
        if isinstance(instructions_result, tuple):
            instructions = instructions_result[0]  # type: ignore[assignment]
        else:
            instructions = instructions_result  # type: ignore[assignment]

        metadata_result = self.metadata_extractor.extract(section_soup, text, title)
        # Metadata extractor returns Dict[str, str]
        if isinstance(metadata_result, dict):
            metadata = metadata_result
        else:
            metadata = {}

        recipe = Recipe(
            title=title,
            book=book_name,
            author=author,
            chapter=chapter,
            epub_section=epub_section,
            ingredients=ingredients,
            instructions=instructions,
            serves=metadata.get("serves"),
            prep_time=metadata.get("prep_time"),
            cook_time=metadata.get("cook_time"),
            cooking_method=metadata.get("cooking_method"),
            protein_type=metadata.get("protein_type"),
            raw_content=text if self.config.include_raw_content else None,
        )

        # Store extraction metadata
        if ingredients_metadata:
            merge_extraction_metadata(recipe.metadata, ingredients_metadata, "ingredients")

        if ab_metadata:
            recipe.metadata["ab_test"] = ab_metadata

        return recipe

