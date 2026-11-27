"""Tests for recipe tagging system."""

from epub_recipe_parser.core.models import Recipe
from epub_recipe_parser.storage.database import RecipeDatabase


def test_save_recipe_with_tags(temp_db):
    """Test saving a recipe with tags."""
    db = RecipeDatabase(temp_db)

    recipe = Recipe(
        title="Test Recipe",
        book="Test Book",
        tags=["vegetarian", "quick", "easy"],
    )

    saved = db.save_recipes([recipe])
    assert saved == 1


def test_retrieve_recipe_with_tags(temp_db):
    """Test retrieving a recipe with its tags."""
    db = RecipeDatabase(temp_db)

    recipe = Recipe(
        title="Grilled Chicken",
        book="Test Book",
        tags=["chicken", "grill", "dinner"],
    )

    db.save_recipes([recipe])
    recipes = db.query()

    assert len(recipes) == 1
    assert set(recipes[0].tags) == {"chicken", "grill", "dinner"}


def test_tags_are_case_insensitive(temp_db):
    """Test that tags are stored and retrieved in lowercase."""
    db = RecipeDatabase(temp_db)

    recipe = Recipe(
        title="Test Recipe",
        book="Test Book",
        tags=["Vegetarian", "QUICK", "Easy"],
    )

    db.save_recipes([recipe])
    recipes = db.query()

    assert len(recipes) == 1
    # All tags should be lowercase
    assert all(tag.islower() for tag in recipes[0].tags)
    assert set(recipes[0].tags) == {"vegetarian", "quick", "easy"}


def test_duplicate_tags_handled_gracefully(temp_db):
    """Test that duplicate tags in a recipe are handled properly."""
    db = RecipeDatabase(temp_db)

    recipe = Recipe(
        title="Test Recipe",
        book="Test Book",
        tags=["quick", "quick", "easy"],  # Duplicate "quick"
    )

    db.save_recipes([recipe])
    recipes = db.query()

    assert len(recipes) == 1
    # Should only have unique tags
    assert recipes[0].tags.count("quick") == 1


def test_empty_tags_handled(temp_db):
    """Test that empty or whitespace tags are ignored."""
    db = RecipeDatabase(temp_db)

    recipe = Recipe(
        title="Test Recipe",
        book="Test Book",
        tags=["quick", "", "  ", "easy"],  # Empty and whitespace tags
    )

    db.save_recipes([recipe])
    recipes = db.query()

    assert len(recipes) == 1
    # Should only have non-empty tags
    assert set(recipes[0].tags) == {"quick", "easy"}


def test_query_by_single_tag(temp_db):
    """Test querying recipes by a single tag."""
    db = RecipeDatabase(temp_db)

    recipes = [
        Recipe(title="Recipe 1", book="Book", tags=["vegetarian", "quick"]),
        Recipe(title="Recipe 2", book="Book", tags=["chicken", "quick"]),
        Recipe(title="Recipe 3", book="Book", tags=["vegetarian", "slow"]),
    ]

    db.save_recipes(recipes)

    # Query for vegetarian recipes
    vegetarian_recipes = db.query(tags=["vegetarian"])

    assert len(vegetarian_recipes) == 2
    titles = {r.title for r in vegetarian_recipes}
    assert titles == {"Recipe 1", "Recipe 3"}


def test_query_by_multiple_tags_or_logic(temp_db):
    """Test querying recipes with multiple tags using OR logic."""
    db = RecipeDatabase(temp_db)

    recipes = [
        Recipe(title="Recipe 1", book="Book", tags=["vegetarian", "quick"]),
        Recipe(title="Recipe 2", book="Book", tags=["chicken", "quick"]),
        Recipe(title="Recipe 3", book="Book", tags=["vegetarian", "slow"]),
        Recipe(title="Recipe 4", book="Book", tags=["beef", "slow"]),
    ]

    db.save_recipes(recipes)

    # Query for recipes with vegetarian OR chicken
    results = db.query(tags=["vegetarian", "chicken"], tags_match_all=False)

    assert len(results) == 3
    titles = {r.title for r in results}
    assert titles == {"Recipe 1", "Recipe 2", "Recipe 3"}


def test_query_by_multiple_tags_and_logic(temp_db):
    """Test querying recipes with multiple tags using AND logic."""
    db = RecipeDatabase(temp_db)

    recipes = [
        Recipe(title="Recipe 1", book="Book", tags=["vegetarian", "quick"]),
        Recipe(title="Recipe 2", book="Book", tags=["chicken", "quick"]),
        Recipe(title="Recipe 3", book="Book", tags=["vegetarian", "slow"]),
    ]

    db.save_recipes(recipes)

    # Query for recipes with BOTH vegetarian AND quick
    results = db.query(tags=["vegetarian", "quick"], tags_match_all=True)

    assert len(results) == 1
    assert results[0].title == "Recipe 1"


