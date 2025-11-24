"""Main CLI entry point."""

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

    console.print(f"\n[bold]📊 Quality Stats:[/bold]")
    console.print(f"  Average score: {avg_score:.1f}")
    console.print(
        f"  Excellent (70+): {excellent} ({excellent*100/len(recipes):.1f}%)"
    )


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
    console.print(f"\n[bold]✓ Validating extraction[/bold]\n")

    # Get extracted recipes from database
    db = RecipeDatabase(database)

    # Get book name from epub file
    epub_path = Path(epub_file)

    # Query all recipes (we'll filter by book if needed)
    all_recipes = db.query()

    # Validate
    toc_analyzer = TOCAnalyzer()
    report = toc_analyzer.validate_extraction(all_recipes, epub_file)

    console.print(f"[bold]📊 Validation Results:[/bold]")
    console.print(f"  TOC entries: {report.toc_count}")
    console.print(f"  Recipes extracted: {report.extracted_count}")
    console.print(f"  Matched: {report.matched}")
    console.print(
        f"  Coverage: {report.coverage*100:.1f}%"
    )

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
def search(database: str, query: str, limit: int):
    """Search recipes in database."""
    db = RecipeDatabase(database)
    recipes = db.search(query, limit=limit)

    if not recipes:
        console.print(f"[yellow]No recipes found for '{query}'[/yellow]")
        return

    console.print(f"\n[bold]🔍 Found {len(recipes)} recipes for '{query}':[/bold]\n")

    table = Table(show_header=True, header_style="bold magenta")
    table.add_column("Title", style="cyan", no_wrap=False, max_width=40)
    table.add_column("Book", style="green", max_width=30)
    table.add_column("Score", justify="right", style="yellow")

    for recipe in recipes:
        table.add_row(recipe.title, recipe.book, str(recipe.quality_score))

    console.print(table)


if __name__ == "__main__":
    cli()
