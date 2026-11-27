"""CLI for offline, source-first EPUB exports."""

import json
import tempfile
from pathlib import Path

import click

from epub_recipe_parser.structured import extract_book_structure


@click.command("structure")
@click.argument("epub_file", type=click.Path(exists=True, dir_okay=False, path_type=Path))
@click.option(
    "--output",
    "-o",
    type=click.Path(file_okay=False, path_type=Path),
    help="New directory for book.json and book.md; existing paths are refused.",
)
@click.option(
    "--template",
    type=click.Path(exists=True, dir_okay=False, path_type=Path),
    help="Custom Knap template; defaults to the packaged book template.",
)
def structure_command(epub_file: Path, output: Path | None, template: Path | None):
    """Preserve EPUB reading order and HTML structure, without AI or recipe heuristics."""
    destination = (output or epub_file.with_name(f"{epub_file.stem}-structured")).absolute()
    if destination.exists():
        raise click.ClickException(f"Output already exists: {destination}. Choose a new directory.")
    try:
        book = extract_book_structure(epub_file, template)
        destination.parent.mkdir(parents=True, exist_ok=True)
        # Prepare both files before exposing the result directory.
        with tempfile.TemporaryDirectory(prefix=".epub-structure-", dir=destination.parent) as tmp:
            staged = Path(tmp) / "export"
            staged.mkdir()
            (staged / "book.json").write_text(
                json.dumps(book.data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
            )
            (staged / "book.md").write_text(book.markdown + "\n", encoding="utf-8")
            if destination.exists():
                raise FileExistsError(f"Output already exists: {destination}")
            staged.rename(destination)
    except Exception as exc:
        raise click.ClickException(str(exc)) from exc
    click.echo(f"Exported {len(book.data['documents'])} documents to {destination}")
    for warning in book.data["warnings"]:
        click.echo(
            f"Warning: {warning['code']}: {warning.get('href', warning.get('message', ''))}",
            err=True,
        )