def test_query_tags_case_insensitive(temp_db):
    """Test that tag queries are case-insensitive."""
    db = RecipeDatabase(temp_db)

    recipe = Recipe(
        title="Test Recipe",
        book="Test Book",
        tags=["vegetarian", "quick"],
    )

    db.save_recipes([recipe])

    # Query with different cases
    results1 = db.query(tags=["VEGETARIAN"])
    results2 = db.query(tags=["Vegetarian"])
    results3 = db.query(tags=["vegetarian"])

    assert len(results1) == len(results2) == len(results3) == 1


def test_search_with_tags(temp_db):
    """Test searching recipes with tag filtering."""
    db = RecipeDatabase(temp_db)

    recipes = [
        Recipe(
            title="Chicken Soup",
            book="Book",
            ingredients="chicken, vegetables",
            tags=["soup", "chicken"],
        ),
        Recipe(
            title="Chicken Salad",
            book="Book",
            ingredients="chicken, lettuce",
            tags=["salad", "chicken"],
        ),
        Recipe(
            title="Vegetable Soup",
            book="Book",
            ingredients="vegetables, broth",
            tags=["soup", "vegetarian"],
        ),
    ]

    db.save_recipes(recipes)

    # Search for "soup" with tag "chicken"
    results = db.search("soup", tags=["chicken"])

    assert len(results) == 1
    assert results[0].title == "Chicken Soup"


def test_tags_shared_across_recipes(temp_db):
    """Test that tags are properly shared across multiple recipes."""
    db = RecipeDatabase(temp_db)

    recipes = [
        Recipe(title="Recipe 1", book="Book", tags=["quick", "easy"]),
        Recipe(title="Recipe 2", book="Book", tags=["quick", "dinner"]),
        Recipe(title="Recipe 3", book="Book", tags=["easy", "breakfast"]),
    ]

    db.save_recipes(recipes)

    # Check that we don't have duplicate tag entries in tags table
    with db._get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM tags WHERE tag_name = 'quick'")
        quick_count = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM tags WHERE tag_name = 'easy'")
        easy_count = cursor.fetchone()[0]

    assert quick_count == 1, "Tag 'quick' should only exist once"
    assert easy_count == 1, "Tag 'easy' should only exist once"


def test_recipe_without_tags(temp_db):
    """Test that recipes without tags work correctly."""
    db = RecipeDatabase(temp_db)

    recipe = Recipe(title="Test Recipe", book="Test Book")  # No tags

    db.save_recipes([recipe])
    recipes = db.query()

    assert len(recipes) == 1
    assert recipes[0].tags == []


def test_query_nonexistent_tag(temp_db):
    """Test querying with a tag that doesn't exist."""
    db = RecipeDatabase(temp_db)

    recipe = Recipe(title="Test Recipe", book="Test Book", tags=["quick"])

    db.save_recipes([recipe])
    results = db.query(tags=["nonexistent"])

    assert len(results) == 0


def test_query_with_filters_and_tags(temp_db):
    """Test combining traditional filters with tag filtering."""
    db = RecipeDatabase(temp_db)

    recipes = [
        Recipe(
            title="Recipe 1",
            book="Book A",
            tags=["quick"],
        ),
        Recipe(
            title="Recipe 2",
            book="Book B",
            tags=["quick"],
        ),
        Recipe(
            title="Recipe 3",
            book="Book A",
            tags=["slow"],
        ),
    ]

    db.save_recipes(recipes)

    # Query for Book A recipes with "quick" tag
    results = db.query(filters={"book": "Book A"}, tags=["quick"])

    assert len(results) == 1
    assert results[0].title == "Recipe 1"


def test_get_recipe_tags_method(temp_db):
    """Test the _get_recipe_tags internal method."""
    db = RecipeDatabase(temp_db)

    recipe = Recipe(
        title="Test Recipe",
        book="Test Book",
        tags=["tag1", "tag2", "tag3"],
    )

    db.save_recipes([recipe])

    # Get the recipe ID
    with db._get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM recipes WHERE title = ?", ("Test Recipe",))
        recipe_id = cursor.fetchone()[0]

        # Get tags for this recipe
        tags = db._get_recipe_tags(cursor, recipe_id)

    assert len(tags) == 3
    assert set(tags) == {"tag1", "tag2", "tag3"}


def test_tags_order_consistent(temp_db):
    """Test that tags are returned in consistent order."""
    db = RecipeDatabase(temp_db)

    recipe = Recipe(
        title="Test Recipe",
        book="Test Book",
        tags=["zebra", "alpha", "mike"],
    )

    db.save_recipes([recipe])
    recipes = db.query()

    # Tags should be ordered alphabetically
    assert recipes[0].tags == ["alpha", "mike", "zebra"]
