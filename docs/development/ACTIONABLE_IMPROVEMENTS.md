# Actionable Database Improvements - Priority List

Based on senior developer review of DATA_STORAGE_IMPROVEMENT_PLAN.md

## TL;DR - What to Do

### DO NOW ✅
1. **Implement tagging system** (2-3 hours)
2. **Improve data extraction** (2-3 days)
3. **Add schema versioning** (2-3 hours)

### DON'T DO ❌
1. **Schema normalization** (books/authors tables) - Not worth it
2. **FTS5 search** - Current search is already fast (16ms)

---

## Priority 1: Implement Tagging System ✅

**Effort**: 2-3 hours
**Risk**: Low
**Value**: High

### Why
- Infrastructure already exists (tables created)
- Recipe model supports tags but they're not persisted
- Users want to organize recipes by category
- Zero breaking changes

### What to Change

**File**: `/Users/csrdsg/projects/epub-recipe-parser/src/epub_recipe_parser/storage/database.py`

#### 1. Update `save_recipes()` method

Add after line 165 (after recipe insert):

```python
# Get the recipe_id of the just-inserted recipe
recipe_id = cursor.lastrowid

# Handle tags if present
if recipe.tags:
    for tag_name in recipe.tags:
        # Insert tag if it doesn't exist
        cursor.execute(
            "INSERT OR IGNORE INTO tags (tag_name) VALUES (?)",
            (tag_name.lower().strip(),)
        )
        # Get tag_id
        cursor.execute(
            "SELECT id FROM tags WHERE tag_name = ?",
            (tag_name.lower().strip(),)
        )
        tag_id = cursor.fetchone()[0]
        # Link recipe to tag
        cursor.execute(
            "INSERT OR IGNORE INTO recipe_tags (recipe_id, tag_id) VALUES (?, ?)",
            (recipe_id, tag_id)
        )
```

#### 2. Update `query()` method

Add `tags` parameter and handle tag filtering:

```python
def query(
    self,
    filters: Optional[Dict[str, Any]] = None,
    tags: Optional[List[str]] = None,  # NEW
    min_quality: Optional[int] = None,
    limit: Optional[int] = None,
) -> List[Recipe]:
    """Query recipes with filters and tags."""

    # If tags provided, use JOIN to filter
    if tags:
        query_sql = """
            SELECT DISTINCT r.* FROM recipes r
            JOIN recipe_tags rt ON r.id = rt.recipe_id
            JOIN tags t ON rt.tag_id = t.id
            WHERE t.tag_name IN ({})
        """.format(','.join('?' * len(tags)))
        params = [tag.lower().strip() for tag in tags]
    else:
        query_sql = "SELECT * FROM recipes WHERE 1=1"
        params = []

    # ... rest of existing filter logic
```

#### 3. Add helper method

```python
def get_all_tags(self) -> List[Dict[str, Any]]:
    """Get all tags with usage counts.

    Returns:
        List of dicts with 'tag_name' and 'count' keys
    """
    with self._get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT t.tag_name, COUNT(rt.recipe_id) as count
            FROM tags t
            LEFT JOIN recipe_tags rt ON t.id = rt.tag_id
            GROUP BY t.tag_name
            ORDER BY count DESC, t.tag_name
        """)
        return [
            {"tag_name": row[0], "count": row[1]}
            for row in cursor.fetchall()
        ]
```

#### 4. Update Recipe loading (in `query()` and `search()`)

After creating Recipe object, load its tags:

```python
# Load tags for this recipe
cursor.execute("""
    SELECT t.tag_name
    FROM tags t
    JOIN recipe_tags rt ON t.id = rt.tag_id
    WHERE rt.recipe_id = ?
""", (row["id"],))
recipe_tags = [tag_row[0] for tag_row in cursor.fetchall()]

recipe = Recipe(
    # ... existing fields ...
    tags=recipe_tags,  # Add this
)
```

### Testing

Add to `/Users/csrdsg/projects/epub-recipe-parser/tests/test_core/test_database.py`:

```python
def test_save_recipe_with_tags(temp_db):
    """Test saving recipe with tags."""
    db = RecipeDatabase(temp_db)
    recipe = Recipe(
        title="Vegan Soup",
        book="Test Book",
        tags=["vegan", "soup", "quick"]
    )
    db.save_recipes([recipe])

    # Verify tags were saved
    tags = db.get_all_tags()
    assert len(tags) == 3
    assert any(t["tag_name"] == "vegan" for t in tags)

def test_query_by_tag(temp_db):
    """Test querying recipes by tag."""
    db = RecipeDatabase(temp_db)
    recipes = [
        Recipe(title="Vegan Soup", book="Book", tags=["vegan", "quick"]),
        Recipe(title="Beef Stew", book="Book", tags=["meat", "slow"]),
        Recipe(title="Quick Salad", book="Book", tags=["vegan", "quick"]),
    ]
    db.save_recipes(recipes)

    vegan_recipes = db.query(tags=["vegan"])
    assert len(vegan_recipes) == 2
    assert all("vegan" in r.tags for r in vegan_recipes)

def test_duplicate_tags_normalized(temp_db):
    """Test that duplicate tags are normalized."""
    db = RecipeDatabase(temp_db)
    recipe = Recipe(
        title="Test",
        book="Book",
        tags=["VEGAN", "vegan", " Vegan "]  # Different cases/spaces
    )
    db.save_recipes([recipe])

    tags = db.get_all_tags()
    # Should only have 1 tag, normalized to lowercase
    assert len(tags) == 1
    assert tags[0]["tag_name"] == "vegan"
```

