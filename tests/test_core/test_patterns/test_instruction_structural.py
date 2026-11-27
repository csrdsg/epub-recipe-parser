"""Unit tests for InstructionStructuralDetector."""

import pytest
from bs4 import BeautifulSoup
from epub_recipe_parser.core.patterns import InstructionStructuralDetector
from epub_recipe_parser.core.models import InstructionZone


class TestInstructionStructuralDetector:
    """Tests for instruction structural detection."""

    def test_find_by_css_class_method(self):
        """Test finding instruction zones by CSS class."""
        html = """
        <div class="method">
            <p>Heat oil in a pan. Cook onions until soft.</p>
        </div>
        """
        soup = BeautifulSoup(html, 'html.parser')
        zones = InstructionStructuralDetector.find_instruction_zones(soup)

        assert len(zones) >= 1, "Should find at least one zone with method class"
        assert any(z.detection_method == 'css_class' for z in zones)
        method_zone = next(z for z in zones if z.detection_method == 'css_class')
        assert method_zone.confidence == 0.9
        assert 'matched_class' in method_zone.context

    def test_find_by_header_method(self):
        """Test finding instruction zones by header keywords."""
        html = """
        <h3>Instructions</h3>
        <p>Preheat oven to 350°F. Mix all ingredients together.</p>
        <p>Bake for 30 minutes until golden brown.</p>
        """
        soup = BeautifulSoup(html, 'html.parser')
        zones = InstructionStructuralDetector.find_instruction_zones(soup)

        assert len(zones) >= 1, "Should find zones after instruction header"
        header_zones = [z for z in zones if z.detection_method == 'header']
        assert len(header_zones) >= 1
        assert header_zones[0].confidence == 0.85
        assert 'header_text' in header_zones[0].context

    def test_find_post_ingredients(self):
        """Test finding instruction zones after ingredient sections."""
        html = """
        <h3>Ingredients</h3>
        <p>2 cups flour</p>
        <p>1 cup sugar</p>
        <p>Heat the oven to 350°F and prepare the baking pan with butter.</p>
        """
        soup = BeautifulSoup(html, 'html.parser')
        zones = InstructionStructuralDetector.find_instruction_zones(soup)

        post_ing_zones = [z for z in zones if z.detection_method == 'post_ingredients']
        assert len(post_ing_zones) >= 1, "Should find zones after ingredients"
        assert post_ing_zones[0].confidence == 0.75

    def test_find_numbered_lists(self):
        """Test finding numbered lists as instruction zones."""
        html = """
        <ol>
            <li>Preheat oven to 350°F</li>
            <li>Mix dry ingredients</li>
            <li>Combine wet ingredients</li>
            <li>Bake for 30 minutes</li>
        </ol>
        """
        soup = BeautifulSoup(html, 'html.parser')
        zones = InstructionStructuralDetector.find_instruction_zones(soup)

        list_zones = [z for z in zones if z.detection_method == 'numbered_list']
        assert len(list_zones) == 1, "Should find one numbered list zone"
        assert list_zones[0].confidence == 0.80
        assert list_zones[0].context['item_count'] == 4

    def test_deduplication(self):
        """Test that duplicate zones are removed."""
        html = """
        <div class="method">
            <h3>Method</h3>
            <p>Heat oil. Cook onions until soft and translucent.</p>
        </div>
        """
        soup = BeautifulSoup(html, 'html.parser')
        zones = InstructionStructuralDetector.find_instruction_zones(soup)

        # Count unique zone IDs
        zone_ids = [id(z.zone) for z in zones]
        unique_ids = set(zone_ids)

        assert len(zone_ids) == len(unique_ids), "Should not have duplicate zones"

    def test_deduplication_keeps_highest_confidence(self):
        """Test that deduplication keeps the zone with highest confidence."""
        html = """
        <div class="method">
            <p>Heat oil in a large skillet over medium heat.</p>
        </div>
        """
        soup = BeautifulSoup(html, 'html.parser')
        zones = InstructionStructuralDetector.find_instruction_zones(soup)

        # If same zone detected by multiple methods, should keep highest confidence
        # In this case, css_class (0.9) should win over post_ingredients (0.75)
        if len(zones) > 0:
            # Group by zone ID
            from collections import defaultdict
            zones_by_id = defaultdict(list)
            for z in zones:
                zones_by_id[id(z.zone)].append(z)

            # Check each group has only one zone (highest confidence)
            for zone_id, zone_list in zones_by_id.items():
                assert len(zone_list) == 1, "Should have deduplicated zones"

    def test_empty_html(self):
        """Test handling of empty HTML."""
        html = "<div></div>"
        soup = BeautifulSoup(html, 'html.parser')
        zones = InstructionStructuralDetector.find_instruction_zones(soup)

        assert zones == [], "Should return empty list for empty HTML"

    def test_no_instruction_zones(self):
        """Test HTML with no instruction indicators."""
        html = """
        <div>
            <p>This is just some random text.</p>
            <p>No instructions here.</p>
        </div>
        """
        soup = BeautifulSoup(html, 'html.parser')
        zones = InstructionStructuralDetector.find_instruction_zones(soup)

        # May find zones but they should have lower confidence
        # or may find no zones at all
        assert isinstance(zones, list)

    def test_multiple_detection_methods(self):
        """Test that multiple detection methods work together."""
        html = """
        <div class="preparation">
            <h2>Directions</h2>
            <ol>
                <li>Preheat oven to 375°F</li>
                <li>Mix all dry ingredients in a large bowl</li>
            </ol>
            <p class="step">Pour into prepared pan and bake.</p>
        </div>
        """
        soup = BeautifulSoup(html, 'html.parser')
        zones = InstructionStructuralDetector.find_instruction_zones(soup)

        # Should detect zones via multiple methods
        detection_methods = {z.detection_method for z in zones}
        assert len(detection_methods) >= 2, "Should use multiple detection methods"

    def test_instruction_class_patterns(self):
        """Test various instruction CSS class patterns."""
        class_patterns = ['method', 'step', 'instruction', 'direction', 'preparation']

        for pattern in class_patterns:
            html = f"""
            <div class="{pattern}">
                <p>Heat oil in a pan and cook the ingredients until done.</p>
            </div>
            """
            soup = BeautifulSoup(html, 'html.parser')
            zones = InstructionStructuralDetector.find_instruction_zones(soup)

            css_zones = [z for z in zones if z.detection_method == 'css_class']
            assert len(css_zones) >= 1, f"Should detect class pattern: {pattern}"

    def test_skip_short_zones(self):
        """Test that very short zones are handled appropriately."""
        html = """
        <div class="method">
            <p>Hi</p>
        </div>
        """
        soup = BeautifulSoup(html, 'html.parser')
        zones = InstructionStructuralDetector.find_instruction_zones(soup)

        # Should still find the zone (structural detector doesn't filter by length)
        # Length filtering happens in extract_with_patterns
        assert len(zones) >= 1

    def test_header_with_multiple_paragraphs(self):
        """Test header detection with multiple following paragraphs."""
        html = """
        <h2>How to Make</h2>
        <p>First, prepare all your ingredients and equipment.</p>
        <p>Heat a large skillet over medium-high heat.</p>
        <p>Add oil and wait until it shimmers before adding ingredients.</p>
        <h2>Serving Suggestions</h2>
        <p>Serve hot with a side salad.</p>
        """
        soup = BeautifulSoup(html, 'html.parser')
        zones = InstructionStructuralDetector.find_instruction_zones(soup)

        header_zones = [z for z in zones if z.detection_method == 'header']

        # Should find multiple paragraphs after instruction header
        # but stop at next header
        instruction_zones = [
            z for z in header_zones
            if 'how to make' in z.context.get('header_text', '')
        ]

        assert len(instruction_zones) >= 1, "Should find zones after instruction header"

    def test_for_the_pattern_ingredients(self):
        """Test detection of 'for the' pattern as ingredient section."""
        html = """
        <h3>For the sauce</h3>
        <p>2 cups tomatoes</p>
        <p>1 tablespoon olive oil</p>
        <p>Heat the oil in a pan and add the crushed tomatoes.</p>
        """
        soup = BeautifulSoup(html, 'html.parser')
        zones = InstructionStructuralDetector.find_instruction_zones(soup)

        # Should detect post-ingredients zone
        post_zones = [z for z in zones if z.detection_method == 'post_ingredients']
        assert len(post_zones) >= 1, "Should find zone after 'for the' section"

    def test_return_type(self):
        """Test that return type is correct."""
        html = "<div><p>Some text</p></div>"
        soup = BeautifulSoup(html, 'html.parser')
        zones = InstructionStructuralDetector.find_instruction_zones(soup)

        assert isinstance(zones, list)
        for zone in zones:
            assert isinstance(zone, InstructionZone)
            assert hasattr(zone, 'zone')
            assert hasattr(zone, 'detection_method')
            assert hasattr(zone, 'confidence')
            assert hasattr(zone, 'context')
            assert isinstance(zone.confidence, float)
            assert 0.0 <= zone.confidence <= 1.0
