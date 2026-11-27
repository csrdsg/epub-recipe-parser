# Utility scripts

Run these from the repository root using `uv`:

| Command | Purpose |
| --- | --- |
| `uv run python scripts/run_integration_tests.py` | Run the older cookbook integration suite with its reporting wrapper |
| `uv run python scripts/benchmark_performance.py cookbook.epub` | Compare extraction strategies on a cookbook |
| `uv run python scripts/validate_improvements.py` | Inspect the existing root `recipes.db` |
| `uv run python scripts/diagnostics/verify_debug_findings.py` | Reproduce older pattern-extraction diagnostics |

The integration wrapper and benchmark still reference a local cookbook path;
check their configuration before running them elsewhere. The diagnostic script
contains historical probes and is not part of the supported automated test suite.

For ordinary testing use `uv run pytest`. The Knap workflow has portable tests
in `tests/test_structured_export.py` and its guide is in
[docs/guides/STRUCTURED_EXPORT.md](../docs/guides/STRUCTURED_EXPORT.md).

The multiprocessing prototype lives in
[examples/multiprocessing.py](../examples/multiprocessing.py); it is an example,
not the implementation of the production `batch` command.
