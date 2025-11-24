"""EPUB Recipe Parser - Extract structured recipe data from EPUB cookbook files."""

from epub_recipe_parser.core.extractor import EPUBRecipeExtractor
from epub_recipe_parser.core.models import Recipe, ExtractorConfig

__version__ = "0.1.0"
__all__ = ["EPUBRecipeExtractor", "Recipe", "ExtractorConfig", "extract_recipes"]


def extract_recipes(epub_path: str, config=None):
    """
    Simple API to extract recipes from an EPUB file.

    Args:
        epub_path: Path to the EPUB file
        config: Optional ExtractorConfig instance

    Returns:
        List of Recipe objects
    """
    extractor = EPUBRecipeExtractor(config=config)
    return extractor.extract_from_epub(epub_path)
