# Offline EPUB structure export with Knap

This workflow keeps the source structure instead of guessing recipe fields.
It runs locally without AI, API keys, network requests, cookbook-specific
selectors, ingredient dictionaries, or quality thresholds.

## Setup

Install Python dependencies as usual, plus Node.js 20.19 or newer. From the project root:

```sh
uv sync --extra dev
npm ci --prefix src/epub_recipe_parser/structured/runtime
```

The npm installation downloads pinned dependencies once. Export itself works
offline and never invokes npm or downloads missing dependencies automatically.
The Node runtime and templates are included in Python wheels; for an installed
wheel, install dependencies in its `epub_recipe_parser/structured/runtime`
directory (the missing-dependencies error prints the exact command).

## Use

```sh
uv run epub-parser structure cookbook.epub --output ./cookbook-structured
uv run epub-parser structure cookbook.epub --output ./custom-export --template ./my-book.knap.md
```

The output directory must not already exist. Template or rendering failures
leave no export directory. The existing `extract` and `batch` commands still
use the older recipe heuristics; `structure` is an independent path.

## Output contract

`book.json` is the reusable source representation, with `schema_version: "1.0"`:

- `mode`: `source-structure`, distinguishing it from inferred recipe data.
- `book`: source filename, title, authors, and languages from EPUB metadata.
  Only a missing book title falls back to the input filename.
- `toc`: nested entries with `title`, `href`, `export_href`, and `children`.
  Original fragments are retained in `href`; `export_href` points to the
  corresponding Markdown anchor, or is null when unresolved or external.
  The TOC does not invent or determine recipe boundaries.
- `documents`: XHTML documents in EPUB spine order, including non-linear entries
  marked `linear: false`. Navigation documents are excluded from the text view.
- Each document includes `id`, `idref`, `href`, `linear`, `source_html`, `title`,
  `structure`, `anchors`, and `markdown`. `title` is the HTML title or null.
  `anchors` maps source IDs and named anchors to document-scoped Markdown
  targets, avoiding collisions between different chapters.
- `structure` is always an array of Knap HTML-to-JSON nodes. Element nodes have
  `type: "element"`, `tag`, optional `attributes`, and optional `children`;
  text nodes have `type: "text"` and `content`. Nested wrappers remain nested;
  their contents are not emitted twice as separate recipes.
- `warnings`: explicit issues such as documents outside the spine, missing
  headings, non-text spine items, and links or media requiring source resources.

`source_html` is normalized XHTML serialized by EbookLib, not the original ZIP
entry bytes. XHTML is serialized with explicit HTML end tags before conversion
so empty source anchors and spans cannot absorb their following siblings.
Knap trims text-node edge whitespace in `structure`; use
`source_html` when exact whitespace or inline spacing matters.

`book.md` is rendered by **Knap** using the bundled `book.knap.md` template.
The input variables are the entire `book.json` object. Edit the template to
change layout without changing Python code. Turndown performs generic HTML to
Markdown conversion before Knap renders the book. Tables, definition lists,
SVG, and MathML stay as embedded HTML rather than being silently flattened.

## Limits

Source markup determines the available structure. An unlabelled paragraph
stays a paragraph; the exporter does not claim it is an ingredient or a step.
It exports one book view, not automatically separated recipe notes. There is
no recipe confidence score or inferred serving/time metadata.

Internal text links are rewritten to explicit anchors in the combined Markdown,
including links within a chapter, between chapters, and to a whole document.
Original links and IDs remain unchanged in `source_html` and `structure`.
Custom templates should include each document's `markdown` so anchors are present.
Missing internal targets are retained and reported as `unresolved_internal_link`.
External URLs stay unchanged. Media references retain their EPUB targets and
assets are not copied; `source_links_or_media` flags documents containing media.
Documents outside the reading spine are reported rather than appended in an
invented order. Keep the EPUB as the authoritative complete source.

Exports contain source HTML and are not sanitized for browser execution.
Rendering has finite Knap limits and a 120-second process timeout; oversized
input or malformed templates fail explicitly instead of silently dropping text.

## Python API

```python
from epub_recipe_parser.structured import extract_book_structure

book = extract_book_structure("cookbook.epub")
print(book.data["documents"][0]["structure"])
print(book.markdown)
```

## Validation

```sh
uv run pytest tests/test_structured_export.py -q
```

Tests build their own tiny EPUBs, so this workflow has no dependency on a
personal cookbook collection or absolute paths.

References: [Knap API](https://knap.md/api),
[HTML filters](https://knap.md/filters), [Turndown](https://github.com/mixmark-io/turndown).
