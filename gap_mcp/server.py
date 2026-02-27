"""
GAP MCP Server — Model Context Protocol server for GAP (Groups, Algorithms, Programming).

Exposes GAP's computational group theory capabilities as MCP tools,
allowing Claude and other LLM clients to perform exact symbolic computations
in group theory, representation theory, and computational discrete algebra.
"""

import logging
import os
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
        "specialized tools for common operations. GAP uses multiplicative notation "
        "for groups by default. Elements are permutations written as Cycles, "
        "e.g. (1,2,3). Statements must end with semicolons. "
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
    Multiline code (for/od, if/fi, etc.) is supported.

    Args:
        code:    Valid GAP code. May be multiline.
        timeout: Maximum seconds to wait (default 30; increase for heavy computations).

    Examples:
        gap_eval('Order(SymmetricGroup(4));')           -> '24'
        gap_eval('Factorial(10);')                      -> '3628800'
        gap_eval('IsPrime(104729);')                    -> 'true'
        gap_eval('for i in [1..5] do Print(i,"\\n"); od;')
    """
    runner = get_runner()
    result = runner.execute(code, timeout=timeout)
    if not result["success"]:
        return f"GAP Error:\n{result['error']}"
    return result["output"] or "(no output)"


# ─────────────────────────────────────────────
# Tool 2: Group information
# ─────────────────────────────────────────────

@mcp.tool()
def gap_group_info(group_expr: str) -> str:
    """
    Return a structured summary of key properties of a group.

    Computes: order, abelian, simple, solvable, nilpotent,
    exponent, and number of conjugacy classes.

    Args:
        group_expr: A GAP expression that evaluates to a group.
                    Examples: 'SymmetricGroup(4)', 'CyclicGroup(12)',
                              'DihedralGroup(8)', 'AlternatingGroup(5)',
                              'SmallGroup(16,5)', 'GL(2,3)'
    """
    code = f"""
G := {group_expr};
Print("Order: ", Order(G), "\\n");
Print("IsAbelian: ", IsAbelian(G), "\\n");
Print("IsSimple: ", IsSimple(G), "\\n");
Print("IsSolvable: ", IsSolvable(G), "\\n");
Print("IsNilpotent: ", IsNilpotentGroup(G), "\\n");
Print("Exponent: ", Exponent(G), "\\n");
Print("NrConjugacyClasses: ", NrConjugacyClasses(G), "\\n");
"""
    result = get_runner().execute(code)
    if not result["success"]:
        return f"GAP Error:\n{result['error']}"
    return result["output"]


# ─────────────────────────────────────────────
# Tool 3: Group elements
# ─────────────────────────────────────────────

@mcp.tool()
def gap_elements(group_expr: str, max_order: int = 24) -> str:
    """
    List elements and their orders in a group.

    For large groups (order > max_order), only generators are shown.

    Args:
        group_expr: GAP group expression.
        max_order:  Maximum group order to list all elements (default 24).
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
    if not result["success"]:
        return f"GAP Error:\n{result['error']}"
    return result["output"]


# ─────────────────────────────────────────────
# Tool 4: Subgroups
# ─────────────────────────────────────────────

@mcp.tool()
def gap_subgroups(group_expr: str, normal_only: bool = False) -> str:
    """
    Compute subgroups (or normal subgroups) of a group.

    Warning: AllSubgroups is expensive for groups of order > 100.
    For large groups use normal_only=True or gap_sylow/gap_derived_series.

    Args:
        group_expr:  GAP group expression.
        normal_only: If True, return only normal subgroups (faster).
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
ord := Order(G);
if ord > 500 then
  Print("Warning: group order ", ord, " is large. Use normal_only=True or ");
  Print("specialized tools to avoid long computation.\\n");
  Print("Showing normal subgroups only:\\n");
  ns := NormalSubgroups(G);
  for H in ns do
    Print("  Order ", Order(H), " [normal]: ", H, "\\n");
  od;
else
  sub := AllSubgroups(G);
  Print("Subgroups of G (order ", ord, "):\\n");
  for H in sub do
    isNorm := "";
    if IsNormal(G, H) then isNorm := " [normal]"; fi;
    Print("  Order ", Order(H), isNorm, ": ", H, "\\n");
  od;
  Print("Total: ", Length(sub), " subgroups\\n");
fi;
"""
    result = get_runner().execute(code, timeout=90)
    if not result["success"]:
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
        gap_character_table('SymmetricGroup(4)')   -> full character table of S4
        gap_character_table('AlternatingGroup(5)') -> character table of A5
    """
    code = f"""
G := {group_expr};
T := CharacterTable(G);
Display(T);
"""
    result = get_runner().execute(code, timeout=60)
    if not result["success"]:
        return f"GAP Error:\n{result['error']}"
    return result["output"]


# ─────────────────────────────────────────────
# Tool 6: Sylow subgroups
# ─────────────────────────────────────────────

@mcp.tool()
def gap_sylow(group_expr: str, prime: int) -> str:
    """
    Compute the Sylow p-subgroup of a group and verify Sylow's theorems.

    Reports the Sylow subgroup, its order, the number of conjugates,
    and whether it is normal.

    Args:
        group_expr: GAP group expression.
        prime:      A prime number p.
    """
    code = f"""