---

## Priority 2: Improve Data Extraction ✅

**Effort**: 2-3 days
**Risk**: Low (fixes existing issues)
**Value**: High (better data quality)

### Why
Current data quality is poor:
```
serves: NULL, "", "3", "40", "(pressure cooker):"
prep_time: NULL, "", "15 minutes"
cook_time: "10 hours", "3 to 5 minutes", "significantly to produce..."
```

### What to Change

**File**: `/Users/csrdsg/projects/epub-recipe-parser/src/epub_recipe_parser/extractors/metadata.py` (or wherever extraction happens)

Add parsing functions:

```python
import re
from typing import Optional

def parse_time_to_minutes(text: Optional[str]) -> Optional[int]:
    """Parse time string to minutes.

    Examples:
        "15 minutes" -> 15
        "1 hour 30 minutes" -> 90
        "2 hours" -> 120
        "30-45 minutes" -> 37 (midpoint)
        "(pressure cooker): 10 minutes" -> 10
    """
    if not text:
        return None

    # Remove parenthetical notes
    text = re.sub(r'\([^)]*\):', '', text)
    text = text.strip().lower()

    if not text:
        return None

    # Handle ranges (take midpoint)
    range_match = re.search(r'(\d+)\s*-\s*(\d+)', text)
    if range_match:
        low = int(range_match.group(1))
        high = int(range_match.group(2))
        base_minutes = (low + high) // 2
    else:
        base_minutes = 0

    # Parse hours
    hours_match = re.search(r'(\d+)\s*hours?', text)
    if hours_match:
        base_minutes += int(hours_match.group(1)) * 60

    # Parse minutes
    minutes_match = re.search(r'(\d+)\s*min', text)
    if minutes_match:
        base_minutes += int(minutes_match.group(1))

    return base_minutes if base_minutes > 0 else None

def parse_serves(text: Optional[str]) -> Optional[int]:
    """Parse serving size to integer.

    Examples:
        "4" -> 4
        "4-6" -> 5 (midpoint)
        "Serves 4" -> 4
        "about 8 servings" -> 8
    """
    if not text:
        return None

    text = text.strip().lower()

    # Handle ranges
    range_match = re.search(r'(\d+)\s*-\s*(\d+)', text)
    if range_match:
        low = int(range_match.group(1))
        high = int(range_match.group(2))
        return (low + high) // 2

    # Extract first number
    number_match = re.search(r'\d+', text)
    if number_match:
        serves = int(number_match.group(0))
        # Sanity check (recipes typically serve 1-100)
        if 1 <= serves <= 100:
            return serves

    return None
```

### Testing

Create `/Users/csrdsg/projects/epub-recipe-parser/tests/test_extractors/test_time_parsing.py`:

```python
from epub_recipe_parser.extractors.metadata import parse_time_to_minutes, parse_serves

def test_parse_time_basic():
    assert parse_time_to_minutes("15 minutes") == 15
    assert parse_time_to_minutes("2 hours") == 120
    assert parse_time_to_minutes("1 hour 30 minutes") == 90

def test_parse_time_ranges():
    assert parse_time_to_minutes("30-45 minutes") == 37
    assert parse_time_to_minutes("1-2 hours") == 90

def test_parse_time_with_notes():
    assert parse_time_to_minutes("(pressure cooker): 10 minutes") == 10

def test_parse_time_invalid():
    assert parse_time_to_minutes("") is None
    assert parse_time_to_minutes("significantly to produce...") is None
    assert parse_time_to_minutes(None) is None

def test_parse_serves_basic():
    assert parse_serves("4") == 4
    assert parse_serves("Serves 6") == 6

def test_parse_serves_ranges():
    assert parse_serves("4-6") == 5
    assert parse_serves("4-6 servings") == 5

def test_parse_serves_invalid():
    assert parse_serves("") is None
    assert parse_serves("(pressure cooker):") is None
    assert parse_serves(None) is None
```

### Validation

After implementing:
1. Re-extract all 8 cookbooks
2. Check data quality:

