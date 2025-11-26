# ACTION PLAN - Next Steps

**Date**: 2025-11-25
**Based on**: IMPROVEMENT_PLAN_REVIEW.md

---

## Quick Summary

Out of 5 proposed improvements, **4 are already implemented or unnecessary**. Only quality scoring needs work.

The real problem: **63% of recipes are missing ingredients** (380/603), but they still score ~60/100, masking the issue.

---

## Immediate Actions (This Week)

### 1. Fix Quality Scoring - Completeness Penalty (15 minutes)

**File**: `/Users/csrdsg/projects/epub-recipe-parser/src/epub_recipe_parser/core/quality.py`

**Change**:
```python
def score_recipe(recipe: Recipe) -> int:
    score = 0

    # NEW: Penalize incomplete recipes
    if not recipe.ingredients:
        score -= 30  # Critical: missing ingredients
    if not recipe.instructions:
        score -= 30  # Critical: missing instructions

    # Existing scoring logic...
    if recipe.ingredients:
        # ...
```

**Expected Impact**:
- Recipes with no ingredients: 60 → 30 score
- Better filtering with score threshold
- Honest quality assessment

**Effort**: 15 minutes + 30 minutes for tests = 45 minutes total

---

### 2. Add Structure-Based Quality Scoring (2 days)

**Files**:
- `/Users/csrdsg/projects/epub-recipe-parser/src/epub_recipe_parser/core/quality.py`
- `/Users/csrdsg/projects/epub-recipe-parser/tests/test_core/test_quality.py`

**Changes**:

#### 2a. Count Ingredient Lines Instead of Length

```python
from epub_recipe_parser.utils.patterns import MEASUREMENT_PATTERN

@staticmethod
def score_ingredients(ingredients: str) -> int:
    """Score based on number of parsed ingredient lines."""
    if not ingredients:
        return 0

    lines = [l.strip() for l in ingredients.split('\n') if l.strip()]

    # Count lines with measurements (actual ingredients)
    ingredient_count = sum(
        1 for line in lines
        if MEASUREMENT_PATTERN.search(line) and len(line) > 5
    )

    # Score based on count
    if ingredient_count >= 10:
        return 40
    elif ingredient_count >= 7:
        return 30
    elif ingredient_count >= 5:
        return 25
    elif ingredient_count >= 3:
        return 20
    elif ingredient_count >= 1:
        return 10
    else:
        return 0
```

#### 2b. Score Instruction Structure

```python
from epub_recipe_parser.utils.patterns import COOKING_VERBS_PATTERN

@staticmethod
def score_instructions(instructions: str) -> int:
    """Score based on instruction structure and content."""
    if not instructions:
        return 0

    # Count steps (paragraphs or numbered items)
    paragraphs = [p.strip() for p in instructions.split('\n\n') if p.strip()]
    step_count = len(paragraphs)

    # Count cooking verbs (indicates real instructions)
    verb_count = len(COOKING_VERBS_PATTERN.findall(instructions.lower()))
    verb_density = verb_count / (len(instructions) / 100) if len(instructions) > 0 else 0

    score = 0

    # Score structure
    if step_count >= 5:
        score += 20
    elif step_count >= 3:
        score += 15
    elif step_count >= 1:
        score += 10

    # Score content quality (verb density)
    if verb_density >= 2.0:
        score += 20
    elif verb_density >= 1.0:
        score += 15
    elif verb_density >= 0.5:
        score += 5

    return min(score, 40)
```

#### 2c. Update Main Scoring

