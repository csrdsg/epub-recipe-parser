#!/usr/bin/env python3
"""Verification script for debug findings in Phase 1 pattern extraction.

This script tests the specific issues identified in the debug report.
"""

import re
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from epub_recipe_parser.core.patterns.instruction_detectors import InstructionPatternDetector
from epub_recipe_parser.core.patterns.instruction_structural import InstructionStructuralDetector
from epub_recipe_parser.core.patterns.analyzers import InstructionLinguisticAnalyzer
from bs4 import BeautifulSoup


def test_issue_1_division_by_zero():
    """Test Issue #1: Division by zero risk."""
    print("\n[Test 1] Division by Zero Risk")
    print("=" * 60)

    # Test with empty string
    result = InstructionPatternDetector.calculate_confidence("")
    print(f"Empty string: {result}")
    assert result == 0.0, "Should return 0.0 for empty string"

    # Test with whitespace-only
    result = InstructionPatternDetector.calculate_confidence("   \t\n  ")
    print(f"Whitespace only: {result}")
    assert result == 0.0, "Should return 0.0 for whitespace"

    # Test with very short text (< 10 chars)
    result = InstructionPatternDetector.calculate_confidence("short")
    print(f"Short text (5 chars): {result}")
    assert result == 0.0, "Should return 0.0 for text < 10 chars"

    # Test with Unicode whitespace
    result = InstructionPatternDetector.calculate_confidence("\u00A0\u00A0\u00A0")
    print(f"Unicode whitespace: {result}")

    print("✅ No division by zero errors encountered")


def test_issue_2_unbounded_loop():
    """Test Issue #2: Unbounded loop in _find_by_header."""
    print("\n[Test 2] Unbounded Loop Test")
    print("=" * 60)

    # Create malformed HTML with many siblings and no closing header
    malformed_html = """
    <html>
        <h2>Instructions</h2>
        """ + "\n".join([f"<p>Paragraph {i}</p>" for i in range(100)]) + """
    </html>
    """

    soup = BeautifulSoup(malformed_html, 'html.parser')

    print(f"HTML has {len(soup.find_all('p'))} paragraphs without closing header")
    print("Testing structural detector (this might hang if issue exists)...")

    import time
    start = time.time()

    try:
        zones = InstructionStructuralDetector.find_instruction_zones(soup)
        elapsed = time.time() - start

        print(f"✅ Completed in {elapsed:.2f}s")
        print(f"Found {len(zones)} zones")

        # Check if method='header' zones exist
        header_zones = [z for z in zones if z.detection_method == 'header']
        print(f"Header-based zones: {len(header_zones)}")

        if elapsed > 1.0:
            print("⚠️ WARNING: Took > 1s for 100 paragraphs. Possible performance issue.")
        else:
            print("✅ Performance acceptable")

    except Exception as e:
        print(f"❌ ERROR: {e}")


def test_issue_3_regex_compilation():
    """Test Issue #3: Regex compiled in loop."""
    print("\n[Test 3] Regex Compilation Performance")
    print("=" * 60)

    import time

    text = "Preheat oven to 350°F. Mix ingredients. Bake for 30 minutes. Cool before serving."

    # Time 1000 calls to detect imperative sentences
    start = time.time()
    for _ in range(1000):
        InstructionPatternDetector._detect_imperative_sentences(text.lower())
    elapsed_current = time.time() - start

    print(f"Current implementation: {elapsed_current:.4f}s for 1000 calls")
    print(f"Average per call: {elapsed_current * 1000:.4f}ms")

    # Simulate with pre-compiled regex
    SENTENCE_SPLIT = re.compile(r'[.!?]+')
    start = time.time()
    for _ in range(1000):
        sentences = SENTENCE_SPLIT.split(text.lower())
        # Simulate rest of method
        for s in sentences:
            s.strip()
    elapsed_optimized = time.time() - start

    print(f"Pre-compiled regex: {elapsed_optimized:.4f}s for 1000 calls")
    print(f"Speedup: {elapsed_current / elapsed_optimized:.2f}x")

    if elapsed_current > elapsed_optimized * 1.5:
        print("⚠️ Significant performance improvement possible with pre-compiled regex")
    else:
        print("✅ Performance difference is negligible")


def test_issue_6_none_reference():
    """Test Issue #6: None reference in extract_with_patterns."""
    print("\n[Test 6] None Reference Check")
    print("=" * 60)

    # Create a mock InstructionZone with None tag
    from epub_recipe_parser.core.models import InstructionZone

    try:
        # This should work (allowing None)
        zone = InstructionZone(
            zone=None,
            detection_method='test',
            confidence=0.9,
            context={}
        )
        print(f"Created zone with None Tag: {zone}")
        print("⚠️ InstructionZone accepts None tags (potential issue)")

        # Try to call get_text() on None
        try:
            text = zone.zone.get_text(strip=True)
            print(f"❌ UNEXPECTED: Got text from None: {text}")
        except AttributeError as e:
            print(f"✅ Expected AttributeError: {e}")

    except Exception as e:
        print(f"Zone creation failed: {e}")


