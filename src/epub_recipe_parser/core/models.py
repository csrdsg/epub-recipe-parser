"""Data models for recipe extraction."""

from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any, Callable


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
class ExtractorConfig:
    """Configuration for recipe extraction."""

    min_quality_score: int = 20
    extract_toc: bool = True
    validate_recipes: bool = True
    split_by_headers: bool = True
    header_split_level: Optional[int] = None
    include_raw_content: bool = True
    custom_validators: List[Callable] = field(default_factory=list)
