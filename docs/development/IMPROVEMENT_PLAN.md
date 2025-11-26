Based on my analysis of the extraction pipeline, here are some potential areas for improvement:

### 1. Pipeline Orchestration (`extractor.py`)

*   **Problem:** The current process is linear: split HTML -> validate -> extract. If a recipe is split across multiple HTML files (e.g., ingredients in `page1.html`, instructions in `page2.html`), it will fail.
*   **Improvement:** Implement a "stitching" mechanism. The extractor could process all HTML files, identify recipe *fragments* (e.g., a list of ingredients, a set of instructions), and then try to combine fragments from adjacent or linked HTML files into a complete recipe. This would require a more sophisticated state management system during extraction.

### 2. Validation (`validator.py`)

*   **Problem:** The `is_valid_recipe` function uses a simple scoring system based on keyword counts. This can lead to false positives (e.g., a "notes" section with cooking verbs) and false negatives (e.g., a valid recipe with unusual wording).
*   **Improvement:**
    *   **Structural Analysis:** Instead of just counting keywords, analyze the *structure* of the HTML. A valid recipe usually has a header, followed by a list (ingredients), and then a series of paragraphs or a numbered list (instructions). The validator could look for this pattern.
    *   **Negative Keywords:** The `EXCLUDE_KEYWORDS` list is a good start, but it could be expanded. Also, the validator could look for "negative" structural indicators, like a high density of links or form elements.

### 3. Ingredient Extraction (`ingredients.py`)

*   **Problem:** The extractor relies heavily on keywords and list tags (`<ul>`, `<ol>`). It may fail if ingredients are in a simple paragraph or if the section header is unconventional. The text-based extraction is a good fallback but can be brittle.
*   **Improvement:**
    *   **Line-by-Line Analysis:** For text-based extraction, instead of just looking for lines with measurements, analyze each line's pattern. Ingredient lines often follow a `(quantity) (unit) (ingredient_name)` format. Regular expressions could be used to identify and parse these lines with higher accuracy.
    *   **Consolidate "For the..." sections:** The current implementation finds "For the..." sections but returns them as a single block of text. It would be more useful to parse these into a structured format, like a dictionary where the keys are the section names (e.g., "For the sauce") and the values are the lists of ingredients.

### 4. Instruction Extraction (`instructions.py`)

*   **Problem:** The instruction extractor has many strategies, which is good, but they can sometimes conflict or misfire. For example, `_extract_long_narrative` might grab a descriptive paragraph that isn't actually part of the instructions.
*   **Improvement:**
    *   **Stateful Parsing:** Instead of trying to find the "best" block of instructions, the extractor could parse the document sequentially. When it enters an "instruction-like" state (e.g., after an "Instructions" header or a numbered list with cooking verbs), it would continue to collect paragraphs until it hits a clear "stop" signal (e.g., a "Notes" header, a copyright notice, or a sudden change in formatting).
    *   **Step-by-Step Parsing:** For lists or paragraphs that start with numbers (e.g., "1.", "2."), parse them as individual steps. This would provide more granular data and allow for better quality scoring (e.g., a recipe with 5 clear steps is likely higher quality than one with a single block of text).

### 5. Quality Scoring (`quality.py`)

*   **Problem:** The `QualityScorer` is based purely on the *length* of the extracted ingredients and instructions. A long but poorly formatted block of text could get a high score.
*   **Improvement:**
    *   **Structure-Based Scoring:** The score should be based on the *structure* and *clarity* of the extracted data. For example:
        *   **Ingredients:** Award points for each successfully parsed ingredient line (quantity, unit, name).
        *   **Instructions:** Award points for each numbered or clearly separated step.
        *   **Metadata:** Award more points for specific, parseable metadata (e.g., "prep_time": "20 minutes") vs. a generic string.
    *   **Completeness Score:** Add a "completeness" score. A recipe with a title, ingredients, and instructions should score higher than one that's missing one of these components.

### Summary of Proposed Plan

1.  **Refactor `EPUBRecipeExtractor`:** Introduce a two-pass system. The first pass identifies potential recipe fragments and their locations. The second pass attempts to "stitch" these fragments together into complete recipes.
2.  **Enhance `RecipeValidator`:** Add structural analysis to look for common recipe patterns (header -> list -> paragraphs).
3.  **Improve `IngredientsExtractor`:**
    *   Implement line-by-line parsing using regular expressions to identify `(quantity) (unit) (name)` patterns.
    *   Modify the "For the..." extraction to return a structured dictionary of ingredient sections.
4.  **Refine `InstructionsExtractor`:**
    *   Implement a stateful parser that collects instruction steps sequentially.
    *   Add logic to parse numbered steps into a list of strings.
5.  **Overhaul `QualityScorer`:**
    *   Change the scoring to be based on the structure and completeness of the extracted data, not just text length.
    *   Introduce a "completeness" metric.
