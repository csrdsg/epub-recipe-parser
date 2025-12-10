# Integration Tests - Pattern-Based Extraction System

Comprehensive integration tests for the EPUB Recipe Parser's pattern-based extraction system.

## Quick Start

### Run All Tests
```bash
# Using the test runner (recommended)
uv run python run_integration_tests.py

# Or directly with pytest
uv run pytest tests/integration/test_integration.py -v
```

### Run Specific Test Classes
```bash
# End-to-end extraction
uv run pytest tests/integration/test_integration.py::TestEndToEndExtraction -v

# A/B comparison
uv run pytest tests/integration/test_integration.py::TestABComparison -v

# Database integration
uv run pytest tests/integration/test_integration.py::TestDatabaseIntegration -v

# Export functionality
uv run pytest tests/integration/test_integration.py::TestExportIntegration -v

# Quality validation
uv run pytest tests/integration/test_integration.py::TestQualityValidation -v

# Pattern detectors
uv run pytest tests/integration/test_integration.py::TestPatternExtractorMethods -v
```

## Test Coverage

### 1. TestEndToEndExtraction
Tests the complete extraction pipeline from EPUB to Recipe objects.

- **test_full_extraction_pipeline**: Validates complete EPUB extraction
- **test_confidence_scores_calculated**: Verifies pattern-based confidence scoring
- **test_extraction_with_different_quality_thresholds**: Tests quality filtering

### 2. TestABComparison
Tests A/B comparison between legacy and pattern-based methods.

- **test_legacy_vs_pattern_agreement**: Compares extraction results
- **test_pattern_confidence_metrics**: Validates confidence scoring

### 3. TestDatabaseIntegration
Tests database storage and retrieval with confidence scores.

- **test_save_and_load_with_confidence**: Database round-trip with metadata
- **test_ab_test_statistics**: A/B statistics aggregation
- **test_query_by_quality_score**: Quality-based filtering

### 4. TestExportIntegration
Tests JSON and Markdown export with confidence scores.

- **test_json_export_includes_confidence**: JSON export validation
- **test_markdown_export_readable**: Markdown format validation

### 5. TestQualityValidation
Tests quality validation and confidence correlation.

- **test_confidence_correlates_with_quality**: Quality tier analysis
- **test_average_confidence_reasonable**: Confidence score validation
- **test_high_quality_extraction_accuracy**: High-quality recipe completeness

### 6. TestPatternExtractorMethods
Tests individual pattern-based extractor methods.

- **test_ingredient_pattern_detector**: Ingredient confidence calculation
- **test_instruction_pattern_detector**: Instruction confidence calculation
- **test_metadata_pattern_detector**: Metadata extraction validation

## Test Data

The tests use a real EPUB cookbook:
- **File:** `101 Things to Do with a Smoker (Eliza Cross) (Z-Library).epub`
- **Location:** `/Users/csrdsg/projects/open_fire_cooking/books/`
- **Expected Recipes:** ~96 recipes

## Test Results (Last Run: 2025-12-06)

```
✅ 16/16 tests passed
⏱️  Execution time: 2.88 seconds
📊 Success rate: 100%
```

## What's Tested

### Pattern-Based Extraction
- ✅ 3-part architecture (Structural 30% + Pattern 50% + Linguistic 20%)
- ✅ Confidence score calculation (0.0-1.0)
- ✅ Multi-strategy ingredient detection
- ✅ Pattern-based instruction extraction
- ✅ Metadata pattern matching

### A/B Testing Framework
- ✅ Legacy vs pattern method comparison
- ✅ Agreement rate calculation
- ✅ Disagreement tracking
- ✅ Statistics aggregation

### Database Integration
- ✅ Recipe storage with metadata
- ✅ Confidence score preservation
- ✅ JSON serialization/deserialization
- ✅ Query filtering by quality

### Export Functionality
- ✅ JSON export with all metadata
- ✅ Markdown export formatting
- ✅ Confidence score inclusion

## Advanced Usage

### Run with Coverage Report
```bash
uv run pytest tests/integration/test_integration.py --cov=epub_recipe_parser --cov-report=html
```

Then open `htmlcov/index.html` in your browser.

### Run with Extra Verbose Output
```bash
uv run pytest tests/integration/test_integration.py -vv -s
```

### Run Specific Test Method
```bash
uv run pytest tests/integration/test_integration.py::TestEndToEndExtraction::test_full_extraction_pipeline -v
```

### Run in Quiet Mode
```bash
uv run pytest tests/integration/test_integration.py -q
```

## Test Runner Features

The `run_integration_tests.py` script provides:
- ✅ Colored terminal output
- ✅ Detailed progress reporting
- ✅ Test coverage summary
- ✅ Usage guide
- ✅ Error handling and debugging tips

### Test Runner Options
```bash
# Show help
uv run python run_integration_tests.py --help

# Show coverage summary
uv run python run_integration_tests.py --coverage
```

## Architecture Validated

The tests validate the complete pattern-based extraction architecture:

### 1. Structural Detection (30%)
- HTML zones (Schema.org, CSS classes)
- Header-based sections
- Semantic markup detection

### 2. Pattern Matching (50%)
- Measurement patterns
- Cooking verbs
- Ingredient markers
- Instruction indicators

### 3. Linguistic Analysis (20%)
- Text quality validation
- Sentence structure
- Coherence scoring

## Confidence Scoring

All tests verify that confidence scores are:
- ✅ In valid range (0.0-1.0)
- ✅ Calculated correctly
- ✅ Preserved in database
- ✅ Exported in JSON/Markdown
- ✅ Reasonable for well-formed content (>0.5)

## Debugging Failed Tests

If tests fail:

1. **Check test output** for specific error messages
2. **Run failing test individually** with `-v` flag
3. **Verify test EPUB exists** at the expected location
4. **Check dependencies** are installed (`pip install -e ".[dev]"`)
5. **Review logs** for extraction errors

## Contributing

When adding new tests:

1. Follow existing test structure
2. Use descriptive test names
3. Add logging for debugging
4. Include assertions with helpful messages
5. Update this README if needed

## See Also

- **Full Report:** `/Users/csrdsg/projects/epub-recipe-parser/INTEGRATION_TEST_REPORT.md`
- **Test Runner:** `/Users/csrdsg/projects/epub-recipe-parser/run_integration_tests.py`
- **Test File:** `/Users/csrdsg/projects/epub-recipe-parser/tests/integration/test_integration.py`