```python
@staticmethod
def score_recipe(recipe: Recipe) -> int:
    """Calculate quality score (0-100)."""
    score = 0

    # Penalize incomplete recipes
    if not recipe.ingredients:
        score -= 30
    if not recipe.instructions:
        score -= 30

    # Score ingredients (40 points max)
    score += QualityScorer.score_ingredients(recipe.ingredients or "")

    # Score instructions (40 points max)
    score += QualityScorer.score_instructions(recipe.instructions or "")

    # Score metadata (20 points max) - unchanged
    metadata_score = 0
    if recipe.serves:
        metadata_score += 5
    if recipe.prep_time:
        metadata_score += 5
    if recipe.cook_time:
        metadata_score += 5
    if recipe.cooking_method:
        metadata_score += 3
    if recipe.protein_type:
        metadata_score += 2

    score += min(metadata_score, 20)

    # Ensure score stays in 0-100 range
    return max(0, min(score, 100))
```

**Effort**:
- Implementation: 4 hours
- Testing: 2 hours
- Documentation: 1 hour
- Integration testing: 1 hour
- Total: ~8 hours (1 day)

**Expected Impact**:
- Recipes with no ingredients: 60 → 20-30 score
- Recipes with poorly formatted ingredients: 70 → 40-50 score
- Excellent recipes maintain 70+ scores
- Better quality distribution

---

## Next Week Actions

### 3. Add Extraction Logging (1 day)

**Purpose**: Understand why 63% of recipes have no ingredients

**Files**:
- `/Users/csrdsg/projects/epub-recipe-parser/src/epub_recipe_parser/extractors/ingredients.py`
- `/Users/csrdsg/projects/epub-recipe-parser/src/epub_recipe_parser/extractors/instructions.py`

**Changes**:

```python
import logging

logger = logging.getLogger(__name__)

@staticmethod
def extract(soup: BeautifulSoup, text: str) -> Optional[str]:
    """Extract ingredients using multiple strategies."""
    logger.debug("Starting ingredient extraction")

    # Strategy 1: Find by HTML header
    ingredients = HTMLParser.find_section_by_header(soup, INGREDIENT_KEYWORDS)
    if ingredients and len(ingredients) > 50:
        logger.info("Extracted ingredients via Strategy 1 (header)")
        return ingredients
    else:
        logger.debug(f"Strategy 1 failed: result length = {len(ingredients) if ingredients else 0}")

    # Strategy 2: Find lists with measurements
    # ... add logging to each strategy

    logger.warning("All ingredient extraction strategies failed")
    return None
```

**How to Use**:
```bash
# Enable debug logging
export EPUB_PARSER_LOG_LEVEL=DEBUG

# Re-extract recipes
epub-parser extract cookbook.epub --output recipes_debug.db

# Analyze logs
grep "Strategy.*failed" extraction.log | sort | uniq -c
```

**Effort**: 4 hours

---

### 4. Analyze Ingredient Extraction Failures (2 hours)

**Process**:

1. Re-extract all 8 cookbooks with debug logging
2. Analyze which strategies succeed/fail most often
3. Sample 10-20 recipes with no ingredients
4. Manually inspect their HTML structure
5. Identify patterns in failures

**Questions to Answer**:
- Which books have highest failure rates?
- Which extraction strategies are most/least effective?
- What HTML patterns are we missing?
- Are ingredients in tables? Prose? Unusual formats?

**Deliverable**: Document with findings and proposed fixes

---

### 5. Fix Ingredient Extraction (3-5 days)

**Wait for results from step 4 before implementing**

Potential fixes based on common patterns:
- Add table-based extraction
- Add prose-style ingredient detection
- Handle unusual measurement formats
- Improve "For the..." section detection

**Effort**: Depends on findings, estimate 3-5 days

---

## One Month Actions

### 6. Improve Validation (4 hours)

**File**: `/Users/csrdsg/projects/epub-recipe-parser/src/epub_recipe_parser/core/validator.py`

**Add more exclude keywords**:
```python
EXCLUDE_KEYWORDS = [
    # Existing...
    "index", "contents", "about the author", "acknowledgment",
    # New
    "how to", "tips for", "guide to", "introduction to",
    "about this", "cleaning", "maintenance", "care instructions",
]
```

