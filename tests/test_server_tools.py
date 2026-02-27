"""Integration tests for server.py MCP tools."""

import pytest
from gap_mcp.server import (
    gap_eval, gap_group_info, gap_elements, gap_subgroups,
    gap_sylow, gap_center, gap_derived_series, gap_conjugacy_classes,
    gap_isomorphism, gap_abelian_invariants, gap_automorphisms,
)


@pytest.mark.integration
class TestServerTools:

    def test_gap_eval_arithmetic(self, gap_available):
        result = gap_eval("Factorial(5);")
        assert "120" in result

    def test_gap_eval_multiline(self, gap_available):
        code = "total := 0;\nfor i in [1..4] do total := total + i; od;\nPrint(total, \"\\n\");"
        result = gap_eval(code)
        assert "10" in result

    def test_gap_group_info_s4(self, gap_available):
        result = gap_group_info("SymmetricGroup(4)")
        assert "Order: 24" in result
        assert "IsAbelian: false" in result
        assert "IsSolvable: true" in result
        assert "IsSimple: false" in result

    def test_gap_group_info_a5(self, gap_available):
        result = gap_group_info("AlternatingGroup(5)")
        assert "Order: 60" in result
        assert "IsSimple: true" in result
        assert "IsSolvable: false" in result

    def test_gap_elements_small(self, gap_available):
        result = gap_elements("CyclicGroup(4)")
        assert "order" in result

    def test_gap_elements_large_shows_generators(self, gap_available):
        result = gap_elements("SymmetricGroup(5)", max_order=10)
        assert "too large" in result or "Generators" in result

    def test_gap_subgroups_normal(self, gap_available):
        result = gap_subgroups("SymmetricGroup(3)", normal_only=True)
        assert "Normal subgroups" in result
        assert "Total:" in result

    def test_gap_sylow_s4_p2(self, gap_available):
        result = gap_sylow("SymmetricGroup(4)", 2)
        assert "8" in result   # Sylow 2-subgroup of S4 has order 8
        assert "3" in result   # there are 3 Sylow 2-subgroups

    def test_gap_sylow_not_prime(self, gap_available):
        result = gap_sylow("SymmetricGroup(4)", 4)
        assert "not prime" in result

    def test_gap_center_s4_trivial(self, gap_available):
        result = gap_center("SymmetricGroup(4)")
        assert "order: 1" in result
        assert "false" in result   # G/Z(G) is not cyclic

    def test_gap_derived_series_a5_simple(self, gap_available):
        result = gap_derived_series("AlternatingGroup(5)")
        assert "IsSolvable: false" in result

    def test_gap_conjugacy_classes_s4(self, gap_available):
        result = gap_conjugacy_classes("SymmetricGroup(4)")
        assert "Total: 5 classes" in result

    def test_gap_isomorphism_s3_d6(self, gap_available):
        result = gap_isomorphism("SymmetricGroup(3)", "DihedralGroup(6)")
        assert "Isomorphic" in result

    def test_gap_isomorphism_different_orders(self, gap_available):
        result = gap_isomorphism("CyclicGroup(4)", "CyclicGroup(6)")
        assert "Not isomorphic" in result

    def test_gap_abelian_invariants_cyclic(self, gap_available):
        result = gap_abelian_invariants("CyclicGroup(12)")
        assert "12" in result

    def test_gap_abelian_invariants_s4(self, gap_available):
        result = gap_abelian_invariants("SymmetricGroup(4)")
        # Abelianization of S4 is Z_2
        assert "2" in result

    def test_gap_abelian_invariants_a5_perfect(self, gap_available):
        result = gap_abelian_invariants("AlternatingGroup(5)")
        assert "trivial or perfect" in result

    def test_gap_automorphisms_cyclic8(self, gap_available):
        result = gap_automorphisms("CyclicGroup(8)")
        assert "Aut(G) order:  4" in result  # Aut(Z_8) has order 4
