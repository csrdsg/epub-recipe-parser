# Small Kitchen Cookbook

This sample contains two original recipes created for this project and covered
by the repository's [MIT license](../../LICENSE). One recipe uses HTML headings
and lists. The other uses styled paragraphs. Each has its own chapter.

- [Sample EPUB](sample.epub) is the input.
- [Markdown](recipes.md) shows the extracted recipes and chapters.
- [JSON](recipes.json) includes the narrative step durations.
- [SQLite](recipes.db) is the searchable sample database.

From the repository root, run the example in a fresh output directory.

```sh
mkdir -p sample-results
uv run epub-parser extract examples/sample-cookbook/sample.epub -o sample-results/recipes.db
uv run epub-parser validate examples/sample-cookbook/sample.epub sample-results/recipes.db
uv run epub-parser search sample-results/recipes.db "ginger"
uv run epub-parser export sample-results/recipes.db -f markdown -o sample-results/recipes.md
uv run epub-parser export sample-results/recipes.db -f json -o sample-results/recipes.json
```

The parser saves two recipes. In JSON, look at `metadata.timing.steps` for the
20–25 minute roast and the tofu's marinating, baking, and resting durations.

To rebuild the input EPUB with its original recipe markup, run
`uv run python examples/sample-cookbook/build_epub.py sample-results/rebuilt.epub`.
