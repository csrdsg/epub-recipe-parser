"""Read EPUB metadata and reading order without interpreting recipe content."""

import json
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import ebooklib
from ebooklib import epub


RUNTIME = Path(__file__).parent / "runtime"


@dataclass
class StructuredBook:
    """Structured source data plus its Knap-rendered Markdown view."""

    data: dict[str, Any]
    markdown: str


def _toc_entries(entries) -> list[dict[str, Any]]:
    result = []
    for entry in entries:
        children = []
        if isinstance(entry, tuple):
            entry, nested = entry
            children = _toc_entries(nested)
        result.append(
            {
                "title": getattr(entry, "title", ""),
                "href": getattr(entry, "href", None),
                "children": children,
            }
        )
    return result


def _read_source(path: Path) -> dict[str, Any]:
    book = epub.read_epub(str(path))
    titles = book.get_metadata("DC", "title")
    documents = []
    warnings = []
    seen = set()
    for position, (idref, linear) in enumerate(book.spine, 1):
        item = book.get_item_with_id(idref)
        if item is None:
            raise ValueError(f"EPUB spine references a missing item: {idref}")
        if item.get_type() != ebooklib.ITEM_DOCUMENT:
            warnings.append({"code": "non_text_spine_item", "href": item.get_name()})
            continue
        seen.add(idref)
        # Navigation belongs in the TOC, not a second copy of the book's text.
        if "nav" in getattr(item, "properties", []):
            continue
        documents.append(
            {
                "id": f"document-{position:04d}",
                "idref": idref,
                "href": item.get_name(),
                "linear": linear != "no",
                # EbookLib serializes XHTML as UTF-8; this is normalized XHTML,
                # not a claim to preserve the original ZIP entry byte for byte.
                "source_html": item.get_content().decode("utf-8"),
            }
        )
    for item in book.get_items_of_type(ebooklib.ITEM_DOCUMENT):
        if item.id not in seen and "nav" not in getattr(item, "properties", []):
            warnings.append({"code": "document_outside_spine", "href": item.get_name()})
    if not documents:
        raise ValueError("EPUB has no text documents in its reading order")
    return {
        "schema_version": "1.0",
        "mode": "source-structure",
        "book": {
            "title": titles[0][0] if titles else path.stem,
            "authors": [value for value, _ in book.get_metadata("DC", "creator")],
            "languages": [value for value, _ in book.get_metadata("DC", "language")],
            "source_file": path.name,
        },
        "toc": _toc_entries(book.toc),
        "documents": documents,
        "warnings": warnings,
    }


def extract_book_structure(
    epub_path: str | Path, template_path: str | Path | None = None
) -> StructuredBook:
    """Preserve EPUB structure, then render it with Knap entirely offline.

    Recipe fields are deliberately not inferred. Node dependencies must first
    be installed beside the packaged runtime (see the structured export guide).
    No subprocess may install dependencies or fetch content during extraction.
    """
    path = Path(epub_path)
    if not path.is_file():
        raise FileNotFoundError(f"EPUB file not found: {path}")
    node = shutil.which("node")
    if node is None:
        raise RuntimeError("Structured export requires Node.js 20.19 or later")
    template = Path(template_path) if template_path else RUNTIME / "book.knap.md"
    payload = {"data": _read_source(path), "template": template.read_text(encoding="utf-8")}
    try:
        result = subprocess.run(
            [node, str(RUNTIME / "render.mjs")],
            input=json.dumps(payload, ensure_ascii=False),
            text=True,
            encoding="utf-8",
            capture_output=True,
            timeout=120,
            check=False,
        )
    except subprocess.TimeoutExpired as exc:
        raise RuntimeError("Knap structured export exceeded the 120 second limit") from exc
    if result.returncode:
        if "ERR_MODULE_NOT_FOUND" in result.stderr:
            raise RuntimeError(
                f"Install the structured renderer dependencies first: npm ci --prefix {RUNTIME}"
            )
        raise RuntimeError(f"Knap structured export failed: {result.stderr.strip()}")
    rendered = json.loads(result.stdout)
    return StructuredBook(data=rendered["data"], markdown=rendered["markdown"])
