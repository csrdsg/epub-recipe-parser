# Defuddle Integration Guide

## Overview

**Defuddle** is an optional HTML cleaning library that removes clutter from web pages (navigation, sidebars, ads, comments, footers) while preserving the main content. The EPUB Recipe Parser now supports defuddle as an optional pre-processing step to improve extraction quality on messy EPUB files.

**Repository**: [kepano/defuddle](https://github.com/kepano/defuddle)
**Status**: Integrated as optional enhancement (disabled by default)

## Why Defuddle?

### Problem
Some EPUB cookbooks have messy HTML with:
- Navigation menus within recipe sections
- Sidebar recommendations mixed with recipe content
- Advertisement placeholders
- Excessive HTML structure (div wrappers, nested containers)
- Multiple footer elements per section

This clutter can interfere with recipe pattern detection, leading to:
- Missed ingredients due to structural noise
- Incorrect instruction parsing

### Solution
Defuddle cleans the HTML before extraction:
1. Removes non-content elements (nav, sidebars, ads, comments)
2. Identifies and isolates main content
3. Returns clean, focused HTML
4. Minimal overhead (~2ms per section)


## Setup

### Prerequisites

1. **Node.js** (v14+) - Required for defuddle CLI
   ```bash
   node --version  # Verify installation
   ```

2. **Defuddle CLI** (optional, auto-installed via npm)
   ```bash
   npm install -g defuddle
   # Or install per-project
   npm install --save-dev defuddle
   ```

### Verification

Check if defuddle is available:

```python
from epub_recipe_parser.utils.defuddle import DefuddleHTMLCleaner

if DefuddleHTMLCleaner.is_available():
    print("Defuddle is installed and ready!")
else:
    print("Defuddle not available. Install with: npm install -g defuddle")
```

## Usage

### Enable for Extraction

```python
from epub_recipe_parser.core.extractor import EPUBRecipeExtractor
from epub_recipe_parser.core.models import ExtractorConfig

# Enable defuddle cleaning
config = ExtractorConfig(use_defuddle_cleaning=True)
extractor = EPUBRecipeExtractor(config=config)

recipes = extractor.extract_from_epub("cookbook.epub")
```

### Using the Cleaner Directly

```python
from epub_recipe_parser.utils.defuddle import DefuddleHTMLCleaner, clean_section_html

# Check availability
if DefuddleHTMLCleaner.is_available():
    # Clean individual HTML sections
    dirty_html = "<nav>...</nav><article>Recipe</article><footer>...</footer>"
    clean_html = DefuddleHTMLCleaner.clean_html(dirty_html)

    # Or use the convenience function
    html = "<article>Recipe with clutter</article>"
    cleaned = clean_section_html(html, use_defuddle=True)
```

## CLI Usage

### Defuddle CLI Commands

```bash
# Parse and clean HTML from file
defuddle parse recipe.html

# Convert to Markdown
defuddle parse recipe.html --markdown

# Get JSON output
defuddle parse recipe.html --json

# Extract specific property
defuddle parse recipe.html --property title

# Clean from URL
defuddle parse https://example.com/recipe

# Pipe from stdin
cat recipe.html | defuddle parse
curl -L https://example.com/recipe | defuddle parse
```

## Configuration

### ExtractorConfig Options

```python
from epub_recipe_parser.core.models import ExtractorConfig

config = ExtractorConfig(
    use_defuddle_cleaning=False,    # Enable HTML cleaning (default: False)
    use_pattern_extraction=True,     # Pattern-based ingredient extraction
)
```

### Backward Compatibility

```python
# Both work identically:
config1 = ExtractorConfig(use_defuddle_cleaning=True)
config2 = ExtractorConfig(
    extraction__use_defuddle_cleaning=True  # Nested config syntax
)
```

## Architecture

### Defuddle Module Structure

```
epub_recipe_parser/utils/defuddle.py
├── DefuddleHTMLCleaner
│   ├── is_available()          # Check if defuddle CLI installed
│   └── clean_html()            # Clean HTML via subprocess
└── clean_section_html()        # Convenience wrapper

Integration in core/extractor.py:
└── extract_from_epub()
    └── For each section:
        └── If use_defuddle_cleaning:
            ├── Convert section to HTML string
            ├── Clean with defuddle
            └── Parse cleaned HTML
```

### Processing Pipeline

**Without Defuddle** (default):
```
EPUB → Parse HTML → Split by headers → Validate → Extract
```

**With Defuddle** (optional):
```
EPUB → Parse HTML → Clean with Defuddle → Split by headers → Validate → Extract
```

## Performance

### Overhead

- Per-section cleaning: ~2-5ms (subprocess call)
- Total for 50 recipes: ~100-250ms additional
- Negligible compared to pattern extraction (~200ms per recipe)

### Memory

- Minimal: subprocess isolates Node.js memory
- No Python memory overhead beyond subprocess management

## Troubleshooting

### "Defuddle not available"

```bash
# Install globally
npm install -g defuddle

# Or install locally and add to PATH
npm install defuddle
export PATH="./node_modules/.bin:$PATH"

# Verify
defuddle --version
```

### Cleaning removes important content

Defuddle is conservative but sometimes removes valid content (e.g., introductory paragraphs). If this occurs:
1. Check the cleaned output: `defuddle parse file.html`
2. Disable for that specific file: `use_defuddle_cleaning=False`
3. Report to defuddle project if it's a systematic issue

### Performance issues

If cleaning is slow:
1. Check Node.js version: `node --version` (v14+ recommended)
2. Monitor with: `time defuddle parse file.html`
3. Consider disabling for batch processing

## Testing

### Unit Tests

```bash
# Run defuddle tests
pytest tests/test_utils/test_defuddle.py -v

# All tests
pytest tests/ -v
```

### Integration Tests

```python
# Test extraction with/without defuddle
from epub_recipe_parser.core.models import ExtractorConfig

# Without defuddle
config_default = ExtractorConfig(use_defuddle_cleaning=False)
recipes_default = extractor.extract_from_epub("test.epub")

# With defuddle
config_clean = ExtractorConfig(use_defuddle_cleaning=True)
recipes_clean = extractor.extract_from_epub("test.epub")

```

## Examples

### Before/After Comparison

**Input HTML:**
```html
<nav>
  <a href="/">Home</a>
  <a href="/recipes">Recipes</a>
</nav>

<article>
  <h2>Chocolate Chip Cookies</h2>

  <h3>Ingredients</h3>
  <ul>
    <li>2 cups flour</li>
    <li>1 cup butter</li>
    <li>2 cups chocolate chips</li>
  </ul>

  <h3>Instructions</h3>
  <ol>
    <li>Preheat oven to 350°F</li>
    <li>Mix ingredients</li>
    <li>Bake for 12 minutes</li>
  </ol>
</article>

<div class="sidebar">
  <h3>Popular</h3>
  <ul>
    <li><a href="/pasta">Pasta</a></li>
  </ul>
</div>

<footer>© 2024 Recipe Site</footer>
```

**After Defuddle:**
```html
<article>
  <h3>Ingredients</h3>
  <ul>
    <li>2 cups flour</li>
    <li>1 cup butter</li>
    <li>2 cups chocolate chips</li>
  </ul>

  <h3>Instructions</h3>
  <ol>
    <li>Preheat oven to 350°F</li>
    <li>Mix ingredients</li>
    <li>Bake for 12 minutes</li>
  </ol>
</article>
```

### Real-World Usage

```python
from pathlib import Path
from epub_recipe_parser.core.extractor import EPUBRecipeExtractor
from epub_recipe_parser.core.models import ExtractorConfig
from epub_recipe_parser.storage.database import RecipeDatabase

# Extract with defuddle enabled (better for messy EPUBs)
config = ExtractorConfig(
    use_defuddle_cleaning=True,    # Clean clutter
)

extractor = EPUBRecipeExtractor(config=config)

# Process cookbook
epub_file = Path("cookbook.epub")
recipes = extractor.extract_from_epub(epub_file)

# Save to database
db = RecipeDatabase("recipes.db")
db.save_recipes(recipes)

print(f"Extracted {len(recipes)} recipes")
```

## Limitations

1. **HTML-only**: Works on HTML sections, not raw EPUB structure
2. **Node.js dependency**: Requires Node.js runtime
3. **Subprocess overhead**: ~2-5ms per section (acceptable)
4. **Aggressive cleaning**: May remove valid content in rare cases
5. **Header level detection**: Prefers h2-h3 (still works with defuddle)

## Comparison with Alternatives

### Defuddle vs BeautifulSoup `get_text()`
- **Defuddle**: Semantic content extraction, removes clutter
- **BeautifulSoup**: Simple text extraction, may include noise

### Defuddle vs Mozilla Readability
- **Defuddle**: More forgiving, consistent output format
- **Readability**: Stricter, designed for articles (less suitable for recipes)

### Defuddle vs Custom Filtering
- **Defuddle**: General-purpose, well-tested, maintained
- **Custom**: Recipe-specific, requires tuning for each EPUB

## Future Enhancements

Potential improvements:
1. Python port of defuddle (eliminate Node.js dependency)
2. Caching of cleaned HTML sections
3. Defuddle configuration options exposure
4. Markdown output option via defuddle
5. Batch cleaning optimization

## Resources

- **Defuddle GitHub**: https://github.com/kepano/defuddle
- **Mozilla Readability**: https://github.com/mozilla/readability
- **BeautifulSoup Docs**: https://www.crummy.com/software/BeautifulSoup/

## Support

If defuddle integration issues arise:
1. Verify defuddle works: `defuddle parse test.html`
2. Check Python wrapper: Review `utils/defuddle.py`
3. Enable debug logging: `logging.getLogger("epub_recipe_parser").setLevel(logging.DEBUG)`
4. Report to project: GitHub issues with test case
