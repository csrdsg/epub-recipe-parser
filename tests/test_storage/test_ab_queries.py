"""Tests for A/B testing database queries."""

import pytest
from pathlib import Path
import tempfile

from epub_recipe_parser.storage.database import RecipeDatabase
from epub_recipe_parser.core.models import Recipe


@pytest.fixture
def temp_ab_db():
    """Create a temporary database for A/B testing."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".db", delete=False) as f:
        db_path = f.name

    db = RecipeDatabase(db_path)
    yield db_path

    # Cleanup
    Path(db_path).unlink(missing_ok=True)


class TestGetABTestStats:
    """Test get_ab_test_stats() method."""

    def test_stats_empty_when_no_data(self, temp_ab_db):
        """Stats return zero when no A/B data exists."""
        db = RecipeDatabase(temp_ab_db)
        stats = db.get_ab_test_stats()

        assert stats["total_tests"] == 0
        assert stats["agreement_rate"] == 0
        assert stats["old_success_rate"] == 0
        assert stats["new_success_rate"] == 0
        assert stats["avg_confidence"] == 0

    def test_stats_with_single_agreement(self, temp_ab_db):
        """Stats calculated correctly with single agreement."""
        db = RecipeDatabase(temp_ab_db)

        recipe = Recipe(
            title="Test Recipe",
            book="Test Book",
            ingredients="2 cups flour",
            metadata={
                "ab_test": {
                    "old_success": True,
                    "new_success": True,
                    "agreement": True,
                    "confidence": 0.8,
                }
            },
        )

        db.save_recipes([recipe])
        stats = db.get_ab_test_stats()

        assert stats["total_tests"] == 1
        assert stats["agreement_rate"] == 100.0
        assert stats["old_success_rate"] == 100.0
        assert stats["new_success_rate"] == 100.0
        assert stats["avg_confidence"] == 0.8

    def test_stats_with_disagreement(self, temp_ab_db):
        """Stats reflect disagreements correctly."""
        db = RecipeDatabase(temp_ab_db)

        recipes = [
            Recipe(
                title="Recipe 1",
                book="Test Book",
                ingredients="test",
                metadata={
                    "ab_test": {
                        "old_success": True,
                        "new_success": False,
                        "agreement": False,
                        "confidence": 0.6,
                    }
                },
            ),
            Recipe(
                title="Recipe 2",
                book="Test Book",
                ingredients="test",
                metadata={
                    "ab_test": {
                        "old_success": True,
                        "new_success": True,
                        "agreement": True,
                        "confidence": 0.9,
                    }
                },
            ),
        ]

        db.save_recipes(recipes)
        stats = db.get_ab_test_stats()

        assert stats["total_tests"] == 2
        assert stats["agreement_rate"] == 50.0  # 1 out of 2
        assert stats["old_success_rate"] == 100.0  # 2 out of 2
        assert stats["new_success_rate"] == 50.0  # 1 out of 2
        assert stats["avg_confidence"] == 0.75  # (0.6 + 0.9) / 2

    def test_stats_ignores_recipes_without_ab_data(self, temp_ab_db):
        """Stats only count recipes with A/B metadata."""
        db = RecipeDatabase(temp_ab_db)

        recipes = [
            Recipe(
                title="With AB",
                book="Test",
                metadata={
                    "ab_test": {
                        "old_success": True,
                        "new_success": True,
                        "agreement": True,
                        "confidence": 0.8,
                    }
                },
            ),
            Recipe(title="Without AB", book="Test", metadata={}),
            Recipe(title="No metadata", book="Test"),
        ]

        db.save_recipes(recipes)
        stats = db.get_ab_test_stats()

        assert stats["total_tests"] == 1  # Only one recipe with A/B data

    def test_stats_with_mixed_success_rates(self, temp_ab_db):
        """Stats handle various success/failure combinations."""
        db = RecipeDatabase(temp_ab_db)

        recipes = [
            Recipe(
                title="Both succeed",
                book="Test",
                metadata={
                    "ab_test": {
                        "old_success": True,
                        "new_success": True,
                        "agreement": True,
                        "confidence": 0.9,
                    }
                },
            ),
            Recipe(
                title="Old succeeds only",
                book="Test",
                metadata={
                    "ab_test": {
                        "old_success": True,
                        "new_success": False,
                        "agreement": False,
                        "confidence": 0.5,
                    }
                },
            ),
            Recipe(
                title="New succeeds only",
                book="Test",
                metadata={
                    "ab_test": {
                        "old_success": False,
                        "new_success": True,
                        "agreement": False,
                        "confidence": 0.7,
                    }
                },
            ),
            Recipe(
                title="Both fail",
                book="Test",
                metadata={
                    "ab_test": {
                        "old_success": False,
                        "new_success": False,
                        "agreement": True,
                        "confidence": 0.2,
                    }
                },
            ),
        ]

        db.save_recipes(recipes)
        stats = db.get_ab_test_stats()

        assert stats["total_tests"] == 4
        assert stats["agreement_rate"] == 50.0  # 2 out of 4 (both succeed + both fail)
        assert stats["old_success_rate"] == 50.0  # 2 out of 4
        assert stats["new_success_rate"] == 50.0  # 2 out of 4
        assert stats["avg_confidence"] == 0.575  # (0.9 + 0.5 + 0.7 + 0.2) / 4


class TestGetABTestDisagreements:
    """Test get_ab_test_disagreements() method."""

    def test_disagreements_empty_when_all_agree(self, temp_ab_db):
        """No disagreements returned when all recipes agree."""
        db = RecipeDatabase(temp_ab_db)

        recipes = [
            Recipe(
                title="Agree 1",
                book="Test",
                metadata={"ab_test": {"agreement": True, "confidence": 0.8}},
            ),
            Recipe(
                title="Agree 2",
                book="Test",
                metadata={"ab_test": {"agreement": True, "confidence": 0.9}},
            ),
        ]

        db.save_recipes(recipes)
        disagreements = db.get_ab_test_disagreements()

        assert len(disagreements) == 0

    def test_disagreements_returned_correctly(self, temp_ab_db):
        """Disagreements are returned with correct structure."""
        db = RecipeDatabase(temp_ab_db)

        recipe = Recipe(
            title="Disagreement Recipe",
            book="Test Book",
            metadata={
                "ab_test": {
                    "agreement": False,
                    "old_success": True,
                    "new_success": False,
                    "confidence": 0.6,
                    "strategy": "original_with_patterns",
                }
            },
        )

        db.save_recipes([recipe])
        disagreements = db.get_ab_test_disagreements()

        assert len(disagreements) == 1
        d = disagreements[0]

        assert d["title"] == "Disagreement Recipe"
        assert d["book"] == "Test Book"
        assert d["old_success"] is True
        assert d["new_success"] is False
        assert d["confidence"] == 0.6
        assert d["strategy"] == "original_with_patterns"

    def test_disagreements_sorted_by_confidence(self, temp_ab_db):
        """Disagreements are sorted by confidence descending."""
        db = RecipeDatabase(temp_ab_db)

        recipes = [
            Recipe(
                title="Low confidence",
                book="Test",
                metadata={
                    "ab_test": {
                        "agreement": False,
                        "old_success": True,
                        "new_success": False,
                        "confidence": 0.3,
                        "strategy": "strategy1",
                    }
                },
            ),
            Recipe(
                title="High confidence",
                book="Test",
                metadata={
                    "ab_test": {
                        "agreement": False,
                        "old_success": False,
                        "new_success": True,
                        "confidence": 0.9,
                        "strategy": "strategy2",
                    }
                },
            ),
            Recipe(
                title="Medium confidence",
                book="Test",
                metadata={
                    "ab_test": {
                        "agreement": False,
                        "old_success": True,
                        "new_success": False,
                        "confidence": 0.6,
                        "strategy": "strategy3",
                    }
                },
            ),
        ]

        db.save_recipes(recipes)
        disagreements = db.get_ab_test_disagreements()

        assert len(disagreements) == 3
        # Should be sorted by confidence descending
        assert disagreements[0]["title"] == "High confidence"
        assert disagreements[0]["confidence"] == 0.9
        assert disagreements[1]["title"] == "Medium confidence"
        assert disagreements[1]["confidence"] == 0.6
        assert disagreements[2]["title"] == "Low confidence"
        assert disagreements[2]["confidence"] == 0.3

    def test_disagreements_ignores_agreements(self, temp_ab_db):
        """Only disagreements are returned, agreements are filtered out."""
        db = RecipeDatabase(temp_ab_db)

        recipes = [
            Recipe(
                title="Agreement",
                book="Test",
                metadata={
                    "ab_test": {
                        "agreement": True,
                        "old_success": True,
                        "new_success": True,
                        "confidence": 0.8,
                    }
                },
            ),
            Recipe(
                title="Disagreement 1",
                book="Test",
                metadata={
                    "ab_test": {
                        "agreement": False,
                        "old_success": True,
                        "new_success": False,
                        "confidence": 0.7,
                        "strategy": "s1",
                    }
                },
            ),
            Recipe(
                title="Disagreement 2",
                book="Test",
                metadata={
                    "ab_test": {
                        "agreement": False,
                        "old_success": False,
                        "new_success": True,
                        "confidence": 0.5,
                        "strategy": "s2",
                    }
                },
            ),
        ]

        db.save_recipes(recipes)
        disagreements = db.get_ab_test_disagreements()

        assert len(disagreements) == 2
        assert all(d["title"].startswith("Disagreement") for d in disagreements)

    def test_disagreements_handles_null_strategy(self, temp_ab_db):
        """Disagreements handle recipes with null strategy gracefully."""
        db = RecipeDatabase(temp_ab_db)

        recipe = Recipe(
            title="No strategy",
            book="Test",
            metadata={
                "ab_test": {
                    "agreement": False,
                    "old_success": True,
                    "new_success": False,
                    "confidence": 0.6,
                    "strategy": None,
                }
            },
        )

        db.save_recipes([recipe])
        disagreements = db.get_ab_test_disagreements()

        assert len(disagreements) == 1
        assert disagreements[0]["strategy"] is None