G := {group_expr};
p := {prime};
if not IsPrime(p) then
  Print("Error: ", p, " is not prime.\\n");
else
  S := SylowSubgroup(G, p);
  nS := Length(ConjugateSubgroups(G, S));
  Print("Group order:                ", Order(G), "\\n");
  Print("Sylow ", p, "-subgroup order: ", Order(S), "\\n");
  Print("Number of Sylow ", p, "-subgroups: ", nS, "\\n");
  Print("Is normal:                  ", IsNormal(G, S), "\\n");
  Print("Sylow subgroup:             ", S, "\\n");
fi;
"""
    result = get_runner().execute(code)
    if not result["success"]:
        return f"GAP Error:\n{result['error']}"
    return result["output"]


# ─────────────────────────────────────────────
# Tool 7: Center
# ─────────────────────────────────────────────

@mcp.tool()
def gap_center(group_expr: str) -> str:
    """
    Compute the center Z(G) of a group.

    Reports order, generators, and whether G/Z(G) is cyclic.
    Elements are only listed for small centers (order ≤ 20).

    Args:
        group_expr: GAP group expression.
    """
    code = f"""
G := {group_expr};
cZ := Center(G);
ordG := Order(G);
ordZ := Order(cZ);
Print("Center Z(G) order: ", ordZ, "\\n");
if ordZ <= 20 then
  Print("Elements: ", Elements(cZ), "\\n");
else
  Print("Generators: ", GeneratorsOfGroup(cZ), "\\n");
fi;
if ordZ = ordG then
  Print("G/Z(G) is cyclic: true (G is abelian)\\n");
elif ordZ = 1 then
  if ordG = 1 then
    Print("G/Z(G) is cyclic: true (trivial group)\\n");
  else
    Print("G/Z(G) is cyclic: false (Z(G) trivial so G/Z(G) non-abelian)\\n");
  fi;
else
  Print("G/Z(G) is cyclic: ", IsCyclic(G/cZ), "\\n");
fi;
"""
    result = get_runner().execute(code)
    if not result["success"]:
        return f"GAP Error:\n{result['error']}"
    return result["output"]


# ─────────────────────────────────────────────
# Tool 8: Derived series and solvability
# ─────────────────────────────────────────────

@mcp.tool()
def gap_derived_series(group_expr: str) -> str:
    """
    Compute the derived series and composition series of a group.

    Useful for determining solvability and the Jordan-Hölder structure.

    Args:
        group_expr: GAP group expression.
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
    if not result["success"]:
        return f"GAP Error:\n{result['error']}"
    return result["output"]


# ─────────────────────────────────────────────
# Tool 9: Conjugacy classes
# ─────────────────────────────────────────────

@mcp.tool()
def gap_conjugacy_classes(group_expr: str) -> str:
    """
    List conjugacy classes with a representative and size for each.

    Args:
        group_expr: GAP group expression.

    Examples:
        gap_conjugacy_classes('SymmetricGroup(4)') -> 5 classes of S4
        gap_conjugacy_classes('AlternatingGroup(5)') -> 5 classes of A5
    """
    code = f"""
G := {group_expr};
cls := ConjugacyClasses(G);
Print("Conjugacy classes of G (order ", Order(G), "):\\n");
for c in cls do
  Print("  [", Representative(c), "]  size=", Size(c),
        "  order=", Order(Representative(c)), "\\n");
od;
Print("Total: ", Length(cls), " classes\\n");
"""
    result = get_runner().execute(code)
    if not result["success"]:
        return f"GAP Error:\n{result['error']}"
    return result["output"]


# ─────────────────────────────────────────────
# Tool 10: Isomorphism testing
# ─────────────────────────────────────────────

@mcp.tool()
def gap_isomorphism(group_expr1: str, group_expr2: str) -> str:
    """
    Test whether two groups are isomorphic and, if so, exhibit an isomorphism.

    Args:
        group_expr1: GAP expression for the first group.
        group_expr2: GAP expression for the second group.

    Examples:
        gap_isomorphism('SymmetricGroup(3)', 'DihedralGroup(6)')  -> isomorphic
        gap_isomorphism('CyclicGroup(4)', 'DihedralGroup(4)')     -> not isomorphic
        gap_isomorphism('SmallGroup(8,3)', 'QuaternionGroup(8)')  -> check Q8 vs D4
    """
    code = f"""
G := {group_expr1};
H := {group_expr2};
if Order(G) <> Order(H) then
  Print("Not isomorphic (different orders: ", Order(G), " vs ", Order(H), ").\\n");
else
  phi := IsomorphismGroups(G, H);
  if phi = fail then
    Print("Not isomorphic (same order ", Order(G), " but different structure).\\n");
  else
    Print("Isomorphic! Orders: ", Order(G), "\\n");
    Print("Isomorphism found: ", phi, "\\n");
    Print("Generator images:\\n");
    for g in GeneratorsOfGroup(G) do
      Print("  ", g, " -> ", Image(phi, g), "\\n");
    od;
  fi;
fi;
"""
    result = get_runner().execute(code, timeout=60)
    if not result["success"]:
        return f"GAP Error:\n{result['error']}"
    return result["output"]


