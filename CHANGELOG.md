# Changelog

All notable changes to **gap-mcp** are documented here.
Format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

---

## [Unreleased]

### Added
- 4 new tools: `gap_conjugacy_classes`, `gap_isomorphism`, `gap_abelian_invariants`,
  `gap_automorphisms`
- Full test suite: 33 tests covering both unit and integration paths
- GitHub Actions CI workflow (lint, typecheck, unit tests, integration tests)
- `CONTRIBUTING.md` and this `CHANGELOG.md`
- `py.typed` marker (PEP 561)

### Fixed
- **Critical**: renamed GAP variable `Z` → `cZ` in `gap_center`; `Z` is a
  read-only GAP built-in (finite-field generator) and the assignment silently
  put GAP into its error-recovery loop, causing a 60 s timeout.
- **Race condition**: `_start()` now allocates fresh `Queue` objects so that
  EOF signals (`None`) from the previous reader thread cannot leak into the new
  session and trigger a spurious `RuntimeError`.
- **Test isolation**: added `autouse` fixture that resets the shared GAP runner
  before each integration test, preventing variable-name collisions (`G`, `H`,
  etc.) between tests.
- `gap_center`: eliminated `IsCyclic(G)` call when `Z(G)` is trivial (which
  was slow for non-abelian groups); instead derive the answer directly from
  the definition.
- `gap_subgroups`: added size guard warning for groups of order > 500.
- Removed eager evaluation of `find_gap_executable()` when `GAP_EXECUTABLE`
  env var is set.
- Removed fragile semicolon-append heuristic from `execute()`; callers provide
  their own terminators.
- Replaced `time.sleep(2)` startup heuristic with sentinel-based readiness
  detection.
- `gap_runner`: separate stderr reader thread prevents stdout from being
  contaminated by GAP diagnostic messages.

### Changed
- `get_runner()` uses double-checked locking for thread-safe singleton init.
- `pyproject.toml`: added `dev` dependency group (pytest, ruff, mypy);
  removed unused `pydantic` dependency; added full PyPI classifiers.

---

## [0.1.0] — 2025-05-01

### Added
- Initial release: 10 MCP tools wrapping GAP functionality
  (`gap_eval`, `gap_group_info`, `gap_elements`, `gap_subgroups`,
  `gap_character_table`, `gap_sylow`, `gap_center`, `gap_derived_series`,
  `gap_load_package`, `gap_reset`)
- Persistent GAP subprocess with sentinel-based output detection
- Security blocklist for dangerous GAP commands (`QUIT`, `Exec`, `Process`, …)
