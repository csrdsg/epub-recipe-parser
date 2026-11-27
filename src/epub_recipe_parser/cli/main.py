"""Main CLI entry point."""

import json
import sys
import click
from pathlib import Path
from rich.console import Console
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn
from rich.panel import Panel
from epub_recipe_parser import __version__

from epub_recipe_parser.core import EPUBRecipeExtractor
from epub_recipe_parser.storage import RecipeDatabase
from epub_recipe_parser.analyzers import TOCAnalyzer, EPUBStructureAnalyzer
from epub_recipe_parser.exporters import ObsidianVaultExporter
from epub_recipe_parser.cli.structure import structure_command

console = Console()


@click.group()
@click.version_option(version=__version__)
def cli():
    """EPUB Recipe Parser - Extract recipes from EPUB cookbooks."""
    pass


cli.add_command(structure_command)


@cli.command()
@click.argument("epub_file", type=click.Path(exists=True))
@click.option("--output", "-o", default="recipes.db", help="Output database file")
@click.option("--verbose", "-v", is_flag=True, help="Show detailed extraction information")
def extract(epub_file: str, output: str, verbose: bool):
    """Extract recipes from an EPUB file."""
    try:
        epub_path = Path(epub_file)

        # Display header
        console.print()
        console.print(
            Panel.fit(
                f"[bold cyan]Extracting Recipes[/bold cyan]\n"
                f"File: {epub_path.name}",
                border_style="cyan",
            )
        )
        console.print()

        extractor = EPUBRecipeExtractor()

        # Extract with progress indicator
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            task = progress.add_task("Analyzing EPUB structure...", total=None)
            recipes = extractor.extract_from_epub(epub_file)
            progress.update(task, completed=True)

        if not recipes:
            console.print("[yellow]⚠️  No recipes found![/yellow]")
            return

        # Save to database with progress
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            task = progress.add_task(f"Saving {len(recipes)} recipes to database...", total=None)
            db = RecipeDatabase(output)
            saved = db.save_recipes(recipes)
            progress.update(task, completed=True)

        # Success summary
        console.print()
        console.print(f"[green]✅ Successfully extracted {len(recipes)} recipes[/green]")
        console.print(f"[green]💾 Saved {saved} recipes to {output}[/green]")

        if verbose:
            for recipe in recipes[:5]:
                console.print(recipe.title, markup=False)

    except FileNotFoundError:
        console.print(f"[red]❌ Error: File not found: {epub_file}[/red]")
        sys.exit(1)
    except Exception as e:
        console.print(f"[red]❌ Error during extraction: {str(e)}[/red]")
        if verbose:
            console.print_exception()
        sys.exit(1)


