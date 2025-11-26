# Development Setup Guide

## Prerequisites

- Python 3.10 or higher
- `uv` package manager (recommended) or `pip`

## Installation

### 1. Clone the Repository

```bash
git clone https://github.com/YOUR_USERNAME/epub-recipe-parser.git
cd epub-recipe-parser
```

### 2. Create Virtual Environment

```bash
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
```

### 3. Install Dependencies

Using `uv` (recommended):
```bash
uv pip install -e ".[dev]"
```

Or using `pip`:
```bash
pip install -e ".[dev]"
```

## Development Tools

### Running Tests

```bash
# Run all tests
uv run pytest

# Run with coverage
uv run pytest --cov=epub_recipe_parser --cov-report=html

# Run specific test file
uv run pytest tests/test_core/test_extractor.py
```

### Code Quality

```bash
# Format code
uv run black .

# Lint code
uv run ruff check .

# Fix linting issues automatically
uv run ruff check . --fix

# Type checking
uv run mypy src/
```

### Running the CLI

```bash
# Extract recipes from an EPUB
uv run epub-parser extract path/to/cookbook.epub --output recipes.db

# Batch process multiple EPUBs
uv run epub-parser batch path/to/cookbooks/ --output all_recipes.db

# Search recipes
uv run epub-parser search recipes.db "chicken"

# Export to JSON
uv run epub-parser export recipes.db --format json --output recipes.json
```

## Project Structure

```
epub-recipe-parser/
├── src/epub_recipe_parser/    # Main source code
│   ├── core/                  # Core extraction logic
│   ├── extractors/            # Component extractors (ingredients, instructions, metadata)
│   ├── analyzers/             # TOC and structure analysis
│   ├── storage/               # Database and export functionality
│   ├── cli/                   # Command-line interface
│   └── utils/                 # Shared utilities
├── tests/                     # Test suite
├── scripts/                   # Utility scripts
├── docs/                      # Documentation
└── pyproject.toml            # Project configuration
```

## Development Workflow

1. Create a new branch for your feature/fix
2. Make changes and add tests
3. Run tests and code quality checks
4. Commit with clear messages
5. Push and create a pull request

## Code Style

- Line length: 100 characters
- Formatter: black
- Linter: ruff
- Type hints: enforced with mypy
- Test coverage: maintain > 85%

## Troubleshooting

### Tests Failing

```bash
# Clean pytest cache
rm -rf .pytest_cache

# Reinstall in development mode
uv pip install -e ".[dev]"
```

### Import Errors

Make sure you're in the virtual environment:
```bash
source .venv/bin/activate
```

### Type Errors

Run mypy to see specific issues:
```bash
uv run mypy src/
```

## Resources

- [Contributing Guide](../CONTRIBUTING.md)
- [Claude Code Guide](../CLAUDE.md)
- [Development Documentation](./development/)
