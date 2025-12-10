# Migration Guide: Pattern-Based Extraction

This guide helps you migrate from the legacy extraction method to the new pattern-based extraction system.

## Overview

As of version 3.0, EPUB Recipe Parser uses **pattern-based extraction** by default. This provides:

- **Confidence scores** (0.0-1.0) for extraction quality assessment
- **Extraction metadata** stored in `recipe.metadata["extraction"]`
- **Graceful fallback** to legacy extraction if pattern method fails
- **Better accuracy** through multi-dimensional detection (structural + pattern + linguistic)

The legacy extraction method is still available for backward compatibility but will be removed in version 4.0.

## What Changed

### 1. Default Extraction Method

**Before (Legacy):**
```python
# IngredientsExtractor.extract() returned Optional[str]
ingredients = IngredientsExtractor.extract(soup, text)
# ingredients = "- 2 cups flour\n- 1 cup sugar" or None
```

**After (Pattern-based - Default):**
```python
# IngredientsExtractor.extract() returns tuple by default
ingredients, metadata = IngredientsExtractor.extract(soup, text)
# ingredients = "- 2 cups flour\n- 1 cup sugar" or None
# metadata = {
#     "strategy": "structural_zones",
#     "confidence": 0.92,
#     "linguistic_score": 0.88,
#     "combined_score": 0.90
# }
```

### 2. Configuration Changes

**New configuration option:**
```python
from epub_recipe_parser import ExtractorConfig

# Pattern-based extraction (default)
config = ExtractorConfig(
    use_pattern_extraction=True  # Default: True
)

# Legacy extraction (for compatibility)
config = ExtractorConfig(
    use_pattern_extraction=False
)
```

### 3. Recipe Metadata Structure

Recipes now include extraction metadata:

```python
recipe.metadata = {
    "extraction": {
        "ingredients": {
            "strategy": "structural_zones",
            "confidence": 0.92,
            "linguistic_score": 0.88,
            "combined_score": 0.90,
            "detection_method": "css_class",
            "zone_count": 1
        }
    },
    # ... other metadata
}
```

## Migration Paths

### Path 1: No Changes Required (Recommended)

If you use the `EPUBRecipeExtractor` class, **no code changes are required**. The pattern-based method is now the default and is fully backward compatible:

```python
from epub_recipe_parser import EPUBRecipeExtractor

# This code works unchanged
extractor = EPUBRecipeExtractor()
recipes = extractor.extract_from_epub("cookbook.epub")

# Recipes are extracted using pattern-based method
# Metadata is automatically added to recipe.metadata["extraction"]
```

**Action:** ✅ None required - existing code works as-is

### Path 2: Access Extraction Metadata (Optional Enhancement)

Enhance your code to use the new confidence scores:

```python
from epub_recipe_parser import EPUBRecipeExtractor
from epub_recipe_parser.utils.extraction import (
    get_extraction_confidence,
    get_extraction_strategy
)

extractor = EPUBRecipeExtractor()
recipes = extractor.extract_from_epub("cookbook.epub")

for recipe in recipes:
    # Access confidence score
    confidence = get_extraction_confidence(recipe.metadata, "ingredients")
    strategy = get_extraction_strategy(recipe.metadata, "ingredients")

    print(f"{recipe.title}: confidence={confidence:.2f}, strategy={strategy}")

    # Filter by confidence if desired
    if confidence and confidence < 0.5:
        print(f"  ⚠️ Low confidence extraction")
```

**Action:** ✨ Optional enhancement - add confidence-based filtering

### Path 3: Explicitly Use Legacy Method (Temporary Compatibility)

If you need the old behavior temporarily:

```python
from epub_recipe_parser import EPUBRecipeExtractor, ExtractorConfig

# Explicitly use legacy extraction
config = ExtractorConfig(use_pattern_extraction=False)
extractor = EPUBRecipeExtractor(config=config)
recipes = extractor.extract_from_epub("cookbook.epub")
```

**Action:** ⚠️ Temporary only - legacy method will be removed in v4.0

### Path 4: Direct Extractor Usage (Advanced)

If you use extractors directly (rare), update your code:

**Before:**
```python
from epub_recipe_parser.extractors import IngredientsExtractor

# Old way - returned just string
ingredients = IngredientsExtractor.extract(soup, text)
```

**After (Pattern-based):**
```python
from epub_recipe_parser.extractors import IngredientsExtractor
from epub_recipe_parser.utils.extraction import normalize_extraction_result

# New way - returns tuple by default
result = IngredientsExtractor.extract(soup, text)
ingredients, metadata = normalize_extraction_result(result)

# Use metadata
if metadata.get("confidence", 0) < 0.5:
    print("Low confidence extraction")
```

**After (Legacy - temporary):**
```python
# Explicitly use legacy method
ingredients = IngredientsExtractor.extract(soup, text, use_patterns=False)
# Returns just string (old behavior)
```