@cli.command()
@click.argument("directory", type=click.Path(exists=True))
@click.option("--output", "-o", default="recipes.db", help="Output database file")
@click.option("--pattern", "-p", default="*.epub", help="File pattern to match")
@click.option("--verbose", "-v", is_flag=True, help="Show detailed processing information")
def batch(directory: str, output: str, pattern: str, verbose: bool):
    """Batch process multiple EPUB files."""
    try:
        dir_path = Path(directory)
        epub_files = list(dir_path.glob(pattern))

        if not epub_files:
            console.print(f"[yellow]⚠️  No EPUB files found in {directory}[/yellow]")
            console.print(f"[dim]Pattern: {pattern}[/dim]")
            return

        # Display batch header
        console.print()
        console.print(
            Panel.fit(
                f"[bold cyan]Batch Processing[/bold cyan]\n"
                f"Directory: {dir_path}\n"
                f"Files: {len(epub_files)}\n"
                f"Pattern: {pattern}",
                border_style="cyan",
            )
        )
        console.print()

        extractor = EPUBRecipeExtractor()
        db = RecipeDatabase(output)

        all_recipes = []
        failed_files = []

        # Process files with progress bar
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TaskProgressColumn(),
            console=console,
        ) as progress:
            task = progress.add_task(
                f"Processing {len(epub_files)} files...", total=len(epub_files)
            )

            for epub_file in epub_files:
                try:
                    progress.update(task, description=f"Processing {epub_file.name}...")

                    recipes = extractor.extract_from_epub(str(epub_file))
                    all_recipes.extend(recipes)
                    db.save_recipes(recipes)

                    if verbose:
                        console.print(
                            f"  [green]✓[/green] {epub_file.name}: {len(recipes)} recipes"
                        )

                except Exception as e:
                    failed_files.append((epub_file.name, str(e)))
                    if verbose:
                        console.print(f"  [red]✗[/red] {epub_file.name}: {str(e)}")

                progress.advance(task)

        # Summary
        console.print()
        console.print(
            f"[green]✅ Successfully processed {len(epub_files) - len(failed_files)}/{len(epub_files)} files[/green]"
        )
        console.print(f"[green]💾 Total recipes extracted: {len(all_recipes)}[/green]")
        console.print(f"[green]📁 Saved to {output}[/green]")

        if failed_files:
            console.print(f"\n[yellow]⚠️  {len(failed_files)} files failed:[/yellow]")
            for filename, error in failed_files[:5]:
                console.print(f"  [red]•[/red] {filename}: {error[:60]}...")
            if len(failed_files) > 5:
                console.print(f"  [dim]... and {len(failed_files) - 5} more[/dim]")

    except Exception as e:
        console.print(f"[red]❌ Error during batch processing: {str(e)}[/red]")
        if verbose:
            console.print_exception()
        sys.exit(1)


@cli.command()
@click.argument("epub_file", type=click.Path(exists=True))
@click.option("--verbose", "-v", is_flag=True, help="Show detailed analysis information")
def analyze(epub_file: str, verbose: bool):
    """Analyze EPUB structure and recipe patterns."""
    try:
        epub_path = Path(epub_file)

        # Display header
        console.print()
        console.print(
            Panel.fit(
                f"[bold cyan]Analyzing EPUB Structure[/bold cyan]\n" f"File: {epub_path.name}",
                border_style="cyan",
            )
        )
        console.print()

        # Analyze with progress indicator
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            task = progress.add_task("Analyzing EPUB...", total=None)
            analyzer = EPUBStructureAnalyzer()
            report = analyzer.analyze_structure(epub_file)
            progress.update(task, completed=True)

        # Display results
        console.print()
        analyzer.print_report(report)

        if verbose:
            console.print("\n[bold]Analysis Tips:[/bold]")
            console.print("  • Check header distribution to understand recipe boundaries")
            console.print("  • Multiple h2/h3 headers typically indicate recipe sections")
            console.print("  • Review pattern matches to verify extraction strategies")

    except FileNotFoundError:
        console.print(f"[red]❌ Error: File not found: {epub_file}[/red]")
        sys.exit(1)
    except Exception as e:
        console.print(f"[red]❌ Error during analysis: {str(e)}[/red]")
        if verbose:
            console.print_exception()
        sys.exit(1)


