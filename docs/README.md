# Documentation

## Current guides

- [User manual](guides/USER_MANUAL.md) covers cookbook extraction, review,
  search, exports, and the Python API.
- [Development setup](guides/SETUP.md): install dependencies and run checks.
- [GitHub release process](guides/RELEASING.md) covers validation, tags, and distribution artifacts.
- [Offline structured export with Knap](guides/STRUCTURED_EXPORT.md): preserve
  EPUB reading order and HTML structure without AI or recipe heuristics.
- [Obsidian export](guides/OBSIDIAN_EXPORT_FEATURE.md): export extracted recipes
  as notes.
- [Optional Defuddle integration](guides/DEFUDDLE_INTEGRATION.md): HTML cleaning
  for the existing recipe extraction pipeline.
- [Migration guide](guides/MIGRATION.md): compatibility notes for older APIs.

## Project layout

| Location | Purpose |
| --- | --- |
| `src/epub_recipe_parser/` | Python package, including the Knap runtime and templates |
| `tests/` | Automated tests |
| `scripts/` | Maintenance, benchmarking, and diagnostic tools |
| `examples/` | Usage examples and experimental implementations |
| `docs/guides/` | User and developer guides |
| `docs/archive/` | Historical plans, research, and reports |

The root keeps project metadata, the main README, contribution instructions,
changelog, license, and agent instructions. Generated caches and installed
dependencies are ignored by Git; actual tests are not ignored.

[Historical documentation](archive/README.md) is retained for context, and may
describe previous behavior or work that was only proposed.
