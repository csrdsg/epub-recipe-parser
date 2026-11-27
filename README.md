# EPUB Recipe Parser

Extract recipe titles, ingredients, instructions, and cooking metadata from EPUB
cookbooks. Use the Python API to get recipe objects or the CLI to save them to
SQLite and export them as JSON, Markdown, or Obsidian notes.

## Get started

From a checkout, install the project and its development dependencies.

```sh
uv sync --extra dev
```

```sh
uv run epub-parser extract cookbook.epub --output recipes.db
uv run epub-parser search recipes.db "chicken"
uv run epub-parser export recipes.db --format json --output recipes.json
```

Use `batch` to process a directory, `analyze` to inspect a book, and `validate`
to compare extracted recipes against a book's table of contents. Run
`uv run epub-parser --help` for the full command list.
See the [user manual](docs/guides/USER_MANUAL.md) for examples of each workflow.
Try the [sample cookbook](examples/sample-cookbook/README.md) for a small EPUB
with matching Markdown, JSON, and SQLite output.

## Python API

```python
from epub_recipe_parser import extract_recipes

for recipe in extract_recipes("cookbook.epub"):
    print(recipe.title)
    print(recipe.ingredients)
    print(recipe.instructions)
```

The parser looks for candidate recipes in HTML sections and falls back to
splitting documents by headings. It validates each candidate, extracts its
components. Ingredient extraction details are
available in `recipe.metadata["extraction"]["ingredients"]` when present.

## Source-preserving export

The `structure` command exports the EPUB reading order, table of contents, and
HTML trees as JSON and renders Markdown with Knap templates. It requires
Node.js 20.19+ and runs offline after installation.

```sh
npm ci --prefix src/epub_recipe_parser/structured/runtime
uv run epub-parser structure cookbook.epub --output ./cookbook-structured
```

See the [structured export guide](docs/guides/STRUCTURED_EXPORT.md) for the
output schema and template options.

## Development

Run the test suite with `uv run pytest`. See the
[documentation index](docs/README.md) for the repository layout and guides,
and the [development setup guide](docs/guides/SETUP.md) for development checks.

[Changelog](CHANGELOG.md) · [MIT License](LICENSE)
