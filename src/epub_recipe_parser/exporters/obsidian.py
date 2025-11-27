"""Obsidian vault exporter for recipes.

This module exports recipe databases to Obsidian-compatible markdown vaults with:
- Individual markdown files per recipe
- YAML frontmatter with metadata
- Wiki-style [[Recipe Name]] links for cross-references
- Configurable folder organization (by book, cooking method, or flat)
"""

import re
import logging
from pathlib import Path
from typing import List, Dict, Set
from collections import defaultdict

from epub_recipe_parser.core.models import Recipe

logger = logging.getLogger(__name__)


class ObsidianVaultExporter:
    """Exports recipes to an Obsidian vault with wiki-style linking."""

    # Regex pattern to match recipe references like "RecipeName(page 123)" or "6Rescoldo Onions(page 260)"
    # This pattern captures the recipe name (with optional leading digits) followed by (page NNN)
    RECIPE_REF_PATTERN = re.compile(
        r"(\d*)([A-Z][a-zA-Z]+(?:\s+[A-Z][a-zA-Z]+)*)\s*\(page\s+\d+\)", re.MULTILINE
    )

    def __init__(self) -> None:
        """Initialize the Obsidian vault exporter."""
        self.recipe_title_map: Dict[str, str] = {}  # Normalized title -> actual title
        self.duplicate_names: Set[str] = set()  # Track duplicates

    def export_vault(
        self,
        recipes: List[Recipe],
        output_dir: Path,
        organize_by: str = "book",
    ) -> Dict[str, int]:
        """Export recipes to an Obsidian vault.

        Args:
            recipes: List of Recipe objects to export
            output_dir: Path to the output vault directory
            organize_by: Organization method - 'book', 'method', or 'flat'

        Returns:
            Dictionary with export statistics

        Raises:
            ValueError: If organize_by is invalid
            OSError: If directory creation or file writing fails
        """
        if organize_by not in ["book", "method", "flat"]:
            raise ValueError(
                f"Invalid organize_by value: {organize_by}. Must be 'book', 'method', or 'flat'"
            )

        if not recipes:
            logger.warning("No recipes to export")
            return {"total": 0, "success": 0, "failed": 0, "duplicates": 0}

        # Create output directory
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        # Build recipe title mapping for cross-reference resolution
        self._build_title_map(recipes)

        # Track statistics
        stats = {
            "total": len(recipes),
            "success": 0,
            "failed": 0,
            "duplicates": len(self.duplicate_names),
        }

        # Export each recipe
        for recipe in recipes:
            try:
                # Determine target directory
                target_dir = self._get_target_directory(output_dir, recipe, organize_by)
                target_dir.mkdir(parents=True, exist_ok=True)

                # Generate safe filename
                filename = self._generate_filename(recipe)
                file_path = target_dir / filename

                # Generate markdown content
                content = self._format_recipe_markdown(recipe)

                # Write file
                file_path.write_text(content, encoding="utf-8")

                stats["success"] += 1
                logger.debug(f"Exported: {recipe.title} -> {file_path}")

            except Exception as e:
                logger.error(f"Failed to export recipe '{recipe.title}': {e}")
                stats["failed"] += 1

        # Create vault index file
        try:
            self._create_vault_index(output_dir, recipes, organize_by, stats)
        except Exception as e:
            logger.warning(f"Failed to create vault index: {e}")

        return stats

    def _build_title_map(self, recipes: List[Recipe]) -> None:
        """Build a mapping of normalized recipe titles to actual titles.

        This enables accurate cross-reference resolution. Also tracks duplicates.

        Args:
            recipes: List of Recipe objects
        """
        self.recipe_title_map.clear()
        self.duplicate_names.clear()

        # Count occurrences of each normalized title
        title_counts: Dict[str, int] = defaultdict(int)
        for recipe in recipes:
            normalized = self._normalize_title(recipe.title)
            title_counts[normalized] += 1

        # Build map and track duplicates
        for recipe in recipes:
            normalized = self._normalize_title(recipe.title)
            if title_counts[normalized] > 1:
                self.duplicate_names.add(recipe.title)
            self.recipe_title_map[normalized] = recipe.title

    def _normalize_title(self, title: str) -> str:
        """Normalize a recipe title for comparison.

        Args:
            title: Recipe title to normalize

        Returns:
            Normalized title (lowercase, no extra spaces)
        """
        # Remove extra whitespace and convert to lowercase
        normalized = " ".join(title.split()).lower()
        # Remove common variations
        normalized = normalized.replace("  ", " ").strip()
        return normalized

    def _get_target_directory(self, base_dir: Path, recipe: Recipe, organize_by: str) -> Path:
        """Determine the target directory for a recipe.

        Args:
            base_dir: Base vault directory
            recipe: Recipe object
            organize_by: Organization method

        Returns:
            Path to the target directory
        """
        if organize_by == "flat":
            return base_dir

        elif organize_by == "book":
            book_name = self._sanitize_dirname(recipe.book)
            return base_dir / book_name

        elif organize_by == "method":
            method = recipe.cooking_method or "other"
            method_name = self._sanitize_dirname(method)
            return base_dir / method_name.title()

        return base_dir

    def _sanitize_dirname(self, name: str) -> str:
        """Sanitize a string for use as a directory name.

        Args:
            name: Directory name to sanitize

        Returns:
            Sanitized directory name
        """
        if not name:
            return "unknown"

        # Replace problematic characters
        sanitized = re.sub(r'[<>:"/\\|?*]', "-", name)
        # Remove leading/trailing dots and spaces
        sanitized = sanitized.strip(". ")
        # Replace multiple spaces/dashes with single dash
        sanitized = re.sub(r"[\s-]+", "-", sanitized)
        # Limit length
        if len(sanitized) > 100:
            sanitized = sanitized[:100]

        return sanitized or "unknown"

    def _generate_filename(self, recipe: Recipe) -> str:
        """Generate a safe filename for a recipe.

        Handles duplicate names by appending book name or counter.

        Args:
            recipe: Recipe object

        Returns:
            Safe filename with .md extension
        """
        base_name = self._sanitize_filename(recipe.title)

        # If this is a duplicate name, append book name
        if recipe.title in self.duplicate_names:
            book_suffix = self._sanitize_filename(recipe.book)
            base_name = f"{base_name}-{book_suffix}"

        return f"{base_name}.md"

    def _sanitize_filename(self, name: str) -> str:
        """Sanitize a string for use as a filename.

        Args:
            name: Filename to sanitize

        Returns:
            Sanitized filename (without extension)
        """
        if not name:
            return "untitled"

        # Replace problematic characters
        sanitized = re.sub(r'[<>:"/\\|?*]', "-", name)
        # Remove leading/trailing dots and spaces
        sanitized = sanitized.strip(". ")
        # Replace multiple spaces/dashes with single dash
        sanitized = re.sub(r"[\s-]+", "-", sanitized)
        # Limit length (leave room for extension and suffixes)
        if len(sanitized) > 100:
            sanitized = sanitized[:100]

        return sanitized or "untitled"

    def _format_recipe_markdown(self, recipe: Recipe) -> str:
        """Generate Obsidian-compatible markdown for a recipe.

        Args:
            recipe: Recipe object

        Returns:
            Formatted markdown string with frontmatter
        """
        # Generate YAML frontmatter
        frontmatter = self._generate_frontmatter(recipe)

        # Start building markdown
        lines = [frontmatter, "", f"# {recipe.title}", ""]

        # Add chapter context if available
        if recipe.chapter:
            lines.append(f"*From: {recipe.chapter}*")
            lines.append("")

        # Add ingredients section
        if recipe.ingredients:
            lines.append("## Ingredients")
            lines.append("")
            ingredients_text = self._parse_recipe_references(recipe.ingredients)
            lines.append(ingredients_text)
            lines.append("")

        # Add instructions section
        if recipe.instructions:
            lines.append("## Instructions")
            lines.append("")
            instructions_text = self._parse_recipe_references(recipe.instructions)
            lines.append(instructions_text)
            lines.append("")

        # Add notes section if present
        if recipe.notes:
            lines.append("## Notes")
            lines.append("")
            notes_text = self._parse_recipe_references(recipe.notes)
            lines.append(notes_text)
            lines.append("")

        # Add metadata section
        lines.append("## Metadata")
        lines.append("")
        metadata_items = []

        if recipe.quality_score:
            metadata_items.append(f"- **Quality Score:** {recipe.quality_score}/100")

        if recipe.serves:
            metadata_items.append(f"- **Serves:** {recipe.serves}")

        if recipe.prep_time:
            metadata_items.append(f"- **Prep Time:** {recipe.prep_time}")

        if recipe.cook_time:
            metadata_items.append(f"- **Cook Time:** {recipe.cook_time}")

        if recipe.cooking_method:
            metadata_items.append(f"- **Cooking Method:** {recipe.cooking_method}")

        if recipe.protein_type:
            metadata_items.append(f"- **Protein Type:** {recipe.protein_type}")

        if recipe.book:
            metadata_items.append(f"- **Book:** {recipe.book}")

        if recipe.author:
            metadata_items.append(f"- **Author:** {recipe.author}")

        lines.extend(metadata_items)

        return "\n".join(lines)

    def _generate_frontmatter(self, recipe: Recipe) -> str:
        """Generate YAML frontmatter for a recipe.

        Args:
            recipe: Recipe object

        Returns:
            YAML frontmatter string
        """
        lines = ["---"]

        # Required fields
        lines.append(f'title: "{self._escape_yaml(recipe.title)}"')

        if recipe.book:
            lines.append(f'book: "{self._escape_yaml(recipe.book)}"')

        if recipe.author:
            lines.append(f'author: "{self._escape_yaml(recipe.author)}"')

        if recipe.chapter:
            lines.append(f'chapter: "{self._escape_yaml(recipe.chapter)}"')

        # Tags
        if recipe.tags:
            lines.append("tags:")
            for tag in recipe.tags:
                lines.append(f"  - {self._escape_yaml(tag)}")

        # Metadata fields
        if recipe.cooking_method:
            lines.append(f'cooking_method: "{self._escape_yaml(recipe.cooking_method)}"')

        if recipe.protein_type:
            lines.append(f'protein_type: "{self._escape_yaml(recipe.protein_type)}"')

        if recipe.quality_score:
            lines.append(f"quality_score: {recipe.quality_score}")

        if recipe.serves:
            lines.append(f'serves: "{self._escape_yaml(recipe.serves)}"')

        if recipe.prep_time:
            lines.append(f'prep_time: "{self._escape_yaml(recipe.prep_time)}"')

        if recipe.cook_time:
            lines.append(f'cook_time: "{self._escape_yaml(recipe.cook_time)}"')

        lines.append("---")

        return "\n".join(lines)

    def _escape_yaml(self, text: str) -> str:
        """Escape special characters in YAML values.

        Args:
            text: Text to escape

        Returns:
            Escaped text safe for YAML
        """
        if not text:
            return ""

        # Escape double quotes
        text = text.replace('"', '\\"')

        return text

    def _parse_recipe_references(self, text: str) -> str:
        """Parse and convert recipe references to wiki-style links.

        Converts patterns like "Chimichurri(page 252)" to "[[Chimichurri]]"
        and preserves context like "6Rescoldo Onions(page 260)" as "6 [[Rescoldo Onions]]".

        Args:
            text: Text containing potential recipe references

        Returns:
            Text with recipe references converted to wiki-links
        """
        if not text:
            return ""

        def replace_reference(match: re.Match[str]) -> str:
            """Replace a single recipe reference with a wiki-link.

            Args:
                match: Regex match object with groups (numeric_prefix, recipe_name)

            Returns:
                Replacement string with wiki-link
            """
            # Group 1: numeric prefix (may be empty), Group 2: recipe name
            numeric_prefix = match.group(1).strip()
            recipe_name = match.group(2).strip()

            # Add space after numeric prefix if present
            if numeric_prefix:
                numeric_prefix = numeric_prefix + " "

            # Normalize and look up in title map
            normalized = self._normalize_title(recipe_name)

            if normalized in self.recipe_title_map:
                actual_title = self.recipe_title_map[normalized]
                return f"{numeric_prefix}[[{actual_title}]]"

            # If not found in map, still convert to wiki-link (might be intentional)
            return f"{numeric_prefix}[[{recipe_name}]]"

        # Replace all recipe references
        converted_text = self.RECIPE_REF_PATTERN.sub(replace_reference, text)

        return converted_text

    def _create_vault_index(
        self,
        vault_dir: Path,
        recipes: List[Recipe],
        organize_by: str,
        stats: Dict[str, int],
    ) -> None:
        """Create an index file for the vault.

        Args:
            vault_dir: Path to vault directory
            recipes: List of all recipes
            organize_by: Organization method used
            stats: Export statistics
        """
        index_path = vault_dir / "README.md"

        lines = [
            "# Recipe Vault",
            "",
            f"This Obsidian vault contains {stats['success']} recipes extracted from EPUB cookbooks.",
            "",
            "## Export Information",
            "",
            f"- **Total Recipes:** {stats['success']}",
            f"- **Organization:** By {organize_by}",
            f"- **Failed Exports:** {stats['failed']}",
        ]

        if stats["duplicates"] > 0:
            lines.append(
                f"- **Duplicate Names:** {stats['duplicates']} (resolved with book suffixes)"
            )

        lines.extend(["", "## Recipe Statistics", ""])

        # Calculate statistics
        books: Dict[str, int] = defaultdict(int)
        methods: Dict[str, int] = defaultdict(int)
        avg_quality = sum(r.quality_score for r in recipes) / len(recipes) if recipes else 0

        for recipe in recipes:
            books[recipe.book] += 1
            if recipe.cooking_method:
                methods[recipe.cooking_method] += 1

        lines.append(f"- **Average Quality Score:** {avg_quality:.1f}/100")
        lines.append(f"- **Number of Books:** {len(books)}")
        lines.append(f"- **Cooking Methods:** {len(methods)}")
        lines.append("")

        # List books
        if books:
            lines.append("### Books")
            lines.append("")
            for book, count in sorted(books.items(), key=lambda x: x[1], reverse=True):
                lines.append(f"- **{book}:** {count} recipes")
            lines.append("")

        # List cooking methods
        if methods:
            lines.append("### Cooking Methods")
            lines.append("")
            for method, count in sorted(methods.items(), key=lambda x: x[1], reverse=True):
                lines.append(f"- **{method.title()}:** {count} recipes")
            lines.append("")

        lines.extend(
            [
                "## Navigation",
                "",
                "- Use the file explorer to browse recipes by folder",
                "- Search for recipes using Obsidian's search (Cmd/Ctrl+O)",
                "- Follow [[Recipe Name]] links to explore related recipes",
                "- Filter by tags in the search panel",
                "",
                "## Wiki Links",
                "",
                "Recipe references (e.g., 'Chimichurri(page 252)') have been converted to wiki-style links.",
                "Click on [[Recipe Name]] links to navigate between related recipes.",
            ]
        )

        index_path.write_text("\n".join(lines), encoding="utf-8")
        logger.info(f"Created vault index at {index_path}")
