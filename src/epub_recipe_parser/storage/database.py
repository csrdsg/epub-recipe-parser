"""SQLite storage for recipes."""

import json
import sqlite3
import threading
from contextlib import contextmanager
from pathlib import Path
from typing import List, Dict, Any, Optional

from epub_recipe_parser.core.models import Recipe


class RecipeDatabase:
    """SQLite storage for recipes with thread-safe initialization."""

    # Class-level lock for thread-safe database initialization
    _init_lock = threading.Lock()

    def __init__(self, db_path: str | Path):
        """Initialize database connection.

        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = Path(db_path)
        self.init_database()

    @contextmanager
    def _get_connection(self):
        """Context manager for database connections.

        Ensures proper cleanup even if exceptions occur.

        Yields:
            sqlite3.Connection: Database connection
        """
        conn = None
        try:
            conn = sqlite3.connect(self.db_path)
            yield conn
        except sqlite3.Error as e:
            if conn:
                conn.rollback()
            raise sqlite3.DatabaseError(f"Database operation failed: {e}") from e
        finally:
            if conn:
                conn.close()

    def init_database(self):
        """Initialize SQLite database schema in a thread-safe manner.

        Uses file locking to prevent race conditions during concurrent
        database initialization. Includes schema versioning for future migrations.

        Raises:
            sqlite3.DatabaseError: If database initialization fails
        """
        with self._init_lock:
            with self._get_connection() as conn:
                cursor = conn.cursor()

                # Schema Version 1: Initial schema with tagging support
                # Create schema_version table first to track migrations
                cursor.execute(
                    """
                    CREATE TABLE IF NOT EXISTS schema_version (
                        version INTEGER PRIMARY KEY,
                        applied_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                        description TEXT
                    )
                """
                )

                current_version = self._get_schema_version(cursor)

                # Only create tables if this is a new database (version 0)
                if current_version == 0:
                    cursor.execute(
                        """
                        CREATE TABLE IF NOT EXISTS recipes (
                            id INTEGER PRIMARY KEY AUTOINCREMENT,
                            title TEXT NOT NULL,
                            book TEXT NOT NULL,
                            author TEXT,
                            chapter TEXT,
                            epub_section TEXT,
                            serves TEXT,
                            prep_time TEXT,
                            cook_time TEXT,
                            ingredients TEXT,
                            instructions TEXT,
                            notes TEXT,
                            tags TEXT,
                            cooking_method TEXT,
                            protein_type TEXT,
                            difficulty TEXT,
                            quality_score INTEGER DEFAULT 0,
                            raw_content TEXT,
                            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                        )
                    """
                    )

                    cursor.execute(
                        """
                        CREATE TABLE IF NOT EXISTS tags (
                            id INTEGER PRIMARY KEY AUTOINCREMENT,
                            tag_name TEXT UNIQUE NOT NULL COLLATE NOCASE
                        )
                    """
                    )

                    cursor.execute(
                        """
                        CREATE TABLE IF NOT EXISTS recipe_tags (
                            recipe_id INTEGER,
                            tag_id INTEGER,
                            FOREIGN KEY (recipe_id) REFERENCES recipes(id) ON DELETE CASCADE,
                            FOREIGN KEY (tag_id) REFERENCES tags(id) ON DELETE CASCADE,
                            PRIMARY KEY (recipe_id, tag_id)
                        )
                    """
                    )

                    # Create indexes for common queries
                    cursor.execute("CREATE INDEX IF NOT EXISTS idx_recipes_book ON recipes(book)")
                    cursor.execute(
                        "CREATE INDEX IF NOT EXISTS idx_recipes_quality ON recipes(quality_score)"
                    )
                    cursor.execute(
                        "CREATE INDEX IF NOT EXISTS idx_recipes_cooking_method ON recipes(cooking_method)"
                    )
                    cursor.execute("CREATE INDEX IF NOT EXISTS idx_tags_name ON tags(tag_name)")
                    cursor.execute(
                        "CREATE INDEX IF NOT EXISTS idx_recipe_tags_recipe ON recipe_tags(recipe_id)"
                    )
                    cursor.execute(
                        "CREATE INDEX IF NOT EXISTS idx_recipe_tags_tag ON recipe_tags(tag_id)"
                    )

                    # Set initial schema version
                    self._set_schema_version(cursor, 1, "Initial schema with tagging support")

                # Apply any pending migrations
                self._apply_migrations(cursor, current_version)

                conn.commit()

    def _get_schema_version(self, cursor: sqlite3.Cursor) -> int:
        """Get the current schema version from the database.

        Args:
            cursor: Database cursor

        Returns:
            Current schema version (0 if no version table exists)
        """
        try:
            cursor.execute("SELECT MAX(version) FROM schema_version")
            result = cursor.fetchone()
            return result[0] if result and result[0] is not None else 0
        except sqlite3.OperationalError:
            # Table doesn't exist yet
            return 0

    def _set_schema_version(
        self, cursor: sqlite3.Cursor, version: int, description: str = ""
    ) -> None:
        """Set the schema version in the database.

        Args:
            cursor: Database cursor
            version: Version number to set
            description: Optional description of the schema version
        """
        cursor.execute(
            """
            INSERT INTO schema_version (version, applied_at, description)
            VALUES (?, datetime('now'), ?)
        """,
            (version, description),
        )

    def _apply_migrations(self, cursor: sqlite3.Cursor, current_version: int) -> None:
        """Apply any pending database migrations.

        Args:
            cursor: Database cursor
            current_version: Current schema version

        Note:
            This method is a placeholder for future migrations.
            When schema changes are needed:
            1. Add migration logic in version order
            2. Update the schema version after each migration
            3. Ensure migrations are idempotent and can be safely re-run

        Example migration pattern:
            if current_version < 2:
                # Apply version 2 changes
                cursor.execute("ALTER TABLE recipes ADD COLUMN new_field TEXT")
                self._set_schema_version(cursor, 2, "Added new_field to recipes")
        """
        # Migration 2: Add metadata column for A/B testing and extensibility
        if current_version < 2:
            cursor.execute("ALTER TABLE recipes ADD COLUMN metadata TEXT")
            self._set_schema_version(cursor, 2, "Added metadata column for JSON data")

    def save_recipes(self, recipes: List[Recipe]) -> int:
        """Save recipes to database with proper error handling and tag support.

        Args:
            recipes: List of Recipe objects to save

        Returns:
            Number of recipes successfully saved

        Raises:
            sqlite3.DatabaseError: If a critical database error occurs
        """
        if not recipes:
            return 0

        saved = 0
        with self._get_connection() as conn:
            cursor = conn.cursor()

            for recipe in recipes:
                try:
                    # Serialize metadata to JSON
                    metadata_json = json.dumps(recipe.metadata) if recipe.metadata else None

                    # Insert recipe
                    cursor.execute(
                        """
                        INSERT INTO recipes (
                            title, book, author, chapter, epub_section,
                            serves, prep_time, cook_time,
                            ingredients, instructions, notes,
                            cooking_method, protein_type,
                            quality_score, raw_content, metadata
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                        (
                            recipe.title,
                            recipe.book,
                            recipe.author,
                            recipe.chapter,
                            recipe.epub_section,
                            recipe.serves,
                            recipe.prep_time,
                            recipe.cook_time,
                            recipe.ingredients,
                            recipe.instructions,
                            recipe.notes,
                            recipe.cooking_method,
                            recipe.protein_type,
                            recipe.quality_score,
                            recipe.raw_content,
                            metadata_json,
                        ),
                    )

                    recipe_id = cursor.lastrowid

                    # Save tags if present
                    if recipe.tags:
                        self._save_recipe_tags(cursor, recipe_id, recipe.tags)

                    saved += 1
                except sqlite3.IntegrityError as e:
                    print(f"Duplicate or constraint violation for recipe '{recipe.title}': {e}")
                except sqlite3.Error as e:
                    print(f"Error saving recipe '{recipe.title}': {e}")

            conn.commit()

        return saved

    def _save_recipe_tags(self, cursor: sqlite3.Cursor, recipe_id: int, tags: List[str]) -> None:
        """Save tags for a recipe.

        Args:
            cursor: Database cursor
            recipe_id: ID of the recipe
            tags: List of tag names

        Note:
            Tags are case-insensitive and duplicates are handled gracefully.
            This method is called within a transaction context.
        """
        for tag_name in tags:
            if not tag_name or not tag_name.strip():
                continue

            tag_name = tag_name.strip().lower()

            # Insert tag if it doesn't exist (case-insensitive)
            cursor.execute(
                """
                INSERT OR IGNORE INTO tags (tag_name) VALUES (?)
            """,
                (tag_name,),
            )

            # Get tag ID
            cursor.execute(
                """
                SELECT id FROM tags WHERE tag_name = ? COLLATE NOCASE
            """,
                (tag_name,),
            )
            tag_id = cursor.fetchone()[0]

            # Create recipe-tag relationship
            cursor.execute(
                """
                INSERT OR IGNORE INTO recipe_tags (recipe_id, tag_id) VALUES (?, ?)
            """,
                (recipe_id, tag_id),
            )

    def _get_recipe_tags(self, cursor: sqlite3.Cursor, recipe_id: int) -> List[str]:
        """Get all tags for a recipe.

        Args:
            cursor: Database cursor
            recipe_id: ID of the recipe

        Returns:
            List of tag names
        """
        cursor.execute(
            """
            SELECT t.tag_name
            FROM tags t
            JOIN recipe_tags rt ON t.id = rt.tag_id
            WHERE rt.recipe_id = ?
            ORDER BY t.tag_name
        """,
            (recipe_id,),
        )
        return [row[0] for row in cursor.fetchall()]

    def _row_to_recipe(self, row: sqlite3.Row, cursor: sqlite3.Cursor) -> Recipe:
        """Convert database row to Recipe object.

        Args:
            row: Database row from query
            cursor: Database cursor for fetching related data

        Returns:
            Recipe object populated from row data
        """
        # Get tags for this recipe
        recipe_tags = self._get_recipe_tags(cursor, row["id"])

        # Deserialize metadata from JSON
        metadata_json = row["metadata"]
        recipe_metadata = json.loads(metadata_json) if metadata_json else {}

        return Recipe(
            title=row["title"],
            book=row["book"],
            author=row["author"],
            chapter=row["chapter"],
            epub_section=row["epub_section"],
            ingredients=row["ingredients"],
            instructions=row["instructions"],
            serves=row["serves"],
            prep_time=row["prep_time"],
            cook_time=row["cook_time"],
            notes=row["notes"],
            tags=recipe_tags,
            cooking_method=row["cooking_method"],
            protein_type=row["protein_type"],
            quality_score=row["quality_score"],
            raw_content=row["raw_content"],
            metadata=recipe_metadata,
        )

    def query(
        self,
        filters: Optional[Dict[str, Any]] = None,
        min_quality: Optional[int] = None,
        limit: Optional[int] = None,
        tags: Optional[List[str]] = None,
        tags_match_all: bool = True,
    ) -> List[Recipe]:
        """Query recipes with filters using safe parameterized queries.

        Args:
            filters: Dictionary of field:value filters (only safe column names allowed)
            min_quality: Minimum quality score
            limit: Maximum number of results
            tags: List of tags to filter by (case-insensitive)
            tags_match_all: If True, match recipes with ALL tags (AND logic).
                           If False, match recipes with ANY tags (OR logic).

        Returns:
            List of matching recipes with their tags populated

        Raises:
            ValueError: If invalid column names are provided in filters
            sqlite3.DatabaseError: If database query fails
        """
        # Whitelist of allowed column names to prevent SQL injection
        allowed_columns = {
            "title",
            "book",
            "author",
            "chapter",
            "epub_section",
            "serves",
            "prep_time",
            "cook_time",
            "cooking_method",
            "protein_type",
            "quality_score",
            "difficulty",
        }

        # Base query - use DISTINCT when filtering by tags
        if tags:
            query_sql = "SELECT DISTINCT r.* FROM recipes r"
            # Join with recipe_tags and tags for tag filtering
            query_sql += " JOIN recipe_tags rt ON r.id = rt.recipe_id"
            query_sql += " JOIN tags t ON rt.tag_id = t.id"
            query_sql += " WHERE 1=1"
        else:
            query_sql = "SELECT * FROM recipes WHERE 1=1"

        params: List[Any] = []

        # Apply tag filters
        if tags:
            if tags_match_all:
                # Match ALL tags (AND logic) - recipe must have all specified tags
                # Use IN clause and then verify count with HAVING
                placeholders = ", ".join(["?"] * len(tags))
                query_sql += f" AND t.tag_name IN ({placeholders}) COLLATE NOCASE"
                params.extend([tag.lower() for tag in tags])
            else:
                # Match ANY tags (OR logic) - recipe has at least one of the tags
                placeholders = ", ".join(["?"] * len(tags))
                query_sql += f" AND t.tag_name IN ({placeholders}) COLLATE NOCASE"
                params.extend([tag.lower() for tag in tags])

        # Apply other filters
        if filters:
            for field, value in filters.items():
                if value is not None:
                    # Validate column name to prevent SQL injection
                    if field not in allowed_columns:
                        raise ValueError(f"Invalid column name: {field}")
                    # Use r.field prefix when joining with tags
                    prefix = "r." if tags else ""
                    query_sql += f" AND {prefix}{field} = ?"
                    params.append(value)

        if min_quality is not None:
            prefix = "r." if tags else ""
            query_sql += f" AND {prefix}quality_score >= ?"
            params.append(min_quality)

        # Group by recipe ID when matching ALL tags
        if tags and tags_match_all:
            query_sql += " GROUP BY r.id"
            query_sql += " HAVING COUNT(DISTINCT t.id) = ?"
            params.append(len(tags))

        query_sql += (
            " ORDER BY quality_score DESC" if not tags else " ORDER BY r.quality_score DESC"
        )

        if limit:
            query_sql += " LIMIT ?"
            params.append(limit)

        with self._get_connection() as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute(query_sql, params)
            rows = cursor.fetchall()

            recipes = []
            for row in rows:
                recipe = self._row_to_recipe(row, cursor)
                recipes.append(recipe)

        return recipes

    def search(self, query: str, limit: int = 50, tags: Optional[List[str]] = None) -> List[Recipe]:
        """Search recipes by text query with proper resource management.

        Args:
            query: Search query string
            limit: Maximum number of results (default: 50)
            tags: Optional list of tags to filter by (case-insensitive)

        Returns:
            List of matching recipes ordered by quality score with tags populated

        Raises:
            sqlite3.DatabaseError: If database search fails
        """
        search_query = f"%{query}%"

        with self._get_connection() as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            if tags:
                # Search with tag filtering
                placeholders = ", ".join(["?"] * len(tags))
                cursor.execute(
                    f"""
                    SELECT DISTINCT r.*
                    FROM recipes r
                    JOIN recipe_tags rt ON r.id = rt.recipe_id
                    JOIN tags t ON rt.tag_id = t.id
                    WHERE (r.title LIKE ? OR r.ingredients LIKE ? OR r.instructions LIKE ?)
                    AND t.tag_name IN ({placeholders}) COLLATE NOCASE
                    ORDER BY r.quality_score DESC
                    LIMIT ?
                """,
                    (
                        search_query,
                        search_query,
                        search_query,
                        *[tag.lower() for tag in tags],
                        limit,
                    ),
                )
            else:
                # Search without tag filtering
                cursor.execute(
                    """
                    SELECT * FROM recipes
                    WHERE title LIKE ? OR ingredients LIKE ? OR instructions LIKE ?
                    ORDER BY quality_score DESC
                    LIMIT ?
                """,
                    (search_query, search_query, search_query, limit),
                )

            rows = cursor.fetchall()

            recipes = []
            for row in rows:
                recipe = self._row_to_recipe(row, cursor)
                recipes.append(recipe)

        return recipes

    def count(self, filters: Optional[Dict[str, Any]] = None) -> int:
        """Count recipes matching filters with proper resource management.

        Args:
            filters: Dictionary of field:value filters (only safe column names allowed)

        Returns:
            Number of matching recipes

        Raises:
            ValueError: If invalid column names are provided in filters
            sqlite3.DatabaseError: If database query fails
        """
        # Whitelist of allowed column names to prevent SQL injection
        allowed_columns = {
            "title",
            "book",
            "author",
            "chapter",
            "epub_section",
            "serves",
            "prep_time",
            "cook_time",
            "cooking_method",
            "protein_type",
            "quality_score",
            "difficulty",
        }

        query_sql = "SELECT COUNT(*) FROM recipes WHERE 1=1"
        params = []

        if filters:
            for field, value in filters.items():
                if value is not None:
                    # Validate column name to prevent SQL injection
                    if field not in allowed_columns:
                        raise ValueError(f"Invalid column name: {field}")
                    query_sql += f" AND {field} = ?"
                    params.append(value)

        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query_sql, params)
            result = cursor.fetchone()
            count = int(result[0]) if result else 0

        return count

    def get_ab_test_stats(self) -> dict:
        """Get A/B testing statistics from metadata.

        Returns:
            dict: Statistics including:
                - total_tests: Number of recipes with A/B data
                - agreement_rate: % where both methods agreed
                - old_success_rate: % where old method succeeded
                - new_success_rate: % where new method succeeded
                - avg_confidence: Average confidence score
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()

            cursor.execute("""
                SELECT
                    COUNT(*) as total,
                    AVG(json_extract(metadata, '$.ab_test.agreement')) as agreement_rate,
                    AVG(json_extract(metadata, '$.ab_test.old_success')) as old_success_rate,
                    AVG(json_extract(metadata, '$.ab_test.new_success')) as new_success_rate,
                    AVG(json_extract(metadata, '$.ab_test.confidence')) as avg_confidence
                FROM recipes
                WHERE json_extract(metadata, '$.ab_test') IS NOT NULL
            """)

            row = cursor.fetchone()

        return {
            "total_tests": row[0] or 0,
            "agreement_rate": (row[1] or 0) * 100,
            "old_success_rate": (row[2] or 0) * 100,
            "new_success_rate": (row[3] or 0) * 100,
            "avg_confidence": row[4] or 0,
        }

    def get_ab_test_disagreements(self) -> list:
        """Get recipes where old and new methods disagreed.

        Returns:
            list: Recipes with disagreement, sorted by confidence
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()

            cursor.execute("""
                SELECT
                    title,
                    book,
                    json_extract(metadata, '$.ab_test.old_success') as old_success,
                    json_extract(metadata, '$.ab_test.new_success') as new_success,
                    json_extract(metadata, '$.ab_test.confidence') as confidence,
                    json_extract(metadata, '$.ab_test.strategy') as strategy
                FROM recipes
                WHERE json_extract(metadata, '$.ab_test.agreement') = 0
                ORDER BY COALESCE(confidence, 0) DESC
            """)

            rows = cursor.fetchall()

        return [
            {
                "title": row[0],
                "book": row[1],
                "old_success": bool(row[2]),
                "new_success": bool(row[3]),
                "confidence": row[4],
                "strategy": row[5],
            }
            for row in rows
        ]