**Add title pattern exclusions**:
```python
def is_valid_recipe(soup: BeautifulSoup, text: str, title: str) -> bool:
    title_lower = title.lower()

    # Exclude non-recipe patterns
    exclude_patterns = [
        r"^how to",
        r"^tips? (for|on)",
        r"^guide to",
        r"^about",
    ]

    for pattern in exclude_patterns:
        if re.match(pattern, title_lower):
            return False

    # Rest of validation...
```

**Expected Impact**: Remove 5-10 false positives

---

## Don't Do (From Improvement Plan)

### Skip These (Already Implemented)
- ~~Pipeline Orchestration~~ - Split by headers already works (191 recipes from shared HTML files)
- ~~Ingredient Line-by-Line~~ - Already in `ingredients.py:75-229`
- ~~Instruction Stateful Parser~~ - Already in `instructions.py:236-300` with 8 strategies

### Defer These (Premature)
- ~~Validation Structural Analysis~~ - 0.8% false positive rate is acceptable
- Consider after 6-12 months of production use

---

## Testing Checklist

After each change:

```bash
# Run tests
uv run pytest

# Check coverage
uv run pytest --cov=src --cov-report=term-missing

# Re-extract test cookbook
uv run epub-parser extract test_data/sample.epub --output test.db

# Compare quality scores
sqlite3 test.db "SELECT AVG(quality_score),
    COUNT(CASE WHEN quality_score >= 70 THEN 1 END) as excellent,
    COUNT(CASE WHEN quality_score < 40 THEN 1 END) as poor
FROM recipes"

# Verify high-quality recipes still score well
sqlite3 test.db "SELECT title, quality_score
FROM recipes
WHERE title IN ('Known', 'Good', 'Recipes')
ORDER BY quality_score DESC"
```

---

## Success Metrics

### Week 1 (Quality Scoring)
- [ ] Test coverage maintained at 90%+
- [ ] All 218 tests pass
- [ ] Recipes with no ingredients score <40
- [ ] Recipes with both ingredients/instructions score >50
- [ ] Top 10 recipes from before still score >70

### Week 2 (Investigation)
- [ ] Debug logging added to all extraction strategies
- [ ] 8 cookbooks re-extracted with logging
- [ ] Analysis document completed
- [ ] Fix proposals documented

### Month 1 (Fixes)
- [ ] Ingredient extraction improved by 10-20%
- [ ] False positives reduced to <5
- [ ] Documentation updated
- [ ] All tests passing

---

## Timeline

```
Week 1:
Mon: Quality scoring - completeness penalty (1 hour)
Tue: Quality scoring - structure-based (4 hours)
Wed: Quality scoring - tests & integration (3 hours)
Thu: Testing & validation (2 hours)
Fri: Documentation & code review (2 hours)

Week 2:
Mon: Add extraction logging (4 hours)
Tue: Re-extract with logging (2 hours)
Wed: Analyze failures (4 hours)
Thu: Document findings (2 hours)
Fri: Plan fixes (2 hours)

Week 3-4:
Implement fixes based on findings (3-5 days)
```

**Total Effort**: ~10-12 days
**Expected ROI**:
- Accurate quality assessment
- 10-20% improvement in ingredient extraction
- Better dataset quality

---

## Questions?

1. **Why not implement the improvement plan?**
   - 4 out of 5 proposals are already implemented or unnecessary
   - Would waste 15-20 days with zero ROI

2. **What's the biggest issue?**
   - 63% of recipes missing ingredients, but scoring system masks this
   - Fix scoring first, then investigate extraction

3. **Why not fix validation?**
   - 0.8% false positive rate is excellent
   - Focus on the 63% missing ingredients first

4. **When to revisit deferred items?**
   - After 6-12 months of production use
   - When we have real metrics on rejection rates
   - When false positives become a real problem (not now)

---

**Document Version**: 1.0
**Status**: Ready to implement
**Next Review**: After Week 1 completion