@cli.command()
@click.argument("epub_file", type=click.Path(exists=True))
@click.argument("database", type=click.Path(exists=True))
@click.option("--book", help="Exact book title to validate in a multi-book database")
def validate(epub_file: str, database: str, book: str | None):
    """Validate extraction against TOC."""
    console.print("\n[bold]✓ Validating extraction[/bold]\n")

    # Get extracted recipes from database
    db = RecipeDatabase(database)

    all_recipes = db.query(filters={"book": book}) if book else db.query()
    if not book and len({recipe.book for recipe in all_recipes}) > 1:
        raise click.UsageError("Use --book with the exact book title for a multi-book database.")

    # Validate
    toc_analyzer = TOCAnalyzer()
    report = toc_analyzer.validate_extraction(all_recipes, epub_file)

    console.print("[bold]📊 Validation Results:[/bold]")
    console.print(f"  Likely recipe entries in the TOC: {report.toc_count}")
    console.print(f"  Recipes extracted: {report.extracted_count}")
    console.print(f"  Matched: {report.matched}")
    if report.toc_count:
        console.print(f"  TOC match rate: {report.coverage*100:.1f}%")
    console.print("  Tables of contents may list only chapters or omit recipes.")

    diagnostics = (
        ("Missing chapter", [r.title for r in all_recipes if r.chapter in (None, "", "Unknown")]),
        ("Missing title", [r.epub_section or "HTML section" for r in all_recipes if
                           r.title.strip().casefold() in ("", "untitled")]),
        ("Missing instructions", [r.title for r in all_recipes if not (r.instructions or "").strip()]),
    )
    for label, entries in diagnostics:
        preview = f" ({', '.join(entries[:3])})" if entries else ""
        console.print(f"  {label}: {len(entries)}{preview}", markup=False)

    if report.missing:
        console.print(f"\n[yellow]⚠️  Unmatched TOC entries: {len(report.missing)}[/yellow]")
        for entry in report.missing[:10]:
            console.print(f"  • {entry.title}")
        if len(report.missing) > 10:
            console.print(f"  ... and {len(report.missing) - 10} more")


@cli.command()
@click.argument("database", type=click.Path(exists=True))
@click.argument("query")
@click.option("--limit", "-l", default=10, help="Maximum results")
@click.option("--tags", "-t", multiple=True, help="Filter by tags (can be used multiple times)")
def search(database: str, query: str, limit: int, tags: tuple):
    """Search recipes in database with optional tag filtering."""
    db = RecipeDatabase(database)

    # Convert tags tuple to list if provided
    tag_list = list(tags) if tags else None
    recipes = db.search(query, limit=limit, tags=tag_list)

    if not recipes:
        if tag_list:
            console.print(
                f"[yellow]No recipes found for '{query}' with tags: {', '.join(tag_list)}[/yellow]"
            )
        else:
            console.print(f"[yellow]No recipes found for '{query}'[/yellow]")
        return

    if tag_list:
        console.print(
            f"\n[bold]🔍 Found {len(recipes)} recipes for '{query}' with tags: {', '.join(tag_list)}[/bold]\n"
        )
    else:
        console.print(f"\n[bold]🔍 Found {len(recipes)} recipes for '{query}':[/bold]\n")

    table = Table(show_header=True, header_style="bold magenta")
    table.add_column("Title", style="cyan", no_wrap=False, max_width=40)
    table.add_column("Book", style="green", max_width=30)
    table.add_column("Tags", style="blue", max_width=20)

    for recipe in recipes:
        tags_str = ", ".join(recipe.tags) if recipe.tags else "-"
        table.add_row(recipe.title, recipe.book, tags_str)

    console.print(table)


@cli.command()
@click.argument("database", type=click.Path(exists=True))
@click.option(
    "--tags", "-t", multiple=True, required=True, help="Tags to filter by (required, multiple)"
)
@click.option("--limit", "-l", default=20, help="Maximum results")
@click.option(
    "--match-all", is_flag=True, help="Match ALL tags (AND logic) instead of ANY tag (OR logic)"
)
def query_tags(database: str, tags: tuple, limit: int, match_all: bool):
    """Query recipes by tags."""
    db = RecipeDatabase(database)

    tag_list = list(tags)
    recipes = db.query(tags=tag_list, tags_match_all=match_all, limit=limit)

    if not recipes:
        match_type = "all" if match_all else "any"
        console.print(
            f"[yellow]No recipes found with {match_type} of these tags: {', '.join(tag_list)}[/yellow]"
        )
        return

    match_type = "all" if match_all else "any"
    console.print(
        f"\n[bold]Found {len(recipes)} recipes with {match_type} of these tags: {', '.join(tag_list)}[/bold]\n"
    )

    table = Table(show_header=True, header_style="bold magenta")
    table.add_column("Title", style="cyan", no_wrap=False, max_width=40)
    table.add_column("Book", style="green", max_width=30)
    table.add_column("Tags", style="blue", max_width=25)

    for recipe in recipes:
        tags_str = ", ".join(recipe.tags) if recipe.tags else "-"
        table.add_row(recipe.title, recipe.book, tags_str)

    console.print(table)


