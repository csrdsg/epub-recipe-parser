"""Extract recipe metadata (servings, time, etc)."""

import re
from typing import Dict, Optional, Any
from bs4 import BeautifulSoup

from epub_recipe_parser.utils.patterns import (
    SERVES_PATTERN,
    PREP_TIME_PATTERN,
    COOK_TIME_PATTERN,
    COOKING_METHODS,
    PROTEIN_TYPES,
)

_RESTING_ACTIONS = {"rest", "cool", "chill", "refrigerate"}
_MARINATING_ACTIONS = {"marinate", "brine", "soak"}
_COOKING_ACTIONS = {
    "bake", "boil", "broil", "cook", "fry", "grill", "roast", "sauté",
    "simmer", "smoke", "steam", "toast",
}
_TIMED_ACTIONS = "|".join(sorted(_RESTING_ACTIONS | _MARINATING_ACTIONS | _COOKING_ACTIONS))
_ACTION_ARGUMENT = rf"(?:(?!\b(?:and|then|until|while|before|after|{_TIMED_ACTIONS})\b)[^.;!?\n])"
_DONENESS_CLAUSE = rf"(?:(?!\b(?:then|while|before|after|{_TIMED_ACTIONS})\b)[^.;!?\n])"
_DURATION_NUMBER = r"\d{1,4}(?:\.\d{1,2})?"
_ISO_DURATION = re.compile(r"P(?:(\d{1,4})D)?(?:T(?:(\d{1,4})H)?(?:(\d{1,4})M)?)?")
_TIMED_STEP = re.compile(
    rf"(?<!\bnot )\b(?P<action>{_TIMED_ACTIONS})\s+"
    rf"(?:(?:{_ACTION_ARGUMENT}{{1,80}}?\b)?"
    rf"(?:for\s+|until\s+{_DONENESS_CLAUSE}{{1,100}}?,\s+))?"
    r"(?:(?:about|approximately|another)\s+)?"
    rf"(?P<start>{_DURATION_NUMBER})"
    rf"(?:\s*(?:[-–—]|to)\s*(?P<end>{_DURATION_NUMBER}))?\s*"
    r"(?P<unit>hours?|hrs?|minutes?|mins?)\b"
    r"(?:\.?\s+(?:and\s+)?(?P<extra_minutes>\d{1,2})\s*(?:minutes?|mins?)\b)?",
    re.IGNORECASE,
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

        for property_name, field in (
            ("recipeYield", "serves"),
            ("prepTime", "prep_time"),
            ("cookTime", "cook_time"),
        ):
            element = soup.select_one(f'[itemprop~="{property_name}"]')
            if element is None:
                continue
            value = str(element.get("content") or element.get("datetime") or element.get_text())
            if field == "serves":
                parsed = MetadataExtractor.parse_servings(value)
            else:
                parsed = MetadataExtractor.parse_time(value)
            if parsed:
                metadata[field] = str(parsed)

        return metadata

    @staticmethod
    def extract_step_times(instructions: str) -> list[dict[str, str | int]]:
        """Extract durations tied to individual actions in the instructions."""
        steps = []
        paragraphs = re.split(r"\n\s*\n", instructions)
        matches = (
            match
            for paragraph in paragraphs
            for match in _TIMED_STEP.finditer(" ".join(paragraph.split()))
        )
        for match in matches:
            action = match["action"].casefold()
            unit = match["unit"].casefold()
            hours = unit.startswith("h")
            if match["extra_minutes"] and not hours:
                continue
            factor = 60 if hours else 1
            extra = int(match["extra_minutes"] or 0)
            minimum = round(float(match["start"]) * factor) + extra
            maximum = round(float(match["end"] or match["start"]) * factor) + extra
            if not 0 < minimum <= maximum:
                continue
            kind = "cook"
            if action in _RESTING_ACTIONS:
                kind = "rest"
            elif action in _MARINATING_ACTIONS:
                kind = "marinate"
            steps.append({
                "action": action,
                "kind": kind,
                "min_minutes": minimum,
                "max_minutes": maximum,
            })
        return steps

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

        iso_match = _ISO_DURATION.fullmatch(raw_value.strip().upper())
        if iso_match:
            days, hours, minutes = (int(part or 0) for part in iso_match.groups())
            return days * 1440 + hours * 60 + minutes or None

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

    @staticmethod
    def extract_with_patterns(
        soup: BeautifulSoup, text: str, title: str = ""
    ) -> tuple[Dict[str, str], Dict[str, Any]]:
        """Modern pattern-based metadata extraction with confidence scoring.

        This method uses multi-dimensional pattern detection to extract metadata:
        1. Structural HTML detection (Schema.org, CSS classes, headers)
        2. Pattern-based confidence scoring
        3. Linguistic quality analysis

        Args:
            soup: BeautifulSoup object of the recipe HTML
            text: Plain text content of the recipe
            title: Recipe title for context

        Returns:
            tuple: (metadata_dict, analysis_metadata)
                - metadata_dict: Extracted metadata fields
                - analysis_metadata: {
                    'strategy': str,
                    'confidence_scores': dict,
                    'used_structural_detector': bool,
                    'zone_count': int,
                    'fields_extracted': list,
                  }
        """
        from epub_recipe_parser.core.patterns import (
            MetadataPatternDetector,
            MetadataLinguisticAnalyzer,
            MetadataStructuralDetector,
        )

        analysis_metadata: Dict[str, Any] = {
            'strategy': None,
            'confidence_scores': {},
            'used_structural_detector': False,
            'zone_count': 0,
            'fields_extracted': [],
        }

        # Try structural detection first
        zones = MetadataStructuralDetector.find_metadata_zones(soup)

        if zones:
            analysis_metadata['used_structural_detector'] = True
            analysis_metadata['zone_count'] = len(zones)
            analysis_metadata['strategy'] = 'structural'

            # Combine text from all zones
            combined_zone_text = " ".join([
                zone.zone.get_text(strip=True) for zone in zones if zone.zone
            ])

            # Extract metadata with confidence from zones
            pattern_results = MetadataPatternDetector.extract_metadata_with_confidence(
                combined_zone_text, title
            )

            if pattern_results:
                # Convert pattern results to legacy format
                metadata = {}
                for field, data in pattern_results.items():
                    value = data['value']
                    confidence = data['confidence']

                    # Parse values using legacy parsers
                    if field == 'servings':
                        parsed = MetadataExtractor.parse_servings(value)
                        if parsed:
                            metadata['serves'] = parsed
                            analysis_metadata['confidence_scores']['serves'] = confidence
                    elif field == 'prep_time':
                        parsed = MetadataExtractor.parse_time(value)  # type: ignore[assignment]
                        if parsed is not None:
                            metadata['prep_time'] = str(parsed)  # type: ignore[assignment]
                            analysis_metadata['confidence_scores']['prep_time'] = confidence
                    elif field == 'cook_time':
                        parsed = MetadataExtractor.parse_time(value)  # type: ignore[assignment]
                        if parsed is not None:
                            metadata['cook_time'] = str(parsed)  # type: ignore[assignment]
                            analysis_metadata['confidence_scores']['cook_time'] = confidence
                    else:
                        # Pass through other fields
                        metadata[field] = value
                        analysis_metadata['confidence_scores'][field] = confidence

                analysis_metadata['fields_extracted'] = list(metadata.keys())

                # Calculate overall linguistic score for the zones
                if combined_zone_text:
                    linguistic_score = MetadataLinguisticAnalyzer.calculate_metadata_score(
                        combined_zone_text
                    )
                    analysis_metadata['linguistic_score'] = linguistic_score

                return metadata, analysis_metadata

        # Fallback to original extraction method
        analysis_metadata['strategy'] = 'legacy'
        metadata = MetadataExtractor.extract(soup, text, title)

        # Calculate confidence for legacy extraction
        combined_text = f"{title} {text}"
        for field in metadata.keys():
            # Estimate confidence based on field type
            if field == 'serves':
                confidence = MetadataPatternDetector.calculate_confidence(
                    metadata[field], 'servings'
                )
            elif field in ('prep_time', 'cook_time'):
                confidence = MetadataPatternDetector.calculate_confidence(
                    metadata[field], 'time'
                )
            elif field == 'cooking_method':
                confidence = MetadataPatternDetector.calculate_confidence(
                    combined_text, 'method'
                )
            elif field == 'protein_type':
                confidence = MetadataPatternDetector.calculate_confidence(
                    combined_text, 'protein'
                )
            elif field == 'difficulty':
                confidence = MetadataPatternDetector.calculate_confidence(
                    combined_text, 'difficulty'
                )
            else:
                confidence = 0.5  # Default moderate confidence

            analysis_metadata['confidence_scores'][field] = confidence

        analysis_metadata['fields_extracted'] = list(metadata.keys())

        return metadata, analysis_metadata
