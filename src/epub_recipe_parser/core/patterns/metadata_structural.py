"""Structural detection for metadata zones in HTML."""

import re
from typing import List, Dict, Any, Set
from bs4 import BeautifulSoup, Tag
from dataclasses import dataclass, field


@dataclass
class MetadataZone:
    """Represents a potential metadata zone in HTML."""
    zone: Tag
    detection_method: str
    confidence: float
    field_hints: List[str]  # Which metadata fields this zone might contain
    context: Dict[str, Any] = field(default_factory=dict)


class MetadataStructuralDetector:
    """Detects metadata zones in HTML structure."""

    # CSS classes commonly used for metadata
    METADATA_CSS_CLASSES = {
        'meta', 'metadata', 'recipe-meta', 'recipe-info', 'info',
        'details', 'recipe-details', 'stats', 'recipe-stats',
        'servings', 'yield', 'time', 'prep', 'cook', 'difficulty'
    }

    # Header patterns for metadata sections
    METADATA_HEADER_PATTERNS = [
        re.compile(r'recipe\s+info', re.IGNORECASE),
        re.compile(r'details', re.IGNORECASE),
        re.compile(r'stats', re.IGNORECASE),
        re.compile(r'at\s+a\s+glance', re.IGNORECASE),
    ]

    # Attribute patterns
    METADATA_ATTRS = {
        'itemprop': {'recipeYield', 'totalTime', 'prepTime', 'cookTime'},
        'class': METADATA_CSS_CLASSES,
        'id': {'recipe-meta', 'recipe-info', 'metadata'}
    }

    @classmethod
    def find_metadata_zones(cls, soup: BeautifulSoup) -> List[MetadataZone]:
        """Find potential metadata zones with context.

        Detection strategies (in order of confidence):
        1. Schema.org microdata (0.95 confidence)
        2. CSS class-based detection (0.90 confidence)
        3. Header-based detection (0.85 confidence)
        4. List-based detection (0.75 confidence)
        5. Early-position detection (0.70 confidence)

        Args:
            soup: BeautifulSoup object of recipe HTML

        Returns:
            List of MetadataZone objects, deduplicated and sorted by confidence
        """
        zones = []

        # Strategy 1: Schema.org microdata
        zones.extend(cls._find_by_schema_org(soup))

        # Strategy 2: CSS class-based
        zones.extend(cls._find_by_css_class(soup))

        # Strategy 3: Header-based
        zones.extend(cls._find_by_header(soup))

        # Strategy 4: List-based (dl, ul with specific patterns)
        zones.extend(cls._find_by_list_structure(soup))

        # Strategy 5: Early position (metadata often at top)
        zones.extend(cls._find_by_position(soup))

        # Deduplicate and sort
        return cls._deduplicate_zones(zones)

    @classmethod
    def _find_by_schema_org(cls, soup: BeautifulSoup) -> List[MetadataZone]:
        """Find metadata zones using Schema.org microdata."""
        zones = []

        # Find elements with itemprop attributes
        for attr_value in cls.METADATA_ATTRS['itemprop']:
            elements = soup.find_all(attrs={'itemprop': attr_value})
            for elem in elements:
                # Get parent container
                parent = elem.find_parent(['div', 'section', 'article'])
                if parent:
                    field_hint = cls._itemprop_to_field(attr_value)
                    zones.append(MetadataZone(
                        zone=parent,
                        detection_method='schema_org',
                        confidence=0.95,
                        field_hints=[field_hint] if field_hint else [],
                        context={'itemprop': attr_value}
                    ))

        return zones

    @classmethod
    def _find_by_css_class(cls, soup: BeautifulSoup) -> List[MetadataZone]:
        """Find metadata zones by CSS class names."""
        zones = []

        for elem in soup.find_all(class_=True):
            elem_classes_raw = elem.get('class')
            # Normalize to list of strings
            if isinstance(elem_classes_raw, str):
                elem_classes = [elem_classes_raw]
            elif isinstance(elem_classes_raw, list):
                elem_classes = [str(c) for c in elem_classes_raw]
            elif elem_classes_raw is None:
                elem_classes = []
            else:
                elem_classes = []

            # Check if any class matches our metadata patterns
            matching_classes = [
                c for c in elem_classes
                if any(meta_class in c.lower() for meta_class in cls.METADATA_CSS_CLASSES)
            ]

            if matching_classes:
                # Determine which fields this might contain based on class names
                field_hints = cls._infer_fields_from_classes(elem_classes)

                zones.append(MetadataZone(
                    zone=elem,
                    detection_method='css_class',
                    confidence=0.90,
                    field_hints=field_hints,
                    context={'classes': matching_classes}
                ))

        return zones

    @classmethod
    def _find_by_header(cls, soup: BeautifulSoup) -> List[MetadataZone]:
        """Find metadata zones by header keywords."""
        zones = []

        # Find all headers
        for header in soup.find_all(['h1', 'h2', 'h3', 'h4', 'h5', 'h6']):
            header_text = header.get_text().strip()

            # Check if header matches metadata patterns
            for pattern in cls.METADATA_HEADER_PATTERNS:
                if pattern.search(header_text):
                    # Find the content after this header
                    content_elem = cls._find_content_after_header(header)
                    if content_elem:
                        zones.append(MetadataZone(
                            zone=content_elem,
                            detection_method='header',
                            confidence=0.85,
                            field_hints=[],  # Will be determined by content analysis
                            context={'header_text': header_text}
                        ))
                    break

        return zones

    @classmethod
    def _find_by_list_structure(cls, soup: BeautifulSoup) -> List[MetadataZone]:
        """Find metadata in definition lists or structured lists."""
        zones = []

        # Definition lists (dl) often contain metadata
        for dl in soup.find_all('dl'):
            # Check if this looks like metadata (short key-value pairs)
            dt_elements = dl.find_all('dt')
            if 1 <= len(dt_elements) <= 10:  # Reasonable number of metadata items
                zones.append(MetadataZone(
                    zone=dl,
                    detection_method='definition_list',
                    confidence=0.80,
                    field_hints=cls._extract_fields_from_dt_elements(dt_elements),
                    context={'item_count': len(dt_elements)}
                ))

        # Unordered lists with colon pattern (key: value)
        for ul in soup.find_all('ul'):
            li_elements = ul.find_all('li', recursive=False)
            if 1 <= len(li_elements) <= 10:
                # Check if items follow "key: value" pattern
                colon_count = sum(1 for li in li_elements if ':' in li.get_text())
                if colon_count / len(li_elements) > 0.5:  # More than half have colons
                    zones.append(MetadataZone(
                        zone=ul,
                        detection_method='list_structure',
                        confidence=0.75,
                        field_hints=[],
                        context={'colon_ratio': colon_count / len(li_elements)}
                    ))

        return zones

    @classmethod
    def _find_by_position(cls, soup: BeautifulSoup) -> List[MetadataZone]:
        """Find metadata by early position in document (metadata often at top)."""
        zones = []

        # Get the first few significant elements
        body = soup.find('body') or soup
        early_elements = []

        for elem in body.find_all(['div', 'section', 'article', 'p'], limit=10):
            text = elem.get_text(strip=True)
            # Skip if too long (likely not metadata)
            if len(text) > 200:
                continue
            # Check if contains metadata keywords
            if any(word in text.lower() for word in ['serves', 'prep', 'cook', 'time', 'yield', 'makes']):
                early_elements.append(elem)

        # Add early elements as low-confidence metadata zones
        for elem in early_elements[:3]:  # Only first 3 to avoid false positives
            zones.append(MetadataZone(
                zone=elem,
                detection_method='early_position',
                confidence=0.70,
                field_hints=[],
                context={'position': 'top'}
            ))

        return zones

    @classmethod
    def _find_content_after_header(cls, header: Tag) -> Tag:
        """Find the content block after a header.

        Args:
            header: Header tag

        Returns:
            Content element (next sibling or parent's next content)
        """
        # Try next sibling first
        next_elem = header.find_next_sibling()
        if next_elem and next_elem.name in ['div', 'section', 'p', 'dl', 'ul']:
            return next_elem

        # Try parent's next sibling
        parent = header.find_parent(['div', 'section', 'article'])
        if parent:
            next_elem = parent.find_next_sibling()
            if next_elem:
                return next_elem

        # Fallback: return header's parent
        return header.find_parent(['div', 'section']) or header

    @classmethod
    def _infer_fields_from_classes(cls, class_names: List[str]) -> List[str]:
        """Infer which metadata fields from CSS class names."""
        fields = []
        class_str = ' '.join(class_names).lower()

        if any(word in class_str for word in ['serve', 'yield', 'portion']):
            fields.append('servings')
        if any(word in class_str for word in ['prep', 'preparation']):
            fields.append('prep_time')
        if any(word in class_str for word in ['cook', 'cooking', 'bake']):
            fields.append('cook_time')
        if 'time' in class_str:
            fields.append('time')
        if 'difficulty' in class_str:
            fields.append('difficulty')
        if 'method' in class_str:
            fields.append('cooking_method')

        return fields

    @classmethod
    def _extract_fields_from_dt_elements(cls, dt_elements: List[Tag]) -> List[str]:
        """Extract field hints from definition term elements."""
        fields = []
        for dt in dt_elements:
            text = dt.get_text().lower()
            if any(word in text for word in ['serve', 'yield', 'portion']):
                fields.append('servings')
            if 'prep' in text:
                fields.append('prep_time')
            if 'cook' in text:
                fields.append('cook_time')
            if 'difficulty' in text:
                fields.append('difficulty')
            if 'method' in text:
                fields.append('cooking_method')

        return fields

    @classmethod
    def _itemprop_to_field(cls, itemprop: str) -> str:
        """Map Schema.org itemprop to field name."""
        mapping = {
            'recipeYield': 'servings',
            'totalTime': 'total_time',
            'prepTime': 'prep_time',
            'cookTime': 'cook_time',
        }
        return mapping.get(itemprop, '')

    @classmethod
    def _deduplicate_zones(cls, zones: List[MetadataZone]) -> List[MetadataZone]:
        """Remove duplicate zones and sort by confidence.

        Zones are considered duplicates if they refer to the same HTML element
        or if one is contained within another.

        Args:
            zones: List of metadata zones

        Returns:
            Deduplicated list sorted by confidence (highest first)
        """
        if not zones:
            return []

        unique_zones: List[MetadataZone] = []
        seen_elements: Set[int] = set()

        # Sort by confidence first (highest first)
        sorted_zones = sorted(zones, key=lambda z: z.confidence, reverse=True)

        for zone in sorted_zones:
            # Skip if we've seen this exact element
            zone_id = id(zone.zone)
            if zone_id in seen_elements:
                continue

            # Skip if this zone is contained in an already-added zone
            is_duplicate = False
            for existing_zone in unique_zones:
                if cls._is_descendant(zone.zone, existing_zone.zone):
                    is_duplicate = True
                    break
                # Also skip if existing zone is contained in this one (keep higher confidence)
                if cls._is_descendant(existing_zone.zone, zone.zone):
                    # Remove existing and add this one instead
                    unique_zones.remove(existing_zone)
                    seen_elements.discard(id(existing_zone.zone))
                    break

            if not is_duplicate:
                unique_zones.append(zone)
                seen_elements.add(zone_id)

        return unique_zones

    @staticmethod
    def _is_descendant(potential_child: Tag, potential_parent: Tag) -> bool:
        """Check if potential_child is a descendant of potential_parent."""
        current = potential_child.parent
        while current:
            if current == potential_parent:
                return True
            current = current.parent
        return False
