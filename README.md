# gap-mcp

**Model Context Protocol server for GAP (Groups, Algorithms, Programming)**

[![CI](https://github.com/cesarneyit-code/gap-mcp/actions/workflows/ci.yml/badge.svg)](https://github.com/cesarneyit-code/gap-mcp/actions)
[![PyPI - Python Version](https://img.shields.io/pypi/pyversions/gap-mcp)](https://pypi.org/project/gap-mcp/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

Connects Claude and other MCP-compatible AI assistants to [GAP](https://www.gap-system.org/),
the open-source computer algebra system for computational discrete algebra —
with particular emphasis on computational group theory.

> This is the first publicly available MCP server for GAP.

---

## What is GAP?

GAP (Groups, Algorithms, Programming) is a system for computational discrete
algebra, specializing in:

- Finite group theory (permutation groups, matrix groups, finitely presented groups)
- Representation theory and character tables
- Combinatorics and graph theory
- Number theory

## What does this MCP do?

It allows Claude to perform **exact symbolic computations** in group theory by
calling GAP directly — instead of approximating or reasoning from memory.

```
You   → "What are the Sylow 2-subgroups of S4?"
Claude → calls gap_sylow('SymmetricGroup(4)', 2)
GAP   → Sylow 2-subgroup order: 8, Number of Sylow 2-subgroups: 3
Claude → explains the result with mathematical context
```

---

## Installation

### Prerequisites

| Requirement | Notes |
|-------------|-------|
| **GAP** ≥ 4.12 | [Download](https://www.gap-system.org/Releases/) |
| **Python** ≥ 3.11 | |
| **uv** | [Install](https://docs.astral.sh/uv/) |
| **Claude Code** | [Install](https://claude.ai/code) |

#### Installing GAP

**macOS (Homebrew):**
```bash
brew install gap
```

**Ubuntu / Debian:**
```bash
sudo apt-get install gap
```

**From source / official installer:** see https://www.gap-system.org/Releases/

### Install gap-mcp

```bash
git clone https://github.com/cesarneyit-code/gap-mcp.git
cd gap-mcp
uv sync
```

### Register with Claude Code

```bash
claude mcp add --transport stdio gap-mcp --scope user -- \
  uv run --directory /path/to/gap-mcp python -m gap_mcp.server
```

If GAP is not on your `PATH`, pass the executable path explicitly:

```bash
claude mcp add --transport stdio gap-mcp --scope user -- \
  uv run --directory /path/to/gap-mcp python -m gap_mcp.server \
  --gap-executable /usr/local/bin/gap
```

You can also set the environment variable `GAP_EXECUTABLE` instead of using
the `--gap-executable` flag.

---

## Available Tools

| Tool | Description |
|------|-------------|
| `gap_eval` | Execute arbitrary GAP code |
| `gap_group_info` | Order, abelian, simple, solvable, nilpotent, exponent, #classes |
| `gap_elements` | List elements with their orders (or generators for large groups) |
| `gap_subgroups` | All subgroups or normal subgroups; size guard for large groups |
| `gap_character_table` | Full character table of a group |
| `gap_sylow` | Sylow p-subgroup, order, count, normality |
| `gap_center` | Center Z(G): order, elements, whether G/Z(G) is cyclic |
| `gap_derived_series` | Derived series, composition series, and solvability |
| `gap_conjugacy_classes` | Conjugacy classes with representative, size, and order |
| `gap_isomorphism` | Test isomorphism and exhibit an explicit isomorphism |
| `gap_abelian_invariants` | Invariant factor decomposition of G or its abelianization |
| `gap_automorphisms` | Aut(G), Inn(G), Out(G) |
| `gap_load_package` | Load a GAP package (GRAPE, Hecke, cohomolo, …) |
| `gap_reset` | Reset the GAP session, clearing all variables |

---

## Example Prompts

Once installed, you can ask Claude things like:

- *"Compute the character table of A5 using GAP"*
- *"How many Sylow 2-subgroups does S4 have? Verify Sylow's theorem."*
- *"Is the alternating group A5 simple? Show the derived series."*
- *"Find all normal subgroups of the dihedral group D8"*
- *"Are SymmetricGroup(3) and DihedralGroup(6) isomorphic?"*
- *"What are the abelian invariants of Z_2 × Z_4 × Z_3?"*
- *"Compute Aut(Z_8) and Out(Z_8)"*
- *"Use GAP to verify that Z_6 is abelian but S3 is not"*

---

## How it works

The server maintains a **persistent GAP process** — avoiding the ~2 s startup
overhead on every call. Commands are sent to GAP via stdin and output is
collected using a sentinel token (`__GAPDONE__`).

```
Claude Code / any MCP client
        ↕  JSON-RPC over stdio
  FastMCP server  (server.py)
        ↕  Python function call
  gap_runner.py  (persistent subprocess manager)
        ↕  stdin / stdout pipes
  GAP process  (gap -q)
```

### Security

Dangerous GAP commands (`QUIT`, `Exec(`, `Process(`, `IO_`, `Filename(`) are
blocked before reaching the subprocess. Use `gap_reset` to restart the session
instead of `QUIT`.

---

## Development

```bash
uv sync --group dev
uv run pytest tests/ -v          # all tests (GAP required)
uv run pytest -m "not integration"  # unit tests only
uv run ruff check gap_mcp/ tests/
uv run mypy gap_mcp/
```

See [CONTRIBUTING.md](CONTRIBUTING.md) for more details.

---

## Troubleshooting

**`GAP executable not found`**
→ Install GAP or set `GAP_EXECUTABLE=/path/to/gap` in your environment.

**`GAP did not respond within 60s`**
→ The computation is too large. Try a smaller group, use `gap_reset()` to
  clear state, or increase the `timeout` parameter in `gap_eval`.

**Tools not appearing in Claude**
→ Run `claude mcp list` to verify registration. Restart Claude Code after
  adding a new MCP server.

**Package not found in `gap_load_package`**
→ Run `gap_eval('ShowPackageInformation();')` to list available packages, or
  install additional GAP packages from https://packages.gap-system.org/.

---

## License

MIT — see [LICENSE](LICENSE)

## Author

César Galindo
[cesarneyit@gmail.com](mailto:cesarneyit@gmail.com)
[github.com/cesarneyit-code](https://github.com/cesarneyit-code)
