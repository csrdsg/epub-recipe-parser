"""Tests for improved metadata extraction with parsing and validation."""

from bs4 import BeautifulSoup
from epub_recipe_parser.extractors.metadata import MetadataExtractor


class TestServingsParsing:
    """Tests for parse_servings method."""

    def test_parse_simple_number(self):
        """Test parsing a simple number."""
        assert MetadataExtractor.parse_servings("4") == "4"
        assert MetadataExtractor.parse_servings("12") == "12"

    def test_parse_range_with_hyphen(self):
        """Test parsing a range with hyphen."""
        assert MetadataExtractor.parse_servings("4-6") == "4-6"
        assert MetadataExtractor.parse_servings("2-4") == "2-4"

    def test_parse_range_with_to(self):
        """Test parsing a range with 'to'."""
        assert MetadataExtractor.parse_servings("4 to 6") == "4-6"
        assert MetadataExtractor.parse_servings("2 to 4") == "2-4"

    def test_parse_range_with_spaces(self):
        """Test parsing a range with spaces."""
        assert MetadataExtractor.parse_servings("4 - 6") == "4-6"

    def test_parse_with_text(self):
        """Test parsing numbers from text."""
        assert MetadataExtractor.parse_servings("serves 4") == "4"
        assert MetadataExtractor.parse_servings("makes 6 servings") == "6"

    def test_parse_with_parenthetical(self):
        """Test parsing with parenthetical text (should be removed)."""
        assert MetadataExtractor.parse_servings("4 (pressure cooker)") == "4"
        assert MetadataExtractor.parse_servings("6 (large portions)") == "6"

    def test_parse_garbage_input(self):
        """Test that garbage input returns None."""
        assert MetadataExtractor.parse_servings("(pressure cooker):") is None
        assert MetadataExtractor.parse_servings("no numbers here") is None
        assert MetadataExtractor.parse_servings("") is None
        assert MetadataExtractor.parse_servings("   ") is None

    def test_parse_none_input(self):
        """Test that None input returns None."""
        assert MetadataExtractor.parse_servings(None) is None


class TestTimeParsing:
    """Tests for parse_time method."""

    def test_parse_minutes_only(self):
        """Test parsing minutes."""
        assert MetadataExtractor.parse_time("30 minutes") == 30
        assert MetadataExtractor.parse_time("15 mins") == 15
        assert MetadataExtractor.parse_time("45 minute") == 45

    def test_parse_hours_only(self):
        """Test parsing hours."""
        assert MetadataExtractor.parse_time("1 hour") == 60
        assert MetadataExtractor.parse_time("2 hours") == 120
        assert MetadataExtractor.parse_time("3 hrs") == 180

    def test_parse_hours_and_minutes(self):
        """Test parsing hours and minutes together."""
        assert MetadataExtractor.parse_time("1 hour 30 minutes") == 90
        assert MetadataExtractor.parse_time("2 hours 15 minutes") == 135
        assert MetadataExtractor.parse_time("1 hr 45 mins") == 105

    def test_parse_decimal_hours(self):
        """Test parsing decimal hours."""
        assert MetadataExtractor.parse_time("1.5 hours") == 90
        assert MetadataExtractor.parse_time("0.5 hour") == 30
        assert MetadataExtractor.parse_time("2.5 hours") == 150

    def test_parse_just_number(self):
        """Test parsing just a number (assumed to be minutes)."""
        assert MetadataExtractor.parse_time("30") == 30
        assert MetadataExtractor.parse_time("45") == 45

    def test_parse_case_insensitive(self):
        """Test that parsing is case-insensitive."""
        assert MetadataExtractor.parse_time("30 MINUTES") == 30
        assert MetadataExtractor.parse_time("1 HOUR") == 60

    def test_parse_with_extra_text(self):
        """Test parsing with extra text."""
        assert MetadataExtractor.parse_time("about 30 minutes") == 30
        assert MetadataExtractor.parse_time("approximately 1 hour") == 60

    def test_parse_garbage_input(self):
        """Test that garbage input returns None."""
        assert MetadataExtractor.parse_time("invalid") is None
        assert MetadataExtractor.parse_time("no time here") is None
        assert MetadataExtractor.parse_time("") is None
        assert MetadataExtractor.parse_time("   ") is None

    def test_parse_none_input(self):
        """Test that None input returns None."""
        assert MetadataExtractor.parse_time(None) is None

    def test_parse_unreasonable_time(self):
        """Test that unreasonably long times are rejected."""
        # More than 24 hours should return None
        assert MetadataExtractor.parse_time("25 hours") is None
        assert MetadataExtractor.parse_time("1500 minutes") is None

    def test_parse_zero_time(self):
        """Test that zero time is rejected."""
        assert MetadataExtractor.parse_time("0 minutes") is None
        assert MetadataExtractor.parse_time("0") is None


