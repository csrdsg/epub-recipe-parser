# Implementation Plan: Extractor Modernization

## Overview

This document provides a detailed, task-by-task implementation plan for modernizing the InstructionsExtractor and MetadataExtractor to match the pattern-based architecture of IngredientsExtractor.

**Total Estimated Effort**: 7-10 days (1.5-2 weeks)

**Approach**: Incremental refactoring with backward compatibility

---

## Phase 1: InstructionsExtractor Modernization (5-7 days)

### Task 1.1: Create Instruction Pattern Detection Infrastructure (6 hours)

**File**: `src/epub_recipe_parser/core/patterns/instruction_detectors.py`

**Subtasks**:
1. Create `InstructionPatternDetector` class
2. Define pattern categories:
   - `COOKING_VERBS`: Port from `COOKING_VERBS_PATTERN` in patterns.py
   - `TEMPORAL_MARKERS`: {"until", "after", "before", "while", "during", "when", "then"}
   - `SEQUENTIAL_MARKERS`: {"first", "second", "next", "finally", "meanwhile", "lastly"}
   - `IMPERATIVE_STARTERS`: {"preheat", "heat", "place", "add", "mix", "stir", "combine"}
   - `MEASUREMENT_INDICATORS`: Negative indicator (presence suggests ingredients)

3. Implement `calculate_confidence(text: str) -> float`:
   ```python
   Scoring algorithm:
   - Cooking verb density (verbs per 100 words): 30% weight
   - Temporal/sequential markers: 25% weight
   - Imperative sentence patterns: 20% weight
   - Paragraph length (100-300 chars optimal): 15% weight
   - Absence of measurements (inverse ratio): 10% weight
   ```

4. Implement helper methods:
   - `_calculate_verb_density(text: str) -> float`
   - `_has_temporal_markers(text: str) -> bool`
   - `_detect_imperative_sentences(text: str) -> float`
   - `_check_paragraph_length(text: str) -> float`
   - `_calculate_measurement_penalty(text: str) -> float`

**Acceptance Criteria**:
- [ ] Class created with all methods
- [ ] Unit tests for confidence calculation
- [ ] Confidence scores in range [0.0, 1.0]
- [ ] High confidence (>0.8) for clear instructions
- [ ] Low confidence (<0.3) for ingredient lists

**Tests**:
```python
def test_high_confidence_instructions():
    text = "Preheat oven to 350°F. Heat oil in skillet. Add onions and cook until soft."
    assert InstructionPatternDetector.calculate_confidence(text) > 0.8

def test_low_confidence_ingredients():
    text = "2 cups flour\n1 cup sugar\n½ tsp salt\n1 egg"
    assert InstructionPatternDetector.calculate_confidence(text) < 0.3
```

---

### Task 1.2: Create Instruction Structural Detection (8 hours)

**File**: `src/epub_recipe_parser/core/patterns/instruction_structural.py`

**Subtasks**:
1. Create `InstructionZone` dataclass in `models.py`:
   ```python
   @dataclass
   class InstructionZone:
       zone: Tag
       detection_method: str
       confidence: float
       context: Dict[str, Any] = field(default_factory=dict)
   ```

2. Create `InstructionStructuralDetector` class

3. Implement detection strategies:
   - **Strategy 1**: CSS class-based detection
     - Port `INSTRUCTION_CLASSES` from current implementation
     - Find elements with instruction-related classes
     - Confidence: 0.9 (high)

   - **Strategy 2**: Header-based detection
     - Port `INSTRUCTION_KEYWORDS` from patterns.py
     - Find sections after instruction headers
     - Confidence: 0.85

   - **Strategy 3**: Post-ingredients positioning
     - Detect ingredient sections first
     - Find paragraphs/sections after ingredients
     - Confidence: 0.75

   - **Strategy 4**: Numbered list detection
     - Find `<ol>` or numbered lists
     - Check for cooking verbs
     - Confidence: 0.80

