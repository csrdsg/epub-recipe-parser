"""Data models for recipe extraction."""

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional, List, Dict, Any, Callable

# Forward declaration for type hints
try:
    from bs4 import Tag
except ImportError:
    Tag = Any  # Fallback if BeautifulSoup not installed


class LogLevel(Enum):
    """Log level enumeration for A/B testing."""

    NONE = "NONE"
    INFO = "INFO"
    DEBUG = "DEBUG"


@dataclass
class Recipe:
    """Recipe data model."""

    title: str
    book: str
    author: Optional[str] = None
    chapter: Optional[str] = None
    epub_section: Optional[str] = None
    ingredients: Optional[str] = None
    instructions: Optional[str] = None
    serves: Optional[str] = None
    prep_time: Optional[str] = None
    cook_time: Optional[str] = None
    notes: Optional[str] = None
    tags: List[str] = field(default_factory=list)
    cooking_method: Optional[str] = None
    protein_type: Optional[str] = None
    quality_score: int = 0
    raw_content: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert recipe to dictionary."""
        return {
            "title": self.title,
            "book": self.book,
            "author": self.author,
            "chapter": self.chapter,
            "epub_section": self.epub_section,
            "ingredients": self.ingredients,
            "instructions": self.instructions,
            "serves": self.serves,
            "prep_time": self.prep_time,
            "cook_time": self.cook_time,
            "notes": self.notes,
            "tags": self.tags,
            "cooking_method": self.cooking_method,
            "protein_type": self.protein_type,
            "quality_score": self.quality_score,
            "raw_content": self.raw_content,
            "metadata": self.metadata,
        }


@dataclass
class ExtractionConfig:
    """Configuration for core extraction behavior."""

    min_quality_score: int = 20
    extract_toc: bool = True
    validate_recipes: bool = True
    split_by_headers: bool = True
    header_split_level: Optional[int] = None
    include_raw_content: bool = True
    custom_validators: List[Callable] = field(default_factory=list)


@dataclass
class InstructionZone:
    """Represents a potential instruction zone in HTML.

    This dataclass is used by InstructionStructuralDetector to represent
    zones detected via HTML structure analysis.
    """
    zone: 'Tag'  # BeautifulSoup Tag object containing potential instructions
    detection_method: str  # Method used to detect this zone (e.g., 'css_class', 'header')
    confidence: float  # Initial confidence score based on detection method (0.0-1.0)
    context: Dict[str, Any] = field(default_factory=dict)  # Additional context information


@dataclass
class ABTestConfig:
    """Configuration for A/B testing framework."""

    enabled: bool = False
    use_new_method: bool = False  # If True, use new system in production
    log_level: LogLevel = LogLevel.INFO
    success_threshold: int = 25  # Minimum characters for extraction success


@dataclass
class ExtractorConfig:
    """Configuration for recipe extraction.

    This class provides a unified configuration interface while organizing
    settings into logical groups.
    """

    # Nested configurations
    extraction: ExtractionConfig = field(default_factory=ExtractionConfig)
    ab_testing: ABTestConfig = field(default_factory=ABTestConfig)

    # Backward compatibility: Flat configuration parameters
    # These are deprecated but maintained for compatibility
    min_quality_score: Optional[int] = None
    extract_toc: Optional[bool] = None
    validate_recipes: Optional[bool] = None
    split_by_headers: Optional[bool] = None
    header_split_level: Optional[int] = None
    include_raw_content: Optional[bool] = None
    custom_validators: Optional[List[Callable]] = None
    enable_ab_testing: Optional[bool] = None
    ab_test_use_new: Optional[bool] = None
    ab_test_log_level: Optional[str] = None
    ab_test_success_threshold: Optional[int] = None

    def __post_init__(self):
        """Handle backward compatibility by mapping flat params to nested configs."""
        # Map extraction params if provided
        if self.min_quality_score is not None:
            self.extraction.min_quality_score = self.min_quality_score
        if self.extract_toc is not None:
            self.extraction.extract_toc = self.extract_toc
        if self.validate_recipes is not None:
            self.extraction.validate_recipes = self.validate_recipes
        if self.split_by_headers is not None:
            self.extraction.split_by_headers = self.split_by_headers
        if self.header_split_level is not None:
            self.extraction.header_split_level = self.header_split_level
        if self.include_raw_content is not None:
            self.extraction.include_raw_content = self.include_raw_content
        if self.custom_validators is not None:
            self.extraction.custom_validators = self.custom_validators

        # Map A/B testing params if provided
        if self.enable_ab_testing is not None:
            self.ab_testing.enabled = self.enable_ab_testing
        if self.ab_test_use_new is not None:
            self.ab_testing.use_new_method = self.ab_test_use_new
        if self.ab_test_log_level is not None:
            # Convert string to enum
            try:
                self.ab_testing.log_level = LogLevel(self.ab_test_log_level)
            except ValueError:
                # Default to INFO if invalid
                self.ab_testing.log_level = LogLevel.INFO
        if self.ab_test_success_threshold is not None:
            self.ab_testing.success_threshold = self.ab_test_success_threshold

        # Expose nested config values as properties for backward compatibility
        if self.min_quality_score is None:
            self.min_quality_score = self.extraction.min_quality_score
        if self.extract_toc is None:
            self.extract_toc = self.extraction.extract_toc
        if self.validate_recipes is None:
            self.validate_recipes = self.extraction.validate_recipes
        if self.split_by_headers is None:
            self.split_by_headers = self.extraction.split_by_headers
        if self.include_raw_content is None:
            self.include_raw_content = self.extraction.include_raw_content

        if self.enable_ab_testing is None:
            self.enable_ab_testing = self.ab_testing.enabled
        if self.ab_test_use_new is None:
            self.ab_test_use_new = self.ab_testing.use_new_method
        if self.ab_test_log_level is None:
            self.ab_test_log_level = self.ab_testing.log_level.value
        if self.ab_test_success_threshold is None:
            self.ab_test_success_threshold = self.ab_testing.success_threshold
