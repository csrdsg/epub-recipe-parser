#!/usr/bin/env python3
"""
Example implementation of parallel batch processing for EPUB Recipe Parser.

This is a standalone example showing how to add multiprocessing to the batch command.
Copy the relevant parts to src/epub_recipe_parser/cli/main.py to integrate.

Usage:
    python multiprocessing_implementation.py /path/to/cookbooks/ --workers 4
"""

import sys
from pathlib import Path
from typing import List, Tuple, Optional
from concurrent.futures import ProcessPoolExecutor, as_completed
import multiprocessing
import time

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent / "src"))

from epub_recipe_parser.core import EPUBRecipeExtractor, ExtractorConfig, Recipe
from epub_recipe_parser.storage import RecipeDatabase


def process_epub_worker(
    epub_path: Path, min_quality: int
) -> Tuple[Path, List[Recipe], Optional[Exception]]:
    """
    Worker function to process a single EPUB file in a separate process.

    Args:
        epub_path: Path to the EPUB file
        min_quality: Minimum quality score for recipes

    Returns:
        Tuple of (epub_path, recipes, error)
        - epub_path: The input file path (for tracking)
        - recipes: List of extracted recipes
        - error: Exception if processing failed, None if successful
    """
    try:
        # Create extractor in this process
        config = ExtractorConfig(min_quality_score=min_quality)
        extractor = EPUBRecipeExtractor(config=config)

        # Extract recipes
        recipes = extractor.extract_from_epub(epub_path)

        return (epub_path, recipes, None)

    except Exception as e:
        # Return error instead of crashing the worker
        return (epub_path, [], e)


def batch_process_sequential(epub_files: List[Path], output: str, min_quality: int) -> dict:
    """
    Process EPUB files sequentially (current implementation).

    Args:
        epub_files: List of EPUB file paths
        output: Database output path
        min_quality: Minimum quality score

    Returns:
        Dictionary with results
    """
    print(f"\nProcessing {len(epub_files)} files sequentially...")
    start_time = time.perf_counter()

    config = ExtractorConfig(min_quality_score=min_quality)
    extractor = EPUBRecipeExtractor(config=config)
    db = RecipeDatabase(output)

    all_recipes = []
    errors = []

    for i, epub_file in enumerate(epub_files, 1):
        try:
            print(f"[{i}/{len(epub_files)}] Processing {epub_file.name}...", end=" ")
            recipes = extractor.extract_from_epub(epub_file)
            all_recipes.extend(recipes)
            db.save_recipes(recipes)
            print(f"✅ {len(recipes)} recipes")
        except Exception as e:
            print(f"❌ Error: {e}")
            errors.append((epub_file, e))

    elapsed = time.perf_counter() - start_time

    return {
        "total_recipes": len(all_recipes),
        "errors": errors,
        "elapsed_time": elapsed,
        "files_processed": len(epub_files),
    }


def batch_process_parallel(
    epub_files: List[Path], output: str, min_quality: int, max_workers: Optional[int] = None
) -> dict:
    """
    Process EPUB files in parallel using multiprocessing.

    Args:
        epub_files: List of EPUB file paths
        output: Database output path
        min_quality: Minimum quality score
        max_workers: Number of worker processes (None = auto-detect)

    Returns:
        Dictionary with results
    """
    # Determine number of workers
    if max_workers is None:
        # Auto-detect: use CPU count, but cap at number of files
        max_workers = min(multiprocessing.cpu_count(), len(epub_files))

    print(f"\nProcessing {len(epub_files)} files with {max_workers} parallel workers...")
    start_time = time.perf_counter()

    db = RecipeDatabase(output)
    all_recipes = []
    errors = []

    # Create process pool and submit all jobs
    with ProcessPoolExecutor(max_workers=max_workers) as executor:
        # Submit all EPUB files for processing
        future_to_epub = {
            executor.submit(process_epub_worker, epub_file, min_quality): epub_file
            for epub_file in epub_files
        }

        # Collect results as they complete
        completed = 0
        for future in as_completed(future_to_epub):
            epub_file = future_to_epub[future]
            completed += 1

            # Get result from worker
            epub_path, recipes, error = future.result()

            if error:
                print(f"[{completed}/{len(epub_files)}] ❌ {epub_file.name}: {error}")
                errors.append((epub_file, error))
            else:
                print(
                    f"[{completed}/{len(epub_files)}] ✅ {epub_file.name}: {len(recipes)} recipes"
                )
                all_recipes.extend(recipes)

                # Save to database (thread-safe for SQLite with single writer)
                try:
                    db.save_recipes(recipes)
                except Exception as e:
                    print(f"  ⚠️  Database save error: {e}")

    elapsed = time.perf_counter() - start_time

    return {
        "total_recipes": len(all_recipes),
        "errors": errors,
        "elapsed_time": elapsed,
        "files_processed": len(epub_files),
    }


