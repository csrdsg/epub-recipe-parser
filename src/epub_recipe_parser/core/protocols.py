"""Protocol definitions for component interfaces.

These protocols define the contracts that components must fulfill,
enabling dependency injection, testing with mocks, and easier extensibility.
"""

from typing import Protocol, Optional, Union, Dict, Any, runtime_checkable
from bs4 import BeautifulSoup

from epub_recipe_parser.core.models import Recipe


@runtime_checkable
class IComponentExtractor(Protocol):
    """Protocol for component extractors (ingredients, instructions, metadata).

    Component extractors are responsible for extracting specific parts of a recipe
    from HTML content.

    The extract() method supports two return types for backward compatibility:
    1. Optional[str]: Legacy mode - returns just the extracted text
    2. tuple[Optional[str], Dict[str, Any]]: Modern mode - returns (text, metadata)

    The metadata dictionary may contain:
    - strategy: str - Detection strategy used
    - confidence: float - Confidence score (0.0-1.0)
    - linguistic_score: float - Linguistic quality score (0.0-1.0)
    - combined_score: float - Overall quality score
    - Other strategy-specific fields
    """

    def extract(
        self,
        soup: BeautifulSoup,
        text: str,
        *args: Any,
        **kwargs: Any
    ) -> Union[Optional[str], tuple[Optional[str], Dict[str, Any]], Dict[str, str]]:
        """Extract a component from HTML content.

        Args:
            soup: BeautifulSoup object containing the HTML
            text: Plain text version of the content
            *args: Variable positional arguments (e.g., title for metadata)
            **kwargs: Variable keyword arguments (e.g., use_patterns for ingredient extraction)

        Returns:
            Either:
            - Optional[str]: Extracted component text (legacy mode)
            - tuple[Optional[str], Dict[str, Any]]: (text, metadata) for pattern-based extraction
            - Dict[str, str]: Metadata dictionary for metadata extractors
        """
        ...


@runtime_checkable
class IRecipeValidator(Protocol):
    """Protocol for recipe validators.

    Validators determine whether a section of content represents a valid recipe.
    """

    def is_valid_recipe(
        self,
        soup: BeautifulSoup,
        text: str,
        title: str = ""
    ) -> bool:
        """Validate if content represents a recipe.

        Args:
            soup: BeautifulSoup object containing the HTML
            text: Plain text version of the content
            title: Optional title/header text

        Returns:
            True if content appears to be a recipe, False otherwise
        """
        ...


@runtime_checkable
class IQualityScorer(Protocol):
    """Protocol for quality scorers.

    Quality scorers evaluate the completeness and quality of extracted recipes.
    """

    def score_recipe(self, recipe: Recipe) -> int:
        """Calculate quality score for a recipe.

        Args:
            recipe: Recipe object to score

        Returns:
            Quality score (typically 0-100)
        """
        ...


@runtime_checkable
class IHTMLParser(Protocol):
    """Protocol for HTML parsing strategies.

    HTML parsers handle the conversion and manipulation of HTML content.
    """

    @staticmethod
    def parse_html(content: bytes) -> BeautifulSoup:
        """Parse HTML content into BeautifulSoup object.

        Args:
            content: Raw HTML bytes

        Returns:
            BeautifulSoup object
        """
        ...

    @staticmethod
    def extract_text(soup: BeautifulSoup) -> str:
        """Extract plain text from HTML.

        Args:
            soup: BeautifulSoup object

        Returns:
            Plain text content
        """
        ...
