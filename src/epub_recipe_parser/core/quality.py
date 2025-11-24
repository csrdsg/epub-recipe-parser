"""Quality scoring system for recipes."""

from epub_recipe_parser.core.models import Recipe


class QualityScorer:
    """Score recipe extraction quality."""

    @staticmethod
    def score_recipe(recipe: Recipe) -> int:
        """Calculate quality score (0-100)."""
        score = 0

        # Score ingredients (40 points max)
        if recipe.ingredients:
            if len(recipe.ingredients) >= 200:
                score += 40
            elif len(recipe.ingredients) >= 100:
                score += 30
            elif len(recipe.ingredients) >= 50:
                score += 20
            else:
                score += 10

        # Score instructions (40 points max)
        if recipe.instructions:
            if len(recipe.instructions) >= 300:
                score += 40
            elif len(recipe.instructions) >= 200:
                score += 30
            elif len(recipe.instructions) >= 100:
                score += 20
            else:
                score += 10

        # Score metadata (20 points max)
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

        return min(score, 100)

    @staticmethod
    def score_ingredients(ingredients: str) -> int:
        """Score ingredient extraction quality (0-40)."""
        if not ingredients:
            return 0

        length = len(ingredients)
        if length >= 200:
            return 40
        elif length >= 100:
            return 30
        elif length >= 50:
            return 20
        else:
            return 10

    @staticmethod
    def score_instructions(instructions: str) -> int:
        """Score instruction extraction quality (0-40)."""
        if not instructions:
            return 0

        length = len(instructions)
        if length >= 300:
            return 40
        elif length >= 200:
            return 30
        elif length >= 100:
            return 20
        else:
            return 10
