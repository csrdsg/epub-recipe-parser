# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.0] - 2025-11-24

### Added

- **Core Extraction Engine**
  - Direct EPUB HTML parsing without markdown conversion
  - Intelligent section splitting by header levels
  - Multi-strategy ingredient extraction (headers, measurements, lists)
  - Multi-strategy instruction extraction (headers, cooking verbs, paragraphs)
  - Comprehensive metadata extraction (serves, times, cooking methods, proteins)

- **Quality Scoring System**
  - 0-100 quality score for each recipe
  - Based on ingredients (40 pts), instructions (40 pts), metadata (20 pts)
  - Configurable quality thresholds for filtering

- **Recipe Validation**
  - Pattern-based recipe detection using cooking verbs and measurements
  - Exclusion of non-recipe content (introduction, index, etc.)
  - Confidence scoring for extracted content

- **Analysis Tools**
  - Table of Contents (TOC) analysis and recipe identification
  - EPUB structure analysis (headers, sections, patterns)
  - TOC-based extraction validation with fuzzy matching
  - Coverage reporting for extraction completeness

- **Storage & Export**
  - SQLite database storage with full-text search
  - JSON export format with metadata
  - Markdown export with formatted recipes
  - Flexible querying with filters and quality thresholds

- **CLI Interface**
  - `extract` - Extract recipes from single EPUB
  - `batch` - Batch process multiple EPUBs
  - `analyze` - Analyze EPUB structure
  - `validate` - Validate extraction against TOC
  - `search` - Search recipes in database
  - `export` - Export recipes to JSON or Markdown

- **Comprehensive Test Suite**
  - 74 tests covering all modules
  - Unit tests for extractors, validators, and utilities
  - Integration tests for database operations
  - Pattern matching and HTML parsing tests
  - Test fixtures and helpers in conftest.py

- **Development Tools**
  - Complete type hints throughout codebase
  - Black code formatting (100 char line length)
  - Ruff linting with automatic fixes
  - MyPy static type checking
  - Pytest with coverage reporting

- **Documentation**
  - Comprehensive README with examples
  - CONTRIBUTING.md with development guidelines
  - Inline code documentation with docstrings
  - Type hints for IDE support

### Technical Details

- Python 3.10+ support
- Dependencies: ebooklib, beautifulsoup4, lxml, click, rich
- Modular architecture with clear separation of concerns
- Regex-based pattern matching for recipe components
- HTML structure-aware parsing
- Quality-first extraction approach

### Known Limitations

- Best results with well-structured EPUB files
- Recipe detection relies on common patterns and keywords
- Some metadata extraction depends on text proximity
- TOC validation requires valid EPUB TOC structure

## [Unreleased]

### Planned Features

- PDF export format
- Recipe schema.org JSON-LD export
- Custom extraction rules/patterns
- Multi-language support
- Image extraction and association
- Recipe deduplication
- Enhanced metadata extraction
- Web interface

---

[0.1.0]: https://github.com/yourusername/epub-recipe-parser/releases/tag/v0.1.0