def print_results(results: dict, method: str):
    """Print processing results."""
    print(f"\n{'='*60}")
    print(f"RESULTS ({method})")
    print(f"{'='*60}")
    print(f"Files processed:  {results['files_processed']}")
    print(f"Total recipes:    {results['total_recipes']}")
    print(f"Errors:           {len(results['errors'])}")
    print(f"Time elapsed:     {results['elapsed_time']:.2f} seconds")
    print(f"Throughput:       {results['total_recipes']/results['elapsed_time']:.2f} recipes/sec")

    if results["errors"]:
        print("\nErrors:")
        for epub_file, error in results["errors"]:
            print(f"  • {epub_file.name}: {error}")


def compare_sequential_vs_parallel(directory: Path, min_quality: int = 20):
    """
    Compare sequential vs parallel processing on the same files.

    This is useful for benchmarking and demonstrating the speedup.
    """
    epub_files = list(directory.glob("*.epub"))

    if not epub_files:
        print(f"No EPUB files found in {directory}")
        return

    print("Comparing sequential vs parallel processing")
    print(f"Directory: {directory}")
    print(f"Files: {len(epub_files)}")

    # Sequential processing
    output_seq = "recipes_sequential.db"
    results_seq = batch_process_sequential(epub_files, output_seq, min_quality)
    print_results(results_seq, "Sequential")

    # Parallel processing (auto-detect workers)
    output_par = "recipes_parallel.db"
    results_par = batch_process_parallel(epub_files, output_par, min_quality)
    print_results(results_par, "Parallel")

    # Comparison
    speedup = results_seq["elapsed_time"] / results_par["elapsed_time"]
    print(f"\n{'='*60}")
    print("COMPARISON")
    print(f"{'='*60}")
    print(f"Speedup:          {speedup:.2f}x")
    print(
        f"Time saved:       {results_seq['elapsed_time'] - results_par['elapsed_time']:.2f} seconds"
    )

    if speedup > 2:
        print("✅ Excellent speedup! Multiprocessing is very effective.")
    elif speedup > 1.5:
        print("✅ Good speedup. Multiprocessing is worthwhile.")
    elif speedup > 1.2:
        print("⚠️  Modest speedup. May or may not be worth the complexity.")
    else:
        print("❌ Minimal speedup. Sequential processing is sufficient.")


def main():
    """Main entry point for demonstration."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Parallel EPUB Recipe Parser - Demonstration & Benchmark"
    )
    parser.add_argument("directory", help="Directory containing EPUB files")
    parser.add_argument("--output", "-o", default="recipes.db", help="Output database file")
    parser.add_argument(
        "--min-quality", "-q", type=int, default=20, help="Minimum quality score (0-100)"
    )
    parser.add_argument(
        "--workers", "-w", type=int, default=None, help="Number of parallel workers (default: auto)"
    )
    parser.add_argument("--sequential", action="store_true", help="Use sequential processing")
    parser.add_argument("--compare", action="store_true", help="Compare sequential vs parallel")

    args = parser.parse_args()

    directory = Path(args.directory)
    if not directory.exists():
        print(f"Error: Directory not found: {directory}")
        sys.exit(1)

    epub_files = list(directory.glob("*.epub"))
    if not epub_files:
        print(f"No EPUB files found in {directory}")
        sys.exit(1)

    if args.compare:
        # Benchmark mode: compare both approaches
        compare_sequential_vs_parallel(directory, args.min_quality)
    elif args.sequential:
        # Sequential mode
        results = batch_process_sequential(epub_files, args.output, args.min_quality)
        print_results(results, "Sequential")
    else:
        # Parallel mode (default)
        results = batch_process_parallel(epub_files, args.output, args.min_quality, args.workers)
        print_results(results, "Parallel")


if __name__ == "__main__":
    main()


# =============================================================================
# INTEGRATION GUIDE
# =============================================================================
"""
To integrate this into the main CLI (src/epub_recipe_parser/cli/main.py):