4. Implement `find_instruction_zones(soup: BeautifulSoup) -> List[InstructionZone]`

5. Implement helper methods:
   - `_find_by_css_class(soup: BeautifulSoup) -> List[InstructionZone]`
   - `_find_by_header(soup: BeautifulSoup) -> List[InstructionZone]`
   - `_find_post_ingredients(soup: BeautifulSoup) -> List[InstructionZone]`
   - `_find_numbered_lists(soup: BeautifulSoup) -> List[InstructionZone]`

**Acceptance Criteria**:
- [ ] InstructionZone dataclass added to models.py
- [ ] All 4 detection strategies implemented
- [ ] Zones include detection method and confidence
- [ ] No duplicate zones in results
- [ ] Unit tests for each strategy

**Tests**:
```python
def test_css_class_detection():
    html = '<div class="method"><p>Heat oil in pan...</p></div>'
    soup = BeautifulSoup(html, 'html.parser')
    zones = InstructionStructuralDetector.find_instruction_zones(soup)
    assert len(zones) > 0
    assert zones[0].detection_method == 'css_class'
    assert zones[0].confidence > 0.8

def test_header_detection():
    html = '<h3>Instructions</h3><p>Preheat oven to 350°F...</p>'
    soup = BeautifulSoup(html, 'html.parser')
    zones = InstructionStructuralDetector.find_instruction_zones(soup)
    assert any(z.detection_method == 'header' for z in zones)
```

---

### Task 1.3: Enhance Linguistic Analysis for Instructions (4 hours)

**File**: `src/epub_recipe_parser/core/patterns/analyzers.py`

**Subtasks**:
1. Add `InstructionLinguisticAnalyzer` class (or enhance existing `LinguisticAnalyzer`)

2. Implement `calculate_instruction_score(text: str) -> float`:
   ```python
   Scoring algorithm:
   - Imperative mood detection: 35% weight
   - Cooking verb frequency: 30% weight
   - Sequential flow markers: 20% weight
   - Appropriate complexity (words per sentence): 15% weight
   ```

3. Implement `detect_stop_patterns(text: str) -> bool`:
   - Check for STOP_PATTERNS from InstructionsExtractor
   - Return True if text matches stop patterns

4. Implement helper methods:
   - `_detect_imperative_mood(text: str) -> float`
   - `_calculate_verb_frequency(text: str) -> float`
   - `_has_sequential_markers(text: str) -> float`
   - `_calculate_complexity_score(text: str) -> float`

**Acceptance Criteria**:
- [ ] Linguistic analysis methods implemented
- [ ] Stop pattern detection works correctly
- [ ] Unit tests for all methods
- [ ] Scores correlate with instruction quality

**Tests**:
```python
def test_instruction_linguistic_score():
    text = "First, preheat oven. Then, mix ingredients. Finally, bake for 30 minutes."
    score = InstructionLinguisticAnalyzer.calculate_instruction_score(text)
    assert score > 0.8

def test_stop_pattern_detection():
    text = "Tip: You can substitute butter for oil."
    assert InstructionLinguisticAnalyzer.detect_stop_patterns(text) == True
```

---

### Task 1.4: Add extract_with_patterns() to InstructionsExtractor (8 hours)

**File**: `src/epub_recipe_parser/extractors/instructions.py`

**Subtasks**:
1. Import new pattern modules:
   ```python
   from epub_recipe_parser.core.patterns import (
       InstructionPatternDetector,
       InstructionLinguisticAnalyzer,
       InstructionStructuralDetector,
   )
   ```

2. Implement `extract_with_patterns(soup: BeautifulSoup, text: str) -> tuple[Optional[str], dict]`:
   ```python
   Algorithm:
   1. Try StructuralDetector.find_instruction_zones()
   2. Evaluate each zone with PatternDetector and LinguisticAnalyzer
   3. Select zone with highest combined confidence
   4. If no zones or confidence < 0.5, fall back to original extract()
   5. Augment result with confidence scoring
   6. Return (instructions_text, metadata)
   ```

