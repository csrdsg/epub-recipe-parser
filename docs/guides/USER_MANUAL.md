# EPUB Recipe Parser User Manual

Use `extract` to turn a cookbook into searchable recipes with ingredients,
instructions, and chapter names. Use `structure` when you need the book's table
of contents, reading order, and markup for your own processing.

## Install from a checkout

Run these commands from the repository root with Python 3.10 or newer and uv
available. The recipe commands use the Python environment. The structure command
has a separate Node.js setup.

```sh
uv sync
uv run epub-parser --help
uv run epub-parser extract --help
```

Replace `cookbook.epub` in the examples with your EPUB path. Quote paths that
contain spaces.

## Extract and review one cookbook

```sh
mkdir -p cookbook-results
uv run epub-parser extract "cookbook.epub" -o cookbook-results/recipes.db
uv run epub-parser export cookbook-results/recipes.db -f markdown -o cookbook-results/recipes.md
uv run epub-parser export cookbook-results/recipes.db -f json -o cookbook-results/recipes.json
```

Open `recipes.md` to review the chapter, ingredients, and instructions for each
recipe. Use `recipes.json` for scripts or import into another tool. The JSON
contains a `recipes` array and export metadata. Keep `recipes.db` for search
and future exports.

Add `--verbose` to `extract` for a preview of the first few recipe titles and
more detail on errors. When you omit `-o`, extraction uses `recipes.db` in the
working directory. Extraction adds rows to an existing database. Use a fresh
database path when re-running a cookbook for comparison.

The parser uses HTML sections and headings to find recipes, then looks for
ingredients, directions, and metadata. Chapter names come from the EPUB table of
contents where the entries can be mapped to the recipe. Missing optional fields
such as serving size and cook time are common in source EPUBs.

## Build a collection from several EPUBs

```sh
uv run epub-parser batch ./cookbooks -o collection.db --verbose
uv run epub-parser batch ./cookbooks --pattern '**/*.epub' -o nested-collection.db
```

The default pattern is `*.epub` in the selected directory. Quote a custom pattern
so the parser can apply it. The batch report lists files that failed. Recipes
saved from earlier books are available if a later book fails.

### Run the multiprocessing example

The built-in `batch` command runs sequentially. From a repository checkout,
run the separate multiprocessing example as a Python module. It reads the
`*.epub` files in the selected directory and saves the results to SQLite.

```sh
uv run python -m examples.multiprocessing ./cookbooks --workers 2 -o parallel.db
uv run epub-parser export parallel.db -f vault -o cookbook-vault
```

## Search by text or tags

```sh
uv run epub-parser search collection.db "garlic" --limit 20
uv run epub-parser list-tags collection.db
uv run epub-parser search collection.db "garlic" --tags quick
uv run epub-parser query-tags collection.db --tags quick --tags dinner
uv run epub-parser query-tags collection.db --tags quick --tags dinner --match-all
```

`search` looks in titles, ingredients, and instructions. Its default limit is
10. When given several tags, it accepts any of them. `query-tags` defaults to
20 results and matches any supplied tag unless you pass `--match-all`. These
commands use stored recipe tags. To assign tags while assembling a database,
use the Python API example below.

## Export to Obsidian

```sh
uv run epub-parser export collection.db -f vault --organize-by book -o cookbook-vault
```

Open `cookbook-vault` as a vault in Obsidian. The exporter creates one Markdown
note per recipe and an index. Choose `--organize-by method` for folders by
cooking method or `--organize-by flat` for a single directory of recipe notes.
The default organization is `book`. See the [Obsidian export guide](OBSIDIAN_EXPORT_FEATURE.md).

## Inspect a cookbook and check extraction coverage

```sh
uv run epub-parser analyze "cookbook.epub" --verbose
uv run epub-parser validate "cookbook.epub" cookbook-results/recipes.db
```

