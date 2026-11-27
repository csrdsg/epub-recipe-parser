"""Tests for Obsidian vault exporter."""

import pytest
from pathlib import Path
from epub_recipe_parser.core.models import Recipe
from epub_recipe_parser.exporters import ObsidianVaultExporter


@pytest.fixture
def sample_recipes():
    """Create sample recipes for testing."""
    return [
        Recipe(
            title="Chimichurri",
            book="Open Fire Cooking",
            author="Test Author",
            chapter="Sauces and Condiments",
            ingredients="1 cup parsley\n2 cloves garlic\n1/4 cup olive oil",
            instructions="Blend all ingredients until smooth.",
            serves="4",
            prep_time="10 minutes",
            cook_time="0 minutes",
            cooking_method="raw",
            tags=["sauce", "condiment"],
        ),
        Recipe(
            title="Grilled Steak",
            book="Open Fire Cooking",
            author="Test Author",
            chapter="Beef Recipes",
            ingredients="2 lb ribeye steak\nSalt and pepper\nChimichurri(page 252)",
            instructions="Season steak. Grill to desired doneness. Serve with Chimichurri(page 252).",
            serves="4",
            prep_time="15 minutes",
            cook_time="15 minutes",
            cooking_method="grilling",
            protein_type="beef",
            tags=["beef", "grilling"],
        ),
        Recipe(
            title="Rescoldo Onions",
            book="Open Fire Cooking",
            author="Test Author",
            chapter="Vegetables",
            ingredients="6 large onions\nOlive oil\nSalt",
            instructions="Wrap onions in foil. Cook in embers for 1 hour.",
            serves="6",
            prep_time="10 minutes",
            cook_time="60 minutes",
            cooking_method="ember-cooking",
            tags=["vegetables", "ember-cooking"],
        ),
    ]


@pytest.fixture
def temp_vault_dir(tmp_path):
    """Create temporary directory for vault."""
    return tmp_path / "test-vault"