class TestMetadataExtraction:
    """Tests for improved metadata extraction."""

    def test_extract_serves_with_parsing(self):
        """Test that serves extraction includes parsing."""
        html = "<div><p>Serves: 4-6 people</p></div>"
        soup = BeautifulSoup(html, "html.parser")
        text = soup.get_text()

        metadata = MetadataExtractor.extract(soup, text)

        assert "serves" in metadata
        assert metadata["serves"] == "4-6"

    def test_extract_serves_garbage_filtered(self):
        """Test that garbage serves values are filtered out."""
        html = "<div><p>Serves: (pressure cooker):</p></div>"
        soup = BeautifulSoup(html, "html.parser")
        text = soup.get_text()

        metadata = MetadataExtractor.extract(soup, text)

        # Should not have serves key if value is garbage
        assert "serves" not in metadata

    def test_extract_prep_time_standardized(self):
        """Test that prep time is standardized to minutes."""
        html = "<div><p>Prep time: 1 hour 30 minutes</p></div>"
        soup = BeautifulSoup(html, "html.parser")
        text = soup.get_text()

        metadata = MetadataExtractor.extract(soup, text)

        assert "prep_time" in metadata
        assert metadata["prep_time"] == "90"  # Converted to minutes

    def test_extract_cook_time_standardized(self):
        """Test that cook time is standardized to minutes."""
        html = "<div><p>Cook time: 2 hours</p></div>"
        soup = BeautifulSoup(html, "html.parser")
        text = soup.get_text()

        metadata = MetadataExtractor.extract(soup, text)

        assert "cook_time" in metadata
        assert metadata["cook_time"] == "120"  # Converted to minutes

    def test_extract_time_garbage_filtered(self):
        """Test that invalid times are filtered out."""
        html = "<div><p>Prep time: not a valid time</p></div>"
        soup = BeautifulSoup(html, "html.parser")
        text = soup.get_text()

        metadata = MetadataExtractor.extract(soup, text)

        # Should not have prep_time key if value is garbage
        assert "prep_time" not in metadata

    def test_extract_all_fields_improved(self):
        """Test extracting multiple fields with improvements."""
        html = """
        <div>
            <h2>Grilled Chicken</h2>
            <p>Serves: 4 to 6</p>
            <p>Prep time: 15 minutes</p>
            <p>Cook time: 30 mins</p>
            <p>Delicious grilled chicken recipe.</p>
        </div>
        """
        soup = BeautifulSoup(html, "html.parser")
        text = soup.get_text()

        metadata = MetadataExtractor.extract(soup, text, title="Grilled Chicken")

        assert metadata["serves"] == "4-6"
        assert metadata["prep_time"] == "15"
        assert metadata["cook_time"] == "30"
        assert metadata["cooking_method"] == "grill"
        assert metadata["protein_type"] == "chicken"


class TestMetadataValidation:
    """Tests for validate_metadata method."""

    def test_validate_removes_empty_strings(self):
        """Test that empty strings are removed."""
        metadata = {"serves": "", "prep_time": "30", "cook_time": ""}

        validated = MetadataExtractor.validate_metadata(metadata)

        assert "serves" not in validated
        assert "prep_time" in validated
        assert "cook_time" not in validated

    def test_validate_serves_parsing(self):
        """Test that serves values are parsed during validation."""
        metadata = {"serves": "4 to 6"}

        validated = MetadataExtractor.validate_metadata(metadata)

        assert validated["serves"] == "4-6"

    def test_validate_time_parsing(self):
        """Test that time values are parsed during validation."""
        metadata = {"prep_time": "1 hour", "cook_time": "30 minutes"}

        validated = MetadataExtractor.validate_metadata(metadata)

        assert validated["prep_time"] == "60"
        assert validated["cook_time"] == "30"

    def test_validate_removes_invalid_serves(self):
        """Test that invalid serves are removed."""
        metadata = {"serves": "(pressure cooker):"}

        validated = MetadataExtractor.validate_metadata(metadata)

        assert "serves" not in validated

    def test_validate_removes_invalid_time(self):
        """Test that invalid times are removed."""
        metadata = {"prep_time": "not a time", "cook_time": "25 hours"}

        validated = MetadataExtractor.validate_metadata(metadata)

        assert "prep_time" not in validated
        assert "cook_time" not in validated

    def test_validate_preserves_other_fields(self):
        """Test that non-time/serves fields are preserved."""
        metadata = {
            "serves": "4",
            "prep_time": "30 minutes",
            "cooking_method": "grill",
            "protein_type": "chicken",
        }

        validated = MetadataExtractor.validate_metadata(metadata)

        assert validated["cooking_method"] == "grill"
        assert validated["protein_type"] == "chicken"


class TestBackwardCompatibility:
    """Tests to ensure backward compatibility with existing extraction."""

    def test_original_test_cases_still_work(self):
        """Test that original test cases still pass."""
        # From test_metadata.py
        html = "<div><p>Serves: 4-6 people</p></div>"
        soup = BeautifulSoup(html, "html.parser")
        text = soup.get_text()

        metadata = MetadataExtractor.extract(soup, text)
        assert "serves" in metadata
        assert "4-6" in metadata["serves"]

    def test_cooking_method_still_works(self):
        """Test that cooking method extraction still works."""
        html = "<div><h2>Grilled Chicken</h2><p>This grilled recipe is perfect.</p></div>"
        soup = BeautifulSoup(html, "html.parser")
        text = soup.get_text()

        metadata = MetadataExtractor.extract(soup, text, title="Grilled Chicken")
        assert "cooking_method" in metadata
        assert metadata["cooking_method"] == "grill"

    def test_protein_type_still_works(self):
        """Test that protein type extraction still works."""
        html = "<div><h2>Beef Steak</h2><p>A delicious beef recipe.</p></div>"
        soup = BeautifulSoup(html, "html.parser")
        text = soup.get_text()

        metadata = MetadataExtractor.extract(soup, text, title="Beef Steak")
        assert "protein_type" in metadata
        assert metadata["protein_type"] == "beef"