3. Implement metadata dictionary:
   ```python
   metadata = {
       'strategy': str,  # 'structural_css_class', 'structural_header', 'original_with_patterns'
       'confidence': float,  # 0.0-1.0
       'linguistic_score': float,  # 0.0-1.0
       'used_structural_detector': bool,
       'zone_count': int,
       'cooking_verb_density': float,
       'detection_method': str,  # from InstructionZone
   }
   ```

4. Add logging for debugging:
   ```python
   logger.debug("Trying structural detection...")
   logger.debug(f"Found {len(zones)} potential zones")
   logger.info(f"Strategy SUCCESS: {metadata['strategy']} (confidence={confidence:.2f})")
   ```

5. Ensure backward compatibility:
   - Keep existing `extract()` method unchanged
   - New method is purely additive

**Acceptance Criteria**:
- [ ] extract_with_patterns() implemented
- [ ] Returns tuple: (result, metadata)
- [ ] Falls back to original method if needed
- [ ] Comprehensive logging
- [ ] Integration tests with A/B framework
- [ ] Backward compatibility maintained

**Tests**:
```python
def test_extract_with_patterns_basic():
    html = '<div class="method"><p>Heat oil. Cook onions. Serve hot.</p></div>'
    soup = BeautifulSoup(html, 'html.parser')
    text = soup.get_text()

    instructions, metadata = InstructionsExtractor.extract_with_patterns(soup, text)

    assert instructions is not None
    assert 'confidence' in metadata
    assert 'strategy' in metadata
    assert metadata['confidence'] > 0.5

def test_extract_with_patterns_fallback():
    # Test that it falls back to original method
    html = '<p>Some random text without instructions.</p>'
    soup = BeautifulSoup(html, 'html.parser')
    text = soup.get_text()

    instructions, metadata = InstructionsExtractor.extract_with_patterns(soup, text)

    # Should either return None or low confidence
    if instructions:
        assert metadata['confidence'] < 0.5
```

---

### Task 1.5: Update Protocol Definitions (2 hours)

**File**: `src/epub_recipe_parser/core/protocols.py`

**Subtasks**:
1. Add optional `extract_with_patterns` to `IComponentExtractor`:
   ```python
   @runtime_checkable
   class IComponentExtractor(Protocol):
       @staticmethod
       def extract(soup: BeautifulSoup, text: str) -> Optional[str]:
           """Legacy extraction method."""
           ...

       # Optional method for modern extractors
       @staticmethod
       def extract_with_patterns(
           soup: BeautifulSoup, text: str
       ) -> tuple[Optional[str], dict]:
           """Pattern-based extraction with confidence scoring."""
           ...
   ```

2. Update `ABTestRunner._extract_with_metadata()` to handle both:
   - Try calling `extract_with_patterns()` first
   - Fall back to `extract()` if method doesn't exist

**Acceptance Criteria**:
- [ ] Protocol updated
- [ ] Backward compatible with old extractors
- [ ] ABTestRunner handles both patterns
- [ ] Type checking passes

---

### Task 1.6: Integration Testing (8 hours)

**File**: `tests/test_extractors/test_instructions_ab.py`

**Subtasks**:
1. Create comprehensive integration tests:
   - Test against 50+ recipes from test corpus
   - Compare old vs new extraction
   - Measure agreement rate
   - Analyze confidence-quality correlation

2. Create test fixtures:
   ```python
   @pytest.fixture
   def recipe_corpus():
       """Load test recipe corpus."""
       return load_recipes_from_test_dir('tests/fixtures/recipes/')
   ```

