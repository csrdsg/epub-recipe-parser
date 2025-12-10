"""Structural detection for ingredients in HTML documents."""

from dataclasses import dataclass, field
from typing import List, Dict, Any
from bs4 import BeautifulSoup, Tag
import re


@dataclass
class IngredientZone:
    """Represents a potential ingredient zone in HTML structure."""

    zone: Tag
    detection_method: str
    confidence: float
    context: Dict[str, Any] = field(default_factory=dict)

    def get_text(self) -> str:
        """Extract text from zone."""
        return self.zone.get_text(separator="\n", strip=True)


class IngredientStructuralDetector:
    """Detects ingredient zones in HTML structure with confidence scoring."""

    # CSS classes commonly used for ingredient sections
    INGREDIENT_CSS_CLASSES = {
        'ingredient', 'ingredients', 'ingred', 'ings', 'ing',
        'recipe-ingredient', 'recipe-ingredients', 'recipeingredient',
        'component', 'components', 'item', 'items',
        'shopping-list', 'shoppinglist', 'grocery', 'groceries'
    }

    # ID patterns for ingredient sections
    INGREDIENT_ID_PATTERNS = {
        'ingredient', 'ingredients', 'ingred', 'ings',
        'recipe-ingredient', 'shopping', 'grocery'
    }

    # Header text patterns that indicate ingredient sections
    INGREDIENT_HEADER_PATTERNS = [
        r'\bingredient(?:s)?\b',
        r'\bwhat you(?:\'ll)? need\b',
        r'\byou(?:\'ll| will) need\b',
        r'\bshopping list\b',
        r'\bgrocery list\b',
        r'\bfor (?:the|this) (?:recipe|dish)\b',
        r'\bfor the (?:\w+)\b',  # "For the sauce", "For the dough"
    ]

    # Compiled patterns for performance
    HEADER_PATTERN = re.compile(
        '|'.join(INGREDIENT_HEADER_PATTERNS),
        re.IGNORECASE
    )

    @classmethod
    def find_ingredient_zones(cls, soup: BeautifulSoup) -> List[IngredientZone]:
        """Find potential ingredient zones with confidence scoring.

        Detection strategies (in order of confidence):
        1. Schema.org microdata (0.95 confidence)
        2. CSS class-based detection (0.90 confidence)
        3. ID-based detection (0.85 confidence)
        4. Header-based detection (0.80 confidence)
        5. List-based detection (0.70-0.75 confidence)
        6. Paragraph class patterns (0.75 confidence)
        7. Position-based heuristics (0.65 confidence)

        Args:
            soup: BeautifulSoup object to analyze

        Returns:
            List of IngredientZone objects, sorted by confidence (highest first)
        """
        if not soup:
            return []

        zones: List[IngredientZone] = []

        # Strategy 1: Schema.org microdata
        zones.extend(cls._find_schema_org_zones(soup))

        # Strategy 2: CSS class-based detection
        zones.extend(cls._find_class_based_zones(soup))

        # Strategy 3: ID-based detection
        zones.extend(cls._find_id_based_zones(soup))

        # Strategy 4: Header-based detection
        zones.extend(cls._find_header_based_zones(soup))

        # Strategy 5: List-based detection
        zones.extend(cls._find_list_based_zones(soup))

        # Strategy 6: Paragraph class patterns (e.g., <p class="ing">)
        zones.extend(cls._find_paragraph_based_zones(soup))

        # Strategy 7: Position-based heuristics
        zones.extend(cls._find_position_based_zones(soup))

        # Remove duplicates (same zone detected by multiple strategies)
        zones = cls._deduplicate_zones(zones)

        # Sort by confidence (highest first)
        zones.sort(key=lambda z: z.confidence, reverse=True)

        return zones

    @classmethod
    def _find_schema_org_zones(cls, soup: BeautifulSoup) -> List[IngredientZone]:
        """Find zones marked with Schema.org microdata."""
        zones = []

        # Look for itemtype="http://schema.org/Recipe" and recipeIngredient
        for elem in soup.find_all(attrs={'itemprop': 'recipeIngredient'}):
            zones.append(IngredientZone(
                zone=elem,
                detection_method='schema_org',
                confidence=0.95,
                context={'type': 'microdata', 'property': 'recipeIngredient'}
            ))

        # Look for class="recipe ingredient" in schema context
        recipe_containers = soup.find_all(attrs={'itemtype': re.compile(r'schema\.org/Recipe')})
        for container in recipe_containers:
            for elem in container.find_all(['ul', 'ol', 'div']):
                if cls._element_has_ingredient_class(elem):
                    zones.append(IngredientZone(
                        zone=elem,
                        detection_method='schema_org_context',
                        confidence=0.92,
                        context={'type': 'schema_context', 'parent': 'Recipe'}
                    ))

        return zones

    @classmethod
    def _find_class_based_zones(cls, soup: BeautifulSoup) -> List[IngredientZone]:
        """Find zones with ingredient-related CSS classes."""
        zones = []

        for elem in soup.find_all(['div', 'section', 'article', 'ul', 'ol']):
            if cls._element_has_ingredient_class(elem):
                # Check specificity of class match
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

                class_str = ' '.join(elem_classes).lower()

                # Exact matches get higher confidence
                if any(class_name == keyword for class_name in elem_classes for keyword in cls.INGREDIENT_CSS_CLASSES):
                    confidence = 0.90
                # Partial matches get slightly lower
                elif any(keyword in class_str for keyword in cls.INGREDIENT_CSS_CLASSES):
                    confidence = 0.85
                else:
                    confidence = 0.80

                zones.append(IngredientZone(
                    zone=elem,
                    detection_method='css_class',
                    confidence=confidence,
                    context={'classes': elem_classes, 'tag': elem.name}
                ))

        return zones

    @classmethod
    def _find_id_based_zones(cls, soup: BeautifulSoup) -> List[IngredientZone]:
        """Find zones with ingredient-related IDs."""
        zones = []

        for elem in soup.find_all(attrs={'id': True}):
            elem_id_raw = elem.get('id', '')
            # Normalize to string
            if isinstance(elem_id_raw, str):
                elem_id = elem_id_raw.lower()
            elif isinstance(elem_id_raw, list):
                elem_id = ' '.join(str(i) for i in elem_id_raw).lower()
            else:
                elem_id = str(elem_id_raw).lower()

            if any(pattern in elem_id for pattern in cls.INGREDIENT_ID_PATTERNS):
                zones.append(IngredientZone(
                    zone=elem,
                    detection_method='id_attribute',
                    confidence=0.85,
                    context={'id': elem_id, 'tag': elem.name}
                ))

        return zones

    @classmethod
    def _find_header_based_zones(cls, soup: BeautifulSoup) -> List[IngredientZone]:
        """Find zones following ingredient headers."""
        zones = []

        for header_tag in ['h1', 'h2', 'h3', 'h4', 'h5', 'h6']:
            headers = soup.find_all(header_tag)
            for header in headers:
                header_text = header.get_text(strip=True)

                if cls.HEADER_PATTERN.search(header_text):
                    # Get content after the header
                    next_elem = header.find_next_sibling()

                    if next_elem:
                        # Prefer lists or divs after headers
                        if next_elem.name in ['ul', 'ol']:
                            confidence = 0.85
                        elif next_elem.name in ['div', 'section']:
                            confidence = 0.80
                        else:
                            confidence = 0.75

                        zones.append(IngredientZone(
                            zone=next_elem,
                            detection_method='header_based',
                            confidence=confidence,
                            context={'header_text': header_text, 'header_tag': header_tag}
                        ))

        return zones

    @classmethod
    def _find_list_based_zones(cls, soup: BeautifulSoup) -> List[IngredientZone]:
        """Find lists that look like ingredient lists."""
        zones = []

        # Pattern to detect measurements in list items
        measurement_pattern = re.compile(
            r'\b\d+[\s/\d]*\s*(?:cup|tbsp|tsp|oz|lb|g|kg|ml|l)s?\b',
            re.IGNORECASE
        )

        for list_elem in soup.find_all(['ul', 'ol']):
            items = list_elem.find_all('li', recursive=False)

            if not items or len(items) < 2:
                continue

            # Count items with measurements
            measurement_count = sum(
                1 for item in items
                if measurement_pattern.search(item.get_text())
            )

            ratio = measurement_count / len(items) if items else 0

            # High measurement ratio = likely ingredients
            if ratio >= 0.5:
                confidence = 0.75
            elif ratio >= 0.3:
                confidence = 0.70
            else:
                continue  # Too low ratio, skip

            zones.append(IngredientZone(
                zone=list_elem,
                detection_method='list_based',
                confidence=confidence,
                context={
                    'item_count': len(items),
                    'measurement_ratio': ratio
                }
            ))

        return zones

    @classmethod
    def _find_paragraph_based_zones(cls, soup: BeautifulSoup) -> List[IngredientZone]:
        """Find ingredients formatted as individual paragraphs with classes."""
        zones = []

        # Common paragraph-based ingredient patterns in EPUBs
        ingredient_para_classes = ['ing', 'ingt', 'ings', 'ingst', 'ingd', 'ingredient']

        # Group consecutive ingredient paragraphs
        current_group = []

        for para in soup.find_all('p'):
            para_classes_raw = para.get('class')
            # Normalize to list of strings
            if isinstance(para_classes_raw, str):
                para_classes = [para_classes_raw]
            elif isinstance(para_classes_raw, list):
                para_classes = [str(c) for c in para_classes_raw]
            elif para_classes_raw is None:
                para_classes = []
            else:
                para_classes = []

            # Check if paragraph has ingredient class
            if any(cls in ingredient_para_classes for cls in para_classes):
                current_group.append(para)
            else:
                # End of group, create zone if we have enough paragraphs
                if len(current_group) >= 3:
                    # Create a container zone for the group
                    parent = current_group[0].parent
                    if parent:
                        zones.append(IngredientZone(
                            zone=parent,
                            detection_method='paragraph_class',
                            confidence=0.75,
                            context={
                                'paragraph_count': len(current_group),
                                'classes': para_classes
                            }
                        ))
                current_group = []

        # Check final group
        if len(current_group) >= 3:
            parent = current_group[0].parent
            if parent:
                zones.append(IngredientZone(
                    zone=parent,
                    detection_method='paragraph_class',
                    confidence=0.75,
                    context={'paragraph_count': len(current_group)}
                ))

        return zones

    @classmethod
    def _find_position_based_zones(cls, soup: BeautifulSoup) -> List[IngredientZone]:
        """Find zones using position-based heuristics."""
        zones = []

        # Ingredients often appear early in recipes, before instructions
        # Look for lists or structured content in the first half of the document
        all_lists = soup.find_all(['ul', 'ol'])

        if len(all_lists) >= 2:
            # First list often ingredients, second often instructions
            first_list = all_lists[0]

            # Only add if not already detected by other methods
            zones.append(IngredientZone(
                zone=first_list,
                detection_method='position_heuristic',
                confidence=0.65,
                context={'position': 'first_list', 'total_lists': len(all_lists)}
            ))

        return zones

    @classmethod
    def _element_has_ingredient_class(cls, elem: Tag) -> bool:
        """Check if element has ingredient-related CSS class."""
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

        class_str = ' '.join(elem_classes).lower()
        return any(keyword in class_str for keyword in cls.INGREDIENT_CSS_CLASSES)

    @classmethod
    def _deduplicate_zones(cls, zones: List[IngredientZone]) -> List[IngredientZone]:
        """Remove duplicate zones, keeping highest confidence version.

        Args:
            zones: List of zones that may contain duplicates

        Returns:
            List with duplicates removed
        """
        seen_elements = {}

        for zone in zones:
            zone_id = id(zone.zone)

            if zone_id not in seen_elements:
                seen_elements[zone_id] = zone
            else:
                # Keep zone with higher confidence
                if zone.confidence > seen_elements[zone_id].confidence:
                    seen_elements[zone_id] = zone

        return list(seen_elements.values())
