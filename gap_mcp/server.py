"""
GAP MCP Server — Model Context Protocol server for GAP (Groups, Algorithms, Programming).

Exposes GAP's computational group theory capabilities as MCP tools,
allowing Claude and other LLM clients to perform exact symbolic computations
in group theory, representation theory, and computational discrete algebra.
"""

import logging
from typing import Optional
from mcp.server.fastmcp import FastMCP
from .gap_runner import get_runner

logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────
# Server initialization
# ─────────────────────────────────────────────

mcp = FastMCP(
    "gap-mcp",
    dependencies=["gap"],
    instructions=(
        "Provides access to GAP (Groups, Algorithms, Programming) for exact "
        "computational group theory. Use gap_eval for arbitrary GAP code, or the "
        "specialized tools for common operations like subgroups, character tables, "
        "Sylow subgroups, etc. GAP uses multiplicative notation for groups by default. "
        "Elements are permutations written as Cycles, e.g. (1,2,3). "
        "Always prefer specialized tools over gap_eval when available."
    ),
)


# ─────────────────────────────────────────────
# Tool 1: Arbitrary GAP code execution
# ─────────────────────────────────────────────

@mcp.tool()
def gap_eval(code: str, timeout: int = 30) -> str:
    """
    Execute arbitrary GAP code and return the output.

    Use this for any GAP computation not covered by the specialized tools.
    GAP uses multiplicative notation. Statements must end with semicolons.

    Args:
        code: Valid GAP code. Example: 'Order(SymmetricGroup(4));'
        timeout: Maximum seconds to wait (default 30, increase for heavy computations)

    Examples:
        gap_eval('Order(SymmetricGroup(4));')           -> '24'
        gap_eval('Factorial(10);')                      -> '3628800'
        gap_eval('x := 2^10; Print(x, "\\n");')        -> '1024'
        gap_eval('IsPrime(104729);')                    -> 'true'
    """
    runner = get_runner()
    result = runner.execute(code, timeout=timeout)
    if not result["success"] and result["error"]:
        return f"GAP Error:\n{result['error']}"
    return result["output"] or "(no output)"


# ─────────────────────────────────────────────
# Tool 2: Group information
# ─────────────────────────────────────────────

@mcp.tool()
def gap_group_info(group_expr: str) -> str:
    """
    Return a summary of key properties of a group.

    Computes: order, abelian, simple, solvable, nilpotent, number of conjugacy classes.

    Args:
        group_expr: A GAP expression that evaluates to a group.
                    Examples: 'SymmetricGroup(4)', 'CyclicGroup(12)',
                              'DihedralGroup(8)', 'AlternatingGroup(5)',
                              'SmallGroup(16,5)'

    Examples:
        gap_group_info('SymmetricGroup(4)')   -> order 24, not abelian, solvable, ...
        gap_group_info('CyclicGroup(6)')      -> order 6, abelian, ...
        gap_group_info('AlternatingGroup(5)') -> order 60, simple, ...
    """
    code = f"""
G := {group_expr};
Print("Order: ", Order(G), "\\n");
Print("IsAbelian: ", IsAbelian(G), "\\n");
Print("IsSimple: ", IsSimple(G), "\\n");
Print("IsSolvable: ", IsSolvable(G), "\\n");
Print("IsNilpotent: ", IsNilpotentGroup(G), "\\n");
Print("NrConjugacyClasses: ", NrConjugacyClasses(G), "\\n");
Print("Exponent: ", Exponent(G), "\\n");
"""
    result = get_runner().execute(code)
    if not result["success"] and result["error"]:
        return f"GAP Error:\n{result['error']}"
    return result["output"]


# ─────────────────────────────────────────────
# Tool 3: Group elements
# ─────────────────────────────────────────────

@mcp.tool()
def gap_elements(group_expr: str, max_order: int = 12) -> str:
    """
    List elements and their orders in a group.

    For large groups (order > max_order), only generators are shown.

    Args:
        group_expr: GAP group expression.
        max_order: Maximum group order to list all elements (default 12).

    Examples:
        gap_elements('CyclicGroup(6)')    -> lists all 6 elements with orders
        gap_elements('SymmetricGroup(3)') -> lists all 6 permutations
        gap_elements('SymmetricGroup(6)') -> shows generators only (order 720)
    """
    code = f"""
G := {group_expr};
ord := Order(G);
if ord <= {max_order} then
  elts := Elements(G);
  for g in elts do
    Print(g, " (order ", Order(g), ")\\n");
  od;
else
  Print("Group too large (order ", ord, ") to list all elements.\\n");
  Print("Generators:\\n");
  for g in GeneratorsOfGroup(G) do
    Print("  ", g, "\\n");
  od;
fi;
"""
    result = get_runner().execute(code)
    if not result["success"] and result["error"]:
        return f"GAP Error:\n{result['error']}"
    return result["output"]