3. Implement comparison tests:
   ```python
   def test_instruction_ab_comparison(recipe_corpus):
       """Compare old and new extraction methods."""
       results = []

       for recipe in recipe_corpus:
           old_result = InstructionsExtractor.extract(recipe.soup, recipe.text)
           new_result, metadata = InstructionsExtractor.extract_with_patterns(
               recipe.soup, recipe.text
           )

           results.append({
               'recipe_id': recipe.id,
               'old_success': old_result is not None and len(old_result) > 100,
               'new_success': new_result is not None and len(new_result) > 100,
               'confidence': metadata['confidence'],
               'agreement': (old_result is not None) == (new_result is not None)
           })

       # Calculate metrics
       agreement_rate = sum(r['agreement'] for r in results) / len(results)
       avg_confidence = sum(r['confidence'] for r in results) / len(results)

       print(f"Agreement rate: {agreement_rate:.1%}")
       print(f"Average confidence: {avg_confidence:.2f}")

       assert agreement_rate > 0.90  # Expect high agreement
   ```

4. Create regression tests:
   - Ensure new method extracts at least as much as old method
   - Verify no breaking changes

5. Performance benchmarks:
   ```python
   def test_instruction_extraction_performance(recipe_corpus, benchmark):
       """Benchmark new extraction method."""
       def run_extraction():
           for recipe in recipe_corpus[:10]:
               InstructionsExtractor.extract_with_patterns(recipe.soup, recipe.text)

       result = benchmark(run_extraction)
       # Performance should be within 10% of old method
   ```

**Acceptance Criteria**:
- [ ] Integration tests pass
- [ ] Agreement rate >90%
- [ ] Performance overhead <10%
- [ ] Confidence correlates with quality
- [ ] Regression tests pass

---

### Task 1.7: Update EPUBRecipeExtractor Integration (4 hours)

**File**: `src/epub_recipe_parser/core/extractor.py`

**Subtasks**:
1. Update `_extract_recipe_from_section()` to use new method when A/B testing enabled:
   ```python
   # Extract instructions with A/B testing
   if self.ab_runner:
       comparison = self.ab_runner.compare_extractors(
           control_extractor=self.instructions_extractor,
           treatment_extractor=self.instructions_extractor,  # Same class, different methods
           soup=soup,
           text=text
       )

       if self.ab_runner.should_use_treatment(comparison):
           instructions = comparison['new_ingredients']  # Note: field name is generic
       else:
           instructions = comparison['old_ingredients']

       # Store A/B metadata
       recipe.metadata['ab_test_instructions'] = {
           'confidence': comparison['confidence'],
           'strategy': comparison['strategy'],
           'agreement': comparison['agreement']
       }
   else:
       # Use legacy method
       instructions = self.instructions_extractor.extract(soup, text)
   ```

2. Add configuration option for per-component A/B testing:
   ```python
   @dataclass
   class ABTestConfig:
       enabled: bool = False
       use_new_method: bool = False
       test_ingredients: bool = True  # NEW
       test_instructions: bool = True  # NEW
       test_metadata: bool = True  # NEW
       log_level: LogLevel = LogLevel.INFO
       success_threshold: int = 25
   ```

3. Update documentation in docstrings

**Acceptance Criteria**:
- [ ] EPUBRecipeExtractor uses new method when configured
- [ ] A/B metadata stored in recipes
- [ ] Configuration options work correctly
- [ ] Integration tests pass

---

## Phase 2: MetadataExtractor Modernization (3-4 days)

### Task 2.1: Create Metadata Pattern Detection (8 hours)

**File**: `src/epub_recipe_parser/core/patterns/metadata_detectors.py`

**Subtasks**:
1. Create `MetadataPattern` dataclass:
   ```python
   @dataclass
   class MetadataPattern:
       field_name: str
       pattern: re.Pattern
       confidence: float
       match_count: int = 0
   ```

2. Create `MetadataPatternDetector` class

3. Implement field-specific extraction methods:
   - `extract_serves(text: str) -> tuple[Optional[str], float]`
   - `extract_time(text: str, time_type: str) -> tuple[Optional[int], float]`
   - `extract_cooking_method(text: str, title: str) -> tuple[Optional[str], float]`
   - `extract_protein_type(text: str, title: str) -> tuple[Optional[str], float]`

