# GitHub Release Process

The package, Python API, and CLI read the same version from
`src/epub_recipe_parser/__version__.py`. Use a matching `v`-prefixed Git tag,
such as `v4.0.0`.

## Verify a release candidate

From the repository root, use uv 0.13.10 to match GitHub Actions. Refresh the
lockfile after changing the version or dependencies. Install the locked
development dependencies and the pinned Knap runtime. Then run the tests and
build the source distribution and wheel.

```sh
uv lock
uv sync --locked --extra dev
npm ci --prefix src/epub_recipe_parser/structured/runtime
uv run --locked --extra dev pytest -q
uv build
```

To include the optional real-cookbook regression tests, set
`EPUB_RECIPE_TEST_BOOK` as described in the
[integration test guide](../../tests/integration/README.md).

Check the wheel from an isolated environment. For version 4.0.0, the CLI
prints `epub-parser, version 4.0.0`.

```sh
uv run --isolated --no-project --with ./dist/epub_recipe_parser-4.0.0-py3-none-any.whl epub-parser --version
```

## Publish on GitHub

1. Review the staged release diff. Keep cookbook files, generated recipe
   exports, databases, and installed dependencies out of the commit.
2. Merge the release commit after CI passes on the pull request.
3. Create and push the annotated tag for that commit, for example `v4.0.0`.
4. Open the CI run for the tag. Confirm the tests and distribution job passed,
   then download its `python-distributions` artifact.
5. Draft a GitHub release using that tag. Copy the latest section of
   [CHANGELOG.md](../../CHANGELOG.md) into the release notes and attach the
   wheel and source archive from the artifact. Review and publish the draft.