# ─────────────────────────────────────────────
# Tool 4: Subgroups
# ─────────────────────────────────────────────

@mcp.tool()
def gap_subgroups(group_expr: str, normal_only: bool = False) -> str:
    """
    Compute subgroups (or normal subgroups) of a group.

    Args:
        group_expr: GAP group expression.
        normal_only: If True, return only normal subgroups (default False).

    Examples:
        gap_subgroups('SymmetricGroup(3)')              -> all subgroups with orders
        gap_subgroups('SymmetricGroup(4)', normal_only=True) -> normal subgroups
        gap_subgroups('DihedralGroup(8)')               -> lattice of subgroups
    """
    if normal_only:
        code = f"""
G := {group_expr};
ns := NormalSubgroups(G);
Print("Normal subgroups of G (order ", Order(G), "):\\n");
for H in ns do
  Print("  Order ", Order(H), ": ", H, "\\n");
od;
Print("Total: ", Length(ns), " normal subgroups\\n");
"""
    else:
        code = f"""
G := {group_expr};
sub := AllSubgroups(G);
Print("Subgroups of G (order ", Order(G), "):\\n");
for H in sub do
  isNorm := "";
  if IsNormal(G, H) then isNorm := " [normal]"; fi;
  Print("  Order ", Order(H), isNorm, ": ", H, "\\n");
od;
Print("Total: ", Length(sub), " subgroups\\n");
"""
    result = get_runner().execute(code, timeout=60)
    if not result["success"] and result["error"]:
        return f"GAP Error:\n{result['error']}"
    return result["output"]


# ─────────────────────────────────────────────
# Tool 5: Character table
# ─────────────────────────────────────────────

@mcp.tool()
def gap_character_table(group_expr: str) -> str:
    """
    Compute and display the character table of a group.

    Shows irreducible characters, conjugacy classes, and character degrees.

    Args:
        group_expr: GAP group expression.

    Examples:
        gap_character_table('SymmetricGroup(4)')  -> full character table of S4
        gap_character_table('CyclicGroup(6)')     -> character table of Z_6
        gap_character_table('AlternatingGroup(5)') -> character table of A5
    """
    code = f"""
G := {group_expr};
T := CharacterTable(G);
Display(T);
"""
    result = get_runner().execute(code, timeout=60)
    if not result["success"] and result["error"]:
        return f"GAP Error:\n{result['error']}"
    return result["output"]


# ─────────────────────────────────────────────
# Tool 6: Sylow subgroups
# ─────────────────────────────────────────────

@mcp.tool()
def gap_sylow(group_expr: str, prime: int) -> str:
    """
    Compute the Sylow p-subgroup of a group.

    Also reports the number of Sylow p-subgroups (verifying Sylow's theorems).

    Args:
        group_expr: GAP group expression.
        prime: A prime number p.

    Examples:
        gap_sylow('SymmetricGroup(4)', 2) -> Sylow 2-subgroup of S4 (order 8)
        gap_sylow('SymmetricGroup(4)', 3) -> Sylow 3-subgroup of S4 (order 3)
        gap_sylow('AlternatingGroup(5)', 5) -> Sylow 5-subgroup of A5
    """
    code = f"""
G := {group_expr};
p := {prime};
if not IsPrime(p) then
  Print("Error: ", p, " is not prime\\n");
else
  S := SylowSubgroup(G, p);
  nS := Length(ConjugateSubgroups(G, S));
  Print("Group order: ", Order(G), "\\n");
  Print("Sylow ", p, "-subgroup order: ", Order(S), "\\n");
  Print("Number of Sylow ", p, "-subgroups: ", nS, "\\n");
  Print("Sylow subgroup: ", S, "\\n");
  Print("Is normal: ", IsNormal(G, S), "\\n");
fi;
"""
    result = get_runner().execute(code)
    if not result["success"] and result["error"]:
        return f"GAP Error:\n{result['error']}"
    return result["output"]