4. Define pattern priorities with confidence scores:
   ```python
   SERVES_PATTERNS = [
       (re.compile(r"serves?[:\s]+(\d+(?:\s*(?:-|to)\s*\d+)?)"), 0.95),
       (re.compile(r"servings?[:\s]+(\d+(?:\s*(?:-|to)\s*\d+)?)"), 0.95),
       (re.compile(r"yield[s]?[:\s]+(\d+(?:\s*(?:-|to)\s*\d+)?)"), 0.90),
       (re.compile(r"makes?[:\s]+(\d+(?:\s*(?:-|to)\s*\d+)?)"), 0.85),
   ]

   PREP_TIME_PATTERNS = [
       (re.compile(r"prep(?:aration)?\s*time[:\s]+([^.\n]+)"), 0.95),
       (re.compile(r"active\s*time[:\s]+([^.\n]+)"), 0.90),
   ]

   COOK_TIME_PATTERNS = [
       (re.compile(r"cook(?:ing)?\s*time[:\s]+([^.\n]+)"), 0.95),
       (re.compile(r"baking\s*time[:\s]+([^.\n]+)"), 0.90),
   ]
   ```

5. Implement confidence boosting based on validation:
   ```python
   def _boost_confidence_if_validated(
       value: Optional[str],
       base_confidence: float,
       validator: Callable
   ) -> float:
       if value and validator(value):
           return min(base_confidence * 1.1, 1.0)
       return base_confidence * 0.7
   ```

6. Implement `extract_all_metadata()`:
   ```python
   def extract_all_metadata(
       text: str, title: str = ""
   ) -> tuple[Dict[str, str], Dict[str, float]]:
       """Extract all metadata with per-field confidence.

       Returns:
           (metadata_dict, confidence_dict)
       """
   ```

**Acceptance Criteria**:
- [ ] All extraction methods implemented
- [ ] Per-field confidence scoring
- [ ] Pattern priority respected
- [ ] Validation boosts confidence
- [ ] Unit tests for each field

**Tests**:
```python
def test_extract_serves_with_confidence():
    serves, confidence = MetadataPatternDetector.extract_serves("Serves: 4-6 people")
    assert serves == "4-6"
    assert confidence > 0.9

def test_extract_time_with_confidence():
    prep_time, confidence = MetadataPatternDetector.extract_time("Prep time: 30 minutes", "prep")
    assert prep_time == 30
    assert confidence > 0.9
```

---

### Task 2.2: Add extract_with_patterns() to MetadataExtractor (4 hours)

**File**: `src/epub_recipe_parser/extractors/metadata.py`

**Subtasks**:
1. Import pattern detector:
   ```python
   from epub_recipe_parser.core.patterns import MetadataPatternDetector
   ```

2. Implement `extract_with_patterns()`:
   ```python
   @staticmethod
   def extract_with_patterns(
       soup: BeautifulSoup, text: str, title: str = ""
   ) -> tuple[Dict[str, str], dict]:
       """Modern pattern-based extraction with per-field confidence.

       Returns:
           (metadata_dict, extraction_metadata)
       """
       metadata, field_confidence = MetadataPatternDetector.extract_all_metadata(
           text, title
       )

       overall_confidence = (
           sum(field_confidence.values()) / len(field_confidence)
           if field_confidence else 0.0
       )

       extraction_metadata = {
           'strategy': 'pattern_based',
           'field_confidence': field_confidence,
           'overall_confidence': overall_confidence,
           'fields_extracted': len(metadata),
           'fields_attempted': 5,  # serves, prep_time, cook_time, cooking_method, protein_type
       }

       return metadata, extraction_metadata
   ```

3. Keep existing `extract()` method unchanged

4. Add logging

**Acceptance Criteria**:
- [ ] New method implemented
- [ ] Returns tuple with metadata
- [ ] Per-field confidence tracked
- [ ] Backward compatible
- [ ] Unit tests pass

---

### Task 2.3: Integration and Testing (6 hours)

