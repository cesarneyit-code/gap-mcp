# Contributing to gap-mcp

Thank you for your interest in contributing! This project is an MCP server that
bridges GAP (Groups, Algorithms, Programming) and AI assistants.

## Setting up the development environment

```bash
git clone https://github.com/cesarneyit-code/gap-mcp.git
cd gap-mcp
uv sync --group dev
```

You also need [GAP](https://www.gap-system.org/Releases/) installed to run the
integration tests.

## Running the tests

```bash
# Unit tests only (no GAP required)
uv run pytest tests/ -m "not integration" -v

# All tests (GAP must be installed)
uv run pytest tests/ -v
```

## Linting and type checking

```bash
uv run ruff check gap_mcp/ tests/
uv run mypy gap_mcp/
```

## Project structure

```
gap_mcp/
  gap_runner.py   — persistent GAP subprocess manager
  server.py       — FastMCP tool definitions
  __init__.py     — public API
tests/
  conftest.py         — fixtures (runner, gap_available, reset)
  test_gap_runner.py  — unit + integration tests for GAPRunner
  test_server_tools.py — integration tests for MCP tools
```

## Adding a new tool

1. Add a function decorated with `@mcp.tool()` in `server.py`.
2. Write a GAP code string — avoid single-letter variable names that GAP
   reserves (`Z` is the finite-field generator, etc.).
3. Add at least one integration test in `test_server_tools.py`.
4. Update the tools table in `README.md`.

## Commit style

Use conventional commits:
- `feat:` new tool or feature
- `fix:` bug fix
- `test:` new or updated tests
- `docs:` documentation only
- `refactor:` code restructuring without behavior change
- `chore:` dependency updates, CI, tooling

## Reporting bugs

Open an issue at https://github.com/cesarneyit-code/gap-mcp/issues and
include:
- GAP version (`gap --version`)
- Python version
- The prompt / tool call that failed
- The error message
