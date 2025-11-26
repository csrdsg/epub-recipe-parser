"""Main CLI entry point."""

import json
import click
from pathlib import Path
from rich.console import Console
from rich.table import Table

from epub_recipe_parser.core import EPUBRecipeExtractor, ExtractorConfig
from epub_recipe_parser.storage import RecipeDatabase
from epub_recipe_parser.analyzers import TOCAnalyzer, EPUBStructureAnalyzer

console = Console()


@click.group()
@click.version_option(version="0.1.0")
def cli():
    """EPUB Recipe Parser - Extract recipes from EPUB cookbooks."""
    pass


@cli.command()
@click.argument("epub_file", type=click.Path(exists=True))
@click.option("--output", "-o", default="recipes.db", help="Output database file")
@click.option("--min-quality", "-q", default=20, help="Minimum quality score (0-100)")
def extract(epub_file: str, output: str, min_quality: int):
    """Extract recipes from an EPUB file."""
    console.print(f"\n[bold]🔥 Extracting recipes from {epub_file}[/bold]\n")

    config = ExtractorConfig(min_quality_score=min_quality)
    extractor = EPUBRecipeExtractor(config=config)

    recipes = extractor.extract_from_epub(epub_file)

    if not recipes:
        console.print("[yellow]No recipes found![/yellow]")
        return

    # Save to database
    db = RecipeDatabase(output)
    saved = db.save_recipes(recipes)

    console.print(f"\n[green]✅ Extracted {len(recipes)} recipes[/green]")
    console.print(f"[green]💾 Saved {saved} recipes to {output}[/green]")

    # Show quality distribution
    quality_scores = [r.quality_score for r in recipes]
    avg_score = sum(quality_scores) / len(quality_scores)
    excellent = len([s for s in quality_scores if s >= 70])

    console.print("\n[bold]📊 Quality Stats:[/bold]")
    console.print(f"  Average score: {avg_score:.1f}")
    console.print(f"  Excellent (70+): {excellent} ({excellent*100/len(recipes):.1f}%)")


@cli.command()
@click.argument("directory", type=click.Path(exists=True))
@click.option("--output", "-o", default="recipes.db", help="Output database file")
@click.option("--min-quality", "-q", default=20, help="Minimum quality score (0-100)")
@click.option("--pattern", "-p", default="*.epub", help="File pattern to match")
def batch(directory: str, output: str, min_quality: int, pattern: str):
    """Batch process multiple EPUB files."""
    dir_path = Path(directory)
    epub_files = list(dir_path.glob(pattern))

    if not epub_files:
        console.print(f"[yellow]No EPUB files found in {directory}[/yellow]")
        return

    console.print(f"\n[bold]🔥 Batch processing {len(epub_files)} files[/bold]\n")

    config = ExtractorConfig(min_quality_score=min_quality)
    extractor = EPUBRecipeExtractor(config=config)
    db = RecipeDatabase(output)

    all_recipes = []
    for epub_file in epub_files:
        recipes = extractor.extract_from_epub(epub_file)
        all_recipes.extend(recipes)
        db.save_recipes(recipes)

    console.print(f"\n[green]✅ Total recipes extracted: {len(all_recipes)}[/green]")
    console.print(f"[green]💾 Saved to {output}[/green]")


@cli.command()
@click.argument("epub_file", type=click.Path(exists=True))
def analyze(epub_file: str):
    """Analyze EPUB structure."""
    console.print(f"\n[bold]🔍 Analyzing {epub_file}[/bold]\n")

    analyzer = EPUBStructureAnalyzer()
    report = analyzer.analyze_structure(epub_file)
    analyzer.print_report(report)


@cli.command()
@click.argument("epub_file", type=click.Path(exists=True))
@click.argument("database", type=click.Path(exists=True))
def validate(epub_file: str, database: str):
    """Validate extraction against TOC."""
    console.print("\n[bold]✓ Validating extraction[/bold]\n")

    # Get extracted recipes from database
    db = RecipeDatabase(database)

    # Query all recipes (we'll filter by book if needed)
    all_recipes = db.query()

    # Validate
    toc_analyzer = TOCAnalyzer()
    report = toc_analyzer.validate_extraction(all_recipes, epub_file)

    console.print("[bold]📊 Validation Results:[/bold]")
    console.print(f"  TOC entries: {report.toc_count}")
    console.print(f"  Recipes extracted: {report.extracted_count}")
    console.print(f"  Matched: {report.matched}")
    console.print(f"  Coverage: {report.coverage*100:.1f}%")

    if report.missing:
        console.print(f"\n[yellow]⚠️  Missing {len(report.missing)} recipes:[/yellow]")
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
    table.add_column("Score", justify="right", style="yellow")

    for recipe in recipes:
        tags_str = ", ".join(recipe.tags) if recipe.tags else "-"
        table.add_row(recipe.title, recipe.book, tags_str, str(recipe.quality_score))

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
    table.add_column("Score", justify="right", style="yellow")

    for recipe in recipes:
        tags_str = ", ".join(recipe.tags) if recipe.tags else "-"
        table.add_row(recipe.title, recipe.book, tags_str, str(recipe.quality_score))

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
    type=click.Choice(["json", "markdown"], case_sensitive=False),
    default="json",
    help="Export format",
)
@click.option("--output", "-o", help="Output file path")
@click.option("--min-quality", "-q", type=int, help="Minimum quality score filter")
def export(database: str, format: str, output: str | None, min_quality: int | None):
    """Export recipes from database to various formats."""
    db = RecipeDatabase(database)

    # Query recipes with optional quality filter
    if min_quality is not None:
        recipes = db.query(min_quality=min_quality)
    else:
        recipes = db.query()

    if not recipes:
        console.print("[yellow]No recipes found to export![/yellow]")
        return

    # Determine output file
    if output is None:
        output = f"recipes.{format}"

    output_path = Path(output)

    # Export based on format
    if format == "json":
        _export_json(recipes, output_path)
    elif format == "markdown":
        _export_markdown(recipes, output_path)

    console.print(f"\n[green]✅ Exported {len(recipes)} recipes to {output}[/green]")


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

            # Quality score
            f.write(f"*Quality Score: {recipe.quality_score}/100*\n\n")

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