# ─────────────────────────────────────────────
# Tool 11: Abelian invariants
# ─────────────────────────────────────────────

@mcp.tool()
def gap_abelian_invariants(group_expr: str) -> str:
    """
    Compute the abelian invariants (invariant factor decomposition) of a group.

    For an abelian group G ≅ Z_{n1} × … × Z_{nk}, returns [n1, …, nk].
    Also works for the abelianization G/[G,G] of a non-abelian group.

    Args:
        group_expr: GAP group expression.

    Examples:
        gap_abelian_invariants('CyclicGroup(12)')          -> [ 12 ] = Z_12
        gap_abelian_invariants('AbelianGroup([2,4,3])')    -> [ 2, 4, 3 ]
        gap_abelian_invariants('SymmetricGroup(4)')        -> [2] (abelianization = Z_2)
        gap_abelian_invariants('AlternatingGroup(5)')      -> [] (perfect group)
    """
    code = f"""
G := {group_expr};
inv := AbelianInvariants(G);
if Length(inv) = 0 then
  Print("Abelian invariants: [] (trivial or perfect group)\\n");
else
  Print("Abelian invariants: ", inv, "\\n");
  Print("Structure: ");
  for i in [1..Length(inv)] do
    if i > 1 then Print(" x "); fi;
    Print("Z_", inv[i]);
  od;
  Print("\\n");
fi;
Print("IsAbelian: ", IsAbelian(G), "\\n");
"""
    result = get_runner().execute(code)
    if not result["success"]:
        return f"GAP Error:\n{result['error']}"
    return result["output"]


# ─────────────────────────────────────────────
# Tool 12: Automorphism group
# ─────────────────────────────────────────────

@mcp.tool()
def gap_automorphisms(group_expr: str) -> str:
    """
    Compute the automorphism group Aut(G) of a group.

    Reports |Aut(G)|, |Inn(G)|, |Out(G)| = |Aut(G)/Inn(G)|.

    Args:
        group_expr: GAP group expression.

    Examples:
        gap_automorphisms('CyclicGroup(8)')    -> Aut(Z_8) ≅ Z_2 x Z_2, order 4
        gap_automorphisms('SymmetricGroup(6)') -> Aut(S6), the exceptional case
    """
    code = f"""
G := {group_expr};
A := AutomorphismGroup(G);
Print("Aut(G) order:  ", Order(A), "\\n");
inn := InnerAutomorphismsAutomorphismGroup(A);
Print("Inn(G) order:  ", Order(inn), "\\n");
Print("Out(G) order:  ", Order(A) / Order(inn), "\\n");
Print("Aut(G): ", A, "\\n");
"""
    result = get_runner().execute(code, timeout=60)
    if not result["success"]:
        return f"GAP Error:\n{result['error']}"
    return result["output"]


# ─────────────────────────────────────────────
# Tool 13: Load GAP package
# ─────────────────────────────────────────────

@mcp.tool()
def gap_load_package(package_name: str) -> str:
    """
    Load a GAP package (e.g. GRAPE, Hecke, cohomolo, FinInG).

    Args:
        package_name: Name of the GAP package to load.

    Examples:
        gap_load_package('GRAPE')    -> graph theory package
        gap_load_package('cohomolo') -> group cohomology
        gap_load_package('Hecke')    -> Hecke algebras
    """
    code = f"""
if LoadPackage("{package_name}") = true then
  Print("Package {package_name} loaded successfully.\\n");
else
  Print("Failed to load package {package_name}.\\n");
  Print("To list available packages, run: gap_eval('ShowPackageInformation();')\\n");
fi;
"""
    result = get_runner().execute(code, timeout=30)
    if not result["success"]:
        return f"GAP Error:\n{result['error']}"
    return result["output"]


# ─────────────────────────────────────────────
# Tool 14: Reset session
# ─────────────────────────────────────────────

@mcp.tool()
def gap_reset() -> str:
    """
    Reset the GAP session, clearing all variables and defined objects.

    Use this when the GAP state has become inconsistent or you want
    to start a computation from a clean slate.
    """
    result = get_runner().reset()
    return result["output"]


# ─────────────────────────────────────────────
# Entry point
# ─────────────────────────────────────────────

def main() -> None:
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
        os.environ["GAP_EXECUTABLE"] = args.gap_executable

    mcp.run()


if __name__ == "__main__":
    main()