class TestObsidianVaultExporter:
    """Test cases for ObsidianVaultExporter."""

    def test_export_vault_by_book(self, sample_recipes, temp_vault_dir):
        """Test exporting vault organized by book."""
        exporter = ObsidianVaultExporter()
        stats = exporter.export_vault(sample_recipes, temp_vault_dir, organize_by="book")

        assert stats["success"] == 3
        assert stats["failed"] == 0
        assert (temp_vault_dir / "Open-Fire-Cooking" / "Chimichurri.md").exists()
        assert (temp_vault_dir / "Open-Fire-Cooking" / "Grilled-Steak.md").exists()

    def test_export_vault_by_method(self, sample_recipes, temp_vault_dir):
        """Test exporting vault organized by cooking method."""
        exporter = ObsidianVaultExporter()
        stats = exporter.export_vault(sample_recipes, temp_vault_dir, organize_by="method")

        assert stats["success"] == 3
        assert stats["failed"] == 0
        assert (temp_vault_dir / "Grilling" / "Grilled-Steak.md").exists()
        assert (temp_vault_dir / "Raw" / "Chimichurri.md").exists()

    def test_export_vault_flat(self, sample_recipes, temp_vault_dir):
        """Test exporting vault with flat organization."""
        exporter = ObsidianVaultExporter()
        stats = exporter.export_vault(sample_recipes, temp_vault_dir, organize_by="flat")

        assert stats["success"] == 3
        assert stats["failed"] == 0
        assert (temp_vault_dir / "Chimichurri.md").exists()
        assert (temp_vault_dir / "Grilled-Steak.md").exists()

    def test_recipe_reference_parsing(self, sample_recipes, temp_vault_dir):
        """Test that recipe references are converted to wiki-links."""
        exporter = ObsidianVaultExporter()
        exporter.export_vault(sample_recipes, temp_vault_dir, organize_by="flat")

        steak_content = (temp_vault_dir / "Grilled-Steak.md").read_text()
        assert "[[Chimichurri]]" in steak_content
        assert "(page 252)" not in steak_content

    def test_numeric_prefix_handling(self):
        """Test handling of recipe references with numeric prefixes."""
        recipe = Recipe(
            title="Test Recipe",
            book="Test Book",
            ingredients="6Rescoldo Onions(page 260)",
            instructions="Use 6Rescoldo Onions(page 260)",
        )

        exporter = ObsidianVaultExporter()
        exporter._build_title_map([
            recipe,
            Recipe(title="Rescoldo Onions", book="Test Book")
        ])

        parsed_ingredients = exporter._parse_recipe_references(recipe.ingredients)
        assert "6 [[Rescoldo Onions]]" in parsed_ingredients

    def test_yaml_frontmatter(self, sample_recipes, temp_vault_dir):
        """Test that YAML frontmatter is correctly generated."""
        exporter = ObsidianVaultExporter()
        exporter.export_vault(sample_recipes, temp_vault_dir, organize_by="flat")

        steak_content = (temp_vault_dir / "Grilled-Steak.md").read_text()
        assert "---" in steak_content
        assert 'title: "Grilled Steak"' in steak_content
        assert 'book: "Open Fire Cooking"' in steak_content
        assert "tags:" in steak_content
        assert "  - beef" in steak_content
        assert 'cooking_method: "grilling"' in steak_content

    def test_duplicate_title_handling(self, temp_vault_dir):
        """Test that duplicate recipe titles are handled correctly."""
        recipes = [
            Recipe(title="Grilled Steak", book="Book One"),
            Recipe(title="Grilled Steak", book="Book Two"),
        ]

        exporter = ObsidianVaultExporter()
        stats = exporter.export_vault(recipes, temp_vault_dir, organize_by="flat")

        assert stats["success"] == 2
        # duplicates counts unique duplicate names (1 name appearing 2 times = 1 duplicate)
        assert stats["duplicates"] == 1
        # Both files should exist with different names
        files = list(temp_vault_dir.glob("*.md"))
        md_files = [f for f in files if f.name != "README.md"]
        assert len(md_files) == 2

    def test_filename_collisions_keep_every_recipe(self, temp_vault_dir):
        titles = ["Chili: Sauce", "Chili? Sauce", "CHILI/SAUCE", "README"]
        recipes = [Recipe(title=title, book="Cookbook") for title in titles]

        stats = ObsidianVaultExporter().export_vault(recipes, temp_vault_dir, organize_by="flat")

        assert stats["success"] == len(titles)
        assert (temp_vault_dir / "README.md").read_text().startswith("# Recipe Vault")
        notes = [path.read_text() for path in temp_vault_dir.glob("*.md") if path.name != "README.md"]
        assert len(notes) == len(titles)
        assert all(any(f"\n# {title}\n" in note for note in notes) for title in titles)

    def test_invalid_organize_by(self, sample_recipes, temp_vault_dir):
        """Test that invalid organize_by raises ValueError."""
        exporter = ObsidianVaultExporter()
        with pytest.raises(ValueError, match="Invalid organize_by value"):
            exporter.export_vault(sample_recipes, temp_vault_dir, organize_by="invalid")

    def test_empty_recipes_list(self, temp_vault_dir):
        """Test exporting with empty recipes list."""
        exporter = ObsidianVaultExporter()
        stats = exporter.export_vault([], temp_vault_dir, organize_by="book")

        assert stats["total"] == 0
        assert stats["success"] == 0

    def test_filename_sanitization(self):
        """Test that filenames are properly sanitized."""
        exporter = ObsidianVaultExporter()

        # Test special characters
        assert exporter._sanitize_filename("Recipe: Name") == "Recipe-Name"
        assert exporter._sanitize_filename("Recipe/Name") == "Recipe-Name"
        assert exporter._sanitize_filename("Recipe?Name") == "Recipe-Name"

        # Test long names
        long_name = "A" * 150
        sanitized = exporter._sanitize_filename(long_name)
        assert len(sanitized) <= 100

    def test_vault_index_creation(self, sample_recipes, temp_vault_dir):
        """Test that vault index README is created."""
        exporter = ObsidianVaultExporter()
        exporter.export_vault(sample_recipes, temp_vault_dir, organize_by="book")

        readme_path = temp_vault_dir / "README.md"
        assert readme_path.exists()

        readme_content = readme_path.read_text()
        assert "Recipe Vault" in readme_content
        assert "Open Fire Cooking" in readme_content
        assert "3 recipes" in readme_content

    def test_normalize_title(self):
        """Test title normalization."""
        exporter = ObsidianVaultExporter()

        assert exporter._normalize_title("Recipe Name") == "recipe name"
        assert exporter._normalize_title("Recipe  Name") == "recipe name"
        assert exporter._normalize_title("  Recipe Name  ") == "recipe name"

    def test_escape_yaml(self):
        """Test YAML escaping."""
        exporter = ObsidianVaultExporter()

        assert exporter._escape_yaml('Test "Quote"') == 'Test \\"Quote\\"'
        assert exporter._escape_yaml("Normal Text") == "Normal Text"
        assert exporter._escape_yaml("") == ""


def test_append_preserves_notes_and_builds_cumulative_index(tmp_path):
    vault = tmp_path / "vault"
    exporter = ObsidianVaultExporter()
    first = Recipe(title="Tomato Salad", book="Book One", source_id="source-one")
    second = Recipe(title="Tomato Salad", book="Book Two", source_id="source-two")
    assert exporter.export_vault([first], vault, organize_by="flat")["success"] == 1
    original = vault / "Tomato-Salad.md"
    edited = original.read_text().replace('source_id: "source-one"', "source_id: source-one")
    edited += "\nA personal note.\n"
    original.write_text(edited)

    result = exporter.export_vault([first, second], vault, organize_by="flat", append=True)
    assert result["success"] == 1
    assert exporter.export_vault([second], vault, organize_by="flat", append=True)["success"] == 0
    assert original.read_text() == edited
    assert len(list(vault.glob("*.md"))) == 3
    index = (vault / "README.md").read_text()
    assert "**Total Recipes:** 2" in index
    assert "**Book One:** 1 recipes" in index
    assert "**Book Two:** 1 recipes" in index


def test_append_preserves_a_custom_readme_and_counts_legacy_notes(tmp_path):
    exporter = ObsidianVaultExporter()
    old = Recipe(title="Old Recipe", book="Old Book")
    new = Recipe(title="New Recipe", book="New Book", source_id="new-source")
    exporter.export_vault([old], tmp_path)
    readme = tmp_path / "README.md"
    readme.write_text("# My vault\n")

    exporter.export_vault([new], tmp_path, append=True)

    assert readme.read_text() == "# My vault\n"
    assert "**Total Recipes:** 2" in (tmp_path / "Recipe Vault Index.md").read_text()