# ─────────────────────────────────────────────
# Tool 7: Center of a group
# ─────────────────────────────────────────────

@mcp.tool()
def gap_center(group_expr: str) -> str:
    """
    Compute the center Z(G) of a group and its properties.

    Args:
        group_expr: GAP group expression.

    Examples:
        gap_center('SymmetricGroup(4)')  -> trivial center
        gap_center('DihedralGroup(4)')   -> center of order 2
        gap_center('CyclicGroup(6)')     -> center = whole group (abelian)
    """
    code = f"""
G := {group_expr};
Z := Center(G);
Print("Center Z(G):\\n");
Print("  Order: ", Order(Z), "\\n");
Print("  Elements: ", Elements(Z), "\\n");
Print("  G/Z(G) is cyclic: ", IsCyclic(G/Z), "\\n");
"""
    result = get_runner().execute(code)
    if not result["success"] and result["error"]:
        return f"GAP Error:\n{result['error']}"
    return result["output"]


# ─────────────────────────────────────────────
# Tool 8: Derived series and solvability
# ─────────────────────────────────────────────

@mcp.tool()
def gap_derived_series(group_expr: str) -> str:
    """
    Compute the derived series and composition series of a group.

    Useful for determining solvability and the structure of a group.

    Args:
        group_expr: GAP group expression.

    Examples:
        gap_derived_series('SymmetricGroup(4)') -> derived series ending at {1}
        gap_derived_series('AlternatingGroup(5)') -> simple group, series length 2
        gap_derived_series('DihedralGroup(8)')    -> derived series of D_8
    """
    code = f"""
G := {group_expr};
ds := DerivedSeriesOfGroup(G);
Print("Derived series (length ", Length(ds), "):\\n");
for i in [1..Length(ds)] do
  Print("  G^(", i-1, "): order ", Order(ds[i]), "\\n");
od;
Print("IsSolvable: ", IsSolvable(G), "\\n");
cs := CompositionSeries(G);
Print("Composition series (length ", Length(cs), "):\\n");
for i in [1..Length(cs)] do
  Print("  order ", Order(cs[i]), "\\n");
od;
"""
    result = get_runner().execute(code, timeout=60)
    if not result["success"] and result["error"]:
        return f"GAP Error:\n{result['error']}"
    return result["output"]


# ─────────────────────────────────────────────
# Tool 9: Load GAP package
# ─────────────────────────────────────────────

@mcp.tool()
def gap_load_package(package_name: str) -> str:
    """
    Load a GAP package (e.g. GRAPE, Hecke, FinInG, etc.).

    Args:
        package_name: Name of the GAP package to load.

    Examples:
        gap_load_package('GRAPE')   -> loads graph theory package
        gap_load_package('Hecke')   -> loads Hecke algebras package
        gap_load_package('cohomolo') -> loads group cohomology package
    """
    code = f"""
if LoadPackage("{package_name}") = true then
  Print("Package {package_name} loaded successfully.\\n");
else
  Print("Failed to load package {package_name}.\\n");
  Print("Available packages: use 'gap_eval' with 'DisplayPackageInformation(\"{package_name}\");'\\n");
fi;
"""
    result = get_runner().execute(code, timeout=30)
    if not result["success"] and result["error"]:
        return f"GAP Error:\n{result['error']}"
    return result["output"]


# ─────────────────────────────────────────────
# Tool 10: Reset session
# ─────────────────────────────────────────────

@mcp.tool()
def gap_reset() -> str:
    """
    Reset the GAP session, clearing all variables and defined objects.

    Use this when the GAP state has become inconsistent or you want
    to start fresh with no previously defined variables.
    """
    result = get_runner().reset()
    return result["output"]


# ─────────────────────────────────────────────
# Entry point
# ─────────────────────────────────────────────

def main():
    import argparse
    logging.basicConfig(level=logging.WARNING)

    parser = argparse.ArgumentParser(description="GAP MCP Server")
    parser.add_argument(
        "--gap-executable",
        type=str,
        help="Path to GAP executable (auto-detected if not provided)",
    )
    args = parser.parse_args()

    if args.gap_executable:
        import os
        os.environ["GAP_EXECUTABLE"] = args.gap_executable

    mcp.run()


if __name__ == "__main__":
    main()
