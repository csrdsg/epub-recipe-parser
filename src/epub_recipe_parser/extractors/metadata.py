"""Extract recipe metadata (servings, time, etc)."""

import re
from typing import Dict, Optional
from bs4 import BeautifulSoup

from epub_recipe_parser.utils.patterns import (
    SERVES_PATTERN,
    PREP_TIME_PATTERN,
    COOK_TIME_PATTERN,
    COOKING_METHODS,
    PROTEIN_TYPES,
)


class MetadataExtractor:
    """Extract recipe metadata with improved parsing and validation."""

    @staticmethod
    def extract(soup: BeautifulSoup, text: str, title: str = "") -> Dict[str, str]:
        """Extract all metadata fields with improved parsing and validation.

        Args:
            soup: BeautifulSoup object of the recipe HTML
            text: Plain text content of the recipe
            title: Recipe title for context

        Returns:
            Dictionary of extracted metadata fields (only valid values included)
        """
        metadata = {}
        text_lower = text.lower()

        # Serves/Yield - with improved parsing
        serves_match = SERVES_PATTERN.search(text_lower)
        if serves_match:
            raw_serves = serves_match.group(1)
            parsed_serves = MetadataExtractor.parse_servings(raw_serves)
            if parsed_serves:
                metadata["serves"] = parsed_serves

        # Prep time - with standardized format
        prep_match = PREP_TIME_PATTERN.search(text_lower)
        if prep_match:
            raw_prep_time = prep_match.group(1).strip()
            parsed_prep_time = MetadataExtractor.parse_time(raw_prep_time)
            if parsed_prep_time is not None:
                metadata["prep_time"] = str(parsed_prep_time)

        # Cook time - with standardized format
        cook_match = COOK_TIME_PATTERN.search(text_lower)
        if cook_match:
            raw_cook_time = cook_match.group(1).strip()
            parsed_cook_time = MetadataExtractor.parse_time(raw_cook_time)
            if parsed_cook_time is not None:
                metadata["cook_time"] = str(parsed_cook_time)

        # Cooking method
        combined = f"{title} {text}".lower()
        for method, keywords in COOKING_METHODS.items():
            if any(keyword in combined for keyword in keywords):
                metadata["cooking_method"] = method
                break

        # Protein type
        for protein in PROTEIN_TYPES:
            if protein in combined:
                metadata["protein_type"] = protein
                break

        return metadata

    @staticmethod
    def parse_servings(raw_value: str) -> Optional[str]:
        """Parse servings value and extract number or range.

        Args:
            raw_value: Raw servings string (e.g., "4-6", "4", "serves 4")

        Returns:
            Normalized servings string (e.g., "4", "4-6") or None if invalid

        Examples:
            >>> MetadataExtractor.parse_servings("4-6")
            "4-6"
            >>> MetadataExtractor.parse_servings("4")
            "4"
            >>> MetadataExtractor.parse_servings("(pressure cooker):")
            None
        """
        if not raw_value:
            return None

        # Remove common non-numeric text
        cleaned = re.sub(r"\(.*?\)", "", raw_value)  # Remove parenthetical text
        cleaned = cleaned.strip()

        # Try to extract number or range pattern (e.g., "4", "4-6", "4 to 6")
        # Match patterns like: "4", "4-6", "4 to 6", "4 - 6"
        number_pattern = re.compile(r"(\d+)\s*(?:-|to)\s*(\d+)|(\d+)")
        match = number_pattern.search(cleaned)

        if match:
            if match.group(1) and match.group(2):
                # Range format: "4-6"
                return f"{match.group(1)}-{match.group(2)}"
            elif match.group(3):
                # Single number: "4"
                return match.group(3)

        # If no valid number found, return None (better than garbage)
        return None

    @staticmethod
    def parse_time(raw_value: str) -> Optional[int]:
        """Parse time value and convert to minutes.

        Args:
            raw_value: Raw time string (e.g., "30 minutes", "1 hour", "1.5 hours")

        Returns:
            Time in minutes as integer, or None if invalid

        Examples:
            >>> MetadataExtractor.parse_time("30 minutes")
            30
            >>> MetadataExtractor.parse_time("1 hour")
            60
            >>> MetadataExtractor.parse_time("1 hour 30 minutes")
            90
            >>> MetadataExtractor.parse_time("invalid")
            None
        """
        if not raw_value:
            return None

        raw_value = raw_value.lower().strip()

        # Check for negative numbers (reject negative times)
        # Match patterns like "-5", "- 5", but not ranges like "30-45"
        if re.search(r"(?:^|\s)-\s*\d", raw_value):
            return None

        total_minutes = 0

        # Pattern for hours (e.g., "1 hour", "2 hours", "1.5 hours")
        hour_pattern = re.compile(r"(\d+(?:\.\d+)?)\s*(?:hour|hr)s?")
        hour_match = hour_pattern.search(raw_value)
        if hour_match:
            try:
                hours = float(hour_match.group(1))
                total_minutes += int(hours * 60)
            except (ValueError, AttributeError):
                pass

        # Pattern for minutes (e.g., "30 minutes", "45 mins")
        minute_pattern = re.compile(r"(\d+)\s*(?:minute|min)s?")
        minute_match = minute_pattern.search(raw_value)
        if minute_match:
            try:
                minutes = int(minute_match.group(1))
                total_minutes += minutes
            except (ValueError, AttributeError):
                pass

        # If we found valid time, validate it
        if total_minutes > 0:
            # Sanity check: time should be reasonable (not more than 24 hours)
            if total_minutes <= 1440:  # 24 hours
                return total_minutes

        # Try parsing just a number (assume minutes)
        simple_number = re.match(r"^\d+$", raw_value.strip())
        if simple_number:
            try:
                minutes = int(raw_value.strip())
                if 0 < minutes <= 1440:
                    return minutes
            except ValueError:
                pass

        # If no valid time found, return None
        return None

    @staticmethod
    def validate_metadata(metadata: Dict[str, str]) -> Dict[str, str]:
        """Validate metadata fields and remove invalid values.

        Args:
            metadata: Dictionary of metadata fields

        Returns:
            Dictionary with only valid metadata fields

        Note:
            This method applies additional validation rules:
            - Servings should contain numbers
            - Times should be reasonable (not > 24 hours)
            - Empty strings are removed
        """
        validated = {}

        for key, value in metadata.items():
            if not value or not value.strip():
                continue

            # Special validation for serves
            if key == "serves":
                parsed = MetadataExtractor.parse_servings(value)
                if parsed:
                    validated[key] = parsed

            # Special validation for times
            elif key in ("prep_time", "cook_time"):
                parsed_time: Optional[int] = MetadataExtractor.parse_time(value)
                if parsed_time is not None:
                    validated[key] = str(parsed_time)

            # Pass through other fields
            else:
                validated[key] = value

        return validated