```python
# Add to extraction report
def generate_quality_report(db: RecipeDatabase):
    conn = sqlite3.connect(db.db_path)
    cursor = conn.cursor()

    # Check time/serves data quality
    cursor.execute("""
        SELECT
            COUNT(*) as total,
            COUNT(serves) as has_serves,
            COUNT(prep_time) as has_prep,
            COUNT(cook_time) as has_cook
        FROM recipes
    """)

    print("Data Quality Report:")
    row = cursor.fetchone()
    print(f"Total recipes: {row[0]}")
    print(f"Has serves: {row[1]} ({row[1]/row[0]*100:.1f}%)")
    print(f"Has prep_time: {row[2]} ({row[2]/row[0]*100:.1f}%)")
    print(f"Has cook_time: {row[3]} ({row[3]/row[0]*100:.1f}%)")
```

---

## Priority 3: Add Schema Versioning ✅

**Effort**: 2-3 hours
**Risk**: Low
**Value**: High (enables safe future migrations)

### Why
- Currently no way to detect database schema version
- Makes future migrations risky
- Can't support backward compatibility safely

### What to Change

**File**: `/Users/csrdsg/projects/epub-recipe-parser/src/epub_recipe_parser/storage/database.py`

#### 1. Add version table creation

In `init_database()` method, add:

```python
# Create schema version table
cursor.execute("""
    CREATE TABLE IF NOT EXISTS schema_version (
        version INTEGER PRIMARY KEY,
        applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        description TEXT
    )
""")

# Initialize version if not exists
cursor.execute("""
    INSERT OR IGNORE INTO schema_version (version, description)
    VALUES (1, 'Initial schema with recipes, tags, and recipe_tags tables')
""")
```

#### 2. Add version checking methods

```python
CURRENT_SCHEMA_VERSION = 1

def get_schema_version(self) -> int:
    """Get current schema version of database.

    Returns:
        Schema version number, or 0 if pre-versioning database
    """
    with self._get_connection() as conn:
        cursor = conn.cursor()
        try:
            cursor.execute("SELECT MAX(version) FROM schema_version")
            result = cursor.fetchone()
            return result[0] if result[0] is not None else 0
        except sqlite3.OperationalError:
            # Table doesn't exist - pre-versioning database
            return 0

def check_schema_version(self):
    """Verify database schema is compatible.

    Raises:
        ValueError: If database schema is newer than code supports
    """
    db_version = self.get_schema_version()

    if db_version > CURRENT_SCHEMA_VERSION:
        raise ValueError(
            f"Database schema version {db_version} is newer than "
            f"supported version {CURRENT_SCHEMA_VERSION}. "
            f"Please upgrade epub-recipe-parser."
        )

    if db_version < CURRENT_SCHEMA_VERSION:
        # Future: Apply migrations here
        pass
```

#### 3. Call version check in `__init__`

```python
def __init__(self, db_path: str | Path):
    """Initialize database connection."""
    self.db_path = Path(db_path)
    self.init_database()
    self.check_schema_version()  # Add this line
```

#### 4. Document migration process

Create `/Users/csrdsg/projects/epub-recipe-parser/docs/SCHEMA_MIGRATIONS.md`:

```markdown
# Database Schema Migrations

## Current Version: 1

## Migration History

### Version 1 (Initial)
- Created `recipes` table
- Created `tags` table
- Created `recipe_tags` table
- Created indexes: idx_recipes_book, idx_recipes_quality, idx_recipes_cooking_method

## Future Migrations

### Version 2 (Planned: Tagging Implementation)
- Update: Make tagging system fully functional
- No schema changes needed

### Version 3 (Proposed: Time/Serves as Integer)
- Add: serves_int INTEGER
- Add: prep_time_minutes INTEGER
- Add: cook_time_minutes INTEGER
- Keep: Original TEXT columns for backward compatibility
- Migration: Parse and populate new columns

## Adding a New Migration

When you need to change the schema:

1. Increment CURRENT_SCHEMA_VERSION in database.py
2. Create migration function:
   ```python
   def _migrate_to_v2(self, conn):
       """Migration to version 2: Add feature X."""
       cursor = conn.cursor()

       # Make schema changes
       cursor.execute("ALTER TABLE ...")

       # Record migration
       cursor.execute(
           "INSERT INTO schema_version (version, description) VALUES (?, ?)",
           (2, "Add feature X")
       )

       conn.commit()
   ```

3. Update check_schema_version() to call migration:
   ```python
   if db_version < CURRENT_SCHEMA_VERSION:
       if db_version < 2:
           self._migrate_to_v2(conn)
   ```

4. Test migration on copy of production database
5. Document in this file
```

---

## Priority 4: DON'T DO - Schema Normalization ❌

