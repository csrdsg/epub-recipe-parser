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

## Use with Obsidian

Import a cookbook EPUB directly into a new or existing Obsidian vault.
The command writes Markdown notes without creating a SQLite database.

```sh
uv run epub-parser import-vault "cookbook.epub" "./cookbook-vault"
```

Open the folder as a vault in Obsidian and start with `README.md` for the
generated cookbook index. Each recipe has its own
Markdown note with ingredients, instructions, and properties such as the source
book, tags, and cooking method when available. Search for an ingredient, browse
by tag, or follow recipe references that resolve to other notes in the vault.
For meal planning, create a weekly menu note and link to dishes with
`[[Recipe note name]]`.

The default layout groups notes by cookbook. Use `--organize-by method` to
group by cooking method or `--organize-by flat` to keep notes in one directory.

### Add recipes to an existing vault

Point `import-vault` at the existing vault folder. It preserves notes and
edits and skips recipes it has already imported.

```sh
uv run epub-parser import-vault "another-cookbook.epub" "/path/to/your vault"
```

Keep the `source_id` property when editing imported recipes so future imports
can skip them. The generated index includes both books. If your vault already
has its own `README.md`, the exporter uses `Recipe Vault Index.md` when available.

### Export recipes from SQLite

If you already have a recipe database, use `export --append` to add its
recipes to an existing vault.

```sh
uv run epub-parser export recipes.db --format vault --append --output "/path/to/your vault"
```

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
