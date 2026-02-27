# gap-mcp

**Model Context Protocol server for GAP (Groups, Algorithms, Programming)**

Connects Claude and other MCP-compatible AI assistants to [GAP](https://www.gap-system.org/), the open-source computer algebra system for computational discrete algebra — with particular emphasis on computational group theory.

> This is the first publicly available MCP server for GAP.

---

## What is GAP?

GAP is a system for computational discrete algebra, specializing in:
- Finite group theory (permutation groups, matrix groups, finitely presented groups)
- Representation theory and character tables
- Combinatorics and graph theory
- Number theory

## What does this MCP do?

It allows Claude to perform **exact symbolic computations** in group theory by calling GAP directly — instead of approximating or reasoning from memory.

```
You: "What are the Sylow 2-subgroups of S4?"
Claude → calls gap_sylow('SymmetricGroup(4)', 2)
GAP   → returns exact answer
Claude → explains the result
```

---

## Installation

### Requirements
- [GAP](https://www.gap-system.org/Releases/) installed on your system
- Python ≥ 3.11
- [uv](https://docs.astral.sh/uv/) package manager
- [Claude Code](https://claude.ai/code)

### Install

```bash
git clone https://github.com/cesargalindo/gap-mcp.git
cd gap-mcp
uv sync
```

### Register with Claude Code

```bash
claude mcp add --transport stdio gap-mcp --scope user -- \
  uv run --directory /path/to/gap-mcp python -m gap_mcp.server
```

If GAP is not on your PATH, specify the executable:

```bash
claude mcp add --transport stdio gap-mcp --scope user -- \
  uv run --directory /path/to/gap-mcp python -m gap_mcp.server \
  --gap-executable /path/to/gap
```

---

## Available Tools

| Tool | Description |
|------|-------------|
| `gap_eval` | Execute arbitrary GAP code |
| `gap_group_info` | Order, abelian, simple, solvable, nilpotent, exponent |
| `gap_elements` | List elements with their orders |
| `gap_subgroups` | All subgroups or normal subgroups only |
| `gap_character_table` | Full character table of a group |
| `gap_sylow` | Sylow p-subgroup and count |
| `gap_center` | Center Z(G) |
| `gap_derived_series` | Derived series and composition series |
| `gap_load_package` | Load a GAP package (GRAPE, Hecke, etc.) |
| `gap_reset` | Reset the GAP session |

---

## Example Prompts

Once installed, you can ask Claude things like:

- *"Compute the character table of A5 using GAP"*
- *"How many Sylow 2-subgroups does S4 have? Verify Sylow's theorem."*
- *"Is the alternating group A5 simple? Show the derived series."*
- *"Find all normal subgroups of the dihedral group D8"*
- *"Compute the center of SymmetricGroup(4)"*
- *"Use GAP to verify that Z_6 is abelian but S3 is not"*

---

## How it works

The server maintains a **persistent GAP process** — avoiding the ~2s startup overhead on every call. Commands are sent via stdin and output is collected using a sentinel token.

```
FastMCP server (Python)
    ↕ JSON-RPC over stdio
Claude Code / any MCP client
    ↕
gap_runner.py (persistent subprocess)
    ↕ stdin/stdout pipes
GAP process (gap -q)
```

---

## License

MIT — see [LICENSE](LICENSE)

## Author

César Galindo