1. Copy the `process_epub_worker()` function to the top of main.py

2. Replace the batch command with this improved version:

    @cli.command()
    @click.argument("directory", type=click.Path(exists=True))
    @click.option("--output", "-o", default="recipes.db", help="Output database file")
    @click.option("--min-quality", "-q", default=20, help="Minimum quality score (0-100)")
    @click.option("--pattern", "-p", default="*.epub", help="File pattern to match")
    @click.option("--workers", "-w", type=int, default=None, help="Number of parallel workers (default: auto)")
    @click.option("--sequential", is_flag=True, help="Process files sequentially")
    def batch(directory: str, output: str, min_quality: int, pattern: str, workers: int | None, sequential: bool):
        '''Batch process multiple EPUB files.'''
        dir_path = Path(directory)
        epub_files = list(dir_path.glob(pattern))

        if not epub_files:
            console.print(f"[yellow]No EPUB files found in {directory}[/yellow]")
            return

        # Determine processing mode
        if sequential:
            max_workers = 1
        elif workers is not None:
            max_workers = max(1, workers)
        else:
            max_workers = min(multiprocessing.cpu_count(), len(epub_files))

        console.print(f"\\n[bold]🔥 Batch processing {len(epub_files)} files[/bold]")
        if max_workers > 1:
            console.print(f"[bold]⚙️  Using {max_workers} parallel workers[/bold]\\n")
        else:
            console.print(f"[bold]⚙️  Processing sequentially[/bold]\\n")

        db = RecipeDatabase(output)
        all_recipes = []
        errors = []

        if max_workers == 1:
            # Sequential processing
            config = ExtractorConfig(min_quality_score=min_quality)
            extractor = EPUBRecipeExtractor(config=config)

            for epub_file in epub_files:
                try:
                    recipes = extractor.extract_from_epub(epub_file)
                    all_recipes.extend(recipes)
                    db.save_recipes(recipes)
                except Exception as e:
                    console.print(f"[red]❌ Error processing {epub_file.name}: {e}[/red]")
                    errors.append((epub_file, e))
        else:
            # Parallel processing
            with ProcessPoolExecutor(max_workers=max_workers) as executor:
                future_to_epub = {
                    executor.submit(process_epub_worker, epub_file, min_quality): epub_file
                    for epub_file in epub_files
                }

                for future in as_completed(future_to_epub):
                    epub_file = future_to_epub[future]
                    epub_path, recipes, error = future.result()

                    if error:
                        console.print(f"[red]❌ {epub_file.name}: {error}[/red]")
                        errors.append((epub_file, error))
                    else:
                        all_recipes.extend(recipes)
                        db.save_recipes(recipes)
                        console.print(f"[green]✅ {epub_file.name}: {len(recipes)} recipes[/green]")

        # Summary
        console.print(f"\\n[green]✅ Total recipes extracted: {len(all_recipes)}[/green]")
        console.print(f"[green]💾 Saved to {output}[/green]")

        if errors:
            console.print(f"\\n[yellow]⚠️  {len(errors)} files had errors[/yellow]")

3. Add these imports at the top of main.py:
    from concurrent.futures import ProcessPoolExecutor, as_completed
    import multiprocessing

4. Test the new batch command:
    epub-parser batch ./cookbooks/ -o recipes.db --workers 4
    epub-parser batch ./cookbooks/ -o recipes.db --sequential  # For comparison
"""
