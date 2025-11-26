# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

EPUB Recipe Parser extracts structured recipe data from EPUB cookbook files. It uses direct HTML parsing with BeautifulSoup, pattern recognition, and quality scoring to identify and extract recipes with high accuracy.

## Development Commands

Always use `uv` to run Python files.

```bash
# Run the CLI tool
uv run epub-parser <command>

# Install with dev dependencies
pip install -e ".[dev]"

# Run tests
pytest

# Run tests with coverage
pytest --cov=epub_recipe_parser

# Format code (100 character line length)
black .

# Lint code
ruff check .

# Type checking
mypy src/
```

## Architecture

The codebase follows a layered architecture:

### Core Extraction Pipeline (`core/`)
- `extractor.py`: Main `EPUBRecipeExtractor` class orchestrates the extraction process
  - Reads EPUB files using ebooklib
  - Splits HTML documents into sections by headers (automatically determines best header level)
  - Validates each section as a recipe
  - Extracts ingredients, instructions, and metadata from each section
  - Calculates quality scores and filters by minimum threshold
- `models.py`: `Recipe` dataclass and `ExtractorConfig` for configuration
- `validator.py`: `RecipeValidator` determines if a section is a valid recipe
- `quality.py`: `QualityScorer` calculates 0-100 quality scores based on:
  - Ingredients quality (40 points max)
  - Instructions quality (40 points max)
  - Metadata presence (20 points max)

### HTML Processing (`utils/html.py`)
- `HTMLParser.parse_html()`: Creates BeautifulSoup from EPUB HTML content
- `HTMLParser.split_by_headers()`: **Core splitting logic** - Intelligently determines which header level (h1-h5) to split on by finding the most common level with at least 3 occurrences, preferring h2-h3 for recipes
- `HTMLParser.find_section_by_header()`: Locates content sections by header keywords
- `HTMLParser.extract_from_list()`: Extracts items from HTML lists

### Component Extractors (`extractors/`)
- `ingredients.py`: `IngredientsExtractor` finds ingredient lists/sections
- `instructions.py`: `InstructionsExtractor` finds instruction text
- `metadata.py`: `MetadataExtractor` extracts serving size, cook time, prep time, cooking method, protein type

### Analysis Tools (`analyzers/`)
- `toc.py`: `TOCAnalyzer` validates extraction completeness against EPUB table of contents
- `structure.py`: `EPUBStructureAnalyzer` analyzes EPUB structure and reports statistics

### Storage (`storage/`)
- `database.py`: `RecipeDatabase` handles SQLite storage, querying, and export to JSON/Markdown

## CLI Commands

The `epub-parser` CLI (in `cli/main.py`) provides:
- `extract <epub_file>`: Extract recipes from single EPUB
- `batch <directory>`: Process multiple EPUBs
- `analyze <epub_file>`: Analyze EPUB structure
- `validate <epub_file> <database>`: Validate extraction against TOC
- `search <database> <query>`: Search recipes in database

Common options:
- `--min-quality/-q`: Set minimum quality score threshold (default: 20)
- `--output/-o`: Specify output database file (default: recipes.db)

## Key Implementation Details

1. **Header-based splitting**: The system automatically detects which header level represents recipe boundaries by analyzing header frequency and preferring h2-h3 levels (see `HTMLParser.split_by_headers()` in `utils/html.py:80`)

2. **Quality filtering**: Recipes below `min_quality_score` threshold are discarded during extraction. Typical thresholds: 20 for good results, 70+ for excellent quality

3. **TOC integration**: The extractor maps EPUB sections to TOC chapters to provide chapter context for each recipe

4. **Pattern recognition**: Uses regex and heuristics in the extractors to identify ingredients and instructions, not hardcoded keywords

5. **Direct EPUB processing**: Works directly with EPUB HTML structure using ebooklib + BeautifulSoup, no conversion to markdown required