def test_issue_9_set_union():
    """Test Issue #9: Set union in loop."""
    print("\n[Test 9] Set Union Performance")
    print("=" * 60)

    import time

    text = "Heat oil in pan until hot. Then add onions. Cook while stirring."

    # Current implementation (union in loop)
    start = time.time()
    for _ in range(1000):
        marker_count = sum(
            1 for marker in InstructionPatternDetector.TEMPORAL_MARKERS | InstructionPatternDetector.SEQUENTIAL_MARKERS
            if marker in text
        )
    elapsed_current = time.time() - start

    print(f"Current (union in loop): {elapsed_current:.4f}s for 1000 calls")

    # Optimized (pre-computed union)
    ALL_MARKERS = InstructionPatternDetector.TEMPORAL_MARKERS | InstructionPatternDetector.SEQUENTIAL_MARKERS
    start = time.time()
    for _ in range(1000):
        marker_count = sum(
            1 for marker in ALL_MARKERS
            if marker in text
        )
    elapsed_optimized = time.time() - start

    print(f"Optimized (pre-computed): {elapsed_optimized:.4f}s for 1000 calls")
    print(f"Speedup: {elapsed_current / elapsed_optimized:.2f}x")

    if elapsed_current > elapsed_optimized * 1.2:
        print("⚠️ Significant performance improvement with pre-computed union")
    else:
        print("✅ Performance difference is minor")


def test_issue_13_measurement_penalty():
    """Test Issue #13: Measurement penalty logic."""
    print("\n[Test 13] Measurement Penalty Logic")
    print("=" * 60)

    # Test cases with different measurement ratios
    test_cases = [
        ("2 cups flour\n1 cup sugar\n½ tsp salt", "High measurements (100%)"),
        ("Mix ingredients\nBake at 350°F\nCool completely", "Low measurements (0%)"),
        ("Add 1 cup flour\nMix well\nBake for 30 minutes", "Medium measurements (33%)"),
    ]

    for text, description in test_cases:
        score = InstructionPatternDetector._calculate_measurement_penalty(text)
        lines = [l for l in text.split('\n') if l.strip()]
        from epub_recipe_parser.utils.patterns import MEASUREMENT_PATTERN
        measurement_lines = sum(1 for line in lines if MEASUREMENT_PATTERN.search(line))
        ratio = measurement_lines / len(lines) if lines else 0

        print(f"\n{description}")
        print(f"  Text: {text[:50]}...")
        print(f"  Measurement ratio: {ratio:.2%}")
        print(f"  Penalty score: {score:.2f}")

        # Verify logic
        if ratio < 0.2:
            expected = 1.0
        elif ratio > 0.5:
            expected = 0.0
        else:
            expected = 1.0 - ((ratio - 0.2) / 0.3)

        if abs(score - expected) < 0.01:
            print(f"  ✅ Score matches expected: {expected:.2f}")
        else:
            print(f"  ❌ Score mismatch! Expected {expected:.2f}, got {score:.2f}")


def test_confidence_bounds():
    """Test that confidence scores stay within [0.0, 1.0]."""
    print("\n[Bonus Test] Confidence Score Bounds")
    print("=" * 60)

    test_texts = [
        "",  # Empty
        "a",  # Very short
        "Heat mix stir cook bake roast grill fry sauté boil " * 100,  # Many verbs
        "The quick brown fox jumps over the lazy dog " * 50,  # No cooking verbs
        "1. Preheat oven.\n2. Mix ingredients.\n3. Bake for 30 minutes.",  # Perfect instructions
    ]

    for i, text in enumerate(test_texts):
        score = InstructionPatternDetector.calculate_confidence(text)
        print(f"Test {i+1}: Score = {score:.3f}")

        if not (0.0 <= score <= 1.0):
            print(f"  ❌ Score out of bounds: {score}")
        else:
            print("  ✅ Score within bounds")

        # Test linguistic score too
        ling_score = InstructionLinguisticAnalyzer.calculate_instruction_score(text)
        print(f"  Linguistic: {ling_score:.3f}")

        if not (0.0 <= ling_score <= 1.0):
            print(f"  ❌ Linguistic score out of bounds: {ling_score}")
        else:
            print("  ✅ Linguistic score within bounds")


def main():
    """Run all verification tests."""
    print("=" * 60)
    print("Phase 1 Debug Verification Tests")
    print("=" * 60)

    tests = [
        test_issue_1_division_by_zero,
        test_issue_2_unbounded_loop,
        test_issue_3_regex_compilation,
        test_issue_6_none_reference,
        test_issue_9_set_union,
        test_issue_13_measurement_penalty,
        test_confidence_bounds,
    ]

    for test in tests:
        try:
            test()
        except Exception as e:
            print(f"\n❌ Test failed with exception: {e}")
            import traceback
            traceback.print_exc()

    print("\n" + "=" * 60)
    print("Verification Complete")
    print("=" * 60)


if __name__ == "__main__":
    main()