**Action:** 🔧 Update code to handle tuple return or use `normalize_extraction_result()`

## Deprecation Timeline

| Version | Status | Notes |
|---------|--------|-------|
| **3.0** | ✅ Pattern-based default | Legacy available via `use_pattern_extraction=False` |
| **3.x** | ⚠️ Legacy deprecated | Warning messages for legacy usage |
| **4.0** | ❌ Legacy removed | Only pattern-based extraction available |

## A/B Testing Migration

The A/B testing framework is now deprecated. Replace it with pattern-based extraction metadata:

**Before (Deprecated):**
```python
config = ExtractorConfig(
    enable_ab_testing=True,
    ab_test_use_new=False,
    ab_test_log_level="INFO"
)

# Access A/B test results
ab_data = recipe.metadata.get('ab_test', {})
```

**After (Recommended):**
```python
config = ExtractorConfig(
    use_pattern_extraction=True  # Default
)

# Access extraction metadata directly
extraction = recipe.metadata.get('extraction', {})
ingredients_meta = extraction.get('ingredients', {})
confidence = ingredients_meta.get('confidence', 0)
```

## Testing Your Migration

### 1. Run Existing Tests

```bash
# Ensure all existing tests pass
uv run pytest tests/

# Run with coverage
uv run pytest --cov=epub_recipe_parser tests/
```

### 2. Compare Extraction Results

Extract recipes with both methods and compare:

```python
from epub_recipe_parser import EPUBRecipeExtractor, ExtractorConfig

# Pattern-based
config_new = ExtractorConfig(use_pattern_extraction=True)
extractor_new = EPUBRecipeExtractor(config=config_new)
recipes_new = extractor_new.extract_from_epub("cookbook.epub")

# Legacy
config_old = ExtractorConfig(use_pattern_extraction=False)
extractor_old = EPUBRecipeExtractor(config=config_old)
recipes_old = extractor_old.extract_from_epub("cookbook.epub")

# Compare
print(f"Pattern-based: {len(recipes_new)} recipes")
print(f"Legacy: {len(recipes_old)} recipes")

# Both should extract the same recipes
assert len(recipes_new) == len(recipes_old)
```

### 3. Validate Confidence Scores

Check that confidence scores are reasonable:

```python
from epub_recipe_parser.utils.extraction import get_extraction_confidence

for recipe in recipes_new:
    confidence = get_extraction_confidence(recipe.metadata, "ingredients")
    if confidence:
        print(f"{recipe.title}: {confidence:.2f}")
        assert 0.0 <= confidence <= 1.0
```

## Troubleshooting

### Issue: "Pattern extraction returned None, falling back to legacy"

**Cause:** Pattern-based method couldn't extract ingredients

**Solution:** This is expected behavior - the system automatically falls back to legacy extraction. Check the metadata:

```python
meta = recipe.metadata["extraction"]["ingredients"]
if meta.get("strategy") == "legacy_fallback":
    print(f"Reason: {meta.get('fallback_reason')}")
```

### Issue: "AttributeError: 'str' object has no attribute..."

**Cause:** Treating extraction result as string when it's now a tuple

**Solution:** Use `normalize_extraction_result()`:

```python
from epub_recipe_parser.utils.extraction import normalize_extraction_result

result = IngredientsExtractor.extract(soup, text)
text, metadata = normalize_extraction_result(result)
```

### Issue: Low confidence scores

**Cause:** HTML structure may not match expected patterns

**Solution:** Check the detection method and strategy:

```python
meta = recipe.metadata["extraction"]["ingredients"]
print(f"Strategy: {meta.get('strategy')}")
print(f"Detection: {meta.get('detection_method')}")

# If using structural_zones, check HTML classes/structure
# If using legacy_fallback, HTML may not have semantic markup
```

## Benefits of Migration

✅ **Confidence Scores**: Know the quality of each extraction
✅ **Better Debugging**: Metadata shows which strategy was used
✅ **Future-Proof**: Pattern-based is the long-term supported method
✅ **Improved Accuracy**: Multi-dimensional detection catches more edge cases
✅ **Graceful Fallback**: Automatically uses legacy if pattern fails

## Need Help?

- Check the [README.md](README.md) for usage examples
- Review [CLAUDE.md](CLAUDE.md) for architectural details
- Open an issue on GitHub for migration questions
- Legacy method will be supported until v4.0

## Rollback Plan

If you encounter issues, you can temporarily rollback:

```python
# Rollback to legacy extraction
config = ExtractorConfig(use_pattern_extraction=False)
extractor = EPUBRecipeExtractor(config=config)
recipes = extractor.extract_from_epub("cookbook.epub")
```

However, we recommend using pattern-based extraction and reporting any issues so they can be fixed before v4.0.
