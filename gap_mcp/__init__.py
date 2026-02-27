"""gap-mcp — MCP server for GAP (Groups, Algorithms, Programming)."""

from .gap_runner import GAPRunner, get_runner
from .server import mcp, main

__version__ = "0.1.0"
__all__ = ["GAPRunner", "get_runner", "mcp", "main"]
