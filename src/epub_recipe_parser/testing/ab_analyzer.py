"""A/B test analysis for extraction comparison."""

from typing import List, Dict, Any
from pathlib import Path

from epub_recipe_parser.storage.database import RecipeDatabase


class ABTestAnalyzer:
    """Analyzes A/B testing results from recipe extraction.

    Separates analysis logic from storage, following Single Responsibility Principle.
    """

    def __init__(self, database: RecipeDatabase):
        """Initialize analyzer with database connection.

        Args:
            database: RecipeDatabase instance containing A/B test data
        """
        self.db = database

    def get_statistics(self) -> Dict[str, Any]:
        """Get overall A/B testing statistics.

        Returns:
            dict: Statistics including:
                - total_tests: Number of recipes with A/B test data
                - agreement_rate: Percentage where old and new methods agreed
                - old_success_rate: Success rate of old method
                - new_success_rate: Success rate of new method
                - avg_confidence: Average confidence score from pattern detection
        """
        with self.db._get_connection() as conn:
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

    def get_disagreements(self) -> List[Dict[str, Any]]:
        """Get recipes where old and new extraction methods disagreed.

        Returns:
            list: Disagreement cases sorted by confidence, each containing:
                - title: Recipe title
                - book: Book name
                - old_success: Whether old method succeeded
                - new_success: Whether new method succeeded
                - confidence: Confidence score from pattern detection
                - strategy: Strategy used by new method
        """
        with self.db._get_connection() as conn:
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

    def generate_report(self) -> str:
        """Generate a formatted text report of A/B test results.

        Returns:
            str: Formatted report text
        """
        stats = self.get_statistics()
        disagreements = self.get_disagreements()

        report = []
        report.append("=" * 70)
        report.append("A/B TESTING REPORT")
        report.append("=" * 70)
        report.append("")

        # Overall statistics
        report.append("OVERALL STATISTICS")
        report.append("-" * 70)
        report.append(f"Total tests:        {stats['total_tests']}")
        report.append(f"Agreement rate:     {stats['agreement_rate']:.1f}%")
        report.append(f"Old success rate:   {stats['old_success_rate']:.1f}%")
        report.append(f"New success rate:   {stats['new_success_rate']:.1f}%")
        report.append(f"Avg confidence:     {stats['avg_confidence']:.2f}")
        report.append("")

        # Disagreements
        if disagreements:
            report.append(f"DISAGREEMENTS ({len(disagreements)} cases)")
            report.append("-" * 70)
            for i, case in enumerate(disagreements[:10], 1):  # Show top 10
                report.append(f"{i}. {case['title'][:50]}")
                report.append(f"   Book: {case['book']}")
                report.append(f"   Old: {'SUCCESS' if case['old_success'] else 'FAIL'}, "
                            f"New: {'SUCCESS' if case['new_success'] else 'FAIL'}")
                report.append(f"   Confidence: {case['confidence']:.2f}, "
                            f"Strategy: {case['strategy']}")
                report.append("")
        else:
            report.append("NO DISAGREEMENTS FOUND")
            report.append("")

        report.append("=" * 70)
        return "\n".join(report)

    @classmethod
    def from_database_path(cls, db_path: str | Path) -> "ABTestAnalyzer":
        """Create analyzer from database file path.

        Args:
            db_path: Path to SQLite database file

        Returns:
            ABTestAnalyzer instance
        """
        db = RecipeDatabase(db_path)
        return cls(db)
