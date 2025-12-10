#!/usr/bin/env python3
"""Performance benchmarking for old vs new extraction methods.

Compares execution time and extraction quality between legacy and pattern-based methods.
"""

import time
import sys
from pathlib import Path
from typing import List, Tuple
from dataclasses import dataclass
from bs4 import BeautifulSoup

from epub_recipe_parser.extractors.ingredients import IngredientsExtractor
from epub_recipe_parser.extractors.instructions import InstructionsExtractor
from epub_recipe_parser.extractors.metadata import MetadataExtractor


@dataclass
class BenchmarkResult:
    """Results from a single benchmark run."""
    method: str
    component: str
    execution_time: float
    success_count: int
    total_count: int
    avg_confidence: float = 0.0
    avg_linguistic_score: float = 0.0
    avg_combined_score: float = 0.0


class PerformanceBenchmark:
    """Benchmarks extraction performance."""

    def __init__(self, epub_path: str):
        self.epub_path = epub_path
        self.results: List[BenchmarkResult] = []

    def benchmark_ingredients(self, iterations: int = 3) -> Tuple[BenchmarkResult, BenchmarkResult]:
        """Benchmark ingredient extraction."""
        print("\n" + "=" * 70)
        print("Benchmarking Ingredient Extraction")
        print("=" * 70)

        # Load EPUB once
        from ebooklib import epub
        book = epub.read_epub(self.epub_path)
        html_docs = [
            item for item in book.get_items()
            if item.get_type() == 9  # ITEM_DOCUMENT
        ]

        # Prepare test sections
        test_sections = []
        for doc in html_docs[:50]:  # Test first 50 documents
            html_content = doc.get_content().decode('utf-8', errors='ignore')
            soup = BeautifulSoup(html_content, 'html.parser')
            text = soup.get_text()
            test_sections.append((soup, text))

        print(f"Testing with {len(test_sections)} HTML sections")
        print(f"Running {iterations} iterations per method...\n")

        # Benchmark legacy method
        print("[1/2] Benchmarking legacy extract()...")
        legacy_times = []
        legacy_successes = 0

        for i in range(iterations):
            start = time.perf_counter()
            for soup, text in test_sections:
                result = IngredientsExtractor.extract(soup, text)
                if result:
                    legacy_successes += 1
            end = time.perf_counter()
            legacy_times.append(end - start)
            print(f"  Iteration {i+1}: {legacy_times[-1]:.3f}s")

        legacy_avg = sum(legacy_times) / len(legacy_times)
        legacy_success_rate = legacy_successes / (len(test_sections) * iterations)

        # Benchmark pattern-based method
        print("\n[2/2] Benchmarking pattern-based extract_with_patterns()...")
        pattern_times = []
        pattern_successes = 0
        confidences = []
        linguistic_scores = []
        combined_scores = []

        for i in range(iterations):
            start = time.perf_counter()
            for soup, text in test_sections:
                result, analysis = IngredientsExtractor.extract_with_patterns(soup, text)
                if result:
                    pattern_successes += 1
                    confidences.append(analysis.get('confidence', 0.0))
                    linguistic_scores.append(analysis.get('linguistic_score', 0.0))
                    combined_scores.append(analysis.get('combined_score', 0.0))
            end = time.perf_counter()
            pattern_times.append(end - start)
            print(f"  Iteration {i+1}: {pattern_times[-1]:.3f}s")

        pattern_avg = sum(pattern_times) / len(pattern_times)
        pattern_success_rate = pattern_successes / (len(test_sections) * iterations)

        # Calculate statistics
        avg_confidence = sum(confidences) / len(confidences) if confidences else 0.0
        avg_linguistic = sum(linguistic_scores) / len(linguistic_scores) if linguistic_scores else 0.0
        avg_combined = sum(combined_scores) / len(combined_scores) if combined_scores else 0.0

        # Create results
        legacy_result = BenchmarkResult(
            method="legacy",
            component="ingredients",
            execution_time=legacy_avg,
            success_count=int(legacy_successes / iterations),
            total_count=len(test_sections)
        )

        pattern_result = BenchmarkResult(
            method="pattern",
            component="ingredients",
            execution_time=pattern_avg,
            success_count=int(pattern_successes / iterations),
            total_count=len(test_sections),
            avg_confidence=avg_confidence,
            avg_linguistic_score=avg_linguistic,
            avg_combined_score=avg_combined
        )

        # Report results
        print("\n" + "-" * 70)
        print("Results:")
        print("-" * 70)
        print("Legacy extract():")
        print(f"  Avg time: {legacy_avg:.3f}s")
        print(f"  Success rate: {legacy_success_rate:.1%}")
        print(f"  Successes: {legacy_result.success_count}/{legacy_result.total_count}")

        print("\nPattern-based extract_with_patterns():")
        print(f"  Avg time: {pattern_avg:.3f}s")
        print(f"  Success rate: {pattern_success_rate:.1%}")
        print(f"  Successes: {pattern_result.success_count}/{pattern_result.total_count}")
        print(f"  Avg confidence: {avg_confidence:.2f}")
        print(f"  Avg linguistic: {avg_linguistic:.2f}")
        print(f"  Avg combined: {avg_combined:.2f}")

        # Performance comparison
        speedup = legacy_avg / pattern_avg if pattern_avg > 0 else 0
        overhead = ((pattern_avg - legacy_avg) / legacy_avg * 100) if legacy_avg > 0 else 0

        print("\nPerformance comparison:")
        if speedup > 1:
            print(f"  Pattern method is {speedup:.2f}x FASTER")
        else:
            print(f"  Pattern method has {overhead:+.1f}% overhead")

        self.results.extend([legacy_result, pattern_result])
        return legacy_result, pattern_result

    def benchmark_instructions(self, iterations: int = 3) -> Tuple[BenchmarkResult, BenchmarkResult]:
        """Benchmark instruction extraction."""
        print("\n" + "=" * 70)
        print("Benchmarking Instruction Extraction")
        print("=" * 70)

        # Load EPUB once
        from ebooklib import epub
        book = epub.read_epub(self.epub_path)
        html_docs = [
            item for item in book.get_items()
            if item.get_type() == 9  # ITEM_DOCUMENT
        ]

        # Prepare test sections
        test_sections = []
        for doc in html_docs[:50]:  # Test first 50 documents
            html_content = doc.get_content().decode('utf-8', errors='ignore')
            soup = BeautifulSoup(html_content, 'html.parser')
            text = soup.get_text()
            test_sections.append((soup, text))

        print(f"Testing with {len(test_sections)} HTML sections")
        print(f"Running {iterations} iterations per method...\n")

        # Benchmark legacy method
        print("[1/2] Benchmarking legacy extract()...")
        legacy_times = []
        legacy_successes = 0

        for i in range(iterations):
            start = time.perf_counter()
            for soup, text in test_sections:
                result = InstructionsExtractor.extract(soup, text)
                if result:
                    legacy_successes += 1
            end = time.perf_counter()
            legacy_times.append(end - start)
            print(f"  Iteration {i+1}: {legacy_times[-1]:.3f}s")

        legacy_avg = sum(legacy_times) / len(legacy_times)

        # Benchmark pattern-based method
        print("\n[2/2] Benchmarking pattern-based extract_with_patterns()...")
        pattern_times = []
        pattern_successes = 0
        confidences = []
        linguistic_scores = []

        for i in range(iterations):
            start = time.perf_counter()
            for soup, text in test_sections:
                result, analysis = InstructionsExtractor.extract_with_patterns(soup, text)
                if result:
                    pattern_successes += 1
                    confidences.append(analysis.get('confidence', 0.0))
                    linguistic_scores.append(analysis.get('linguistic_score', 0.0))
            end = time.perf_counter()
            pattern_times.append(end - start)
            print(f"  Iteration {i+1}: {pattern_times[-1]:.3f}s")

        pattern_avg = sum(pattern_times) / len(pattern_times)

        # Calculate statistics
        avg_confidence = sum(confidences) / len(confidences) if confidences else 0.0
        avg_linguistic = sum(linguistic_scores) / len(linguistic_scores) if linguistic_scores else 0.0

        # Create results
        legacy_result = BenchmarkResult(
            method="legacy",
            component="instructions",
            execution_time=legacy_avg,
            success_count=int(legacy_successes / iterations),
            total_count=len(test_sections)
        )

        pattern_result = BenchmarkResult(
            method="pattern",
            component="instructions",
            execution_time=pattern_avg,
            success_count=int(pattern_successes / iterations),
            total_count=len(test_sections),
            avg_confidence=avg_confidence,
            avg_linguistic_score=avg_linguistic
        )

        # Report results
        print("\n" + "-" * 70)
        print("Results:")
        print("-" * 70)
        print(f"Legacy extract(): {legacy_avg:.3f}s")
        print(f"Pattern-based extract_with_patterns(): {pattern_avg:.3f}s")

        speedup = legacy_avg / pattern_avg if pattern_avg > 0 else 0
        overhead = ((pattern_avg - legacy_avg) / legacy_avg * 100) if legacy_avg > 0 else 0

        print("\nPerformance comparison:")
        if speedup > 1:
            print(f"  Pattern method is {speedup:.2f}x FASTER")
        else:
            print(f"  Pattern method has {overhead:+.1f}% overhead")

        self.results.extend([legacy_result, pattern_result])
        return legacy_result, pattern_result

    def benchmark_metadata(self, iterations: int = 3) -> Tuple[BenchmarkResult, BenchmarkResult]:
        """Benchmark metadata extraction."""
        print("\n" + "=" * 70)
        print("Benchmarking Metadata Extraction")
        print("=" * 70)

        # Load EPUB once
        from ebooklib import epub
        book = epub.read_epub(self.epub_path)
        html_docs = [
            item for item in book.get_items()
            if item.get_type() == 9  # ITEM_DOCUMENT
        ]

        # Prepare test sections
        test_sections = []
        test_titles = []
        for doc in html_docs[:50]:  # Test first 50 documents
            html_content = doc.get_content().decode('utf-8', errors='ignore')
            soup = BeautifulSoup(html_content, 'html.parser')
            text = soup.get_text()
            # Extract a title for metadata extraction
            title_elem = soup.find(['h1', 'h2', 'h3'])
            title = title_elem.get_text(strip=True) if title_elem else "Recipe"
            test_sections.append((soup, text))
            test_titles.append(title)

        print(f"Testing with {len(test_sections)} HTML sections")
        print(f"Running {iterations} iterations per method...\n")

        # Benchmark legacy method
        print("[1/2] Benchmarking legacy extract()...")
        legacy_times = []
        legacy_field_counts = []

        for i in range(iterations):
            start = time.perf_counter()
            for (soup, text), title in zip(test_sections, test_titles):
                result = MetadataExtractor.extract(soup, text, title)
                legacy_field_counts.append(len(result))
            end = time.perf_counter()
            legacy_times.append(end - start)
            print(f"  Iteration {i+1}: {legacy_times[-1]:.3f}s")

        legacy_avg = sum(legacy_times) / len(legacy_times)
        avg_legacy_fields = sum(legacy_field_counts) / len(legacy_field_counts)

        # Benchmark pattern-based method
        print("\n[2/2] Benchmarking pattern-based extract_with_patterns()...")
        pattern_times = []
        pattern_field_counts = []
        confidences = []

        for i in range(iterations):
            start = time.perf_counter()
            for (soup, text), title in zip(test_sections, test_titles):
                result, analysis = MetadataExtractor.extract_with_patterns(soup, text, title)
                pattern_field_counts.append(len(result))
                # Average confidence across fields
                field_confidences = analysis.get('confidence_scores', {}).values()
                if field_confidences:
                    confidences.append(sum(field_confidences) / len(field_confidences))
            end = time.perf_counter()
            pattern_times.append(end - start)
            print(f"  Iteration {i+1}: {pattern_times[-1]:.3f}s")

        pattern_avg = sum(pattern_times) / len(pattern_times)
        avg_pattern_fields = sum(pattern_field_counts) / len(pattern_field_counts)
        avg_confidence = sum(confidences) / len(confidences) if confidences else 0.0

        # Create results
        legacy_result = BenchmarkResult(
            method="legacy",
            component="metadata",
            execution_time=legacy_avg,
            success_count=int(avg_legacy_fields),
            total_count=len(test_sections)
        )

        pattern_result = BenchmarkResult(
            method="pattern",
            component="metadata",
            execution_time=pattern_avg,
            success_count=int(avg_pattern_fields),
            total_count=len(test_sections),
            avg_confidence=avg_confidence
        )

        # Report results
        print("\n" + "-" * 70)
        print("Results:")
        print("-" * 70)
        print(f"Legacy extract(): {legacy_avg:.3f}s (avg {avg_legacy_fields:.1f} fields)")
        print(f"Pattern-based extract_with_patterns(): {pattern_avg:.3f}s (avg {avg_pattern_fields:.1f} fields)")
        print(f"  Avg confidence: {avg_confidence:.2f}")

        speedup = legacy_avg / pattern_avg if pattern_avg > 0 else 0
        overhead = ((pattern_avg - legacy_avg) / legacy_avg * 100) if legacy_avg > 0 else 0

        print("\nPerformance comparison:")
        if speedup > 1:
            print(f"  Pattern method is {speedup:.2f}x FASTER")
        else:
            print(f"  Pattern method has {overhead:+.1f}% overhead")

        self.results.extend([legacy_result, pattern_result])
        return legacy_result, pattern_result

    def print_summary(self):
        """Print overall benchmark summary."""
        print("\n" + "=" * 70)
        print("OVERALL BENCHMARK SUMMARY")
        print("=" * 70)

        # Group by component
        components = {}
        for result in self.results:
            if result.component not in components:
                components[result.component] = {}
            components[result.component][result.method] = result

        for component, methods in components.items():
            print(f"\n{component.upper()}:")
            print("-" * 70)

            legacy = methods.get('legacy')
            pattern = methods.get('pattern')

            if legacy and pattern:
                speedup = legacy.execution_time / pattern.execution_time
                overhead_pct = ((pattern.execution_time - legacy.execution_time) / legacy.execution_time * 100)

                print(f"  Legacy:  {legacy.execution_time:.3f}s")
                print(f"  Pattern: {pattern.execution_time:.3f}s", end="")

                if speedup > 1:
                    print(f"  ({speedup:.2f}x faster)")
                else:
                    print(f"  ({overhead_pct:+.1f}% overhead)")

                if hasattr(pattern, 'avg_confidence') and pattern.avg_confidence > 0:
                    print(f"  Pattern avg confidence: {pattern.avg_confidence:.2f}")
                if hasattr(pattern, 'avg_combined_score') and pattern.avg_combined_score > 0:
                    print(f"  Pattern combined score: {pattern.avg_combined_score:.2f}")

        # Overall statistics
        total_legacy_time = sum(r.execution_time for r in self.results if r.method == 'legacy')
        total_pattern_time = sum(r.execution_time for r in self.results if r.method == 'pattern')

        print("\n" + "=" * 70)
        print("TOTAL EXECUTION TIME:")
        print(f"  Legacy methods:  {total_legacy_time:.3f}s")
        print(f"  Pattern methods: {total_pattern_time:.3f}s")

        overall_speedup = total_legacy_time / total_pattern_time if total_pattern_time > 0 else 0
        overall_overhead = ((total_pattern_time - total_legacy_time) / total_legacy_time * 100) if total_legacy_time > 0 else 0

        if overall_speedup > 1:
            print(f"  Overall: Pattern methods are {overall_speedup:.2f}x FASTER")
        else:
            print(f"  Overall: Pattern methods have {overall_overhead:+.1f}% overhead")

        print("=" * 70)


if __name__ == "__main__":
    epub_path = "/Users/csrdsg/projects/open_fire_cooking/books/101 Things to Do with a Smoker (Eliza Cross) (Z-Library).epub"

    if not Path(epub_path).exists():
        print(f"Error: EPUB file not found: {epub_path}")
        sys.exit(1)

    print("=" * 70)
    print("EPUB RECIPE PARSER - PERFORMANCE BENCHMARK")
    print("=" * 70)
    print(f"EPUB: {Path(epub_path).name}")
    print("Testing: Legacy vs Pattern-based extraction methods")
    print("=" * 70)

    benchmark = PerformanceBenchmark(epub_path)

    # Run benchmarks
    benchmark.benchmark_ingredients(iterations=3)
    benchmark.benchmark_instructions(iterations=3)
    benchmark.benchmark_metadata(iterations=3)

    # Print summary
    benchmark.print_summary()

    print("\nBenchmark complete!")
