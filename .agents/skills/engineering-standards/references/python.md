# Python defaults

Use Python 3.12+, uv, FastAPI, Pydantic v2, Ruff, strict mypy, and structlog. Manage dependencies with uv rather than pip, requirements.txt, Poetry, or Conda.

- Use Pydantic at I/O boundaries and dataclasses internally. Wire dependencies in the app factory.
- Use `src/project_name/{services,repositories,gateways,domain,pipelines}/`, `tests/`, `notebooks/`, and gitignored `data/`.
- Explore in notebooks, preferably marimo; ship code from `src/`. Use Python's `.py` extension with the shared file naming pattern.
- Use plain assertions, `pytest.mark.parametrize`, pytest-mock for boundary mocks, and `pytest-xdist -n auto` for parallel tests.

Default verification: `uv run ruff check . && uv run mypy . && uv run pytest`.
