# Obsidian Vault Export Example

This example demonstrates how to export your recipe database to an Obsidian vault with wiki-style linking.

## Basic Usage

### Export to Obsidian Vault

```bash
# Export recipes organized by book (default)
uv run epub-parser export recipes.db --format vault --output my-recipes-vault

# Export organized by cooking method
uv run epub-parser export recipes.db --format vault --organize-by method --output my-recipes-vault

# Export with flat structure (all recipes in one folder)
uv run epub-parser export recipes.db --format vault --organize-by flat --output my-recipes-vault

# Filter by minimum quality score
uv run epub-parser export recipes.db --format vault --min-quality 70 --output my-recipes-vault
```

## Vault Organization Options

### By Book (Default)
Organizes recipes into folders by book title:
```
my-recipes-vault/
├── README.md
├── Open-Fire-Cooking/
│   ├── Chimichurri.md
│   ├── Grilled-Steak.md
│   └── Rescoldo-Onions.md
└── Another-Cookbook/
    ├── Recipe-1.md
    └── Recipe-2.md
```

### By Cooking Method
Organizes recipes into folders by cooking method:
```
my-recipes-vault/
├── README.md
├── Grilling/
│   ├── Grilled-Steak.md
│   └── Grilled-Lamb.md
├── Ember-Cooking/
│   └── Rescoldo-Onions.md
└── Raw/
    └── Chimichurri.md
```

### Flat
All recipes in one folder:
```
my-recipes-vault/
├── README.md
├── Chimichurri.md
├── Grilled-Steak.md
└── Rescoldo-Onions.md
```

## Recipe File Format

Each recipe is exported as a markdown file with YAML frontmatter:

```markdown
---
title: "Grilled Steak"
book: "Open Fire Cooking"
author: "Francis Mallmann"
chapter: "Beef Recipes"
tags:
  - beef
  - grilling
cooking_method: "grilling"
protein_type: "beef"
quality_score: 90
serves: "4"
prep_time: "15 minutes"
cook_time: "15 minutes"
---

# Grilled Steak

*From: Beef Recipes*

## Ingredients

2 lb ribeye steak
Salt and pepper
[[Chimichurri]]

## Instructions

Season steak. Grill to desired doneness. Serve with [[Chimichurri]].

## Metadata

- **Quality Score:** 90/100
- **Serves:** 4
- **Prep Time:** 15 minutes
- **Cook Time:** 15 minutes
- **Cooking Method:** grilling
- **Protein Type:** beef
- **Book:** Open Fire Cooking
- **Author:** Francis Mallmann
```

## Wiki-Style Cross-References

Recipe references are automatically converted to Obsidian wiki-links:

### Input (from EPUB)
```
Ingredients:
- 2 lb ribeye steak
- Chimichurri(page 252)

Instructions:
Serve with 6Rescoldo Onions(page 260).
```

### Output (in Obsidian vault)
```markdown
Ingredients:
- 2 lb ribeye steak
- [[Chimichurri]]

Instructions:
Serve with 6 [[Rescoldo Onions]].
```

### Supported Reference Formats

- `RecipeName(page 123)` → `[[RecipeName]]`
- `Recipe Name(page 123)` → `[[Recipe Name]]`
- `6Rescoldo Onions(page 260)` → `6 [[Rescoldo Onions]]`

The exporter intelligently handles:
- Multi-word recipe names
- Numeric prefixes (quantities)
- Various spacing patterns

## Using the Vault in Obsidian

1. **Open the vault in Obsidian:**
   - Launch Obsidian
   - Click "Open folder as vault"
   - Select your exported vault directory

2. **Navigate between recipes:**
   - Click on any `[[Recipe Name]]` link to jump to that recipe
   - Use backlinks panel to see which recipes reference the current one

3. **Search and filter:**
   - Use Cmd/Ctrl+O for quick search
   - Filter by tags using the tag pane
   - Use search operators: `tag:#beef`, `file:Grilled`

4. **Organize further:**
   - Add notes to recipes by editing the markdown files
   - Create custom MOCs (Maps of Content) linking related recipes
   - Add your own tags in the frontmatter

## Vault Index

A `README.md` file is automatically created with:
- Total recipe count and export statistics
- List of books with recipe counts
- List of cooking methods with recipe counts
- Navigation tips

## Handling Duplicate Names

If multiple recipes have the same name (from different books), the exporter automatically appends the book name to the filename:

```
Grilled-Steak-Open-Fire-Cooking.md
Grilled-Steak-Another-Book.md
```

The wiki-links still use the recipe name only: `[[Grilled Steak]]` and Obsidian will prompt you to choose which one when clicked.

## Complete Workflow Example

```bash
# 1. Extract recipes from EPUB
uv run epub-parser extract open_fire_cooking.epub --output recipes.db --min-quality 20

# 2. Review recipes in database
uv run epub-parser search recipes.db "steak"

# 3. Export high-quality recipes to Obsidian vault
uv run epub-parser export recipes.db --format vault --min-quality 70 --organize-by book --output cookbook-vault

# 4. Open in Obsidian
# Launch Obsidian → Open folder as vault → Select cookbook-vault/
```

## Tips for Best Results

1. **Quality filtering:** Use `--min-quality 50` or higher to export only well-extracted recipes
2. **Organization:** Choose organization method based on your needs:
   - `book` for keeping cookbook structure
   - `method` for browsing by cooking technique
   - `flat` for simplicity
3. **Multiple exports:** You can export different subsets to different vaults
4. **Version control:** Consider using git to track changes to your vault

## Programmatic Usage

You can also use the exporter directly in Python:

```python
from pathlib import Path
from epub_recipe_parser.storage import RecipeDatabase
from epub_recipe_parser.exporters import ObsidianVaultExporter

# Load recipes from database
db = RecipeDatabase("recipes.db")
recipes = db.query(min_quality=70)

# Export to vault
exporter = ObsidianVaultExporter()
stats = exporter.export_vault(
    recipes=recipes,
    output_dir=Path("my-vault"),
    organize_by="book"
)

print(f"Exported {stats['success']} recipes")
print(f"Failed: {stats['failed']}")
print(f"Duplicates resolved: {stats['duplicates']}")
```
