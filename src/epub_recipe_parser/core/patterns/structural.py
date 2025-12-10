"""Structural detection for HTML document analysis."""

from typing import List
from bs4 import BeautifulSoup, Tag


class StructuralDetector:
    """
    Detects ingredient sections based on HTML structure.

    TODO: This is a stub implementation. Full implementation should include:
    - CSS class pattern recognition
    - Semantic HTML analysis
    - DOM tree traversal strategies
    - Context-aware zone detection
    """

    # Common CSS classes and IDs for ingredients
    INGREDIENT_CLASS_PATTERNS = [
        "ingredient", "ingredients", "ingred",
        "recipe-ingredient", "recipe-ingredients",
        "component", "components",
        "item", "items",
        "list", "listing"
    ]

    # Common header text patterns
    INGREDIENT_HEADER_PATTERNS = [
        "ingredient", "ingred", "what you need", "you will need",
        "for the", "for this recipe", "shopping list"
    ]

    @staticmethod
    def find_ingredient_zones(soup: BeautifulSoup) -> List[Tag]:
        """
        Find potential ingredient zones in HTML structure.

        Args:
            soup: BeautifulSoup object to analyze

        Returns:
            List of Tag objects that may contain ingredients
        """
        if not soup:
            return []

        zones: List[Tag] = []

        # Strategy 1: Find by CSS class patterns
        for pattern in StructuralDetector.INGREDIENT_CLASS_PATTERNS:
            # Check class attributes
            def has_pattern_in_class(x: str | List[str] | None) -> bool:
                if not x:
                    return False
                if isinstance(x, str):
                    return pattern in x.lower()
                return pattern in " ".join(x).lower()

            elements = soup.find_all(attrs={"class": has_pattern_in_class})
            zones.extend(elements)

            # Check id attributes
            def has_pattern_in_id(x: str | None) -> bool:
                return bool(x and pattern in x.lower())

            elements = soup.find_all(attrs={"id": has_pattern_in_id})
            zones.extend(elements)

        # Strategy 2: Find by header text patterns
        for header_tag in ["h1", "h2", "h3", "h4", "h5", "h6"]:
            headers = soup.find_all(header_tag)
            for header in headers:
                header_text = header.get_text().lower().strip()
                if any(pattern in header_text for pattern in StructuralDetector.INGREDIENT_HEADER_PATTERNS):
                    # Include the header's next sibling(s) as potential zones
                    next_elem = header.find_next_sibling()
                    if next_elem:
                        zones.append(next_elem)

        # Strategy 3: Find lists (ul, ol) that might be ingredients
        # Look for lists near ingredient headers or with ingredient-like classes
        lists = soup.find_all(["ul", "ol"])
        for lst in lists:
            # Check if list has relevant classes
            classes_raw = lst.get("class")
            # Normalize classes to list of strings
            if isinstance(classes_raw, str):
                classes = [classes_raw]
            elif isinstance(classes_raw, list):
                classes = [str(c) for c in classes_raw]
            elif classes_raw is None:
                classes = []
            else:
                classes = []

            if any(pattern in " ".join(classes).lower() for pattern in StructuralDetector.INGREDIENT_CLASS_PATTERNS):
                zones.append(lst)
                continue

            # Check if list follows an ingredient header
            prev_header = lst.find_previous(["h1", "h2", "h3", "h4", "h5", "h6"])
            if prev_header:
                header_text = prev_header.get_text().lower().strip()
                if any(pattern in header_text for pattern in StructuralDetector.INGREDIENT_HEADER_PATTERNS):
                    zones.append(lst)

        # Remove duplicates while preserving order
        seen = set()
        unique_zones = []
        for zone in zones:
            zone_id = id(zone)
            if zone_id not in seen:
                seen.add(zone_id)
                unique_zones.append(zone)

        return unique_zones