**Files**:
- `tests/test_extractors/test_metadata_ab.py`
- Update `src/epub_recipe_parser/core/extractor.py`

**Subtasks**:
1. Create integration tests for metadata A/B testing

2. Update EPUBRecipeExtractor to use new metadata method

3. Run full corpus testing

4. Validate confidence-quality correlation

5. Performance benchmarking

**Acceptance Criteria**:
- [ ] Integration tests pass
- [ ] EPUBRecipeExtractor uses new method
- [ ] Performance overhead <5%
- [ ] Agreement rate >95% (metadata is more stable)

---

## Phase 3: Documentation and Finalization (2-3 days)

### Task 3.1: Update Documentation (4 hours)

**Files to Update**:
1. `CLAUDE.md`:
   - Document new `extract_with_patterns()` methods
   - Explain confidence scoring
   - Update architecture section

2. `README.md`:
   - Mention pattern-based extraction
   - Document A/B testing capability

3. `ARCHITECTURE_ANALYSIS.md`:
   - Already created

4. Code docstrings:
   - All new classes and methods
   - Examples for complex methods

**Acceptance Criteria**:
- [ ] All documentation updated
- [ ] Examples provided
- [ ] Clear migration guidance
- [ ] Architecture diagrams (optional)

---

### Task 3.2: Create Migration Guide (2 hours)

**File**: `MIGRATION_GUIDE.md`

**Content**:
1. How to enable A/B testing
2. How to interpret confidence scores
3. When to switch from old to new methods
4. Troubleshooting low confidence
5. Performance considerations

**Acceptance Criteria**:
- [ ] Clear migration steps
- [ ] Examples provided
- [ ] Troubleshooting section
- [ ] FAQ section

---

### Task 3.3: Create Example Scripts (2 hours)

**File**: `examples/ab_testing_example.py`

**Content**:
```python
"""Example: A/B testing with pattern-based extraction."""

from epub_recipe_parser.core.extractor import EPUBRecipeExtractor
from epub_recipe_parser.core.models import ExtractorConfig, ABTestConfig, LogLevel
from epub_recipe_parser.testing.ab_analyzer import ABTestAnalyzer

# Configure A/B testing
config = ExtractorConfig(
    ab_testing=ABTestConfig(
        enabled=True,
        use_new_method=False,  # Test only, don't use in production yet
        test_ingredients=True,
        test_instructions=True,
        test_metadata=True,
        log_level=LogLevel.INFO
    )
)

# Extract with A/B testing
extractor = EPUBRecipeExtractor(config=config)
recipes = extractor.extract_from_epub("test.epub")

# Analyze results
analyzer = ABTestAnalyzer.from_database_path("recipes.db")
print(analyzer.generate_report())
```

**Acceptance Criteria**:
- [ ] Working example script
- [ ] Clear comments
- [ ] Demonstrates key features
- [ ] Includes output examples

---

### Task 3.4: Final Testing and Validation (8 hours)

**Subtasks**:
1. Run full test suite
2. Test on production corpus (if available)
3. Performance profiling
4. Memory profiling
5. Edge case testing
6. Documentation review
7. Code review checklist

**Acceptance Criteria**:
- [ ] All tests pass
- [ ] No memory leaks
- [ ] Performance within 10% of baseline
- [ ] Edge cases handled
- [ ] Code review approved

---

## Success Metrics

### Quantitative Metrics
- [ ] Test coverage >85% for new code
- [ ] Agreement rate >90% (instructions), >95% (metadata)
- [ ] Confidence-quality correlation >0.70
- [ ] Performance overhead <10%
- [ ] Zero breaking changes

### Qualitative Metrics
- [ ] Code more maintainable (subjective assessment)
- [ ] Architecture more consistent
- [ ] Easier to add new strategies
- [ ] Better observability via confidence scores

---

## Risk Mitigation

### High-Risk Areas
1. **Confidence calibration**: Scores might not correlate with actual quality
   - **Mitigation**: Extensive A/B testing, empirical adjustment

