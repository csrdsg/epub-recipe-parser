"""SQLite storage for recipes."""

import sqlite3
from pathlib import Path
from typing import List, Dict, Any, Optional

from epub_recipe_parser.core.models import Recipe


class RecipeDatabase:
    """SQLite storage for recipes."""

    def __init__(self, db_path: str | Path):
        """Initialize database connection."""
        self.db_path = Path(db_path)
        self.init_database()

    def init_database(self):
        """Initialize SQLite database schema."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

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
                tag_name TEXT UNIQUE NOT NULL
            )
        """
        )

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS recipe_tags (
                recipe_id INTEGER,
                tag_id INTEGER,
                FOREIGN KEY (recipe_id) REFERENCES recipes(id),
                FOREIGN KEY (tag_id) REFERENCES tags(id),
                PRIMARY KEY (recipe_id, tag_id)
            )
        """
        )

        # Create indexes for common queries
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_recipes_book ON recipes(book)"
        )
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_recipes_quality ON recipes(quality_score)"
        )
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_recipes_cooking_method ON recipes(cooking_method)"
        )

        conn.commit()
        conn.close()

    def save_recipes(self, recipes: List[Recipe]) -> int:
        """
        Save recipes to database.

        Returns:
            Number of recipes saved
        """
        if not recipes:
            return 0

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        saved = 0
        for recipe in recipes:
            try:
                cursor.execute(
                    """
                    INSERT INTO recipes (
                        title, book, author, chapter, epub_section,
                        serves, prep_time, cook_time,
                        ingredients, instructions, notes,
                        cooking_method, protein_type,
                        quality_score, raw_content
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
                    ),
                )
                saved += 1
            except sqlite3.Error as e:
                print(f"Error saving recipe '{recipe.title}': {e}")

        conn.commit()
        conn.close()

        return saved

    def query(
        self,
        filters: Optional[Dict[str, Any]] = None,
        min_quality: Optional[int] = None,
        limit: Optional[int] = None,
    ) -> List[Recipe]:
        """
        Query recipes with filters.

        Args:
            filters: Dictionary of field:value filters
            min_quality: Minimum quality score
            limit: Maximum number of results

        Returns:
            List of matching recipes
        """
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        query = "SELECT * FROM recipes WHERE 1=1"
        params = []

        if filters:
            for field, value in filters.items():
                if value is not None:
                    query += f" AND {field} = ?"
                    params.append(value)

        if min_quality is not None:
            query += " AND quality_score >= ?"
            params.append(min_quality)

        query += " ORDER BY quality_score DESC"

        if limit:
            query += " LIMIT ?"
            params.append(limit)

        cursor.execute(query, params)
        rows = cursor.fetchall()

        recipes = []
        for row in rows:
            recipe = Recipe(
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
                cooking_method=row["cooking_method"],
                protein_type=row["protein_type"],
                quality_score=row["quality_score"],
                raw_content=row["raw_content"],
            )
            recipes.append(recipe)

        conn.close()
        return recipes

    def search(self, query: str, limit: int = 50) -> List[Recipe]:
        """
        Search recipes by text query.

        Args:
            query: Search query
            limit: Maximum number of results

        Returns:
            List of matching recipes
        """
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        search_query = f"%{query}%"
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
            recipe = Recipe(
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
                cooking_method=row["cooking_method"],
                protein_type=row["protein_type"],
                quality_score=row["quality_score"],
                raw_content=row["raw_content"],
            )
            recipes.append(recipe)

        conn.close()
        return recipes

    def count(self, filters: Optional[Dict[str, Any]] = None) -> int:
        """Count recipes matching filters."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        query = "SELECT COUNT(*) FROM recipes WHERE 1=1"
        params = []

        if filters:
            for field, value in filters.items():
                if value is not None:
                    query += f" AND {field} = ?"
                    params.append(value)

        cursor.execute(query, params)
        count = cursor.fetchone()[0]

        conn.close()
        return count