**Why Not**:
- Saves only 25KB (0.7% of 3.4MB database)
- High implementation complexity (2-3 days)
- Breaking changes requiring migration
- Risk of data loss
- Increased query complexity

**When to Reconsider**:
- Dataset exceeds 50,000 recipes
- Data duplication exceeds 5MB
- Frequent need to update author/book metadata across many recipes

**Current Reality**:
- 603 recipes from 8 books
- No performance issues
- No user complaints
- Not worth the effort

---

## Priority 5: DON'T DO - FTS5 Search ❌

**Why Not**:
- Current search is already fast: 16ms for 603 recipes
- Adds significant complexity
- No user complaints about search speed
- FTS5 shines at 10,000+ recipes, you have 603

**When to Reconsider**:
- Dataset exceeds 10,000 recipes
- Search time exceeds 200ms
- Users request advanced features (phrase search, ranking)
- You're doing a major schema change anyway

**Alternative**:
- Current LIKE search is fine
- Add comment about FTS5 for future consideration

```python
def search(self, query: str, limit: int = 50) -> List[Recipe]:
    """Search recipes by text query.

    Note: Currently uses LIKE for simplicity. Performance is excellent
    at current scale (~16ms for 603 recipes). Consider SQLite FTS5 if
    dataset exceeds 10,000 recipes or search time exceeds 200ms.
    """
```

---

## Summary - Effort vs Value

| Improvement | Effort | Value | Risk | Recommendation |
|------------|---------|-------|------|----------------|
| Tagging System | 3 hours | High | Low | ✅ DO NOW |
| Data Extraction | 2-3 days | High | Low | ✅ DO NOW |
| Schema Versioning | 3 hours | High | Low | ✅ DO NOW |
| Schema Normalization | 2-3 days | Very Low | High | ❌ DON'T DO |
| FTS5 Search | 1-2 days | Low | Medium | ❌ DON'T DO |

---

## Timeline

### This Week
- [ ] Implement tagging system (3 hours)
- [ ] Add schema versioning (3 hours)
- [ ] Start data extraction improvements (1 day)

### Next Week
- [ ] Finish data extraction improvements
- [ ] Re-extract all cookbooks
- [ ] Test data quality improvements
- [ ] Write documentation

### This Month
- [ ] Monitor performance
- [ ] Gather user feedback
- [ ] Consider dual-column approach (TEXT + INTEGER) if data quality is good

---

## Questions to Ask Before Making Changes

1. **Is there a real problem?**
   - User complaints? Performance issues? Data showing problems?
   - Or just theoretical concerns?

2. **What's the ROI?**
   - Hours of work vs. concrete benefit?
   - Risk vs. reward?

3. **Breaking changes?**
   - Can we add features without breaking existing code?
   - Can old databases still work?

4. **Can we test it easily?**
   - Simple to verify it works?
   - Or complex with many edge cases?

5. **Will users notice?**
   - Does this solve a problem users have?
   - Or is it just cleaner code?

Remember: **Ship features users want. Measure what matters. Optimize what's slow.**

---

## Files to Modify

### For Tagging System
- `/Users/csrdsg/projects/epub-recipe-parser/src/epub_recipe_parser/storage/database.py`
- `/Users/csrdsg/projects/epub-recipe-parser/tests/test_core/test_database.py`

### For Data Extraction
- `/Users/csrdsg/projects/epub-recipe-parser/src/epub_recipe_parser/extractors/metadata.py`
- `/Users/csrdsg/projects/epub-recipe-parser/tests/test_extractors/test_time_parsing.py`

### For Schema Versioning
- `/Users/csrdsg/projects/epub-recipe-parser/src/epub_recipe_parser/storage/database.py`
- `/Users/csrdsg/projects/epub-recipe-parser/docs/SCHEMA_MIGRATIONS.md` (create)

---

## Testing Checklist

Before committing changes:
- [ ] All existing tests pass
- [ ] New tests added for new features
- [ ] Manual testing on sample cookbook
- [ ] Data quality validation
- [ ] Performance hasn't regressed
- [ ] Documentation updated

---

## Getting Started

```bash
# 1. Create a branch for tagging feature
git checkout -b feature/tagging-system

# 2. Implement tagging (see Priority 1 above)
# Edit src/epub_recipe_parser/storage/database.py

# 3. Write tests
# Edit tests/test_core/test_database.py

# 4. Run tests
uv run pytest tests/test_core/test_database.py -v

# 5. Test manually
uv run python -m epub_recipe_parser.cli extract sample.epub --output test.db
uv run python -c "
from epub_recipe_parser.storage.database import RecipeDatabase
db = RecipeDatabase('test.db')
tags = db.get_all_tags()
print('Tags found:', tags)
"

# 6. Commit and test again
git add .
git commit -m "feat: implement tagging system for recipe organization"
```

Good luck! Focus on real user value, not theoretical perfection.
