"""Quality scoring system for recipes."""

import re
from epub_recipe_parser.core.models import Recipe


class QualityScorer:
    """Score recipe extraction quality with completeness and structure-based penalties."""

    @staticmethod
    def score_recipe(recipe: Recipe) -> int:
        """Calculate quality score (0-100) with completeness penalties.

        Scoring breakdown:
        - Ingredients: 0-45 points (based on structure and content)
        - Instructions: 0-45 points (based on structure and content)
        - Metadata: 0-10 points (serves, times, etc.)
        - Completeness penalty: -80 points if critical components missing

        This ensures incomplete recipes get honest low scores.
        """
        score = 0

        # Score ingredients with structure analysis (45 points max)
        ingredients_score = QualityScorer.score_ingredients(recipe.ingredients or "")
        score += ingredients_score

        # Score instructions with structure analysis (45 points max)
        instructions_score = QualityScorer.score_instructions(recipe.instructions or "")
        score += instructions_score

        # Score metadata (10 points max)
        metadata_score = 0
        if recipe.serves:
            metadata_score += 3
        if recipe.prep_time:
            metadata_score += 2
        if recipe.cook_time:
            metadata_score += 2
        if recipe.cooking_method:
            metadata_score += 2
        if recipe.protein_type:
            metadata_score += 1

        score += min(metadata_score, 10)

        # Apply completeness penalties (CRITICAL)
        # This is the key fix - recipes missing critical components get heavily penalized
        penalty = 0

        if not recipe.ingredients or len(recipe.ingredients.strip()) < 10:
            # No ingredients = recipe is unusable
            penalty += 40

        if not recipe.instructions or len(recipe.instructions.strip()) < 20:
            # No instructions = recipe is unusable
            penalty += 40

        # Apply penalty
        score = max(0, score - penalty)

        return min(score, 100)

    @staticmethod
    def score_ingredients(ingredients: str) -> int:
        """Score ingredient extraction quality (0-45) based on structure and content.

        Awards points for:
        - Having content (basic length)
        - Structured lists (lines starting with -, *, or numbers)
        - Multiple items (line count)
        - Measurements present

        This rewards well-extracted, structured ingredients over just long text.
        """
        if not ingredients:
            return 0

        score = 0

        # Base score for length (0-15 points)
        length = len(ingredients)
        if length >= 300:
            score += 15
        elif length >= 200:
            score += 12
        elif length >= 100:
            score += 9
        elif length >= 50:
            score += 6
        else:
            score += 3

        # Bonus for structured content (0-15 points)
        lines = [line.strip() for line in ingredients.split("\n") if line.strip()]

        # Check for list structure (lines starting with -, *, or numbers)
        structured_lines = sum(1 for line in lines if re.match(r"^[-*\d]+[\.)]\s", line))
        structure_ratio = structured_lines / len(lines) if lines else 0

        if structure_ratio >= 0.7:
            score += 15  # Well-structured list
        elif structure_ratio >= 0.4:
            score += 10  # Partially structured
        elif structure_ratio >= 0.2:
            score += 5  # Some structure

        # Bonus for number of ingredients (0-10 points)
        # Count meaningful lines (not headers or empty)
        ingredient_count = len([line for line in lines if len(line) > 5])

        if ingredient_count >= 10:
            score += 10
        elif ingredient_count >= 7:
            score += 8
        elif ingredient_count >= 5:
            score += 6
        elif ingredient_count >= 3:
            score += 4
        elif ingredient_count >= 1:
            score += 2

        # Bonus for measurements (0-5 points)
        # Common measurement indicators
        measurement_indicators = [
            r"\d+\s*(?:cup|tablespoon|teaspoon|tbsp|tsp|oz|lb|gram|kg|ml|liter)s?",
            r"\d+\s*(?:clove|slice|head|bunch|sprig|stalk|can|jar)s?",
            r"[¼½¾⅓⅔⅛⅜⅝⅞]",
        ]
        has_measurements = any(
            re.search(pattern, ingredients, re.IGNORECASE) for pattern in measurement_indicators
        )
        if has_measurements:
            score += 5

        return min(score, 45)

    @staticmethod
    def score_instructions(instructions: str) -> int:
        """Score instruction extraction quality (0-45) based on structure and content.

        Awards points for:
        - Having content (basic length)
        - Numbered or structured steps
        - Cooking verbs present
        - Multiple steps

        This rewards well-extracted, structured instructions over just long text.
        """
        if not instructions:
            return 0

        score = 0

        # Base score for length (0-15 points)
        length = len(instructions)
        if length >= 500:
            score += 15
        elif length >= 300:
            score += 12
        elif length >= 200:
            score += 9
        elif length >= 100:
            score += 6
        else:
            score += 3

        # Bonus for structured steps (0-15 points)
        lines = [line.strip() for line in instructions.split("\n") if line.strip()]

        # Check for numbered steps
        numbered_steps = sum(1 for line in lines if re.match(r"^\d+[\.)]\s", line))
        if numbered_steps >= 5:
            score += 15
        elif numbered_steps >= 3:
            score += 12
        elif numbered_steps >= 2:
            score += 8

        # Bonus for cooking verbs (0-10 points)
        cooking_verbs = [
            "heat",
            "cook",
            "mix",
            "stir",
            "combine",
            "add",
            "place",
            "remove",
            "transfer",
            "bake",
            "roast",
            "grill",
            "fry",
            "boil",
            "simmer",
            "season",
        ]
        verb_count = sum(1 for verb in cooking_verbs if verb in instructions.lower())

        if verb_count >= 8:
            score += 10
        elif verb_count >= 5:
            score += 8
        elif verb_count >= 3:
            score += 5
        elif verb_count >= 1:
            score += 3

        # Bonus for multiple steps/sentences (0-5 points)
        # Count sentences or major punctuation
        sentence_enders = (
            instructions.count(".") + instructions.count("!") + instructions.count("?")
        )
        if sentence_enders >= 5:
            score += 5
        elif sentence_enders >= 3:
            score += 3
        elif sentence_enders >= 1:
            score += 1

        return min(score, 45)
