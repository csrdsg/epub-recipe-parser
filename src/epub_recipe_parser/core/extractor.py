"""Main EPUB recipe extractor."""

import logging
from pathlib import Path
from typing import List, Optional

import ebooklib
from ebooklib import epub

from epub_recipe_parser.core.models import Recipe, ExtractorConfig
from epub_recipe_parser.core.validator import RecipeValidator
from epub_recipe_parser.core.quality import QualityScorer
from epub_recipe_parser.core.protocols import (
    IComponentExtractor,
    IRecipeValidator,
    IQualityScorer,
)
from epub_recipe_parser.extractors import (
    IngredientsExtractor,
    InstructionsExtractor,
    MetadataExtractor,
)
from epub_recipe_parser.utils.html import HTMLParser
from epub_recipe_parser.utils.text import clean_text

logger = logging.getLogger(__name__)


class EPUBRecipeExtractor:
    """Extract recipes directly from EPUB files using HTML structure.

    Supports dependency injection for better testability and extensibility.
    All dependencies are optional - defaults will be used if not provided.
    """

    def __init__(
        self,
        config: Optional[ExtractorConfig] = None,
        validator: Optional[IRecipeValidator] = None,
        scorer: Optional[IQualityScorer] = None,
        ingredients_extractor: Optional[IComponentExtractor] = None,
        instructions_extractor: Optional[IComponentExtractor] = None,
        metadata_extractor: Optional[IComponentExtractor] = None,
    ):
        """Initialize extractor with optional configuration and dependencies.

        Args:
            config: Extraction configuration
            validator: Recipe validator (defaults to RecipeValidator)
            scorer: Quality scorer (defaults to QualityScorer)
            ingredients_extractor: Ingredients extractor (defaults to IngredientsExtractor)
            instructions_extractor: Instructions extractor (defaults to InstructionsExtractor)
            metadata_extractor: Metadata extractor (defaults to MetadataExtractor)
        """
        self.config = config or ExtractorConfig()
        self.validator = validator or RecipeValidator()
        self.scorer = scorer or QualityScorer()
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
        logger.debug("Found %d HTML documents", len(doc_items))

        recipes = []
        for item in doc_items:
            # Determine chapter from TOC
            item_name = item.get_name()
            chapter = chapter_map.get(item_name, "Unknown")

            # Get HTML content and split by headers
            content = item.get_content()
            main_soup = HTMLParser.parse_html(content)

            # Try section-based parsing first (modern EPUB structure)
            all_sections = main_soup.find_all("section", recursive=True)

            # Filter to recipe sections (exclude wrapper sections)
            recipe_sections = []
            for section in all_sections:
                # Skip "part" sections which are wrappers
                epub_type = section.get("epub:type")
                if epub_type == "part":
                    continue

                # Must have substantial content
                text = section.get_text(strip=True)
                if len(text) > 100:
                    recipe_sections.append(section)

            # Process each section as a potential recipe
            if recipe_sections:
                sections = []
                for section in recipe_sections:
                    # Extract title from header within section
                    title = None
                    for header in section.find_all(["h1", "h2", "h3", "h4", "h5"], limit=3):
                        header_text = header.get_text(strip=True)
                        if len(header_text) > 3 and not header_text.isdigit():
                            title = header_text
                            break

                    if not title:
                        title = section.get("aria-label", "Untitled")

                    # Create soup from this section
                    import copy
                    from bs4 import BeautifulSoup

                    section_soup = BeautifulSoup("<html><body></body></html>", "html.parser")
                    section_soup.body.append(copy.copy(section))

                    sections.append((title, section_soup))
            else:
                # Fall back to header-based splitting
                section_tag = main_soup.find("section")
                section_title_attr = None
                if section_tag:
                    title_value = section_tag.get("title")
                    # Type safety: Ensure title is a string
                    if title_value and isinstance(title_value, str):
                        section_title_attr = title_value

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

                # A/B Testing: Compare extraction methods (if enabled)
                ab_metadata = None
                if self.ab_runner:
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

                # Skip sections where no ingredients could be extracted
                if not ingredients:
                    logger.debug(f"Skipping '{title}': No ingredients found")
                    continue

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

                # Add A/B test metadata if testing is enabled
                if ab_metadata:
                    recipe.metadata["ab_test"] = ab_metadata

                # Calculate quality score
                recipe.quality_score = self.scorer.score_recipe(recipe)

                # Filter by quality threshold
                if recipe.quality_score < self.config.min_quality_score:
                    continue

                recipes.append(recipe)
                logger.debug("Extracted recipe [%d]: %s (score: %d)",
                           len(recipes), recipe.title[:60], recipe.quality_score)

        logger.info("Extracted %d recipes from EPUB", len(recipes))
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