Use `analyze` before extraction to inspect the EPUB's document structure and
recipe patterns. Use `validate` afterward to compare extracted titles with
recipe entries detected in the table of contents. A single-book database makes
the comparison easier to interpret. Check reported misses against the EPUB, since
a heading or table-of-contents title can differ from the extracted recipe title.
Review the Markdown export to check the ingredient and instruction text itself.

## Preserve a book's source structure

Install the pinned JavaScript dependencies once with Node.js 20.19 or newer.
Subsequent exports run offline.

```sh
npm ci --prefix src/epub_recipe_parser/structured/runtime
uv run epub-parser structure "cookbook.epub" -o cookbook-structured
```

Choose a new output directory. Open `book.md` for the rendered reading view or
`book.json` for metadata, the nested table of contents, document-level HTML
trees, and warnings. Media references point to source resources. Keep the EPUB
for its original assets. Use `--template ./my-book.knap.md` with a new output
directory to customize the Markdown rendering. See the [structured export guide](STRUCTURED_EXPORT.md).

## Use the Python API

Save snippets as a Python file and run them with `uv run python your_script.py`.

### Extract recipes, assign tags, and query SQLite

```python
from epub_recipe_parser import ExtractorConfig, extract_recipes
from epub_recipe_parser.storage import RecipeDatabase

config = ExtractorConfig(include_raw_content=False)
recipes = extract_recipes("cookbook.epub", config=config)

for recipe in recipes:
    recipe.tags.append("review")
    print(recipe.chapter, recipe.title)

db = RecipeDatabase("python-recipes.db")
print(f"Saved {db.save_recipes(recipes)} recipes")
matches = db.query(tags=["review"], limit=10)
for recipe in matches:
    print(recipe.to_dict()["ingredients"])
```

Use `db.search("garlic")` for text search or
`db.query(filters={"chapter": "Breakfasts"})` for an exact field match. Use the
chapter name shown in your own export for the filter value.

### Extract from a standalone HTML section

```python
from pathlib import Path

from bs4 import BeautifulSoup
from epub_recipe_parser import EPUBRecipeExtractor

html = Path("recipe.html").read_text(encoding="utf-8")
soup = BeautifulSoup(html, "html.parser")
recipe = EPUBRecipeExtractor().extract_from_section(soup, title="Smoked Almonds")
if recipe is not None:
    print(recipe.to_dict())
```

Pass one candidate recipe section at a time. The method returns a recipe when
the section passes validation.

### Clean cluttered HTML or compare ingredient extraction methods

Enable `ExtractorConfig(use_defuddle_cleaning=True)` to try optional HTML
cleanup for an EPUB. The parser uses the original section when the
`defuddle` executable is unavailable or cleaning fails. To compare against
legacy ingredient extraction, run a separate extraction with
`ExtractorConfig(use_pattern_extraction=False)`. The default pattern-based
method can expose ingredient detection details at
`recipe.metadata["extraction"]["ingredients"]`. See the [Defuddle guide](DEFUDDLE_INTEGRATION.md).

### Read book structure in Python

```python
from epub_recipe_parser.structured import extract_book_structure

book = extract_book_structure("cookbook.epub")
print(book.data["toc"])
print(book.markdown)
```

This uses the same Node.js dependencies as the `structure` command.

## Read legacy A/B comparison data

```sh
uv run epub-parser ab-report comparison.db
```

Run this on a database with saved A/B extraction metadata. The report summarizes
the two ingredient extraction methods and their disagreements. To generate
comparison data from Python, use `ExtractorConfig(enable_ab_testing=True)`
when extracting, then save the returned recipes to a separate comparison
database. This workflow is deprecated.

## Troubleshoot an export

- **The EPUB cannot be opened.** Check the path and confirm the file opens in an EPUB reader.
- **Recipes or chapters are missing.** Run `analyze` and `validate`, then use `structure` to inspect the table of contents and source HTML.
- **An export has too many copies.** Re-extract into a fresh database path.
- **The structure command reports missing dependencies.** Run the npm command from the error and retry with a new output directory.
- **A command rejects an option.** Run `uv run epub-parser <command> --help` to see the supported arguments.