2. **Performance degradation**: Pattern detection adds overhead
   - **Mitigation**: Profile early, optimize hot paths, consider caching

3. **Breaking changes**: New approach breaks existing code
   - **Mitigation**: Maintain backward compatibility, phased rollout

### Contingency Plans
1. If agreement rate <80%: Revisit pattern detection logic
2. If performance overhead >20%: Optimize or disable by default
3. If confidence correlation <0.5: Reconsider entire approach

---

## Rollout Strategy

### Phase 1: Internal Testing (Week 1-2)
- Implement with A/B testing disabled by default
- Internal testing and validation
- Fix bugs and adjust confidence scoring

### Phase 2: Opt-in A/B Testing (Week 3-4)
- Enable A/B testing via configuration flag
- Collect data from users
- Analyze disagreements
- Tune confidence thresholds

### Phase 3: Gradual Rollout (Week 5-6)
- Enable new methods for high-confidence cases (>0.8)
- Monitor for issues
- Gradually lower threshold

### Phase 4: Full Migration (Week 7-8)
- Make new methods default
- Deprecate old methods (but keep for compatibility)
- Update all documentation

### Phase 5: Cleanup (Future release)
- Remove old methods after 2-3 stable releases
- Simplify codebase
- Archive migration documentation

---

## Development Workflow

### Daily Workflow
1. Morning: Review previous day's work
2. Implement 1-2 tasks from plan
3. Write tests alongside implementation
4. Run test suite before committing
5. Update task checklist
6. Commit with clear messages

### Commit Message Format
```
[phase] category: description

Example:
[P1] feat: Add InstructionPatternDetector with confidence scoring
[P1] test: Add unit tests for instruction pattern detection
[P2] feat: Add extract_with_patterns() to MetadataExtractor
[P3] docs: Update CLAUDE.md with pattern-based architecture
```

### Code Review Checklist
- [ ] Tests written and passing
- [ ] Docstrings complete
- [ ] Type hints added
- [ ] No hardcoded values
- [ ] Error handling implemented
- [ ] Logging added
- [ ] Performance acceptable
- [ ] Backward compatible

---

## Next Steps

1. **Review this implementation plan** with team
2. **Create GitHub issues** for each task
3. **Set up project board** to track progress
4. **Begin with Task 1.1** (InstructionPatternDetector)
5. **Daily standup** to track progress and blockers

---

## Appendix: Dependency Graph

```
Task Dependencies:

1.1 (Pattern Detection) → 1.4 (extract_with_patterns)
1.2 (Structural Detection) → 1.4 (extract_with_patterns)
1.3 (Linguistic Analysis) → 1.4 (extract_with_patterns)
1.4 (extract_with_patterns) → 1.5 (Protocol Updates)
1.5 (Protocol Updates) → 1.6 (Integration Testing)
1.6 (Integration Testing) → 1.7 (EPUBRecipeExtractor)

2.1 (Metadata Pattern Detection) → 2.2 (extract_with_patterns)
2.2 (extract_with_patterns) → 2.3 (Integration)

1.7 (EPUBRecipeExtractor) → 3.1 (Documentation)
2.3 (Metadata Integration) → 3.1 (Documentation)
3.1 (Documentation) → 3.2 (Migration Guide)
3.2 (Migration Guide) → 3.3 (Examples)
3.3 (Examples) → 3.4 (Final Testing)
```

**Critical Path**: 1.1 → 1.2 → 1.3 → 1.4 → 1.7 → 2.1 → 2.2 → 2.3 → 3.4

**Parallel Work Opportunities**:
- 1.1 and 1.2 can be done in parallel
- 1.3 can start after 1.1 completes
- 2.1 can start while 1.6 is running
- Documentation (3.1-3.3) can be done in parallel with testing

---

*Document Version: 1.0*
*Created: 2025-12-05*
*Estimated Total Effort: 7-10 days*