@cli.command()
@click.argument("database", type=click.Path(exists=True))
def list_tags(database: str):
    """List all available tags in the database."""
    db = RecipeDatabase(database)

    # Query to get all tags with recipe counts
    with db._get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT t.tag_name, COUNT(rt.recipe_id) as recipe_count
            FROM tags t
            LEFT JOIN recipe_tags rt ON t.id = rt.tag_id
            GROUP BY t.id, t.tag_name
            ORDER BY recipe_count DESC, t.tag_name
        """
        )
        tag_data = cursor.fetchall()

    if not tag_data:
        console.print("[yellow]No tags found in database.[/yellow]")
        return

    console.print(f"\n[bold]Available Tags ({len(tag_data)} total):[/bold]\n")

    table = Table(show_header=True, header_style="bold magenta")
    table.add_column("Tag", style="cyan")
    table.add_column("Recipe Count", justify="right", style="green")

    for tag_name, count in tag_data:
        table.add_row(tag_name, str(count))

    console.print(table)


@cli.command()
@click.argument("database", type=click.Path(exists=True))
@click.option(
    "--format",
    "-f",
    type=click.Choice(["json", "markdown", "vault"], case_sensitive=False),
    default="json",
    help="Export format (json, markdown, or vault for Obsidian)",
)
@click.option("--output", "-o", help="Output file/directory path")
@click.option(
    "--organize-by",
    type=click.Choice(["book", "method", "flat"], case_sensitive=False),
    default="book",
    help="Vault organization method (book, method, or flat) - only for vault format",
)
@click.option("--verbose", "-v", is_flag=True, help="Show detailed export information")
@click.option("--append", is_flag=True, help="Add to an Obsidian vault without replacing notes")
def export(
    database: str,
    format: str,
    output: str | None,
    organize_by: str,
    verbose: bool,
    append: bool,
):
    """Export recipes from database to various formats."""
    if append and format != "vault":
        raise click.UsageError("--append requires --format vault.")
    try:
        db = RecipeDatabase(database)

        # Query recipes with progress indicator
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            task = progress.add_task("Loading recipes from database...", total=None)
            recipes = db.query()
            progress.update(task, completed=True)

        if not recipes:
            console.print("[yellow]⚠️  No recipes found to export![/yellow]")
            return

        # Determine output path
        if output is None:
            if format == "vault":
                output = "recipes-vault"
            else:
                output = f"recipes.{format}"

        output_path = Path(output)

        # Display export header
        console.print()
        if format == "vault":
            console.print(
                Panel.fit(
                    f"[bold cyan]Exporting Recipes[/bold cyan]\n"
                    f"Format: Obsidian Vault\n"
                    f"Recipes: {len(recipes)}\n"
                    f"Organization: By {organize_by}\n"
                    f"Output: {output_path.name}/",
                    border_style="cyan",
                )
            )
        else:
            console.print(
                Panel.fit(
                    f"[bold cyan]Exporting Recipes[/bold cyan]\n"
                    f"Format: {format.upper()}\n"
                    f"Recipes: {len(recipes)}\n"
                    f"Output: {output_path.name}",
                    border_style="cyan",
                )
            )
        console.print()

        # Export with progress indicator
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            task = progress.add_task(f"Exporting to {format.upper()}...", total=None)

            if format == "json":
                _export_json(recipes, output_path)
            elif format == "markdown":
                _export_markdown(recipes, output_path)
            elif format == "vault":
                exporter = ObsidianVaultExporter()
                stats = exporter.export_vault(
                    recipes, output_path, organize_by=organize_by, append=append
                )
                # Store stats for later display
                vault_stats = stats

            progress.update(task, completed=True)

        # Success message
        console.print()
        if format == "vault":
            console.print(
                f"[green]✅ Successfully exported {vault_stats['success']} recipes[/green]"
            )
            console.print(f"[green]📁 Vault directory: {output}[/green]")
            if append:
                skipped = len(recipes) - vault_stats["success"] - vault_stats["failed"]
                if skipped:
                    console.print(f"Preserved {skipped} existing recipe notes.")
            if vault_stats["failed"] > 0:
                console.print(
                    f"[yellow]⚠️  Failed to export {vault_stats['failed']} recipes[/yellow]"
                )
            if vault_stats["duplicates"] > 0:
                console.print(
                    f"[blue]ℹ️  {vault_stats['duplicates']} duplicate names resolved with filename suffixes[/blue]"
                )

            if verbose:
                console.print("\n[bold]Vault Details:[/bold]")
                console.print(f"  Organization: By {organize_by}")
                console.print(f"  Path: {output_path.absolute()}")
                console.print(f"  Files created: {vault_stats['success']}")
        else:
            file_size = output_path.stat().st_size
            size_mb = file_size / (1024 * 1024)

            console.print(f"[green]✅ Successfully exported {len(recipes)} recipes[/green]")
            console.print(f"[green]📄 Output: {output}[/green]")
            console.print(f"[green]💾 Size: {size_mb:.2f} MB[/green]")

            if verbose:
                console.print("\n[bold]Export Details:[/bold]")
                console.print(f"  Format: {format}")
                console.print(f"  Path: {output_path.absolute()}")

    except FileNotFoundError:
        console.print(f"[red]❌ Error: Database not found: {database}[/red]")
        sys.exit(1)
    except Exception as e:
        console.print(f"[red]❌ Error during export: {str(e)}[/red]")
        if verbose:
            console.print_exception()
        sys.exit(1)


@cli.command()
@click.argument("database", type=click.Path(exists=True))
def ab_report(database: str):
    """Generate A/B testing report from database.

    Analyzes recipes extracted with A/B testing enabled and compares
    the performance of old vs new extraction methods.

    \b
    ARGUMENTS:
        database: Path to SQLite database with A/B test data
    """
    try:
        db = RecipeDatabase(database)

        # Get overall statistics
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            task = progress.add_task("Analyzing A/B test data...", total=None)
            stats = db.get_ab_test_stats()
            disagreements = db.get_ab_test_disagreements()
            progress.update(task, completed=True)

        if stats["total_tests"] == 0:
            console.print("[yellow]⚠️  No A/B test data found in database[/yellow]")
            console.print(
                "[dim]Run extraction with --enable-ab-testing flag to generate test data[/dim]"
            )
            return

        # Print summary
        console.print()
        console.print(
            Panel.fit(
                "[bold cyan]A/B Testing Summary[/bold cyan]", border_style="cyan"
            )
        )
        console.print()

        console.print(f"[bold]Total recipes tested:[/bold] {stats['total_tests']}")
        console.print(f"[bold]Agreement rate:[/bold] {stats['agreement_rate']:.1f}%")
        console.print(
            f"[bold]Old method success:[/bold] {stats['old_success_rate']:.1f}%"
        )
        console.print(
            f"[bold]New method success:[/bold] {stats['new_success_rate']:.1f}%"
        )
        console.print(
            f"[bold]Average confidence:[/bold] {stats['avg_confidence']:.2f}"
        )

        # Calculate improvement
        improvement = stats["new_success_rate"] - stats["old_success_rate"]
        console.print()
        if improvement > 0:
            console.print(
                f"[green]✓ New method improves by {improvement:.1f}%[/green]"
            )
        elif improvement < 0:
            console.print(
                f"[red]✗ New method worse by {abs(improvement):.1f}%[/red]"
            )
        else:
            console.print("[yellow]= No difference in success rate[/yellow]")

        # Get disagreements
        if disagreements:
            console.print()
            console.print(
                f"[bold yellow]Disagreements ({len(disagreements)})[/bold yellow]"
            )
            console.print()

            table = Table(show_header=True, header_style="bold cyan")
            table.add_column("Title", style="cyan", width=40, no_wrap=False)
            table.add_column("Book", style="magenta", width=30, no_wrap=False)
            table.add_column("Old", justify="center", width=5)
            table.add_column("New", justify="center", width=5)
            table.add_column("Confidence", justify="right", width=10)
            table.add_column("Strategy", width=25, no_wrap=False)

            for d in disagreements[:20]:  # Show top 20
                old_icon = "✓" if d["old_success"] else "✗"
                new_icon = "✓" if d["new_success"] else "✗"

                # Color code confidence (handle NULL values)
                conf_val = d["confidence"]
                if conf_val is None:
                    conf_str = "[dim]N/A[/dim]"
                elif conf_val >= 0.7:
                    conf_str = f"[green]{conf_val:.2f}[/green]"
                elif conf_val >= 0.5:
                    conf_str = f"[yellow]{conf_val:.2f}[/yellow]"
                else:
                    conf_str = f"[red]{conf_val:.2f}[/red]"

                table.add_row(
                    d["title"][:40],
                    d["book"][:30] if d["book"] else "N/A",
                    old_icon,
                    new_icon,
                    conf_str,
                    d["strategy"] or "N/A",
                )

            console.print(table)

            if len(disagreements) > 20:
                console.print()
                console.print(
                    f"[dim]Showing top 20 of {len(disagreements)} disagreements[/dim]"
                )
        else:
            console.print()
            console.print(
                "[green]✓ Perfect agreement! Both methods produced identical results.[/green]"
            )

        console.print()

    except FileNotFoundError:
        console.print(f"[red]❌ Error: Database not found: {database}[/red]")
        sys.exit(1)
    except Exception as e:
        console.print(f"[red]❌ Error generating report: {str(e)}[/red]")
        console.print_exception()
        sys.exit(1)


def _export_json(recipes: list, output_path: Path) -> None:
    """Export recipes to JSON format."""
    data = {
        "metadata": {"count": len(recipes), "format_version": "1.0"},
        "recipes": [recipe.to_dict() for recipe in recipes],
    }

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def _export_markdown(recipes: list, output_path: Path) -> None:
    """Export recipes to Markdown format."""
    with open(output_path, "w", encoding="utf-8") as f:
        f.write("# Recipe Collection\n\n")
        f.write(f"Total Recipes: {len(recipes)}\n\n")
        f.write("---\n\n")

        for i, recipe in enumerate(recipes, 1):
            f.write(f"## {i}. {recipe.title}\n\n")

            if recipe.author:
                f.write(f"**Author:** {recipe.author}\n\n")
            if recipe.book:
                f.write(f"**Book:** {recipe.book}\n\n")
            if recipe.chapter:
                f.write(f"**Chapter:** {recipe.chapter}\n\n")

            # Metadata
            metadata_parts = []
            if recipe.serves:
                metadata_parts.append(f"Serves: {recipe.serves}")
            if recipe.prep_time:
                metadata_parts.append(f"Prep Time: {recipe.prep_time}")
            if recipe.cook_time:
                metadata_parts.append(f"Cook Time: {recipe.cook_time}")

            if metadata_parts:
                f.write(f"**{' | '.join(metadata_parts)}**\n\n")

            # Ingredients
            if recipe.ingredients:
                f.write("### Ingredients\n\n")
                f.write(recipe.ingredients)
                f.write("\n\n")

            # Instructions
            if recipe.instructions:
                f.write("### Instructions\n\n")
                f.write(recipe.instructions)
                f.write("\n\n")

            # Notes
            if recipe.notes:
                f.write("### Notes\n\n")
                f.write(recipe.notes)
                f.write("\n\n")

            f.write("---\n\n")


if __name__ == "__main__":
    cli()
