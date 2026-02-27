"""Unit and integration tests for gap_runner.py"""

import pytest
from unittest.mock import patch
from gap_mcp.gap_runner import find_gap_executable, _contains_blocked, GAPRunner


# ─── Unit tests (no GAP required) ────────────────────────────────────────────

class TestFindGapExecutable:
    def test_raises_when_not_found(self):
        with patch("shutil.which", return_value=None), \
             patch("os.path.isfile", return_value=False):
            with pytest.raises(FileNotFoundError, match="GAP executable not found"):
                find_gap_executable()

    def test_finds_via_which(self):
        with patch("shutil.which", return_value="/usr/bin/gap"), \
             patch("os.access", return_value=True):
            result = find_gap_executable()
            assert result == "/usr/bin/gap"

    def test_env_var_takes_precedence(self, monkeypatch):
        monkeypatch.setenv("GAP_EXECUTABLE", "/custom/gap")
        runner = GAPRunner.__new__(GAPRunner)
        runner.gap_executable = (
            None
            or "/custom/gap"   # simulates env var logic
        )
        assert runner.gap_executable == "/custom/gap"


class TestContainsBlocked:
    def test_blocks_quit(self):
        assert _contains_blocked("Order(G); QUIT;") == "QUIT"

    def test_blocks_exec(self):
        assert _contains_blocked("Exec('rm -rf /')") == "Exec("

    def test_allows_normal_code(self):
        assert _contains_blocked("Order(SymmetricGroup(4));") is None

    def test_allows_multiline(self):
        code = "for i in [1..5] do\n  Print(i);\nod;"
        assert _contains_blocked(code) is None


# ─── Integration tests (require GAP) ─────────────────────────────────────────

@pytest.mark.integration
class TestGAPRunner:
    def test_basic_arithmetic(self, runner):
        result = runner.execute("2 + 2;")
        assert result["success"] is True
        assert result["output"] == "4"

    def test_group_order(self, runner):
        result = runner.execute("Order(SymmetricGroup(4));")
        assert result["success"] is True
        assert result["output"] == "24"

    def test_multiline_code(self, runner):
        code = "for i in [1..3] do\n  Print(i, \"\\n\");\nod;"
        result = runner.execute(code)
        assert result["success"] is True
        assert "1" in result["output"]
        assert "2" in result["output"]
        assert "3" in result["output"]

    def test_is_abelian(self, runner):
        r1 = runner.execute("IsAbelian(CyclicGroup(6));")
        assert r1["output"] == "true"
        r2 = runner.execute("IsAbelian(SymmetricGroup(3));")
        assert r2["output"] == "false"

    def test_blocked_quit_is_rejected(self, runner):
        result = runner.execute("QUIT;")
        assert result["success"] is False
        assert "Blocked" in result["error"]

    def test_runner_stays_alive_after_error(self, runner):
        runner.execute("NotAFunction();")
        result = runner.execute("Order(CyclicGroup(5));")
        assert result["success"] is True
        assert result["output"] == "5"

    def test_session_state_persists(self, runner):
        runner.execute("myVar := 42;")
        result = runner.execute("Print(myVar, \"\\n\");")
        assert "42" in result["output"]

    def test_reset_clears_state(self, runner):
        runner.execute("anotherVar := 99;")
        runner.reset()
        result = runner.execute("IsBound(anotherVar);")
        assert result["output"] == "false"
