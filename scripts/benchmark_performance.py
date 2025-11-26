#!/usr/bin/env python3
"""Benchmark script to measure EPUB processing performance."""

import time
import sys
from pathlib import Path
from typing import Dict, Any
import cProfile
import pstats
import io

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent / "src"))

from epub_recipe_parser.core import EPUBRecipeExtractor, ExtractorConfig


def profile_extraction(epub_path: Path) -> Dict[str, Any]:
    """Profile a single EPUB extraction."""
    # Create profiler
    profiler = cProfile.Profile()

    # Time the extraction
    start_time = time.perf_counter()

    # Profile the extraction
    profiler.enable()
    config = ExtractorConfig(min_quality_score=20)
    extractor = EPUBRecipeExtractor(config=config)
    recipes = extractor.extract_from_epub(epub_path)
    profiler.disable()

    end_time = time.perf_counter()
    elapsed = end_time - start_time

    # Get profiling stats
    s = io.StringIO()
    ps = pstats.Stats(profiler, stream=s).sort_stats("cumulative")
    ps.print_stats(20)  # Top 20 functions

    return {
        "epub_file": epub_path.name,
        "recipes_extracted": len(recipes),
        "elapsed_time": elapsed,
        "recipes_per_second": len(recipes) / elapsed if elapsed > 0 else 0,
        "profiling_stats": s.getvalue(),
    }


def benchmark_single_file(epub_path: Path, runs: int = 3) -> None:
    """Benchmark a single EPUB file multiple times."""
    print(f"\n{'='*80}")
    print(f"BENCHMARKING: {epub_path.name}")
    print(f"{'='*80}\n")

    if not epub_path.exists():
        print(f"ERROR: File not found: {epub_path}")
        return

    results = []
    for i in range(runs):
        print(f"Run {i+1}/{runs}...")
        result = profile_extraction(epub_path)
        results.append(result)
        print(f"  Time: {result['elapsed_time']:.2f}s, Recipes: {result['recipes_extracted']}")

    # Calculate statistics
    times = [r["elapsed_time"] for r in results]
    avg_time = sum(times) / len(times)
    min_time = min(times)
    max_time = max(times)

    recipes = results[0]["recipes_extracted"]

    print(f"\n{'='*80}")
    print("RESULTS")
    print(f"{'='*80}")
    print(f"Recipes extracted: {recipes}")
    print(f"Average time: {avg_time:.2f}s")
    print(f"Min time: {min_time:.2f}s")
    print(f"Max time: {max_time:.2f}s")
    print(f"Throughput: {recipes/avg_time:.2f} recipes/second")

    # Show profiling stats from first run
    print(f"\n{'='*80}")
    print("PROFILING (Top 20 functions by cumulative time)")
    print(f"{'='*80}")
    print(results[0]["profiling_stats"])


def benchmark_batch(directory: Path) -> None:
    """Benchmark batch processing of multiple EPUB files."""
    epub_files = list(directory.glob("*.epub"))

    if not epub_files:
        print(f"No EPUB files found in {directory}")
        return

    print(f"\n{'='*80}")
    print(f"BATCH BENCHMARK: {len(epub_files)} files in {directory}")
    print(f"{'='*80}\n")

    # Sequential processing (current implementation)
    print("Processing files sequentially (current implementation)...")
    start_time = time.perf_counter()

    config = ExtractorConfig(min_quality_score=20)
    extractor = EPUBRecipeExtractor(config=config)

    total_recipes = 0
    for epub_file in epub_files:
        recipes = extractor.extract_from_epub(epub_file)
        total_recipes += len(recipes)

    end_time = time.perf_counter()
    elapsed = end_time - start_time

    print(f"\n{'='*80}")
    print("BATCH RESULTS")
    print(f"{'='*80}")
    print(f"Files processed: {len(epub_files)}")
    print(f"Total recipes: {total_recipes}")
    print(f"Total time: {elapsed:.2f}s")
    print(f"Average per file: {elapsed/len(epub_files):.2f}s")
    print(f"Throughput: {total_recipes/elapsed:.2f} recipes/second")


def analyze_bottlenecks(epub_path: Path) -> None:
    """Detailed analysis of bottlenecks in the extraction process."""
    print(f"\n{'='*80}")
    print(f"BOTTLENECK ANALYSIS: {epub_path.name}")
    print(f"{'='*80}\n")

    if not epub_path.exists():
        print(f"ERROR: File not found: {epub_path}")
        return

    # Profile with detailed stats
    profiler = cProfile.Profile()

    config = ExtractorConfig(min_quality_score=20)
    extractor = EPUBRecipeExtractor(config=config)

    profiler.enable()
    recipes = extractor.extract_from_epub(epub_path)
    profiler.disable()

    # Detailed stats
    s = io.StringIO()
    ps = pstats.Stats(profiler, stream=s)

    print("Top 30 functions by cumulative time:")
    print("-" * 80)
    ps.sort_stats("cumulative").print_stats(30)

    print("\n" + "=" * 80)
    print("Top 30 functions by total time:")
    print("-" * 80)
    ps.sort_stats("tottime").print_stats(30)

    print(f"\nTotal recipes extracted: {len(recipes)}")


def main():
    """Main benchmark runner."""
    import argparse

    parser = argparse.ArgumentParser(description="Benchmark EPUB Recipe Parser")
    parser.add_argument("path", help="EPUB file or directory to benchmark")
    parser.add_argument("--runs", type=int, default=3, help="Number of runs for single file")
    parser.add_argument("--batch", action="store_true", help="Run batch benchmark")
    parser.add_argument("--analyze", action="store_true", help="Run detailed bottleneck analysis")

    args = parser.parse_args()

    path = Path(args.path)

    if not path.exists():
        print(f"ERROR: Path not found: {path}")
        sys.exit(1)

    if args.analyze:
        if path.is_file():
            analyze_bottlenecks(path)
        else:
            print("ERROR: --analyze requires a single EPUB file")
            sys.exit(1)
    elif args.batch or path.is_dir():
        benchmark_batch(path)
    else:
        benchmark_single_file(path, runs=args.runs)


if __name__ == "__main__":
    main()
