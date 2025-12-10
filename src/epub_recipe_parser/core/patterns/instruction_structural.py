"""Structural detection for instruction zones in HTML."""

from typing import List, Dict
from bs4 import BeautifulSoup
from epub_recipe_parser.core.models import InstructionZone
from epub_recipe_parser.utils.patterns import INSTRUCTION_KEYWORDS


class InstructionStructuralDetector:
    """Detects instruction zones via HTML structure."""

    INSTRUCTION_CLASS_PATTERNS = [
        "method", "step", "instruction", "direction", "preparation",
        "noindentt", "noindent", "noindentp", "methodp", "stepp",
        "dir", "proc", "procedure"
    ]

    @classmethod
    def find_instruction_zones(cls, soup: BeautifulSoup) -> List[InstructionZone]:
        """Find potential instruction zones with context.

        Args:
            soup: BeautifulSoup object to analyze

        Returns:
            List of InstructionZone objects

        Example:
            >>> html = '<div class="method"><p>Heat oil. Cook onions.</p></div>'
            >>> soup = BeautifulSoup(html, 'html.parser')
            >>> zones = InstructionStructuralDetector.find_instruction_zones(soup)
            >>> len(zones)
            1
            >>> zones[0].detection_method
            'css_class'
            >>> zones[0].confidence
            0.9
        """
        zones = []

        # Strategy 1: CSS class-based detection (confidence: 0.9)
        zones.extend(cls._find_by_css_class(soup))

        # Strategy 2: Header-based detection (confidence: 0.85)
        zones.extend(cls._find_by_header(soup))

        # Strategy 3: Post-ingredients positioning (confidence: 0.75)
        zones.extend(cls._find_post_ingredients(soup))

        # Strategy 4: Numbered list detection (confidence: 0.80)
        zones.extend(cls._find_numbered_lists(soup))

        # Remove duplicates (same Tag object)
        return cls._deduplicate_zones(zones)

    @classmethod
    def _find_by_css_class(cls, soup: BeautifulSoup) -> List[InstructionZone]:
        """Find instruction zones by CSS class patterns.

        Args:
            soup: BeautifulSoup object

        Returns:
            List of InstructionZone objects
        """
        zones = []

        for tag in soup.find_all(['div', 'section', 'p']):
            classes_raw = tag.get('class')
            # Normalize to list of strings
            if isinstance(classes_raw, str):
                classes = [classes_raw]
            elif isinstance(classes_raw, list):
                classes = [str(c) for c in classes_raw]
            elif classes_raw is None:
                classes = []
            else:
                classes = []

            class_str = ' '.join(classes).lower()

            # Check if any instruction class pattern matches
            for pattern in cls.INSTRUCTION_CLASS_PATTERNS:
                if pattern in class_str:
                    zones.append(InstructionZone(
                        zone=tag,
                        detection_method='css_class',
                        confidence=0.9,
                        context={'matched_class': pattern}
                    ))
                    break

        return zones

    @classmethod
    def _find_by_header(cls, soup: BeautifulSoup) -> List[InstructionZone]:
        """Find instruction zones following instruction headers.

        Args:
            soup: BeautifulSoup object

        Returns:
            List of InstructionZone objects
        """
        zones = []

        for header_tag in ['h1', 'h2', 'h3', 'h4', 'h5', 'h6']:
            headers = soup.find_all(header_tag)

            for header in headers:
                header_text = header.get_text().lower().strip()

                # Check if header matches instruction keywords
                if any(keyword in header_text for keyword in INSTRUCTION_KEYWORDS):
                    # Collect all content between this header and the next header
                    content_elements = []
                    next_elem = header.find_next_sibling()

                    while next_elem:
                        # Stop if we hit another header
                        if next_elem.name in ['h1', 'h2', 'h3', 'h4', 'h5', 'h6']:
                            break

                        # Collect paragraphs and lists
                        if next_elem.name in ['p', 'ol', 'ul', 'div']:
                            content_elements.append(next_elem)

                        next_elem = next_elem.find_next_sibling()

                    # If we found content, create zones for substantial elements
                    for elem in content_elements:
                        text = elem.get_text(strip=True)
                        if len(text) > 40:  # Substantial content only
                            zones.append(InstructionZone(
                                zone=elem,
                                detection_method='header',
                                confidence=0.85,
                                context={
                                    'header_text': header_text,
                                    'header_tag': header_tag
                                }
                            ))

        return zones

    @classmethod
    def _find_post_ingredients(cls, soup: BeautifulSoup) -> List[InstructionZone]:
        """Find instruction zones positioned after ingredient sections.

        Args:
            soup: BeautifulSoup object

        Returns:
            List of InstructionZone objects
        """
        zones = []

        # Find ingredient sections first
        ingredient_keywords = ['ingredient', 'for the', 'you will need', "you'll need"]
        ingredient_sections = []

        for tag in soup.find_all(['div', 'section', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'p']):
            text = tag.get_text().lower().strip()

            # Only consider short text as potential headers
            if len(text) < 50 and any(kw in text for kw in ingredient_keywords):
                ingredient_sections.append(tag)

        # Find paragraphs after ingredient sections
        for ing_section in ingredient_sections:
            # Get all siblings after ingredient section
            next_elem = ing_section.find_next_sibling()
            sibling_count = 0

            while next_elem and sibling_count < 10:  # Limit lookahead
                sibling_count += 1

                if next_elem.name in ['p', 'div', 'section']:
                    text = next_elem.get_text(strip=True)

                    # Must be substantial paragraph
                    if len(text) > 40:
                        zones.append(InstructionZone(
                            zone=next_elem,
                            detection_method='post_ingredients',
                            confidence=0.75,
                            context={'after_ingredient_section': True}
                        ))

                next_elem = next_elem.find_next_sibling()

        return zones

    @classmethod
    def _find_numbered_lists(cls, soup: BeautifulSoup) -> List[InstructionZone]:
        """Find numbered lists that might be instructions.

        Args:
            soup: BeautifulSoup object

        Returns:
            List of InstructionZone objects
        """
        zones = []

        for list_tag in soup.find_all('ol'):
            items = list_tag.find_all('li')

            if len(items) >= 2:  # At least 2 steps
                zones.append(InstructionZone(
                    zone=list_tag,
                    detection_method='numbered_list',
                    confidence=0.80,
                    context={'item_count': len(items)}
                ))

        return zones

    @classmethod
    def _deduplicate_zones(cls, zones: List[InstructionZone]) -> List[InstructionZone]:
        """Remove duplicate zones (same Tag object).

        When multiple detection strategies find the same zone, keep the one
        with the highest confidence score.

        Args:
            zones: List of InstructionZone objects

        Returns:
            Deduplicated list with highest-confidence zones
        """
        zone_dict: Dict[int, InstructionZone] = {}

        for zone in zones:
            zone_id = id(zone.zone)

            if zone_id not in zone_dict:
                zone_dict[zone_id] = zone
            else:
                # Keep zone with higher confidence
                if zone.confidence > zone_dict[zone_id].confidence:
                    zone_dict[zone_id] = zone

        return list(zone_dict.values())
