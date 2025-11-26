# Contributing to EPUB Recipe Parser

Thank you for your interest in contributing to EPUB Recipe Parser! This document provides guidelines and instructions for contributing to the project.

## Code of Conduct

This project follows a code of conduct that all contributors are expected to uphold. Please be respectful, inclusive, and professional in all interactions.

## Getting Started

### Prerequisites

- Python 3.10 or higher
- Git
- `uv` package manager (recommended) or `pip`

### Development Setup

1. Fork and clone the repository:
```bash
git clone https://github.com/yourusername/epub-recipe-parser.git
cd epub-recipe-parser
```

2. Install development dependencies:
```bash
pip install -e ".[dev]"
# or with uv
uv pip install -e ".[dev]"
```

3. Run tests to verify setup:
```bash
pytest tests/
```

## Development Workflow

### Code Quality Standards

This project maintains high code quality standards:

1. **Type Hints**: All functions must have complete type hints
2. **Testing**: All new features must include comprehensive tests
3. **Documentation**: Public APIs must have clear docstrings
4. **Code Style**: Code must pass black, ruff, and mypy checks

### Before Committing

Run these checks before committing:

```bash
# Format code
black src/ tests/

# Lint code
ruff check --fix src/ tests/

# Type check
mypy src/ --ignore-missing-imports

# Run tests
pytest tests/ -v
```

### Writing Tests

- Place tests in the appropriate `tests/` subdirectory
- Use descriptive test names: `test_<function>_<scenario>`
- Include docstrings explaining what each test validates
- Aim for meaningful coverage, not just high percentages
- Use fixtures from `tests/conftest.py` when applicable

Example:
```python
def test_extract_ingredients_by_header():
    """Test extracting ingredients using header strategy."""
    html = """<h3>Ingredients</h3><ul><li>flour</li></ul>"""
    soup = BeautifulSoup(html, "html.parser")
    result = IngredientsExtractor.extract(soup, soup.get_text())
    assert result is not None
    assert "flour" in result
```

### Code Style Guidelines

1. **Imports**: Organize imports in this order:
   - Standard library
   - Third-party packages
   - Local application imports

2. **Line Length**: Maximum 100 characters (configured in `pyproject.toml`)

3. **Naming Conventions**:
   - Functions/variables: `snake_case`
   - Classes: `PascalCase`
   - Constants: `UPPER_SNAKE_CASE`

4. **Docstrings**: Use Google or NumPy style:
```python
def extract_recipes(epub_path: str, min_quality: int = 20) -> list[Recipe]:
    """Extract recipes from an EPUB file.

    Args:
        epub_path: Path to the EPUB file
        min_quality: Minimum quality score (0-100)

    Returns:
        List of extracted Recipe objects

    Raises:
        ValueError: If EPUB file is invalid or unreadable
    """
```

## Pull Request Process

1. **Create a Feature Branch**
   ```bash
   git checkout -b feature/your-feature-name
   ```

2. **Make Your Changes**
   - Write code following the style guide
   - Add tests for new functionality
   - Update documentation as needed

3. **Test Your Changes**
   ```bash
   pytest tests/ -v --cov=src/epub_recipe_parser
   ```

4. **Commit Your Changes**
   ```bash
   git add .
   git commit -m "Add feature: brief description"
   ```

   Commit message format:
   - Use imperative mood ("Add feature" not "Added feature")
   - First line: brief summary (max 72 characters)
   - Blank line, then detailed description if needed

5. **Push and Create PR**
   ```bash
   git push origin feature/your-feature-name
   ```
   Then create a pull request on GitHub.

6. **PR Requirements**:
   - All tests must pass
   - Code coverage should not decrease
   - Passes all linting checks (black, ruff, mypy)
   - Includes relevant documentation updates
   - Has a clear description of changes

## Types of Contributions

### Bug Reports

When reporting bugs, include:
- Clear description of the issue
- Steps to reproduce
- Expected vs actual behavior
- Python version and OS
- Relevant code snippets or EPUB samples (if applicable)

### Feature Requests

For new features:
- Describe the use case and benefits
- Provide examples of how it would work
- Consider implementation complexity

### Code Contributions

Priority areas for contributions:
- New extraction strategies for different EPUB formats
- Improved pattern recognition for ingredients/instructions
- Better handling of edge cases
- Performance optimizations
- Documentation improvements

## Project Structure

```
epub-recipe-parser/
├── src/epub_recipe_parser/
│   ├── core/          # Core extraction logic
│   ├── analyzers/     # TOC and structure analysis
│   ├── extractors/    # Component extractors
│   ├── storage/       # Database functionality
│   ├── cli/           # Command-line interface
│   └── utils/         # Shared utilities
├── tests/             # Test suite
├── docs/              # Documentation
└── examples/          # Usage examples
```

## Development Tips

### Testing with Real EPUBs

1. Place test EPUBs in `examples/` (not committed)
2. Use the CLI to test extraction:
   ```bash
   epub-parser extract examples/cookbook.epub --output test.db
   epub-parser analyze examples/cookbook.epub
   ```

### Debugging Extraction Issues

Enable verbose logging:
```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

### Performance Profiling

Use cProfile for performance analysis:
```python
python -m cProfile -o profile.stats your_script.py
```

## Release Process (Maintainers Only)

1. Update version in `pyproject.toml`
2. Update `CHANGELOG.md`
3. Create release tag
4. Build and publish to PyPI

## Getting Help

- Check existing issues and discussions
- Review documentation in `docs/`
- Ask questions in GitHub Discussions
- Contact maintainers for major changes

## Recognition

Contributors will be recognized in:
- `CHANGELOG.md` for their contributions
- GitHub contributors list
- Release notes for significant features

Thank you for contributing to EPUB Recipe Parser!
