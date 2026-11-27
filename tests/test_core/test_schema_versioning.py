"""Tests for database schema versioning."""

import sqlite3
from epub_recipe_parser.storage.database import RecipeDatabase


def test_schema_version_table_created(temp_db):
    """Test that schema_version table is created on initialization."""
    db = RecipeDatabase(temp_db)

    with db._get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='schema_version'"
        )
        result = cursor.fetchone()

    assert result is not None, "schema_version table should be created"


def test_initial_schema_version(temp_db):
    """Test that initial schema version is set to 2 (after metadata migration)."""
    db = RecipeDatabase(temp_db)

    with db._get_connection() as conn:
        cursor = conn.cursor()
        version = db._get_schema_version(cursor)

    assert version == 2, "Initial schema version should be 2 (after metadata migration)"


def test_schema_version_has_description(temp_db):
    """Test that schema version includes description."""
    db = RecipeDatabase(temp_db)

    with db._get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT description FROM schema_version WHERE version = 1")
        result = cursor.fetchone()

    assert result is not None
    assert "tagging" in result[0].lower(), "Description should mention tagging support"


def test_existing_database_version_preserved(temp_db):
    """Test that existing database version is preserved on re-initialization."""
    # First initialization
    db1 = RecipeDatabase(temp_db)

    with db1._get_connection() as conn:
        cursor = conn.cursor()
        version1 = db1._get_schema_version(cursor)

    # Second initialization (simulating app restart)
    db2 = RecipeDatabase(temp_db)

    with db2._get_connection() as conn:
        cursor = conn.cursor()
        version2 = db2._get_schema_version(cursor)

    assert version1 == version2 == 2, "Schema version should be preserved at version 2"


def test_get_schema_version_empty_database(tmp_path):
    """Test getting schema version from brand new database."""
    new_db_path = tmp_path / "brand_new.db"

    # Create connection but don't initialize schema
    conn = sqlite3.connect(new_db_path)
    cursor = conn.cursor()

    # Create a dummy RecipeDatabase just to use the method
    dummy_db_path = tmp_path / "temp.db"
    db = RecipeDatabase(dummy_db_path)

    # Test on the empty database cursor
    version = db._get_schema_version(cursor)

    conn.close()

    assert version == 0, "Empty database should return version 0"


def test_set_schema_version(temp_db):
    """Test setting a new schema version."""
    db = RecipeDatabase(temp_db)

    with db._get_connection() as conn:
        cursor = conn.cursor()

        # Set a new version (version 2 already exists from migration)
        db._set_schema_version(cursor, 3, "Test migration")
        conn.commit()

        # Verify it was set
        cursor.execute("SELECT version, description FROM schema_version WHERE version = 3")
        result = cursor.fetchone()

    assert result is not None
    assert result[0] == 3
    assert result[1] == "Test migration"


def test_multiple_schema_versions(temp_db):
    """Test that MAX version is returned when multiple versions exist."""
    db = RecipeDatabase(temp_db)

    with db._get_connection() as conn:
        cursor = conn.cursor()

        # Add additional versions (version 2 already exists from migration)
        db._set_schema_version(cursor, 3, "Third version")
        db._set_schema_version(cursor, 4, "Fourth version")
        conn.commit()

        # Get current version
        version = db._get_schema_version(cursor)

    assert version == 4, "Should return the maximum version"


def test_schema_version_timestamp(temp_db):
    """Test that schema version records timestamp."""
    db = RecipeDatabase(temp_db)

    with db._get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT applied_at FROM schema_version WHERE version = 1")
        result = cursor.fetchone()

    assert result is not None
    assert result[0] is not None, "Timestamp should be recorded"
    # Basic format check for SQLite datetime
    assert len(result[0]) > 0


def test_schema_version_table_structure(temp_db):
    """Test that schema_version table has correct structure."""
    db = RecipeDatabase(temp_db)

    with db._get_connection() as conn:
        cursor = conn.cursor()

        # Check table structure
        cursor.execute("PRAGMA table_info(schema_version)")
        columns = cursor.fetchall()

        column_names = [col[1] for col in columns]

    assert "version" in column_names
    assert "applied_at" in column_names
    assert "description" in column_names
